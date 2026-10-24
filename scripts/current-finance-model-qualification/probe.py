"""Native15 on the complete current finance/policy/model v2 composition.

The latest full A source admission and all declared B/correction hashes are
checked before DB. Fifteen real Native business cases, strict rollback and full22 inverse;
no hosted effects, real-Auth claim, factory-scale claim or audit acceptance.
"""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_p21_current_chain_rehearsal_probe as chain
import cp7_current_finance_model_installation as product
import importlib.util
_spec=importlib.util.spec_from_file_location("current_bounded_finance_native_cases",HERE/"cases.py")
business=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(business)
_spec=importlib.util.spec_from_file_location('bounded_finance_current_native',REPO/'scripts/current-analog-consumer-opening-qualification/probe.py')
current_native=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(current_native)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
IDS=business.IDS
LABEL='CP7_CURRENT_FINANCE_MODEL_NATIVE15'
PRE_DUMP='/tmp/current_finance_model_native_pre.dump'
database,drill,dump=current_native.database,current_native.drill,current_native.dump
sql=current_native.sql
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None


def admitted():
    spec=importlib.util.spec_from_file_location('current_finance_model_admission',HERE/'admission.py')
    admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
    return admission.admitted(REPO,HERE,IDS,product,business)


def cases(cur,today):
    result=business.cases(cur,today)
    assert tuple(key for key,_ in result)==IDS
    return result


def verify(cur):
    if STATE is None:raise ValueError('OW12A_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return product.verify(cur,STATE)


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
        with business.installed(STATE,verify)as source_binding,exact_public_catalog(native,retain_raw=True)as catalog:
            report['retained_business_source_binding']=source_binding
            report['native']=native.strict_group(LABEL,cases,verify)
        report['retained_model_setup_admissions']=business.SETUP_ADMISSIONS
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
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)and all(c['status']=='PASS'for c in group.get('cases',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report.get('baseline_full22_all_rows_all_sequences_equal')and report.get('complete_preuse_removal')and report['required_case_ids_pass']and group.get('counts')=={'PASS':len(IDS)}:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for name,case in group.get('cases',{}).items():
            print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],full_OW11_acceptance=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
