"""Actual current Mandor17 and standalone money19 are required, never modeled."""
from hashlib import sha256
import json

PARENT_HEAD=None
PARENT_TREE=None
PARENT_ROOT_PIN=None
PARENT_SOURCE_PIN=None
PARENT_MODULE_PIN=None
SKU_HEAD=None
SKU_TREE=None
SKU_ROOT_PIN=None
SKU_SOURCE_PIN=None
RUNTIME_ENTRY=None
GATES=('PARENT_HEAD','PARENT_TREE','PARENT_ROOT_PIN','PARENT_SOURCE_PIN','PARENT_MODULE_PIN',
    'SKU_HEAD','SKU_TREE','SKU_ROOT_PIN','SKU_SOURCE_PIN','RUNTIME_ENTRY')


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def require_ready():
    if any(globals()[name]is None for name in GATES):
        raise ValueError('SKU_MONEY_COMPOSITE_ACTUAL_MANDOR17_MONEY19_AND_OWNING_ENTRY_PENDING')


def admitted(parent_raw,money_raw,case_ids):
    # Refuse before reading receipts, inspecting modules or accessing Git/ERP.
    require_ready()
    if pin(parent_raw)!=PARENT_ROOT_PIN or pin(money_raw)!=SKU_ROOT_PIN:
        raise ValueError('SKU_MONEY_COMPOSITE_EXACT_ROOT_ORIGINALS_REQUIRED')
    parent,money=json.loads(parent_raw),json.loads(money_raw)
    expected_parent=dict(status='ROOT_VERIFIED_CURRENT_MANDOR17_ALL5',head=PARENT_HEAD,tree=PARENT_TREE,
        actual_Native_cases=9,actual_Native_session_cases=4,actual_Auth_HTTP_cases=2,actual_browser_cases=2,
        actual_business_cases=17,complete17_qualified=True,package_all_five=True,prior_runs_aggregated=False,
        assembly_source=PARENT_MODULE_PIN,production_go=False,independent_acceptance=False)
    expected_money=dict(status='ROOT_VERIFIED_CURRENT_SKU_MONEY_NATIVE19_ALL5',head=SKU_HEAD,tree=SKU_TREE,
        actual_Native_cases=19,actual_Auth_HTTP_cases=0,actual_browser_cases=0,complete19_qualified=True,
        native_case_ids=case_ids,package_all_five=True,prior_runs_aggregated=False,production_go=False,
        independent_acceptance=False)
    if type(case_ids)is not list or len(case_ids)!=19 or len(set(case_ids))!=19:
        raise ValueError('SKU_MONEY_COMPOSITE_EXACT_NINETEEN_CASES_REQUIRED')
    for value,expected in ((parent,expected_parent),(money,expected_money)):
        for key,item in expected.items():
            if type(value.get(key))is not type(item)or value[key]!=item:
                raise ValueError('SKU_MONEY_COMPOSITE_ACTUAL_COMPLETE_PARENT_OR_CHILD_REQUIRED:'+key)
        if value.get('synthetic_receipt_not_an_actual_qualification')is True:
            raise ValueError('SKU_MONEY_COMPOSITE_SYNTHETIC_RECEIPT_REFUSED')
    for value,key,expected in ((parent,'qualified_current_Mandor_sources',PARENT_SOURCE_PIN),
        (money,'qualified_SKU_cost_money_sources',SKU_SOURCE_PIN)):
        if type(value.get(key))is not dict or pin(canonical(value[key]))!=expected:
            raise ValueError('SKU_MONEY_COMPOSITE_COMPLETE_ACCEPTED_SOURCE_GRAPH_REQUIRED:'+key)
    return dict(parent_root=pin(parent_raw),money_root=pin(money_raw),runtime_entry=RUNTIME_ENTRY,
        actual_composite_cases=0,production_go=False,independent_acceptance=False)
