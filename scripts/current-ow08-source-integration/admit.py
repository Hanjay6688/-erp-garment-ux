"""Exact OW08 six-journey acceptance; retained money is not fresh money credit."""
from hashlib import sha256
from decimal import Decimal
import json, math

IDS = tuple(f'OW08_{family}_{width}' for family in
    ('KASBON_JOURNAL_SOURCE', 'UNKNOWN_WASH_SCREEN_PRICE', 'FG_INVERSE_QC_BLOCKERS')
    for width in ('DESKTOP', 'MOBILE'))
GATES = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')

def admit(pin, original, package, expected_source, runtime_files, parent_digest, backend_head, money_head, overlays, entrypoint):
    if pin is None:
        raise ValueError('OW08_INTEGRATION_CLOSED_ACTUAL_SOURCE6_REQUIRED')
    for name, raw in (('original', original), ('package', package)):
        assert len(raw) == pin[name]['bytes'] and sha256(raw).hexdigest() == pin[name]['sha256'], name
    actual, pkg = json.loads(original), json.loads(package)
    assert actual.get('label') == 'CP7_OW08_SOURCE_BROWSER6' and actual.get('status') == 'PASS'
    assert actual.get('qualification_commit') == pin['head']
    for key in ('cp6_restored', 'advisor_gate', 'baseline_full22_all_rows_all_sequences_equal',
                'baseline_advisors_equal', 'used_guard_refused_before_DDL', 'required_case_ids_pass', 'real_Auth_browser_claim'):
        assert actual.get(key) is True, key
    assert actual['actual_browser_cases'] == 6 and actual['retained_backend11_cases'] == 11
    assert actual['new_vendor_money_UI_qualified'] is False
    source = actual['source_declaration']
    assert source['status'] == 'EXACT_BACKEND_AND_DECLARED_CSS_SUCCESSOR_ADMITTED_NEW_OW08_SOURCE6'
    assert source['qualification'] == expected_source
    assert source['current_installation']['files'] == runtime_files
    assert sha256(json.dumps(source['current_installation']['predecessor'], sort_keys=True,
                            separators=(',', ':'), ensure_ascii=False).encode()).hexdigest() == parent_digest
    assert source['parent_backend_sha256'] == parent_digest
    assert source['prerequisite']['head'] == backend_head
    assert source['retained_money_browser']['head'] == money_head
    assert source['retained_money_browser']['backend_head'] == backend_head
    assert actual['production_go'] is False and actual['independent_acceptance'] is False
    assert actual['formal_CP7C_started'] is False and actual['actual_cron_claim'] is False
    assert source['full_OW08_acceptance'] is False
    assert source['scoped_paint_overlays'] == overlays
    assert source['current_installation_entrypoint'] == entrypoint
    assert source['retained_money_browser_repeated'] is False and source['B_combined_browser_repeated'] is False
    group = actual['committed']['OW08_SOURCE_BROWSER6']; browser = group['browser']
    assert group['status'] == 'PASS' and browser['counts'] == {'PASS': 6}
    assert browser['real_auth'] is True and browser['jwt_signed_by_runtime'] is False and browser['test_only_usage_grant'] is False
    assert browser['host_status'] == 'RUN_COMPLETE' and browser['host_exit'] == 0 and browser['console_errors'] == 0
    assert browser['auth_counts']['restored'] is True and browser['auth_counts']['before'] == browser['auth_counts']['after']
    assert browser['database_remaining'] == 0
    assert not any(browser.get(k) for k in ('cleanup_failures', 'auth_cleanup_failures', 'session_leaks'))
    assert len(group['copy_catalog_admissions']) == 1 and group['copy_catalog_admissions'][0]['all22_groups_equal_original_install'] is True
    assert browser['script_sha256'] == expected_source['files']['scripts/current-ow08-source-browser/cases.mjs']
    assert set(browser['cases']) == set(IDS) and set(browser['planned_case_ids']) == set(IDS)
    observations = {}
    for name in IDS:
        row = browser['cases'][name]
        assert row['status'] == 'PASS' and row['console_evidence']['unexpected_errors'] == []
        assert row['width']['page'] <= row['width']['viewport']
        assert row['width']['viewport'] == (390 if name.endswith('MOBILE') else 1440)
        assert row['visible_text_contrasts'] and row['shots']
        ratios = []
        for state in row['visible_text_contrasts']:
            assert state['rows']
            for v in state['rows']:
                ratio = v.get('ratio')
                assert isinstance(ratio, (int, float)) and math.isfinite(ratio) and ratio >= 4.5
                ratios.append(ratio)
        if 'KASBON' in name:
            for k in ('actual_real_Auth_public_source_RPC', 'actual_ledger_click_opens_given_and_cancelled_kasbon', 'all_business_rows_and_sequences_unchanged'):
                assert row[k] is True, k
            assert row['screen_creation_claim'] is False
            assert {r['document']['status'] for r in row['observed']} == {'GIVEN', 'CANCELLED'}
            assert len(row['observed']) == 2 and all(r['document']['domain'] == 'KASBON' for r in row['observed'])
        elif 'WASH' in name:
            for k in ('actual_screen_failed_attempt_unknown', 'unknown_is_not_zero', 'actual_screen_price_once', 'physical_unchanged_by_price', 'own_period_blocker_removed_after_price'):
                assert row[k] is True, k
            assert row['full_period_close_claim'] is False and row['actual_existing_finished_lot_recost_claim'] is False
            unknown, priced = row['unknown'], row['priced']
            assert unknown['line'] == [None, None, 'PENDING'] and priced['line'] == ['3.00', '30.00', 'ESTIMATED']
            assert unknown['physical'] == priced['physical']
            for amount in ('desired', 'accrued'):
                assert Decimal(priced['money'][amount]) - Decimal(unknown['money'][amount]) == Decimal('30.00')
            assert len(unknown['own_close_blockers']) == 1 and priced['own_close_blockers'] == []
            assert len(priced['price_rows']) == 1 and priced['price_rows'][0][0] == 'KNOWN'
            assert priced['price_rows'][0][3] is True and priced['price_rows'][0][4] is True
            assert [r['request']['p_action'] for r in row['writes']] == ['POST_FAILED_WASH', 'SET_FAILED_WASH_PRICE']
        else:
            for k in ('actual_QC_screen_names_sale_and_adjustment', 'blocked_QC_action_disabled', 'actual_inverse_FG_click_opens_same_reversed_adjustment', 'all_business_rows_and_sequences_unchanged'):
                assert row[k] is True, k
            assert row['screen_creation_or_QC_inverse_claim'] is False
            answer = row['source_response']
            assert answer['status'] == 'AVAILABLE' and answer['business_DML'] is False
            assert answer['document']['domain'] == 'FG_ADJUSTMENT' and answer['document']['status'] == 'REVERSED'
            assert row['positive_actor_role'] == 'OWNER'
            if name.endswith('MOBILE'):
                denied = row['admin_denial']
                assert denied['role'] == 'ADMIN' and denied['http_status'] == 403
                assert denied['body']['code'] == '42501'
                assert denied['body']['message'] == 'CP7_TRANSACTION_SOURCE_ACCESS_DENIED'
                assert denied['display_message'] == 'Akun tidak memiliki izin untuk operasi ini.'
                assert 'document' not in denied['body'] and denied['business_unchanged'] is True
                assert denied['console_evidence']['unexpected_errors'] == []
        observations[name] = dict(minimum_contrast=min(ratios), measurements=len(ratios), width=row['width'], screenshots=len(row['shots']))
    assert pkg['gate'] == {k: True for k in GATES}
    assert pkg['run_identity']['tool_head'] == pin['head'] and pkg['writer_runtime']['status'] == 'PASS'
    assert pkg['auth_users_before'] == pkg['auth_users_after']
    return dict(status='EXACT_ACTUAL_OW08_SOURCE6_ACCEPTABLE_TO_INTEGRATOR', head=pin['head'], fresh_browser=6,
                fresh_money_browser=0, retained_backend_cases=11, observations=observations,
                full_OW08_acceptance=False, production_go=False, independent_acceptance=False)
