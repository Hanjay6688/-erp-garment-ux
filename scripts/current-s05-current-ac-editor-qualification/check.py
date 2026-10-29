"""Source/import-only admission; the runner alone may execute Native cases."""
from pathlib import Path
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def run(runtime=False):
    proof = load('s05_current_AC_cli_admission', HERE/'admission.py').offline()
    if runtime:
        imported = load('s05_current_AC_cli_imports', HERE/'probe.py').check()
        if imported['fresh_runtime_credit_from_admission'] != 0:
            raise ValueError('S05_CURRENT_AC_SOURCE_IMPORT_IS_NOT_NATIVE_PASS')
    return dict(status='PASS_SOURCE_ONLY', source_files=proof['source_files'],
        Native_case_ids=proof['Native_case_ids'], current_AC_premise=proof['current_AC_premise'],
        retained_cdbdea_failure=proof['retained_cdbdea_failure'], runtime_source_imports_checked=runtime,
        Native_executions=0, database_calls=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--runtime']):
        raise SystemExit('Only --runtime import check or no arguments are supported.')
    print(json.dumps(run(sys.argv[1:] == ['--runtime']), indent=2))
