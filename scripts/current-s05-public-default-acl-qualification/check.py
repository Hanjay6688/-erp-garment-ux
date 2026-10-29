"""Offline by default; --runtime checks exact real source imports, with DB forbidden."""
from pathlib import Path
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def run(runtime=False):
    source = load('s05_acl_cli_source_admission', HERE/'admission.py').offline()
    if runtime:
        actual = load('s05_acl_cli_runtime_admission', HERE/'probe.py').check()
        if actual['fresh_runtime_credit_from_admission'] != 0 or actual['prerequisite']['fresh_S05_runtime_credit'] != 0:
            raise ValueError('S05_ACL_SOURCE_IMPORT_CANNOT_GRANT_RUNTIME_CREDIT')
    return dict(status='PASS_SOURCE_ONLY', source_files=source['source_files'],
        Native_cases_prepared=len(source['Native_case_ids']), prerequisite=source['prerequisite'],
        bounded_product_transition=source['bounded_product_transition'], retained_b0_failure=source['retained_b0_failure'],
        workflow_derivation=source['workflow_derivation'], runtime_import_source_check=runtime,
        Native_executions=0, database_calls=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--runtime']):
        raise SystemExit('Use no arguments for offline checks or --runtime for exact source-only import admission.')
    print(json.dumps(run(sys.argv[1:] == ['--runtime']), indent=2))
