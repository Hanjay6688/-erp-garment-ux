"""A new child never rewrites the qualified parent's source or evidence."""
from pathlib import Path
from hashlib import sha256
import ast
import importlib.util
import json
import os
import subprocess
import tempfile


def admitted(repo, here, product, derivation):
    cfg = json.loads((here / 'CONFIG.json').read_bytes())
    source = json.loads((here / 'SOURCE.json').read_bytes())
    assert cfg['contract'] == 'cp7.credit-de-native.v1'
    if cfg.get('qualified_parent') is None:
        raise ValueError('CREDIT_DE_NATIVE_CLOSED_ACTUAL_VENDOR_PARENT_REQUIRED')
    for path, digest in source['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    changed = git('diff', '--name-only', cfg['base_head'], 'HEAD').decode().splitlines()
    assert set(changed) <= set(source['allowed_changes']), 'UNDECLARED_CREDIT_DE_NATIVE_SUCCESSOR_CHANGE'
    assert not git('status', '--porcelain', '--untracked-files=no').strip()
    for path in cfg['unchanged_parent_files']:
        assert (repo / path).read_bytes() == git('show', cfg['base_head'] + ':' + path), path
    for path, digest in cfg['signed_dependencies'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    cap = cfg['cap_successor_transition']
    raw_cap = (repo / cap['path']).read_bytes()
    assert sha256(raw_cap).hexdigest() == cap['sha256'], 'D1_CAP_REVIEWED_TRANSITION_CHANGED'
    reviewed_cap = json.loads(raw_cap)
    assert reviewed_cap['base_head'] == cap['base_head'] and cap['base_is_failed_not_prerequisite'] is True
    assert reviewed_cap['base_actual_result'] == dict(PASS=5, INCOMPLETE=8, usable_prerequisite=False)
    assert reviewed_cap['changed_runtime_leaves'] == ['owning.sql']
    assert reviewed_cap['changed_SQL_functions'] == ['cp7_credit_correction_de.quote_v1']
    for path, digest in cfg['cap_fixture_dependencies'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    assert derivation == cfg['runner_derivation']
    tree = ast.parse((repo / 'scripts/cp7_credit_correction_de/cases.py').read_text())
    declarations = [ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in node.targets)]
    assert len(declarations) == 1 and list(declarations[0]) == cfg['native_case_ids']
    assert len(set(cfg['native_case_ids'])) == len(cfg['native_case_ids']) > 0
    parent = product.predecessor.sources()
    parent_digest = sha256(json.dumps(parent['predecessor'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    assert parent_digest == cfg['parent_backend_sha256']
    verifier = cfg['frozen_parent_verifier']
    verifier_raw = git('show', verifier['head'] + ':' + verifier['path'])
    assert sha256(verifier_raw).hexdigest() == verifier['sha256']
    pin = cfg['qualified_parent']
    originals = Path(os.environ['CP7_VENDOR_BACKEND11_ORIGINALS'])
    with tempfile.TemporaryDirectory(prefix='credit-de-parent-admission-') as directory:
        path = Path(directory) / 'check.py'
        path.write_bytes(verifier_raw)
        spec = importlib.util.spec_from_file_location('credit_de_frozen_parent_intake', path)
        verifier_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier_module)
        proof = verifier_module.admit(pin, (originals / pin['original']['name']).read_bytes(),
                                      (originals / pin['package']['name']).read_bytes(),
                                      parent['files'], parent_digest)
    current = product.sources()
    assert current['predecessor'] == parent
    assert current['files'] == cfg['runtime_files']
    return dict(status='EXACT_VENDOR_PARENT_AND_DECLARED_D1_CHILD_ADMITTED',
                qualification=source, current_installation=current,
                qualified_parent=proof, parent_backend_sha256=parent_digest,
                runner_derivation=derivation, actual_Native_case_ids=cfg['native_case_ids'],
                current_installation_entrypoint=dict(module='cp7_credit_correction_de.composition',
                    path='scripts/cp7_credit_correction_de/composition.py', install='install', verify='verify', rollback_preuse='rollback_preuse'),
                retained_vendor11_reexecuted=False, retained_money_browser_reexecuted=False,
                B_browser_reexecuted=False, production_go=False, independent_acceptance=False)
