create or replace function cp7_stock_formula.material_source(p_type text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r jsonb;lvl numeric:=(cp7_stock_formula.current_settings()->>'service_level')::numeric;t timestamptz:=clock_timestamp();
begin
 if p_type='FABRIC'then
  if erp.has_permission('warehouse.material.view')is not true or erp.has_permission('master.fabric.view')is not true then
   raise exception using errcode='42501',message='CP7_FORMULA_MATERIAL_SOURCE_DENIED';end if;
 elsif p_type='ACCESSORY'then
  if erp.has_permission('warehouse.accessory.view')is not true then raise exception using errcode='42501',message='CP7_FORMULA_MATERIAL_SOURCE_DENIED';end if;
 else raise exception 'CP7_FORMULA_MATERIAL_TYPE';end if;
 if cp7_stock_formula.ensure_computed()then
  select jsonb_build_object(
   'rows',coalesce(jsonb_agg(cp7_stock_formula.material_alert_row(to_jsonb(e),lvl)order by e.sku,e.material_id)
    filter(where e.state='AT_OR_BELOW'and(p_type='ACCESSORY'or e.basis='FORMULA')),'[]'),
   'states',coalesce(jsonb_object_agg(e.material_id::text,case when e.manual_source='FABRIC_MINIMUM'then'MANUAL_MINIMUM_IN_FORCE'
     when e.state='ABOVE'then'ABOVE_REORDER_POINT'else'NO_REORDER_POINT'end)
    filter(where not(e.state='AT_OR_BELOW'and(p_type='ACCESSORY'or e.basis='FORMULA'))),'{}'))
  into r from cp7_stock_formula.material_evaluations e where e.material_type=p_type;
  return r;
 end if;
 -- Busy: the materials at or under their point in the last evaluation, against the stock now (same locations), with that
 -- evaluation's point and on-order quantity.
 with low as(select e.*,to_jsonb(e)j from cp7_stock_formula.material_evaluations e
   where e.material_type=p_type and e.state='AT_OR_BELOW'and(p_type='ACCESSORY'or e.basis='FORMULA')),
 live as(select l.material_id,l.sku,l.point,l.on_order_qty,l.j,coalesce((select sum(s.qty_signed)from erp.material_stock_movements s
   left join erp.locations x on x.id=s.location_id where s.material_id=l.material_id and s.physical_at<=t and s.system_created_at<=t
    and(p_type='FABRIC'or(x.location_type='RAW_MATERIAL_WAREHOUSE'and x.is_active
     and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=x.id)))),0)::numeric free from low l),
 now_state as(select v.*,v.free+v.on_order_qty<=v.point still from live v)
 select jsonb_build_object(
  'rows',coalesce(jsonb_agg(cp7_stock_formula.material_alert_row(n.j||jsonb_build_object('free_qty',n.free),lvl)order by n.sku,n.material_id)
   filter(where n.still),'[]'),
  'states',coalesce(jsonb_object_agg(n.material_id::text,'ABOVE_REORDER_POINT')filter(where not n.still),'{}'))into r from now_state n;
 return jsonb_set(r,'{states}',(r->'states')||coalesce((select jsonb_object_agg(e.material_id::text,case when e.manual_source='FABRIC_MINIMUM'
   then'MANUAL_MINIMUM_IN_FORCE'when e.state='ABOVE'then'ABOVE_REORDER_POINT'else'NO_REORDER_POINT'end)
  from cp7_stock_formula.material_evaluations e where e.material_type=p_type
   and not(e.state='AT_OR_BELOW'and(p_type='ACCESSORY'or e.basis='FORMULA'))),'{}'));
end $$;
