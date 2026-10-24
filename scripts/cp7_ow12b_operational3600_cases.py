"""Operational3600 component only: no finance, full-factory or UI SLA claim."""
from time import monotonic
from hashlib import sha256
from pathlib import Path
import json
import uuid
import cp7_ow13c_bounded_stage_cases as bounded

plan=bounded.plan
CONTRACT='cp7.ow12b.operational3600-native.v1'
IDS=dict(native=['OW12B_OPERATIONAL3600_RETAINED_CATALOG_ANCHOR',
                 'OW12B_OPERATIONAL3600_REAL_DONE_ALL_PAGES_FULL_FRESHNESS'])
REQUIRED=dict(native=2)
EXPECTED=DECLARED=2
FUNCTIONS,SCHEDULES=bounded.FUNCTIONS,bounded.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}


def seed(cur):
    """Larger separate synthetic fixture; leave the qualified2000 seed intact."""
    plan.b.api.admin(cur)
    cur.execute('set local session_replication_role=replica')
    cur.execute("insert into erp.product_models(id,model_code,model_name,is_active)"
                "select gen_random_uuid(),'OW12B36-M'||g,'OW12B3600 synthetic model '||g,true from generate_series(1,360)g")
    cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,created_at,is_active,is_portal_visible)
        select x.id,'OW12B36-'||x.n,m.id,b.brand_id,'OW12B36',b.size_id,'OW12B3600 synthetic '||x.n,x.id,
         now()-interval'131 days',now()-interval'131 days',true,true
        from(select gen_random_uuid()id,g n from generate_series(1,3600)g)x
        join(select id,row_number()over(order by model_code)rn from erp.product_models where model_code like 'OW12B36-M%%')m on m.rn=1+(x.n%%360)
        cross join(select*from erp.products where id=%s)b""",(bounded.work.base.retained.formula.sales.fg.base.BASE_PRODUCT,))
    location=bounded.work.base.retained.formula.sales.fg.base.LOCATION
    cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
        select gen_random_uuid(),p.id,null,%s,'GRADE_A','OPENING',800,10,'OW12B3600_VOLUME',now()-interval'130 days',now()-interval'130 days'
        from erp.products p where p.sku like 'OW12B36-%%'""",(location,))
    cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
        select gen_random_uuid(),p.id,null,%s,'GRADE_A','SALE',-(1+(g%%6)),10,'OW12B3600_VOLUME',now()-((g%%120)||' days')::interval-interval'2 hours',now()-interval'1 hour'
        from erp.products p cross join generate_series(1,100)g where p.sku like 'OW12B36-%%'""",(location,))
    cur.execute('set local session_replication_role=origin')
    cur.execute('analyze erp.fg_stock_movements')
    count=cur.execute("select (select count(*)from erp.products where sku like 'OW12B36-%%'),"
                      "(select count(*)from erp.fg_stock_movements where source_type='OW12B3600_VOLUME')").fetchone()
    assert count==(3600,363600),count
    return dict(products=count[0],movements=count[1],synthetic_fixture=True)


def cases(cur,today):
    for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
        setattr(bounded,name,globals()[name])
    catalog=dict(bounded.cases(cur,today))['OW13C_BOUNDED_STAGE_CATALOG22_AND_LEGACY_HASH']

    def scale():
        x=plan.fixture(cur,today)
        size=seed(cur)
        physical=plan.monetary_state(cur)
        # Measure the actual predecessor rather than inventing a before time.
        # Dense history is still honestly INCOMPLETE on the legacy method.
        oldkey=str(uuid.uuid4());start=monotonic()
        old=plan.staged.request(cur,today,oldkey)
        old_ms=round((monotonic()-start)*1000,3)
        plan.staged.checked(old,oldkey,'RUNNING')
        stopped,old_calls=plan.staged.drive(cur,oldkey)
        assert stopped['state']=='FAILED' and stopped['failure']['code']=='CP7_PLANNING_CAPTURE_INCOMPLETE',stopped
        assert plan.staged.job_row(cur,oldkey)['reference']['status']=='INCOMPLETE'
        key=str(uuid.uuid4());start=monotonic()
        initial=bounded.request(cur,today,key)
        request_ms=(monotonic()-start)*1000
        plan.staged.checked(initial,key,'RUNNING')
        assert request_ms<8000 and initial['units_done']==0 and initial['run_id']is None
        row=plan.staged.job_row(cur,key);c=row['reference']
        assert c['status']=='INCOMPLETE' and c['stock_raw_omitted']is True
        assert c['bounded_history_inputs']['coverage']=='COMPLETE' and c['bounded_history_inputs']['raw_native_status_overridden']is False
        assert c['bounded_history_inputs']['raw_native_capture_status']==c['status']
        products=c['facts']['products']
        assert sum(p['sku'].startswith('OW12B36-')for p in products)==3600
        assert int(c['bounded_stock_reference']['row_count'])>=363600
        f=dict(x=x,key=key,initial=initial,row=row,subject=None,request_millis=round(request_ms,3))
        bounded.finish(cur,f)
        assert f['pages']['targets_total']==len(products)>=3600
        assert 'RAW_NATIVE_CAPTURE_INCOMPLETE_COMPLETE_SQL_HISTORY_INPUTS'in f['original']['analysis']['generation_warnings']
        times=[]
        for _ in range(3):
            start=monotonic()
            state=plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(f['done']['run_id'],))
            elapsed=(monotonic()-start)*1000
            assert state['source_state']=='UNCHANGED' and elapsed<8000,(state,elapsed)
            times.append(round(elapsed,3))
        assert plan.monetary_state(cur)==physical
        plan.found_fg(cur,x,'1')
        before=plan.monetary_state(cur)
        stale=plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(f['done']['run_id'],))
        assert stale['source_state']=='ARCHIVED_STALE' and plan.monetary_state(cur)==before
        unchanged2000=Path(__file__).with_name('cp7_ow13c_checked_scale_cases.py')
        return dict(status='PASS',**size,actual_products=len(products),real_Native_job_DONE=True,all_target_pages_verified=True,
                    **f['page_meta'],request_millis=f['request_millis'],step_count=len(f['calls']),
                    slowest_step_millis=max(c['ms']for c in f['calls']),full_source_check_millis=times,
                    legacy_request_millis=old_ms,legacy_step_millis=[c['ms']for c in old_calls],
                    legacy_terminal_state='FAILED',legacy_failure='CP7_PLANNING_CAPTURE_INCOMPLETE',
                    complete_before_result_available=False,before_after_equal_complete_results_claim=False,
                    raw_native_INCOMPLETE_preserved=True,raw_stock_digest_rows=int(c['bounded_stock_reference']['row_count']),
                    original2000_fixture_sha256=sha256(unchanged2000.read_bytes()).hexdigest(),
                    actual_Native_stock_change_stales_job=True,no_ERP_write_by_analysis_or_freshness=True,
                    statement_limit='8s',wall_limit_ms=8000,financial_capture='DEFERRED',official_finance_included=False,
                    money_HPP_report_parity_qualified=False,full_factory3600_qualified=False,
                    full_OW12b_acceptance=False,operational3600_component_qualified=True,production_go=False)

    return [(IDS['native'][0],catalog),(IDS['native'][1],scale)]
