"""Six unchanged contract controls on CP6 and the full current dated target.

Preserve the first failed Original; restore all22/rows/sequences between the
baseline and current phases and again at the end. No oracle or case edit.
"""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import json,os,subprocess,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_p21_current_chain_rehearsal_probe as chain
import cp7_current_selected_return_installation as product
import importlib.util
_spec=importlib.util.spec_from_file_location("current_target_contract_business",REPO/"scripts/current-cp6-contract-qualification/cases.py")
business=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(business)
_spec=importlib.util.spec_from_file_location('bounded_finance_current_native',REPO/'scripts/current-analog-consumer-opening-qualification/probe.py')
current_native=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(current_native)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
IDS=business.IDS
LABEL='CP7_CURRENT_SELECTED_RETURN_CONTRACT6'
PRE_DUMP='/tmp/current_selected_return_contract_pre.dump'
database,drill,dump=current_native.database,current_native.drill,current_native.dump
sql=current_native.sql
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None
FIXTURES={}


def admitted():
    spec=importlib.util.spec_from_file_location('current_target_contract_admission',HERE/'admission.py')
    admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
    return admission.admitted(REPO,HERE,IDS,product,business)


def cases(cur,today):
    stage="current"if STATE is not None else"baseline"
    result=business.cases(cur,today,current=STATE is not None,evidence=FIXTURES.setdefault(stage,{}))
    assert tuple(key for key,_ in result)==IDS
    return result


