"""OW16 real Native cutting, policy, concurrent users and Auth controls.

Masters/PO are administrative fixtures; receipt and every ordinary cutting
SAVE/POST use existing writers. Read status never writes stock, journals/HPP.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import copy
import json
import time
import uuid
import psycopg
import cp7_cutting_input_cases as inputs
import cp7_cutting_correction_cases as inverse
from cp7_ow16_status_install import verify

b, auth, e01 = inputs.b, inputs.auth, inputs.e01
CONTRACT = 'cp7.ow16.automatic-status.v1'
FUNCTIONS = ('erp_cp7_get_cutting_status_v1', 'erp_cp7_save_cutting_status_policy_v1',
             'erp_cp7_get_cutting_status_policy_request_v1')
IDS = dict(native=[
    'OW16_NO_GUESSED_POLICY', 'OW16_FACTORY_CURRENT_CONTEXT', 'OW16_LOW_HIGH_TOTAL_PCS',
    'OW16_READ_ONLY_NATIVE_FACTS', 'OW16_OWNER_POLICY_REPLAY_IMMUTABLE', 'OW16_INVALID_POLICY_ZERO_EFFECT',
    'OW16_PAUSED_INSUFFICIENT_UNPOSTED', 'OW16_NEGATIVE_LOOKUP_SEALS_REQUEST',
    'OW16_NATIVE_HISTORY_REOPEN_REPOST', 'OW16_PRIVATE_CATALOG_AND_CURRENT_ACCESS'],
    races=['OW16_WAIT_REVOKED_OWNER_REFUSED', 'OW16_TWO_OWNERS_ONE_REVISION'],
    http=['OW16_REAL_AUTH_FACTORY_STATUS_POLICY', 'OW16_REAL_AUTH_CURRENT_REVOKE'],
    browser=['OW16_BROWSER_DESKTOP_AUTO_AFTER_POST', 'OW16_BROWSER_MOBILE_UUID_RECOVERY'])
REQUIRED = {kind: len(keys) for kind, keys in IDS.items()}
EXPECTED = sum(REQUIRED.values())


def read(cur, group, subject=None):
    auth.actor(cur, subject)
    result = cur.execute('select public.erp_cp7_get_cutting_status_v1(%s)', (group,)).fetchone()[0]
    b.api.admin(cur)
    return result


def payload(revision='0', **changes):
    # Explicit fixture-only values; no production policy is installed by tests.
    return dict(expected_revision=revision, state='ACTIVE', coverage='0.8', min_groups='3',
                reason='OW16 fixture OWNER explicit reviewed policy', explicit_review=True, **changes)


def save(cur, value, request=None, subject=None, lookup=False):
    auth.actor(cur, subject)
    fn = FUNCTIONS[2] if lookup else FUNCTIONS[1]
    result = cur.execute('select public.'+fn+'(%s,%s)', (json.dumps(value), request or uuid.uuid4())).fetchone()[0]
    b.api.admin(cur)
    return result


def metadata(cur):
    b.api.admin(cur)
    return cur.execute('select (select count(*)from cp7_cutting_status.policies),'
                       '(select count(*)from cp7_cutting_status.requests)').fetchone()


def cutting(cur, f, pcs, consumed='10', existing=None, post=True):
    p = copy.deepcopy(f['cut_payload'])
    p['action'] = 'SAVE_DRAFT'
    p['rolls'] = [dict(roll_id=f['roll'], qty_issued=Decimal(consumed), qty_consumed=Decimal(consumed),
                       qty_reported_remaining=0, yields=[dict(slot_no=1, qty_pcs=pcs)])]
    version = None
    if existing:
        p['id'] = existing
        version = cur.execute('select row_version from erp.cutting_groups where id=%s', (existing,)).fetchone()[0]
    result = e01.prod.rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', p, expected_version=version)
    if post:
        p.update(id=result['cutting_group_id'], action='POST')
        result = e01.prod.rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', p,
                              expected_version=int(result['row_version']))
    b.api.admin(cur)
    return dict(group=result['cutting_group_id'], number=result['group_number'], payload=p,
                version=result['row_version'], po=f['po'], roll=f['roll'])


def factory(cur, today, current_pcs=40, current_consumed='10', draft=False):
    f = e01.production(cur, today, cutting_draft_only=True)
    # Administrative header fixture, before any cutting posts; not a claim
    # that a user creates this PO or its masters through the screen.
    cur.execute('update erp.production_orders set target_qty_pcs=10000 where id=%s', (f['po'],))
    first = cutting(cur, f, 20, existing=f['group'])
    history = [first, cutting(cur, f, 40), cutting(cur, f, 60)]
    current = cutting(cur, f, current_pcs, current_consumed, post=not draft)
    f.update(group=current['group'], group_number=current['number'], current=current, history=history)
    return f


def assessed(cur, f, status='WITHIN', low='20', high='60', subject=None, history=3):
    w = read(cur, f['group'], subject)
    assert w['scope'] == 'FACTORY' and not w['business_write']
    row = next(x for x in w['materials'] if x['material_id'] == f['material'])
    assert (row['status'], row['history_groups'], row['lower_pcs'], row['upper_pcs']) == \
           (status, str(history), low, high), row
    return w, row


def cases(cur, today):
    def no_policy():
        f = factory(cur, today)
        before = b.boundary.snapshot(cur)
        value = read(cur, f['group'])
        assert value['policy'] is None and value['materials'][0]['status'] == 'POLICY_REQUIRED'
        assert value['materials'][0]['history_groups'] == '3'
        assert value['materials'][0]['lower_pcs'] is None and metadata(cur) == (0, 0)
        assert b.boundary.snapshot(cur) == before
        return dict(status='PASS', no_activated_default=True, actual_Native_history_groups=3, no_business_or_metadata_write=True)

    def context():
        f = factory(cur, today)
        owner = inputs.custom_owner(cur)
        save(cur, payload(), subject=owner)
        w, row = assessed(cur, f, subject=owner)
        assert row['total_pcs'] == '40' and Decimal(row['consumed']) == 10
        assert row['size_ids'] == [e01.base.SIZE] and w['group']['posted']
        assert w['group']['pattern_id'] == e01.prod.PATTERN
        # A second real factory context uses another material. Its rows must
        # not enter this one's history, even though the pattern/size match.
        other = factory(cur, today)
        assert other['material'] != f['material']
        assessed(cur, f, subject=owner)
        return dict(status='PASS', ordinary_Native_cuts=True, history_shared_across_owner_accounts=True,
                    other_material_excluded=True, same_physical_time_known_before_target=True,
                    observed_total_pcs='40', range=['20', '60'])

    def totals():
        save(cur, payload())
        for actual, state, qty, lower, upper in [(19, 'LOW', '10', '20', '60'),
                                                (61, 'HIGH', '10', '20', '60'),
                                                (80, 'WITHIN', '20', '40', '120')]:
            f = factory(cur, today, actual, qty)
            _, row = assessed(cur, f, state, lower, upper)
            assert row['total_pcs'] == str(actual)
        return dict(status='PASS', actual_Native_total_pcs_low19_high61=True, double_consumption_range=['40', '120'],
                    no_per_size_or_per_roll_sample_inflation=True)

    def readonly():
        f = factory(cur, today)
        save(cur, payload())
        before = b.boundary.snapshot(cur)
        private = metadata(cur)
        for _ in range(3):
            assessed(cur, f)
        assert b.boundary.snapshot(cur) == before and metadata(cur) == private
        return dict(status='PASS', all_native_rows_stock_journals_hpp_unchanged=True, no_read_receipts_or_observation_captures=True)

    def policy():
        p, key = payload(), uuid.uuid4()
        before = b.boundary.snapshot(cur)
        first = save(cur, p, key)
        assert save(cur, p, key) == first and save(cur, p, key, lookup=True) == first
        assert first['policy']['revision'] == '1'
        auth.refused(cur, lambda: save(cur, dict(p, coverage='0.9'), key), 'CP7_CUTTING_STATUS_REQUEST_CHANGED')
        auth.refused(cur, lambda: save(cur, p), 'CP7_CUTTING_STATUS_POLICY_CHANGED')
        assert metadata(cur) == (1, 1)
        for table in ('policies', 'requests'):
            auth.refused(cur, lambda table=table: cur.execute('delete from cp7_cutting_status.'+table), 'CP7_CUTTING_STATUS_HISTORY_IMMUTABLE')
            auth.refused(cur, lambda table=table: cur.execute('truncate cp7_cutting_status.'+table), 'CP7_CUTTING_STATUS_HISTORY_IMMUTABLE')
        assert b.boundary.snapshot(cur) == before
        return dict(status='PASS', exact_UUID_replay=True, stale_revision_refused=True, original_policy_receipts_immutable=True)

    def invalid():
        p = payload()
        before = b.boundary.snapshot(cur)
        changes = [dict(coverage='0'), dict(coverage='1'), dict(coverage='NaN'), dict(coverage='0.1234567890123'),
                   dict(min_groups='0'), dict(min_groups='1000001'), dict(min_groups='3.5'),
                   dict(explicit_review=False), dict(reason=''), dict(expected_revision='9223372036854775807')]
        for delta in changes:
            auth.refused(cur, lambda delta=delta: save(cur, dict(p, **delta)), 'CP7_CUTTING_STATUS_POLICY_REVIEW')
        auth.refused(cur, lambda: save(cur, dict(p, actual_pcs='100')), 'CP7_WIP_FIELDS')
        assert metadata(cur) == (0, 0) and b.boundary.snapshot(cur) == before
        return dict(status='PASS', invalid_payloads_refused=len(changes)+1, zero_partial_policy_or_request=True)

    def states():
        f = factory(cur, today)
        save(cur, dict(payload(), min_groups='4'))
        assessed(cur, f, 'INSUFFICIENT_HISTORY', None, None)
        save(cur, dict(payload('1'), state='PAUSED'))
        assessed(cur, f, 'POLICY_PAUSED', None, None)
        draft = factory(cur, today, draft=True)
        assessed(cur, draft, 'NOT_FINISHED', None, None)
        return dict(status='PASS', insufficient_not_zero=True, paused_not_normal=True, actual_unposted_draft_never_physical_completion=True)

    def negative():
        key, p = uuid.uuid4(), payload()
        missing = save(cur, p, key, lookup=True)
        assert missing['status'] == 'NOT_COMMITTED' and missing['policy'] is None
        assert save(cur, p, key) == missing and metadata(cur) == (0, 1)
        return dict(status='PASS', negative_lookup_permanently_seals_UUID=True, no_late_new_policy_effect=True)

    def correction():
        f = factory(cur, today)
        save(cur, payload())
        assessed(cur, f)
        historical = dict(f, group=f['history'][0]['group'])
        p, version = inverse.payload(cur, historical)
        reopened = inverse.command(cur, p, version)
        assert reopened['status'] == 'DRAFT_FOR_CORRECTION'
        assessed(cur, f, 'INSUFFICIENT_HISTORY', None, None, history=2)
        cutting(cur, f, 20, existing=historical['group'])
        assessed(cur, f)
        return dict(status='PASS', actual_public_Native_reopen_removes_historical_group=True,
                    actual_public_Native_repost_restores_group=True, current_status_recomputed_without_manual_capture=True)

    def boundary():
        verify(cur)
        f = factory(cur, today)
        subject = inputs.custom_owner(cur)
        save(cur, payload(), subject=subject)
        assessed(cur, f, subject=subject)
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (subject,))
        auth.refused(cur, lambda: read(cur, f['group'], subject), 'CP7_ACCESS_DENIED')
        auth.refused(cur, lambda: save(cur, payload('1'), subject=subject), 'CP7_ACCESS_DENIED')
        return dict(status='PASS', every_exact_body_owner_acl_RLS_trigger_verified=True, no_Native_DML=True,
                    current_deactivation_refuses_status_and_policy=True)

    result = list(zip(IDS['native'], (no_policy, context, totals, readonly, policy, invalid, states, negative, correction, boundary)))
    assert len(result) == REQUIRED['native']
    return result


def races(tools, today):
    def revoked():
        with tools.connect() as conn, conn.cursor() as cur:
            subject = inputs.custom_owner(cur)
            conn.commit()
        key, p = uuid.uuid4(), payload()
        with tools.connect() as holder, holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_STATUS_FACTORY_POLICY',0))")
            def call():
                with tools.connect() as conn, conn.cursor() as cur:
                    try:
                        r = save(cur, p, key, subject)
                        conn.commit()
                        return r
                    except psycopg.Error as error:
                        conn.rollback()
                        return dict(code=error.sqlstate, message=str(error))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(call)
                waited = False
                try:
                    with tools.connect(autocommit=True) as inspect, inspect.cursor() as c:
                        deadline = time.monotonic()+8
                        while time.monotonic() < deadline:
                            waited = c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()"
                                               "and wait_event='advisory'and query like '%erp_cp7_save_cutting_status_policy_v1%')").fetchone()[0]
                            if waited: break
                            time.sleep(.03)
                    assert waited, 'OW16_ACTUAL_POLICY_WAIT_REQUIRED'
                    with tools.connect() as conn, conn.cursor() as c:
                        c.execute('update erp.app_users set is_active=false where auth_user_id=%s', (subject,))
                        conn.commit()
                finally:
                    holder.rollback()
                result = future.result(30)
        assert result.get('code') == '42501' and 'CP7_ACCESS_DENIED' in result.get('message', ''), result
        with tools.connect() as conn, conn.cursor() as cur:
            assert metadata(cur) == (0, 0)
        return dict(status='PASS', observed_advisory_wait=True, current_owner_deactivation_denied_after_wait=True, no_partial_rows=True)

    def same_revision():
        with tools.connect() as conn, conn.cursor() as cur:
            users = [inputs.custom_owner(cur), inputs.custom_owner(cur)]
            conn.commit()
        def write(subject):
            with tools.connect() as conn, conn.cursor() as cur:
                try:
                    r = save(cur, payload(), subject=subject)
                    conn.commit()
                    return r['status']
                except psycopg.Error as error:
                    conn.rollback()
                    return error.sqlstate
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, users))
        assert sorted(results) == ['40001', 'COMMITTED'], results
        with tools.connect() as conn, conn.cursor() as cur:
            assert metadata(cur) == (1, 1)
        return dict(status='PASS', two_real_owner_sessions=True, one_policy_one_stale_refusal=True)

    return list(zip(IDS['races'], (revoked, same_revision)))


def http_cases(http, today):
    def flow():
        user = http.login('OWNER', 'ow16-owner')
        admin = http.login('ADMIN', 'ow16-admin')
        with http.connect() as conn, conn.cursor() as cur:
            f = factory(cur, today)
            conn.commit()
        args = dict(p_group=f['group'])
        r = user.rpc(FUNCTIONS[0], args)
        assert r['status'] == 200 and r['body']['materials'][0]['status'] == 'POLICY_REQUIRED', r
        command = dict(p_payload=payload(), p_request=str(uuid.uuid4()))
        r = user.rpc(FUNCTIONS[1], command)
        assert r['status'] == 200 and r['body']['status'] == 'COMMITTED', r
        assert user.rpc(FUNCTIONS[2], command)['body'] == r['body']
        r = user.rpc(FUNCTIONS[0], args)
        assert r['status'] == 200 and r['body']['materials'][0]['status'] == 'WITHIN', r
        assert admin.rpc(FUNCTIONS[0], args)['status'] == 200
        assert admin.rpc(FUNCTIONS[1], dict(p_payload=payload('1'), p_request=str(uuid.uuid4())))['status'] == 403
        assert http.anon_rpc(FUNCTIONS[0], args)['status'] in (401, 403)
        return dict(status='PASS', actual_GoTrue_PostgREST=True, factory_status_and_policy=True,
                    same_UUID_lookup=True, admin_reads_not_writes=True, anonymous_closed=True)

    def revoked():
        user = http.login('OWNER', 'ow16-revoked')
        with http.connect() as conn, conn.cursor() as cur:
            f = factory(cur, today)
            revision = cur.execute('select max(revision)from cp7_cutting_status.policies').fetchone()[0] or 0
            conn.commit()
        command = dict(p_payload=payload(str(revision)), p_request=str(uuid.uuid4()))
        assert user.rpc(FUNCTIONS[1], command)['status'] == 200
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (user.auth_user_id,))
            before = metadata(cur)
            conn.commit()
        assert user.rpc(FUNCTIONS[0], dict(p_group=f['group']))['status'] == 403
        assert user.rpc(FUNCTIONS[2], command)['status'] == 403
        with http.connect() as conn, conn.cursor() as cur:
            assert metadata(cur) == before
        return dict(status='PASS', real_existing_access_token_current_deactivation=True, replay_and_status_denied=True, no_extra_rows=True)

    return list(zip(IDS['http'], (flow, revoked)))
