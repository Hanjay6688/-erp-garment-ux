"""P19 Business Report v2: a published report of a staged analysis snapshot (snapshot contract v2 §4).

Owner decision 8 Oct 2026: the report may use a snapshot that is no longer
current as analysis, always labelled "Data analisis per <time>" with its
freshness and the changes since, and never called current; actual finance,
stock and HPP figures follow the authoritative sources at the report date.
The report is built one unit per ordinary request under the unchanged 8 s
statement limit (actuals, one section per page of the run, freshness,
summary) and sealed once. Real Native E01 facts and staged runs, real
concurrent sessions and real Auth/PostgREST calls on the closed harness; the
v1 report path is not changed by any case.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from queue import Queue
from time import monotonic
import json
import threading
import time
import uuid

import psycopg

import cp7_p19_staged_cases as staged
import cp7_p19_native_load_cases as load
import cp7_p18_e01_bridge_cases as bridge
import cp7_analysis_cases as analysis
import cp7_analysis_finance_cases as finance_cases
import cp7_fg_cases as fg

IDS = dict(
    native=['P19R_PUBLISH_STEPS_SEAL', 'P19R_ACTUAL_STOCK_AT_REPORT_TIME', 'P19R_FRESHNESS_STATES_WORDED', 'P19R_FINANCE_FROM_OWNER_REPORT',
            'P19R_FINANCE_ACCESS_CURRENT', 'P19R_REVISION_SERIES', 'P19R_REQUEST_ONE_UUID', 'P19R_AUTHORITY', 'P19R_FIELDS_AND_IDENTITY',
            'P19R_V1_APART'],
    races=['P19R_RACE_TWO_STEPS_ONE_UNIT', 'P19R_RACE_TWO_REVISIONS_ONE_SEALS', 'P19R_RACE_STOCK_COMMITTED_DURING_JOB',
           'P19R_RACE_ACCESS_CHANGED_MID_JOB', 'P19R_RACE_SAME_UUID_TWO_SESSIONS', 'P19R_RACE_LIMIT_RETRIES_THEN_CONTINUES'],
    http=['P19R_HTTP_FLOW', 'P19R_HTTP_REVOKED'],
    browser=['P19R_BROWSER_DESKTOP_REPORT', 'P19R_BROWSER_MOBILE_REPORT'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.p19.report-v2.v1'
FUNCTIONS = ('erp_cp7_publish_report_v2', 'erp_cp7_get_report_request_v2', 'erp_cp7_step_report_v2', 'erp_cp7_read_report_v2',
             'erp_cp7_read_report_section_v2', 'erp_cp7_list_reports_v2')
SIGNATURES = ('public.erp_cp7_publish_report_v2(jsonb,uuid)', 'public.erp_cp7_get_report_request_v2(jsonb,uuid)', 'public.erp_cp7_step_report_v2(uuid)',
              'public.erp_cp7_read_report_v2(uuid)', 'public.erp_cp7_read_report_section_v2(uuid,integer,text)', 'public.erp_cp7_list_reports_v2(jsonb)')
TABLES = ('report_jobs', 'report_reads', 'report_sections', 'report_publications')
TEMPLATE = 'native-report-staged-1'
DRIVER_CALLS = 20000
auth, b = staged.auth, staged.b


def limited(cur, name, args, subject=None, timeout=staged.STATEMENT_TIMEOUT):
    return staged.limited(cur, name, args, subject, timeout)


def publish(cur, p, key=None, subject=None, lookup=False):
    name = 'erp_cp7_get_report_request_v2' if lookup else 'erp_cp7_publish_report_v2'
    return checked(limited(cur, name, (json.dumps(p), key or uuid.uuid4()), subject))


def step(cur, key, subject=None, timeout=staged.STATEMENT_TIMEOUT):
    return checked(limited(cur, 'erp_cp7_step_report_v2', (key,), subject, timeout))


def read(cur, pid, subject=None):
    return limited(cur, 'erp_cp7_read_report_v2', (pid,), subject)


def section(cur, pid, index, epoch, subject=None):
    return limited(cur, 'erp_cp7_read_report_section_v2', (pid, index, epoch), subject)


def index(cur, before=None, limit=50, subject=None):
    return limited(cur, 'erp_cp7_list_reports_v2', (json.dumps(dict(before_id=before, limit=limit)),), subject)


def checked(s):
    """Every job status field the contract fixes."""
    assert s['contract_version'] == 'cp7.report-job.v2' and s['production_go'] is False, s
    assert s['state'] in ('RUNNING', 'DONE', 'FAILED', 'CLOSED_UNCOMMITTED'), s
    assert (s['stage'] is None) == (s['state'] != 'RUNNING'), s
    assert (s['publication_id'] is not None) == (s['state'] == 'DONE') and (s['failure'] is not None) == (s['state'] == 'FAILED'), s
    assert 0 <= s['units_done'] <= s['unit_count'] and (s['unit_count'] == 0) == (s['state'] == 'CLOSED_UNCOMMITTED'), s
    assert s['state'] == 'CLOSED_UNCOMMITTED' or s['unit_count'] == s['section_count'] + 3, s
    return s


def drive(cur, key, subject=None):
    """Step until terminal, one unit per call, each under 8 s; returns the final status and the call log."""
    calls, last = [], publish_status(cur, key, subject)
    while last['state'] == 'RUNNING':
        assert len(calls) < DRIVER_CALLS, 'P19R_DRIVER_BOUND'
        started = monotonic()
        nxt = step(cur, key, subject)
        calls.append(dict(ms=round((monotonic() - started) * 1000, 3), stage=last['stage'], units_done=nxt['units_done']))
        assert nxt['units_done'] >= last['units_done'], (last, nxt)
        assert nxt['state'] != 'RUNNING' or nxt['units_done'] > last['units_done'] or nxt['unit_attempts'] > last['unit_attempts'], (last, nxt)
        last = nxt
    return last, calls


def publish_status(cur, key, subject=None):
    b.api.admin(cur)
    p = cur.execute('select payload from cp7_analysis_stage.report_jobs where request_id=%s', (key,)).fetchone()[0]
    return publish(cur, p, key, subject)


def wib(t):
    if isinstance(t, str):
        t = datetime.fromisoformat(t)
    return (t + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') + ' WIB'


def fact(v):
    """cp7_analysis_native.report_fact, written independently."""
    if v.get('state') == 'UNKNOWN':
        return 'Belum diketahui (' + (v.get('reason') or 'sumber belum terbukti') + ')'
    return (v.get('value') if v.get('value') is not None else 'Belum diketahui') + ' ' + (v.get('unit') or '') + (' [asumsi]' if v.get('state') == 'ASSUMED' else '')


def payload(r, **kw):
    p = dict(run_id=r['run'], identity_hash=r['identity'], kind='DAILY', series_id=None, expected_revision=None, title='P19 report v2 briefing',
             reason='P19 report v2: reviewed report of a dated staged snapshot', finance='DEFERRED', explicit_review=True)
    p.update(kw)
    return p


def staged_run(cur, today, subject=None, q=None):
    key, _, done, _ = staged.staged_done(cur, today, subject=subject, q=q)
    original, ps, shape = staged.fetch(cur, done['run_id'], subject)
    job = staged.job_row(cur, key, subject)
    return dict(key=key, run=done['run_id'], identity=ps['identity_hash'], captured=datetime.fromisoformat(job['captured_at']),
                original=original, ps=ps, pages=shape['page_count'], job=job['id'], query=job['query'])


def published(cur, r, subject=None, **kw):
    key = uuid.uuid4()
    first = publish(cur, payload(r, **kw), key, subject)
    assert first['state'] == 'RUNNING' and first['stage'] == 'ACTUALS' and first['section_count'] == r['pages'], first
    done, calls = drive(cur, key, subject)
    assert done['state'] == 'DONE', done
    return key, done, calls


def document(cur, pid, subject=None):
    """The publication and every section, verified as the client does: hashes, report hash, contiguous ranges."""
    d = read(cur, pid, subject)
    assert d['contract_version'] == 'cp7.report-publication.v2' and d['id'] == str(pid) and d['production_go'] is False, d.get('contract_version')
    assert d['template_version'] == TEMPLATE and len(d['access_epoch']) == 64, d['template_version']
    assert staged.sha(d['summary']) == d['summary_sha256'], 'P19R_SUMMARY_HASH'
    bodies, nxt = [], 1
    for entry in d['sections']:
        e = section(cur, pid, entry['index'], d['access_epoch'], subject)
        assert (e['contract_version'], e['publication_id'], e['index'], e['section_count'], e['target_lo'], e['target_hi'], e['report_hash']) == (
            'cp7.report-section.v2', str(pid), entry['index'], len(d['sections']), entry['target_lo'], entry['target_hi'], d['report_hash']), e.get('index')
        assert staged.sha(e['body']) == e['sha256'] == entry['sha256'] and len(e['body'].encode('utf8')) == e['utf8_bytes'] == entry['utf8_bytes'] <= 8000000
        assert entry['target_lo'] == nxt, ('P19R_SECTION_RANGE', entry, nxt)
        nxt = entry['target_hi'] + 1
        bodies.append(e['body'])
    assert [s['index'] for s in d['sections']] == list(range(len(d['sections'])))
    assert nxt - 1 == d['targets_total'], ('P19R_SECTIONS_DO_NOT_COVER_EVERY_TARGET', nxt - 1, d['targets_total'])
    assert d['report_hash'] == staged.sha('\n'.join([d['summary_sha256']] + [s['sha256'] for s in d['sections']])), 'P19R_REPORT_HASH'
    for text in [d['summary']] + bodies:
        assert 'terkini' not in text.lower(), 'P19R_SNAPSHOT_CALLED_CURRENT'
    return d, bodies


def stock(cur, root, at):
    """Finished stock of one product root at a time, by the analysis' own rules, written independently of the SQL."""
    b.api.admin(cur)
    rows = cur.execute("""select m.qty_signed,m.movement_type,m.reversal_of_id::text,m.quality_grade from erp.fg_stock_movements m
        join erp.products p on p.id=m.product_id where coalesce(p.identity_root_id,p.id)=%s::uuid and m.physical_at<=%s and m.system_created_at<=%s""",
                       (root, at, at)).fetchall()
    reserves = {r[0] for r in cur.execute("select id::text from erp.fg_stock_movements where movement_type='SALE_RESERVE'").fetchall()}
    ab = [r for r in rows if r[3] in ('GRADE_A', 'GRADE_B')]
    return sum(q for q, kind, rev, _ in ab if kind != 'SALE_RESERVE' and rev not in reserves), sum(q for q, _, _, _ in ab)


