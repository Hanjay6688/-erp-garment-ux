"""Writer-only explicit source sealing; never chooses backend proof or runs in CI."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'scripts/current-attendance-period-choice-native11-qualification'
WORKFLOW = '.github/workflows/cp7-s03-choice-reader-native14.yml'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def pin(path):
    raw = path.read_bytes(); return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def bind():
    if os.environ.get('CI'):
        raise ValueError('S03_NATIVE14_SOURCE_REGENERATION_IN_CI_FORBIDDEN')
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
    closure = load('s03_native14_writer_closure_helpers', HERE / 'source_check.py')
    prior = closure.historical(ROOT, HERE, origin)
    alias = None if cfg['backend_binding'] is None else closure.binding(ROOT, HERE, cfg, origin)
    producers = set()
    for name in ('GENERATED_RECEIPTS.json', 'LATER_GENERATED_RECEIPTS.json'):
        producers.update(json.loads((HERE / name).read_bytes())['producer_files'])
    own = {str(p.relative_to(ROOT)) for p in HERE.rglob('*')
           if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if any('__pycache__' in p.parts or p.suffix == '.pyc' for p in HERE.rglob('*')):
        raise ValueError('S03_NATIVE14_BYTECODE_IS_NOT_SOURCE')
    self_path = str((HERE / 'SOURCE.json').relative_to(ROOT))
    product_paths = set() if alias is None else set(alias['files'])
    allowed = own | product_paths | {WORKFLOW, self_path}
    paths = (set(prior['files']) | set(origin['unchanged_old_native11_namespace']) |
             producers | allowed) - {self_path}
    files = {name: pin(ROOT / name) for name in sorted(paths)}
    for name, old_pin in prior['files'].items():
        expected = alias['files'][name] if alias is not None and name in alias['files'] else old_pin
        if files[name] != expected:
            raise ValueError('S03_NATIVE14_WRITER_CANNOT_RESEAL_UNDECLARED_OLD251_CHANGE:' + name)
    # Validate any producer-generated untracked paths, rather than ignoring folders.
    git = lambda *args: subprocess.check_output(['git', '-C', str(ROOT), *args], text=True)
    if git('rev-parse', cfg['source_base'] + '^{tree}').strip() != cfg['source_base_tree']:
        raise ValueError('S03_NATIVE14_PUBLIC_BASE_TREE_CHANGED')
    changed = set(git('diff', '--name-only', cfg['source_base']).splitlines())
    if not changed <= allowed:
        raise ValueError('S03_NATIVE14_WRITER_UNALLOCATED_TRACKED_SOURCE:' + repr(sorted(changed - allowed)))
    untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    known = set(files) | {self_path} | set(prior['untracked_historical_proof_inputs']) | set(prior['inherited_untracked_workflow_proof_inputs'])
    p0, _ = load('s03_native14_writer_exact_P0', HERE / 'generated_receipts.py').admit(ROOT, HERE, untracked - known)
    known.update(p0)
    later, _ = load('s03_native14_writer_exact_later', HERE / 'generated_later.py').admit(ROOT, HERE, untracked - known)
    known.update(later)
    if not untracked <= known:
        raise ValueError('S03_NATIVE14_WRITER_UNALLOCATED_UNTRACKED_SOURCE:' + repr(sorted(untracked - known)))
    source = dict(contract='cp7.attendance-choice-reader-native14.v1', status='PREPARED_SOURCE_ONLY_NOT_NATIVE14_PASS',
        files=files, allowed_changes=sorted(allowed), producer_source_paths=sorted(producers),
        untracked_historical_proof_inputs=prior['untracked_historical_proof_inputs'],
        inherited_untracked_workflow_proof_inputs=prior['inherited_untracked_workflow_proof_inputs'],
        source_base=cfg['source_base'], source_base_is_runtime_prerequisite=False,
        historical_source251_sha256='cc2dc65b6f73b288a34fc7dc9ad5e745f18b0f066595b02572e31804956cd438',
        exact_copied_S03_files=80, exact_copied_files_are_history_only=True,
        expected_existing_capture=15, expected_private_clones=2, Native_case_ids=cfg['Native_case_ids'],
        actual_groups=[11, 3], no_combined_strict14_original=True,
        current_backend_bound=alias is not None, Native_executed=False,
        old_cases_and_oracles_modified=False, old_parent_profile_modified=False,
        independent_acceptance=False, production_go=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(source, indent=2) + '\n')
    return dict(status=source['status'], files=len(files), backend_bound=alias is not None,
                Native_executed=False, actual_groups=[11, 3])


if __name__ == '__main__':
    print(json.dumps(bind()))
