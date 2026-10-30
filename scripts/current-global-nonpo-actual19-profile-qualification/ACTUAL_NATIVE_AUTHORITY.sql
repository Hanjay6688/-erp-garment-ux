CREATE VIEW erp.v_current_hpp WITH (security_invoker='true') AS
 SELECT DISTINCT ON (lot_id) lot_id,
    id AS hpp_version_id,
    version_no,
    cost_state,
    qty_basis_pcs,
    total_cost,
    hpp_per_pcs,
    calculated_at
   FROM erp.hpp_versions hv
  WHERE (is_current = true)
  ORDER BY lot_id, version_no DESC;

CREATE OR REPLACE FUNCTION erp.require_internal()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_app_role text;v_jwt_role text;
begin
 if session_user in('postgres','supabase_admin') then return;end if;
 begin v_jwt_role:=coalesce(auth.jwt()->>'role','');exception when others then v_jwt_role:='';end;
 if v_jwt_role='service_role' then return;end if;
 -- R4-05 one context probe (scripts/cp7_internal_guard_bundle.py): without a private command context row of this
 -- backend and transaction no branch below admits; only the final role test decides. A transaction that has
 -- no transaction id yet has written no row (a context row carries the id of the transaction that wrote it).
 if txid_current_if_assigned() is null or not exists(select 1 from cp7_sales.command_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from erp.cutting_bridge_execution_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from erp.bs_resolution_execution_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from erp.cp6_laundry_qc_execution_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from cp7_procurement.execution_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from cp7_material.execution_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from cp7_supplier_return.execution_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from cp7_payroll.execution_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from cp7_payroll.settlement_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from cp7_attendance.command_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()
  union all select 1 from cp7_credit.consumer_execution_context x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current())then
  if coalesce(erp.current_app_role(),'') not in('OWNER','ADMIN','STAFF') then raise exception 'Internal ERP access required';end if;
  return;
 end if;
 if exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and c.action in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
   and not exists(select 1 from erp.cutting_bridge_execution_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current() union all select 1 from erp.bs_resolution_execution_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current() union all select 1 from erp.cp6_laundry_qc_execution_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current() union all select 1 from cp7_procurement.execution_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current() union all select 1 from cp7_material.execution_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current() union all select 1 from cp7_supplier_return.execution_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current() union all select 1 from cp7_payroll.execution_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current() union all select 1 from cp7_payroll.settlement_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current() union all select 1 from cp7_attendance.command_context before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current())
   then cp7_sales.command_allowed(c.action) else false end) then return;end if;

 -- Keep indexable identity filters, and evaluate live scope permissions only
 -- for that exact candidate. SQL AND does not fix predicate evaluation order.
 -- Matched scope checks and the existing legacy fallback remain unchanged.
 if exists(select 1 from erp.cutting_bridge_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor_key=erp._idempotency_actor_key() and c.action='POST_CUTTING'
   and c.permission_key='production.cutting.post' then erp.has_permission(c.permission_key) else false end) then return;end if;
 if exists(select 1 from erp.bs_resolution_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor_key=erp._idempotency_actor_key()
   and c.permission_key in('production.bs_rework.create','production.bs_rework.post','production.bs_rework.reverse')
   then erp.has_permission(c.permission_key) else false end) then return;end if;
 if exists(select 1 from erp.cp6_laundry_qc_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor_key=erp._idempotency_actor_key()
   and ((c.action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH') and c.permission_key='production.laundry.post')
    or(c.action='POST_FINAL_SKU' and c.permission_key='production.final_sku.post')
    or(c.action in('REVERSE_DELIVERY','REVERSE_RECEIPT') and c.permission_key='production.laundry.reverse')
    or(c.action='REVERSE_FINAL_SKU' and c.permission_key='production.final_sku.reverse'))
   then erp.has_permission(c.permission_key) else false end) then return;end if;
 -- Only a private, transaction/actor-bound public-command context extends the
 -- legacy internal-role guard. Caller-controlled GUCs cannot grant this path.
 if exists(select 1 from cp7_procurement.execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and ((c.action='SAVE_DRAFT' and c.permission_key='warehouse.procurement.create')
    or(c.action='POST' and c.permission_key='warehouse.procurement.post'))
   then erp.has_permission('warehouse.procurement.view') and erp.has_permission(c.permission_key) else false end) then return;end if;
 if exists(select 1 from cp7_material.execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and c.action in('SAVE_TRANSFER','POST_TRANSFER','REVERSE_TRANSFER','SAVE_COUNT','POST_COUNT','DELETE_COUNT','REVERSE_COUNT') and c.permission_key='warehouse.stock.adjust'
   then erp.has_permission('warehouse.material.view') and erp.has_permission(c.permission_key) else false end) then return;end if;
 if exists(select 1 from cp7_supplier_return.execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and ((c.action='SAVE' and c.permission_key='warehouse.procurement.create')
    or(c.action in('POST','REVERSE') and c.permission_key='warehouse.procurement.reverse'))
   then erp.has_permission('warehouse.procurement.view') and erp.has_permission(c.permission_key) else false end) then return;end if;
 if exists(select 1 from cp7_payroll.execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and c.action='POST_NOTE' and c.permission_key='production.fg_handoff.post'
   then erp.has_permission('production.fg_handoff.view') and erp.has_permission(c.permission_key) else false end) then return;end if;
  if exists(select 1 from cp7_payroll.settlement_context c where c.backend_pid=pg_backend_pid()
    and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
     and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
    then erp.has_permission('finance.payroll.view')
    and(c.action not in('PREPARE','APPROVE','CANCEL','REVERSE') or erp.has_permission('finance.payroll.approve'))
    and(c.action not in('PAY','REVERSE') or erp.has_permission('finance.payroll.pay'))
    else false end) then return;end if;
  if exists(select 1 from cp7_attendance.command_context c where c.backend_pid=pg_backend_pid()
    and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
     and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
    then erp.has_permission('finance.attendance.view') and erp.has_permission(c.permission)
    and(not c.owner_required or erp.current_app_role() in('OWNER','ADMIN'))
    else false end) then return;end if;
 if exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and c.action in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
   then cp7_sales.command_allowed(c.action) else false end) then return;end if;
 if exists(select 1 from cp7_credit.consumer_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and c.phase in('LOCKED','POSTING','MATERIALIZED','COMPLETE')
   then cp7_credit.consumer_internal_allowed_v1() else false end) then return;end if;
 v_app_role:=erp.current_app_role();
 if coalesce(v_app_role,'') not in('OWNER','ADMIN','STAFF') then raise exception 'Internal ERP access required';end if;
