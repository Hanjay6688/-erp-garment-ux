"""Reversibly connect current cent custody to every prepared cost consumer."""
from hashlib import sha256
from pathlib import Path
import re
from valuation_delta import Derivation

HERE=Path(__file__).resolve().parent
PINS={'costs.sql':'999ce0516366efb0a2cdc59e0c90b7edf99717dc387fa51f972934e287c1e6c1',
      'source_rebalance.sql':'7a9ab4a887fe92b82eeb003989418b5ab4da57607fccefc365b2f2445bade765'}


def originals(name):
    raw=(HERE/name).read_bytes()
    if sha256(raw).hexdigest()!=PINS[name]:raise ValueError('SKU_MONEY_ORIGINAL_CHANGED:'+name)
    return {m.group(1):m.group(0)for m in re.finditer(r'(?ms)^create function ([^\s(]+)\([\s\S]*?\$\$;\n',raw.decode())}


def definitions(valuation):
    source=originals('costs.sql')|originals('source_rebalance.sql');changed={};routes={}
    def finish(name,d):
        if d.inverse()!=source[name]:raise ValueError('SKU_MONEY_DERIVATION_NOT_REVERSIBLE:'+name)
        changed[name]=d.source.replace('create function ','create or replace function ',1)
        routes[name]=[r[2]for r in d.routes]

    name='cp7_sku_conversion.pool_cost_components_v3';d=Derivation(source[name])
    d.once('a.units,r.unit_value,\n  round(a.units*r.unit_value,6)::numeric,r.source_revision',
        """a.units,cp7_sku_conversion.cost_current_unit_v3(a.root_lot_id,p_product),
  round(a.units*cp7_sku_conversion.cost_current_unit_v3(a.root_lot_id,p_product),6)::numeric,
  r.source_revision||jsonb_build_object('money_events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')
    from cp7_sku_conversion.cost_money_events_v3 e where e.root_lot_id=a.root_lot_id))""",'pool current allocated cents and complete monetary revision')
    finish(name,d)

    name='cp7_sku_conversion.cost_scope_value_v3';d=Derivation(source[name])
    d.once('sum(t.units*r.unit_value)','sum(t.units*cp7_sku_conversion.cost_current_unit_v3(t.root_lot_id,p_product))',
           'same monetary custody for owned conversion sold and returned scopes')
    finish(name,d)

    name='cp7_sku_conversion.return_cost_components_v3';d=Derivation(source[name])
    d.once('declare v_sold numeric;v_prior numeric;','declare v_sold numeric;v_prior numeric;v_product uuid;',
           'return cost belongs to its original sale product')
    d.once('select v.qty_pcs into v_sold','select v.qty_pcs,v.product_id into v_sold,v_product','capture actual sold monetary scope')
    d.once('p.units,r.unit_value,r.hpp_version_id','p.units,cp7_sku_conversion.cost_current_unit_v3(p.root_lot_id,v_product),r.hpp_version_id',
           'return uses current owned money without rewriting original sale snapshot')
    finish(name,d)

    name='cp7_sku_conversion.finalize_costs_v3';d=Derivation(source[name])
    d.once('end $$;',' perform cp7_sku_conversion.post_conversion_money_v3(p_group);\nend $$;',
           'record original zero costs and paired transferred cents after unit events')
    finish(name,d)

    name='cp7_sku_conversion.reverse_costs_v3';d=Derivation(source[name])
    token="  raise exception 'CP7_SKU_COST_ALREADY_REVERSED';end if;"
    d.once(token,token+"\n if p_type='SKU_CONVERSION'then perform cp7_sku_conversion.reverse_conversion_money_v3(p_source);end if;",
           'current monetary inverse before its custody units reverse')
    finish(name,d)

    name='cp7_sku_conversion.capture_cost_source_v3';d=Derivation(source[name])
    d.once("return jsonb_build_object('document_id',p_document,", "return jsonb_build_object('cost_money_state',cp7_sku_conversion.cost_document_money_state_v3(p_document),'document_id',p_document,",
           'freeze complete monetary custody before Native source write')
    finish(name,d)

    name='cp7_sku_conversion.rebalance_cost_source_v3';d=Derivation(source[name])
    d.once(' perform erp.be_nonpo_prepare_transfers_v1(p_date);',
        " perform cp7_sku_conversion.reprice_document_money_v3(p_document,p_date,p_before->'cost_money_state',new_events,p_source_delta);\n perform erp.be_nonpo_prepare_transfers_v1(p_date);",
        'exact new source total allocated before retained Native physical and financial reconciliation')
    finish(name,d)

    name='cp7_sku_conversion.prepare_return_values_v2';d=Derivation(valuation[name])
    d.once('c.component_units*cr.unit_value','c.component_units*cp7_sku_conversion.cost_current_unit_v3(c.root_lot_id,v.product_id)',
           'pending return cents use the same original sale monetary scope')
    if d.inverse()!=valuation[name]:raise ValueError('SKU_MONEY_RETURN_DERIVATION_NOT_REVERSIBLE')
    valuation[name]=d.source;routes[name]=[r[2]for r in d.routes]

    name='cp7_sku_conversion.finalize_valuation_v2';d=Derivation(valuation[name])
    d.once(' perform cp7_sku_conversion.finalize_costs_v3(p_group);',
        """ perform cp7_sku_conversion.finalize_costs_v3(p_group);
 perform erp.sync_non_po_product_hpp_to_gl_v2620f(q.source_product_id,(q.physical_at at time zone 'Asia/Jakarta')::date,
  'SKU_COST_CENT_TRANSFER',p_group,'Pembagian sen mengikuti biaya yang berpindah');
 perform erp.sync_non_po_product_hpp_to_gl_v2620f(q.target_product_id,(q.physical_at at time zone 'Asia/Jakarta')::date,
  'SKU_COST_CENT_TRANSFER',p_group,'Pembagian sen mengikuti biaya yang berpindah');""",
        'retain exact source-total refusal and synchronize FG COGS cent redistribution after transfer')
    if d.inverse()!=valuation[name]:raise ValueError('SKU_MONEY_FINALIZE_DERIVATION_NOT_REVERSIBLE')
    valuation[name]=d.source;routes[name]=[r[2]for r in d.routes]
    return changed,valuation,routes


