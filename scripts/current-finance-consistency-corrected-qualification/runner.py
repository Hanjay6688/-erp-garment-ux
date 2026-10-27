"""Corrected Native helper and actual cron; complete installed DB restoration."""
from pathlib import Path
import importlib.util,traceback
import psycopg

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
INSTALLED_DUMP='/tmp/d17_18_consistency_corrected_unused.dump'


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
CASE='FINANCE_CONSISTENCY_CORRECTED_NATIVE20_CRON1'
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
    active_result=None

    def run(operation,result):
        nonlocal active_result
        active_result=result;cases.EXPECTED_CATALOG=None
        with psycopg.connect(url)as current,current.cursor()as c:
            raw=catalog._catalog_rows(c)
            assert catalog._portable(raw)==before_catalog
            assert catalog._data(c)==before_data and database._roles(c)==before_roles
            result['fresh_restored_catalog_spelling_diff']={g:{k:dict(original=installation_state['after'][g].get(k),restored=raw[g].get(k))
                for k in set(raw[g])|set(installation_state['after'][g])
                if raw[g].get(k)!=installation_state['after'][g].get(k)}for g in raw}
            result['fresh_restored_catalog_spelling_diff']={g:v for g,v in result['fresh_restored_catalog_spelling_diff'].items()if v}
            current.rollback();operation(current,c,database,url,result)

    def restore():
        quiet=scheduler_quiet(url)
        with psycopg.connect(url)as current,current.cursor()as c:
            held=catalog._catalog_rows(c);actual=catalog._data(c)
            schema_changed=catalog._portable(held)!=before_catalog
            data_changed=actual!=before_data
            expected_catalog=cases.EXPECTED_CATALOG if cases.EXPECTED_CATALOG is not None else before_catalog
            undeclared=catalog._portable(held)!=expected_catalog
            # Full dump/reparse can change only the previously admitted portable
            # spellings. The original inverse still compares its exact raw seal.
            raw_changed=held!=installation_state['after']
            refusal=inverse_expectation(raw_changed,data_changed)
            guard_error=None
            if refusal is not None:
                try:
                    try:product.rollback_preuse(c,installation_state)
                    except ValueError as error:assert str(error)==refusal,str(error)
                    else:raise AssertionError('CONSISTENT_CAPTURE_PARENT_INVERSE_NOT_REFUSED')
                    assert catalog._catalog_rows(c)==held and catalog._data(c)==actual
                except Exception as error:guard_error=(error,traceback.format_exc())
            current.rollback()
        restored=database._restore(INSTALLED_DUMP,database.SOURCE,profile)
        assert restored['only_pg_cron_errors']
        assert retained.drill.data_hashes(database.SOURCE)==before_hashes
        with psycopg.connect(url)as current,current.cursor()as c:
            assert catalog._portable(catalog._catalog_rows(c))==before_catalog
            assert catalog._data(c)==before_data and database._roles(c)==before_roles
            current.rollback()
        proof=dict(all22_all_rows_all_sequences_roles_exact=True,
            complete_database_dump_restored=True,scheduler_quiet=quiet,restore=restored,
            selected_table_cleanup=False,candidate_catalog_changed=schema_changed,
            committed_data_changed=data_changed,parent_inverse_refusal=refusal,
            parent_inverse_refused_before_DDL=refusal is not None,
            used_guard_applicable=refusal==product.USED_ERROR,
            used_guard_refused_before_DDL=refusal==product.USED_ERROR)
        proof.update(unexpected_catalog_change=undeclared,raw_parent_catalog_spelling_changed=raw_changed)
        active_result['installed_baseline_restoration']=proof
        if guard_error:
            proof['guard_error']=str(guard_error[0]);proof['guard_traceback']=guard_error[1]
            raise guard_error[0]
        assert not undeclared,'CONSISTENT_CAPTURE_UNDECLARED_CATALOG_CHANGE_BEFORE_RESTORE'
        return proof

    try:
        cases.patch.RUNTIME_BASELINE=None
        first=report.setdefault('baseline_null_snapshot_counterexample',dict(status='INCOMPLETE'))
        print('BASELINE_NULL_SNAPSHOT_COUNTEREXAMPLE_START',flush=True)
        try:run(cases.baseline_assigned_transaction,first)
        except Exception as error:first.update(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc())
        finally:restore()
        print('BASELINE_NULL_SNAPSHOT_COUNTEREXAMPLE_END '+first['status']+' '+str(first.get('error')),flush=True)
        cases.patch.require_actual_baseline(first)
        assert first['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
        cases.patch.RUNTIME_BASELINE=first
        isolated.exercise(CHILDREN,run,restore,report)
    finally:retained.drill.docker('rm','-f',INSTALLED_DUMP,check=False)
    proofs=[c['installed_baseline_restoration']for c in report['cases'].values()]
    assert len(proofs)==2 and all(p['complete_database_dump_restored']for p in proofs)
    # The unchanged-parent overhead fixture proves the actual used-data guard.
    # Candidate-schema cases prove the earlier exact-catalog refusal instead.
    assert all(p['parent_inverse_refused_before_DDL']for p in proofs)
    report.update(status='PASS',diagnostic_collection_completed=True,
        candidate_schema_never_projected_into_parent_catalog=True,
        rollback_only_native_group_not_claimed_as_committed_fixture=True,
        actual_cron_claim=True,used_guard_refused_before_DDL=True,
        first_null_snapshot_counterexample_retained_as_INCOMPLETE=True)
