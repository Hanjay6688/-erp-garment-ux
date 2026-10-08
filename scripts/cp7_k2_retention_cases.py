"""K2: staged analysis results kept 7 days after they finished, then expired (owner decision 8 Oct 2026).

"hasil analisis sementara disimpan 7 hari setelah selesai atau dibatalkan. Jangan hapus job yang belum
selesai, dokumen transaksi, atau bukti yang diperlukan audit. Hasil kedaluwarsa harus diberi keterangan
jelas." A finished job (DONE, or FAILED when it stopped) is kept 7 days; then its status says EXPIRED with
the time and every reader of the run refuses it with CP7_ANALYSIS_RESULT_EXPIRED. The private purge (no
grants, no schedule yet: the server scheduler is CP7C) removes only what an expired finished job held as
temporary analysis: the intermediates, and its pages when no document was made from the run. Documents
(plan drafts, reports, reminder sets) stay readable. Real staged runs, real sessions and real Auth/PostgREST
calls on the closed harness. The only SYNTHETIC step is labelled: a job row's finish time moved back
(administrative) to stand for eight days passing inside one test.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import threading
import uuid

import psycopg

import cp7_p19_staged_cases as staged
import cp7_p19_report_v2_cases as report
import cp7_p19_plan_v2_cases as planv2

IDS = dict(
    native=['K2_KEPT_SEVEN_DAYS_LABELLED', 'K2_EXPIRED_REFUSED_EVERYWHERE', 'K2_RUNNING_NEVER_EXPIRES', 'K2_PURGE_ONLY_EXPIRED_TEMPORARY',
            'K2_PURGE_KEEPS_DOCUMENT_RUNS', 'K2_PURGE_PRIVATE_ONCE'],
    races=['K2_RACE_TWO_PURGES_ONE_LOG'],
    http=['K2_HTTP_EXPIRED_REFUSED'],
    browser=['K2_BROWSER_DESKTOP_RETENTION', 'K2_BROWSER_MOBILE_RETENTION'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.k2.retention.v1'
FUNCTIONS = ('erp_cp7_get_staged_analysis_v1', 'erp_cp7_read_staged_analysis_pages_v1', 'erp_cp7_read_staged_analysis_page_v1',
             'erp_cp7_check_staged_analysis_source_v1', 'erp_cp7_staged_snapshot_freshness_v1', 'erp_cp7_check_staged_snapshot_v1',
             'erp_cp7_get_plan_options_v2', 'erp_cp7_publish_report_v2', 'erp_cp7_get_staged_ai_brief_v1', 'erp_cp7_step_reminder_conditions_v2')
EXPIRED = 'CP7_ANALYSIS_RESULT_EXPIRED'
TEMPORARY = ('outputs', 'target_rows', 'pair_rows', 'pair_lists', 'fragments')
KEPT = ('units', 'headers', 'page_sets', 'capture_marks', 'plan_targets', 'plan_scope', 'plan_groups')
auth, b = staged.auth, staged.b
refused, refusal = planv2.refused, planv2.refusal


def age(cur, run, delta):
    """SYNTHETIC (labelled): the finished job's finish time moved back by `delta` (administrative), standing for
    that much time passing. Only updated_at changes; the job row's identity columns stay immutable."""
    b.api.admin(cur)
    cur.execute('update cp7_analysis_stage.jobs set updated_at=updated_at-%s where run_id=%s', (delta, run))


def job(cur, run):
    b.api.admin(cur)
    return cur.execute('select id::text,request_id::text,state,updated_at from cp7_analysis_stage.jobs where run_id=%s', (run,)).fetchone()


def status(cur, key, subject=None):
    return staged.limited(cur, 'erp_cp7_get_staged_analysis_v1', (key,), subject)


def counts(cur, j, run):
    b.api.admin(cur)
    out = {t: cur.execute(f'select count(*)from cp7_analysis_stage.{t} where job_id=%s', (j,)).fetchone()[0] for t in TEMPORARY + ('units', 'capture_marks', 'plan_targets', 'plan_scope', 'plan_groups')}
    for t in ('headers', 'pages', 'page_sets'):
        out[t] = cur.execute(f'select count(*)from cp7_analysis_stage.{t} where run_id=%s', (run,)).fetchone()[0]
    return out


def purge(cur, limit=100):
    b.api.admin(cur)
    return cur.execute('select cp7_analysis_stage.purge_expired(%s)', (limit,)).fetchone()[0]


def expired_detail(detail):
    assert isinstance(detail, dict) and detail['days'] == 7 and detail['kept_until'], detail
    return detail


