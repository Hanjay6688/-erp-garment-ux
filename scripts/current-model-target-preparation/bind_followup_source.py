"""Bind a prepared followup to actual Originals; never run or publish a job.

Run from the frozen writer cwd. The input manifest names a clean worktree, kind,
existing environment JSON and each {proof_path, report_path}. The native20
Original is mandatory. Commit the new SOURCE, then run the selected probe's
full admitted() gate before publishing its dedicated branch.
"""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import json
import os
import subprocess
import sys

NATIVE = 'CURRENT_MODEL_TARGET_ORIGINAL_REPORT'
COMMON = {NATIVE}
KINDS = {
    'browser': ('current-model-target-browser-qualification', 'cp7-current-model-target-browser.yml',
                COMMON | {'MODEL_POLICY_BROWSER_ORIGINAL_REPORT', 'MODEL_V2_BROWSER_ORIGINAL_REPORT', 'MODEL_TARGET_BROWSER_ORIGINAL_REPORT'}),
    'restore': ('current-model-target-used-restore-qualification', 'cp7-current-model-target-restore.yml',
                COMMON | {'CURRENT_FINANCE_MODEL_RESTORE_ORIGINAL_REPORT'}),
    'transport': ('current-model-target-transport-qualification', 'cp7-current-model-target-transport.yml',
                  COMMON | {'MODEL_POLICY_TRANSPORT_ORIGINAL_REPORT', 'MODEL_V2_TRANSPORT_ORIGINAL_REPORT'}),
    'finance': ('current-model-target-finance-qualification', 'cp7-current-model-target-finance.yml',
                COMMON | {'CURRENT_FINANCE_UTC_ORIGINAL_REPORT', 'FIRST_FINANCE_TRANSPORT_ORIGINAL_REPORT'}),
    'cron': ('current-model-target-cron-qualification', 'cp7-current-model-target-cron.yml',
             COMMON | {'CURRENT_FINANCE_MODEL_CRON_ORIGINAL_REPORT'}),
    'factory': ('current-factory-finance-qualification', 'cp7-current-factory-finance.yml',
                COMMON | {'CURRENT_MODEL_TARGET_CRON_ORIGINAL_REPORT'}),
}
TARGET_FULL = {'MODEL_TARGET_TRANSPORT_ORIGINAL_REPORT'}
TARGET_PARTS = {'MODEL_TARGET_TRANSPORT_PART_A_ORIGINAL_REPORT', 'MODEL_TARGET_TRANSPORT_PART_B_ORIGINAL_REPORT'}


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def bind(manifest):
    repo = Path(manifest['repo']).resolve()
    kind = manifest['kind']
    folder, workflow, required = KINDS[kind]
    here = repo / 'scripts' / folder
    source_path = here / 'SOURCE.json'
    env_output = Path(manifest['env_output']).resolve()
    assert not source_path.exists() and not env_output.exists(), 'BINDING_OUTPUT_ALREADY_EXISTS'
    assert not env_output.is_relative_to(repo), 'ENV_OUTPUT_MUST_BE_OUTSIDE_REPOSITORY'
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True).strip()
    originals = manifest['originals']
    if kind == 'transport':
        target = set(originals) - required
        assert target in (TARGET_FULL, TARGET_PARTS), 'FULL_TARGET_OR_BOTH_PARTS_REQUIRED'
        required = required | target
    assert set(originals) == required, 'FOLLOWUP_ORIGINAL_SET_CHANGED'
    env = read(manifest['env_input'])
    os.environ.update(env)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo / 'scripts'))
    import cp7_current_model_target_installation as product
    native_path = repo / 'scripts/current-model-target-native-qualification/SOURCE.json'
    native_pins = read(native_path)
    proofs, reports = {}, {}
    for variable, locations in originals.items():
        proof = read(locations['proof_path'])
        report_path = Path(locations['report_path']).resolve()
        raw = report_path.read_bytes()
        assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256'], variable
        actual = json.loads(raw)
        expected = 'INCOMPLETE' if variable == 'FIRST_FINANCE_TRANSPORT_ORIGINAL_REPORT' else 'PASS'
        assert actual['status'] == proof['status'] == expected, variable
        assert actual['cp6_restored'] and actual['advisor_gate'], variable
        gate = read(report_path.parent / 'T3_PACKAGE_INSTALL.json')['gate']
        assert gate == dict(installed=True, primary_unchanged=True, backup_restore_drill=True,
                            security_advisors=True, writer_runtime=expected == 'PASS'), variable
        proofs[variable], reports[variable] = proof, actual
        env[variable] = str(report_path)
    actual = reports[NATIVE]
    assert actual['native']['counts'] == {'PASS': 20} and actual['observed_case_count'] == 20
    assert actual['required_case_ids_pass'] and actual['required_case_ids'] == native_pins['case_ids']
    assert actual['baseline_full22_all_rows_all_sequences_equal'] and actual['baseline_advisors_equal']
    assert actual['complete_preuse_removal']
    assert actual['source_declaration']['current_installation'] == product.sources()
    assert actual['source_declaration']['qualification'] == native_pins
    for variable, proof in native_pins['actual_qualification_originals'].items():
        # The selected followup must retain the full parent admission environment,
        # including all preserved first failures with collision-free input paths.
        raw = Path(env[variable]).read_bytes()
        assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256'], variable
    files = dict(native_pins['files'])
    for path, expected in files.items():
        assert digest(repo / path) == expected, ('CURRENT_NATIVE20_SOURCE_CHANGED', path)
    paths = subprocess.check_output(['git', '-C', str(repo), 'ls-files', 'scripts', 'src'], text=True).splitlines()
    paths += [str(native_path.relative_to(repo)), '.github/workflows/' + workflow]
    for path in paths:
        if (repo / path).is_file():
            files[path] = digest(repo / path)
    os.environ.update(env)
    probe = module('current_followup_source_binding', here / 'probe.py')
    assert getattr(probe, 'product', getattr(probe, 'composed', None)) is product
    pins = dict(contract='cp7.current-model-target-' + kind + '-qualification.v1',
                files=dict(sorted(files.items())), actual_qualification_originals=proofs,
                production_go=False, independent_acceptance=False)
    if kind == 'restore':
        pins['required_steps'] = list(probe.STEPS)
        assert len(probe.STEPS) == 8
    else:
        pins['case_ids'] = list(probe.IDS)
        assert len(probe.IDS) == len(set(probe.IDS)) == dict(browser=6, transport=28, finance=10, cron=1, factory=1)[kind]
        if hasattr(probe, 'GROUPS'):
            pins['groups'] = probe.GROUPS
    if kind == 'transport':
        admission = module('current_transport_prerequisite_binding', here / 'admission.py')
        admission.target_prerequisites(proofs, probe.transport, product)
    # No SOURCE or output is written until all parent data and source checks pass.
    source_path.write_text(json.dumps(pins, indent=2) + '\n')
    env_output.write_text(json.dumps(env, indent=2) + '\n')
    return dict(status='BOUND_PENDING_COMMIT_AND_FULL_ADMISSION_NOT_RUNTIME', kind=kind,
                source_pins=len(files), actual_originals=len(proofs), production_go=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    arguments = parser.parse_args()
    print(json.dumps(bind(read(arguments.manifest))))
