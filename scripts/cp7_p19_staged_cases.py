"""P19 staged analysis (5,000 targets as supported capacity): request, step, status, page set, pages, source check.

Every call is one ordinary authenticated request under the existing 8 s
statement limit; no limit is raised. The staged run lives apart from
cp7_analysis_native.runs (no whole reader can serve it) and is read as a
header plus byte-adaptive pages bound by identity_hash. Real Native E01 and
planner facts, real concurrent sessions and real Auth/PostgREST calls. The
5,000-target point itself is measured by the scale ladder (P19 Scale); this
suite proves the contract and its authority on the closed harness.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from time import monotonic
import hashlib
import json
import re
import threading
import time
import uuid

import psycopg

import cp7_analysis_cases as analysis
import cp7_p19_native_load_cases as load
import cp7_p18_e01_bridge_cases as bridge

IDS = dict(
    native=['P19G_STAGED_EQUALS_SINGLE', 'P19G_STAGED_AUTHORITY', 'P19G_STAGED_IDENTITY', 'P19G_STAGED_SOURCE_CHECK',
            'P19G_STAGED_BOUNDS_VS_SINGLE'],
    races=['P19G_RACE_TWO_STEPS_ONE_UNIT', 'P19G_RACE_LIMIT_RETRIES_THEN_CONTINUES', 'P19G_RACE_ACCESS_CHANGED_MID_JOB'],
    http=['P19G_HTTP_STAGED_FLOW', 'P19G_HTTP_REVOKED'],
    browser=['P19G_BROWSER_DESKTOP_STAGED_RELOAD', 'P19G_BROWSER_MOBILE_STAGED'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.p19.analysis-staged.v1'
PAGE_BYTES = 8000000
STATEMENT_TIMEOUT = '8s'
# Driver bound only (calls per job); never an application limit.
DRIVER_CALLS = 20000
auth, b, schedule = analysis.auth, analysis.b, analysis.schedule
FUNCTIONS = ('erp_cp7_request_staged_analysis_v1', 'erp_cp7_step_staged_analysis_v1', 'erp_cp7_get_staged_analysis_v1',
             'erp_cp7_read_staged_analysis_pages_v1', 'erp_cp7_read_staged_analysis_page_v1',
             'erp_cp7_check_staged_analysis_source_v1')
SIGNATURES = ('public.erp_cp7_request_staged_analysis_v1(jsonb,uuid)', 'public.erp_cp7_step_staged_analysis_v1(uuid)',
              'public.erp_cp7_get_staged_analysis_v1(uuid)', 'public.erp_cp7_read_staged_analysis_pages_v1(uuid)',
              'public.erp_cp7_read_staged_analysis_page_v1(uuid,integer,text)',
              'public.erp_cp7_check_staged_analysis_source_v1(uuid)')
STATES = ('RUNNING', 'DONE', 'FAILED')


def query(today):
    return analysis.previous.baseline.history.query(today)


def limited(cur, name, args, subject=None, timeout=STATEMENT_TIMEOUT):
    """One public call as the actor under the ordinary authenticated statement limit."""
    prior = cur.execute('show statement_timeout').fetchone()[0]
    auth.actor(cur, subject)
    cur.execute("select set_config('statement_timeout',%s,true),set_config('lock_timeout','0',true)", (timeout,))
    placeholders = ','.join('%s' for _ in args)
    result = cur.execute('select public.' + name + '(' + placeholders + ')', args).fetchone()[0]
    b.api.admin(cur)
    cur.execute("select set_config('statement_timeout',%s,true)", (prior,))
    return result


def request(cur, today, key, subject=None, q=None):
    return limited(cur, 'erp_cp7_request_staged_analysis_v1', (json.dumps(q or query(today)), key), subject)


def step(cur, key, subject=None, timeout=STATEMENT_TIMEOUT):
    return limited(cur, 'erp_cp7_step_staged_analysis_v1', (key,), subject, timeout)


def status(cur, key, subject=None):
    return limited(cur, 'erp_cp7_get_staged_analysis_v1', (key,), subject)


def checked(job, key, state=None):
    assert job['contract_version'] == 'cp7.native-analysis-staged-job.v1' and job['request_id'] == str(key), job
    assert job['state'] in STATES and (state is None or job['state'] == state), job
    assert job['apply_enabled'] is False and job['production_go'] is False, job
    assert (job.get('run_id') is not None) == (job['state'] == 'DONE'), job
    assert (job.get('failure') is not None) == (job['state'] == 'FAILED'), job
    assert 0 <= job['units_done'] <= job['unit_count'] and 0 <= job['stage_index'] <= job['stage_count'], job
    assert set(job['reference']) == {'captured_at', 'source_hash'} and len(job['reference']['source_hash']) == 64, job
    return job


def drive(cur, key, subject=None):
    """Step until terminal, one call per unit, each under 8 s. Returns the final status and the call log."""
    calls, last = [], checked(status(cur, key, subject), key)
    while last['state'] == 'RUNNING':
        assert len(calls) < DRIVER_CALLS, 'P19G_DRIVER_BOUND'
        started = monotonic()
        nxt = checked(step(cur, key, subject), key)
        calls.append(dict(ms=round((monotonic() - started) * 1000, 3), stage=last['stage'], units_done=nxt['units_done'],
                          unit_attempts=nxt.get('unit_attempts')))
        # Progress is never claimed without a stored unit: each RUNNING step
        # either completes a unit or records an attempt of the same unit.
        assert nxt['units_done'] >= last['units_done'], (last, nxt)
        assert nxt['state'] != 'RUNNING' or nxt['units_done'] > last['units_done'] or nxt.get('unit_attempts', 0) > last.get('unit_attempts', 0), (last, nxt)
        last = nxt
    return last, calls


def sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def parse(text):
    return json.loads(text, parse_float=Decimal)


def fetch(cur, run_id, subject=None):
    """Page set plus every page, verified exactly as the client does; returns the reassembled Original."""
    ps = limited(cur, 'erp_cp7_read_staged_analysis_pages_v1', (run_id,), subject)
    assert ps['contract_version'] == 'cp7.native-analysis-pages.v1' and ps['run_id'] == str(run_id), ps.get('contract_version')
    assert ps['apply_enabled'] is False and ps['production_go'] is False and len(ps['access_epoch']) == 64
    assert 'document' not in ps and 'semantic_hash' not in ps, 'P19G_STAGED_RUN_CLAIMS_A_WHOLE_DOCUMENT'
    h = ps['header']
    assert len(h['body'].encode('utf8')) == h['utf8_bytes'] <= PAGE_BYTES and sha(h['body']) == h['sha256']
    header = parse(h['body'])
    assert header['contract_version'] == 'cp7.native-analysis-header.v1' and header['run_id'] == str(run_id)
    assert header['request_id'] == ps['request_id'] and header['financial_source'] is None
    assert (header['targets_total'], header['page_count'], header['paged']) == (ps['targets_total'], ps['page_count'], ps['paged'])
    assert header['apply_enabled'] is False and header['production_go'] is False
    pages = ps['pages']
    assert [p['index'] for p in pages] == list(range(ps['page_count'])) and ps['page_count'] >= 1
    assert ps['identity_hash'] == sha(h['sha256'] + '\n' + '\n'.join(p['sha256'] for p in pages)), 'P19G_IDENTITY_HASH'
    nxt, bodies, sizes = 1, [], []
    for entry in pages:
        assert entry['target_lo'] == nxt and entry['target_hi'] >= entry['target_lo'], entry
        nxt = entry['target_hi'] + 1
        e = limited(cur, 'erp_cp7_read_staged_analysis_page_v1', (run_id, entry['index'], ps['access_epoch']), subject)
        assert (e['contract_version'], e['run_id'], e['index'], e['page_count'], e['target_lo'], e['target_hi'], e['header_sha256'],
                e['identity_hash']) == ('cp7.native-analysis-page-read.v1', str(run_id), entry['index'], ps['page_count'],
                                        entry['target_lo'], entry['target_hi'], h['sha256'], ps['identity_hash']), e.get('index')
        raw = e['body'].encode('utf8')
        assert len(raw) == e['utf8_bytes'] == entry['utf8_bytes'] <= PAGE_BYTES and sha(e['body']) == e['sha256'] == entry['sha256']
        page = parse(e['body'])
        assert page['contract_version'] == 'cp7.native-analysis-page.v1' and page['run_id'] == str(run_id)
        assert (page['index'], page['target_lo'], page['target_hi'], page['targets_total'], page['header_sha256']) == (
            entry['index'], entry['target_lo'], entry['target_hi'], ps['targets_total'], h['sha256'])
        assert page['counts'] == entry['counts'] and page['apply_enabled'] is False and page['production_go'] is False
        bodies.append(page)
        sizes.append(len(raw))
    assert nxt - 1 == ps['targets_total'], ('P19G_PAGES_DO_NOT_COVER_EVERY_TARGET', nxt - 1, ps['targets_total'])
    # Reassemble: each paged array is its header prefix followed by every
    # page's items in page order; everything else is the header's.
    whole = dict(header['analysis_header'])
    for name, layout in header['paged'].items():
        prefix = whole[name]
        assert len(prefix) == layout['prefix'], (name, len(prefix), layout)
        items = [x for page in bodies for x in page['items'].get(name, [])]
        assert len(items) == layout['items'], (name, len(items), layout)
        whole[name] = prefix + items
    original = dict(contract_version='cp7.native-analysis-run.v1', run_id=header['run_id'], request_id=header['request_id'],
                    analysis=whole, product_labels=header['product_labels'], query=header['query'],
                    financial_source=header['financial_source'], apply_enabled=False, production_go=False)
    return original, ps, dict(page_count=ps['page_count'], targets_total=ps['targets_total'], header_utf8_bytes=h['utf8_bytes'],
                              page_utf8_bytes_max=max(sizes), page_utf8_bytes_total=sum(sizes),
                              uneven_ranges=len({p['target_hi'] - p['target_lo'] for p in pages}) > 1)


def job_row(cur, key, subject=None):
    b.api.admin(cur)
    # actor is auth.uid() (cp7_private.access_now), as in cp7_analysis_native.runs.
    return cur.execute("""select row_to_json(j)::jsonb from cp7_analysis_stage.jobs j where j.request_id=%s
        and (%s::uuid is null or j.actor=%s::uuid)""", (key, subject, subject)).fetchone()[0]


def single_on_reference(cur, job):
    """The single path's compiler on the staged job's own stored reference (admin; immutable build)."""
    b.api.admin(cur)
    r = cur.execute('select cp7_analysis_native.build(%s::jsonb,%s::jsonb,%s,%s::jsonb)::text',
                    (json.dumps(job['reference']), json.dumps(job['query']), job['run_id'],
                     json.dumps(job['access_at_capture']))).fetchone()[0]
    built = parse(r)
    assert 'semantic_hash' in built
    return built


def counts(cur, key):
    b.api.admin(cur)
    return cur.execute("""select (select count(*) from cp7_analysis_native.runs where request_id=%s),
        (select count(*) from cp7_analysis_jobs.jobs where request_id=%s),
        (select count(*) from cp7_analysis_stage.jobs where request_id=%s),
        (select count(*) from cp7_analysis_stage.pages p join cp7_analysis_stage.jobs j on j.run_id=p.run_id where j.request_id=%s)""",
                       (key, key, key, key)).fetchone()


def refused(cur, op, code):
    return auth.refused(cur, op, code)


def staged_done(cur, today, key=None, subject=None, q=None):
    key = key or uuid.uuid4()
    first = checked(request(cur, today, key, subject, q), key, 'RUNNING')
    assert first['units_done'] == 0 and first.get('run_id') is None
    done, calls = drive(cur, key, subject)
    checked(done, key, 'DONE')
    return key, first, done, calls


def cases(cur, today):
    def equals_single():
        f, _ = load.real_workload(cur, today)
        before = b.boundary.snapshot(cur)
        started = monotonic()
        key, first, done, calls = staged_done(cur, today)
        elapsed = round((monotonic() - started) * 1000, 3)
        assert checked(status(cur, key), key, 'DONE') == done and checked(request(cur, today, key), key, 'DONE') == done
        assert checked(step(cur, key), key, 'DONE') == done, 'P19G_STEP_AFTER_DONE_CHANGED_THE_JOB'
        original, ps, shape = fetch(cur, done['run_id'])
        job = job_row(cur, key)
        built = single_on_reference(cur, job)
        expected = {k: v for k, v in built.items() if k != 'semantic_hash'}
        assert original['analysis'] == expected, 'P19G_STAGED_ANALYSIS_DIFFERS_FROM_SINGLE_ON_SAME_REFERENCE'
        # No whole reader serves a staged run (fail closed by construction).
        for name, args in (('erp_cp7_read_analysis_v1', (done['run_id'],)), ('erp_cp7_read_analysis_manifest_v1', (done['run_id'],))):
            refused(cur, lambda: schedule.rpc(cur, name, args), 'CP7_ANALYSIS_RUN_UNAVAILABLE')
        assert counts(cur, key)[:3] == (0, 0, 1)
        assert b.boundary.snapshot(cur) == before
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', request_steps_status_pages_exact=True, units=len(calls), job_elapsed_ms=elapsed,
                    slowest_call_ms=max(c['ms'] for c in calls), statement_timeout=STATEMENT_TIMEOUT, pages=shape,
                    identity_hash=ps['identity_hash'], reassembled_analysis_equals_single_build_on_same_reference=True,
                    whole_readers_refuse_staged_run=True, finance_deferred=True, Native_business_unchanged=True)

    def authority():
        f, _ = load.real_workload(cur, today)
        key, _, done, _ = staged_done(cur, today)
        other, other_role = auth.custom_actor(cur)
        for op in (lambda: status(cur, key, other), lambda: step(cur, key, other)):
            refused(cur, op, 'CP7_ANALYSIS_JOB_UNAVAILABLE')
        for name, args in (('erp_cp7_read_staged_analysis_pages_v1', (done['run_id'],)),
                           ('erp_cp7_check_staged_analysis_source_v1', (done['run_id'],))):
            refused(cur, lambda: limited(cur, name, args, other), 'CP7_ANALYSIS_RUN_UNAVAILABLE')
        own = uuid.uuid4()
        _, _, mine, _ = staged_done(cur, today, own, other)
        _, ps, _ = fetch(cur, mine['run_id'], other)
        refused(cur, lambda: limited(cur, 'erp_cp7_read_staged_analysis_page_v1', (done['run_id'], 0, ps['access_epoch']), other),
                'CP7_ANALYSIS_RUN_UNAVAILABLE')
        # Any change of the actor's current access retires the page-set epoch.
        b.api.admin(cur)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')", (other_role,))
        refused(cur, lambda: limited(cur, 'erp_cp7_read_staged_analysis_page_v1', (mine['run_id'], 0, ps['access_epoch']), other),
                'CP7_ANALYSIS_ACCESS_CHANGED')
        renewed = fetch(cur, mine['run_id'], other)[1]
        assert renewed['access_epoch'] != ps['access_epoch'] and renewed['identity_hash'] == ps['identity_hash']
        b.api.admin(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'", (other_role,))
        for name, args in (('erp_cp7_request_staged_analysis_v1', (json.dumps(query(today)), own)), ('erp_cp7_step_staged_analysis_v1', (own,)),
                           ('erp_cp7_get_staged_analysis_v1', (own,)), ('erp_cp7_read_staged_analysis_pages_v1', (mine['run_id'],)),
                           ('erp_cp7_read_staged_analysis_page_v1', (mine['run_id'], 0, renewed['access_epoch'])),
                           ('erp_cp7_check_staged_analysis_source_v1', (mine['run_id'],))):
            refused(cur, lambda: limited(cur, name, args, other), 'CP7_ACCESS_DENIED')
        # No direct table or private function path for API roles; the six
        # public functions are authenticated only.
        b.api.admin(cur)
        tables = [r[0] for r in cur.execute("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                                            "where n.nspname='cp7_analysis_stage' and c.relkind in ('r','p')").fetchall()]
        assert tables, 'P19G_STAGE_TABLES_NOT_FOUND'
        for who in ('anon', 'authenticated', 'service_role'):
            assert not cur.execute("select has_schema_privilege(%s,'cp7_analysis_stage','USAGE')", (who,)).fetchone()[0], who
            for table in tables:
                assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",
                                       (who, 'cp7_analysis_stage.' + table)).fetchone()[0], (who, table)
            for sig in SIGNATURES:
                assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0] == (who == 'authenticated'), (who, sig)
        for table in tables:
            assert cur.execute("select relrowsecurity from pg_class where oid=%s::regclass", ('cp7_analysis_stage.' + table,)).fetchone()[0], table
        # Outputs are immutable.
        for table in ('pages',):
            refused(cur, lambda: cur.execute('update cp7_analysis_stage.' + table + ' set run_id=run_id'), 'CP7_RUN_IMMUTABLE')
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', foreign_actor_job_pages_source_refused=True, access_epoch_change_refused=True,
                    current_permission_loss_refuses_all_six=True, no_direct_API_path=True, pages_immutable=True,
                    stage_tables=sorted(tables))

    def identity():
        f, _ = load.real_workload(cur, today)
        key = uuid.uuid4()
        first = checked(request(cur, today, key), key, 'RUNNING')
        assert checked(request(cur, today, key), key, 'RUNNING') == first, 'P19G_SAME_UUID_NOT_SAME_JOB'
        changed = query(today)
        changed['group_mode'] = 'RESTATED'
        refused(cur, lambda: request(cur, today, key, q=changed), 'CP7_ANALYSIS_REQUEST_CHANGED')
        # A UUID the actor's ordinary capture or analysis job owns is refused here, and vice versa none is adopted.
        captured = uuid.uuid4()
        analysis.capture(cur, today, captured)
        refused(cur, lambda: request(cur, today, captured), 'CP7_ANALYSIS_REQUEST_CHANGED')
        jobbed = uuid.uuid4()
        schedule.rpc(cur, 'erp_cp7_request_operational_analysis_job_v1', (json.dumps(query(today)), jobbed))
        refused(cur, lambda: request(cur, today, jobbed), 'CP7_ANALYSIS_REQUEST_CHANGED')
        missing = uuid.uuid4()
        for op in (lambda: step(cur, missing), lambda: status(cur, missing)):
            refused(cur, op, 'CP7_ANALYSIS_JOB_UNAVAILABLE')
        refused(cur, lambda: limited(cur, 'erp_cp7_request_staged_analysis_v1', (json.dumps(query(today)), None)), 'CP7_ANALYSIS_REQUEST_REQUIRED')
        for name, args in (('erp_cp7_read_staged_analysis_pages_v1', (uuid.uuid4(),)),
                           ('erp_cp7_check_staged_analysis_source_v1', (uuid.uuid4(),))):
            refused(cur, lambda: limited(cur, name, args), 'CP7_ANALYSIS_RUN_UNAVAILABLE')
        # Epoch validation precedes run lookup, like the ordinary segment
        # reader. Test a bad epoch and an unknown run separately.
        refused(cur, lambda: limited(cur, 'erp_cp7_read_staged_analysis_page_v1', (uuid.uuid4(), 0, '0' * 64)),
                'CP7_ANALYSIS_ACCESS_CHANGED')
        # A running job exposes no page.
        assert first.get('run_id') is None and counts(cur, key)[2:] == (1, 0)
        done, _ = drive(cur, key)
        _, ps, _ = fetch(cur, done['run_id'])
        refused(cur, lambda: limited(cur, 'erp_cp7_read_staged_analysis_page_v1', (uuid.uuid4(), 0, ps['access_epoch'])),
                'CP7_ANALYSIS_RUN_UNAVAILABLE')
        for index in (ps['page_count'], -1):
            refused(cur, lambda: limited(cur, 'erp_cp7_read_staged_analysis_page_v1', (done['run_id'], index, ps['access_epoch'])),
                    'CP7_ANALYSIS_PAGE_UNAVAILABLE')
        assert counts(cur, missing) == (0, 0, 0, 0)
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', same_UUID_same_job=True, changed_query_refused=True, ordinary_capture_or_job_UUID_refused=True,
                    missing_UUID_refused=True, foreign_or_missing_run_refused=True, running_job_exposes_no_page=True,
                    out_of_range_page_refused=True)

    def source_check():
        f, _ = load.real_workload(cur, today)
        key, _, done, _ = staged_done(cur, today)
        first = limited(cur, 'erp_cp7_check_staged_analysis_source_v1', (done['run_id'],))
        assert first['source_state'] == 'UNCHANGED' and set(first) >= {'source_state', 'checked_at'}, first
        original, ps, _ = fetch(cur, done['run_id'])
        analysis.setup(cur, today)
        stale = limited(cur, 'erp_cp7_check_staged_analysis_source_v1', (done['run_id'],))
        assert stale['source_state'] == 'ARCHIVED_STALE', stale
        again, ps2, _ = fetch(cur, done['run_id'])
        assert again == original and ps2['identity_hash'] == ps['identity_hash'], 'P19G_ARCHIVED_RUN_CHANGED'
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', unchanged_then_archived_stale=True, archived_pages_unchanged=True, one_statement_check=True)

    def bounds_vs_single():
        """The staged bounds are declared once and read back; within them the staged job completes where the
        single path refuses (its grid cap is unchanged); beyond them both paths refuse with the same code and
        nothing is paged. Seeded through the scale ladder's ordinary writers inside this rolled-back case."""
        import cp7_p19_scale_cases as scale
        bounds = scale.staged_bounds(cur)
        assert bounds['declared_match'], ('P19G_STAGED_BOUNDS_DIFFER_FROM_DECLARED', bounds)
        size, days = scale.NATIVE_CASE['size'], scale.NATIVE_CASE['grid_cap_days']
        seed = scale.ensure(cur, today, size, False)
        targets = scale.current_targets(cur)
        cells = len(targets) * days
        assert len(targets) == size and 100000 < cells <= scale.STAGED_BOUNDS['job_history_cells'], (len(targets), days)
        q = analysis.previous.baseline.history.query(today, days)
        single = refused(cur, lambda: schedule.rpc(cur, 'erp_cp7_capture_operational_analysis_v1', (json.dumps(q), uuid.uuid4())), '_GRID_LIMIT')
        single_code = re.search(r'CP7_[A-Z0-9_]+', single).group(0)
        key = uuid.uuid4()
        checked(request(cur, today, key, q=q), key, 'RUNNING')
        done, calls = drive(cur, key)
        checked(done, key, 'DONE')
        original, ps, shape = fetch(cur, done['run_id'])
        x = original['analysis']
        cover = scale.coverage([label['target_key'] for label in original['product_labels']],
                               [r['target']['key'] for r in x['recommendations']], x['generation_warnings'], x['status'], targets)
        assert cover['complete'] and ps['targets_total'] == size, ('P19G_STAGED_COVERAGE_INCOMPLETE', cover)
        # The reassembled analysis passes the frozen contract with its semantic_hash recomputed server side.
        b.api.admin(cur)
        pages = [cur.execute('select p.body from cp7_analysis_stage.pages p where p.run_id=%s and p.idx=%s', (done['run_id'], i)).fetchone()[0]
                 for i in range(ps['page_count'])]
        reassembled, _ = scale.staged_reassemble(cur, ps['header']['body'], pages)
        analysis.checked({**original, 'analysis': reassembled, 'source_state': 'UNCHANGED'})
        assert {k: v for k, v in reassembled.items() if k != 'semantic_hash'} == x, 'P19G_SERVER_REASSEMBLY_DIFFERS_FROM_CLIENT_REASSEMBLY'
        # Beyond the staged bound: more cells than job_history_cells.
        beyond_days = 3660
        beyond_size = scale.STAGED_BOUNDS['job_history_cells'] // beyond_days + 4
        scale.ensure(cur, today, beyond_size, True)
        beyond = scale.current_targets(cur)
        assert len(beyond) == beyond_size and len(beyond) * beyond_days > scale.STAGED_BOUNDS['job_history_cells'], (len(beyond), beyond_days)
        q2 = analysis.previous.baseline.history.query(today, beyond_days)
        single2 = refused(cur, lambda: schedule.rpc(cur, 'erp_cp7_capture_operational_analysis_v1', (json.dumps(q2), uuid.uuid4())), '_GRID_LIMIT')
        single2_code = re.search(r'CP7_[A-Z0-9_]+', single2).group(0)
        key2 = uuid.uuid4()
        b.api.admin(cur)
        cur.execute('savepoint p19g_beyond')
        try:
            started = checked(request(cur, today, key2, q=q2), key2)
            cur.execute('release savepoint p19g_beyond')
            failed, _ = drive(cur, key2) if started['state'] == 'RUNNING' else (started, [])
            checked(failed, key2, 'FAILED')
            staged_code, where = failed['failure']['code'], 'unit ' + str(failed['failure']['unit'])
            assert counts(cur, key2)[3] == 0 and failed.get('run_id') is None, 'P19G_FAILED_JOB_EXPOSED_PAGES'
            assert checked(step(cur, key2), key2, 'FAILED') == failed, 'P19G_STEP_AFTER_FAILED_CHANGED_THE_JOB'
        except psycopg.Error as error:
            detail = (error.diag.message_primary or str(error)).strip()
            cur.execute('rollback to savepoint p19g_beyond')
            b.api.admin(cur)
            staged_code, where = re.search(r'CP7_[A-Z0-9_]+', detail).group(0), 'request'
            assert counts(cur, key2) == (0, 0, 0, 0)
        assert staged_code == 'CP7_PLANNING_HISTORY_GRID_LIMIT' == single2_code, (staged_code, single2_code)
        return dict(status='PASS', bounds=bounds, within=dict(targets=size, history_days=days, cells=cells, single_refusal=single_code,
                    staged_state='DONE', units=len(calls), slowest_call_ms=max(c['ms'] for c in calls), pages=shape, coverage=cover,
                    frozen_contract_valid=True, semantic_hash_recomputed_from_reassembly=True),
                    beyond=dict(targets=beyond_size, history_days=beyond_days, cells=beyond_size * beyond_days, single_refusal=single2_code,
                                staged_refusal=staged_code, staged_refused_at=where, nothing_paged=True),
                    single_path_caps_unchanged=True, seed_ms_not_app_latency=seed.get('seed_ms'))

    return list(zip(IDS['native'], (equals_single, authority, identity, source_check, bounds_vs_single)))


