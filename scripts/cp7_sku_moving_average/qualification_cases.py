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
 'SKU_MOVAVG_FRACTIONAL_RETURNS_INTERLEAVE_RECOST_AND_EARLIER_INVERSE',
)

def canonical(cur,today):
    x=f.masters(cur)
    x['lots']=[f.opening(cur,x['source'],2,'10.00',today-timedelta(days=3)),
               f.opening(cur,x['source'],2,'30.00',today-timedelta(days=2))]
    x['target_lot']=f.opening(cur,x['target'],1,'50.00',today-timedelta(days=4))
    x['payload']=f.payload(x,1)
    return x

def quote(cur,product,location):
    f.admin(cur)
    value=cur.execute("select cp7_sku_conversion.pool_quote_v2(%s,%s,'GRADE_A')",(product,location)).fetchone()[0]
    f.admin(cur);return value

def components(cur,product,location):
    f.admin(cur)
    rows=cur.execute("select root_lot_id::text,po_id::text,component_units::text,unit_value::text,value::text from cp7_sku_conversion.pool_components_v2(%s,%s,'GRADE_A')order by root_lot_id",(product,location)).fetchall()
    f.admin(cur);return rows

def value(q):return D(q['value'])

def event_balance(cur,source_type,source_id):
    f.admin(cur)
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

def normal_fg_readers(cur,x):
    """Read both current public facades with the original ordinary actor."""
    found=[];offset=0
    while True:
        current=f.public(cur,'erp_cp7_get_fg_v1',json.dumps(dict(purpose='SUMMARY',limit=100,offset=offset)))
        assert current['financial_captured']is True
        found.extend(r for r in current['page']['rows']if r['product_id']in(x['source'],x['target'])
            and r['location_id']==x['location']and r['quality_grade']=='GRADE_A')
        offset=current['page']['next_offset']
        if offset is None:break
        assert offset<=10000,'SKU_FG_FIXTURE_UNEXPECTED_SIZE'
    checked={}
    for product,quantity,total,unit in((x['source'],D(4),D(95),D('23.75')),(x['target'],D(1),D(35),D(35))):
        rows=[r for r in found if r['product_id']==product];assert rows
        assert sum(D(r['physical_qty'])for r in rows)==quantity
        assert sum(D(r['valuation']['value'])for r in rows)==total
        for row in rows:
            value=row['valuation'];assert value['state']=='KNOWN'and value['basis']=='SKU_LOCATION_GRADE_MOVING_AVERAGE_V2'
            assert D(value['unit_cost'])==unit and value['reserved_included']is True
        row=rows[0]
        card=f.public(cur,'erp_cp7_get_fg_ledger_v2',json.dumps({k:row[k]for k in('product_id','lot_id','location_id','quality_grade')}))
        assert card['financial_captured']is True and card['page']['rows']
        for movement in card['page']['rows']:
            assert movement['valuation']['basis']=='CURRENT_RESTATED_SKU_POOL_MOVEMENT_SNAPSHOT'
            assert movement['valuation']['state']=='KNOWN'and D(movement['valuation']['unit_cost'])==unit
        checked[product]=dict(physical_qty=str(quantity),value=str(total),unit_cost=str(unit),public_card_rows=len(card['page']['rows']))
    return dict(status='PASS',ordinary_public_RPC=True,rows=checked,real_Auth_or_browser_credit=0)

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
    f.admin(cur)
    invalid=cur.execute("select count(*)from(select source_id,side,sum(units_delta)units from cp7_sku_conversion.component_events_v2 where source_type='SKU_CONVERSION'group by source_id,side having abs(sum(units_delta))>0.000000000001)x").fetchone()[0]
    wrong_accounts=cur.execute("select count(*)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='SKU_MOVING_AVERAGE'and j.source_id in(%s,%s)and l.account_id<>erp.account_id('FG_INVENTORY')",(made['conversion_id'],result['conversion_id'])).fetchone()[0]
    f.admin(cur);assert invalid==0 and wrong_accounts==0
    readers=normal_fg_readers(cur,x)
    return dict(status='PASS',forward_group=made['conversion_id'],manual_back_group=result['conversion_id'],
      forward_value='20.00',manual_back_value='35.00',final_source_value='95.00',final_target_value='35.00',
      total_value='130.00',physical_FIFO_preserved=True,component_pool_quantity_conserved=True,
      correction_accounts=['FG_INVENTORY'],cash_AR_AP_revenue_COGS_created=False,
      actual_normal_FG_readers=readers)

