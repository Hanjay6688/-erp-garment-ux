"""K3b + CP7C: a finished analysis's temporary work removed on the server's schedule; the schedule and the
nightly backup built and tested, not installed (owner decision 9 Oct 2026 WIB).

Owner: "Hapus data kerja yang benar-benar sementara setelah analisis DONE dan seluruh hasil final tersimpan serta
terverifikasi." Conditions: (1) the final result, pages, hashes, analysis time and the source it came from stay
for the 7-day retention, documents and audit evidence are protected; (2) Business Report, plan, reminders, AI and
reopening a DONE result keep working after the cleanup; (3) the cleanup is safe to repeat, never touches a job
that is not finished, and a failed cleanup leaves the result available and is retried; (4) checks of numbers,
completeness, hashes and origin stay strict and reopening after the cleanup is tested; (6) the cleanup and purge
schedule and the nightly backup are built and tested; installing them for real waits for the audit and the
owner's installation permission.

The cleanup is cp7_ops.cleanup_tick (pg_cron every 5 minutes) -> cp7_analysis_stage.clean_pending ->
clean_done: verify the stored result (header and page hashes against their bodies, page count, identity hash,
plan index), then remove outputs/target_rows/pair_rows/pair_lists/fragments and write one immutable log row.
It never runs inside a user's request. Real staged runs, real sessions, a real pg_cron job on the disposable
race copy, real Auth/PostgREST and a real browser. SYNTHETIC steps are labelled where they are used.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import hashlib
import json
import os
import tempfile
import threading
import time
import uuid

import psycopg

import cp7_p19_staged_cases as staged
import cp7_p19_report_v2_cases as report
import cp7_p19_plan_v2_cases as planv2
import cp7_p19_ai_v2_cases as ai
import cp7_p19_reminder_v2_cases as rem
import cp7_schedule as schedule
import cp7_nightly_backup as nightly

IDS = dict(
    native=['K3C_CLEANED_ONLY_TEMPORARY', 'K3C_REOPEN_AFTER_CLEANUP', 'K3C_PLAN_V2_AFTER_CLEANUP', 'K3C_REPORT_V2_AFTER_CLEANUP',
            'K3C_AI_AND_REMINDERS_AFTER_CLEANUP', 'K3C_FAILED_CLEANUP_KEEPS_RESULT_RETRIED', 'K3C_ONLY_DONE_KEPT_RUNS',
            'K3C_DOCUMENTS_AND_RETENTION_AFTER_CLEANUP', 'K3C_SCHEDULE_DEFINED_PRIVATE'],
    races=['K3C_RACE_TWO_TICKS_ONE_LOG', 'K3C_RACE_BUSY_TABLE_RETRIED', 'K3C_RACE_PG_CRON_FIRES', 'K3C_RACE_NIGHTLY_BACKUP_VERIFIED',
           'K3C_RACE_CRON_TWO_DATABASES', 'K3C_RACE_BACKUP_RETRY_SAME_SECOND'],
    http=['K3C_HTTP_REOPEN_AFTER_CLEANUP', 'K3C_HTTP_TICK_NOT_REACHABLE'],
    browser=['K3C_BROWSER_DESKTOP_REOPEN_AFTER_CLEANUP', 'K3C_BROWSER_MOBILE_REOPEN_AFTER_CLEANUP'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.k3b.cleanup-and-schedule.v1'
FUNCTIONS = ('erp_cp7_get_staged_analysis_v1', 'erp_cp7_read_staged_analysis_pages_v1', 'erp_cp7_read_staged_analysis_page_v1',
             'erp_cp7_check_staged_analysis_source_v1', 'erp_cp7_staged_snapshot_freshness_v1', 'erp_cp7_check_staged_snapshot_v1')
TEMPORARY = {'outputs': 'output', 'target_rows': 'payload', 'pair_rows': 'pair_row', 'pair_lists': 'results', 'fragments': 'body'}
SCHEDULES = [dict(name='cp7-staged-cleanup', schedule='*/5 * * * *', command='select cp7_ops.cleanup_tick()', timezone='UTC', meaning='every 5 minutes'),
             dict(name='cp7-staged-retention', schedule='30 19 * * *', command='select cp7_ops.retention_tick()', timezone='UTC', meaning='02:30 WIB daily'),
             # K4 (owner decision 8 Oct 2026, 6): the server runner joins the same schedule (its own suite: k4-runner).
             dict(name='cp7-staged-runner', schedule='* * * * *',
                  command="set statement_timeout to '8s'; " + ' '.join(['begin; select cp7_ops.analysis_tick(); commit;'] * 60),
                  timezone='UTC', meaning='every minute: up to 60 units, each in its own transaction under the 8 s limit')]
PRIVATE = ('cp7_analysis_stage.clean_done(uuid)', 'cp7_analysis_stage.clean_pending(integer)', 'cp7_analysis_stage.verify_final(uuid)',
           'cp7_analysis_stage.cleanup_due(uuid,text,timestamp with time zone)')
TICKS = ('cp7_ops.cleanup_tick()', 'cp7_ops.retention_tick()', 'cp7_ops.schedules()', 'cp7_ops.analysis_tick()')
auth, b = staged.auth, staged.b
refused, refusal = planv2.refused, planv2.refusal


def temp_counts(cur, job):
    b.api.admin(cur)
    return {t: cur.execute(f'select count(*)from cp7_analysis_stage.{t} where job_id=%s', (job,)).fetchone()[0] for t in TEMPORARY}


def temp_bytes(cur, job):
    b.api.admin(cur)
    return {t: int(cur.execute(f'select coalesce(sum(pg_column_size(x.{c})),0)from cp7_analysis_stage.{t} x where x.job_id=%s', (job,)).fetchone()[0])
            for t, c in TEMPORARY.items()}


def result_digest(cur, job, run):
    """md5 of every row the cleanup must keep: the job row, units, header, pages, page index, capture mark, plan index."""
    b.api.admin(cur)
    one = lambda q, a: cur.execute("select md5(coalesce(string_agg(x::text,chr(10) order by x::text),'')),count(*) from(" + q + ")x", a).fetchone()
    return dict(
        job=one('select j.* from cp7_analysis_stage.jobs j where j.id=%s', (job,)),
        units=one('select u.* from cp7_analysis_stage.units u where u.job_id=%s', (job,)),
        header=one('select h.* from cp7_analysis_stage.headers h where h.run_id=%s', (run,)),
        pages=one('select p.* from cp7_analysis_stage.pages p where p.run_id=%s', (run,)),
        page_set=one('select s.* from cp7_analysis_stage.page_sets s where s.run_id=%s', (run,)),
        capture_mark=one('select c.job_id,c.source_snapshot::text from cp7_analysis_stage.capture_marks c where c.job_id=%s', (job,)),
        plan_targets=one('select p.* from cp7_analysis_stage.plan_targets p where p.job_id=%s', (job,)),
        plan_scope=one('select p.* from cp7_analysis_stage.plan_scope p where p.job_id=%s', (job,)),
        plan_groups=one('select p.* from cp7_analysis_stage.plan_groups p where p.job_id=%s', (job,)))


def tick(cur, role=None):
    """The schedule's entry exactly as pg_cron runs it (as the scheduler role postgres when `role` is given)."""
    b.api.admin(cur)
    if role:
        cur.execute('set local role ' + role)
    out = cur.execute('select cp7_ops.cleanup_tick()').fetchone()[0]
    cur.execute('reset role')
    b.api.admin(cur)
    return out


