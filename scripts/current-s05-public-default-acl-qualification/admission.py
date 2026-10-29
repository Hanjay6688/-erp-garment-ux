"""Closed successor source admission; no DB, Git, network or historical repinning."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = 'scripts/current-s05-native10-qualification'
REPAIR = 'scripts/current-s05-public-default-acl-repair'
COMPONENT = 'scripts/cp7_accessory_standard_report/'
CHANGED_PRODUCT = {COMPONENT+name for name in ('SOURCE.json', 'stage.py', 'report.sql')}
CONTRACT = 'cp7.s05-public-default-acl-qualification.v1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def offline(repo=ROOT, here=HERE):
    repo, here = Path(repo), Path(here)
    config = json.loads((here/'CONFIG.json').read_bytes())
    source = json.loads((here/'SOURCE.json').read_bytes())
    if config['contract'] != CONTRACT or source['contract'] != CONTRACT:
        raise ValueError('S05_ACL_SUCCESSOR_CONTRACT_CHANGED')
    if source['production_go'] is not False or source['independent_acceptance'] is not False:
        raise ValueError('S05_ACL_SOURCE_IS_NOT_ACCEPTANCE')
    for path, digest in source['files'].items():
        if sha256((repo/path).read_bytes()).hexdigest() != digest:
            raise ValueError('S05_ACL_SOURCE_CHANGED: '+path)
    old_raw = (repo/OLD/'SOURCE.json').read_bytes()
    if sha256(old_raw).hexdigest() != config['inherited_qualifier_manifest_sha256']:
        raise ValueError('S05_B0_QUALIFIER_MANIFEST_CHANGED')
    old_source = json.loads(old_raw)
    for path, digest in old_source['files'].items():
        if path not in CHANGED_PRODUCT and source['files'].get(path) != digest:
            raise ValueError('S05_B0_FROZEN_QUALIFIER_PARENT_OR_ORACLE_REPINNED: '+path)
    old_config = json.loads((repo/OLD/'CONFIG.json').read_bytes())
    if config['inherited_configuration'] != old_config:
        raise ValueError('S05_B0_VENDOR_GATE_OR_ENGINE_CONFIGURATION_CHANGED')
    allowed_extra = lambda path: (path.startswith(REPAIR+'/') or path.startswith(str(here.relative_to(repo))+'/')
                                  or path == config['workflow'] or path == OLD+'/SOURCE.json')
    if any(not allowed_extra(path) for path in set(source['files'])-set(old_source['files'])):
        raise ValueError('S05_ACL_UNDECLARED_SOURCE_EXTENSION')
    for path in CHANGED_PRODUCT:
        if path not in source['files']:
            raise ValueError('S05_ACL_EXACT_PRODUCT_TRANSITION_PINS_REQUIRED')
    repair = load('s05_acl_bounded_product_transition', repo/REPAIR/'transition.py').check(repo)
    manifest = (repo/(COMPONENT+'SOURCE.json')).read_bytes()
    if sha256(manifest).hexdigest() != config['S05_manifest_sha256']:
        raise ValueError('S05_ACL_BOUNDED_COMPONENT_MANIFEST_CHANGED')
    component = json.loads(manifest)
    ids_tree = ast.parse((repo/(COMPONENT+'cases.py')).read_bytes())
    ids = next(ast.literal_eval(n.value) for n in ids_tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
    if list(ids) != old_config['Native_case_ids'] or component['Native_case_ids'] != list(ids) or len(ids) != len(set(ids)) or len(ids) != 10:
        raise ValueError('S05_ACL_EXACT_UNCHANGED_NATIVE10_REQUIRED')
    inherited = repo/OLD
    engine, derivation = load('s05_acl_retained_six_change_derivation', inherited/'derive.py').derive(
        (inherited/'frozen_vendor/probe.py').read_bytes())
    ast.parse(engine)
    if derivation != old_config['engine_derivation']:
        raise ValueError('S05_ACL_FULL_RESTORE_ENGINE_DERIVATION_CHANGED')
    prerequisite = load('s05_acl_retained_vendor_gate', inherited/'gate.py').retained(repo, old_config)
    failure = load('s05_acl_retained_b0_failure', here/'first_failure.py').checked(here)
    workflow = load('s05_acl_workflow_derivation', here/'workflow_source.py').checked(
        (repo/config['workflow']).read_text())
    for path in here.glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
    return dict(status='PASS_SOURCE_ONLY_NO_RUNTIME_CREDIT', contract=CONTRACT,
        source_files=len(source['files']), frozen_component_and_fixture_files=len(component['files']),
        Native_case_ids=list(ids), prerequisite=prerequisite, bounded_product_transition=repair,
        retained_b0_failure=failure, engine_derivation=derivation, workflow_derivation=workflow,
        old_qualifier_files_and_manifests_unchanged=True,
        Native_executions=0, database_calls=0, production_go=False, independent_acceptance=False)


def admitted(repo, here, product, derivation):
    check = offline(repo, here)
    config = json.loads((Path(here)/'CONFIG.json').read_bytes())
    current = product.sources()
    prerequisite = load('s05_acl_runtime_vendor_gate', Path(repo)/OLD/'gate.py').retained(
        repo, config['inherited_configuration'], current)
    if derivation != check['engine_derivation']:
        raise ValueError('S05_ACL_RUNTIME_ENGINE_DERIVATION_CHANGED')
    return dict(status='EXACT_VENDOR41C_BACKEND3194_AND_BOUNDED_S05_PUBLIC_ACL_ADMITTED',
        qualification=json.loads((Path(here)/'SOURCE.json').read_bytes()), current_installation=current,
        readonly_component=config['S05_manifest_sha256'], Native_case_ids=check['Native_case_ids'],
        prerequisite=prerequisite, bounded_product_transition=check['bounded_product_transition'],
        retained_b0_failure=check['retained_b0_failure'], engine_derivation=derivation, source_only=check,
        retained_vendor11_reexecuted=False, fresh_runtime_credit_from_admission=0,
        fresh_Auth_HTTP_races_browser_claim=False, Afui_positive_HPP_zero_reimbursement_actual_coverage=False,
        actual_CI_extra_tuple_identity_proven=False, production_go=False, independent_acceptance=False)
