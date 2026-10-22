"""Initial OW05 Native qualification on a local, disposable aligned CP6 copy."""
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO/'scripts'), str(REPO/'scripts/ow04-consumer-closure-qualification')]
import native32_probe as framework
import psycopg
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors, advisor_delta
from cp7_contractor_correction import composition as product, native_cases as business

control = framework.control
previous, native, package, core, p09 = framework.previous, framework.native, framework.package, framework.core, framework.p09
LABEL = 'CP7_OW05_EXTENDED_NATIVE14'
OUT = REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE = None


def admitted():
    raw = Path(os.environ['OW04_NATIVE32_ORIGINAL_REPORT']).read_bytes()
    assert len(raw)==8166263 and sha256(raw).hexdigest()=='9a66b07743087e107e3d7d9298d9e517b786077f848cee79ffc326a8246c3a50'
    old = json.loads(raw)
    assert old['status']=='PASS' and old['native']['counts']=={'PASS':32}
    assert old['current_financial_sources']==product.predecessor.sources()
    pins = json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest, ('OW05_DECLARED_SOURCE_CHANGED',path)
    assert pins['case_ids']==list(business.IDS) and len(business.IDS)==14
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--','scripts/cp7_contractor_correction'],text=True).strip()
    return dict(predecessor_Native32_financial_sources_equal=True, Native32_rerun=False,
                raw_sha256=sha256(raw).hexdigest(), declared_source=pins)


def verify(cur):
    if STATE is None:
        raise ValueError('OW05_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE. It is removed only
    # during catalog verification, not projected into product permissions.
    with control.product_catalog(cur):
        return product.verify(cur, STATE)


def run():
    global STATE
    report = dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(business.IDS),required_case_ids=list(business.IDS),formal_CP7C_started=False,
        OW05_complete=False,production_go=False,independent_acceptance=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            STATE=product.install(cur)
            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,business.cases,verify)
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
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(business.IDS) and all(c['status']=='PASS'for c in group.get('cases',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and group.get('counts')=={'PASS':len(business.IDS)}:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],OW05_complete=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
