"""Current-source actual SQL8, bound to the exact actual Native26 report."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,lzma,subprocess,sys,traceback
sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Current SQL8 qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),
 str(REPO/'scripts/ow04-payment-source-qualification'),str(REPO/'scripts/ow04-consumer-race-qualification')]
import source_probe as control
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta
spec=importlib.util.spec_from_file_location('current_sql8_cases',HERE/'race_cases.py')
races=importlib.util.module_from_spec(spec);spec.loader.exec_module(races)
spec=importlib.util.spec_from_file_location('current_sql8_authority',HERE/'copy_authority.py')
copies=importlib.util.module_from_spec(spec);spec.loader.exec_module(copies)
product,previous,package,core,p09=control.product,control.previous,control.package,control.core,control.p09
LABEL='CP7_OW04_PAYMENT_CURRENT_SQL8'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate']=='bce802a3254b6d63e10781a80b29e43d6c4342fc'
    assert source['product_sources']==product.sources()
    for path,digest in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CURRENT_SQL8_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows'],text=True).splitlines()
    assert set(changed)<=set(source['files'])|{'scripts/ow04-payment-current-races-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts','src','supabase','tests','.github/workflows/cp7-ow04-payment-current-races.yml'],text=True).strip()
    path=REPO/'docs/cp7/d17-14/ow04/payment-native26-527ed740-pass/CP7_OW04_PAYMENT_SOURCE_NATIVE26_POSITIVE.json.xz'
    raw=lzma.decompress(path.read_bytes())
    assert sha256(raw).hexdigest()=='4f2e6a3ec2d325d2b10a00abc823e1177a1c4e9dbbaa0445a397966d7dddab91'
    native=json.loads(raw)
    assert native['candidate_commit']=='527ed740647724abc06368b29744ed721193599a'
    assert native['status']=='PASS'and native['native']['counts']=={'PASS':26}
    assert native['required_case_ids_pass']and native['cp6_restored']and native['advisor_gate']
    assert native['actual_financial_sources']==native['source_declaration']['product_sources']==product.sources()
    verification=native['complete_installed_verification']['payment']
    assert verification['changed_functions']==25 and verification['new_functions']==30
    races.expected()
    return dict(candidate=native['candidate_commit'],raw_sha256=sha256(raw).hexdigest(),
        actual_counts=native['native']['counts'],exact_same_financial_source=True)


def verify(cur):return product.verify(cur,control.STATE)


def run():
    binding=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        actual_Native26_binding=binding,current_financial_sources=product.sources(),expected_case_count=8,
        expected_race_ids=list(races.IDS),retained6_actually_rerun=True,Native26_rerun=False,
        authenticated_SQL_fixtures_not_real_Auth=True,real_Auth_HTTP_browser_qualification_not_inferred=True,
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
        report['races']=modes.run_races(races,verify,'ow04_payment_current8')
        report['copy_catalog_admissions']=copies.COPY_ADMISSIONS
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc(),copy_catalog_admissions=copies.COPY_ADMISSIONS)
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
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        race=report.get('races',{})
        report['observed_case_count']=sum(race.get('counts',{}).values())
        report['required_case_ids_pass']=set(race.get('races',{}))==set(races.IDS)and all(row['status']=='PASS'for row in race.get('races',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and race.get('status')in('PASS','RUN_COMPLETE')and race.get('counts')=={'PASS':8}and race.get('database_remaining',1)==0 and not race.get('cleanup_failures')and all(row['all22_groups_equal_original_install']for row in copies.COPY_ADMISSIONS):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
