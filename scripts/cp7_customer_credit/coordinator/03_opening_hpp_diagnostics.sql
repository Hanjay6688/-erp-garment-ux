-- Source-derived diagnostics only; Native financial/conversion workflows are
-- deliberately not called from this fixed post-journal refresh. The original
-- Native function remains unchanged and verified alongside this exact tail.
do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;
do $opening_diagnostic_source$begin
 if not exists(select 1 from pg_proc p where p.oid=to_regprocedure('erp.sync_opening_lot_hpp_to_gl(uuid,date)')
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='59d22a90beecddbe2cd4ca8cd246493c61f2ec9ad882311e7f974819cd117a1e'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig=array['search_path=erp, public'])then
  raise exception 'CP7_CREDIT_OPENING_HPP_DIAGNOSTIC_SOURCE_CHANGED';end if;
end $opening_diagnostic_source$;

create function cp7_credit.refresh_opening_return_hpp_diagnostics_v1(p_return uuid,p_lot_id uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $function$
declare
 l erp.fg_lots; s erp.opening_lot_hpp_gl_state; h erp.hpp_versions;v_baseline numeric;v_expected_delta numeric;
 v_current_qty numeric;v_base_fg numeric;v_net_sold_qty numeric;v_actual_cogs numeric;v_expense numeric;v_income numeric;
begin
 perform erp.require_internal();
 if not exists(select 1 from cp7_credit.opening_return_hpp_work_v1 w where w.return_id=p_return
  and w.backend_pid=pg_backend_pid()and w.transaction_id=txid_current()and p_lot_id=any(w.lot_ids)
  and w.owner_fact=cp7_credit.opening_return_hpp_owner_v1(p_return))then
  raise exception 'CP7_CREDIT_OPENING_HPP_DIAGNOSTIC_SCOPE_REQUIRED';end if;
 select *into strict l from erp.fg_lots where id=p_lot_id for update;
 if l.lot_origin<>'OPENING'or l.po_id is not null then raise exception 'CP7_CREDIT_OPENING_HPP_DIAGNOSTIC_LOT_REQUIRED';end if;
 select *into strict h from erp.hpp_versions where lot_id=l.id and is_current;
 select fm.unit_hpp_snapshot into v_baseline from erp.fg_stock_movements fm where fm.lot_id=l.id and fm.movement_type='OPENING'
  order by fm.physical_at,fm.system_created_at,fm.id limit 1;
 if v_baseline is null then raise exception 'Opening lot % has no source movement',l.lot_number;end if;
 select *into strict s from erp.opening_lot_hpp_gl_state where lot_id=l.id for update;
 v_expected_delta:=round(h.total_cost,2)-round(l.initial_qty_pcs*coalesce(s.current_hpp,v_baseline),2);
 if v_expected_delta is distinct from 0::numeric then raise exception 'CP7_CREDIT_OPENING_HPP_PENDING_SOURCE_CHANGE';end if;
 perform erp.assert_non_po_product_hpp_target_book_v2620f(l.product_id);
  -- Preserve the historical raw revaluation diagnostics and trigger-activation
  -- contract. These projections are not used as monetary posting authority:
  -- actual journals and F's cumulative source/target/book checks are.
  -- DRAFT reservations reduce sellable qty, not company ownership.
  select coalesce(sum(fm.qty_signed),0),coalesce(sum(fm.qty_signed*fm.unit_hpp_snapshot),0)
    into v_current_qty,v_base_fg from erp.fg_stock_movements fm where fm.lot_id=l.id;
  select v_current_qty+coalesce(sum(abs(fm.qty_signed)),0),
    v_base_fg+coalesce(sum(abs(fm.qty_signed)*fm.unit_hpp_snapshot),0)
    into v_current_qty,v_base_fg from erp.fg_stock_movements fm
    where fm.lot_id=l.id and fm.movement_type='SALE_RESERVE'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id);
  select coalesce(sum(a.qty_pcs),0),coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0)
    into v_net_sold_qty,v_actual_cogs from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id join erp.sales_headers sh on sh.id=i.sale_id
    where a.lot_id=l.id and sh.status in('POSTED','PARTIAL_PAID','PAID');
  select v_net_sold_qty-coalesce(sum(i.qty_pcs),0),v_actual_cogs-coalesce(sum(i.qty_pcs*i.unit_hpp_snapshot),0)
    into v_net_sold_qty,v_actual_cogs from erp.sales_return_items i
    join erp.sales_returns rh on rh.id=i.return_id where i.lot_id=l.id and rh.status='POSTED';
  select coalesce(sum(case when i.qty_signed<0 then -i.qty_signed*(h.hpp_per_pcs-i.unit_hpp_snapshot) else 0 end),0),
    coalesce(sum(case when i.qty_signed>0 then i.qty_signed*(h.hpp_per_pcs-i.unit_hpp_snapshot) else 0 end),0)
    into v_expense,v_income from erp.fg_adjustment_items i
    join erp.fg_adjustments a on a.id=i.adjustment_id where i.lot_id=l.id and a.status='POSTED';
  insert into erp.opening_lot_hpp_gl_state(lot_id,current_hpp,fg_revaluation,cogs_revaluation,
    expense_revaluation,income_revaluation,equity_revaluation,updated_at)
  values(l.id,h.hpp_per_pcs,v_current_qty*h.hpp_per_pcs-v_base_fg,
    v_net_sold_qty*h.hpp_per_pcs-v_actual_cogs,v_expense,v_income,
    l.initial_qty_pcs*(h.hpp_per_pcs-v_baseline),statement_timestamp())
  on conflict(lot_id) do update set current_hpp=excluded.current_hpp,
    fg_revaluation=excluded.fg_revaluation,cogs_revaluation=excluded.cogs_revaluation,
    expense_revaluation=excluded.expense_revaluation,income_revaluation=excluded.income_revaluation,
    equity_revaluation=excluded.equity_revaluation,updated_at=statement_timestamp();
end
$function$;
alter function cp7_credit.refresh_opening_return_hpp_diagnostics_v1(uuid,uuid)owner to postgres;
revoke all on function cp7_credit.refresh_opening_return_hpp_diagnostics_v1(uuid,uuid)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
