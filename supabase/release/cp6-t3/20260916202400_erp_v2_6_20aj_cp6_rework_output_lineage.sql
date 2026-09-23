-- CP6 AJ: distinct rework lot identity and retained cost lineage; row import diagnostics.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.audit_logs,erp.journal_entries,erp.journal_lines,
  erp.account_daily_balances,erp.sales_headers,erp.sales_items,
  erp.sale_stock_allocations,erp.sales_returns,erp.sales_return_items,
  erp.sales_payments,erp.fg_lots,erp.fg_stock_movements,
  erp.fg_inventory_balances,erp.hpp_versions,erp.product_conversions,
  erp.product_conversion_allocations,erp.laundry_deliveries,
  erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,erp.cp6_v2620j_rollback_capsule,
  erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,
  erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,
  erp.laundry_claims,erp.laundry_vendors,erp.cp6_v2620l_rollback_capsule,
  erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_subledger_balances,erp.opening_subledger_settlements,
  erp.opening_financial_corrections,erp.supplier_payments,
  erp.material_purchase_headers,erp.material_purchase_items,
  erp.material_supplier_invoices,erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,erp.material_supplier_return_items,
  erp.material_purchase_cost_corrections,
  erp.material_purchase_cost_correction_items,erp.material_stock_movements,
  erp.material_rolls,erp.cost_recalc_queue,erp.cost_adjustments,
  erp.suppliers,erp.materials,erp.cp6_v2620m_rollback_capsule,
  erp.supplier_cent_posting_facts,erp.material_cost_history,
  erp.material_cost_revaluation_state,erp.material_cost_revaluation_events,
  erp.material_cost_checkpoints,erp.cp6_v2620n_rollback_capsule,
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,
  erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule,
  erp.cp6_v2620s_rollback_capsule,erp.material_adjustments,
  erp.material_adjustment_items,erp.material_adjustment_revaluation_facts,
  erp.cp6_v2620t_rollback_capsule,erp.cp6_v2620u_rollback_capsule,
  erp.misc_finance_transactions,erp.misc_finance_categories,
  erp.cp6_v2620v_rollback_capsule,erp.scrap_batches,erp.scrap_sales,
  erp.cp6_v2620w_rollback_capsule,erp.app_roles,erp.app_role_permissions,erp.app_permissions,erp.cutting_bridge_execution_context,erp.bs_resolution_execution_context,erp.cp6_laundry_qc_execution_context
in share row exclusive mode;

do $lock_all_erp_v2620aj$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620aj_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620aj$;