end $function$;

CREATE FUNCTION erp.account_id(p_mapping_key text) RETURNS uuid
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'erp', 'public'
    AS $$ DECLARE v_id uuid; BEGIN PERFORM erp.require_internal();SELECT account_id INTO v_id FROM erp.accounting_account_mappings WHERE mapping_key=p_mapping_key; IF v_id IS NULL THEN RAISE EXCEPTION 'Accounting mapping % is not configured',p_mapping_key; END IF;RETURN v_id;END; $$;

CREATE OR REPLACE FUNCTION erp.be_conversion_extra_v1(p_conversion uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum(e.target_amount-e.previous_amount),0) from erp.be_conversion_cost_sources_v1 s
 join erp.be_conversion_cost_events_v1 e on e.document_id=s.document_id where s.conversion_id=p_conversion
$function$;

CREATE OR REPLACE FUNCTION erp.be_allocation_extra_v1(p_allocation uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select a.conversion_cost_allocated+erp.be_conversion_extra_v1(a.conversion_id)
 from erp.product_conversion_allocations a where a.id=p_allocation
$function$;

CREATE OR REPLACE FUNCTION erp.be_nonpo_admitted_v1(p_conversion uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select exists(select 1 from erp.be_conversion_sources_v1 b join erp.product_conversions c on c.id=b.conversion_id
  join erp.fg_lots l on l.id=b.source_lot_id join erp.v_current_hpp h on h.lot_id=l.id
  where b.conversion_id=p_conversion and l.po_id is null and l.product_id=c.from_product_id
   and l.lot_origin<>'VOIDED_PRODUCTION' and h.hpp_per_pcs>=0)
$function$;

CREATE OR REPLACE FUNCTION erp.compute_non_po_product_hpp_targets_v2620f(p_product_id uuid)
returns table(
  hpp_total_cost numeric,fg_value numeric,cogs_value numeric,
  other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with lots as(
  select fl.id,
    (case when fl.lot_origin<>'CONVERSION' or exists(select 1 from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id
       where a.destination_lot_id=fl.id and c.status='POSTED') then coalesce(hv.total_cost,0) else 0 end
     -coalesce((select sum(a.qty_pcs*(hv.total_cost/nullif(hv.qty_basis_pcs,0))) from erp.product_conversion_allocations a
       join erp.product_conversions c on c.id=a.conversion_id where a.source_lot_id=fl.id and c.status='POSTED'),0))::numeric raw_total,
    case when coalesce(hv.qty_basis_pcs,0)>0
      then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.product_id=p_product_id and fl.po_id is null
    and fl.lot_origin<>'VOIDED_PRODUCTION'
), balances as(
  select l.id,l.raw_total,l.hpp_per_pcs,
    (coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed)) filter(
      where m.movement_type='SALE_RESERVE' and not exists(
        select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id
      )),0))::numeric owned_qty
  from lots l
  left join erp.fg_stock_movements m on m.lot_id=l.id
  group by l.id,l.raw_total,l.hpp_per_pcs
), sold as(
  select a.lot_id,coalesce(sum(a.qty_pcs),0)::numeric qty
  from erp.sale_stock_allocations a
  join erp.sales_items i on i.id=a.sale_item_id
  join erp.sales_headers h on h.id=i.sale_id
  join lots l on l.id=a.lot_id
  where h.status in('POSTED','PARTIAL_PAID','PAID')
  group by a.lot_id
), returned as(
  select i.lot_id,coalesce(sum(i.qty_pcs),0)::numeric qty
  from erp.sales_return_items i
  join erp.sales_returns h on h.id=i.return_id
  join lots l on l.id=i.lot_id
  where h.status='POSTED'
  group by i.lot_id
), per_lot as(
  select b.id,round(b.raw_total,2)::numeric hpp,
    round(b.raw_total-greatest(b.owned_qty,0)*b.hpp_per_pcs,2)::numeric total_out,
    round(greatest(coalesce(s.qty,0)-coalesce(r.qty,0),0)
      *b.hpp_per_pcs,2)::numeric cogs
  from balances b
  left join sold s on s.lot_id=b.id
  left join returned r on r.lot_id=b.id
)
select coalesce(sum(hpp),0)::numeric,
  coalesce(sum(hpp-total_out),0)::numeric,
  coalesce(sum(cogs),0)::numeric,
  coalesce(sum(total_out-cogs),0)::numeric