def cleaned(out, job):
    return [c for c in out['cleaned'] if c['job_id'] == str(job)]


def log_row(cur, job):
    b.api.admin(cur)
    r = cur.execute('select row_to_json(c)::jsonb from cp7_analysis_stage.cleanups c where c.job_id=%s', (job,)).fetchone()
    return r and r[0]


def job_of(cur, key):
    b.api.admin(cur)
    return cur.execute('select id::text from cp7_analysis_stage.jobs where request_id=%s', (key,)).fetchone()[0]


def pages_unchanged(ps_before, ps_after):
    keep = ('run_id', 'identity_hash', 'header', 'pages', 'page_count', 'targets_total', 'totals', 'paged', 'access_epoch')
    return {k: ps_before.get(k) for k in keep} == {k: ps_after.get(k) for k in keep}


def logged_checked(cur, r, before_counts, before_bytes):
    log = log_row(cur, r['job'])
    v = log['verified']
    assert (v['run_id'], v['identity_hash'], v['pages'], v['targets'], v['plan_targets']) == (
        r['run'], r['identity'], r['ps']['page_count'], r['ps']['targets_total'], r['ps']['targets_total']), log
    assert log['removed'] == before_counts and log['stored_bytes_removed'] == before_bytes, log
    assert all((before_bytes[t] > 0) == (before_counts[t] > 0) for t in TEMPORARY), log
    return log


def pause(cur, key):
    """SYNTHETIC (labelled): a running job's last progress moved back 11 minutes (administrative) for a paused or
    abandoned analysis; only updated_at changes."""
    b.api.admin(cur)
    cur.execute("update cp7_analysis_stage.jobs set updated_at=updated_at-interval'11 minutes' where request_id=%s and state='RUNNING'", (key,))


def age(cur, run, delta):
    """SYNTHETIC (labelled): the finished job's finish time moved back (administrative) for days passing."""
    b.api.admin(cur)
    cur.execute('update cp7_analysis_stage.jobs set updated_at=updated_at-%s where run_id=%s', (delta, run))