def races(tools, today):
    def prepared(subject=None):
        key = uuid.uuid4()
        with tools.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            if subject == 'custom':
                subject, role = auth.custom_actor(cur)
            else:
                role = None
            checked(request(cur, today, key, subject), key, 'RUNNING')
            conn.commit()
        return key, f, subject, role

    def two_steps():
        key, f, _, _ = prepared()
        with tools.connect() as conn, conn.cursor() as cur:
            before = checked(status(cur, key), key, 'RUNNING')
            conn.commit()
        with tools.connect() as holder, holder.cursor() as h:
            # The first worker holds the job row exactly as a running unit does.
            h.execute('select 1 from cp7_analysis_stage.jobs where request_id=%s for update', (key,))

            def send():
                with tools.connect() as conn, conn.cursor() as cur:
                    result = step(cur, key)
                    conn.commit()
                    return result
            with ThreadPoolExecutor(max_workers=1) as pool:
                skipped = pool.submit(send).result(30)
            holder.rollback()
        assert skipped['worker_active'] is True and skipped['units_done'] == before['units_done'], skipped
        gate = threading.Barrier(2)

        def racing():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                result = step(cur, key)
                conn.commit()
                return result
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [job.result(60) for job in [pool.submit(racing), pool.submit(racing)]]
        with tools.connect() as conn, conn.cursor() as cur:
            after = checked(status(cur, key), key)
            conn.commit()
        ran = [r for r in results if not r.get('worker_active')]
        assert after['units_done'] - before['units_done'] == len(ran) and len(ran) in (1, 2), (before, results, after)
        assert len(ran) == 2 or any(r.get('worker_active') for r in results), results
        with tools.connect() as conn, conn.cursor() as cur:
            done, _ = drive(cur, key)
            conn.commit()
            assert done['state'] == 'DONE'
            bridge.literal(cur, f, '175.00')
        return dict(status='PASS', locked_job_step_runs_nothing_worker_active=True, concurrent_steps_never_run_one_unit_twice=True,
                    results=results)

    def limit():
        key, f, _, _ = prepared()
        stops = []
        with tools.connect() as holder, holder.cursor() as h:
            # Units read the stored reference, never the live tables: the next
            # unit's output INSERT waits on a real lock until the existing
            # kind of statement limit stops it inside the unit handler.
            # Locking units/headers also blocks compilation of the function's
            # composite argument types before the handler can even be entered.
            locks = h.execute("""select string_agg(format('lock table %I.%I in exclusive mode',n.nspname,c.relname),';')
                from pg_class c join pg_namespace n on n.oid=c.relnamespace
                where n.nspname='cp7_analysis_stage' and c.relkind in('r','p') and c.relname='outputs'""").fetchone()[0]
            assert locks, 'P19G_STAGE_TABLES_NOT_FOUND'
            h.execute(locks)

            def send():
                with tools.connect() as conn, conn.cursor() as cur:
                    result = step(cur, key, timeout='3s')
                    conn.commit()
                    return result
            with ThreadPoolExecutor(max_workers=1) as pool:
                for _ in range(2):
                    stops.append(pool.submit(send).result(30))
            holder.rollback()
        assert all(s['state'] == 'RUNNING' for s in stops) and [s['unit_attempts'] for s in stops] == [1, 2], stops
        assert all(s['units_done'] == 0 for s in stops), 'P19G_STOP_SAVED_A_PARTIAL_UNIT'
        with tools.connect() as conn, conn.cursor() as cur:
            done, calls = drive(cur, key)
            conn.commit()
            assert done['state'] == 'DONE'
            bridge.literal(cur, f, '175.00')
        return dict(status='PASS', statement_limit_stop_recorded_as_attempt=True, job_continues_after_lock_release=True,
                    stops=stops, units_after=len(calls))

    def access_changed():
        key, f, subject, role = prepared('custom')
        with tools.connect() as conn, conn.cursor() as cur:
            first = checked(step(cur, key, subject), key)
            conn.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')", (role,))
            conn.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            failed = checked(step(cur, key, subject), key, 'FAILED')
            conn.commit()
        assert failed['failure']['code'] == 'CP7_ANALYSIS_ACCESS_CHANGED' and failed['units_done'] == first['units_done'], failed
        with tools.connect() as conn, conn.cursor() as cur:
            assert checked(status(cur, key, subject), key, 'FAILED') == failed
            assert counts(cur, key)[3] == 0
            bridge.literal(cur, f, '175.00')
        return dict(status='PASS', access_change_between_units_fails_job=True, no_mixed_access_pages=True, failed=failed['failure'])

    return list(zip(IDS['races'], (two_steps, limit, access_changed)))


