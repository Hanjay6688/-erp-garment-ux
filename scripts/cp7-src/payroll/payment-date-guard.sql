-- FIN01 (Fable FABLE-001, Astra FIN01; owner D14-2): an ordinary payroll payment
-- settles payable sources, so its economic date may not precede the latest
-- payable source of that payroll. Paying earlier needs a recorded kasbon.
-- The guard sits on the native row transition to PAID, so every caller of the
-- accepted native payment (CP7 PAY, final installment, legacy or direct calls)
-- is covered without editing the accepted native definition. Early installments
-- call the same assertion before any posting.
create function cp7_payroll.payment_floor(p_id uuid) returns date
language sql stable security definer set search_path='' as $$
 select max(d) from(
  -- Approval accruals (attendance, manual reimbursement/adjustment) are dated period_end.
  select je.economic_date d from erp.journal_entries je
   where je.source_id=p_id and je.status='POSTED'
    and je.source_type in('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION')
  union all
  -- WORK_COMPLETION accrues on the completion's WIB physical date.
  select (e.physical_at at time zone 'Asia/Jakarta')::date from erp.payroll_work_items w
   join erp.work_completion_lines l on l.id=w.source_id
   join erp.work_completion_events e on e.id=l.completion_id
   where w.payroll_id=p_id and w.source_type='PRODUCTION'
  union all
  -- REWORK_COMPLETION accrues on the rework's WIB completion date.
  select (coalesce(o.completed_at,o.physical_sent_at) at time zone 'Asia/Jakarta')::date from erp.payroll_work_items w
   join erp.rework_component_lines l on l.id=w.source_id
   join erp.rework_orders o on o.id=l.rework_order_id
   where w.payroll_id=p_id and w.source_type='REWORK'
  union all
  -- FG_UNSOURCED_RECEIPT accrues the repair wage on the receipt's WIB date.
  select (f.physical_at at time zone 'Asia/Jakarta')::date from erp.payroll_work_items w
   join erp.fg_unsourced_repair_wages_v1 f on f.id=w.source_id
   where w.payroll_id=p_id and w.source_type='FG_REPAIR'
  union all
  -- Accessory reimbursement entitlement is recognized on its physical date.
  select (e.physical_at at time zone 'Asia/Jakarta')::date from erp.payroll_reimbursements r
   join erp.contractor_accessory_reimbursement_entitlements e on e.id=r.source_id
   where r.payroll_id=p_id and r.source_type='ACCESSORY_BOM'
  union all
  -- A carried note-return credit is payable from its credit event.
  select (v.event_at at time zone 'Asia/Jakarta')::date from erp.payroll_reimbursements r
   join erp.bc_lot_events_v1 v on v.id=r.bc_credit_event_id
   where r.payroll_id=p_id
  union all
  -- Opening work entitlements are payable from cutover. Opening payables keep
  -- their own native dated floor (bb_assert_opening_balance_floor_v1).
  select b.cutover_date from erp.payroll_reimbursements r
   join erp.bb_payroll_entitlements_v1 b on b.id=r.opening_carry_entitlement_id
   where r.payroll_id=p_id
 ) x $$;

create function cp7_payroll.assert_payment_date(p_id uuid,p_date date) returns void
language plpgsql stable security definer set search_path='' as $$
declare v_floor date;
begin
 v_floor:=cp7_payroll.payment_floor(p_id);
 if p_date is not null and v_floor is not null and p_date<v_floor then
  raise exception 'CP7_PAYROLL_PAID_BEFORE_ACCRUAL: tanggal bayar % sebelum utang upah terakhir di payroll ini tercatat (%). Bayar sebelum itu hanya lewat kasbon.',p_date,v_floor;
 end if;
end $$;

create function cp7_payroll.guard_paid_date() returns trigger
language plpgsql volatile security definer set search_path='' as $$
begin
 if new.status='PAID' and old.status is distinct from 'PAID' then
  perform cp7_payroll.assert_payment_date(new.id,new.payment_date);
 end if;
 return new;
end $$;

create trigger cp7_payroll_paid_date_guard before update of status on erp.payroll_settlements
 for each row execute function cp7_payroll.guard_paid_date();

alter function cp7_payroll.payment_floor(uuid) owner to postgres;
alter function cp7_payroll.assert_payment_date(uuid,date) owner to postgres;
alter function cp7_payroll.guard_paid_date() owner to postgres;
revoke all on function cp7_payroll.payment_floor(uuid),cp7_payroll.assert_payment_date(uuid,date),cp7_payroll.guard_paid_date()
 from public,anon,authenticated,service_role,cp7_capture,cp7_payroll_read,cp7_nota_write,cp7_payroll_header,cp7_payroll_write;
