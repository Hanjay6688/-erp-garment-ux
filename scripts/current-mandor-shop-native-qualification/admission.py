"""Closed actual-parent gate; a prepared or modeled report cannot arm it."""
from hashlib import sha256
import json

PARENT_HEAD='fd797083eab093d9dc97f2d52ca61dc37812b437'
PARENT_TREE='02a8812e9eae2272a976d1dbd1e21aff8c022467'
PARENT_RUN=42258224710
PARENT_JOB=128031001027
PARENT_ROOT_PIN={'bytes': 1981, 'sha256': '18f068fa23983cb64980bcf3882bfbce7f794640e280d03e5c37a90eb04a999d'}
RUNTIME_ENTRY='scripts/current-mandor-shop-native-qualification/qualification.py'
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
