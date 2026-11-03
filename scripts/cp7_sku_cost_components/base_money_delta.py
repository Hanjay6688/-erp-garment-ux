"""Exact reversible base-cent bindings; existing Native guards remain intact."""
from hashlib import sha256
from pathlib import Path
import re
try:from .valuation_delta import Derivation,PARENT,PARENT_SHA256
except ImportError:from valuation_delta import Derivation,PARENT,PARENT_SHA256

HERE=Path(__file__).resolve().parent


def definitions(valuation,consumers,credit):
    raw=PARENT.read_bytes()
    if sha256(raw).hexdigest()!=PARENT_SHA256:raise ValueError('BASE_MONEY_PARENT_VALUATION_CHANGED')
    originals={m.group(1):m.group(0)for m in re.finditer(r'(?ms)^create function ([^\s(]+)\([\s\S]*?\$\$;\n',raw.decode())}
    result=dict(valuation);routes={}
    def apply(name,edits):
        before=result.get(name,originals.get(name));d=Derivation(before)
        for old,new,label in edits:d.once(old,new,label)
        if d.inverse()!=before:raise ValueError('BASE_MONEY_VALUATION_NOT_REVERSIBLE:'+name)
        result[name]=d.source.replace('create function ','create or replace function ',1)
        routes[name]=[r[2]for r in d.routes]
    pool_unit="(case when h.id is null or h.cost_state='ESTIMATED'then h.hpp_per_pcs else cp7_sku_conversion.base_current_unit_v4(t.root_lot_id,p_product)end)"
    apply('cp7_sku_conversion.pool_components_v2',[
        ('h.hpp_per_pcs unit_value',pool_unit+'unit_value','current owned base money; retain the original unknown-source refusal'),
        ('t.units*h.hpp_per_pcs','t.units*'+pool_unit,'pool uses the same cent owner')])
    apply('cp7_sku_conversion.owned_scope_value_v2',[
        ('sum(x.units*h.hpp_per_pcs)',"sum(x.units*cp7_sku_conversion.base_current_unit_v4(x.root_lot_id,p_product)\n +case when p_po is null then cp7_sku_conversion.base_transition_value_v4(x.root_lot_id,p_product)else 0 end)",
         'retain exact physical Native intermediate values only in owning execution context')])
    apply('cp7_sku_conversion.return_components_v2',[
        ('v_plan jsonb;v_legacy boolean;','v_plan jsonb;v_legacy boolean;v_product uuid;','original sale product for current base money'),
        ('select v.qty_pcs into v_sold','select v.qty_pcs,v.product_id into v_sold,v_product','capture the actual sale monetary owner'),
        ('if v_legacy then select a.qty_pcs into strict v_sold from erp.sale_stock_allocations a where a.id=p_allocation;end if;',
         'if v_legacy then select a.qty_pcs,l.product_id into strict v_sold,v_product from erp.sale_stock_allocations a join erp.fg_lots l on l.id=a.lot_id where a.id=p_allocation;end if;',
         'legacy return keeps its physical product'),
        ("'hpp_per_pcs',h.hpp_per_pcs", "'hpp_per_pcs',case when h.id is null or h.cost_state='ESTIMATED'then h.hpp_per_pcs else cp7_sku_conversion.base_current_unit_v4(p.root_lot_id,v_product)end",'return current monetary base after the unchanged unknown-root refusal')])
    apply('cp7_sku_conversion.prepare_return_values_v2',[
        ('sum(c.component_units*h.hpp_per_pcs)','sum(c.component_units*cp7_sku_conversion.base_current_unit_v4(c.root_lot_id,v.product_id))',
         'earlier items of the same return use current base custody')])
    apply('cp7_sku_conversion.pool_quote_v2',[
        ("'events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.recorded_at,e.id),'[]'::jsonb)from cp7_sku_conversion.valuation_events_v2 e",
         "'base_money',(select coalesce(jsonb_agg(to_jsonb(m)order by m.id),'[]')from cp7_sku_conversion.base_money_events_v4 m\n   where m.root_lot_id in(select root_lot_id from cp7_sku_conversion.pool_components_v2(p_product,p_location,p_grade))),\n  'events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.recorded_at,e.id),'[]'::jsonb)from cp7_sku_conversion.valuation_events_v2 e",
         'complete base monetary history is part of the source revision')])
    apply('cp7_sku_conversion.prepare_valuation_v2',[
        ('v_revision text;','v_revision text;v_enrolled jsonb;','enrollment must preserve the admitted preview value'),
        (' v_transfer:=round(v_qty*(s->>\'average\')::numeric,2);',
         """ perform cp7_sku_conversion.prepare_base_money_v4(p_preview);
 v_enrolled:=cp7_sku_conversion.pool_quote_v2((p_preview->>'source_product_id')::uuid,(p_preview->>'location_id')::uuid,'GRADE_A');
 if v_enrolled->'qty'is distinct from s->'qty'or v_enrolled->'value'is distinct from s->'value'
  or v_enrolled->'base_value'is distinct from s->'base_value'
  or round(v_qty*(v_enrolled->>'average')::numeric,2)is distinct from round(v_qty*(s->>'average')::numeric,2)then
  raise exception 'CP7_SKU_BASE_ENROLLMENT_PREVIEW_VALUE_CHANGED';end if;
 v_transfer:=round(v_qty*(s->>'average')::numeric,2);""",
         'enroll only known unused roots after the unchanged stale-preview check')])
    apply('cp7_sku_conversion.finalize_valuation_v2',[
        (' perform cp7_sku_conversion.finalize_costs_v3(p_group);',
         ' perform cp7_sku_conversion.transfer_base_money_v4(p_group,false);\n perform cp7_sku_conversion.finalize_costs_v3(p_group);',
         'pair base units and historical quoted cents after physical component posting')])
    apply('cp7_sku_conversion.reverse_valuation_v2',[
        (" insert into cp7_sku_conversion.component_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date,supersedes_event_id)",
         " perform cp7_sku_conversion.transfer_base_money_v4(p_group,true);\n insert into cp7_sku_conversion.component_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date,supersedes_event_id)",
         'current base monetary inverse immediately before original component inverse')])

    changed={}
    for sig,source in consumers.items():
        d=Derivation(source)
        if sig=='erp.compute_non_po_product_hpp_targets_v2620f(uuid)':
            d.once('round(n.value+a.value+', 'round(n.value+a.value+cp7_sku_conversion.base_scope_correction_v4(p_product_id)+',
                   'base monetary source correction preserves Native intermediate source accounting')
            d.many('c.component_units*h.hpp_per_pcs','c.component_units*cp7_sku_conversion.base_current_unit_v4(c.root_lot_id,v.product_id)',2,
                   'sold and returned base money retain their original economic product')
            d.once('a.qty_pcs*h.hpp_per_pcs','a.qty_pcs*cp7_sku_conversion.base_current_unit_v4(a.lot_id,p_product_id)',
                   'legacy sold base cost on the actual original product')
            d.once('i.qty_pcs*h.hpp_per_pcs','i.qty_pcs*cp7_sku_conversion.base_current_unit_v4(i.lot_id,p_product_id)',
                   'legacy returned base cost on the actual original product')
        elif sig=='erp.post_opening_hpp_correction(uuid,numeric,text,date)':
            d.once('v_scope record;','v_scope record;v_base_money_before jsonb;','base price proof declaration')
            d.once('  update erp.hpp_versions set is_current=false',
                   '  v_base_money_before:=cp7_sku_conversion.capture_base_price_v4(l.id);\n  update erp.hpp_versions set is_current=false',
                   'capture unchanged base ownership after all original Native preconditions')
            token="returning id into v_new_id;"
            d.once(token,token+'\n  perform cp7_sku_conversion.reprice_base_money_v4(l.id,p_effective_date,v_base_money_before);',
                   'new exact source cents before unchanged Native book and source reconciliation')
        if d.inverse()!=source:raise ValueError('BASE_MONEY_NATIVE_NOT_REVERSIBLE:'+sig)
        changed[sig]=d.source;routes[sig]=[r[2]for r in d.routes]
    independent,credit_routes=credit_definitions(credit);routes.update(credit_routes)
    return result,changed,independent,routes


