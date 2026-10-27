"""One combined install, seven separate fixtures, complete restoration each time."""
from pathlib import Path
import importlib.util,traceback
import psycopg

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


cases=load('combined_runtime_cases',HERE/'qualification_cases.py')
parent=load('combined_unchanged_complete_restore',ROOT/'scripts/current-finance-followups-qualification/runner.py')
product=cases.product
isolated,retained,scheduler_quiet=parent.isolated,parent.retained,parent.scheduler_quiet
CASE='COMBINED_FINANCE_NATIVE_SOURCE_REPORT_FACTORY_CRON7'
INSTALLED_DUMP='/tmp/d17_18_combined_finance_unused.dump'
CATALOG_REFUSAL='COMBINED_FINANCE_ACTUAL_ALL22_CHANGED'


def exercise(conn,cur,database,url,report,state):
    product.sources()  # Accepted prerequisite required before any DB access.
    assert conn.info.host in ('localhost','127.0.0.1') and conn.info.port==54322
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    conn.rollback();conn.close()
    _,_,_,_,catalog=product.runtime()
    with psycopg.connect(url)as baseline,baseline.cursor()as b:
        assert catalog._catalog_rows(b)==state['after']
        before=catalog._portable(catalog._catalog_rows(b))
        data=catalog._data(b);roles=database._roles(b);baseline.rollback()
    hashes=retained.drill.data_hashes(database.SOURCE);profile=database._database_profile(database.SOURCE)
    retained.dump.dump(database.SOURCE,INSTALLED_DUMP)
    active=None
    report.update(case_id=CASE,status='INCOMPLETE',shared_fixture_data=False,
        actual_combined_installation=True,production_go=False,independent_acceptance=False,
        default_adopted=False,real_Auth_browser_claim=False,performance_qualification=False)

    def run(operation,result):
        nonlocal active
        active=result
        with psycopg.connect(url)as current,current.cursor()as c:
            raw=catalog._catalog_rows(c)
            assert catalog._portable(raw)==before
            assert catalog._data(c)==data and database._roles(c)==roles
            result['fresh_restored_catalog_spelling_diff']={g:{k:dict(original=state['after'][g].get(k),restored=raw[g].get(k))
                for k in set(raw[g])|set(state['after'][g])if raw[g].get(k)!=state['after'][g].get(k)}for g in raw}
            result['fresh_restored_catalog_spelling_diff']={g:v for g,v in result['fresh_restored_catalog_spelling_diff'].items()if v}
            current.rollback();operation(current,c,database,url,result)

    def restore():
        quiet=scheduler_quiet(url);guard_error=None
        with psycopg.connect(url)as current,current.cursor()as c:
            held=catalog._catalog_rows(c);actual=catalog._data(c)
            undeclared=catalog._portable(held)!=before
            raw_changed=held!=state['after'];data_changed=actual!=data
            reason=CATALOG_REFUSAL if raw_changed else product.USED_ERROR if data_changed else None
            if reason is not None:
                try:
                    try:product.rollback_preuse(c,state)
                    except (AssertionError,ValueError)as error:assert str(error)==reason,str(error)
                    else:raise AssertionError('COMBINED_AFTER_USE_INVERSE_NOT_REFUSED')
                    assert catalog._catalog_rows(c)==held and catalog._data(c)==actual
                except Exception as error:guard_error=(error,traceback.format_exc())
            current.rollback()
        restored=database._restore(INSTALLED_DUMP,database.SOURCE,profile)
        assert restored['only_pg_cron_errors']
        assert retained.drill.data_hashes(database.SOURCE)==hashes
        with psycopg.connect(url)as current,current.cursor()as c:
            assert catalog._portable(catalog._catalog_rows(c))==before
            assert catalog._data(c)==data and database._roles(c)==roles
            current.rollback()
        proof=dict(all22_all_rows_all_sequences_roles_exact=True,complete_database_dump_restored=True,
            scheduler_quiet=quiet,restore=restored,selected_table_cleanup=False,
            inverse_refusal=reason,inverse_refused_before_DDL=reason is not None,
            used_guard_refused_before_DDL=reason==product.USED_ERROR,
            committed_data_changed=data_changed,raw_catalog_spelling_changed=raw_changed,
            unexpected_catalog_change=undeclared)
        active['installed_baseline_restoration']=proof
        if guard_error:
            proof.update(guard_error=str(guard_error[0]),guard_traceback=guard_error[1]);raise guard_error[0]
        assert not undeclared,'COMBINED_UNDECLARED_CATALOG_CHANGE_BEFORE_RESTORE'
        return proof

    try:
        with cases.installed_operations(state):isolated.exercise(cases.CHILDREN,run,restore,report)
    finally:retained.drill.docker('rm','-f',INSTALLED_DUMP,check=False)
    first=report['cases'][cases.CHILDREN[0][0]]
    assert first['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    assert all(c['installed_baseline_restoration']['complete_database_dump_restored']for c in report['cases'].values())
    report.update(status='PASS',used_guard_refused_before_DDL=True,actual_cron_claim=True,
        actual_minute_cron_groups=2,unchanged_native_cases=20,
        factory_current_public_jobs_completed=True,combined_component_qualified=True,
        full_combined_final_qualification=False,real_Auth_browser_claim=False)