def http_cases(http, today):
    state = {}

    def ok(user, name, payload):
        r = user.rpc(name, payload)
        assert r['status'] == 200, (name, r)
        return r['body']

    def flow():
        owner = http.login('OWNER', 'p19g-owner')
        other = http.login('OWNER', 'p19g-other')
        with http.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            conn.commit()
        key = str(uuid.uuid4())
        args = dict(p_query=query(today), p_request=key)
        job = ok(owner, 'erp_cp7_request_staged_analysis_v1', args)
        assert job['state'] == 'RUNNING'
        started, calls = monotonic(), 0
        while job['state'] == 'RUNNING':
            assert calls < DRIVER_CALLS
            job = ok(owner, 'erp_cp7_step_staged_analysis_v1', dict(p_request=key))
            calls += 1
        elapsed = round((monotonic() - started) * 1000, 3)
        assert job['state'] == 'DONE' and ok(owner, 'erp_cp7_get_staged_analysis_v1', dict(p_request=key)) == job
        ps = ok(owner, 'erp_cp7_read_staged_analysis_pages_v1', dict(p_run=job['run_id']))
        bodies = [ok(owner, 'erp_cp7_read_staged_analysis_page_v1', dict(p_run=job['run_id'], p_index=i, p_access=ps['access_epoch']))
                  for i in range(ps['page_count'])]
        assert all(sha(e['body']) == e['sha256'] and e['identity_hash'] == ps['identity_hash'] for e in bodies)
        assert ps['identity_hash'] == sha(ps['header']['sha256'] + '\n' + '\n'.join(e['sha256'] for e in bodies))
        checked_source = ok(owner, 'erp_cp7_check_staged_analysis_source_v1', dict(p_run=job['run_id']))
        assert checked_source['source_state'] == 'UNCHANGED'
        foreign = [other.rpc('erp_cp7_read_staged_analysis_pages_v1', dict(p_run=job['run_id']))['status'],
                   other.rpc('erp_cp7_read_staged_analysis_page_v1', dict(p_run=job['run_id'], p_index=0, p_access=ps['access_epoch']))['status'],
                   other.rpc('erp_cp7_check_staged_analysis_source_v1', dict(p_run=job['run_id']))['status']]
        assert foreign == [403, 403, 403], foreign
        missing = other.rpc('erp_cp7_get_staged_analysis_v1', dict(p_request=key))
        assert missing['status'] == 400 and 'CP7_ANALYSIS_JOB_UNAVAILABLE' in json.dumps(missing['body']), missing
        whole = owner.rpc('erp_cp7_read_analysis_v1', dict(p_run=job['run_id']))
        assert whole['status'] == 403 and 'CP7_ANALYSIS_RUN_UNAVAILABLE' in json.dumps(whole['body']), whole
        anonymous = [http.anon_rpc(name, payload)['status'] for name, payload in (
            ('erp_cp7_request_staged_analysis_v1', args), ('erp_cp7_step_staged_analysis_v1', dict(p_request=key)),
            ('erp_cp7_get_staged_analysis_v1', dict(p_request=key)), ('erp_cp7_read_staged_analysis_pages_v1', dict(p_run=job['run_id'])),
            ('erp_cp7_read_staged_analysis_page_v1', dict(p_run=job['run_id'], p_index=0, p_access=ps['access_epoch'])),
            ('erp_cp7_check_staged_analysis_source_v1', dict(p_run=job['run_id'])))]
        assert all(code in (401, 403) for code in anonymous), anonymous
        with http.connect() as conn, conn.cursor() as cur:
            assert counts(cur, key)[:3] == (0, 0, 1)
            bridge.literal(cur, f, '175.00')
        state.update(owner=owner, key=key, run=job['run_id'], epoch=ps['access_epoch'], args=args)
        return dict(status='PASS', real_Auth_request_steps_get_pages_check=True, actual_HTTP_steps=calls, actual_HTTP_job_ms=elapsed,
                    page_count=ps['page_count'], foreign_403=True, foreign_job_unknown=True, whole_reader_refuses_staged_run=True,
                    anonymous_refused=anonymous)

    def revoked():
        assert state, 'P19G_REQUIRED_PRIOR_HTTP_CASE'
        owner = state['owner']
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner.auth_user_id,))
            conn.commit()
        codes = [owner.rpc(name, payload)['status'] for name, payload in (
            ('erp_cp7_request_staged_analysis_v1', state['args']), ('erp_cp7_step_staged_analysis_v1', dict(p_request=state['key'])),
            ('erp_cp7_get_staged_analysis_v1', dict(p_request=state['key'])), ('erp_cp7_read_staged_analysis_pages_v1', dict(p_run=state['run'])),
            ('erp_cp7_read_staged_analysis_page_v1', dict(p_run=state['run'], p_index=0, p_access=state['epoch'])),
            ('erp_cp7_check_staged_analysis_source_v1', dict(p_run=state['run'])))]
        assert codes == [403] * 6, codes
        with http.connect() as conn, conn.cursor() as cur:
            assert counts(cur, state['key'])[:3] == (0, 0, 1)
        return dict(status='PASS', deactivated_user_all_six_403=True, no_new_effect=True)

    return list(zip(IDS['http'], (flow, revoked)))
