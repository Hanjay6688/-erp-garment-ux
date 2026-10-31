"""No actual permanent-parent intake yet: no ERP/runtime/DB admission."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
PARENT_HEAD=None
PARENT_RECEIPT=None


def parent_receipt():
    if PARENT_HEAD is None or PARENT_RECEIPT is None:
        raise ValueError('COMPLETE_DE_ACTUAL_PERMANENT_PARENT_INTAKE_PENDING')
    raw=(HERE/'PERMANENT_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes()
    if len(raw)!=PARENT_RECEIPT['bytes']or sha256(raw).hexdigest()!=PARENT_RECEIPT['sha256']:
        raise ValueError('COMPLETE_DE_EXACT_PERMANENT_PARENT_INTAKE_CHANGED')
    value=json.loads(raw)
    required=dict(status='ROOT_VERIFIED_PERMANENT_S05_NATIVE4_BROWSER2_ALL5',head=PARENT_HEAD,
        complete6_qualified=True,actual_Native_cases=4,actual_browser_cases=2,
        retained_join37_fresh_case_credit=0,package_all_five=True,prior_runs_aggregated=False,
        production_go=False,independent_acceptance=False)
    for key,expected in required.items():
        if type(value.get(key))is not type(expected)or value[key]!=expected:
            raise ValueError('COMPLETE_DE_ACTUAL_QUALIFIED_PERMANENT_PARENT_REQUIRED:'+key)
    return value
