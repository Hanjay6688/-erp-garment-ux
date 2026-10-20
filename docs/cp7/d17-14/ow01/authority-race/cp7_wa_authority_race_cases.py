"""Uninstalled WA write/replay authority races for the closed disposable harness.

No database call occurs at import. The operations under test use the real public
WA RPCs as authenticated fixture owners. Holders take the actual production lock;
pg_blocking_pids proves the wait before another transaction retires that owner.
Only access fixtures and the labelled UNKNOWN clock fixture use direct writes.
This module starts no pg_net worker and makes no provider-delivery claim.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from urllib.parse import urlparse
import json
import time
import uuid

import psycopg


RACE_IDS = (
    'WAF_RACE_WA_SETTINGS_NEW_REVOKED_AFTER_WAIT',
    'WAF_RACE_WA_SETTINGS_REPLAY_REVOKED_AFTER_WAIT',
    'WAF_RACE_WA_KEY_NEW_REVOKED_AFTER_WAIT',
    'WAF_RACE_WA_KEY_REPLAY_REVOKED_AFTER_WAIT',
    'WAF_RACE_WA_TEST_NEW_REVOKED_AFTER_WAIT',
    'WAF_RACE_WA_TEST_REPLAY_REVOKED_AFTER_WAIT',
    'WAF_RACE_WA_RESOLVE_NEW_REVOKED_AFTER_WAIT',
    'WAF_RACE_WA_RESOLVE_REPLAY_REVOKED_AFTER_WAIT',
)

# These complete rows contain every durable WA request receipt. The Vault
# fingerprint is over encrypted stored data; no plaintext secret is read/output.
_FINGERPRINTS = (
    ('settings', 'cp7_alert_native.settings', 'x.revision', ''),
    ('key_events', 'cp7_alert_native.key_events', 'x.id', ''),
    ('vault_secret', 'vault.secrets', 'x.id', "where x.name='cp7_callmebot_apikey'"),
    ('dispatches', 'cp7_alert_native.dispatches', 'x.id', ''),
    ('outbox', 'cp7_alert_native.outbox', 'x.id', ''),
    ('dispatch_items', 'cp7_alert_native.dispatch_items', 'x.dispatch_id,x.outbox_id', ''),
    ('transport', 'cp7_alert_native.transport', 'x.id', ''),
    ('alerts', 'cp7_alert_native.alerts', 'x.id', ''),
    ('ticks', 'cp7_alert_native.ticks', 'x.job', ''),
    ('source_state', 'cp7_alert_native.source_state', 'x.kind', ''),
    ('net_queue', 'net.http_request_queue', 'x.id', ''),
    ('net_response', 'net._http_response', 'x.id', ''),
)


def _committed(tools, operation):
    with tools.connect() as conn, conn.cursor() as cur:
        out = operation(cur)
        conn.commit()
        return out


def _disposable(cur, tools):
    # A caller cannot accidentally point this committed race at the hosted ERP.
    expected = 'cp6_auditor_race'
    actual = cur.execute('select current_database()').fetchone()[0]
    assert urlparse(tools.admin).path.lstrip('/') == actual == expected, (
        'WA_AUTHORITY_RACE_REQUIRES_DISPOSABLE_DATABASE', actual)
    # This authority case never starts/repoints the provider worker. Refuse a
    # leftover worker configuration rather than racing its queue consumption.
    worker_database = cur.execute("select current_setting('pg_net.database_name',true)").fetchone()[0]
    assert worker_database != actual, 'WA_AUTHORITY_RACE_PROVIDER_WORKER_MUST_NOT_TARGET_COPY'


def _fingerprints(cur, wa):
    wa.b.api.admin(cur)
    result = {}
    for label, relation, order, predicate in _FINGERPRINTS:
        # Identifiers are this module's fixed literals, never request input.
        row = cur.execute(
            "select count(*),encode(sha256(convert_to(coalesce("
            "jsonb_agg(to_jsonb(x) order by " + order + "),'[]'::jsonb)::text,"
            "'UTF8')),'hex') from " + relation + ' x ' + predicate).fetchone()
        result[label] = {'count': row[0], 'sha256': row[1]}
    return result


def _owners(cur, wa, ids=None):
    wa.b.api.admin(cur)
    predicate = 'where r.role_code=%s'
    params = ['OWNER']
    if ids is not None:
        predicate += ' and u.id=any(%s::uuid[])'
        params.append(ids)
    return cur.execute(
        'select u.id::text,to_jsonb(u) from erp.app_users u '
        'join erp.app_roles r on r.id=u.role_id ' + predicate + ' order by u.id', params).fetchall()


def _wait_blocked(tools, worker_pid, holder_pid, seconds=4):
    deadline = time.monotonic() + seconds
    with tools.connect() as conn, conn.cursor() as cur:
        while time.monotonic() < deadline:
            cur.execute('select pg_stat_clear_snapshot()')
            row = cur.execute(
                'select wait_event_type,pg_blocking_pids(pid) from pg_stat_activity '
                'where datname=current_database() and pid=%s', (worker_pid,)).fetchone()
            conn.rollback()
            if row and row[0] == 'Lock' and holder_pid in row[1]:
                return {'wait_event_type': row[0], 'actual_holder_is_blocker': True}
            time.sleep(.02)
    return None


def _prepare(cur, tools, wa, operation, replay):
    wa.b.api.admin(cur)
    _disposable(cur, tools)
    assert wa.one(cur, 'select count(*) from cp7_alert_native.dispatches') == 0, (
        'WA_AUTHORITY_REQUIRES_FRESH_COPY_PER_REGISTERED_RACE')
    existing = _owners(cur, wa)
    assert existing and any(row['is_active'] is True for _, row in existing), 'WA_AUTHORITY_SEED_OWNER_MISSING'
    # setup() creates a fresh app_user in the existing seeded OWNER role. It
    # never retires or changes the original protected owner.
    fixture = wa.setup(cur, enabled=False, key=True, kinds=['ACCESSORY_NEED'], analysis_every_minutes=0)
    assert fixture['user'] not in [ident for ident, _ in existing], 'WA_AUTHORITY_OWNER_NOT_FRESH'
    wa.b.api.admin(cur)
    assert wa.one(cur, 'select base_url from cp7_alert_native.transport where id') == (
        'http://fake-callmebot:8080/whatsapp.php'), 'WA_AUTHORITY_REQUIRES_FAKE_TRANSPORT'
    request = str(uuid.uuid4())
    target = None
    if operation == 'SETTINGS':
        rpc = 'erp_cp7_save_wa_settings_v1'
        args = (wa.settings_payload(wa.revision(cur), enabled=True, kinds=['ACCESSORY_NEED'],
                                    detail='DETAILED', analysis_every_minutes=0), request)
    elif operation == 'KEY':
        rpc = 'erp_cp7_set_wa_key_v1'
        args = ('FAKEKEY-AUTHRACE-' + uuid.uuid4().hex[:12], request)
    elif operation == 'TEST':
        rpc = 'erp_cp7_send_wa_test_v1'
        args = (request,)
    elif operation == 'RESOLVE':
        # A real public TEST operation and real reconcile establish the target.
        # TEST_CLOCK_OVERRIDE: only this committed fixture's queue timestamp is
        # aged 11 minutes; no provider answer/delivery is fabricated or claimed.
        test = wa.rpc(cur, 'erp_cp7_send_wa_test_v1', (str(uuid.uuid4()),), fixture['owner'])
        target = test['dispatch_id']
        wa.test_clock(cur,
            'update cp7_alert_native.dispatches set queued_at=queued_at-interval\'11 minutes\' where id=%s',
            (target,))
        tick = wa.tick(cur, 'send_tick')
        actual = wa.dispatch(cur, target)
        assert tick['answered'] == 1 and actual['status'] == 'UNKNOWN' and actual['resolved'] is None, (
            'WA_AUTHORITY_RESOLVE_FIXTURE_NOT_UNKNOWN', tick, actual)
        rpc = 'erp_cp7_resolve_wa_dispatch_v1'
        args = (json.dumps({'dispatch_id': target, 'outcome': 'NOT_DELIVERED'}), request)
    else:
        raise AssertionError('WA_AUTHORITY_UNKNOWN_OPERATION')
    original = None
    if replay:
        original = wa.rpc(cur, rpc, args, fixture['owner'])
        assert original.get('replay') is False, ('WA_AUTHORITY_FIRST_REQUEST_WAS_REPLAY', operation)
    # This is a real public read while the fixture owner is still active. It
    # proves initial eligibility independently of the worker's later refusal.
    readable = wa.rpc(cur, 'erp_cp7_get_wa_settings_v1', (), fixture['owner'])
    assert isinstance(readable, dict), 'WA_AUTHORITY_FIXTURE_NOT_INITIALLY_AUTHORIZED'
    wa.b.api.admin(cur)
    assert _owners(cur, wa, [ident for ident, _ in existing]) == existing, 'WA_AUTHORITY_SEED_OWNER_CHANGED_BY_SETUP'
    if operation == 'SETTINGS':
        receipt_count = wa.one(cur, 'select count(*) from cp7_alert_native.settings where request_id=%s', (request,))
    elif operation == 'KEY':
        receipt_count = wa.one(cur, 'select count(*) from cp7_alert_native.key_events where request_id=%s', (request,))
    else:
        field = 'request_id' if operation == 'TEST' else 'resolve_request'
        receipt_count = wa.one(cur, 'select count(*) from cp7_alert_native.dispatches where ' + field + '=%s', (request,))
    assert receipt_count == int(replay), ('WA_AUTHORITY_BASE_RECEIPT_COUNT', operation, replay, receipt_count)
    return dict(fixture=fixture, request=request, rpc=rpc, args=args, existing=existing,
                target=target if operation == 'RESOLVE' else None,
                before=_fingerprints(cur, wa), committed_replay=original is not None)


def races(tools, today, wa):
    """Eight all-or-fail committed races; no setup runs during registration."""
    def run(operation, replay):
        x = _committed(tools, lambda cur: _prepare(cur, tools, wa, operation, replay))
        holder = tools.connect()
        started = Event()
        worker_pids = []
        observed = None

        def worker():
            with tools.connect() as conn, conn.cursor() as cur:
                cur.execute("set local statement_timeout='8s'")
                worker_pids.append(cur.execute('select pg_backend_pid()').fetchone()[0])
                started.set()
                try:
                    result = wa.rpc(cur, x['rpc'], x['args'], x['fixture']['owner'])
                    conn.commit()
                    # Log only receipt metadata; never key material or settings
                    # payloads. Even a side-effect-free replay must be refused.
                    return {'returned_receipt': True, 'replay': result.get('replay')}
                except psycopg.Error as error:
                    conn.rollback()
                    return {'returned_receipt': False, 'sqlstate': error.sqlstate,
                            'message': error.diag.message_primary}

        try:
            with holder.cursor() as cur:
                wa.b.api.admin(cur)
                _disposable(cur, tools)
                if operation == 'RESOLVE':
                    locked = cur.execute('select id from cp7_alert_native.dispatches where id=%s for update', (x['target'],)).fetchone()
                    assert locked == (x['target'],), 'WA_AUTHORITY_RESOLVE_TARGET_MISSING'
                else:
                    lock = 'CP7:WA:TEST' if operation == 'TEST' else 'CP7:WA:SETTINGS'
                    cur.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))', (lock,))
                holder_pid = cur.execute('select pg_backend_pid()').fetchone()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(worker)
                try:
                    assert started.wait(3), 'WA_AUTHORITY_WORKER_DID_NOT_START'
                    observed = _wait_blocked(tools, worker_pids[0], holder_pid)
                    assert observed is not None, (
                        'WA_AUTHORITY_ACTUAL_LOCK_WAIT_NOT_OBSERVED', operation, replay)

                    def retire(cur):
                        wa.b.api.admin(cur)
                        existing_ids = [ident for ident, _ in x['existing']]
                        assert _owners(cur, wa, existing_ids) == x['existing'], 'WA_AUTHORITY_SEED_OWNER_CHANGED_BEFORE_REVOKE'
                        cur.execute('update erp.app_users set is_active=false where id=%s and is_active', (x['fixture']['user'],))
                        assert cur.rowcount == 1, 'WA_AUTHORITY_FIXTURE_OWNER_NOT_RETIRED'
                        assert _owners(cur, wa, existing_ids) == x['existing'], 'WA_AUTHORITY_SEED_OWNER_CHANGED_DURING_REVOKE'
                        # Retirement changes access fixtures only. No WA row,
                        # stored receipt, encrypted key or pg_net row changes.
                        assert _fingerprints(cur, wa) == x['before'], 'WA_AUTHORITY_REVOKE_MUTATED_WA_STATE'
                    _committed(tools, retire)
                finally:
                    holder.rollback()
                result = future.result(15)
        finally:
            holder.rollback()
            holder.close()
        assert result == {'returned_receipt': False, 'sqlstate': '42501', 'message': 'CP7_WA_OWNER_ONLY'}, (
            'WA_AUTHORITY_REVOKED_OPERATION_NOT_REFUSED', operation, replay, result)

        def verify(cur):
            wa.b.api.admin(cur)
            assert _fingerprints(cur, wa) == x['before'], 'WA_AUTHORITY_REFUSAL_CHANGED_DURABLE_STATE'
            assert _owners(cur, wa, [ident for ident, _ in x['existing']]) == x['existing'], 'WA_AUTHORITY_SEED_OWNER_CHANGED'
            assert wa.one(cur, 'select is_active from erp.app_users where id=%s', (x['fixture']['user'],)) is False, (
                'WA_AUTHORITY_REVOKED_FIXTURE_OWNER_REACTIVATED')
        _committed(tools, verify)
        return dict(status='PASS', operation=operation, committed_replay=replay,
                    actual_lock_wait_observed_by='pg_blocking_pids', actual_holder_is_blocker=True,
                    initially_authorized_public_read=True, fresh_owner_retired_during_wait=True,
                    existing_owner_rows_unchanged=True, refusal_sqlstate=result['sqlstate'],
                    refusal_message=result['message'], returned_receipt=False,
                    WA_receipts_key_and_transport_state_unchanged=True,
                    unknown_fixture='TEST_CLOCK_OVERRIDE_11_MINUTES_THEN_REAL_RECONCILE' if operation == 'RESOLVE' else None,
                    provider_delivery_proven=False)

    operations = tuple((name, replay) for name in ('SETTINGS', 'KEY', 'TEST', 'RESOLVE') for replay in (False, True))
    planned = [(key, lambda operation=op, replay=replay: run(operation, replay))
               for key, (op, replay) in zip(RACE_IDS, operations)]
    assert len(planned) == 8 and [key for key, _ in planned] == list(RACE_IDS), 'WA_AUTHORITY_RACE_REGISTRATION_CHANGED'
    return planned
