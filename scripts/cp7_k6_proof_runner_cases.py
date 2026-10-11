"""K6: the PL-8 exhaustion proofs are made by the server (owner decision 8 Oct 2026, 8).

Owner: "arahkan penjalan bukti otomatis di server. Bukti harus diperiksa terhadap versi sumber dan tidak boleh tetap
dianggap berlaku setelah koreksi atau pembatalan."

The runner is cp7_ops.proof_tick (pg_cron every 10 minutes, 20 ticks, each in its own transaction under the 8 s
statement limit) -> cp7_proof_runner.prove_next: one window of the posted cutting history (by id, at the pass clock)
through the unchanged PL-8 prover cp7_supply_native.prove_exhausted; a pass ends at the last group and the runner rests
an hour. Proved here: a pass proves exactly the finished groups and a capture then finds them proven (it stores none
again); a cancellation and a backdated correction make the old proof unmatched (the group drops out of the history
yield) and only a later pass proves the group again at its new facts, the old proof row kept; nothing runs without the
8 s limit; the schedule entry and the runner are private; a second tick never waits for the first (BUSY at once, also on
a fresh installation); a window stopped by the limit stores nothing, shrinks, and after three stops at 50 groups is
skipped and recorded, the pass going on past it; a capture during a window gets the same result; real pg_cron finishes
a pass; nothing of it is reachable over real Auth/PostgREST and the public capture uses the runner's proofs.
SYNTHETIC steps are labelled where they are used: administrative clones of a finished group (PL-8 suite helper) and the
rest between passes shortened on the disposable copy (TEST_REST_OVERRIDE).
"""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlunparse
import json
import time
import uuid

import psycopg

import cp7_pl5_history_yield_cases as pl5
import cp7_schedule as schedule

