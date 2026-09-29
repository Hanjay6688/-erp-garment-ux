"""Independent F02 execution; product source frozen, own and writer cases separated by ID."""
import probe
import os
from types import SimpleNamespace
from collections import Counter
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
OUT=probe.ROOT/'cp6-proof/t3/CP7_F02_INDEPENDENT.json'
def verify(cur):
    value=policy.verify(cur)
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_wip' and (pg_get_userbyid(p.proowner)<>'cp7_capture' or p.prosecdef or p.provolatile<>case when p.proname in ('capture_cutting_sources','capture_other_sources','capture_production_sources') then 's' when p.proname in ('capture','serve','capture_production','serve_production') then 'v' else 'i' end)").fetchone()[0]==0
    return dict(value,cp7_p04_bundle_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
def run():
    report=dict(label='CP7_F02_INDEPENDENT',status='INCOMPLETE',production_go=False,independent_acceptance=False,
      scope='F02_P03_P04_FROZEN_17e8540',candidate='17e85404c9c5f088875099d7875be6342ca6b266',blind_audit=False,source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=native.public_state(cur);conn.rollback()
            cur.execute(bundle.bundle(),prepare=False);conn.commit();installed=True;verify(cur);conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        report['native']=native.strict_group('AUD_F02_NATIVE',probe.cases,verify)
        if os.environ.get('F02_TARGETED')!='1':
            report['races']=modes.run_races(probe,verify,'aud_f02')
            report['http']=modes.run_http(probe,verify,'aud_f02')
        else:
            report['preserved_prior_run']=36526434075
            report['targeted_only']=True
        report['http_production']=modes.run_http(SimpleNamespace(http_cases=probe.http_production_cases),verify,'aud_f02_production')
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
        groups=[report.get(k,{}) for k in (('native','http_production') if os.environ.get('F02_TARGETED')=='1' else ('native','races','http','http_production'))]
        all_rows={}
        for group in groups:
            for key in ('cases','races'):
                all_rows.update(group.get(key,{}) if isinstance(group.get(key,{}),dict) else {})
        report['independent_counts']=dict(Counter(v['status'] for k,v in all_rows.items() if k.startswith('AUD_F02_')))
        report['writer_rerun_counts']=dict(Counter(v['status'] for k,v in all_rows.items() if k.startswith('WRITER_RERUN_')))
        complete=not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and all(r.get('status') in ('PASS','RUN_COMPLETE','COUNTEREXAMPLE') and not r.get('counts',{}).get('INCOMPLETE') and r.get('database_remaining',0)==0 for r in groups)
        counts=Counter(v['status'] for v in all_rows.values())
        report['status']=('COUNTEREXAMPLE' if counts.get('COUNTEREXAMPLE') or counts.get('FAIL') else 'PASS') if complete and all_rows else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k) for k in ('label','status','source_sha256','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)
if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
