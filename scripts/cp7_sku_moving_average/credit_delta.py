"""Bind retained credit HPP proofs to current SKU components without bypasses.

All four inputs must equal the retained Native definitions. Authority, account,
period, physical allocation, actual book and actual journal guards are retained.
The targets below derive current and hypothetical values from raw source rows;
they never substitute the Native target for the independent canonical proof.
"""
from hashlib import sha256

ORIGINAL_SHA256={'cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)': '6d9dfbd46bf06f21664fcdc3580367473fc20458aea050e41d73d9b0b23e5fb1', 'cp7_credit.initial_hpp_projection_v1(jsonb)': '8221158e00e1b9c27b273fae189f1960c9ea56ec964fd38ac1d942ac91aa186b', 'cp7_credit.initial_hpp_support_v1(uuid,uuid)': 'd866ba785052832d2e98e2ef045a298b12d3ec2c1090c1aa2eb358778d2f3dcd', 'cp7_credit.initial_opening_hpp_source_v1(uuid,uuid)': 'd2847d50918acfd012c5c0a21ebb0942e159086add28332486debad12d417cc6'}
SIGNATURES=tuple(ORIGINAL_SHA256)

TARGET="""CREATE OR REPLACE FUNCTION cp7_credit.initial_hpp_targets_v1(p_product uuid, p_po uuid, p_items jsonb, p_after boolean)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
 with requested as(
  select (x->>'lot_id')::uuid lot_id,sum((x->>'qty_pcs')::numeric)qty
  from jsonb_array_elements(p_items)x group by (x->>'lot_id')::uuid
 ),lot_source as(
  select fl.id lot_id,fl.product_id,fl.po_id,fl.lot_origin,fl.initial_qty_pcs,
   to_jsonb(fl)lot_source,to_jsonb(hv)hpp_source,
   case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric unit_raw,
   case when p_po is not null then case when fl.lot_origin='PRODUCTION' then coalesce(hv.total_cost,0)else 0 end
    else (case when fl.lot_origin<>'CONVERSION'or exists(select 1 from erp.product_conversion_allocations a
      join erp.product_conversions c on c.id=a.conversion_id where a.destination_lot_id=fl.id and c.status='POSTED')
      then coalesce(hv.total_cost,0)else 0 end)-coalesce((select sum(a.qty_pcs*(hv.total_cost/nullif(hv.qty_basis_pcs,0)))
       from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id
       where a.source_lot_id=fl.id and c.status='POSTED'),0)end::numeric raw_total
  from erp.fg_lots fl left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where (p_po is not null and fl.po_id=p_po and fl.lot_origin in('PRODUCTION','CONVERSION'))
   or(p_po is null and fl.po_id is null and fl.product_id=p_product and fl.lot_origin<>'VOIDED_PRODUCTION')
 ),facts as(
  select l.*,coalesce(q.qty,0)::numeric requested_qty,m.owned_qty,s.sold_qty,r.returned_qty,
   (m.owned_qty+case when p_after then coalesce(q.qty,0)else 0 end)::numeric owned_after,
   (s.sold_qty-r.returned_qty-case when p_after then coalesce(q.qty,0)else 0 end)::numeric net_sold_after
  from lot_source l left join requested q on q.lot_id=l.lot_id
  cross join lateral(select(coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed))filter(
   where m.movement_type='SALE_RESERVE'and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),0))::numeric owned_qty
   from erp.fg_stock_movements m where m.lot_id=l.lot_id)m
  cross join lateral(select coalesce(sum(a.qty_pcs),0)::numeric sold_qty from erp.sale_stock_allocations a
   join erp.sales_items i on i.id=a.sale_item_id join erp.sales_headers h on h.id=i.sale_id
   where a.lot_id=l.lot_id and h.status in('POSTED','PARTIAL_PAID','PAID'))s
  cross join lateral(select coalesce(sum(i.qty_pcs),0)::numeric returned_qty from erp.sales_return_items i
   join erp.sales_returns h on h.id=i.return_id where i.lot_id=l.lot_id and h.status='POSTED')r
 ),extra as(select case when p_po is null then 0 else erp.be_po_extra_v1(p_po)end::numeric amount),
 requested_components as(
  select si.product_id,c.* from jsonb_array_elements(p_items)x
  join erp.sale_stock_allocations a on a.id=(x->>'allocation_id')::uuid join erp.sales_items si on si.id=a.sale_item_id
  cross join lateral cp7_sku_conversion.return_components_v2(a.id,(x->>'qty_pcs')::numeric,null)c
 ),addition as(
  select coalesce(sum(c.component_units*c.hpp_per_pcs),0)::numeric amount from requested_components c
  where(p_po is null and c.po_id is null and c.product_id=p_product)or c.po_id=p_po
 ),physical as(
  select l.id root_lot_id,(coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed))filter(
   where m.movement_type='SALE_RESERVE'and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),0))::numeric units
  from erp.fg_lots l left join erp.fg_stock_movements m on m.lot_id=l.id
  where((p_po is null and l.po_id is null and l.product_id=p_product)or l.po_id=p_po)
   and l.lot_origin<>'VOIDED_PRODUCTION'group by l.id
 ),owned_entries as(
  select root_lot_id,units from physical
  union all select e.root_lot_id,e.units_delta from cp7_sku_conversion.component_events_v2 e join erp.fg_lots l on l.id=e.root_lot_id
  where((p_po is null and l.po_id is null and e.product_id=p_product)or l.po_id=p_po)
   and(e.source_type<>'SALE'or exists(select 1 from erp.sales_headers h where h.id=e.source_id and h.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')))
   and(e.source_type<>'SALES_RETURN'or exists(select 1 from erp.sales_returns h where h.id=e.source_id and h.status in('POSTED','REVERSED')))
 ),owned as(
  select coalesce(sum(e.units*h.hpp_per_pcs),0)::numeric amount from owned_entries e
  join erp.hpp_versions h on h.lot_id=e.root_lot_id and h.is_current
 ),conversion_adjustment as(
  select coalesce(sum(e.units_delta*h.hpp_per_pcs),0)::numeric amount from cp7_sku_conversion.component_events_v2 e
  join erp.fg_lots l on l.id=e.root_lot_id and l.po_id is null join erp.hpp_versions h on h.lot_id=l.id and h.is_current
  where p_po is null and e.product_id=p_product and e.source_type='SKU_CONVERSION'
 ),net_sold_entries as(
  select c.root_lot_id,c.component_units units from cp7_sku_conversion.sale_allocation_components_v2 c
  join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
  join erp.sales_headers sh on sh.id=v.sale_id and sh.status in('POSTED','PARTIAL_PAID','PAID')join erp.fg_lots l on l.id=c.root_lot_id
  where(p_po is null and l.po_id is null and v.product_id=p_product)or l.po_id=p_po
  union all select c.root_lot_id,-c.component_units from cp7_sku_conversion.sales_return_components_v2 c
  join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
  join erp.sales_returns rh on rh.id=v.return_id and rh.status='POSTED'join erp.fg_lots l on l.id=c.root_lot_id
  where(p_po is null and l.po_id is null and v.product_id=p_product)or l.po_id=p_po
  union all select a.lot_id,a.qty_pcs::numeric from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
  join erp.sales_headers sh on sh.id=i.sale_id and sh.status in('POSTED','PARTIAL_PAID','PAID')join erp.fg_lots l on l.id=a.lot_id
  where((p_po is null and l.po_id is null and l.product_id=p_product)or l.po_id=p_po)
   and not exists(select 1 from cp7_sku_conversion.sale_allocation_values_v2 v where v.sale_stock_allocation_id=a.id)
  union all select i.lot_id,-i.qty_pcs::numeric from erp.sales_return_items i
  join erp.sales_returns rh on rh.id=i.return_id and rh.status='POSTED'join erp.fg_lots l on l.id=i.lot_id
  where((p_po is null and l.po_id is null and l.product_id=p_product)or l.po_id=p_po)
   and not exists(select 1 from cp7_sku_conversion.sales_return_values_v2 v where v.sales_return_item_id=i.id)
 ),net_sold as(
  select coalesce(sum(e.units*h.hpp_per_pcs),0)::numeric amount from net_sold_entries e
  join erp.hpp_versions h on h.lot_id=e.root_lot_id and h.is_current
 ),raw_values as(
  select (select coalesce(sum(raw_total),0)from facts)+(select amount from extra)+(select amount from conversion_adjustment)hpp,
   (select amount from owned)+case when p_after then(select amount from addition)else 0 end fg,
   (select amount from net_sold)-case when p_after then(select amount from addition)else 0 end cogs
 ),cents as(select round(hpp,2)::numeric hpp,round(fg,2)::numeric fg,round(greatest(cogs,0),2)::numeric cogs from raw_values),
 target as(select hpp hpp_total_cost,fg fg_value,cogs cogs_value,(hpp-fg-cogs)::numeric other_out_value from cents
 )select jsonb_build_object('target',to_jsonb(t)||case when p_po is null then'{}'::jsonb else jsonb_build_object(
   'base_output_qty',(select coalesce(sum(initial_qty_pcs),0)from facts where lot_origin='PRODUCTION'))end,
  'lots',(select coalesce(jsonb_agg(to_jsonb(f)order by f.lot_id),'[]')from facts f),
  'economic_return_components',(select coalesce(jsonb_agg(to_jsonb(c)order by c.product_id,c.root_lot_id),'[]')from requested_components c),
  'po_extra',(select amount from extra),'conversions',(select coalesce(jsonb_agg(jsonb_build_object(
   'allocation',to_jsonb(a),'conversion',to_jsonb(c))order by a.id),'[]')from erp.product_conversion_allocations a
   join erp.product_conversions c on c.id=a.conversion_id where a.source_lot_id in(select lot_id from facts)
    or a.destination_lot_id in(select lot_id from facts)))from target t
$function$
"""

