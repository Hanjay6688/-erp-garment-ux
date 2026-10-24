"""Six actual Native v2 controls. No historical capture or policy is backdated."""
from copy import deepcopy
from time import monotonic
import json
import uuid
import cp7_model_evaluation_v2_stage as stage
import cp7_ow11_model_policy_cases as policy
import cp7_model_native_cases as legacy
from cp7_ow04_restore_bundle import _catalog_rows

plan,master,bounded=policy.plan,policy.master,policy.bounded
CONTRACT='cp7.ow11.model-evaluation-v2-native.v1'
IDS=dict(native=['OW11_MODEL_V2_CATALOG22_COMPOSED_PREUSE_DEPENDENCY',
 'OW11_MODEL_V2_NATIVE_BASELINE_EXACT_REPLAY_V1_UNCHANGED',
 'OW11_MODEL_V2_ACTUAL_POLICY_CLOCK_NO_POSTHOC_APPROVAL',
 'OW11_MODEL_V2_NATIVE_POST_SOURCE_WITHDRAWAL_OLD_RESULT',
 'OW11_MODEL_V2_CURRENT_ACCESS_FOREIGN_CLOSED_QUERY',
 'OW11_MODEL_V2_IMMUTABLE_ATOMIC_LAST_ROW_AND_GUARD'])
REQUIRED=dict(native=6)
EXPECTED=DECLARED=6
FUNCTIONS=(*policy.FUNCTIONS,'erp_cp7_capture_model_evaluation_v2','erp_cp7_read_model_evaluation_v2')
SCHEDULES=policy.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def install(cur):
    policy.PARENT_CHECKER=PARENT_CHECKER
    ps=policy.install(cur)
    vs=stage.install_delta(cur,lambda c:policy.stage.verify(c,ps))
    return ps,vs


def capture(cur,q,subject=None,key=None):
    start=monotonic();r=plan.rpc(cur,'erp_cp7_capture_model_evaluation_v2',(json.dumps(q),key or uuid.uuid4()),subject)
    elapsed=(monotonic()-start)*1000;assert elapsed<8000,('MODEL_V2_CAPTURE_OVER8S',elapsed)
    return r


def read(cur,run,subject=None):
    return plan.rpc(cur,'erp_cp7_read_model_evaluation_v2',(run,),subject)


def stored(cur,run):
    plan.b.api.admin(cur)
    return cur.execute('select input,result,payload,query from cp7_model_registry_adapter.runs where id=%s',(run,)).fetchone()


def unchanged(one,two):
    assert {k:v for k,v in one.items()if k!='current_guard'}=={k:v for k,v in two.items()if k!='current_guard'}