def exact_group_reverse(cur,today):
    x=canonical(cur,today);made,_=forward(cur,x)
    result=f.action(cur,'REVERSE',dict(conversion_id=made['conversion_id'],reason='Moving average exact group inverse'))
    source=quote(cur,x['source'],x['location']);target=quote(cur,x['target'],x['location'])
    assert (D(source['qty']),value(source))==(D(4),D(80)),source
    assert (D(target['qty']),value(target))==(D(1),D(50)),target
    f.admin(cur)
    residual=cur.execute("select count(*)from(select side,root_lot_id,sum(units_delta)units from cp7_sku_conversion.component_events_v2 where group_id=%s group by side,root_lot_id having abs(sum(units_delta))>0.000000000001)x",(made['conversion_id'],)).fetchone()[0]
    value_residual=cur.execute("select coalesce(sum(effective_value_delta),0),coalesce(sum(adjustment_delta),0)from cp7_sku_conversion.valuation_events_v2 where group_id=%s",(made['conversion_id'],)).fetchone()
    f.admin(cur);assert residual==0 and tuple(map(D,value_residual))==(D(0),D(0))
    return dict(status='PASS',group_id=made['conversion_id'],reverse=result,source_value='80.00',target_value='50.00',
      total_value='130.00',component_inverse_exact=True,value_inverse_exact=True)

def root_recost(cur,today):
    x=canonical(cur,today);made,_=forward(cur,x)
    before=(components(cur,x['source'],x['location']),components(cur,x['target'],x['location']))
    f.admin(cur);event_count=cur.execute('select count(*)from cp7_sku_conversion.component_events_v2').fetchone()[0];f.admin(cur)
    correction=f.b.internal(cur,'post_opening_hpp_correction',x['lots'][1],D('40.00'),
      'Moving-average actual root recost lineage',today)
    f.admin(cur)
    source=quote(cur,x['source'],x['location']);target=quote(cur,x['target'],x['location'])
    assert (D(source['qty']),value(source))==(D(3),D(75)),source
    assert (D(target['qty']),value(target))==(D(2),D(75)),target
    assert value(source)+value(target)==D(150)
    after=(components(cur,x['source'],x['location']),components(cur,x['target'],x['location']))
    assert before!=after
    f.admin(cur);assert cur.execute('select count(*)from cp7_sku_conversion.component_events_v2').fetchone()[0]==event_count;f.admin(cur)
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
    f.admin(cur)
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
    f.admin(cur)
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
    # A one-lot ordinary sale needs no component correction row, but its
    # economic value event must still receive an exact status inverse.
    ordinary_before=sales_cmd.accounts(cur)
    ordinary_sale=f.reserve(cur,x,x['source'],1,at=x['now'].isoformat(),location=other_location)
    ordinary=dict(sale=ordinary_sale,tag='',destination=other_location)
    post_payload,post_version=sales_cmd.review(cur,ordinary)
    posted=sales_cmd.command(cur,'POST',post_payload,post_version);assert posted['status']=='POSTED',posted
    f.admin(cur)
    component_posts=cur.execute("select count(*)from cp7_sku_conversion.component_events_v2 where source_type='SALE'and source_id=%s and phase='POST'",(ordinary_sale,)).fetchone()[0]
    value_posts=cur.execute("select count(*)from cp7_sku_conversion.valuation_events_v2 where source_type='SALE'and source_id=%s and phase='POST'",(ordinary_sale,)).fetchone()[0]
    f.admin(cur);assert component_posts==0 and value_posts==1,(component_posts,value_posts)
    isolated_sold=quote(cur,x['source'],other_location);assert (D(isolated_sold['qty']),value(isolated_sold))==(D(2),D(180)),isolated_sold
    ordinary_reverse=sales_returns.reverse_sale(cur,ordinary);assert ordinary_reverse['status']=='REVERSED',ordinary_reverse
    assert event_balance(cur,'SALE',ordinary_sale)==(0,0)
    assert sales_cmd.accounts(cur)==ordinary_before
    isolated_restored=quote(cur,x['source'],other_location);assert isolated_restored==isolated,(isolated,isolated_restored)
    return dict(status='PASS',group_id=moved['conversion_id'],reservation_id=reservation,
      active_reservation_included_in_pool=True,source_after_qty='3',source_after_value='60.00',
      other_location_qty='3',other_location_value='270.00',other_location_unchanged=True,
      zero_component_sale_value_inverse_exact=True,ordinary_sale_id=ordinary_sale)

