"""File-only source closure before importing a runtime or opening a database."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def offline(repo=ROOT, here=HERE):
    repo, here = Path(repo), Path(here)
    config = json.loads((here/'CONFIG.json').read_bytes())
    source = json.loads((here/'SOURCE.json').read_bytes())
    if config['contract'] != 'cp7.s05-native10-qualification.v1' or source['contract'] != config['contract']:
        raise ValueError('S05_QUALIFIER_CONTRACT_CHANGED')
    if source['production_go'] is not False or source['independent_acceptance'] is not False:
        raise ValueError('S05_PREPARATION_IS_NOT_ACCEPTANCE')
    for path, digest in source['files'].items():
        if sha256((repo/path).read_bytes()).hexdigest() != digest:
            raise ValueError('S05_QUALIFIER_SOURCE_CHANGED: '+path)
    component = repo/'scripts/cp7_accessory_standard_report'
    old = json.loads((component/'SOURCE.json').read_bytes())
    if sha256((component/'SOURCE.json').read_bytes()).hexdigest() != config['S05_manifest_sha256']:
        raise ValueError('S05_BOUNDED_COMPONENT_DECLARATION_CHANGED')
    installer_transition = load('s05_offline_bounded_installer', here/'owner_transfer/transition.py').check(repo, here/'owner_transfer')
    import_transition = load('s05_offline_import_arguments', here/'cli_import/transition.py').checked(repo, here/'cli_import')
    for path, digest in old['files'].items():
        if sha256((repo/path).read_bytes()).hexdigest() != digest:
            raise ValueError('S05_FROZEN_COMPONENT_OR_FIXTURE_CHANGED: '+path)
    tree = ast.parse((component/'cases.py').read_text())
    ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
    if list(ids) != config['Native_case_ids'] or len(ids) != len(set(ids)) or len(ids) != 10:
        raise ValueError('S05_EXACT_TEN_CASES_REQUIRED')
    derived, derivation = load('s05_offline_exact_derivation', here/'derive.py').derive((here/'frozen_vendor/probe.py').read_bytes())
    ast.parse(derived)
    if derivation != config['engine_derivation']:
        raise ValueError('S05_ENGINE_DERIVATION_CHANGED')
    prerequisite = load('s05_offline_vendor_gate', here/'gate.py').retained(repo, config)
    for path in here.glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
    return dict(status='PASS_SOURCE_ONLY_NO_RUNTIME_CREDIT', contract=config['contract'], source_files=len(source['files']),
                frozen_component_and_fixture_files=len(old['files']), Native_case_ids=list(ids),
                prerequisite=prerequisite, engine_derivation=derivation, Native_executions=0, database_calls=0,
                installer_transition=installer_transition,
                import_transition=import_transition,
                production_go=False, independent_acceptance=False)


def admitted(repo, here, product, derivation):
    check = offline(repo, here)
    config = json.loads((Path(here)/'CONFIG.json').read_bytes())
    current = product.sources()
    proof = load('s05_runtime_prerequisite_gate', Path(here)/'gate.py').retained(repo, config, current)
    if derivation != check['engine_derivation']:
        raise ValueError('S05_RUNTIME_DERIVATION_CHANGED')
    return dict(status='EXACT_VENDOR41C_BACKEND3194_AND_BOUNDED_S05_INSTALLER_ADMITTED',
                qualification=json.loads((Path(here)/'SOURCE.json').read_bytes()), current_installation=current,
                readonly_component=config['S05_manifest_sha256'], Native_case_ids=config['Native_case_ids'],
                prerequisite=proof, engine_derivation=derivation, source_only=check,
                retained_vendor11_reexecuted=False, fresh_runtime_credit_from_admission=0,
                fresh_Auth_HTTP_races_browser_claim=False, Afui_positive_HPP_zero_reimbursement_actual_coverage=False,
                production_go=False, independent_acceptance=False)