IDS = dict(
    native=['K6P_PASS_PROVES_FINISHED_HISTORY', 'K6P_CANCEL_CORRECT_BACKDATE_REPROVEN_BY_SERVER', 'K6P_LIMIT_REQUIRED',
            'K6P_SCHEDULE_DEFINED_PRIVATE'],
    races=['K6P_RACE_SECOND_TICK_NEVER_WAITS', 'K6P_RACE_WINDOW_STOPPED_THEN_SKIPPED', 'K6P_RACE_CAPTURE_DURING_WINDOW',
           'K6P_RACE_PG_CRON_FINISHES_PASS'],
    http=['K6P_HTTP_TICK_NOT_REACHABLE', 'K6P_HTTP_CAPTURE_USES_SERVER_PROOFS'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.k6.proof-runner.v1'
FUNCTIONS = ('erp_cp7_capture_production_supply_v1',)
RUNNER = dict(name='cp7-proof-runner', schedule='*/10 * * * *',
              command="set statement_timeout to '8s'; " + ' '.join(['begin; select cp7_ops.proof_tick(); commit;'] * 20),
              timezone='UTC', meaning='every 10 minutes: up to 20 proof windows, each in its own transaction under the 8 s limit')
TICK = 'cp7_ops.proof_tick()'
PRIVATE = ('cp7_proof_runner.prove_next()', 'cp7_proof_runner.status()')
OUTCOMES = ('WINDOW_PROVEN', 'PASS_DONE', 'WINDOW_STOPPED', 'WINDOW_SKIPPED', 'RESTING', 'BUSY', 'REFUSED')
# Driver bound only (ticks per pass); never an application limit.
TICKS = 500
b, supply, auth = pl5.b, pl5.supply, pl5.auth
refused, refusal = pl5.refused, pl5.refusal


def tick(cur, timeout='8s'):
    """One proof tick exactly as pg_cron runs it: the scheduler role postgres, under the given statement limit (restored after)."""
    b.api.admin(cur)
    prior = cur.execute('show statement_timeout').fetchone()[0]
    cur.execute("select set_config('statement_timeout',%s,true)", (timeout,))
    cur.execute('set local role postgres')
    out = cur.execute('select cp7_ops.proof_tick()').fetchone()[0]
    cur.execute('reset role')
    b.api.admin(cur)
    cur.execute("select set_config('statement_timeout',%s,true)", (prior,))
    assert out['tick'] == 'cp7-proof-runner' and out['outcome'] in OUTCOMES, out
    return out


def rest_over(cur):
    """TEST_REST_OVERRIDE (labelled, disposable copy only): the hour between passes is over now."""
    b.api.admin(cur)
    cur.execute("update cp7_proof_runner.state set rest_until=clock_timestamp()-interval'1 second' where id and rest_until is not null")


def run_pass(cur):
    """Ticks until the current pass is done (a resting runner first gets its rest shortened); returns the ticks."""
    outs = []
    first = tick(cur)
    if first['outcome'] == 'RESTING':
        rest_over(cur)
        first = tick(cur)
    outs.append(first)
    while outs[-1]['outcome'] != 'PASS_DONE':
        assert len(outs) < TICKS, ('K6P_DRIVER_BOUND', outs[-3:])
        assert outs[-1]['outcome'] == 'WINDOW_PROVEN', outs[-1]
        outs.append(tick(cur))
    return outs


def state(cur):
    b.api.admin(cur)
    return cur.execute('select cp7_proof_runner.status()').fetchone()[0]


def proof_rows(cur, groups):
    b.api.admin(cur)
    return cur.execute("""select group_id::text,id::text,facts_hash from cp7_supply_native.exhaustion_proofs
        where group_id=any(%s::uuid[]) order by group_id,captured_at,id""", (groups,)).fetchall()


def finished(cur, today, label, n=5):
    """n ordinary finished groups (PL-5 production: cut, pickup, sewing, laundry, final SKU, BS scrapped) of a new product."""
    p = pl5.product(cur, label)
    make = pl5.Production(cur, today)
    made = [make.group(p, 40, 37) for _ in range(n)]
    return p, make, made


def open_group(cur, today):
    """A posted cutting group still in work (cut only)."""
    production = pl5.planv2.previous.production
    c = production.cut.fixture(cur, today)
    b.api.admin(cur)
    return str(c['group'])


def cases(cur, today):
    def pass_proves_history():
        p, _, made = finished(cur, today, 'k6-pass')
        groups = [g['group'] for g in made]
        work = open_group(cur, today)
        assert proof_rows(cur, groups + [work]) == []
        outs = run_pass(cur)
        rows = proof_rows(cur, groups + [work])
        assert sorted(r[0] for r in rows) == sorted(groups), rows
        s = state(cur)
        assert s['state']['scanned'] >= len(groups) + 1 and s['state']['rest_until'] and s['passes'][0]['pass'] == s['state']['pass'], s
        # A capture now finds the server's proofs: it lists the groups exhausted, the open group in work, and stores none again.
        n = cur.execute('select count(*) from cp7_supply_native.exhaustion_proofs').fetchone()[0]
        c = supply.capture(cur, today)
        b.api.admin(cur)
        listed = set(c['production_scope']['exhausted_cutting_groups'])
        assert set(groups) <= listed and work not in listed and work in c['production_scope']['cutting_groups'], c['production_scope']
        assert cur.execute('select count(*) from cp7_supply_native.exhaustion_proofs').fetchone()[0] == n
        # And the history yield counts them through the server's proofs.
        owner = pl5.actor(cur)
        pl5.save(cur, pl5.payload(), owner)
        h, _ = pl5.history(cur, p['target'], p['model'], owner)
        pl5.available(h, 'PRODUCT_SIZE', 5, 200, 185)
        assert sorted(x['proof_id'] for x in h['proofs']) == sorted(r[1] for r in rows), (h['proofs'], rows)
        return dict(status='PASS', ticks=len(outs), finished_groups_proven=len(groups), open_group_unproven=True,
                    capture_reuses_server_proofs=True, capture_added_proofs=0, history_yield_counts_server_proofs=True)

    def cancel_correct_backdate():
        owner = pl5.actor(cur)
        p, make, made = finished(cur, today, 'k6-redo')
        groups = [g['group'] for g in made]
        run_pass(cur)
        pl5.save(cur, pl5.payload(), owner)
        h, _ = pl5.history(cur, p['target'], p['model'], owner)
        pl5.available(h, 'PRODUCT_SIZE', 5, 200, 185)
        old = next(x for x in h['proofs'] if x['group_id'] == groups[0])
        rows_before = proof_rows(cur, groups)
        # Cancellation: the scrap of one group is reversed through the ordinary command. The old proof row stays,
        # unmatched; the group is out of the history at once, before any runner pass.
        g0 = made[0]
        b.chain.bs_action(cur, 'REVERSE_DISPOSITION', dict(resolution_id=g0['resolution'], change_reason='K6P scrap reversed'),
                          b.chain.version(cur, 'bs_cases', g0['case']))
        b.api.admin(cur)
        h, _ = pl5.history(cur, p['target'], p['model'], owner)
        assert h['status'] == 'INSUFFICIENT_SAMPLE' and h['excluded']['stale_or_unverifiable'] == '1', h
        assert proof_rows(cur, groups) == rows_before
        # A server pass now: the cancelled group is not exhausted, so nothing new is proven for it.
        run_pass(cur)
        assert proof_rows(cur, groups) == rows_before
        h, _ = pl5.history(cur, p['target'], p['model'], owner)
        assert h['status'] == 'INSUFFICIENT_SAMPLE' and h['excluded']['stale_or_unverifiable'] == '1', h
        # Correction, backdated: scrapped again at an earlier physical time than the first scrap. Still out until proven.
        make.scrap(g0, pl5.az.chain.production.at(g0['day'], 13, 30))
        h, _ = pl5.history(cur, p['target'], p['model'], owner)
        assert h['status'] == 'INSUFFICIENT_SAMPLE' and h['excluded']['stale_or_unverifiable'] == '1', h
        # The next server pass proves it again at the new facts; it counts with its new proof, the old row kept.
        run_pass(cur)
        rows_after = proof_rows(cur, groups)
        mine = [r for r in rows_after if r[0] == groups[0]]
        assert len(mine) == 2 and mine[0][1] == old['proof_id'] and mine[1][2] != mine[0][2], mine
        assert [r for r in rows_after if r[0] != groups[0]] == [r for r in rows_before if r[0] != groups[0]]
        h, _ = pl5.history(cur, p['target'], p['model'], owner)
        pl5.available(h, 'PRODUCT_SIZE', 5, 200, 185)
        new = next(x for x in h['proofs'] if x['group_id'] == groups[0])
        assert new['proof_id'] == mine[1][1] != old['proof_id'], (old, new)
        return dict(status='PASS', reversed_scrap_drops_group_before_any_pass=True, pass_after_cancel_proves_nothing=True,
                    backdated_rescrap_out_until_next_pass=True, reproven_by_server_with_new_hash=True, old_proof_row_kept=True,
                    other_groups_unchanged=True)

    def limit_required():
        b.api.admin(cur)
        before = cur.execute('select count(*) from cp7_proof_runner.state').fetchone()[0]
        details = {}
        for bad in ('0', '9s', '1h'):
            state_code, message, detail = refusal(cur, lambda bad=bad: tick(cur, bad))
            assert (state_code, message) == ('55000', 'CP7_RUNNER_STATEMENT_LIMIT_REQUIRED'), (bad, state_code, message)
            details[bad] = detail
        b.api.admin(cur)
        assert cur.execute('select count(*) from cp7_proof_runner.state').fetchone()[0] == before
        stricter = tick(cur, '3s')
        assert stricter['outcome'] in ('WINDOW_PROVEN', 'PASS_DONE', 'RESTING'), stricter
        assert state(cur)['state']['statement_timeout_ms'] == 3000
        return dict(status='PASS', refused_without_limit=details, nothing_read_or_written_when_refused=True, stricter_limit_allowed=True,
                    statement_limit_never_raised=True)

    def schedule_private():
        b.api.admin(cur)
        defs = cur.execute('select cp7_ops.schedules()').fetchone()[0]
        mine = [d for d in defs if d['name'] == RUNNER['name']]
        assert mine == [RUNNER], mine
        assert mine[0]['command'].count('select cp7_ops.proof_tick()') == 20 == mine[0]['command'].count('begin;') == mine[0]['command'].count('commit;')
        assert cur.execute("select has_function_privilege('postgres',%s,'EXECUTE')", (TICK,)).fetchone()[0]
        for who in ('anon', 'authenticated', 'service_role'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, TICK)).fetchone()[0], who
            assert not cur.execute("select has_schema_privilege(%s,'cp7_proof_runner','USAGE')", (who,)).fetchone()[0], who
            for table in ('cp7_proof_runner.state', 'cp7_proof_runner.passes', 'cp7_supply_native.exhaustion_proofs'):
                assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')", (who, table)).fetchone()[0], (who, table)
        for sig in PRIVATE:
            for who in ('anon', 'authenticated', 'service_role', 'postgres'):
                if who == 'postgres' and cur.execute("select rolsuper from pg_roles where rolname='postgres'").fetchone()[0]:
                    continue
                assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
        state_code, _, _ = refusal(cur, lambda: (cur.execute("select set_config('statement_timeout','8s',true)"),
                                                 cur.execute('set local role authenticated'), cur.execute('select cp7_ops.proof_tick()')))
        assert state_code == '42501', state_code
        b.api.admin(cur)
        tick(cur)
        refused(cur, lambda: cur.execute('delete from cp7_proof_runner.state'), 'CP7_RUN_IMMUTABLE')
        run_pass(cur)
        refused(cur, lambda: cur.execute('update cp7_proof_runner.passes set scanned=scanned+1'), 'CP7_RUN_IMMUTABLE')
        refused(cur, lambda: cur.execute('delete from cp7_proof_runner.passes'), 'CP7_RUN_IMMUTABLE')
        assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like '%proof%'").fetchone()[0] == 0
        return dict(status='PASS', runner_definition=RUNNER['name'], twenty_ticks_each_own_transaction=True, tick_scheduler_role_only=True,
                    runner_private=True, authenticated_refused='42501', state_row_never_deleted=True, finished_passes_immutable=True, no_public_rpc=True)

    return list(zip(IDS['native'], (pass_proves_history, cancel_correct_backdate, limit_required, schedule_private)))


def races(tools, today):
    def committed(op):
        with tools.connect() as conn, conn.cursor() as cur:
            out = op(cur)
            conn.commit()
            return out

    def spent_history(n):
        """One real finished group and n SYNTHETIC administrative clones of it (the PL-8 suite helper), committed."""
        def make(cur):
            production = pl5.planv2.previous.production
            s = production.ax.stocked_product(cur, today)
            b.api.admin(cur)
            clones = supply.clone_groups(cur, s['group'], n, 'K6P SYNTHETIC spent cutting history')
            return [str(s['group'])] + [str(x) for x in clones]
        return committed(make)

    def server_tick(timeout='8s'):
        return committed(lambda cur: tick(cur, timeout))

    def blocked_proofs():
        """A real lock that makes every window wait on the proof table (its reuse read and its insert)."""
        holder = tools.connect()
        holder.execute('lock table cp7_supply_native.exhaustion_proofs in access exclusive mode')
        return holder

    def wait_for_lock(relation):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            with tools.connect() as conn, conn.cursor() as cur:
                if cur.execute("select count(*) from pg_locks where locktype='relation' and relation=%s::regclass and not granted",
                               (relation,)).fetchone()[0]:
                    return True
            time.sleep(0.1)
        return False

    def runner_rows(cur):
        b.api.admin(cur)
        return cur.execute('select count(*) from cp7_proof_runner.state').fetchone()[0]

    def second_never_waits():
        groups = spent_history(60)
        results = {}
        for label, fresh in (('cold', True), ('warm', False)):
            if fresh:
                assert committed(runner_rows) == 0
            else:
                committed(rest_over)
            holder = blocked_proofs()
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    first = pool.submit(server_tick)
                    assert wait_for_lock('cp7_supply_native.exhaustion_proofs'), 'K6P_FIRST_TICK_NEVER_REACHED_ITS_WINDOW'
                    started = time.monotonic()
                    second = server_tick()
                    waited = time.monotonic() - started
                    holder.rollback()
                    out = first.result(30)
            finally:
                holder.close()
            assert second['outcome'] == 'BUSY' and second['ran'] is False and waited < 1.5, (label, second, waited)
            assert out['outcome'] in ('WINDOW_PROVEN', 'PASS_DONE'), (label, out)
            results[label] = dict(second='BUSY', second_waited_s=round(waited, 3), first=out['outcome'])
        proven = committed(lambda cur: proof_rows(cur, groups))
        assert sorted({r[0] for r in proven}) == sorted(groups), len(proven)
        return dict(status='PASS', cold_start=results['cold'], warm=results['warm'], no_tick_waited_on_another=True, groups_proven=len(groups))

    def window_stopped_then_skipped():
        groups = sorted(spent_history(120), key=uuid.UUID)
        outs = []
        holder = blocked_proofs()
        try:
            for _ in range(5):
                outs.append(server_tick('1s'))
        finally:
            holder.rollback()
            holder.close()
        assert [o['outcome'] for o in outs] == ['WINDOW_STOPPED'] * 4 + ['WINDOW_SKIPPED'], outs
        assert [o['window_size'] for o in outs] == [100, 50, 50, 50, 50], outs
        assert all(o['stop']['code'] == 'CP7_PROOF_WINDOW_STOPPED' and o['stop']['sqlstate'] == '57014' for o in outs), outs
        assert committed(lambda cur: proof_rows(cur, groups)) == [], 'K6P_STOPPED_WINDOW_STORED_SOMETHING'
        s = committed(state)
        skipped = s['state']['skipped']
        assert len(skipped) == 1 and skipped[0]['groups'] <= 50 and skipped[0]['code'] == 'CP7_PROOF_WINDOW_STOPPED', skipped
        # Released: the pass goes on past the skipped window and ends; those groups stay unproven in this pass.
        with tools.connect() as conn, conn.cursor() as cur:
            rest = run_pass(cur)
            conn.commit()
        s = committed(state)
        first, last = uuid.UUID(skipped[0]['first']), uuid.UUID(skipped[0]['last'])
        inside = [g for g in groups if first <= uuid.UUID(g) <= last]
        proven = {r[0] for r in committed(lambda cur: proof_rows(cur, groups))}
        assert proven == set(groups) - set(inside), (len(proven), len(inside))
        assert s['passes'][0]['skipped'] == skipped, s['passes'][0]
        # The next pass proves the skipped groups too.
        with tools.connect() as conn, conn.cursor() as cur:
            run_pass(cur)
            conn.commit()
        assert {r[0] for r in committed(lambda cur: proof_rows(cur, groups))} == set(groups)
        return dict(status='PASS', stops_shrink_window=[200, 100, 50], three_stops_at_50_skip=True, nothing_partial_stored=True,
                    skipped_recorded_in_pass=True, pass_went_on=len(rest), next_pass_proves_skipped=len(inside))

    def scope(c):
        return dict(cutting=c['production_scope']['cutting_groups'], exhausted=c['production_scope']['exhausted_cutting_groups'],
                    positions=c['wip']['positions'], totals=c['wip']['totals'])

    def capture_during_window():
        groups = spent_history(80)
        assert committed(lambda cur: proof_rows(cur, groups)) == []
        holder = blocked_proofs()
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                ticking = pool.submit(server_tick)
                assert wait_for_lock('cp7_supply_native.exhaustion_proofs'), 'K6P_TICK_NEVER_REACHED_ITS_WINDOW'
                capturing = pool.submit(lambda: committed(lambda cur: supply.capture(cur, today)))
                time.sleep(0.5)
                holder.rollback()
                out, got = ticking.result(30), capturing.result(60)
        finally:
            holder.close()
        assert out['outcome'] in ('WINDOW_PROVEN', 'PASS_DONE'), out
        # Both may have stored the same proof (no unique key, so neither waits); the capture's result is the same as a
        # capture made afterwards, and every group has one proof meaning.
        reference = committed(lambda cur: supply.capture(cur, today))
        assert scope(got) == scope(reference) and set(groups) <= set(got['production_scope']['exhausted_cutting_groups']), 'K6P_CAPTURE_CHANGED_BY_RUNNER'
        rows = committed(lambda cur: proof_rows(cur, groups))
        distinct = {(r[0], r[2]) for r in rows}
        assert {r[0] for r in rows} == set(groups) and len(distinct) == len(groups), (len(rows), len(distinct))
        return dict(status='PASS', capture_same_result=True, every_group_one_proof_meaning=True, duplicate_rows=len(rows) - len(distinct))

    def pg_cron_finishes():
        groups = spent_history(150)
        u = urlparse(tools.admin)
        database = u.path.lstrip('/')
        cron_url = urlunparse(u._replace(path='/postgres'))
        defs = committed(lambda cur: [d for d in schedule.definitions(cur) if d['name'] == RUNNER['name']])
        assert defs == [RUNNER], defs
        with psycopg.connect(cron_url, autocommit=True) as cron, cron.cursor() as cc:
            version = cc.execute("select extversion from pg_extension where extname='pg_cron'").fetchone()
            assert version, 'K6P_PG_CRON_NOT_AVAILABLE'
            seconds = tuple(int(x) for x in version[0].split('.')[:2]) >= (1, 5)
            # TEST_SCHEDULE_OVERRIDE (labelled): the runner fires every 5 seconds (or every minute) on this disposable copy only.
            fast = '5 seconds' if seconds else '* * * * *'
            since = cc.execute('select now()').fetchone()[0]
            ids = schedule.install(cc, database, 'postgres', defs, {RUNNER['name']: fast})
            try:
                deadline, s = time.monotonic() + 240, None
                while time.monotonic() < deadline:
                    s = committed(state)
                    if s['passes']:
                        break
                    time.sleep(2)
                runs = schedule.runs(cc, ids[RUNNER['name']], since)
            finally:
                removed = schedule.uninstall(cc, database)
                quiet(cc, database)
                cc.execute('delete from cron.job_run_details where jobid=any(%s)', (list(ids.values()),))
            assert removed == [schedule.job_name(RUNNER['name'], database)] and schedule.installed(cc, database) == []
        assert s and s['passes'], ('K6P_PG_CRON_DID_NOT_FINISH_A_PASS', s)
        finished_runs = [r for r in runs if r['status'] in ('succeeded', 'failed')]
        assert finished_runs and all(r['status'] == 'succeeded' for r in finished_runs), runs
        assert {r[0] for r in committed(lambda cur: proof_rows(cur, groups))} == set(groups)
        return dict(status='PASS', pg_cron=version[0], test_schedule_override=fast, cron_runs=len(finished_runs), pass_done=s['passes'][0]['pass'],
                    groups_proven=len(groups), removed_after_test=removed)

    def quiet(cc, database):
        """Wait until pg_cron has no session left on the copy (a run finishing), so the copy can be dropped."""
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            cc.execute('select pg_stat_clear_snapshot()')
            if not cc.execute("select count(*) from pg_stat_activity where datname=%s and application_name='pg_cron'", (database,)).fetchone()[0]:
                return
            time.sleep(0.5)
        raise AssertionError('K6P_PG_CRON_SESSION_LEFT')

    return list(zip(IDS['races'], (second_never_waits, window_stopped_then_skipped, capture_during_window, pg_cron_finishes)))


def http_cases(http, today):
    def not_reachable():
        owner = http.login('OWNER', 'k6p-owner')
        refusals = {}
        for name in ('proof_tick', 'prove_next', 'prove_exhausted', 'status', 'erp_cp7_proof_tick_v1'):
            x = owner.rpc(name, {})
            assert x['status'] >= 400, (name, x)
            refusals[name] = x['status']
            y = http.anon_rpc(name, {})
            assert y['status'] >= 400, (name, y)
        with http.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert cur.execute('select count(*) from cp7_proof_runner.state').fetchone()[0] == 0
        return dict(status='PASS', not_exposed=refusals, nothing_ran=True)

    def capture_uses_server_proofs():
        owner = http.login('OWNER', 'k6p-owner-2')
        with http.connect() as conn, conn.cursor() as cur:
            production = pl5.planv2.previous.production
            s = production.ax.stocked_product(cur, today)
            b.api.admin(cur)
            groups = [str(s['group'])] + [str(x) for x in supply.clone_groups(cur, s['group'], 40, 'K6P SYNTHETIC spent cutting history')]
            conn.commit()
            run_pass(cur)
            conn.commit()
            n = cur.execute('select count(*) from cp7_supply_native.exhaustion_proofs').fetchone()[0]
            conn.commit()
        query = supply.baseline.history.query(today)
        got = owner.rpc('erp_cp7_capture_production_supply_v1', dict(p_query=query, p_request=str(uuid.uuid4())))
        assert got['status'] == 200, got
        listed = set(got['body']['production_scope']['exhausted_cutting_groups'])
        assert set(groups) <= listed, len(listed)
        with http.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert cur.execute('select count(*) from cp7_supply_native.exhaustion_proofs').fetchone()[0] == n
        return dict(status='PASS', real_Auth_capture=True, exhausted_listed=len(groups), capture_added_proofs=0)

    return list(zip(IDS['http'], (not_reachable, capture_uses_server_proofs)))