def raw_unit(root,product,native):
    return """(case when p_po is null and exists(select 1 from cp7_sku_conversion.base_money_events_v4 bm where bm.root_lot_id=ROOT)
 then coalesce((select sum(bm.amount_delta)/nullif(sum(bm.units_delta),0)from cp7_sku_conversion.base_money_events_v4 bm
  where bm.root_lot_id=ROOT and bm.product_id=PRODUCT),0)else NATIVE end)""".replace('ROOT',root).replace('PRODUCT',product).replace('NATIVE',native)


RAW_BASE=""" ),base_roots as(
  select distinct e.root_lot_id from cp7_sku_conversion.base_money_events_v4 e
  where p_po is null and(e.product_id=p_product or e.root_lot_id in(select root_lot_id from requested_components where kind='BASE'))
 ),base_cells as(
  select e.root_lot_id,e.product_id,sum(e.units_delta)units,sum(e.amount_delta)amount
  from cp7_sku_conversion.base_money_events_v4 e where e.root_lot_id in(select root_lot_id from base_roots)
  group by e.root_lot_id,e.product_id
 ),base_raw_custody_entries as(
  select l.id root_lot_id,l.product_id,(l.initial_qty_pcs-coalesce((select sum(a.qty_pcs)from erp.product_conversion_allocations a
   join erp.product_conversions c on c.id=a.conversion_id where a.source_lot_id=l.id and c.status='POSTED'),0))::numeric units
  from erp.fg_lots l where l.id in(select root_lot_id from base_roots)
  union all select e.root_lot_id,e.product_id,e.units_delta from cp7_sku_conversion.component_events_v2 e
   where e.source_type='SKU_CONVERSION'and e.root_lot_id in(select root_lot_id from base_roots)
 ),base_raw_custody as(
  select root_lot_id,product_id,sum(units)units from base_raw_custody_entries group by root_lot_id,product_id
 ),base_integrity as(
  select(case when exists(select 1 from base_roots r left join erp.hpp_versions h on h.lot_id=r.root_lot_id and h.is_current
   left join erp.fg_lots l on l.id=r.root_lot_id
   where h.id is null or l.po_id is not null or l.lot_origin in('CONVERSION','VOIDED_PRODUCTION')or h.cost_state='ESTIMATED'
    or(select count(*)from cp7_sku_conversion.base_money_events_v4 e where e.root_lot_id=r.root_lot_id and e.kind='ORIGIN')<>1
    or(select sum(c.units)from base_cells c where c.root_lot_id=r.root_lot_id)is distinct from h.qty_basis_pcs
    or(select sum(c.amount)from base_cells c where c.root_lot_id=r.root_lot_id)is distinct from round(h.total_cost,2))
   or exists(select 1 from base_cells c full join base_raw_custody r using(root_lot_id,product_id)
    where coalesce(c.units,0)<>coalesce(r.units,0)or c.units<0 or c.amount<0 or(c.units=0 and c.amount<>0))
   then 'CP7_CREDIT_RAW_BASE_MONEY_NOT_EXACT'else '1'end)::numeric factor
 ),base_adjustment as(
  select coalesce(sum(c.amount-c.units*h.hpp_per_pcs),0)::numeric amount from base_cells c
  join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current where c.product_id=p_product and p_po is null
 ),raw_values as("""


