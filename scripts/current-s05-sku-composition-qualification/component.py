"""One current S05 Native10/browser2 component; retained SKU27 is not repeated."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
CASE = 'S05_ON_CURRENT_SKU_NATIVE10_REAL_AUTH_BROWSER2'


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE/file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def scheduler_quiet(url):
    native, _ = load('s05_sku_scheduler_component', 'native.py').component()
    return native.scheduler_quiet(url)


def exercise(conn, cur, database, url, report, state):
    native, proof = load('s05_sku_complete_native_component', 'native.py').component()
    report.update(status='INCOMPLETE', native_component_derivation=proof,
        actual_Native_cases=0, actual_browser_cases=0, production_go=False, independent_acceptance=False)
    first = report['fresh_Native10'] = dict(status='INCOMPLETE')
    native.exercise(conn, cur, database, url, first, state)
    if first.get('status') != 'PASS' or first.get('actual_Native_cases') != 10 or first.get('used_guard_refused_before_DDL') is not True:
        raise ValueError('S05_NATIVE10_AND_ACTUAL_USED_INVERSE_REQUIRED_BEFORE_BROWSER')
    second = report['fresh_real_Auth_browser2'] = dict(status='INCOMPLETE')
    load('s05_sku_complete_browser_component', 'browser_component.py').exercise(url, state, second)
    if second.get('status') != 'PASS' or second.get('actual_browser_cases') != 2:
        raise ValueError('S05_CURRENT_BROWSER2_REQUIRED')
    report.update(status='PASS', business_counts={'PASS': 12}, actual_Native_cases=10, actual_browser_cases=2,
        actual_Auth_HTTP_cases=0, actual_two_session_races=0, used_guard_refused_before_DDL=True,
        retained_SKU27_fresh_case_credit=0, report_business_DML=False,
        outer_restore_and_all5_package_gates_still_required=True,
        Afui_positive_HPP_zero_reimbursement_coverage=False)