def cases(cur, today):
    def kept():
        r = report.staged_run(cur, today)
        j = job(cur, r['run'])
        s = status(cur, r['key'])
        k = s['retention']
        finished = j[3]
        assert (k['days'], k['state']) == (7, 'KEPT') and k['kept_until'] is not None, s
        assert cur.execute('select %s::timestamptz=%s::timestamptz+interval\'7 days\'', (k['kept_until'], finished)).fetchone()[0], (k, finished)
        ps = staged.limited(cur, 'erp_cp7_read_staged_analysis_pages_v1', (r['run'],))
        assert ps['identity_hash'] == r['identity']
        # One minute before day 7 is still kept.
        age(cur, r['run'], timedelta(days=7) - timedelta(minutes=1))
        assert status(cur, r['key'])['retention']['state'] == 'KEPT'
        assert staged.limited(cur, 'erp_cp7_read_staged_analysis_pages_v1', (r['run'],))['identity_hash'] == r['identity']
        return dict(status='PASS', kept_until_is_finish_plus_7_days=True, readable_while_kept=True, one_minute_before_still_kept=True)

    def everywhere():
        x = planv2.single(cur, today)
        run, key = x['run'], x['key']
        ps = staged.limited(cur, 'erp_cp7_read_staged_analysis_pages_v1', (run,))
        epoch, identity = ps['access_epoch'], ps['identity_hash']
        age(cur, run, timedelta(days=7, minutes=1))
        s = status(cur, key)
        assert s['state'] == 'DONE' and s['retention']['state'] == 'EXPIRED', s
        calls = [
            ('pages', lambda: staged.limited(cur, 'erp_cp7_read_staged_analysis_pages_v1', (run,))),
            ('page', lambda: staged.limited(cur, 'erp_cp7_read_staged_analysis_page_v1', (run, 0, epoch))),
            ('source', lambda: staged.limited(cur, 'erp_cp7_check_staged_analysis_source_v1', (run,))),
            ('freshness', lambda: staged.limited(cur, 'erp_cp7_staged_snapshot_freshness_v1', (run,))),
            ('full_check', lambda: staged.limited(cur, 'erp_cp7_check_staged_snapshot_v1', (run,))),
            ('plan_options', lambda: planv2.options(cur, x['query'])),
            ('plan_save', lambda: planv2.save(cur, x['payload'])),
            ('report', lambda: report.publish(cur, report.payload(dict(run=run, identity=identity)))),
            ('ai', lambda: staged.limited(cur, 'erp_cp7_get_staged_ai_brief_v1', (run, json.dumps([])))),
            ('reminders', lambda: staged.limited(cur, 'erp_cp7_step_reminder_conditions_v2', (run,))),
        ]
        seen = {}
        for name, op in calls:
            state, message, detail = refusal(cur, op)
            assert message == EXPIRED, (name, state, message, detail)
            expired_detail(detail)
            seen[name] = message
        return dict(status='PASS', status_expired_with_time=True, refused=sorted(seen), code=EXPIRED)

    def running():
        key = uuid.uuid4()
        first = staged.request(cur, today, key)
        assert first['state'] == 'RUNNING' and first['retention'] == dict(days=7, kept_until=None, state='NOT_FINISHED'), first
        b.api.admin(cur)
        cur.execute("update cp7_analysis_stage.jobs set updated_at=updated_at-interval'30 days' where request_id=%s", (key,))
        assert status(cur, key)['retention']['state'] == 'NOT_FINISHED'
        j = cur.execute('select id from cp7_analysis_stage.jobs where request_id=%s', (key,)).fetchone()[0]
        before = cur.execute('select count(*)from cp7_analysis_stage.units where job_id=%s', (j,)).fetchone()[0]
        out = purge(cur)
        assert all(p['job_id'] != str(j) for p in out['purged']), out
        assert cur.execute('select count(*)from cp7_analysis_stage.units where job_id=%s', (j,)).fetchone()[0] == before
        assert cur.execute('select count(*)from cp7_analysis_stage.retention_log where job_id=%s', (j,)).fetchone()[0] == 0
        return dict(status='PASS', running_job_never_expires=True, untouched_by_purge=True)

    def temporary():
        a = report.staged_run(cur, today)
        keep = report.staged_run(cur, today)
        ja, jk = job(cur, a['run'])[0], job(cur, keep['run'])[0]
        before_a, before_k = counts(cur, ja, a['run']), counts(cur, jk, keep['run'])
        hashes = [list(r) for r in cur.execute('select idx,utf8_bytes,sha256 from cp7_analysis_stage.pages where run_id=%s order by idx', (a['run'],)).fetchall()]
        assert before_a['pages'] >= 1 and before_a['headers'] == before_a['page_sets'] == 1
        age(cur, a['run'], timedelta(days=8))
        out = purge(cur)
        mine = [p for p in out['purged'] if p['job_id'] == ja]
        assert len(mine) == 1 and mine[0]['documents'] == {} and mine[0]['removed']['pages'] == before_a['pages'], out
        assert all(p['job_id'] != jk for p in out['purged']), out
        after_a, after_k = counts(cur, ja, a['run']), counts(cur, jk, keep['run'])
        assert all(after_a[t] == 0 for t in TEMPORARY) and after_a['pages'] == 0, after_a
        assert all(after_a[t] == before_a[t] for t in KEPT), (before_a, after_a)
        assert after_k == before_k, (before_k, after_k)
        log = cur.execute('select removed_pages,documents,kept_until=finished_at+interval\'7 days\' from cp7_analysis_stage.retention_log where job_id=%s', (ja,)).fetchone()
        assert [[p['index'], p['utf8_bytes'], p['sha256']] for p in log[0]] == hashes and log[1] == {} and log[2], log
        assert cur.execute('select count(*)from cp7_analysis_stage.jobs where id=%s', (ja,)).fetchone()[0] == 1
        return dict(status='PASS', expired_intermediates_and_pages_removed=True, job_header_index_units_kept=True,
                    page_hashes_kept_in_log=len(hashes), kept_run_untouched=True)

    def documents():
        x = planv2.single(cur, today)
        d = planv2.save(cur, x['payload'])
        j = job(cur, x['run'])[0]
        before = counts(cur, j, x['run'])
        age(cur, x['run'], timedelta(days=8))
        out = purge(cur)
        mine = [p for p in out['purged'] if p['job_id'] == j]
        assert len(mine) == 1 and mine[0]['documents'] == {'plan_v2_drafts': 1} and 'pages' not in mine[0]['removed'], out
        after = counts(cur, j, x['run'])
        assert after['pages'] == before['pages'] and all(after[t] == 0 for t in TEMPORARY), (before, after)
        r = planv2.read(cur, d['draft_id'])
        assert r['draft_id'] == d['draft_id'], r
        refused(cur, lambda: planv2.preview(cur, d['draft_id']), EXPIRED)
        return dict(status='PASS', document_run_pages_kept=True, draft_still_readable=True, draft_preview_refused_expired=True)

    def private_once():
        a = report.staged_run(cur, today)
        ja = job(cur, a['run'])[0]
        age(cur, a['run'], timedelta(days=8))
        first = purge(cur)
        assert any(p['job_id'] == ja for p in first['purged'])
        second = purge(cur)
        assert all(p['job_id'] != ja for p in second['purged']), second
        for sql in ('update cp7_analysis_stage.retention_log set removed=removed', 'delete from cp7_analysis_stage.retention_log'):
            refused(cur, lambda sql=sql: cur.execute(sql), 'CP7_RUN_IMMUTABLE')
        for who in ('anon', 'authenticated', 'service_role'):
            for sig in ('cp7_analysis_stage.purge_expired(integer)', 'cp7_analysis_stage.require_kept(uuid)', 'cp7_analysis_stage.retention(text,timestamp with time zone)'):
                assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')', (who, sig)).fetchone()[0], (who, sig)
            assert not cur.execute('select has_table_privilege(%s,\'cp7_analysis_stage.retention_log\',\'SELECT,INSERT,UPDATE,DELETE\')', (who,)).fetchone()[0]
        for bad in (0, 1001, None):
            refused(cur, lambda bad=bad: purge(cur, bad), 'CP7_ANALYSIS_RETENTION_LIMIT')
        return dict(status='PASS', purged_once=True, log_immutable=True, private_no_grants=True, limit_bounded=True)

    return list(zip(IDS['native'], (kept, everywhere, running, temporary, documents, private_once)))


