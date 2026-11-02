"""Intended Native cases for the moving-average successor.

This file registers actual disposable-database work. Merely importing or
source-checking it earns zero case credit; only a retained strict-group report
may count a case.
"""
from datetime import timedelta
from decimal import Decimal as D
import importlib.util
import json
import sys
import uuid
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
import cp7_sales_command_cases as sales_cmd
import cp7_sales_return_cases as sales_returns

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

f=load('sku_movavg_native_fixture',ROOT/'current-sku-pair-conversion-qualification/fixture.py')

IDS=(
 'SKU_MOVAVG_CANONICAL_FORWARD20_MANUAL_BACK35_TOTAL130',
 'SKU_MOVAVG_EXACT_GROUP_REVERSE_COMPONENT_AND_VALUE_INVERSE',
 'SKU_MOVAVG_ROOT_RECOST_FOLLOWS_REMAINING_LINEAGE_TOTAL150',
 'SKU_MOVAVG_SALE_PARTIAL_RETURN_AND_EXACT_REVERSAL',
 'SKU_MOVAVG_RESERVATION_INCLUDED_AND_LOCATION_ISOLATED',
)

def canonical(cur,today):
    x=f.masters(cur)
    x['lots']=[f.opening(cur,x['source'],2,'10.00',today-timedelta(days=3)),
               f.opening(cur,x['source'],2,'30.00',today-timedelta(days=2))]
    x['target_lot']=f.opening(cur,x['target'],1,'50.00',today-timedelta(days=4))
    x['payload']=f.payload(x,1)
    return x

def quote(cur,product,location):
    f.owner(cur)
    value=cur.execute("select cp7_sku_conversion.pool_quote_v2(%s,%s,'GRADE_A')",(product,location)).fetchone()[0]
    f.admin(cur);return value

def components(cur,product,location):
    f.owner(cur)
    rows=cur.execute("select root_lot_id::text,po_id::text,component_units::text,unit_value::text,value::text from cp7_sku_conversion.pool_components_v2(%s,%s,'GRADE_A')order by root_lot_id",(product,location)).fetchall()
    f.admin(cur);return rows

def value(q):return D(q['value'])

def event_balance(cur,source_type,source_id):
    f.owner(cur)
    component_residual=cur.execute("select count(*)from(select product_id,location_id,quality_grade,root_lot_id from cp7_sku_conversion.component_events_v2 where source_type=%s and source_id=%s group by product_id,location_id,quality_grade,root_lot_id having abs(sum(units_delta))>0.000000000001)x",(source_type,source_id)).fetchone()[0]
    valuation_residual=cur.execute("select count(*)from(select product_id,location_id,quality_grade from cp7_sku_conversion.valuation_events_v2 where source_type=%s and source_id=%s group by product_id,location_id,quality_grade having abs(sum(qty_delta))>0.000000000001 or abs(sum(effective_value_delta))>0.001 or abs(sum(legacy_value_delta))>0.001 or abs(sum(adjustment_delta))>0.001)x",(source_type,source_id)).fetchone()[0]
    f.admin(cur);return int(component_residual),int(valuation_residual)

def forward(cur,x):
    payload,preview=f.review(cur,x['payload'])
    assert D(preview['cost']['source_value'])==D('20.00'),preview
    assert D(preview['cost']['native_physical_value'])==D('10.00'),preview
    result=f.action(cur,'POST',payload)
    source=quote(cur,x['source'],x['location']);target=quote(cur,x['target'],x['location'])
    assert (D(source['qty']),value(source),D(source['average']))==(D(3),D(60),D(20)),source
    assert (D(target['qty']),value(target),D(target['average']))==(D(2),D(70),D(35)),target
    return result,preview

def canonical_forward_back(cur,today):
    x=canonical(cur,today);made,first=forward(cur,x)
    back=f.payload(x,1,source=x['target'],target=x['source'],at=x['back_at'])
    payload,preview=f.review(cur,back)
    assert D(preview['cost']['source_value'])==D('35.00'),preview
    result=f.action(cur,'POST',payload)
    source=quote(cur,x['source'],x['location']);target=quote(cur,x['target'],x['location'])
    assert (D(source['qty']),value(source))==(D(4),D(95)),source
    assert (D(target['qty']),value(target))==(D(1),D(35)),target
    assert value(source)+value(target)==D(130)
    f.owner(cur)
    invalid=cur.execute("select count(*)from(select source_id,side,sum(units_delta)units from cp7_sku_conversion.component_events_v2 where source_type='SKU_CONVERSION'group by source_id,side having abs(sum(units_delta))>0.000000000001)x").fetchone()[0]
    wrong_accounts=cur.execute("select count(*)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='SKU_MOVING_AVERAGE'and j.source_id in(%s,%s)and l.account_id<>erp.account_id('FG_INVENTORY')",(made['conversion_id'],result['conversion_id'])).fetchone()[0]
    f.admin(cur);assert invalid==0 and wrong_accounts==0
    return dict(status='PASS',forward_group=made['conversion_id'],manual_back_group=result['conversion_id'],
      forward_value='20.00',manual_back_value='35.00',final_source_value='95.00',final_target_value='35.00',
      total_value='130.00',physical_FIFO_preserved=True,component_pool_quantity_conserved=True,
      correction_accounts=['FG_INVENTORY'],cash_AR_AP_revenue_COGS_created=False)

