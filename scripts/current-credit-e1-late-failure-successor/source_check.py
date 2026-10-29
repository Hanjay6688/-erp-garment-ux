"""Closed source successor: one test callback changes; no product/runtime import."""
from hashlib import sha256
from pathlib import Path
import ast
import json
import os
import subprocess
import sys

BASE = 'f5b085a2bf3a34397616e9a9a3326af5119d19c4'
BASE_TREE = '0f54938eea7893327456cbc8d850ae85ea9c6e58'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NAMESPACE = 'scripts/current-credit-e1-late-failure-successor/'
CASES = 'scripts/cp7_credit_correction_de/e_cases.py'
DEPENDENCIES = 'scripts/cp7_credit_correction_de/E_DEPENDENCIES.json'
OLD_QUALIFIER = 'scripts/current-credit-e1-native-qualification/'
OLD_WORKFLOW = '.github/workflows/cp7-credit-e1-native17.yml'


def digest(raw):
    return sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def callback_parts(raw):
    text = raw.decode(); tree = ast.parse(text)
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'late_failure']
    if len(nodes) != 1:
        raise ValueError('E1_EXACT_SINGLE_LATE_FAILURE_CALLBACK_REQUIRED')
    node, lines = nodes[0], text.splitlines(keepends=True)
    prefix = ''.join(lines[:node.lineno-1]).encode()
    body = ''.join(lines[node.lineno-1:node.end_lineno]).encode()
    suffix = ''.join(lines[node.end_lineno:]).encode()
    ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
    return prefix, body, suffix, ids


def derivation(before, after):
    old_prefix, old_body, old_suffix, old_ids = callback_parts(before)
    new_prefix, new_body, new_suffix, new_ids = callback_parts(after)
    if old_prefix != new_prefix or old_suffix != new_suffix:
        raise ValueError('E1_CHANGE_OUTSIDE_SINGLE_APPROVED_LATE_FAILURE_CALLBACK')
    if old_ids != new_ids or len(new_ids) != len(set(new_ids)) or len(new_ids) != 17:
        raise ValueError('E1_ALL_SEVENTEEN_CASE_IDS_MUST_REMAIN_EXACT')
    if old_body == new_body:
        raise ValueError('E1_LATE_POINT_FIX_NOT_PRESENT')
    if b'create trigger test_e_post_failure before insert on erp.journal_entries' not in old_body:
        raise ValueError('E1_EXACT_OLD_ERP_TRIGGER_SOURCE_FINDING_REQUIRED')
    if b'after insert on cp7_credit_note_carry_de.operations_v1' not in new_body:
        raise ValueError('E1_APPROVED_PRIVATE_AFTER_INSERT_POINT_REQUIRED')
    if b'before insert on erp.journal_entries' in new_body:
        raise ValueError('E1_NO_NEW_NATIVE_ERP_TRIGGER_ALLOWED')
    return dict(status='EXACT_ONE_CALLBACK_SOURCE_DERIVATION_NOT_NATIVE_PROOF', old_cases_sha256=digest(before),
        new_cases_sha256=digest(after), old_late_failure_sha256=digest(old_body), new_late_failure_sha256=digest(new_body),
        unchanged_prefix_sha256=digest(old_prefix), unchanged_suffix_sha256=digest(old_suffix),
        changes_outside_late_failure=False, other_sixteen_callback_bodies_unchanged=True, all_seventeen_case_ids=list(new_ids),
        failure_point='AFTER_NATIVE_POST_DURING_E_FINISH', unchanged_injected_message='E_TEST_ACTUAL_NATIVE_POST_FAILURE',
        setup_refusal_message='E_TEST_LATE_POINT_SETUP_FAILED', Native_execution=False)


