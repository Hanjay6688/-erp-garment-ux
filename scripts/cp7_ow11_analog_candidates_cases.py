"""Private-consumer component, not confirmation, forecasts or full OW11."""
from time import monotonic
from pathlib import Path
import json
import re
import uuid
import cp7_product_analog_stage as prototype
import cp7_ow13c_bounded_stage_cases as bounded
import cp7_p19_scale_cases as volume
from cp7_ow04_restore_bundle import _catalog_rows
from cp7_production_stage import _row

plan=bounded.plan
CONTRACT='cp7.ow11.analog-private-native.v1'
IDS=dict(native=['OW11_ANALOG_PRIVATE_CATALOG22_EXACT',
                 'OW11_ANALOG_NATIVE_SOURCE_DENSE_PAGINATION_ADVISORY',
                 'OW11_ANALOG_NATIVE_PROFILE_INSUFFICIENT_AND_PAGE_GUARDS'])
REQUIRED=dict(native=3)
EXPECTED=DECLARED=3
FUNCTIONS,SCHEDULES=bounded.FUNCTIONS,bounded.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
SIGNATURE='cp7_product_analog_stage.candidates(jsonb,text,integer,integer)'


def install(cur):
    plan.b.api.admin(cur)
    prototype.verify_sources()
    before=_catalog_rows(cur)
    cur.execute((prototype.ROOT/'candidates.sql').read_text(),prepare=False)
    after=_catalog_rows(cur)
    assert set(before)==set(after)and len(before)==22
    for group in before:
        for key in set(before[group])|set(after[group]):
            if before[group].get(key)==after[group].get(key):continue
            assert before[group].get(key)is None and(group,key)in(
                ('schemas','cp7_product_analog_stage'),('functions',SIGNATURE)),(group,key)
    row=_row(cur,SIGNATURE)
    expected=re.search(r'as\s*\$\$(.*?)\$\$;', (prototype.ROOT/'candidates.sql').read_text(),re.S)[1]
    assert row[1]==expected and row[2:6]==['cp7_capture',False,'i',['search_path=""','TimeZone=UTC']]
    for role in('anon','authenticated','service_role','cp7_alert'):
        assert not cur.execute("select has_schema_privilege(%s,'cp7_product_analog_stage','USAGE')or has_function_privilege(%s,%s,'EXECUTE')",(role,role,SIGNATURE)).fetchone()[0]
    return before


def remove(cur,before):
    plan.b.api.admin(cur)
    cur.execute('drop function '+SIGNATURE+' restrict;drop schema cp7_product_analog_stage restrict',prepare=False)
    assert _catalog_rows(cur)==before,'ANALOG_PRIVATE_CATALOG22_NOT_RESTORED'


def call(cur,c,target,offset=0,limit=50):
    plan.b.api.admin(cur)
    cur.execute('set local role cp7_capture')
    cur.execute("set local statement_timeout='8s'")
    start=monotonic()
    result=cur.execute('select cp7_product_analog_stage.candidates(%s::jsonb,%s,%s,%s)',(json.dumps(c),target,offset,limit)).fetchone()[0]
    elapsed=(monotonic()-start)*1000
    plan.b.api.admin(cur)
    assert elapsed<8000,('ANALOG_PRIVATE_READ_OVER8S',elapsed)
    return result,round(elapsed,3)


def capture(cur,today):
    key=str(uuid.uuid4());initial=bounded.request(cur,today,key)
    plan.staged.checked(initial,key,'RUNNING')
    return plan.staged.job_row(cur,key)['reference']


