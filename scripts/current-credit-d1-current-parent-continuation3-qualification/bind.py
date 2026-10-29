"""Writer-only explicit declaration; no CI regeneration and no automatic proof selection."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CURRENT = ROOT / 'scripts/current-credit-d1-product-phase-native13-qualification'
WORKFLOW = '.github/workflows/cp7-credit-d1-current-parent-continuation3.yml'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def bind():
    if os.environ.get('CI'):
        raise ValueError('D1_CONT_CURRENT_SOURCE_CANNOT_BE_REGENERATED_IN_CI')
    config = json.loads((HERE / 'CONFIG.json').read_bytes())
    origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
    parent = config['frozen_parent_head']
    git = lambda *args: subprocess.check_output(['git', '-C', str(ROOT), *args])
    if parent != '17ac1eeb5833cbf2a786194fe3bfbba6628a1ff8' or git('rev-parse', parent + '^{tree}').decode().strip() != origin['public_parent_tree']:
        raise ValueError('D1_CONT_CURRENT_EXACT_PUBLIC17AC_REQUIRED')
    current_raw = (CURRENT / 'SOURCE.json').read_bytes()
    if sha256(current_raw).hexdigest() != config['current_D1_source_sha256']:
        raise ValueError('D1_CONT_CURRENT_REVIEWED_SOURCE174_REQUIRED')
    current = json.loads(current_raw)
    parents = set(current['files']) | {str((CURRENT / 'SOURCE.json').relative_to(ROOT))}
    if len(parents) != 175:
        raise ValueError('D1_CONT_CURRENT_ALL175_PARENT_FILES_REQUIRED')
    parent_pins = {}
    for path in sorted(parents):
        raw = (ROOT / path).read_bytes()
        if raw != git('show', parent + ':' + path):
            raise ValueError('D1_CONT_CURRENT_PARENT_FILE_MODIFIED:' + path)
        parent_pins[path] = sha256(raw).hexdigest()
    for path, pin in origin['imported_paths'].items():
        raw = (ROOT / path).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('D1_CONT_CURRENT_OLD_IMPORTED_BYTES_CHANGED:' + path)
    transition = load('d1_cont_current_explicit_source_transition', HERE / 'transition.py').check()
    _, engine = load('d1_cont_current_exact_engine_writer', HERE / 'derive.py').derive((ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes())
    if engine != config['runner_derivation']:
        raise ValueError('D1_CONT_CURRENT_SIX_CHANGE_ENGINE_CHANGED')
    own = {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if any('__pycache__' in p.parts or p.suffix == '.pyc' for p in HERE.rglob('*')):
        raise ValueError('D1_CONT_CURRENT_NO_GENERATED_BYTECODE_IN_SOURCE')
    self_path = str((HERE / 'SOURCE.json').relative_to(ROOT))
    allowed = own | set(origin['imported_paths']) | {WORKFLOW, self_path}
    actual = set(git('diff', '--name-only', parent).decode().splitlines()) | set(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
    if not actual <= allowed:
        raise ValueError('D1_CONT_CURRENT_UNALLOCATED_SOURCE_PATH:' + repr(sorted(actual - allowed)))
    paths = (parents | allowed) - {self_path}
    source = dict(contract=config['contract'], status='PREPARED_CURRENT_PARENT_SOURCE_ONLY_NOT_NATIVE3_PASS',
        frozen_parent_head=parent, frozen_parent_tree=config['frozen_parent_tree'], frozen_D1_source=current,
        frozen_parent_files=parent_pins, allowed_child_paths=sorted(allowed), continuation_source_transition=transition,
        files={path: dict(bytes=len((ROOT / path).read_bytes()), sha256=sha256((ROOT / path).read_bytes()).hexdigest()) for path in sorted(paths)},
        actual_executions=0, actual_Auth_HTTP=0, actual_browser=0, actual_races=0,
        D_complete=False, E_complete=False, production_go=False, independent_acceptance=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(source, indent=2) + '\n')
    return dict(status=source['status'], files=len(paths), frozen_parent_files=len(parents),
                accepted_parent_bound=config['accepted_native13'] is not None, actual_executions=0)


if __name__ == '__main__':
    print(json.dumps(bind()))
