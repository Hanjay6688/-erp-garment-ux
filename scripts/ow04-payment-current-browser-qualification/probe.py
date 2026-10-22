"""Actual current browser9 retry plus two isolated transaction timing observations."""
from hashlib import sha256
from pathlib import Path
import gzip,importlib.util,json,lzma,os,shutil,subprocess,sys,tempfile,traceback
sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Current browser/race qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),
 str(REPO/'scripts/ow04-payment-source-qualification'),str(REPO/'scripts/ow04-consumer-qualification'),str(REPO/'scripts/ow04-qualification')]
import source_probe as control
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta
spec=importlib.util.spec_from_file_location('payment_current_copy_authority',REPO/'scripts/ow04-payment-current-qualification/copy_authority.py')
copies=importlib.util.module_from_spec(spec);spec.loader.exec_module(copies)
spec=importlib.util.spec_from_file_location('current_isolated_timing',HERE/'diagnostics.py')
diagnostics=importlib.util.module_from_spec(spec);spec.loader.exec_module(diagnostics)
from cp7_catalog_state import exact_public_catalog
product,previous,package,core,p09=control.product,control.previous,control.package,control.core,control.p09
LABEL='CP7_OW04_PAYMENT_CURRENT_BROWSER9_READY'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate']=='5359767befe09fb54bf421ff0eef07c26d6560f0'
    assert source['product_sources']==product.sources()
    for path,digest in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CURRENT_BROWSER9_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows'],text=True).splitlines()
    assert set(changed)<=set(source['files'])|{'scripts/ow04-payment-current-browser-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts','src','supabase','tests','.github/workflows/cp7-ow04-payment-current-browser.yml'],text=True).strip()
    bindings=json.loads((HERE/'QUALIFIED.json').read_bytes());reports={}
    for label,row in bindings['reports'].items():
        packed=(REPO/row['file']).read_bytes()
        raw=lzma.decompress(packed)if row['file'].endswith('.xz')else gzip.decompress(packed)
        assert sha256(raw).hexdigest()==row['raw_sha256'];reports[label]=json.loads(raw)
    n,h,q=reports['Native26'],reports['HTTP18_phase'],reports['SQL8']
    assert n['candidate_commit']=='527ed740647724abc06368b29744ed721193599a'
    assert n['status']=='PASS'and n['native']['counts']=={'PASS':26}and n['required_case_ids_pass']
    assert q['status']=='PASS'and q['races']['counts']=={'PASS':8}and q['required_case_ids_pass']
    assert q['actual_Native26_binding']['raw_sha256']==bindings['reports']['Native26']['raw_sha256']
    assert h['candidate_commit']=='bce802a3254b6d63e10781a80b29e43d6c4342fc'
    assert h['status']=='INCOMPLETE'and h['browser']['counts']=={'PASS':8,'INCOMPLETE':1}
    http=h['http'];assert http['status']=='RUN_COMPLETE'and http['counts']=={'PASS':18}
    assert all(row['status']=='PASS'for row in http['cases'].values())
    expected_http=json.loads((REPO/'scripts/ow04-payment-current-qualification/EXPECTED.json').read_bytes())['http_case_ids']
    assert set(http['cases'])==set(expected_http)and len(expected_http)==18
    assert http['real_auth']and not http['jwt_signed_by_runtime']and not http['test_only_usage_grant']
    assert http['auth_counts']['restored']and http['database_remaining']==0 and not http.get('cleanup_failures')
    assert all(row['all22_groups_equal_original_install']for row in h['copy_catalog_admissions'])
    for report,sources in((n,n['actual_financial_sources']),(h,h['current_financial_sources']),(q,q['current_financial_sources'])):
        assert sources==product.sources()and report['cp6_restored']and report['advisor_gate']
    expected=json.loads((HERE/'EXPECTED.json').read_bytes())
    assert len(expected['browser_case_ids'])==len(set(expected['browser_case_ids']))==9
    assert tuple(expected['diagnostic_ids'])==diagnostics.IDS
    return bindings,expected


def verify(cur):return product.verify(cur,control.STATE)


