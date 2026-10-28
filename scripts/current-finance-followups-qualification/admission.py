"""Admit exact qualified sources and immutable evidence before any connection."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_gate(config):
    if not config['allow_database_execution'] or config['parent']['status'] != 'PASS':
        raise ValueError('FOLLOWUP_PARENT_NOT_ACCEPTED_DATABASE_GATE_CLOSED')


def admitted(repo, here, ids, product, native):
    config = json.loads((here / 'CONFIG.json').read_bytes())
    check_gate(config)
    source = json.loads((here / 'SOURCE.json').read_bytes())
    assert source['case_ids'] == list(ids)
    assert source['production_go'] is source['independent_acceptance'] is False
    for path, digest in source['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    parent_file = repo / 'scripts/current-finance-readonly-integration-qualification/SOURCE.json'
    assert sha256(parent_file.read_bytes()).hexdigest() == source['parent_source_sha256']
    parent_source = json.loads(parent_file.read_bytes())
    for path, digest in parent_source['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    proof = config['parent']
    directory = Path(os.environ[config['original_directory_variable']])
    current = product.sources()
    evidence = load('followup_accepted_evidence', here / 'evidence.py').accepted(
        proof, (directory / proof['name']).read_bytes(),
        (directory / proof['package_name']).read_bytes(), parent_source, current)
    guard = load('followup_probe_derivation_guard', here / 'source_guard.py').check(repo, here)
    return dict(qualification=source, current_installation=current,
                accepted_readonly_native13_cron1=evidence, source_guard=guard,
                production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    probe = load('followup_probe_admission', here / 'probe.py')
    result = probe.admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED', pins=len(result['qualification']['files']),
                          prepared_diagnostics=2, actual_cases_executed=False)))
