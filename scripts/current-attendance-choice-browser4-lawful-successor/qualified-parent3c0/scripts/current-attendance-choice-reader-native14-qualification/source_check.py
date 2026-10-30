"""Full actual current closure precedes explicitly adapted historical intake.

Retained80 is history only. Actual authored product/prepared/Reader3 files must
all match the separately published root alias and explicit transitions.
"""
from pathlib import Path, PurePosixPath
from hashlib import sha256
from types import ModuleType
import ast
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = 'scripts/current-attendance-period-choice-native11-qualification'
NS = 'scripts/current-attendance-choice-reader-native14-qualification'
WORKFLOW = '.github/workflows/cp7-s03-choice-reader-native14.yml'
BASE = '9a0ca1de04723717c9d6635b8d3a6bd094233b97'
BASE_TREE = '9b13113d5ec63afb95874d41f06699e0016744b3'
SOURCE251 = 'cc2dc65b6f73b288a34fc7dc9ad5e745f18b0f066595b02572e31804956cd438'
PREFIXES = ('scripts/cp7_attendance_period_choice/',
            'scripts/current-attendance-period-choice-qualification/',
            'scripts/current-attendance-period-choice-readers-qualification/')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def pinned(root, name, pin):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or str(relative) != name:
        raise ValueError('S03_NATIVE14_UNSAFE_SOURCE_PATH:' + name)
    path = Path(root)
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('S03_NATIVE14_SOURCE_SYMLINK:' + name)
    raw = path.read_bytes()
    if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('S03_NATIVE14_EXACT_SOURCE_CHANGED:' + name)
    return raw


def historical(root, here, origin):
    raw = (here / 'retained_9a0/native11/SOURCE.json').read_bytes()
    if sha256(raw).hexdigest() != SOURCE251 or raw != (root / OLD / 'SOURCE.json').read_bytes():
        raise ValueError('S03_NATIVE14_OLD251_SOURCE_MUST_REMAIN_HISTORICAL_EXACT')
    prior = json.loads(raw)
    if len(prior['files']) != 251:
        raise ValueError('S03_NATIVE14_EXACT_HISTORICAL251_REQUIRED')
    for name, pin in origin['unchanged_old_native11_namespace'].items():
        pinned(root, name, pin)
    if len(origin['historical_old80_files']) != 80:
        raise ValueError('S03_NATIVE14_EXACT_HISTORICAL80_REQUIRED')
    for name, pin in origin['historical_old80_files'].items():
        pinned(here / 'retained_9a0/source80', name, pin)
    return prior


