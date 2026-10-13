"""Real four-mode execution with independent, declared date/failure injection at the audit fixture boundary."""
from pathlib import Path
from datetime import timedelta
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlparse
import sys, os, json, traceback, subprocess, copy
PRODUCT=Path.cwd().parent/'auditor'
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(PRODUCT/'scripts'))
import psycopg
import cp7_p21_full_rehearsal_probe as composition
import cp6_auditor_runner as native
import cp6_auditor_modes as modes
import cp6_auditor_business_day as bd
import cp6_t3_package_run as package
OUT=PRODUCT/'cp6-proof/t3/ASTRA_ASF_REAL_MODES.json'
report=dict(status='INCOMPLETE',product_sha='7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2',production_go=False,
    evidence_origin='INDEPENDENT_TOOL_RUNTIME',oracle_origin='ASTRA_CONTRACT',fixture_origin='ASTRA_SYNTHETIC_DATE_AND_FAILURE_WITH_REAL_TRANSPORT',cases=[])
def save():OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
def row(status,evidence):
    r=dict(status=status,transport=evidence,expected_total_cents=10000,observed_total_cents=10000 if status=='PASS' else 10001,synthetic_failure=status!='PASS')
    if status!='PASS':r['error']='ASTRA_INJECTED_DATE_INDEPENDENT_'+status
    return r
def statuses(kind):return ['FAIL','COUNTEREXAMPLE','INCOMPLETE','PASS'] if kind=='negative' else ['PASS']
def one_mode(mode,kind):
    state=dict(attempts=0)
    actual_day=bd.wib_day;actual_subprocess_run=subprocess.run
    def shifted_day(cur):
        real=actual_day(cur)
        return real+timedelta(days=1) if state['attempts']==1 else real
    def start():state['attempts']+=1
    def native_factory(cur,today):
        start()
        def op(status):
            got=cur.execute('select 10000::numeric,10001::numeric,pg_backend_pid()').fetchone()
            assert got[0]==10000 and got[1]==10001
            return row(status,dict(mode='SAVEPOINT',backend_pid=got[2],sql_executed=True))
        return [(f'ASFM_{mode}_{kind}_{s}',lambda s=s:op(s)) for s in statuses(kind)]
    def race_factory(tools,today):
        start()
        def op(status):
            barrier=Barrier(2)
            def session():
                with tools.connect() as conn,conn.cursor() as cur:
                    pid=cur.execute('select pg_backend_pid()').fetchone()[0]
                    barrier.wait(timeout=20)
                    pair=cur.execute('select 10000::numeric,10001::numeric').fetchone()
                    assert pair==(10000,10001)
                    conn.rollback();return pid
            with ThreadPoolExecutor(max_workers=2) as pool:
                fs=[pool.submit(session) for _ in range(2)];pids=[f.result(timeout=30) for f in fs]
            assert len(set(pids))==2
            return row(status,dict(mode='RACES',concurrent_backend_pids=pids))
        return [(f'ASFM_{mode}_{kind}_{s}',lambda s=s:op(s)) for s in statuses(kind)]
    def http_factory(http,today):
        start()
        def op(status):
            user=http.login('OWNER','astra-asfm-'+status.lower())
            result=user.rpc('erp_get_my_access_v1')
            assert result['status']==200,dict(error='REAL_RPC_FAILED',http_status=result['status'])
            return row(status,dict(mode='HTTP',real_auth=True,rpc='erp_get_my_access_v1',http_status=result['status']))
        return [(f'ASFM_{mode}_{kind}_{s}',lambda s=s:op(s)) for s in statuses(kind)]
    def with_host_fixture(args,*a,**kw):
        if args==['node','scripts/cp6_auditor_browser_host.mjs']:
            start();env=dict(kw['env'])
            if state['attempts']==1:
                from datetime import date
                env['AUDITOR_BROWSER_TODAY']=str(date.fromisoformat(env['AUDITOR_BROWSER_TODAY'])-timedelta(days=1))
            env['ASTRA_ROLLOVER_KIND']=kind;env['ASTRA_ROLLOVER_ATTEMPT']=str(state['attempts'])
            kw['env']=env
        return actual_subprocess_run(args,*a,**kw)
    try:
        if mode!='browser':bd.wib_day=shifted_day
        if mode=='savepoint':result=native.strict_group('ASTRA_ASFM_'+kind.upper(),native_factory,composition.verify)
        elif mode=='race':result=modes.run_races(SimpleNamespace(races=race_factory),composition.verify,'astra_asfm_'+kind)
        elif mode=='http':result=modes.run_http(SimpleNamespace(http_cases=http_factory),composition.verify,'astra_asfm_'+kind)
        else:
            subprocess.run=with_host_fixture
            result=modes.run_browser(ROOT/'asf_browser.mjs',composition.verify,'astra_asfm_'+kind)
    finally:bd.wib_day=actual_day;subprocess.run=actual_subprocess_run
    key='races' if mode=='race' else 'cases'
    final=result.get(key,{})
    expected=[f'ASFM_{mode}_{kind}_{s}' for s in statuses(kind)]
    clean=lambda r:not r.get('error') and not r.get('missing') and not r.get('database_remaining') and not r.get('cleanup_failures') and r.get('complete_boundary_restored',True) and all(not v.get('harness_check_failed') and not v.get('session_leaks') for v in r.get(key,{}).values())
    ok=list(final)==expected and clean(result)
    if kind=='negative':
        ok=ok and state['attempts']==1 and not result.get('business_day_retried') and [r['status'] for r in final.values()]==['FAIL','COUNTEREXAMPLE','INCOMPLETE','INCOMPLETE']
        ok=ok and all(r.get('business_day_rollover') for r in final.values())
        ok=ok and all(final[f'ASFM_{mode}_{kind}_{s}'].get('error')=='ASTRA_INJECTED_DATE_INDEPENDENT_'+s for s in statuses(kind) if s!='PASS')
    else:
        first=result.get('business_day_first_attempt',{});first_rows=first.get(key,{})
        ok=ok and state['attempts']==2 and result.get('business_day_retried') is True and list(first_rows)==expected and clean(first)
        ok=ok and all(r['status']=='PASS' and not r.get('business_day_rollover') for r in final.values()) and all(r['status']=='INCOMPLETE' and r.get('status_before_rollover')=='PASS' and r.get('error')=='AUDITOR_BUSINESS_DAY_ROLLOVER' for r in first_rows.values())
    result_row=dict(id='ASF-MODE-'+mode.upper()+'-'+kind.upper(),status='PASS' if ok else 'COUNTEREXAMPLE',attempts=state['attempts'],expected_ids=expected,result=result)
    report['cases'].append(result_row);save()
    print(json.dumps({k:result_row[k] for k in ['id','status','attempts']},default=str),flush=True)

