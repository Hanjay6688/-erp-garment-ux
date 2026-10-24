"""Real concurrent SQL sessions and real Auth/PostgREST for choice metadata.

The catalog anchor repeats Native6 for no new credit. No UI/forecast claim.
New stages exist only inside each disposable copy, never the installed parent.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic, sleep
import copy
import uuid
import psycopg
import cp7_ow11_analog_choice_cases as native

plan=native.plan
stage=native.stage
CONTRACT='cp7.ow11.analog-choice-transport.v1'
IDS=dict(native=[native.IDS['native'][0]],
         races=['OW11_ANALOG_CHOICE_RACE_SAME_UUID','OW11_ANALOG_CHOICE_RACE_REVISION',
                'OW11_ANALOG_CHOICE_RACE_ACCESS_AFTER_ENVELOPE',
                'OW11_ANALOG_CHOICE_RACE_REPLAY_ACCESS_AFTER_REQUEST',
                'OW11_ANALOG_CHOICE_RACE_ACCESS_AFTER_TARGET',
                'OW11_ANALOG_CHOICE_RACE_SOURCE_AFTER_ENVELOPE'],
         http=['OW11_ANALOG_CHOICE_AUTH_CONFIRM_CLEAR_EXACT_REPLAY',
               'OW11_ANALOG_CHOICE_AUTH_REVOKED_COMMITTED_REPLAY',
               'OW11_ANALOG_CHOICE_AUTH_ANON_AND_FOREIGN_REFERENCE'])
REQUIRED={k:len(v)for k,v in IDS.items()}
EXPECTED=DECLARED=sum(REQUIRED.values())
assert EXPECTED==10
FUNCTIONS,SCHEDULES=native.FUNCTIONS,native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
SAVE='erp_cp7_save_product_analog_choice_v1'
GET='erp_cp7_get_product_analog_choices_v1'


def cases(cur,today):
    native.PARENT_CHECKER=PARENT_CHECKER
    return native.cases(cur,today)[:1]


def install(cur):
    native.PARENT_CHECKER=PARENT_CHECKER
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
            actor=native.bounded.work.base.retained.master.role_actor(cur,'OWNER')
            f=native.prepare(cur,today,actor);key=str(uuid.uuid4())
            if replay:native.save(cur,f['payload'],key,actor)
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
                out,_=native.save(cur,copy.deepcopy(f['payload']),key,actor)
                conn.commit();return out
            except psycopg.Error as e:
                conn.rollback();return dict(sqlstate=e.sqlstate,message=e.diag.message_primary)

    def check(before,physical,delta):
        with tools.connect()as conn,conn.cursor()as cur:
            assert counts(cur)==tuple(n+delta for n in before)
            assert plan.monetary_state(cur)==physical

    def simultaneous(same):
        f,actor,key,before,physical=prepare()
        barrier,backends=Barrier(2),[]
        with ThreadPoolExecutor(max_workers=2)as pool:
            answers=list(pool.map(lambda _:save(f,actor,key if same else str(uuid.uuid4()),backends,barrier),range(2)))
        assert len(set(backends))==2,backends
        if same:assert answers[0]==answers[1]and answers[0].get('state')=='CONFIRMED_ASSUMPTION',answers
        else:
            assert sum(a.get('revision')=='1'for a in answers)==1,answers
            assert sum(a==dict(sqlstate='P0001',message='CP7_ANALOG_CHOICE_REVISION_CHANGED')for a in answers)==1,answers
        check(before,physical,1)
        return dict(status='PASS',two_actual_backends=True,same_UUID_exact_replay=same,
                    different_UUID_CAS_one_winner=not same,one_choice_one_command=True,
                    no_physical_stock_money_HPP_change=True)

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
        return dict(status='PASS',actual_lock_wait_observed=lock,actual_committed_replay_wait=replay,
                    access_revoked_during_wait=not source,Native_stock_changed_during_wait=source,
                    no_orphan_choice_or_command=True,two_actual_backends=True)

    return list(zip(IDS['races'],[lambda:simultaneous(True),lambda:simultaneous(False),
        lambda:waiting('envelope'),lambda:waiting('request'),lambda:waiting('target'),
        lambda:waiting('envelope',True)]))


def http_cases(http,today):
    with http.connect()as conn,conn.cursor()as cur:
        _,_,state=install(cur)
        cur.execute("notify pgrst,'reload schema'")
        conn.commit()

    def prepare(label):
        user=http.login('OWNER',label)
        with http.connect()as conn,conn.cursor()as cur:
            native.stage.verify(cur,state)
            f=native.prepare(cur,today,user.auth_user_id)
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