from per_lot
$function$;

CREATE OR REPLACE FUNCTION erp.compute_non_po_product_hpp_book_v2620f(p_product_id uuid)
 RETURNS TABLE(hpp_total_cost numeric, fg_value numeric, cogs_value numeric, other_out_value numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
with book as(
  select
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=(select erp.account_id('FG_INVENTORY'))),0)::numeric fg,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=(select erp.account_id('COGS'))),0)::numeric cogs,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id in(
        (select erp.account_id('OTHER_EXPENSE')),(select erp.account_id('OTHER_INCOME'))
      )),0)::numeric other_out
  from erp.journal_lines l
  join erp.journal_entries e on e.id=l.journal_entry_id
    and e.status in('POSTED','REVERSED')
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where l.po_id is null and l.product_id=p_product_id
    and (e.source_type<>'PRODUCT_CONVERSION' or erp.be_nonpo_admitted_v1(e.source_id))
    and (e.source_type<>'JOURNAL_REVERSAL' or o.source_type is distinct from 'PRODUCT_CONVERSION'
      or erp.be_nonpo_admitted_v1(o.source_id))
)
select (fg+cogs+other_out)::numeric,fg,cogs,other_out from book
$function$;

create or replace function erp.be_propagate_nonpo_v1()
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  r record;
  v_source_hpp numeric(18,6);
  v_desired numeric(18,6);
  v_current numeric(18,6);
  v_old_id uuid;
  v_new_id uuid;
  v_ver integer;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform 1 from erp.fg_lots
  where po_id is null and lot_origin<>'VOIDED_PRODUCTION'
  order by id for update;

  for r in
    with recursive rooted(lot_id,depth,path) as(
      select fl.id,0,array[fl.id]
      from erp.fg_lots fl
      where fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
      union all
      select a.destination_lot_id,x.depth+1,x.path||a.destination_lot_id
      from rooted x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path)
        and x.depth<128
    )
    select a.*,x.depth source_depth
    from rooted x
    join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    where a.destination_lot_id is not null
    order by x.depth,a.id
  loop
    select hpp_per_pcs into v_source_hpp
    from erp.v_current_hpp where lot_id=r.source_lot_id;
    if v_source_hpp is null or r.qty_pcs<=0 then continue; end if;
    v_desired:=v_source_hpp+(erp.be_allocation_extra_v1(r.id)/r.qty_pcs);
    if v_desired<0 then raise exception 'BE_RECOVERY_EXCEEDS_VALUE: nilai pemulihan melebihi nilai sumber dan biaya sah';end if;
    select hpp_version_id,hpp_per_pcs into v_old_id,v_current
    from erp.v_current_hpp where lot_id=r.destination_lot_id;
    if v_old_id is null or abs(coalesce(v_current,0)-v_desired)>0.000001 then
      select coalesce(max(version_no),0)+1 into v_ver
      from erp.hpp_versions where lot_id=r.destination_lot_id;
      update erp.hpp_versions set is_current=false
      where lot_id=r.destination_lot_id and is_current;
      insert into erp.hpp_versions(
        lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,
        supersedes_id,calculation_reason,created_by
      ) values(
        r.destination_lot_id,v_ver,'ADJUSTED',r.qty_pcs,r.qty_pcs*v_desired,
        true,v_old_id,'Root-to-leaf propagated source HPP through SKU conversion',
        erp.current_app_user_id()
      ) returning id into v_new_id;
      insert into erp.hpp_version_components(
        hpp_version_id,component_type,description,qty_basis,unit_cost,total_cost,
        source_type,source_id
      ) values
        (v_new_id,'OTHER','Latest source lot HPP carry-forward',r.qty_pcs,
          v_source_hpp,r.qty_pcs*v_source_hpp,'FG_LOT',r.source_lot_id),
        (v_new_id,'CONVERSION','Conversion/relabel cost',r.qty_pcs,
          erp.be_allocation_extra_v1(r.id)/r.qty_pcs,erp.be_allocation_extra_v1(r.id),
          'PRODUCT_CONVERSION_ALLOCATION',r.id);
    end if;
  end loop;

  if exists(
    with recursive reachable(lot_id,path,depth) as(
      select fl.id,array[fl.id],0
      from erp.fg_lots fl
      where fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
      union all
      select a.destination_lot_id,x.path||a.destination_lot_id,x.depth+1
      from reachable x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path) and x.depth<128
    )
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id and s.po_id is null
    join erp.fg_lots d on d.id=a.destination_lot_id
    where not exists(select 1 from reachable x where x.lot_id=a.destination_lot_id)
       or not erp.be_nonpo_admitted_v1(c.id) or d.po_id is distinct from s.po_id
       or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
       or a.qty_pcs<=0
  ) then
    raise exception 'BE_NON_PO_LINEAGE_ORPHAN_OR_CYCLE';
  end if;
