"""Joined reviewed source closure. This module never imports the ERP runtime."""
from hashlib import sha256
from pathlib import Path
import ast
import gzip
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = 'scripts/current-credit-de-native-qualification'
WORKFLOW = '.github/workflows/cp7-credit-d1-product-phase-native13.yml'
OWNING = 'scripts/cp7_credit_correction_de/owning.sql'
MAT = 'scripts/cp7_credit_correction_de/materialize.sql'
EXECUTION_BRANCH = 'astra-a/credit-d1-product-phase-native13-20261030'
CLOSED = 'D1_PRODUCT_PHASE_CLOSED_REVIEWED_NATIVE_AUGMENTATION_REQUIRED'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(raw):
    return sha256(raw).hexdigest()


def pinned(root, path, pin):
    raw = (root / path).read_bytes()
    expected = pin if isinstance(pin, str) else pin['sha256']
    if digest(raw) != expected or isinstance(pin, dict) and len(raw) != pin['bytes']:
        raise ValueError('D1_JOINED_EXACT_SOURCE_CHANGED:' + path)
    return raw


def augmentation(cfg, root=ROOT, required=True):
    value = cfg['native_augmentation']
    if value['SOURCE'] is None or value['required_source'] is None:
        if value['SOURCE'] is not None or value['required_source'] is not None:
            raise ValueError('D1_AUGMENTATION_BINDING_MUST_BE_COMPLETE')
        if required:
            raise ValueError(CLOSED)
        return dict(status='CLOSED_PENDING_ROOT_SOURCE_BINDING', actual_Native_cases=0)
    raw = pinned(root, value['source_path'], value['required_source'])
    source = json.loads(raw)
    if source != value['SOURCE'] or not isinstance(source.get('files'), dict):
        raise ValueError('D1_AUGMENTATION_REVIEWED_DECLARATION_CHANGED')
    for path, pin in source['files'].items():
        pinned(root, path, pin)
    if value['factory_path'] not in source['files']:
        raise ValueError('D1_AUGMENTATION_FACTORY_MUST_BE_SOURCE_PINNED')
    return dict(status='EXACT_REVIEWED_AUGMENTATION_SOURCE_BOUND',
                source_sha256=digest(raw), source_files=len(source['files']))


