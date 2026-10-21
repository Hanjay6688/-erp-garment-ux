"""Real browser4, exact active/historical UI and qualified atomic backend; copied DB only."""
from pathlib import Path
import hashlib,json,os,shutil,sys,tempfile,traceback
if len(sys.argv)>1:raise SystemExit('OW04 browser entry accepts no arguments')
import transport_probe as transport
import browser_sources
import full_backend
core=transport.core
p09,package,credit=core.p09,core.package,core.credit
modes=transport.modes
psycopg=transport.psycopg
OUT=p09.bundle.ROOT/'cp6-proof/t3/CP7_OW04_BROWSER.json'
EXPECTED_BYTES=Path(__file__).with_name('BROWSER_EXPECTED.json').read_bytes()
assert hashlib.sha256(EXPECTED_BYTES).hexdigest()=='498f1943b91704d916268d0fe0a3f5caa1924199484de512626b72847170424f'
IDS=tuple(c['id']for c in json.loads(EXPECTED_BYTES)['cases'])
assert len(IDS)==len(set(IDS))==4
def run():
    assert os.environ.get('AUDITOR_UI_MODE')=='ENTENG','OW04_BROWSER_ENTENG_LOOPBACK_BUILD_REQUIRED'
    reused=transport.qualified_core()
    assert reused['native_case_count']==73,'OW04_BROWSER_ACTUAL_FULL_NATIVE73_REQUIRED'
    source,_=browser_sources.inspect_sources()
    report=dict(label='CP7_OW04_BROWSER',status='INCOMPLETE',expected_case_count=4,
      required_case_ids=list(IDS),candidate_commit=transport.git('rev-parse','HEAD'),
      core_directory_tree=reused['core_directory_tree'],native_probe_blob=reused['native_probe_blob'],
      reused_native_binding=reused,predeclared_case_sha256=hashlib.sha256(EXPECTED_BYTES).hexdigest(),
      implementation_sha256={n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest()
        for n in('browser_probe.py','browser_sources.py','browser_fixture.py','browser_cases.mjs')},
      frontend=source,scope=('REAL_AUTH_ENTENG_LOOPBACK_ACTIVE_PRODUCT_UI_INITIAL_SETTLEMENT_BROWSER'
        if 'active_UI_sha256'in source else'REAL_AUTH_ENTENG_LOOPBACK_EXACT_ESCROW_INITIAL_SETTLEMENT_BROWSER'),
      production_go=False,independent_acceptance=False,feature_complete=False)
    installed=False;originals={}
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=core.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions);conn.rollback()
            originals=full_backend.install(cur,report)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            report['integrated_source_verification']=full_backend.verify(cur)
            conn.commit();installed=True;conn.rollback()
        report['advisors_with_cp7']=transport.advisors(package.boundary.PG)
        host_before=set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))
        with browser_sources.applied_sources(report['frontend']):
            report['browser']=modes.run_browser(Path(__file__).with_name('browser_cases.mjs'),full_backend.verify,'cp7_ow04_settlement_browser')
        hosts=[]
        for folder in sorted(set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))-host_before):
            file=folder/'BROWSER.json'
            if not file.is_file():continue
            value=json.loads(file.read_bytes());destination=OUT.parent/('OW04_BROWSER_HOST_'+str(len(hosts)+1)+'.json')
            shutil.copyfile(file,destination)
            hosts.append(dict(receipt=destination.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),report=value))
        report['actual_browser_hosts']=hosts
        final=next((h['report']for h in reversed(hosts)if set(h['report'].get('cases',{}))==set(IDS)
          and all(r.get('status')=='PASS'for r in h['report']['cases'].values())),None)
        assert final and final.get('ui_mode')=='ENTENG'and final.get('enteng_requests_answered_by_loopback',0)>0 \
          and final.get('real_auth')is True and final.get('product_responses_mocked')is False,'OW04_BROWSER_ACTUAL_ENTENG_HOST_PROOF_REQUIRED'
        report['actual_Enteng_loopback_host_proven']=True
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    full_backend.uninstall(cur,originals)
                    conn.commit()
                    report['cp6_restored']=core.restore_state.prove(cur,before,package.boundary.snapshot,core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=transport.advisor_delta(transport.advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('browser',{});rows=group.get('cases',{})
        report['observed_case_count']=len(rows)
        if not report.get('error')and report.get('cp6_restored')is True and report.get('advisor_gate')is True \
            and group.get('status')in('PASS','RUN_COMPLETE')and group.get('counts')=={'PASS':4} \
            and set(rows)==set(IDS)and all(r.get('status')=='PASS'for r in rows.values()) \
            and group.get('real_auth')is True and group.get('host_exit')==0 and group.get('host_status')=='RUN_COMPLETE' \
            and group.get('database_remaining',1)==0 and(group.get('auth_counts')or{}).get('restored')is True \
            and not group.get('cleanup_failures')and not group.get('auth_cleanup_failures') \
            and report.get('actual_Enteng_loopback_host_proven')is True \
            and report['frontend'].get('frontend_source_restored')is True:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','candidate_commit','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','traceback','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False,feature_complete=False)
if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