PLAN=""" select coalesce(jsonb_agg(jsonb_build_object('allocation_id',planned_allocation.id,'product_id',si.product_id,'root_lot_id',c.root_lot_id,
  'po_id',c.po_id,'component_units',c.component_units,'hpp_per_pcs',c.hpp_per_pcs,'hpp_version_id',c.hpp_version_id)
  order by planned_allocation.id,c.root_lot_id),'[]')into component_plan from jsonb_array_elements(p_legacy->'items')as planned_item(value)
  join erp.sale_stock_allocations planned_allocation on planned_allocation.id=(planned_item.value->>'allocation_id')::uuid join erp.sales_items si on si.id=planned_allocation.sale_item_id
  cross join lateral cp7_sku_conversion.return_components_v2(planned_allocation.id,(planned_item.value->>'qty_pcs')::numeric,null)c;
"""
SCOPES=""" select coalesce(jsonb_agg(z order by z->>'po_id',z->>'product_id'),'[]')into scope_items from(
  select distinct jsonb_build_object('product_id',case when fl.po_id is null then si.product_id end,'po_id',fl.po_id)z
  from jsonb_array_elements(p_legacy->'items')as planned_item(value) join erp.sale_stock_allocations planned_allocation on planned_allocation.id=(planned_item.value->>'allocation_id')::uuid
  join erp.sales_items si on si.id=planned_allocation.sale_item_id join erp.fg_lots fl on fl.id=planned_allocation.lot_id
  union select distinct jsonb_build_object('product_id',case when planned_item.value->>'po_id'is null then(planned_item.value->>'product_id')::uuid end,'po_id',(planned_item.value->>'po_id')::uuid)
   from jsonb_array_elements(component_plan)as planned_item(value))s;
 select coalesce(array_agg(distinct id order by id),'{}'::uuid[])into pos from(
  select unnest(pos)id union select(planned_item.value->>'po_id')::uuid from jsonb_array_elements(scope_items)as planned_item(value) where planned_item.value->>'po_id'is not null)s;
"""
LOTS=""" select coalesce(array_agg(distinct id order by id),'{}'::uuid[])into lots from(
  select id from erp.fg_lots where product_id=any(products)or po_id=any(pos)
  union select unnest(cp7_sku_conversion.hpp_scope_lot_ids_v2((planned_item.value->>'product_id')::uuid,(planned_item.value->>'po_id')::uuid))
   from jsonb_array_elements(scope_items)as planned_item(value))s;"""
