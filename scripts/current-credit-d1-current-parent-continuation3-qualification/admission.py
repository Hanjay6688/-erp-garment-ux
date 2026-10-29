"""Full current parent/source closure precedes every private historical intake."""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'scripts/current-credit-d1-owner-followup-qualification'
CURRENT = ROOT / 'scripts/current-credit-d1-product-phase-native13-qualification'
PARENT = '17ac1eeb5833cbf2a786194fe3bfbba6628a1ff8'
TREE = '52870c467cb37c328fd6ff73fe8484f8d6798953'
SOURCE174 = 'eeb47a301fd3241677bbae8c2a6189179cf8b5c82d6114561b2b47d52031a3e5'
WORKFLOW = '.github/workflows/cp7-credit-d1-current-parent-continuation3.yml'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def cfg():
    return json.loads((HERE / 'CONFIG.json').read_bytes())


def legacy():
    code, proof = load('d1_cont_current_private_admission_deriver', HERE / 'derive.py').admission((OLD / 'admission.py').read_bytes())
    module = ModuleType('d1_cont_current_private_old_admission')
    module.__file__ = str(HERE / 'admission.py')
    exec(compile(code, str(OLD / 'admission.py'), 'exec'), module.__dict__)
    return module, proof


def source_only():
    config = cfg(); source = json.loads((HERE / 'SOURCE.json').read_bytes())
    origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
    if (config['frozen_parent_head'], config['frozen_parent_tree']) != (PARENT, TREE):
        raise ValueError('D1_CONT_CURRENT_EXACT_PUBLIC_PARENT_REQUIRED')
    if origin['public_parent_head'] != PARENT or origin['public_parent_tree'] != TREE or len(origin['imported_paths']) != 35:
        raise ValueError('D1_CONT_CURRENT_EXACT35_RETAINED_IMPORTS_REQUIRED')
    for path, pin in source['files'].items():
        raw = (ROOT / path).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('D1_CONT_CURRENT_PINNED_SOURCE_CHANGED:' + path)
    for path, pin in origin['imported_paths'].items():
        raw = (ROOT / path).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('D1_CONT_CURRENT_FROZEN_OLD_MODULE_CHANGED:' + path)
    current_raw = (CURRENT / 'SOURCE.json').read_bytes()
    current = json.loads(current_raw)
    if sha256(current_raw).hexdigest() != SOURCE174 or len(current['files']) != 174:
        raise ValueError('D1_CONT_CURRENT_EXACT_SOURCE174_REQUIRED')
    parents = set(current['files']) | {str((CURRENT / 'SOURCE.json').relative_to(ROOT))}
    if len(parents) != 175 or set(source['frozen_parent_files']) != parents or source['frozen_D1_source'] != current:
        raise ValueError('D1_CONT_CURRENT_ALL175_PARENT_FILES_REQUIRED')
    own = {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    allowed = own | set(origin['imported_paths']) | {WORKFLOW}
    if set(source['allowed_child_paths']) != allowed or len(source['allowed_child_paths']) != len(allowed):
        raise ValueError('D1_CONT_CURRENT_EXACT_ALLOCATED_PATHS_REQUIRED')
    if set(source['files']) != (parents | allowed) - {str((HERE / 'SOURCE.json').relative_to(ROOT))}:
        raise ValueError('D1_CONT_CURRENT_EVERY_PARENT_AND_CHILD_SOURCE_REQUIRED')
    # This checker is byte-exact public17ac source and operates on actual physical files.
    load('d1_cont_current_exact_joined_parent_closure', CURRENT / 'source_check.py').check(ROOT, CURRENT, require_bound=True)
    module, _ = legacy()
    result = module.source_only()
    return result


def retained(product, source):
    return legacy()[0].retained(product, source)


def admitted(product, derivation):
    load('d1_cont_current_closed_before_parent_intake', HERE / 'gate.py').selected(cfg())
    # Entire joined parent and actual child delta close before two physical exceptions
    # and before the single fixed historical endpoint of old D1 Git-diff admission.
    source_only()
    module, proof = legacy()
    result = module.admitted(product, derivation)
    return dict(result, current_parent_private_routing=proof,
                current_public_parent=PARENT, current_parent_source_sha256=SOURCE174,
                retained_Native13_reexecuted=False, fresh_cases_credited=0)