def races(tools, today):
    def two_purges():
        with tools.connect() as conn, conn.cursor() as cur:
            runs = [report.staged_run(cur, today) for _ in range(2)]
            for r in runs:
                age(cur, r['run'], timedelta(days=8))
            jobs = [job(cur, r['run'])[0] for r in runs]
            conn.commit()
        gate = threading.Barrier(2)

        def send():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                out = purge(cur)
                conn.commit()
                return [p['job_id'] for p in out['purged']]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [f.result(120) for f in [pool.submit(send) for _ in range(2)]]
        mine = [j for r in results for j in r if j in jobs]
        assert sorted(mine) == sorted(jobs), results
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert cur.execute('select count(*)from cp7_analysis_stage.retention_log where job_id=any(%s::uuid[])', (jobs,)).fetchone()[0] == 2
        return dict(status='PASS', two_concurrent_purges_each_job_once=True)

    return list(zip(IDS['races'], (two_purges,)))


def http_cases(http, today):
    def expired():
        owner = http.login('OWNER', 'k2-owner')
        with http.connect() as conn, conn.cursor() as cur:
            r = report.staged_run(cur, today, owner.auth_user_id)
            age(cur, r['run'], timedelta(days=8))
            conn.commit()
        s = owner.rpc('erp_cp7_get_staged_analysis_v1', dict(p_request=str(r['key'])))
        assert s['status'] == 200 and s['body']['retention']['state'] == 'EXPIRED', s
        p = owner.rpc('erp_cp7_read_staged_analysis_pages_v1', dict(p_run=r['run']))
        assert p['status'] >= 400 and EXPIRED in json.dumps(p['body']), p
        return dict(status='PASS', status_expired_over_http=True, pages_refused=p['status'])

    return list(zip(IDS['http'], (expired,)))
