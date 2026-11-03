"""Closed actual-parent gate; a prepared or modeled report cannot arm it."""
from hashlib import sha256
import json

PARENT_HEAD='76b3f1e1bcce49cc405e55f92a733dcd0f360cad'
PARENT_TREE='b3182ae21e3981e91d6d3730ec4ffb33dce1afb4'
PARENT_RUN=41596005356
PARENT_JOB=125783405360
PARENT_ROOT_PIN=None
RUNTIME_ENTRY=None
EXPECTED=dict(status='ROOT_VERIFIED_CURRENT_AFUI_GOOD_NONPAYABLE_FULL15_ALL5',
    head=PARENT_HEAD,tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,
    actual_Native_cases=9,actual_Auth_HTTP_cases=2,actual_two_session_races=2,actual_browser_cases=2,
    actual_business_cases=15,complete15_qualified=True,package_all_five=True,
    prior_runs_aggregated=False,production_go=False,independent_acceptance=False)


def parent(raw):
    if PARENT_ROOT_PIN is None or RUNTIME_ENTRY is None:
        raise ValueError('MANDOR_NATIVE_ACTUAL_AFUI15_ROOT_ACCEPTANCE_AND_OWNING_CALLER_PENDING')
    if dict(bytes=len(raw),sha256=sha256(raw).hexdigest())!=PARENT_ROOT_PIN:
        raise ValueError('MANDOR_NATIVE_EXACT_ACTUAL_AFUI15_ROOT_BYTES_REQUIRED')
    value=json.loads(raw)
    for key,expected in EXPECTED.items():
        if type(value.get(key))is not type(expected)or value[key]!=expected:
            raise ValueError('MANDOR_NATIVE_ACTUAL_AFUI15_PARENT_REQUIRED:'+key)
    if value.get('synthetic_receipt_not_an_actual_qualification')is True:
        raise ValueError('MANDOR_NATIVE_SYNTHETIC_PARENT_REFUSED')
    return value