def run():
    binding,expected=admitted()
    assert os.environ['AUDITOR_UI_MODE']=='ENTENG'
    report=dict(label=LABEL,status='INCOMPLETE',candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        qualified_actual_current_Native26_HTTP18_SQL8=binding,current_financial_sources=product.sources(),
        expected_browser_case_ids=expected['browser_case_ids'],expected_diagnostic_ids=list(diagnostics.IDS),
        expected_case_count=9,retained_browser9_actually_rerun=True,
        Native26_HTTP18_SQL8_rerun=False,diagnostic_observations_not_additional_feature_cases=True,formal_CP7C_started=False,production_go=False,feature_complete=False,hosted=False)
    installed=False;original=modes.copy_db;tracking=None
    try:
        # Disposable cluster observability only; no business body, database
        # authority, role setting, public capability or product budget changes.
        with psycopg.connect(package.boundary.PRIMARY_ADMIN,autocommit=True)as conn,conn.cursor()as cur:
            tracking=cur.execute("select setting,sourcefile from pg_settings where name='track_functions'").fetchone()
            cur.execute("alter system set track_functions='all'");cur.execute('select pg_reload_conf()')
        report['disposable_tracking_before']=tracking
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
        with exact_public_catalog(control.native,retain_raw=True)as diagnostic_catalog:
            report['isolated_diagnostics']=control.native.strict_group('OW04_CURRENT_ISOLATED_TIMING',diagnostics.cases,control.verify)
        report['diagnostic_public_catalog_comparison']=diagnostic_catalog
        before_hosts=set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))
        report['browser']=modes.run_browser(REPO/'scripts/ow04-payment-current-qualification/all_browser_cases.mjs',verify,'ow04_payment_current9_ready')
        hosts=[]
        for directory in sorted(set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))-before_hosts):
            file=directory/'BROWSER.json'
            if file.is_file():
                target=OUT.parent/('CURRENT_BROWSER_HOST_'+str(len(hosts))+'.json')
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
        if tracking is not None:
            try:
                with psycopg.connect(package.boundary.PRIMARY_ADMIN,autocommit=True)as conn,conn.cursor()as cur:
                    if tracking[1]and tracking[1].endswith('/postgresql.auto.conf'):
                        from psycopg import sql
                        cur.execute(sql.SQL('alter system set track_functions={}').format(sql.Literal(tracking[0])))
                    else:cur.execute('alter system reset track_functions')
                    cur.execute('select pg_reload_conf()')
                with psycopg.connect(package.boundary.PRIMARY_ADMIN)as conn,conn.cursor()as cur:
                    after=cur.execute("show track_functions").fetchone()[0]
                report['disposable_tracking_restored']=after==tracking[0]
            except Exception as error:report.update(tracking_restore_error=str(error),disposable_tracking_restored=False)
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
        browser=report.get('browser',{});diagnostic=report.get('isolated_diagnostics',{})
        report['observed_case_count']=sum(browser.get('counts',{}).values())
        report['required_case_ids_pass']=set(browser.get('cases',{}))==set(expected['browser_case_ids'])and all(row['status']=='PASS'for row in browser.get('cases',{}).values())
        report['isolated_diagnostic_observations_count']=sum(diagnostic.get('counts',{}).values())
        diagnostics_pass=diagnostic.get('status')=='PASS'and diagnostic.get('counts')=={'PASS':2}and set(diagnostic.get('cases',{}))==set(diagnostics.IDS)
        groups=browser.get('status')in('PASS','RUN_COMPLETE')and browser.get('counts')=={'PASS':9}and diagnostics_pass
        clean=browser.get('database_remaining',1)==0 and(browser.get('auth_counts')or{}).get('restored')and not browser.get('cleanup_failures')and not browser.get('auth_cleanup_failures')and browser.get('host_exit')==0 and browser.get('host_status')=='RUN_COMPLETE'and browser.get('console_errors')==0 and browser.get('real_auth')is True and browser.get('jwt_signed_by_runtime')is False and browser.get('test_only_usage_grant')is False
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and groups and clean and report.get('actual_product_loopback_proven')and report.get('disposable_tracking_restored'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in ('label','status','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