def credit_definitions(credit):
    result={};routes={}
    for sig,source in credit.items():
        d=Derivation(source)
        if sig=='cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)':
            d.many('e.units*h.hpp_per_pcs','e.units*'+raw_unit('e.root_lot_id','p_product','h.hpp_per_pcs'),2,
                   'independent base-owned and sold amounts from raw monetary facts')
            d.once('sum(c.component_units*c.hpp_per_pcs),0)::numeric amount from requested_components c',
                   'sum(c.component_units*'+raw_unit('c.root_lot_id','c.product_id','h.hpp_per_pcs')+'),0)::numeric amount from requested_components c\n  join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current',
                   'hypothetical base return independent of official planned price')
            d.once(' ),raw_values as(',RAW_BASE,'independent full base-source and custody conservation')
            d.once('(select converted from cost_owned)hpp','(select converted from cost_owned)+(select amount from base_adjustment)hpp',
                   'independent exact base source-cent correction')
            d.once('hpp*(select factor from cost_monetary_integrity)',
                   'hpp*(select factor from cost_monetary_integrity)*(select factor from base_integrity)',
                   'require raw base custody before returning canonical credit targets')
        elif sig=='cp7_credit.initial_hpp_support_v1(uuid,uuid)':
            d.once("  union all select 'RESIDUAL_CLOSE'","  union all select 'SKU_BASE_MONEY_EVENT',e.id::text,to_jsonb(e)\n   from cp7_sku_conversion.base_money_events_v4 e where e.root_lot_id in(select id from lots)\n  union all select 'RESIDUAL_CLOSE'",
                   'seal every original base monetary fact with the source proof')
        if d.inverse()!=source:raise ValueError('BASE_MONEY_CREDIT_NOT_REVERSIBLE:'+sig)
        result[sig]=d.source;routes[sig]=[r[2]for r in d.routes]
    return result,routes