def cases(cur, today):
    def only_temporary():
        r = report.staged_run(cur, today)
        running_key = uuid.uuid4()
        assert staged.request(cur, today, running_key)['state'] == 'RUNNING'
        assert staged.step(cur, running_key)['state'] == 'RUNNING'
        running = job_of(cur, running_key)
        before, size = temp_counts(cur, r['job']), temp_bytes(cur, r['job'])
        assert before['outputs'] > 0 and before['target_rows'] > 0 and before['fragments'] > 0, before
        running_before, keep_before = temp_counts(cur, running), result_digest(cur, r['job'], r['run'])
        status_before = staged.status(cur, r['key'])
        # While an analysis is being worked, the run defers: no table lock can slow its units.
        deferred = tick(cur, 'postgres')
        assert deferred['cleaned'] == [] and deferred['failed'] == [] and deferred['deferred']['reason'] == 'ANALYSIS_RUNNING', deferred
        assert temp_counts(cur, r['job']) == before and log_row(cur, r['job']) is None
        pause(cur, running_key)
        out = tick(cur, 'postgres')
        mine = cleaned(out, r['job'])
        assert len(mine) == 1 and mine[0]['state'] == 'CLEANED' and mine[0]['removed'] == before and out['failed'] == [] and out['deferred'] is None, out
        assert not cleaned(out, running) and temp_counts(cur, running) == running_before, 'K3C_RUNNING_JOB_TOUCHED'
        assert all(n == 0 for n in temp_counts(cur, r['job']).values()), temp_counts(cur, r['job'])
        assert result_digest(cur, r['job'], r['run']) == keep_before, 'K3C_RESULT_ROWS_CHANGED'
        assert staged.status(cur, r['key']) == status_before, 'K3C_STATUS_CHANGED'
        log = logged_checked(cur, r, before, size)
        job = staged.job_row(cur, r['key'])
        assert log['verified']['source_hash'] == job['source_hash'], log
        assert datetime.fromisoformat(log['verified']['captured_at']) == datetime.fromisoformat(job['captured_at']), (log, job['captured_at'])
        return dict(status='PASS', deferred_while_analysis_running=True, removed_rows=before, stored_bytes_removed=size, result_rows_identical=True, running_job_untouched=True,
                    status_unchanged=True, log_verified_identity_pages_targets_plan_index=True, ran_as_scheduler_role='postgres')

    def reopen():
        r = report.staged_run(cur, today)
        original, ps, shape = staged.fetch(cur, r['run'])
        status_before = staged.status(cur, r['key'])
        tick(cur)
        assert log_row(cur, r['job']) is not None
        again, ps2, shape2 = staged.fetch(cur, r['run'])
        assert again == original and shape2 == shape and pages_unchanged(ps, ps2), 'K3C_REOPENED_RESULT_DIFFERS'
        built = staged.single_on_reference(cur, staged.job_row(cur, r['key']))
        assert again['analysis'] == {k: v for k, v in built.items() if k != 'semantic_hash'}, 'K3C_ORIGIN_NO_LONGER_REBUILDS_THE_RESULT'
        assert staged.status(cur, r['key']) == status_before
        assert staged.limited(cur, 'erp_cp7_check_staged_analysis_source_v1', (r['run'],))['source_state'] == 'UNCHANGED'
        fresh, _ = staged.freshness(cur, r['run'], ps2, r['captured'])
        full = staged.limited(cur, 'erp_cp7_check_staged_snapshot_v1', (r['run'],))
        assert full['source_state'] == 'UNCHANGED', full
        return dict(status='PASS', reassembled_original_identical=True, page_set_identical=True, origin_rebuilds_same_analysis=True,
                    status_identical=True, source_unchanged=True, freshness=fresh['freshness_state'], recorded_check=full['source_state'],
                    pages=shape2['page_count'])

    def plan_v2():
        x = planv2.single(cur, today)
        j = job_of(cur, x['key'])
        tick(cur)
        assert log_row(cur, j) is not None and all(n == 0 for n in temp_counts(cur, j).values())
        o = planv2.options(cur, x['query'])
        keys = ('identity_hash', 'data_as_of', 'needed_pcs', 'capacity_pcs', 'production_state', 'size_id', 'rolls', 'patterns', 'assumptions')
        assert {k: o.get(k) for k in keys} == {k: x['options'].get(k) for k in keys}, 'K3C_PLAN_OPTIONS_CHANGED'
        d = planv2.save(cur, x['payload'])
        p = planv2.preview(cur, d['draft_id'])
        live = p['live']
        assert p['status'] == 'READY_FOR_EXPLICIT_NATIVE_DRAFT' and live['apply_ready'] is True, p
        assert [v['check'] for v in live['verdicts']] == planv2.VERDICTS and all(v['status'] == 'OK' for v in live['verdicts']), live
        assert D(live['need_now_pcs']) == D(x['options']['needed_pcs']), live
        out = planv2.apply(cur, planv2.action(d))
        assert out['state'] == 'NATIVE_DRAFT_CREATED' and out['live']['apply_ready'] is True, out
        return dict(status='PASS', options_same_after_cleanup=True, draft_saved=True, preview_ready=True, applied_with_live_recheck=True)

    def report_v2():
        r = report.staged_run(cur, today)
        tick(cur)
        assert log_row(cur, r['job']) is not None
        key, done, calls = report.published(cur, r)
        d, bodies = report.document(cur, done['publication_id'])
        assert len(d['sections']) == r['pages'] and d['targets_total'] == r['ps']['targets_total'], d.get('sections')
        assert 'Data analisis per ' in d['summary'], d['summary'][:300]
        return dict(status='PASS', report_published_after_cleanup=True, sections=len(d['sections']), hashes_verified=True)

    def ai_and_reminders():
        r = report.staged_run(cur, today)
        idx = ai.index_rows(cur, r)
        keys = [k for _, k, _, _ in idx][:2]
        before = ai.checked(ai.brief(cur, r['run'], keys), r)
        tick(cur)
        assert log_row(cur, r['job']) is not None
        after = ai.checked(ai.brief(cur, r['run'], keys), r)
        drop = ('freshness', 'read_at', 'evaluated_at')
        assert {k: v for k, v in after.items() if k not in drop} == {k: v for k, v in before.items() if k not in drop}, 'K3C_AI_BRIEF_CHANGED'
        assert ai.normal(after['selected']) == ai.normal([ai.expected_row(*t) for t in idx if t[1] in keys])
        s, _ = rem.ready_set(cur, r['run'])
        rows = rem.conditions(cur, r['run'])
        expected = rem.expected_rows(r['original'])
        got = {c['key']: dict(state=c['state'], value=c['value'], rule_id=c['rule_id'], target_key=c['target_key'], material_key=c['material_key'],
                              label=c['label']) for c in rows}
        assert got == expected, 'K3C_REMINDER_CONDITIONS_DIFFER'
        return dict(status='PASS', ai_brief_identical=True, reminder_set_done=s['state'], reminder_conditions_equal_independent=len(rows))

    def failed_retried():
        r = report.staged_run(cur, today)
        before, size = temp_counts(cur, r['job']), temp_bytes(cur, r['job'])
        b.api.admin(cur)
        good = cur.execute('select sha256 from cp7_analysis_stage.pages where run_id=%s and idx=0', (r['run'],)).fetchone()[0]

        def page_hash(value):
            # SYNTHETIC (labelled): the stored hash of page 0 changed and restored (administrative, trigger suspended)
            # to stand for a result that does not verify; nothing else is touched.
            b.api.admin(cur)
            cur.execute('alter table cp7_analysis_stage.pages disable trigger immutable_stage_pages')
            cur.execute('update cp7_analysis_stage.pages set sha256=%s where run_id=%s and idx=0', (value, r['run']))
            cur.execute('alter table cp7_analysis_stage.pages enable trigger immutable_stage_pages')
        page_hash('0' * 64)
        out = tick(cur)
        fail = [f for f in out['failed'] if f['job_id'] == r['job']]
        assert len(fail) == 1 and fail[0]['code'] == 'CP7_ANALYSIS_CLEANUP_UNVERIFIED' and not cleaned(out, r['job']), out
        assert temp_counts(cur, r['job']) == before and log_row(cur, r['job']) is None, 'K3C_UNVERIFIED_RESULT_CLEANED'
        page_hash(good)
        out = tick(cur)
        assert len(cleaned(out, r['job'])) == 1 and not [f for f in out['failed'] if f['job_id'] == r['job']], out
        logged_checked(cur, r, before, size)
        again = tick(cur)
        assert not cleaned(again, r['job']) and not [f for f in again['failed'] if f['job_id'] == r['job']], again
        b.api.admin(cur)
        direct = cur.execute('select cp7_analysis_stage.clean_done(%s)', (r['job'],)).fetchone()[0]
        assert direct['state'] == 'ALREADY_CLEANED' and direct['removed'] == before, direct
        for sql in ('update cp7_analysis_stage.cleanups set removed=removed', 'delete from cp7_analysis_stage.cleanups'):
            refused(cur, lambda sql=sql: cur.execute(sql), 'CP7_RUN_IMMUTABLE')
        assert staged.fetch(cur, r['run'])[1]['identity_hash'] == r['identity']
        return dict(status='PASS', unverified_result_nothing_removed=True, retried_and_cleaned=True, repeat_changes_nothing=True,
                    direct_call_returns_logged_cleanup=True, log_immutable=True)

    def only_done_kept():
        running_key = uuid.uuid4()
        staged.request(cur, today, running_key)
        staged.step(cur, running_key)
        running = job_of(cur, running_key)
        pause(cur, running_key)
        # A real FAILED job: its actor's access changes after the capture, so its next unit fails the job
        # (CP7_ANALYSIS_ACCESS_CHANGED). FAILED work is the 7-day purge's, never this cleanup's.
        other, other_role = auth.custom_actor(cur)
        failed_key = uuid.uuid4()
        staged.request(cur, today, failed_key, other)
        staged.step(cur, failed_key, other)
        b.api.admin(cur)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')", (other_role,))
        st = staged.step(cur, failed_key, other)
        assert st['state'] == 'FAILED' and st['failure']['code'] == 'CP7_ANALYSIS_ACCESS_CHANGED', st
        failed = dict(job=job_of(cur, failed_key))
        assert temp_counts(cur, failed['job'])['outputs'] > 0
        expired = report.staged_run(cur, today)
        age(cur, expired['run'], timedelta(days=8))
        counts = {j: temp_counts(cur, j) for j in (running, failed['job'], expired['job'])}
        out = tick(cur)
        assert all(not cleaned(out, j) for j in counts) and all(f['job_id'] not in counts for f in out['failed']), out
        assert {j: temp_counts(cur, j) for j in counts} == counts, 'K3C_NOT_DUE_JOB_TOUCHED'
        b.api.admin(cur)
        for j, code in ((running, 'CP7_ANALYSIS_CLEANUP_NOT_DONE'), (failed['job'], 'CP7_ANALYSIS_CLEANUP_NOT_DONE'),
                        (expired['job'], 'CP7_ANALYSIS_CLEANUP_EXPIRED')):
            refused(cur, lambda j=j: cur.execute('select cp7_analysis_stage.clean_done(%s)', (j,)), code)
        assert {j: temp_counts(cur, j) for j in counts} == counts
        purged = cur.execute('select cp7_analysis_stage.purge_expired(100)').fetchone()[0]
        assert any(p['job_id'] == expired['job'] for p in purged['purged']), purged
        assert not cleaned(tick(cur), expired['job']), 'K3C_PURGED_JOB_SELECTED_AGAIN'
        return dict(status='PASS', running_untouched=True, failed_untouched=True, expired_left_to_7_day_purge=True,
                    refusals=['CP7_ANALYSIS_CLEANUP_NOT_DONE', 'CP7_ANALYSIS_CLEANUP_EXPIRED'])

    def documents():
        x = planv2.single(cur, today)
        j = job_of(cur, x['key'])
        d = planv2.save(cur, x['payload'])
        tick(cur)
        log = log_row(cur, j)
        assert log is not None
        r = planv2.read(cur, d['draft_id'])
        assert r['draft_id'] == d['draft_id'] and planv2.preview(cur, d['draft_id'])['live']['apply_ready'] is True
        b.api.admin(cur)
        pages = cur.execute('select count(*)from cp7_analysis_stage.pages where run_id=%s', (x['run'],)).fetchone()[0]
        age(cur, x['run'], timedelta(days=8))
        purged = cur.execute('select cp7_analysis_stage.purge_expired(100)').fetchone()[0]
        mine = [p for p in purged['purged'] if p['job_id'] == j]
        assert len(mine) == 1 and mine[0]['documents'] == {'plan_v2_drafts': 1}, purged
        assert all(n == 0 for k, n in mine[0]['removed'].items() if k in TEMPORARY) and 'pages' not in mine[0]['removed'], mine
        assert cur.execute('select count(*)from cp7_analysis_stage.pages where run_id=%s', (x['run'],)).fetchone()[0] == pages
        assert log_row(cur, j) == log and planv2.read(cur, d['draft_id'])['draft_id'] == d['draft_id']
        return dict(status='PASS', draft_readable_after_cleanup=True, purge_after_7_days_keeps_document_pages=True, cleanup_log_kept=True)

    def schedule_private():
        b.api.admin(cur)
        assert cur.execute('select cp7_ops.schedules()').fetchone()[0] == SCHEDULES
        for sig in TICKS:
            assert cur.execute("select has_function_privilege('postgres',%s,'EXECUTE')", (sig,)).fetchone()[0], sig
            for who in ('anon', 'authenticated', 'service_role'):
                assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')', (who, sig)).fetchone()[0], (who, sig)
        for sig in PRIVATE:
            for who in ('anon', 'authenticated', 'service_role', 'postgres'):
                if who == 'postgres' and cur.execute("select rolsuper from pg_roles where rolname='postgres'").fetchone()[0]:
                    continue
                assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')', (who, sig)).fetchone()[0], (who, sig)
        for who in ('anon', 'authenticated', 'service_role'):
            assert not cur.execute("select has_table_privilege(%s,'cp7_analysis_stage.cleanups','SELECT,INSERT,UPDATE,DELETE')", (who,)).fetchone()[0], who
            assert not cur.execute("select has_schema_privilege(%s,'cp7_ops','USAGE')", (who,)).fetchone()[0], who
        state, message, _ = refusal(cur, lambda: tick(cur, 'authenticated'))
        assert state == '42501', (state, message)
        for bad in (0, 101, None):
            refused(cur, lambda bad=bad: cur.execute('select cp7_analysis_stage.clean_pending(%s)', (bad,)), 'CP7_ANALYSIS_CLEANUP_LIMIT')
        assert cur.execute("select count(*)from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like '%clean%'").fetchone()[0] == 0
        return dict(status='PASS', schedules=SCHEDULES, ticks_scheduler_role_only=True, cleanup_functions_private=True, no_public_rpc=True,
                    authenticated_refused='42501', limit_bounded=True)

    return list(zip(IDS['native'], (only_temporary, reopen, plan_v2, report_v2, ai_and_reminders, failed_retried, only_done_kept,
                                    documents, schedule_private)))


