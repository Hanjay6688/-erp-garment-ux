"""Independent auditor runner. Product source is a separate immutable checkout."""
from pathlib import Path
import sys,os,json,hashlib,traceback
from urllib.parse import urlparse
PRODUCT=Path.cwd().parent/'auditor'
sys.path.insert(0,str(PRODUCT/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import psycopg
import cp7_p21_full_rehearsal_probe as composition
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp7_catalog_state import exact_public_catalog
import cases_cont_money as cases_stage
OUT=PRODUCT/'cp6-proof/t3/ASTRA_P20_INDEPENDENT_CONT_MONEY.json'

def run():
    report=dict(status='INCOMPLETE',product_sha='2e605bb7d9b6b7903919b8df2be1443f1740140b',production_go=False,
       independent_acceptance=False,expected_cases=4,evidence_origin='INDEPENDENT_NATIVE_CASE',oracle_origin='ASTRA_CONTRACT',fixture_origin='WRITER_SETUP_UNCHANGED')
    installed=False
    for url in (package.boundary.ADMIN,package.boundary.PRIMARY_ADMIN):
        assert urlparse(url).hostname in ('127.0.0.1','localhost','::1'),'AUDIT_DISPOSABLE_LOOPBACK_ONLY'
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            composition.p09.wip.policy.bf.verified(cur)
            before=package.boundary.snapshot(cur);public_before=composition.f05.public_state(cur);functions_before=composition.p09.functions(cur);conn.rollback()
            originals,install=composition.install(cur);conn.commit();installed=True
            report['install']=install;report['verify']=composition.verify(cur);conn.rollback()
        with exact_public_catalog(native,retain_raw=True) as catalog:
            report['native']=native.strict_group('ASTRA_P20_CONT_MONEY_NATIVE',cases_stage.cases,composition.verify)
        report['catalog_comparison']=catalog
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                    composition.uninstall(cur,originals);conn.commit()
                    report['restore']=dict(boundary=package.boundary.snapshot(cur)==before,public=composition.f05.public_state(cur)==public_before,functions=composition.p09.functions(cur)==functions_before)
                    conn.rollback();composition.p09.wip.policy.bf.verified(cur);conn.rollback()
            except Exception as e:report.update(restore_error=str(e),restore_traceback=traceback.format_exc())
        group=report.get('native',{})
        ok=not report.get('error') and group.get('counts')=={'PASS':report['expected_cases']} and group.get('complete_boundary_restored') and all(report.get('restore',{}).values()) and bool(report.get('restore'))
        report['status']='PASS' if ok else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k) for k in ('status','expected_cases','restore','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)

if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
