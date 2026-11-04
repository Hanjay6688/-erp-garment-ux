"""Closed current-parent/source/complete-lifecycle entry gates."""
from hashlib import sha256
import json

MANDOR_ROOT_PIN = None
MONEY_SOURCE_PREFLIGHT_PIN = None
CURRENT_MONEY_GRAPH_PIN = None
COMBINED_NATIVE_PLAN_PIN = None
OWNING_RUNTIME_ENTRY = None
GATES = ('MANDOR_ROOT_PIN', 'MONEY_SOURCE_PREFLIGHT_PIN', 'CURRENT_MONEY_GRAPH_PIN',
         'COMBINED_NATIVE_PLAN_PIN', 'OWNING_RUNTIME_ENTRY')


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def require_ready():
    if any(globals()[name] is None for name in GATES):
        raise ValueError('SKU_AUTOMATIC_CURRENT_PARENT_AND_FULL_NATIVE_LIFECYCLE_PENDING')


def inputs(parent_raw, money_raw, plan_raw):
    require_ready()
    for raw, expected in ((parent_raw, MANDOR_ROOT_PIN), (money_raw, MONEY_SOURCE_PREFLIGHT_PIN),
                          (plan_raw, COMBINED_NATIVE_PLAN_PIN)):
        if pin(raw) != expected:
            raise ValueError('SKU_AUTOMATIC_EXACT_CURRENT_PARENT_SOURCE_AND_PLAN_REQUIRED')
    plan = json.loads(plan_raw)
    if (plan.get('classification') != 'COMPLETE_NATIVE_MONEY_AND_AUTOMATIC_CASE_PLAN_NOT_ACCEPTANCE'
            or plan.get('full_upstream_native_completion_required') is not True
            or plan.get('retained_money19_unchanged') is not True
            or plan.get('model_receipt_can_satisfy_plan') is not False
            or type(plan.get('case_ids')) is not list or len(plan['case_ids']) <= 19
            or len(set(plan['case_ids'])) != len(plan['case_ids'])
            or type(plan.get('actual_ERP_cases')) is not int or plan['actual_ERP_cases'] != 0):
        raise ValueError('SKU_AUTOMATIC_FULL_NATIVE_CASE_PLAN_REQUIRED_BEFORE_INSTALL')
    return dict(parent_root=pin(parent_raw), money_source_preflight=pin(money_raw),
                complete_native_plan=pin(plan_raw), owning_entry=OWNING_RUNTIME_ENTRY,
                actual_ERP_cases=0, production_go=False)
