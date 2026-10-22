"""OW14b: retain every WA99 control; add explicit fabric-rule acceptance on disposable Native copies.

Fabric master/receipt/cutting fixtures use the existing public/Native writers.
Direct administrative edits are labelled reference changes or current-account
revocation. No Enteng values, installed schedules or real WhatsApp messages.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import json
import time
import uuid
import psycopg
import cp7_wa_forward_cases as retained
import cp7_stock_formula_cases as formula

b, auth, master = formula.b, formula.auth, formula.master
CONTRACT = 'cp7.ow14b.fabric-rule.v1'
FUNCTIONS, SCHEDULES = retained.FUNCTIONS, retained.SCHEDULES
ADDED_IDS = dict(
    native=['OW14B_PREVIOUS_RULE_THEN_ONE_FORMULA', 'OW14B_PINNED_REFERENCE_OLD_CLIENT',
            'OW14B_CHANGED_REFERENCE_NO_APPEND', 'OW14B_REPLAY_IMMUTABLE_NO_SWITCH',
            'OW14B_ZERO_AND_UNKNOWN_DISTINCT', 'OW14B_CLOSED_SCOPE_AND_PRECISE_WIRE'],
    races=['OW14B_TWO_SESSIONS_ONE_UUID_AND_LIVE_MINIMUM', 'OW14B_TWO_USERS_ONE_REVISION',
           'OW14B_WAIT_CURRENT_OWNER_REVOKED', 'OW14B_WAIT_REPLAY_OWNER_REVOKED'],
    http=['OW14B_REAL_AUTH_CHOICE_AND_EXACT_REPLAY', 'OW14B_REAL_AUTH_REPLAY_CURRENT_REVOKE'],
    browser=['OW14B_BROWSER_DESKTOP_CHOICE_RELOAD_UUID', 'OW14B_BROWSER_MOBILE_CHOICE_RELOAD_CURRENT_ACCESS'],
)
IDS = {k: list(v) + ADDED_IDS[k] for k, v in retained.IDS.items()}
REQUIRED = {k: len(v) for k, v in IDS.items()}
EXPECTED = DECLARED = sum(REQUIRED.values())
assert REQUIRED == dict(native=61, races=34, http=7, browser=11) and EXPECTED == 113


def factory(cur, today, history=True, minimum='500'):
    f = formula.fabric(cur, 300, today-timedelta(days=40), minimum=minimum)
    oracle = None
    if history:
        formula.cut_days(cur, f, today, formula.SPARSE)
        settings = formula.one(cur, 'select cp7_stock_formula.current_settings()')
        offset = 30-int(settings['window_days'])
        oracle = formula.material_oracle(300-sum(formula.SPARSE[:offset]), formula.SPARSE[offset:], 6,
                                         level=settings['service_level'])
    return dict(f, oracle=oracle)


def payload(f, revision=0, rule='FORMULA', reference='500', lead='6'):
    return dict(material_id=f['material'], expected_revision=revision, lead_days=lead, manual_point=None,
                reason='OW14b explicit reviewed Native rule', fabric_rule=rule, expected_legacy_minimum_qty=reference)


def save(cur, p, key=None, subject=None):
    return formula.as_actor(cur, subject, 'select public.erp_cp7_save_material_reorder_v1(%s::jsonb,%s)',
                            (json.dumps(p), str(key or uuid.uuid4())))


def combined(cur, subject):
    b.api.admin(cur)
    cur.execute("select set_config('request.jwt.claims',%s,true),set_config('request.jwt.claim.sub','',true)",
                (json.dumps(dict(sub=subject, role='authenticated')),))
    cur.execute('set local role cp7_alert')
    r = formula.one(cur, 'select cp7_alert_native.fabric_kind_source()')
    cur.execute('reset role')
    b.api.admin(cur)
    return r


def mine(result, f):
    return [r for r in result['rows'] if r['subject_key'] == f['material']]


def revisions(cur, f):
    b.api.admin(cur)
    return formula.one(cur, 'select count(*) from cp7_stock_formula.material_settings where material_id=%s', (f['material'],))


def reference(cur, f, amount):
    # ADMINISTRATIVE_REFERENCE_CHANGE_ONLY, never edits a posted quantity/value.
    b.api.admin(cur)
    cur.execute('update erp.fabric_master_profiles set minimum_stock_qty=%s where material_id=%s', (amount, f['material']))


def cases(cur, today):
    def formula_choice():
        f = factory(cur, today)
        owner = master.role_actor(cur, 'OWNER')
        formula.save_material(cur, owner, f['material'], lead=6)
        e = formula.material_evaluation(cur, f['material'])
        assert e['fabric_rule'] is None and D(str(e['point'])) == 500, e
        before = formula.business(cur)
        result = save(cur, payload(f, revision=1), subject=owner)
        e = result['evaluation']
        assert result['revision'] == 2 and e['fabric_rule'] == 'FORMULA' and e['manual_point'] is None, result
        assert D(str(e['point'])) == f['oracle']['point'] and e['state'] == 'ABOVE', (e, f['oracle'])
        assert D(str(e['legacy_minimum_qty'])) == 500
        source = combined(cur, owner)
        assert not mine(source, f) and source['states'][f['material']] == 'ABOVE_REORDER_POINT', source
        assert formula.business(cur) == before
        return dict(status='PASS', independent_oracle=f['oracle'], legacy_reference=500,
                    active_formula_only=True, settings_do_not_write_Native_business=True)

    def pinned():
        f = factory(cur, today)
        owner = master.role_actor(cur, 'OWNER')
        save(cur, payload(f, rule='LEGACY_MINIMUM'), subject=owner)
        reference(cur, f, '600')
        formula.commitment(cur, today, f, 1000)
        before = formula.business(cur)
        formula.save_material(cur, owner, f['material'], lead=7)
        e = formula.material_evaluation(cur, f['material'])
        assert e['fabric_rule'] == 'LEGACY_MINIMUM' and D(str(e['point'])) == 500 and D(str(e['legacy_minimum_qty'])) == 600, e
        assert D(str(e['on_order_qty'])) == 1000 and e['state'] == 'AT_OR_BELOW', e
        own = mine(combined(cur, owner), f)
        assert len(own) == 1 and D(own[0]['detail']['reorder_point_qty']) == 500, own
        item = dict(own[0], kind='FABRIC_BELOW_MINIMUM')
        line = formula.one(cur, 'select cp7_alert_native.item_line(%s::jsonb,%s)', (json.dumps(item), 'AMOUNT'))
        assert 'minimum lama yang dipilih 500' in line and 'minimum rumus' not in line and 'dipesan' not in line, line
        long_item = dict(item, detail=dict(item['detail'], name='SYNTHETIC_LABEL_ONLY '*40))
        long_line = formula.one(cur, 'select cp7_alert_native.item_line(%s::jsonb,%s)', (json.dumps(long_item), 'AMOUNT'))
        assert len(long_line) <= 256 and long_line.endswith('minimum lama yang dipilih 500 YD'), long_line
        assert revisions(cur, f) == 2 and formula.business(cur) == before
        return dict(status='PASS', pinned=500, changed_reference=600, ordinary_open_PO=1000,
                    physical_stock_only=True, old_client_preserves_rule=True, one_reminder=True,
                    message_names_active_rule=True, synthetic_long_label_preserves_facts=True)

    def changed_reference():
        f = factory(cur, today, history=False)
        owner = master.role_actor(cur, 'OWNER')
        before = formula.business(cur)
        code, message = formula.refused(cur, lambda: save(cur, payload(f, reference='499'), subject=owner))
        assert (code, message) == ('40001', 'CP7_FORMULA_FABRIC_REFERENCE_CHANGED'), (code, message)
        bad = [dict(payload(f), fabric_rule='BOTH'), dict(payload(f), expected_legacy_minimum_qty=500),
               dict(payload(f), manual_point='500'), dict(payload(f), extra='x'), dict(payload(f), fabric_rule=None)]
        for p in bad:
            assert formula.refused(cur, lambda p=p: save(cur, p, subject=owner))[0] == '22023', p
        assert revisions(cur, f) == 0 and formula.business(cur) == before
        return dict(status='PASS', stale_reference_atomic=True, invalid_closed_shapes_refused=len(bad))

    def replay():
        f = factory(cur, today, history=False)
        owner = master.role_actor(cur, 'OWNER')
        p, key = payload(f, rule='LEGACY_MINIMUM'), uuid.uuid4()
        assert save(cur, p, key, owner)['revision'] == 1
        reference(cur, f, '600')
        before = formula.business(cur)
        result = save(cur, p, key, owner)
        assert result['replay'] is True and result['revision'] == 1, result
        assert formula.refused(cur, lambda: save(cur, dict(p, fabric_rule='FORMULA'), key, owner)) == ('22023', 'CP7_FORMULA_REQUEST_REUSED')
        assert formula.refused(cur, lambda: save(cur, dict(p, expected_revision=1), subject=owner)) == ('40001', 'CP7_FORMULA_FABRIC_REFERENCE_CHANGED')
        assert 'APPEND_ONLY' in formula.refused(cur, lambda: cur.execute('delete from cp7_stock_formula.material_settings where material_id=%s', (f['material'],)))[1]
        assert revisions(cur, f) == 1 and formula.business(cur) == before
        return dict(status='PASS', immutable_replay_before_reference_fence=True, changed_UUID_body_refused=True)

    def zero_unknown():
        owner = master.role_actor(cur, 'OWNER')
        zero = factory(cur, today, history=False, minimum='0')
        save(cur, payload(zero, rule='LEGACY_MINIMUM', reference='0'), subject=owner)
        reference(cur, zero, '500')
        unknown = factory(cur, today, history=False)
        save(cur, payload(unknown, lead=None), subject=owner)
        z, u = (formula.material_evaluation(cur, f['material']) for f in (zero, unknown))
        assert z['basis'] == 'MANUAL' and D(str(z['point'])) == 0 and z['state'] == 'NO_POINT', z
        assert u['fabric_rule'] == 'FORMULA' and u['point'] is None and u['state'] == 'NO_POINT', u
        source = combined(cur, owner)
        assert not mine(source, zero) and not mine(source, unknown), source
        return dict(status='PASS', chosen_zero_known=True, missing_formula_unknown=True, legacy_not_resurrected=True)

    def closed_scope():
        f = factory(cur, today, history=False)
        owner = master.role_actor(cur, 'OWNER')
        staff = formula.staff_with(cur, 'warehouse.material.view', 'master.fabric.view')
        assert formula.refused(cur, lambda: save(cur, payload(f, rule='LEGACY_MINIMUM'), subject=staff))[0] == '42501'
        a = formula.accessory(cur, today, 300)
        assert formula.refused(cur, lambda: save(cur, payload(a), subject=owner)) == ('22023', 'CP7_FORMULA_MATERIAL_INVALID')
        save(cur, payload(f, rule='LEGACY_MINIMUM'), subject=owner)
        w = formula.material_workspace(cur, owner, material_type='FABRIC', q=f['sku'])
        assert w['contract_version'] == 'cp7.material-reorder.v2', w
        row = next(x for x in w['page']['rows'] if x['material_id'] == f['material'])
        assert row['fabric_rule'] == 'LEGACY_MINIMUM', row
        for key in ('point', 'manual_point', 'legacy_minimum_qty'):
            assert isinstance(row[key], str) and D(row[key]) == 500, (key, row)
        for who in ('anon', 'authenticated', 'service_role'):
            assert not formula.one(cur, "select has_schema_privilege(%s,'cp7_stock_formula','USAGE')", (who,)), who
        return dict(status='PASS', read_only_staff_denied=True, accessory_scope_closed=True, exact_decimal_wire=True,
                    private_schema_stays_private=True)

    return retained.cases(cur, today) + list(zip(ADDED_IDS['native'], (formula_choice, pinned, changed_reference, replay, zero_unknown, closed_scope)))


def races(tools, today):
    def prepare(two=False):
        with tools.connect() as conn, conn.cursor() as cur:
            f = factory(cur, today, history=False)
            users = [master.role_actor(cur, 'OWNER')]
            if two:
                users.append(master.role_actor(cur, 'ADMIN'))
            conn.commit()
        return f, users

    def write(p, key, subject):
        with tools.connect() as conn, conn.cursor() as cur:
            try:
                result = save(cur, p, key, subject)
                conn.commit()
                return dict(result, code='COMMITTED')
            except psycopg.Error as error:
                conn.rollback()
                return dict(code=error.sqlstate, message=error.diag.message_primary)

    def same_uuid_live():
        f, users = prepare()
        p, key = payload(f, rule='LEGACY_MINIMUM'), uuid.uuid4()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: write(p, key, users[0]), range(2)))
        assert all(r['code'] == 'COMMITTED' for r in results) and sorted(r['replay'] for r in results) == [False, True], results
        with tools.connect() as holder, holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))")
            with tools.connect() as conn, conn.cursor() as cur:
                assert revisions(cur, f) == 1
                assert len(mine(combined(cur, users[0]), f)) == 1
                conn.commit()
            with tools.connect() as conn, conn.cursor() as cur:
                formula.receive_fabric(cur, f['material'], 200, today, location=f['location'], hour=0)
                conn.commit()
            with tools.connect() as conn, conn.cursor() as cur:
                assert not mine(combined(cur, users[0]), f), 'OW14B_BUSY_LEGACY_EQUALITY_MUST_RESOLVE'
                assert D(str(formula.material_evaluation(cur, f['material'])['free_qty'])) == 300, 'BUSY_READ_MUST_NOT_WRITE_CACHE'
                conn.rollback()
            holder.rollback()
        return dict(status='PASS', two_sessions_same_UUID_one_revision=True, actual_Native_receipt=200,
                    equality_500_resolves_strict_legacy=True, busy_live_read_does_not_write_cache=True)

    def competing():
        f, users = prepare(two=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda user: write(payload(f, rule='LEGACY_MINIMUM'), uuid.uuid4(), user), users))
        assert sorted(r['code'] for r in results) == ['40001', 'COMMITTED'], results
        with tools.connect() as conn, conn.cursor() as cur:
            assert revisions(cur, f) == 1
        return dict(status='PASS', current_revision_CAS_two_users=True)

    def revoke(replaying):
        f, users = prepare()
        p, key, actor = payload(f, rule='LEGACY_MINIMUM'), uuid.uuid4(), users[0]
        if replaying:
            assert write(p, key, actor)['code'] == 'COMMITTED'
        with tools.connect() as holder, holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))")
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(write, p, key, actor)
                waited = False
                try:
                    with tools.connect(autocommit=True) as observer, observer.cursor() as c:
                        deadline = time.monotonic()+8
                        while time.monotonic() < deadline:
                            waited = c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()"
                                               "and wait_event='advisory' and query like '%erp_cp7_save_material_reorder_v1%')").fetchone()[0]
                            if waited:
                                break
                            time.sleep(.03)
                    assert waited, 'OW14B_ACTUAL_FORMULA_WAIT_REQUIRED'
                    # ADMINISTRATIVE_CURRENT_ACCOUNT_REVOCATION, not a fake claims adapter.
                    with tools.connect() as conn, conn.cursor() as c:
                        c.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
                        conn.commit()
                finally:
                    holder.rollback()
                result = future.result(30)
        assert result['code'] == '42501', result
        with tools.connect() as conn, conn.cursor() as cur:
            assert revisions(cur, f) == (1 if replaying else 0)
        return dict(status='PASS', actual_advisory_wait=True, current_access_before_replay=True,
                    replaying=replaying, no_partial_or_second_revision=True)

    return retained.races(tools, today) + list(zip(ADDED_IDS['races'], (same_uuid_live, competing, lambda: revoke(False), lambda: revoke(True))))


def http_cases(http, today):
    def choice():
        owner = http.login('OWNER', 'ow14b-owner')
        with http.connect() as conn, conn.cursor() as cur:
            f = factory(cur, today)
            conn.commit()
        command = dict(p_payload=payload(f), p_request=str(uuid.uuid4()))
        first = owner.rpc('erp_cp7_save_material_reorder_v1', command)
        assert first['status'] == 200, first
        assert first['body']['evaluation']['fabric_rule'] == 'FORMULA'
        assert D(first['body']['evaluation']['point']) == f['oracle']['point'], (first, f['oracle'])
        replay = owner.rpc('erp_cp7_save_material_reorder_v1', command)
        assert replay['status'] == 200 and replay['body']['replay'] is True and replay['body']['revision'] == 1, replay
        second = owner.rpc('erp_cp7_save_material_reorder_v1', dict(p_payload=payload(f, revision=1, rule='LEGACY_MINIMUM'), p_request=str(uuid.uuid4())))
        assert second['status'] == 200 and second['body']['revision'] == 2 and D(second['body']['evaluation']['point']) == 500, second
        old = owner.rpc('erp_cp7_save_material_reorder_v1', command)
        assert old['status'] == 200 and old['body']['revision'] == 1, old
        args = dict(p_query=dict(material_type='FABRIC', q=f['sku']))
        w = owner.rpc('erp_cp7_get_material_reorder_v1', args)
        assert w['status'] == 200 and w['body']['contract_version'] == 'cp7.material-reorder.v2', w
        row = w['body']['page']['rows'][0]
        assert row['fabric_rule'] == 'LEGACY_MINIMUM' and isinstance(row['legacy_minimum_qty'], str), row
        anonymous = http.anon_rpc('erp_cp7_get_material_reorder_v1', args)
        assert anonymous['status'] in (401, 403), anonymous
        return dict(status='PASS', actual_Auth_and_PostgREST=True, two_policy_revisions_only=True,
                    old_UUID_reports_old_result_without_switching_current_rule=True, anon_denied=True)

    def revoke_replay():
        user = http.login('ADMIN', 'ow14b-revoked')
        with http.connect() as conn, conn.cursor() as cur:
            f = factory(cur, today, history=False)
            conn.commit()
        command = dict(p_payload=payload(f, rule='LEGACY_MINIMUM'), p_request=str(uuid.uuid4()))
        first = user.rpc('erp_cp7_save_material_reorder_v1', command)
        assert first['status'] == 200, first
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (user.auth_user_id,))
            conn.commit()
        replay = user.rpc('erp_cp7_save_material_reorder_v1', command)
        read = user.rpc('erp_cp7_get_material_reorder_v1', dict(p_query=dict(material_type='FABRIC', q=f['sku'])))
        assert replay['status'] == 403 and read['status'] == 403, (replay, read)
        with http.connect() as conn, conn.cursor() as cur:
            assert revisions(cur, f) == 1
        return dict(status='PASS', current_access_denies_even_committed_replay=True, one_revision=True)

    return retained.http_cases(http, today) + list(zip(ADDED_IDS['http'], (choice, revoke_replay)))
