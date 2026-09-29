"""P02 actor facade qualification on disposable CP6 clone; never hosted."""
from pathlib import Path
import hashlib,json,traceback
import psycopg
import cp7_snapshot_bundle as bundle
import cp7_snapshot_cases as cases
import cp6_bf_probe as bf
import cp6_auditor_runner as native
import cp6_auditor_modes as modes
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta

OUT=Path(__file__).resolve().parents[1]/'cp6-proof/t3/CP7_P02_FACADE.json'

def verify(cur):
    value=bf.verified(cur)
    assert cur.execute("select rolcanlogin,rolsuper,rolinherit from pg_roles where rolname='cp7_capture'").fetchone()==(False,False,False)
    assert cur.execute("select count(*) from pg_proc where oid in ('public.erp_cp7_capture_snapshot_v1(uuid,uuid)'::regprocedure,'public.erp_cp7_read_snapshot_v1(uuid,text,text,integer)'::regprocedure) and pg_get_userbyid(proowner)='cp7_capture'").fetchone()[0]==2
    assert cur.execute("select provolatile from pg_proc where oid='cp7_private.capture_sources(uuid,boolean)'::regprocedure").fetchone()[0]=='s'
    return dict(value,cp7_bundle_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())

def run():
    report=dict(label='CP7_P02_FACADE_FAMILY',status='INCOMPLETE',production_go=False,independent_acceptance=False,
        scope='ONE_ROOT_SIX_SOURCE_DOMAINS_CURRENT_ONLY',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            bf.verified(cur);before=package.boundary.snapshot(cur);public_before=native.public_state(cur);conn.rollback()
            cur.execute(bundle.bundle(),prepare=False);conn.commit();installed=True;verify(cur);conn.rollback()
        initial_advisors=advisors(package.boundary.PG)
        # Compare with pristine CP6 after cleanup below, preserving every finding.
        report['native']=native.strict_group('CP7_P02_FACADE_NATIVE',cases.cases,verify)
        report['races']=modes.run_races(cases,verify,'cp7_p02')
        report['http']=modes.run_http(cases,verify,'cp7_p02')
        report['advisors_with_cp7']=initial_advisors
    except Exception as e:
        report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                cur.execute('drop owned by cp7_capture cascade;drop role cp7_capture',prepare=False);conn.commit()
                report['cp6_restored']=package.boundary.snapshot(cur)==before and native.public_state(cur)==public_before
                conn.rollback();bf.verified(cur);conn.rollback()
            baseline=advisors(package.boundary.PG)
            report['advisor_delta']=advisor_delta(baseline,report.get('advisors_with_cp7',baseline))
            delta=report['advisor_delta']
            report['advisor_gate']=delta['status']=='NO_NEW_FINDINGS' or (delta['status']=='REVIEW_REQUIRED' and all(
                (f.get('name'),f.get('level'),(f.get('metadata') or {}).get('schema'))==('rls_enabled_no_policy','INFO','cp7_private')
                for f in delta.get('added',[])))
        groups=[report.get(k,{}) for k in ('native','races','http')]
        ok=not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and all(
            v.get('status') in ('PASS','RUN_COMPLETE') and set(v.get('counts',{}))=={'PASS'} and v['counts']['PASS']>0
            and v.get('database_remaining',0)==0 for v in groups)
        report['status']='PASS' if ok else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps(dict(cp7_p02_facade={k:report.get(k) for k in ('status','source_sha256','cp6_restored','advisor_gate','error')},
            groups={k:{n:v.get(n) for n in ('status','counts','error','database_remaining')} for k,v in report.items() if k in ('native','races','http')}),default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)

if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
