create or replace function erp.compute_po_hpp_gl_targets_v2620d(p_po_id uuid)
returns table(
  base_output_qty integer,hpp_total_cost numeric,fg_value numeric,
  cogs_value numeric,other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with base as(
  select coalesce(sum(fl.initial_qty_pcs),0)::integer qty,
    coalesce(sum(hv.total_cost),0)::numeric raw_total
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
), lot_hpp as(
  select fl.id lot_id,
    case when coalesce(hv.qty_basis_pcs,0)>0
      then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.po_id=p_po_id
    and fl.lot_origin in('PRODUCTION','CONVERSION')
), lot_balance as(
  select lh.lot_id,lh.hpp_per_pcs,
    (coalesce(sum(fm.qty_signed),0)+coalesce(sum(abs(fm.qty_signed)) filter(
      where fm.movement_type='SALE_RESERVE'
        and not exists(select 1 from erp.fg_stock_movements rv
          where rv.reversal_of_id=fm.id)
    ),0))::numeric owned_qty
  from lot_hpp lh
  left join erp.fg_stock_movements fm on fm.lot_id=lh.lot_id
  group by lh.lot_id,lh.hpp_per_pcs
), sold as(
  select a.lot_id,coalesce(sum(a.qty_pcs),0)::numeric qty
  from erp.sale_stock_allocations a
  join erp.sales_items i on i.id=a.sale_item_id
  join erp.sales_headers h on h.id=i.sale_id
  join erp.fg_lots fl on fl.id=a.lot_id
  where fl.po_id=p_po_id and h.status in('POSTED','PARTIAL_PAID','PAID')
  group by a.lot_id
), returned as(
  select i.lot_id,coalesce(sum(i.qty_pcs),0)::numeric qty
  from erp.sales_return_items i
  join erp.sales_returns h on h.id=i.return_id
  join erp.fg_lots fl on fl.id=i.lot_id
  where fl.po_id=p_po_id and h.status='POSTED'
  group by i.lot_id
), raw_values as(
  select b.qty,b.raw_total,
    coalesce(sum(greatest(lb.owned_qty,0)*lb.hpp_per_pcs),0)::numeric raw_owned,
    coalesce(sum(greatest(coalesce(s.qty,0)-coalesce(r.qty,0),0)
      *lb.hpp_per_pcs),0)::numeric raw_cogs
  from base b left join lot_balance lb on true
  left join sold s on s.lot_id=lb.lot_id
  left join returned r on r.lot_id=lb.lot_id
  group by b.qty,b.raw_total
), cents as(
  select qty,round(raw_total,2)::numeric hpp,
    round(raw_total-raw_owned,2)::numeric total_out,
    round(raw_cogs,2)::numeric cogs
  from raw_values
)
select qty,hpp,(hpp-total_out)::numeric,cogs,(total_out-cogs)::numeric
from cents
$function$;
alter function erp.compute_po_hpp_gl_targets_v2620d(uuid) owner to postgres;
