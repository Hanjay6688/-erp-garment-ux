"""Source gate before ERP imports, DB startup or historical materialization."""
from pathlib import Path
from hashlib import sha256
import ast
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def check(root=ROOT, here=HERE):
    cfg = json.loads((here / 'CONFIG.json').read_bytes())
    source = json.loads((here / 'SOURCE.json').read_bytes())
    if (cfg['contract'] != 'cp7.attendance-period-choice-native11.v1'
            or cfg['production_go'] is not False or cfg['independent_acceptance'] is not False
            or source['Native_executed'] is not False):
        raise ValueError('S03_NATIVE11_PREPARED_SOURCE_CONTRACT_REQUIRED')
    for name, pin in source['files'].items():
        raw = (root / name).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('S03_NATIVE11_SOURCE_CHANGED:' + name)
    origin = json.loads((here / 'ORIGIN.json').read_bytes())
    for name, pin in origin['copied_S03_files'].items():
        raw = (root / name).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('S03_NATIVE11_FROZEN_COMPONENT_CHANGED:' + name)
    if len(origin['copied_S03_files']) != 80:
        raise ValueError('S03_NATIVE11_EXACT80_COMPONENT_FILES_REQUIRED')
    git = lambda *args: subprocess.check_output(['git', '-C', str(root), *args], text=True)
    if git('rev-parse', cfg['source_base'] + '^{tree}').strip() != cfg['source_base_tree']:
        raise ValueError('S03_NATIVE11_PUBLIC_SOURCE_BASE_CHANGED')
    changed = git('diff', '--name-only', cfg['source_base'], 'HEAD').splitlines()
    if not set(changed) <= set(source['allowed_changes']):
        raise ValueError('S03_NATIVE11_UNDECLARED_SOURCE_SUCCESSOR_CHANGE')
    if git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('S03_NATIVE11_TRACKED_WORKTREE_CHANGED')
    allowed_untracked = set(source['files']) | {str((here / 'SOURCE.json').relative_to(root))}
    allowed_untracked.update(source['untracked_historical_proof_inputs'])
    allowed_untracked.update(source['inherited_untracked_workflow_proof_inputs'])
    for name, pin in source['inherited_untracked_workflow_proof_inputs'].items():
        target = root / name
        if target.exists():
            raw = target.read_bytes()
            if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
                raise ValueError('S03_NATIVE11_INHERITED_WORKFLOW_PROOF_CHANGED:' + name)
    if not set(git('ls-files', '--others', '--exclude-standard').splitlines()) <= allowed_untracked:
        raise ValueError('S03_NATIVE11_UNDECLARED_UNTRACKED_SOURCE')
    proof = load('s03_native11_offline_proof_inputs', here / 'proof_inputs.py')
    docs = proof.documents(here)
    for name, value in docs.items():
        target = root / proof.HISTORICAL / (name + '.gz')
        if target.exists() and target.read_bytes() != value['compressed']:
            raise ValueError('S03_NATIVE11_MATERIALIZED_PROOF_CHANGED:' + name)
    declaration = ast.parse((root / cfg['case_path']).read_text())
    ids = [ast.literal_eval(n.value) for n in declaration.body if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets)]
    if len(ids) != 1 or list(ids[0]) != cfg['Native_case_ids'] or len(set(ids[0])) != 11:
        raise ValueError('S03_NATIVE11_EXACT_IDS_REQUIRED')
    stage = load('s03_native11_offline_counted_hooks', root / 'scripts/cp7_attendance_period_choice/native_delta.py')
    if len(stage.NATIVE_SIGNATURES) != 12 or len(stage.SIGNATURES) != 13 or len(stage.CLONES) != 2:
        raise ValueError('S03_NATIVE11_EXACT_CAPTURE13_CLONES2_REQUIRED')
    derive = load('s03_native11_offline_engine_derivation', here / 'derive.py')
    raw = (root / cfg['vendor_probe_path']).read_bytes()
    derived, observed = derive.derive(raw)
    if observed != cfg['runner_derivation']:
        raise ValueError('S03_NATIVE11_ENGINE_DERIVATION_CHANGED')
    # Every substitution is one-to-one and the whole original reconstructs.
    for before, after in reversed(derive.REPLACEMENTS):
        if derived.count(after) != 1:
            raise ValueError('S03_NATIVE11_NONREVERSIBLE_ENGINE')
        derived = derived.replace(after, before, 1)
    if derived.encode() != raw:
        raise ValueError('S03_NATIVE11_ORIGINAL_ENGINE_NOT_EXACT')
    prepared = json.loads((root / 'scripts/current-attendance-period-choice-qualification/SOURCE.json').read_bytes())
    if (prepared['accepted_current_S03_Native_original'] is not None
            or any(prepared['counts'][key] != 0 for key in
                   ('actual_s03_native', 'actual_s03_real_Auth', 'actual_s03_browser'))):
        raise ValueError('S03_NATIVE11_UNEXECUTED_PREPARATION_RELABELLED')
    return dict(status='EXACT_PREPARED_S03_NATIVE11_SOURCE', files=len(source['files']),
        source_base=cfg['source_base'], source_base_is_runtime_prerequisite=False,
        frozen_S03_files=80, existing_captures=13, private_clones=2,
        Native_case_ids=cfg['Native_case_ids'], engine_substitutions=6,
        source_derived_local_ABI_is_installed_proof=False, Native_executed=False,
        inherited_archived_workflow_inputs=24, restored_Git_workflow_triggers=0,
        production_go=False, independent_acceptance=False)
