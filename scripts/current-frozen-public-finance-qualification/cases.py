"""Actual bounded finance Auth and two-backend races on the full model chain.

Private finance advancement is labelled SQL preparation, never actual cron or
an HTTP step. Every request under test uses the unchanged public bounded RPC.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Event
from time import monotonic,sleep
from pathlib import Path
import importlib.util,json,uuid
import psycopg
import cp7_current_frozen_public_installation as product
import cp7_ow13c_bounded_stage_cases as bounded
import cp7_p21_current_chain_rehearsal_probe as chain

p=Path(__file__).resolve().parents[1]/'current-bounded-finance-native-qualification/cases.py'
spec=importlib.util.spec_from_file_location('retained_bounded_finance_native_helpers',p)
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
staged,finance,plan=native.staged,native.finance,bounded.plan
REQUEST='erp_cp7_request_bounded_frozen_finance_analysis_v2'
OPERATIONAL='erp_cp7_request_bounded_staged_analysis_v2'
STATUS='erp_cp7_get_staged_analysis_v1'
IDS=dict(http=['CURRENT_FINANCE_AUTH_PUBLIC_FLOW_READY_REPLAY',
 'CURRENT_FINANCE_AUTH_PERMISSION_WITHDRAWAL_SEALED_HISTORY',
 'CURRENT_FINANCE_AUTH_FOREIGN_ANON_CLOSED_QUERY'],
 races=['CURRENT_FINANCE_RACE_SAME_UUID','CURRENT_FINANCE_RACE_CROSS_MODE_UUID',
 'CURRENT_FINANCE_RACE_CHANGED_QUERY_UUID','CURRENT_FINANCE_RACE_PERMISSION_AFTER_REQUEST',
 'CURRENT_FINANCE_RACE_REPLAY_PERMISSION_AFTER_REQUEST','CURRENT_FINANCE_RACE_ACTOR_AFTER_REQUEST',
 'CURRENT_FINANCE_RACE_NATIVE_BOOK_AFTER_REQUEST'])
STATE=None
COPY_SETUP_ADMISSIONS=[]


def installed(cur):
    assert STATE is not None,'FULL_CURRENT_FINANCE_MODEL_INSTALLATION_REQUIRED'
    staged.b.api.admin(cur)
    db=cur.execute('select current_database()').fetchone()[0]
    assert db in('cp6_auditor_http','cp6_auditor_race')
    actual=product.catalog._catalog_rows(cur);expected=STATE['after']
    assert len(actual)==len(expected)==22 and set(actual)==set(expected)
    changes={g:sorted(k for k in set(actual[g])|set(expected[g])if actual[g].get(k)!=expected[g].get(k))
        for g in expected if actual[g]!=expected[g]}
    if changes:
        assert db=='cp6_auditor_race'and changes=={'schemas':['erp']},changes
        before,after=expected['schemas']['erp'],actual['schemas']['erp']
        assert before[0]==after[0]
        assert [x for x in after[1]if x not in before[1]]==[['authenticated',before[0],'USAGE',False]]
        assert not[x for x in before[1]if x not in after[1]]
    with chain.helper.control.product_catalog(cur):proof=product.verify(cur,STATE)
    assert product.catalog._catalog_rows(cur)==actual
    COPY_SETUP_ADMISSIONS.append(dict(database=db,actual_full22_changes=changes,
        actual_current_product_verification=proof,product_catalog_projection=False))


def prepare_fixture(cur,today):
    installed(cur)
    acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
    had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    if not had:cur.execute('grant usage on schema erp to authenticated')
    native.setup(cur,today)
    staged.b.api.admin(cur)
    if not had:cur.execute('revoke usage on schema erp from authenticated')
    assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl


def query(today):return dict(staged.query(today),finance_mode='STAGED')


def counts(cur):
    staged.b.api.admin(cur)
    return cur.execute('select(select count(*)from cp7_analysis_stage.jobs),'
        '(select count(*)from cp7_analysis_stage.capture_marks),'
        '(select count(*)from cp7_finance_capture.captures)').fetchone()


def request(cur,today,key,actor,kind='finance',changed=False):
    q=query(today)if kind=='finance'else staged.query(today)
    if changed:q['group_mode']='RESTATED'
    return staged.checked(staged.limited(cur,REQUEST if kind=='finance'else OPERATIONAL,
        (json.dumps(q),key),actor),key)


def ready(cur,key,actor):
    job=staged.status(cur,key,actor);cid=native.sidecar(job,key,'RUNNING')['capture']['capture_id']
    result,_=native.run_capture(cur,cid,actor);assert result['state']=='READY',result
    job=staged.status(cur,key,actor);side=native.sidecar(job,key,'READY')
    source=finance.call(cur,'select cp7_finance_capture.result(%s)',(cid,),actor)
    signature,rows=finance.independent_signature(cur,source['dates']['as_of'])
    assert signature==source['book_signature']
    assert rows=={family:source['capture']['plan'][family]['rows']for family in finance.FAMILIES}
    official=finance.official(cur,source['dates'])
    for name in('performance','financial_position','basis','data_confidence'):
        assert source['report']['snapshot'][name]==official['snapshot'][name],name
    metrics,readiness=finance.metrics(cur,source)
    assert len(metrics)==24
    assert{m['metric_id']:m['value']for m in side['result']['metrics']}==metrics
    assert side['result']['readiness']==readiness
    assert all('value'not in value for value in metrics.values()if value['state']=='UNKNOWN')
    return job,native.stored_capture(cur,cid)


def races(tools,today):
    def prepare(replay=False):
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='8s'")
            prepare_fixture(cur,today)
            actor,role=finance.finance_cases.admin_actor(cur,staged.analysis)
            key=str(uuid.uuid4());sealed=None
            if replay:
                request(cur,today,key,actor);_,sealed=ready(cur,key,actor)
            before,physical=counts(cur),plan.monetary_state(cur);conn.commit()
        return actor,role,key,before,physical,sealed

    def send(actor,key,backends,barrier=None,started=None,kind='finance',changed=False):
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='8s'")
            backends.append(cur.execute('select pg_backend_pid()').fetchone()[0])
            if barrier is not None:barrier.wait(timeout=5)
            if started is not None:started.set()
            start=monotonic()
            try:
                answer=request(cur,today,key,actor,kind,changed);conn.commit()
            except psycopg.Error as e:
                conn.rollback();answer=dict(sqlstate=e.sqlstate,message=e.diag.message_primary)
            assert(monotonic()-start)*1000<8000,'BOUNDED_FINANCE_REQUEST_OVER8S'
            return answer

    def check(before,physical,delta):
        with tools.connect()as conn,conn.cursor()as cur:
            assert counts(cur)==tuple(a+b for a,b in zip(before,delta)),(before,counts(cur),delta)
            assert plan.monetary_state(cur)==physical

    def simultaneous(kind):
        actor,_,key,before,physical,_=prepare();backends=[];barrier=Barrier(2)
        with ThreadPoolExecutor(max_workers=2)as pool:
            futures=[pool.submit(send,actor,key,backends,barrier,None,
                'operational'if kind=='cross_mode'and n else'finance',kind=='changed_query'and n==1)for n in range(2)]
            answers=[f.result(timeout=15)for f in futures]
        assert len(set(backends))==2
        if kind=='same':assert answers[0]==answers[1]and answers[0].get('state')=='RUNNING',answers
        else:
            assert sum(a.get('state')=='RUNNING'for a in answers)==1,answers
            assert sum(a==dict(sqlstate='P0001',message='CP7_ANALYSIS_REQUEST_CHANGED')for a in answers)==1,answers
        winner=next(a for a in answers if a.get('state')=='RUNNING')
        finance_count=int('finance_capture'in winner)
        if finance_count:native.sidecar(winner,key,'RUNNING')
        check(before,physical,(1,1,finance_count))
        return dict(status='PASS',two_actual_backends=True,one_job_one_capture_mark=True,
            finance_captures=finance_count,mode=kind,no_orphan_capture=True,no_physical_stock_money_HPP_change=True)

    def waiting(kind):
        replay=kind=='replay_permission'
        actor,role,key,before,physical,sealed=prepare(replay)
        backends=[];started=Event()
        with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=1)as pool:
            h.execute("set local statement_timeout='8s'")
            h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',('CP7:ANALYSIS-REQUEST:'+actor+':'+key,))
            future=pool.submit(send,actor,key,backends,None,started)
            assert started.wait(5)
            observed=False;deadline=monotonic()+5
            try:
                while monotonic()<deadline:
                    if h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))',(backends[0],)).fetchone()[0]:
                        observed=True;break
                    sleep(.03)
                assert observed,'ACTUAL_BOUNDED_FINANCE_REQUEST_WAIT_NOT_OBSERVED'
                if kind=='source':finance.given(h,today,'900.00')
                elif kind=='actor':h.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,));assert h.rowcount==1
                else:
                    h.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(role,));assert h.rowcount==1
                physical=plan.monetary_state(h);holder.commit()
            finally:holder.rollback()
            answer=future.result(timeout=15)
        if kind=='source':
            assert answer.get('state')=='RUNNING',answer
            check(before,physical,(1,1,1))
            with tools.connect()as conn,conn.cursor()as cur:
                ready(cur,key,actor);assert plan.monetary_state(cur)==physical;conn.commit()
        else:
            assert answer.get('sqlstate')=='42501',answer
            check(before,physical,(0,0,0))
            if replay:
                with tools.connect()as conn,conn.cursor()as cur:
                    assert native.stored_capture(cur,sealed['id'])==sealed
        return dict(status='PASS',actual_request_lock_wait_observed=True,two_actual_backends=True,
            change=kind,committed_replay=replay,no_orphan_job_mark_or_capture=True,
            old_capture_immutable=replay,source_after_wait_official_parity=kind=='source',
            private_finance_advancement_not_actual_cron=kind=='source')

    return list(zip(IDS['races'],[lambda:simultaneous('same'),lambda:simultaneous('cross_mode'),
        lambda:simultaneous('changed_query'),lambda:waiting('permission'),lambda:waiting('replay_permission'),
        lambda:waiting('actor'),lambda:waiting('source')]))


def http_cases(http,today):
    shared={}
    timings=[]
    def call(user,name,payload):
        started=monotonic();response=user.rpc(name,payload)
        elapsed=(monotonic()-started)*1000
        timings.append(dict(rpc=name,status=response['status'],millis=round(elapsed,3)))
        assert elapsed<8000,('BOUNDED_FINANCE_HTTP_OVER8S',name,elapsed)
        return response

    def ok(user,name,payload):
        response=call(user,name,payload);assert response['status']==200,(name,response)
        return response['body']

    def prepare(role,label):
        user=http.login(role,label)
        with http.connect()as conn,conn.cursor()as cur:
            prepare_fixture(cur,today);physical=plan.monetary_state(cur);before=counts(cur)
            conn.commit()
        return user,dict(p_query=query(today),p_request=str(uuid.uuid4())),before,physical

    def flow():
        owner,args,before,physical=prepare('OWNER','current-finance-owner')
        key=args['p_request'];first=ok(owner,REQUEST,args);native.sidecar(first,key,'RUNNING')
        assert ok(owner,REQUEST,args)==first
        job=first;calls=0
        while job['state']=='RUNNING':
            assert calls<staged.DRIVER_CALLS
            job=ok(owner,'erp_cp7_step_staged_analysis_v1',dict(p_request=key));calls+=1
        assert job['state']=='DONE';native.sidecar(job,key,'RUNNING')
        page_args=dict(p_run=job['run_id'])
        pages=ok(owner,'erp_cp7_read_staged_analysis_pages_v1',page_args)
        with http.connect()as conn,conn.cursor()as cur:
            status,sealed=ready(cur,key,owner.auth_user_id)
            assert counts(cur)==tuple(a+b for a,b in zip(before,(1,1,1)))
            assert plan.monetary_state(cur)==physical;conn.commit()
        assert ok(owner,STATUS,dict(p_request=key))==status and ok(owner,REQUEST,args)==status
        assert ok(owner,'erp_cp7_read_staged_analysis_pages_v1',page_args)==pages
        crossed=call(owner,OPERATIONAL,dict(p_query=staged.query(today),p_request=key))
        assert crossed['status']==400 and'CP7_ANALYSIS_REQUEST_CHANGED'in json.dumps(crossed['body'])
        shared.update(owner=owner,args=args,status=status,sealed=sealed)
        return dict(status='PASS',actual_Auth_request_step_status_READY_and_replay=True,actual_HTTP_operational_steps=calls,
            private_finance_advancement_not_HTTP_or_cron=True,official_sections_and_24_metrics_equal=True,
            independent_book_signature=True,UNKNOWN_never_zero=True,one_job_mark_capture=True,
            cross_mode_UUID_refused=True,sealed_operational_pages_unchanged=True,no_physical_stock_money_HPP_change=True)

    def withdrawn():
        admin,args,before,physical=prepare('ADMIN','current-finance-admin')
        key=args['p_request'];ok(admin,REQUEST,args)
        with http.connect()as conn,conn.cursor()as cur:
            _,sealed=ready(cur,key,admin.auth_user_id)
            role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,)).fetchone()[0]
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(role,));assert cur.rowcount==1
            conn.commit()
        hidden=ok(admin,STATUS,dict(p_request=key));side=native.sidecar(hidden,key,'ACCESS_REVOKED')
        assert side['capture']is None and side['result']is None
        assert call(admin,REQUEST,args)['status']==403
        assert call(admin,REQUEST,dict(args,p_request=str(uuid.uuid4())))['status']==403
        with http.connect()as conn,conn.cursor()as cur:
            assert native.stored_capture(cur,sealed['id'])==sealed
            assert counts(cur)==tuple(a+b for a,b in zip(before,(1,1,1)))
            assert plan.monetary_state(cur)==physical
        return dict(status='PASS',actual_Auth_current_permission_withdrawal=True,progress_and_result_hidden=True,
            fresh_and_saved_UUID_requests_403=True,sealed_finance_history_unchanged=True,no_orphan_capture=True)

    def boundaries():
        assert shared
        other=http.login('OWNER','current-finance-foreign');owner=shared['owner'];args=shared['args']
        missing=call(other,STATUS,dict(p_request=args['p_request']))
        assert missing['status']==400 and'CP7_ANALYSIS_JOB_UNAVAILABLE'in json.dumps(missing['body'])
        for name,payload in((REQUEST,args),(STATUS,dict(p_request=args['p_request']))):
            started=monotonic();answer=http.anon_rpc(name,payload)
            assert(monotonic()-started)*1000<8000 and answer['status']in(401,403)
        with http.connect()as conn,conn.cursor()as cur:before=counts(cur)
        for q in(staged.query(today),dict(query(today),finance_mode='DEFERRED'),dict(query(today),finance_mode=True),dict(query(today),extra=True)):
            response=call(owner,REQUEST,dict(p_query=q,p_request=str(uuid.uuid4())))
            assert response['status']==400,response
        with http.connect()as conn,conn.cursor()as cur:
            assert counts(cur)==before
            assert native.stored_capture(cur,shared['sealed']['id'])==shared['sealed']
        return dict(status='PASS',actual_Auth_foreign_job_unavailable=True,anonymous_refused=True,
            explicit_STAGED_closed_query_enforced=True,no_refused_job_mark_or_capture=True,original_capture_unchanged=True,
            actual_Auth_call_timings=timings,wall_limit_ms=8000)

    return list(zip(IDS['http'],(flow,withdrawn,boundaries)))