SUPPORT_EXTRA="""  union all select 'SKU_COMPONENT_EVENT',e.id::text,jsonb_build_object('event',to_jsonb(e),'sale_status',sh.status,'return_status',rh.status)
   from cp7_sku_conversion.component_events_v2 e left join erp.sales_headers sh on e.source_type='SALE'and sh.id=e.source_id
   left join erp.sales_returns rh on e.source_type='SALES_RETURN'and rh.id=e.source_id where e.root_lot_id in(select id from lots)
  union all select 'SKU_SALE_COMPONENT',c.sale_stock_allocation_id::text||':'||c.root_lot_id::text,
   jsonb_build_object('component',to_jsonb(c),'value',to_jsonb(v),'sale',to_jsonb(h))
   from cp7_sku_conversion.sale_allocation_components_v2 c join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
   join erp.sales_headers h on h.id=v.sale_id where c.root_lot_id in(select id from lots)
  union all select 'SKU_RETURN_COMPONENT',c.sales_return_item_id::text||':'||c.root_lot_id::text,
   jsonb_build_object('component',to_jsonb(c),'value',to_jsonb(v),'return',to_jsonb(h))
   from cp7_sku_conversion.sales_return_components_v2 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
   join erp.sales_returns h on h.id=v.return_id where c.root_lot_id in(select id from lots)
  union all select 'SKU_CONTRIBUTOR',c.group_id::text||':'||c.root_lot_id::text,to_jsonb(c)
   from cp7_sku_conversion.valuation_contributors_v2 c where c.root_lot_id in(select id from lots)
"""