def raw_unit(root,product):
    """Independent credit arithmetic from raw rows, not the official helper."""
    return """(case when l.po_id is not null then erp.be_allocation_extra_v1(a.id)/a.qty_pcs
 else coalesce((select sum(m.amount_delta)from cp7_sku_conversion.cost_money_events_v3 m
  where m.root_lot_id=ROOT and m.product_id=PRODUCT)/nullif((select sum(u.units_delta)
  from cp7_sku_conversion.cost_events_v3 u where u.root_lot_id=ROOT and u.product_id=PRODUCT
   and u.source_type='SKU_CONVERSION'),0),0)end)""".replace('ROOT',root).replace('PRODUCT',product)


INTEGRITY=""" ),cost_monetary_integrity as(
  select(case when exists(
   select 1 from(select distinct e.root_lot_id from cost_owned_entries e join erp.fg_lots l on l.id=e.root_lot_id
    where p_po is null and l.po_id is null and e.product_id=p_product)roots
   left join erp.product_conversion_allocations a on a.destination_lot_id=roots.root_lot_id
   where a.id is null or(select count(*)from erp.product_conversion_allocations a2 where a2.destination_lot_id=roots.root_lot_id)<>1
    or(select count(*)from cp7_sku_conversion.cost_money_events_v3 m where m.root_lot_id=roots.root_lot_id and m.kind='ORIGIN')<>1
    or coalesce((select sum(m.amount_delta)from cp7_sku_conversion.cost_money_events_v3 m where m.root_lot_id=roots.root_lot_id),0)
       is distinct from erp.be_allocation_extra_v1(a.id)
    or coalesce((select sum(u.units_delta)from cp7_sku_conversion.cost_events_v3 u
       where u.root_lot_id=roots.root_lot_id and u.source_type='SKU_CONVERSION'),0)not in(0,a.qty_pcs)
    or(coalesce((select sum(u.units_delta)from cp7_sku_conversion.cost_events_v3 u
       where u.root_lot_id=roots.root_lot_id and u.source_type='SKU_CONVERSION'),0)=0 and erp.be_allocation_extra_v1(a.id)<>0)
    or exists(with raw_units as(
      select u.product_id,sum(u.units_delta)units from cp7_sku_conversion.cost_events_v3 u
      where u.root_lot_id=roots.root_lot_id and u.source_type='SKU_CONVERSION'group by u.product_id
     ),raw_money as(
      select m.product_id,sum(m.amount_delta)amount from cp7_sku_conversion.cost_money_events_v3 m
      where m.root_lot_id=roots.root_lot_id group by m.product_id
     )select 1 from raw_units u full join raw_money m using(product_id)
      where coalesce(u.units,0)<0 or(coalesce(u.units,0)=0 and coalesce(m.amount,0)<>0))
    or exists(select 1 from cost_owned_entries e where e.root_lot_id=roots.root_lot_id
      group by e.product_id having sum(e.units)<0)
  )then 'CP7_CREDIT_RAW_COST_MONEY_NOT_EXACT'else '1'end)::numeric factor
 ),cost_owned as("""


