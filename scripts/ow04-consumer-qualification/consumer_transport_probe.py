"""Real Auth HTTP on an exact independently recorded bounded consumer Native18.

The Native18 receipt is required before any connection. This does not adopt
Native87 as execution of the consumer overlay, run a browser, or deploy ERP.
"""
from hashlib import sha256
from pathlib import Path
import gzip
import json
import os
import subprocess
import sys
import traceback

REPO=Path(os.environ.get('ERP_REPO',Path(__file__).resolve().parents[2])).resolve()
HERE=Path(__file__).resolve().parent
if sys.argv[1:]:raise SystemExit('Consumer real Auth HTTP entry accepts no arguments')
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),str(REPO/'scripts/ow04-qualification')]
sys.argv.extend(['--signed-source','--credit-dependencies','--native-fractional-hpp'])
import cp7_full_ow04_probe as predecessor
import composition as consumer
import consumer_http_cases as business
import cp6_auditor_modes as modes
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta

package,core,p09=predecessor.package,predecessor.core,predecessor.p09
OUT=predecessor.full.ROOT/'cp6-proof/t3/CP7_OW04_CONSUMER_HTTP14.json'
STATE=None


def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()


def qualified_consumer():
    binding=json.loads((HERE/'QUALIFIED_CONSUMER_NATIVE.json').read_bytes())
    assert binding['classification']=='EXACT_ACTUAL_BOUNDED_CONSUMER_NATIVE18_BINDING_NOT_NATIVE87_OR_TRANSPORT_EXECUTION'
    assert binding['status']=='PASS'and binding['native_case_count']==18
    raw=gzip.decompress((REPO/binding['original_report']).read_bytes())
    assert sha256(raw).hexdigest()==binding['original_report_sha256']
    actual=json.loads(raw)
    assert actual['candidate_commit']==binding['candidate']and actual['status']=='PASS'
    assert actual['expected_case_count']==actual['observed_case_count']==18
    assert actual['native']['counts']=={'PASS':18}and actual['cp6_restored']and actual['advisor_gate']
    assert set(actual['native']['cases'])==set(actual['required_case_ids'])and actual['required_case_ids_pass']
    assert actual['consumer_sources']==consumer.sources()
    assert actual['consumer_installed_verification']['new_function_count']==45
    assert actual['consumer_exact_preuse_restore']['status']=='EXACT_PREUSE_RESTORE'
    assert all(case['status']=='PASS'and case['full_boundary_restored']and case['public_schema_unchanged']
        and case['session_leaks']=={'advisory_locks':0,'advisory_lock_keys':[],'other_sessions':[]}
        for case in actual['native']['cases'].values())
    assert git('rev-parse',binding['candidate']+'^{tree}')==binding['tree']
    # Every product/source path tested by actual Native18 remains byte exact.
    # New bounded HTTP-only code has a closed source list and its own hashes.
    paths=git('diff','--name-only',binding['candidate'],'HEAD','--','scripts','src','supabase').splitlines()
    allowed={'scripts/ow04-consumer-qualification/'+name for name in
             ('consumer_http_cases.py','consumer_transport_probe.py','QUALIFIED_CONSUMER_NATIVE.json','HTTP_EXPECTED.json')}
    assert set(paths)<=allowed,('CONSUMER_HTTP_QUALIFIED_PRODUCT_SOURCE_CHANGED',paths)
    assert not git('status','--porcelain','--','scripts/cp7_customer_credit','scripts/cp7_consumer_ow04_probe.py','src','supabase'),\
        'CONSUMER_HTTP_UNCOMMITTED_PRODUCT_CHANGED'
    expected=business.expected()
    return dict(**binding,transport_case_count=len(business.IDS),transport_declaration_sha256=business.EXPECTED_SHA256,
        new_transport_sources={str(path.relative_to(REPO)):sha256(path.read_bytes()).hexdigest()
            for path in sorted(HERE.iterdir())if path.is_file()},
        original_frozen_nine_sha256=expected['original_frozen_nine_sha256'],
        frozen_refund_nine_sha256=expected['frozen_refund_nine_sha256'])


def verify(cur):
    if STATE is None:raise ValueError('CONSUMER_HTTP_COMPLETE_INSTALL_REQUIRED')
    return consumer.verify(cur,STATE)


def run():
    global STATE
    accepted=qualified_consumer()  # No connection before the exact receipt/source gate.
    report=dict(label='CP7_OW04_CONSUMER_HTTP14',status='INCOMPLETE',expected_case_count=14,
        required_case_ids=list(business.IDS),candidate_commit=git('rev-parse','HEAD'),
        qualified_native_binding=accepted,consumer_sources=consumer.sources(),
        scope='ACTUAL_AUTH_AND_POSTGREST_BOUND_CONSUMER_APPLY_REFUND_NAMED_UNDO_AND_REFUSALS',
        Native87_rerun=False,Native18_rerun=False,browser_or_races_qualified=False,
        production_go=False,feature_complete=False,independent_acceptance=False,
        hosted=False,formal_CP7C_started=False,qualification_only=True)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=predecessor.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            full_state=predecessor.full.install(cur)
            report['qualified_predecessor_installation']=predecessor.full.verify(cur,full_state)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            STATE=consumer.install(cur)
            report['consumer_installed_verification']=verify(cur)
            conn.commit();installed=True
        report['advisors_with_consumer']=advisors(package.boundary.PG)
        report['http']=modes.run_http(business,verify,'ow04_consumer14')
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['consumer_exact_preuse_restore']=consumer.uninstall_preuse(cur,STATE)
                    report['qualified_predecessor_restored']=predecessor.full.verify(cur,full_state)
                    predecessor.full.rollback_preuse(cur,full_state);conn.commit()
                    report['cp6_restored']=predecessor.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_consumer'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('http',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(business.IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']\
            and group.get('status')in('PASS','RUN_COMPLETE')and group.get('counts')=={'PASS':14}\
            and group.get('database_remaining',1)==0 and(group.get('auth_counts')or{}).get('restored')and not group.get('cleanup_failures'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    qualified_consumer()  # Also before outer package preparation opens any DB.
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
