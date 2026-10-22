"""Two additional Native journeys on the unchanged Native32 financial source."""
from pathlib import Path
import importlib.util,json,subprocess,sys,traceback
sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Four generation qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/ow04-consumer-closure-qualification')]
import native32_probe as framework
import psycopg
import source_gate
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors,advisor_delta
business=framework.previous.native_fractional
control=framework.control
product,previous,native,package,core,p09=framework.product,framework.previous,framework.native,framework.package,framework.core,framework.p09
IDS=business.IDS
LABEL='CP7_OW04_FINAL_OPENING_HPP_NATIVE14'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    binding=source_gate.admitted(product)
    assert len(IDS)==len(set(IDS))==14
    business.expected()
    return binding


def cases(cur,today):return business.cases(cur,today)


def run():
    binding=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',expected_case_count=14,required_case_ids=list(IDS),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        source_declaration=binding,current_financial_sources=product.sources(),
        actual_Native32_same_source_binding=binding,Native32_rerun=False,
        multiple_distinct_return_cohorts_qualified=False,
        Auth_HTTP_browser_races_restore_not_rerun_in_this_job=True,
        opening_fractional_expected_sha256=business.EXPECTED_SHA,
        formal_CP7C_started=False,production_go=False,feature_complete=False,hosted=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            control.STATE=product.install(cur)
            report['complete_installed_verification']=product.verify(cur,control.STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,control.verify)
        report['native_public_catalog_comparison']=catalog
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_preuse_removal']=product.rollback_preuse(cur,control.STATE)
                    conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('native',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass'] \
         and group.get('status')=='PASS'and group.get('counts')=={'PASS':14}and group.get('database_remaining',0)==0:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)

if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
