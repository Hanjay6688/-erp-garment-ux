"""Actual bounded finance Auth and concurrency on the full current finance-model chain."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import importlib.util
import json
import subprocess
import sys
import traceback

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
from cp7_current_transport_original_schema import checked_group
import cp7_p21_current_chain_rehearsal_probe as chain_proof
import cp7_p21_chain_adapter as chain_adapter
import cp7_ab_ui_admission as current_admission
import cp7_current_versioned_target_installation as quote_capability
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

transport=load('current_finance_model_transport_cases',HERE/'cases.py')
snapshots=load('full_capture_snapshot_observer',HERE/'utc_snapshot.py')
native=load('current_consumer_transport_native_admission',REPO/'scripts/current-versioned-target-native-qualification/probe.py')
GROUPS=dict(finance_auth=list(transport.IDS['http']),finance_races=list(transport.IDS['races']))
IDS=tuple(k for group in GROUPS.values()for k in group)
copies=load('current_consumer_http_copy_authority',REPO/'scripts/ow04-payment-current-qualification/copy_authority.py')
race_copies=load('current_consumer_race_copy_authority',REPO/'scripts/ow04-payment-current-races-qualification/copy_authority.py')
product,previous,package,core,p09=quote_capability,chain_proof.previous,chain_proof.package,chain_proof.core,chain_proof.p09
LABEL='CP7_CURRENT_VERSIONED_TARGET_FINANCE10'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None

def admitted():
    admission=load('current_finance_model_transport_admission',HERE/'admission.py')
    return admission.admitted(REPO,HERE,IDS,product,native)


def group_ok(group,ids,races=False):
    try:checked_group(group,list(ids),races=races)
    except (AssertionError,KeyError,TypeError):return False
    return True


def verify(cur):
    if STATE is None:raise ValueError('CURRENT_FINANCE_MODEL_TRANSPORT_INSTALLATION_REQUIRED')
    return product.verify(cur,STATE)

def run():
    global STATE
    original=modes.copy_db
    observer=snapshots.CaptureObserver(transport.native)
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,
        all_owner_scope_complete=False,real_browser_claim=False,production_go=False,independent_acceptance=False,
        transport_groups={},new_bounded_finance_transport_cases=True,original_predecessor_cases_unchanged=True,actual_cron_claim=False)
    installed=False
    observer.install()
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            report['install_boundary_lock']=native.current_native.acquire_boundary(cur)
            STATE=product.install(cur)
            chain_proof.helper.control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        # The old copy helper only names its catalog field installed_catalog.
        # The chain adapter already supplies the SAME full current catalog; neither
        # product verification nor any observed member is projected/normalized.
        for helper in (copies,race_copies):
            helper.PRODUCT=SimpleNamespace(catalog=product.catalog,verify=product.verify)
            helper.STATE=dict(STATE,installed_catalog=STATE['after'])
            helper.ORIGINAL_COPY_DATABASE=original
        def copy_database(name):
            return race_copies.copy_database(name)if name=='cp6_auditor_race'else copies.copy_database(name)
        modes.copy_db=copy_database;transport.STATE=STATE
        for name,ids in GROUPS.items():
            if name=='finance_auth':group=modes.run_http(transport,verify,'current_finance_model_auth3')
            else:group=modes.run_races(transport,verify,'current_finance_model_races7')
            report['transport_groups'][name]=group
            if not group_ok(group,ids,name=='finance_races'):
                report.setdefault('group_failures',[]).append(dict(group=name,error=group.get('error'),counts=group.get('counts')))
            assert group.get('database_remaining')==0 and not group.get('cleanup_failures'),('TRANSPORT_GROUP_NOT_CLEAN',name)
            if name!='finance_races':
                assert(group.get('auth_counts')or{}).get('restored')and not group.get('auth_cleanup_failures'),('AUTH_GROUP_NOT_CLEAN',name)
        report['copy_catalog_admissions']=copies.COPY_ADMISSIONS
        report['race_copy_catalog_admissions']=race_copies.COPY_ADMISSIONS
        report['retained_setup_admissions']=transport.COPY_SETUP_ADMISSIONS

    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc(),copy_catalog_admissions=copies.COPY_ADMISSIONS,
            race_copy_catalog_admissions=race_copies.COPY_ADMISSIONS,retained_setup_admissions=transport.COPY_SETUP_ADMISSIONS)
    finally:
        observer.restore()
        report['full_capture_snapshot_observations']=observer.observations
        modes.copy_db=original
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['quiesce_before_removal']=chain_proof.quiesce(cur)
                    assert report['quiesce_before_removal']['clear'],'OW09_CHAIN_REMOVAL_LOCK_WAIT_EXHAUSTED'
                    report['inverse_boundary_lock']=native.current_native.acquire_boundary(cur)
                    report['complete_preuse_removal']=product.rollback_preuse(cur,STATE);conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        groups=report['transport_groups']
        report['observed_case_count']=sum(sum(g.get('counts',{}).values())for g in groups.values())
        report['required_case_ids_pass']=set(groups)==set(GROUPS)and all(group_ok(groups[name],ids,name=='finance_races')for name,ids in GROUPS.items())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass'] \
                and report['observed_case_count']==10 and len(copies.COPY_ADMISSIONS)==1 and len(race_copies.COPY_ADMISSIONS)==7:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for group in groups.values():
            for name,case in group.get('cases',group.get('races',{})).items():
                print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],all_owner_scope_complete=False,real_browser_claim=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
