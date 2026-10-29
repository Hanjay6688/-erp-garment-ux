"""Writer-only explicit source declaration; never auto-bind proof or regenerate in CI."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-credit-d1-owner-followup-qualification/'
CONT = 'scripts/current-credit-d1-continuation-qualification/'
WORKFLOW = '.github/workflows/cp7-credit-d1-continuation-native3.yml'


def load(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def bind():
    if os.environ.get('CI'):
        raise ValueError('D1_CONT_SOURCE_CANNOT_BE_REGENERATED_IN_CI')
    config = json.loads((HERE/'CONFIG.json').read_bytes())
    git = lambda *args:subprocess.check_output(['git','-C',str(ROOT),*args])
    parent = config['frozen_parent_head']
    if git('rev-parse',parent+'^{tree}').decode().strip() != config['frozen_parent_tree']:
        raise ValueError('D1_CONT_EXACT_PUBLIC_PARENT_TREE_REQUIRED')
    path = 'scripts/current-credit-de-native-qualification/SOURCE.json'
    old_raw = git('show',parent+':'+path); old = json.loads(old_raw)
    prior = json.loads(git('show',parent+':scripts/current-credit-de-native-qualification/CONFIG.json'))
    frozen = set(old['files'])|{path}|set(prior['signed_dependencies'])|set(prior['unchanged_parent_files'])|set(prior['cap_fixture_dependencies'])
    frozen |= {'scripts/cp6_bd_probe.py','scripts/cp7_catalog_state.py',
               'scripts/current-vendor-receivable-qualification/native_runner.py'}
    frozen |= set(git('ls-tree','-r','--name-only',parent,'scripts/current-credit-de-native-qualification').decode().splitlines())
    parents = {}
    for name in sorted(frozen):
        raw = git('show',parent+':'+name)
        if (ROOT/name).read_bytes() != raw:
            raise ValueError('D1_CONT_OLD_D1_SOURCE_OR_WORKFLOW_MUST_REMAIN_UNCHANGED:'+name)
        parents[name] = sha256(raw).hexdigest()
    transition = load('continuation_exact_writer_transition',HERE/'transition.py').check()
    continuation = json.loads((ROOT/CONT/'SOURCE.json').read_bytes())
    _,engine = load('continuation_writer_engine_deriver',HERE/'derive.py').derive((ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes())
    if engine != config['runner_derivation']or engine != prior['runner_derivation']:
        raise ValueError('D1_CONT_UNCHANGED_EXACT_CURRENT_D1_ENGINE_PROOF_REQUIRED')
    own = {str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()}
    imports = {CONT+name for name in ('LOCAL_CHECKS.json','README.md','SOURCE.json','cases.py','native_fixture.py','oracle.py','source_guard.py','test_local.py')}
    allowed = own|imports|{WORKFLOW,NS+'SOURCE.json'}
    actual = set(git('diff','--name-only',parent).decode().splitlines())|set(git('ls-files','--others','--exclude-standard').decode().splitlines())
    if not actual <= allowed or any('__pycache__'in path or path.endswith('.pyc')for path in own):
        raise ValueError('D1_CONT_ONLY_NEW_WRAPPER_AND_EIGHT_NEW_CONTINUATION_FILES_ALLOWED')
    paths = set(frozen)|set(continuation['files'])|own|imports|{WORKFLOW,
        'scripts/current-vendor-receivable-qualification/native_runner.py',
        'scripts/ow04-payment-positive-qualification/native26_probe.py'}
    paths.discard(NS+'SOURCE.json')
    source = dict(contract=config['contract'],status='PREPARED_CLOSED_NOT_ACTUAL_NATIVE_PASS',
        frozen_parent_head=parent,frozen_parent_tree=config['frozen_parent_tree'],frozen_D1_source=old,
        frozen_parent_files=parents,allowed_child_paths=sorted(allowed),continuation_source_transition=transition,
        files={name:dict(bytes=len((ROOT/name).read_bytes()),sha256=sha256((ROOT/name).read_bytes()).hexdigest())for name in sorted(paths)},
        actual_executions=0,actual_Auth_HTTP=0,actual_browser=0,actual_races=0,
        D_complete=False,E_complete=False,production_go=False,independent_acceptance=False)
    (HERE/'SOURCE.json').write_text(json.dumps(source,indent=2)+'\n')
    return dict(status=source['status'],files=len(source['files']),frozen_parent_files=len(parents),actual_executions=0)


if __name__ == '__main__':
    print(json.dumps(bind()))
