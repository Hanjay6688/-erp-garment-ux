"""Exact current Native consumer bindings for effective SKU pool values."""

SIGNATURES=(
 'erp.post_sale(uuid)',
 'erp.post_sales_return(uuid)',
 'erp.compute_non_po_product_hpp_targets_v2620f(uuid)',
 'erp.compute_po_hpp_gl_targets_v2620d(uuid)',
 'erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)',
 'erp.sync_po_hpp_to_gl(uuid,date)',
)

NONPO_TARGET="""CREATE OR REPLACE FUNCTION erp.compute_non_po_product_hpp_targets_v2620f(p_product_id uuid)
 RETURNS TABLE(hpp_total_cost numeric, fg_value numeric, cogs_value numeric, other_out_value numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
with native_lots as(
 select fl.id,(case when fl.lot_origin<>'CONVERSION'or exists(select 1 from erp.product_conversion_allocations a
  join erp.product_conversions c on c.id=a.conversion_id where a.destination_lot_id=fl.id and c.status='POSTED')
  then coalesce(hv.total_cost,0)else 0 end-coalesce((select sum(a.qty_pcs*(hv.total_cost/nullif(hv.qty_basis_pcs,0)))
  from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id
  where a.source_lot_id=fl.id and c.status='POSTED'),0))::numeric raw_total
 from erp.fg_lots fl left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
 where fl.product_id=p_product_id and fl.po_id is null and fl.lot_origin<>'VOIDED_PRODUCTION'
), native_total as(select coalesce(sum(raw_total),0)::numeric value from native_lots),
physical as(
 select l.id root_lot_id,(coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed))filter(
  where m.movement_type='SALE_RESERVE'and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),0))::numeric units
 from erp.fg_lots l left join erp.fg_stock_movements m on m.lot_id=l.id
 where l.product_id=p_product_id and l.po_id is null and l.lot_origin<>'VOIDED_PRODUCTION'group by l.id
), component_entries as(
 select root_lot_id,units from physical
 union all select e.root_lot_id,e.units_delta from cp7_sku_conversion.component_events_v2 e
 join erp.fg_lots root on root.id=e.root_lot_id and root.po_id is null where e.product_id=p_product_id
), owned as(
 select coalesce(sum(x.units*h.hpp_per_pcs),0)::numeric value from(
  select root_lot_id,sum(units)::numeric units from component_entries group by root_lot_id)x
 join erp.hpp_versions h on h.lot_id=x.root_lot_id and h.is_current
), conversion_adjustment as(
 select coalesce(sum(e.units_delta*h.hpp_per_pcs),0)::numeric value from cp7_sku_conversion.component_events_v2 e
 join erp.fg_lots root on root.id=e.root_lot_id and root.po_id is null
 join erp.hpp_versions h on h.lot_id=e.root_lot_id and h.is_current
 where e.source_type='SKU_CONVERSION'and e.product_id=p_product_id
), sold as(
 select coalesce(sum(c.component_units*h.hpp_per_pcs),0)::numeric value
 from cp7_sku_conversion.sale_allocation_components_v2 c
 join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
 join erp.sales_headers s on s.id=v.sale_id and s.status in('POSTED','PARTIAL_PAID','PAID')
 join erp.fg_lots root on root.id=c.root_lot_id and root.po_id is null
 join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current where v.product_id=p_product_id
), returned as(
 select coalesce(sum(c.component_units*h.hpp_per_pcs),0)::numeric value
 from cp7_sku_conversion.sales_return_components_v2 c
 join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
 join erp.sales_returns r on r.id=v.return_id and r.status='POSTED'
 join erp.fg_lots root on root.id=c.root_lot_id and root.po_id is null
 join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current where v.product_id=p_product_id
), cents as(
 select round(n.value+a.value,2)::numeric hpp,round(o.value,2)::numeric fg,
  round(greatest(s.value-r.value,0),2)::numeric cogs from native_total n cross join conversion_adjustment a
  cross join owned o cross join sold s cross join returned r
)
select hpp,fg,cogs,(hpp-fg-cogs)::numeric from cents
$function$
"""

