"""Native inactive-document episode qualification plus the retained E01 bridge.

No Native monetary/stock outcome is inserted. The missing-source check is an
explicit private-reader fault control; its original definition is restored.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import uuid
import psycopg
import cp7_p18_e01_bridge_cases as bridge
import cp7_rule_source_cases as rules
import cp7_receipt_correction_cases as correction

ap, auth, b = rules.ap, rules.auth, rules.b
REQUIRED = dict(native=10, races=2, http=2, browser=2)
EXPECTED = sum(REQUIRED.values())


def prepared(cur, today):
    f, e = ap.prepared(cur, today)
    posted = ap.finalize(cur, f, today)
    key = 'AP_DUE:MATERIAL:' + f['receipt']['purchase_id']
    first = rules.observation(rules.observe(cur, e), key)
    assert first['condition']['economic_state'] == 'OPEN'
    assert first['episode']['state'] == 'ACTIVE'
    return f, e, key, first['episode'], posted


def replace(cur, f):
    w = correction.ws(cur, f['receipt']['purchase_id'])
    assert w['can_correct'], w
    p = dict(correction.payload(w), invoices=correction.invoices(w, price='24'))
    return correction.fix(cur, p, w['purchase']['row_version'])


def archived(cur, e, key, first):
    before = b.boundary.snapshot(cur)
    result = rules.observe(cur, e)
    row = rules.observation(result, key)
    episode = row['episode']
    assert row['transition'] == 'ARCHIVED_INACTIVE_DOCUMENT', row
    assert row['condition']['economic_state'] == 'INACTIVE'
    assert not row['condition']['business_resolved']
    assert episode['id'] == first['id'] and episode['state'] == 'ARCHIVED'
    assert episode['resolved_at'] is None and episode['archived_at'] == episode['last_observed_at']
    assert episode['first_observed_at'] == first['first_observed_at']
    assert b.boundary.snapshot(cur) == before
    auth.refused(cur, lambda: cur.execute(
        "update cp7_reminder_native.rule_episodes set state='ACTIVE',archived_at=null where id=%s",
        (episode['id'],)), 'CP7_RULE_EPISODE_IMMUTABLE')
    return result


def cases(cur, today):
    def reversed():
        f, e, key, first, invoice = prepared(cur, today)
        ap.invoice.reverse(cur, f, invoice['invoice_id'])
        pending = rules.observation(rules.observe(cur, e), key)
        assert pending['episode']['id'] == first['id'] and pending['episode']['state'] == 'ACTIVE'
        assert pending['episode']['freshness'] == 'UNKNOWN' and not pending['condition']['business_resolved']
        d = ap.invoice.receipt.workspace(cur, dict(purchase_id=f['receipt']['purchase_id']))['detail']
        ap.invoice.receipt.command(cur, 'REVERSE', dict(purchase_id=d['id'], change_reason='Wrong receipt reversed through owning command'), version=d['row_version'])
        archived(cur, e, key, first)
        return dict(status='PASS', Native_invoice_inverse_pending_not_paid=True,
                    Native_receipt_inverse_archives_exact_episode_not_debt_settlement=True)

    def corrected():
        f, e, key, first, _ = prepared(cur, today)
        out = replace(cur, f)
        result = archived(cur, e, key, first)
        new_key = 'AP_DUE:MATERIAL:' + out['purchase_id']
        new = rules.observation(result, new_key)
        assert new_key != key and new['episode']['id'] != first['id']
        assert new['episode']['number'] == '1' and new['episode']['state'] == 'ACTIVE'
        assert new['condition']['financial_source']['remaining']['value'] == '480.00'
        return dict(status='PASS', Native_correction500_to480_old_archived_new_source_episode=True,
                    old_first_observed_identity_and_history_immutable=True)

    def paid():
        f, e, key, first, _ = prepared(cur, today)
        payment = ap.payment(cur, f, today, '500')
        row = rules.observation(rules.observe(cur, e), key)
        assert row['episode']['id'] == first['id'] and row['episode']['state'] == 'RESOLVED'
        assert row['episode']['resolved_at'] == row['episode']['last_observed_at']
        assert 'archived_at' not in row['episode'] and row['condition']['business_resolved']
        ap.inverse(cur, payment)
        reopened = rules.observation(rules.observe(cur, e), key)
        assert reopened['transition'] == 'REOPENED_NEW_EPISODE'
        assert reopened['episode']['number'] == '2' and reopened['episode']['previous_id'] == first['id']
        return dict(status='PASS', actual_payment_resolves_and_inverse_reopens_linked_episode=True)

    def missing():
        f, e, key, first, _ = prepared(cur, today)
        before = b.boundary.snapshot(cur)
        definition = cur.execute("select pg_get_functiondef('cp7_reminder_native.payable_source()'::regprocedure)").fetchone()[0]
        try:
            cur.execute(definition.replace('cp7_reminder_native.payable_source()', 'cp7_reminder_native.lifecycle_actual_ap_source()'))
            cur.execute("""create or replace function cp7_reminder_native.payable_source()returns jsonb
                language plpgsql stable security invoker set search_path='' as $$declare s jsonb;v jsonb;begin
                s:=cp7_reminder_native.lifecycle_actual_ap_source();
                select coalesce(jsonb_agg(x),'[]')into v from jsonb_array_elements(s->'rows')x
                where x->'liability'->>'purchase_id'<>%s;
                return s||jsonb_build_object('rows',v,'total',jsonb_array_length(v)::text);end$$""".replace('%s', "'" + f['receipt']['purchase_id'] + "'"))
            result = rules.observe(cur, e)
            assert all(r['condition']['key'] != key for r in result['result']['rows'])
            assert cur.execute('select state,archived_at,resolved_at from cp7_reminder_native.rule_episodes where id=%s',
                               (first['id'],)).fetchone() == ('ACTIVE', None, None)
        finally:
            cur.execute(definition)
            cur.execute('drop function cp7_reminder_native.lifecycle_actual_ap_source()')
        assert b.boundary.snapshot(cur) == before
        return dict(status='PASS', fixture_kind='EXPLICIT_PRIVATE_READER_MISSING_SOURCE_FAULT',
                    absence_never_archives_or_resolves_actual_Native_AP_episode=True)

    def recovery():
        f, e, key, first, _ = prepared(cur, today)
        replace(cur, f)
        s = rules.source(cur, e)
        p = dict(run_id=e['run_id'], source_hash=s['source_hash'])
        request = uuid.uuid4()
        result = rules.command(cur, 'EPISODES', p, request)
        assert rules.observation(result, key)['episode']['state'] == 'ARCHIVED'
        count = rules.counts(cur)
        assert rules.command(cur, 'EPISODES', p, request, lookup=True)['result'] == result['result']
        assert rules.command(cur, 'EPISODES', p, request)['result'] == result['result']
        assert rules.counts(cur) == count
        actor = result['actor_scope_id']
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
        auth.refused(cur, lambda: rules.command(cur, 'EPISODES', p, request, lookup=True), 'CP7_REMINDER_ACCESS_DENIED')
        return dict(status='PASS', archived_exact_UUID_lost_reply_replay_no_extra_observation=True,
                    current_revoke_before_cached_archived_receipt=True)

    return bridge.cases(cur, today) + [('P16_LIFECYCLE_' + name, fn) for name, fn in (
        ('INVOICE_AND_RECEIPT_INVERSE', reversed), ('CORRECTED_REPLACEMENT', corrected),
        ('PAID_AND_PAYMENT_INVERSE', paid), ('MISSING_SOURCE_UNKNOWN', missing), ('REPLAY_CURRENT_REVOKE', recovery))]


def races(tools, today):
    def correction_wait():
        with tools.connect() as conn, conn.cursor() as cur:
            f, e, key, first, _ = prepared(cur, today)
            source = rules.source(cur, e)
            p = dict(run_id=e['run_id'], source_hash=source['source_hash'])
            request = uuid.uuid4()
            conn.commit()
        with tools.connect() as holder, holder.cursor() as held:
            held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0))")
            def send():
                try:
                    with tools.connect() as conn, conn.cursor() as cur:
                        result = rules.command(cur, 'EPISODES', p, request)
                        conn.commit()
                        return result
                except psycopg.Error as error:
                    return error.sqlstate, str(error).split('\n', 1)[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                job = pool.submit(send)
                try:
                    rules.wait_for(tools, 'erp_cp7_evaluate_rule_episodes_v1')
                    with tools.connect() as conn, conn.cursor() as cur:
                        replace(cur, f)
                        conn.commit()
                finally:
                    holder.rollback()
                outcome = job.result(90)
        assert outcome == ('40001', 'CP7_RULE_EPISODE_SOURCE_CHANGED'), outcome
        with tools.connect() as conn, conn.cursor() as cur:
            assert cur.execute('select count(*)from cp7_reminder_native.requests where request_id=%s', (request,)).fetchone()[0] == 0
            archived(cur, e, key, first)
            conn.commit()
        return dict(status='PASS', actual_observed_episode_lock_wait_Native_correction=True,
                    stale_source_refused_no_receipt_fresh_observation_archives=True)
    return bridge.races(tools, today) + [('P16_LIFECYCLE_RACE_CORRECTION_WAIT', correction_wait)]


def http_cases(http, today):
    def corrected():
        owner = http.login('OWNER', 'p16-lifecycle-archive')
        with http.connect() as conn, conn.cursor() as cur:
            f, _, _, _, _ = prepared(cur, today)
            conn.commit()
        response = owner.rpc('erp_cp7_capture_analysis_v1', dict(p_query=bridge.analysis.previous.baseline.history.query(today), p_request=str(uuid.uuid4())))
        assert response['status'] == 200, response
        e = response['body']
        def observe(request=None, lookup=False):
            s = owner.rpc('erp_cp7_get_rule_conditions_v1', dict(p_run=e['run_id']))
            assert s['status'] == 200, s
            args = dict(p_payload=dict(run_id=e['run_id'], source_hash=s['body']['source_hash']), p_request=request or str(uuid.uuid4()))
            result = owner.rpc('erp_cp7_get_rule_episode_request_v1' if lookup else 'erp_cp7_evaluate_rule_episodes_v1', args)
            assert result['status'] == 200, result
            return result['body'], args
        first, _ = observe()
        key = 'AP_DUE:MATERIAL:' + f['receipt']['purchase_id']
        episode = rules.observation(first, key)['episode']
        with http.connect() as conn, conn.cursor() as cur:
            out = replace(cur, f)
            conn.commit()
        result, args = observe()
        old = rules.observation(result, key)
        assert old['episode']['id'] == episode['id'] and old['episode']['state'] == 'ARCHIVED'
        assert not old['condition']['business_resolved'] and old['episode']['resolved_at'] is None
        assert rules.observation(result, 'AP_DUE:MATERIAL:' + out['purchase_id'])['episode']['state'] == 'ACTIVE'
        replay = owner.rpc('erp_cp7_get_rule_episode_request_v1', args)
        assert replay['status'] == 200 and replay['body']['result'] == result['result']
        assert http.anon_rpc('erp_cp7_get_rule_episode_request_v1', args)['status'] in (401, 403)
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner.auth_user_id,))
            conn.commit()
        assert owner.rpc('erp_cp7_get_rule_episode_request_v1', args)['status'] == 403
        return dict(status='PASS', actual_Auth_HTTP_archived_not_paid_replacement_active=True,
                    exact_lost_reply_anonymous_and_current_revoke=True)
    return bridge.http_cases(http, today) + [('P16_LIFECYCLE_HTTP_ARCHIVED_CURRENT_AUTH', corrected)]