def binding(root, here, cfg, origin):
    gate = load('s03_native14_current_exact_binding_gate', here / 'gate.py')
    current = gate.selected(cfg)
    git = lambda *args: subprocess.check_output(['git', '-C', str(root), *args])
    if git('rev-parse', current['head'] + '^{tree}').decode().strip() != current['tree']:
        raise ValueError('S03_NATIVE14_EXACT_PUBLIC_BACKEND_ALIAS_TREE_REQUIRED')
    paths = set(git('ls-tree', '-r', '--name-only', current['head'], *(p[:-1] for p in PREFIXES)).decode().splitlines())
    if paths != set(current['files']) or any(not p.startswith(PREFIXES) for p in paths):
        raise ValueError('S03_NATIVE14_EVERY_AUTHORED_THREE_PREFIX_FILE_REQUIRED')
    for name, pin in current['files'].items():
        raw = pinned(root, name, pin)
        if raw != git('show', current['head'] + ':' + name):
            raise ValueError('S03_NATIVE14_FROZEN_AUTHORED_ALIAS_BODY_CHANGED:' + name)
    for key in ('source', 'API'):
        pin = current[key]
        if pin['path'] not in current['files'] or pinned(root, pin['path'], pin) != git('show', current['head'] + ':' + pin['path']):
            raise ValueError('S03_NATIVE14_SOURCE_API_MUST_BELONG_TO_FROZEN_ALIAS:' + key)
    expected_runtime = current['runtime_files']
    if cfg['runtime_files'] != expected_runtime or len(expected_runtime) != 7:
        raise ValueError('S03_NATIVE14_EXACT_SEVEN_CURRENT_RUNTIME_PINS_REQUIRED')
    for name, digest in expected_runtime.items():
        if name not in current['files'] or current['files'][name]['sha256'] != digest:
            raise ValueError('S03_NATIVE14_RUNTIME_OUTSIDE_ACTUAL_AUTHORED_ALIAS:' + name)
    before80 = origin['historical_old80_files']
    transitions = {name: dict(before=before80[name], after=current['files'][name])
                   for name in before80 if current['files'].get(name) != before80[name]}
    if any(name not in current['files'] for name in before80):
        raise ValueError('S03_NATIVE14_FROZEN_ORIGINAL80_PATH_REMOVED')
    if transitions != current['old80_transitions']:
        raise ValueError('S03_NATIVE14_EXPLICIT_EVERY_CHANGED_OLD80_PIN_REQUIRED')
    cases = 'scripts/current-attendance-period-choice-qualification/cases.py'
    if current['files'][cases]['sha256'] != origin['original11_cases_sha256']:
        raise ValueError('S03_NATIVE14_ORIGINAL11_FINANCIAL_BODIES_MUST_REMAIN_EXACT')
    reader_path = 'scripts/current-attendance-period-choice-readers-qualification/cases.py'
    reader_tree = ast.parse((root / reader_path).read_text())
    reader_ids = [ast.literal_eval(n.value) for n in reader_tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets)]
    factories = [n for n in reader_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'cases']
    if len(reader_ids) != 1 or list(reader_ids[0]) != cfg['reader_Native3_ids'] or len(factories) != 1:
        raise ValueError('S03_NATIVE14_FROZEN_READER3_FACTORY_IDS_REQUIRED')
    args = factories[0].args
    names = [n.arg for n in args.posonlyargs + args.args]
    keywords = {n.arg for n in args.kwonlyargs} | set(names[2:])
    if names[:2] != ['cur', 'today'] or not {'state', 'evidence', 'fresh_original11'} <= keywords:
        raise ValueError('S03_NATIVE14_ACTUAL_READER_FACTORY_ABI_CHANGED')
    # Same parent Original readers; metadata/helper ownership belongs to author.
    admission = 'scripts/current-attendance-period-choice-qualification/admission.py'
    before = ast.parse((here / 'retained_9a0/source80' / admission).read_text())
    after = ast.parse((root / admission).read_text())
    functions = lambda tree: {n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, ast.FunctionDef)}
    old_functions, new_functions = functions(before), functions(after)
    if any(old_functions[key] != new_functions.get(key) for key in ('read_original', 'admit_documents')):
        raise ValueError('S03_NATIVE14_RETAINED_ORIGINAL_READERS_CHANGED')
    return current


def private_intake(root, here):
    raw = (root / OLD / 'source_check.py').read_bytes()
    code, proof = load('s03_native14_historical_metadata_deriver', here / 'derive.py').source_checker(raw)
    module = ModuleType('s03_native14_private_metadata_intake')
    module.__file__ = str(root / OLD / 'source_check.py')
    exec(compile(code, module.__file__, 'exec'), module.__dict__)
    return module.check(root, here), proof