def target_lines(r, read_at, cur):
    """The expected head of every target's line, per page, from the run's own pages and the independent stock read."""
    labels = {}
    for lb in r['original']['product_labels']:
        labels.setdefault(lb['target_key'], []).append(lb)
    state = dict(ACTIVE='Aktif', PAUSED='Ditunda', STOPPED='Dihentikan')
    out, consistent = [], 0
    for rec in r['original']['analysis']['recommendations']:
        key = rec['target']['key']
        (lb,) = labels[key]
        physical, available = stock(cur, key.split(':')[0], read_at)
        at_snapshot = stock(cur, key.split(':')[0], r['captured'])
        if rec['actual_fg'].get('state') == 'KNOWN':
            assert str(at_snapshot[0]) == rec['actual_fg']['value'], ('P19R_SNAPSHOT_STOCK_RULE', key, at_snapshot, rec['actual_fg'])
            consistent += 1
        out.append((key, (lb['sku'] or key) + ' · ' + (lb['product_name'] or '') + ' · size ' + rec['target']['size_id'] + ' · ' +
                    state.get(rec['production_state'], 'Status lain') + ': stok fisik saat analisis ' + fact(rec['actual_fg']) +
                    '; stok fisik aktual per ' + wib(read_at) + ' ' + str(physical) + ' PCS; stok tersedia setelah reservasi aktual ' +
                    str(available) + ' PCS; target ' + fact(rec['target_qty']) + '; gap dasar ' + fact(rec['q_base'])))
    return out, consistent


def found_fg(cur, root, pcs):
    """Finished stock of a target found at a count, through the unchanged Native writer."""
    at = fg.ax.r1.now(cur) - timedelta(minutes=50)
    b.api.admin(cur)
    p = dict(source_kind='FOUND_AT_OPNAME', product_id=root, location_id=fg.base.LOCATION, qty_pcs=pcs, physical_at=at.isoformat(),
             reason='P19 report v2 finished stock found after the snapshot')
    # The writer's own rule: with an HPP reference the value follows its average;
    # an owner value is allowed (and required) only when there is none.
    if cur.execute('select erp.fg_unsourced_valuation_v1(%s,%s)->>%s', (root, at, 'tier')).fetchone()[0] == 'OWNER_INPUT_REQUIRED':
        p.update(owner_unit_value='10', owner_value_reason='P19 report v2 explicit independently supplied value')
    fg.ax.post(cur, p)
    b.api.admin(cur)


