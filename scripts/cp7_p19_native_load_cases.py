"""Complete public analysis calls under bounded real Native/real Auth load.

This selected six-case qualifier does not close P19 or assert factory capacity.
Fixture inputs, policies and work reviews stay explicitly synthetic; production,
sale, cash and inverse outcomes come only from the ordinary Native writers.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from time import monotonic
import hashlib
import json
import threading
import uuid

import cp7_analysis_cases as analysis
import cp7_analysis_finance_cases as financial
import cp7_p18_e01_bridge_cases as bridge

PROFILE_FACTSETS = (0, 1, 4, 12)
USERS = 4
READS_PER_USER = 4
CALENDAR_MARGIN_MINUTES = 60
IDS = dict(
    native=['P19_COMPLETE_CAPTURE_REAL_PROFILE', 'P19_COMPLETE_UUID_RECOVERY'],
    races=['P19_FOUR_ACTOR_CAPTURE', 'P19_CASH_WRITER_DURING_FOUR_READERS'],
    http=['P19_REAL_AUTH_FOUR_ACTOR_CAPTURE', 'P19_REAL_AUTH_ONE_ACTOR_REVOKED'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.p19.bounded-native-load.v1'


def witness(name, value):
    # Separate, complete stage evidence survives a later assertion failure.
    # Concurrent participants own separate files, never one shared log/JSON.
    root = Path(__file__).resolve().parents[1] / 'cp6-proof/t3'
    root.mkdir(parents=True, exist_ok=True)
    (root / ('P19_LOAD_' + name + '.json')).write_text(json.dumps(
        dict(contract=CONTRACT, stage_witness_only=True, Native_case_credit=0,
             independent_acceptance=False, production_go=False, observed=value),
        ensure_ascii=False, indent=2) + '\n')


def digest(raw):
    return hashlib.sha256(raw.encode('UTF8')).hexdigest()


def timings(values):
    ordered = sorted(values)
    assert ordered and all(value >= 0 for value in ordered)
    return dict(sample_count=len(values), milliseconds=values,
                p95_nearest_rank_ms=ordered[ceil(.95 * len(ordered)) - 1],
                maximum_ms=ordered[-1], factory_SLA_claim=False)


def unchanged(original, observed):
    # Current freshness is a separate property; a stale archive retains the
    # entire earlier operational and protected financial Original.
    assert observed['run_id'] == original['run_id']
    assert observed['analysis'] == original['analysis']
    assert observed['financial_source'] == original['financial_source']
    analysis.checked(observed)


def sql_capture(cur, today, request=None, subject=None):
    started = monotonic()
    # A failed call rolls back its own subtransaction before re-raising. Never
    # retry it or lose its original error while restoring the ordinary bound.
    with cur.connection.transaction():
        prior = cur.execute('show statement_timeout').fetchone()[0]
        cur.execute("set local statement_timeout='8s'")
        result = analysis.capture(cur, today, request, subject)
        cur.execute("select set_config('statement_timeout',%s,true)", (prior,))
    analysis.checked(result)
    return result, round((monotonic() - started) * 1000, 3)


def stored(cur, run):
    facts, body = cur.execute('select facts::text,result::text from cp7_analysis_native.runs where id=%s',
                              (run,)).fetchone()
    parsed = json.loads(facts)
    return dict(complete_facts_SQL_text=facts, complete_analysis_SQL_text=body,
                facts_utf8_bytes=len(facts.encode('UTF8')), facts_sha256=digest(facts),
                analysis_utf8_bytes=len(body.encode('UTF8')), analysis_sha256=digest(body),
                product_rows=len(parsed['facts']['products']),
                collection_rows={key: len(value) for key, value in parsed['facts'].items()
                                 if isinstance(value, list)})


def real_workload(cur, today, factsets=1):
    f, trace = bridge.prepare(cur, today)
    for _ in range(factsets):
        analysis.setup(cur, today)
    return f, trace


def reviewed_workload_calendar(cur, today):
    # The one-fixture helper declares a two-hour centre. Twelve45-minute jobs
    # cannot all fit there. Review sufficient synthetic capacity from every
    # declared remaining-work input; never fabricate an ETA or alter a result.
    source = analysis.previous.supply.capture(cur, today)
    revision = str(cur.execute('select coalesce(max(revision),0) from cp7_schedule_native.plans').fetchone()[0])
    proposal = analysis.schedule.payload(cur, source, revision)
    work_minutes = sum(int(step['remaining_minutes']) for position in proposal['config']['positions']
                       for step in position['remaining_steps'])
    assert work_minutes > 0
    capacity = max(120, work_minutes + CALENDAR_MARGIN_MINUTES)
    window = proposal['config']['windows'][0]
    start = datetime.fromisoformat(window['starts_at'].replace('Z', '+00:00'))
    end = start + timedelta(minutes=capacity)
    window['ends_at'] = analysis.schedule.stamp(end)
    proposal['config']['through_at'] = analysis.schedule.stamp(end + timedelta(hours=1))
    proposal['reason'] = 'P19 synthetic reviewed complete work minutes plus60 margin; no factory calendar default'
    result = analysis.schedule.save(cur, proposal)
    return dict(reviewed_position_count=len(proposal['config']['positions']),
                selected_total_work_minutes=work_minutes, reviewed_capacity_minutes=capacity,
                margin_minutes=CALENDAR_MARGIN_MINUTES, proposal=proposal, result=result)


def cases(cur, today):
    def profile():
        f, trace = bridge.prepare(cur, today)
        prepared = 0
        observations = []
        for count in PROFILE_FACTSETS:
            while prepared < count:
                _, root, _, _ = analysis.setup(cur, today)
                prepared += 1
            before = analysis.b.boundary.snapshot(cur)
            old_count = cur.execute('select count(*) from cp7_analysis_native.runs').fetchone()[0]
            counter = None
            if count == PROFILE_FACTSETS[-1]:
                # Retain the overloaded input and require honest missing ETAs.
                # The happy path then uses an explicit, sufficient review.
                limited, limited_elapsed = sql_capture(cur, today)
                uncertain = [source for source in limited['analysis']['sources']
                             if source['eta'] is None and source['eta_basis'] == 'UNKNOWN']
                assert uncertain and all(source['physical_remaining']['value'] == '8' for source in uncertain)
                assert all(source['eligible_projected']['value'] == '7' for source in uncertain)
                counter = dict(original=limited, stored=stored(cur, limited['run_id']),
                               elapsed_ms=limited_elapsed, insufficient_work_window_minutes=120,
                               missing_ETA_not_invented=True)
                witness('UNDERPROVISIONED_' + str(count), counter)
            review = reviewed_workload_calendar(cur, today) if count else None
            result, elapsed = sql_capture(cur, today)
            retained = stored(cur, result['run_id'])
            witness('PROFILE_' + str(count), dict(actual_Native_factsets=count,
                    complete_public_capture_ms=elapsed, original=result, stored=retained))
            if count:
                selected = analysis.recommendation(result['analysis'], root)
                assert selected['q_base']['value'] == '93'
            reread = analysis.read(cur, result['run_id'])
            unchanged(result, reread)
            assert stored(cur, result['run_id']) == retained
            assert cur.execute('select count(*) from cp7_analysis_native.runs').fetchone()[0] == old_count + 1 + (1 if counter else 0)
            assert analysis.b.boundary.snapshot(cur) == before
            bridge.literal(cur, f, '175.00')
            observations.append(dict(actual_Native_factsets=count, actual_E01_journeys=1,
                                     complete_public_capture_ms=elapsed, original=result, stored=retained,
                                     explicit_workload_calendar=review, underprovisioned_counter=counter))
        return dict(status='PASS', profile_factsets=list(PROFILE_FACTSETS),
                    complete_public_capture_and_read_all_profiles=True,
                    fixed_E01_FG45_value675_HPP15_AR175_cash200_payroll180=True,
                    complete_stored_Originals=observations, Native_business_unchanged=True,
                    statement_timeout='8s', full_P19_acceptance=False,
                    production_checkpoints=trace['checkpoints'])

    def recovery():
        f, _ = real_workload(cur, today)
        request = uuid.uuid4()
        before = analysis.b.boundary.snapshot(cur)
        first, elapsed = sql_capture(cur, today, request)
        original = stored(cur, first['run_id'])
        recovered, replay_elapsed = sql_capture(cur, today, request)
        unchanged(first, recovered)
        unchanged(first, analysis.read(cur, first['run_id']))
        assert stored(cur, first['run_id']) == original
        assert cur.execute('select count(*) from cp7_analysis_native.runs where request_id=%s',
                           (request,)).fetchone()[0] == 1
        q = analysis.previous.baseline.history.query(today)
        q['group_mode'] = 'RESTATED'
        analysis.auth.refused(cur, lambda: analysis.capture(cur, today, request, q=q),
                             'CP7_ANALYSIS_REQUEST_CHANGED')
        assert analysis.b.boundary.snapshot(cur) == before
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', first_complete_public_capture_ms=elapsed,
                    exact_same_UUID_recovery_ms=replay_elapsed, original=first, stored=original,
                    one_saved_Original=True, changed_query_refused=True, Native_business_unchanged=True)

    return list(zip(IDS['native'], (profile, recovery)))


def races(tools, today):
    def actors(cur):
        return [financial.admin_actor(cur, analysis)[0] for _ in range(USERS)]

    def simultaneous():
        request = uuid.uuid4()
        with tools.connect() as conn, conn.cursor() as cur:
            f, _ = real_workload(cur, today)
            subjects = actors(cur)
            before = analysis.b.boundary.snapshot(cur)
            conn.commit()
        gate = threading.Barrier(USERS)
        def send(index, subject):
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                result, elapsed = sql_capture(cur, today, request, subject)
                conn.commit()
                witness('SQL_CAPTURE_' + str(index), dict(original=result, elapsed_ms=elapsed))
                return result, elapsed
        with ThreadPoolExecutor(max_workers=USERS) as pool:
            pending = [pool.submit(send, index, subject) for index, subject in enumerate(subjects)]
            observed = [future.result(40) for future in pending]
        assert len({result['run_id'] for result, _ in observed}) == USERS
        with tools.connect() as conn, conn.cursor() as cur:
            for subject, (result, _) in zip(subjects, observed):
                assert result['analysis']['scope']['actor_scope_id'] == subject
                recovered, _ = sql_capture(cur, today, request, subject)
                unchanged(result, recovered)
            assert cur.execute('select count(*) from cp7_analysis_native.runs where request_id=%s',
                               (request,)).fetchone()[0] == USERS
            assert analysis.b.boundary.snapshot(cur) == before
            bridge.literal(cur, f, '175.00')
            conn.commit()
        return dict(status='PASS', concurrent_actor_count=USERS, same_UUID_different_actor_Originals=USERS,
                    all_complete_public_results_actor_bound=True, one_original_per_actor=True,
                    capture_timings=timings([elapsed for _, elapsed in observed]),
                    full_Originals=[result for result, _ in observed], Native_business_unchanged=True)

    def writer():
        with tools.connect() as conn, conn.cursor() as cur:
            f, trace = real_workload(cur, today)
            subjects = actors(cur)
            saved = [sql_capture(cur, today, subject=subject)[0] for subject in subjects]
            conn.commit()
        gate = threading.Barrier(USERS + 1)
        windows = []
        def read(index):
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                started = monotonic()
                samples = []
                states = []
                for _ in range(READS_PER_USER):
                    with conn.transaction():
                        cur.execute("set local statement_timeout='8s'")
                        at = monotonic()
                        result = analysis.read(cur, saved[index]['run_id'], subjects[index])
                        samples.append(round((monotonic() - at) * 1000, 3))
                        unchanged(saved[index], result)
                        states.append(result['source_state'])
                conn.commit()
                return dict(samples=samples, states=states, started=started, ended=monotonic())
        def inverse():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                started = monotonic()
                cur.execute("set local statement_timeout='8s'")
                result = bridge.inverse(cur, f)
                conn.commit()
                return dict(result=result, started=started, ended=monotonic())
        with ThreadPoolExecutor(max_workers=USERS + 1) as pool:
            readers = [pool.submit(read, index) for index in range(USERS)]
            command = pool.submit(inverse)
            observed = [future.result(45) for future in readers]
            written = command.result(45)
        # The first reads and real writer overlap. A scheduler that completes
        # an entire operation before starting the others is not this witness.
        windows = observed + [written]
        witness('WRITER_AND_READERS', dict(readers=observed, writer=written, complete_Originals=saved))
        assert max(row['started'] for row in windows) < min(row['ended'] for row in windows), 'P19_REQUIRED_ACTUAL_OVERLAP'
        with tools.connect() as conn, conn.cursor() as cur:
            bridge.literal(cur, f, '375.00')
            for subject, original in zip(subjects, saved):
                archived = analysis.read(cur, original['run_id'], subject)
                unchanged(original, archived)
                assert archived['source_state'] == 'ARCHIVED_STALE'
            fresh, _ = sql_capture(cur, today)
            assert fresh['financial_source']['book_signature'] != saved[0]['financial_source']['book_signature']
            conn.commit()
        return dict(status='PASS', real_Native_cash_inverse_during_four_readers=True,
                    real_operation_intervals=windows, reader_timings=timings([v for row in observed for v in row['samples']]),
                    writer_commit_ms=round((written['ended'] - written['started']) * 1000, 3),
                    original_body_and_money_immutable=True, current_AR175_to375_FG45_HPP15=True,
                    Native_command_not_retried=True, statement_timeout='8s', source_trace=trace['checkpoints'])

    return list(zip(IDS['races'], (simultaneous, writer)))


def http_cases(http, today):
    state = {}
    def complete():
        users = [http.login('OWNER', 'p19-load-' + str(index)) for index in range(USERS)]
        with http.connect() as conn, conn.cursor() as cur:
            f, _ = real_workload(cur, today, factsets=4)
            before = analysis.b.boundary.snapshot(cur)
            conn.commit()
        request = str(uuid.uuid4())
        args = dict(p_query=analysis.previous.baseline.history.query(today), p_request=request)
        gate = threading.Barrier(USERS)
        def send(index, user):
            gate.wait(timeout=8)
            start = monotonic()
            result = user.rpc('erp_cp7_capture_analysis_v1', args)
            elapsed = round((monotonic() - start) * 1000, 3)
            witness('HTTP_CAPTURE_' + str(index), dict(response=result, elapsed_ms=elapsed,
                    actor=user.auth_user_id, request=request))
            assert result['status'] == 200, ('P19_ACTUAL_HTTP_CAPTURE', result)
            analysis.checked(result['body'])
            return result['body'], elapsed
        with ThreadPoolExecutor(max_workers=USERS) as pool:
            pending = [pool.submit(send, index, user) for index, user in enumerate(users)]
            observed = [future.result(45) for future in pending]
        bodies = [body for body, _ in observed]
        assert len({body['run_id'] for body in bodies}) == USERS
        for index, user in enumerate(users):
            assert bodies[index]['analysis']['scope']['actor_scope_id'] == user.auth_user_id
            recovered = user.rpc('erp_cp7_capture_analysis_v1', args)
            assert recovered['status'] == 200, recovered
            unchanged(bodies[index], recovered['body'])
            foreign = user.rpc('erp_cp7_read_analysis_v1', dict(p_run=bodies[(index + 1) % USERS]['run_id']))
            assert foreign['status'] == 403, foreign
        assert http.anon_rpc('erp_cp7_read_analysis_v1', dict(p_run=bodies[0]['run_id']))['status'] in (401, 403)
        with http.connect() as conn, conn.cursor() as cur:
            assert cur.execute('select count(*) from cp7_analysis_native.runs where request_id=%s',
                               (request,)).fetchone()[0] == USERS
            assert analysis.b.boundary.snapshot(cur) == before
            bridge.literal(cur, f, '175.00')
        state.update(users=users, bodies=bodies, args=args, fixture=f)
        return dict(status='PASS', real_Auth_signed_in_users=USERS, distinct_same_UUID_actor_Originals=USERS,
                    actual_HTTP_capture_timings=timings([elapsed for _, elapsed in observed]),
                    complete_native_Originals=bodies, exact_same_UUID_recovery=True,
                    every_foreign_actor_and_anonymous_read_denied=True, Native_business_unchanged=True)

    def revoked():
        assert state, 'P19_REQUIRED_PRIOR_COMPLETE_HTTP_CASE'
        users, bodies, args = (state[key] for key in ('users', 'bodies', 'args'))
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (users[0].auth_user_id,))
            before = analysis.b.boundary.snapshot(cur)
            conn.commit()
        for name, payload in (('erp_cp7_capture_analysis_v1', args),
                              ('erp_cp7_read_analysis_v1', dict(p_run=bodies[0]['run_id']))):
            result = users[0].rpc(name, payload)
            assert result['status'] == 403, result
        for user, body in zip(users[1:], bodies[1:]):
            current = user.rpc('erp_cp7_read_analysis_v1', dict(p_run=body['run_id']))
            assert current['status'] == 200, current
            unchanged(body, current['body'])
            replay = user.rpc('erp_cp7_capture_analysis_v1', args)
            assert replay['status'] == 200, replay
            unchanged(body, replay['body'])
        with http.connect() as conn, conn.cursor() as cur:
            assert analysis.b.boundary.snapshot(cur) == before
            assert cur.execute('select count(*) from cp7_analysis_native.runs where request_id=%s',
                               (args['p_request'],)).fetchone()[0] == USERS
            bridge.literal(cur, state['fixture'], '175.00')
        return dict(status='PASS', one_actor_revoked_before_cached_request_and_archive=True,
                    other_three_actual_Auth_users_still_read_and_recover_own_complete_Originals=True,
                    no_new_capture_or_Native_effect=True)

    return list(zip(IDS['http'], (complete, revoked)))
