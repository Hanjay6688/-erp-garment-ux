"""Require the canonical accepted FREE3 parent before any ERP import.

These bindings deliberately remain unarmed. A prepared branch, successful
small model, or an earlier partially successful run is not a parent receipt.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import math
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT_HEAD = None
PARENT_TREE = None
PARENT_RUN = None
PARENT_JOB = None
PARENT_RECEIPT = None


def strict(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('NONPAYABLE_DUPLICATE_RECEIPT_KEY')
            value[key] = item
        return value

    def finite(value):
        if type(value) is float and not math.isfinite(value):
            raise ValueError('NONPAYABLE_NONFINITE_RECEIPT')
        if type(value) is dict:
            for item in value.values():
                finite(item)
        elif type(value) is list:
            for item in value:
                finite(item)

    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONPAYABLE_NONFINITE_RECEIPT')))
    finite(value)
    return value


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def require_pin(value):
    if (type(value) is not dict or set(value) != {'bytes', 'sha256'}
        or type(value.get('bytes')) is not int or value['bytes'] <= 0
        or type(value.get('sha256')) is not str
        or re.fullmatch('[0-9a-f]{64}', value['sha256']) is None):
        raise ValueError('NONPAYABLE_EXACT_TYPED_SOURCE_PIN_REQUIRED')
    return value


def parent_receipt():
    if any(value is None for value in (PARENT_HEAD, PARENT_TREE, PARENT_RUN, PARENT_JOB, PARENT_RECEIPT)):
        raise ValueError('NONPAYABLE_ACTUAL_FREE3_ROOT_INTAKE_PENDING')
    if (any(type(value) is not str or re.fullmatch('[0-9a-f]{40}', value) is None
            for value in (PARENT_HEAD, PARENT_TREE))
        or any(type(value) is not int or value <= 0 for value in (PARENT_RUN, PARENT_JOB))):
        raise ValueError('NONPAYABLE_EXACT_ACTUAL_PARENT_IDENTITY_REQUIRED')
    path = HERE / 'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json'
    if path.is_symlink():
        raise ValueError('NONPAYABLE_PARENT_RECEIPT_SYMLINK_REFUSED')
    raw = path.read_bytes()
    if pin(raw) != require_pin(PARENT_RECEIPT):
        raise ValueError('NONPAYABLE_PARENT_RECEIPT_BYTES_CHANGED')
    value = strict(raw)
    expected = dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_ALL5',
        head=PARENT_HEAD, tree=PARENT_TREE, run_id=PARENT_RUN, job_id=PARENT_JOB,
        actual_Native_cases=3, actual_business_cases=3, actual_browser_cases=0,
        actual_Auth_HTTP_cases=0, actual_two_session_races=0, complete3_qualified=True,
        package_all_five=True, prior_runs_aggregated=False, retained_DE30_fresh_case_credit=0,
        GOOD_eligibility_policy_decided=False, Afui_GOOD_nonpayable_path_complete=False,
        D_complete=False, E_complete=False, global_writer_or_permission_or_lock_closure=False,
        production_go=False, independent_acceptance=False)
    if type(value) is not dict:
        raise ValueError('NONPAYABLE_EXACT_CANONICAL_FREE3_PARENT_REQUIRED')
    for key, item in expected.items():
        if type(value.get(key)) is not type(item) or value[key] != item:
            raise ValueError('NONPAYABLE_EXACT_CANONICAL_FREE3_PARENT_REQUIRED:' + key)
    require_pin(value.get('qualified_complete_DE_FREE_date_sources'))
    return value


def qualified_parent_sources(receipt, sources):
    actual = pin(json.dumps(sources, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
    if actual != require_pin(receipt.get('qualified_complete_DE_FREE_date_sources')):
        raise ValueError('NONPAYABLE_ENTIRE_ACCEPTED_FREE3_PARENT_SOURCE_REQUIRED')
    return actual


@contextmanager
def parent_scope():
    parent_receipt()
    path = ROOT / 'scripts/current-de-free-date-preparation/admission.py'
    spec = importlib.util.spec_from_file_location('nonpayable_actual_FREE3_parent_scope', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with module.import_scope():
        yield