def first_root(r):
    return r['original']['analysis']['recommendations'][0]['target']['key'].split(':')[0]


def jobs_and_publications(cur):
    b.api.admin(cur)
    return cur.execute('select (select count(*)from cp7_analysis_stage.report_jobs),(select count(*)from cp7_analysis_stage.report_publications)').fetchone()


def refused(cur, op, code, sqlstate=None):
    b.api.admin(cur)
    cur.execute('savepoint p19r_refusal')
    try:
        op()
    except psycopg.Error as e:
        cur.execute('rollback to savepoint p19r_refusal')
        b.api.admin(cur)
        cur.execute('release savepoint p19r_refusal')
        assert e.diag.message_primary == code and (sqlstate is None or e.sqlstate == sqlstate), (code, sqlstate, e.sqlstate, e.diag.message_primary)
        return e.sqlstate
    cur.execute('rollback to savepoint p19r_refusal')
    b.api.admin(cur)
    raise AssertionError(('P19R_EXPECTED_REFUSAL', code))


def actuals(cur, job):
    b.api.admin(cur)
    return cur.execute("select r.body from cp7_analysis_stage.report_reads r join cp7_analysis_stage.report_jobs j on j.id=r.job_id "
                       "where j.request_id=%s and r.kind='ACTUALS'", (job,)).fetchone()[0]


