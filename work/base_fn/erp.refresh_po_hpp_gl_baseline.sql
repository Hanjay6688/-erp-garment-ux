-- bootstrap lines 16644-16699
CREATE OR REPLACE FUNCTION erp.refresh_po_hpp_gl_baseline(p_po_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  t record;
  v_documented_gain numeric(24,6):=0;
begin
  perform erp.require_internal();
  select * into t from erp.compute_po_hpp_gl_targets(p_po_id);
  if t.base_output_qty is null or t.base_output_qty<=0 then return; end if;

  with lot_hpp as (
    select fl.id as lot_id,
           case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric as hpp_per_pcs
    from erp.fg_lots fl
    left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
    where fl.po_id=p_po_id
  ), adj_net as (
    select fm.lot_id,sum(fm.qty_signed)::numeric as qty
    from erp.fg_stock_movements fm
    join erp.fg_lots fl on fl.id=fm.lot_id
    where fl.po_id=p_po_id
      and (
        (fm.movement_type='ADJUSTMENT' and fm.source_type='FG_ADJUSTMENT_ITEM')
        or (fm.movement_type='REVERSAL' and exists (
          select 1 from erp.fg_stock_movements orig
          where orig.id=fm.reversal_of_id and orig.movement_type='ADJUSTMENT' and orig.source_type='FG_ADJUSTMENT_ITEM'
        ))
      )
    group by fm.lot_id
  )
  select coalesce(sum(greatest(a.qty,0)*lh.hpp_per_pcs),0)
  into v_documented_gain
  from adj_net a join lot_hpp lh on lh.lot_id=a.lot_id;

  if t.other_out_value < -v_documented_gain-0.01 then
    raise exception 'PO HPP allocation inconsistent: current FG + net sold exceeds production output without a matching documented positive FG adjustment';
  end if;

  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)
  values (p_po_id,t.base_output_qty,t.hpp_total_cost,t.fg_value,t.cogs_value,t.other_out_value,now())
  on conflict (po_id) do update set
    base_output_qty=excluded.base_output_qty,
    hpp_total_cost=excluded.hpp_total_cost,
    fg_value=excluded.fg_value,
    cogs_value=excluded.cogs_value,
    other_out_value=excluded.other_out_value,
    updated_at=now();
end;
$function$;

alter function "erp"."refresh_po_hpp_gl_baseline"(p_po_id uuid) owner to "postgres";
