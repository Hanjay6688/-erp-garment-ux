"""Predeclared actual policy Auth and two-backend controls; no activation claim."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Event
from time import monotonic,sleep
from copy import deepcopy
import uuid
import psycopg
import cp7_ow11_model_policy_cases as native

plan,stage=native.plan,native.stage
CONTRACT='cp7.ow11.model-policy-transport.v1'
IDS=dict(native=[native.IDS['native'][0]],races=[
 'OW11_MODEL_POLICY_RACE_SAME_UUID','OW11_MODEL_POLICY_RACE_REVISION',
 'OW11_MODEL_POLICY_RACE_ACCESS_AFTER_ENVELOPE','OW11_MODEL_POLICY_RACE_REPLAY_AFTER_REQUEST',
 'OW11_MODEL_POLICY_RACE_ACCESS_AFTER_POLICY','OW11_MODEL_POLICY_RACE_ROLE_CHANGE_AFTER_ENVELOPE'],
 http=['OW11_MODEL_POLICY_AUTH_SET_SUSPEND_EXACT_REPLAY','OW11_MODEL_POLICY_AUTH_REVOKED_COMMITTED_REPLAY',
       'OW11_MODEL_POLICY_AUTH_ANON_READER_FOREIGN_EPOCH'])
REQUIRED={k:len(v)for k,v in IDS.items()}
EXPECTED=DECLARED=sum(REQUIRED.values())
assert EXPECTED==10
FUNCTIONS,SCHEDULES=native.FUNCTIONS,native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
GET,SAVE='erp_cp7_get_model_activation_policy_v1','erp_cp7_save_model_activation_policy_v1'


def cases(cur,today):
    native.PARENT_CHECKER=PARENT_CHECKER
    return native.cases(cur,today)[:1]


def install(cur):
    native.PARENT_CHECKER=PARENT_CHECKER
    return native.install(cur)


def counts(cur):
    plan.b.api.admin(cur)
    return cur.execute('select(select count(*)from cp7_model_policy.policies),'
      '(select count(*)from cp7_model_policy.commands),(select count(*)from cp7_model_native.registry)').fetchone()


def races(tools,today):
    def prepare(replay=False):
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='8s'");install(cur)
            actor=native.master.role_actor(cur,'OWNER');payload=native.payload(cur,actor);key=str(uuid.uuid4())
            if replay:native.save(cur,payload,actor,key)
            before,physical=counts(cur),plan.monetary_state(cur);conn.commit()
        return payload,actor,key,before,physical

    def save(payload,actor,key,backends,barrier=None,started=None):
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='8s'");backends.append(cur.execute('select pg_backend_pid()').fetchone()[0])
            if barrier is not None:barrier.wait(timeout=5)
            if started is not None:started.set()
            try:
                out=native.save(cur,deepcopy(payload),actor,key);conn.commit();return out
            except psycopg.Error as e:
                conn.rollback();return dict(sqlstate=e.sqlstate,message=e.diag.message_primary)

    def check(before,physical,delta):
        with tools.connect()as conn,conn.cursor()as cur:
            assert counts(cur)==tuple(x+delta for x in before)
            assert plan.monetary_state(cur)==physical

    def simultaneous(same):
        payload,actor,key,before,physical=prepare();barrier,backends=Barrier(2),[]
        with ThreadPoolExecutor(max_workers=2)as pool:
            answers=list(pool.map(lambda _:save(payload,actor,key if same else str(uuid.uuid4()),backends,barrier),range(2)))
        assert len(set(backends))==2,backends
        if same:assert answers[0]==answers[1]and answers[0].get('policy',{}).get('state')=='ACTIVE',answers
        else:
            assert sum(a.get('policy',{}).get('revision')=='1'for a in answers)==1,answers
            assert sum(a==dict(sqlstate='P0001',message='CP7_MODEL_POLICY_REVISION_CHANGED')for a in answers)==1,answers
        check(before,physical,1)
        return dict(status='PASS',two_actual_backends=True,same_UUID_exact_replay=same,CAS_one_winner=not same,
         one_policy_one_command_one_registry=True,no_physical_stock_money_HPP_change=True)

    def waiting(lock,role_change=False):
        replay=lock=='request';payload,actor,key,before,physical=prepare(replay)
        locks=dict(envelope='FG_HPP_SALES_V2620C',request='CP7:MODEL:POLICY:REQUEST:'+actor+':'+key,policy='CP7:MODEL:POLICY:GLOBAL')
        started,backends=Event(),[]
        with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=1)as pool:
            h.execute("set local statement_timeout='8s'");h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(locks[lock],))
            future=pool.submit(save,payload,actor,key,backends,None,started);assert started.wait(5)
            deadline,observed=monotonic()+5,False
            try:
                while monotonic()<deadline:
                    if h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))',(backends[0],)).fetchone()[0]:observed=True;break
                    sleep(.05)
                assert observed,('MODEL_POLICY_ACTUAL_WAIT_NOT_OBSERVED',lock)
                if role_change:
                    h.execute("update erp.app_users set role='AUDITOR_VIEW_ONLY',role_id=(select id from erp.app_roles where role_code='AUDITOR_VIEW_ONLY')where auth_user_id=%s",(actor,))
                else:h.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
                holder.commit()
            finally:holder.rollback()
            answer=future.result(timeout=15)
        assert answer.get('sqlstate')=='42501',answer;check(before,physical,0)
        return dict(status='PASS',actual_lock_wait_observed=lock,two_actual_backends=True,
         actual_committed_replay_wait=replay,current_role_change=role_change,current_deactivation=not role_change,
         current_access_before_saved_replay=True,no_orphan_registry_policy_command=True)

    return list(zip(IDS['races'],[lambda:simultaneous(True),lambda:simultaneous(False),
      lambda:waiting('envelope'),lambda:waiting('request'),lambda:waiting('policy'),lambda:waiting('envelope',True)]))


def http_cases(http,today):
    with http.connect()as conn,conn.cursor()as cur:
        state=install(cur);cur.execute("notify pgrst,'reload schema'");conn.commit()

    def read(user):
        deadline=monotonic()+5
        while True:
            r=user.rpc(GET,{})
            if r['status']!=404 or not isinstance(r['body'],dict)or r['body'].get('code')!='PGRST202':return r
            if monotonic()>=deadline:return r
            sleep(.05)

    def prepare(label):
        user=http.login('OWNER',label);w=read(user);assert w['status']==200,w
        p=dict(contract_version='cp7.model-activation-policy-command.v1',action='SET',config=deepcopy(native.CONFIG),
         template_hash=w['body']['model_template']['hash'],reason='Explicit SYNTHETIC HTTP policy fixture',reviewed=True,
         expected_revision=w['body']['revision'],access_epoch=w['body']['access_epoch'])
        with http.connect()as conn,conn.cursor()as cur:
            stage.verify(cur,state);before,physical=counts(cur),plan.monetary_state(cur)
        return user,p,dict(p_payload=p,p_request=str(uuid.uuid4())),before,physical

    def unchanged(before,physical,delta):
        with http.connect()as conn,conn.cursor()as cur:
            assert counts(cur)==tuple(x+delta for x in before)and plan.monetary_state(cur)==physical

    def flow():
        user,p,args,before,physical=prepare('policy-flow');first=user.rpc(SAVE,args)
        assert first['status']==200 and first['body']['policy']['state']=='ACTIVE',first
        assert user.rpc(SAVE,args)==first and first['body']['forecast_applied']is False
        w=read(user);assert w['status']==200 and w['body']['current']['policy']==first['body']['policy']
        clear=dict(p,action='SUSPEND',config=None,template_hash=None,expected_revision=first['body']['policy']['revision'],reason='Explicit HTTP withdrawal')
        second=user.rpc(SAVE,dict(p_payload=clear,p_request=str(uuid.uuid4())))
        assert second['status']==200 and second['body']['policy']['state']=='SUSPENDED',second
        assert second['body']['policy']['config']==first['body']['policy']['config']and user.rpc(SAVE,args)==first
        changed=user.rpc(SAVE,dict(args,p_payload=dict(p,reason='Changed same UUID')))
        assert changed['status']!=200 and changed['body']['message']=='CP7_MODEL_POLICY_REQUEST_CHANGED',changed
        assert read(user)['body']['state']=='SUSPENDED';unchanged(before,physical,2)
        return dict(status='PASS',actual_Auth_PostgREST_SET_SUSPEND=True,exact_UUID_after_withdrawal=True,
         changed_payload_refused=True,no_physical_stock_money_HPP_change=True,forecast_applied=False)

    def revoked():
        user,p,args,before,physical=prepare('policy-revoked');assert user.rpc(SAVE,args)['status']==200
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));conn.commit()
        assert read(user)['status']==403 and user.rpc(SAVE,args)['status']==403;unchanged(before,physical,1)
        return dict(status='PASS',actual_old_token_read_and_committed_replay_refused=True)

    def outsiders():
        user,p,args,before,physical=prepare('policy-owner');other=http.login('OWNER','policy-other');auditor=http.login('AUDITOR_VIEW_ONLY','policy-auditor')
        assert http.anon_rpc(GET,{})['status']in(401,403)and http.anon_rpc(SAVE,args)['status']in(401,403)
        assert auditor.rpc(SAVE,args)['status']==403
        w=read(other);assert w['status']==200,w
        foreign=other.rpc(SAVE,args);assert foreign['status']==403 and foreign['body']['message']=='CP7_MODEL_POLICY_ACCESS_CHANGED',foreign
        own=dict(p,access_epoch=w['body']['access_epoch']);accepted=other.rpc(SAVE,dict(p_payload=own,p_request=str(uuid.uuid4())))
        assert accepted['status']==200 and accepted['body']['actor_scope_id']==other.auth_user_id,accepted
        unchanged(before,physical,1)
        return dict(status='PASS',anonymous_facades_denied=True,reader_write_denied=True,foreign_epoch_refused=True,
         authorized_global_policy_shared_with_other_owner=True)

    return list(zip(IDS['http'],[flow,revoked,outsiders]))
