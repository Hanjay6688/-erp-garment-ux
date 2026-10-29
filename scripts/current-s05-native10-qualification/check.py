"""Default is offline. --runtime imports exact source only; no DB or remote."""
from pathlib import Path
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def run(runtime=False):
    source = load('s05_cli_source_admission', HERE/'admission.py').offline()
    workflow = load('s05_cli_workflow_source', HERE/'workflow_source.py').checked((ROOT/'.github/workflows/cp7-current-s05-native10.yml').read_text())
    if runtime:
        actual = load('s05_cli_runtime_admission', HERE/'probe.py').check()
        if actual['prerequisite']['fresh_S05_runtime_credit'] != 0:
            raise ValueError('S05_SOURCE_CHECK_CANNOT_GRANT_RUNTIME_CREDIT')
    return dict(status='PASS_SOURCE_ONLY', files=source['source_files'], frozen_component_files=source['frozen_component_and_fixture_files'],
                Native_cases_prepared=len(source['Native_case_ids']), prerequisite=source['prerequisite'],
                workflow_derivation=workflow, runtime_import_source_check=runtime, Native_executions=0, database_calls=0,
                production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--runtime']):
        raise SystemExit('Use no arguments for offline checks or --runtime for source admission with inherited prerequisite directories.')
    print(json.dumps(run(sys.argv[1:] == ['--runtime']), indent=2))
