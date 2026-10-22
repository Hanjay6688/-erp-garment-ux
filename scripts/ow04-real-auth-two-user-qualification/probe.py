"""Two still-funded real-Auth races on the immutable current financial source.

Bind the original27 passed Auth/browser rows without turning its incomplete
combined job green. The new harness is a separate versioned clean checkout.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,subprocess,sys,traceback
sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Real Auth2 qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
QUALIFIER_REPO=HERE.parents[1]
REPO=Path(os.environ['OW04_FROZEN_PRODUCT_REPO']).resolve()
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/ow04-final-qualification'),
 str(REPO/'scripts/cp7_customer_credit/consumer'),str(REPO/'scripts/ow04-payment-source-qualification'),
 str(REPO/'scripts/ow04-consumer-qualification'),str(REPO/'scripts/ow04-qualification')]
import source_probe as control
import source_gate
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta
spec=importlib.util.spec_from_file_location('auth2_copy_authority',REPO/'scripts/ow04-payment-current-qualification/copy_authority.py')
copies=importlib.util.module_from_spec(spec);spec.loader.exec_module(copies)
spec=importlib.util.spec_from_file_location('distinct_still_funded_Auth2',HERE/'cases.py')
business=importlib.util.module_from_spec(spec);spec.loader.exec_module(business)
product,previous,package,core,p09=control.product,control.previous,control.package,control.core,control.p09
LABEL='CP7_OW04_DISTINCT_AUTH2_FUNDED_STALE'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()==source['product_commit']=='36a6b880d789452dbe4096fd4c401430bba1a5cb'
    assert source['product_sources']==product.sources()
    for path,digest in source['files'].items():
        assert sha256((QUALIFIER_REPO/path).read_bytes()).hexdigest()==digest,('AUTH2_QUALIFIER_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(QUALIFIER_REPO),'status','--porcelain','--',
        'scripts/ow04-real-auth-two-user-qualification','.github/workflows/cp7-ow04-real-auth-two-user.yml'],text=True).strip()
    binding=source_gate.admitted(product)
    business.expected()
    raw=Path(os.environ['OW04_HTTP18_BROWSER9_ORIGINAL_REPORT']).read_bytes()
    assert len(raw)==415098 and sha256(raw).hexdigest()==source['retained_original_report_sha256']=='77e1847a2a2b445dadf275a3cba4f00caa72253bd75ce3e65767c3cc221df7b2'
    prior=json.loads(raw)
    assert prior['candidate_commit']==source['product_commit']and prior['current_financial_sources']==product.sources()
    assert prior['status']=='INCOMPLETE'and prior['http']['counts']=={'PASS':18,'INCOMPLETE':2}
    expected=json.loads((REPO/'scripts/ow04-payment-current-qualification/EXPECTED.json').read_bytes())
    for name in expected['http_case_ids']:assert prior['http']['cases'][name]['status']=='PASS'
    assert set(prior['browser']['cases'])==set(expected['browser_case_ids'])and prior['browser']['counts']=={'PASS':9}
    assert all(row['status']=='PASS'for row in prior['browser']['cases'].values())
    assert prior['cp6_restored']and prior['advisor_gate']and prior['actual_product_loopback_proven']and prior['disposable_tracking_restored']
    for group in (prior['http'],prior['browser']):
        assert group['database_remaining']==0 and group['auth_counts']['restored']and not group.get('cleanup_failures')and not group.get('auth_cleanup_failures')
        assert group['real_auth']is True and group['jwt_signed_by_runtime']is False and group['test_only_usage_grant']is False
    return dict(actual_Native32_same_source=binding,retained_same_source_Auth18_browser9=dict(
        run_id=39746622801,job_id=119716563410,raw_sha256=sha256(raw).hexdigest(),passed_HTTP_cases=18,
        passed_browser_cases=9,original_combined_status='INCOMPLETE',old_two150_cases_not_reclassified=True),
        frozen_product_commit=source['product_commit'],qualification_commit=subprocess.check_output(
            ['git','-C',str(QUALIFIER_REPO),'rev-parse','HEAD'],text=True).strip())


def verify(cur):return product.verify(cur,control.STATE)


def run():
    binding=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',candidate_commit=binding['frozen_product_commit'],
        source_declaration=binding,current_financial_sources=product.sources(),expected_case_count=2,
        required_case_ids=list(business.IDS),Native32_and_retained27_rerun=False,
        formal_CP7C_started=False,production_go=False,feature_complete=False,hosted=False)
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
        report['http']=modes.run_http(business,verify,'ow04_distinct_real_auth2')
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
        group=report.get('http',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(business.IDS)and all(r['status']=='PASS'for r in group.get('cases',{}).values())
        clean=group.get('database_remaining',1)==0 and(group.get('auth_counts')or{}).get('restored')and not group.get('cleanup_failures')and not group.get('auth_cleanup_failures')
        clean=clean and group.get('real_auth')is True and group.get('jwt_signed_by_runtime')is False and group.get('test_only_usage_grant')is False
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and group.get('counts')=={'PASS':2}and clean:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
