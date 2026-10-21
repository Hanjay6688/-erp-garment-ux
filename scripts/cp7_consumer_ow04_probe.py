"""Bounded Native consumer8 on the actual qualified owning predecessor.

No hosted connection, provider, production install, CP7C rollout, full consumer
acceptance or retrospective Native87 claim. The same closed disposable package
prepares CP6. All cases roll back; exact pre-use removal restores the baseline.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import subprocess
import sys
import traceback

if sys.argv[1:]:
    raise SystemExit('Bounded consumer qualification accepts no arguments')
sys.argv.extend(['--signed-source','--credit-dependencies','--native-fractional-hpp'])
import cp7_full_ow04_probe as predecessor
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog

HERE=Path(__file__).resolve().parent
CONSUMER=HERE/'cp7_customer_credit/consumer'
sys.path.insert(0,str(CONSUMER))
import composition as consumer
import native_basic_cases as business

package,native,p09=predecessor.package,predecessor.native,predecessor.p09
LABEL='CP7_OW04_CONSUMER_NATIVE_BASIC8'
OUT=predecessor.full.ROOT/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None


def verify(cur):
    if STATE is None:
        raise ValueError('OW04_CONSUMER_QUALIFICATION_INSTALLATION_REQUIRED')
    return consumer.verify(cur,STATE)


def run():
    global STATE
    report=dict(label=LABEL,status='INCOMPLETE',expected_case_count=8,required_case_ids=list(business.IDS),
        candidate_commit=subprocess.check_output(['git','-C',str(predecessor.full.ROOT),'rev-parse','HEAD'],text=True).strip(),
        qualified_predecessor_native_count=87,predecessor_native87_rerun=False,
        frozen_nine_arithmetic_sha256=business.fixture.EXPECTED_SHA256,
        consumer_sources=consumer.sources(),case_source_sha256=sha256(Path(business.__file__).read_bytes()).hexdigest(),
        fixture_source_sha256=sha256(Path(business.fixture.__file__).read_bytes()).hexdigest(),
        scope='BOUNDED_FIRST_EIGHT_LITERAL_CONSUMER_CASES_ON_ACTUAL_NATIVE_WRITERS',
        full_nine_case_consumer_acceptance=False,source_inverse_and_historical_restatement_qualified=False,
        real_Auth_HTTP_browser_race_qualified=False,formal_CP7C_started=False,
        production_go=False,feature_complete=False,independent_acceptance=False,qualification_only=True,hosted=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=predecessor.restore_state.capture(cur,package.boundary.snapshot,predecessor.core.predecessor.public_state,p09.functions)
            conn.rollback()
            full_state=predecessor.full.install(cur)
            report['qualified_predecessor_installation']=predecessor.full.verify(cur,full_state)
            report['verified_predecessor_info_manifest']=predecessor.core.predecessor_info_manifest(cur)
            STATE=consumer.install(cur)
            report['consumer_installed_verification']=verify(cur)
            report['source_declared_native_FK_transition']=STATE['source_trigger_transition']
            report['consumer_native_poster_derivation']=STATE['native_poster_proof']
            conn.commit();installed=True
        report['advisors_with_consumer']=advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,business.cases,verify)
        report['native_public_catalog_comparison']=catalog
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['consumer_exact_preuse_restore']=consumer.uninstall_preuse(cur,STATE)
                    report['qualified_predecessor_restored']=predecessor.full.verify(cur,full_state)
                    predecessor.full.rollback_preuse(cur,full_state);conn.commit()
                    report['cp6_restored']=predecessor.restore_state.prove(cur,before,package.boundary.snapshot,
                        predecessor.core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_consumer'])
                report['advisor_disposition']=predecessor.core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('native',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(business.IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report.get('required_case_ids_pass') \
            and group.get('status')=='PASS'and group.get('counts')=={'PASS':8}and group.get('database_remaining',0)==0:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