def races(tools, today):
    def committed_run(n=1):
        with tools.connect() as conn, conn.cursor() as cur:
            runs = [report.staged_run(cur, today) for _ in range(n)]
            counts = {r['job']: temp_counts(cur, r['job']) for r in runs}
            conn.commit()
        return runs, counts

    def two_ticks():
        runs, counts = committed_run(2)
        gate = threading.Barrier(2)

        def send():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                out = tick(cur)
                conn.commit()
                return out
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [f.result(240) for f in [pool.submit(send) for _ in range(2)]]
        # The cleanups take the temporary tables' lock in turn: a tick that waited too long gives up (55P03)
        # and its job is cleaned by the next run. No job is cleaned twice and no other failure is allowed.
        done = [c['job_id'] for o in results for c in o['cleaned']]
        waited = [f for o in results for f in o['failed']]
        assert all(f['sqlstate'] == '55P03' for f in waited) and len(done) == len(set(done)), results
        with tools.connect() as conn, conn.cursor() as cur:
            follow = tick(cur)
            conn.commit()
        done += [c['job_id'] for c in follow['cleaned']]
        assert sorted(j for j in done if j in counts) == sorted(counts) and follow['failed'] == [], (results, follow)
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert cur.execute('select count(*)from cp7_analysis_stage.cleanups where job_id=any(%s::uuid[])', (list(counts),)).fetchone()[0] == 2
            for r in runs:
                assert all(n == 0 for n in temp_counts(cur, r['job']).values()) and staged.fetch(cur, r['run'])[1]['identity_hash'] == r['identity']
        return dict(status='PASS', two_concurrent_ticks_each_job_cleaned_once=True, log_rows=2, lock_waits_retried=len(waited))

    def busy_table():
        runs, counts = committed_run(1)
        r = runs[0]
        holder = tools.connect()
        try:
            with holder.cursor() as h:
                b.api.admin(h)
                # A concurrent writer of the temporary tables (another analysis's unit) holds ROW EXCLUSIVE.
                h.execute('lock table cp7_analysis_stage.outputs in row exclusive mode')
                with tools.connect() as conn, conn.cursor() as cur:
                    started = time.monotonic()
                    out = tick(cur)
                    waited = time.monotonic() - started
                    conn.commit()
                fail = [f for f in out['failed'] if f['job_id'] == r['job']]
                assert len(fail) == 1 and fail[0]['sqlstate'] == '55P03' and not cleaned(out, r['job']), out
                assert waited < 7, waited
            holder.commit()
        finally:
            holder.close()
        with tools.connect() as conn, conn.cursor() as cur:
            assert temp_counts(cur, r['job']) == counts[r['job']] and log_row(cur, r['job']) is None, 'K3C_BUSY_CLEANUP_PARTLY_APPLIED'
            assert staged.fetch(cur, r['run'])[1]['identity_hash'] == r['identity']
            out = tick(cur)
            conn.commit()
            assert len(cleaned(out, r['job'])) == 1, out
        return dict(status='PASS', gave_up_on_busy_table=fail[0]['sqlstate'], waited_s=round(waited, 2), result_available=True, retried_and_cleaned=True)

    def cron_fires():
        runs, counts = committed_run(1)
        r = runs[0]
        u = urlparse(tools.admin)
        database = u.path.lstrip('/')
        cron_url = urlunparse(u._replace(path='/postgres'))
        with tools.connect() as conn, conn.cursor() as cur:
            defs = schedule.definitions(cur)
        assert defs == SCHEDULES, defs
        with psycopg.connect(cron_url, autocommit=True) as cron, cron.cursor() as cc:
            version = cc.execute("select extversion from pg_extension where extname='pg_cron'").fetchone()
            assert version, 'K3C_PG_CRON_NOT_AVAILABLE'
            seconds = tuple(int(x) for x in version[0].split('.')[:2]) >= (1, 5)
            # TEST_SCHEDULE_OVERRIDE (labelled): both jobs fire every 10 seconds (or every minute) on this disposable copy only.
            fast = '10 seconds' if seconds else '* * * * *'
            since = cc.execute('select now()').fetchone()[0]
            ids = schedule.install(cc, database, 'postgres', defs, {d['name']: fast for d in defs})
            try:
                ok, detail = schedule.matches(cc, database, 'postgres', [dict(d, schedule=fast) for d in defs])
                assert ok, detail
                deadline, runs_seen = time.monotonic() + 150, {}
                while time.monotonic() < deadline:
                    runs_seen = {n: schedule.runs(cc, i, since) for n, i in ids.items()}
                    if all(any(x['status'] in ('succeeded', 'failed') for x in v) for v in runs_seen.values()):
                        break
                    time.sleep(3)
                finished = {n: [x for x in v if x['status'] in ('succeeded', 'failed')] for n, v in runs_seen.items()}
                assert all(v and all(x['status'] == 'succeeded' for x in v) for v in finished.values()), runs_seen
            finally:
                removed = schedule.uninstall(cc, database)
                cc.execute('delete from cron.job_run_details where jobid=any(%s)', (list(ids.values()),))
            assert sorted(removed) == sorted(schedule.job_name(n, database) for n in ids) and schedule.installed(cc, database) == []
        with tools.connect() as conn, conn.cursor() as cur:
            log = log_row(cur, r['job'])
            assert log is not None and all(n == 0 for n in temp_counts(cur, r['job']).values()), 'K3C_CRON_DID_NOT_CLEAN'
            assert log['removed'] == counts[r['job']]
            assert staged.fetch(cur, r['run'])[1]['identity_hash'] == r['identity']
        return dict(status='PASS', pg_cron=version[0], test_schedule_override=fast, jobs_fired={n: len(v) for n, v in finished.items()},
                    cleaned_by_cron=True, removed_after_test=sorted(removed), installed_definitions_are_the_package=True)

    def nightly_backup():
        runs, _ = committed_run(1)
        r = runs[0]
        with tools.connect() as conn, conn.cursor() as cur:
            tick(cur)
            conn.commit()
        u = urlparse(tools.admin)
        database = u.path.lstrip('/')
        container = os.environ.get('CP6_DATABASE_CONTAINER', 'supabase_db_cp5-local')
        with tempfile.TemporaryDirectory(prefix='cp7-nightly-') as dest:
            # SYNTHETIC (labelled): three earlier nights' receipts (two verified, one not) to prove retention.
            for i, verified in enumerate((True, False, True)):
                name = 'erp-synthetic-%d.dump' % i
                (Path(dest) / name).write_bytes(b'SYNTHETIC EARLIER NIGHT')
                (Path(dest) / (name + '.receipt.json')).write_text(json.dumps(dict(
                    contract=nightly.CONTRACT, file=name, restore_verified=verified,
                    started_at_utc=(datetime.now(timezone.utc) - timedelta(days=3 - i)).isoformat())))
            # A night whose backup cannot be made (the source cannot be read) removes nothing.
            bad = nightly.backup(tools.admin, 'cp7_no_such_database', 'cp7_nightly_verify', dest, keep=2, container=container)
            assert bad['restore_verified'] is False and 'BACKUP_DUMP_FAILED' in bad.get('error', '') and bad['retention']['removed'] == [], bad
            good = nightly.backup(tools.admin, database, 'cp7_nightly_verify', dest, keep=2, container=container)
            assert good['restore_verified'] is True and good['data']['differ'] == {} and good['restore']['unexplained'] == [], good
            assert good['bytes'] == (Path(dest) / good['file']).stat().st_size and len(good['sha256']) == 64
            kept = good['retention']['kept']
            assert kept[0] == good['file'] and len(kept) == 2 and 'erp-synthetic-0.dump' in good['retention']['removed'], good['retention']
            assert not (Path(dest) / 'erp-synthetic-0.dump').exists() and (Path(dest) / good['file']).exists()
            tables = good['data']['tables']
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert cur.execute("select count(*) from pg_database where datname='cp7_nightly_verify'").fetchone()[0] == 0
        return dict(status='PASS', restore_verified=True, tables_compared=tables, failed_night_removed_nothing=True,
                    newest_verified_kept=kept, older_removed_after_verified_night=good['retention']['removed'], schedule=nightly.SCHEDULE)

    def cron_two_databases():
        """P20 F02 (AS20-43): one pg_cron scheduler and role, the package jobs for two databases. Installing for B never
        moves A's jobs, installing A again changes nothing, a same-named job of another database is refused before any
        change, and uninstall removes only the target database's jobs."""
        u = urlparse(tools.admin)
        a = u.path.lstrip('/')
        cron_url = urlunparse(u._replace(path='/postgres'))
        other = 'cp7_cron_b_' + uuid.uuid4().hex[:8]
        clash_db = a + '_clash'
        with tools.connect() as conn, conn.cursor() as cur:
            defs = schedule.definitions(cur)
        # TEST_SCHEDULE_OVERRIDE (labelled): once a year, so no job fires during the case.
        yearly = {d['name']: '0 3 1 1 *' for d in defs}
        with psycopg.connect(cron_url, autocommit=True) as cron, cron.cursor() as cc:
            assert cc.execute("select extversion from pg_extension where extname='pg_cron'").fetchone(), 'K3C_PG_CRON_NOT_AVAILABLE'
            cc.execute('create database "%s"' % other)
            misnamed = None
            try:
                ids_a = schedule.install(cc, a, 'postgres', defs, yearly)
                jobs_a = schedule.installed(cc, a)
                ids_b = schedule.install(cc, other, 'postgres', defs, yearly)
                assert schedule.installed(cc, a) == jobs_a and set(ids_b.values()).isdisjoint(ids_a.values()), (jobs_a, ids_b)
                ok_b, detail_b = schedule.matches(cc, other, 'postgres', [dict(d, schedule=yearly[d['name']]) for d in defs])
                assert ok_b, detail_b
                again = schedule.install(cc, a, 'postgres', defs, yearly)
                assert again == ids_a and schedule.installed(cc, a) == jobs_a, (again, ids_a)
                # A job named for a third database but pointing at B: installing for that name is refused, nothing moves.
                misnamed = cc.execute('select cron.schedule_in_database(%s,%s,%s,%s,%s,false)',
                                      (schedule.job_name(defs[0]['name'], clash_db), '0 3 1 1 *', 'select 1', other, 'postgres')).fetchone()[0]
                before = (schedule.installed(cc, a), schedule.installed(cc, other))
                try:
                    schedule.install(cc, clash_db, 'postgres', defs, yearly)
                    raise AssertionError('K3C_CLASH_NOT_REFUSED')
                except RuntimeError as e:
                    assert 'CP7_SCHEDULE_NAME_USED_BY_ANOTHER_DATABASE' in str(e), e
                assert (schedule.installed(cc, a), schedule.installed(cc, other)) == before
                cc.execute('select cron.unschedule(%s::bigint)', (misnamed,))
                misnamed = None
                removed_b = schedule.uninstall(cc, other)
                assert sorted(removed_b) == sorted(schedule.job_name(d['name'], other) for d in defs) and schedule.installed(cc, a) == jobs_a
            finally:
                if misnamed is not None:
                    cc.execute('select cron.unschedule(%s::bigint)', (misnamed,))
                schedule.uninstall(cc, a)
                schedule.uninstall(cc, other)
                cc.execute('drop database if exists "%s" with (force)' % other)
            assert schedule.installed(cc, a) == [] and schedule.installed(cc, other) == []
        return dict(status='PASS', a_untouched_by_b=True, reinstall_same_ids=True, clash_refused_before_change=True,
                    uninstall_only_target=True, job_names=[j['name'] for j in jobs_a], test_schedule_override='0 3 1 1 *')

    def backup_retry_same_second():
        """P20 F03 (AS20-45): a verified backup, then a failed retry in the same second into the same folder. The first
        dump and its receipt stay byte-identical; a name that already exists is refused before anything is written."""
        u = urlparse(tools.admin)
        database = u.path.lstrip('/')
        container = os.environ.get('CP6_DATABASE_CONTAINER', 'supabase_db_cp5-local')
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        at = datetime.now(timezone.utc).replace(microsecond=0)
        with tempfile.TemporaryDirectory(prefix='cp7-nightly-retry-') as dest:
            good = nightly.backup(tools.admin, database, 'cp7_nightly_verify', dest, keep=14, container=container, now=at)
            assert good['restore_verified'] is True, good
            dump, rec = Path(dest) / good['file'], Path(dest) / (good['file'] + '.receipt.json')
            before = (digest(dump), digest(rec))
            bad = nightly.backup(tools.admin, 'cp7_no_such_database', 'cp7_nightly_verify', dest, keep=14, container=container, now=at)
            assert bad['restore_verified'] is False and bad['file'] != good['file'] and bad['retention']['removed'] == [], bad
            assert bad['file'].split('-WIB-')[0] == good['file'].split('-WIB-')[0], (good['file'], bad['file'])
            assert (digest(dump), digest(rec)) == before and json.loads(rec.read_text())['restore_verified'] is True
            # A name collision (forced: the same token twice) is refused before any file is written.
            token = uuid.UUID(int=7)
            real = nightly.uuid.uuid4
            nightly.uuid.uuid4 = lambda: token
            try:
                first = nightly.backup(tools.admin, 'cp7_no_such_database', 'cp7_nightly_verify', dest, keep=14, container=container, now=at)
                files = sorted(p.name for p in Path(dest).iterdir())
                try:
                    nightly.backup(tools.admin, database, 'cp7_nightly_verify', dest, keep=14, container=container, now=at)
                    raise AssertionError('K3C_COLLISION_NOT_REFUSED')
                except FileExistsError as e:
                    assert 'BACKUP_NAME_COLLISION' in str(e), e
            finally:
                nightly.uuid.uuid4 = real
            assert sorted(p.name for p in Path(dest).iterdir()) == files and (digest(dump), digest(rec)) == before
        return dict(status='PASS', verified_dump_and_receipt_unchanged=True, retry_same_second_new_name=bad['file'],
                    collision_refused_before_write=True, failed_retry_removed_nothing=True, synthetic='same timestamp passed as now; forced equal token')

    return list(zip(IDS['races'], (two_ticks, busy_table, cron_fires, nightly_backup, cron_two_databases, backup_retry_same_second)))


