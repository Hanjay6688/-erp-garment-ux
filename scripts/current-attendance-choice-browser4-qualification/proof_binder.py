"""Validate only explicitly bound actual Original bytes; no projected source or PASS synthesis.

Combined14 labels/group paths are intentionally not guessed. Root must bind them
after its actual successor finishes and retain the original artifacts here.
"""
from hashlib import sha256
from pathlib import PurePosixPath
import gzip
import importlib.util
import json
import os
import re
import subprocess

RESTORE_FLAGS = ('cp6_restored', 'baseline_full22_all_rows_all_sequences_equal',
    'baseline_advisors_equal', 'advisor_gate', 'used_guard_refused_before_DDL', 'required_case_ids_pass')
PACKAGE_GATES = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')
ORIGINAL11_IDS = (
    'S03_NATIVE_OWNER_FIELDS_READ_FULL_NO_EFFECT',
    'S03_NATIVE_EXPENSE_APPROVAL_ONCE_PAID_E05_REOPEN',
    'S03_NATIVE_TWO_EXACT_PERIODS_CENTS_AND_NATIVE_HPP',
    'S03_NATIVE_P2_PAYROLL_POOL_COEXIST_AND_POLICY_FENCES',
    'S03_NATIVE_OWNING_CANCEL_LATE_OUTPUT_AND_RESTORATION_FLOOR',
    'S03_NATIVE_BOTH_CORRECTIONS_LINKED_INVERSES_NO_RECOGNITION',
    'S03_NATIVE_STALE_REVIEW_UUID_RECOVERY_AND_APPEND_ONLY',
    'S03_NATIVE_CLOSED_SOURCE_OPEN_OUTPUT_AND_CLOSED_CORRECTION',
    'S03_NATIVE_ZERO_OUTPUT_SUCCESSOR_POLICY_RETAINS_OLD_INFO',
    'S03_NATIVE_FINISHED_PO_FG_COGS_COST_AND_CANCEL_EXACT',
    'S03_NATIVE_OLD_ACCRUAL_LATER_BOOK_REOPEN_DATE_FLOOR',
)
READER3_IDS = (
    'S03_READER_NATIVE_OWNED_ACTIVE_PERIODS_AND_DISJOINT_P2_UNCHANGED',
    'S03_READER_NATIVE_CANCELLED_LIFETIME_AND_STALE_COMPOSITE_NO_EFFECT',
    'S03_READER_NATIVE_EXACT_HELD_P1_BLOCKS_LEGACY_REPLACE_AND_CREATE',
)


def at(value, path):
    if not isinstance(path, list) or not path or any(not isinstance(key, str) or not key for key in path):
        raise ValueError('S03_BROWSER4_EXPLICIT_ORIGINAL_PATH_REQUIRED')
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise ValueError('S03_BROWSER4_ACTUAL_ORIGINAL_FIELD_MISSING:' + '.'.join(path))
        value = value[key]
    return value