def expected():
    if git('rev-parse', BASE+'^{tree}').decode().strip() != BASE_TREE:
        raise ValueError('E1_EXACT_FROZEN_PUBLIC_PREPARATION_BASE_REQUIRED')
    before, after = git('show', BASE+':'+CASES), (ROOT/CASES).read_bytes()
    proof = derivation(before, after)
    old_dependencies = json.loads(git('show', BASE+':'+DEPENDENCIES))
    new_dependencies = json.loads((ROOT/DEPENDENCIES).read_bytes())
    changed_keys = {key for key in set(old_dependencies)|set(new_dependencies) if old_dependencies.get(key) != new_dependencies.get(key)}
    if changed_keys != {'qualifier_sha256', 'native_failure_injection_successor'} or new_dependencies['qualifier_sha256'] != proof['new_cases_sha256']:
        raise ValueError('E1_ONLY_APPROVED_TESTCASE_DEPENDENCY_PROVENANCE_MAY_CHANGE')
    frozen = {}
    for name in git('ls-tree', '-r', '--name-only', BASE, OLD_QUALIFIER, OLD_WORKFLOW).decode().splitlines():
        raw = git('show', BASE+':'+name)
        if (ROOT/name).read_bytes() != raw:
            raise ValueError('E1_FROZEN_OLD_QUALIFIER_MUST_REMAIN_UNCHANGED:'+name)
        frozen[name] = digest(raw)
    for name, h in old_dependencies['runtime_sources'].items():
        path = 'scripts/cp7_credit_correction_de/'+name
        if digest((ROOT/path).read_bytes()) != h:
            raise ValueError('E1_NINE_RUNTIME_LEAVES_MUST_REMAIN_EXACT:'+path)
        frozen[path] = h
    parent = json.loads(git('show', BASE+':scripts/current-credit-de-native-qualification/CONFIG.json'))
    for name, h in parent['runtime_files'].items():
        path = 'scripts/cp7_credit_correction_de/'+name
        if digest((ROOT/path).read_bytes()) != h:
            raise ValueError('E1_D1_RUNTIME_MUST_REMAIN_UNCHANGED:'+path)
        frozen[path] = h
    for group in ('retained_helper_sha256', 'UI_sha256'):
        for path, h in old_dependencies[group].items():
            if digest((ROOT/path).read_bytes()) != h:
                raise ValueError('E1_RETAINED_HELPER_AND_UI_MUST_REMAIN_UNCHANGED:'+path)
            frozen[path] = h
    paths = {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file()}
    if any('__pycache__' in p or p.endswith('.pyc') for p in paths):
        raise ValueError('E1_NO_GENERATED_CACHE_IN_SUCCESSOR_INPUTS')
    paths |= {CASES, DEPENDENCIES}; paths.discard(NAMESPACE+'SOURCE.json')
    changed = git('diff', '--name-only', BASE).decode().splitlines()
    changed += git('ls-files', '--others', '--exclude-standard').decode().splitlines()
    if any(p not in (CASES, DEPENDENCIES) and not p.startswith(NAMESPACE) for p in changed):
        raise ValueError('E1_UNALLOCATED_SUCCESSOR_PATH')
    source = dict(contract='cp7.e1-late-failure-source-successor.v1', status='PREPARED_LOCAL_DOUBLE_CONTROLS_NOT_ACTUAL_E_PASS',
        base_head=BASE, base_tree=BASE_TREE, callback_derivation=proof, frozen_inputs=frozen,
        files={p: dict(bytes=len((ROOT/p).read_bytes()), sha256=digest((ROOT/p).read_bytes())) for p in sorted(paths)},
        original_closed_qualifier_manifests_unchanged=True, old_closed_qualifier_admits_changed_cases=False,
        future_root_intake='EXPLICIT_SUCCESSFUL_D1_SOURCE_AND_E_CASE_DEPENDENCY_REBIND_REQUIRED_BEFORE_ACTUAL17',
        actual_E_cases=0, actual_Auth_HTTP=0, actual_browser=0, actual_races=0, production_go=False, independent_acceptance=False)
    return source


def run(bind=False):
    source = expected()
    if bind:
        if os.environ.get('CI'):
            raise ValueError('E1_LATE_SUCCESSOR_SOURCE_CANNOT_BE_REGENERATED_IN_CI')
        (HERE/'SOURCE.json').write_text(json.dumps(source, indent=2)+'\n')
    elif json.loads((HERE/'SOURCE.json').read_bytes()) != source:
        raise ValueError('E1_LATE_SUCCESSOR_DECLARATION_CHANGED')
    return dict(status='PASS_EXACT_SINGLE_TESTCASE_TRANSITION_NO_RUNTIME_CREDIT', files=len(source['files']),
        frozen_inputs=len(source['frozen_inputs']), unchanged_other_callbacks=16, actual_E_cases=0, production_go=False)


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--bind']):
        raise SystemExit('Use no arguments for source proof or --bind for the explicit writer-only successor declaration.')
    print(json.dumps(run(sys.argv[1:] == ['--bind'])))