def cases(cur, today):
    def publish_steps_seal():
        f, _ = load.real_workload(cur, today)
        r = staged_run(cur, today)
        before = b.boundary.snapshot(cur)
        key = uuid.uuid4()
        p = payload(r)
        first = publish(cur, p, key)
        assert (first['run_id'], first['identity_hash'], datetime.fromisoformat(first['data_as_of'])) == (r['run'], r['identity'], r['captured']), first
        assert first['finance'] == 'DEFERRED' and first['revision'] == '1' and first['units_done'] == 0, first
        assert publish(cur, p, key) == first, 'P19R_SAME_UUID_NOT_SAME_JOB'
        done, calls = drive(cur, key)
        assert [c['stage'] for c in calls] == ['ACTUALS'] + ['SECTION'] * r['pages'] + ['FRESHNESS', 'SUMMARY'], calls
        assert step(cur, key) == done and publish(cur, p, key) == done, 'P19R_STEP_AFTER_DONE_CHANGED_THE_JOB'
        d, bodies = document(cur, done['publication_id'])
        assert (d['run_id'], d['identity_hash'], datetime.fromisoformat(d['data_as_of']), d['kind'], d['revision'], d['is_latest']) == (
            r['run'], r['identity'], r['captured'], 'DAILY', '1', True), d
        assert d['finance'] == 'DEFERRED' and d['financial_source_hash'] is None and d['period_query'] == r['query'], d
        assert d['summary'].startswith(p['title'] + '\n\nBRIEFING HARIAN\n\n'), d['summary'][:200]
        label = 'Data analisis per ' + wib(r['captured'])
        assert label in d['summary'] and all(label in s for s in bodies), 'P19R_SNAPSHOT_TIME_LABEL'
        assert 'bukan angka saat ini' in d['summary'] and 'Keuangan dan HPP tidak dimasukkan ke laporan ini. Tidak ada angka pengganti.' in d['summary']
        assert len(bodies) == r['pages'] and d['targets_total'] == r['ps']['targets_total'], (len(bodies), r['pages'])
        assert b.boundary.snapshot(cur) == before, 'P19R_REPORT_CHANGED_NATIVE_BUSINESS'
        bridge.literal(cur, f, '175.00')
        assert jobs_and_publications(cur) == (1, 1)
        return dict(status='PASS', one_unit_per_request=len(calls), slowest_call_ms=max(c['ms'] for c in calls), statement_timeout=staged.STATEMENT_TIMEOUT,
                    stages=sorted({c['stage'] for c in calls}), sections=len(bodies), summary_bytes=len(d['summary'].encode('utf8')),
                    data_as_of_label=label, hashes_verified=True, replay_same_job=True, never_called_current=True, Native_business_unchanged=True)

    def actual_stock():
        f, _ = load.real_workload(cur, today)
        r = staged_run(cur, today)
        root = first_root(r)
        snap = stock(cur, root, r['captured'])
        found_fg(cur, root, 3)
        key, done, _ = published(cur, r)
        d, bodies = document(cur, done['publication_id'])
        read_at = datetime.fromisoformat(d['actuals_read_at'])
        assert read_at > r['captured'] and d['report_date'] == (read_at + timedelta(hours=7)).date().isoformat(), d['report_date']
        lines, consistent = target_lines(r, read_at, cur)
        text = '\n'.join(bodies)
        for k, line in lines:
            assert line in text, ('P19R_TARGET_LINE', k, line)
        now = stock(cur, root, read_at)
        assert now[0] == snap[0] + 3 and now[1] == snap[1] + 3, (snap, now)
        assert d['freshness']['state'] == 'CHANGES_RECORDED' and int(d['freshness']['changes_total']) >= 1, d['freshness']
        assert 'Stok barang jadi: ' in d['summary'] and 'isi analisis tetap keadaan per ' + wib(r['captured']) in d['summary'], d['summary'][:1500]
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', targets=len(lines), snapshot_stock_rule_equals_independent_read=consistent,
                    actual_stock_read_at_report_time_beside_snapshot=True, found_after_snapshot_pcs=3, snapshot=snap, actual=now,
                    freshness=d['freshness'])

    def freshness_states():
        f, _ = load.real_workload(cur, today)
        r = staged_run(cur, today)
        same = staged.recorded_check(cur, r['run'], 'RECORDING_TIME')
        assert same['source_state'] == 'UNCHANGED', same
        _, done, _ = published(cur, r)
        d1, _ = document(cur, done['publication_id'])
        assert d1['freshness']['state'] == 'VERIFIED_SAME', d1['freshness']
        assert 'Sama dengan data per ' + wib(same['checked_at']) + ' menurut cek sumber penuh' in d1['summary'], d1['summary'][:1200]
        # An actual source change: finished stock of a target found after the snapshot.
        found_fg(cur, first_root(r), 1)
        stale = staged.recorded_check(cur, r['run'], 'RECORDING_TIME')
        assert stale['source_state'] == 'ARCHIVED_STALE', stale
        # The same series, revised over the same snapshot after the source changed.
        _, done2, _ = published(cur, r, series_id=d1['series_id'], expected_revision='1', title='P19 report v2 briefing (revised)')
        d2, _ = document(cur, done2['publication_id'])
        assert d2['freshness']['state'] == 'STALE_VERIFIED' and d2['revision'] == '2', d2['freshness']
        assert 'Data sudah berubah menurut cek sumber penuh ' + wib(stale['checked_at']) + '; isi analisis tetap keadaan per ' + wib(r['captured']) in d2['summary']
        assert read(cur, d1['id'])['is_latest'] is False and d2['is_latest'] is True
        assert d1['summary'] == read(cur, d1['id'])['summary'], 'P19R_PUBLICATION_CHANGED'
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', verified_same_worded_with_check_time=True, stale_verified_worded_snapshot_kept=True, never_called_current=True,
                    revision_over_same_snapshot=True)

    def finance_owner_report():
        f, _ = load.real_workload(cur, today)
        r = staged_run(cur, today)
        assert r['original']['financial_source'] is None, 'P19R_STAGED_RUN_HAS_NO_FINANCE'
        key, done, _ = published(cur, r, finance='INCLUDED')
        d, _ = document(cur, done['publication_id'])
        a = actuals(cur, key)
        fin = a['finance']
        assert d['finance'] == 'INCLUDED' and d['financial_source_hash'] == fin['source_hash'] and fin['contract_version'] == 'cp7.native-analysis-finance.v1'
        read_at = datetime.fromisoformat(d['actuals_read_at'])
        assert fin['dates']['as_of'] == d['report_date'] == (read_at + timedelta(hours=7)).date().isoformat(), (fin['dates'], d['report_date'])
        assert (fin['dates']['from'], fin['dates']['to']) == (r['query']['from_date'], r['query']['through_date']), fin['dates']
        auth.actor(cur)
        native = cur.execute('select public.erp_cp7_get_finance_report_v1(%s)', (json.dumps(fin['dates']),)).fetchone()[0]
        b.api.admin(cur)
        for part in ('performance', 'financial_position', 'basis'):
            assert fin['report']['snapshot'][part] == native['snapshot'][part], part
        assert cur.execute('select cp7_analysis_native.financial_fingerprint(%s::jsonb,%s)', (json.dumps(native), fin['book_signature'])).fetchone()[0] == fin['source_hash']
        position, performance = native['snapshot']['financial_position'], native['snapshot']['performance']
        for label, value in (('Saldo kas tercatat', position['cash']), ('Utang pemasok final tercatat', position['supplier_final_ap']),
                             ('HPP penjualan tercatat', performance['cogs_gl'])):
            assert label + ': ' + value + ' IDR;' in d['summary'], (label, value)
        assert 'Angka keuangan dan HPP dari laporan Native ERP untuk tanggal laporan ' + d['report_date'] + ', dibaca ' + wib(read_at) in d['summary']
        assert 'Keuangan dan HPP tidak dimasukkan' not in d['summary'] and 'FINANCIAL_DOMAIN_NOT_CAPTURED' not in d['summary']
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', finance_read_from_accepted_owner_report_at_report_date=True, same_fingerprint_as_public_report=True,
                    staged_snapshot_itself_without_finance=True, report_date=d['report_date'], cash=position['cash'], cogs=performance['cogs_gl'])

    def finance_access():
        f, _ = load.real_workload(cur, today)
        staff, staff_role = auth.custom_actor(cur)
        r = staged_run(cur, today, staff)
        refused(cur, lambda: publish(cur, payload(r, finance='INCLUDED'), subject=staff), 'CP7_REPORT_V2_FINANCE_ACCESS', '42501')
        _, own, _ = published(cur, r, staff)
        admin, admin_role = finance_cases.admin_actor(cur, analysis)
        ra = staged_run(cur, today, admin)
        _, fin, _ = published(cur, ra, admin, finance='INCLUDED')
        _, ops, _ = published(cur, ra, admin)
        listed = lambda subject: {x['id'] for x in index(cur, subject=subject)['rows']}
        assert listed(admin) == {fin['publication_id'], ops['publication_id']} and listed(staff) == {own['publication_id']}
        kept = read(cur, fin['publication_id'], admin)['report_hash']
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'", (admin_role,))
        refused(cur, lambda: read(cur, fin['publication_id'], admin), 'CP7_REPORT_UNAVAILABLE', '42501')
        assert listed(admin) == {ops['publication_id']} and index(cur, subject=admin)['total'] == '1'
        refused(cur, lambda: publish(cur, payload(ra, finance='INCLUDED'), subject=admin), 'CP7_REPORT_V2_FINANCE_ACCESS', '42501')
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.reports.view')", (admin_role,))
        assert read(cur, fin['publication_id'], admin)['report_hash'] == kept, 'P19R_RESTORED_ACCESS_CHANGED_THE_REPORT'
        # A finance job whose actor's access changes between units fails without a publication.
        key = uuid.uuid4()
        publish(cur, payload(ra, finance='INCLUDED'), key, admin)
        step(cur, key, admin)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'", (admin_role,))
        failed = step(cur, key, admin)
        assert failed['state'] == 'FAILED' and failed['failure']['code'] == 'CP7_REPORT_ACCESS_CHANGED' and failed['publication_id'] is None, failed
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.reports.view')", (admin_role,))
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', ops_actor_finance_refused=True, ops_report_published=True, finance_hidden_after_permission_loss=True,
                    restored_permission_same_report=True, access_change_mid_job_fails_without_publication=True)

    def revision_series():
        f, _ = load.real_workload(cur, today)
        r1 = staged_run(cur, today)
        _, one, _ = published(cur, r1)
        d1 = read(cur, one['publication_id'])
        staged.location(cur, 'a newer snapshot for the revision')
        r2 = staged_run(cur, today)
        assert r2['run'] != r1['run']
        rev = dict(series_id=d1['series_id'], expected_revision='1', title='P19 report v2 briefing (newer snapshot)')
        _, two, _ = published(cur, r2, **rev)
        d2 = read(cur, two['publication_id'])
        assert (d2['series_id'], d2['revision'], d2['run_id'], d2['is_latest']) == (d1['series_id'], '2', r2['run'], True), d2
        assert read(cur, d1['id'])['is_latest'] is False
        refused(cur, lambda: publish(cur, payload(r2, **rev)), 'CP7_REPORT_REVISION_CHANGED', '40001')
        refused(cur, lambda: publish(cur, payload(r2, **dict(rev, expected_revision='2', kind='PERIOD'))), 'CP7_REPORT_SERIES_SCOPE_CHANGED')
        refused(cur, lambda: publish(cur, payload(r2, series_id=str(uuid.uuid4()), expected_revision='1')), 'CP7_REPORT_V2_SERIES_UNAVAILABLE', '42501')
        other_q = dict(staged.query(today), from_date=(datetime.fromisoformat(staged.query(today)['from_date']) - timedelta(days=1)).date().isoformat())
        r3 = staged_run(cur, today, q=other_q)
        refused(cur, lambda: publish(cur, payload(r3, series_id=d1['series_id'], expected_revision='2')), 'CP7_REPORT_SERIES_SCOPE_CHANGED')
        page = index(cur, limit=1)
        assert page['rows'][0]['id'] == two['publication_id'] and page['next_before_id'] == two['publication_id'] and page['total'] == '2', page
        rest = index(cur, before=page['next_before_id'], limit=1)
        assert [x['id'] for x in rest['rows']] == [one['publication_id']] and rest['next_before_id'] is None, rest
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', revision_on_newer_snapshot=True, stale_expected_revision_40001=True, kind_and_period_kept_per_series=True,
                    unknown_series_refused=True, index_pages=True)

    def request_one_uuid():
        f, _ = load.real_workload(cur, today)
        r = staged_run(cur, today)
        p, key = payload(r), uuid.uuid4()
        first = publish(cur, p, key)
        assert publish(cur, p, key, lookup=True) == first, 'P19R_LOOKUP_OF_A_RUNNING_JOB'
        refused(cur, lambda: publish(cur, dict(p, title='changed'), key), 'CP7_REPORT_REQUEST_CHANGED')
        closed_key = uuid.uuid4()
        closed = publish(cur, p, closed_key, lookup=True)
        assert closed['state'] == 'CLOSED_UNCOMMITTED' and closed['unit_count'] == 0, closed
        assert publish(cur, p, closed_key) == closed and step(cur, closed_key) == closed, 'P19R_CLOSED_UUID_REOPENED'
        refused(cur, lambda: publish(cur, dict(p, title='changed'), closed_key), 'CP7_REPORT_REQUEST_CHANGED')
        assert jobs_and_publications(cur) == (2, 0)
        b.api.admin(cur)
        assert cur.execute("select count(*)from cp7_analysis_stage.report_reads r join cp7_analysis_stage.report_jobs j on j.id=r.job_id where j.request_id=%s",
                           (closed_key,)).fetchone()[0] == 0
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', same_uuid_same_job=True, changed_payload_refused=True, lookup_closes_unknown_uuid_for_good=True)

    def authority():
        f, _ = load.real_workload(cur, today)
        r = staged_run(cur, today)
        key, done, _ = published(cur, r)
        d = read(cur, done['publication_id'])
        other, other_role = auth.custom_actor(cur)
        refused(cur, lambda: step(cur, key, other), 'CP7_REPORT_V2_JOB_UNAVAILABLE', '42501')
        refused(cur, lambda: read(cur, done['publication_id'], other), 'CP7_REPORT_UNAVAILABLE', '42501')
        refused(cur, lambda: publish(cur, payload(r), subject=other), 'CP7_REPORT_V2_SNAPSHOT_UNAVAILABLE', '42501')
        mine = staged_run(cur, today, other)
        _, own, _ = published(cur, mine, other)
        od = read(cur, own['publication_id'], other)
        refused(cur, lambda: section(cur, done['publication_id'], 0, od['access_epoch'], other), 'CP7_REPORT_UNAVAILABLE', '42501')
        assert {x['id'] for x in index(cur, subject=other)['rows']} == {own['publication_id']}
        assert own['publication_id'] not in {x['id'] for x in index(cur)['rows']}
        b.api.admin(cur)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')", (other_role,))
        refused(cur, lambda: section(cur, own['publication_id'], 0, od['access_epoch'], other), 'CP7_REPORT_ACCESS_CHANGED', '42501')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'", (other_role,))
        for op in (lambda: publish(cur, payload(mine), subject=other), lambda: publish(cur, payload(mine), subject=other, lookup=True),
                   lambda: step(cur, uuid.uuid4(), other), lambda: read(cur, own['publication_id'], other),
                   lambda: section(cur, own['publication_id'], 0, od['access_epoch'], other), lambda: index(cur, subject=other)):
            refused(cur, op, 'CP7_ACCESS_DENIED', '42501')
        b.api.admin(cur)
        for who in ('anon', 'authenticated', 'service_role'):
            for table in TABLES:
                assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')", (who, 'cp7_analysis_stage.' + table)).fetchone()[0], (who, table)
            for sig in SIGNATURES:
                assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0] == (who == 'authenticated'), (who, sig)
        for table in TABLES:
            assert cur.execute('select relrowsecurity from pg_class where oid=%s::regclass', ('cp7_analysis_stage.' + table,)).fetchone()[0], table
        for sql in ("update cp7_analysis_stage.report_publications set summary='x'", 'delete from cp7_analysis_stage.report_sections',
                    "update cp7_analysis_stage.report_reads set body='{}'", "update cp7_analysis_stage.report_jobs set payload='{}'",
                    'delete from cp7_analysis_stage.report_jobs'):
            refused(cur, lambda: cur.execute(sql), 'CP7_RUN_IMMUTABLE')
        assert read(cur, done['publication_id'])['report_hash'] == d['report_hash']
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', foreign_job_report_section_run_refused=True, index_actor_bound=True, access_epoch_change_refused=True,
                    current_permission_loss_refuses_all_six=True, no_direct_API_path=True, rows_immutable=True)

    def fields_identity():
        f, _ = load.real_workload(cur, today)
        r = staged_run(cur, today)
        p = payload(r)
        before = jobs_and_publications(cur)
        refused(cur, lambda: publish(cur, dict(p, extra=True)), 'CP7_WIP_FIELDS', '22023')
        refused(cur, lambda: publish(cur, {k: v for k, v in p.items() if k != 'finance'}), 'CP7_WIP_FIELDS', '22023')
        for bad in (dict(explicit_review=False), dict(finance='MAYBE'), dict(kind='WEEKLY'), dict(title=' '), dict(reason=''), dict(title='x' * 201),
                    dict(run_id='not-a-uuid'), dict(identity_hash='A' * 64)):
            refused(cur, lambda: publish(cur, dict(p, **bad)), 'CP7_REPORT_REVIEW')
        for bad in (dict(expected_revision='1'), dict(series_id=str(uuid.uuid4())), dict(series_id=str(uuid.uuid4()), expected_revision='0'),
                    dict(series_id=str(uuid.uuid4()), expected_revision=1)):
            refused(cur, lambda: publish(cur, dict(p, **bad)), 'CP7_REPORT_REVISION')
        refused(cur, lambda: publish(cur, dict(p, identity_hash='e' * 64)), 'CP7_REPORT_V2_IDENTITY_CHANGED')
        refused(cur, lambda: publish(cur, dict(p, run_id=str(uuid.uuid4()))), 'CP7_REPORT_V2_SNAPSHOT_UNAVAILABLE', '42501')
        running = uuid.uuid4()
        staged.checked(staged.request(cur, today, running), running, 'RUNNING')
        unfinished = staged.job_row(cur, running)['run_id']
        refused(cur, lambda: publish(cur, dict(p, run_id=unfinished)), 'CP7_REPORT_V2_SNAPSHOT_UNAVAILABLE', '42501')
        refused(cur, lambda: limited(cur, 'erp_cp7_publish_report_v2', (json.dumps(p), None)), 'CP7_REPORT_REVIEW')
        assert jobs_and_publications(cur) == before
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', exact_fields=True, review_title_reason_kind_finance=True, revision_format=True, identity_bound=True,
                    unfinished_or_unknown_run_refused=True, nothing_written=True)

    def v1_apart():
        f, _ = load.real_workload(cur, today)
        r = staged_run(cur, today)
        _, done, _ = published(cur, r)
        e = analysis.capture(cur, today)
        v1 = dict(run_id=e['run_id'], source_hash=e['analysis']['snapshot']['source_hash'], semantic_hash=e['analysis']['semantic_hash'], kind='DAILY',
                  series_id=None, expected_revision=None, title='P19 report v1 control', reason='P19 report v2 control: v1 unchanged', explicit_review=True)
        key = uuid.uuid4()
        one = limited(cur, 'erp_cp7_publish_report_v1', (json.dumps(v1), key))
        assert one['status'] == 'COMMITTED', one['status']
        staged_v1 = dict(v1, run_id=r['run'])
        refused(cur, lambda: limited(cur, 'erp_cp7_publish_report_v1', (json.dumps(staged_v1), uuid.uuid4())), 'CP7_ANALYSIS_RUN_UNAVAILABLE')
        refused(cur, lambda: publish(cur, payload(r), key), 'CP7_REPORT_REQUEST_CHANGED')
        v1_ids = {x['id'] for x in limited(cur, 'erp_cp7_list_reports_v1', (json.dumps(dict(before_id=None, limit=50)),))['rows']}
        v2_ids = {x['id'] for x in index(cur)['rows']}
        assert v1_ids == {one['document']['id']} and v2_ids == {done['publication_id']}, (v1_ids, v2_ids)
        refused(cur, lambda: limited(cur, 'erp_cp7_read_report_v1', (done['publication_id'],)), 'CP7_REPORT_UNAVAILABLE')
        refused(cur, lambda: read(cur, one['document']['id']), 'CP7_REPORT_UNAVAILABLE', '42501')
        refused(cur, lambda: publish(cur, payload(r, series_id=one['document']['series_id'], expected_revision='1')), 'CP7_REPORT_V2_SERIES_UNAVAILABLE', '42501')
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', v1_publish_unchanged=True, v1_refuses_staged_run=True, one_uuid_across_versions=True, indexes_apart=True,
                    readers_apart=True, v1_series_not_continued_by_v2=True)

    return list(zip(IDS['native'], (publish_steps_seal, actual_stock, freshness_states, finance_owner_report, finance_access, revision_series,
                                     request_one_uuid, authority, fields_identity, v1_apart)))