def check(root=ROOT, here=HERE, require_bound=False):
    cfg = json.loads((here / 'CONFIG.json').read_bytes())
    parent = json.loads((here / 'PARENT.json').read_bytes())
    source = json.loads((here / 'SOURCE.json').read_bytes())
    old_cfg = json.loads(pinned(root, OLD + '/CONFIG.json', parent['old_config_sha256']))
    old_source = json.loads(pinned(root, OLD + '/SOURCE.json', parent['old_source_sha256']))
    if len(parent['old_qualifier_files']) != 20:
        raise ValueError('D1_ALL_TWENTY_RETAINED_QUALIFIER_FILES_REQUIRED')
    for path, pin in parent['old_qualifier_files'].items():
        pinned(root, path, pin)
    expected = dict(old_cfg, runtime_files=parent['runtime_after'],
        root_execution_branch=EXECUTION_BRANCH, native_augmentation=cfg['native_augmentation'],
        joined_product_transition='PARENT.json', qualified_D1_prerequisite_required=False)
    if cfg != expected or parent['runtime_before'] != old_cfg['runtime_files']:
        raise ValueError('D1_ONLY_REVIEWED_TWO_RUNTIME_PINS_AND_OWN_DECLARATION_ALLOWED')
    changed = {name for name in parent['runtime_after']
               if parent['runtime_after'][name] != parent['runtime_before'][name]}
    if changed != {'owning.sql', 'materialize.sql'}:
        raise ValueError('D1_EXACT_TWO_REVIEWED_RUNTIME_TRANSITIONS_REQUIRED')
    for name, pin in parent['runtime_after'].items():
        pinned(root, 'scripts/cp7_credit_correction_de/' + name, pin)
    aug = cfg['native_augmentation']
    if (aug['source_path'] != 'scripts/current-credit-d1-product-cap-native-augmentation/SOURCE.json'
        or aug['factory_path'] != 'scripts/current-credit-d1-product-cap-native-augmentation/factory.py'
        or aug['api'] != 'business(retained_business_module)'
        or aug['same_Native_ids'] != cfg['native_case_ids']
        or aug['single_augmented_case'] != 'D_MULTIFAMILY_ORDINAL'
        or aug['independent_acceptance'] is not False):
        raise ValueError('D1_THIRTEEN_IDS_AND_SINGLE_CALLBACK_AUGMENTATION_REQUIRED')
    # Keep all historical SOURCE declarations intact, with two explicit new pins.
    for path, pin in old_source['files'].items():
        expected_pin = parent['runtime_after'].get(Path(path).name, pin) if path in (OWNING, MAT) else pin
        if source['files'].get(path) != expected_pin:
            raise ValueError('D1_RETAINED_SOURCE_PIN_WAS_NOT_EXPLICITLY_CARRIED:' + path)
    if parent['inherited_allowed_changes'] != old_source['allowed_changes']:
        raise ValueError('D1_HISTORICAL_DIFF_ALLOWLIST_CHANGED')
    for path, pin in source['files'].items():
        pinned(root, path, pin)
    own_files = {str(path.relative_to(root)) for path in here.rglob('*')
                 if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}
    augmentation_paths = set()
    augmentation_dependencies = set()
    if aug['SOURCE'] is not None:
        prefix = 'scripts/current-credit-d1-product-cap-native-augmentation/'
        augmentation_paths = {p for p in aug['SOURCE']['files'] if p.startswith(prefix)} | {aug['source_path']}
        augmentation_dependencies = set(aug['SOURCE']['files'])
    expected_allowed = (set(old_source['allowed_changes']) |
        set(parent['joined_added_or_changed_paths']) | own_files | {WORKFLOW} | augmentation_paths)
    if set(source['allowed_changes']) != expected_allowed or len(source['allowed_changes']) != len(expected_allowed):
        raise ValueError('D1_JOINED_EXACT_PATH_ALLOWLIST_REQUIRED')
    expected_files = (expected_allowed - {str((here / 'SOURCE.json').relative_to(root))}) | augmentation_dependencies
    if set(source['files']) != expected_files:
        raise ValueError('D1_EVERY_ALLOWED_FILE_EXCEPT_SELF_MUST_BE_SOURCE_PINNED')
    if aug['SOURCE'] is not None:
        binding = json.loads((here / 'AUGMENTATION_BINDING.json').read_bytes())
        if (binding['frozen_augmentation_commit'] != aug['frozen_commit']
            or binding['frozen_augmentation_tree'] != aug['frozen_tree']
            or binding['source_required_sha256'] != aug['required_source']
            or len(binding['copied_namespace_files']) != 16
            or set(binding['copied_namespace_files']) != augmentation_paths
            or binding['SOURCE_and_API_regenerated'] is not False):
            raise ValueError('D1_EXACT_REVIEWED_AUGMENTATION_COPY_BINDING_REQUIRED')
        for path, pin in binding['copied_namespace_files'].items():
            pinned(root, path, pin)
    review = parent['reviewed_counterparts']
    quote = json.loads(pinned(root, review['quote']['path'], review['quote']['sha256']))
    exception = review['quote']['only_file_exception']
    if exception != dict(path=MAT, before=parent['runtime_before']['materialize.sql'],
                         after=parent['runtime_after']['materialize.sql']):
        raise ValueError('D1_QUOTE_PRECISE_MATERIALIZE_EXCEPTION_REQUIRED')
    for path, pin in quote['files'].items():
        if path == exception['path']:
            if pin['sha256'] != exception['before']:
                raise ValueError('D1_QUOTE_HISTORICAL_MATERIALIZE_PIN_CHANGED')
            pinned(root, path, exception['after'])
        else:
            pinned(root, path, pin)
    phase = json.loads(pinned(root, review['phase']['path'], review['phase']['sha256']))
    for path, pin in phase['files'].items():
        pinned(root, path, pin)
    quote_helper = load('d1_joined_pure_quote_scope', root / 'scripts/current-credit-d1-product-cap-qualification/source_check.py')
    quote_scope = quote_helper.quote_scope((root / review['quote']['original_owning']).read_text(), (root / OWNING).read_text())
    phase_helper = load('d1_joined_pure_phase_scope', root / 'scripts/current-credit-d1-materialize-phase-successor/check.py')
    phase_scope = phase_helper.derivation((root / review['phase']['original_materialize']).read_bytes(), (root / MAT).read_bytes())
    tree = ast.parse((root / 'scripts/cp7_credit_correction_de/cases.py').read_text())
    ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
    if list(ids) != cfg['native_case_ids'] or len(set(ids)) != 13:
        raise ValueError('D1_EXACT_RETAINED_THIRTEEN_IDS_REQUIRED')
    from_failure = here / 'retained_d902'
    receipt = json.loads((from_failure / 'RECEIPT.json').read_bytes())
    if (receipt['case_counts'] != {'PASS': 4, 'INCOMPLETE': 9}
        or receipt['usable_as_Native13_prerequisite'] is not False
        or receipt['case_ids'] != cfg['native_case_ids']):
        raise ValueError('D1_D902_IS_FAILED_EVIDENCE_NEVER_PREREQUISITE')
    for name, pin in receipt['files'].items():
        packed = (from_failure / (name + '.gz')).read_bytes()
        raw = gzip.decompress(packed)
        if digest(raw) != pin['raw_sha256'] or len(raw) != pin['raw_bytes'] or digest(packed) != pin['gzip_sha256']:
            raise ValueError('D1_D902_FIRST_FAILURE_RAW_CHANGED:' + name)
    derive = load('d1_joined_private_native_source_derivation', here / 'derive.py')
    native_code, native_proof = derive.native_runner((root / OLD / 'native_runner.py').read_bytes())
    if native_proof != json.loads((here / 'NATIVE_RUNNER_DERIVATION.json').read_bytes()):
        raise ValueError('D1_EXACT_ONE_IMPORT_DERIVATION_CHANGED')
    legacy_derive = load('d1_joined_retained_six_vendor_changes', root / OLD / 'derive.py')
    _, vendor_proof = legacy_derive.derive((root / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes())
    if vendor_proof != cfg['runner_derivation']:
        raise ValueError('D1_RETAINED_COMPLETE_VENDOR_ENGINE_DERIVATION_CHANGED')
    workflow = load('d1_joined_exact_workflow_source_derivation', here / 'workflow.py')
    workflow_raw, workflow_proof = workflow.derive((root / workflow.OLD_PATH).read_bytes())
    if workflow_raw != (root / WORKFLOW).read_bytes() or workflow_proof != json.loads((here / 'WORKFLOW_DERIVATION.json').read_bytes()):
        raise ValueError('D1_ONLY_DECLARED_WORKFLOW_ROUTING_CHANGES_ALLOWED')
    # Historical failures are evidence only. Their complete original bytes stay pinned.
    original077 = json.loads((root / OLD / 'retained077/RECEIPT.json').read_bytes())
    if original077['status'] != 'INCOMPLETE' or original077['actual_Native_cases'] != 0:
        raise ValueError('D1_077_INSTALL_FAILURE_CANNOT_BECOME_A_PREREQUISITE')
    a994 = json.loads((root / 'scripts/cp7_credit_correction_de/evidence/native_cap_successor/A994_FIRST_FAILURE.json').read_bytes())
    if a994['counts'] != {'PASS': 5, 'INCOMPLETE': 8} or a994['actual_Native13_success'] is not False:
        raise ValueError('D1_A994_INCOMPLETE_CANNOT_BECOME_A_PREREQUISITE')
    bound = augmentation(cfg, root, required=require_bound)
    return dict(status='PREPARED_JOINED_SOURCE_ONLY', source_files=len(source['files']),
        retained_qualifier_files=20, changed_runtime_leaves=sorted(changed), quote=quote_scope,
        phase=phase_scope, augmentation=bound, qualified_parent=cfg['qualified_parent'],
        private_native_runner_derivation=native_proof, complete_vendor_engine_derivation=vendor_proof,
        D902_counts={'PASS': 4, 'INCOMPLETE': 9}, D902_usable_prerequisite=False,
        actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
        production_go=False, independent_acceptance=False)
