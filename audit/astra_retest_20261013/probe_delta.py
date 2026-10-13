"""Own delta checks, real disposable runtime; all counterexamples remain red."""
from pathlib import Path
from urllib.parse import urlparse
import sys,os,json,traceback
PRODUCT=Path.cwd().parent/'auditor'
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(PRODUCT/'scripts'),str(ROOT)]
import psycopg
import cp7_p21_full_rehearsal_probe as composition
import cp6_auditor_runner as native
import cp6_auditor_modes as modes
import cp6_t3_package_run as package
import cases_delta as cases
OUT=PRODUCT/'cp6-proof/t3/ASTRA_DELTA_OWN.json'
def run():
    report=dict(status='INCOMPLETE',product_sha='7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2',production_go=False,expected_cases=14,evidence_origin='INDEPENDENT_NATIVE_CASE',oracle_origin='ASTRA_CONTRACT',fixture_origin='MIXED_OWN_BACKUP_AND_UI_FIXTURES_WITH_WRITER_STAGED_SETUP')
    installed=False
    try:
        for url in (package.boundary.ADMIN,package.boundary.PRIMARY_ADMIN):assert urlparse(url).hostname in ('127.0.0.1','localhost','::1')
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            composition.p09.wip.policy.bf.verified(cur)
            before=package.boundary.snapshot(cur);public_before=composition.f05.public_state(cur);functions_before=composition.p09.functions(cur);conn.rollback()
            originals,install=composition.install(cur);conn.commit();installed=True
            report['install']=install;report['verify']=composition.verify(cur);conn.rollback()
        report['native']=native.strict_group('ASTRA_DELTA_NATIVE',cases.cases,composition.verify)
        report['races']=modes.run_races(cases,composition.verify,'astra_delta')
        report['http']=modes.run_http(cases,composition.verify,'astra_delta')
        os.environ['ASTRA_EVIDENCE_DIR']=str(OUT.parent.resolve())
        report['browser']=modes.run_browser(ROOT/'delta_browser.mjs',composition.verify,'astra_delta')
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                    composition.uninstall(cur,originals);conn.commit()
                    report['restore']=dict(boundary=package.boundary.snapshot(cur)==before,public=composition.f05.public_state(cur)==public_before,functions=composition.p09.functions(cur)==functions_before)
                    conn.rollback();composition.p09.wip.policy.bf.verified(cur);conn.rollback()
            except Exception as e:report.update(restore_error=str(e),restore_traceback=traceback.format_exc())
        expected={'native':3,'races':6,'http':1,'browser':4}
        report['case_verdicts']={k:{i:r['status'] for i,r in report.get(k,{}).get('races' if k=='races' else 'cases',{}).items()} for k in expected}
        good=all(report.get(k,{}).get('counts')=={'PASS':n} and not report[k].get('error') and not report[k].get('database_remaining') and not report[k].get('cleanup_failures') for k,n in expected.items())
        good=good and report.get('native',{}).get('complete_boundary_restored') and all(report.get('restore',{}).values()) and bool(report.get('restore')) and not report.get('error')
        report['status']='PASS' if good else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k) for k in ('status','case_verdicts','error','restore','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)
if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
