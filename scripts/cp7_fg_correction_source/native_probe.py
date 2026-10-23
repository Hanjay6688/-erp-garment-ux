"""OW-08b FG-correction Native qualification on a disposable aligned CP6 copy; no hosted or production effect.

The predecessor is the kasbon stage (cp7_kasbon_source). Admission checks its qualified Native4 original (bytes, sha256,
PASS 4/4, restore and advisor gates, declared source equal to scripts/cp7_kasbon_source/SOURCE.json), and through the
kasbon probe chain the OW06 Native10 original it was built on.
"""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
from cp7_kasbon_source import native_probe as setup
from cp7_fg_correction_source import composition as product,cases as business
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog
control=setup.control
previous,native,package,core,p09=setup.previous,setup.native,setup.package,setup.core,setup.p09
IDS=business.IDS
LABEL='CP7_OW08B_FG_CORRECTION_NATIVE9'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None


def admitted():
    old=setup.admitted()
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('OW08B_FG_SOURCE_CHANGED',path)
    # The OW06 Native10 original stays admitted through the kasbon probe chain, exactly as before.
    ow06=pins['ow06_native_original']
    assert ow06==old['OW08b_kasbon_declared_source']['ow06_native_original']and ow06==old['qualified_predecessor']
    # The immediate predecessor's own qualified original: kasbon Native4 (run 39847032024, artifact 12456785458).
    proof=pins['predecessor_original']
    raw=Path(os.environ['OW08B_KASBON_NATIVE4_ORIGINAL_REPORT']).read_bytes()
    assert proof['name']=='CP7_OW08B_KASBON_SOURCE_NATIVE4.json'and len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['label']=='CP7_OW08B_KASBON_SOURCE_NATIVE4'and actual['status']=='PASS'and actual['native']['counts']=={'PASS':4}
    assert actual['required_case_ids_pass']and actual['cp6_restored']and actual['advisor_gate']
    assert actual['source_declaration']['OW08b_kasbon_declared_source']==old['OW08b_kasbon_declared_source']
    assert pins['case_ids']==list(IDS)and len(IDS)==9
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    return dict(qualified_predecessor=proof,ow06_native_original=ow06,
        predecessor_source_declaration=old,OW08b_fg_declared_source=pins)


def cases(cur,today):
    business.ORIGINALS=STATE['originals'];business.AS_OWNER=product.function_ddl;business.AS_POSTGRES=product.as_owner;business.BEFORE=STATE['before']
    result=business.cases(cur,today)
    assert tuple(key for key,_ in result)==IDS
    return result


def verify(cur):
    if STATE is None:raise ValueError('OW08B_FG_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return product.verify(cur,STATE)


def run():
    global STATE
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,
        OW08b_complete=False,production_go=False,independent_acceptance=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            try:
                STATE=product.install(cur)
            except Exception:
                # Keep the exact predecessor definitions for diagnosis of a changed anchor.
                report['predecessor_definitions_on_install_failure']=dict(product.CAPTURED)
                raise
            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison']=catalog
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_preuse_removal']=product.rollback_preuse(cur,STATE)
                    conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
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
    return dict(status=report['status'],OW08b_complete=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
