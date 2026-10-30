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
