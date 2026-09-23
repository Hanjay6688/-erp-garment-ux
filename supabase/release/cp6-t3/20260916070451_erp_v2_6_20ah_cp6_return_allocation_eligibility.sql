-- CP6 AH: original allocation eligibility and independent return destination.
-- Posted history is unchanged; ordinary draft validation uses a confined private trigger.
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

do $lock_all_erp_v2620ah$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ah_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ah$;


do $predecessor_v2620ah$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ag')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20ah')
     or to_regclass('erp.cp6_v2620ah_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ag_rollback_capsule') is null then raise exception 'AH_REQUIRES_EXACT_AG_WITHOUT_AH_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ag_cp6_sale_reservation_lineage')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='20260916050822' and name='erp_v2_6_20ag_cp6_sale_reservation_lineage'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='085b84cb6917617c5e6a2d375fd5177542ebe3f021a20de48e239159e34d66c0')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260916050822')
     or (select count(*) from erp.cp6_v2620ag_rollback_capsule)<>4 then raise exception 'AH_REQUIRES_EXACT_AG_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    ('erp.normalize_sales_return_item_from_allocation()','ea7781898a894cd7694e912f47231fdbcde8745a06a04e8e635210f84bba99ce',array['postgres=X/postgres']::text[]),
    ('erp.post_sales_return(uuid)','7640b5781a8838f550595d47bbc3f452a50a846f58018e714a0a209b8f32ff02',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','e62f7fa0d2892708128c372d6e99d39d7833a3fa2eedfe25f17695c7ca94e3ef',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_work_completion()','8706d6353ef4f5621a02e0db943f66599a446db0bf2ae2c375d04ead742e8be0',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_vendor_invoice_item_lineage()','0f9e0ae58e8482c449a9c76994055e03c2e077b2868e3febc3b1699b0c73158e',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AH_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
  if (with active_return as (
  select ah_line.*,ah_return.sale_id,ah_return.customer_id,ah_return.physical_at
  from erp.sales_return_items ah_line join erp.sales_returns ah_return on ah_return.id=ah_line.return_id
  where ah_return.status='POSTED'
), live_movement as (
  select ah_movement.* from erp.fg_stock_movements ah_movement
  where ah_movement.source_type='SALES_RETURN_ITEM' and ah_movement.movement_type='SALE_RETURN'
    and not exists(select 1 from erp.fg_stock_movements ah_reversal where ah_reversal.reversal_of_id=ah_movement.id)
)
select count(*)::bigint from (
  select ah_line.id from active_return ah_line
  left join erp.sale_stock_allocations ah_allocation on ah_allocation.id=ah_line.sale_stock_allocation_id
  left join erp.sales_items ah_sale_line on ah_sale_line.id=ah_allocation.sale_item_id
  left join erp.sales_headers ah_sale on ah_sale.id=ah_sale_line.sale_id
  where ah_allocation.id is null or ah_sale.status is null or ah_sale.status not in('POSTED','PARTIAL_PAID','PAID')
    or ah_line.sale_id is distinct from ah_sale.id or ah_line.customer_id is distinct from ah_sale.customer_id
    or ah_line.product_id is distinct from ah_sale_line.product_id or ah_line.lot_id is distinct from ah_allocation.lot_id
    or ah_line.physical_at<ah_sale.sale_date
  union all
  select ah_allocation.id from erp.sale_stock_allocations ah_allocation join active_return ah_line on ah_line.sale_stock_allocation_id=ah_allocation.id
  group by ah_allocation.id,ah_allocation.qty_pcs having sum(ah_line.qty_pcs)>ah_allocation.qty_pcs
  union all
  select ah_movement.id from live_movement ah_movement left join active_return ah_line on ah_line.id=ah_movement.source_id
  where ah_line.id is null or ah_movement.product_id is distinct from ah_line.product_id or ah_movement.lot_id is distinct from ah_line.lot_id
    or ah_movement.location_id is distinct from ah_line.location_id or ah_movement.quality_grade is distinct from ah_line.quality_grade
    or ah_movement.customer_id is distinct from ah_line.customer_id or ah_movement.physical_at is distinct from ah_line.physical_at
    or ah_movement.qty_signed is distinct from ah_line.qty_pcs
  union all
  select ah_line.id from active_return ah_line left join live_movement ah_movement on ah_movement.source_id=ah_line.id
  group by ah_line.id,ah_line.qty_pcs having count(ah_movement.id)<>1 or sum(ah_movement.qty_signed) is distinct from ah_line.qty_pcs::bigint
  union all
  select ah_return.id from erp.sales_returns ah_return where ah_return.status='POSTED'
    and not exists(select 1 from erp.sales_return_items ah_line where ah_line.return_id=ah_return.id)
) broken)<>0 then raise exception 'AH_PREEXISTING_RETURN_ALLOCATION_REVIEW_REQUIRED'; end if;
  if (select exists(
  select 1 from erp.sales_return_items ah_draft_line
  join erp.sales_returns ah_return on ah_return.id=ah_draft_line.return_id and ah_return.status='DRAFT'
  join erp.sale_stock_allocations ah_allocation on ah_allocation.id=ah_draft_line.sale_stock_allocation_id
  join erp.sales_items ah_sale_line on ah_sale_line.id=ah_allocation.sale_item_id
  join erp.sales_headers ah_sale on ah_sale.id=ah_sale_line.sale_id
  where ah_sale.status='DRAFT'
)) then raise exception 'AH_PREEXISTING_DRAFT_RETURN_SOURCE_REVIEW_REQUIRED'; end if;
end
$predecessor_v2620ah$;

create table erp.cp6_v2620ah_rollback_capsule(
  like erp.cp6_v2620ag_rollback_capsule including all
);
alter table erp.cp6_v2620ah_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ah_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ah_rollback_capsule(
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
where p.oid in('erp.normalize_sales_return_item_from_allocation()'::regprocedure,'erp.post_sales_return(uuid)'::regprocedure,'erp.run_v268_financial_report_checks()'::regprocedure,'erp.validate_work_completion()'::regprocedure,'erp.validate_vendor_invoice_item_lineage()'::regprocedure);


do $canonical_opening_v2620ah$
begin
  execute $definition$CREATE OR REPLACE FUNCTION erp.normalize_sales_return_item_from_allocation()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_return_sale uuid;
  v_return_customer uuid;
  v_alloc_sale uuid;
  v_alloc_customer uuid;
  v_alloc_status text;
  v_product uuid;
  v_lot uuid;
  v_hpp numeric(18,6);
  v_alloc_qty integer;
  v_sale_item_qty integer;
  v_sale_line_total numeric(24,6);
  v_max_refund numeric(24,6);
begin
  perform erp.require_internal();
  select sr.sale_id,sr.customer_id into v_return_sale,v_return_customer
  from erp.sales_returns sr where sr.id=new.return_id;
  if v_return_sale is null then raise exception 'Sales return must reference an original sale'; end if;

  select si.sale_id,sh.customer_id,sh.status,si.product_id,ssa.lot_id,ssa.unit_hpp_snapshot,ssa.qty_pcs,si.qty_pcs,si.line_total
  into v_alloc_sale,v_alloc_customer,v_alloc_status,v_product,v_lot,v_hpp,v_alloc_qty,v_sale_item_qty,v_sale_line_total
  from erp.sale_stock_allocations ssa
  join erp.sales_items si on si.id=ssa.sale_item_id
  join erp.sales_headers sh on sh.id=si.sale_id
  where ssa.id=new.sale_stock_allocation_id;

  if v_alloc_sale is null then raise exception 'Original sale stock allocation not found'; end if;
  if v_alloc_status not in('POSTED','PARTIAL_PAID','PAID') then
    raise exception 'AH_RETURN_SOURCE_MUST_BE_ACTIVE_POSTED_SALE';
  end if;
  if v_alloc_sale<>v_return_sale then raise exception 'Return allocation does not belong to the selected original sale'; end if;
  if v_alloc_customer is distinct from v_return_customer then raise exception 'Return customer does not match original sale customer'; end if;
  if new.qty_pcs>v_alloc_qty then raise exception 'Return qty % exceeds qty % sold from this lot allocation',new.qty_pcs,v_alloc_qty; end if;
  if not exists (select 1 from erp.locations l where l.id=new.location_id and l.is_active=true and l.location_type='FG_WAREHOUSE') then
    raise exception 'Sales return destination must be an active FG warehouse';
  end if;

  v_max_refund:=case when v_sale_item_qty>0 then (v_sale_line_total/v_sale_item_qty)*new.qty_pcs else 0 end;
  if new.refund_amount>v_max_refund+0.01 then
    raise exception 'Refund amount % exceeds original net sales value % for returned qty',new.refund_amount,round(v_max_refund,2);
  end if;

  select coalesce(ch.hpp_per_pcs,v_hpp) into v_hpp
  from (select 1) x
  left join erp.v_current_hpp ch on ch.lot_id=v_lot;

  new.product_id:=v_product;
  new.lot_id:=v_lot;
  new.unit_hpp_snapshot:=v_hpp;
  return new;
end;
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.post_sales_return(p_return_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.sales_returns%rowtype;
  s erp.sales_headers%rowtype;
  r record;
  v_refund numeric(24,6):=0;
  v_sold_qty integer;
  v_prior_returned integer;
  v_current_return integer;
  v_product_sale_value numeric(24,6);
  v_prior_product_refund numeric(24,6);
  v_current_product_refund numeric(24,6);
  v_original_hpp numeric(18,6);
  v_unit_hpp numeric(18,6);
  v_net_total numeric(20,2);
  v_paid numeric(20,2);
  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_delta_other numeric(24,6);
  v_target_hpp numeric(24,6);
  v_target_other numeric(24,6);
  v_book_hpp numeric(24,6);
  v_book_other numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.sales_returns where id=p_return_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sales return must be DRAFT'; end if;
  if h.sale_id is null then raise exception 'Native sales return must reference the original sale'; end if;
  select * into s from erp.sales_headers where id=h.sale_id for update;
  if s.id is null or s.status not in('POSTED','PARTIAL_PAID','PAID') then raise exception 'Original sale must be active/posted'; end if;
  if s.customer_id is distinct from h.customer_id then raise exception 'Sales return customer does not match original sale customer'; end if;
  if not exists(select 1 from erp.sales_return_items where return_id=h.id) then raise exception 'Sales return has no lines'; end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  for r in
    select * from erp.sales_return_items where return_id=h.id
    order by product_id,location_id,quality_grade,lot_id,id
  loop
    if r.lot_id is null then raise exception 'Sales return line requires original FG lot'; end if;
    if not exists(select 1 from erp.fg_lots fl where fl.id=r.lot_id and fl.product_id=r.product_id) then raise exception 'Sales return lot does not belong to selected product'; end if;

    insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
    values(r.product_id,r.location_id,r.quality_grade,0)
    on conflict(product_id,location_id,quality_grade) do nothing;
    perform 1 from erp.fg_inventory_balances
    where product_id=r.product_id and location_id=r.location_id and quality_grade=r.quality_grade
    for update;
    perform 1 from erp.fg_lots where id=r.lot_id for update;

    -- Eligibility belongs to the selected allocation. Receipt destination is
    -- independently validated and may be another active FG warehouse.
    select a.qty_pcs,a.unit_hpp_snapshot into v_sold_qty,v_original_hpp
    from erp.sale_stock_allocations a join erp.sales_items si on si.id=a.sale_item_id
    where a.id=r.sale_stock_allocation_id and si.sale_id=h.sale_id
      and si.product_id=r.product_id and a.lot_id=r.lot_id;
    if v_sold_qty is null or v_sold_qty<=0 or v_original_hpp is null then
      raise exception 'AH_RETURN_ALLOCATION_SOURCE_MISMATCH';
    end if;

    v_unit_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.lot_id),v_original_hpp);
    select coalesce(sum(sri.qty_pcs),0)::integer into v_prior_returned
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED'
      and sri.sale_stock_allocation_id=r.sale_stock_allocation_id;
    select coalesce(sum(sri.qty_pcs),0)::integer into v_current_return
    from erp.sales_return_items sri
    where sri.return_id=h.id and sri.sale_stock_allocation_id=r.sale_stock_allocation_id;
    if v_prior_returned+v_current_return>v_sold_qty then
      raise exception 'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION: Sales return exceeds quantity originally sold for this allocation. Sold %, prior returned %, current return %',v_sold_qty,v_prior_returned,v_current_return;
    end if;

    select coalesce(sum(si.line_total),0) into v_product_sale_value
    from erp.sales_items si where si.sale_id=h.sale_id and si.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_prior_product_refund
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED' and sri.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_current_product_refund
    from erp.sales_return_items sri where sri.return_id=h.id and sri.product_id=r.product_id;
    if v_prior_product_refund+v_current_product_refund>v_product_sale_value then
      raise exception 'Refund exceeds original net sale value for product. Sold value %, prior refund %, current refund %',v_product_sale_value,v_prior_product_refund,v_current_product_refund;
    end if;

    update erp.sales_return_items set unit_hpp_snapshot=v_unit_hpp where id=r.id;
    perform erp.post_fg_movement(r.product_id,r.lot_id,r.location_id,r.quality_grade,
      'SALE_RETURN',r.qty_pcs,v_unit_hpp,h.customer_id,'SALES_RETURN_ITEM',r.id,
      h.physical_at,'Customer sales return',false);
    v_refund:=v_refund+r.refund_amount;
  end loop;

  select greatest(erp.sale_net_total(h.sale_id)-v_refund,0)::numeric(20,2) into v_net_total;
  select coalesce(sum(sp.amount),0)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.sale_id and sp.status='POSTED';
  if v_paid>v_net_total then
    raise exception 'Retur ini membuat pembayaran customer melebihi nilai penjualan tersisa. Nilai setelah retur %, sudah dibayar %. Reverse/koreksi pembayaran customer dulu agar kelebihan bayar tidak hilang dari pembukuan.',v_net_total,v_paid;
  end if;

  update erp.sales_returns set status='POSTED' where id=h.id;
  if abs(v_refund)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',round(v_refund,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',round(v_refund,2),'customer_id',h.customer_id));
  end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    select round(t.fg_value-b.fg_value,2),
      round(t.cogs_value-b.cogs_value,2),
      round(t.other_out_value-b.other_out_value,2)
    into v_delta_fg,v_delta_cogs,v_delta_other
    from erp.compute_non_po_product_hpp_targets_v2620f(r.product_id) t
    cross join lateral erp.compute_non_po_product_hpp_book_v2620f(r.product_id) b;
    if abs(v_delta_fg+v_delta_cogs+v_delta_other)>0.005 then
      raise exception 'Return non-PO HPP delta does not conserve source value for product %: fg %, cogs %, other %',
        r.product_id,v_delta_fg,v_delta_cogs,v_delta_other;
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0
        then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
          'credit',abs(v_delta_fg),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0
        then jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,
          'credit',abs(v_delta_cogs),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0
        then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
          'credit',abs(v_delta_other),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
  end loop;

  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select
      round(coalesce(t.cogs_value,0),2)-st.cogs_value,
      round(coalesce(t.fg_value,0),2)-st.fg_value,
      (round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)
        -round(coalesce(t.cogs_value,0),2))-st.other_out_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      st.hpp_total_cost,st.other_out_value
    into v_delta_cogs,v_delta_fg,v_delta_other,
      v_target_hpp,v_target_other,v_book_hpp,v_book_other
    from erp.po_hpp_gl_state st
    cross join lateral erp.compute_po_hpp_gl_targets_v2620d(r.po_id) t
    where st.po_id=r.po_id for update of st;
    if v_delta_cogs>0.005 or v_delta_fg<-0.005
       or abs(v_delta_cogs+v_delta_fg+v_delta_other)>0.005
       or v_target_hpp is distinct from v_book_hpp then
      raise exception 'Sales-return cumulative HPP target does not conserve PO value %. dc %, df %, do %, target/book hpp %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_delta_other,v_target_hpp,v_book_hpp;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0 then
        jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_delta_cogs),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0 then
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_delta_fg),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0 then
        jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_delta_other),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
  end loop;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALES_RETURN',h.id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,
      'Sales return from customer · cumulative exact HPP target',v_lines);
  end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  update erp.sales_headers
  set status=case when v_paid=v_net_total then 'PAID' when v_paid>0 and v_paid<v_net_total then 'PARTIAL_PAID' else 'POSTED' end
  where id=h.sale_id;
  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620e(r.po_id);
  end loop;