PO_TARGET="""CREATE OR REPLACE FUNCTION erp.compute_po_hpp_gl_targets_v2620d(p_po_id uuid)
 RETURNS TABLE(base_output_qty integer, hpp_total_cost numeric, fg_value numeric, cogs_value numeric, other_out_value numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
with base as(
 select coalesce(sum(fl.initial_qty_pcs),0)::integer qty,
  (coalesce(sum(hv.total_cost),0)+erp.be_po_extra_v1(p_po_id))::numeric raw_total
 from erp.fg_lots fl left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
 where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
), physical as(
 select l.id root_lot_id,(coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed))filter(
  where m.movement_type='SALE_RESERVE'and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),0))::numeric units
 from erp.fg_lots l left join erp.fg_stock_movements m on m.lot_id=l.id
 where l.po_id=p_po_id and l.lot_origin<>'VOIDED_PRODUCTION'group by l.id
), component_entries as(
 select root_lot_id,units from physical
 union all select e.root_lot_id,e.units_delta from cp7_sku_conversion.component_events_v2 e
 join erp.fg_lots root on root.id=e.root_lot_id and root.po_id=p_po_id
), owned as(
 select coalesce(sum(x.units*h.hpp_per_pcs),0)::numeric value from(
  select root_lot_id,sum(units)::numeric units from component_entries group by root_lot_id)x
 join erp.hpp_versions h on h.lot_id=x.root_lot_id and h.is_current
), sold as(
 select coalesce(sum(c.component_units*h.hpp_per_pcs),0)::numeric value
 from cp7_sku_conversion.sale_allocation_components_v2 c
 join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
 join erp.sales_headers s on s.id=v.sale_id and s.status in('POSTED','PARTIAL_PAID','PAID')
 join erp.fg_lots root on root.id=c.root_lot_id and root.po_id=p_po_id
 join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current
), returned as(
 select coalesce(sum(c.component_units*h.hpp_per_pcs),0)::numeric value
 from cp7_sku_conversion.sales_return_components_v2 c
 join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
 join erp.sales_returns r on r.id=v.return_id and r.status='POSTED'
 join erp.fg_lots root on root.id=c.root_lot_id and root.po_id=p_po_id
 join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current
), cents as(
 select b.qty,round(b.raw_total,2)::numeric hpp,round(o.value,2)::numeric fg,
  round(greatest(s.value-r.value,0),2)::numeric cogs from base b cross join owned o cross join sold s cross join returned r
)
select qty,hpp,fg,cogs,(hpp-fg-cogs)::numeric from cents
$function$
"""

def once(text,before,after,label):
    if text.count(before)!=1:raise ValueError('SKU_MOVAVG_CONSUMER_PREDECESSOR_CHANGED:'+label)
    return text.replace(before,after,1)

def many(text,before,after,count,label):
    if text.count(before)!=count:raise ValueError('SKU_MOVAVG_CONSUMER_PREDECESSOR_CHANGED:'+label)
    return text.replace(before,after)

def first(text,before,after,count,label):
    if text.count(before)!=count:raise ValueError('SKU_MOVAVG_CONSUMER_PREDECESSOR_CHANGED:'+label)
    return text.replace(before,after,1)