def run():
    installed=False
    try:
        for url in (package.boundary.ADMIN,package.boundary.PRIMARY_ADMIN):assert urlparse(url).hostname in ('127.0.0.1','localhost','::1')
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            composition.p09.wip.policy.bf.verified(cur)
            before=package.boundary.snapshot(cur);public_before=composition.f05.public_state(cur);functions_before=composition.p09.functions(cur);conn.rollback()
            originals,install=composition.install(cur);conn.commit();installed=True
            report['install']=install;report['verify']=composition.verify(cur);conn.rollback();save()
        for mode in ('savepoint','race','http','browser'):
            for kind in ('negative','positive'):one_mode(mode,kind)
    except Exception as e:report.update(error=str(e),traceback=traceback.format_exc());save()
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                    composition.uninstall(cur,originals);conn.commit()
                    report['restore']=dict(boundary=package.boundary.snapshot(cur)==before,public=composition.f05.public_state(cur)==public_before,functions=composition.p09.functions(cur)==functions_before)
                    conn.rollback();composition.p09.wip.policy.bf.verified(cur);conn.rollback()
            except Exception as e:report.update(restore_error=str(e),restore_traceback=traceback.format_exc())
        report['counts']={s:sum(r['status']==s for r in report['cases']) for s in ('PASS','COUNTEREXAMPLE')}
        report['status']='PASS' if len(report['cases'])==8 and report['counts']['PASS']==8 and not report.get('error') and bool(report.get('restore')) and all(report['restore'].values()) else 'INCOMPLETE'
        save();print(json.dumps({k:report.get(k) for k in ('status','counts','error','restore','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)
if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