end
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.run_v268_financial_report_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
 SET "TimeZone" TO 'UTC'
AS $function$
begin
  perform erp.require_owner_admin();
  return query
  select r.check_name,r.severity,r.issue_count,r.details
  from erp._v268_financial_report_checks_pre_scope() r
  where r.check_name not in(
    'V268_BROWSER_DIRECT_FINANCIAL_WRITE',
    'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE',
    'V268_ACTIVE_SALE_MISSING_JOURNAL',
    'V268_POSTED_SALES_RETURN_MISSING_JOURNAL'
  )

  union all
  select 'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE','CRITICAL',count(*)::bigint,
    'Browser roles must not directly mutate ledger or supplier-invoice aggregates'
  from information_schema.role_table_grants g
  where g.table_schema='erp'
    and g.table_name in('journal_entries','journal_lines','account_daily_balances',
      'material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')

  union all
  select 'V2620C_PO_HPP_TARGET_STATE_MISMATCH','CRITICAL',count(*)::bigint,
    'Saved PO HPP/FG/COGS/other state must equal independently recomputed current minor-unit targets'
  from erp.po_hpp_gl_state s
  cross join lateral erp.compute_po_hpp_gl_targets_v2620d(s.po_id) t
  where s.base_output_qty is distinct from coalesce(t.base_output_qty,0)
     or s.hpp_total_cost is distinct from round(coalesce(t.hpp_total_cost,0),2)
     or s.fg_value is distinct from round(coalesce(t.fg_value,0),2)
     or s.cogs_value is distinct from round(coalesce(t.cogs_value,0),2)
     or s.other_out_value is distinct from(
       round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2))

  union all
  select 'V2620C_HPP_COMPONENT_SUM_MISMATCH','CRITICAL',count(*)::bigint,
    'Every current production HPP version must equal the exact sum of its traceable production components'
  from erp.hpp_versions h
  join erp.fg_lots fl on fl.id=h.lot_id and fl.lot_origin='PRODUCTION'
  where h.is_current and abs(h.total_cost-coalesce((
    select sum(c.total_cost) from erp.hpp_version_components c where c.hpp_version_id=h.id
  ),0))>0.000001

  union all
  select 'V2620C_PO_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Per-PO FG, COGS, and HPP-disposition books must equal the saved minor-unit state after every post, recost, cancellation, return, and reversal'
  from erp.po_hpp_gl_state s
  cross join lateral erp.compute_po_hpp_gl_book_v2620e(s.po_id) b
  where abs(b.fg_value-s.fg_value)>0.005
     or abs(b.cogs_value-s.cogs_value)>0.005
     or abs(b.other_out_value-s.other_out_value)>0.005

  union all
  select 'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH','CRITICAL',count(*)::bigint,
    'Per-PO WIP book must equal independently sourced manufacturing cost not yet transferred into current HPP, net of an active final residual close'
  from erp.po_hpp_gl_state s
  cross join lateral(
    select (
      coalesce((
        select sum(-m.qty_signed*m.unit_cost_snapshot)
        from erp.material_stock_movements m
        where (m.source_type='CUTTING_GROUP' and m.source_id in(
          select g.id from erp.cutting_groups g where g.po_id=s.po_id
        )) or (m.source_type='CUTTING_GROUP_RETURN' and m.source_id in(
          select g.id from erp.cutting_groups g where g.po_id=s.po_id
        ))
      ),0)
      +coalesce((
        select sum(i.qty*i.unit_cost_snapshot)
        from erp.contractor_material_issue_items i
        join erp.contractor_material_issues h on h.id=i.issue_id and h.status='POSTED'
        join erp.materials m on m.id=i.material_id and m.material_type<>'ACCESSORY'
        where h.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(l.amount_payable)
        from erp.work_completion_lines l
        join erp.work_completion_events h on h.id=l.completion_id and h.status='POSTED'
        where h.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(a.allocated_amount)
        from erp.attendance_hpp_pool_allocations a
        join erp.attendance_hpp_pools h on h.id=a.pool_id and h.status='ACTIVE'
        where a.po_id=s.po_id
      ),0)
      +coalesce((
        with delivery_cost as(
          select dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot,
            coalesce(sum(case when rh.status='POSTED'
              and rl.actual_cost_status in('ESTIMATED','FINAL')
              then rl.qty_good_received+rl.qty_bs_laundry else 0 end),0) qty_costed,
            coalesce(sum(case when rh.status='POSTED'
              and rl.actual_cost_status in('ESTIMATED','FINAL')
              then coalesce(rl.actual_cost,0) else 0 end),0) actual_cost
          from erp.laundry_delivery_lines dl
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
          left join erp.laundry_receipt_lines rl on rl.delivery_line_id=dl.id
          left join erp.laundry_receipts rh on rh.id=rl.receipt_id
          where d.po_id=s.po_id
          group by dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot
        )
        select sum(actual_cost+greatest(qty_sent_pcs-qty_costed,0)
          *coalesce(estimated_rate_snapshot,0)) from delivery_cost
      ),0)
      +coalesce((
        select sum(rl.actual_cost)
        from erp.laundry_failed_wash_attempts a
        join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
          and rl.actual_cost_status in('ESTIMATED','FINAL')
        join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
        join erp.laundry_deliveries d on d.id=a.delivery_id and d.status='REVERSED'
        where d.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(l.amount_payable)
        from erp.rework_component_lines l
        join erp.rework_orders r on r.id=l.rework_order_id
          and r.status<>'CANCELLED' and r.cost_posted=true
        join erp.bs_cases b on b.id=r.bs_case_id
        where b.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(a.adjustment_amount) from erp.cost_adjustments a
        where a.po_id=s.po_id and a.component_type='OTHER'
      ),0)
      +coalesce((
        select sum(a.total_hpp_cost)
        from erp.fg_accessory_cost_snapshots a
        join erp.fg_lots fl on fl.id=a.lot_id
          and fl.lot_origin='PRODUCTION'
        where fl.po_id=s.po_id
      ),0)
    )::numeric source_cost
  ) truth
  cross join lateral(
    select coalesce(sum(jl.debit-jl.credit),0)::numeric wip_book
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
      and je.status in('POSTED','REVERSED')
    where jl.po_id=s.po_id and jl.account_id=erp.account_id('WIP')
  ) w
  cross join lateral(
    select coalesce(sum(e.residual_amount),0)::numeric active_wip_close
    from erp.po_wip_close_events e
    join erp.journal_entries je on je.id=e.journal_entry_id
      and je.source_type='PO_WIP_RESIDUAL_CLOSE' and je.status='POSTED'
    where e.po_id=s.po_id
  ) c
  where abs(w.wip_book-(round(truth.source_cost,2)-s.hpp_total_cost-c.active_wip_close))>0.005

  union all
  select 'V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH','CRITICAL',count(*)::bigint,
    'Each sale lifecycle must contribute its exact line total to SALES_REVENUE while active and zero after cancellation/reversal'
  from(
    select h.id,h.status,
      case when h.status in('POSTED','PARTIAL_PAID','PAID')
        then coalesce((select sum(i.line_total) from erp.sales_items i where i.sale_id=h.id),0)
        else 0 end::numeric expected_revenue,
      coalesce(sum(jl.credit-jl.debit),0)::numeric booked_revenue
    from erp.sales_headers h
    left join erp.journal_entries origin on origin.source_type='SALE' and origin.source_id=h.id
      and origin.status in('POSTED','REVERSED')
    left join erp.journal_entries je on je.id=origin.id
      or (je.source_type='JOURNAL_REVERSAL' and je.reversal_of_id=origin.id
          and je.status in('POSTED','REVERSED'))
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
      and jl.account_id=erp.account_id('SALES_REVENUE')
    group by h.id,h.status
  ) x
  where abs(x.booked_revenue-x.expected_revenue)>0.005

  union all
  select 'V2620C_SALES_RETURN_REPORT_INPUT_MISMATCH','CRITICAL',count(*)::bigint,
    'Each sales-return lifecycle must reduce SALES_REVENUE by its exact refund while active and contribute zero after reversal'
  from(
    select h.id,h.status,
      case when h.status='POSTED'
        then -coalesce((select sum(i.refund_amount) from erp.sales_return_items i where i.return_id=h.id),0)
        else 0 end::numeric expected_revenue,
      coalesce(sum(jl.credit-jl.debit),0)::numeric booked_revenue
    from erp.sales_returns h
    left join erp.journal_entries origin on origin.source_type='SALES_RETURN' and origin.source_id=h.id
      and origin.status in('POSTED','REVERSED')
    left join erp.journal_entries je on je.id=origin.id
      or (je.source_type='JOURNAL_REVERSAL' and je.reversal_of_id=origin.id
          and je.status in('POSTED','REVERSED'))
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
      and jl.account_id=erp.account_id('SALES_REVENUE')
    group by h.id,h.status
  ) x
  where abs(x.booked_revenue-x.expected_revenue)>0.005

  union all
  select 'V2620C_DRAFT_SALE_VALUE_LEAK','CRITICAL',count(*)::bigint,
    'An active Draft reservation may reduce sellable quantity but may not classify current HPP as COGS/other expense'
  from(
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.sales_headers h on h.id=i.sale_id and h.status='DRAFT'
    join erp.fg_lots fl on fl.id=a.lot_id and fl.po_id is not null
  ) d
  cross join lateral erp.compute_po_hpp_gl_targets_v2620d(d.po_id) t
  where abs(coalesce(t.other_out_value,0))>0.005

  union all
  select 'V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH','CRITICAL',count(*)::bigint,
    'Vendor invoice PAID/PARTIAL status must match the exact two-decimal payment subledger'
  from erp.vendor_invoices h
  cross join lateral(
    select coalesce(sum(p.amount),0)::numeric(20,2) paid
    from erp.vendor_payments p where p.vendor_invoice_id=h.id and p.status='POSTED'
  ) x
  where (h.status='PAID' and x.paid<>h.total_amount)
     or (h.status='PARTIAL_PAID' and not(x.paid>0 and x.paid<h.total_amount))
     or (h.status='POSTED' and x.paid<>0)

  union all
  select 'V2620C_HPP_STATE_HAS_SUBCENT','CRITICAL',count(*)::bigint,
    'Cumulative PO HPP GL state must contain exactly the minor-unit amounts that were journaled'
  from erp.po_hpp_gl_state s
  where s.hpp_total_cost<>round(s.hpp_total_cost,2)
     or s.fg_value<>round(s.fg_value,2)
     or s.cogs_value<>round(s.cogs_value,2)
     or s.other_out_value<>round(s.other_out_value,2)

  union all
  select 'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Every carried participant interval must be contiguous, bounded, acyclic, same-source, and descend from a prior immutable full return'
  from(
    select a.id issue_id
    from erp.laundry_redispatch_participant_allocations a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sdl on sdl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sdl.delivery_id
    join erp.laundry_delivery_batch_size_lines dx
      on dx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines ddl on ddl.id=dx.delivery_line_id
    join erp.laundry_deliveries dd on dd.id=ddl.delivery_id
    where sx.distribution_batch_id<>dx.distribution_batch_id
       or sx.size_id<>dx.size_id or sdl.cutting_group_id<>ddl.cutting_group_id
       or sd.status<>'REVERSED'
       or (sd.physical_at,sd.created_at,sd.id)>=(dd.physical_at,dd.created_at,dd.id)
       or a.source_offset_pcs+a.qty_pcs>sx.qty_sent_pcs
       or a.successor_offset_pcs+a.qty_pcs>dx.qty_sent_pcs
       or not exists(
         select 1 from erp.laundry_failed_wash_attempts f
         join erp.laundry_failed_wash_batch_size_lines fx
           on fx.attempt_id=f.id and fx.delivery_batch_size_line_id=sx.id
          and fx.qty_attempted_pcs=sx.qty_sent_pcs
         join erp.laundry_receipts fr on fr.id=f.receipt_id
           and fr.status in('POSTED','REVERSED')
         join erp.wip_stage_events rv on rv.id=f.return_wip_event_id
           and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
           and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
           and rv.qty_pcs=f.qty_attempted_pcs
         join erp.wip_stage_events src on src.id=rv.source_id
           and src.source_type='LAUNDRY_DELIVERY_LINE'
           and src.source_id=sx.delivery_line_id
         join erp.laundry_delivery_lines fdl on fdl.id=src.source_id
           and fdl.delivery_id=f.delivery_id
           and rv.po_id=sd.po_id
           and rv.cutting_group_id=fdl.cutting_group_id
         where f.delivery_id=sd.id and f.custody_outcome='RETURN_UNPROCESSED'
           and fr.physical_at<=dd.physical_at and rv.physical_at<=dd.physical_at
       )
    union all
    select min(a.id::text)::uuid
    from erp.laundry_redispatch_participant_allocations a
    group by a.source_delivery_batch_size_line_id
    having min(a.source_offset_pcs)<>0
       or max(a.source_offset_pcs+a.qty_pcs)<>sum(a.qty_pcs)
    union all
    select min(a.id::text)::uuid
    from erp.laundry_redispatch_participant_allocations a
    group by a.successor_delivery_batch_size_line_id
    having min(a.successor_offset_pcs)<>0
       or max(a.successor_offset_pcs+a.qty_pcs)<>sum(a.qty_pcs)
  ) bad_lineage

  union all
  select 'V268_ACTIVE_SALE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
    'Every active Sale with a monetary or rounded non-PO HPP effect requires its SALE journal'
  from erp.sales_headers h
  where h.status in('POSTED','PARTIAL_PAID','PAID')
    and round(coalesce((select sum(i.line_total) from erp.sales_items i
          where i.sale_id=h.id),0),2)>0.005
    and not exists(select 1 from erp.journal_entries j
      where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V268_POSTED_SALES_RETURN_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
    'Every posted return with a monetary or rounded non-PO HPP effect requires its SALES_RETURN journal'
  from erp.sales_returns h
  where h.status='POSTED'
    and round(coalesce((select sum(i.refund_amount)
          from erp.sales_return_items i where i.return_id=h.id),0),2)>0.005
    and not exists(select 1 from erp.journal_entries j
      where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Each non-PO product book must equal cumulative per-lot minor-unit HPP targets across every active Sale, return, correction, and reversal'
  from(
    select distinct fl.product_id
    from erp.fg_lots fl
    where fl.po_id is null
      and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
  ) p
  cross join lateral erp.compute_non_po_product_hpp_targets_v2620f(p.product_id) t
  cross join lateral erp.compute_non_po_product_hpp_book_v2620f(p.product_id) b
  where abs(t.hpp_total_cost-b.hpp_total_cost)>0.005
     or abs(t.fg_value-b.fg_value)>0.005
     or abs(t.cogs_value-b.cogs_value)>0.005
     or abs(t.other_out_value-b.other_out_value)>0.005

  union all
  select 'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE','CRITICAL',count(*)::bigint,
    'Posted cumulative product refund may never exceed the exact original product sale value'
  from(
    select sr.sale_id,i.product_id,sum(i.refund_amount)::numeric refund,
      coalesce((select sum(si.line_total) from erp.sales_items si
        where si.sale_id=sr.sale_id and si.product_id=i.product_id),0)::numeric sold
    from erp.sales_returns sr join erp.sales_return_items i on i.return_id=sr.id
    where sr.status='POSTED'
    group by sr.sale_id,i.product_id
  ) refund where refund.refund>refund.sold

  union all
  select 'V2620E_OPENING_HPP_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Opening FG HPP must follow its opening source or latest active correction and must not pretend to have production components'
  from erp.fg_lots fl
  left join lateral(
    select count(*)::integer movement_count,min(m.id::text)::uuid movement_id,
      min(m.source_id::text)::uuid source_id,min(m.qty_signed)::integer qty_signed,
      min(m.unit_hpp_snapshot)::numeric unit_hpp
    from erp.fg_stock_movements m
    where m.lot_id=fl.id and m.movement_type='OPENING'
  ) om on true
  left join erp.opening_balance_items oi on oi.id=om.source_id
  left join erp.opening_balance_headers oh on oh.id=oi.opening_id
  left join lateral(
    select count(*)::integer current_count,min(h.id::text)::uuid current_id,
      min(h.qty_basis_pcs)::integer qty_basis,min(h.total_cost)::numeric total_cost
    from erp.hpp_versions h where h.lot_id=fl.id and h.is_current
  ) ch on true
  left join lateral(
    select h.total_cost,h.qty_basis_pcs
    from erp.hpp_versions h where h.lot_id=fl.id
    order by h.version_no,h.id limit 1
  ) first_hpp on true
  left join lateral(
    select c.corrected_hpp
    from erp.opening_hpp_corrections c
    join erp.hpp_versions h on h.id=c.hpp_version_id
    where c.lot_id=fl.id and c.status='POSTED'
    order by h.version_no desc,h.id desc limit 1
  ) correction on true
  where fl.lot_origin='OPENING' and(
    om.movement_count<>1 or ch.current_count<>1
    or oi.id is null or oi.balance_type<>'FINISHED_GOODS'
    or oh.status<>'POSTED' or oi.product_id is distinct from fl.product_id
    or om.qty_signed is distinct from fl.initial_qty_pcs
    or ch.qty_basis is distinct from fl.initial_qty_pcs
    or abs(first_hpp.total_cost-fl.initial_qty_pcs*om.unit_hpp)>0.000001
    or abs(om.unit_hpp-erp.resolve_opening_fg_unit_hpp(oi.id,oh.opening_date))>0.000001
    or abs(ch.total_cost-fl.initial_qty_pcs
      *coalesce(correction.corrected_hpp,om.unit_hpp))>0.000001
    or fl.cached_qty_pcs is distinct from coalesce((
      select sum(m.qty_signed)::integer from erp.fg_stock_movements m
      where m.lot_id=fl.id
    ),0)
    or exists(select 1 from erp.hpp_version_components c
      join erp.hpp_versions h on h.id=c.hpp_version_id where h.lot_id=fl.id)
  )

  union all
  select 'V2620E_OPENING_FG_GL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each posted opening document FG journal must equal its immutable opening FG movement value'
  from erp.opening_balance_headers h
  cross join lateral(
    select coalesce(sum(round(m.qty_signed*m.unit_hpp_snapshot,2)),0)::numeric expected_fg
    from erp.opening_balance_items i
    join erp.fg_stock_movements m
      on m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
     and m.movement_type='OPENING'
    where i.opening_id=h.id and i.balance_type='FINISHED_GOODS'
  ) expected
  cross join lateral(
    select coalesce(sum(l.debit-l.credit),0)::numeric actual_fg
    from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
    where j.source_type='OPENING_BALANCE' and j.source_id=h.id
      and j.status='POSTED' and l.account_id=erp.account_id('FG_INVENTORY')
  ) actual
  where h.status='POSTED' and abs(expected.expected_fg-actual.actual_fg)>0.005

  union all
  select 'V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Each customer payment must own exactly one exact cash/AR journal and, when reversed, exactly one exact inverse'
  from(
    select p.id
    from erp.sales_payments p
    join erp.sales_headers h on h.id=p.sale_id
    where
      (p.status='DRAFT' and exists(
        select 1 from erp.journal_entries o
        where o.source_type='SALES_PAYMENT' and o.source_id=p.id
      ))
      or
      (p.status in('POSTED','REVERSED') and(
        (select count(*) from erp.journal_entries o
         where o.source_type='SALES_PAYMENT' and o.source_id=p.id)<>1
        or not exists(
          select 1
          from erp.journal_entries o
          where o.source_type='SALES_PAYMENT' and o.source_id=p.id
            and o.status=case when p.status='POSTED' then 'POSTED' else 'REVERSED' end
            and o.economic_date=case when p.replaces_payment_id is null
          then erp._cp3_business_date(p.payment_date) else (select pr.reversal_economic_date
            from erp.sales_payment_reversal_facts pr
            where pr.payment_id=p.replaces_payment_id) end
            and (select count(*) from erp.journal_lines l where l.journal_entry_id=o.id)=2
            and (select coalesce(sum(l.debit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount
            and (select coalesce(sum(l.credit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount
            and (select count(*) from erp.journal_lines l
                 join erp.cash_accounts ca on ca.id=p.cash_account_id and ca.coa_account_id=l.account_id
                 where l.journal_entry_id=o.id and l.debit=p.amount and l.credit=0
                   and l.customer_id=h.customer_id and l.vendor_id is null
                   and l.contractor_id is null and l.po_id is null and l.product_id is null)=1
            and (select count(*) from erp.journal_lines l
                 where l.journal_entry_id=o.id and l.account_id=erp.account_id('AR_CUSTOMER')
                   and l.debit=0 and l.credit=p.amount and l.customer_id=h.customer_id
                   and l.vendor_id is null and l.contractor_id is null
                   and l.po_id is null and l.product_id is null)=1
            and (
              (p.status='POSTED' and not exists(
                select 1 from erp.journal_entries r
                where r.source_type='JOURNAL_REVERSAL'
                  and (r.source_id=o.id or r.reversal_of_id=o.id)
              ))
              or
              (p.status='REVERSED'
                and (select count(*) from erp.journal_entries r
                     where r.source_type='JOURNAL_REVERSAL'
                       and (r.source_id=o.id or r.reversal_of_id=o.id))=1
                and exists(
                  select 1 from erp.journal_entries r
                  where r.source_type='JOURNAL_REVERSAL' and r.source_id=o.id
                    and r.reversal_of_id=o.id and r.status='POSTED'
                    and (select count(*) from erp.journal_lines x where x.journal_entry_id=r.id)=2
                    and not exists(
                      select 1 from erp.journal_lines ol
                      where ol.journal_entry_id=o.id and not exists(
                        select 1 from erp.journal_lines rl
                        where rl.journal_entry_id=r.id
                          and rl.account_id=ol.account_id
                          and rl.debit=ol.credit and rl.credit=ol.debit
                          and rl.customer_id is not distinct from ol.customer_id
                          and rl.vendor_id is not distinct from ol.vendor_id
                          and rl.contractor_id is not distinct from ol.contractor_id
                          and rl.po_id is not distinct from ol.po_id
                          and rl.product_id is not distinct from ol.product_id
                      )
                    )
                    and not exists(
                      select 1 from erp.journal_lines rl
                      where rl.journal_entry_id=r.id and not exists(
                        select 1 from erp.journal_lines ol
                        where ol.journal_entry_id=o.id
                          and ol.account_id=rl.account_id
                          and ol.debit=rl.credit and ol.credit=rl.debit
                          and ol.customer_id is not distinct from rl.customer_id
                          and ol.vendor_id is not distinct from rl.vendor_id
                          and ol.contractor_id is not distinct from rl.contractor_id
                          and ol.po_id is not distinct from rl.po_id
                          and ol.product_id is not distinct from rl.product_id
                      )
                    )
                )
              )
            )
        )
      ))
    union all
    select o.id
    from erp.journal_entries o
    where o.source_type='SALES_PAYMENT'
      and not exists(select 1 from erp.sales_payments p where p.id=o.source_id)
  ) payment_lineage_faults

  union all
  select 'V2620K_PAYMENT_ALLOCATION_DATE_MISMATCH','CRITICAL',count(*)::bigint,
    'Allocation replacement must conserve cash and customer AR on each economic and GL date'
  from erp.sales_payment_posting_facts f
  left join erp.sales_payment_reversal_facts pr on pr.payment_id=f.replaces_payment_id
  where f.replaces_payment_id is not null and(
    pr.payment_id is null
    or f.journal_economic_date is distinct from pr.reversal_economic_date
    or f.journal_transaction_date is distinct from pr.reversal_transaction_date
    or f.journal_posting_at<pr.reversal_posting_at)

  union all
  select 'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH','CRITICAL',count(*)::bigint,
    'Posted payment invoice/cash identity and reversal dates must match append-only facts; correction requires one linked replacement'
  from(
    select p.id
    from erp.sales_payments p
    left join erp.sales_headers h on h.id=p.sale_id
    left join erp.sales_payment_posting_facts f on f.payment_id=p.id
    left join erp.journal_entries o on o.id=f.original_journal_entry_id
    left join erp.sales_payment_reversal_facts rf on rf.payment_id=p.id
    left join erp.journal_entries r on r.id=rf.reversal_journal_entry_id
    left join erp.sales_payment_posting_facts pf on pf.payment_id=f.replaces_payment_id
    left join erp.sales_payment_reversal_facts prf on prf.payment_id=f.replaces_payment_id
    where
      (p.status='DRAFT' and(f.payment_id is not null or rf.payment_id is not null))
      or
      (p.status in('POSTED','REVERSED') and(
        f.payment_id is null or h.id is null
        or f.sale_id is distinct from p.sale_id
        or f.customer_id is distinct from h.customer_id
        or f.payment_number is distinct from p.payment_number
        or f.payment_date is distinct from p.payment_date
        or f.amount is distinct from p.amount
        or f.cash_account_id is distinct from p.cash_account_id
        or f.replaces_payment_id is distinct from p.replaces_payment_id
        or f.payment_snapshot is distinct from to_jsonb(p)-'status'
        or f.lineage_sha256 is distinct from encode(extensions.digest(convert_to(jsonb_build_array(
          f.payment_id,f.sale_id,f.customer_id,f.payment_number,f.payment_date,f.amount,
          f.cash_account_id,f.original_journal_entry_id,f.journal_economic_date,
          f.journal_transaction_date,f.journal_posting_at,f.replaces_payment_id,
          f.predecessor_reversal_journal_id,f.payment_snapshot
        )::text,'UTF8'),'sha256'),'hex')
        or o.id is null or o.source_type<>'SALES_PAYMENT' or o.source_id is distinct from p.id
        or o.status is distinct from case when p.status='POSTED' then 'POSTED' else 'REVERSED' end
        or o.economic_date is distinct from f.journal_economic_date
        or o.transaction_date is distinct from f.journal_transaction_date
        or o.posting_at is distinct from f.journal_posting_at
        or ((f.replaces_payment_id is null)<>(f.predecessor_reversal_journal_id is null))
        or (f.replaces_payment_id is not null and(
          pf.payment_id is null or prf.payment_id is null
          or f.predecessor_reversal_journal_id is distinct from prf.reversal_journal_entry_id
          or pf.sale_id=f.sale_id or pf.customer_id is distinct from f.customer_id
          or pf.amount is distinct from f.amount
          or pf.cash_account_id is distinct from f.cash_account_id
          or pf.payment_date is distinct from f.payment_date
        ))
        or (p.status='POSTED' and(
          rf.payment_id is not null or exists(
            select 1 from erp.journal_entries x where x.source_type='JOURNAL_REVERSAL'
              and(x.source_id=o.id or x.reversal_of_id=o.id)
          )
        ))
        or (p.status='REVERSED' and(
          rf.payment_id is null or r.id is null
          or rf.original_journal_entry_id is distinct from o.id
          or r.source_type<>'JOURNAL_REVERSAL' or r.source_id is distinct from o.id
          or r.reversal_of_id is distinct from o.id or r.status<>'POSTED'
          or r.economic_date is distinct from rf.reversal_economic_date
          or r.transaction_date is distinct from rf.reversal_transaction_date
          or r.posting_at is distinct from rf.reversal_posting_at
          or rf.reversal_economic_date<f.journal_economic_date
          or rf.reversal_posting_at<f.journal_posting_at
          or rf.lineage_sha256 is distinct from encode(extensions.digest(convert_to(jsonb_build_array(
            rf.payment_id,rf.original_journal_entry_id,rf.reversal_journal_entry_id,
            rf.reversal_economic_date,rf.reversal_transaction_date,rf.reversal_posting_at
          )::text,'UTF8'),'sha256'),'hex')
        ))
      ))
    union all
    select f.payment_id from erp.sales_payment_posting_facts f
    left join erp.sales_payments p on p.id=f.payment_id where p.id is null
    union all
    select r.payment_id from erp.sales_payment_reversal_facts r
    left join erp.sales_payments p on p.id=r.payment_id
    left join erp.sales_payment_posting_facts f on f.payment_id=r.payment_id
    where p.id is null or f.payment_id is null or p.status<>'REVERSED'
  ) payment_fact_faults

  union all
  select 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH','CRITICAL',count(*)::bigint,
    'RETURN_UNPROCESSED inverse WIP time must equal its authoritative physical receipt time'
  from erp.laundry_failed_wash_attempts a
  left join erp.laundry_receipts rh on rh.id=a.receipt_id
  left join erp.wip_stage_events rv on rv.id=a.return_wip_event_id
  where a.custody_outcome='RETURN_UNPROCESSED' and(
    rh.id is null or rv.id is null
    or rv.source_type<>'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
    or rv.physical_at is distinct from rh.physical_at
  )

  union all
  select 'V2620H_CUSTOMER_AR_STATUS_MISMATCH','CRITICAL',count(*)::bigint,
    'Sale PAID/PARTIAL/POSTED status must equal the exact two-decimal payment subledger and overpayment is unsupported'
  from erp.sales_headers h
  cross join lateral(
    select round(erp.sale_net_total(h.id),2)::numeric(20,2) total,
      round(coalesce(sum(round(p.amount,2)),0),2)::numeric(20,2) paid
    from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'
  ) x
  where h.status in('POSTED','PARTIAL_PAID','PAID') and(
    x.paid>x.total
    or (h.status='PAID' and x.paid<>x.total)
    or (h.status='PARTIAL_PAID' and not(x.paid>0 and x.paid<x.total))
    or (h.status='POSTED' and x.paid<>0)
  )

  union all
  select 'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH','CRITICAL',count(*)::bigint,
    'Each customer signed AR general-ledger balance must equal active net sales less posted payments'
  from(
    select coalesce(g.customer_id,s.customer_id) customer_id,
      coalesce(g.amount,0)::numeric gl_amount,coalesce(s.amount,0)::numeric subledger_amount
    from(
      select jl.customer_id,sum(jl.debit-jl.credit)::numeric amount
      from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where je.status in('POSTED','REVERSED') and jl.account_id=erp.account_id('AR_CUSTOMER')
        and jl.customer_id is not null
      group by jl.customer_id
    ) g
    full join(
      select x.customer_id,sum(x.amount)::numeric amount from(
        select h.customer_id,round(erp.sale_net_total(h.id),2)-coalesce((
          select sum(round(p.amount,2)) from erp.sales_payments p
          where p.sale_id=h.id and p.status='POSTED'),0) amount
        from erp.sales_headers h where h.status in('POSTED','PARTIAL_PAID','PAID')
        union all
        select ob.customer_id,ob.original_amount-ob.settled_amount
        from erp.opening_subledger_balances ob
        join erp.opening_balance_items oi on oi.id=ob.opening_item_id
        join erp.opening_balance_headers oh on oh.id=oi.opening_id and oh.status='POSTED'
        where ob.party_type='CUSTOMER' and ob.direction='RECEIVABLE'
      ) x group by x.customer_id
    ) s on s.customer_id=g.customer_id
  ) ar where round(ar.gl_amount,2) is distinct from round(ar.subledger_amount,2)

  union all
  select 'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH','CRITICAL',count(*)::bigint,
    'Laundry source and inverse events must match authoritative delivery quantity, dimensions, direction, chronology and net physical custody'
  from(
    select dl.id
    from erp.laundry_delivery_lines dl
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    join erp.production_orders po on po.id=d.po_id
    left join lateral(
      select count(*) total_sources,
        count(*) filter(where s.po_id=d.po_id
          and s.cutting_group_id is not distinct from dl.cutting_group_id
          and s.contractor_id is not distinct from po.contractor_id
          and s.stage_from='SEWING' and s.stage_to='LAUNDRY'
          and s.qty_pcs=dl.qty_sent_pcs and s.physical_at=d.physical_at) valid_sources,
        coalesce(sum(s.qty_pcs),0) source_qty
      from erp.wip_stage_events s
      where s.source_type='LAUNDRY_DELIVERY_LINE' and s.source_id=dl.id
    ) source on true
    left join lateral(
      select count(*) total_inverses,
        count(*) filter(where r.po_id=s.po_id
          and r.cutting_group_id is not distinct from s.cutting_group_id
          and r.contractor_id is not distinct from s.contractor_id
          and r.stage_from='LAUNDRY' and r.stage_to='SEWING'
          and r.qty_pcs=dl.qty_sent_pcs and r.qty_pcs=s.qty_pcs
          and r.physical_at>=s.physical_at) valid_inverses,
        coalesce(sum(r.qty_pcs),0) inverse_qty
      from erp.wip_stage_events s
      join erp.wip_stage_events r on r.source_id=s.id
        and r.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      where s.source_type='LAUNDRY_DELIVERY_LINE' and s.source_id=dl.id
    ) inverse on true
    where d.status<>'DRAFT' and(
      source.total_sources<>1 or source.valid_sources<>1
      or inverse.total_inverses<>case when d.status='REVERSED' then 1 else 0 end
      or inverse.valid_inverses<>inverse.total_inverses
      or source.source_qty-inverse.inverse_qty<>
        case when d.status='REVERSED' then 0 else dl.qty_sent_pcs end
    )
    union all
    select s.id from erp.wip_stage_events s
    left join erp.laundry_delivery_lines dl on dl.id=s.source_id
    left join erp.laundry_deliveries d on d.id=dl.delivery_id
    where s.source_type='LAUNDRY_DELIVERY_LINE'
      and(dl.id is null or d.id is null or d.status='DRAFT')
    union all
    select r.id from erp.wip_stage_events r
    left join erp.wip_stage_events s on s.id=r.source_id
      and s.source_type='LAUNDRY_DELIVERY_LINE'
    where r.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL' and s.id is null
  ) bad_custody

  union all
  select 'V2620E_REDISPATCH_EVENT_MISMATCH','CRITICAL',count(*)::bigint,
    'Effective redispatch allocation/release events must be bounded, non-overlapping, chronological, and backed by exact custody facts'
  from(
    select a.id
    from erp.laundry_redispatch_participant_events a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sl on sl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sl.delivery_id
    join erp.laundry_delivery_batch_size_lines dx
      on dx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=dx.delivery_line_id
    join erp.laundry_deliveries dd on dd.id=dl.delivery_id
    where a.event_type='ALLOCATE' and(
      sx.distribution_batch_id<>dx.distribution_batch_id or sx.size_id<>dx.size_id
      or sl.cutting_group_id<>dl.cutting_group_id or sd.status<>'REVERSED'
      or (sd.physical_at,sd.created_at,sd.id)>=(dd.physical_at,dd.created_at,dd.id)
      or a.source_offset_pcs+a.qty_pcs>sx.qty_sent_pcs
      or a.successor_offset_pcs+a.qty_pcs>dx.qty_sent_pcs
      or not exists(
        select 1 from erp.laundry_failed_wash_attempts f
        join erp.laundry_failed_wash_batch_size_lines fx
          on fx.attempt_id=f.id and fx.delivery_batch_size_line_id=sx.id
         and fx.qty_attempted_pcs=sx.qty_sent_pcs
        join erp.laundry_receipts fr on fr.id=f.receipt_id
           and fr.status in('POSTED','REVERSED')
         join erp.wip_stage_events rv on rv.id=f.return_wip_event_id
           and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
           and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
           and rv.qty_pcs=f.qty_attempted_pcs
         join erp.wip_stage_events src on src.id=rv.source_id
           and src.source_type='LAUNDRY_DELIVERY_LINE'
           and src.source_id=sx.delivery_line_id
         join erp.laundry_delivery_lines fdl on fdl.id=src.source_id
           and fdl.delivery_id=f.delivery_id
           and rv.po_id=sd.po_id
           and rv.cutting_group_id=fdl.cutting_group_id
        where f.delivery_id=sd.id and f.custody_outcome='RETURN_UNPROCESSED'
          and fr.physical_at<=dd.physical_at and rv.physical_at<=dd.physical_at)
      or (not exists(select 1 from erp.laundry_redispatch_participant_events x
            where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
          and dd.status='REVERSED'
          and not exists(select 1 from erp.laundry_receipts r where r.delivery_id=dd.id))
    )
    union all
    select a.id
    from erp.laundry_redispatch_participant_events a
    where a.event_type='ALLOCATE'
      and not exists(select 1 from erp.laundry_redispatch_participant_events x
        where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
      and exists(
        select 1 from erp.laundry_redispatch_participant_events b
        where b.event_type='ALLOCATE' and b.id>a.id
          and not exists(select 1 from erp.laundry_redispatch_participant_events x
            where x.event_type='RELEASE' and x.releases_allocation_event_id=b.id)
          and ((b.source_delivery_batch_size_line_id=a.source_delivery_batch_size_line_id
              and int4range(b.source_offset_pcs,b.source_offset_pcs+b.qty_pcs,'[)')
                && int4range(a.source_offset_pcs,a.source_offset_pcs+a.qty_pcs,'[)'))
            or (b.successor_delivery_batch_size_line_id=a.successor_delivery_batch_size_line_id
              and int4range(b.successor_offset_pcs,b.successor_offset_pcs+b.qty_pcs,'[)')
                && int4range(a.successor_offset_pcs,a.successor_offset_pcs+a.qty_pcs,'[)')))
      )
    union all
    select x.id
    from erp.laundry_redispatch_participant_events x
    join erp.laundry_redispatch_participant_events a
      on a.id=x.releases_allocation_event_id and a.event_type='ALLOCATE'
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    where x.event_type='RELEASE' and(
      x.released_delivery_id<>d.id or d.status<>'REVERSED'
      or exists(select 1 from erp.laundry_receipts r where r.delivery_id=d.id)
    )
  ) bad_events

  union all
  select 'V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Every posted conversion must be PO-sourced, value-preserving, rooted, and represented by exact OUT/IN facts with current descendant HPP'
  from erp.product_conversion_allocations a
  join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
  join erp.fg_lots s on s.id=a.source_lot_id
  left join erp.fg_lots d on d.id=a.destination_lot_id
  left join erp.v_current_hpp sh on sh.lot_id=s.id
  left join erp.v_current_hpp dh on dh.lot_id=d.id
  where s.po_id is null or d.id is null or d.po_id is distinct from s.po_id
     or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
     or d.initial_qty_pcs is distinct from a.qty_pcs or a.qty_pcs<=0
     or sh.hpp_per_pcs is null or dh.hpp_per_pcs is null
     or abs(dh.hpp_per_pcs-(sh.hpp_per_pcs
       +a.conversion_cost_allocated/nullif(a.qty_pcs,0)))>0.000001
     or (select count(*) from erp.fg_stock_movements m
         where m.source_type='PRODUCT_CONVERSION' and m.source_id=c.id
           and m.lot_id=s.id and m.movement_type='REBRAND_OUT'
           and m.qty_signed=-a.qty_pcs)<>1
     or (select count(*) from erp.fg_stock_movements m
         where m.source_type='PRODUCT_CONVERSION' and m.source_id=c.id
           and m.lot_id=d.id and m.movement_type='REBRAND_IN'
           and m.qty_signed=a.qty_pcs)<>1

  union all
  select 'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','CRITICAL',count(*)::bigint,
    'Every Sale lifecycle journal must conserve FG/COGS/disposition independently inside each PO or non-PO dimension'
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  cross join lateral(
    select coalesce(sum(l.debit-l.credit) filter(where l.account_id in(
      erp.account_id('COGS'),erp.account_id('FG_INVENTORY'),
      erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
    )),0) hpp_net
    from erp.journal_lines l where l.journal_entry_id=e.id
  ) b
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  ) and(
    abs(b.hpp_net)>0.005
    or exists(
      select 1 from erp.journal_lines l
      where l.journal_entry_id=e.id
        and l.account_id in(
          erp.account_id('COGS'),erp.account_id('FG_INVENTORY'),
          erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
        )
      group by l.po_id
      having abs(sum(l.debit-l.credit))>0.005
    )
  );
  return query
  select 'V2620AD_OPENING_MATERIAL_TIMELINE_MISMATCH'::text,'CRITICAL'::text,
    (select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id
    where h.status='POSTED' and i.balance_type='MATERIAL' and (
      (select count(*) from erp.material_stock_movements m
       where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id)<>1
      or not exists(select 1 from erp.material_stock_movements m
        where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
          and m.movement_type='OPENING' and m.material_id=i.material_id
          and m.location_id=i.location_id and m.roll_id is not distinct from i.roll_id
          and m.physical_at=(h.opening_date::timestamp at time zone 'Asia/Jakarta'))
    )),
    'Every posted material opening line must own one movement at the start of its Jakarta document date'::text;

  return query
  select 'V2620AE_OPENING_MATERIAL_ROLL_INTEGRITY'::text,'CRITICAL'::text,
    (select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
    left join erp.materials material on material.id=i.material_id
    left join erp.material_rolls roll on roll.id=i.roll_id
    where (i.roll_id is not null and i.balance_type<>'MATERIAL')
      or (i.balance_type='MATERIAL' and (
      (material.material_type='FABRIC' and i.roll_id is null)
      or (i.roll_id is not null and (
        material.material_type is distinct from 'FABRIC'
        or
        roll.material_id is distinct from i.material_id
        or roll.purchase_item_id is not null
        or i.qty>roll.original_qty
        or (select count(*) from erp.opening_balance_items other_i
            join erp.opening_balance_headers other_h on other_h.id=other_i.opening_id
            where other_h.status='POSTED' and other_i.balance_type='MATERIAL'
              and other_i.roll_id=i.roll_id)<>1
        or (select count(*) from erp.material_stock_movements opening_m
            where opening_m.roll_id=i.roll_id and opening_m.movement_type='OPENING'
              and opening_m.reversal_of_id is null)<>1
        or exists(select 1 from erp.material_stock_movements purchase_m
            where purchase_m.roll_id=i.roll_id and purchase_m.movement_type='PURCHASE'
              and purchase_m.reversal_of_id is null)
      ))
    ))),
    'Each posted opening roll must belong to one fabric line, enter once, and stay within original quantity'::text;

  return query
  select 'V2620AF_OPENING_SOURCE_LINEAGE_MISMATCH'::text,'CRITICAL'::text,
    (select count(*)::bigint from (
    select m.id
    from erp.material_stock_movements m
    left join erp.opening_balance_items i on i.id=m.source_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where m.source_type='OPENING_BALANCE_ITEM' and m.movement_type='OPENING'
      and m.reversal_of_id is null and (
        h.status is distinct from 'POSTED' or i.balance_type is distinct from 'MATERIAL'
        or m.material_id is distinct from i.material_id
        or m.roll_id is distinct from i.roll_id or m.location_id is distinct from i.location_id
        or m.qty_signed is distinct from i.qty
        or m.input_unit_cost is distinct from i.unit_cost_snapshot)
    union all
    select m.id
    from erp.fg_stock_movements m
    left join erp.opening_balance_items i on i.id=m.source_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where m.source_type='OPENING_BALANCE_ITEM' and m.movement_type='OPENING'
      and m.reversal_of_id is null and (
        h.status is distinct from 'POSTED' or i.balance_type is distinct from 'FINISHED_GOODS'
        or m.product_id is distinct from i.product_id or m.qty_signed is distinct from i.qty
        or (i.location_id is not null and m.location_id is distinct from i.location_id))
    union all
    select s.id
    from erp.opening_subledger_balances s
    left join erp.opening_balance_items i on i.id=s.opening_item_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where h.status is distinct from 'POSTED'
      or i.balance_type is distinct from (s.party_type||'_'||s.direction)
      -- original_amount is the CURRENT corrected balance (numeric(20,2)),
      -- despite its legacy column name. The immutable opening line remains
      -- unchanged; posted linked correction deltas determine its effective sum.
      or s.original_amount is distinct from (round(i.amount,2)+coalesce((
        select sum(c.delta_amount) from erp.opening_financial_corrections c
        where c.opening_item_id=i.id and c.status='POSTED'),0))
    union all
    select h.id from erp.opening_balance_headers h
    where h.status='POSTED'
      and not exists(select 1 from erp.opening_balance_items i where i.opening_id=h.id)
    union all
    select e.id from erp.journal_entries e
    left join erp.opening_balance_headers h on h.id=e.source_id
    where e.source_type='OPENING_BALANCE' and e.reversal_of_id is null
      and h.status is distinct from 'POSTED'
    union all
    select h.id from erp.opening_balance_headers h
    cross join lateral (
      select coalesce(sum(greatest(coalesce(round(case
        when i.balance_type in('MATERIAL','FINISHED_GOODS') then i.qty*i.unit_cost_snapshot
        when i.balance_type='WIP' then coalesce(i.amount,coalesce(i.qty,0)*coalesce(i.unit_cost_snapshot,0))
        when i.balance_type in('CONTRACTOR_RECEIVABLE','CUSTOMER_RECEIVABLE','CASH_BANK') then i.amount
        else 0 end,2),0),0)),0) debits,
        coalesce(sum(greatest(coalesce(round(case
        when i.balance_type in('CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE') then i.amount
        else 0 end,2),0),0)),0) credits
      from erp.opening_balance_items i where i.opening_id=h.id
    ) expected
    cross join lateral (
      select coalesce(sum(l.debit),0) debits,coalesce(sum(l.credit),0) credits
      from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
      where e.source_type='OPENING_BALANCE' and e.source_id=h.id and e.reversal_of_id is null
    ) actual
    where h.status='POSTED' and (
      actual.debits<>greatest(expected.debits,expected.credits)
      or actual.credits<>greatest(expected.debits,expected.credits))
  ) broken_opening_lineage),
    'Opening stock and subledger facts require their original posted source with conserved quantity and input value'::text;

  return query select 'V2620AG_SALE_RESERVATION_LINEAGE_MISMATCH'::text,'CRITICAL'::text,(with active as (
  select m.* from erp.fg_stock_movements m
  where m.source_type='SALE_ITEM' and m.movement_type in('SALE_RESERVE','SALE')
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)
), allocations as (
  select a.sale_item_id,a.lot_id,a.location_id,sum(a.qty_pcs)::bigint qty
  from erp.sale_stock_allocations a group by a.sale_item_id,a.lot_id,a.location_id
), movements as (
  select m.source_id sale_item_id,m.lot_id,m.location_id,sum(-m.qty_signed)::bigint qty
  from active m group by m.source_id,m.lot_id,m.location_id
)
select count(*)::bigint from (
  select m.id,sh_lineage.id sale_id from active m
  left join erp.sales_items i on i.id=m.source_id
  left join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  left join erp.fg_lots l on l.id=m.lot_id
  where sh_lineage.status is null or sh_lineage.status not in('DRAFT','POSTED','PARTIAL_PAID','PAID')
    or m.movement_type is distinct from case when sh_lineage.status='DRAFT' then 'SALE_RESERVE' else 'SALE' end
    or m.product_id is distinct from i.product_id or l.product_id is distinct from i.product_id
    or m.location_id is distinct from sh_lineage.source_location_id
    or m.customer_id is distinct from sh_lineage.customer_id or m.physical_at is distinct from sh_lineage.sale_date
    or m.quality_grade is distinct from 'GRADE_A' or m.qty_signed>=0
  union all
  select a.id,sh_lineage.id from erp.sale_stock_allocations a
  left join erp.sales_items i on i.id=a.sale_item_id
  left join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  left join erp.fg_lots l on l.id=a.lot_id
  where sh_lineage.status is null or sh_lineage.status not in('DRAFT','POSTED','PARTIAL_PAID','PAID','REVERSED')
    or l.product_id is distinct from i.product_id
    or a.location_id is distinct from sh_lineage.source_location_id or a.qty_pcs<=0
  union all
  select i.id,sh_lineage.id from allocations a full join movements m using(sale_item_id,lot_id,location_id)
  join erp.sales_items i on i.id=coalesce(a.sale_item_id,m.sale_item_id)
  join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  where sh_lineage.status in('DRAFT','POSTED','PARTIAL_PAID','PAID') and a.qty is distinct from m.qty
  union all
  select i.id,sh_lineage.id from erp.sales_items i join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  where (sh_lineage.status in('POSTED','PARTIAL_PAID','PAID') or
    (sh_lineage.status='DRAFT' and (exists(select 1 from erp.sale_stock_allocations a
       join erp.sales_items sibling on sibling.id=a.sale_item_id where sibling.sale_id=sh_lineage.id)
      or exists(select 1 from active m join erp.sales_items sibling on sibling.id=m.source_id where sibling.sale_id=sh_lineage.id))))
    and (i.qty_pcs is distinct from (select coalesce(sum(a.qty_pcs),0) from erp.sale_stock_allocations a where a.sale_item_id=i.id)
      or i.qty_pcs is distinct from (select coalesce(sum(-m.qty_signed),0) from active m where m.source_id=i.id))
  union all
  select sh_lineage.id,sh_lineage.id from erp.sales_headers sh_lineage where sh_lineage.status in('POSTED','PARTIAL_PAID','PAID')
    and not exists(select 1 from erp.sales_items i where i.sale_id=sh_lineage.id)
) broken where /*SCOPE*/true),'Sale source and reserved or posted stock must agree on item, lot, quantity, location, customer and physical time'::text;
  return query select 'V2620AH_RETURN_ALLOCATION_LINEAGE_MISMATCH'::text,'CRITICAL'::text,(with active_return as (
  select ah_line.*,ah_return.sale_id,ah_return.customer_id,ah_return.physical_at
  from erp.sales_return_items ah_line join erp.sales_returns ah_return on ah_return.id=ah_line.return_id
  where ah_return.status='POSTED'
), live_movement as (
  select ah_movement.* from erp.fg_stock_movements ah_movement
  where ah_movement.source_type='SALES_RETURN_ITEM' and ah_movement.movement_type='SALE_RETURN'
    and not exists(select 1 from erp.fg_stock_movements ah_reversal where ah_reversal.reversal_of_id=ah_movement.id)
)
select count(*)::bigint from (
  select ah_line.id from active_return ah_line
  left join erp.sale_stock_allocations ah_allocation on ah_allocation.id=ah_line.sale_stock_allocation_id
  left join erp.sales_items ah_sale_line on ah_sale_line.id=ah_allocation.sale_item_id
  left join erp.sales_headers ah_sale on ah_sale.id=ah_sale_line.sale_id
  where ah_allocation.id is null or ah_sale.status is null or ah_sale.status not in('POSTED','PARTIAL_PAID','PAID')
    or ah_line.sale_id is distinct from ah_sale.id or ah_line.customer_id is distinct from ah_sale.customer_id
    or ah_line.product_id is distinct from ah_sale_line.product_id or ah_line.lot_id is distinct from ah_allocation.lot_id
    or ah_line.physical_at<ah_sale.sale_date
  union all
  select ah_allocation.id from erp.sale_stock_allocations ah_allocation join active_return ah_line on ah_line.sale_stock_allocation_id=ah_allocation.id
  group by ah_allocation.id,ah_allocation.qty_pcs having sum(ah_line.qty_pcs)>ah_allocation.qty_pcs
  union all
  select ah_movement.id from live_movement ah_movement left join active_return ah_line on ah_line.id=ah_movement.source_id
  where ah_line.id is null or ah_movement.product_id is distinct from ah_line.product_id or ah_movement.lot_id is distinct from ah_line.lot_id
    or ah_movement.location_id is distinct from ah_line.location_id or ah_movement.quality_grade is distinct from ah_line.quality_grade
    or ah_movement.customer_id is distinct from ah_line.customer_id or ah_movement.physical_at is distinct from ah_line.physical_at
    or ah_movement.qty_signed is distinct from ah_line.qty_pcs
  union all
  select ah_line.id from active_return ah_line left join live_movement ah_movement on ah_movement.source_id=ah_line.id
  group by ah_line.id,ah_line.qty_pcs having count(ah_movement.id)<>1 or sum(ah_movement.qty_signed) is distinct from ah_line.qty_pcs::bigint
  union all
  select ah_return.id from erp.sales_returns ah_return where ah_return.status='POSTED'
    and not exists(select 1 from erp.sales_return_items ah_line where ah_line.return_id=ah_return.id)
) broken),'Active return quantities and receipt facts must match their selected original sale allocation and chosen destination'::text;
end
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.validate_work_completion()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$ DECLARE v_event_po uuid;v_event_contractor uuid;v_po_contractor uuid;v_snapshot_po uuid;v_snapshot_component uuid;v_snapshot_rate numeric(18,2); BEGIN PERFORM erp.require_internal(); SELECT po_id,contractor_id INTO v_event_po,v_event_contractor FROM erp.work_completion_events WHERE id=NEW.completion_id; SELECT contractor_id INTO v_po_contractor FROM erp.production_orders WHERE id=v_event_po; SELECT po_id,work_component_id,rate_per_pcs_snapshot INTO v_snapshot_po,v_snapshot_component,v_snapshot_rate FROM erp.po_work_component_snapshots WHERE id=NEW.po_component_snapshot_id; IF v_event_po IS NULL THEN RAISE EXCEPTION 'Completion event not found'; END IF; IF v_po_contractor IS DISTINCT FROM v_event_contractor THEN RAISE EXCEPTION 'Completion contractor must match PO contractor'; END IF; IF v_snapshot_po<>v_event_po OR v_snapshot_component<>NEW.work_component_id THEN RAISE EXCEPTION 'Work component snapshot does not match completion PO/component'; END IF; NEW.rate_snapshot:=v_snapshot_rate; RETURN NEW; END; $function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.validate_vendor_invoice_item_lineage()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_header_vendor uuid;
  v_delivery_vendor uuid;
begin
  perform erp.require_internal();
  select vendor_id into v_header_vendor from erp.vendor_invoices where id=new.invoice_id;
  select ld.vendor_id into v_delivery_vendor
  from erp.laundry_receipt_lines lrl
  join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where lrl.id=new.receipt_line_id;
  if v_header_vendor is null then raise exception 'Vendor invoice header not found'; end if;
  if v_delivery_vendor is null then raise exception 'Laundry receipt line not found'; end if;
  if v_header_vendor is distinct from v_delivery_vendor then raise exception 'Vendor invoice vendor does not match laundry delivery vendor'; end if;
  return new;
end;
$function$
$definition$;
end
$canonical_opening_v2620ah$;

do $installed_v2620ah$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620ah_rollback_capsule)<>5 then
    raise exception 'AH_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620ah_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.normalize_sales_return_item_from_allocation()','ea7781898a894cd7694e912f47231fdbcde8745a06a04e8e635210f84bba99ce','eaa4a353f0f455f47e7934c0f33d43a81a68fa15329f686c5283bd338829de08',array['postgres=X/postgres']::text[]),
    ('erp.post_sales_return(uuid)','7640b5781a8838f550595d47bbc3f452a50a846f58018e714a0a209b8f32ff02','a9a7202d34d2111a7def2ec475cd4e95963f5ea6029e6f1ea52c4ec236ed72f8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','e62f7fa0d2892708128c372d6e99d39d7833a3fa2eedfe25f17695c7ca94e3ef','ef5ab903b541819a64ca99e20021f5d1a7ad59bee9cda9122834bef5ce93f889',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_work_completion()','8706d6353ef4f5621a02e0db943f66599a446db0bf2ae2c375d04ead742e8be0','c1a44bfbc3d54131d6d9e52e903f885c8f6aa9df1e5d1a6c0d1905d20a7387bf',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_vendor_invoice_item_lineage()','0f9e0ae58e8482c449a9c76994055e03c2e077b2868e3febc3b1699b0c73158e','05fd228e13dcf54476eb3a2f17810ed958101153336fc9b85cc00aea633b630e',array['postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620ah_rollback_capsule
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
      raise exception 'AH_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620ah$;

do $boundary_v2620ah$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ah_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>220 then
    raise exception 'AH_FULL_ERP_BOUNDARY_CARDINALITY expected220 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620ah_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620ah$;

insert into erp.schema_migrations(version,description)
values('v2.6.20ah','Return allocation eligibility, destination and ordinary draft validation remain coherent');
commit;
