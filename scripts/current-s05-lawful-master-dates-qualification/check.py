"""Source-only: retain all authoritative Original readers; no runtime credit."""
from pathlib import Path
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def run(runtime=False):
    proof = load('s05_lawful_cli_offline', HERE/'admission.py').offline()
    if runtime:
        actual = load('s05_lawful_cli_actual_source_import', HERE/'probe.py').check()
        if actual['fresh_runtime_credit_from_admission'] != 0:
            raise ValueError('S05_SOURCE_IMPORT_IS_NOT_ACTUAL_NATIVE')
    return dict(status='PASS_SOURCE_ONLY', source_files=proof['source_files'],
                Native_case_ids=proof['Native_case_ids'], original_vendor_prerequisite=proof['inherited']['prerequisite'],
                exact_911_first_failure=proof['first_failure'], runtime_source_imports_checked=runtime,
                Native_executions=0, database_calls=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--runtime']):
        raise SystemExit('Use no arguments or --runtime for source-only admission.')
    print(json.dumps(run(sys.argv[1:] == ['--runtime']), indent=2))
