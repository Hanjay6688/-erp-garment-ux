"""Existing two-session runtime and exact clone authority, on unchanged backend3194."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import cp6_auditor_modes as modes
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CASE='RETURN_REVERSE_COMMIT_ABORT2'
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def scheduler_quiet(url):
    return load('return_race_quiet',ROOT/'scripts/current-factory-initial-stage/factory.py').scheduler_quiet(url)

def exercise(conn,cur,database,url,report,state):
    from cp7_p21_current_chain_rehearsal_probe import helper
    control=helper.control
    legacy=load('return_race_unchanged_case_builders',ROOT/'scripts/current-cp6-race-qualification/cases.py')
    adapter=load('return_reverse_exact_guard',HERE/'race.py')
    product=load('return_race_current_product',ROOT/'scripts/current-factory-initial-stage/composition.py')
    copies=load('return_race_exact_clone_authority',ROOT/'scripts/ow04-payment-current-races-qualification/copy_authority.py')
    _,_,_,_,catalog=product.runtime()
    # All modules must use the same streamed catalog instance held by the
    # qualified outer runtime; do not independently patch or project a catalog.
    assert catalog is control.product.catalog if hasattr(control,'product')else True
    original_copy=modes.copy_db
    copies.ORIGINAL_COPY_DATABASE=original_copy
    copies.PRODUCT=SimpleNamespace(catalog=catalog,verify=product.verify)
    copies.STATE=dict(state,installed_catalog=state['after'])
    def verify(c):
        with control.product_catalog(c):return product.verify(c,state)
    class Selected:
        @staticmethod
        def races(tools,today):
            plans=dict(legacy.races(tools,today));assert set(adapter.IDS)<=set(plans)
            return [(name,lambda n=name:adapter.execute(legacy,plans[n],n,tools,product,state,control))for name in adapter.IDS]
    # PostgreSQL CREATE DATABASE ... TEMPLATE needs zero source sessions.
    # This connection belongs only to the outer diagnostics wrapper.
    conn.rollback();cur.close();conn.close()
    try:
        modes.copy_db=copies.copy_database
        result=modes.run_races(Selected,verify,'current_return_reverse_successor2')
    finally:modes.copy_db=original_copy
    report.update(races=result,copy_catalog_admissions=list(copies.COPY_ADMISSIONS),actual_two_session=True,
        real_Auth_browser_claim=False,production_go=False,independent_acceptance=False)
    assert result.get('counts')=={'PASS':2}and set(result['races'])==set(adapter.IDS),result
    assert result['database_remaining']==0 and not result.get('cleanup_failures')
    assert len(copies.COPY_ADMISSIONS)==2
    assert all(c['all22_groups_equal_original_install']is True for c in copies.COPY_ADMISSIONS)
    assert all(c['used_guard_refused_before_DDL']is True and not c['session_leaks']for c in result['races'].values())
    report.update(status='PASS',used_guard_refused_before_DDL=True,old_result_preserved=True,new_business_case_credit=0)
