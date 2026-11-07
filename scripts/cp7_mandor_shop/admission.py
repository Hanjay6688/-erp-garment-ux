"""No ERP import or installation is admitted by a storage/model result."""
from hashlib import sha256
import json

PARENT_HEAD='fd797083eab093d9dc97f2d52ca61dc37812b437'
PARENT_TREE='02a8812e9eae2272a976d1dbd1e21aff8c022467'
PARENT_RUN=42258224710
PARENT_JOB=128031001027
PARENT_ROOT_PIN={'bytes': 1981, 'sha256': '18f068fa23983cb64980bcf3882bfbce7f794640e280d03e5c37a90eb04a999d'}
PARENT_ROOT_CONTRACT={'status': 'ROOT_VERIFIED_CURRENT_AFUI_GOOD_NONPAYABLE_FULL15_ALL5', 'actual_Native_cases': 9, 'actual_Auth_HTTP_cases': 2, 'actual_two_session_races': 2, 'actual_browser_cases': 2, 'actual_business_cases': 15, 'complete15_qualified': True, 'prior_runs_aggregated': False}
RUNTIME_ENTRY='scripts/current-mandor-shop-native-qualification/qualification.py'


def accepted_parent(raw):
    if any(value is None for value in(PARENT_HEAD,PARENT_TREE,PARENT_RUN,PARENT_JOB,
            PARENT_ROOT_PIN,PARENT_ROOT_CONTRACT)):
        raise ValueError('CP7_MANDOR_SHOP_ACTUAL_FINAL_ACCEPTED_PARENT_PENDING')
    if {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}!=PARENT_ROOT_PIN:
        raise ValueError('CP7_MANDOR_SHOP_EXACT_ACTUAL_PARENT_BYTES_REQUIRED')
    value=json.loads(raw)
    expected=dict(PARENT_ROOT_CONTRACT,head=PARENT_HEAD,tree=PARENT_TREE,run_id=PARENT_RUN,
        job_id=PARENT_JOB,package_all_five=True,production_go=False,independent_acceptance=False)
    for key,item in expected.items():
        if type(value.get(key))is not type(item)or value[key]!=item:
            raise ValueError('CP7_MANDOR_SHOP_ACTUAL_PARENT_CONTRACT_REQUIRED:'+key)
    return value


def runtime_admission(raw):
    parent=accepted_parent(raw)
    if RUNTIME_ENTRY is None:
        raise ValueError('CP7_MANDOR_SHOP_NATIVE_COMMAND_AND_UI_INTEGRATION_PENDING')
    return parent
