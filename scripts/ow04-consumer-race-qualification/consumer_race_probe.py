"""Two real SQL-session races on the exact actual HTTP14/Native18 backend.

Separate branch/entry: no Auth14 rerun or qualification of a browser/load test.
The actual passing HTTP receipt is mandatory before any connection.
"""
from hashlib import sha256
from pathlib import Path
import gzip
import json
import os
import subprocess
import sys
import traceback

sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Consumer SQL race entry accepts no arguments')
REPO=Path(os.environ.get('ERP_REPO',Path(__file__).resolve().parents[2])).resolve()
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/ow04-consumer-qualification')]
import consumer_transport_probe as transport
sys.path.insert(0,str(HERE))
import consumer_race_cases as business
import cp6_auditor_modes as modes
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta

consumer,predecessor=transport.consumer,transport.predecessor
package,core,p09=transport.package,transport.core,transport.p09
OUT=predecessor.full.ROOT/'cp6-proof/t3/CP7_OW04_CONSUMER_SQL_RACE2.json'


def qualified_http():
    binding=json.loads((HERE/'QUALIFIED_CONSUMER_HTTP.json').read_bytes())
    assert binding['classification']=='EXACT_ACTUAL_CONSUMER_HTTP14_SOURCE_BINDING_NOT_NEW_AUTH_NATIVE_OR_BROWSER_EXECUTION'
    assert binding['status']=='PASS'and binding['http_case_count']==14
    raw=gzip.decompress((REPO/binding['original_report']).read_bytes())
    assert sha256(raw).hexdigest()==binding['original_report_sha256']
    report=json.loads(raw)
    assert report['candidate_commit']==binding['candidate']and report['status']=='PASS'
    assert report['expected_case_count']==report['observed_case_count']==14
    assert report['http']['counts']=={'PASS':14}and report['cp6_restored']and report['advisor_gate']
    assert report['required_case_ids_pass']and len(report['http']['cases'])==14
    assert report['http']['real_auth']is True and report['http']['jwt_signed_by_runtime']is False
    assert report['http']['test_only_usage_grant']is False and report['http']['auth_counts']['restored']
    assert report['http']['database_remaining']==0 and not report['http']['cleanup_failures']
    assert report['consumer_exact_preuse_restore']['status']=='EXACT_PREUSE_RESTORE'
    assert report['consumer_sources']==consumer.sources()
    native=report['qualified_native_binding']
    original=gzip.decompress((REPO/native['original_report']).read_bytes())
    assert sha256(original).hexdigest()==native['original_report_sha256']
    source=json.loads(original)
    assert source['status']=='PASS'and source['native']['counts']=={'PASS':18}
    assert source['candidate_commit']==native['candidate']and source['cp6_restored']and source['advisor_gate']
    assert source['consumer_sources']==consumer.sources()
    assert transport.git('rev-parse',binding['candidate']+'^{tree}')==binding['tree']
    # HTTP14 already proved the exact Native18 financial source plus its4
    # qualification files. This branch adds ONLY its four new SQL race files.
    changed=transport.git('diff','--name-only',binding['candidate'],'HEAD','--','scripts','src','supabase').splitlines()
    allowed={'scripts/ow04-consumer-race-qualification/'+name for name in
             ('consumer_race_cases.py','consumer_race_probe.py','RACE_EXPECTED.json','QUALIFIED_CONSUMER_HTTP.json')}
    assert set(changed)<=allowed,('CONSUMER_RACE_QUALIFIED_HTTP_BACKEND_CHANGED',changed)
    assert not transport.git('status','--porcelain','--','scripts/cp7_customer_credit','scripts/cp7_consumer_ow04_probe.py','src','supabase')
    business.expected()
    return dict(**binding,race_expectations_sha256=business.EXPECTED_SHA256,
        race_sources={str(p.relative_to(REPO)):sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.iterdir())if p.is_file()},
        reused_native_binding=native)


def run():
    accepted=qualified_http()
    report=dict(label='CP7_OW04_CONSUMER_SQL_RACE2',status='INCOMPLETE',expected_case_count=2,
        required_case_ids=list(business.IDS),candidate_commit=transport.git('rev-parse','HEAD'),
        qualified_http_binding=accepted,consumer_sources=consumer.sources(),
        scope='TWO_ACTUAL_SQL_SESSION_CONSUMER_UUID_AND_STALE_REVIEW_RACES',
        authenticated_SQL_fixture_not_real_Auth=True,real_Auth_HTTP_rerun=False,
        Native18_rerun=False,Native87_rerun=False,browser_or_load_qualified=False,
        production_go=False,feature_complete=False,independent_acceptance=False,
        hosted=False,formal_CP7C_started=False,qualification_only=True)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=predecessor.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback();full_state=predecessor.full.install(cur)
            report['qualified_predecessor_installation']=predecessor.full.verify(cur,full_state)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            transport.STATE=consumer.install(cur)
            report['consumer_installed_verification']=transport.verify(cur)
            conn.commit();installed=True
        report['advisors_with_consumer']=advisors(package.boundary.PG)
        report['races']=modes.run_races(business,transport.verify,'ow04_consumer2')
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['consumer_exact_preuse_restore']=consumer.uninstall_preuse(cur,transport.STATE)
                    report['qualified_predecessor_restored']=predecessor.full.verify(cur,full_state)
                    predecessor.full.rollback_preuse(cur,full_state);conn.commit()
                    report['cp6_restored']=predecessor.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_consumer'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('races',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('races',{}))==set(business.IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']\
            and group.get('status')in('PASS','RUN_COMPLETE')and group.get('counts')=={'PASS':2}\
            and group.get('database_remaining',1)==0:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    qualified_http()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
