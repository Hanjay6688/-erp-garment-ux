"""Actual browser7 synchronization qualification; reuse bound real SQL races6."""
from hashlib import sha256
from pathlib import Path
import gzip,importlib.util,json,lzma,os,shutil,subprocess,sys,tempfile,traceback
sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Current browser/race qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
PREVIOUS=HERE.parent/'ow04-payment-current-qualification'
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),
 str(REPO/'scripts/ow04-payment-source-qualification'),str(REPO/'scripts/ow04-consumer-qualification'),str(REPO/'scripts/ow04-qualification')]
import source_probe as control
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta
spec=importlib.util.spec_from_file_location('payment_current_copy_authority',PREVIOUS/'copy_authority.py')
copies=importlib.util.module_from_spec(spec);spec.loader.exec_module(copies)
spec=importlib.util.spec_from_file_location('current_actual_http18',HERE/'http20_cases.py')
business=importlib.util.module_from_spec(spec);spec.loader.exec_module(business)
product,previous,package,core,p09=control.product,control.previous,control.package,control.core,control.p09
LABEL='CP7_OW04_PAYMENT_CURRENT_HTTP20_BROWSER9'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    import source_gate
    binding=source_gate.admitted(product)
    expected=json.loads((PREVIOUS/'EXPECTED.json').read_bytes())
    assert tuple(expected['http_case_ids'])==business.RETAINED_IDS and len(business.IDS)==20
    assert len(expected['browser_case_ids'])==len(set(expected['browser_case_ids']))==9
    business.credit.expected();business.expected()
    return binding,expected


def verify(cur):return product.verify(cur,control.STATE)


def run():
    binding,expected=admitted()
    assert os.environ['AUDITOR_UI_MODE']=='ENTENG'
    report=dict(label=LABEL,status='INCOMPLETE',candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        actual_Native32_same_source_binding=binding,current_financial_sources=product.sources(),
        expected_browser_case_ids=expected['browser_case_ids'],expected_http_case_ids=list(business.IDS),
        expected_case_count=29,planned_retained_HTTP16_and_browser7=True,
        current_Native32_original_verified=True,SQLraces6_on_changed_source_not_claimed=True,formal_CP7C_started=False,production_go=False,feature_complete=False,hosted=False)
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
        report['http']=modes.run_http(business,verify,'ow04_final_http20')
        before_hosts=set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))
        report['browser']=modes.run_browser(PREVIOUS/'all_browser_cases.mjs',verify,'ow04_payment_current9')
        hosts=[]
        for directory in sorted(set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))-before_hosts):
            file=directory/'BROWSER.json'
            if file.is_file():
                target=OUT.parent/('CURRENT_HOST_'+str(len(hosts))+'.json')
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
        browser=report.get('browser',{});http=report.get('http',{})
        report['observed_case_count']=sum(browser.get('counts',{}).values())+sum(http.get('counts',{}).values())
        report['required_case_ids_pass']=set(browser.get('cases',{}))==set(expected['browser_case_ids'])and all(row['status']=='PASS'for row in browser.get('cases',{}).values())and set(http.get('cases',{}))==set(business.IDS)and all(row['status']=='PASS'for row in http.get('cases',{}).values())
        groups=browser.get('status')in('PASS','RUN_COMPLETE')and browser.get('counts')=={'PASS':9}and http.get('status')in('PASS','RUN_COMPLETE')and http.get('counts')=={'PASS':20}
        clean=browser.get('database_remaining',1)==0 and(browser.get('auth_counts')or{}).get('restored')and not browser.get('cleanup_failures')and not browser.get('auth_cleanup_failures')and browser.get('host_exit')==0 and browser.get('host_status')=='RUN_COMPLETE'and browser.get('console_errors')==0 and browser.get('real_auth')is True and browser.get('jwt_signed_by_runtime')is False and browser.get('test_only_usage_grant')is False
        clean=clean and http.get('database_remaining',1)==0 and(http.get('auth_counts')or{}).get('restored')and not http.get('cleanup_failures')and http.get('real_auth')is True and http.get('jwt_signed_by_runtime')is False and http.get('test_only_usage_grant')is False
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and groups and clean and report.get('actual_product_loopback_proven')and report.get('disposable_tracking_restored'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in ('label','status','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