def races(tools, today):
    def prepared(subject=None, **kw):
        with tools.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            role = None
            if subject == 'custom':
                subject, role = auth.custom_actor(cur)
            r = staged_run(cur, today, subject)
            key = uuid.uuid4()
            first = publish(cur, payload(r, **kw), key, subject)
            conn.commit()
        return dict(key=key, f=f, r=r, subject=subject, role=role, first=first)

    def waiting(workers, kind='advisory'):
        with tools.connect(autocommit=True) as inspect, inspect.cursor() as c:
            deadline, seen = time.monotonic() + 10, []
            while time.monotonic() < deadline:
                seen = c.execute('select pid from pg_locks where pid=any(%s)and locktype=%s and not granted', (workers, kind)).fetchall()
                if len(seen) == len(workers):
                    break
                time.sleep(.05)
        assert len(seen) == len(workers), ('P19R_WAIT_NOT_OBSERVED', kind, seen)
        return [x[0] for x in seen]

    def run_to(key, units, subject=None):
        with tools.connect() as conn, conn.cursor() as cur:
            s = publish_status(cur, key, subject)
            while s['state'] == 'RUNNING' and s['units_done'] < units:
                s = step(cur, key, subject)
            conn.commit()
        return s

    def two_steps():
        x = prepared()
        with tools.connect() as holder, holder.cursor() as h:
            # The first worker holds the job row exactly as a running unit does.
            h.execute('select 1 from cp7_analysis_stage.report_jobs where request_id=%s for update', (x['key'],))

            def once():
                with tools.connect() as conn, conn.cursor() as cur:
                    result = limited(cur, 'erp_cp7_step_report_v2', (x['key'],))
                    conn.commit()
                    return result
            with ThreadPoolExecutor(max_workers=1) as pool:
                skipped = pool.submit(once).result(30)
            holder.rollback()
        assert skipped['worker_active'] is True and skipped['units_done'] == 0, skipped
        gate = threading.Barrier(2)

        def racing():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                result = limited(cur, 'erp_cp7_step_report_v2', (x['key'],))
                conn.commit()
                return result
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [j.result(60) for j in [pool.submit(racing), pool.submit(racing)]]
        ran = [y for y in results if not y.get('worker_active')]
        with tools.connect() as conn, conn.cursor() as cur:
            after = publish_status(cur, x['key'])
            assert after['units_done'] == len(ran) and len(ran) in (1, 2), (results, after)
            done, _ = drive(cur, x['key'])
            conn.commit()
            assert done['state'] == 'DONE'
            b.api.admin(cur)
            assert cur.execute('select count(*)from cp7_analysis_stage.report_reads r join cp7_analysis_stage.report_jobs j on j.id=r.job_id '
                               "where j.request_id=%s and r.kind='ACTUALS'", (x['key'],)).fetchone()[0] == 1
            bridge.literal(cur, x['f'], '175.00')
        return dict(status='PASS', locked_job_step_runs_nothing_worker_active=True, concurrent_steps_never_run_one_unit_twice=True, results=results)

    def two_revisions():
        x = prepared()
        with tools.connect() as conn, conn.cursor() as cur:
            done, _ = drive(cur, x['key'])
            series = done['series_id']
            conn.commit()
        keys = []
        with tools.connect() as conn, conn.cursor() as cur:
            for title in ('P19 report v2 revision A', 'P19 report v2 revision B'):
                k = uuid.uuid4()
                publish(cur, payload(x['r'], series_id=series, expected_revision='1', title=title), k)
                keys.append(k)
            conn.commit()
        last = [run_to(k, x['first']['unit_count'] - 1) for k in keys]
        assert all(s['stage'] == 'SUMMARY' for s in last), last
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            actor = cur.execute('select actor::text from cp7_analysis_stage.report_jobs where request_id=%s', (keys[0],)).fetchone()[0]
            conn.commit()
        pids, gate = Queue(), threading.Barrier(2)

        def seal(k):
            with tools.connect() as conn, conn.cursor() as cur:
                pids.put(cur.execute('select pg_backend_pid()').fetchone()[0])
                gate.wait(timeout=8)
                result = step(cur, k)
                conn.commit()
                return result
        with tools.connect() as holder, holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:REPORT_SERIES_V2:'||%s||':'||%s,0))", (actor, series))
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(seal, k) for k in keys]
                workers = [pids.get(timeout=8), pids.get(timeout=8)]
                try:
                    observed = waiting(workers)
                finally:
                    holder.commit()
                results = [j.result(60) for j in jobs]
        won = [s for s in results if s['state'] == 'DONE']
        lost = [s for s in results if s['state'] == 'FAILED']
        assert len(won) == len(lost) == 1 and lost[0]['failure'] == dict(unit=lost[0]['unit_count'] - 1, sqlstate='40001', code='CP7_REPORT_REVISION_CHANGED'), results
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            revisions = [r[0] for r in cur.execute('select revision from cp7_analysis_stage.report_publications where series_id=%s order by revision', (series,)).fetchall()]
            assert revisions == [1, 2], revisions
            bridge.literal(cur, x['f'], '175.00')
        return dict(status='PASS', both_seals_waited_on_the_series_lock=observed, one_revision_sealed_other_refused_40001=True, revisions=revisions)

    def stock_during_job():
        x = prepared()
        root = first_root(x['r'])
        after_actuals = run_to(x['key'], 1)
        assert after_actuals['stage'] == 'SECTION' or after_actuals['stage'] == 'FRESHNESS', after_actuals
        with tools.connect() as conn, conn.cursor() as cur:
            read_at = datetime.fromisoformat(actuals(cur, x['key'])['read_at'])
            held = stock(cur, root, read_at)
            found_fg(cur, root, 4)
            conn.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            done, _ = drive(cur, x['key'])
            d, bodies = document(cur, done['publication_id'])
            now = stock(cur, root, datetime.fromisoformat(d['published_at']))
            lines, _ = target_lines(x['r'], read_at, cur)
            text = '\n'.join(bodies)
            assert all(line in text for _, line in lines), 'P19R_ACTUAL_NOT_AT_ITS_READ_TIME'
            assert now[0] == held[0] + 4, (held, now)
            assert d['freshness']['state'] == 'CHANGES_RECORDED' and 'Stok barang jadi: ' in d['summary'], d['freshness']
            # A later report reads the stock found during the first one.
            key2, done2, _ = published(cur, x['r'])
            later = datetime.fromisoformat(actuals(cur, key2)['read_at'])
            lines2, _ = target_lines(x['r'], later, cur)
            assert all(line in '\n'.join(document(cur, done2['publication_id'])[1]) for _, line in lines2)
            conn.commit()
            bridge.literal(cur, x['f'], '175.00')
        return dict(status='PASS', stock_committed_mid_job_not_in_actuals_read_before_it=True, freshness_counts_it=True,
                    later_report_reads_it=True, held=held, after=now)

    def access_changed():
        x = prepared('custom')
        with tools.connect() as conn, conn.cursor() as cur:
            first = step(cur, x['key'], x['subject'])
            conn.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')", (x['role'],))
            conn.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            failed = step(cur, x['key'], x['subject'])
            conn.commit()
        assert failed['state'] == 'FAILED' and failed['failure']['code'] == 'CP7_REPORT_ACCESS_CHANGED' and failed['units_done'] == first['units_done'], failed
        with tools.connect() as conn, conn.cursor() as cur:
            assert publish_status(cur, x['key'], x['subject']) == failed
            b.api.admin(cur)
            assert cur.execute('select count(*)from cp7_analysis_stage.report_publications p join cp7_analysis_stage.report_jobs j on j.id=p.job_id '
                               'where j.request_id=%s', (x['key'],)).fetchone()[0] == 0
            bridge.literal(cur, x['f'], '175.00')
        return dict(status='PASS', access_change_between_units_fails_job=True, no_publication=True, failure=failed['failure'])

    def same_uuid():
        with tools.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            r = staged_run(cur, today)
            conn.commit()
        key, gate = uuid.uuid4(), threading.Barrier(2)

        def send():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                result = publish(cur, payload(r), key)
                conn.commit()
                return result
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [j.result(60) for j in [pool.submit(send), pool.submit(send)]]
        assert results[0] == results[1] and results[0]['state'] == 'RUNNING', results
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert cur.execute('select count(*)from cp7_analysis_stage.report_jobs where request_id=%s', (key,)).fetchone()[0] == 1
            done, _ = drive(cur, key)
            conn.commit()
            assert done['state'] == 'DONE'
            bridge.literal(cur, f, '175.00')
        return dict(status='PASS', one_uuid_two_sessions_one_job=True, same_series=results[0]['series_id'])

    def limit():
        x = prepared()
        stops = []
        with tools.connect() as holder, holder.cursor() as h:
            # The ACTUALS unit's insert waits on a real lock until the ordinary
            # statement limit stops it inside the unit handler.
            h.execute('lock table cp7_analysis_stage.report_reads in exclusive mode')

            def once():
                with tools.connect() as conn, conn.cursor() as cur:
                    result = step(cur, x['key'], timeout='3s')
                    conn.commit()
                    return result
            with ThreadPoolExecutor(max_workers=1) as pool:
                for _ in range(2):
                    stops.append(pool.submit(once).result(30))
            holder.rollback()
        assert all(s['state'] == 'RUNNING' for s in stops) and [s['unit_attempts'] for s in stops] == [1, 2], stops
        assert all(s['units_done'] == 0 for s in stops), 'P19R_STOP_SAVED_A_PARTIAL_UNIT'
        with tools.connect() as conn, conn.cursor() as cur:
            done, calls = drive(cur, x['key'])
            conn.commit()
            assert done['state'] == 'DONE' and done['unit_attempts'] == 0
            bridge.literal(cur, x['f'], '175.00')
        return dict(status='PASS', statement_limit_stop_recorded_as_attempt=True, job_continues_after_lock_release=True, stops=stops, units_after=len(calls))

    return list(zip(IDS['races'], (two_steps, two_revisions, stock_during_job, access_changed, same_uuid, limit)))


