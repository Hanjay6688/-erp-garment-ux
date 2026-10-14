-- bootstrap lines 12238-12394
CREATE OR REPLACE FUNCTION erp.populate_payroll_draft(p_payroll_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.payroll_settlements%rowtype;
  r record;
  v_remaining numeric(24,6);
  v_apply numeric(24,6);
  v_budget numeric(24,6) := 0;
  v_attendance_required boolean;
begin
  perform erp.require_internal();
  select * into p from erp.payroll_settlements where id = p_payroll_id for update;
  if p.id is null or p.status not in ('DRAFT','CALCULATED','REVIEW') then
    raise exception 'Payroll draft cannot be rebuilt in current status';
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p.contractor_id::text, 0));

  delete from erp.payroll_work_items where payroll_id = p.id;
  delete from erp.payroll_attendance_items where payroll_id = p.id;
  delete from erp.payroll_deductions
    where payroll_id = p.id and contractor_issue_item_id is not null;
  delete from erp.payroll_reimbursements
    where payroll_id = p.id and source_type = 'ACCESSORY_BOM';

  insert into erp.payroll_work_items(
    payroll_id, po_id, work_component_id, source_type, source_id,
    qty_payable, rate_snapshot
  )
  select p.id, e.po_id, e.work_component_id, e.source_type, e.source_id,
         e.remaining_qty, e.rate_snapshot
  from erp.v_payroll_eligible_work_lines e
  where e.contractor_id = p.contractor_id
    and e.eligible_at::date <= p.period_end
    and e.remaining_qty > 0
  order by e.eligible_at, e.source_type, e.source_id;

  select attendance_required into v_attendance_required
  from erp.contractors where id = p.contractor_id;

  if v_attendance_required then
    insert into erp.payroll_attendance_items(
      payroll_id, worker_id, attendance_record_id,
      paid_fraction_snapshot, daily_rate_snapshot,
      worker_rate_version_id, attendance_date_snapshot,
      worker_name_snapshot, job_description_snapshot
    )
    select
      p.id,
      ar.worker_id,
      ar.id,
      ar.paid_fraction,
      erp.require_worker_daily_rate_at(ar.worker_id, ar.attendance_date),
      erp.worker_daily_rate_version_id_at(ar.worker_id, ar.attendance_date),
      ar.attendance_date,
      cw.worker_name,
      cw.job_description
    from erp.attendance_records ar
    join erp.contractor_workers cw on cw.id = ar.worker_id
    left join erp.attendance_periods ap on ap.id = ar.attendance_period_id
    where ar.contractor_id = p.contractor_id
      and ar.attendance_date between p.period_start and p.period_end
      and cw.pay_scheme in ('DAILY','HYBRID')
      and ar.paid_fraction > 0
      and (ar.attendance_period_id is null or ap.status = 'POSTED')
      and coalesce(ar.record_lifecycle, 'POSTED') = 'POSTED'
    order by ar.attendance_date, ar.id;
  end if;

  insert into erp.payroll_reimbursements(
    payroll_id, amount, description, source_type, source_id, po_id
  )
  select p.id, round(e.amount, 2),
         'Accessory reimbursement from accepted GOOD FG',
         'ACCESSORY_BOM', e.id, e.po_id
  from erp.contractor_accessory_reimbursement_entitlements e
  where e.contractor_id = p.contractor_id
    and e.amount > 0
    and e.payroll_status <> 'CANCELLED'
    and e.physical_at::date <= p.period_end
    and not exists (
      select 1
      from erp.payroll_reimbursements pr
      join erp.payroll_settlements ps2 on ps2.id = pr.payroll_id
      where pr.source_type = 'ACCESSORY_BOM'
        and pr.source_id = e.id
        and ps2.id <> p.id
        and ps2.status <> 'REVERSED'
    )
  order by e.physical_at, e.id;

  update erp.contractor_accessory_reimbursement_entitlements e
  set payroll_status = 'ALLOCATED'
  where exists (
    select 1
    from erp.payroll_reimbursements pr
    where pr.payroll_id = p.id
      and pr.source_type = 'ACCESSORY_BOM'
      and pr.source_id = e.id
  );

  perform erp.recalculate_payroll(p.id);
  select greatest(net_payable, 0) into v_budget
  from erp.payroll_settlements where id = p.id;

  for r in
    select
      cmii.id,
      cmii.total_receivable,
      cmi.physical_at,
      cmii.total_receivable - coalesce((
        select sum(pd.amount)
        from erp.payroll_deductions pd
        join erp.payroll_settlements ps2 on ps2.id = pd.payroll_id
        where pd.contractor_issue_item_id = cmii.id
          and ps2.id <> p.id
          and ps2.status <> 'REVERSED'
      ), 0) as remaining_amount
    from erp.contractor_material_issue_items cmii
    join erp.contractor_material_issues cmi on cmi.id = cmii.issue_id
    where cmi.contractor_id = p.contractor_id
      and cmi.status = 'POSTED'
      and cmi.physical_at::date <= p.period_end
    order by cmi.physical_at, cmii.id
  loop
    exit when v_budget <= 0;
    v_remaining := greatest(r.remaining_amount, 0);
    v_apply := least(v_remaining, v_budget);
    if v_apply > 0 then
      insert into erp.payroll_deductions(
        payroll_id, deduction_type, contractor_issue_item_id, amount, notes
      ) values (
        p.id, 'MATERIAL_KASBON', r.id, round(v_apply, 2),
        'Auto capped outstanding material/accessory kasbon (FIFO)'
      );
      v_budget := greatest(v_budget - round(v_apply, 2), 0);
    end if;
  end loop;

  perform erp.recalculate_payroll(p.id);
  for r in
    select cmii.id
    from erp.contractor_material_issue_items cmii
    join erp.contractor_material_issues cmi on cmi.id = cmii.issue_id
    where cmi.contractor_id = p.contractor_id
      and cmi.status = 'POSTED'
  loop
    perform erp.refresh_contractor_issue_payroll_status(r.id);
  end loop;
end;
$function$;

alter function "erp"."populate_payroll_draft"(p_payroll_id uuid) owner to "postgres";
