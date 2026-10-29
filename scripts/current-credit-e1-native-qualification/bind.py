"""Writer-only binding. Root reviews prerequisite transitions; never run in CI."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-credit-e1-native-qualification/'
WORKFLOW = '.github/workflows/cp7-credit-e1-native17.yml'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def bind():
    if os.environ.get('CI'):
        raise ValueError('E1_EXPECTED_SOURCE_CANNOT_BE_REGENERATED_IN_CI')
    config = json.loads((HERE/'CONFIG.json').read_bytes())
    git = lambda *args: subprocess.check_output(['git', '-C', str(ROOT), *args])
    parent = config['frozen_parent_head']
    assert git('rev-parse', parent+'^{tree}').decode().strip() == config['frozen_parent_tree']
    old_path = 'scripts/current-credit-de-native-qualification/SOURCE.json'
    old_raw = git('show', parent+':'+old_path)
    assert (ROOT/old_path).read_bytes() == old_raw
    old = json.loads(old_raw)
    frozen = set(old['files']) | {old_path, '.github/workflows/cp7-credit-de-native.yml'}
    prior_cfg = json.loads(git('show', parent+':scripts/current-credit-de-native-qualification/CONFIG.json'))
    frozen |= set(prior_cfg['unchanged_parent_files']) | set(prior_cfg['signed_dependencies'])
    frozen |= set(git('ls-tree', '-r', '--name-only', parent, 'scripts/current-credit-de-native-qualification').decode().splitlines())
    frozen |= set(git('diff', '--name-only', config['source_base_head'], parent).decode().splitlines())
    parent_files = {}
    for name in sorted(frozen):
        raw = git('show', parent+':'+name)
        assert (ROOT/name).read_bytes() == raw, 'E1_PARENT_REPAIR_OR_ORIGINAL_NOT_RETAINED:'+name
        parent_files[name] = sha256(raw).hexdigest()
    imports = json.loads((HERE/'E_IMPORT.json').read_bytes())
    for name, digest in imports['files'].items():
        assert sha256((ROOT/name).read_bytes()).hexdigest() == digest, 'E1_IMPORT_CHANGED:'+name
    deps = json.loads((ROOT/'scripts/cp7_credit_correction_de/E_DEPENDENCIES.json').read_bytes())
    for name, digest in deps['runtime_sources'].items():
        assert sha256((ROOT/'scripts/cp7_credit_correction_de'/name).read_bytes()).hexdigest() == digest
    for name, digest in deps['unchanged_D1_core_sha256'].items():
        assert sha256((ROOT/'scripts/cp7_credit_correction_de'/name).read_bytes()).hexdigest() == digest, 'E1_D1_DEPENDENCY_REVIEW_REBIND_REQUIRED:'+name
    config['E_runtime_files'] = deps['runtime_sources']
    _, config['runner_derivation'] = load('e1_writer_exact_derivation', HERE/'derive.py').derive((ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes())
    assert config['runner_derivation'] == prior_cfg['runner_derivation'], 'E1_EXACT_OLD_D1_ENGINE_PROOF_REQUIRED'
    (HERE/'CONFIG.json').write_text(json.dumps(config, indent=2)+'\n')
    own = {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file()}
    assert not any('__pycache__' in p or p.endswith('.pyc') for p in own)
    allowed = set(imports['files']) | own | {WORKFLOW, NS+'SOURCE.json'}
    changed = set(git('diff', '--name-only', parent).decode().splitlines())
    assert changed <= allowed, 'E1_UNDECLARED_CHILD_PATH'
    paths = set(frozen) | set(imports['files']) | own | {WORKFLOW}
    paths |= {'scripts/cp7_credit_correction_de/'+p for p in deps['unchanged_D1_core_sha256']}
    paths |= set(deps['retained_helper_sha256']) | set(deps['UI_sha256'])
    paths.discard(NS+'SOURCE.json')
    files = {}
    for name in sorted(paths):
        raw = (ROOT/name).read_bytes(); files[name] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    value = dict(contract=config['contract'], status='PREPARED_CLOSED_NOT_ACTUAL_NATIVE_PASS' if config['accepted_D1'] is None else 'PREPARED_EXACT_PARENT_BOUND_NOT_EXECUTED',
        source_base_head=config['source_base_head'], frozen_parent_head=parent, frozen_parent_tree=config['frozen_parent_tree'],
        frozen_D1_source=old, frozen_parent_files=parent_files, allowed_child_paths=sorted(allowed), files=files,
        actual_executions=0, actual_Auth_HTTP=0, actual_browser=0, actual_races=0,
        D_complete=False, E_complete=False, production_go=False, independent_acceptance=False)
    (HERE/'SOURCE.json').write_text(json.dumps(value, indent=2)+'\n')
    return dict(status=value['status'], source_files=len(files), frozen_parent_files=len(parent_files), child_paths=len(allowed), actual_executions=0)


if __name__ == '__main__':
    print(json.dumps(bind()))
