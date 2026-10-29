"""Independent exact vendor41c prerequisite; failed D1 is source history only."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def admitted(root, here, product, derivation):
    closure = load('s03_native11_runtime_source_check', here / 'source_check.py').check(root, here)
    cfg = json.loads((here / 'CONFIG.json').read_bytes())
    if derivation != cfg['runner_derivation']:
        raise ValueError('S03_NATIVE11_RUNTIME_ENGINE_CHANGED')
    proof_inputs = load('s03_native11_runtime_historical_inputs', here / 'proof_inputs.py')
    docs = proof_inputs.documents(here)
    prior = load('s03_native11_unchanged_prepared_parent_admission',
        root / 'scripts/current-attendance-period-choice-qualification/admission.py')
    parent = product.predecessor.sources()
    proof = prior.admit_documents(docs['CP7_VENDOR_RECEIVABLE_COMBINED11.json']['document'],
        docs['T3_PACKAGE_INSTALL.json']['document'], parent)
    # Preserve the complete current installation object, not a projected source.
    current = product.sources()
    if current['predecessor'] != parent or current['files'] != cfg['runtime_files']:
        raise ValueError('S03_NATIVE11_RUNTIME_COMPONENT_CHANGED')
    parent_digest = sha256(json.dumps(parent, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    if parent_digest != cfg['qualified_vendor_sources_sha256']:
        raise ValueError('S03_NATIVE11_EXACT_QUALIFIED_VENDOR_SOURCES_REQUIRED')
    return dict(status='EXACT_VENDOR41C_AND_PREPARED_S03_NATIVE11_ADMITTED',
        source_declaration=closure, current_installation=current,
        qualified_parent=proof, qualified_vendor_sources_sha256=parent_digest,
        retained_parent_Native7_races3_AuthHTTP1_reexecuted=False,
        D1_failed_source_base_is_runtime_prerequisite=False,
        runner_derivation=derivation, actual_Native_case_ids=cfg['Native_case_ids'],
        current_installation_entrypoint=dict(module='cp7_attendance_period_choice.composition',
            install='install', install_delta='install_delta', verify='verify',
            rollback_preuse='rollback_preuse', rollback_delta_preuse='rollback_delta_preuse'),
        fresh_race_Auth_HTTP_browser_credit=0, production_go=False, independent_acceptance=False)
