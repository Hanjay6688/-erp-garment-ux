"""Three real PostgreSQL two-session races; not Auth/browser/cron evidence."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic, sleep
import psycopg

C = None
PRODUCT = None


def races(tools, today):
    def prepare(enqueue=False):
        observed = {}
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            actor = C.B.native.native.policy.master.role_actor(cur, 'OWNER')
            f = C.fixture(cur, today, actor, observed)
            if enqueue:
                assert C.B.call(cur, 'request', f, observed)['state'] == 'QUEUED'
            before = C.snapshot(cur)
            conn.commit()
        return f, before, observed

    def call(verb, f, backends, barrier=None, started=None):
        observed = {}
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            backends.append(cur.execute('select pg_backend_pid()').fetchone()[0])
            if barrier is not None:
                barrier.wait(timeout=5)
            if started is not None:
                started.set()
            try:
                value = C.B.call(cur, verb, f, observed)
                conn.commit()
                return dict(value=value, observations=observed)
            except psycopg.Error as error:
                conn.rollback()
                return dict(sqlstate=error.sqlstate, message=error.diag.message_primary,
                            observations=observed)

    def simultaneous(verb):
        f, before, observed = prepare(enqueue=verb == 'step')
        backends, barrier = [], Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(pool.map(lambda _: call(verb, f, backends, barrier), range(2)))
        assert len(set(backends)) == 2, backends
        values = [r['value'] for r in replies if 'value' in r]
        if verb == 'request':
            assert values and all(v['state'] == 'QUEUED' for v in values), replies
            for reply in replies:
                if 'value' not in reply:
                    assert reply['sqlstate'] == 'P0001' and reply['message'] == 'CP7_CHOICE_PREPARATION_START_IN_FLIGHT', replies
            if len(values) == 2:
                assert values[0] == values[1]
        else:
            assert len(values) == 2 and any(v['state'] == 'READY' for v in values), replies
            assert all(v['state'] in ('RUNNING', 'READY') for v in values), replies
            assert len({v['created_at'] for v in values}) == 1
        with tools.connect() as conn, conn.cursor() as cur:
            C.unchanged(cur, before)
            work = C.one_work(cur, f)
            actual = C.B.call(cur, 'get', f, observed)
            expected = 'QUEUED' if verb == 'request' else 'READY'
            assert work['state'] == actual['state'] == expected and work['attempts'] == 0
            if verb == 'step':
                assert work['payload']['inputs'] == f['expected']
            else:
                assert work['payload'] is None
            C.CHECKER(cur)
        return dict(status='PASS', two_actual_backends=backends, simultaneous_method=verb,
            exactly_one_work=True, no_duplicate_choice_or_receipt=True,
            payload_equal_to_original_compiler=verb == 'step',
            no_money_stock_HPP_change=True, no_hidden_retry=True,
            observations=C.observations(observed), concurrent_replies=replies)

    def revoked_after_work():
        f, before, observed = prepare(enqueue=True)
        with tools.connect() as conn, conn.cursor() as cur:
            original_work = C.one_work(cur, f)
            catalog = PRODUCT.catalog._catalog_rows(cur)
            cur.execute("""create function public.cp7_choice_transport_hold_ready()
                returns trigger language plpgsql security invoker set search_path='' as $$
                begin
                    if new.state='READY' then
                        perform pg_advisory_xact_lock(hashtextextended('CP7:CHOICE:TRANSPORT:READY',0));
                    end if;
                    return new;
                end $$""")
            cur.execute('create trigger cp7_choice_transport_hold_ready before update '
                'on cp7_frozen_choice_preparation.work for each row '
                'execute function public.cp7_choice_transport_hold_ready()')
            conn.commit()
        backends, started = [], Event()
        waited = False
        try:
            with tools.connect() as holder, holder.cursor() as h, ThreadPoolExecutor(max_workers=1) as pool:
                h.execute("set local statement_timeout='8s'")
                holder_pid = h.execute('select pg_backend_pid()').fetchone()[0]
                h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:CHOICE:TRANSPORT:READY',0))")
                future = pool.submit(call, 'step', f, backends, None, started)
                try:
                    assert started.wait(5), 'CHOICE_WORKER_NOT_STARTED'
                    deadline = monotonic() + 5
                    while monotonic() < deadline:
                        if h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))', (backends[0],)).fetchone()[0]:
                            waited = True
                            break
                        sleep(.025)
                    assert waited, 'CHOICE_ACTUAL_READY_WAIT_NOT_OBSERVED'
                    h.execute('update erp.app_users set is_active=false where auth_user_id=%s', (f['subject'],))
                    assert h.rowcount == 1
                    holder.commit()
                finally:
                    holder.rollback()
                reply = future.result(timeout=15)
            assert reply.get('sqlstate') == '42501' and 'value' not in reply, reply
            assert len(backends) == 1 and holder_pid != backends[0]
            with tools.connect() as conn, conn.cursor() as cur:
                C.unchanged(cur, before)
                assert C.one_work(cur, f) == original_work, 'REVOKED_WORKER_PERSISTED_PAYLOAD_OR_PROGRESS'
                assert cur.execute('select is_active from erp.app_users where auth_user_id=%s', (f['subject'],)).fetchone() == (False,)
        finally:
            with tools.connect() as conn, conn.cursor() as cur:
                cur.execute('drop trigger cp7_choice_transport_hold_ready on cp7_frozen_choice_preparation.work')
                cur.execute('drop function public.cp7_choice_transport_hold_ready()')
                assert PRODUCT.catalog._catalog_rows(cur) == catalog
                C.CHECKER(cur)
                conn.commit()
        return dict(status='PASS', two_actual_backends=[holder_pid, backends[0]],
            actual_blocking_PID_observed=waited, access_revoked_after_compilation=True,
            full_STEP_statement_rolled_back=True, queued_row_exactly_unchanged=True,
            temporary_trigger_exact_catalog_restored=True, no_money_stock_HPP_change=True,
            SQL_fault_coordination_not_Auth_or_cron=True, observations=C.observations(observed),
            worker_reply=reply)

    return list(zip(C.IDS['races'], (lambda: simultaneous('request'),
        lambda: simultaneous('step'), revoked_after_work)))
