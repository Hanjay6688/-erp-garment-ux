"""P19 background analysis job and complete-Original segment transport.

Every job runs the unchanged capture compiler inside one ordinary request
under the existing statement limit; no limit is raised. Real Native E01 and
planner facts, real concurrent sessions and real Auth/PostgREST calls. One
case uses an explicitly synthetic stored run only to prove multi-segment
transport at the real stack; it gives no analysis or capacity credit.
"""
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
import hashlib
import json
import threading
import time
import uuid

import psycopg

import cp7_analysis_cases as analysis
import cp7_analysis_finance_cases as financial
import cp7_p19_native_load_cases as load
import cp7_p18_e01_bridge_cases as bridge

IDS = dict(
    native=['P19T_JOB_COMPLETE_ORIGINAL', 'P19T_MULTI_SEGMENT_EXACT', 'P19T_SEGMENT_AUTHORITY', 'P19T_JOB_IDENTITY_REFUSALS',
            'P19T_FINANCE_DEFERRED_NO_BOOK_READ', 'P19T_FINANCE_MODE_IDENTITY'],
    races=['P19T_RACE_TWO_RUNS_ONE_ORIGINAL', 'P19T_RACE_LIMIT_STOPS_THEN_CONTINUES', 'P19T_RACE_REVOKE_WHILE_WAITING'],
    http=['P19T_HTTP_JOB_TRANSPORT', 'P19T_HTTP_REVOKED', 'P19T_HTTP_FINANCE_ON_DEMAND'],
    browser=['P19T_BROWSER_DESKTOP_RELOAD_RECOVERY', 'P19T_BROWSER_MOBILE_BACKGROUND', 'P19T_BROWSER_FINANCE_ON_DEMAND'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.p19.analysis-job-transport.v1'
SEGMENT_CHARACTERS = 2000000
auth, b, schedule = analysis.auth, analysis.b, analysis.schedule
FUNCTIONS = ('erp_cp7_request_analysis_job_v1', 'erp_cp7_run_analysis_job_v1', 'erp_cp7_get_analysis_job_v1',
             'erp_cp7_read_analysis_manifest_v1', 'erp_cp7_read_analysis_segment_v1')


# The books: what the protected owner report and its all-book provenance scan
# read. The operational demand source reads only the journal headers of sales
# and returns (their posting state), so erp.journal_entries is not listed.
BOOK_TABLES = ('journal_lines', 'account_daily_balances', 'cash_accounts')


def book_reads(cur):
    # Pending counters of this transaction; every reader runs in it.
    rows = cur.execute("""select relname,coalesce(seq_scan,0)+coalesce(idx_scan,0) from pg_stat_xact_user_tables
        where schemaname='erp' and relname=any(%s)""", (list(BOOK_TABLES),)).fetchall()
    return {**{t: 0 for t in BOOK_TABLES}, **dict(rows)}


def operational(cur, today, key, subject=None, q=None):
    return rpc(cur, 'erp_cp7_capture_operational_analysis_v1', (json.dumps(q or query(today)), key), subject)


def request_operational(cur, today, key, subject=None, q=None):
    return rpc(cur, 'erp_cp7_request_operational_analysis_job_v1', (json.dumps(q or query(today)), key), subject)


def query(today):
    return analysis.previous.baseline.history.query(today)


def rpc(cur, name, args, subject=None):
    return schedule.rpc(cur, name, args, subject)


def request(cur, today, key, subject=None, q=None):
    return rpc(cur, 'erp_cp7_request_analysis_job_v1', (json.dumps(q or query(today)), key), subject)


def status(cur, key, subject=None):
    return rpc(cur, 'erp_cp7_get_analysis_job_v1', (key,), subject)


def run(cur, key, subject=None, timeout='8s'):
    # The ordinary authenticated statement limit applies to the worker call.
    prior = cur.execute('show statement_timeout').fetchone()[0]
    auth.actor(cur, subject)
    cur.execute("select set_config('statement_timeout',%s,true),set_config('lock_timeout','0',true)", (timeout,))
    result = cur.execute('select public.erp_cp7_run_analysis_job_v1(%s)', (key,)).fetchone()[0]
    b.api.admin(cur)
    cur.execute("select set_config('statement_timeout',%s,true)", (prior,))
    return result


def checked_job(job, key, state, attempts=1):
    assert job['contract_version'] == 'cp7.native-analysis-job.v1' and job['request_id'] == str(key), job
    assert job['state'] == state and job['attempts'] == attempts, job
    assert job['apply_enabled'] is False and job['production_go'] is False
    assert (job['run_id'] is not None) == (state == 'DONE') and (job['failure'] is not None) == (state == 'FAILED'), job
    assert (job['finished_at'] is None) == (state in ('WAITING', 'RUNNING')), job
    return job


def fetch(cur, run_id, subject=None):
    """Manifest plus every segment, verified exactly as the client does."""
    m = rpc(cur, 'erp_cp7_read_analysis_manifest_v1', (run_id,), subject)
    assert m['contract_version'] == 'cp7.native-analysis-manifest.v1' and m['run_id'] == str(run_id)
    assert m['apply_enabled'] is False and m['production_go'] is False and len(m['access_epoch']) == 64
    d = m['document']
    assert d['segment_characters'] == SEGMENT_CHARACTERS and d['segment_count'] == -(-d['characters'] // SEGMENT_CHARACTERS)
    parts = []
    for i in range(d['segment_count']):
        s = rpc(cur, 'erp_cp7_read_analysis_segment_v1', (run_id, i, m['access_epoch']), subject)
        assert (s['contract_version'], s['run_id'], s['index'], s['segment_count'], s['document_sha256'], s['document_utf8_bytes']) == (
            'cp7.native-analysis-segment.v1', str(run_id), i, d['segment_count'], d['sha256'], d['utf8_bytes']), s
        raw = s['body'].encode('utf8')
        assert len(raw) == s['utf8_bytes'] <= 8000000 and hashlib.sha256(raw).hexdigest() == s['sha256']
        assert len(s['body']) == min(SEGMENT_CHARACTERS, d['characters'] - i * SEGMENT_CHARACTERS)
        parts.append(s['body'])
    whole = ''.join(parts)
    raw = whole.encode('utf8')
    assert len(raw) == d['utf8_bytes'] and len(whole) == d['characters'] and hashlib.sha256(raw).hexdigest() == d['sha256']
    document = json.loads(whole)
    assert 'source_state' not in document
    return {**document, 'source_state': m['source_state']}, m, parts


def counts(cur, key):
    return cur.execute("""select (select count(*) from cp7_analysis_native.runs where request_id=%s),
        (select count(*) from cp7_analysis_jobs.documents d join cp7_analysis_native.runs r on r.id=d.run_id where r.request_id=%s),
        (select count(*) from cp7_analysis_jobs.jobs where request_id=%s)""", (key, key, key)).fetchone()


def refused(cur, op, code):
    return auth.refused(cur, op, code)


def cases(cur, today):
    def complete():
        f, _ = load.real_workload(cur, today)
        before = b.boundary.snapshot(cur)
        key = uuid.uuid4()
        started = monotonic()
        first = checked_job(request(cur, today, key), key, 'WAITING')
        assert first['run_id'] is None and checked_job(status(cur, key), key, 'WAITING') == first
        done = checked_job(run(cur, key), key, 'DONE')
        elapsed = round((monotonic() - started) * 1000, 3)
        assert checked_job(run(cur, key), key, 'DONE') == done and checked_job(request(cur, today, key), key, 'DONE') == done
        served = analysis.read(cur, done['run_id'])
        analysis.checked(served)
        assembled, manifest, parts = fetch(cur, done['run_id'])
        assert assembled == served, 'P19T_ASSEMBLED_ORIGINAL_DIFFERS_FROM_SERVE'
        stored = cur.execute('select cp7_analysis_jobs.original(r)::text from cp7_analysis_native.runs r where id=%s',
                             (done['run_id'],)).fetchone()[0]
        assert ''.join(parts) == stored
        # The ordinary capture of the same UUID is the same immutable Original.
        same = analysis.capture(cur, today, key)
        assert same['run_id'] == done['run_id'] and same['analysis'] == served['analysis']
        assert counts(cur, key) == (1, 1, 1)
        assert b.boundary.snapshot(cur) == before
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', request_run_get_manifest_segments_exact=True, job_elapsed_ms=elapsed,
                    document=manifest['document'], one_Original_one_document_one_job=True,
                    ordinary_capture_same_UUID_same_Original=True, Native_business_unchanged=True, statement_timeout='8s')

    def multi_segment():
        subject, _ = auth.custom_actor(cur)
        b.api.admin(cur)
        key, run_id = uuid.uuid4(), uuid.uuid4()
        q = cur.execute('select cp7_planning.history_query(%s::jsonb)', (json.dumps(query(today)),)).fetchone()[0]
        pad = 'a\U0001F600é' * 1500000
        # Explicit synthetic stored run: transport proof only, never analysis credit.
        cur.execute("""insert into cp7_analysis_native.runs(id,actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
            values(%s,%s,%s,%s,clock_timestamp(),'{}','{"facts":{"products":[]},"fixture":"EXPLICIT_SYNTHETIC_TRANSPORT_ONLY"}',%s,'synthetic')""",
                    (run_id, subject, key, json.dumps(q), json.dumps(dict(run_id=str(run_id), pad=pad))))
        assembled, manifest, parts = fetch(cur, run_id, subject)
        assert manifest['document']['segment_count'] == 3 and manifest['source_state'] == 'ARCHIVED_STALE'
        assert assembled['analysis'] == dict(run_id=str(run_id), pad=pad) and assembled['product_labels'] == []
        assert ''.join(parts) == cur.execute('select cp7_analysis_jobs.original(r)::text from cp7_analysis_native.runs r where id=%s',
                                             (run_id,)).fetchone()[0]
        assert max(len(p.encode('utf8')) for p in parts) <= 8000000
        assert all('\U0001F600' in part and '\u00e9' in part for part in parts)
        for index in (3, -1):
            refused(cur, lambda: rpc(cur, 'erp_cp7_read_analysis_segment_v1', (run_id, index, manifest['access_epoch']), subject),
                    'CP7_ANALYSIS_SEGMENT_UNAVAILABLE')
        again = fetch(cur, run_id, subject)
        assert again[1]['document'] == manifest['document'] and again[2] == parts
        for table in ('documents', 'segments'):
            refused(cur, lambda: cur.execute('update cp7_analysis_jobs.' + table + ' set run_id=run_id'), 'CP7_RUN_IMMUTABLE')
        return dict(status='PASS', explicit_synthetic_transport_only=True, analysis_credit=False, segments=3,
                    multibyte_segment_cuts_exact=True, every_segment_within_8000000_bytes=True, immutable_document=True)

    def authority():
        f, _ = load.real_workload(cur, today)
        owner_key = uuid.uuid4()
        request(cur, today, owner_key)
        owner = run(cur, owner_key)
        other, other_role = auth.custom_actor(cur)
        refused(cur, lambda: rpc(cur, 'erp_cp7_read_analysis_manifest_v1', (owner['run_id'],), other), 'CP7_ANALYSIS_RUN_UNAVAILABLE')
        refused(cur, lambda: status(cur, owner_key, other), 'CP7_ANALYSIS_JOB_UNAVAILABLE')
        refused(cur, lambda: run(cur, owner_key, other), 'CP7_ANALYSIS_JOB_UNAVAILABLE')
        own_key = uuid.uuid4()
        request(cur, today, own_key, other)
        mine = checked_job(run(cur, own_key, other), own_key, 'DONE')
        _, m, _ = fetch(cur, mine['run_id'], other)
        refused(cur, lambda: rpc(cur, 'erp_cp7_read_analysis_segment_v1', (owner['run_id'], 0, m['access_epoch']), other),
                'CP7_ANALYSIS_RUN_UNAVAILABLE')
        # Any change of the actor's current access retires the manifest epoch.
        b.api.admin(cur)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')", (other_role,))
        refused(cur, lambda: rpc(cur, 'erp_cp7_read_analysis_segment_v1', (mine['run_id'], 0, m['access_epoch']), other),
                'CP7_ANALYSIS_ACCESS_CHANGED')
        renewed = fetch(cur, mine['run_id'], other)[1]
        assert renewed['access_epoch'] != m['access_epoch'] and renewed['document'] == m['document']
        b.api.admin(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'", (other_role,))
        for name, args in (('erp_cp7_request_analysis_job_v1', (json.dumps(query(today)), own_key)), ('erp_cp7_run_analysis_job_v1', (own_key,)),
                           ('erp_cp7_get_analysis_job_v1', (own_key,)), ('erp_cp7_read_analysis_manifest_v1', (mine['run_id'],)),
                           ('erp_cp7_read_analysis_segment_v1', (mine['run_id'], 0, renewed['access_epoch']))):
            refused(cur, lambda: rpc(cur, name, args, other), 'CP7_ACCESS_DENIED')
        # Protected finance: the manifest refuses exactly when serve refuses.
        finance_subject, finance_role = financial.admin_actor(cur, analysis)
        finance_key = uuid.uuid4()
        request(cur, today, finance_key, finance_subject)
        financed = checked_job(run(cur, finance_key, finance_subject), finance_key, 'DONE')
        served = analysis.read(cur, financed['run_id'], finance_subject)
        assert served['financial_source'] is not None and fetch(cur, financed['run_id'], finance_subject)[0] == served
        b.api.admin(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'", (finance_role,))
        refused(cur, lambda: analysis.read(cur, financed['run_id'], finance_subject), 'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
        refused(cur, lambda: rpc(cur, 'erp_cp7_read_analysis_manifest_v1', (financed['run_id'],), finance_subject),
                'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
        # A later Native source change archives both readings identically.
        assert fetch(cur, owner['run_id'])[0]['source_state'] == analysis.read(cur, owner['run_id'])['source_state'] == 'UNCHANGED'
        analysis.setup(cur, today)
        archived = analysis.read(cur, owner['run_id'])
        assert archived['source_state'] == 'ARCHIVED_STALE' and fetch(cur, owner['run_id'])[0] == archived
        # No direct table or private function path for API roles.
        b.api.admin(cur)
        for who in ('anon', 'authenticated', 'service_role'):
            for table in ('jobs', 'documents', 'segments'):
                assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",
                                       (who, 'cp7_analysis_jobs.' + table)).fetchone()[0]
            assert not cur.execute("select has_function_privilege(%s,'cp7_analysis_jobs.run(uuid)','EXECUTE')", (who,)).fetchone()[0]
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', foreign_actor_manifest_segment_job_refused=True, access_epoch_change_refused=True,
                    current_permission_loss_refuses_all_five=True, finance_refusal_equals_serve=True,
                    stale_state_equals_serve=True, no_direct_API_path=True)

    def identity():
        f, _ = load.real_workload(cur, today)
        key = uuid.uuid4()
        captured = analysis.capture(cur, today, key)
        adopted = checked_job(request(cur, today, key), key, 'DONE')
        assert adopted['run_id'] == captured['run_id'] and counts(cur, key) == (1, 0, 1)
        changed = query(today)
        changed['group_mode'] = 'RESTATED'
        refused(cur, lambda: request(cur, today, key, q=changed), 'CP7_ANALYSIS_REQUEST_CHANGED')
        fresh = uuid.uuid4()
        request(cur, today, fresh)
        refused(cur, lambda: request(cur, today, fresh, q=changed), 'CP7_ANALYSIS_REQUEST_CHANGED')
        missing = uuid.uuid4()
        for op in (lambda: run(cur, missing), lambda: status(cur, missing)):
            refused(cur, op, 'CP7_ANALYSIS_JOB_UNAVAILABLE')
        refused(cur, lambda: rpc(cur, 'erp_cp7_request_analysis_job_v1', (json.dumps(query(today)), None)), 'CP7_ANALYSIS_REQUEST_REQUIRED')
        refused(cur, lambda: rpc(cur, 'erp_cp7_read_analysis_manifest_v1', (uuid.uuid4(),)), 'CP7_ANALYSIS_RUN_UNAVAILABLE')
        assert counts(cur, fresh) == (0, 0, 1) and counts(cur, missing) == (0, 0, 0)
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', ordinary_capture_UUID_adopted_without_recompute=True, changed_query_refused=True,
                    unknown_UUID_refused=True, missing_UUID_refused=True, foreign_or_missing_run_refused=True)

    def deferred_no_books():
        f, _ = load.real_workload(cur, today)
        subject, role = financial.admin_actor(cur, analysis)
        before = b.boundary.snapshot(cur)
        start = book_reads(cur)
        key = uuid.uuid4()
        e = operational(cur, today, key, subject)
        analysis.checked(e)
        # Not loaded is never zero: no financial source, no IDR figure, the
        # existing not-captured warning and BLOCKED financial readiness.
        assert e['financial_source'] is None and 'FINANCIAL_DOMAIN_NOT_CAPTURED' in e['analysis']['generation_warnings']
        assert e['analysis']['financial_readiness'] == 'BLOCKED' and e['analysis']['quality']['financial'] == 'UNKNOWN'
        facts = cur.execute('select facts from cp7_analysis_native.runs where id=%s', (e['run_id'],)).fetchone()[0]
        assert facts['financial_capture'] == 'DEFERRED' and facts['financial_source'] is None
        served = analysis.read(cur, e['run_id'], subject)
        assert served == e and served['source_state'] == 'UNCHANGED'
        job_key = uuid.uuid4()
        checked_job(request_operational(cur, today, job_key, subject), job_key, 'WAITING')
        done = checked_job(run(cur, job_key, subject), job_key, 'DONE')
        assembled, manifest, _ = fetch(cur, done['run_id'], subject)
        assert assembled == analysis.read(cur, done['run_id'], subject) and assembled['financial_source'] is None
        assert manifest['source_state'] == 'UNCHANGED'
        after = book_reads(cur)
        assert after == start, ('P19T_OPERATIONAL_ANALYSIS_READ_THE_BOOKS', start, after)
        # Positive control under the same counters: the full path reads them.
        full = analysis.capture(cur, today, uuid.uuid4(), subject)
        analysis.checked(full)
        assert full['financial_source'] is not None
        control = book_reads(cur)
        assert all(control[t] > after[t] for t in BOOK_TABLES), ('P19T_BOOK_COUNTER_BLIND', after, control)
        assert b.boundary.snapshot(cur) == before
        # Operational rights suffice for an operational-only run; the run with
        # financial figures still refuses without the report permission.
        b.api.admin(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'", (role,))
        assert analysis.read(cur, e['run_id'], subject)['analysis'] == e['analysis']
        assert fetch(cur, done['run_id'], subject)[0]['analysis'] == assembled['analysis']
        refused(cur, lambda: analysis.read(cur, full['run_id'], subject), 'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', operational_capture_serve_job_manifest_segments_read_no_book_table=True,
                    book_tables=list(BOOK_TABLES), book_reads_operational=after, book_reads_after_full_control=control,
                    not_loaded_is_unknown_not_zero=True, full_path_unchanged_and_still_protected=True,
                    operational_rights_suffice_for_operational_run=True, Native_business_unchanged=True)

    def mode_identity():
        f, _ = load.real_workload(cur, today)
        subject, _ = financial.admin_actor(cur, analysis)
        key = uuid.uuid4()
        e = operational(cur, today, key, subject)
        assert operational(cur, today, key, subject) == e
        # One UUID is one request: same query and same finance mode.
        refused(cur, lambda: analysis.capture(cur, today, key, subject), 'CP7_ANALYSIS_REQUEST_CHANGED')
        refused(cur, lambda: request(cur, today, key, subject), 'CP7_ANALYSIS_REQUEST_CHANGED')
        adopted = checked_job(request_operational(cur, today, key, subject), key, 'DONE')
        assert adopted['run_id'] == e['run_id'] and counts(cur, key) == (1, 0, 1)
        full_key = uuid.uuid4()
        full = analysis.capture(cur, today, full_key, subject)
        assert full['financial_source'] is not None
        refused(cur, lambda: operational(cur, today, full_key, subject), 'CP7_ANALYSIS_REQUEST_CHANGED')
        refused(cur, lambda: request_operational(cur, today, full_key, subject), 'CP7_ANALYSIS_REQUEST_CHANGED')
        waiting = uuid.uuid4()
        checked_job(request_operational(cur, today, waiting, subject), waiting, 'WAITING')
        refused(cur, lambda: request(cur, today, waiting, subject), 'CP7_ANALYSIS_REQUEST_CHANGED')
        # An ordinary capture does not consult jobs; a run of the other mode on
        # the same UUID makes the job fail instead of adopting a mixed result.
        analysis.capture(cur, today, waiting, subject)
        failed = checked_job(run(cur, waiting, subject), waiting, 'FAILED')
        assert failed['failure']['code'] == 'CP7_ANALYSIS_REQUEST_CHANGED', failed
        # Only the two modes exist, at every private entry.
        b.api.admin(cur)
        q = json.dumps(query(today))
        for sql, args in (('select cp7_analysis_native.source_for(%s::jsonb,%s)', (q, 'MAYBE')),
                          ('select cp7_analysis_native.source_for(%s::jsonb,%s)', (q, None)),
                          ('select cp7_analysis_native.capture(%s::jsonb,%s,%s)', (q, uuid.uuid4(), 'MAYBE')),
                          ('select cp7_analysis_jobs.request(%s::jsonb,%s,%s)', (q, uuid.uuid4(), None))):
            refused(cur, lambda: cur.execute(sql, args).fetchone(), 'CP7_ANALYSIS_FINANCE_MODE')
        for who in ('anon', 'authenticated', 'service_role'):
            for sig in ('cp7_analysis_native.capture(jsonb,uuid,text)', 'cp7_analysis_native.source_for(jsonb,text)',
                        'cp7_analysis_native.finance_mode(jsonb)', 'cp7_analysis_jobs.request(jsonb,uuid,text)'):
                assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
        for sig in ('public.erp_cp7_capture_operational_analysis_v1(jsonb,uuid)', 'public.erp_cp7_request_operational_analysis_job_v1(jsonb,uuid)'):
            assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (sig,)).fetchone()[0]
            assert not any(cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0] for who in ('anon', 'service_role'))
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', one_UUID_one_mode_capture_and_job=True, same_mode_UUID_adopted=True,
                    other_mode_run_fails_job_not_mixed=True, only_two_modes=True, no_direct_API_path=True)

    return list(zip(IDS['native'], (complete, multi_segment, authority, identity, deferred_no_books, mode_identity)))


def races(tools, today):
    def prepared(subject=None):
        key = uuid.uuid4()
        with tools.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            if subject == 'custom':
                subject, role = auth.custom_actor(cur)
            else:
                role = None
            checked_job(request(cur, today, key, subject), key, 'WAITING')
            conn.commit()
        return key, f, subject, role

    def two_runs():
        key, f, _, _ = prepared()
        gate = threading.Barrier(2)

        def send():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                result = run(cur, key)
                conn.commit()
                return result
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [job.result(60) for job in [pool.submit(send), pool.submit(send)]]
        assert all(r['state'] == 'DONE' for r in results) and results[0]['run_id'] == results[1]['run_id'], results
        with tools.connect() as conn, conn.cursor() as cur:
            assert counts(cur, key) == (1, 1, 1)
            assert cur.execute('select attempts from cp7_analysis_jobs.jobs where request_id=%s', (key,)).fetchone()[0] == 1
            bridge.literal(cur, f, '175.00')
        return dict(status='PASS', two_concurrent_workers_one_computation_one_Original=True, results=results)

    def limit():
        key, f, _, _ = prepared()
        with tools.connect() as holder, holder.cursor() as h:
            # The source reader waits on a real lock until the existing kind of
            # statement limit stops it; nothing but the FAILED state commits.
            h.execute('lock table erp.products in access exclusive mode')

            def send():
                with tools.connect() as conn, conn.cursor() as cur:
                    result = run(cur, key, timeout='3s')
                    conn.commit()
                    return result
            with ThreadPoolExecutor(max_workers=1) as pool:
                job = pool.submit(send)
                seen = None
                deadline = monotonic() + 3
                with tools.connect(autocommit=True) as observe, observe.cursor() as o:
                    while monotonic() < deadline and seen != 'RUNNING':
                        with o.connection.transaction():
                            seen = status(o, key)['state']
                        time.sleep(.05)
                stopped = job.result(30)
            holder.rollback()
        assert seen == 'RUNNING', seen
        assert stopped['state'] == 'FAILED' and stopped['failure'] == dict(sqlstate='57014', code='CP7_ANALYSIS_JOB_STOPPED'), stopped
        with tools.connect() as conn, conn.cursor() as cur:
            assert counts(cur, key) == (0, 0, 1)
            assert checked_job(status(cur, key), key, 'FAILED') == stopped
            again = checked_job(request(cur, today, key), key, 'WAITING', 2)
            assert again['started_at'] > stopped['started_at']
            conn.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            done = checked_job(run(cur, key), key, 'DONE', 2)
            conn.commit()
            assert counts(cur, key) == (1, 1, 1)
            bridge.literal(cur, f, '175.00')
        return dict(status='PASS', status_read_RUNNING_while_worker_waits=True, existing_limit_kind_stops_worker=True,
                    stopped=stopped, failed_state_only_committed=True, same_UUID_continued_attempt2=done)

    def revoke():
        key, f, subject, role = prepared('custom')
        with tools.connect() as holder, holder.cursor() as h:
            h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))', ('CP7:ANALYSIS:%s:%s' % (subject, key),))

            def send():
                with tools.connect() as conn, conn.cursor() as cur:
                    try:
                        result = run(cur, key, subject)
                        conn.commit()
                        return result
                    except psycopg.Error as error:
                        conn.rollback()
                        return str(error)
            with ThreadPoolExecutor(max_workers=1) as pool:
                job = pool.submit(send)
                waiting = False
                deadline = monotonic() + 8
                try:
                    with tools.connect(autocommit=True) as inspect, inspect.cursor() as c:
                        while monotonic() < deadline and not waiting:
                            waiting = c.execute("""select exists(select 1 from pg_stat_activity where datname=current_database()
                                and wait_event='advisory' and query like 'select public.erp_cp7_run_analysis_job_v1%%')""").fetchone()[0]
                            time.sleep(.03)
                        assert waiting, 'P19T_REAL_WORKER_LOCK_NOT_OBSERVED'
                    with tools.connect() as conn, conn.cursor() as c:
                        c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'", (role,))
                        conn.commit()
                finally:
                    holder.rollback()
                result = job.result(30)
        assert isinstance(result, str) and 'CP7_ACCESS_DENIED' in result, result
        with tools.connect() as conn, conn.cursor() as cur:
            assert counts(cur, key) == (0, 0, 1)
            assert cur.execute('select state,attempts from cp7_analysis_jobs.jobs where request_id=%s', (key,)).fetchone() == ('WAITING', 1)
            bridge.literal(cur, f, '175.00')
        return dict(status='PASS', permission_revoked_while_worker_waited_refused_before_effect=True, job_left_waiting=True)

    return list(zip(IDS['races'], (two_runs, limit, revoke)))


