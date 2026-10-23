"""Four actual two-backend checked-save controls, prepared for the next suite.

Not run or qualified by Native25: its four retained races are OW10 only.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic, sleep
import copy
import uuid
import psycopg
import cp7_ow13c_checked_cases as base

IDS = ['OW13C_RACE_SAME_UUID_ONE_DRAFT_RECEIPT',
       'OW13C_RACE_TWO_REVISIONS_ONE_WINNER',
       'OW13C_RACE_REVOKED_WHILE_CAPACITY_LOCKED',
       'OW13C_RACE_STOCK_CHANGED_WHILE_CAPACITY_LOCKED']


def races(tools, today):
    def prepare():
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            actor = base.retained.master.role_actor(cur, 'OWNER')
            x = base.plan.single(cur, today, subject=actor)
            conn.commit()
        return x, actor

    def save(p, actor, request, started=None, backend=None, barrier=None):
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            if backend is not None:
                backend.append(cur.execute('select pg_backend_pid()').fetchone()[0])
            if barrier is not None:
                barrier.wait(timeout=5)
            if started is not None:
                started.set()
            try:
                result = base.save(cur, p, request, subject=actor)
                conn.commit()
                return result
            except psycopg.Error as error:
                conn.rollback()
                return dict(sqlstate=error.sqlstate, message=error.diag.message_primary)

    def counts(actor):
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            return cur.execute('select(select count(*)from cp7_plan_native.drafts where actor=%s),'
                               '(select count(*)from cp7_cutting_checked.receipts where actor=%s)',
                               (actor, actor)).fetchone()

    def same():
        x, actor = prepare()
        p, request = base.payload(x), str(uuid.uuid4())
        barrier, backend = Barrier(2), []
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = list(pool.map(lambda _: save(p, actor, request, backend=backend, barrier=barrier), range(2)))
        assert len(set(backend)) == 2, backend
        assert a == b and a.get('state') == 'SAVED', (a, b)
        assert counts(actor) == (1, 1)
        return dict(status='PASS', actual_two_backends_same_UUID_same_receipt_one_draft=True)

    def revision():
        x, actor = prepare()
        p = base.payload(x)
        first = save(p, actor, str(uuid.uuid4()))
        assert first.get('state') == 'SAVED', first
        p.update(plan_id=first['plan_id'], expected_revision=first['revision'])
        barrier, backend = Barrier(2), []
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(lambda _: save(copy.deepcopy(p), actor, str(uuid.uuid4()), backend=backend, barrier=barrier), range(2)))
        assert len(set(backend)) == 2, backend
        assert sum(a.get('revision') == '2' for a in answers) == 1, answers
        assert sum(a.get('message') == 'CP7_PLAN_REVISION_CHANGED' and a.get('sqlstate') == '40001'
                   for a in answers) == 1, answers
        assert counts(actor) == (2, 2)
        return dict(status='PASS', expected_revision_one_winner_history_and_receipts_preserved=True)

    def while_waiting(revoke):
        x, actor = prepare()
        started, backend = Event(), []
        with tools.connect() as holder, holder.cursor() as h, ThreadPoolExecutor(max_workers=1) as pool:
            h.execute("set local statement_timeout='8s'")
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:PLAN_CAPACITY',0))")
            pending = pool.submit(save, base.payload(x), actor, str(uuid.uuid4()), started, backend)
            assert started.wait(5)
            deadline, observed = monotonic()+5, False
            while monotonic() < deadline:
                row = h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))', (backend[0],)).fetchone()
                if row and row[0] is True:
                    observed = True
                    break
                sleep(.05)
            assert observed, 'OW13C_ACTUAL_CAPACITY_WAIT_NOT_OBSERVED'
            try:
                with tools.connect() as conn, conn.cursor() as cur:
                    cur.execute("set local statement_timeout='8s'")
                    cur.execute("set local lock_timeout='5s'")
                    if revoke:
                        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
                    else:
                        base.plan.found_fg(cur, x, '1')
                    conn.commit()
            finally:
                # Release the test's lock even if its external writer fails.
                # Otherwise pool shutdown could itself wait on this holder.
                holder.rollback()
            answer = pending.result(timeout=15)
        if revoke:
            assert answer.get('sqlstate') == '42501', answer
        else:
            assert answer.get('sqlstate') == '40001' and answer.get('message') == 'CP7_CUTTING_SUGGESTION_SOURCE_CHANGED', answer
        assert counts(actor) == (0, 0)
        return dict(status='PASS', real_capacity_wait_observed=True,
                    real_revoke_after_wait=revoke, actual_stock_writer_after_wait=not revoke,
                    no_orphan_draft_or_receipt=True)

    return list(zip(IDS, [same, revision, lambda: while_waiting(True), lambda: while_waiting(False)]))
