"""Exact file-only f671 derivation; no product or database imports."""
from hashlib import sha256
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONT = 'scripts/current-credit-d1-continuation-qualification/'
NATIVE_TRANSFORMS = (
    ('native, basic, fixture, correction = d1.native, d1.basic, d1.fixture, d1.correction',
     'native, basic, fixture, correction = d1.native, d1.basic, d1.fixture, d1.correction\n'
     '# Preparation uses the owned lawful D1 two-piece fixture. The unchanged\n'
     '# target-only GL oracle is explicitly delegated to its retained helper.\n'
     'target_document_ar = fixture.retained._document_ar'),
    ("ar = fixture._document_ar(cur, sale, target['customer'], pair['ar']['target'])",
     "ar = target_document_ar(cur, sale, target['customer'], pair['ar']['target'])"),
)
TEST_TRANSFORM = ('n.fixture._document_ar','n.target_document_ar')


def exact_substitute(raw, transforms):
    text = raw.decode()
    for old,new in transforms:
        if text.count(old) != 1:
            raise ValueError('D1_CONT_EXACT_QUALIFICATION_ABI_ANCHOR_REQUIRED:'+old)
        text = text.replace(old,new,1)
    return text.encode()


def check():
    declared = json.loads((HERE/'TRANSITION.json').read_bytes()); retained = HERE/'retained_f671'
    originals = {}
    for path,digest in declared['retained_original_files'].items():
        raw = (retained/(Path(path).name+'.txt')).read_bytes()
        if sha256(raw).hexdigest() != digest:
            raise ValueError('D1_CONT_ORIGINAL_F671_BYTES_CHANGED:'+path)
        originals[Path(path).name] = raw
    if len(originals) != 8:
        raise ValueError('D1_CONT_EXACT_EIGHT_IMPORTED_ORIGINAL_FILES_REQUIRED')
    for name in ('cases.py','oracle.py','source_guard.py','LOCAL_CHECKS.json'):
        if (ROOT/CONT/name).read_bytes() != originals[name]:
            raise ValueError('D1_CONT_FROZEN_CASE_OR_ORACLE_CHANGED:'+name)
    if (ROOT/CONT/'native_fixture.py').read_bytes() != exact_substitute(originals['native_fixture.py'],NATIVE_TRANSFORMS):
        raise ValueError('D1_CONT_ONLY_EXPLICIT_OWNED_FIXTURE_TARGET_HELPER_ABI_TRANSITION_ALLOWED')
    if (ROOT/CONT/'test_local.py').read_bytes() != exact_substitute(originals['test_local.py'],(TEST_TRANSFORM,)):
        raise ValueError('D1_CONT_ONLY_RETAINED_LOCAL_SIGNATURE_CHECK_TARGET_MAY_CHANGE')
    if not (ROOT/CONT/'README.md').read_bytes().startswith(originals['README.md']):
        raise ValueError('D1_CONT_ORIGINAL_README_MUST_REMAIN_RETAINED')
    old = json.loads(originals['SOURCE.json']); new_raw = (ROOT/CONT/'SOURCE.json').read_bytes(); new = json.loads(new_raw)
    if sha256(new_raw).hexdigest() != declared['new_manifest_sha256']:
        raise ValueError('D1_CONT_EXPLICIT_SUCCESSOR_SOURCE_MANIFEST_CHANGED')
    changed = {key for key in set(old)|set(new)if old.get(key) != new.get(key)}
    if changed != {'files','D1_runtime_files','source_transition'}:
        raise ValueError('D1_CONT_ONLY_COUNTED_SOURCE_DEPENDENCIES_MAY_TRANSITION')
    external = declared['external_dependency_changes']
    if len(external) != 4 or declared['external_changed_pin_count'] != 4:
        raise ValueError('D1_CONT_EXACT_FOUR_EXTERNAL_DEPENDENCY_CHANGES_REQUIRED')
    expected_changed = {row['path']for row in external}|{CONT+name for name in ('native_fixture.py','test_local.py','README.md')}
    actual_changed = {path for path in old['files']if old['files'][path] != new['files'].get(path)}
    if actual_changed != expected_changed or len(actual_changed) != 7 or declared['own_changed_pin_count'] != 3:
        raise ValueError('D1_CONT_EXACT_FOUR_EXTERNAL_THREE_OWN_PIN_TRANSITION_REQUIRED')
    if set(new['files']) != set(old['files'])|set(declared['added_dependency_paths'])or len(declared['added_dependency_paths']) != 2:
        raise ValueError('D1_CONT_EXACT_TWO_OWNED_FIXTURE_SOURCE_ADDITIONS_REQUIRED')
    for row in external:
        if old['files'][row['path']] != row['before_sha256']or new['files'][row['path']] != row['after_sha256']:
            raise ValueError('D1_CONT_EXTERNAL_PIN_PROVENANCE_CHANGED')
    for path,digest in new['files'].items():
        if sha256((ROOT/path).read_bytes()).hexdigest() != digest:
            raise ValueError('D1_CONT_EXACT_SUCCESSOR_SOURCE_CHANGED:'+path)
    return dict(status='EXACT_BOUNDED_F671_QUALIFICATION_SUCCESSOR_ONLY',imported_original_files=8,
        external_changed_pins=4,own_changed_pins=3,added_dependency_pins=2,
        qualification_helper_substitutions=2,local_signature_substitutions=1,
        unchanged_callback_count=3,unchanged_money_history_cost_conservation_oracles=True,Native_executions=0)
