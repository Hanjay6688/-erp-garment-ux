"""OW-01 real transport proposals: three committed races and one Auth/PostgREST case.

No provider answer is fabricated. The first race uses the existing fake CallMeBot
and pg_net worker; the other races observe a real Native BOM writer in
pg_blocking_pids before committing a changed BOM or revoking the owner.
Imported by cp7_wa_forward_cases only after its helpers have been defined.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event
from urllib.parse import urlparse, urlunparse
import json
import re
import time
import urllib.request
import uuid

import psycopg

import cp7_wa_accessory_cases as accessory

RACE_IDS = (
    'WAF_RACE_ACCESSORY_NEED_TWO_TICKS_ONE_RECEIPT',
    'WAF_RACE_ACCESSORY_NEED_BOM_CHANGE_DURING_WAIT',
    'WAF_RACE_ACCESSORY_NEED_ACCESS_REVOKED_DURING_WAIT',
)
HTTP_IDS = ('WAF_HTTP_ACCESSORY_NEED_SETTINGS_LOST_REPLY_REVOKED_REPLAY',)
BROWSER_IDS = ('WAF_BROWSER_ACCESSORY_NEED_DESKTOP', 'WAF_BROWSER_ACCESSORY_NEED_MOBILE')


def review_message(body, unit):
    """An unknown purchase amount remains unknown in the actual provider text."""
    text = body.lower()
    assert 'aksesori perlu diperiksa' in text, body
    assert 'jumlah tambahan belum diketahui' in text, body
    assert re.search(r'\bbom(?:\s*\([^)]*\))?\s*186\b', text), body
    assert 'BOM (perkiraan) 186 ' + unit in body, body
    assert not re.search(r'(?:beli|membeli|tambahan)\s*[:=]?\s*186\b', text), body


def _committed(tools, operation):
    with tools.connect() as conn, conn.cursor() as cur:
        out = operation(cur)
        conn.commit()
        return out


def _dispatch_count(cur, wa):
    wa.b.api.admin(cur)
    return wa.one(cur, "select count(*) from cp7_alert_native.dispatches where kind<>'TEST'")


def _wait_blocked(tools, sender_pid, holder_pid, seconds=4):
    deadline = time.monotonic() + seconds
    with tools.connect() as conn, conn.cursor() as cur:
        while time.monotonic() < deadline:
            cur.execute('select pg_stat_clear_snapshot()')
            row = cur.execute(
                'select wait_event_type,pg_blocking_pids(pid) from pg_stat_activity '
                'where datname=current_database() and pid=%s', (sender_pid,)).fetchone()
            conn.rollback()
            if row and row[0] == 'Lock' and holder_pid in row[1]:
                return True
            time.sleep(.02)
    return False


@contextmanager
def _provider_worker(tools, wa):
    """The existing pg_net worker, pointed only at this disposable race copy."""
    database = urlparse(tools.admin).path.lstrip('/')
    assert database == 'cp6_auditor_race', ('OW01_NOT_DISPOSABLE_RACE', database)
    try:
        wa.docker_admin("alter system set pg_net.database_name='%s'" % database)
        wa.docker_admin('select pg_reload_conf()')
        time.sleep(1)
        with psycopg.connect(tools.admin, autocommit=True) as conn:
            conn.execute('select net.worker_restart()')
        time.sleep(2)
        yield
    finally:
        wa.docker_admin('alter system reset pg_net.database_name')
        wa.docker_admin('select pg_reload_conf()')
        time.sleep(1)
        primary = urlunparse(urlparse(tools.admin)._replace(path='/postgres'))
        with psycopg.connect(primary, autocommit=True) as conn:
            if conn.execute("select exists(select 1 from pg_extension where extname='pg_net')").fetchone()[0]:
                conn.execute('select net.worker_restart()')


def _wait_answer(tools, dispatch_id, seconds=40):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        with tools.connect() as conn, conn.cursor() as cur:
            answered = cur.execute(
                'select exists(select 1 from net._http_response r join cp7_alert_native.dispatches d '
                'on d.net_request_id=r.id where d.id=%s)', (dispatch_id,)).fetchone()[0]
        if answered:
            return True
        time.sleep(.2)
    return False


def races(tools, today, wa):
    def prepared():
        return _committed(tools, lambda cur: accessory.prepared(cur, today, wa))

    def send():
        return _committed(tools, lambda cur: wa.tick(cur, 'send_tick'))

    def two_ticks_one_receipt():
        x = prepared()
        initial = _committed(tools, lambda cur: wa.alerts(cur, 'ACCESSORY_NEED')[x['key']])
        accessory.assert_detail(initial, x)
        queued = _committed(tools, lambda cur: wa.outbox(cur, initial['id']))
        assert len(queued) == 1 and queued[0]['round'] == 0 and queued[0]['state'] == 'PENDING', queued
        before = len(wa.fake_log())
        with _provider_worker(tools, wa):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = [f.result(30) for f in [pool.submit(send), pool.submit(send)]]
            sent = [r for r in results if r['outcome'] == 'SENT']
            assert len(sent) == 1 and all(r['outcome'] in ('SENT', 'BUSY', 'IDLE', 'WAITING') for r in results), results
            did = sent[0]['dispatch_id']
            assert _wait_answer(tools, did), ('OW01_FAKE_PROVIDER_NO_ANSWER', did)
            send()  # Record the real pg_net answer; this must not queue another message.
            d = _committed(tools, lambda cur: wa.dispatch(cur, did))
            assert (d['kind'], d['status'], d['http']) == ('INSTANT', 'PROVIDER_ACCEPTED', 200), d
            review_message(d['body'], x['m']['gross']['unit'])
            receipts = wa.fake_log()[before:]
            assert len(receipts) == 1, ('OW01_CONCURRENT_DUPLICATE_PROVIDER_RECEIPT', receipts)
            assert receipts[0]['phone'] == wa.PHONE and receipts[0]['key_ok'] is True and receipts[0]['status'] == 200, receipts
            assert receipts[0]['text'] == d['body'], (receipts[0], d['body'])
            assert _committed(tools, lambda cur: _dispatch_count(cur, wa)) == 1
            current = _committed(tools, lambda cur: wa.alerts(cur, 'ACCESSORY_NEED')[x['key']])
            pending = _committed(tools, lambda cur: wa.outbox(cur, initial['id']))
            assert current['id'] == initial['id'] and current['episode'] == 1, current
            assert len(pending) == 1 and pending[0]['state'] == 'ACCEPTED' and pending[0]['attempts'] == 1, pending
            _committed(tools, lambda cur: accessory.original_unchanged(cur, x))
        return dict(status='PASS', real_fake_provider_receipts=1, concurrent_outcomes=[r['outcome'] for r in results],
                    one_alert_one_round_one_dispatch=True, body_equals_provider_receipt=True, external_quantity_stays_unknown=True)

    def native_wait(revoke):
        x = prepared()
        original = _committed(tools, lambda cur: wa.alerts(cur, 'ACCESSORY_NEED')[x['key']])
        before = _committed(tools, lambda cur: _dispatch_count(cur, wa))
        holder = tools.connect()
        started = Event()
        sender_pid = []

        def waiting_send():
            with tools.connect() as conn, conn.cursor() as cur:
                sender_pid.append(cur.execute('select pg_backend_pid()').fetchone()[0])
                started.set()
                try:
                    result = wa.tick(cur, 'send_tick')
                    conn.commit()
                    return dict(result=result)
                except psycopg.Error as error:
                    conn.rollback()
                    return dict(sqlstate=error.sqlstate, error=error.diag.message_primary)

        observed = False
        revoked = False
        try:
            with holder.cursor() as cur:
                # This invokes the real BF writer. Its own FG/BF locks are kept
                # until the holder commits/rolls back; no artificial reminder lock.
                successor = accessory.successor(cur, x, qty='3')
                holder_pid = cur.execute('select pg_backend_pid()').fetchone()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(waiting_send)
                try:
                    assert started.wait(3), 'OW01_SENDER_DID_NOT_START'
                    observed = _wait_blocked(tools, sender_pid[0], holder_pid)
                    assert observed, ('OW01_NATIVE_BOM_LOCK_WAIT_NOT_OBSERVED', sender_pid, holder_pid)
                    if revoke:
                        def disable(cur):
                            wa.b.api.admin(cur)
                            cur.execute('update erp.app_users set is_active=false where id=%s and is_active', (x['s']['user'],))
                            assert cur.rowcount == 1, 'OW01_OWNER_REVOKE_NOT_APPLIED'
                        _committed(tools, disable)
                        revoked = True
                        holder.rollback()  # Only revocation wins; the BOM remains unchanged.
                    else:
                        holder.commit()  # The real Native successor wins before the sender resumes.
                finally:
                    holder.rollback()
                result = future.result(30)
            assert _committed(tools, lambda cur: _dispatch_count(cur, wa)) == before, result
            waiting = _committed(tools, lambda cur: wa.outbox(cur, original['id']))
            assert len(waiting) == 1 and waiting[0]['dispatch'] is None and waiting[0]['attempts'] == 0, waiting
            current = _committed(tools, lambda cur: wa.alerts(cur, 'ACCESSORY_NEED')[x['key']])
            assert current['id'] == original['id'] and current['episode'] == original['episode'], current
            if revoke:
                assert result.get('sqlstate') == '42501' and 'ACCESS' in result.get('error', ''), result
            else:
                assert result.get('result', {}).get('outcome') not in ('SENT', 'DIGEST'), result
                v = _committed(tools, lambda cur: wa.rpc(cur, 'erp_cp7_recheck_reminder_v2',
                                                       (x['r']['run'], x['key']), x['s']['owner']))
                assert (v['verdict'], v['reason']) == ('CHANGED_REVIEW_REQUIRED', 'ACCESSORY_SOURCE_CHANGED_AFTER_SNAPSHOT'), v
                _committed(tools, lambda cur: accessory.original_unchanged(cur, x))
        finally:
            holder.rollback()
            holder.close()
            if revoked:
                def restore(cur):
                    wa.b.api.admin(cur)
                    cur.execute('update erp.app_users set is_active=true where id=%s', (x['s']['user'],))
                _committed(tools, restore)
        if revoke:
            _committed(tools, lambda cur: accessory.original_unchanged(cur, x))
        return dict(status='PASS', actual_native_BOM_writer_wait=observed, wait_observed_by='pg_blocking_pids',
                    old_snapshot_dispatches=0, same_open_episode_and_outbox_preserved=True,
                    owner_revoked_during_wait=revoke, BOM_successor_committed=not revoke,
                    sender_refusal=result.get('error'), successor_created_by_Native=bool(successor))

    return list(zip(RACE_IDS, (two_ticks_one_receipt, lambda: native_wait(False), lambda: native_wait(True))))


def _discard_http_reply(user, name, args):
    """Real HTTP request; close after response headers without reading its body.

    The database state is checked separately before retrying this exact UUID.
    No tokens, request headers or key values enter the receipt.
    """
    import cp6_auditor_modes as modes
    request = urllib.request.Request(modes.REST_URL + '/rpc/' + name, json.dumps(args).encode(),
                                     headers={'Content-Type': 'application/json', 'apikey': user._http._anon,
                                              'Authorization': 'Bearer ' + user._token}, method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 200, ('OW01_LOST_REPLY_HTTP_STATUS', response.status)
        # Intentionally do not call response.read(). The caller has no receipt.
        return response.status


def http_cases(http, today, wa):
    def settings_lost_reply_revoked_replay():
        owner = http.login('OWNER', 'ow01-accessory-http')
        with http.connect() as conn, conn.cursor() as cur:
            app_user = cur.execute('select id::text from erp.app_users where auth_user_id=%s', (owner.auth_user_id,)).fetchone()[0]
            settings = dict(owner=owner.auth_user_id, user=app_user)
            x = accessory.prepared(cur, today, wa, subject=owner.auth_user_id, settings=settings, enabled=None, collect=False)
            revision = wa.revision(cur)
            conn.commit()
        key = owner.rpc('erp_cp7_set_wa_key_v1', dict(p_key=wa.KEY, p_request=str(uuid.uuid4())))
        assert key['status'] == 200 and key['body']['key_present'] is True, key
        request_id = str(uuid.uuid4())
        payload = dict(wa.SETTINGS, expected_revision=revision, enabled=True, kinds=['ACCESSORY_NEED'],
                       detail='DETAILED', analysis_every_minutes=0)
        args = dict(p=payload, p_request=request_id)
        _discard_http_reply(owner, 'erp_cp7_save_wa_settings_v1', args)

        def stored(cur):
            wa.b.api.admin(cur)
            rows = cur.execute('select revision,cp7_alert_native.settings_json(s) from cp7_alert_native.settings s '
                               'where request_id=%s', (request_id,)).fetchall()
            assert len(rows) == 1 and rows[0][0] == revision + 1, rows
            return rows[0][1]
        with http.connect() as conn, conn.cursor() as cur:
            saved = stored(cur)
        replay = owner.rpc('erp_cp7_save_wa_settings_v1', args)
        replay_again = owner.rpc('erp_cp7_save_wa_settings_v1', args)
        assert replay['status'] == replay_again['status'] == 200, (replay, replay_again)
        assert replay['body'] == replay_again['body'] == dict(replay=True, settings=saved), (replay, replay_again)
        assert saved['kinds'] == ['ACCESSORY_NEED'] and saved['enabled'] is True, saved
        changed = owner.rpc('erp_cp7_save_wa_settings_v1', dict(p=dict(payload, enabled=False), p_request=request_id))
        assert changed['status'] >= 400 and 'CP7_WA_REQUEST_REUSED' in json.dumps(changed['body']), changed
        anonymous = http.anon_rpc('erp_cp7_save_wa_settings_v1', args)
        assert anonymous['status'] >= 400, anonymous
        with http.connect() as conn, conn.cursor() as cur:
            wa.drain(cur)
            a = wa.alerts(cur, 'ACCESSORY_NEED')[x['key']]
            accessory.assert_detail(a, x)
            accessory.original_unchanged(cur, x)
            assert stored(cur) == saved
            cur.execute('update erp.app_users set is_active=false where id=%s and is_active', (app_user,))
            assert cur.rowcount == 1
            conn.commit()
        # Same real Auth object/token, no login or refresh after revocation.
        denied = owner.rpc('erp_cp7_save_wa_settings_v1', args)
        assert denied['status'] == 403 and 'CP7_WA_OWNER_ONLY' in json.dumps(denied['body']), denied
        with http.connect() as conn, conn.cursor() as cur:
            assert stored(cur) == saved
            assert wa.revision(cur) == revision + 1
        return dict(status='PASS', real_Auth_PostgREST=True, reply_body_discarded_after_200_headers=True,
                    exact_UUID_replay_one_revision=True, changed_UUID_payload_refused=True, anonymous_replay_refused=True,
                    same_token_revoked_replay_http=denied['status'], preserved_unknown_accessory_detail=True)

    return [(HTTP_IDS[0], settings_lost_reply_revoked_replay)]


def browser_prepare(cur, today, p, wa, with_erp_usage):
    """Native source only. Browser settings, kind selection and key stay in UI."""
    subject = p['subject']
    wa.b.api.admin(cur)
    row = cur.execute('select id::text from erp.app_users where auth_user_id=%s and is_active', (subject,)).fetchone()
    assert row is not None, 'OW01_BROWSER_AUTH_OWNER_NOT_FOUND'
    settings = dict(owner=subject, user=row[0])
    x = with_erp_usage(cur, lambda: accessory.prepared(cur, today, wa, subject=subject, settings=settings, enabled=None, collect=False))
    assert wa.revision(cur) == 0, 'OW01_BROWSER_FIXTURE_MUST_NOT_PRESET_SETTINGS'
    assert _dispatch_count(cur, wa) == 0, 'OW01_BROWSER_FIXTURE_SENT_A_MESSAGE'
    return dict(proof=x, run_id=x['r']['run'], target_key=x['r']['target'], condition_key=x['key'],
                label=x['c']['label'], gross='186', no_WA_settings_written=True)


def browser_collect(cur, p, wa):
    x = p['proof']
    wa.b.api.admin(cur)
    row = cur.execute('select actor::text,kinds,enabled from cp7_alert_native.settings order by revision desc limit 1').fetchone()
    assert row and row[0] == x['s']['owner'] and row[1] == ['ACCESSORY_NEED'] and row[2], row
    ticks = wa.drain(cur)
    a = wa.alerts(cur, 'ACCESSORY_NEED')[x['key']]
    detail = accessory.assert_detail(a, x)
    accessory.original_unchanged(cur, x)
    pending = wa.outbox(cur, a['id'])
    assert len(pending) == 1 and pending[0]['state'] == 'PENDING', pending
    return dict(ticks=ticks, alert=a, detail=detail, outbox=pending)


def browser_source_proof(cur, p, wa):
    """No local preview records or rewritten analysis after the provider send."""
    x = p['proof']
    accessory.original_unchanged(cur, x)
    wa.b.api.admin(cur)
    counts = cur.execute('select (select count(*) from cp7_reminder_native.staged_claims where run_id=%s),'
                         '(select count(*) from cp7_reminder_native.staged_rechecks where run_id=%s)',
                         (x['r']['run'], x['r']['run'])).fetchone()
    assert counts == (0, 0), ('OW01_BROWSER_CREATED_LOCAL_PREVIEW_RECORDS', counts)
    return dict(original_unchanged=True, local_claims=counts[0], local_rechecks=counts[1])
