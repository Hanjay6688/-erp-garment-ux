"""Focused actual Native/Auth/race/browser proof for the staged work screen.

The one catalog anchor repeats Native11; only the nine new transport cases
receive new credit. No dense checked SAVE2000 or production quantity claim.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic, sleep
import copy
import uuid
import psycopg
import cp7_ow13c_schedule_cases as work

CONTRACT = 'cp7.ow13c.staged-schedule-transport.v1'
IDS = dict(native=['OW13C_SCHEDULE_NATIVE_PRIVATE_CATALOG22'],
           races=['OW13C_SCHEDULE_RACE_SAME_UUID', 'OW13C_SCHEDULE_RACE_REVISION',
                  'OW13C_SCHEDULE_RACE_CURRENT_ACCESS_AFTER_WAIT', 'OW13C_SCHEDULE_RACE_SOURCE_AFTER_WAIT'],
           http=['OW13C_SCHEDULE_AUTH_READ_SAVE_REPLAY', 'OW13C_SCHEDULE_AUTH_REVOKED_REPLAY',
                 'OW13C_SCHEDULE_AUTH_ANON_FOREIGN'],
           browser=['OW13C_SCHEDULE_BROWSER_DESKTOP_STALE_DIRTY', 'OW13C_SCHEDULE_BROWSER_MOBILE_LOST_REPLY'])
REQUIRED = {k: len(v) for k, v in IDS.items()}
EXPECTED = DECLARED = sum(REQUIRED.values())
assert EXPECTED == 10
FUNCTIONS, SCHEDULES = work.FUNCTIONS, work.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE = {}, {}, {}, {}
SAVE = 'erp_cp7_save_staged_production_schedule_v1'
GET = 'erp_cp7_get_staged_production_schedule_v1'


def cases(cur, today):
    work.SCHEDULE_STATE = SCHEDULE_STATE
    return work.cases(cur, today)[:1]


def counts(cur):
    work.plan.b.api.admin(cur)
    return cur.execute('select(select count(*)from cp7_schedule_native.plans),'
                       '(select count(*)from cp7_schedule_native.commands)').fetchone()


def races(tools, today):
    def prepare():
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            actor = work.base.retained.master.role_actor(cur, 'OWNER')
            f = work.prepare(cur, today, subject=actor)
            before = counts(cur)
            physical = work.plan.monetary_state(cur)
            conn.commit()
        return f, actor, before, physical

    def save(f, actor, key, backend, barrier=None, started=None):
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            backend.append(cur.execute('select pg_backend_pid()').fetchone()[0])
            if barrier is not None:
                barrier.wait(timeout=5)
            if started is not None:
                started.set()
            try:
                out = work.save(cur, copy.deepcopy(f['payload']), key, actor)
                conn.commit()
                return out
            except psycopg.Error as error:
                conn.rollback()
                return dict(sqlstate=error.sqlstate, message=error.diag.message_primary)

    def check(before, physical, delta):
        with tools.connect() as conn, conn.cursor() as cur:
            assert counts(cur) == tuple(x+delta for x in before)
            assert work.plan.monetary_state(cur) == physical

    def simultaneous(same):
        f, actor, before, physical = prepare()
        barrier, backend, key = Barrier(2), [], str(uuid.uuid4())
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(lambda _: save(f, actor, key if same else str(uuid.uuid4()), backend, barrier), range(2)))
        assert len(set(backend)) == 2, backend
        if same:
            assert answers[0] == answers[1] and answers[0].get('staged_review_contract') == work.stage.render.CONTRACT, answers
        else:
            assert sum(a.get('revision') == str(int(f['payload']['expected_revision'])+1) for a in answers) == 1, answers
            assert sum(a.get('sqlstate') == 'P0001' and a.get('message') == 'CP7_SCHEDULE_REVISION_CHANGED' for a in answers) == 1, answers
        check(before, physical, 1)
        return dict(status='PASS', two_actual_backends=True, same_UUID_exact_replay=same,
                    distinct_UUID_CAS_one_winner=not same, one_plan_one_command=True, physical_stock_money_HPP_unchanged=True)

    def waiting(revoke):
        f, actor, before, physical = prepare()
        started, backend = Event(), []
        with tools.connect() as holder, holder.cursor() as h, ThreadPoolExecutor(max_workers=1) as pool:
            h.execute("set local statement_timeout='8s'")
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:GLOBAL',0))")
            future = pool.submit(save, f, actor, str(uuid.uuid4()), backend, None, started)
            assert started.wait(5)
            deadline, observed = monotonic()+5, False
            try:
                while monotonic() < deadline:
                    if h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))', (backend[0],)).fetchone()[0]:
                        observed = True
                        break
                    sleep(.05)
                assert observed, 'STAGED_SCHEDULE_REAL_GLOBAL_WAIT_NOT_OBSERVED'
                with tools.connect() as conn, conn.cursor() as cur:
                    cur.execute("set local statement_timeout='8s'")
                    cur.execute("set local lock_timeout='5s'")
                    if revoke:
                        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
                    else:
                        work.plan.found_fg(cur, f['x'], '1')
                    physical = work.plan.monetary_state(cur)
                    conn.commit()
            finally:
                holder.rollback()
            answer = future.result(timeout=15)
        if revoke:
            assert answer.get('sqlstate') == '42501', answer
        else:
            assert answer == dict(sqlstate='40001', message='CP7_SCHEDULE_SOURCE_CHANGED'), answer
        check(before, physical, 0)
        return dict(status='PASS', actual_global_lock_wait_observed=True, access_revoked_after_wait=revoke,
                    Native_stock_changed_after_wait=not revoke, no_orphan_plan_or_command=True)

    return list(zip(IDS['races'], [lambda: simultaneous(True), lambda: simultaneous(False),
                                 lambda: waiting(True), lambda: waiting(False)]))


def http_cases(http, today):
    def prepare(label):
        user = http.login('OWNER', label)
        with http.connect() as conn, conn.cursor() as cur:
            f = work.prepare(cur, today, subject=user.auth_user_id)
            before, physical = counts(cur), work.plan.monetary_state(cur)
            conn.commit()
        return user, f, dict(p_payload=f['payload'], p_request=str(uuid.uuid4())), before, physical

    def unchanged(before, physical, delta):
        with http.connect() as conn, conn.cursor() as cur:
            assert counts(cur) == tuple(x+delta for x in before)
            assert work.plan.monetary_state(cur) == physical

    def flow():
        user, f, args, before, physical = prepare('staged-work-flow')
        read = user.rpc(GET, dict(p_source_request=f['request']))
        assert read['status'] == 200 and read['body']['source_request_id'] == f['request'], read
        first, replay = user.rpc(SAVE, args), user.rpc(SAVE, args)
        assert first['status'] == replay['status'] == 200 and first['body'] == replay['body'], (first, replay)
        assert first['body']['staged_review_contract'] == work.stage.render.CONTRACT
        unchanged(before, physical, 1)
        return dict(status='PASS', actual_Auth_PostgREST_READ_SAVE_exact_replay=True, physical_stock_money_HPP_unchanged=True)

    def revoked():
        user, f, args, before, physical = prepare('staged-work-revoked')
        assert user.rpc(SAVE, args)['status'] == 200
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (user.auth_user_id,))
            conn.commit()
        assert user.rpc(GET, dict(p_source_request=f['request']))['status'] == 403
        assert user.rpc(SAVE, args)['status'] == 403
        unchanged(before, physical, 1)
        return dict(status='PASS', real_old_token_revoked_READ_and_committed_replay_refused=True)

    def outsiders():
        user, f, args, before, physical = prepare('staged-work-owner')
        other = http.login('OWNER', 'staged-work-other')
        assert http.anon_rpc(GET, dict(p_source_request=f['request']))['status'] in (401, 403)
        assert http.anon_rpc(SAVE, args)['status'] in (401, 403)
        assert other.rpc(GET, dict(p_source_request=f['request']))['status'] == 403
        assert other.rpc(SAVE, args)['status'] == 403
        unchanged(before, physical, 0)
        return dict(status='PASS', anonymous_both_facades_denied=True, foreign_owner_cannot_read_or_save_reference=True)

    return list(zip(IDS['http'], [flow, revoked, outsiders]))
