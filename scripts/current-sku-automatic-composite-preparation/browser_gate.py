"""Read complete current browser Originals, unchanged cleanup, and real assets.

The retained typed copy checks use Nonpayable's row names. Five reversible
field routes select the current SKU journey's actual evidence. They do not
rewrite a result. Full observation and economic checks are required below.
"""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import importlib.util
import json
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDS = ('SKU_CURRENT_MOVAVG_DESKTOP_REAL_AUTH_PAIR_VALUE_RECOVERY_INVERSE',
       'SKU_CURRENT_MOVAVG_MOBILE390_REAL_AUTH_PAIR_VALUE_GUARDS_INVERSE')
LABEL = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER2'
TYPED = ROOT / 'scripts/cp7_accessory_nonpayable/qualification_gate.py'
TYPED_PIN = dict(bytes=4826, sha256='c0647aeb14b09cd179c7f977c2c60c70434dc3afcd91a66755229e5de353482c')
ROUTES = (('normal_App_menu', 'actual_Auth_form_normal_full_App'),
          ('real_Auth', 'actual_public_PostgREST'),
          ('visuals', 'visible_text_contrast'),
          ('complete_census_proofs', 'current_observations'),
          ('all_stock_HPP_journals_entitlements_and_existing_history_unchanged', 'Native_financial_accounts_restored'))


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def typed():
    raw = TYPED.read_bytes();require(pin(raw) == TYPED_PIN, 'CURRENT_BROWSER_EXACT_WHOLE_TYPED_COPY_GATE')
    text = raw.decode()
    for before, after in ROUTES:
        old, new = "row.get('" + before + "')", "row.get('" + after + "')"
        require(text.count(old) == 1 and new not in text, 'CURRENT_BROWSER_ONE_ACTUAL_EVIDENCE_FIELD_ROUTE')
        text = text.replace(old, new, 1)
    restored = text
    for before, after in reversed(ROUTES):
        restored = restored.replace("row.get('" + after + "')", "row.get('" + before + "')", 1)
    require(restored.encode() == raw, 'CURRENT_BROWSER_WHOLE_COPY_GATE_NOT_RECOVERED')
    namespace = {}
    exec(compile(text, str(TYPED) + '::current-browser-fields', 'exec', dont_inherit=True), namespace)
    return namespace['copies'], dict(retained=TYPED_PIN, field_routes=len(ROUTES),
        complete_original_recovered=True, all_copy_Auth_session_cleanup_checks_preserved=True,
        original_results_not_projected=True)


def copy_source():
    original = ROOT / 'scripts/ow04-payment-current-qualification/copy_authority.py'
    raw = original.read_bytes()
    require(pin(raw) == dict(bytes=3895, sha256='cfdc3b899e335dd13a9456242ed5158b718ac5c56d9b1ebf06c4571eda2cc7a2'),
            'CURRENT_BROWSER_EXACT_COMPLETE_COPY_AUTHORITY')
    before = "assert name in('cp6_auditor_browser','cp6_auditor_http')"
    after = "assert name in('cp6_auditor_browser','cp6_auditor_http','cp6_auditor_race')"
    text = raw.decode();require(text.count(before) == 1 and after not in text, 'CURRENT_BROWSER_ONE_FIXED_COPY_NAME_EXTENSION')
    derived = text.replace(before, after, 1)
    require(derived.replace(after, before, 1).encode() == raw, 'CURRENT_BROWSER_COMPLETE_COPY_AUTHORITY_NOT_RECOVERED')
    return dict(original_bytes=len(raw), original_sha256=sha256(raw).hexdigest(),
        derived_sha256=sha256(derived.encode()).hexdigest(), exact_copy_name_extension_count=1,
        original_bytes_recovered=True, all_raw22_authority_checks_unchanged=True,
        product_or_schema_or_RPC_grants_added=False, actual_case_credit=0)


