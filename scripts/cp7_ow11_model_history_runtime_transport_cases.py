"""Seven controls for real scoped-history races and Auth/PostgREST calls.

The repeated catalog anchor earns no additional Native credit. Each race uses
its own disposable database; no production or model-caller claim is made.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic, sleep
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import uuid
import psycopg
import cp7_ow11_model_history_runtime_cases as native

plan, stage, history = native.plan, native.stage, native.history
CONTRACT = 'cp7.ow11.model-history-runtime-transport.v1'
IDS = dict(native=[native.IDS['native'][0]], races=[
    'OW11_MODEL_HISTORY_RUNTIME_RACE_SAME_UUID',
    'OW11_MODEL_HISTORY_RUNTIME_RACE_ACCESS_AFTER_ENVELOPE',
    'OW11_MODEL_HISTORY_RUNTIME_RACE_REPLAY_ACCESS_AFTER_REQUEST',
    'OW11_MODEL_HISTORY_RUNTIME_RACE_POSTED_SOURCE_AFTER_ENVELOPE'], http=[
    'OW11_MODEL_HISTORY_RUNTIME_AUTH_CAPTURE_REPLAY_CURRENT_SOURCE',
    'OW11_MODEL_HISTORY_RUNTIME_AUTH_REVOKED_FOREIGN_ANONYMOUS'])
REQUIRED = {k: len(v) for k, v in IDS.items()}
EXPECTED = DECLARED = sum(REQUIRED.values())
assert EXPECTED == 7
FUNCTIONS, SCHEDULES = native.FUNCTIONS, native.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE, REFERENCE_STATE, STAGE_STATE = {}, {}, {}, {}, {}, {}, {}
PARENT_CHECKER = None
CAPTURE, READ = 'erp_cp7_capture_model_history_v1', 'erp_cp7_read_model_history_v1'


def sources():
    return {p.name: sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__), Path(native.__file__))}


def cases(cur, today):
    native.PARENT_CHECKER = PARENT_CHECKER
    return native.cases(cur, today)[:1]


def install(cur):
    native.PARENT_CHECKER = PARENT_CHECKER
    return native.install(cur)


def races(tools, today):
    def prepare(replay=False):
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            install(cur)
            actor, _ = history.auth.custom_actor(cur)
            actor = str(actor)
            f = history.fixture(cur, today)
            q, key = native.query(cur, f, today), str(uuid.uuid4())
            if replay:
                native.capture(cur, q, key, actor)
            before, physical = native.count(cur), plan.monetary_state(cur)
            conn.commit()
        return f, q, actor, key, before, physical

    def capture(q, actor, key, backends, barrier=None, started=None):
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            backends.append(cur.execute('select pg_backend_pid()').fetchone()[0])
            if barrier is not None:
                barrier.wait(timeout=5)
            if started is not None:
                started.set()
            try:
                answer = native.capture(cur, deepcopy(q), key, actor)
                conn.commit()
                return answer
            except psycopg.Error as e:
                conn.rollback()
                return dict(sqlstate=e.sqlstate, message=e.diag.message_primary)

    def check(before, physical, delta):
        with tools.connect() as conn, conn.cursor() as cur:
            assert native.count(cur) == before + delta
            assert plan.monetary_state(cur) == physical

    def simultaneous():
        _, q, actor, key, before, physical = prepare()
        barrier, backends = Barrier(2), []
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(lambda _: capture(q, actor, key, backends, barrier), range(2)))
        assert len(set(backends)) == 2, backends
        assert all(a.get('contract_version') == 'cp7.scoped-history-run.v1' for a in answers), answers
        native.same_archive(*answers)
        assert all(a['current_guard']['source_state'] == 'UNCHANGED' for a in answers)
        check(before, physical, 1)
        return dict(status='PASS', two_actual_backends=True, one_UUID_one_immutable_run=True,
                    exact_archive_replay=True, no_physical_stock_money_HPP_change=True)

    def waiting(kind):
        replay = kind == 'request'
        f, q, actor, key, before, physical = prepare(replay)
        lock = 'CP7:MODEL:HISTORY:V1:' + actor + ':' + key if replay else 'FG_HPP_SALES_V2620C'
        started, backends = Event(), []
        with tools.connect() as holder, holder.cursor() as h, ThreadPoolExecutor(max_workers=1) as pool:
            h.execute("set local statement_timeout='8s'")
            h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))', (lock,))
            future = pool.submit(capture, q, actor, key, backends, None, started)
            assert started.wait(5)
            deadline, observed = monotonic() + 5, False
            try:
                while monotonic() < deadline:
                    if h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))', (backends[0],)).fetchone()[0]:
                        observed = True
                        break
                    sleep(.05)
                assert observed, ('MODEL_HISTORY_RUNTIME_ACTUAL_WAIT_NOT_OBSERVED', kind)
                if kind == 'source':
                    # The holder can re-enter the Native envelope it owns.
                    history.sales.fg.post_sale(h, f['draft'])
                    physical = plan.monetary_state(h)
                else:
                    h.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
                holder.commit()
            finally:
                holder.rollback()
            answer = future.result(timeout=15)
        if kind == 'source':
            assert answer.get('contract_version') == 'cp7.scoped-history-run.v1', answer
            assert answer['history']['history']['rows'][0]['gross_observed_pcs'] == '24'
            assert answer['history']['current_stock'][0]['native_available_pcs'] == '76'
            assert answer['current_guard']['source_state'] == 'UNCHANGED'
            check(before, physical, 1)
        else:
            assert answer.get('sqlstate') == '42501', answer
            check(before, physical, 0)
        return dict(status='PASS', actual_lock_wait_observed=kind, two_actual_backends=True,
                    actual_committed_replay_wait=replay, current_access_after_wait=kind != 'source',
                    actual_Native_post_captured_after_wait=kind == 'source', no_orphan_run=True,
                    no_double_stock_subtraction=kind == 'source')

    return list(zip(IDS['races'], [simultaneous, lambda: waiting('envelope'),
        lambda: waiting('request'), lambda: waiting('source')]))


def http_cases(http, today):
    with http.connect() as conn, conn.cursor() as cur:
        _, state = install(cur)
        cur.execute("notify pgrst,'reload schema'")
        conn.commit()

    def send(user, name, args):
        deadline = monotonic() + 5
        while True:
            reply = user.rpc(name, args)
            if reply['status'] != 404 or not isinstance(reply['body'], dict) or reply['body'].get('code') != 'PGRST202':
                return reply
            if monotonic() >= deadline:
                return reply
            sleep(.05)

    def prepare(label):
        user = http.login('OWNER', label)
        with http.connect() as conn, conn.cursor() as cur:
            stage.verify(cur, state)
            f = history.fixture(cur, today)
            q = native.query(cur, f, today)
            before, physical = native.count(cur), plan.monetary_state(cur)
            conn.commit()
        return user, f, dict(p_query=q, p_request=str(uuid.uuid4())), before, physical

    def unchanged(before, physical, delta):
        with http.connect() as conn, conn.cursor() as cur:
            assert native.count(cur) == before + delta
            assert plan.monetary_state(cur) == physical

    def flow():
        user, f, args, before, physical = prepare('scoped-history-flow')
        one = send(user, CAPTURE, args)
        assert one['status'] == 200, one
        read_args = dict(p_run=one['body']['run_id'])
        for reply in (send(user, CAPTURE, args), send(user, READ, read_args)):
            assert reply['status'] == 200, reply
            native.same_archive(one['body'], reply['body'])
        changed = send(user, CAPTURE, dict(args, p_query=dict(args['p_query'], group_mode='RESTATED')))
        assert changed['status'] != 200 and changed['body']['message'] == 'CP7_MODEL_HISTORY_REQUEST_CHANGED', changed
        for field in ('actor', 'source_hash', 'captured_at', 'history_complete'):
            forged = send(user, CAPTURE, dict(p_request=str(uuid.uuid4()), p_query=dict(args['p_query'], **{field: 'forged'})))
            assert forged['status'] != 200, forged
        unchanged(before, physical, 1)
        with http.connect() as conn, conn.cursor() as cur:
            frozen = native.stored(cur, one['body']['run_id'])
            history.sales.fg.post_sale(cur, f['draft'])
            physical = plan.monetary_state(cur)
            conn.commit()
        for reply in (send(user, READ, read_args), send(user, CAPTURE, args)):
            assert reply['status'] == 200, reply
            native.same_archive(one['body'], reply['body'])
            assert reply['body']['current_guard']['reason'] == 'CURRENT_SCOPED_SOURCE_CHANGED'
            assert reply['body']['current_guard']['source_state'] == 'ARCHIVED_STALE'
        fresh = send(user, CAPTURE, dict(args, p_request=str(uuid.uuid4())))
        assert fresh['status'] == 200, fresh
        assert fresh['body']['history']['history']['rows'][0]['gross_observed_pcs'] == '24'
        assert fresh['body']['history']['current_stock'][0]['native_available_pcs'] == '76'
        assert fresh['body']['current_guard']['source_state'] == 'UNCHANGED'
        with http.connect() as conn, conn.cursor() as cur:
            assert native.stored(cur, one['body']['run_id']) == frozen
        unchanged(before, physical, 2)
        return dict(status='PASS', actual_Auth_PostgREST_capture_read_replay=True,
                    changed_payload_and_forged_source_fields_refused=True,
                    actual_Native_post_retires_immutable_old_history=True,
                    fresh_capture_gross24_available76=True, no_double_stock_subtraction=True)

    def outsiders():
        user, _, args, before, physical = prepare('scoped-history-revoked')
        one = send(user, CAPTURE, args)
        assert one['status'] == 200, one
        read_args = dict(p_run=one['body']['run_id'])
        other = http.login('OWNER', 'scoped-history-other')
        assert http.anon_rpc(READ, read_args)['status'] in (401, 403)
        assert http.anon_rpc(CAPTURE, args)['status'] in (401, 403)
        foreign = send(other, READ, read_args)
        assert foreign['status'] == 403 and foreign['body']['message'] == 'CP7_MODEL_HISTORY_RUN_UNAVAILABLE', foreign
        # A permitted actor may independently capture the same public target;
        # UUID idempotency is actor-bound and cannot expose the first archive.
        own = send(other, CAPTURE, args)
        assert own['status'] == 200 and own['body']['run_id'] != one['body']['run_id'], own
        assert own['body']['actor_scope_id'] == str(other.auth_user_id)
        assert send(user, READ, dict(p_run=own['body']['run_id']))['status'] == 403
        with http.connect() as conn, conn.cursor() as cur:
            frozen = native.stored(cur, one['body']['run_id'])
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (user.auth_user_id,))
            conn.commit()
        assert send(user, READ, read_args)['status'] == 403
        assert send(user, CAPTURE, args)['status'] == 403
        assert send(other, READ, dict(p_run=own['body']['run_id']))['status'] == 200
        with http.connect() as conn, conn.cursor() as cur:
            assert native.stored(cur, one['body']['run_id']) == frozen
        unchanged(before, physical, 2)
        return dict(status='PASS', actual_old_token_read_and_committed_replay_refused=True,
                    anonymous_both_facades_denied=True, foreign_archive_denied=True,
                    same_UUID_isolated_per_actor=True, original_archive_unchanged=True)

    return list(zip(IDS['http'], [flow, outsiders]))
