"""K4: the staged analysis runs on the server, so it goes on while its page is closed (owner decision 8 Oct 2026, 6).

Owner: "arah akhirnya berjalan di server, supaya tetap lanjut saat halaman ditutup. Membuka ulang harus melanjutkan
job yang sama, bukan menghitung ulang atau menggandakan pekerjaan."

The runner is cp7_ops.analysis_tick (pg_cron every minute, 60 ticks, each in its own transaction under the 8 s
statement limit) -> cp7_analysis_stage.run_next: the running job with the oldest progress that no other session holds
gets ONE unit through the same step() a page uses; the actor's access is re-read for every unit through the same ERP
access functions (the job's stored actor as the transaction's request identity, no login session). Proved here: a job
requested by a page finishes with no page at all and its result is the single path's on the same reference; page and
server together never run or store a unit twice; reopening is the same job and run; access is re-checked per unit; a
denied job fails and does not hold the others back; nothing runs without the 8 s limit; a stopped unit is an attempt
as for a page; the schedule entry is private; real pg_cron runs a job to the end; real Auth/PostgREST and a real
browser whose page is closed. SYNTHETIC steps are labelled where they are used.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from time import monotonic
from urllib.parse import urlparse, urlunparse
import threading
import time
import uuid

import psycopg

import cp7_p19_staged_cases as staged
import cp7_p19_native_load_cases as load
import cp7_p18_e01_bridge_cases as bridge
import cp7_p19_plan_v2_cases as planv2
import cp7_schedule as schedule

IDS = dict(
    native=['K4R_SERVER_FINISHES_WITHOUT_PAGE', 'K4R_PAGE_AND_SERVER_ONE_JOB', 'K4R_ACCESS_RECHECKED_EACH_UNIT',
            'K4R_DENIED_JOB_DOES_NOT_HOLD_OTHERS', 'K4R_LIMIT_REQUIRED', 'K4R_SCHEDULE_DEFINED_PRIVATE', 'K4R_STATUS_REPORTS_RUNNER'],
    races=['K4R_RACE_PAGE_AND_SERVER_ONE_UNIT', 'K4R_RACE_TWO_TICKS_ONE_UNIT', 'K4R_RACE_LIMIT_STOPS_THEN_CONTINUES',
           'K4R_RACE_ACCESS_CHANGED_DURING_UNIT', 'K4R_RACE_PG_CRON_FINISHES_JOB'],
    http=['K4R_HTTP_CLOSED_PAGE_FINISHES', 'K4R_HTTP_TICK_NOT_REACHABLE'],
    browser=['K4R_BROWSER_DESKTOP_CLOSED_PAGE_FINISHES', 'K4R_BROWSER_MOBILE_CLOSED_PAGE_FINISHES'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.k4.server-runner.v1'
FUNCTIONS = ('erp_cp7_request_staged_analysis_v1', 'erp_cp7_step_staged_analysis_v1', 'erp_cp7_get_staged_analysis_v1',
             'erp_cp7_read_staged_analysis_pages_v1', 'erp_cp7_read_staged_analysis_page_v1')
RUNNER = dict(name='cp7-staged-runner', schedule='* * * * *',
              command="set statement_timeout to '8s'; " + ' '.join(['begin; select cp7_ops.analysis_tick(); commit;'] * 60),
              timezone='UTC', meaning='every minute: up to 60 units, each in its own transaction under the 8 s limit')
TICK = 'cp7_ops.analysis_tick()'
PRIVATE = ('cp7_analysis_stage.run_next()',)
OUTCOMES = ('UNIT_STORED', 'UNIT_RETRY', 'JOB_DONE', 'JOB_FAILED', 'ACCESS_CHANGED_DURING_UNIT', 'IDLE')
# Driver bound only (ticks per job); never an application limit.
TICKS = 20000
auth, b = staged.auth, staged.b
refused, refusal = planv2.refused, planv2.refusal


def tick(cur, timeout='8s'):
    """One runner tick exactly as pg_cron runs it: the scheduler role postgres, under the given statement limit (restored after)."""
    b.api.admin(cur)
    prior = cur.execute('show statement_timeout').fetchone()[0]
    cur.execute("select set_config('statement_timeout',%s,true)", (timeout,))
    cur.execute('set local role postgres')
    out = cur.execute('select cp7_ops.analysis_tick()').fetchone()[0]
    cur.execute('reset role')
    b.api.admin(cur)
    cur.execute("select set_config('statement_timeout',%s,true)", (prior,))
    assert out['tick'] == 'cp7-staged-runner' and out['outcome'] in OUTCOMES, out
    return out


def run_by_server(cur, key, subject=None):
    """Ticks only (no page call) until the job is DONE or FAILED; every tick that ran advanced or recorded an attempt."""
    job = job_id(cur, key)
    ticks, last = [], staged.checked(staged.status(cur, key, subject), key)
    while last['state'] == 'RUNNING':
        assert len(ticks) < TICKS, 'K4R_DRIVER_BOUND'
        out = tick(cur)
        assert out.get('job_id') == job, ('K4R_TICK_RAN_ANOTHER_JOB', out)
        nxt = staged.checked(staged.status(cur, key, subject), key)
        assert nxt['units_done'] == out['units_done'] and (nxt['units_done'] > last['units_done'] or nxt['unit_attempts'] > last['unit_attempts']
                                                           or nxt['state'] != 'RUNNING'), (last, out, nxt)
        ticks.append(out['outcome'])
        last = nxt
    return last, ticks


def job_id(cur, key):
    b.api.admin(cur)
    return cur.execute('select id::text from cp7_analysis_stage.jobs where request_id=%s', (key,)).fetchone()[0]


def units_once(cur, key):
    """Every unit of the job stored exactly once, contiguous from 0, and nothing beyond the plan."""
    b.api.admin(cur)
    n, lo, hi, distinct, count = cur.execute("""select j.unit_count,min(o.idx),max(o.idx),count(distinct o.idx),count(o.idx)
        from cp7_analysis_stage.jobs j left join cp7_analysis_stage.outputs o on o.job_id=j.id where j.request_id=%s group by j.unit_count""",
                                             (key,)).fetchone()
    assert (lo, hi, distinct, count) == (0, n - 1, n, n), ('K4R_UNIT_NOT_STORED_ONCE', n, lo, hi, distinct, count)
    return n


def same_as_single(cur, key, done):
    original, ps, shape = staged.fetch(cur, done['run_id'])
    built = staged.single_on_reference(cur, staged.job_row(cur, key))
    assert original['analysis'] == {k: v for k, v in built.items() if k != 'semantic_hash'}, 'K4R_SERVER_RESULT_DIFFERS_FROM_SINGLE_ON_SAME_REFERENCE'
    return ps, shape


def runner_row(cur):
    b.api.admin(cur)
    r = cur.execute('select row_to_json(r)::jsonb from cp7_analysis_stage.runner r').fetchone()
    return r and r[0]


def claims(cur):
    return cur.execute("select current_setting('request.jwt.claims',true),current_setting('request.jwt.claim.sub',true)").fetchone()


def cases(cur, today):
    def finishes_without_page():
        f, _ = load.real_workload(cur, today)
        before = b.boundary.snapshot(cur)
        key = uuid.uuid4()
        first = staged.checked(staged.request(cur, today, key), key, 'RUNNING')
        started = monotonic()
        done, ticks = run_by_server(cur, key)
        elapsed = round((monotonic() - started) * 1000, 3)
        staged.checked(done, key, 'DONE')
        assert ticks[-1] == 'JOB_DONE' and set(ticks[:-1]) <= {'UNIT_STORED'}, ticks
        n = units_once(cur, key)
        assert len(ticks) == n, ('K4R_TICKS_NOT_ONE_PER_UNIT', len(ticks), n)
        # Reopening is the same job and run: the same UUID answers DONE, a page step after it changes nothing.
        assert staged.checked(staged.request(cur, today, key), key, 'DONE') == done and staged.checked(staged.step(cur, key), key, 'DONE') == done
        assert done['run_id'] is not None and staged.job_row(cur, key)['run_id'] == done['run_id']
        assert tick(cur)['outcome'] == 'IDLE', 'K4R_DONE_JOB_TICKED_AGAIN'
        ps, shape = same_as_single(cur, key, done)
        assert staged.counts(cur, key)[:3] == (0, 0, 1)
        assert b.boundary.snapshot(cur) == before
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', page_calls_after_request=0, ticks=len(ticks), units=n, server_job_ms=elapsed, pages=shape,
                    identity_hash=ps['identity_hash'], result_equals_single_on_same_reference=True, reopened_same_job_and_run=True,
                    every_unit_stored_once=True, request_reference=first['reference'])

    def page_and_server():
        f, _ = load.real_workload(cur, today)
        key = uuid.uuid4()
        staged.checked(staged.request(cur, today, key), key, 'RUNNING')
        by = dict(page=0, server=0)
        last = staged.checked(staged.status(cur, key), key)
        turn = 0
        while last['state'] == 'RUNNING':
            assert sum(by.values()) < TICKS
            if turn % 3 == 2:
                nxt = staged.checked(staged.step(cur, key), key)
                by['page'] += 1
            else:
                out = tick(cur)
                nxt = staged.checked(staged.status(cur, key), key)
                assert out['units_done'] == nxt['units_done'], (out, nxt)
                by['server'] += 1
            assert nxt['units_done'] == last['units_done'] + 1 or nxt['state'] != 'RUNNING', (last, nxt)
            last, turn = nxt, turn + 1
        staged.checked(last, key, 'DONE')
        n = units_once(cur, key)
        assert by['page'] >= 1 and by['server'] >= 2 and sum(by.values()) == n, (by, n)
        # Both drivers worked on one job: one job row, one run, the same answers to the page and to a new request.
        assert staged.counts(cur, key)[:3] == (0, 0, 1)
        assert staged.checked(staged.status(cur, key), key, 'DONE') == last == staged.checked(staged.request(cur, today, key), key, 'DONE')
        same_as_single(cur, key, last)
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', units=n, units_by_page=by['page'], units_by_server=by['server'], one_job_one_run=True,
                    every_unit_stored_once=True, result_equals_single_on_same_reference=True)

    def access_rechecked():
        subject, role = auth.custom_actor(cur)
        key = uuid.uuid4()
        staged.checked(staged.request(cur, today, key, subject), key, 'RUNNING')
        b.api.admin(cur)
        held = claims(cur)
        first = tick(cur)
        assert first['outcome'] == 'UNIT_STORED' and claims(cur) == held, ('K4R_CLAIMS_NOT_RESTORED', first, claims(cur), held)
        # The actor's role changes (any change of the access, here one more permission): the next unit fails the job.
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')", (role,))
        failed = tick(cur)
        assert failed['outcome'] == 'JOB_FAILED', failed
        s = staged.checked(staged.status(cur, key, subject), key, 'FAILED')
        assert s['failure']['code'] == 'CP7_ANALYSIS_ACCESS_CHANGED' and s['failure']['unit'] == first['units_done'] == s['units_done'], s
        assert staged.counts(cur, key)[3] == 0 and tick(cur)['outcome'] == 'IDLE'
        # An actor deactivated after the request: the next unit fails the job too (denied is a changed access).
        gone, _ = auth.custom_actor(cur)
        key2 = uuid.uuid4()
        staged.checked(staged.request(cur, today, key2, gone), key2, 'RUNNING')
        b.api.admin(cur)
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (gone,))
        held = claims(cur)
        assert tick(cur)['outcome'] == 'JOB_FAILED' and claims(cur) == held, 'K4R_CLAIMS_NOT_RESTORED'
        b.api.admin(cur)
        s2 = cur.execute('select state,failure_code,units_done from cp7_analysis_stage.jobs where request_id=%s', (key2,)).fetchone()
        assert s2 == ('FAILED', 'CP7_ANALYSIS_ACCESS_CHANGED', 0), s2
        return dict(status='PASS', unit_ran_as_stored_actor=True, request_identity_restored_after_tick=True,
                    role_change_fails_job=s['failure'], deactivated_actor_fails_job=s2[1], no_pages_after_failure=True)

    def denied_does_not_hold():
        gone, _ = auth.custom_actor(cur)
        stuck, other = uuid.uuid4(), uuid.uuid4()
        staged.checked(staged.request(cur, today, stuck, gone), stuck, 'RUNNING')
        staged.checked(staged.request(cur, today, other), other, 'RUNNING')
        b.api.admin(cur)
        # SYNTHETIC (labelled): the denied actor's job is made the oldest so the runner reaches it first.
        cur.execute("update cp7_analysis_stage.jobs set updated_at=updated_at-interval'1 hour' where request_id=%s", (stuck,))
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (gone,))
        a = tick(cur)
        assert a['outcome'] == 'JOB_FAILED' and a['job_id'] == job_id(cur, stuck), a
        c = tick(cur)
        assert c['outcome'] == 'UNIT_STORED' and c['job_id'] == job_id(cur, other), c
        done, ticks = run_by_server(cur, other)
        staged.checked(done, other, 'DONE')
        return dict(status='PASS', denied_job_failed_once=True, other_job_ran_next=True, other_job_done_by_server=len(ticks) + 1)

    def limit_required():
        key = uuid.uuid4()
        staged.checked(staged.request(cur, today, key), key, 'RUNNING')
        b.api.admin(cur)
        before = (staged.job_row(cur, key)['units_done'], runner_row(cur))
        details = {}
        for timeout in ('0', '9s', '1h'):
            details[timeout] = refused(cur, lambda timeout=timeout: tick(cur, timeout), 'CP7_RUNNER_STATEMENT_LIMIT_REQUIRED')
            assert (staged.job_row(cur, key)['units_done'], runner_row(cur)) == before, 'K4R_REFUSED_TICK_CHANGED_SOMETHING'
        ran = tick(cur, '8s')
        assert ran['outcome'] == 'UNIT_STORED' and staged.job_row(cur, key)['units_done'] == before[0] + 1, ran
        stricter = tick(cur, '5s')
        assert stricter['outcome'] in ('UNIT_STORED', 'JOB_DONE'), stricter
        return dict(status='PASS', refused_without_limit=details, ran_at_8s=True, stricter_limit_allowed=True,
                    statement_limit_never_raised=True)

    def schedule_private():
        b.api.admin(cur)
        defs = cur.execute('select cp7_ops.schedules()').fetchone()[0]
        mine = [d for d in defs if d['name'] == RUNNER['name']]
        assert mine == [RUNNER], mine
        assert mine[0]['command'].count('select cp7_ops.analysis_tick()') == 60 == mine[0]['command'].count('begin;') == mine[0]['command'].count('commit;')
        assert cur.execute("select has_function_privilege('postgres',%s,'EXECUTE')", (TICK,)).fetchone()[0]
        for who in ('anon', 'authenticated', 'service_role'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, TICK)).fetchone()[0], who
            assert not cur.execute("select has_table_privilege(%s,'cp7_analysis_stage.runner','SELECT,INSERT,UPDATE,DELETE')", (who,)).fetchone()[0], who
        for sig in PRIVATE:
            for who in ('anon', 'authenticated', 'service_role', 'postgres'):
                if who == 'postgres' and cur.execute("select rolsuper from pg_roles where rolname='postgres'").fetchone()[0]:
                    continue
                assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
        state, message, _ = refusal(cur, lambda: (staged.auth.actor(cur), cur.execute('select cp7_ops.analysis_tick()')))
        assert state == '42501', (state, message)
        assert cur.execute("select count(*)from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' "
                           "and(p.proname like '%tick%' or p.proname like '%run_next%' or p.proname like '%runner%')").fetchone()[0] == 0
        tick(cur)
        assert runner_row(cur) is not None
        refused(cur, lambda: cur.execute('delete from cp7_analysis_stage.runner'), 'CP7_RUN_IMMUTABLE')
        return dict(status='PASS', runner_definition=RUNNER['name'], sixty_ticks_each_own_transaction=True, tick_scheduler_role_only=True,
                    run_next_private=True, authenticated_refused=state, no_public_rpc=True, runner_row_never_deleted=True)

    def status_reports_runner():
        key = uuid.uuid4()
        staged.checked(staged.request(cur, today, key), key, 'RUNNING')
        b.api.admin(cur)
        cur.execute('alter table cp7_analysis_stage.runner disable trigger immutable_stage_runner')
        # SYNTHETIC (labelled): no runner yet in this transaction (the row is removed administratively, restored by the rollback).
        cur.execute('delete from cp7_analysis_stage.runner')
        cur.execute('alter table cp7_analysis_stage.runner enable trigger immutable_stage_runner')
        off = staged.status(cur, key)['server_runner']
        assert off == dict(active=False, last_tick_at=None), off
        tick(cur)
        on = staged.status(cur, key)['server_runner']
        row = runner_row(cur)
        assert on['active'] is True and datetime.fromisoformat(on['last_tick_at']) == datetime.fromisoformat(row['last_tick_at']), (on, row)
        assert row['statement_timeout_ms'] == 8000
        tick(cur)
        assert runner_row(cur)['last_tick_at'] == row['last_tick_at'], 'K4R_HEARTBEAT_WRITTEN_EVERY_TICK'
        # SYNTHETIC (labelled): the last tick moved 3 minutes back (administrative): the runner is no longer active.
        cur.execute("update cp7_analysis_stage.runner set last_tick_at=last_tick_at-interval'3 minutes'")
        stale = staged.status(cur, key)['server_runner']
        assert stale['active'] is False and stale['last_tick_at'] is not None, stale
        tick(cur)
        assert staged.status(cur, key)['server_runner']['active'] is True
        return dict(status='PASS', inactive_without_tick=True, active_after_tick=True, heartbeat_at_most_every_10s=True,
                    inactive_after_2_minutes=True, statement_limit_recorded_ms=row['statement_timeout_ms'])

    return list(zip(IDS['native'], (finishes_without_page, page_and_server, access_rechecked, denied_does_not_hold, limit_required,
                                    schedule_private, status_reports_runner)))


def races(tools, today):
    def requested(subject=None, workload=False):
        key = uuid.uuid4()
        with tools.connect() as conn, conn.cursor() as cur:
            f = load.real_workload(cur, today)[0] if workload else None
            role = None
            if subject == 'custom':
                subject, role = auth.custom_actor(cur)
            staged.checked(staged.request(cur, today, key, subject), key, 'RUNNING')
            conn.commit()
        return key, subject, role, f

    def server_tick(timeout='8s'):
        with tools.connect() as conn, conn.cursor() as cur:
            out = tick(cur, timeout)
            conn.commit()
            return out

    def state(key, subject=None):
        with tools.connect() as conn, conn.cursor() as cur:
            s = staged.checked(staged.status(cur, key, subject), key)
            conn.commit()
            return s

    def blocked_outputs():
        """A real lock that makes a unit's output INSERT wait (units read only the stored reference)."""
        holder = tools.connect()
        holder.execute('lock table cp7_analysis_stage.outputs in exclusive mode')
        return holder

    def page_and_server():
        key, *_ = requested()
        before = state(key)
        holder = blocked_outputs()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                ticking = pool.submit(server_tick)
                # The tick holds the job row while its unit waits on the lock; the page's step meanwhile runs nothing.
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    with tools.connect() as conn, conn.cursor() as cur:
                        held = cur.execute("""select count(*) from pg_locks l join pg_stat_activity a on a.pid=l.pid
                            where l.locktype='relation' and l.relation='cp7_analysis_stage.outputs'::regclass and not l.granted""").fetchone()[0]
                    if held:
                        break
                    time.sleep(0.1)
                assert held, 'K4R_TICK_NEVER_REACHED_THE_UNIT'
                with tools.connect() as conn, conn.cursor() as cur:
                    skipped = staged.checked(staged.step(cur, key), key)
                    conn.commit()
                holder.rollback()
                out = ticking.result(30)
        finally:
            holder.close()
        assert skipped['worker_active'] is True and skipped['units_done'] == before['units_done'], skipped
        assert out['outcome'] == 'UNIT_STORED' and out['units_done'] == before['units_done'] + 1, out
        # And the other way round: a page holding the job, the tick skips it (no other job) and runs nothing.
        holder = tools.connect()
        try:
            holder.execute('select 1 from cp7_analysis_stage.jobs where request_id=%s for update', (key,))
            idle = server_tick()
            holder.rollback()
        finally:
            holder.close()
        assert idle['outcome'] == 'IDLE' and state(key)['units_done'] == out['units_done'], idle
        with tools.connect() as conn, conn.cursor() as cur:
            done, _ = run_by_server(cur, key)
            conn.commit()
            staged.checked(done, key, 'DONE')
            units_once(cur, key)
        return dict(status='PASS', page_step_while_server_holds_runs_nothing=True, tick_while_page_holds_runs_nothing=True,
                    every_unit_stored_once=True)

    def two_ticks():
        key, *_ = requested()
        before = state(key)
        gate = threading.Barrier(2)

        def racing():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                out = tick(cur)
                conn.commit()
                return out
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [x.result(60) for x in [pool.submit(racing), pool.submit(racing)]]
        after = state(key)
        ran = [r for r in results if r['outcome'] != 'IDLE']
        assert after['units_done'] - before['units_done'] == len(ran) and len(ran) in (1, 2), (before, results, after)
        # Two jobs, two ticks at once: each tick takes a different job.
        k1, *_ = requested()
        k2, *_ = requested()
        with tools.connect() as conn, conn.cursor() as cur:
            j1, j2 = job_id(cur, k1), job_id(cur, k2)
            conn.commit()
        holder = blocked_outputs()
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = [pool.submit(server_tick), pool.submit(server_tick)]
                time.sleep(1.5)
                holder.rollback()
                pair = [x.result(60) for x in pending]
        finally:
            holder.close()
        jobs = [x.get('job_id') for x in pair if x['outcome'] != 'IDLE']
        assert len(jobs) == 2 and len(set(jobs)) == 2 and set(jobs) <= {job_id_of(key), j1, j2}, ('K4R_TWO_TICKS_ONE_JOB_TWICE', pair)
        with tools.connect() as conn, conn.cursor() as cur:
            for k in (key, k1, k2):
                done, _ = run_by_server_any(cur, k)
                staged.checked(done, k, 'DONE')
                units_once(cur, k)
            conn.commit()
        return dict(status='PASS', concurrent_ticks_never_run_one_unit_twice=True, results=[r['outcome'] for r in results],
                    two_jobs_two_ticks=[x['outcome'] for x in pair], every_unit_stored_once=True)

    def job_id_of(key):
        with tools.connect() as conn, conn.cursor() as cur:
            return job_id(cur, key)

    def run_by_server_any(cur, key):
        """Ticks until this job is terminal; ticks may serve other running jobs of the copy on the way."""
        last = staged.checked(staged.status(cur, key), key)
        n = 0
        while last['state'] == 'RUNNING':
            assert n < TICKS
            tick(cur)
            n += 1
            last = staged.checked(staged.status(cur, key), key)
        return last, n

    def limit_stops():
        key, *_ = requested()
        holder = blocked_outputs()
        try:
            stops = [server_tick('2s') for _ in range(2)]
            holder.rollback()
        finally:
            holder.close()
        assert [s['outcome'] for s in stops] == ['UNIT_RETRY', 'UNIT_RETRY'] and all(s['units_done'] == 0 for s in stops), stops
        s = state(key)
        assert s['state'] == 'RUNNING' and s['unit_attempts'] == 2 and s['units_done'] == 0, s
        go = server_tick()
        assert go['outcome'] == 'UNIT_STORED' and state(key)['unit_attempts'] == 0, go
        with tools.connect() as conn, conn.cursor() as cur:
            done, _ = run_by_server(cur, key)
            conn.commit()
            staged.checked(done, key, 'DONE')
            units_once(cur, key)
        # Three stops in a row fail the job, as for a page (the only running job, so every tick reaches it).
        key2, *_ = requested()
        holder = blocked_outputs()
        try:
            third = [server_tick('2s') for _ in range(3)]
            holder.rollback()
        finally:
            holder.close()
        assert [t['outcome'] for t in third] == ['UNIT_RETRY', 'UNIT_RETRY', 'JOB_FAILED'], third
        failed = state(key2)
        assert failed['state'] == 'FAILED' and failed['failure']['code'] == 'CP7_ANALYSIS_STAGE_STOPPED' and failed['failure']['sqlstate'] == '57014', failed
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert cur.execute('select count(*) from cp7_analysis_stage.outputs o join cp7_analysis_stage.jobs j on j.id=o.job_id '
                               'where j.request_id=%s', (key2,)).fetchone()[0] == 0, 'K4R_STOPPED_UNIT_STORED'
        return dict(status='PASS', stopped_unit_is_an_attempt=True, continues_after_release=True, three_stops_fail_job=failed['failure'],
                    nothing_partial_stored=True)

    def access_changed_during_unit():
        key, subject, role, _ = requested('custom')
        first = server_tick()
        assert first['outcome'] == 'UNIT_STORED', first
        holder = blocked_outputs()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                ticking = pool.submit(server_tick)
                deadline = time.monotonic() + 20
                waiting = 0
                while time.monotonic() < deadline and not waiting:
                    with tools.connect() as conn, conn.cursor() as cur:
                        waiting = cur.execute("""select count(*) from pg_locks l where l.locktype='relation'
                            and l.relation='cp7_analysis_stage.outputs'::regclass and not l.granted""").fetchone()[0]
                    time.sleep(0.1)
                assert waiting, 'K4R_TICK_NEVER_REACHED_THE_UNIT'
                # The actor's access changes while the unit runs.
                with tools.connect() as conn, conn.cursor() as cur:
                    cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')", (role,))
                    conn.commit()
                holder.rollback()
                out = ticking.result(30)
        finally:
            holder.close()
        assert out['outcome'] == 'ACCESS_CHANGED_DURING_UNIT' and out['ran'] is False and out['units_done'] == first['units_done'], out
        s = state(key, subject)
        assert s['state'] == 'RUNNING' and s['units_done'] == first['units_done'], 'K4R_UNIT_KEPT_ACROSS_ACCESS_CHANGE'
        failed = server_tick()
        assert failed['outcome'] == 'JOB_FAILED', failed
        s = state(key, subject)
        assert s['state'] == 'FAILED' and s['failure']['code'] == 'CP7_ANALYSIS_ACCESS_CHANGED', s
        return dict(status='PASS', unit_discarded_when_access_changed_during_it=True, next_tick_fails_job=s['failure'])

    def pg_cron_finishes():
        key, subject, _, f = requested(workload=True)
        u = urlparse(tools.admin)
        database = u.path.lstrip('/')
        cron_url = urlunparse(u._replace(path='/postgres'))
        with tools.connect() as conn, conn.cursor() as cur:
            defs = [d for d in schedule.definitions(cur) if d['name'] == RUNNER['name']]
            conn.commit()
        assert defs == [RUNNER], defs
        with psycopg.connect(cron_url, autocommit=True) as cron, cron.cursor() as cc:
            version = cc.execute("select extversion from pg_extension where extname='pg_cron'").fetchone()
            assert version, 'K4R_PG_CRON_NOT_AVAILABLE'
            seconds = tuple(int(x) for x in version[0].split('.')[:2]) >= (1, 5)
            # TEST_SCHEDULE_OVERRIDE (labelled): the runner fires every 5 seconds (or every minute) on this disposable copy only.
            fast = '5 seconds' if seconds else '* * * * *'
            since = cc.execute('select now()').fetchone()[0]
            ids = schedule.install(cc, database, 'postgres', defs, {RUNNER['name']: fast})
            try:
                deadline, s = time.monotonic() + 240, None
                while time.monotonic() < deadline:
                    s = state(key)
                    if s['state'] != 'RUNNING':
                        break
                    time.sleep(2)
                runs = schedule.runs(cc, ids[RUNNER['name']], since)
            finally:
                removed = schedule.uninstall(cc, database)
                quiet(cc, database)
                cc.execute('delete from cron.job_run_details where jobid=any(%s)', (list(ids.values()),))
            assert removed == [schedule.job_name(RUNNER['name'], database)] and schedule.installed(cc, database) == []
        assert s and s['state'] == 'DONE', ('K4R_PG_CRON_DID_NOT_FINISH', s)
        finished = [r for r in runs if r['status'] in ('succeeded', 'failed')]
        assert finished and all(r['status'] == 'succeeded' for r in finished), runs
        with tools.connect() as conn, conn.cursor() as cur:
            n = units_once(cur, key)
            same_as_single(cur, key, s)
            bridge.literal(cur, f, '175.00')
            conn.commit()
        return dict(status='PASS', pg_cron=version[0], test_schedule_override=fast, cron_runs=len(finished), units=n, no_page_call=True,
                    result_equals_single_on_same_reference=True, removed_after_test=removed)

    def quiet(cc, database):
        """Wait until pg_cron has no session left on the copy (a run finishing), so the copy can be dropped."""
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            cc.execute('select pg_stat_clear_snapshot()')
            if not cc.execute("select count(*) from pg_stat_activity where datname=%s and application_name='pg_cron'", (database,)).fetchone()[0]:
                return
            time.sleep(0.5)
        raise AssertionError('K4R_PG_CRON_SESSION_LEFT')

    return list(zip(IDS['races'], (page_and_server, two_ticks, limit_stops, access_changed_during_unit, pg_cron_finishes)))


