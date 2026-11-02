"""No ERP import or installation is admitted by a storage/model result."""
from hashlib import sha256
import json

PARENT_HEAD=None
PARENT_TREE=None
PARENT_RUN=None
PARENT_JOB=None
PARENT_ROOT_PIN=None
PARENT_ROOT_CONTRACT=None
RUNTIME_ENTRY=None


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