def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('SKU_MOVAVG_EXACT_CONSUMER_FOUR_REQUIRED')
    result={}

    sig=SIGNATURES[0];text=originals[sig]
    text=first(text,
      "  for r in\n    select distinct fl.product_id",
      "  perform cp7_sku_conversion.prepare_sale_values_v2(h.id);\n\n  for r in\n    select distinct fl.product_id",
      3,'sale prepare before every economic scope')
    text=once(text,
      "  update erp.sale_stock_allocations a\n  set unit_hpp_snapshot=coalesce(erp.lock_current_hpp_per_pcs(a.lot_id),0)",
      "  update erp.sale_stock_allocations a\n  set unit_hpp_snapshot=cp7_sku_conversion.sale_allocation_unit_v2(a.id,a.lot_id)",
      'sale exact allocation snapshots')
    sale_nonpo_old="""    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id"""
    sale_nonpo_new="""    select distinct v.product_id
    from cp7_sku_conversion.sale_allocation_attributions_v2 a
    join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
    where v.sale_id=h.id and a.po_id is null
    order by v.product_id"""
    text=many(text,sale_nonpo_old,sale_nonpo_new,3,'sale nonpo economic scopes')
    sale_po_old="""    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null
    order by fl.po_id"""
    sale_po_new="""    select distinct a.po_id
    from cp7_sku_conversion.sale_allocation_attributions_v2 a
    join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
    where v.sale_id=h.id and a.po_id is not null
    order by a.po_id"""
    text=many(text,sale_po_old,sale_po_new,2,'sale PO economic scopes')
    result[sig]=text

    sig=SIGNATURES[1];text=originals[sig]
    text=first(text,
      "  for r in\n    select distinct fl.product_id",
      "  perform cp7_sku_conversion.prepare_return_values_v2(h.id);\n\n  for r in\n    select distinct fl.product_id",
      3,'return prepare before every economic scope')
    text=once(text,
      "    v_unit_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.lot_id),v_original_hpp);",
      "    v_unit_hpp:=cp7_sku_conversion.return_item_unit_v2(r.id,r.lot_id,v_original_hpp);",
      'return exact item snapshot')
    return_nonpo_old="""    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id"""
    return_nonpo_new="""    select distinct v.product_id
    from cp7_sku_conversion.sales_return_attributions_v2 a
    join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
    where v.return_id=h.id and a.po_id is null
    order by v.product_id"""
    text=many(text,return_nonpo_old,return_nonpo_new,3,'return nonpo economic scopes')
    return_po_old="""    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id"""
    return_po_new="""    select distinct a.po_id
    from cp7_sku_conversion.sales_return_attributions_v2 a
    join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
    where v.return_id=h.id and a.po_id is not null order by a.po_id"""
    text=many(text,return_po_old,return_po_new,2,'return PO economic scopes')
    result[sig]=text

    sig=SIGNATURES[2];text=originals[sig]
    if text.count('CREATE OR REPLACE FUNCTION erp.compute_non_po_product_hpp_targets_v2620f')!=1 or 'with lots as('not in text:
        raise ValueError('SKU_MOVAVG_CONSUMER_PREDECESSOR_CHANGED:nonpo target body')
    text=NONPO_TARGET
    result[sig]=text

    sig=SIGNATURES[3];text=originals[sig]
    if text.count('CREATE OR REPLACE FUNCTION erp.compute_po_hpp_gl_targets_v2620d')!=1 or 'with base as('not in text:
        raise ValueError('SKU_MOVAVG_CONSUMER_PREDECESSOR_CHANGED:po target body')
    text=PO_TARGET
    result[sig]=text

    sig=SIGNATURES[4];text=originals[sig]
    text=once(text,
      "  v_lines jsonb:='[]'::jsonb;",
      "  v_lines jsonb:='[]'::jsonb;\n  v_scope record;v_guard text:=coalesce(current_setting('cp7.sku_nonpo_sync_expanding',true),'');",
      'nonpo sync scope declarations')
    text=once(text,
      "  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));\n  if nullif(btrim(p_trigger_source_type),'') is null",
      "  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));\n  if v_guard<>'1'then\n   perform set_config('cp7.sku_nonpo_sync_expanding','1',true);\n   for v_scope in select distinct e.product_id from cp7_sku_conversion.component_events_v2 e\n    join erp.fg_lots root on root.id=e.root_lot_id and root.po_id is null and root.product_id=p_product_id\n    where e.product_id<>p_product_id order by e.product_id loop\n    perform erp.sync_non_po_product_hpp_to_gl_v2620f(v_scope.product_id,p_effective_date,p_trigger_source_type,p_trigger_source_id,p_reason);\n   end loop;\n   for v_scope in\n    with related_sales as(select distinct v.sale_id from cp7_sku_conversion.sale_allocation_components_v2 c\n      join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)\n      join erp.fg_lots root on root.id=c.root_lot_id and root.po_id is null and root.product_id=p_product_id),\n    related_returns as(select distinct v.return_id from cp7_sku_conversion.sales_return_components_v2 c\n      join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)\n      join erp.fg_lots root on root.id=c.root_lot_id and root.po_id is null and root.product_id=p_product_id),\n    scopes as(\n      select c.po_id from cp7_sku_conversion.sale_allocation_components_v2 c join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)\n       where v.sale_id in(select sale_id from related_sales)\n      union select c.po_id from cp7_sku_conversion.sales_return_components_v2 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)\n       where v.return_id in(select return_id from related_returns)\n      union select c2.po_id from cp7_sku_conversion.valuation_contributors_v2 c1\n       join erp.fg_lots root on root.id=c1.root_lot_id and root.po_id is null and root.product_id=p_product_id\n       join cp7_sku_conversion.valuation_contributors_v2 c2 using(group_id))\n    select distinct po_id from scopes where po_id is not null order by po_id\n   loop\n    perform erp.sync_po_hpp_to_gl(v_scope.po_id,p_effective_date);\n   end loop;\n   perform set_config('cp7.sku_nonpo_sync_expanding',v_guard,true);\n  end if;\n  if nullif(btrim(p_trigger_source_type),'') is null",
      'nonpo recost component scopes')
    result[sig]=text

    sig=SIGNATURES[5];text=originals[sig]
    text=once(text,
      "  v_cap date;v_end date;v_sf numeric(24,6):=0;v_sc numeric(24,6):=0;v_so numeric(24,6):=0;v_caller date:=p_effective_date;",
      "  v_cap date;v_end date;v_sf numeric(24,6):=0;v_sc numeric(24,6):=0;v_so numeric(24,6):=0;v_caller date:=p_effective_date;\n  v_scope record;v_guard text:=coalesce(current_setting('cp7.sku_po_sync_expanding',true),'');",
      'PO sync scope declarations')
    text=once(text,
      "  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));\n  select * into t from erp.compute_po_hpp_gl_targets_v2620d(p_po_id);",
      "  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));\n  if v_guard<>'1'then\n   perform set_config('cp7.sku_po_sync_expanding','1',true);\n   for v_scope in\n    with related_sales as(select distinct v.sale_id from cp7_sku_conversion.sale_allocation_components_v2 c\n      join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)where c.po_id=p_po_id),\n    related_returns as(select distinct v.return_id from cp7_sku_conversion.sales_return_components_v2 c\n      join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)where c.po_id=p_po_id),\n    scopes as(\n      select c.po_id from cp7_sku_conversion.sale_allocation_components_v2 c join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)\n       where v.sale_id in(select sale_id from related_sales)\n      union select c.po_id from cp7_sku_conversion.sales_return_components_v2 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)\n       where v.return_id in(select return_id from related_returns)\n      union select c2.po_id from cp7_sku_conversion.valuation_contributors_v2 c1 join cp7_sku_conversion.valuation_contributors_v2 c2 using(group_id)where c1.po_id=p_po_id)\n    select distinct po_id from scopes where po_id is not null and po_id<>p_po_id order by po_id\n   loop\n    perform erp.sync_po_hpp_to_gl(v_scope.po_id,p_effective_date);\n   end loop;\n   for v_scope in\n    with related_sales as(select distinct v.sale_id from cp7_sku_conversion.sale_allocation_components_v2 c\n      join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)where c.po_id=p_po_id),\n    related_returns as(select distinct v.return_id from cp7_sku_conversion.sales_return_components_v2 c\n      join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)where c.po_id=p_po_id),\n    scopes as(\n      select v.product_id from cp7_sku_conversion.sale_allocation_components_v2 c join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)\n       where c.po_id is null and v.sale_id in(select sale_id from related_sales)\n      union select v.product_id from cp7_sku_conversion.sales_return_components_v2 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)\n       where c.po_id is null and v.return_id in(select return_id from related_returns))\n    select distinct product_id from scopes order by product_id\n   loop\n    perform erp.sync_non_po_product_hpp_to_gl_v2620f(v_scope.product_id,p_effective_date,'SKU_COMPONENT_SCOPE',p_po_id,'Mixed PO/non-PO component redistribution');\n   end loop;\n   perform set_config('cp7.sku_po_sync_expanding',v_guard,true);\n  end if;\n  select * into t from erp.compute_po_hpp_gl_targets_v2620d(p_po_id);",
      'PO mixed component scopes')
    result[sig]=text
    return result
