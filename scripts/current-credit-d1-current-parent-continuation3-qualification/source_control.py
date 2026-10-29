"""Real complete source/parent intake, with every database connection denied.

Call with the same existing Original/frozen-source environment as admission.
Do not redirect a live log into this sealed source namespace. Evidence output
must be captured outside it, then deliberately added in a later reviewed seal.
"""
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent


def check():
    blocked = []
    def deny(*args, **kwargs):
        blocked.append('psycopg.connect')
        raise AssertionError('D1_CONT_CURRENT_REAL_SOURCE_CONTROL_FORBIDS_DATABASE')
    spec = importlib.util.spec_from_file_location('d1_cont_current_actual_source_control_probe', HERE / 'probe.py')
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    with patch('psycopg.connect', side_effect=deny):
        engine = value.runtime()
        proof = engine.admitted()
        actual = engine.product.sources()
        if proof['current_installation'] != actual:
            raise AssertionError('D1_CONT_CURRENT_ACTUAL_PRODUCT_SOURCE_MISMATCH')
        if proof['retained_Native13']['retained_Native_cases'] != 13:
            raise AssertionError('D1_CONT_CURRENT_EXACT_PARENT_NATIVE13_NOT_ADMITTED')
    return dict(status='PASS_REAL_CURRENT_PRODUCT_AND_COMPLETE_PARENT_ADMISSION_DB_FORBIDDEN',
        engine_admission=proof['status'], source_snapshot_sha256=sha256((HERE / 'SOURCE.json').read_bytes()).hexdigest(),
        source_files=len(proof['qualification']['files']), full175_parent=True,
        current_installation_matches_actual_product_sources=True, actual_runtime_files=actual['files'],
        retained_parent_proof=proof['retained_Native13'],
        historical_D1_diff_endpoint=proof['historical_scope_derivation']['fixed_historical_diff_head'],
        historical_diff_changes=proof['historical_scope_derivation']['counted_changes'],
        current_private_admission=proof['current_parent_private_routing'],
        DB_connections_forbidden=True, blocked_attempts=blocked, actual_SQL_statements=0,
        fresh_Native3_executed=0, actual_Auth=0, actual_browser=0,
        production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit('Current D1 continuation source control accepts no arguments.')
    print(json.dumps(check(), indent=2))
