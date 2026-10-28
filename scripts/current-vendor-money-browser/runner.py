"""A money-only UI witness using the existing committed browser mode and copy adapter."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import cp6_auditor_modes as modes
from cp7_vendor_receivable import composition as product

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CASE='VENDOR_MONEY_BROWSER2'
IDS=('VENDOR_MONEY_BROWSER_DESKTOP_REFUND_INVERSE_HISTORY','VENDOR_MONEY_BROWSER_MOBILE_REFUND_ACCESS_HIDDEN')


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def scheduler_quiet(url):
    return load('vendor_money_browser_quiet',ROOT/'scripts/current-factory-initial-stage/factory.py').scheduler_quiet(url)


def exercise(conn,cur,database,url,report,state):
    from cp7_p21_current_chain_rehearsal_probe import helper
    _,_,_,_,catalog=product.runtime()
    adapter=load('vendor_money_browser_copy',ROOT/'scripts/ow04-payment-current-qualification/copy_authority.py')
    original=modes.copy_db;adapter.ORIGINAL_COPY_DATABASE=original
    adapter.PRODUCT=SimpleNamespace(catalog=catalog,verify=product.verify)
    adapter.STATE=dict(state,installed_catalog=state['after'])
    def verify(cursor):
        with helper.control.product_catalog(cursor):return product.verify(cursor,state)
    conn.rollback();cur.close();conn.close()
    try:
        modes.copy_db=adapter.copy_database
        report['browser']=modes.run_browser(HERE/'cases.mjs',verify,'vendor_money2')
    finally:
        modes.copy_db=original;report['copy_catalog_admissions']=list(adapter.COPY_ADMISSIONS)
    actual=report['browser']
    assert actual.get('counts')=={'PASS':2}and set(actual.get('cases',{}))==set(IDS),actual
    assert actual['database_remaining']==0 and not actual.get('cleanup_failures'),actual
    assert actual['auth_counts']['restored']is True and actual['console_errors']==0,actual
    assert not actual.get('session_leaks')and len(adapter.COPY_ADMISSIONS)==1
    assert adapter.COPY_ADMISSIONS[0]['all22_groups_equal_original_install']is True
    report.update(status='PASS',actual_browser_cases=2,actual_Native_cases=0,actual_two_session_races=0,
        used_guard_refused_before_DDL=True,used_guard_evidence='RETAINED_EXACT_COMPLETE_BACKEND11_NOT_RERUN',
        new_invoice_or_credit_screen_creation_claim=False,B_combined_analysis_browser_repeated=False,
        production_go=False,independent_acceptance=False)
