"""Current target and independent credit-proof additions for sourced costs.

The canonical credit target reads raw rows directly. It never reads the Native
target or its cost-scope helper. Native permission/book/date checks stay intact.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
from valuation_delta import Derivation

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'cp7_sku_moving_average'
PINS={'consumer_delta.py':'958dd155969a85c75ed78b5d9bb4853f7c262739b91fc8bcdcdb3fff1fa6fa8a',
      'credit_delta.py':'40db04666d22bd619cdba2a7e3e44b848ca55d8d73cf880f3ead7a9f1cf74945',
      'private_delta.py':'e57e89f8291a7b62ce1584b4f30b4927dadac9b5bbb17feefe1c97c6c8f4218e'}


def parent(name):
    path=PARENT/name
    if sha256(path.read_bytes()).hexdigest()!=PINS[name]:raise ValueError('SKU_COST_FINANCIAL_PARENT_CHANGED:'+name)
    spec=importlib.util.spec_from_file_location('cost_parent_'+path.stem,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def expand_component_relations(d):
    """Expand only component source relations used for economic lock/sync scope."""
    for old,cost,key in(
        ('sale_allocation_components_v2','sale_cost_components_v3','sale_stock_allocation_id'),
        ('sales_return_components_v2','return_cost_components_v3','sales_return_item_id'),
        ('valuation_contributors_v2','cost_contributors_v3','group_id')):
        token='cp7_sku_conversion.'+old+' '
        count=d.source.count(token)
        if count:
            replacement='(select '+key+',root_lot_id,po_id from cp7_sku_conversion.'+old+\
                ' union all select '+key+',root_lot_id,po_id from cp7_sku_conversion.'+cost+') '
            d.many(token,replacement,count,'economic scope '+old)
    token='cp7_sku_conversion.component_events_v2 e'
    count=d.source.count(token)
    if count:d.many(token,'(select product_id,root_lot_id,source_type from cp7_sku_conversion.component_events_v2 union all select product_id,root_lot_id,source_type from cp7_sku_conversion.cost_events_v3)e',count,'economic source cost event scope')


def derive_consumers(originals):
    previous=parent('consumer_delta.py').patched(originals);result={};routes={}
    for sig,source in previous.items():
        d=Derivation(source)
        if sig=='erp.compute_non_po_product_hpp_targets_v2620f(uuid)':
            d.once('round(n.value+a.value,2)::numeric hpp',"round(n.value+a.value+cp7_sku_conversion.cost_scope_value_v3(p_product_id,null,'CONVERSION'),2)::numeric hpp",'retain all owned converted cost in source total')
            d.once('s.value+ls.value-r.value-lr.value',"s.value+ls.value-r.value-lr.value+cp7_sku_conversion.cost_scope_value_v3(p_product_id,null,'SOLD')-cp7_sku_conversion.cost_scope_value_v3(p_product_id,null,'RETURNED')",'current nonpo sold cost')
        elif sig=='erp.compute_po_hpp_gl_targets_v2620d(uuid)':
            d.once('s.value+ls.value-r.value-lr.value',"s.value+ls.value-r.value-lr.value+cp7_sku_conversion.cost_scope_value_v3(null,p_po_id,'SOLD')-cp7_sku_conversion.cost_scope_value_v3(null,p_po_id,'RETURNED')",'current PO sold cost, original PO source total unchanged')
        elif sig in('erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)','erp.sync_po_hpp_to_gl(uuid,date)'):
            expand_component_relations(d)
        if d.inverse()!=source:raise ValueError('SKU_COST_CONSUMER_DERIVATION_NOT_REVERSIBLE:'+sig)
        result[sig]=d.source;routes[sig]=[x[2]for x in d.routes]
    return result,routes


RAW_COSTS=""" ),cost_owned_entries as(
  select e.product_id,e.root_lot_id,e.source_type,e.units_delta units from cp7_sku_conversion.cost_events_v3 e
  where(e.source_type<>'SALE'or exists(select 1 from erp.sales_headers h where h.id=e.source_id and h.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')))
   and(e.source_type<>'SALES_RETURN'or exists(select 1 from erp.sales_returns h where h.id=e.source_id and h.status in('POSTED','REVERSED')))
 ),cost_owned as(
  select coalesce(sum(e.units*erp.be_allocation_extra_v1(a.id)/a.qty_pcs),0)::numeric amount,
   coalesce(sum(e.units*erp.be_allocation_extra_v1(a.id)/a.qty_pcs)filter(where p_po is null and e.source_type='SKU_CONVERSION'),0)::numeric converted
  from cost_owned_entries e join erp.fg_lots l on l.id=e.root_lot_id
  join erp.product_conversion_allocations a on a.destination_lot_id=l.id
  where(p_po is null and l.po_id is null and e.product_id=p_product)or l.po_id=p_po
 ),cost_sold_entries as(
  select v.product_id,c.root_lot_id,c.component_units units from cp7_sku_conversion.sale_cost_components_v3 c
  join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
  join erp.sales_headers h on h.id=v.sale_id and h.status in('POSTED','PARTIAL_PAID','PAID')
  union all select v.product_id,c.root_lot_id,-c.component_units from cp7_sku_conversion.return_cost_components_v3 c
  join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
  join erp.sales_returns h on h.id=v.return_id and h.status='POSTED'
 ),cost_net_sold as(
  select coalesce(sum(e.units*erp.be_allocation_extra_v1(a.id)/a.qty_pcs),0)::numeric amount
  from cost_sold_entries e join erp.fg_lots l on l.id=e.root_lot_id
  join erp.product_conversion_allocations a on a.destination_lot_id=l.id
  where(p_po is null and l.po_id is null and e.product_id=p_product)or l.po_id=p_po
 ),raw_values as("""

SUPPORT="""  union all select 'SKU_COST_EVENT',e.id::text,jsonb_build_object('event',to_jsonb(e),'sale_status',sh.status,'return_status',rh.status)
   from cp7_sku_conversion.cost_events_v3 e left join erp.sales_headers sh on e.source_type='SALE'and sh.id=e.source_id
   left join erp.sales_returns rh on e.source_type='SALES_RETURN'and rh.id=e.source_id where e.root_lot_id in(select id from lots)
  union all select 'SKU_SALE_COST',c.sale_stock_allocation_id::text||':'||c.root_lot_id::text,
   jsonb_build_object('component',to_jsonb(c),'value',to_jsonb(v),'sale',to_jsonb(h))
   from cp7_sku_conversion.sale_cost_components_v3 c join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
   join erp.sales_headers h on h.id=v.sale_id where c.root_lot_id in(select id from lots)
  union all select 'SKU_RETURN_COST',c.sales_return_item_id::text||':'||c.root_lot_id::text,
   jsonb_build_object('component',to_jsonb(c),'value',to_jsonb(v),'return',to_jsonb(h))
   from cp7_sku_conversion.return_cost_components_v3 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
   join erp.sales_returns h on h.id=v.return_id where c.root_lot_id in(select id from lots)
  union all select 'SKU_COST_CONTRIBUTOR',c.group_id::text||':'||c.root_lot_id::text,to_jsonb(c)
   from cp7_sku_conversion.cost_contributors_v3 c where c.root_lot_id in(select id from lots)
"""


def derive_credit(originals):
    previous=parent('credit_delta.py').patched(originals);result={};routes={}
    for sig,source in previous.items():
        d=Derivation(source)
        if sig=='cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)':
            d.once("cross join lateral cp7_sku_conversion.return_components_v2(a.id,(x->>'qty_pcs')::numeric,null)c",
                "cross join lateral(select 'BASE'::text kind,*from cp7_sku_conversion.return_components_v2(a.id,(x->>'qty_pcs')::numeric,null)\n   union all select 'COST',*from cp7_sku_conversion.return_cost_components_v3(a.id,(x->>'qty_pcs')::numeric,null))c",'independent hypothetical return includes sourced costs')
            d.once(' ),raw_values as(',RAW_COSTS,'independent raw current cost source quantities')
            d.once('(select amount from conversion_adjustment)hpp','(select amount from conversion_adjustment)+(select converted from cost_owned)hpp','independent nonpo total')
            d.once('(select amount from owned)+case','(select amount from owned)+(select amount from cost_owned)+case','independent owned cost')
            d.once('(select amount from net_sold)-case','(select amount from net_sold)+(select amount from cost_net_sold)-case','independent sold cost')
        elif sig=='cp7_credit.initial_hpp_projection_v1(jsonb)':
            old="cross join lateral cp7_sku_conversion.return_components_v2(planned_allocation.id,(planned_item.value->>'qty_pcs')::numeric,null)c;"
            new="cross join lateral(select 'BASE'::text kind,*from cp7_sku_conversion.return_components_v2(planned_allocation.id,(planned_item.value->>'qty_pcs')::numeric,null)\n  union all select 'COST',*from cp7_sku_conversion.return_cost_components_v3(planned_allocation.id,(planned_item.value->>'qty_pcs')::numeric,null))c;"
            d.many(old,new,2,'cost plan before locks and fresh reread after wait')
            d.many("'po_id',c.po_id,'component_units',c.component_units", "'component_kind',c.kind,'po_id',c.po_id,'component_units',c.component_units",2,'sealed cost identity')
            d.many('order by planned_allocation.id,c.root_lot_id','order by planned_allocation.id,c.kind,c.root_lot_id',2,'deterministic combined plans')
        elif sig=='cp7_credit.initial_hpp_support_v1(uuid,uuid)':
            d.once("  union all select 'RESIDUAL_CLOSE'",SUPPORT+"  union all select 'RESIDUAL_CLOSE'",'complete immutable cost source proof')
        if d.inverse()!=source:raise ValueError('SKU_COST_CREDIT_DERIVATION_NOT_REVERSIBLE:'+sig)
        result[sig]=d.source;routes[sig]=[x[2]for x in d.routes]
    return result,routes
