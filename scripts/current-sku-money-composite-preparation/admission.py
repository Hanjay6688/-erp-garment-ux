"""Admit an actual Mandor17 parent and an unqualified, exact money candidate.

The owning combined run must execute all nineteen financial cases and restore
all five gates. A source preflight grants no financial case or acceptance.
"""
from hashlib import sha256
import json

PARENT_HEAD=None
PARENT_TREE=None
PARENT_ROOT_PIN=None
PARENT_SOURCE_PIN=None
PARENT_MODULE_PIN=None
SKU_HEAD=None
SKU_TREE=None
SKU_SOURCE_PREFLIGHT_PIN=None
SKU_SOURCE_PIN=None
RUNTIME_ENTRY=None
GATES=('PARENT_HEAD','PARENT_TREE','PARENT_ROOT_PIN','PARENT_SOURCE_PIN','PARENT_MODULE_PIN',
    'SKU_HEAD','SKU_TREE','SKU_SOURCE_PREFLIGHT_PIN','SKU_SOURCE_PIN','RUNTIME_ENTRY')
SOURCE_FENCE_SHA256='1439d70810383db377c48e043df7fb6d487a1b2f1a995e8993a2c08590f9f797'


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def require_ready():
    if any(globals()[name]is None for name in GATES):
        raise ValueError('SKU_MONEY_COMPOSITE_ACTUAL_MANDOR17_CANDIDATE_SOURCE_AND_OWNING_ENTRY_PENDING')


def admitted(parent_raw,money_raw,case_ids):
    # Refuse before reading receipts, inspecting modules or accessing Git/ERP.
    require_ready()
    if pin(parent_raw)!=PARENT_ROOT_PIN or pin(money_raw)!=SKU_SOURCE_PREFLIGHT_PIN:
        raise ValueError('SKU_MONEY_COMPOSITE_EXACT_PARENT_ROOT_AND_CANDIDATE_SOURCE_REQUIRED')
    parent,money=json.loads(parent_raw),json.loads(money_raw)
    expected_parent=dict(status='ROOT_VERIFIED_CURRENT_MANDOR17_ALL5',head=PARENT_HEAD,tree=PARENT_TREE,
        actual_Native_cases=9,actual_Native_session_cases=4,actual_Auth_HTTP_cases=2,actual_browser_cases=2,
        actual_business_cases=17,complete17_qualified=True,package_all_five=True,prior_runs_aggregated=False,
        assembly_source=PARENT_MODULE_PIN,production_go=False,independent_acceptance=False)
    expected_money=dict(status='EXACT_PREPARED_MONEY19_SOURCE_NO_RUNTIME_CREDIT',
        declared_candidate_head=SKU_HEAD,candidate_tree=SKU_TREE,
        identity_basis='IMMUTABLE_TREE_AND_COMPLETE_SOURCE_GRAPH_NOT_EXECUTED_PUBLIC_COMMIT',
        accepted_parent_requirements_preserved=['actual Native27 and all five gates','actual moving Native6 and all five gates'],
        candidate_money_financially_qualified=False,actual_ERP_cases=0,actual_Native_cases=0,actual_Auth_HTTP_cases=0,
        actual_browser_cases=0,production_go=False,independent_acceptance=False)
    if type(case_ids)is not list or len(case_ids)!=19 or len(set(case_ids))!=19:
        raise ValueError('SKU_MONEY_COMPOSITE_EXACT_NINETEEN_CASES_REQUIRED')
    for value,expected in ((parent,expected_parent),(money,expected_money)):
        for key,item in expected.items():
            if type(value.get(key))is not type(item)or value[key]!=item:
                raise ValueError('SKU_MONEY_COMPOSITE_ACTUAL_PARENT_AND_UNQUALIFIED_CANDIDATE_REQUIRED:'+key)
        if value.get('synthetic_receipt_not_an_actual_qualification')is True:
            raise ValueError('SKU_MONEY_COMPOSITE_SYNTHETIC_RECEIPT_REFUSED')
    if any(money.get(key)is True for key in('complete19_qualified','package_all_five','prior_runs_aggregated')):
        raise ValueError('SKU_MONEY_COMPOSITE_SOURCE_PREFLIGHT_IS_NOT_FINANCIAL_ACCEPTANCE')
    current=money.get('complete_candidate_source_admission')
    expected_current=dict(status='EXACT_NATIVE27_MOVING6_AND_MONEY19_GRAPH_ADMITTED',case_ids=case_ids,
        actual_Native_case_ids=case_ids,actual_ERP_cases=0,production_go=False,independent_acceptance=False)
    if type(current)is not dict:raise ValueError('SKU_MONEY_COMPOSITE_COMPLETE_CANDIDATE_SOURCE_PREFLIGHT_REQUIRED')
    for key,value in expected_current.items():
        if type(current.get(key))is not type(value)or current[key]!=value:
            raise ValueError('SKU_MONEY_COMPOSITE_SOURCE_PREFLIGHT_CANNOT_REPLACE_FRESH_NINETEEN:'+key)
    parents=current.get('parents',{})
    if parents.get('status')!='EXACT_NATIVE27_AND_MOVING_NATIVE6_PARENTS' or type(parents.get('actual_new_cases'))is not int or parents['actual_new_cases']!=0:
        raise ValueError('SKU_MONEY_COMPOSITE_RETAINED_ACTUAL_NATIVE27_AND_MOVING6_REQUIRED')
    guard=money.get('network_database_guard')
    expected_guard=dict(attempts=[],network_nonGit_attempts=[],public_source_sha256=SOURCE_FENCE_SHA256,
        self_controls=[dict(api=name,result='DENIED_BEFORE_LIBPQ')for name in
            ('psycopg.connect','psycopg.Connection.connect','psycopg.AsyncConnection.connect')]+
            [dict(original_connect_descriptors_restored=True)])
    if canonical(guard)!=canonical(expected_guard):
        raise ValueError('SKU_MONEY_COMPOSITE_EXACT_SOURCE_DATABASE_NETWORK_FENCE_REQUIRED')
    for value,key,expected in ((parent,'qualified_current_Mandor_sources',PARENT_SOURCE_PIN),
        (current,'current_installation',SKU_SOURCE_PIN)):
        if type(value.get(key))is not dict or pin(canonical(value[key]))!=expected:
            raise ValueError('SKU_MONEY_COMPOSITE_COMPLETE_PARENT_OR_CANDIDATE_SOURCE_GRAPH_REQUIRED:'+key)
    return dict(parent_root=pin(parent_raw),candidate_source_preflight=pin(money_raw),runtime_entry=RUNTIME_ENTRY,
        fresh_complete_money19_still_required=True,candidate_money_financially_qualified=False,
        actual_composite_cases=0,production_go=False,independent_acceptance=False)
