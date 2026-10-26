"""Actual Native6 prerequisite, exact sources and a six-case-only transport delta."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admitted(repo, here, ids, product, native, groups):
    cfg = json.loads((here / 'CONFIG.json').read_bytes())
    assert cfg['choice_head'] is not None, 'ACTUAL_NATIVE6_PASS_REQUIRED_BEFORE_BINDING'
    assert groups == cfg['groups'] and list(ids) == cfg['case_ids']
    assert len(ids) == len(set(ids)) == cfg['count'] == 6
    assert {key: len(value) for key, value in groups.items()} == dict(choice_http=3, choice_races=3)
    pins = json.loads((here / 'SOURCE.json').read_bytes())
    assert pins['contract'] == cfg['contract'] and pins['case_ids'] == list(ids)
    assert pins['production_go'] is pins['independent_acceptance'] is False
    for path, digest in pins['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    changed = subprocess.check_output(['git', '-C', str(repo), 'diff', '--name-only', cfg['choice_head'], 'HEAD'], text=True).splitlines()
    for path in changed:
        assert path.startswith('scripts/current-choice-preparation-transport-qualification/') or path == '.github/workflows/cp7-d17-18-choice-preparation-transport.yml', path
    parent = native.admitted()
    proof = pins['actual_predecessor']
    raw = Path(os.environ[cfg['choice_variable']]).read_bytes()
    checked = load('choice_transport_actual_evidence', here / 'evidence.py').validate(repo, here, proof, raw, product, parent)
    return dict(qualified_public_parent=parent, current_installation=product.sources(),
        qualification=pins, actual_parent_verified=checked, focused_groups=groups,
        actual_cron_claim=False, real_browser_claim=False, factory3600_claim=False,
        default_adopted=False, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    probe = load('choice_transport_admission_probe', here / 'probe.py')
    result = probe.admitted()
    print(json.dumps(dict(status='ADMITTED_FOCUSED_AUTH3_RACE3',
        source_pins=len(result['qualification']['files']), production_go=False)))