end
$function$;

CREATE OR REPLACE FUNCTION erp.be_nonpo_prepare_transfers_v1(p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;v_own boolean;v_old numeric;v_new numeric;v_delta numeric;v_journal uuid;v_event uuid;
begin
 perform erp.require_internal();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 v_own:=not erp.be_in_context_v1();
 if v_own then
   insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id,syncing_nonpo)
   values(pg_backend_pid(),txid_current(),gen_random_uuid(),true);
 end if;
 perform erp.be_propagate_nonpo_v1();
 for r in select c.id,c.from_product_id,c.to_product_id,a.id allocation_id,a.qty_pcs,a.original_hpp_per_pcs,
    h.hpp_per_pcs from erp.product_conversions c join erp.product_conversion_allocations a on a.conversion_id=c.id
    join erp.fg_lots l on l.id=a.source_lot_id join erp.v_current_hpp h on h.lot_id=l.id
    where l.po_id is null and c.status='POSTED' order by c.physical_at,c.id loop
   if not erp.be_nonpo_admitted_v1(r.id) then raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';end if;
   select round(r.qty_pcs*r.original_hpp_per_pcs,2)+coalesce(sum(target_value-previous_value),0) into v_old
     from erp.be_nonpo_transfer_events_v1 where conversion_id=r.id;
   v_new:=round(r.qty_pcs*r.hpp_per_pcs,2);v_delta:=v_new-v_old;
   if v_delta<>0 then
     v_event:=gen_random_uuid();
     v_journal:=erp.post_journal('BE_NONPO_CONVERSION_RECOST',v_event,p_date,'Nilai sumber terkini konversi '||r.id::text,
       jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','product_id',r.to_product_id,'debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
         jsonb_build_object('mapping_key','FG_INVENTORY','product_id',r.from_product_id,'debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
     insert into erp.be_nonpo_transfer_events_v1(id,conversion_id,previous_value,target_value,journal_id,economic_date)
       values(v_event,r.id,v_old,v_new,v_journal,p_date);
   end if;
 end loop;
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_nonpo_sync_all_v1(p_date date,p_source_type text,p_source_id uuid,p_reason text)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_own boolean;v_product uuid;
begin
 perform erp.require_internal();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if erp.be_nonpo_in_sync_v1() then raise exception 'BE_NON_PO_RECURSION';end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id) values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 update erp.be_execution_context_v1 set syncing_nonpo=true where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 perform erp.be_nonpo_prepare_transfers_v1(p_date);
 for v_product in select distinct product_id from erp.fg_lots where po_id is null order by product_id loop
   perform erp.sync_non_po_product_hpp_to_gl_v2620f(v_product,p_date,p_source_type,p_source_id,p_reason);
 end loop;
 update erp.be_execution_context_v1 set syncing_nonpo=false where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.sync_non_po_product_hpp_to_gl_v2620f(
  p_product_id uuid,
  p_effective_date date,
  p_trigger_source_type text,
  p_trigger_source_id uuid,
  p_reason text
)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  t record;
  b record;
  v_df numeric(20,2);
  v_dc numeric(20,2);
  v_do numeric(20,2);
  v_event uuid:=gen_random_uuid();
  v_journal uuid;
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(btrim(p_trigger_source_type),'') is null
     or nullif(btrim(p_reason),'') is null then
    raise exception 'Non-PO HPP synchronization requires source and reason';
  end if;
  if not erp.be_nonpo_in_sync_v1() and exists(select 1 from erp.be_conversion_sources_v1 be_source
      join erp.fg_lots be_lot on be_lot.id=be_source.source_lot_id where be_lot.po_id is null) then
    perform erp.be_nonpo_sync_all_v1(p_effective_date,p_trigger_source_type,p_trigger_source_id,p_reason);return;
  end if;
  if exists(
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where(s.po_id is null or d.po_id is null) and not erp.be_nonpo_admitted_v1(c.id)
      and(s.product_id=p_product_id or d.product_id=p_product_id)
  ) then
    raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';
  end if;

  select * into t
  from erp.compute_non_po_product_hpp_targets_v2620f(p_product_id);
  select * into b
  from erp.compute_non_po_product_hpp_book_v2620f(p_product_id);
  if abs(t.hpp_total_cost-b.hpp_total_cost)>0.005 then
    raise exception 'NON_PO_HPP_SOURCE_VALUE_MISMATCH: product %, target total %, book total %',
      p_product_id,t.hpp_total_cost,b.hpp_total_cost;
  end if;

  v_df:=round(t.fg_value-b.fg_value,2);
  v_dc:=round(t.cogs_value-b.cogs_value,2);
  v_do:=round(t.other_out_value-b.other_out_value,2);
  if abs(v_df+v_dc+v_do)>0.005 then
    raise exception 'NON_PO_HPP_DELTA_NOT_CONSERVED: product %, fg %, cogs %, other %',
      p_product_id,v_df,v_dc,v_do;
  end if;
  if abs(v_df)<=0.005 and abs(v_dc)<=0.005 and abs(v_do)<=0.005 then
    return;
  end if;

  if abs(v_df)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_df>0
      then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_df,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
        'credit',abs(v_df),'product_id',p_product_id) end);
  end if;
  if abs(v_dc)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_dc>0
      then jsonb_build_object('mapping_key','COGS','debit',v_dc,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','COGS','debit',0,
        'credit',abs(v_dc),'product_id',p_product_id) end);
  end if;
  if abs(v_do)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_do>0
      then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_do,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
        'credit',abs(v_do),'product_id',p_product_id) end);
  end if;

  v_journal:=erp.post_journal(
    'NON_PO_HPP_GL_SYNC_V2620F',v_event,p_effective_date,
    'Cumulative non-PO HPP redistribution · '||p_reason,v_lines
  );
  insert into erp.non_po_hpp_gl_sync_events_v2620f(
    id,product_id,trigger_source_type,trigger_source_id,effective_date,
    old_fg_value,new_fg_value,fg_delta,
    old_cogs_value,new_cogs_value,cogs_delta,
    old_other_out_value,new_other_out_value,other_delta,
    journal_entry_id,reason,created_by
  ) values(
    v_event,p_product_id,p_trigger_source_type,p_trigger_source_id,
    p_effective_date,b.fg_value,t.fg_value,v_df,
    b.cogs_value,t.cogs_value,v_dc,
    b.other_out_value,t.other_out_value,v_do,
    v_journal,p_reason,erp.current_app_user_id()
  );
  perform erp.assert_non_po_product_hpp_target_book_v2620f(p_product_id);
end
$function$;

CREATE OR REPLACE FUNCTION erp.be_in_context_v1()
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select exists(select 1 from erp.be_execution_context_v1
   where backend_pid=pg_backend_pid() and transaction_id=txid_current())
$function$;

CREATE OR REPLACE FUNCTION erp.be_nonpo_in_sync_v1()
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce((select syncing_nonpo from erp.be_execution_context_v1
   where backend_pid=pg_backend_pid() and transaction_id=txid_current()),false)
$function$;