def check(root=ROOT, here=HERE, require_bound=False):
    root, here = Path(root), Path(here)
    cfg = json.loads((here / 'CONFIG.json').read_bytes())
    source = json.loads((here / 'SOURCE.json').read_bytes())
    origin = json.loads((here / 'ORIGIN.json').read_bytes())
    if (cfg.get('qualification_contract') != 'cp7.attendance-choice-reader-native14.v1'
            or cfg['source_base'] != BASE or cfg['source_base_tree'] != BASE_TREE
            or cfg['source_base_is_runtime_prerequisite'] is not False
            or source['Native_executed'] is not False):
        raise ValueError('S03_NATIVE14_NEW_CLOSED_QUALIFICATION_CONTRACT_REQUIRED')
    prior = historical(root, here, origin)
    for name, pin in source['files'].items():
        pinned(root, name, pin)
    for name, digest in (('generated_receipts.py', 'a569138a5b6d4c0d1ce542ab45af98ee156f47e6d772766c214bbae3366ffc7e'),
                         ('generated_later.py', '7bf35d85d9f7ec19da34c5626f24af908f3691a4e3ed7251dbc4958e59b4bea3')):
        if sha256((here / name).read_bytes()).hexdigest() != digest:
            raise ValueError('S03_NATIVE14_INHERITED_OUTPUT_VALIDATOR_CHANGED:' + name)
    own = {str(p.relative_to(root)) for p in here.rglob('*')
           if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    alias = cfg['backend_binding']
    product_paths = set() if alias is None else set(alias['files'])
    allowed = own | product_paths | {WORKFLOW}
    if set(source['allowed_changes']) != allowed:
        raise ValueError('S03_NATIVE14_EXACT_NEW_NAMESPACE_AND_AUTHORED_PATH_ALLOCATION_REQUIRED')
    expected = (set(prior['files']) | set(origin['unchanged_old_native11_namespace']) |
                allowed | set(source['producer_source_paths'])) - {str((here / 'SOURCE.json').relative_to(root))}
    if set(source['files']) != expected:
        raise ValueError('S03_NATIVE14_EVERY_CURRENT_SOURCE_AND_HISTORICAL_INPUT_MUST_BE_PINNED')
    for name, old_pin in prior['files'].items():
        current_pin = alias['files'][name] if alias is not None and name in alias['files'] else old_pin
        if source['files'][name] != current_pin:
            raise ValueError('S03_NATIVE14_UNDECLARED_OLD251_PIN_TRANSITION:' + name)
    git = lambda *args: subprocess.check_output(['git', '-C', str(root), *args], text=True)
    if git('rev-parse', BASE + '^{tree}').strip() != BASE_TREE:
        raise ValueError('S03_NATIVE14_EXACT_PUBLIC_FAILED_BASE_TREE_REQUIRED')
    changed = set(git('diff', '--name-only', BASE, 'HEAD').splitlines())
    if not changed <= allowed or git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('S03_NATIVE14_CURRENT_TRACKED_SOURCE_DELTA_OR_DIRTY_TREE')
    allowed_untracked = set(source['files']) | {str((here / 'SOURCE.json').relative_to(root))}
    allowed_untracked.update(source['untracked_historical_proof_inputs'])
    allowed_untracked.update(source['inherited_untracked_workflow_proof_inputs'])
    for name, pin in source['inherited_untracked_workflow_proof_inputs'].items():
        if (root / name).exists():
            pinned(root, name, pin)
    untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    p0, p0_proof = load('s03_native14_exact_P0_output_validator', here / 'generated_receipts.py').admit(root, here, untracked - allowed_untracked)
    allowed_untracked.update(p0)
    later, later_proof = load('s03_native14_exact_later_output_validator', here / 'generated_later.py').admit(root, here, untracked - allowed_untracked)
    allowed_untracked.update(later)
    if not untracked <= allowed_untracked:
        raise ValueError('S03_NATIVE14_UNKNOWN_SOURCE_OR_GENERATED_OUTPUT:' + repr(sorted(untracked - allowed_untracked)))
    inputs = load('s03_native14_read_only_four_Originals', here / 'proof_inputs.py')
    inputs.documents(here)
    if alias is None:
        if require_bound:
            load('s03_native14_null_before_any_ERP', here / 'gate.py').selected(cfg)
        return dict(status='SOURCE_CLOSED_PREPARATION_ONLY', files=len(source['files']),
            historical_files=80, current_backend_bound=False, actual_Native_cases=0,
            actual_Auth_HTTP_cases=0, actual_browser_cases=0, generated_outputs=p0_proof,
            later_generated_outputs=later_proof, production_go=False)
    current = binding(root, here, cfg, origin)
    inner, derivation = private_intake(root, here)
    return dict(status='EXACT_CURRENT_SOURCE15_FRESH_NATIVE11_PLUS_READER3_PLAN', files=len(source['files']),
        actual_authored_files=len(current['files']), exact_runtime_files=7, captured_originals=15,
        private_clones=2, actual_Native_case_plan=cfg['Native_case_ids'], groups=[11, 3],
        historical80_is_current_product_projection=False, historical_inner_intake=inner,
        historical_metadata_derivation=derivation, Native_executed=False,
        generated_outputs=p0_proof, later_generated_outputs=later_proof,
        accepted_successful_Native11_prerequisite_required=False, production_go=False, independent_acceptance=False)