def exact_group_reverse(cur,today):
    x=canonical(cur,today);made,_=forward(cur,x)
    result=f.action(cur,'REVERSE',dict(conversion_id=made['conversion_id'],reason='Moving average exact group inverse'))
    source=quote(cur,x['source'],x['location']);target=quote(cur,x['target'],x['location'])
    assert (D(source['qty']),value(source))==(D(4),D(80)),source
    assert (D(target['qty']),value(target))==(D(1),D(50)),target
    f.owner(cur)
    residual=cur.execute("select count(*)from(select side,root_lot_id,sum(units_delta)units from cp7_sku_conversion.component_events_v2 where group_id=%s group by side,root_lot_id having abs(sum(units_delta))>0.000000000001)x",(made['conversion_id'],)).fetchone()[0]
    value_residual=cur.execute("select coalesce(sum(effective_value_delta),0),coalesce(sum(adjustment_delta),0)from cp7_sku_conversion.valuation_events_v2 where group_id=%s",(made['conversion_id'],)).fetchone()
    f.admin(cur);assert residual==0 and tuple(map(D,value_residual))==(D(0),D(0))
    return dict(status='PASS',group_id=made['conversion_id'],reverse=result,source_value='80.00',target_value='50.00',
      total_value='130.00',component_inverse_exact=True,value_inverse_exact=True)

def root_recost(cur,today):
    x=canonical(cur,today);made,_=forward(cur,x)
    before=(components(cur,x['source'],x['location']),components(cur,x['target'],x['location']))
    f.owner(cur);event_count=cur.execute('select count(*)from cp7_sku_conversion.component_events_v2').fetchone()[0];f.admin(cur)
    correction=f.b.internal(cur,'post_opening_hpp_correction',x['lots'][1],D('40.00'),
      'Moving-average actual root recost lineage',today)
    f.admin(cur)
    source=quote(cur,x['source'],x['location']);target=quote(cur,x['target'],x['location'])
    assert (D(source['qty']),value(source))==(D(3),D(75)),source
    assert (D(target['qty']),value(target))==(D(2),D(75)),target
    assert value(source)+value(target)==D(150)
    after=(components(cur,x['source'],x['location']),components(cur,x['target'],x['location']))
    assert before!=after
    f.owner(cur);assert cur.execute('select count(*)from cp7_sku_conversion.component_events_v2').fetchone()[0]==event_count;f.admin(cur)
    return dict(status='PASS',group_id=made['conversion_id'],correction_id=str(correction),source_value='75.00',
      target_value='75.00',total_value='150.00',root_recost_followed_remaining_lineage=True,
      append_only_component_events_unchanged=True)