def verify(cur):
    if STATE is None:raise ValueError('CURRENT_TARGET_CONTRACT_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return product.verify(cur,STATE)


@contextmanager
def keep_originals():
    old=native.r1.OUT
    native.r1.OUT=OUT.parent/"strict-groups"
    try:yield
    finally:native.r1.OUT=old


def run():
    global STATE
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,real_Auth_browser_claim=False,factory3600_claim=False,
        full_OW11_acceptance=False,production_go=False,independent_acceptance=False)
    installed=False;pre_dumped=False;before=None;new_roles=set()
    try:
        assert drill.SOURCE==database.SOURCE=='cp6_rollback'and drill.CONTAINER=='supabase_db_cp5-local'
        report['baseline_advisors']=advisors(package.boundary.PG)
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            assert conn.info.host in('127.0.0.1','localhost')and cur.execute('select current_database()').fetchone()==(database.SOURCE,)
            p09.wip.policy.bf.verified(cur)
            before_roles=database._roles(cur)
            baseline_catalog=product.catalog._portable(product.catalog._catalog_rows(cur))
            baseline_data=product.catalog._data(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
        pre_data=drill.data_hashes(database.SOURCE);pre_profile=database._database_profile(database.SOURCE)
        dump.dump(database.SOURCE,PRE_DUMP);pre_dumped=True
        with keep_originals(),exact_public_catalog(native,retain_raw=True)as baseline_observation:
            report['baseline']=native.strict_group(LABEL+'_BASELINE',cases,p09.wip.policy.bf.verified)
        report['baseline_public_catalog_comparison']=baseline_observation
        assert report['baseline']['complete_boundary_restored'],'BASELINE_CASE_BOUNDARY_NOT_RESTORED'
        # A SQL rollback cannot undo nextval. Start the second phase from the
        # exact complete backup, not the first phase's advanced sequences.
        baseline_reset=database._restore(PRE_DUMP,database.SOURCE,pre_profile)
        assert baseline_reset['only_pg_cron_errors']and not baseline_reset['unexplained']
        assert drill.data_hashes(database.SOURCE)==pre_data
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            assert database._roles(cur)==before_roles
            assert product.catalog._portable(product.catalog._catalog_rows(cur))==baseline_catalog
            assert product.catalog._data(cur)==baseline_data
            p09.wip.policy.bf.verified(cur);conn.rollback()
        report['between_phases_full22_ALLrows_ALLsequences_reset']=True
        report['between_phases_full_backup_restore']=baseline_reset
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            try:
                report['install_boundary_lock']=current_native.acquire_boundary(cur)
                STATE=product.install(cur)
                report['complete_preuse_removal']=product.rollback_preuse(cur,STATE)
                STATE=product.install(cur)
            except Exception:
                # Keep the exact predecessor definitions for diagnosis of a changed anchor.
                report['installation_failed_before_commit']=True
                raise
            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            new_roles=database._roles(cur)-before_roles
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with keep_originals(),exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,verify)
        report['unchanged_original_business_cases']=True
        report['native_public_catalog_comparison']=catalog
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            report['post_native_boundary_lock']=current_native.acquire_boundary(cur)
            held_catalog=product.catalog._catalog_rows(cur);actual=product.catalog._data(cur)
            changes={k:dict(before=STATE['preuse_data_and_sequences'].get(k),after=actual.get(k))
                for k in set(actual)|set(STATE['preuse_data_and_sequences'])if actual.get(k)!=STATE['preuse_data_and_sequences'].get(k)}
            report['post_native_all_data_changes']=changes
            assert all(k.startswith('sequence:')for k in changes),('NATIVE_CASES_PERSISTED_ROWS',changes)
            if changes:
                try:product.rollback_preuse(cur,STATE)
                except ValueError as error:assert str(error)==product.USED_ERROR
                else:raise AssertionError('AFTER_USE_INVERSE_WAS_NOT_REFUSED')
                assert product.catalog._catalog_rows(cur)==held_catalog and product.catalog._data(cur)==actual
                report['used_guard_refused_before_DDL']=True
            conn.rollback()
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if before is not None and pre_dumped:
            try:
                # Native nextval is not undone by case savepoints. Restore the
                # complete preinstall dump; never reset selected sequences or
                # weaken the product's global all-data guard.
                restored=database._restore(PRE_DUMP,database.SOURCE,pre_profile)
                assert restored['only_pg_cron_errors']
                report['baseline_restore']=restored
                assert drill.data_hashes(database.SOURCE)==pre_data
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    for role in sorted(new_roles):cur.execute(sql.SQL('drop role {}').format(sql.Identifier(role)))
                    conn.commit();assert database._roles(cur)==before_roles
                    assert product.catalog._portable(product.catalog._catalog_rows(cur))==baseline_catalog
                    assert product.catalog._data(cur)==baseline_data
                    report['baseline_full22_all_rows_all_sequences_equal']=True
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['baseline_advisors_equal']=advisors(package.boundary.PG)==report['baseline_advisors']
                if 'advisors_with_cp7'in report:
                    report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                    report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                    report['advisor_gate']=report['advisor_disposition']['gate']and report['baseline_advisors_equal']
                else:report['advisor_gate']=report['baseline_advisors_equal']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        drill.docker('rm','-f',PRE_DUMP,check=False)
        group=report.get('native',{})
        report['seed_prerequisite_preparation']=FIXTURES
        report['strict_group_originals']=[dict(path=str(p.relative_to(OUT.parent)),bytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())for p in sorted((OUT.parent/'strict-groups').glob('*.json'))]
        baseline=report.get('baseline',{})
        report['baseline_observed_case_count']=sum(baseline.get('counts',{}).values())
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['execution_count']=report['baseline_observed_case_count']+report['observed_case_count']
        report['legacy_results_relabelled']=False
        report['new_business_case_credit']=0
        report['case_status_comparison']={name:dict(baseline=baseline.get('cases',{}).get(name,{}).get('status'),current=group.get('cases',{}).get(name,{}).get('status'))for name in IDS}
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)and all(c['status']=='PASS'for c in group.get('cases',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report.get('baseline_full22_all_rows_all_sequences_equal')and report.get('complete_preuse_removal')and report['required_case_ids_pass']and group.get('counts')==baseline.get('counts')=={'PASS':len(IDS)}and report.get('between_phases_full22_ALLrows_ALLsequences_reset'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for name,case in group.get('cases',{}).items():
            print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],full_OW11_acceptance=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
