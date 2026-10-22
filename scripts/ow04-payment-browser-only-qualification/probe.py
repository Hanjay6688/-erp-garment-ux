"""Actual browser7 synchronization qualification; reuse bound real SQL races6."""
from hashlib import sha256
from pathlib import Path
import gzip,importlib.util,json,lzma,os,shutil,subprocess,sys,tempfile,traceback
sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Current browser/race qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),
 str(REPO/'scripts/ow04-payment-source-qualification'),str(REPO/'scripts/ow04-consumer-race-qualification')]
import source_probe as control
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta
spec=importlib.util.spec_from_file_location('payment_current_copy_authority',REPO/'scripts/ow04-payment-browser-races-qualification/copy_authority.py')
copies=importlib.util.module_from_spec(spec);spec.loader.exec_module(copies)
product,previous,package,core,p09=control.product,control.previous,control.package,control.core,control.p09
LABEL='CP7_OW04_PAYMENT_CURRENT_BROWSER7_SYNC'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['product_sources']==product.sources()
    for path,expected in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==expected,('CURRENT_BROWSER_RACE_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows/cp7-ow04-payment-browser-only.yml'],text=True).splitlines()
    assert set(changed)<=set(source['files'])|{'scripts/ow04-payment-browser-only-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts','src','supabase','tests','.github/workflows/cp7-ow04-payment-browser-only.yml'],text=True).strip()
    binding=json.loads((HERE/'QUALIFIED.json').read_bytes())
    reports={}
    for label,row in binding['reports'].items():
        packed=(REPO/row['file']).read_bytes()
        raw=lzma.decompress(packed)if row['file'].endswith('.xz')else gzip.decompress(packed)
        assert sha256(raw).hexdigest()==row['raw_sha256'];reports[label]=json.loads(raw)
    n,h=reports['native22'],reports['http16']
    assert n['candidate_commit']==binding['native22_candidate']=='e830604509210377f19c24b49c2fe22cc7476b6b'
    assert h['candidate_commit']==binding['http16_candidate']=='365c2df32b95c1f4c1824f4a984c8d18bdee5e36'
    assert h['qualified_Native22_binding']['original_reports']['native22']['raw_sha256']==binding['reports']['native22']['raw_sha256']
    assert n['status']==h['status']=='PASS'
    assert n['native']['counts']=={'PASS':22}and h['http']['counts']=={'PASS':16}
    assert n['source_declaration']['product_sources']==h['actual_financial_sources']==product.sources()
    for report in (n,h):
        assert report['required_case_ids_pass']and report['cp6_restored']and report['advisor_gate']
    assert h['http']['real_auth']and not h['http']['jwt_signed_by_runtime']and not h['http']['test_only_usage_grant']
    assert h['http']['auth_counts']['restored']and h['http']['database_remaining']==0
    assert all(x['all22_groups_equal_original_install']for x in h['copy_catalog_admissions'])
    declaration=json.loads((HERE/'EXPECTED.json').read_bytes())
    assert declaration['browser_count']==len(set(declaration['browser_case_ids']))==7
    r=reports['races6'];race=r['races']
    assert r['candidate_commit']==binding['races6_candidate']==source['base_candidate']=='92c297f2cdc82f107dfa0f079627a09608c3551b'
    assert r['current_financial_sources']==product.sources()and r['cp6_restored']and r['advisor_gate']
    assert r['status']=='INCOMPLETE'and r['browser']['counts']=={'PASS':6,'INCOMPLETE':1}
    assert race['status']=='RUN_COMPLETE'and race['counts']=={'PASS':6}and race['database_remaining']==0
    assert set(race['races'])==set(binding['race_case_ids'])and len(binding['race_case_ids'])==6
    assert all(row['status']=='PASS'for row in race['races'].values())
    assert declaration['retained_actual_SQL_races6']==6
    return binding,declaration


def verify(cur):return product.verify(cur,control.STATE)


def run():
    binding,expected=admitted()
    assert os.environ['AUDITOR_UI_MODE']=='ENTENG'
    report=dict(label=LABEL,status='INCOMPLETE',candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        qualified_actual_Native22_HTTP16_SQLraces6=binding,current_financial_sources=product.sources(),
        expected_browser_case_ids=expected['browser_case_ids'],retained_actual_SQL_races6=True,
        expected_case_count=7,retained_browser4_plus_sourceUI1_actually_rerun=True,
        Native22_HTTP16_SQLraces6_rerun=False,formal_CP7C_started=False,production_go=False,feature_complete=False,hosted=False)
    installed=False;original=modes.copy_db
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback();control.STATE=product.install(cur)
            report['complete_installed_verification']=product.verify(cur,control.STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        copies.PRODUCT=product;copies.STATE=control.STATE;copies.ORIGINAL_COPY_DATABASE=original
        modes.copy_db=copies.copy_database
        before_hosts=set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))
        report['browser']=modes.run_browser(HERE/'all_browser_cases.mjs',verify,'ow04_payment_current7_sync')
        hosts=[]
        for directory in sorted(set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))-before_hosts):
            file=directory/'BROWSER.json'
            if file.is_file():
                target=OUT.parent/('PAYMENT_CURRENT_HOST_'+str(len(hosts))+'.json')
                shutil.copyfile(file,target);hosts.append(dict(file=target.name,raw_sha256=sha256(target.read_bytes()).hexdigest(),report=json.loads(target.read_bytes())))
        report['actual_product_browser_hosts']=hosts
        report['actual_product_loopback_proven']=any(h['report'].get('ui_mode')=='ENTENG'
            and h['report'].get('real_auth')is True and h['report'].get('product_responses_mocked')is False
            and h['report'].get('enteng_requests_answered_by_loopback',0)>0
            and set(h['report'].get('cases',{}))==set(expected['browser_case_ids'])
            and all(row['status']=='PASS'for row in h['report']['cases'].values())for h in hosts)
        report['copy_catalog_admissions']=copies.COPY_ADMISSIONS
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc(),copy_catalog_admissions=copies.COPY_ADMISSIONS)
    finally:
        modes.copy_db=original
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_preuse_removal']=product.rollback_preuse(cur,control.STATE);conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        browser=report.get('browser',{})
        report['observed_case_count']=sum(browser.get('counts',{}).values())
        report['required_case_ids_pass']=set(browser.get('cases',{}))==set(expected['browser_case_ids'])and all(row['status']=='PASS'for row in browser.get('cases',{}).values())
        groups=browser.get('status')in('PASS','RUN_COMPLETE')and browser.get('counts')=={'PASS':7}
        clean=browser.get('database_remaining',1)==0 and(browser.get('auth_counts')or{}).get('restored')and not browser.get('cleanup_failures')and not browser.get('auth_cleanup_failures')and browser.get('host_exit')==0 and browser.get('host_status')=='RUN_COMPLETE'and browser.get('console_errors')==0 and browser.get('real_auth')is True and browser.get('jwt_signed_by_runtime')is False and browser.get('test_only_usage_grant')is False
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and groups and clean and report.get('actual_product_loopback_proven'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in ('label','status','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
