"""Exact reviewed settings-page/source-owner/test routing changes; no ERP."""
from hashlib import sha1, sha256
from pathlib import Path
import json

from . import admission

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHANGED = frozenset(('src/ConnectedErpSettingsPage.tsx', 'scripts/check-source-ownership.mjs',
    'src/ConnectedErpSettingsPage.dom.test.tsx', 'scripts/check-access-catalog.mjs'))
ADDED = frozenset(('src/GoodPolicyDatesPanel.tsx', 'src/nativeGoodPolicyDates.ts',
    'src/good-policy-dates.css', 'src/GoodPolicyDatesPanel.dom.test.tsx', 'src/nativeGoodPolicyDates.test.ts'))


def git_blob(raw):
    return sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def originals():
    origin = admission.strict((HERE / 'UI_ORIGIN.json').read_bytes())
    if set(origin['files']) != CHANGED:
        raise ValueError('NONPAYABLE_EXACT_FOUR_REVIEWED_UI_PATHS_REQUIRED')
    return {name: (HERE / row['captured_file']).read_bytes() for name, row in origin['files'].items()}


def derive(actual):
    origin = admission.strict((HERE / 'UI_ORIGIN.json').read_bytes())
    if set(actual) != CHANGED or set(origin['files']) != CHANGED:
        raise ValueError('NONPAYABLE_EXACT_UI_PREDECESSOR_SET_REQUIRED')
    result, proof = {}, {}
    for name, row in origin['files'].items():
        raw = actual[name]
        if admission.pin(raw) != admission.require_pin(row['original']) or git_blob(raw) != row['original_blob_sha']:
            raise ValueError('NONPAYABLE_UI_PREDECESSOR_BYTES_CHANGED:' + name)
        text = raw.decode()
        if not row['changes']:
            raise ValueError('NONPAYABLE_REVIEWED_UI_CHANGE_REQUIRED:' + name)
        for change in row['changes']:
            if change.get('count') != 1 or not change['before'] or text.count(change['before']) != 1:
                raise ValueError('NONPAYABLE_EXACT_UI_CHANGE_ANCHOR_REQUIRED:' + name)
            text = text.replace(change['before'], change['after'], 1)
        derived = text.encode()
        if admission.pin(derived) != admission.require_pin(row['derived']) or git_blob(derived) != row['derived_blob_sha']:
            raise ValueError('NONPAYABLE_EXACT_REVIEWED_UI_BYTES_REQUIRED:' + name)
        for change in reversed(row['changes']):
            if not change['after'] or text.count(change['after']) != 1:
                raise ValueError('NONPAYABLE_EXACT_UI_INVERSE_ANCHOR_REQUIRED:' + name)
            text = text.replace(change['after'], change['before'], 1)
        if text.encode() != raw:
            raise ValueError('NONPAYABLE_ORIGINAL_UI_BYTES_NOT_RECOVERED:' + name)
        result[name] = derived
        proof[name] = dict(original=row['original'], derived=row['derived'],
            original_blob_sha=row['original_blob_sha'], derived_blob_sha=row['derived_blob_sha'],
            counted_hunks=len(row['changes']), exact_inverse=True)
    return result, proof


def source_manifest():
    source = admission.strict((HERE / 'UI_SOURCE.json').read_bytes())
    required = CHANGED | ADDED | {'scripts/cp7_accessory_nonpayable/UI_ORIGIN.json'}
    origin = admission.strict((HERE / 'UI_ORIGIN.json').read_bytes())
    required |= {'scripts/cp7_accessory_nonpayable/' + row['captured_file'] for row in origin['files'].values()}
    if (source.get('contract') != 'cp7.good-policy-date-settings-ui.v1' or set(source['files']) != required
        or type(source.get('actual_browser_cases')) is not int or source['actual_browser_cases'] != 0
        or source.get('production_go') is not False or source.get('independent_acceptance') is not False):
        raise ValueError('NONPAYABLE_EXACT_SETTINGS_UI_SOURCE_REQUIRED')
    for name, expected in source['files'].items():
        path = ROOT / name
        if path.is_symlink() or admission.pin(path.read_bytes()) != admission.require_pin(expected):
            raise ValueError('NONPAYABLE_SETTINGS_UI_SOURCE_CHANGED:' + name)
    derived, proof = derive(originals())
    for name, expected in derived.items():
        if (ROOT / name).read_bytes() != expected:
            raise ValueError('NONPAYABLE_ONLY_REVIEWED_UI_DERIVATION_ALLOWED:' + name)
    return dict(contract=source['contract'], source=source, source_manifest=admission.pin((HERE / 'UI_SOURCE.json').read_bytes()),
        UI_derivations=proof, actual_browser_cases=0, actual_Auth_HTTP_cases=0,
        production_go=False, independent_acceptance=False)