def checked(report, package, files, restoration, native11, reader3, binding):
    if not isinstance(binding, dict) or type(binding.get('actual_case_count')) is not int or binding.get('actual_case_count') != 14:
        raise ValueError('S03_BROWSER4_EXACT_BACKEND14_BINDING_REQUIRED')
    if (not re.fullmatch(r'[a-f0-9]{40}', binding.get('qualifying_commit', ''))
            or not re.fullmatch(r'[a-f0-9]{40}', binding.get('qualifying_tree', ''))
            or not re.fullmatch(r'\d+', str(binding.get('run_id', '')))
            or not re.fullmatch(r'\d+', str(binding.get('job_id', '')))
            or report.get('qualification_commit') != binding['qualifying_commit']):
        raise ValueError('S03_BROWSER4_EXACT_ACTUAL_RUN_AND_GIT_COMMIT_REQUIRED')
    original11, reader_ids = binding['original11_ids'], binding['reader3_ids']
    ids = original11 + reader_ids
    if original11 != list(ORIGINAL11_IDS) or reader_ids != list(READER3_IDS) or len(set(ids)) != 14:
        raise ValueError('S03_BROWSER4_EXACT_UNCHANGED11_PLUS_READER3_IDS_REQUIRED')
    if report.get('status') != 'PASS' or report.get('label') != binding['outer_label']:
        raise ValueError('S03_BROWSER4_ACTUAL_BACKEND_OUTER_PASS_REQUIRED')
    if any(report.get(key) is not True for key in RESTORE_FLAGS) or report.get('error') or report.get('restore_error'):
        raise ValueError('S03_BROWSER4_FULL_OUTER_RESTORE_AND_USED_INVERSE_REQUIRED')
    for key, number in dict(actual_Native_cases=14, actual_browser_cases=0,
            actual_Auth_HTTP_cases=0, actual_two_session_races=0).items():
        if type(report.get(key)) is not int or report[key] != number:
            raise ValueError('S03_BROWSER4_EXACT_NATIVE_ONLY_PARENT_COUNTS_REQUIRED:' + key)
    group = at(report, binding['component_path'])
    if group.get('status') != 'PASS' or group.get('used_guard_refused_before_DDL') is not True:
        raise ValueError('S03_BROWSER4_ACTUAL_COMMITTED_USED_WITNESS_REQUIRED')
    planned = []
    sections = binding['strict_sections']
    if len(sections) != 2 or [section['ids'] for section in sections] != [original11, reader_ids]:
        raise ValueError('S03_BROWSER4_TWO_ACTUAL_STRICT_GROUPS_11_THEN_3_REQUIRED')
    for section, raw_original in zip(sections, (native11, reader3)):
        actual = at(report, section['path'])
        if actual != raw_original:
            raise ValueError('S03_BROWSER4_SEPARATE_STRICT_GROUP_ORIGINAL_CHANGED')
        expected = section['ids']
        if (actual.get('status') != 'PASS' or actual.get('counts') != {'PASS': len(expected)}
                or actual.get('planned_case_ids') != expected or set(actual.get('cases', {})) != set(expected)
                or any(row.get('status') != 'PASS' for row in actual['cases'].values())
                or actual.get('complete_boundary_restored') is not True):
            raise ValueError('S03_BROWSER4_EVERY_ACTUAL_NATIVE14_CALLBACK_REQUIRED')
        planned += expected
    if planned != ids:
        raise ValueError('S03_BROWSER4_NO_MISSING_DUPLICATE_OR_REORDERED_PARENT_CASE')
    before = at(report, binding['used_before_path'])
    after = at(report, binding['used_after_path'])
    if (before != after or set(before) != {'actual_all22', 'full_data_and_sequences'}
            or len(before['actual_all22']) != 22 or not before['full_data_and_sequences']
            or not any(key.startswith('sequence:') for key in before['full_data_and_sequences'])
            or any(before['full_data_and_sequences'].get(key, [0])[0] < 1 for key in
                ('cp7_attendance_choice.decisions_v1', 'cp7_attendance_choice.allocations_v1'))):
        raise ValueError('S03_BROWSER4_ACTUAL_COMMITTED_USED_FULL22_DATA_SEQUENCE_WITNESS_REQUIRED')
    if (package.get('status') != 'ALL_STAGES_INSTALLED' or set(package.get('gate', {})) != set(PACKAGE_GATES)
            or any(package['gate'][key] is not True for key in PACKAGE_GATES)):
        raise ValueError('S03_BROWSER4_ALL_FIVE_ACTUAL_PACKAGE_GATES_REQUIRED')
    # Additional original file/restore verdicts are source-declared exact paths/values,
    # not optional fallbacks or a newly invented substitute report.
    for name, actual in (('files', files), ('restoration', restoration)):
        assertions = binding[name + '_required_values']
        if not assertions:
            raise ValueError('S03_BROWSER4_ACTUAL_' + name.upper() + '_ORIGINAL_REQUIRED')
        for expected in assertions:
            if at(actual, expected['path']) != expected['value']:
                raise ValueError('S03_BROWSER4_ACTUAL_' + name.upper() + '_GATE_REQUIRED')
    installation = at(report, binding['current_installation_path'])
    runtime = binding['runtime_files']
    if (not isinstance(installation, dict) or installation.get('files') != runtime or len(runtime) != 7
            or set(runtime) != {'scripts/cp7_attendance_period_choice/' + name for name in
                ('choice.sql', 'native_delta.py', 'catalog_contract.py', 'NEW_CATALOG_IDENTITIES.json', 'composition.py', 'readers.sql', 'installer_ddl.py')}):
        raise ValueError('S03_BROWSER4_EXACT_ACTUAL_SEVEN_RUNTIME_FILES_REQUIRED')
    current = at(report, binding['current_qualification_path'])
    if (current.get('actual_authored_files') != 118 or current.get('exact_runtime_files') != 7
            or current.get('captured_originals') != 15 or current.get('private_clones') != 2
            or current.get('groups') != [11, 3]):
        raise ValueError('S03_BROWSER4_ACTUAL_READER15_AND_CANONICAL_AUTHOR118_ADMISSION_REQUIRED')
    return dict(status='EXACT_ACTUAL_BACKEND14_AND_ALL5_ORIGINALS_ADMITTED',
        current_installation=installation, actual_parent_Native_cases=14,
        used_inverse_guard_before_DDL=True, fresh_parent_cases_claim=False,
        source_projection=False, catalog_projection=False, catalog_resealed=False, production_go=False)