def http_cases(http, today):
    def reopen():
        owner = http.login('OWNER', 'k3c-owner')
        with http.connect() as conn, conn.cursor() as cur:
            r = report.staged_run(cur, today, owner.auth_user_id)
            original, ps, _ = staged.fetch(cur, r['run'], owner.auth_user_id)
            conn.commit()
        with http.connect() as conn, conn.cursor() as cur:
            out = tick(cur)
            conn.commit()
            assert len(cleaned(out, r['job'])) == 1, out
        s = owner.rpc('erp_cp7_get_staged_analysis_v1', dict(p_request=str(r['key'])))
        assert s['status'] == 200 and s['body']['state'] == 'DONE' and s['body']['run_id'] == r['run'], s
        p = owner.rpc('erp_cp7_read_staged_analysis_pages_v1', dict(p_run=r['run']))
        assert p['status'] == 200 and p['body']['identity_hash'] == r['identity'] and p['body']['pages'] == ps['pages'], p['status']
        for page in p['body']['pages']:
            e = owner.rpc('erp_cp7_read_staged_analysis_page_v1', dict(p_run=r['run'], p_index=page['index'], p_access=p['body']['access_epoch']))
            assert e['status'] == 200 and staged.sha(e['body']['body']) == page['sha256'], (page['index'], e['status'])
        c = owner.rpc('erp_cp7_check_staged_analysis_source_v1', dict(p_run=r['run']))
        assert c['status'] == 200 and c['body']['source_state'] == 'UNCHANGED', c
        anon = http.anon_rpc('erp_cp7_read_staged_analysis_pages_v1', dict(p_run=r['run']))
        assert anon['status'] in (401, 403), anon
        return dict(status='PASS', real_Auth_reopen_after_cleanup=True, pages_hash_verified=len(p['body']['pages']), source_unchanged=True,
                    anonymous_refused=anon['status'])

    def not_reachable():
        owner = http.login('OWNER', 'k3c-owner-2')
        with http.connect() as conn, conn.cursor() as cur:
            r = report.staged_run(cur, today, owner.auth_user_id)
            conn.commit()
        refusals = {}
        for name, args in (('cleanup_tick', {}), ('clean_done', dict(p_job=r['job'])), ('clean_pending', dict(p_limit=5))):
            x = owner.rpc(name, args)
            assert x['status'] >= 400, (name, x)
            refusals[name] = x['status']
        with http.connect() as conn, conn.cursor() as cur:
            assert log_row(cur, r['job']) is None and temp_counts(cur, r['job'])['outputs'] > 0, 'K3C_CLEANUP_REACHABLE_OVER_HTTP'
        return dict(status='PASS', not_exposed=refusals, nothing_cleaned=True)

    return list(zip(IDS['http'], (reopen, not_reachable)))