def fractional_return_scope(cur,today):
    def setup():
        x= f.masters(cur)
        x['lots']=[f.opening(cur,x['source'],1,'3.32',today-timedelta(days=3)),
                   f.opening(cur,x['source'],2,'3.34',today-timedelta(days=2))]
        before=sales_cmd.accounts(cur)
        sale=f.reserve(cur,x,x['source'],3,at=x['now'].isoformat())
        sf=dict(sale=sale,tag='',destination=x['location'])
        payload,version=sales_cmd.review(cur,sf)
        assert sales_cmd.command(cur,'POST',payload,version)['status']=='POSTED'
        sf['allocations']=sales_returns.read(cur,sf)['page']['rows']
        assert sorted(row['allocated_qty']for row in sf['allocations'])==['1','2']
        one=next(row['allocation_id']for row in sf['allocations']if row['allocated_qty']=='1')
        two=next(row['allocation_id']for row in sf['allocations']if row['allocated_qty']=='2')
        assert tuple(map(D,f.product_books(cur,x['source'])))==(D(10),D(0),D(10),D(0))
        return x,sf,before,one,two

    def post(x,sf,allocation,expected,extra=None):
        before=sales_cmd.accounts(cur)
        payload,version=sales_returns.payload(cur,sf,qty='1',refund='185000',allocation=allocation,destination=x['location'])
        if extra is not None:
            payload['items'].append(dict(payload['items'][0],allocation_id=extra))
        returned=sales_cmd.command(cur,'RETURN',payload,version)
        ident=returned['return_id'];f.admin(cur)
        snapshot=cur.execute('select sum(effective_value)from cp7_sku_conversion.sales_return_values_v2 where return_id=%s',(ident,)).fetchone()[0]
        delta=sales_cmd.delta(before,sales_cmd.accounts(cur))
        assert D(snapshot)==D(expected),('RETURN_SNAPSHOT_CENTS',snapshot,expected)
        assert delta[sales_cmd.mapping(cur,'FG_INVENTORY')]==D(expected),(snapshot,delta)
        f.product_books(cur,x['source'])
        return ident,dict(return_id=ident,snapshot_value=str(snapshot),FG_journal_delta=str(delta[sales_cmd.mapping(cur,'FG_INVENTORY')]))

    def undo_all(x,sf,returns,before=None):
        for ident in returns:
            assert sales_returns.inverse(cur,sf,ident)['return_status']=='REVERSED'
            assert event_balance(cur,'SALES_RETURN',ident)==(0,0)
            f.product_books(cur,x['source'])
        assert sales_returns.reverse_sale(cur,sf)['status']=='REVERSED'
        assert event_balance(cur,'SALE',sf['sale'])==(0,0)
        if before is not None:assert sales_cmd.accounts(cur)==before
        return f.product_books(cur,x['source'])

    x,sf,before,one,two=setup()
    first,a=post(x,sf,two,'3.33');second,b=post(x,sf,two,'3.34')
    f.admin(cur)
    frozen=cur.execute('select jsonb_agg(to_jsonb(v)order by sales_return_item_id)from cp7_sku_conversion.sales_return_values_v2 v where return_id in(%s,%s)',(first,second)).fetchone()[0]
    assert sales_returns.inverse(cur,sf,first)['return_status']=='REVERSED'
    assert tuple(map(D,f.product_books(cur,x['source'])))==(D(10),D('3.33'),D('6.67'),D(0))
    f.admin(cur)
    assert cur.execute('select jsonb_agg(to_jsonb(v)order by sales_return_item_id)from cp7_sku_conversion.sales_return_values_v2 v where return_id in(%s,%s)',(first,second)).fetchone()[0]==frozen
    assert event_balance(cur,'SALES_RETURN',first)==(0,0)
    replacement,c=post(x,sf,two,'3.34')
    assert tuple(map(D,undo_all(x,sf,[replacement,second],before)))==(D(10),D(10),D(0),D(0))
    split=dict(sale_id=sf['sale'],returns=[a,b,c],earlier_inverse_current_book_exact=True,immutable_snapshots_unchanged=True,full_inverse_neutral=True)

    x,sf,before,one,two=setup()
    batch,a=post(x,sf,two,'6.67',extra=one)
    last,b=post(x,sf,two,'3.33')
    assert tuple(map(D,f.product_books(cur,x['source'])))==(D(10),D(10),D(0),D(0))
    undo_all(x,sf,[last,batch],before)
    multi=dict(sale_id=sf['sale'],returns=[a,b],distinct_allocation_lines=True,full_inverse_neutral=True)

    x,sf,before,one,two=setup()
    first,a=post(x,sf,two,'3.33')
    correction=f.b.internal(cur,'post_opening_hpp_correction',x['lots'][1],D('4.50'),
        'Fractional return current-root HPP correction',today)
    assert tuple(map(D,f.product_books(cur,x['source'])))==(D('12.32'),D('4.11'),D('8.21'),D(0))
    second,b=post(x,sf,two,'4.10')
    assert tuple(map(D,f.product_books(cur,x['source'])))==(D('12.32'),D('8.21'),D('4.11'),D(0))
    restored=undo_all(x,sf,[second,first])
    assert tuple(map(D,restored))==(D('12.32'),D('12.32'),D(0),D(0))
    recost=dict(sale_id=sf['sale'],correction_id=str(correction),returns=[a,b],current_root_values_restored=restored)
    return dict(status='PASS',split_and_earlier_inverse=split,multiple_allocations=multi,intervening_recost=recost,
        actual_public_sale_commands=True,snapshots_equal_current_FG_journal_deltas=True,no_direct_posted_financial_rows=True)

def cases(cur,today):
    operations=(canonical_forward_back,exact_group_reverse,root_recost,sale_partial_return_reverse,reservation_location_isolation,fractional_return_scope)
    return [(name,lambda operation=operation:operation(cur,today))for name,operation in zip(IDS,operations)]