def validate(p, actual, part, head, source):
    require(actual.get('synthetic_receipt_not_an_actual_qualification') is not True,
            'CURRENT_BROWSER_SYNTHETIC_ORIGINAL_REFUSED')
    check, proof = typed()
    result = check(actual, IDS, mode='BROWSER')
    p.exact(part['current_browser_gate'], result, 'CURRENT_BROWSER_COMPLETE_TYPED_COPY_RESULT')
    copies = part['current_browser_copy_authority']
    p.exact(copies['source'], copy_source(), 'CURRENT_BROWSER_COMPLETE_ORIGINAL_COPY_AUTHORITY')
    require(type(copies['actual_copy_admissions']) is list and len(copies['actual_copy_admissions']) == 1,
            'CURRENT_BROWSER_ONE_REAL_AUTH_COPY')
    p.fields(copies['actual_copy_admissions'][0], dict(all22_groups_equal_original_install=True,
        product_state_modified=False, Native_or_schema_or_RPC_permissions_changed=False),
        'CURRENT_BROWSER_ALL22_AND_CURRENT_PRODUCT_AUTHORITY')
    prepare = module('current_browser_final_full_journey_derivation', HERE / 'browser_prepare.py')
    text, derived = prepare.derive()
    p.exact(part['current_browser_journey_derivation'], derived, 'CURRENT_BROWSER_COMPLETE_CURRENT_JOURNEYS')
    p.exact(actual['script_sha256'], sha256(text.encode()).hexdigest(), 'CURRENT_BROWSER_EXACT_EXECUTED_MODULE')
    for index, name in enumerate(IDS):
        row = actual['cases'][name]
        p.fields(row, dict(status='PASS', actual_Auth_form_normal_full_App=True, actual_public_PostgREST=True,
            role='ADMIN' if index else 'OWNER', viewport=390 if index else 1440,
            actual_UI_refusal_zero_all22_rows_sequences_effect=True,
            actual_UI_whole_group_inverse_from_other_member=True, Native_financial_accounts_restored=True,
            no_horizontal_page_overflow_at_feature_checkpoints=True, unexpected_console_errors=0,
            full_manual_group_accessory_recovery_claim=False, expected_returns_first_child_limitation_not_closed=True,
            outer_full_backup_Auth_restore_still_required=True, production_go=False, independent_acceptance=False),
            'CURRENT_BROWSER_ACTUAL_COMPLETE_JOURNEY:' + name)
        p.fields(row['post'], dict(one_complete_group_two_Native_parts_physical_value='60.06',
            moving_average_value='68.07', source_available=5, source_reserved=1, target_physical=8,
            actual_double_click_one_new_group=True,
            actual_lost_committed_reply_same_UUID_after_reload=not bool(index),
            all_read_after_replay_rows_sequences_catalog_unchanged=not bool(index)),
            'CURRENT_BROWSER_PHYSICAL_AND_ECONOMIC_FACTS')
        current = row['source_pins']['entire_current_source_admission']
        p.fields(current, dict(status='COMPLETE_CURRENT_PRODUCT_SOURCE_ADMITTED_NOT_BROWSER_OR_FINANCIAL_ACCEPTANCE',
            qualification_commit=head, source_projected=False, database_calls=0, real_case_success_not_implied=True,
            actual_ERP_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0), 'CURRENT_BROWSER_EXACT_ADMITTED_HEAD')
        p.exact(current['complete_current_source_admission'], source, 'CURRENT_BROWSER_ENTIRE_CURRENT_SOURCE_NOT_PROJECTED')
        p.fields(current['source_database_network_guard'], dict(attempts=[], network_nonGit_attempts=[]),
                 'CURRENT_BROWSER_SOURCE_READ_DID_NOT_TOUCH_ERP')
        p.fields(row['console_evidence'], dict(unexpected_errors=[], page_errors=[]), 'CURRENT_BROWSER_COMPLETE_CLEAN_CONSOLE')
    return dict(typed=result, typed_source=proof, actual_browser_cases=2,
                primary_Auth_counts_restored=True, actual_Auth_HTTP_case_credit=0, actual_two_session_case_credit=0)


def asset(directory, name):
    path = directory / name
    require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)),
            'CURRENT_BROWSER_EXACT_REGULAR_ORIGINAL_ASSET')
    return path.read_bytes()


