"""Four real-Auth OW05 journeys on an exact disposable copy; no product grants."""
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
from cp7_contractor_correction import native_probe as setup
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

business=load('ow05_distinct_real_auth_cases',HERE/'cases.py')
copies=load('ow05_exact_copy_authority',REPO/'scripts/ow04-payment-current-qualification/copy_authority.py')
product,previous,package,core,p09=setup.product,setup.previous,setup.package,setup.core,setup.p09
LABEL='CP7_OW05_REAL_AUTH4'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None

def admitted():
    predecessor=setup.admitted()
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    proof=pins['native_original']
    raw=Path(os.environ['OW05_NATIVE28_ORIGINAL_REPORT']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    old=json.loads(raw)
    assert old['status']=='PASS'and old['native']['counts']=={'PASS':28}and old['required_case_ids_pass']
    assert old['cp6_restored']and old['advisor_gate']
    assert old['source_declaration']['declared_source']==json.loads((REPO/'scripts/cp7_contractor_correction/SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('OW05_AUTH_SOURCE_CHANGED',path)
    assert pins['case_ids']==list(business.IDS)and len(business.IDS)==4
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    return dict(predecessor_source_binding=predecessor,qualifier_source=pins,Native28_rerun_here=False)

def verify(cur):
    if STATE is None:raise ValueError('OW05_AUTH_INSTALLATION_REQUIRED')
    return product.verify(cur,STATE)

def run():
    global STATE
    original=modes.copy_db
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=4,required_case_ids=list(business.IDS),formal_CP7C_started=False,
        OW05_complete=False,production_go=False,independent_acceptance=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback();STATE=product.install(cur)
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        # The old copy helper only names its catalog field installed_catalog.
        # Supply an additional alias to the SAME full current catalog; neither
        # product verification nor any observed member is projected/normalized.
        copies.PRODUCT=SimpleNamespace(catalog=product.predecessor.catalog,verify=product.verify)
        copies.STATE={**STATE,'installed_catalog':STATE['after']}
        copies.ORIGINAL_COPY_DATABASE=original
        modes.copy_db=copies.copy_database
        report['http']=modes.run_http(business,verify,'ow05_real_auth4')
        report['copy_catalog_admissions']=copies.COPY_ADMISSIONS
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc(),copy_catalog_admissions=copies.COPY_ADMISSIONS)
    finally:
        modes.copy_db=original
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_preuse_removal']=product.rollback_preuse(cur,STATE);conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('http',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(business.IDS)and all(c['status']=='PASS'for c in group.get('cases',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass'] \
                and group.get('counts')=={'PASS':4}and not group.get('cleanup_failures')and group.get('database_remaining')==0:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],OW05_complete=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
