"""Native-linked payroll prerequisite for thirteen unchanged work-source race oracles."""
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
import cp7_current_analog_installation as installation
import importlib.util
from types import SimpleNamespace
import cp6_auditor_modes as modes
_spec=importlib.util.spec_from_file_location("current_work_payroll_race_cases",HERE/"cases.py")
business=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(business)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
_spec=importlib.util.spec_from_file_location("analog_installation_boundary",REPO/"scripts/current-analog-native-fixture-qualification/probe.py")
analog_boundary=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(analog_boundary)
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
_copy_spec=importlib.util.spec_from_file_location('current_cp6_race_authority',REPO/'scripts/ow04-payment-current-races-qualification/copy_authority.py')
copies=importlib.util.module_from_spec(_copy_spec);_copy_spec.loader.exec_module(copies)
IDS=business.IDS
LABEL='CP7_CURRENT_WORK_PAYROLL_RACE13'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None


def admitted():
    spec=importlib.util.spec_from_file_location('qualified_current_return_installation',REPO/'scripts/current-analog-native-fixture-qualification/probe.py')
    predecessor=importlib.util.module_from_spec(spec);spec.loader.exec_module(predecessor)
    previous=predecessor.admitted()
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CURRENT_RETURN_RACE_SOURCE_CHANGED',path)
    assert pins['case_ids']==list(IDS)and len(IDS)==13
    transforms=business.verify_transforms()
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            actual=Path(module.__file__);key='scripts/'+actual.name
            assert sha256(actual.read_bytes()).hexdigest()==pins['files'][key],('WORK_RACE_LOADED_SOURCE_CHANGED',name)
            loaded.append(name)
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw);assert actual['status']==proof['status']and actual['cp6_restored'],variable
        if variable=='COMPOSED_ANALOG_ORIGINAL_REPORT':
            assert actual['required_steps_pass']and actual['baseline_advisors_equal']
            assert actual['source_declaration']['current_installation']==installation.sources()
        else:
            assert actual['baseline']['counts']=={'PASS':23,'INCOMPLETE':13}
            assert actual['races']['counts']=={'PASS':22,'INCOMPLETE':14}
            for group in('baseline','races'):
                for legacy in business.LEGACY_IDS:
                    import ast
                    case=actual[group]['races'][legacy];assert case['status']=='INCOMPLETE'
                    confidence=ast.literal_eval(case['error'])['data_confidence']
                    assert confidence['status']=='BLOCKED'
                    assert [r['code']for r in confidence['blockers']]==['PAYROLL_WORK_UNCOVERED']
                    assert all(r['severity']=='INFO'for r in confidence['info'])
        originals[variable]=dict(status=actual['status'],**{k:v for k,v in proof.items()if k!='status'})

    return dict(qualified_composed_predecessor=previous,current_installation=installation.sources(),qualification=pins,verified_transforms=transforms,actual_originals_verified=originals,actual_loaded_modules_verified=loaded)


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
        report['baseline']=modes.run_races(business,p09.wip.policy.bf.verified,'current_work_payroll_baseline13')
        report['baseline_copy_catalog_admissions']=list(copies.COPY_ADMISSIONS)
        assert report['baseline']['database_remaining']==0,'CP6_RACE_BASELINE_COPY_NOT_REMOVED'
        copies.COPY_ADMISSIONS.clear()
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            try:
                report['install_boundary_lock']=analog_boundary.acquire_boundary(cur)
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
        report['races']=modes.run_races(business,verify,'current_work_payroll_13')
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
                    report['inverse_boundary_lock']=analog_boundary.acquire_boundary(cur)
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
        report['retained_case_credit']=0
        report['explicit_successor_case_count']=13
        report['original_legacy_results_relabelled']=False
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