def cases(cur,today):
    def catalog():
        before=_catalog_rows(cur);ps,vs=install(cur);v=stage.verify(cur,vs)
        assert(v['private_functions'],v['public_rpcs'],v['new_tables'],v['old_replacements'])==(7,2,1,0)
        snap=_catalog_rows(cur);cur.execute('create view public.ow11_model_v2_inverse_guard as select id from cp7_model_registry_adapter.runs')
        guarded=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,vs)
        except Exception as e:assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else:raise AssertionError('MODEL_V2_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_model_v2_inverse_guard');assert _catalog_rows(cur)==snap
        stage.rollback_preuse(cur,vs);policy.stage.rollback_preuse(cur,ps);assert _catalog_rows(cur)==before
        return dict(status='PASS',exact_catalog22_composed_preuse_inverse=True,
         private7_public2_table1_replacements0=True,dependent_view_partial_DDL_restored=True,source_sha256=stage.sources())

    def replay():
        _,vs=install(cur);_,_,q=legacy.prepared(cur,today,12);key=uuid.uuid4()
        old=legacy.capture(cur,q,key);old_stored=legacy.stored(cur,old['run_id']);physical=plan.monetary_state(cur)
        one=capture(cur,q,key=key);snapshot=stored(cur,one['run_id']);two=capture(cur,q,key=key)
        unchanged(one,two);unchanged(one,read(cur,one['run_id']));assert stored(cur,one['run_id'])==snapshot
        assert one['assessment']['activation']['reason']=='EXPLICIT_ACTIVATION_POLICY_REQUIRED'
        assert one['current_guard']['state']=='BASELINE_REQUIRED'and one['forecast_applied']is False
        assert legacy.read(cur,old['run_id'])==old and legacy.stored(cur,old['run_id'])==old_stored
        assert cur.execute('select count(*)from cp7_model_registry_adapter.runs where request_id=%s',(key,)).fetchone()[0]==1
        assert cur.execute('select count(*)from cp7_model_native.runs where request_id=%s',(key,)).fetchone()[0]==1
        assert plan.refusal(cur,lambda:capture(cur,dict(q,horizon_days='2'),key=key))[1]=='CP7_MODEL_V2_REQUEST_CHANGED'
        try:stage.rollback_preuse(cur,vs)
        except ValueError as e:assert str(e)=='MODEL_V2_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
        else:raise AssertionError('MODEL_V2_AFTER_USE_INVERSE_ALLOWED')
        assert plan.monetary_state(cur)==physical
        return dict(status='PASS',actual_Native_history_explicit_baseline=True,exact_UUID_one_v2_run=True,
         same_UUID_v1_separate_immutable_namespace=True,no_stock_money_HPP_change=True)

    def clocks():
        install(cur);subject=master.role_actor(cur,'OWNER');f,original,q=legacy.prepared(cur,today,12,subject)
        first=capture(cur,q,subject);frozen=stored(cur,first['run_id']);p=policy.save(cur,policy.payload(cur,subject),subject)
        late=capture(cur,q,subject);assert late['assessment']['policy_source']is None
        assert late['assessment']['activation']['reason']=='ACTIVATION_POLICY_CHANGED'
        old=read(cur,first['run_id'],subject);unchanged(first,old);assert old['current_guard']['reason']=='ACTIVATION_POLICY_CHANGED'
        fresh=legacy.previous.capture(cur,today,subject=subject,q=legacy.previous.query(today,12));new_q=legacy.query(fresh,f)
        current=capture(cur,new_q,subject);d,r,_,_=stored(cur,current['run_id'])
        assert d['policy_source']['policy']==p['policy']and d['registered_at']==p['policy']['recorded_at']
        assert r['activation']['reason']=='REGISTRY_NOT_KNOWN_BEFORE_VALIDATION'and r['activation']['forecast']is None
        assert all(x['known_at']<=fresh['captured_at']for x in d['series'])
        assert stored(cur,first['run_id'])==frozen
        return dict(status='PASS',actual_recorded_policy_not_backdated=True,old_capture_never_posthoc_approved=True,
         new_capture_uses_explicit_late_registry_baseline=True,actual_Native_knowledge_clock=True)

    def source():
        install(cur);f,_,q=legacy.prepared(cur,today,12);one=capture(cur,q);frozen=stored(cur,one['run_id'])
        legacy.previous.sales.fg.post_sale(cur,f['draft'])
        stale=read(cur,one['run_id']);unchanged(one,stale)
        assert stale['current_guard']['reason']=='NATIVE_HISTORY_SOURCE_CHANGED'and stale['current_guard']['source_state']=='ARCHIVED_STALE'
        assert plan.refusal(cur,lambda:capture(cur,q))[1]=='CP7_MODEL_V2_HISTORY_STALE'
        assert stored(cur,one['run_id'])==frozen
        fresh=legacy.previous.capture(cur,today,q=legacy.previous.query(today,12));new=capture(cur,legacy.query(fresh,f));d,_,_,_=stored(cur,new['run_id'])
        assert legacy.previous.history(fresh,f)['gross_observed_pcs']=='24'
        assert all(x['state']!='OBSERVED'and x['value']is None for x in d['series'])
        return dict(status='PASS',actual_posted_sale24_retires_source=True,old_input_result_immutable=True,
         stale_new_capture_refused=True,unknown_availability_never_observed_zero=True)

    def access():
        install(cur);_,_,q=legacy.prepared(cur,today,12);one=capture(cur,q);other,role=legacy.auth.custom_actor(cur)
        assert plan.refusal(cur,lambda:capture(cur,q,other))[0]=='42501'
        assert plan.refusal(cur,lambda:read(cur,one['run_id'],other))[1]=='CP7_MODEL_V2_RUN_UNAVAILABLE'
        f,_,own_q=legacy.prepared(cur,today,12,other);own=capture(cur,own_q,other)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
        assert plan.refusal(cur,lambda:capture(cur,own_q,other,own['request_id']))[0]=='42501'
        assert plan.refusal(cur,lambda:read(cur,own['run_id'],other))[0]=='42501'
        for field in('series','policy','actor','registered_at','forecast','engine_hash'):
            assert plan.refusal(cur,lambda field=field:capture(cur,dict(q,**{field:'forged'})))[1]=='CP7_WIP_FIELDS'
        for horizon in('0','91'):
            assert plan.refusal(cur,lambda horizon=horizon:capture(cur,dict(q,horizon_days=horizon)))[1]=='CP7_MODEL_NATIVE_HORIZON'
        return dict(status='PASS',actual_current_permission_precedes_committed_replay=True,
         foreign_run_history_denied=True,closed_input_cannot_supply_history_policy_forecast=True,actual_Auth_HTTP_credit=False)

    def atomic():
        install(cur);_,_,q=legacy.prepared(cur,today,12);one=capture(cur,q);snapshot=stored(cur,one['run_id']);physical=plan.monetary_state(cur)
        for stmt in('update cp7_model_registry_adapter.runs set input=input','delete from cp7_model_registry_adapter.runs'):
            assert plan.refusal(cur,lambda:cur.execute(stmt))[1]=='CP7_RUN_IMMUTABLE'
        cur.execute("create function cp7_model_registry_adapter.test_fault()returns trigger language plpgsql as $$begin raise exception 'MODEL_V2_LAST_ROW_FAULT';end$$;create trigger test_fault before insert on cp7_model_registry_adapter.runs for each row execute function cp7_model_registry_adapter.test_fault()",prepare=False)
        assert plan.refusal(cur,lambda:capture(cur,q))[1]=='MODEL_V2_LAST_ROW_FAULT'
        cur.execute('drop trigger test_fault on cp7_model_registry_adapter.runs;drop function cp7_model_registry_adapter.test_fault()',prepare=False)
        assert cur.execute('select count(*)from cp7_model_registry_adapter.runs').fetchone()[0]==1
        assert stored(cur,one['run_id'])==snapshot and plan.monetary_state(cur)==physical
        d,r,_,_=snapshot
        guard=cur.execute('select cp7_model_registry_adapter.current_guard(%s,%s,%s,%s,%s,clock_timestamp())',
         (json.dumps(d),json.dumps(r),json.dumps(dict(run_id=q['history_run_id'],source_state='UNCHANGED')),json.dumps(d['policy_source']),'0'*32)).fetchone()[0]
        assert guard['reason']=='MODEL_ENGINE_CHANGED'and guard['state']=='BASELINE_REQUIRED'
        return dict(status='PASS',actual_immutable_v2_table=True,last_row_fault_atomic=True,
         unchanged_stored_result_after_failed_capture=True,changed_engine_current_guard_baseline=True,no_stock_money_HPP_change=True)

    return list(zip(IDS['native'],(catalog,replay,clocks,source,access,atomic)))


def races(tools,today):return []
def http_cases(http,today):return []