def credit_definitions(credit):
    from financial_delta import RAW_COSTS
    result={};routes={}
    for sig,source in credit.items():
        d=Derivation(source)
        if sig=='cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)':
            raw=Derivation(RAW_COSTS)
            raw.many('erp.be_allocation_extra_v1(a.id)/a.qty_pcs',raw_unit('e.root_lot_id','e.product_id'),3,
                     'current monetary price independently recomputed from raw custody and immutable money rows')
            raw.once(' ),cost_owned as(',INTEGRITY,'independent complete source cent and custody conservation')
            raw.once(' ),raw_values as(',""" ),cost_addition as(
  select coalesce(sum(c.component_units*"""+raw_unit('c.root_lot_id','c.product_id')+"""),0)::numeric amount
  from requested_components c join erp.fg_lots l on l.id=c.root_lot_id
  join erp.product_conversion_allocations a on a.destination_lot_id=c.root_lot_id
  where c.kind='COST'and((p_po is null and c.po_id is null and c.product_id=p_product)or c.po_id=p_po)
 ),addition as(select(select amount from addition_base)+(select amount from cost_addition)amount
 ),raw_values as(""",'hypothetical return amount independent of the official planned cost price')
            if raw.inverse()!=RAW_COSTS:raise ValueError('SKU_MONEY_RAW_CREDIT_NOT_REVERSIBLE')
            d.once(RAW_COSTS,raw.source,'complete independent raw monetary credit projection')
            old=""" ),addition as(
  select coalesce(sum(c.component_units*c.hpp_per_pcs),0)::numeric amount from requested_components c
  where(p_po is null and c.po_id is null and c.product_id=p_product)or c.po_id=p_po
 ),physical as("""
            new=""" ),addition_base as(
  select coalesce(sum(c.component_units*c.hpp_per_pcs),0)::numeric amount from requested_components c
  where c.kind='BASE'and((p_po is null and c.po_id is null and c.product_id=p_product)or c.po_id=p_po)
 ),physical as("""
            d.once(old,new,'base and cost hypothetical return sources stay separate')
            d.once(" ),cents as(select round(hpp,2)::numeric hpp,round(fg,2)::numeric fg,round(greatest(cogs,0),2)::numeric cogs from raw_values)",
                " ),cents as(select round(hpp*(select factor from cost_monetary_integrity),2)::numeric hpp,round(fg,2)::numeric fg,round(greatest(cogs,0),2)::numeric cogs from raw_values)",
                'mandatory raw source conservation before returning independent target')
        elif sig=='cp7_credit.initial_hpp_support_v1(uuid,uuid)':
            d.once("  union all select 'RESIDUAL_CLOSE'","""  union all select 'SKU_COST_MONEY_EVENT',e.id::text,to_jsonb(e)
   from cp7_sku_conversion.cost_money_events_v3 e where e.root_lot_id in(select id from lots)
  union all select 'RESIDUAL_CLOSE'""",'seal every monetary custody source fact with existing Native source proof')
        if d.inverse()!=source:raise ValueError('SKU_MONEY_CREDIT_NOT_REVERSIBLE:'+sig)
        result[sig]=d.source;routes[sig]=[r[2]for r in d.routes]
    return result,routes