def once(source, before, after, label):
    if source.count(before)!=1:raise ValueError('SKU_MOVAVG_CREDIT_PREDECESSOR_CHANGED:'+label)
    return source.replace(before,after,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('SKU_MOVAVG_EXACT_CREDIT_SET_REQUIRED')
    for sig,source in originals.items():
        if sha256(source.encode()).hexdigest()!=ORIGINAL_SHA256[sig]:
            raise ValueError('SKU_MOVAVG_CREDIT_PREDECESSOR_CHANGED:'+sig)
    result={SIGNATURES[0]:TARGET}
    source=originals[SIGNATURES[1]]
    source=once(source,' delta_fg numeric;'," component_plan jsonb;fresh_component_plan jsonb;scope_items jsonb;\n delta_fg numeric;",'plan-declarations')
    source=once(source," pos:=coalesce(pos,'{}'::uuid[]);", " pos:=coalesce(pos,'{}'::uuid[]);\n"+PLAN+SCOPES,'component-plan-before-locks')
    old=" select coalesce(array_agg(id order by id),'{}'::uuid[])into lots from erp.fg_lots where product_id=any(products)or po_id=any(pos);"
    source=once(source,old,LOTS,'root-lock-closure')
    source=once(source,old.replace('into lots','into fresh_lots'),LOTS.replace('into lots','into fresh_lots'),'fresh-root-closure')
    source=once(source,' if fresh_lots is distinct from lots or fresh_versions is distinct from versions then',
        PLAN.replace('into component_plan','into fresh_component_plan')+' if component_plan is distinct from fresh_component_plan or fresh_lots is distinct from lots or fresh_versions is distinct from versions then','fresh-plan-after-wait')
    source=once(source,"  (z->>'po_id')::uuid po_id from jsonb_array_elements(items)z", "  (z->>'po_id')::uuid po_id from jsonb_array_elements(scope_items)z",'economic-financial-groups')
    source=once(source,"  'locked_lot_ids',to_jsonb(lots)","  'economic_return_components',component_plan,'locked_lot_ids',to_jsonb(lots)",'sealed-component-plan')
    result[SIGNATURES[1]]=source
    source=originals[SIGNATURES[2]]
    before=" with lots as(select fl.id from erp.fg_lots fl where(p_po is not null and fl.po_id=p_po)\n  or(p_po is null and fl.po_id is null and fl.product_id=p_product))"
    source=once(source,before," with lots as(select unnest(cp7_sku_conversion.hpp_scope_lot_ids_v2(p_product,p_po))id)",'support-root-closure')
    source=once(source,"  union all select 'RESIDUAL_CLOSE'",SUPPORT_EXTRA+"  union all select 'RESIDUAL_CLOSE'",'component-provenance')
    result[SIGNATURES[2]]=source
    source=originals[SIGNATURES[3]]
    source=once(source,"  and((p_po is null and l.po_id is null and l.product_id=p_product)or(p_po is not null and l.po_id=p_po))",
        "  and l.id=any(cp7_sku_conversion.hpp_scope_lot_ids_v2(p_product,p_po))",'opening-root-provenance')
    result[SIGNATURES[3]]=source
    return result
