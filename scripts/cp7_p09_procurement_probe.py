"""P09 public receipt bridge on a disposable accepted CP6 install; writer proof."""
from pathlib import Path
import hashlib,json,traceback
import psycopg
import cp7_procurement_bundle as bundle
import cp7_procurement_cases as cases
import cp7_p04_wip_probe as wip
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=Path(__file__).resolve().parents[1]/'cp6-proof/t3/CP7_P09_PROCUREMENT.json'

def verify(cur):
    value=wip.verify(cur)
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_procurement' and (p.prosecdef or pg_get_userbyid(p.proowner)<>case when p.proname='command' then 'cp7_procure_write' else 'cp7_procure_read' end or p.proconfig is distinct from array['search_path=\"\"'])").fetchone()[0]==0
    for name,role in [('erp_cp7_get_procurement_v1','cp7_procure_read'),('erp_cp7_get_procurement_options_v1','cp7_procure_read'),('erp_cp7_save_procurement_v1','cp7_procure_write')]:
        assert cur.execute("select p.prosecdef and pg_get_userbyid(p.proowner)=%s and p.proconfig=array['search_path=\"\"'] from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname=%s",(role,name)).fetchone()==(True,)
    return dict(value,cp7_p09_bundle_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())

def run():
    report=dict(label='CP7_P09_RECEIPT_BRIDGE',status='INCOMPLETE',production_go=False,independent_acceptance=False,
      scope='BOUNDED_RECEIPT_DRAFT_POST_LIVE_READ_NO_BROWSER_YET',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            wip.policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=native.public_state(cur);conn.rollback()
            cur.execute(bundle.bundle(),prepare=False);conn.commit();installed=True;verify(cur);conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        report['smoke']=native.strict_group('CP7_P09_SMOKE',cases.smoke,verify)
        assert report['smoke']['status']=='PASS','P09_SMOKE_INCOMPLETE'
        report['native']=native.strict_group('CP7_P09_NATIVE',cases.cases,verify)
        report['races']=modes.run_races(cases,verify,'cp7_p09')
        report['http']=modes.run_http(cases,verify,'cp7_p09')
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                cur.execute('drop owned by cp7_procure_write cascade;drop role cp7_procure_write;drop owned by cp7_procure_read cascade;drop role cp7_procure_read;drop owned by cp7_policy cascade;drop role cp7_policy;drop owned by cp7_capture cascade;drop role cp7_capture',prepare=False);conn.commit()
                report['cp6_restored']=package.boundary.snapshot(cur)==before and native.public_state(cur)==public_before
                conn.rollback();wip.policy.bf.verified(cur);conn.rollback()
            report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}))
            d=report['advisor_delta'];report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or (d['status']=='REVIEW_REQUIRED' and all(
             f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and (f.get('metadata') or {}).get('schema') in ('cp7_private','cp7_identity','cp7_wip') for f in d.get('added',[])))
        groups=[report.get(k,{}) for k in ('smoke','native','races','http')]
        report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and all(r.get('status') in ('PASS','RUN_COMPLETE') and set(r.get('counts',{}))=={'PASS'} and r['counts']['PASS']>0 and r.get('database_remaining',0)==0 for r in groups) else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k) for k in ('label','status','source_sha256','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)

if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
