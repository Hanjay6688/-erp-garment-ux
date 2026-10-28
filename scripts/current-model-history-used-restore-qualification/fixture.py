"""Native opening + one Native sale; explicit synthetic planning profile only."""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import importlib.util,json,uuid
import cp7_ow11_analog_consumer_cases as consumer
import cp7_ow11_analog_choice_cases as analog
p=Path(__file__).resolve().with_name('opening_fixture.py')
spec=importlib.util.spec_from_file_location('successor_native_opening_fixture',p)
qualified=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualified)
ready=qualified.ready


def prepare(cur,today,report):
    f=qualified.prepare(cur,today,report)
    import cp7_sales_cases as sales
    import cp7_procurement_cases as receipt
    day=today-timedelta(days=1);product=f['source'].split(':')[0]
    consumer.plan.b.api.admin(cur);tag='OW11A-'+uuid.uuid4().hex[:12]
    customer=str(sales.fg.base.create_customer(cur,tag))
    draft=consumer.plan.b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number=tag,customer_id=customer,
        source_location_id=f['imported'][0]['location'],sale_date=receipt.aa.at(day,10).isoformat(),
        reason='Explicit SYNTHETIC composed consumer Native sale',items=[dict(product_id=product,qty_pcs=1,
        unit_price_snapshot='20',discount_amount='0')]),uuid.uuid4(),None)
    posted=sales.fg.post_sale(cur,draft)
    consumer.plan.b.api.admin(cur)
    stock=cur.execute("select sum(qty_signed)from erp.fg_stock_movements where product_id=%s",(product,)).fetchone()[0]
    cache=cur.execute("select sum(cached_qty_pcs)from erp.fg_inventory_balances where product_id=%s",(product,)).fetchone()[0]
    assert stock==cache==799,(stock,cache)
    report.update(actual_Native_sale=posted,comparator_stock_after_Native_sale=stock,comparator_cache_after_Native_sale=cache)
    report['READY_after_Native_sale']=ready(cur,day)
    consumer.profile(cur,f['imported'][0]['root'])
    query=dict(from_date=str(today-timedelta(days=3)),through_date=str(day),group_mode='AS_SOLD')
    consumer.plan.b.api.admin(cur)
    source=cur.execute('select cp7_baseline_native.source_within(5000)').fetchone()[0]
    boundary_query=dict(query,from_date=report['opening_day'])
    availability=cur.execute('select cp7_planning.history_availability(%s::jsonb,%s::jsonb)',
        (json.dumps(source),json.dumps(boundary_query))).fetchone()[0]
    observed=[dict(date=x['date'],state=x['state'])for x in availability if x['target_key']==f['source']]
    expected=[dict(date=str(today-timedelta(days=n)),state='STOCKOUT'if n==4 else'AVAILABLE')for n in (4,3,2,1)]
    report['actual_Native_opening_boundary']=dict(observed=observed,expected=expected,
        first_day_inflow_not_counted_as_whole_day=True)
    assert observed==expected,('NATIVE_COMPARATOR_DAY_BOUNDARY',observed,expected)
    f=consumer.fresh(cur,today,f,query)
    hist=next(x for x in f['row']['reference']['bounded_history_inputs']['inputs']['history']if x['target_key']==f['source'])
    report['actual_prechoice_comparator_history']=hist
    assert hist['available_days']==3,('NATIVE_COMPARATOR_AVAILABLE_DAYS',hist)
    assert [(x['date'],x['state'])for x in hist['days']]==[(x['date'],x['state'])for x in expected[1:]],hist
    f['payload']=consumer.payload(f)
    report['query']=query
    report['READY_after_explicit_own_history_profile']=ready(cur,day)
    return f


def assert_fresh(cur,today,f,choice,report):
    physical=consumer.plan.monetary_state(cur)
    fresh=consumer.fresh(cur,today,f,f['row']['query'])
    r=consumer.row(fresh);staged=consumer.staged_row(cur,fresh)
    report['observed_fresh_consumer']=dict(bounded=r,staged=staged)
    assert r['analog_resolution']['analog']['available_total_pcs']=='1'
    assert r['analog_resolution']['available_days']=='3',r['analog_resolution']
    assert r['target']['target_pcs']==staged['target']['target_pcs']=='1'
    assert r['demand_estimate']['basis']==staged['demand_estimate']['basis']==consumer.BASIS
    public,_=analog.reader.call(cur,fresh,fresh['target']);d=public['target_demand']
    assert public['contract_version']=='cp7.product-analog-candidates-read.v2'
    assert d==r['demand_provenance']and d['basis']==consumer.BASIS and d['target_pcs']=='1'
    assert d['own_total_pcs']=='0'and d['own_available_days']=='0'
    assert d['analog']['choice_id']==choice['choice_id']and d['analog']['scale_factor']=='1'
    consumer.plan.b.api.admin(cur)
    direct=cur.execute('select cp7_baseline_native.build(%s::jsonb,%s::jsonb)',
        (json.dumps(fresh['row']['reference']),json.dumps(fresh['row']['query']))).fetchone()[0]
    direct_row=next(x for x in direct['rows']if x['target_key']==fresh['target'])
    assert direct_row['target']['target_pcs']=='1'and direct_row['demand_estimate']['basis']==consumer.BASIS
    compiled=cur.execute('select cp7_reorder_inputs.compile(cp7_reorder_inputs.source_within(5000))').fetchone()[0]
    point=next(x for x in compiled['points']['rows']if x['target_key']==fresh['target'])
    assert point['point_pcs']=='1'and point['demand_basis']==consumer.BASIS
    assert point['available_total_pcs']=='0'and point['available_days']=='0'
    assert consumer.plan.monetary_state(cur)==physical
    report['consumed_public_reader']=public
    report['fresh_consumer_proof']=dict(actual_Native_sale_pcs='1',available_days='3',lead_days='3',scale='1',
        exact_direct_staged_bounded_and_ROP_target='1',own_history_pcs='0',own_history_days='0',
        physical_stock_money_HPP_unchanged=True,retained_old_capture_not_rewritten=True)
    return fresh


def assert_clear(cur,today,f,report):
    physical=consumer.plan.monetary_state(cur)
    fresh=consumer.fresh(cur,today,f,f['row']['query']);r=consumer.row(fresh)
    assert r['analog_resolution']['reason']=='ANALOG_CHOICE_CLEARED'
    assert r['demand_estimate']['status']=='UNKNOWN'and r['target']['target_pcs']is None
    public,_=analog.reader.call(cur,fresh,fresh['target'])
    assert public['target_demand']['basis']=='UNKNOWN'and public['target_demand']['target_pcs']is None
    assert public['target_demand']['own_total_pcs']=='0'and public['target_demand']['own_available_days']=='0'
    assert consumer.plan.monetary_state(cur)==physical
    report['after_full_restore_CLEAR_fresh_UNKNOWN']=dict(public=public,no_physical_money_HPP_change=True)