do $predecessor_v2620aj$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ai')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20aj')
     or to_regclass('erp.cp6_v2620aj_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ai_rollback_capsule') is null then raise exception 'AJ_REQUIRES_EXACT_AI_WITHOUT_AJ_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ai_cp6_work_source_lineage')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='20260916090022' and name='erp_v2_6_20ai_cp6_work_source_lineage'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='1ea5a602c5a5fcc9697355d9cca526709a06ee20e4eb4cdb765b2b7345c18d25')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260916090022')
     or (select count(*) from erp.cp6_v2620ai_rollback_capsule)<>3 then raise exception 'AJ_REQUIRES_EXACT_AI_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    ('erp.post_rework_completion(uuid)','209338cc2b3099b163c0b344d1706a1f42dbdf804307e5fadee08e02f966f34d',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.rebuild_po_hpp(uuid,text)','9bbadaead01d33c7d23cab2172b1cc0b04a9fbe210bfab8a4d2724e936e6ef9b',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.cp6_lot_failed_wash_cost_v2620e(uuid)','cc02ece93afca767142d997fc6210c6d0d700633a998262fe95dd5435ea794bb',array['postgres=X/postgres']::text[]),
    ('erp._validate_migration_batch_base(uuid)','78f165c0b42edec0cfa8e3fa295abb64b94cde0df9af9b5611b5f6e4ec3e1fb6',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_migration_opening_stock_costs(uuid)','3b2316af1604ff6bc355ea3b7bb6559e32d41fa4c96b35af7e5f8c3bccb905e7',array['postgres=X/postgres']::text[]),
    ('erp.validate_migration_batch(uuid)','166aa25ae8bce86daedffc82f5db2cb3266a310b374518672080a08345271b26',array['authenticated=X/postgres','postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AJ_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620aj$;

create table erp.cp6_v2620aj_rollback_capsule(
  like erp.cp6_v2620ai_rollback_capsule including all
);
alter table erp.cp6_v2620aj_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620aj_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620aj_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,
    pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  array(select a::text from unnest(p.proacl) a order by a::text),
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in('erp.post_rework_completion(uuid)'::regprocedure,'erp.rebuild_po_hpp(uuid,text)'::regprocedure,'erp.cp6_lot_failed_wash_cost_v2620e(uuid)'::regprocedure,'erp._validate_migration_batch_base(uuid)'::regprocedure,'erp.validate_migration_opening_stock_costs(uuid)'::regprocedure,'erp.validate_migration_batch(uuid)'::regprocedure);


do $canonical_opening_v2620aj$
begin
  execute $definition$CREATE OR REPLACE FUNCTION erp.post_rework_completion(p_rework_order_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.rework_orders%rowtype;
  b erp.bs_cases%rowtype;
  v_total numeric(20,2):=0;
  v_location uuid;
  v_location_count integer:=0;
  v_lot uuid;
  v_lot_number text;
  v_hpp numeric(18,6):=0;
  v_remaining integer:=0;
  v_completed_at timestamptz;
begin
  perform erp.require_internal();
  select * into r from erp.rework_orders where id=p_rework_order_id for update;
  if r.id is null then raise exception 'Rework order not found'; end if;
  if r.status<>'COMPLETED' then raise exception 'Rework must be COMPLETED before posting'; end if;
  if r.qty_good_returned+r.qty_bs_returned<>r.qty_sent then
    raise exception 'Rework completion must reconcile exactly: GOOD + BS must equal qty sent';
  end if;
  if r.cost_posted then return; end if;
  if not exists(
    select 1 from erp.rework_accessory_decisions d where d.rework_order_id=r.id
  ) then raise exception 'Rework accessory decision lineage is missing'; end if;
  select * into b from erp.bs_cases where id=r.bs_case_id for update;
  if b.id is null then raise exception 'BS case not found'; end if;
  v_completed_at:=coalesce(r.completed_at,clock_timestamp());

  if r.qty_good_returned>0 then
    if b.po_id is null or b.product_id is null then
      raise exception 'GOOD rework return requires native production PO and product lineage';
    end if;
    if r.return_fg_location_id is not null then
      select id into v_location from erp.locations
      where id=r.return_fg_location_id and is_active and location_type='FG_WAREHOUSE';
      if v_location is null then
        raise exception 'Selected rework return location must be an active FG warehouse';
      end if;
    else
      select count(*),(array_agg(id order by id))[1]
      into v_location_count,v_location
      from erp.locations where is_active and location_type='FG_WAREHOUSE';
      if v_location_count<>1 then
        raise exception 'Select return FG warehouse for rework GOOD output; active FG warehouse count is %',v_location_count;
      end if;
    end if;
    v_lot_number:='RW-'||r.rework_number||'-'||substr(r.id::text,1,8);
    insert into erp.fg_lots(
      lot_number,po_id,qc_item_id,cutting_group_id,product_id,
      initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin
    ) values(
      -- qc_item_id identifies the single original QC output. Recovery is
      -- identified by rework_orders.good_fg_lot_id -> bs_cases -> source QC.
      v_lot_number,b.po_id,null,b.cutting_group_id,b.product_id,
      r.qty_good_returned,0,v_completed_at,true,'PRODUCTION'
    ) returning id into v_lot;
    perform erp.post_fg_movement(
      b.product_id,v_lot,v_location,'GRADE_A','REWORK_IN',r.qty_good_returned,
      0,null,'REWORK_ORDER',r.id,v_completed_at,'GOOD returned from rework',false
    );
    -- Link the lot before snapshotting so the immutable selection, including
    -- an explicit empty selection, is the only source the snapshotter can use.
    update erp.rework_orders
    set good_fg_lot_id=v_lot,return_fg_location_id=v_location,completed_at=v_completed_at
    where id=r.id;
    perform erp.ensure_fg_accessory_cost_snapshot(v_lot);
    perform erp.post_accessory_reimbursement_accrual(v_lot);
    insert into erp.bs_resolutions(
      bs_case_id,resolution_type,qty_pcs,compensation_amount,
      responsible_contractor_id,responsible_vendor_id,
      source_rework_order_id,physical_at,notes
    ) values(
      b.id,case when r.destination_type='CONTRACTOR'
        then 'REWORK_SEWING' else 'REWORK_LAUNDRY' end,
      r.qty_good_returned,0,r.contractor_id,r.vendor_id,r.id,v_completed_at,
      'Recovered to GOOD FG from rework'
    );
  else
    update erp.rework_orders set completed_at=v_completed_at where id=r.id;
  end if;

  select greatest(b.qty_pcs-coalesce(sum(br.qty_pcs),0),0)::integer
  into v_remaining from erp.bs_resolutions br where br.bs_case_id=b.id;
  update erp.bs_cases
  set status=case when v_remaining=0 then 'RESOLVED' else 'PARTIAL' end,
      updated_at=clock_timestamp()
  where id=b.id;
  if r.destination_type='CONTRACTOR' then
    select coalesce(sum(amount_payable),0) into v_total
    from erp.rework_component_lines where rework_order_id=r.id;
    if v_total>0 then
      perform erp.post_journal(
        'REWORK_COMPLETION',r.id,(v_completed_at AT TIME ZONE 'Asia/Jakarta')::date,'Rework labor completion',
        jsonb_build_array(
          jsonb_build_object(
            'mapping_key','WIP','debit',round(v_total,2),'credit',0,
            'contractor_id',r.contractor_id,'po_id',b.po_id
          ),
          jsonb_build_object(
            'mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_total,2),
            'contractor_id',r.contractor_id,'po_id',b.po_id
          )
        )
      );
    end if;
  end if;
  update erp.rework_orders set cost_posted=true where id=r.id;
  if b.po_id is not null and exists(select 1 from erp.fg_lots where po_id=b.po_id) then
    perform erp.rebuild_po_hpp(b.po_id,'Rework completion posted with physical GOOD return');
    perform erp.propagate_conversion_hpp_for_po(b.po_id);
    perform erp.sync_po_hpp_to_gl(b.po_id,(v_completed_at AT TIME ZONE 'Asia/Jakarta')::date);
    if v_lot is not null then
      select coalesce(hpp_per_pcs,0) into v_hpp
      from erp.v_current_hpp where lot_id=v_lot;
      update erp.fg_stock_movements set unit_hpp_snapshot=v_hpp
      where lot_id=v_lot and movement_type='REWORK_IN'
        and source_type='REWORK_ORDER' and source_id=r.id;
    end if;
  end if;
end
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.rebuild_po_hpp(p_po_id uuid, p_reason text DEFAULT 'Recalculate HPP'::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_material numeric(24,6):=0;
  v_material_allocated numeric(24,6):=0;
  v_contractor_material numeric(24,6):=0;
  v_accessory numeric(24,6):=0;
  v_labor numeric(24,6):=0;
  v_commission numeric(24,6):=0;
  v_laundry numeric(24,6):=0;
  v_rework numeric(24,6):=0;
  v_other numeric(24,6):=0;
  v_attendance_hpp numeric(24,6):=0;
  v_shared_attendance_hpp numeric(24,6):=0;
  v_shared_labor numeric(24,6):=0;
  v_shared_commission numeric(24,6):=0;
  v_shared_rework numeric(24,6):=0;
  v_shared_other numeric(24,6):=0;
  v_total_current numeric(24,6):=0;
  v_total_qty integer:=0;
  v_pending boolean:=false;
  r record;
  c record;
  v_old_id uuid;
  v_new_id uuid;
  v_version integer;
  v_lot_accessory numeric(24,6);
  v_lot_cost numeric(24,6);
  v_lot_material numeric(24,6);
  v_pool_material numeric(24,6);
  v_pool_qty numeric(24,6);
  v_batch_id uuid;
  v_state varchar(20);
  v_group_fg_qty numeric(24,6);
  v_group_labor numeric(24,6);
  v_group_commission numeric(24,6);
  v_group_laundry numeric(24,6);
  v_group_rework numeric(24,6);
  v_group_attendance_hpp numeric(24,6);
  v_lot_attendance_hpp numeric(24,6);
  v_lot_labor numeric(24,6);
  v_lot_commission numeric(24,6);
  v_lot_laundry numeric(24,6);
  v_lot_rework numeric(24,6);
  v_lot_other numeric(24,6);
  v_cp6_lineage boolean:=false;
  v_lot_cp6_receipt_laundry numeric(24,6):=0;
  v_lot_cp6_attempt_laundry numeric(24,6):=0;
  v_laundry_allocated numeric(24,6):=0;
  v_labor_allocated numeric(24,6):=0;
  v_commission_allocated numeric(24,6):=0;
  v_rework_allocated numeric(24,6):=0;
  v_attendance_allocated numeric(24,6):=0;
  v_po_source_qty numeric(24,6):=0;
begin
  perform erp.require_internal();
  -- One lock order covers Draft reservation, post/reversal, late recost, and GL sync.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));

  select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_material
  from erp.material_stock_movements msm
  where (msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id))
     or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id));

  select coalesce(sum(cmii.qty*cmii.unit_cost_snapshot),0) into v_contractor_material
  from erp.contractor_material_issue_items cmii
  join erp.contractor_material_issues cmi on cmi.id=cmii.issue_id
  join erp.materials m on m.id=cmii.material_id
  where cmi.po_id=p_po_id and cmi.status='POSTED' and m.material_type<>'ACCESSORY';

  select
    coalesce(sum(case when wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wce.cutting_group_id is null and wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wce.cutting_group_id is null and wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0)
  into v_commission,v_labor,v_shared_commission,v_shared_labor
  from erp.work_completion_lines wcl
  join erp.work_completion_events wce on wce.id=wcl.completion_id
  join erp.work_components wc on wc.id=wcl.work_component_id
  where wce.po_id=p_po_id and wce.status='POSTED';

  with dl as (
    select ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot,
           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then lrl.qty_good_received+lrl.qty_bs_laundry else 0 end),0) as qty_costed_actual,
           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0) else 0 end),0) as actual_cost,
           bool_or(lr.status='POSTED' and lrl.actual_cost_status in('PENDING','ESTIMATED')) as has_pending_receipt
    from erp.laundry_delivery_lines ldl
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
    left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where ld.po_id=p_po_id and ld.status<>'REVERSED'
    group by ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
  )
  select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0),
         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual),false)
  into v_laundry,v_pending from dl;

  select v_laundry+coalesce(sum(rl.actual_cost),0)
    into v_laundry
  from erp.laundry_failed_wash_attempts a
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
  join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
  join erp.laundry_deliveries ld on ld.id=a.delivery_id and ld.status='REVERSED'
  where ld.po_id=p_po_id and rl.actual_cost_status in('ESTIMATED','FINAL');

  v_pending:=v_pending or exists(
    select 1
    from erp.laundry_failed_wash_attempts a
    join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
    join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    join erp.laundry_deliveries ld on ld.id=a.delivery_id
    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED'
  );


  select coalesce(sum(rcl.amount_payable),0),
         coalesce(sum(case when bc.cutting_group_id is null then rcl.amount_payable else 0 end),0)
  into v_rework,v_shared_rework
  from erp.rework_component_lines rcl
  join erp.rework_orders ro on ro.id=rcl.rework_order_id
  join erp.bs_cases bc on bc.id=ro.bs_case_id
  where bc.po_id=p_po_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

  select coalesce(sum(adjustment_amount),0),coalesce(sum(case when lot_id is null then adjustment_amount else 0 end),0)
  into v_other,v_shared_other
  from erp.cost_adjustments
  where po_id=p_po_id and component_type='OTHER';

  select
    coalesce(sum(a.allocated_amount),0),
    coalesce(sum(case when a.cutting_group_id is null then a.allocated_amount else 0 end),0)
  into v_attendance_hpp,v_shared_attendance_hpp
  from erp.attendance_hpp_pool_allocations a
  join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
  where a.po_id=p_po_id;

  select coalesce(sum(initial_qty_pcs),0) into v_total_qty
  from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION';
  if v_total_qty<=0 then return; end if;
  v_po_source_qty:=erp.cp6_po_source_qty_v2620c(p_po_id);
  if coalesce(v_po_source_qty,0)<=0 then
    raise exception 'PO source quantity is required before HPP can be allocated';
  end if;

  for r in select id from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION' order by produced_at,id
  loop perform erp.ensure_fg_accessory_cost_snapshot(r.id); end loop;

  select coalesce(sum(facs.total_hpp_cost),0) into v_accessory
  from erp.fg_accessory_cost_snapshots facs join erp.fg_lots fl on fl.id=facs.lot_id
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION';

  v_state:=case when v_pending then 'ESTIMATED' when exists (select 1 from erp.cost_adjustments where po_id=p_po_id) then 'ADJUSTED' else 'ACTUAL' end;

  for r in
    select fl.*,coalesce(fl.qc_item_id,(
      select bc.qc_item_id from erp.rework_orders ro
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where ro.good_fg_lot_id=fl.id
    )) as source_qc_item_id,
      coalesce(fl.cutting_group_id,qi.cutting_group_id) as lineage_group_id
    from erp.fg_lots fl left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
    where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
    order by fl.produced_at,fl.id
  loop
    v_lot_material:=0;v_pool_material:=0;v_pool_qty:=0;v_batch_id:=null;
    v_group_fg_qty:=0;v_group_labor:=0;v_group_commission:=0;v_group_laundry:=0;v_group_rework:=0;v_group_attendance_hpp:=0;
    v_cp6_lineage:=false;v_lot_cp6_receipt_laundry:=0;v_lot_cp6_attempt_laundry:=0;

    if r.lineage_group_id is not null then
      select cutting_batch_id into v_batch_id from erp.cutting_groups where id=r.lineage_group_id;
      if v_batch_id is not null then
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where (msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id))
           or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id));
        select effective_pcs::numeric into v_pool_qty from erp.v_cutting_batch_totals where cutting_batch_id=v_batch_id;
      else
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where msm.source_id=r.lineage_group_id and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN');
        select total_pcs::numeric into v_pool_qty from erp.v_cutting_group_totals where cutting_group_id=r.lineage_group_id;
      end if;

      select coalesce(sum(fl2.initial_qty_pcs),0)::numeric into v_group_fg_qty
      from erp.fg_lots fl2 where fl2.po_id=p_po_id and fl2.lot_origin='PRODUCTION' and fl2.cutting_group_id=r.lineage_group_id;

      select
        coalesce(sum(case when wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0),
        coalesce(sum(case when wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0)
      into v_group_labor,v_group_commission
      from erp.work_completion_lines wcl
      join erp.work_completion_events wce on wce.id=wcl.completion_id
      join erp.work_components wc on wc.id=wcl.work_component_id
      where wce.po_id=p_po_id and wce.status='POSTED' and wce.cutting_group_id=r.lineage_group_id;

      with dl as (
        select ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot,
               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then lrl.qty_good_received+lrl.qty_bs_laundry else 0 end),0) as qty_costed_actual,
               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0) else 0 end),0) as actual_cost
        from erp.laundry_delivery_lines ldl
        join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
        left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
        left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
        where ld.po_id=p_po_id and ld.status<>'REVERSED' and ldl.cutting_group_id=r.lineage_group_id
        group by ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
      )
      select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0)
      into v_group_laundry from dl;

      select v_group_laundry+coalesce(sum(rl.actual_cost),0)
        into v_group_laundry
      from erp.laundry_failed_wash_attempts a
      join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
      join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
      join erp.laundry_deliveries ld on ld.id=a.delivery_id and ld.status='REVERSED'
      join erp.laundry_delivery_lines ldl on ldl.delivery_id=ld.id
      where ld.po_id=p_po_id and ldl.cutting_group_id=r.lineage_group_id
        and rl.actual_cost_status in('ESTIMATED','FINAL');


      select coalesce(sum(rcl.amount_payable),0) into v_group_rework
      from erp.rework_component_lines rcl
      join erp.rework_orders ro on ro.id=rcl.rework_order_id
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where bc.po_id=p_po_id and bc.cutting_group_id=r.lineage_group_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

      select coalesce(sum(a.allocated_amount),0) into v_group_attendance_hpp
      from erp.attendance_hpp_pool_allocations a
      join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
      where a.po_id=p_po_id and a.cutting_group_id=r.lineage_group_id;
    end if;

    select exists(
      select 1
      from erp.qc_inspection_items qi
      join erp.laundry_receipt_batch_size_lines rx
        on rx.id=qi.source_laundry_receipt_batch_size_line_id
      where qi.id=r.source_qc_item_id
    ) into v_cp6_lineage;

    if v_cp6_lineage then
      select coalesce((case
          when rl.actual_cost_status in('ESTIMATED','FINAL') and rl.actual_cost is not null
            then rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)
          else coalesce(rl.actual_rate_snapshot,dl.estimated_rate_snapshot,0)
        end)*r.initial_qty_pcs,0)
      into v_lot_cp6_receipt_laundry
      from erp.qc_inspection_items qi
      join erp.laundry_receipt_batch_size_lines rx
        on rx.id=qi.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
        and rl.id=qi.source_laundry_receipt_line_id
      join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
      join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
      left join erp.laundry_failed_wash_attempts fa on fa.receipt_line_id=rl.id
      where qi.id=r.source_qc_item_id and fa.id is null;
      v_lot_cp6_receipt_laundry:=coalesce(v_lot_cp6_receipt_laundry,0);

      select erp.cp6_lot_failed_wash_cost_v2620e(r.id)
      into v_lot_cp6_attempt_laundry;
    end if;

    if coalesce(v_pool_qty,0)>0 then v_lot_material:=v_pool_material*(r.initial_qty_pcs::numeric/v_pool_qty);
    else v_lot_material:=v_material*(r.initial_qty_pcs::numeric/v_total_qty::numeric); end if;
    v_lot_material:=v_lot_material+v_contractor_material*(r.initial_qty_pcs::numeric/v_po_source_qty);
    v_material_allocated:=v_material_allocated+v_lot_material;

    v_lot_labor:=erp.cp6_lot_work_cost_v2620c(r.id,'LABOR');
    v_lot_commission:=erp.cp6_lot_work_cost_v2620c(r.id,'COMMISSION');
    v_lot_laundry:=case when v_cp6_lineage
      then v_lot_cp6_receipt_laundry+v_lot_cp6_attempt_laundry
      when r.lineage_group_id is not null then v_group_laundry*(r.initial_qty_pcs::numeric/nullif(
        coalesce(nullif((select total_pcs::numeric from erp.v_cutting_group_totals
          where cutting_group_id=r.lineage_group_id),0),v_po_source_qty),0))
      else v_laundry*(r.initial_qty_pcs::numeric/v_po_source_qty) end;
    v_lot_rework:=erp.cp6_lot_rework_cost_v2620c(r.id);
    v_lot_attendance_hpp:=erp.cp6_lot_attendance_cost_v2620c(r.id);

    select coalesce(sum(total_hpp_cost),0) into v_lot_accessory from erp.fg_accessory_cost_snapshots where lot_id=r.id;
    select coalesce(sum(adjustment_amount),0) into v_lot_other from erp.cost_adjustments where lot_id=r.id and component_type='OTHER';
    v_lot_other:=v_lot_other+v_shared_other*(r.initial_qty_pcs::numeric/v_po_source_qty);
    v_laundry_allocated:=v_laundry_allocated+v_lot_laundry;
    v_labor_allocated:=v_labor_allocated+v_lot_labor;
    v_commission_allocated:=v_commission_allocated+v_lot_commission;
    v_rework_allocated:=v_rework_allocated+v_lot_rework;
    v_attendance_allocated:=v_attendance_allocated+v_lot_attendance_hpp;
    v_lot_cost:=v_lot_material+v_lot_labor+v_lot_commission+v_lot_laundry+v_lot_rework+v_lot_attendance_hpp+v_lot_other+v_lot_accessory;
    v_total_current:=v_total_current+v_lot_cost;

    select id into v_old_id from erp.hpp_versions where lot_id=r.id and is_current=true order by version_no desc limit 1;
    select coalesce(max(version_no),0)+1 into v_version from erp.hpp_versions where lot_id=r.id;
    if v_old_id is not null then update erp.hpp_versions set is_current=false where id=v_old_id; end if;

    insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,supersedes_id,calculation_reason,created_by)
    values (r.id,v_version,v_state,r.initial_qty_pcs,v_lot_cost,true,v_old_id,p_reason,erp.current_app_user_id()) returning id into v_new_id;

    insert into erp.hpp_version_components(hpp_version_id,component_type,description,total_cost,source_type,source_id)
    values
      (v_new_id,'MATERIAL',case when v_batch_id is not null then 'Cutting material by effective batch yield + PO-shared non-accessory contractor material' else 'Cutting/legacy material pool + PO-shared non-accessory contractor material' end,v_lot_material,case when v_batch_id is not null then 'CUTTING_BATCH' else 'PO' end,coalesce(v_batch_id,p_po_id)),
      (v_new_id,'LABOR','Labor allocation: immutable component completion intervals; unfinished remains WIP',v_lot_labor,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'COMMISSION','Commission allocation: immutable component completion intervals; unfinished remains WIP',v_lot_commission,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LAUNDRY',case when v_cp6_lineage
        then 'CP6 exact receipt/batch-size service lineage; unfinished cost remains WIP'
        else 'Legacy Laundry allocation from same cutting group; PENDING uses estimate' end,
        v_lot_laundry,case when v_cp6_lineage then 'QC_ITEM'
          when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,
        case when v_cp6_lineage then r.source_qc_item_id else coalesce(r.lineage_group_id,p_po_id) end),
      (v_new_id,'REWORK','Rework allocation: exact good rework lot and qty-sent source',v_lot_rework,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LABOR','Attendance HPP: ACTIVE source sewing intervals; unfinished remains WIP',v_lot_attendance_hpp,'ATTENDANCE_HPP_ACTIVE_ALLOCATION',coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'OTHER','Other/adjustment allocation',v_lot_other,'PO',p_po_id);

    for c in
      select facs.id,facs.total_hpp_cost,ac.category_name,facs.hpp_method
      from erp.fg_accessory_cost_snapshots facs join erp.accessory_categories ac on ac.id=facs.category_id
      where facs.lot_id=r.id order by ac.category_code
    loop
      insert into erp.hpp_version_components(hpp_version_id,component_type,description,total_cost,source_type,source_id)
      values (v_new_id,'ACCESSORY','Accessory category: '||c.category_name||' ['||c.hpp_method||']',c.total_hpp_cost,'FG_ACCESSORY_SNAPSHOT',c.id);
    end loop;

    update erp.fg_stock_movements set unit_hpp_snapshot=(select hpp_per_pcs from erp.hpp_versions where id=v_new_id)
    where lot_id=r.id and movement_type in ('QC_GOOD','REWORK_IN');
  end loop;

  if v_labor_allocated < -0.005 or v_labor_allocated > v_labor+0.005
     or v_commission_allocated < -0.005 or v_commission_allocated > v_commission+0.005
     or v_rework_allocated < -0.005 or v_rework_allocated > v_rework+0.005
     or v_attendance_allocated < -0.005 or v_attendance_allocated > v_attendance_hpp+0.005 then
    raise exception 'CP6 source-owned HPP allocation violates cost conservation: labor %/%, commission %/%, rework %/%, attendance %/%',
      v_labor_allocated,v_labor,v_commission_allocated,v_commission,
      v_rework_allocated,v_rework,v_attendance_allocated,v_attendance_hpp;
  end if;

  if v_laundry_allocated < -0.005 or v_laundry_allocated > v_laundry+0.005 then
    raise exception 'CP6 Laundry HPP allocation violates cost conservation: accrued %, FG allocated %',
      v_laundry,v_laundry_allocated;
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values ('production_orders',p_po_id,'RECALCULATE',jsonb_build_object(
    'material_total_issued',v_material+v_contractor_material,'cutting_material_total',v_material,'contractor_nonaccessory_material_total',v_contractor_material,'material_allocated_to_current_fg',v_material_allocated,'material_basis','CUTTING_BATCH_EFFECTIVE_YIELD_PLUS_PO_SHARED_CONTRACTOR_MATERIAL',
    'accessory',v_accessory,'labor',v_labor,'attendance_hpp',v_attendance_hpp,'commission',v_commission,'laundry',v_laundry,'rework',v_rework,'other',v_other,
    'laundry_allocated_to_current_fg',v_laundry_allocated,
    'laundry_remaining_in_wip',v_laundry-v_laundry_allocated,
    'labor_allocated_to_fg',v_labor_allocated,'labor_remaining_in_wip',v_labor-v_labor_allocated,
    'commission_allocated_to_fg',v_commission_allocated,'commission_remaining_in_wip',v_commission-v_commission_allocated,
    'rework_allocated_to_fg',v_rework_allocated,'rework_remaining_in_wip',v_rework-v_rework_allocated,
    'attendance_allocated_to_fg',v_attendance_allocated,'attendance_remaining_in_wip',v_attendance_hpp-v_attendance_allocated,
    'po_physical_source_qty',v_po_source_qty,
    'laundry_basis','CP6_EXACT_DELIVERY_SIZE_CUSTODY_INTERVAL_V2620C',
    'total_current_fg_cost',v_total_current,'cost_state',v_state,'nonmaterial_basis','CUTTING_GROUP_LINEAGE_WITH_PO_SHARED_FALLBACK','accessory_basis','GOOD_FG_X_CATEGORY_BOM'),
    erp.current_app_user_id(),p_reason);
end;
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.cp6_lot_failed_wash_cost_v2620e(p_lot_id uuid)
 RETURNS numeric
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
with recursive lot_source as(
  select fl.initial_qty_pcs::numeric lot_qty,
    rx.delivery_batch_size_line_id final_line_id,
    rx.qty_good_received::numeric+rx.qty_bs_laundry::numeric receipt_qty,
    rh.physical_at receipt_at,rh.id receipt_id,rx.id receipt_batch_size_id,
    sx.qty_sent_pcs::numeric final_line_qty,
    coalesce((
      select sum(px.qty_good_received+px.qty_bs_laundry)::numeric
      from erp.laundry_receipt_batch_size_lines px
      join erp.laundry_receipt_lines pl on pl.id=px.receipt_line_id
      join erp.laundry_receipts ph on ph.id=pl.receipt_id and ph.status='POSTED'
      where px.delivery_batch_size_line_id=rx.delivery_batch_size_line_id
        and (ph.physical_at,ph.id,px.id)<(rh.physical_at,rh.id,rx.id)
    ),0) receipt_start
  from erp.fg_lots fl
  join erp.qc_inspection_items qi on qi.id=coalesce(fl.qc_item_id,(
      select bc.qc_item_id from erp.rework_orders ro
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where ro.good_fg_lot_id=fl.id
    ))
  join erp.laundry_receipt_batch_size_lines rx
    on rx.id=qi.source_laundry_receipt_batch_size_line_id
  join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
    and rl.id=qi.source_laundry_receipt_line_id
  join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
  join erp.laundry_delivery_batch_size_lines sx
    on sx.id=rx.delivery_batch_size_line_id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
), effective_allocations as(
  select a.*
  from erp.laundry_redispatch_participant_events a
  where a.event_type='ALLOCATE'
    and not exists(select 1 from erp.laundry_redispatch_participant_events x
      where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
), participant_map(line_id,line_start,line_end,final_start,final_end,path) as(
  select s.final_line_id,0::numeric,s.final_line_qty,0::numeric,s.final_line_qty,
    array[s.final_line_id]::uuid[]
  from lot_source s
  union all
  select a.source_delivery_batch_size_line_id,
    a.source_offset_pcs::numeric+(o.overlap_start-a.successor_offset_pcs),
    a.source_offset_pcs::numeric+(o.overlap_end-a.successor_offset_pcs),
    m.final_start+(o.overlap_start-m.line_start),
    m.final_start+(o.overlap_end-m.line_start),
    m.path||a.source_delivery_batch_size_line_id
  from participant_map m
  join effective_allocations a
    on a.successor_delivery_batch_size_line_id=m.line_id
  cross join lateral(
    select greatest(m.line_start,a.successor_offset_pcs::numeric) overlap_start,
      least(m.line_end,(a.successor_offset_pcs+a.qty_pcs)::numeric) overlap_end
  ) o
  where o.overlap_end>o.overlap_start
    and not a.source_delivery_batch_size_line_id=any(m.path)
), attempts as(
  select ax.delivery_batch_size_line_id line_id,
    ax.qty_attempted_pcs::numeric attempt_qty,
    coalesce(rl.actual_cost,a.qty_attempted_pcs*coalesce(rl.actual_rate_snapshot,0))
      *(ax.qty_attempted_pcs::numeric/nullif(a.qty_attempted_pcs,0)) size_cost,
    coalesce((
      select sum(px.qty_good_received+px.qty_bs_laundry)::numeric
      from erp.laundry_receipt_batch_size_lines px
      join erp.laundry_receipt_lines pl on pl.id=px.receipt_line_id
      join erp.laundry_receipts ph on ph.id=pl.receipt_id and ph.status='POSTED'
      where px.delivery_batch_size_line_id=ax.delivery_batch_size_line_id
        and (ph.physical_at,ph.id)<(ah.physical_at,ah.id)
    ),0) attempt_start
  from erp.laundry_failed_wash_batch_size_lines ax
  join erp.laundry_failed_wash_attempts a on a.id=ax.attempt_id
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    and rl.actual_cost_status in('ESTIMATED','FINAL')
  join erp.laundry_receipts ah on ah.id=a.receipt_id and ah.status='POSTED'
), mapped_attempts as(
  select
    m.final_start+(greatest(m.line_start,a.attempt_start)-m.line_start) attempt_final_start,
    m.final_start+(least(m.line_end,a.attempt_start+a.attempt_qty)-m.line_start) attempt_final_end,
    a.size_cost/nullif(a.attempt_qty,0) cost_per_participant
  from participant_map m join attempts a on a.line_id=m.line_id
  where least(m.line_end,a.attempt_start+a.attempt_qty)>greatest(m.line_start,a.attempt_start)
)
select coalesce(sum(
  greatest(least(s.receipt_start+s.receipt_qty,a.attempt_final_end)
    -greatest(s.receipt_start,a.attempt_final_start),0)
  *a.cost_per_participant*s.lot_qty/nullif(s.receipt_qty,0)
),0)::numeric
from lot_source s left join mapped_attempts a on true
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp._validate_migration_batch_base(p_batch_id uuid)
 RETURNS TABLE(total_rows bigint, valid_rows bigint, error_rows bigint)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare r record;e jsonb;v_required text[];k text;v_total bigint;v_valid bigint;v_error bigint;v_bt text;v_material_type text;v_number numeric;
begin
  perform erp.require_owner_admin();
  if not exists(select 1 from erp.migration_batches where id=p_batch_id) then raise exception 'Migration batch not found'; end if;
  update erp.migration_batches set status='VALIDATING',error_message=null where id=p_batch_id;
  update erp.migration_staging_rows set validation_status='PENDING',validation_errors='[]'::jsonb,updated_at=statement_timestamp() where batch_id=p_batch_id;
  update erp.migration_staging_rows s set validation_status='ERROR',validation_errors=jsonb_build_array('Duplicate legacy_key inside entity type'),updated_at=statement_timestamp()
  where s.batch_id=p_batch_id and s.legacy_key is not null and exists(select 1 from erp.migration_staging_rows d where d.batch_id=s.batch_id and d.entity_type=s.entity_type and d.legacy_key=s.legacy_key and d.id<>s.id);

  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id order by entity_type,source_row_no loop
    e:='[]'::jsonb;
    begin
      -- A malformed input is a row error. It must not roll back diagnostics
      -- for the entire batch or be accepted as NaN/infinite business quantity.
      foreach k in array array['qty','opening_qty','unit_cost','amount',
        'hpp_percent_of_price','target_qty_pcs','target_dozens'] loop
        if nullif(btrim(r.normalized_payload->>k),'') is not null then
          v_number:=(r.normalized_payload->>k)::numeric;
          if v_number::text in('NaN','Infinity','-Infinity') then
            e:=e||jsonb_build_array('Field must be a finite number: '||k);
          end if;
        end if;
      end loop;
    if jsonb_typeof(r.normalized_payload)<>'object' then e:=e||jsonb_build_array('normalized_payload must be a JSON object'); end if;
    v_required:=case r.entity_type
      when 'BRAND' then array['brand_code','brand_name']
      when 'SIZE' then array['size_code']
      when 'MODEL' then array['model_code','model_name']
      when 'PRODUCT' then array['sku','product_name','model_code','brand_code','color_name','size_code']
      when 'CUSTOMER' then array['customer_code','customer_name']
      when 'SUPPLIER' then array['supplier_code','supplier_name']
      when 'CONTRACTOR' then array['contractor_code','contractor_name']
      when 'ACCESSORY_CATEGORY' then array['category_code','category_name','base_uom_code']
      when 'MATERIAL' then array['material_sku','material_name','material_type','unit_code']
      when 'MATERIAL_ROLL' then array['material_sku','roll_number','opening_qty','unit_cost','location_code']
      when 'OPENING_BALANCE_ITEM' then array['balance_type']
      when 'OPEN_PO' then array['po_number','model_code','status','current_stage']
      else array[]::text[] end;
    foreach k in array v_required loop
      if nullif(trim(coalesce(r.normalized_payload->>k,'')),'') is null then e:=e||jsonb_build_array('Missing required field: '||k); end if;
    end loop;

    if r.entity_type='ACCESSORY_CATEGORY' and not exists(select 1 from erp.uom_definitions where unit_code=upper(r.normalized_payload->>'base_uom_code')) then e:=e||jsonb_build_array('Unknown base_uom_code'); end if;
    if r.entity_type='MATERIAL' then
      if upper(coalesce(r.normalized_payload->>'material_type','')) not in('FABRIC','ACCESSORY','OTHER') then e:=e||jsonb_build_array('material_type must be FABRIC, ACCESSORY or OTHER'); end if;
      if upper(coalesce(r.normalized_payload->>'material_type',''))='ACCESSORY' and nullif(trim(coalesce(r.normalized_payload->>'accessory_category_code','')),'') is null then e:=e||jsonb_build_array('ACCESSORY material requires accessory_category_code'); end if;
    end if;
    if r.entity_type='MATERIAL_ROLL' then
      if coalesce(nullif(r.normalized_payload->>'opening_qty','')::numeric,0)<=0 then e:=e||jsonb_build_array('MATERIAL_ROLL opening_qty must be positive'); end if;
      if coalesce(nullif(r.normalized_payload->>'unit_cost','')::numeric,-1)<0 then e:=e||jsonb_build_array('MATERIAL_ROLL unit_cost must be zero or positive'); end if;
      select material_type into v_material_type from erp.materials where material_sku=r.normalized_payload->>'material_sku';
      if v_material_type is null then
        select upper(s.normalized_payload->>'material_type') into v_material_type from erp.migration_staging_rows s
        where s.batch_id=p_batch_id and s.entity_type='MATERIAL' and s.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku' limit 1;
      end if;
      if coalesce(v_material_type,'')<>'FABRIC' then e:=e||jsonb_build_array('MATERIAL_ROLL requires a FABRIC material'); end if;
      if not exists(select 1 from erp.locations where location_code=r.normalized_payload->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true) then e:=e||jsonb_build_array('MATERIAL_ROLL location_code must be an active raw-material warehouse'); end if;
      if nullif(trim(coalesce(r.normalized_payload->>'supplier_code','')),'') is not null
         and not exists(select 1 from erp.suppliers where supplier_code=r.normalized_payload->>'supplier_code')
         and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='SUPPLIER' and s.normalized_payload->>'supplier_code'=r.normalized_payload->>'supplier_code') then
        e:=e||jsonb_build_array('Unknown MATERIAL_ROLL supplier_code');
      end if;
      if exists(select 1 from erp.migration_staging_rows d where d.batch_id=p_batch_id and d.entity_type='MATERIAL_ROLL' and d.id<>r.id
                and d.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku' and d.normalized_payload->>'roll_number'=r.normalized_payload->>'roll_number') then
        e:=e||jsonb_build_array('Duplicate roll_number for material inside migration batch');
      end if;
      if exists(select 1 from erp.material_rolls mr join erp.materials m on m.id=mr.material_id where m.material_sku=r.normalized_payload->>'material_sku' and mr.roll_number=r.normalized_payload->>'roll_number') then
        e:=e||jsonb_build_array('MATERIAL_ROLL conflicts with an existing roll number');
      end if;
    end if;

    if r.entity_type='OPENING_BALANCE_ITEM' then
      v_bt:=upper(coalesce(r.normalized_payload->>'balance_type',''));
      if v_bt not in('MATERIAL','FINISHED_GOODS','WIP','BS','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','CUSTOMER_RECEIVABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CASH_BANK') then e:=e||jsonb_build_array('Unsupported opening balance_type for migration framework'); end if;
      if v_bt='MATERIAL' and(nullif(r.normalized_payload->>'material_sku','') is null or nullif(r.normalized_payload->>'location_code','') is null or coalesce(nullif(r.normalized_payload->>'qty','')::numeric,0)<=0) then e:=e||jsonb_build_array('MATERIAL opening needs material_sku, location_code and positive qty'); end if;
      if v_bt='MATERIAL' and exists(select 1 from erp.materials m where m.material_sku=r.normalized_payload->>'material_sku' and m.material_type='FABRIC') then e:=e||jsonb_build_array('FABRIC opening stock must use MATERIAL_ROLL rows, not anonymous MATERIAL opening'); end if;
      if v_bt='FINISHED_GOODS' and(nullif(r.normalized_payload->>'product_sku','') is null or coalesce(nullif(r.normalized_payload->>'qty','')::numeric,0)<=0) then e:=e||jsonb_build_array('FINISHED_GOODS opening needs product_sku and positive qty'); end if;
      if v_bt in('CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') and(nullif(r.normalized_payload->>'contractor_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Contractor opening balance needs contractor_code and positive amount'); end if;
      if v_bt='CUSTOMER_RECEIVABLE' and(nullif(r.normalized_payload->>'customer_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Customer receivable opening needs customer_code and positive amount'); end if;
      if v_bt='SUPPLIER_PAYABLE' and(nullif(r.normalized_payload->>'supplier_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Supplier payable opening needs supplier_code and positive amount'); end if;
      if v_bt='VENDOR_PAYABLE' and(nullif(r.normalized_payload->>'vendor_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Vendor payable opening needs vendor_code and positive amount'); end if;
      if v_bt='CASH_BANK' and(nullif(r.normalized_payload->>'cash_account_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('CASH_BANK opening needs cash_account_code and positive amount'); end if;
    end if;
    if r.entity_type='OPEN_PO' then
      if upper(coalesce(r.normalized_payload->>'status','')) not in('DRAFT','CUTTING','SEWING','LAUNDRY','QC','FINISHED','ON_HOLD','CANCELLED') then e:=e||jsonb_build_array('Invalid PO status'); end if;
      if upper(coalesce(r.normalized_payload->>'current_stage','')) not in('CUTTING','SEWING','LAUNDRY','QC','FINISHED','ON_HOLD') then e:=e||jsonb_build_array('Invalid PO current_stage'); end if;
    end if;
    exception when others then
      e:=e||jsonb_build_array('Invalid row value: '||sqlerrm);
    end;
    if r.validation_status='ERROR' and jsonb_array_length(r.validation_errors)>0 then e:=r.validation_errors||e; end if;
    update erp.migration_staging_rows set validation_status=case when jsonb_array_length(e)=0 then 'VALID' else 'ERROR' end,validation_errors=e,updated_at=statement_timestamp() where id=r.id;
  end loop;
  select count(*),count(*) filter(where validation_status='VALID'),count(*) filter(where validation_status='ERROR') into v_total,v_valid,v_error from erp.migration_staging_rows where batch_id=p_batch_id;
  update erp.migration_batches set status=case when v_error=0 then 'READY' else 'DRAFT' end,validated_at=statement_timestamp(),error_message=case when v_error=0 then null else v_error||' staging row(s) failed validation' end where id=p_batch_id;
  return query select v_total,v_valid,v_error;
end;$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.validate_migration_opening_stock_costs(p_batch_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r record;j jsonb;v_bt text;v_method text;v_product uuid;v_number numeric;
begin
  perform erp.require_owner_admin();
  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM' and validation_status='VALID' loop
    begin
    j:=r.normalized_payload;v_bt:=upper(coalesce(j->>'balance_type',''));v_method:=coalesce(nullif(upper(j->>'hpp_input_method'),''),'MANUAL');
    if v_bt in('MATERIAL','FINISHED_GOODS') and nullif(btrim(j->>'unit_cost'),'') is not null then
      v_number:=(j->>'unit_cost')::numeric;
      if v_number<0 or v_number::text in('NaN','Infinity','-Infinity') then
        raise exception 'unit_cost must be finite and zero or positive';
      end if;
    end if;
    if v_bt='FINISHED_GOODS' and (j->>'qty')::numeric<>trunc((j->>'qty')::numeric) then
      raise exception 'FINISHED_GOODS qty must be whole PCS';
    end if;
    if v_bt='MATERIAL' and nullif(btrim(j->>'unit_cost'),'') is null then raise exception 'Migration opening MATERIAL row % wajib punya unit_cost (0 boleh)',r.source_row_no; end if;
    if v_bt='FINISHED_GOODS' then
      if v_method not in('MANUAL','PRICE_PERCENT') then raise exception 'Migration opening FG row % hpp_input_method harus MANUAL atau PRICE_PERCENT',r.source_row_no; end if;
      if v_method='MANUAL' and nullif(btrim(j->>'unit_cost'),'') is null then raise exception 'Migration opening FG row % wajib punya unit_cost atau PRICE_PERCENT',r.source_row_no; end if;
      if v_method='PRICE_PERCENT' and (nullif(j->>'hpp_percent_of_price','') is null or (j->>'hpp_percent_of_price')::numeric<=0) then raise exception 'Migration opening FG row % wajib punya hpp_percent_of_price > 0',r.source_row_no; end if;
      begin
        v_product:=erp.resolve_opening_product_identity(
          j->>'product_sku',
          (select cutover_at from erp.migration_batches where id=p_batch_id),
          j->>'color_name',j->>'size_code',j->>'model_code',j->>'brand_code'
        );
      exception when others then
        raise exception 'Migration opening FG row %: %',r.source_row_no,sqlerrm;
      end;
    end if;
    exception when others then
      update erp.migration_staging_rows
      set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm),
          updated_at=statement_timestamp()
      where id=r.id;
    end;
  end loop;
  update erp.migration_batches b set
    status=case when exists(select 1 from erp.migration_staging_rows s
      where s.batch_id=b.id and s.validation_status<>'VALID') then 'DRAFT' else 'READY' end,
    validated_at=statement_timestamp(),
    error_message=case when exists(select 1 from erp.migration_staging_rows s
      where s.batch_id=b.id and s.validation_status='ERROR') then
      (select count(*) from erp.migration_staging_rows s where s.batch_id=b.id and s.validation_status='ERROR')||' staging row(s) failed validation'
      else null end
  where b.id=p_batch_id;
end$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.validate_migration_batch(p_batch_id uuid)
 RETURNS TABLE(total_rows bigint, valid_rows bigint, error_rows bigint)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
begin
  perform * from erp._validate_migration_batch_base(p_batch_id);
  perform erp.validate_migration_opening_stock_costs(p_batch_id);
  return query select count(*),count(*) filter(where validation_status='VALID'),
    count(*) filter(where validation_status='ERROR')
  from erp.migration_staging_rows where batch_id=p_batch_id;
end;$function$
$definition$;
end
$canonical_opening_v2620aj$;

do $installed_v2620aj$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620aj_rollback_capsule)<>6 then
    raise exception 'AJ_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620aj_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.post_rework_completion(uuid)','209338cc2b3099b163c0b344d1706a1f42dbdf804307e5fadee08e02f966f34d','63116e419dbbb6e59296416793288d785a348a30cdc46aad7eb44d097444d6c3',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.rebuild_po_hpp(uuid,text)','9bbadaead01d33c7d23cab2172b1cc0b04a9fbe210bfab8a4d2724e936e6ef9b','4e2e96017513d4990c9b2f8da2edf666b992ba016c8d688ea336daba36202d1f',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.cp6_lot_failed_wash_cost_v2620e(uuid)','cc02ece93afca767142d997fc6210c6d0d700633a998262fe95dd5435ea794bb','e8627bc0891322148819e17aca7a98b1177014b6ece6234ec7940e0876e896e1',array['postgres=X/postgres']::text[]),
    ('erp._validate_migration_batch_base(uuid)','78f165c0b42edec0cfa8e3fa295abb64b94cde0df9af9b5611b5f6e4ec3e1fb6','eb6fc2bc6cf419a72be75891d145782dbb1dec06186243834c2a444fc1fa9801',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_migration_opening_stock_costs(uuid)','3b2316af1604ff6bc355ea3b7bb6559e32d41fa4c96b35af7e5f8c3bccb905e7','8223a856b0a0cd66d29a9eba31ebb6644434f934d910f184947a35ae0ffa77a0',array['postgres=X/postgres']::text[]),
    ('erp.validate_migration_batch(uuid)','166aa25ae8bce86daedffc82f5db2cb3266a310b374518672080a08345271b26','88bd4f2283fbdbea3faf2c4694426e87c71883c770243ddb44818797b0f22482',array['authenticated=X/postgres','postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620aj_rollback_capsule
      where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'AJ_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620aj$;

do $boundary_v2620aj$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620aj_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>222 then
    raise exception 'AJ_FULL_ERP_BOUNDARY_CARDINALITY expected222 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620aj_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620aj$;

insert into erp.schema_migrations(version,description)
values('v2.6.20aj','Rework outputs retain separate identity and original cost source; import errors persist per row');
commit;
