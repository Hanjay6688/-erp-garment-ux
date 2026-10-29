"""Explicit child closure over a frozen public D1 source; no projected catalog."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import ast
import gzip
import importlib.util
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-credit-e1-native-qualification/'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def cfg():
    return json.loads((HERE/'CONFIG.json').read_bytes())


def source_only():
    config, source = cfg(), json.loads((HERE/'SOURCE.json').read_bytes())
    for name, pin in source['files'].items():
        raw = (ROOT/name).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('E1_DECLARED_CHILD_SOURCE_CHANGED:' + name)
    git = lambda *args: subprocess.check_output(['git', '-C', str(ROOT), *args])
    if git('rev-parse', config['frozen_parent_head']+'^{tree}').decode().strip() != config['frozen_parent_tree']:
        raise ValueError('E1_EXACT_FROZEN_PARENT_TREE_REQUIRED')
    for name, pin in source['frozen_parent_files'].items():
        raw = (ROOT/name).read_bytes()
        if raw != git('show', config['frozen_parent_head']+':'+name) or sha256(raw).hexdigest() != pin:
            raise ValueError('E1_FROZEN_D1_SOURCE_CHANGED:' + name)
    actual = set(git('diff', '--name-only', config['frozen_parent_head'], 'HEAD').decode().splitlines())
    if not actual <= set(source['allowed_child_paths']):
        raise ValueError('E1_UNDECLARED_CHILD_PATH')
    if git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('E1_COMMITTED_CLEAN_SOURCE_REQUIRED')
    old = json.loads((ROOT/'scripts/current-credit-de-native-qualification/SOURCE.json').read_bytes())
    if old != source['frozen_D1_source']:
        raise ValueError('E1_EXACT_OLD_D1_DECLARATION_REQUIRED')
    for name, digest in old['files'].items():
        if sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError('E1_CURRENT_OLD_D1_SOURCE_HASH_CHANGED:' + name)
    imports = json.loads((HERE/'E_IMPORT.json').read_bytes())
    for name, digest in imports['files'].items():
        if sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError('E1_REVIEWED_E_IMPORT_CHANGED:' + name)
    failure = config['retained_failed_D1']
    load('e1_retained_failure_source_control', HERE/'gate.py').retained_failure(config, gzip.decompress((ROOT/failure['path']).read_bytes()))
    return source


def historical_D1_admission(raw, parent):
    if not re.fullmatch('[a-f0-9]{40}', parent):
        raise ValueError('E1_EXPLICIT_PUBLIC_PARENT_COMMIT_REQUIRED')
    old = "changed = git('diff', '--name-only', cfg['base_head'], 'HEAD').decode().splitlines()"
    new = "changed = git('diff', '--name-only', cfg['base_head'], '"+parent+"').decode().splitlines()"
    text = raw.decode()
    if text.count(old) != 1:
        raise ValueError('E1_EXACT_HISTORICAL_D1_ADMISSION_ANCHOR_REQUIRED')
    return text.replace(old, new, 1), dict(counted_changes=1, original_sha256=sha256(raw).hexdigest(),
        fixed_historical_diff_head=parent, all_current_old_hash_checks_retained=True)


def retained(product, source):
    config = cfg()
    gate = load('e1_exact_parent_gate', HERE/'gate.py')
    pin = gate.selected(config)
    folder = Path(os.environ['CP7_E1_D1_ORIGINALS'])
    raw = {key: (folder/pin[key]['name']).read_bytes() for key in ('original', 'native_group', 'package')}
    ids = load('e1_exact_parent_case_ids', HERE/'plan.py').D1_IDS
    return gate.admitted(config, raw, product.predecessor.sources(), source['frozen_D1_source'], ids)


def admitted(product, derivation):
    config = cfg()
    load('e1_closed_before_runtime_admission', HERE/'gate.py').selected(config)
    source = source_only()
    proof = retained(product, source)
    original = ROOT/'scripts/current-credit-de-native-qualification/admission.py'
    text, historical = historical_D1_admission(original.read_bytes(), config['frozen_parent_head'])
    old = ModuleType('e1_frozen_historical_D1_admission'); old.__file__ = str(original)
    exec(compile(text, str(original), 'exec'), old.__dict__)
    prior = old.admitted(ROOT, original.parent, product.predecessor, derivation)
    current = product.sources()
    if current['predecessor'] != prior['current_installation'] or current['files'] != config['E_runtime_files']:
        raise ValueError('E1_EXACT_E_DELTA_AND_QUALIFIED_D1_REQUIRED')
    ids = load('e1_actual_case_plan', HERE/'plan.py').E_IDS
    tree = ast.parse((ROOT/'scripts/cp7_credit_correction_de/e_cases.py').read_text())
    selected = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
    if list(ids) != list(selected):
        raise ValueError('E1_EXACT_UNCHANGED_SEVENTEEN_CASES_REQUIRED')
    return dict(status='EXACT_QUALIFIED_D1_AND_CLOSED_SOURCE_E1_CHILD_ADMITTED', qualification=source,
        current_installation=current, retained_D1=proof, historical_D1_admission=prior,
        historical_scope_derivation=historical, runner_derivation=derivation, actual_Native_case_ids=list(ids),
        retained_D1_reexecuted=False, fresh_cases_credited=0, D_complete=False, E_complete=False,
        production_go=False, independent_acceptance=False)
