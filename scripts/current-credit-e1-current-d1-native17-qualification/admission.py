"""Explicit full E delta, then unchanged current-D1 closure and private intake."""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'scripts/current-credit-e1-native-qualification'
CURRENT = ROOT / 'scripts/current-credit-d1-product-phase-native13-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def legacy():
    text, proof = load('e1_current_bounded_source_derivation', HERE / 'derive.py').admission((OLD / 'admission.py').read_bytes())
    module = ModuleType('e1_current_private_legacy_admission')
    module.__file__ = str(HERE / 'admission.py')  # Its existing HERE/ROOT parser uses NEW declarations.
    exec(compile(text, str(OLD / 'admission.py'), 'exec'), module.__dict__)
    return module, proof


def source_only():
    # Exact current delta and every frozen parent path are checked first.
    module, private_proof = legacy()
    source = module.source_only()
    load('e1_current_exact_source_API_boundary', HERE / 'api_check.py').check()
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
    transition = json.loads((HERE / 'TRANSITION.json').read_bytes())
    imports = json.loads((HERE / 'E_IMPORT.json').read_bytes())
    exceptions = set(imports['changed_paths_explicit'])
    if exceptions != {'scripts/cp7_credit_correction_de/e_cases.py', 'scripts/cp7_credit_correction_de/E_DEPENDENCIES.json'}:
        raise ValueError('E1_CURRENT_PRECISE_TWO_E_IMPORT_TRANSITIONS_REQUIRED')
    for path, pin in origin['imported_old_E_paths'].items():
        if path in exceptions:
            continue
        raw = (ROOT / path).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('E1_CURRENT_FROZEN_OLD_E_INPUT_CHANGED:' + path)
    for path, pin in origin['imported_feba_namespace_paths'].items():
        raw = (ROOT / path).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('E1_CURRENT_FROZEN_FEBA_PROVENANCE_CHANGED:' + path)
    case_path = 'scripts/cp7_credit_correction_de/e_cases.py'
    if sha256((HERE / 'evidence/e_cases.before_feba.py.txt').read_bytes()).hexdigest() != origin['imported_old_E_paths'][case_path]['sha256']:
        raise ValueError('E1_CURRENT_RETAINED_BEFORE_FEBA_CALLBACK_SOURCE_CHANGED')
    if sha256((ROOT / case_path).read_bytes()).hexdigest() != origin['feba_case_sha256']:
        raise ValueError('E1_CURRENT_EXACT_FEBA_SEVENTEEN_CALLBACKS_REQUIRED')
    deps_path = ROOT / 'scripts/cp7_credit_correction_de/E_DEPENDENCIES.json'
    if sha256(deps_path.read_bytes()).hexdigest() != transition['E_dependencies_current_sha256']:
        raise ValueError('E1_CURRENT_REVIEWED_E_DEPENDENCY_TRANSITION_CHANGED')
    deps = json.loads(deps_path.read_bytes())
    if set(transition['E_dependency_changed_keys']) != {
        'required_parent_actual_gate', 'unchanged_D1_core_sha256', 'retained_helper_sha256',
        'current_D1_source_qualification', 'historical_D1_guard_superseded_by_E17'}:
        raise ValueError('E1_CURRENT_ONLY_DECLARED_SOURCE_METADATA_TRANSITIONS_ALLOWED')
    for name, expected in origin['financial_E_runtime_leaves_unchanged'].items():
        if sha256((ROOT / 'scripts/cp7_credit_correction_de' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('E1_CURRENT_NINE_E_FINANCIAL_LEAVES_MUST_REMAIN_EXACT:' + name)
    if len(origin['financial_E_runtime_leaves_unchanged']) != 9 or deps['runtime_sources'] != cfg['E_runtime_files']:
        raise ValueError('E1_CURRENT_EXACT_NINE_E_RUNTIME_PINS_REQUIRED')
    for name, expected in deps['unchanged_D1_core_sha256'].items():
        if sha256((ROOT / 'scripts/cp7_credit_correction_de' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('E1_CURRENT_DECLARED_D1_DEPENDENCY_CHANGED:' + name)
    for path, expected in deps['retained_helper_sha256'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError('E1_CURRENT_RETAINED_FIXTURE_API_CHANGED:' + path)
    current_raw = (ROOT / cfg['current_D1_source_path']).read_bytes()
    if sha256(current_raw).hexdigest() != cfg['current_D1_source_sha256'] or len(json.loads(current_raw)['files']) != 174:
        raise ValueError('E1_CURRENT_EXACT_PARENT_SOURCE174_REQUIRED')
    # Byte-exact joined quote/phase/augmentation checker; no catalogue projection.
    current = load('e1_current_exact_D1_joined_closure', CURRENT / 'source_check.py').check(ROOT, CURRENT, require_bound=True)
    if current['augmentation']['source_sha256'] != '79cf8ca8ca72de93fba2c2da29e3777bc64ee0cf84bd1bdf71256d203589790d':
        raise ValueError('E1_CURRENT_FROZEN_D1_AUGMENTATION_REQUIRED')
    if transition['parent_Native13_rerun_after_E_install'] is not False:
        raise ValueError('E1_CURRENT_PARENT_THIRTEENTH_GUARD_IS_HISTORICAL_ONLY')
    return source


def admitted(product, derivation):
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    load('e1_current_root_terminal_gate', HERE / 'gate.py').selected(cfg)
    source_only()  # Full current E diff closure precedes fixed historical endpoint.
    module, private_proof = legacy()
    proof = module.admitted(product, derivation)
    return dict(proof, current_D1_private_intake_derivation=private_proof,
                parent_Native13_reexecuted_after_E_install=False,
                historical_guard_superseded_by_implemented_E17=True)
