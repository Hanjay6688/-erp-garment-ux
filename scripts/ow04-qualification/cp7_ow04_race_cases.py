"""Predeclared actual public-SQL races, not real Auth or browser tests.

Source documents use the retained real writers. Administrative role/permission
fixtures and connection termination are restricted to disposable race copies.
The complete backend remains exactly the Native44-qualified candidate.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import copy,hashlib,json,queue,time,uuid
import psycopg
import cp7_ow04_http_cases as transport

initial,nf=transport.initial,transport.nf
IDS=tuple('OW04_RACE_'+x for x in ('DISTINCT_REQUESTS_ONE_SETTLEMENT','SAME_REQUEST_REPLAY',
    'CHANGED_REQUEST_REFUSAL','REVOKED_AFTER_FG_WAIT','HOLDER_ROLLBACK_RECOVERY','BACKEND_TERMINATION_RECOVERY'))


def observe(cur):
    """Exact full private rows and ERP/platform boundary, no projected subset."""
    nf.b.api.admin(cur)
    schemas=('cp7_credit','ow04_ordinal_wrapper','ow04_source_proposal','ow04_pure_kernel')
    namespaces=[r[0]for r in cur.execute('select nspname from pg_namespace where nspname=any(%s::text[])order by 1',(list(schemas),)).fetchall()]
    assert namespaces==sorted(schemas),'OW04_RACE_PRIVATE_SCHEMA_INVENTORY_MISSING'
    tables=[r[0]for r in cur.execute("select quote_ident(n.nspname)||'.'||quote_ident(c.relname)from pg_class c join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname=any(%s::text[])and c.relkind in('r','p')order by 1",(list(schemas),)).fetchall()]
    assert 'cp7_credit.return_requests'in tables,'OW04_RACE_PRIVATE_TABLE_INVENTORY_MISSING'
    tables+=['cp7_sales.requests','cp7_sales.command_context']
    private={table:nf._array(cur,table,'true',())for table in tables}
    return dict(boundary=nf.b.boundary.snapshot(cur),private_schema_inventory=namespaces,private_table_inventory=tables,private=private)


def snapshot(tools):
    with tools.connect()as conn,conn.cursor()as cur:
        value=observe(cur);conn.rollback();return value


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def reviewed(tools,today,subject=None):
    f=transport.prepared(tools,today)
    before=snapshot(tools)
    with tools.connect()as conn,conn.cursor()as cur:
        q=nf.call_quote(cur,f['query'],subject)
        if subject is None:initial._assert_quote(cur,q,f['query'],f['x'],f['gold'],f['master'])
        else:assert q['capabilities']['record_return']and q['capabilities']['recognize_credit']
        conn.rollback()
    assert snapshot(tools)==before,'OW04_RACE_QUOTE_MUTATED_STATE'
    return f,initial._envelope(f['query'],q),q


def settle(cur,envelope,request,subject=None):
    cur.execute("set local lock_timeout='20s';set local statement_timeout='60s'")
    nf.auth.actor(cur,subject)
    result=cur.execute('select public.erp_cp7_settle_sales_return_v1(%s::jsonb,%s::uuid,%s::text)',
        (json.dumps(envelope['document']),request,envelope['expected_version'])).fetchone()[0]
    nf.b.api.admin(cur)
    return result


def actual(tools,f,envelope,q,result,request,requests,aborted=None):
    initial._assert_outcome(result,request,envelope,q,'CREDIT')
    with tools.connect()as conn,conn.cursor()as cur:
        nf.b.api.admin(cur)
        facts=initial._assert_actual(cur,f['x'],f['gold'],f['master'],result,request,f['original_movements'])
        nf.assert_payment_unchanged(cur,f['x'])
        rows=cur.execute('select request_id,response from cp7_credit.return_requests where request_id=any(%s::uuid[])',(list(requests),)).fetchall()
        inner=cur.execute('select request_id,response from cp7_sales.requests where request_id=any(%s::uuid[])',(list(requests),)).fetchall()
        assert rows==[(request,result)]and len(inner)==1 and inner[0][0]==request and inner[0][1]['return_id']==result['return_id'],(rows,inner)
        if aborted is not None:
            assert aborted['return_id']!=result['return_id']and aborted['credit_id']!=result['credit_id']
            assert cur.execute('select count(*)from erp.sales_returns where id=%s',(aborted['return_id'],)).fetchone()[0]==0
            assert cur.execute('select count(*)from cp7_credit.cohorts where id=%s',(aborted['credit_id'],)).fetchone()[0]==0
        final=observe(cur);conn.rollback()
    return dict(full_private_sha256=sha(final),private_table_count=len(final['private_table_inventory']),
        native_return_journal_sha256=facts['native_return_journal']['sha256'],recognition_journal_sha256=facts['recognition_journal']['sha256'],
        exact_original_money_date_stock_HPP_oracles=True,original_payments_and_journals_unchanged=True,one_outer_and_inner_receipt=True),final


def race(tools,today,kind):
    f,envelope,q=reviewed(tools,today)
    first_request=uuid.uuid4();second_request=uuid.uuid4()if kind=='DISTINCT'else first_request
    second_envelope=copy.deepcopy(envelope)
    if kind=='CHANGED':second_envelope['document']['change_reason']+=' changed concurrent intent'
    def first(cur):
        result=settle(cur,envelope,first_request)
        cur.execute('set constraints all immediate')
        return dict(result=result,complete_state=observe(cur))
    held,contention,outcome=tools.two_sessions(first,lambda cur:settle(cur,second_envelope,second_request),kind!='ROLLBACK')
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    if kind in('DISTINCT','CHANGED'):
        expected='CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'if kind=='DISTINCT'else'CP7_CREDIT_RETURN_REQUEST_CHANGED'
        assert outcome==dict(ok=False,sqlstate='P0001',message=expected),outcome
        winner=held['result'];request=first_request
    else:
        assert outcome['ok']is True,outcome
        winner=outcome['result'];request=second_request
        if kind=='REPLAY':assert winner==held['result'],'OW04_RACE_REPLAY_OUTCOME_CHANGED'
    proof,final=actual(tools,f,envelope,q,winner,request,(first_request,second_request),held['result']if kind=='ROLLBACK'else None)
    if kind!='ROLLBACK':assert final==held['complete_state'],'OW04_RACE_ADDITIONAL_PRIVATE_OR_BUSINESS_EFFECT'
    return dict(status='PASS',two_actual_sessions=True,authenticated_SQL_fixture_not_real_Auth=True,
        observed_holder_blocks_worker=True,holder_committed=kind!='ROLLBACK',kind=kind,
        identical_committed_replay=kind=='REPLAY',aborted_return_and_cohort_absent=kind=='ROLLBACK',
        actual_worker=outcome,**proof,production_go=False)


def worker(tools,envelope,request,ready,subject=None):
    try:
        with tools.connect()as conn,conn.cursor()as cur:
            ready.put(cur.execute('select pg_backend_pid()').fetchone()[0])
            result=settle(cur,envelope,request,subject);conn.commit()
            return dict(ok=True,result=result)
    except psycopg.Error as error:
        return dict(ok=False,sqlstate=error.sqlstate,message=error.diag.message_primary)


def wait_for_holder(cur,holder,waiter):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        cur.execute('select pg_stat_clear_snapshot()')
        if cur.execute('select %s=any(pg_blocking_pids(%s))',(holder,waiter)).fetchone()[0]:return
        time.sleep(.03)
    raise AssertionError('OW04_RACE_EXACT_HOLDER_DID_NOT_BLOCK_WORKER')


def revoke(tools,today):
    with tools.connect()as conn,conn.cursor()as cur:
        nf.b.api.admin(cur);subject,role=nf.auth.custom_actor(cur)
        cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)select %s,p.permission_key from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id where r.role_code='OWNER'",(role,));conn.commit()
    f,envelope,q=reviewed(tools,today,subject)
    with tools.connect()as holder,holder.cursor()as h:
        hpid=h.execute('select pg_backend_pid()').fetchone()[0]
        h.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        ready=queue.Queue()
        with ThreadPoolExecutor(max_workers=1)as pool:
            future=pool.submit(worker,tools,envelope,uuid.uuid4(),ready,subject)
            try:
                wpid=ready.get(timeout=10)
                with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
                    wait_for_holder(c,hpid,wpid)
                    c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.return.post'",(role,))
                    assert c.rowcount==1,'OW04_RACE_PERMISSION_WAS_NOT_PRESENT'
                baseline=snapshot(tools)
            finally:holder.rollback()
            outcome=future.result(timeout=40)
    assert outcome==dict(ok=False,sqlstate='42501',message='CP7_SALES_WRITE_DENIED'),outcome
    after=snapshot(tools)
    assert after==baseline,'OW04_RACE_REVOKED_REQUEST_LEFT_PARTIAL_EFFECT'
    return dict(status='PASS',actual_FG_holder_blocks_worker=True,permission_revoked_by_committed_third_session=True,
        post_revocation_full_state_identical=True,full_private_sha256=sha(after),actual_worker=outcome,
        authenticated_SQL_fixture_not_real_Auth=True,production_go=False)


def backend_loss(tools,today):
    import cp6_auditor_modes as modes
    f,envelope,q=reviewed(tools,today)
    request=uuid.uuid4();ready=queue.Queue();holder=tools.connect();h=holder.cursor()
    try:
        # Kill only the exact connection opened by this case on the isolated
        # harness race copy. No guessed PID, hosted URL or arbitrary database.
        assert h.execute('select current_database()').fetchone()[0]==modes.RACE_DB
        hpid=h.execute('select pg_backend_pid()').fetchone()[0]
        aborted=settle(h,envelope,request);h.execute('set constraints all immediate')
        with ThreadPoolExecutor(max_workers=1)as pool:
            future=pool.submit(worker,tools,envelope,request,ready)
            try:
                wpid=ready.get(timeout=10)
                with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
                    assert c.execute('select current_database()').fetchone()[0]==modes.RACE_DB
                    wait_for_holder(c,hpid,wpid)
                    assert c.execute('select pg_terminate_backend(%s)',(hpid,)).fetchone()[0]is True
            finally:
                # Closing a still-live holder also releases it if setup failed;
                # pool shutdown must never wait behind our own forgotten lock.
                h.close();holder.close()
            outcome=future.result(timeout=40)
        assert outcome['ok']is True,outcome
        proof,_=actual(tools,f,envelope,q,outcome['result'],request,(request,),aborted)
    finally:
        if not h.closed:h.close()
        if not holder.closed:holder.close()
    return dict(status='PASS',known_disposable_holder_backend_terminated=True,observed_holder_blocks_worker=True,
        server_aborted_uncommitted_transaction=True,aborted_return_and_cohort_absent=True,
        authenticated_SQL_fixture_not_real_Auth=True,actual_worker=outcome,**proof,production_go=False)


def races(tools,today):
    expected=json.loads(Path(__file__).with_name('RACE_EXPECTED.json').read_text())
    assert tuple(x['id']for x in expected['cases'])==IDS
    operations=[lambda:race(tools,today,'DISTINCT'),lambda:race(tools,today,'REPLAY'),lambda:race(tools,today,'CHANGED'),
        lambda:revoke(tools,today),lambda:race(tools,today,'ROLLBACK'),lambda:backend_loss(tools,today)]
    return list(zip(IDS,operations))
