-- bootstrap lines 26455-26504
CREATE OR REPLACE FUNCTION erp.compute_po_hpp_gl_targets(p_po_id uuid)
 RETURNS TABLE(base_output_qty integer, hpp_total_cost numeric, fg_value numeric, cogs_value numeric, other_out_value numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
with base as (
  select coalesce(sum(fl.initial_qty_pcs),0)::integer as qty,
         coalesce(sum(hv.total_cost),0)::numeric as total
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
), lot_hpp as (
  select fl.id as lot_id,
         case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric as hpp_per_pcs
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
  where fl.po_id=p_po_id
), lot_balance as (
  select lh.lot_id,lh.hpp_per_pcs,coalesce(sum(fm.qty_signed),0)::numeric as qty
  from lot_hpp lh
  left join erp.fg_stock_movements fm on fm.lot_id=lh.lot_id
  group by lh.lot_id,lh.hpp_per_pcs
), sold as (
  select a.lot_id,coalesce(sum(a.qty_pcs),0)::numeric as qty
  from erp.sale_stock_allocations a
  join erp.sales_items si on si.id=a.sale_item_id
  join erp.sales_headers sh on sh.id=si.sale_id
  join erp.fg_lots fl on fl.id=a.lot_id
  where fl.po_id=p_po_id and sh.status in ('POSTED','PARTIAL_PAID','PAID')
  group by a.lot_id
), returned as (
  select sri.lot_id,coalesce(sum(sri.qty_pcs),0)::numeric as qty
  from erp.sales_return_items sri
  join erp.sales_returns sr on sr.id=sri.return_id
  join erp.fg_lots fl on fl.id=sri.lot_id
  where fl.po_id=p_po_id and sr.status='POSTED'
  group by sri.lot_id
), vals as (
  select
    coalesce((select sum(greatest(lb.qty,0)*lb.hpp_per_pcs) from lot_balance lb),0)::numeric as fg_val,
    coalesce((select sum(greatest(coalesce(s.qty,0)-coalesce(r.qty,0),0)*lh.hpp_per_pcs)
              from lot_hpp lh left join sold s on s.lot_id=lh.lot_id left join returned r on r.lot_id=lh.lot_id),0)::numeric as cogs_val
)
select base.qty,base.total,vals.fg_val,vals.cogs_val,(base.total-vals.fg_val-vals.cogs_val)::numeric
from base,vals;
$function$;

alter function "erp"."compute_po_hpp_gl_targets"(p_po_id uuid) owner to "postgres";