def http_cases(http, today):
    state = {}

    def flow():
        owner = http.login('OWNER', 'p19t-owner')
        other = http.login('OWNER', 'p19t-other')
        with http.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            conn.commit()
        key = str(uuid.uuid4())
        args = dict(p_query=query(today), p_request=key)

        def ok(user, name, payload):
            r = user.rpc(name, payload)
            assert r['status'] == 200, (name, r)
            return r['body']
        assert ok(owner, 'erp_cp7_request_analysis_job_v1', args)['state'] == 'WAITING'
        started = monotonic()
        done = ok(owner, 'erp_cp7_run_analysis_job_v1', dict(p_request=key))
        elapsed = round((monotonic() - started) * 1000, 3)
        assert done['state'] == 'DONE' and ok(owner, 'erp_cp7_get_analysis_job_v1', dict(p_request=key)) == done
        manifest = ok(owner, 'erp_cp7_read_analysis_manifest_v1', dict(p_run=done['run_id']))
        parts = [ok(owner, 'erp_cp7_read_analysis_segment_v1', dict(p_run=done['run_id'], p_index=i, p_access=manifest['access_epoch']))['body']
                 for i in range(manifest['document']['segment_count'])]
        whole = ''.join(parts)
        assert hashlib.sha256(whole.encode('utf8')).hexdigest() == manifest['document']['sha256']
        served = ok(owner, 'erp_cp7_read_analysis_v1', dict(p_run=done['run_id']))
        assert {**json.loads(whole), 'source_state': manifest['source_state']} == served
        analysis.checked(served)
        foreign = [other.rpc('erp_cp7_read_analysis_manifest_v1', dict(p_run=done['run_id']))['status'],
                   other.rpc('erp_cp7_read_analysis_segment_v1', dict(p_run=done['run_id'], p_index=0, p_access=manifest['access_epoch']))['status']]
        assert foreign == [403, 403], foreign
        missing = other.rpc('erp_cp7_get_analysis_job_v1', dict(p_request=key))
        assert missing['status'] == 400 and 'CP7_ANALYSIS_JOB_UNAVAILABLE' in json.dumps(missing['body']), missing
        anonymous = [http.anon_rpc(name, payload)['status'] for name, payload in (
            ('erp_cp7_request_analysis_job_v1', args), ('erp_cp7_run_analysis_job_v1', dict(p_request=key)),
            ('erp_cp7_get_analysis_job_v1', dict(p_request=key)), ('erp_cp7_read_analysis_manifest_v1', dict(p_run=done['run_id'])),
            ('erp_cp7_read_analysis_segment_v1', dict(p_run=done['run_id'], p_index=0, p_access=manifest['access_epoch'])))]
        assert all(code in (401, 403) for code in anonymous), anonymous
        with http.connect() as conn, conn.cursor() as cur:
            assert counts(cur, key) == (1, 1, 1)
            bridge.literal(cur, f, '175.00')
        state.update(owner=owner, key=key, run=done['run_id'], epoch=manifest['access_epoch'], args=args)
        return dict(status='PASS', real_Auth_request_run_get_manifest_segments=True, actual_HTTP_run_ms=elapsed,
                    assembled_equals_actual_HTTP_serve=True, foreign_403=True, foreign_job_unknown=True, anonymous_refused=anonymous)

    def revoked():
        assert state, 'P19T_REQUIRED_PRIOR_HTTP_CASE'
        owner = state['owner']
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner.auth_user_id,))
            conn.commit()
        codes = [owner.rpc(name, payload)['status'] for name, payload in (
            ('erp_cp7_request_analysis_job_v1', state['args']), ('erp_cp7_run_analysis_job_v1', dict(p_request=state['key'])),
            ('erp_cp7_get_analysis_job_v1', dict(p_request=state['key'])), ('erp_cp7_read_analysis_manifest_v1', dict(p_run=state['run'])),
            ('erp_cp7_read_analysis_segment_v1', dict(p_run=state['run'], p_index=0, p_access=state['epoch'])))]
        assert codes == [403] * 5, codes
        with http.connect() as conn, conn.cursor() as cur:
            assert counts(cur, state['key']) == (1, 1, 1)
        return dict(status='PASS', deactivated_user_all_five_403=True, no_new_effect=True)

    def finance_on_demand():
        assert state, 'P19T_REQUIRED_PRIOR_HTTP_CASE'
        admin = http.login('ADMIN', 'p19t-finance-admin')
        q = query(today)

        def ok(name, payload):
            r = admin.rpc(name, payload)
            assert r['status'] == 200, (name, r)
            return r['body']
        ops = ok('erp_cp7_capture_operational_analysis_v1', dict(p_query=q, p_request=str(uuid.uuid4())))
        analysis.checked(ops)
        assert ops['financial_source'] is None
        full = ok('erp_cp7_capture_analysis_v1', dict(p_query=q, p_request=str(uuid.uuid4())))
        analysis.checked(full)
        assert full['financial_source'] is not None
        key = str(uuid.uuid4())
        assert ok('erp_cp7_request_operational_analysis_job_v1', dict(p_query=q, p_request=key))['state'] == 'WAITING'
        done = ok('erp_cp7_run_analysis_job_v1', dict(p_request=key))
        assert done['state'] == 'DONE' and ok('erp_cp7_read_analysis_v1', dict(p_run=done['run_id']))['financial_source'] is None
        changed = admin.rpc('erp_cp7_capture_analysis_v1', dict(p_query=q, p_request=key))
        assert changed['status'] == 400 and 'CP7_ANALYSIS_REQUEST_CHANGED' in json.dumps(changed['body']), changed
        anonymous = [http.anon_rpc(name, dict(p_query=q, p_request=str(uuid.uuid4())))['status']
                     for name in ('erp_cp7_capture_operational_analysis_v1', 'erp_cp7_request_operational_analysis_job_v1')]
        assert all(code in (401, 403) for code in anonymous), anonymous
        with http.connect() as conn, conn.cursor() as cur:
            assert counts(cur, key) == (1, 1, 1)
        return dict(status='PASS', real_Auth_operational_capture_and_job_without_finance=True,
                    full_capture_still_carries_owner_report=True, one_UUID_one_mode=True, anonymous_refused=anonymous)

    return list(zip(IDS['http'], (flow, revoked, finance_on_demand)))
