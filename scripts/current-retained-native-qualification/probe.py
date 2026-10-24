"""Unique retained Native controls on the current A/B installation.

The latest full A source admission and all declared B/correction hashes are
checked before DB. 153 retained Native cases, strict rollback and full22 inverse;
no hosted effects, real-Auth claim, factory-scale claim or audit acceptance.
"""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys,traceback
from contextlib import contextmanager
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_p21_current_chain_rehearsal_probe as chain
from cp7_ab_bounded_chain import composition as product
import cp7_ab_ui_admission as current_admission
import cp7_current_installation as installation
import importlib.util
_spec=importlib.util.spec_from_file_location("current_retained_native_cases",HERE/"cases.py")
business=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(business)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
IDS=business.IDS
LABEL='CP7_CURRENT_RETAINED_NATIVE153'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None


def admitted():
    previous,_=current_admission.admitted()
    guard_path=REPO/'scripts/cp7_customer_credit/integration/source_triggers/trigger_guard.py'
    spec=importlib.util.spec_from_file_location('current_owner_trigger_guard',guard_path)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.declarations(REPO)
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CURRENT_RETAINED_NATIVE_SOURCE_CHANGED',path)
    assert pins['case_ids']==list(IDS)and len(IDS)==153
    expected=json.loads((HERE/'EXPECTED.json').read_text())
    assert expected['count']==153 and expected['case_ids']==list(IDS)
    assert expected['historical_native_entries']==180 and expected['duplicates']==27
    # Some unchanged factories import helpers lazily while listing cases.
    # Enumerate without a cursor before checking the actually loaded bytes.
    business.enumerate_cases(None,business.date(2026,10,24))
    imported=[]
    for entry in pins['loaded_local_modules']:
        module=sys.modules.get(entry['module'])
        assert module is not None and getattr(module,'__file__',None),entry
        actual=sha256(Path(module.__file__).read_bytes()).hexdigest()
        assert actual==entry['sha256']==pins['files'][entry['path']],entry['module']
        imported.append(entry['module'])
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    return dict(actual_loaded_modules_verified=imported,qualified_A_predecessor=previous,complete_AB_product=product.sources(),current_installation=installation.sources(),qualification=pins)


def cases(cur,today):
    result=business.cases(cur,today)
    assert tuple(key for key,_ in result)==IDS
    return result


def verify(cur):
    if STATE is None:raise ValueError('CURRENT_RETAINED_NATIVE_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return installation.verify(cur,STATE)


@contextmanager
def keep_group_originals():
    old=native.r1.OUT
    native.r1.OUT=OUT.parent/'strict-groups'
    try:yield
    finally:native.r1.OUT=old


def run():
    global STATE
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,real_Auth_browser_claim=False,factory3600_claim=False,
        unique_retained_native_only=True,production_go=False,independent_acceptance=False)
    installed=False
    try:
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
        with keep_group_originals(),exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison']=catalog
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
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
        report['strict_group_originals']=[dict(path=str(p.relative_to(OUT.parent)),bytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())for p in sorted((OUT.parent/'strict-groups').glob('*.json'))]
        report['seed_prerequisite_preparation']=business.FIXTURE
        report['historical_native_entries']=180
        report['identical_inherited_entries_not_reexecuted']=27
        report['non_native_mode_entries_not_executed']=106
        report['new_business_case_credit']=0
        group=report.get('native',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)and all(c['status']=='PASS'for c in group.get('cases',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and group.get('counts')=={'PASS':len(IDS)}:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for name,case in group.get('cases',{}).items():
            print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],unique_retained_native_only=True,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
