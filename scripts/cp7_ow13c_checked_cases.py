"""Four Native checked-save cases, two actual Auth cases, retained19 unchanged.

Retained race/browser controls are OW10 only, NOT checked-save race/browser
qualification. This suite cannot close OW13c or claim the whole A chain.
"""
import copy
import json
import uuid
import cp7_ow10_reorder_cases as retained
import cp7_p19_plan_v2_cases as plan
import cp7_cutting_checked_save as checked
from cp7_ow04_restore_bundle import _catalog_rows

CONTRACT = 'cp7.ow13c.checked-save-native.v1'
NEW_NATIVE = ['OW13C_NATIVE_FRESH_SAVE_REPLAY_AND_NO_PHYSICAL_FACT',
              'OW13C_NATIVE_STALE_REFUSED_OLD_ARCHIVE_SAVE_UNCHANGED',
              'OW13C_NATIVE_OLD_UUID_CANNOT_BECOME_CHECKED',
              'OW13C_NATIVE_USED_RECEIPT_BLOCKS_INVERSE_BEFORE_DDL']
NEW_HTTP = ['OW13C_HTTP_REAL_AUTH_SAVE_REPLAY', 'OW13C_HTTP_CURRENT_ACCESS_AND_ANON']
IDS = {k: list(v) for k, v in retained.IDS.items()}
IDS['native'] += NEW_NATIVE
IDS['http'] += NEW_HTTP
REQUIRED = {k: len(v) for k, v in IDS.items()}
EXPECTED = DECLARED = sum(REQUIRED.values())
assert REQUIRED == dict(native=15, races=4, http=4, browser=2) and EXPECTED == 25
FUNCTIONS = (*retained.FUNCTIONS, 'erp_cp7_save_cutting_suggestion_v1')
SCHEDULES = retained.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE = {}, {}, {}


def payload(x):
    return dict(copy.deepcopy(x['payload']), cutting_save_contract='cp7.cutting-checked-save.v1')


def save(cur, p, request=None, subject=None):
    return plan.rpc(cur, 'erp_cp7_save_cutting_suggestion_v1',
                    (json.dumps(p), request or uuid.uuid4()), subject)


def receipt_count(cur):
    plan.b.api.admin(cur)
    return cur.execute('select count(*)from cp7_cutting_checked.receipts').fetchone()[0]


def cases(cur, today):
    retained.INSTALL_STATES, retained.REORDER_STATES = INSTALL_STATES, REORDER_STATES

    def fresh():
        x = plan.single(cur, today)
        key, p = str(uuid.uuid4()), payload(x)
        before = plan.monetary_state(cur)
        result = save(cur, p, key)
        assert result['contract_version'] == 'cp7.plan-draft.v2' and result['cutting_save_guard']['feasible'] is True, result
        assert result['cutting_save_guard']['target_key'] == x['target']
        assert save(cur, p, key) == result
        plan.refused(cur, lambda: save(cur, dict(p, reason='changed same UUID'), key), 'CP7_PLAN_REQUEST_CHANGED')
        assert receipt_count(cur) == 1 and plan.monetary_state(cur) == before
        assert plan.read(cur, result['draft_id'])['state'] == 'SAVED'
        return dict(status='PASS', actual_Native_staged_source_preflight_and_writer=True,
                    exact_UUID_replay=True, no_stock_money_or_physical_posting=True)

    def stale():
        x = plan.single(cur, today)
        plan.found_fg(cur, x, '1')
        before = plan.monetary_state(cur)
        plan.refused(cur, lambda: save(cur, payload(x)), 'CP7_CUTTING_SUGGESTION_SOURCE_CHANGED', '40001')
        assert receipt_count(cur) == 0 and plan.monetary_state(cur) == before
        assert plan.save(cur, x['payload'])['state'] == 'SAVED'
        return dict(status='PASS', actual_stock_writer_invalidates_checked_SAVE=True,
                    old_dated_archive_SAVE_preserved=True)

    def old_uuid():
        x = plan.single(cur, today)
        key = str(uuid.uuid4())
        original = plan.save(cur, x['payload'], key)
        plan.refused(cur, lambda: save(cur, payload(x), key), 'CP7_PLAN_REQUEST_CHANGED')
        assert receipt_count(cur) == 0 and plan.read(cur, original['draft_id'])['state'] == 'SAVED'
        return dict(status='PASS', old_UUID_never_relabelled_as_checked=True)

    def used():
        x = plan.single(cur, today)
        save(cur, payload(x))
        plan.b.api.admin(cur)
        before = _catalog_rows(cur)
        try:
            checked.rollback_preuse(cur, CHECKED_STATE)
        except ValueError as error:
            assert str(error) == 'OW13C_CHECKED_SAVE_AFTER_USE_REQUIRES_BACKUP_RESTORE'
        else:
            raise AssertionError('OW13C_AFTER_USE_INVERSE_ALLOWED')
        assert _catalog_rows(cur) == before and receipt_count(cur) == 1
        return dict(status='PASS', actual_receipt_marker_refused_before_DDL=True)

    return retained.cases(cur, today)+list(zip(NEW_NATIVE, [fresh, stale, old_uuid, used]))


def races(tools, today):
    return retained.races(tools, today)


def http_cases(http, today):
    def prepare(label):
        user = http.login('OWNER', label)
        with http.connect() as conn, conn.cursor() as cur:
            x = plan.single(cur, today, subject=user.auth_user_id)
            conn.commit()
        return user, dict(p_payload=payload(x), p_request=str(uuid.uuid4()))

    def flow():
        user, args = prepare('ow13c-checked-owner')
        first = user.rpc('erp_cp7_save_cutting_suggestion_v1', args)
        replay = user.rpc('erp_cp7_save_cutting_suggestion_v1', args)
        assert first['status'] == replay['status'] == 200, (first, replay)
        assert first['body'] == replay['body'] and first['body']['cutting_save_guard']['feasible'] is True
        return dict(status='PASS', actual_Auth_PostgREST_checked_SAVE_and_exact_replay=True)

    def denied():
        user, args = prepare('ow13c-revoked-owner')
        first = user.rpc('erp_cp7_save_cutting_suggestion_v1', args)
        assert first['status'] == 200, first
        assert http.anon_rpc('erp_cp7_save_cutting_suggestion_v1', args)['status'] in (401, 403)
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (user.auth_user_id,))
            conn.commit()
        assert user.rpc('erp_cp7_save_cutting_suggestion_v1', args)['status'] == 403
        return dict(status='PASS', actual_old_token_revoked_replay_refused=True, anonymous_refused=True)

    return retained.http_cases(http, today)+list(zip(NEW_HTTP, [flow, denied]))
