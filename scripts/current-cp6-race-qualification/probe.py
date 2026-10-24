"""Retained AF/AG/AH/AI committed races before and on current A/B.

The latest full A source admission and all declared B/correction hashes are
checked before DB. 36 retained two-session schedules at each installation boundary, strict rollback and full22 inverse;
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
from cp7_ab_bounded_chain import composition as product
import cp7_ab_ui_admission as current_admission
import cp7_current_installation as installation
import importlib.util
from types import SimpleNamespace
import cp6_auditor_modes as modes
_spec=importlib.util.spec_from_file_location("current_cp6_race_cases",HERE/"cases.py")
business=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(business)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
_copy_spec=importlib.util.spec_from_file_location('current_cp6_race_authority',REPO/'scripts/ow04-payment-current-races-qualification/copy_authority.py')
copies=importlib.util.module_from_spec(_copy_spec);_copy_spec.loader.exec_module(copies)
IDS=business.IDS
LABEL='CP7_CURRENT_CP6_RACE36'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None


def admitted():
    previous,_=current_admission.admitted()
    guard_path=REPO/'scripts/cp7_customer_credit/integration/source_triggers/trigger_guard.py'
    spec=importlib.util.spec_from_file_location('current_owner_trigger_guard',guard_path)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.declarations(REPO)
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CURRENT_CP6_RACE_SOURCE_CHANGED',path)
    assert pins['case_ids']==list(IDS)and len(IDS)==36
    expected=json.loads((HERE/'EXPECTED.json').read_text())
    assert expected['count']==36 and expected['families']=={k:list(v)for k,v in business.FAMILY_IDS.items()}
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    return dict(qualified_A_predecessor=previous,complete_AB_product=product.sources(),current_installation=installation.sources(),qualification=pins)


def verify(cur):
    if STATE is None:raise ValueError('CURRENT_CP6_RACE_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return installation.verify(cur,STATE)


def run():
    global STATE
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,real_Auth_browser_claim=False,factory3600_claim=False,
        CP6_committed_races_only=True,production_go=False,independent_acceptance=False)
    installed=False
    original_copy=modes.copy_db
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            baseline_catalog=product.catalog._catalog_rows(cur)
            conn.rollback()
        copies.PRODUCT=SimpleNamespace(catalog=product.catalog,verify=lambda cur,state:p09.wip.policy.bf.verified(cur))
        copies.STATE=dict(installed_catalog=baseline_catalog)
        copies.ORIGINAL_COPY_DATABASE=original_copy
        modes.copy_db=copies.copy_database
        business.CURRENT=False
        report['baseline']=modes.run_races(business,p09.wip.policy.bf.verified,'current_cp6_baseline36')
        report['baseline_copy_catalog_admissions']=list(copies.COPY_ADMISSIONS)
        assert report['baseline']['database_remaining']==0,'CP6_RACE_BASELINE_COPY_NOT_REMOVED'
        copies.COPY_ADMISSIONS.clear()
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            try:
                STATE=installation.install(cur)
            except Exception:
                # Keep the exact predecessor definitions for diagnosis of a changed anchor.
                report['installation_failed_before_commit']=True
                raise
            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=installation.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        copies.PRODUCT=SimpleNamespace(catalog=product.catalog,verify=installation.verify)
        copies.STATE=dict(STATE,installed_catalog=STATE['after'])
        business.CURRENT=True
        report['races']=modes.run_races(business,verify,'current_cp6_36')
        report['copy_catalog_admissions']=list(copies.COPY_ADMISSIONS)
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        modes.copy_db=original_copy
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['quiesce_before_removal']=chain.quiesce(cur)
                    assert report['quiesce_before_removal']['clear']
                    report['complete_preuse_removal']=installation.rollback_preuse(cur,STATE)
                    conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('races',{})
        baseline=report.get('baseline',{})
        report['baseline_observed_case_count']=sum(baseline.get('counts',{}).values())
        report['case_status_comparison']={name:dict(baseline=baseline.get('races',{}).get(name,{}).get('status'),current=group.get('races',{}).get(name,{}).get('status'))for name in IDS}
        report['changed_case_statuses']={name:row for name,row in report['case_status_comparison'].items()if row['baseline']!=row['current']}
        report['retained_case_credit']=len(IDS)
        report['execution_count']=report['baseline_observed_case_count']+sum(group.get('counts',{}).values())
        report['new_business_case_credit']=0
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('races',{}))==set(IDS)and all(c['status']=='PASS'for c in group.get('races',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and group.get('counts')=={'PASS':len(IDS)}and baseline.get('counts')=={'PASS':len(IDS)}and group.get('database_remaining')==0 and not group.get('cleanup_failures') and len(copies.COPY_ADMISSIONS)==len(IDS):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for name,case in group.get('races',{}).items():
            print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],CP6_committed_races_only=True,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