def gate(p, directory, actual, part, head, source):
    result = validate(p, actual, part, head, source)
    original_name = LABEL + '.json';raw = asset(directory, original_name)
    p.exact(p.strict(raw), actual, 'CURRENT_BROWSER_COMPLETE_ORIGINAL_NOT_PROJECTED')
    p.exact(part['current_browser_original'], dict(name=original_name, **pin(raw)), 'CURRENT_BROWSER_FIRST_ORIGINAL_EXACT_BYTES')
    assets, screenshots = {}, []
    for index, name in enumerate(IDS):
        row = actual['cases'][name];suffix = 'MOBILE390' if index else 'DESKTOP'
        for observed in row['current_observations']:
            census = observed['state']['census'];reference = census['raw_evidence']
            parts = PurePosixPath(reference['path']).parts
            require(len(parts) == 3 and parts[:2] == ('cp6-proof', 't3') and re.fullmatch(
                'SKU29_' + suffix + r'_[A-Z0-9_]+_FULL_CURRENT_STATE\.json', parts[2]),
                'CURRENT_BROWSER_FIXED_FULL_CENSUS_ORIGINAL')
            complete = asset(directory, parts[2]);p.exact(pin(complete), {key: reference[key] for key in ('bytes', 'sha256')},
                                                        'CURRENT_BROWSER_RAW_CENSUS_BYTES')
            value = p.strict(complete)
            require(len(value['catalog_rows']) == 22, 'CURRENT_BROWSER_COMPLETE_ALL22_RAW_CATALOG')
            digest = sha256(json.dumps(value['catalog_rows'], sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
            p.exact(census['catalog_sha256'], digest, 'CURRENT_BROWSER_COMPLETE_RAW_CATALOG_HASH')
            p.exact(census['data_and_sequences'], value['data_and_sequences'], 'CURRENT_BROWSER_ALL_ROWS_AND_SEQUENCE_VALUES')
            p.fields(census, dict(catalog_groups=22, dropped_catalog_fields=[], dropped_data_or_sequence_keys=[]),
                     'CURRENT_BROWSER_NO_DROPPED_RAW_FIELDS')
            assets[parts[2]] = pin(complete)
        require(len(row['screenshots']) == 8 and len(set(row['screenshots'])) == 8, 'CURRENT_BROWSER_EIGHT_DISTINCT_REAL_SCREENSHOTS')
        for name in row['screenshots']:
            parts = PurePosixPath(name).parts
            require(len(parts) == 3 and parts[:2] == ('cp6-proof', 't3') and re.fullmatch(
                'SKU29_' + suffix + r'_[A-Z0-9_]+_(PAGE|FOCUS)\.png', parts[2]), 'CURRENT_BROWSER_FIXED_SCREENSHOT_PATH')
            raw_image = asset(directory, parts[2]);require(raw_image[:8] == b'\x89PNG\r\n\x1a\n', 'CURRENT_BROWSER_REAL_PNG')
            width, height = struct.unpack('>II', raw_image[16:24]);viewport = row['viewport']
            require(0 < width <= viewport and height > 0 and (not name.endswith('_PAGE.png') or width == viewport),
                    'CURRENT_BROWSER_ACTUAL_SCREENSHOT_DIMENSIONS')
            screenshots.append(dict(name=parts[2], **pin(raw_image), width=width, height=height))
    checked = subprocess.run(['node', str(HERE / 'browser_readback_gate.mjs'), str(directory / original_name)],
                             capture_output=True, text=True, check=False, timeout=60)
    require(checked.returncode == 0, 'CURRENT_BROWSER_INDEPENDENT_ECONOMIC_AND_FULL_OBSERVATION_RECHECK:' + checked.stderr[-2000:])
    oracle = p.strict(checked.stdout)
    p.fields(oracle, dict(status='CURRENT_BROWSER2_COMPLETE_RECORDED_ORACLES_RECHECKED', cases=2,
                         actual_Auth_HTTP_case_credit=0, actual_two_session_case_credit=0), 'CURRENT_BROWSER_ORACLE_RECHECK')
    return dict(result, complete_census_originals=assets, screenshots=screenshots, recorded_oracle_recheck=oracle)
