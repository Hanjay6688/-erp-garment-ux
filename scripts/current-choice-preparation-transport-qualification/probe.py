"""Focused actual Auth3/race3 on complete composition with exact baseline restore."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import json,os,subprocess,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_p21_current_chain_rehearsal_probe as chain
import cp7_current_choice_preparation.installation as product
import importlib.util
_spec=importlib.util.spec_from_file_location("current_bounded_finance_native_cases",HERE/"cases.py")
business=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(business)
_spec=importlib.util.spec_from_file_location('bounded_finance_current_native',REPO/'scripts/current-analog-consumer-opening-qualification/probe.py')
current_native=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(current_native)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
import cp6_auditor_modes as modes
from cp7_current_transport_original_schema import checked_group
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
GROUPS=business.GROUPS
IDS=tuple(key for ids in GROUPS.values() for key in ids)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

qualified_native=load('choice_transport_public_native_parent',REPO/'scripts/current-frozen-public-native-qualification/probe.py')
copies=load('choice_transport_http_copy',REPO/'scripts/ow04-payment-current-qualification/copy_authority.py')
race_copies=load('choice_transport_race_copy',REPO/'scripts/ow04-payment-current-races-qualification/copy_authority.py')
LABEL='CP7_D17_18_CHOICE_TRANSPORT6'
PRE_DUMP='/tmp/current_d17_18_choice_transport_pre.dump'
database,drill,dump=current_native.database,current_native.drill,current_native.dump
sql=current_native.sql
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None
_spec=importlib.util.spec_from_file_location('performance_native_phase_diagnostics',REPO/'scripts/current-frozen-public-native-qualification/progress.py')
phase_diagnostics=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(phase_diagnostics)
progress=phase_diagnostics.Progress(OUT.with_name(LABEL+'_PROGRESS.jsonl'))


current_advisor=load('current_choice_private_advisor_review',REPO/'scripts/current-choice-preparation-native-qualification/advisor_review.py')


def admitted():
    spec=importlib.util.spec_from_file_location('current_finance_model_admission',HERE/'admission.py')
    admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
    return admission.admitted(REPO,HERE,IDS,product,qualified_native,GROUPS)


def group_ok(group,ids,races=False):
    try:checked_group(group,list(ids),races=races)
    except (AssertionError,KeyError,TypeError):return False
    return True


def verify(cur):
    if STATE is None:raise ValueError('OW12A_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return product.verify(cur,STATE)


def run():
    global STATE
    original_copy=modes.copy_db
    progress.mark('WRITER_RUNTIME_START')
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,real_browser_claim=False,factory3600_claim=False,
        actual_cron_claim=False,transport_groups={},
        full_OW11_acceptance=False,production_go=False,independent_acceptance=False)
    progress.mark('SOURCE_ADMITTED')
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
        progress.mark('BASELINE_CAPTURED')
        dump.dump(database.SOURCE,PRE_DUMP);pre_dumped=True
        progress.mark('PREINSTALL_DUMP_READY')
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            try:
                report['install_boundary_lock']=current_native.acquire_boundary(cur)
                STATE=product.install(cur)
                progress.mark('INSTALL_RETURNED')
            except Exception:
                # Keep the exact predecessor definitions for diagnosis of a changed anchor.
                report['installation_failed_before_commit']=True
                raise
            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            report['current_private_info_authority']=current_advisor.capture(cur)
            new_roles=database._roles(cur)-before_roles
            conn.commit();installed=True
        progress.mark('INSTALL_COMMITTED')
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        for helper in (copies,race_copies):
            helper.PRODUCT=SimpleNamespace(catalog=product.catalog,verify=product.verify)
            helper.STATE=dict(STATE,installed_catalog=STATE['after'])
            helper.ORIGINAL_COPY_DATABASE=original_copy
        def copy_database(name):
            return race_copies.copy_database(name) if name=='cp6_auditor_race' else copies.copy_database(name)
        modes.copy_db=copy_database
        with business.installed(STATE,verify) as source_binding:
            report['business_source_binding']=source_binding
            for name,ids in GROUPS.items():
                progress.mark(name.upper()+'_STARTED')
                is_race=name.endswith('_races')
                runner=modes.run_races if is_race else modes.run_http
                group=runner(business,verify,'choice_preparation_'+name)
                report['transport_groups'][name]=group
                if not group_ok(group,ids,is_race):
                    report.setdefault('group_failures',[]).append(dict(group=name,error=group.get('error'),counts=group.get('counts')))
                assert group.get('database_remaining')==0 and not group.get('cleanup_failures'),('CHOICE_TRANSPORT_COPY_NOT_CLEAN',name)
                if not is_race:
                    assert (group.get('auth_counts') or {}).get('restored') and not group.get('auth_cleanup_failures'),'CHOICE_AUTH_NOT_CLEAN'
                progress.mark(name.upper()+'_RETURNED')
        report['copy_catalog_admissions']=copies.COPY_ADMISSIONS
        report['race_copy_catalog_admissions']=race_copies.COPY_ADMISSIONS
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            report['inverse_boundary_lock']=current_native.acquire_boundary(cur)
            assert product.catalog._data(cur)==STATE['preuse_data_and_sequences'],'TRANSPORT_CHANGED_SOURCE_DATABASE'
            report['source_database_all_rows_sequences_unchanged']=True
            report['complete_preuse_removal']=product.rollback_preuse(cur,STATE)
            conn.commit()
        progress.mark('PRISTINE_SOURCE_INVERSE_RETURNED')
    except Exception as error:
        progress.mark('WRITER_ERROR')
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        modes.copy_db=original_copy
        report['copy_catalog_admissions']=copies.COPY_ADMISSIONS
        report['race_copy_catalog_admissions']=race_copies.COPY_ADMISSIONS
        if before is not None and pre_dumped:
            try:
                # Restore the complete source baseline even after a failed copy
                # or inverse. Copy deletion alone is not backup-restore credit.
                progress.mark('RESTORE_STARTED')
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
                    report['advisor_disposition']=current_advisor.review(report['advisor_delta'],report['verified_predecessor_info_manifest'],report['current_private_info_authority'],core.advisor_disposition)
                    report['advisor_gate']=report['advisor_disposition']['gate']and report['baseline_advisors_equal']
                else:report['advisor_gate']=report['baseline_advisors_equal']
                progress.mark('BASELINE_RESTORATION_CHECKED')
            except Exception as error:
                progress.mark('RESTORE_ERROR')
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        drill.docker('rm','-f',PRE_DUMP,check=False)
        groups=report['transport_groups']
        report['observed_case_count']=sum(sum(g.get('counts',{}).values()) for g in groups.values())
        report['required_case_ids_pass']=set(groups)==set(GROUPS) and all(group_ok(groups[name],ids,name.endswith('_races')) for name,ids in GROUPS.items())
        if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and report.get('baseline_full22_all_rows_all_sequences_equal') and report.get('complete_preuse_removal') and report['required_case_ids_pass'] and report['observed_case_count']==6 and len(copies.COPY_ADMISSIONS)==1 and len(race_copies.COPY_ADMISSIONS)==3:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        progress.mark('ORIGINAL_WRITTEN')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for group in groups.values():
            for name,case in group.get('cases',group.get('races',{})).items():
                print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],full_OW11_acceptance=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    progress.mark('PACKAGE_START')
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
    progress.mark('PACKAGE_RETURNED')
