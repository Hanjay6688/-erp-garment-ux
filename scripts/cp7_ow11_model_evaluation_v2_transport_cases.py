"""Actual v2 capture races and Auth HTTP, with immutable old assessments."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Event
from time import monotonic,sleep
from copy import deepcopy
import uuid
import psycopg
import cp7_ow11_model_evaluation_v2_cases as native

plan,stage,policy,legacy=native.plan,native.stage,native.policy,native.legacy
CONTRACT='cp7.ow11.model-evaluation-v2-transport.v1'
IDS=dict(native=[native.IDS['native'][0]],races=[
 'OW11_MODEL_V2_RACE_SAME_UUID','OW11_MODEL_V2_RACE_CHANGED_SAME_UUID',
 'OW11_MODEL_V2_RACE_ACCESS_AFTER_ENVELOPE','OW11_MODEL_V2_RACE_REPLAY_AFTER_REQUEST',
 'OW11_MODEL_V2_RACE_POLICY_AFTER_ENVELOPE','OW11_MODEL_V2_RACE_SOURCE_AFTER_ENVELOPE'],
 http=['OW11_MODEL_V2_AUTH_CAPTURE_READ_EXACT_REPLAY','OW11_MODEL_V2_AUTH_REVOKED_FOREIGN_ANON',
 'OW11_MODEL_V2_AUTH_CURRENT_POLICY_AND_POSTED_SOURCE'])
REQUIRED={k:len(v)for k,v in IDS.items()}
EXPECTED=DECLARED=sum(REQUIRED.values())
assert EXPECTED==10
FUNCTIONS,SCHEDULES=native.FUNCTIONS,native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
CAPTURE,READ='erp_cp7_capture_model_evaluation_v2','erp_cp7_read_model_evaluation_v2'


def cases(cur,today):
    native.PARENT_CHECKER=PARENT_CHECKER
    return native.cases(cur,today)[:1]


def install(cur):
    native.PARENT_CHECKER=PARENT_CHECKER
    return native.install(cur)


def count(cur):
    plan.b.api.admin(cur)
    return cur.execute('select count(*)from cp7_model_registry_adapter.runs').fetchone()[0]


def races(tools,today):
    def prepare(replay=False):
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='8s'");install(cur)
            actor=policy.master.role_actor(cur,'OWNER');f,_,q=legacy.prepared(cur,today,12,actor);key=str(uuid.uuid4())
            if replay:native.capture(cur,q,actor,key)
            before,physical=count(cur),plan.monetary_state(cur);conn.commit()
        return f,q,actor,key,before,physical

    def capture(q,actor,key,backends,barrier=None,started=None):
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='8s'");backends.append(cur.execute('select pg_backend_pid()').fetchone()[0])
            if barrier is not None:barrier.wait(timeout=5)
            if started is not None:started.set()
            try:
                out=native.capture(cur,deepcopy(q),actor,key);conn.commit();return out
            except psycopg.Error as e:
                conn.rollback();return dict(sqlstate=e.sqlstate,message=e.diag.message_primary)

    def check(before,physical,delta):
        with tools.connect()as conn,conn.cursor()as cur:
            assert count(cur)==before+delta
            assert plan.monetary_state(cur)==physical

    def simultaneous(changed):
        _,q,actor,key,before,physical=prepare();barrier,backends=Barrier(2),[]
        queries=[q,dict(q,horizon_days='2')if changed else q]
        with ThreadPoolExecutor(max_workers=2)as pool:
            answers=list(pool.map(lambda query:capture(query,actor,key,backends,barrier),queries))
        assert len(set(backends))==2,backends
        if changed:
            assert sum(a.get('contract_version')=='cp7.native-model-run.v2'for a in answers)==1,answers
            assert sum(a==dict(sqlstate='P0001',message='CP7_MODEL_V2_REQUEST_CHANGED')for a in answers)==1,answers
        else:
            native.unchanged(*answers);assert answers[0]['current_guard']['state']=='BASELINE_REQUIRED'
        check(before,physical,1)
        return dict(status='PASS',two_actual_backends=True,one_UUID_one_immutable_run=True,
         exact_replay=not changed,changed_same_UUID_one_refusal=changed,no_physical_stock_money_HPP_change=True)

    def waiting(kind):
        replay=kind=='request';f,q,actor,key,before,physical=prepare(replay)
        lock='CP7:MODEL:EVALUATION:V2:'+actor+':'+key if replay else'FG_HPP_SALES_V2620C'
        started,backends=Event(),[];changed_policy=None
        with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=1)as pool:
            h.execute("set local statement_timeout='8s'");h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(lock,))
            future=pool.submit(capture,q,actor,key,backends,None,started);assert started.wait(5)
            deadline,observed=monotonic()+5,False
            try:
                while monotonic()<deadline:
                    if h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))',(backends[0],)).fetchone()[0]:observed=True;break
                    sleep(.05)
                assert observed,('MODEL_V2_ACTUAL_WAIT_NOT_OBSERVED',kind)
                if kind=='policy':changed_policy=policy.save(h,policy.payload(h,actor),actor)
                elif kind=='source':legacy.previous.sales.fg.post_sale(h,f['draft']);physical=plan.monetary_state(h)
                else:h.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
                holder.commit()
            finally:holder.rollback()
            answer=future.result(timeout=15)
        if kind=='policy':
            assert changed_policy and answer['assessment']['policy_source']is None,answer
            assert answer['assessment']['activation']['reason']=='ACTIVATION_POLICY_CHANGED'
            assert answer['current_guard']['state']=='BASELINE_REQUIRED';check(before,physical,1)
        elif kind=='source':
            assert answer==dict(sqlstate='P0001',message='CP7_MODEL_V2_HISTORY_STALE'),answer;check(before,physical,0)
        else:assert answer.get('sqlstate')=='42501',answer;check(before,physical,0)
        return dict(status='PASS',actual_lock_wait_observed=kind,two_actual_backends=True,
         actual_committed_replay_wait=replay,current_policy_after_wait=kind=='policy',
         current_posted_source_after_wait=kind=='source',current_access_after_wait=kind in('envelope','request'),
         no_orphan_model_run=True,forecast_applied=False)

    return list(zip(IDS['races'],[lambda:simultaneous(False),lambda:simultaneous(True),
      lambda:waiting('envelope'),lambda:waiting('request'),lambda:waiting('policy'),lambda:waiting('source')]))


def http_cases(http,today):
    with http.connect()as conn,conn.cursor()as cur:
        _,state=install(cur);cur.execute("notify pgrst,'reload schema'");conn.commit()

    def send(user,name,args):
        deadline=monotonic()+5
        while True:
            r=user.rpc(name,args)
            if r['status']!=404 or not isinstance(r['body'],dict)or r['body'].get('code')!='PGRST202':return r
            if monotonic()>=deadline:return r
            sleep(.05)

    def prepare(label):
        user=http.login('OWNER',label)
        with http.connect()as conn,conn.cursor()as cur:
            stage.verify(cur,state);f=legacy.previous.fixture(cur,today);conn.commit()
        h=send(user,'erp_cp7_capture_demand_history_v1',dict(p_query=legacy.previous.query(today,12),p_request=str(uuid.uuid4())))
        assert h['status']==200,h;q=legacy.query(h['body'],f)
        with http.connect()as conn,conn.cursor()as cur:before,physical=count(cur),plan.monetary_state(cur)
        return user,f,dict(p_query=q,p_request=str(uuid.uuid4())),before,physical

    def unchanged(before,physical,delta):
        with http.connect()as conn,conn.cursor()as cur:
            assert count(cur)==before+delta and plan.monetary_state(cur)==physical

    def flow():
        user,_,args,before,physical=prepare('model-v2-flow');first=send(user,CAPTURE,args)
        assert first['status']==200,first;second=send(user,CAPTURE,args);assert second['status']==200,second
        native.unchanged(first['body'],second['body']);read=send(user,READ,dict(p_run=first['body']['run_id']));assert read['status']==200;native.unchanged(first['body'],read['body'])
        assert first['body']['current_guard']['state']=='BASELINE_REQUIRED'and first['body']['forecast_applied']is False
        changed=send(user,CAPTURE,dict(args,p_query=dict(args['p_query'],horizon_days='2')))
        assert changed['status']!=200 and changed['body']['message']=='CP7_MODEL_V2_REQUEST_CHANGED',changed
        for key in('policy','forecast','series','actor'):
            bad=send(user,CAPTURE,dict(p_request=str(uuid.uuid4()),p_query=dict(args['p_query'],**{key:'forged'})))
            assert bad['status']!=200,bad
        unchanged(before,physical,1)
        return dict(status='PASS',actual_Auth_capture_read_replay_immutable=True,exact_changed_payload_and_closed_query_refused=True,no_business_effect=True)

    def outsiders():
        user,_,args,before,physical=prepare('model-v2-revoked');one=send(user,CAPTURE,args);assert one['status']==200
        read_args=dict(p_run=one['body']['run_id']);other=http.login('OWNER','model-v2-other')
        assert http.anon_rpc(READ,read_args)['status']in(401,403)and http.anon_rpc(CAPTURE,args)['status']in(401,403)
        assert send(other,READ,read_args)['status']!=200 and send(other,CAPTURE,args)['status']!=200
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));conn.commit()
        assert send(user,READ,read_args)['status']==403 and send(user,CAPTURE,args)['status']==403
        unchanged(before,physical,1)
        return dict(status='PASS',actual_old_token_read_and_committed_replay_refused=True,foreign_run_history_and_anonymous_refused=True)

    def current():
        user,f,args,before,physical=prepare('model-v2-current');one=send(user,CAPTURE,args);assert one['status']==200
        w=send(user,'erp_cp7_get_model_activation_policy_v1',{});assert w['status']==200
        payload=dict(contract_version='cp7.model-activation-policy-command.v1',action='SET',config=deepcopy(policy.CONFIG),template_hash=w['body']['model_template']['hash'],reason='Explicit SYNTHETIC HTTP policy',reviewed=True,expected_revision=w['body']['revision'],access_epoch=w['body']['access_epoch'])
        saved=send(user,'erp_cp7_save_model_activation_policy_v1',dict(p_payload=payload,p_request=str(uuid.uuid4())));assert saved['status']==200,saved
        old=send(user,READ,dict(p_run=one['body']['run_id']));assert old['status']==200;native.unchanged(one['body'],old['body']);assert old['body']['current_guard']['reason']=='ACTIVATION_POLICY_CHANGED';unchanged(before,physical,1)
        with http.connect()as conn,conn.cursor()as cur:
            legacy.previous.sales.fg.post_sale(cur,f['draft']);physical=plan.monetary_state(cur);conn.commit()
        stale=send(user,READ,dict(p_run=one['body']['run_id']));assert stale['status']==200;native.unchanged(one['body'],stale['body']);assert stale['body']['current_guard']['reason']=='NATIVE_HISTORY_SOURCE_CHANGED'
        blocked=send(user,CAPTURE,dict(args,p_request=str(uuid.uuid4())));assert blocked['status']!=200 and blocked['body']['message']=='CP7_MODEL_V2_HISTORY_STALE',blocked
        unchanged(before,physical,1)
        return dict(status='PASS',current_policy_change_retires_old_model=True,actual_posted_sale_retires_source=True,old_assessment_immutable=True,stale_new_capture_refused=True,forecast_applied=False)

    return list(zip(IDS['http'],[flow,outsiders,current]))
