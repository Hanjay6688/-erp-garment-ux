"""Closed current-parent/source/complete-lifecycle entry gates."""
from hashlib import sha256
import json

MANDOR_ROOT_PIN = {'bytes': 19149, 'sha256': '87f9c26be35fb84288189162c6ed18edc9d12f9648901ef36a41c85a168e7670'}
MONEY_SOURCE_PREFLIGHT_PIN = {'bytes': 368964, 'sha256': '55c13119aef4a9307b1638864b8eec3199e574a8876c26aa3254aa0920b1a8cb'}
CURRENT_MONEY_GRAPH_PIN = {'bytes': 13001, 'sha256': '238cac4f3827b6631bd9278fb6f06113b7f6b824dc07bea1ef97d83be50bbf44'}
COMBINED_NATIVE_PLAN_PIN = {'bytes': 2762, 'sha256': 'df9837324b15cba9be756a27e27776fa11f1a153e01ee2ee0fa296aa9ddeb1a8'}
OWNING_RUNTIME_ENTRY = 'scripts/current-sku-automatic-composite-preparation/qualification.py'
GATES = ('MANDOR_ROOT_PIN', 'MONEY_SOURCE_PREFLIGHT_PIN', 'CURRENT_MONEY_GRAPH_PIN',
         'COMBINED_NATIVE_PLAN_PIN', 'OWNING_RUNTIME_ENTRY')
BROWSER_IDS = ('SKU_CURRENT_MOVAVG_DESKTOP_REAL_AUTH_PAIR_VALUE_RECOVERY_INVERSE',
               'SKU_CURRENT_MOVAVG_MOBILE390_REAL_AUTH_PAIR_VALUE_GUARDS_INVERSE')


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
            or plan.get('required_browser_case_ids') != list(BROWSER_IDS)
            or plan.get('fresh_real_Auth_browser_required') is not True
            or plan.get('business_cases_planned') != 27
            or type(plan.get('actual_ERP_cases')) is not int or plan['actual_ERP_cases'] != 0):
        raise ValueError('SKU_AUTOMATIC_FULL_NATIVE_CASE_PLAN_REQUIRED_BEFORE_INSTALL')
    return dict(parent_root=pin(parent_raw), money_source_preflight=pin(money_raw),
                complete_native_plan=pin(plan_raw), owning_entry=OWNING_RUNTIME_ENTRY,
                actual_ERP_cases=0, production_go=False)
