"""P04 kernel qualification; adapter and public snapshot integration remain separate."""
from pathlib import Path
import hashlib,json,traceback
import psycopg
import cp7_wip_bundle as bundle
import cp7_wip_cases as cases
import cp7_wip_source_cases as source_cases
import cp7_wip_production_cases as production_cases
import cp6_auditor_modes as modes
import cp7_p03_identity_probe as policy
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=Path(__file__).resolve().parents[1]/'cp6-proof/t3/CP7_P04_KERNEL.json'
def verify(cur):
    value=policy.verify(cur)
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_wip' and (pg_get_userbyid(p.proowner)<>'cp7_capture' or p.prosecdef or p.provolatile<>case when p.proname in ('capture_cutting_sources','capture_other_sources','capture_production_sources') then 's' when p.proname in ('capture','serve','capture_production','serve_production') then 'v' else 'i' end)").fetchone()[0]==0
    return dict(value,cp7_p04_bundle_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
def run():
    report=dict(label='CP7_P04_NORMALIZED_KERNEL',status='INCOMPLETE',production_go=False,independent_acceptance=False,
      scope='KERNELS_AND_EXPLICIT_CUTTING_OPENING_UNSOURCED_ORIGINS',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=native.public_state(cur);conn.rollback()
            cur.execute(bundle.bundle(),prepare=False);conn.commit();installed=True;verify(cur);conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        report['native']=native.strict_group('CP7_P04_KERNEL',cases.cases,verify)
        report['source_smoke']=native.strict_group('CP7_P04_SOURCE_SMOKE',source_cases.smoke,verify)
        assert report['source_smoke']['status']=='PASS','P04_SOURCE_FIXTURE_SMOKE_INCOMPLETE'
        report['source']=native.strict_group('CP7_P04_SOURCE_NATIVE',source_cases.cases,verify)
        report['races']=modes.run_races(source_cases,verify,'cp7_p04')
        report['http']=modes.run_http(source_cases,verify,'cp7_p04')
        report['production']=native.strict_group('CP7_P04_PRODUCTION_NATIVE',production_cases.cases,verify)
        report['production_races']=modes.run_races(production_cases,verify,'cp7_p04_production')
        report['production_http']=modes.run_http(production_cases,verify,'cp7_p04_production')
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                cur.execute('drop owned by cp7_policy cascade;drop role cp7_policy;drop owned by cp7_capture cascade;drop role cp7_capture',prepare=False);conn.commit()
                report['cp6_restored']=package.boundary.snapshot(cur)==before and native.public_state(cur)==public_before
                conn.rollback();policy.bf.verified(cur);conn.rollback()
            report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}))
            d=report['advisor_delta'];report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or (d['status']=='REVIEW_REQUIRED' and all(
             f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and (f.get('metadata') or {}).get('schema') in ('cp7_private','cp7_identity','cp7_wip') for f in d.get('added',[])))
        groups=[report.get(k,{}) for k in ('native','source_smoke','source','races','http','production','production_races','production_http')]
        report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and all(r.get('status') in ('PASS','RUN_COMPLETE') and set(r.get('counts',{}))=={'PASS'} and r['counts']['PASS']>0 and r.get('database_remaining',0)==0 for r in groups) else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k) for k in ('label','status','source_sha256','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)
if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
