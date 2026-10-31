"""Complete retained physical browser-copy bridge; real joined product supplied."""
from types import SimpleNamespace
IDS=('S03_BROWSER_OWNER_EXPENSE_CORRECT_REVERSE_DESKTOP', 'S03_BROWSER_OWNER_CARRY_ALLOCATE_CANCEL_MOBILE390', 'S03_BROWSER_ACTUAL_STALE_AND_LOST_REPLY_SAME_UUID', 'S03_BROWSER_CURRENT_AUTH_RIGHTS_AND_DELAYED_CONTEXT')

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