def sale_partial_return_reverse(cur,today):
    x=canonical(cur,today);made,_=forward(cur,x)
    before_sale=sales_cmd.accounts(cur)
    sale=f.reserve(cur,x,x['target'],2,at=x['now'].isoformat())
    sf=dict(sale=sale,tag='',destination=x['location'])
    post_payload,post_version=sales_cmd.review(cur,sf)
    posted=sales_cmd.command(cur,'POST',post_payload,post_version)
    assert posted['status']=='POSTED',posted
    f.owner(cur)
    sale_totals=cur.execute("select count(*),sum(qty_pcs)::text,sum(effective_value)::text,sum(legacy_value)::text from cp7_sku_conversion.sale_allocation_values_v2 where sale_id=%s",(sale,)).fetchone()
    sold_components=cur.execute("select sum(c.component_units)::text,sum(c.booked_value)::text from cp7_sku_conversion.sale_allocation_components_v2 c join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)where v.sale_id=%s",(sale,)).fetchone()
    f.admin(cur)
    assert int(sale_totals[0])>=1 and tuple(map(D,sale_totals[1:3]))==(D(2),D(70)),sale_totals
    assert D(sale_totals[3])!=D(70),sale_totals
    assert tuple(map(D,sold_components))==(D(2),D(70)),sold_components
    assert sales_cmd.delta(before_sale,sales_cmd.accounts(cur))=={
      sales_cmd.mapping(cur,'AR_CUSTOMER'):D(370000),sales_cmd.mapping(cur,'SALES_REVENUE'):D(-370000),
      sales_cmd.mapping(cur,'FG_INVENTORY'):D(-70),sales_cmd.mapping(cur,'COGS'):D(70)}
    after_sale=sales_cmd.accounts(cur)
    empty=quote(cur,x['target'],x['location']);assert (D(empty['qty']),value(empty))==(D(0),D(0)),empty

    sf['allocations']=sales_returns.read(cur,sf)['page']['rows']
    return_payload,return_version=sales_returns.payload(cur,sf,qty='1',refund='185000',destination=x['location'])
    returned=sales_cmd.command(cur,'RETURN',return_payload,return_version)
    return_id=returned['return_id']
    f.owner(cur)
    return_totals=cur.execute("select sum(qty_pcs)::text,sum(effective_value)::text from cp7_sku_conversion.sales_return_values_v2 where return_id=%s",(return_id,)).fetchone()
    remaining=cur.execute("with sold as(select c.root_lot_id,sum(c.component_units)units,sum(c.booked_value)value from cp7_sku_conversion.sale_allocation_components_v2 c join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)where v.sale_id=%s group by c.root_lot_id),returned as(select c.root_lot_id,sum(c.component_units)units,sum(c.booked_value)value from cp7_sku_conversion.sales_return_components_v2 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)join erp.sales_returns h on h.id=v.return_id where v.sale_stock_allocation_id in(select sale_stock_allocation_id from cp7_sku_conversion.sale_allocation_values_v2 where sale_id=%s)and h.status='POSTED'group by c.root_lot_id)select coalesce(sum(s.units-coalesce(r.units,0)),0)::text,coalesce(sum(s.value-coalesce(r.value,0)),0)::text from sold s left join returned r using(root_lot_id)",(sale,sale)).fetchone()
    f.admin(cur)
    assert tuple(map(D,return_totals))==(D(1),D(35)),return_totals
    assert tuple(map(D,remaining))==(D(1),D(35)),remaining
    assert sales_cmd.delta(after_sale,sales_cmd.accounts(cur))=={
      sales_cmd.mapping(cur,'AR_CUSTOMER'):D(-185000),sales_cmd.mapping(cur,'SALES_REVENUE'):D(185000),
      sales_cmd.mapping(cur,'FG_INVENTORY'):D(35),sales_cmd.mapping(cur,'COGS'):D(-35)}
    half=quote(cur,x['target'],x['location']);assert (D(half['qty']),value(half))==(D(1),D(35)),half

    reversed_return=sales_returns.inverse(cur,sf,return_id)
    assert reversed_return['return_status']=='REVERSED',reversed_return
    empty_again=quote(cur,x['target'],x['location']);assert (D(empty_again['qty']),value(empty_again))==(D(0),D(0)),empty_again
    assert event_balance(cur,'SALES_RETURN',return_id)==(0,0)
    assert sales_cmd.accounts(cur)==after_sale
    reversed_sale=sales_returns.reverse_sale(cur,sf);assert reversed_sale['status']=='REVERSED',reversed_sale
    restored=quote(cur,x['target'],x['location']);assert (D(restored['qty']),value(restored))==(D(2),D(70)),restored
    assert event_balance(cur,'SALE',sale)==(0,0)
    assert sales_cmd.accounts(cur)==before_sale
    return dict(status='PASS',group_id=made['conversion_id'],sale_id=sale,return_id=return_id,
      sale_effective_value='70.00',physical_FIFO_legacy_value=sale_totals[3],partial_return_value='35.00',
      remaining_sale_value='35.00',return_reverse_exact=True,sale_reverse_exact=True,
      final_target_qty='2',final_target_value='70.00')

def reservation_location_isolation(cur,today):
    x=f.masters(cur)
    f.opening(cur,x['source'],2,'10.00',today-timedelta(days=3))
    f.opening(cur,x['source'],2,'30.00',today-timedelta(days=2))
    f.opening(cur,x['target'],1,'50.00',today-timedelta(days=4))
    f.admin(cur);other_location=str(uuid.uuid4())
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active)values(%s,%s,'Moving average isolated warehouse','FG_WAREHOUSE',true)",(other_location,'S29ISO-'+uuid.uuid4().hex[:8]))
    f.opening(cur,x['source'],3,'90.00',today-timedelta(days=2),other_location)
    before=quote(cur,x['source'],x['location']);isolated=quote(cur,x['source'],other_location)
    assert (D(before['qty']),value(before))==(D(4),D(80))
    assert (D(isolated['qty']),value(isolated))==(D(3),D(270))
    reservation=f.reserve(cur,x,x['source'],1)
    reserved=quote(cur,x['source'],x['location'])
    assert (D(reserved['qty']),value(reserved))==(D(4),D(80)),reserved
    payload,preview=f.review(cur,f.payload(x,1));assert D(preview['cost']['source_value'])==D(20)
    moved=f.action(cur,'POST',payload)
    after=quote(cur,x['source'],x['location']);isolated_after=quote(cur,x['source'],other_location)
    assert (D(after['qty']),value(after))==(D(3),D(60)),after
    assert isolated_after==isolated,(isolated,isolated_after)
    f.cancel_reservation(cur,reservation)
    return dict(status='PASS',group_id=moved['conversion_id'],reservation_id=reservation,
      active_reservation_included_in_pool=True,source_after_qty='3',source_after_value='60.00',
      other_location_qty='3',other_location_value='270.00',other_location_unchanged=True)

def cases(cur,today):
    operations=(canonical_forward_back,exact_group_reverse,root_recost,sale_partial_return_reverse,reservation_location_isolation)
    return [(name,lambda operation=operation:operation(cur,today))for name,operation in zip(IDS,operations)]