def cases(cur,today):
    def catalog():
        physical=plan.monetary_state(cur);before=install(cur)
        assert prototype.verify_sources()['runtime_qualified']is False
        assert plan.monetary_state(cur)==physical
        remove(cur,before)
        return dict(status='PASS',one_private_no_public_no_table_no_existing_replacement=True,
                    exact_source_owner_ACL_GUC_and_catalog22_restored=True,actual_Auth_HTTP_credit=False)

    def dense():
        plan.fixture(cur,today);size=bounded.work.dense.seed(cur)
        root,target=cur.execute("select identity_root_id::text,identity_root_id::text||':'||size_id::text from erp.products where sku='OW13CSV-1'").fetchone()
        log=volume.Phases();volume.profile(cur,[root],log)
        c=capture(cur,today);physical=plan.monetary_state(cur);before=install(cur)
        assert c['status']=='INCOMPLETE'and c['bounded_history_inputs']['coverage']=='COMPLETE'
        one,elapsed=call(cur,c,target)
        two,_=call(cur,c,target,50)
        assert one['total']>=1999 and len(one['candidates'])==len(two['candidates'])==50
        assert one['total']==two['total']and one['suggested']==two['suggested']
        keys=[r['target_key']for r in one['candidates']+two['candidates']]
        assert len(set(keys))==100 and target not in keys
        for page in(one,two):
            assert page['state']=='REVIEW_REQUIRED'and not page['selected']and not page['reviewed']and not page['forecast_applied']
            assert page['source_captured_at']==c['captured_at']and page['query']==c['bounded_query']
            assert page['history_hash']==c['bounded_history_inputs']['inputs']['history_hash']
            for item in page['candidates']:
                assert item['size_id']==target.split(':')[1]and int(item['available_days'])>=1
                assert item['observed_available_daily_mean']is not None
                assert item['suggested']and 'SAME_CAPTURED_BRAND'in item['reasons']
                assert not item['selected']and not item['reviewed']
        unconfigured=cur.execute("select identity_root_id::text||':'||size_id::text from erp.products where sku='OW13CSV-2'").fetchone()[0]
        empty,_=call(cur,c,unconfigured)
        assert empty['state']=='PLANNING_CONFIG_REQUIRED'and empty['candidates']==[]and not empty['forecast_applied']
        assert empty['source_captured_at']==c['captured_at']and empty['history_hash']==one['history_hash']
        assert plan.monetary_state(cur)==physical
        remove(cur,before)
        return dict(status='PASS',**size,real_Native_bounded_reference=True,real_public_Native_profile_fixture=True,
                    source_raw_INCOMPLETE_preserved=True,minimum_days_from_selected_profile=True,
                    whole_total=one['total'],first_two_pages_exact_unique100=True,target_itself_excluded=True,
                    all_returned_candidates_same_physical_size=True,different_size_positive_fixture_qualified=False,
                    captured_brand_reason_and_Native_mean_only=True,unconfigured_target_no_invented_default=True,
                    captured_context_bound_including_not_ready=True,read_millis=elapsed,statement_limit='8s',
                    selected=False,reviewed=False,forecast_applied=False,no_ERP_write_by_candidate_reader=True)

    def guards():
        f=bounded.prepare(cur,today);root=f['x']['target'].split(':')[0]
        row=volume.baseline.get(cur,[root])['rows'][0]
        config=dict(volume.SYNTHETIC['profile']);config['minimum_available_days']='2'
        volume.baseline.save(cur,dict(root_id=root,product_version_id=row['product_version_id'],expected_revision=row['revision'],
                                     config=config,reason='Explicit synthetic minimum2 against one-day query; not owner default'))
        c=capture(cur,today);physical=plan.monetary_state(cur);before=install(cur)
        result,_=call(cur,c,f['x']['target'])
        assert c['bounded_query']['from_date']==c['bounded_query']['through_date']
        assert result['state']=='INSUFFICIENT_REVIEWABLE_HISTORY'and result['total']==0 and result['candidates']==[]
        assert result['minimum_available_days']=='2'and not result['selected']and not result['reviewed']
        plan.refused(cur,lambda:call(cur,c,f['x']['target'],-1),'CP7_PRODUCT_ANALOG_PAGE')
        plan.refused(cur,lambda:call(cur,c,f['x']['target'],0,101),'CP7_PRODUCT_ANALOG_PAGE')
        plan.refused(cur,lambda:call(cur,c,'missing-target'),'CP7_PRODUCT_ANALOG_TARGET')
        assert plan.monetary_state(cur)==physical
        remove(cur,before)
        return dict(status='PASS',actual_Native_minimum2_vs_one_day_no_zero_forecast=True,
                    negative_offset_and_limit101_refused=True,missing_target_refused=True,
                    no_ERP_write_or_selected_analog_or_forecast=True,full_OW11_acceptance=False)

    return list(zip(IDS['native'],[catalog,dense,guards]))
