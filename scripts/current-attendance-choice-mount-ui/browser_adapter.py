"""Prepared S03 full-App browser component. Admission is CLOSED before any DB/Auth/browser import.

The owning backend and its reader extension need actual qualification first. This adapter
reuses the unchanged committed-copy engine; it never projects or reseals an all22 catalog.
"""
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from types import SimpleNamespace
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = 'S03_MOUNTED_FULL_APP_AUTH_BROWSER4'
IDS = (
    'S03_BROWSER_OWNER_EXPENSE_CORRECT_REVERSE_DESKTOP',
    'S03_BROWSER_OWNER_CARRY_ALLOCATE_CANCEL_MOBILE390',
    'S03_BROWSER_ACTUAL_STALE_AND_LOST_REPLY_SAME_UUID',
    'S03_BROWSER_CURRENT_AUTH_RIGHTS_AND_DELAYED_CONTEXT',
)


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admission():
    return load('s03_mount_ui_source_before_runtime', HERE / 'source_check.py').require_execution()


def _bridge(conn, cur, report, state, *, product, modes, helper, adapter, script, prerequisite):
    """Same physical copy-authority bridge as Source6, bound to the actual S03 product verifier.

    Tests may exercise orchestration using explicit doubles; those tests prove no money or
    real catalog. This function receives an already source-admitted, qualified product.
    """
    _, _, _, _, catalog = product.runtime()
    original = modes.copy_db
    adapter.ORIGINAL_COPY_DATABASE = original
    adapter.PRODUCT = SimpleNamespace(catalog=catalog, verify=product.verify)
    adapter.STATE = dict(state, installed_catalog=state['after'])
    if len(state['after']) != 22:
        raise ValueError('S03_BROWSER_COMPLETE22_REQUIRED')

    def verify(cursor):
        with helper.control.product_catalog(cursor):
            return product.verify(cursor, state)

    conn.rollback()
    cur.close()
    conn.close()
    try:
        modes.copy_db = adapter.copy_database
        report['browser'] = modes.run_browser(script, verify, 's03_choice_mounted4')
    finally:
        modes.copy_db = original
        report['copy_catalog_admissions'] = list(adapter.COPY_ADMISSIONS)
    actual = report['browser']
    assert actual.get('counts') == {'PASS': len(IDS)} and set(actual.get('cases', {})) == set(IDS), actual
    assert actual['database_remaining'] == 0 and not actual.get('cleanup_failures'), actual
    assert actual['auth_counts']['restored'] is True and actual['console_errors'] == 0, actual
    assert not actual.get('session_leaks') and len(adapter.COPY_ADMISSIONS) == 1
    assert adapter.COPY_ADMISSIONS[0]['all22_groups_equal_original_install'] is True
    assert prerequisite['used_inverse_guard_before_DDL'] is True
    report.update(status='PASS', actual_browser_cases=len(IDS), actual_Native_cases=0,
        actual_two_session_races=0, actual_Auth_HTTP_cases=0,
        actual_Auth_observed_within_browser=True,
        retained_backend_qualification=prerequisite,
        used_guard_refused_before_DDL=True,
        used_guard_evidence_classification='RETAINED_ACTUAL_BACKEND_NOT_RERUN',
        full_original_install_preuse_reinstall_restore_engine_required=True,
        product_catalog_projection=False, product_catalog_resealed=False,
        fixture_financial_UI_creation_claim=False, production_go=False, independent_acceptance=False)


def exercise(conn, cur, database, url, report, state):
    # Required before closing a cursor, opening a copy, importing ERP or touching Auth.
    prerequisite = admission()
    import cp6_auditor_modes as modes
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_attendance_period_choice import composition as product
    adapter = load('s03_mounted_copy_authority', ROOT / 'scripts/ow04-payment-current-qualification/copy_authority.py')
    return _bridge(conn, cur, report, state, product=product, modes=modes, helper=helper,
        adapter=adapter, script=HERE / 'cases.mjs', prerequisite=prerequisite)


if __name__ == '__main__':
    result = load('s03_mount_ui_source_only', HERE / 'source_check.py').check()
    print(json.dumps(result, sort_keys=True))
