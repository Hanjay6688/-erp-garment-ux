"""Five diagnostic operations; restore the entire installed DB between each."""
from pathlib import Path
import importlib.util
import psycopg

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
INSTALLED_DUMP='/tmp/d17_18_consistent_capture_unused.dump'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


cases=load('consistent_capture_operations',HERE/'cases.py')
parent=load('consistent_capture_parent_restore',ROOT/'scripts/current-finance-followups-qualification/runner.py')
isolated=parent.isolated
retained=parent.retained
product=parent.product
scheduler_quiet=parent.scheduler_quiet
CASE='FINANCE_REPORT_BOOK_CONSISTENCY_ISOLATED5'
CHILDREN=cases.CHILDREN
CATALOG_REFUSAL='READONLY_FINANCE_ACTUAL_FULL22_CHANGED'


def inverse_expectation(catalog_changed,data_changed):
    # The parent inverse is deliberately not rewritten to accept our candidate.
    # Its exact-catalog guard precedes its data guard. Report the real reason.
    if catalog_changed:return CATALOG_REFUSAL
    if data_changed:return product.USED_ERROR
    return None


def exercise(conn,cur,database,url,report,installation_state):
    assert conn.info.host in ('localhost','127.0.0.1') and conn.info.port==54322
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    conn.rollback();conn.close()
    predecessor,_,_,_=product.runtime();catalog=predecessor.catalog
    with psycopg.connect(url)as baseline,baseline.cursor()as b:
        before_catalog=catalog._portable(catalog._catalog_rows(b))
        before_data=catalog._data(b);before_roles=database._roles(b);baseline.rollback()
    before_hashes=retained.drill.data_hashes(database.SOURCE)
    profile=database._database_profile(database.SOURCE)
    retained.dump.dump(database.SOURCE,INSTALLED_DUMP)
    report.update(case_id=CASE,status='INCOMPLETE',diagnostic_only=True,
        shared_installation_only=True,shared_fixture_data=False,
        production_go=False,independent_acceptance=False,product_adoption=False,
        performance_qualification=False,factory3600_claim=False)

    def run(operation,result):
        with psycopg.connect(url)as current,current.cursor()as c:
            assert catalog._portable(catalog._catalog_rows(c))==before_catalog
            assert catalog._data(c)==before_data and database._roles(c)==before_roles
            current.rollback();operation(current,c,database,url,result)

    def restore():
        quiet=scheduler_quiet(url)
        with psycopg.connect(url)as current,current.cursor()as c:
            held=catalog._catalog_rows(c);actual=catalog._data(c)
            schema_changed=catalog._portable(held)!=before_catalog
            data_changed=actual!=before_data
            refusal=inverse_expectation(schema_changed,data_changed)
            if refusal is not None:
                try:product.rollback_preuse(c,installation_state)
                except ValueError as error:assert str(error)==refusal,str(error)
                else:raise AssertionError('CONSISTENT_CAPTURE_PARENT_INVERSE_NOT_REFUSED')
                assert catalog._catalog_rows(c)==held and catalog._data(c)==actual
            current.rollback()
        restored=database._restore(INSTALLED_DUMP,database.SOURCE,profile)
        assert restored['only_pg_cron_errors']
        assert retained.drill.data_hashes(database.SOURCE)==before_hashes
        with psycopg.connect(url)as current,current.cursor()as c:
            assert catalog._portable(catalog._catalog_rows(c))==before_catalog
            assert catalog._data(c)==before_data and database._roles(c)==before_roles
            current.rollback()
        return dict(all22_all_rows_all_sequences_roles_exact=True,
            complete_database_dump_restored=True,scheduler_quiet=quiet,restore=restored,
            selected_table_cleanup=False,candidate_catalog_changed=schema_changed,
            committed_data_changed=data_changed,parent_inverse_refusal=refusal,
            parent_inverse_refused_before_DDL=refusal is not None,
            used_guard_applicable=refusal==product.USED_ERROR,
            used_guard_refused_before_DDL=refusal==product.USED_ERROR)

    try:isolated.exercise(CHILDREN,run,restore,report)
    finally:retained.drill.docker('rm','-f',INSTALLED_DUMP,check=False)
    proofs=[c['installed_baseline_restoration']for c in report['cases'].values()]
    assert len(proofs)==5 and all(p['complete_database_dump_restored']for p in proofs)
    # The unchanged-parent overhead fixture proves the actual used-data guard.
    # Candidate-schema cases prove the earlier exact-catalog refusal instead.
    assert any(p['used_guard_refused_before_DDL']for p in proofs)
    assert all(p['parent_inverse_refused_before_DDL']for p in proofs)
    report.update(status='PASS',diagnostic_collection_completed=True,
        candidate_schema_never_projected_into_parent_catalog=True,
        rollback_only_native_group_not_claimed_as_committed_fixture=True,
        actual_cron_claim=True,used_guard_refused_before_DDL=True)
