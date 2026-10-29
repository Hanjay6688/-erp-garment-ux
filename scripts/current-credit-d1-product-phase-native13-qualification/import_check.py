"""Real complete engine/Native adapter import with every DB connection denied."""
from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def main():
    if sys.argv[1:]:
        raise SystemExit('D1 combined import control accepts no arguments')
    spec = importlib.util.spec_from_file_location('d1_bound_real_complete_runtime_import', HERE / 'probe.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    caller, contents = sys.argv, sys.argv[:]
    try:
        sys.argv = [contents[0], '--runtime']
        saved = sys.argv
        with patch('psycopg.connect', side_effect=AssertionError('D1_COMBINED_SOURCE_CONTROL_FORBIDS_DATABASE')):
            engine = probe.runtime()
        assert sys.argv is saved and sys.argv == [contents[0], '--runtime']
        assert engine.runner.CASE == 'CREDIT_DE_NATIVE13_AND_USED_INVERSE'
        assert engine.LABEL == 'CP7_CREDIT_DE_NATIVE13'
    finally:
        caller[:] = contents
        sys.argv = caller
    print(json.dumps(dict(status='PASS_REAL_COMPLETE_RUNTIME_IMPORT_DB_FORBIDDEN',
        engine_module=engine.__name__, runner_case=engine.runner.CASE, label=engine.LABEL,
        caller_argv_object_and_contents_restored=True, new_Native_cases=0,
        actual_SQL_statements=0, production_go=False, independent_acceptance=False)))


if __name__ == '__main__':
    main()