def check_qualified_metadata(config, source, prepared, expected_runtime):
    """Exact source correspondence, not a second/fabricated Native verdict."""
    author = prepared['author_binding']
    if (len(author['files']) != 118 or config.get('backend_binding') != author
            or config.get('runtime_files') != expected_runtime
            or author['runtime_files'] != expected_runtime
            or any(source['files'].get(path) != pin for path, pin in author['files'].items())):
        raise ValueError('S03_BROWSER4_CANONICAL_PUBLIC_AUTHOR118_SOURCE_BINDING_CHANGED')
    return dict(exact_public_authored_files=118, exact_actual_runtime_files=7)


def qualified_source(root, here, binding):
    """Read the actual qualifying Git object locally; never fetch or use HEAD."""
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1')
    commit = binding['qualifying_commit']
    git = lambda *args: subprocess.check_output(['git', '-C', str(root), *args], env=env)
    if git('rev-parse', commit + '^{tree}').decode().strip() != binding['qualifying_tree']:
        raise ValueError('S03_BROWSER4_EXACT_ACTUAL_QUALIFYING_TREE_REQUIRED')
    pins = binding['qualified_source_files']
    prefix = 'scripts/current-attendance-choice-reader-native14-qualification/'
    if set(pins) != {'CONFIG.json', 'SOURCE.json'}:
        raise ValueError('S03_BROWSER4_ACTUAL_QUALIFIER_SOURCE_AND_CONFIG_PINS_REQUIRED')
    values = {}
    for name, pin in pins.items():
        if pin['path'] != prefix + name:
            raise ValueError('S03_BROWSER4_EXACT_QUALIFIER_SOURCE_PATH_REQUIRED')
        raw = git('show', commit + ':' + pin['path'])
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('S03_BROWSER4_ACTUAL_QUALIFIER_SOURCE_BYTES_CHANGED:' + name)
        values[name] = json.loads(raw)
    prepared = json.loads((here / 'PREPARED_AUTHOR_BINDING.json').read_bytes())
    proof = check_qualified_metadata(values['CONFIG.json'], values['SOURCE.json'], prepared, binding['runtime_files'])
    # __init__ is an explicit eighth import/bootstrap source, not a business leaf.
    entry = json.loads((here / 'RUNTIME_SOURCE.json').read_bytes())['package_entry']
    raw = git('show', commit + ':' + entry['path'])
    if len(raw) != entry['bytes'] or sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError('S03_BROWSER4_ACTUAL_QUALIFIED_PACKAGE_ENTRY_CHANGED')
    return dict(proof, qualifying_commit=commit, qualifying_tree=binding['qualifying_tree'],
        source_files=pins, exact_bootstrap_sha256=entry['sha256'], actual_verdict_reexecuted=False)


def admit(root, here, config, source):
    originals = config['accepted_originals']
    if not isinstance(originals, dict) or set(originals) != {'report', 'package', 'files', 'restoration', 'native11', 'reader3'}:
        raise ValueError('S03_BROWSER4_EXACT_SIX_ACTUAL_ORIGINALS_REQUIRED')
    documents = {}
    receipts = {}
    for name, item in originals.items():
        relative = PurePosixPath(item['path'])
        if relative.is_absolute() or '..' in relative.parts or not str(relative).startswith('retained/'):
            raise ValueError('S03_BROWSER4_RETAINED_ORIGINAL_PATH_REQUIRED')
        path = here / str(relative)
        packed = path.read_bytes()
        raw = gzip.decompress(packed)
        if (len(packed) != item['gzip_bytes'] or sha256(packed).hexdigest() != item['gzip_sha256']
                or len(raw) != item['raw_bytes'] or sha256(raw).hexdigest() != item['raw_sha256']):
            raise ValueError('S03_BROWSER4_ORIGINAL_BYTES_CHANGED:' + name)
        documents[name] = json.loads(raw)
        receipts[name] = item
    proof = checked(**documents, binding=config['backend_binding'])
    source_proof = qualified_source(root, here, config['backend_binding'])
    spec = importlib.util.spec_from_file_location('s03_browser4_admitted_source_routes', here / 'backend_runtime.py')
    loader = importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
    route = loader.retained(config['backend_binding']['runtime_files'])
    return dict(proof, accepted_originals=receipts, source_declaration=source,
        actual_qualified_source=source_proof,
        actual_component_root=str(route['component_root']), actual_backend_runtime_files=route['runtime_files'],
        frozen_UI_backend_files_replaced=False)
