"""Six unchanged policy/v2/target browser cases on the full dated-target composition."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import importlib.util
import json
import os
import subprocess
import sys
import traceback

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_p21_current_chain_rehearsal_probe as chain_proof
import cp7_p21_chain_adapter as chain_adapter
import cp7_ab_ui_admission as current_admission
import cp7_current_model_target_installation as quote_capability
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

native=load('current_consumer_browser_native_admission',REPO/'scripts/current-model-target-native-qualification/probe.py')
GROUPS={'policy': ['OW11_MODEL_POLICY_BROWSER_MOBILE_EXACT_RECOVERY_SUSPEND', 'OW11_MODEL_POLICY_BROWSER_DESKTOP_REVIEW_ACCESS_REVOKED'], 'evaluation': ['OW11_MODEL_V2_BROWSER_MOBILE_EXACT_RECOVERY_POLICY_SOURCE', 'OW11_MODEL_V2_BROWSER_DESKTOP_BASELINE_CURRENT_ACCESS'], 'target': ['OW11_MODEL_TARGET_BROWSER_MOBILE_UNKNOWN_ANALOG_CLEAR', 'OW11_MODEL_TARGET_BROWSER_DESKTOP_DENSE_PROVENANCE_RELOAD']}
IDS=tuple(k for group in GROUPS.values()for k in group)
copies=load('ow09_chain_exact_copy_authority',REPO/'scripts/ow04-payment-current-qualification/copy_authority.py')
product,previous,package,core,p09=quote_capability,chain_proof.previous,chain_proof.package,chain_proof.core,chain_proof.p09
LABEL='CP7_CURRENT_MODEL_TARGET_BROWSER6'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None

def admitted():
    admission=load('current_finance_model_browser_admission',HERE/'admission.py')
    return admission.admitted(REPO,HERE,IDS,product,native,GROUPS)


def group_ok(group,ids):
    return (set(group.get('cases',{}))==set(ids)
        and all(c.get('status')=='PASS'for c in group.get('cases',{}).values())
        and group.get('counts')=={'PASS':len(ids)}and not group.get('cleanup_failures')
        and group.get('database_remaining')==0 and group.get('host_exit')==0
        and group.get('host_status')=='RUN_COMPLETE'and group.get('console_errors')==0
        and(group.get('auth_counts')or{}).get('restored')and not group.get('auth_cleanup_failures')
        and not group.get('session_leaks')and group.get('real_auth')is True
        and group.get('test_only_usage_grant')is False and group.get('jwt_signed_by_runtime')is False)


def verify(cur):
    if STATE is None:raise ValueError('CURRENT_FINANCE_MODEL_BROWSER_INSTALLATION_REQUIRED')
    return product.verify(cur,STATE)

def run():
    global STATE
    original=modes.copy_db
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,
        all_owner_scope_complete=False,real_browser_claim=True,production_go=False,independent_acceptance=False,unchanged_B_policy_v2_target_browser_oracles=True,
        actual_positive_model_winner=False,forecast_applied=False,full_OW11_acceptance=False,
        browser_groups={},each_two_case_group_gets_separate_full_current_copy=True)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            report['install_boundary_lock']=native.current_native.acquire_boundary(cur)
            STATE=product.install(cur)
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        # The old copy helper only names its catalog field installed_catalog.
        # The chain adapter already supplies the SAME full current catalog; neither
        # product verification nor any observed member is projected/normalized.
        copies.PRODUCT=SimpleNamespace(catalog=product.catalog,verify=product.verify)
        copies.STATE=dict(STATE,installed_catalog=STATE['after'])
        copies.ORIGINAL_COPY_DATABASE=original
        modes.copy_db=copies.copy_database
        for name,ids in GROUPS.items():
            group=modes.run_browser(HERE/(name+'.mjs'),verify,'current_model_target_browser6_'+name)
            report['browser_groups'][name]=group
            if not group_ok(group,ids):
                report.setdefault('group_failures',[]).append(dict(group=name,error=group.get('error'),counts=group.get('counts')))
            # Independent cases may continue only after the previous real
            # browser copy and Auth state are fully cleaned. Preserve all
            # failed case results; the final six-case gate still requires PASS.
            assert group.get('database_remaining')==0 and(group.get('auth_counts')or{}).get('restored') \
                and not group.get('cleanup_failures')and not group.get('auth_cleanup_failures'),('CURRENT_BROWSER_GROUP_NOT_CLEAN',name)
        report['copy_catalog_admissions']=copies.COPY_ADMISSIONS
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc(),copy_catalog_admissions=copies.COPY_ADMISSIONS)
    finally:
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
        groups=report['browser_groups']
        report['observed_case_count']=sum(sum(g.get('counts',{}).values())for g in groups.values())
        report['required_case_ids_pass']=set(groups)==set(GROUPS)and all(group_ok(groups[name],ids)for name,ids in GROUPS.items())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and report['observed_case_count']==6 and len(copies.COPY_ADMISSIONS)==3:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for group in groups.values():
            for name,case in group.get('cases',{}).items():
                print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],all_owner_scope_complete=False,real_browser_claim=True,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
