"""Inert parent/source binding gate; own fresh17 is deliberately not a prerequisite."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = '17ac1eeb5833cbf2a786194fe3bfbba6628a1ff8'
BACKEND = 'fe2ae370c00e68437c4951c28c3a1038ce35fb38'
RAW_KEYS = ('original', 'native_group', 'package', 'package_files', 'backup_drill')


def original():
    p = ROOT/'scripts/current-credit-e1-native-qualification/gate.py'
    s = importlib.util.spec_from_file_location('e_phase_retained_parent_gate', p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def selected(cfg):
    if any(cfg.get(k) is None for k in ('accepted_D1', 'accepted_raw_parent', 'required_qualified_parent', 'prepared_backend')):
        raise ValueError('E_PHASE_CLOSED_QUALIFIED_PARENT_AND_PUBLIC_SOURCE_BINDING_REQUIRED')
    pin = original().selected(cfg)
    backend = cfg['prepared_backend']
    if pin['head'] != PARENT or backend['head'] != BACKEND or backend['tree'] != '600d4575309e67a5575d7896382b38a27e000d7e':
        raise ValueError('E_PHASE_EXACT_PUBLIC_PARENT_AND_PREPARED_BACKEND_REQUIRED')
    if (backend['source_sha256'] != 'c1899ebed78fd3cd94a6e8e2d148fc6fe34911b48951aa1756e9e46dbef38ce3'
            or backend['source_pins'] != 319 or backend['private_functions'] != 41):
        raise ValueError('E_PHASE_CURRENT319_PRIVATE41_REQUIRED')
    if cfg['accepted_raw_parent'] != {k: pin[k] for k in RAW_KEYS}:
        raise ValueError('E_PHASE_EXACT_FIVE_PARENT_RAW_BINDING_REQUIRED')
    failed = cfg['retained_failed_E17']
    if (failed['head'] != backend['parent'] or failed['counts'] != {'PASS': 15, 'INCOMPLETE': 2}
            or failed['usable_prerequisite'] is not False or failed['source_pins'] != 282):
        raise ValueError('E_PHASE_FIRST_FAILED_E17_MUST_REMAIN_NEGATIVE')
    if any(cfg.get(k) is not False for k in ('production_go', 'independent_acceptance', 'E_complete')):
        raise ValueError('E_PHASE_PREPARED_WRAPPER_IS_NOT_ACCEPTANCE')
    # accepted_native17 is the outcome to be earned by THIS candidate, not its parent.
    if cfg.get('accepted_native17') is not None:
        raise ValueError('E_PHASE_NEW_TERMINAL_BINDING_REQUIRES_ROOT_SUCCESSOR')
    return pin


def retained_failure(cfg, raw):
    return original().retained_failure(cfg, raw)


def exact_group(group, ids, count):
    return original().exact_group(group, ids, count)


def admitted(cfg, originals, current_D1, frozen_D1_source, ids):
    pin = selected(cfg)
    result = original().admitted(cfg, originals, current_D1, frozen_D1_source, ids)
    folder = Path(os.environ['CP7_E1_D1_ORIGINALS'])
    docs = {}
    for key in ('package_files', 'backup_drill'):
        item = pin[key]; raw = (folder/item['name']).read_bytes()
        if len(raw) != item['bytes'] or sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('E_PHASE_EXACT_PARENT_ADDITIONAL_RAW_REQUIRED:' + key)
        docs[key] = json.loads(raw)
    return dict(result, parent_originals_retained=5, additional_raw_names=[pin[k]['name'] for k in docs],
                fresh_E17_outcome_not_used_as_prerequisite=True)