def http_cases(http, today):
    state = {}

    def ok(user, name, args):
        r = user.rpc(name, args)
        assert r['status'] == 200, (name, r)
        return r['body']

    def flow():
        owner = http.login('OWNER', 'p19r-owner')
        other = http.login('OWNER', 'p19r-other')
        with http.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            r = staged_run(cur, today, owner.auth_user_id)
            conn.commit()
        key = str(uuid.uuid4())
        args = dict(p_payload=payload(r), p_request=key)
        job = checked(ok(owner, 'erp_cp7_publish_report_v2', args))
        calls = 0
        while job['state'] == 'RUNNING':
            assert calls < DRIVER_CALLS
            job = checked(ok(owner, 'erp_cp7_step_report_v2', dict(p_request=key)))
            calls += 1
        assert job['state'] == 'DONE' and checked(ok(owner, 'erp_cp7_get_report_request_v2', args)) == job
        pid = job['publication_id']
        d = ok(owner, 'erp_cp7_read_report_v2', dict(p_id=pid))
        bodies = [ok(owner, 'erp_cp7_read_report_section_v2', dict(p_id=pid, p_index=s['index'], p_access=d['access_epoch'])) for s in d['sections']]
        assert all(staged.sha(e['body']) == e['sha256'] for e in bodies) and staged.sha(d['summary']) == d['summary_sha256']
        assert d['report_hash'] == staged.sha('\n'.join([d['summary_sha256']] + [e['sha256'] for e in bodies]))
        listed = ok(owner, 'erp_cp7_list_reports_v2', dict(p_query=dict(before_id=None, limit=10)))
        assert [x['id'] for x in listed['rows']] == [pid], listed
        foreign = [other.rpc('erp_cp7_step_report_v2', dict(p_request=key))['status'], other.rpc('erp_cp7_read_report_v2', dict(p_id=pid))['status'],
                   other.rpc('erp_cp7_read_report_section_v2', dict(p_id=pid, p_index=0, p_access=d['access_epoch']))['status'],
                   other.rpc('erp_cp7_publish_report_v2', dict(p_payload=payload(r), p_request=str(uuid.uuid4())))['status']]
        assert foreign == [403] * 4, foreign
        assert ok(other, 'erp_cp7_list_reports_v2', dict(p_query=dict(before_id=None, limit=10)))['rows'] == []
        anonymous = [http.anon_rpc(name, a)['status'] for name, a in (
            ('erp_cp7_publish_report_v2', args), ('erp_cp7_get_report_request_v2', args), ('erp_cp7_step_report_v2', dict(p_request=key)),
            ('erp_cp7_read_report_v2', dict(p_id=pid)), ('erp_cp7_read_report_section_v2', dict(p_id=pid, p_index=0, p_access=d['access_epoch'])),
            ('erp_cp7_list_reports_v2', dict(p_query=dict(before_id=None, limit=10))))]
        assert all(code in (401, 403) for code in anonymous), anonymous
        with http.connect() as conn, conn.cursor() as cur:
            assert jobs_and_publications(cur) == (1, 1)
            bridge.literal(cur, f, '175.00')
        state.update(owner=owner, key=key, pid=pid, epoch=d['access_epoch'], args=args)
        return dict(status='PASS', real_Auth_publish_steps_read_sections_list=True, actual_HTTP_steps=calls, foreign_403=foreign,
                    anonymous_refused=anonymous)

    def revoked():
        assert state, 'P19R_REQUIRED_PRIOR_HTTP_CASE'
        owner = state['owner']
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner.auth_user_id,))
            conn.commit()
        codes = [owner.rpc(name, a)['status'] for name, a in (
            ('erp_cp7_publish_report_v2', dict(state['args'], p_request=str(uuid.uuid4()))), ('erp_cp7_get_report_request_v2', state['args']),
            ('erp_cp7_step_report_v2', dict(p_request=state['key'])), ('erp_cp7_read_report_v2', dict(p_id=state['pid'])),
            ('erp_cp7_read_report_section_v2', dict(p_id=state['pid'], p_index=0, p_access=state['epoch'])),
            ('erp_cp7_list_reports_v2', dict(p_query=dict(before_id=None, limit=10))))]
        assert codes == [403] * 6, codes
        with http.connect() as conn, conn.cursor() as cur:
            assert jobs_and_publications(cur) == (1, 1)
        return dict(status='PASS', deactivated_user_all_six_403=True, no_new_effect=True)

    return list(zip(IDS['http'], (flow, revoked)))
