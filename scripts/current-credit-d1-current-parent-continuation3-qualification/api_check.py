"""Actual retained interfaces and private source routing; DB connections forbidden."""
from pathlib import Path
from unittest.mock import patch
from hashlib import sha256
import importlib.util
import inspect
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def check():
    scope = load('d1_cont_current_no_argument_import_scope', HERE / 'argv_scope.py')
    with scope.inherited_arguments(), patch('psycopg.connect', side_effect=AssertionError('D1_CONT_CURRENT_SOURCE_CONTROL_FORBIDS_DATABASE')):
        business = load('d1_cont_current_actual_retained_business_API', HERE / 'business.py').load_business()
        guard = business.guard.admitted()
        n = business.n
        from cp7_credit_correction_de import native_fixture as actual_owned
        assert n.fixture is actual_owned and n.fixture.prepare is actual_owned.prepare
        assert n.target_document_ar is actual_owned.retained._document_ar
        inventory = actual_owned.inventory()
        assert inventory['substitutions'] == 10 and len(inventory['functions']) == 5
        bindings = ((n.d1.post, (None, None, '275.00', 'first-return'), {}),
            (n.d1.profile, (None, None, '250.00', '30.00'), {}),
            (n.basic.apply, (None, None, '220.00'), {}), (n.refunds.refund, (None, None, '230.00'), {}),
            (n.basic.payload, (None, 'UNDO'), dict(original='named-event')),
            (n.basic.review, (None, None), {}), (n.basic.command, (None, None, None), {}),
            (n.correction.correct, (None, None, None, None), {}),
            (n.target_document_ar, (None, 'target-sale', 'customer', 'AR-account'), {}))
        for operation, args, kwargs in bindings:
            inspect.signature(operation).bind(*args, **kwargs)
        assert list(business.IDS) == guard['case_ids'] and len(business.IDS) == 3
        assert sha256((ROOT / 'scripts/cp7_credit_correction_de/native_fixture.py').read_bytes()).hexdigest() == '4fbe56583ffc63473c12195ddaae6ff3e0cd0ad46b358bf7eef7b5175c67e829'
    return dict(status='PASS_ACTUAL_RETAINED_API_IMPORT_AND_CURRENT_SOURCE_GUARD_DB_FORBIDDEN',
        Native_callbacks=3, actual_binding_signatures=len(bindings), fixture_substitutions=10,
        fixture_functions=5, actual_SQL_statements=0, actual_Native_cases=0,
        actual_Auth_HTTP=0, independent_acceptance=False, production_go=False)


if __name__ == '__main__':
    print(json.dumps(check()))
