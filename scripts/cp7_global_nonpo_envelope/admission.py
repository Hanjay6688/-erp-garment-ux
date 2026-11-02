"""Closed actual-parent/input boundary; model results never open admission."""
from hashlib import sha256
import json

PARENT_HEAD=None
PARENT_TREE=None
PARENT_ROOT_RECEIPT=None
PARENT_RUN=None
PARENT_JOB=None
PARENT_ROOT_CONTRACT=None
INPUT_PROFILE_PIN=None
RUNTIME_ENTRY=None


def parent():
    raise ValueError('CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING')


def runtime_admission(parent_raw,input_raw):
    if any(value is None for value in(PARENT_HEAD,PARENT_TREE,PARENT_ROOT_RECEIPT,
        PARENT_RUN,PARENT_JOB,PARENT_ROOT_CONTRACT,INPUT_PROFILE_PIN,RUNTIME_ENTRY)):
        parent()
    def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    if pin(parent_raw)!=PARENT_ROOT_RECEIPT or pin(input_raw)!=INPUT_PROFILE_PIN:
        raise ValueError('CP7_GLOBAL_EXACT_REVIEWED_PARENT_AND_INPUT_PROFILE_BYTES_REQUIRED')
    accepted=json.loads(parent_raw);profile=json.loads(input_raw)
    expected=dict(PARENT_ROOT_CONTRACT,head=PARENT_HEAD,tree=PARENT_TREE,run_id=PARENT_RUN,
        job_id=PARENT_JOB,package_all_five=True,production_go=False,independent_acceptance=False)
    for key,value in expected.items():
        if type(accepted.get(key))is not type(value)or accepted[key]!=value:
            raise ValueError('CP7_GLOBAL_ACTUAL_PARENT_CONTRACT_REQUIRED:'+key)
    if(profile.get('contract')!='cp7.global-reviewed-input-profile.v1'
      or profile.get('parent')!={'head':PARENT_HEAD,'tree':PARENT_TREE}
      or profile.get('complete_input_review')is not True):
        raise ValueError('CP7_GLOBAL_COMPLETE_REVIEWED_INPUT_PROFILE_REQUIRED')
    return dict(head=PARENT_HEAD,tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,
        root_receipt_pin=pin(parent_raw)),profile