def http_cases(http, today):
    def closed_page():
        owner = http.login('OWNER', 'k4r-owner')
        key = str(uuid.uuid4())
        args = dict(p_query=staged.query(today), p_request=key)
        first = owner.rpc('erp_cp7_request_staged_analysis_v1', args)
        assert first['status'] == 200 and first['body']['state'] == 'RUNNING' and first['body']['units_done'] == 0, first
        # The page is closed: no HTTP call until the server has finished the job.
        with http.connect() as conn, conn.cursor() as cur:
            done, n = run_by_server_quiet(cur, key, owner.auth_user_id)
            conn.commit()
        assert done['state'] == 'DONE', done
        again = owner.rpc('erp_cp7_request_staged_analysis_v1', args)
        got = owner.rpc('erp_cp7_get_staged_analysis_v1', dict(p_request=key))
        assert again['status'] == got['status'] == 200 and again['body']['run_id'] == got['body']['run_id'] == done['run_id'], (again, got)
        assert got['body']['state'] == 'DONE' and got['body']['units_done'] == got['body']['unit_count'] == n, got
        assert got['body']['server_runner']['active'] is True, got['body']['server_runner']
        ps = owner.rpc('erp_cp7_read_staged_analysis_pages_v1', dict(p_run=done['run_id']))
        assert ps['status'] == 200, ps['status']
        bodies = [owner.rpc('erp_cp7_read_staged_analysis_page_v1', dict(p_run=done['run_id'], p_index=i, p_access=ps['body']['access_epoch']))
                  for i in range(ps['body']['page_count'])]
        assert all(e['status'] == 200 and staged.sha(e['body']['body']) == e['body']['sha256'] for e in bodies)
        assert ps['body']['identity_hash'] == staged.sha(ps['body']['header']['sha256'] + '\n' + '\n'.join(e['body']['sha256'] for e in bodies))
        with http.connect() as conn, conn.cursor() as cur:
            assert staged.counts(cur, key)[:3] == (0, 0, 1)
            units_once(cur, key)
        return dict(status='PASS', real_Auth_request_then_server_only=True, units_by_server=n, reopened_same_job_and_run=True,
                    pages_hash_verified=len(bodies), server_runner_reported_active=True)

    def run_by_server_quiet(cur, key, subject):
        b.api.admin(cur)
        last = cur.execute('select state from cp7_analysis_stage.jobs where request_id=%s', (key,)).fetchone()[0]
        n = 0
        while last == 'RUNNING':
            assert n < TICKS
            tick(cur)
            n += 1
            last = cur.execute('select state from cp7_analysis_stage.jobs where request_id=%s', (key,)).fetchone()[0]
        return staged.checked(staged.status(cur, key, subject), key), n

    def not_reachable():
        owner = http.login('OWNER', 'k4r-owner-2')
        key = str(uuid.uuid4())
        first = owner.rpc('erp_cp7_request_staged_analysis_v1', dict(p_query=staged.query(today), p_request=key))
        assert first['status'] == 200 and first['body']['state'] == 'RUNNING', first
        refusals = {}
        for name in ('analysis_tick', 'run_next', 'erp_cp7_analysis_tick_v1'):
            x = owner.rpc(name, {})
            assert x['status'] >= 400, (name, x)
            refusals[name] = x['status']
            y = http.anon_rpc(name, {})
            assert y['status'] >= 400, (name, y)
        with http.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert cur.execute('select units_done from cp7_analysis_stage.jobs where request_id=%s', (key,)).fetchone()[0] == 0
        return dict(status='PASS', not_exposed=refusals, nothing_ran=True)

    return list(zip(IDS['http'], (closed_page, not_reachable)))
