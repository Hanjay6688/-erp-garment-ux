"""Real concurrent SQL sessions and real Auth/PostgREST for choice metadata.

The catalog anchor repeats frozen Native6 for no new credit. No UI/forecast claim.
New stages exist only inside each disposable copy, never the installed parent.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
import copy
import uuid
import psycopg
from hashlib import sha256
from pathlib import Path
import cp7_ow12b_frozen_choice_cases as native

plan=native.plan
stage=native.stage
CONTRACT='cp7.ow12b.frozen-choice-transport10.v2'
IDS=dict(native=['OW12B_FROZEN_CHOICE_V2_TRANSPORT_CATALOG22_ANCHOR'],
         races=['OW12B_FROZEN_CHOICE_V2_RACE_SAME_UUID','OW12B_FROZEN_CHOICE_V2_RACE_REVISION',
                'OW12B_FROZEN_CHOICE_V2_RACE_ACCESS_AFTER_ENVELOPE',
                'OW12B_FROZEN_CHOICE_V2_RACE_REPLAY_ACCESS_AFTER_REQUEST',
                'OW12B_FROZEN_CHOICE_V2_RACE_ACCESS_AFTER_TARGET',
                'OW12B_FROZEN_CHOICE_V2_RACE_SOURCE_AFTER_ENVELOPE'],
         http=['OW12B_FROZEN_CHOICE_V2_AUTH_CONFIRM_CLEAR_EXACT_REPLAY',
               'OW12B_FROZEN_CHOICE_V2_AUTH_REVOKED_COMMITTED_REPLAY',
               'OW12B_FROZEN_CHOICE_V2_AUTH_ANON_AND_FOREIGN_REFERENCE'])
REQUIRED={k:len(v)for k,v in IDS.items()}
EXPECTED=DECLARED=sum(REQUIRED.values())
assert EXPECTED==10
FUNCTIONS,SCHEDULES=native.FUNCTIONS,native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
SAVE='erp_cp7_save_product_analog_choice_v2'
GET='erp_cp7_get_product_analog_choices_v1'

def sources():
    return {**native.sources(),**{p.name:sha256(p.read_bytes()).hexdigest()for p in(Path(__file__),Path(__file__).with_name('cp7_ow12b_frozen_choice_transport_probe.py'),Path(__file__).with_name('cp7_ow12b_frozen_choice_transport_preflight.py'))}}


def prepare_frozen(cur,today,actor):
    x=plan.fixture(cur,today)
    imported=native.reader.reader.volume.import_batch(cur,today,11,native.reader.reader.volume.Phases())
    historical=native.reader.reader.historical.seed(cur,imported);target=imported[0]['target']
    source=next(p['target']for p in historical if p['target'].split(':')[1]==target.split(':')[1])
    native.consumer.profile(cur,imported[0]['root'])
    # Keep another active owner while exercising current actor revocation.
    native.native.native.policy.master.role_actor(cur,'OWNER')
    f=native.fresh(cur,today,dict(x=x,target=target,source=source,subject=actor),{})
    f['payload']=native.payload(f)
    return f


def cases(cur,today):
    native.PARENT_CHECKER=PARENT_CHECKER
    for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
        setattr(native,name,globals()[name])
    return [(IDS['native'][0],native.cases(cur,today)[0][1])]


def install(cur):
    native.PARENT_CHECKER=PARENT_CHECKER
    for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
        setattr(native,name,globals()[name])
    return native.install(cur)


def counts(cur):
    plan.b.api.admin(cur)
    return cur.execute('select(select count(*)from cp7_product_analog_choice.choices),'
                       '(select count(*)from cp7_product_analog_choice.commands)').fetchone()


def races(tools,today):
    def prepare(replay=False):
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='8s'")
            install(cur)
            actor=native.native.native.policy.master.role_actor(cur,'OWNER')
            f=prepare_frozen(cur,today,actor);key=str(uuid.uuid4())
            if replay:f['committed_receipt']=native.save(cur,f,f['payload'],key)
            before,physical=counts(cur),plan.monetary_state(cur)
            conn.commit()
        return f,actor,key,before,physical

    def save(f,actor,key,backends,barrier=None,started=None):
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='8s'")
            backends.append(cur.execute('select pg_backend_pid()').fetchone()[0])
            if barrier is not None:barrier.wait(timeout=5)
            if started is not None:started.set()
            try:
                out=native.save(cur,f,copy.deepcopy(f['payload']),key)
                conn.commit();return out
            except psycopg.Error as e:
                conn.rollback();return dict(sqlstate=e.sqlstate,message=e.diag.message_primary)

    def check(before,physical,delta):
        with tools.connect()as conn,conn.cursor()as cur:
            assert counts(cur)==tuple(n+delta for n in before)
            assert plan.monetary_state(cur)==physical

    def simultaneous(same):
        f,actor,key,before,physical=prepare();backends=[];events=[Event(),Event()]
        with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=2)as pool:
            h.execute("set local statement_timeout='8s'")
            h.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
            futures=[pool.submit(save,f,actor,key if same else str(uuid.uuid4()),backends,None,event)for event in events]
            try:
                assert all(e.wait(5)for e in events)
                deadline,observed=monotonic()+5,False
                while monotonic()<deadline:
                    observed=len(set(backends))==2 and all(h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))',(pid,)).fetchone()[0]for pid in backends)
                    if observed:break
                    sleep(.03)
                assert observed,'FROZEN_CHOICE_TWO_ACTUAL_BLOCKED_WORKERS_REQUIRED'
            finally:holder.rollback()
            answers=[future.result(timeout=15)for future in futures]
        if same:
            assert answers[0]==answers[1]and answers[0].get('state')=='CONFIRMED_ASSUMPTION',answers
            assert answers[0]['contract_version']=='cp7.product-analog-choice-outcome.v2'
        else:
            assert sum(a.get('revision')=='1'for a in answers)==1,answers
            assert sum(a==dict(sqlstate='P0001',message='CP7_ANALOG_CHOICE_REVISION_CHANGED')for a in answers)==1,answers
        check(before,physical,1)
        return dict(status='PASS',two_actual_backends=True,both_actual_blocking_backends_observed=True,
                    same_UUID_exact_replay=same,different_UUID_CAS_one_winner=not same,
                    one_choice_one_command=True,no_physical_stock_money_HPP_change=True)

    def waiting(lock,source=False):
        replay=lock=='request'
        f,actor,key,before,physical=prepare(replay)
        locks=dict(envelope='FG_HPP_SALES_V2620C',request='CP7:ANALOG:REQUEST:'+actor+':'+key,
                   target='CP7:ANALOG:TARGET:'+f['target'])
        started,backends=Event(),[]
        with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=1)as pool:
            h.execute("set local statement_timeout='8s'")
            h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(locks[lock],))
            future=pool.submit(save,f,actor,key,backends,None,started)
            assert started.wait(5)
            deadline,observed=monotonic()+5,False
            try:
                while monotonic()<deadline:
                    if h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))',(backends[0],)).fetchone()[0]:
                        observed=True;break
                    sleep(.05)
                assert observed,('ANALOG_CHOICE_ACTUAL_WAIT_NOT_OBSERVED',lock)
                if source:
                    # The holder owns the same Native envelope. Its real stock
                    # writer can re-enter it; a third session would deadlock.
                    plan.found_fg(h,f['x'],'1')
                else:
                    h.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
                physical=plan.monetary_state(h)
                holder.commit()
            finally:holder.rollback()
            answer=future.result(timeout=15)
        if source:assert answer==dict(sqlstate='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED'),answer
        else:assert answer.get('sqlstate')=='42501',answer
        check(before,physical,0)
        if replay:
            with tools.connect()as conn,conn.cursor()as cur:
                plan.b.api.admin(cur)
                assert cur.execute('select result from cp7_product_analog_choice.commands where actor=%s and request_id=%s',(actor,key)).fetchone()[0]==f['committed_receipt']
        return dict(status='PASS',actual_lock_wait_observed=lock,actual_committed_replay_wait=replay,
                    access_revoked_during_wait=not source,Native_stock_changed_during_wait=source,
                    no_orphan_choice_or_command=True,two_actual_backends=True)

    return list(zip(IDS['races'],[lambda:simultaneous(True),lambda:simultaneous(False),
        lambda:waiting('envelope'),lambda:waiting('request'),lambda:waiting('target'),
        lambda:waiting('envelope',True)]))


def http_cases(http,today):
    with http.connect()as conn,conn.cursor()as cur:
        state=install(cur)
        cur.execute("notify pgrst,'reload schema'")
        conn.commit()

    def prepare(label):
        user=http.login('OWNER',label)
        with http.connect()as conn,conn.cursor()as cur:
            native.stage.verify(cur,state['current'])
            f=prepare_frozen(cur,today,user.auth_user_id)
            before,physical=counts(cur),plan.monetary_state(cur)
            conn.commit()
        return user,f,dict(p_payload=f['payload'],p_request=str(uuid.uuid4())),before,physical

    def read(user,target):
        deadline=monotonic()+5
        while True:
            reply=user.rpc(GET,dict(p_targets=[target]))
            if reply['status']!=404 or not isinstance(reply['body'],dict)or reply['body'].get('code')!='PGRST202':return reply
            if monotonic()>=deadline:return reply
            sleep(.05)

    def unchanged(before,physical,delta):
        with http.connect()as conn,conn.cursor()as cur:
            assert counts(cur)==tuple(n+delta for n in before)
            assert plan.monetary_state(cur)==physical

    def flow():
        user,f,args,before,physical=prepare('analog-choice-flow')
        initial=read(user,f['target']);assert initial['status']==200 and initial['body']['rows'][0]['state']=='UNREVIEWED',initial
        first=user.rpc(SAVE,args);repeat=user.rpc(SAVE,args)
        assert first['status']==repeat['status']==200 and first['body']==repeat['body'],(first,repeat)
        assert first['body']['state']=='CONFIRMED_ASSUMPTION'and first['body']['forecast_applied']is False
        assert first['body']['contract_version']=='cp7.product-analog-choice-outcome.v2'
        assert read(user,f['target'])['body']['rows'][0]['choice_id']==first['body']['choice_id']
        p=dict(f['payload'],action='CLEAR',source_request=None,source_hash=None,source_key=None,scale_factor=None,
               expected_revision='1',reason='Explicit real-HTTP fixture withdrawal')
        clear=user.rpc(SAVE,dict(p_payload=p,p_request=str(uuid.uuid4())))
        assert clear['status']==200 and clear['body']['state']=='CLEARED'and clear['body']['revision']=='2',clear
        assert read(user,f['target'])['body']['rows'][0]['state']=='CLEARED'
        assert user.rpc(SAVE,args)==first
        changed=user.rpc(SAVE,dict(args,p_payload=dict(f['payload'],reason='changed same UUID')))
        assert changed['status']!=200 and changed['body']['message']=='CP7_ANALOG_CHOICE_REQUEST_CHANGED',changed
        unchanged(before,physical,2)
        return dict(status='PASS',actual_Auth_PostgREST_confirm_clear_workspace=True,
                    exact_committed_UUID_replay_after_clear=True,changed_payload_same_UUID_refused=True,
                    no_physical_stock_money_HPP_change=True,forecast_applied=False)

    def revoked():
        user,f,args,before,physical=prepare('analog-choice-revoked')
        assert user.rpc(SAVE,args)['status']==200
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,))
            conn.commit()
        assert read(user,f['target'])['status']==403
        assert user.rpc(SAVE,args)['status']==403
        assert user.rpc(SAVE,dict(args,p_request=str(uuid.uuid4())))['status']==403
        unchanged(before,physical,1)
        return dict(status='PASS',actual_old_token_revoked_read_and_committed_replay_refused=True)

    def outsiders():
        user,f,args,before,physical=prepare('analog-choice-owner')
        other=http.login('OWNER','analog-choice-other')
        assert http.anon_rpc(GET,dict(p_targets=[f['target']]))['status']in(401,403)
        assert http.anon_rpc(SAVE,args)['status']in(401,403)
        # Configuration is shared with authorized readers. The request's
        # immutable analysis snapshot is still private to its capturing actor.
        workspace=read(other,f['target']);assert workspace['status']==200,workspace
        p=dict(f['payload'],access_epoch=workspace['body']['access_epoch'])
        foreign=other.rpc(SAVE,dict(p_payload=p,p_request=str(uuid.uuid4())))
        assert foreign['status']==403 and foreign['body']['message']=='CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE',foreign
        unchanged(before,physical,0)
        return dict(status='PASS',anonymous_both_facades_denied=True,
                    authorized_shared_config_read=True,foreign_actor_own_epoch_cannot_confirm_private_reference=True)

    return list(zip(IDS['http'],[flow,revoked,outsiders]))
