"""Current Native18/Auth14/race2 + workspace4/browser4 on isolated databases.

Old receipts remain bound evidence, never relabelled. The exact optional-target
record fix now requires the retained financial groups to run on this source.
"""
from hashlib import sha256
from pathlib import Path
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback

sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Consumer UI entry accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=Path(os.environ.get('ERP_REPO',HERE.parents[1])).resolve()
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/ow04-consumer-qualification')]
import consumer_transport_probe as transport
sys.path.insert(0,str(HERE))
import workspace_http_cases as business
import selector_record_fix
import native_consumer_cases as native_business
sys.path.insert(0,str(REPO/'scripts/ow04-consumer-race-qualification'))
import consumer_race_cases as race_business
from cp7_catalog_state import exact_public_catalog

consumer,predecessor=transport.consumer,transport.predecessor
package,core,p09=transport.package,transport.core,transport.p09
modes,psycopg=transport.modes,transport.psycopg
OUT=predecessor.full.ROOT/'cp6-proof/t3/CP7_OW04_CONSUMER_CURRENT42.json'
PRODUCT=('src/CustomerCreditPanel.tsx','src/customerCreditContract.ts','src/customerCreditContract.test.ts',
 'src/ConnectedCustomerCredit.dom.test.tsx','src/ConnectedSalesPage.tsx','src/productionRecovery.ts',
 'src/types/database.preconnect.ts','src/lib/clientError.ts','tests/fixtures/customerCredit.ts',
 'scripts/check-access-catalog.mjs','scripts/check-source-ownership.mjs',
 'scripts/cp7_customer_credit/consumer/07_locked_projection.sql',
 'scripts/cp7_customer_credit/consumer/13_workspace.sql','scripts/cp7_customer_credit/consumer/composition.py',
 'scripts/cp7_customer_credit/consumer/local_full_ddl_compile.mjs')
HARNESS=tuple('scripts/ow04-consumer-ui-qualification/'+name for name in
 ('EXPECTED.json','QUALIFIED_FINANCIAL_BASE.json','UI_SOURCE.json','consumer_ui_probe.py',
  'workspace_http_cases.py','browser_fixture.py','browser_cases.mjs','selector_record_fix.py'))


def original(path,want):
    raw=gzip.decompress((REPO/path).read_bytes());assert sha256(raw).hexdigest()==want
    return json.loads(raw)


def qualified_source():
    binding=json.loads((HERE/'QUALIFIED_FINANCIAL_BASE.json').read_bytes())
    assert binding['classification']=='ACTUAL_AUTH14_AND_SQL_RACE2_WITH_EXACT_NATIVE18_FINANCIAL_SOURCE_NOT_NEW_UI_QUALIFICATION'
    race=original(binding['race_original_report'],binding['race_original_report_sha256'])
    auth=original(binding['auth_original_report'],binding['auth_original_report_sha256'])
    assert race['candidate_commit']==binding['race_candidate']and auth['candidate_commit']==binding['auth_candidate']
    assert race['status']==auth['status']=='PASS'and race['races']['counts']=={'PASS':2}and auth['http']['counts']=={'PASS':14}
    assert race['observed_case_count']==race['expected_case_count']==2 and auth['observed_case_count']==auth['expected_case_count']==14
    for report in(race,auth):
        assert report['cp6_restored']and report['advisor_gate']and report['required_case_ids_pass']
        assert report['consumer_exact_preuse_restore']['status']=='EXACT_PREUSE_RESTORE'
    assert auth['http']['real_auth']and not auth['http']['jwt_signed_by_runtime']and not auth['http']['test_only_usage_grant']
    assert auth['http']['auth_counts']['restored']and not auth['http']['cleanup_failures']and auth['http']['database_remaining']==0
    assert race['races']['database_remaining']==0 and all(row['status']=='PASS'and row['actual_holder_blocks_worker']
        and row['complete_holder_state_equals_final']and row['worker_additional_effects']==0 and row['session_leaks']==[]
        for row in race['races']['races'].values())
    native_binding=auth['qualified_native_binding']
    native=original(native_binding['original_report'],native_binding['original_report_sha256'])
    assert native['candidate_commit']==binding['native_candidate']and native['status']=='PASS'
    assert native['native']['counts']=={'PASS':18}and native['observed_case_count']==native['expected_case_count']==18
    assert native['cp6_restored']and native['advisor_gate']and native['required_case_ids_pass']
    assert race['consumer_sources']==auth['consumer_sources']==native['consumer_sources']
    old=auth['consumer_sources'];now=consumer.sources()
    assert set(now)==set(old)|{'13_workspace.sql'}
    assert all(now[k]==v for k,v in old.items()if k not in('composition.py','07_locked_projection.sql')),'CONSUMER_EXISTING_FINANCIAL_SOURCE_CHANGED'
    old_selector=subprocess.check_output(['git','-C',str(REPO),'show',binding['auth_candidate']+':scripts/cp7_customer_credit/consumer/07_locked_projection.sql'],text=True)
    assert sha256(old_selector.encode()).hexdigest()==old['07_locked_projection.sql']
    assert selector_record_fix.derive(old_selector)==(consumer.HERE/'07_locked_projection.sql').read_text(),\
        'CONSUMER_SELECTOR_CHANGE_NOT_EXACT_TYPED_OPTIONAL_TARGET_FIX'
    # Admit exactly the two source-declared readonly function additions, not a
    # wildcard exception for installer changes or a relaxed financial callback.
    old_text=subprocess.check_output(['git','-C',str(REPO),'show',binding['auth_candidate']+':scripts/cp7_customer_credit/consumer/composition.py'],text=True)
    assert sha256(old_text.encode()).hexdigest()==old['composition.py']
    expected=old_text.replace("'12_payment_restatement_preflight.sql')","'12_payment_restatement_preflight.sql','13_workspace.sql')")
    expected=expected.replace("'public.erp_cp7_customer_credit_command_v1(jsonb,uuid,jsonb)')", "'public.erp_cp7_customer_credit_command_v1(jsonb,uuid,jsonb)',\n          'public.erp_cp7_get_customer_credit_workspace_v1(jsonb)')")
    assert expected!=old_text and(consumer.HERE/'composition.py').read_text()==expected,'CONSUMER_COMPOSITION_DELTA_NOT_EXACT_TWO_READ_FUNCTIONS'
    for prefix in('race','auth'):
        assert transport.git('rev-parse',binding[prefix+'_candidate']+'^{tree}')==binding[prefix+'_tree']
    manifest_raw=(HERE/'UI_SOURCE.json').read_bytes();manifest=json.loads(manifest_raw)
    assert manifest['classification']=='EXACT_NEW_CONSUMER_UI_AND_QUALIFIER_SOURCE_NOT_EXECUTION'
    assert set(manifest['files'])==set(PRODUCT)|set(HARNESS)-{'scripts/ow04-consumer-ui-qualification/UI_SOURCE.json'}
    for path,want in manifest['files'].items():assert sha256((REPO/path).read_bytes()).hexdigest()==want,('UI_SOURCE_CHANGED',path)
    changed=transport.git('diff','--name-only',binding['race_candidate'],'HEAD','--','scripts','src','supabase','tests').splitlines()
    assert set(changed)<=set(PRODUCT)|set(HARNESS),('UNDECLARED_CONSUMER_UI_PRODUCT_CHANGE',changed)
    assert not transport.git('status','--porcelain','--','src','scripts/cp7_customer_credit','scripts/ow04-consumer-ui-qualification','tests/fixtures/customerCredit.ts')
    assert len(consumer.new_function_names())==47
    declaration=business.expected()
    assert tuple(native['required_case_ids'])==native_business.IDS and len(native_business.IDS)==18
    assert tuple(auth['required_case_ids'])==transport.business.IDS and len(transport.business.IDS)==14
    assert tuple(race['required_case_ids'])==race_business.IDS and len(race_business.IDS)==2
    race_business.expected();transport.business.expected()
    assert sha256(Path(native_business.__file__).read_bytes()).hexdigest()==native['case_source_sha256']
    assert tuple(re.findall(r"\['(OW04_CONSUMER_BROWSER_[A-Z_]+)'",(HERE/'browser_cases.mjs').read_text()))==business.BROWSER_IDS
    return dict(binding=binding,original_financial_sources=old,new_sources=now,
                ui_source_manifest_sha256=sha256(manifest_raw).hexdigest(),ui_source_files=manifest['files'],
                declaration_sha256=business.EXPECTED_SHA256,expected_http=declaration['http_case_ids'],
                expected_browser=declaration['browser_case_ids'],financial_source_delta='EXACT_TYPED_OPTIONAL_TARGET_RECORD_BINDING_FIX_ONLY',
                posting_projection_permission_date_and_money_expressions_unchanged=True,
                retained_current_source_groups_scheduled=dict(Native=18,Auth_HTTP=14,SQL_races=2))


def group_pass(group,ids,browser=False):
    return group.get('status')in('PASS','RUN_COMPLETE')and group.get('counts')=={'PASS':len(ids)}\
        and set(group.get('cases',{}))==set(ids)and group.get('real_auth')is True\
        and group.get('jwt_signed_by_runtime')is False and group.get('test_only_usage_grant')is False\
        and group.get('database_remaining',1)==0 and(group.get('auth_counts')or{}).get('restored')is True\
        and not group.get('cleanup_failures')and(not browser or(group.get('host_exit')==0 and group.get('host_status')=='RUN_COMPLETE'and not group.get('auth_cleanup_failures')))


def run():
    accepted=qualified_source()
    assert os.environ.get('AUDITOR_UI_MODE')=='ENTENG','CURRENT_PRODUCT_ENTENG_LOOPBACK_BUILD_REQUIRED'
    report=dict(label='CP7_OW04_CONSUMER_CURRENT42',status='INCOMPLETE',candidate_commit=transport.git('rev-parse','HEAD'),
        expected_case_count=42,expected_native_count=18,expected_retained_http_count=14,expected_race_count=2,
        expected_http_count=4,expected_browser_count=4,source_binding=accepted,
        consumer_sources=consumer.sources(),scope='NEW_READONLY_WORKSPACE_AND_CURRENT_PRODUCT_BROWSER_RECOVERY',
        Native18_rerun=True,Auth14_rerun=True,SQL_race2_rerun=True,Native87_rerun=False,
        production_go=False,formal_CP7C_started=False,feature_complete=False,independent_acceptance=False,hosted=False)
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
        report['advisors_with_consumer']=transport.advisors(package.boundary.PG)
        with exact_public_catalog(predecessor.native,retain_raw=True)as catalog:
            report['native']=predecessor.native.strict_group('CP7_CURRENT_CONSUMER_NATIVE18',native_business.cases,transport.verify)
        report['native_public_catalog_comparison']=catalog
        report['retained_http']=modes.run_http(transport.business,transport.verify,'ow04_consumer_current_http14')
        report['races']=modes.run_races(race_business,transport.verify,'ow04_consumer_current_race2')
        report['http']=modes.run_http(business,transport.verify,'ow04_consumer_workspace4')
        previous_hosts=set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))
        report['browser']=modes.run_browser(HERE/'browser_cases.mjs',transport.verify,'ow04_consumer_browser4')
        hosts=[]
        for directory in sorted(set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))-previous_hosts):
            path=directory/'BROWSER.json'
            if not path.is_file():continue
            raw=path.read_bytes();host=json.loads(raw);destination=OUT.parent/('CONSUMER_BROWSER_HOST_'+str(len(hosts)+1)+'.json')
            shutil.copyfile(path,destination)
            hosts.append(dict(receipt=destination.name,sha256=sha256(raw).hexdigest(),report=host))
        report['actual_browser_hosts']=hosts
        report['actual_product_browser_loopback_proven']=any(h['report'].get('ui_mode')=='ENTENG'
            and h['report'].get('real_auth')is True and h['report'].get('product_responses_mocked')is False
            and h['report'].get('enteng_requests_answered_by_loopback',0)>0
            and set(h['report'].get('cases',{}))==set(business.BROWSER_IDS)
            and all(x['status']=='PASS'for x in h['report']['cases'].values())for h in hosts)
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        report['frontend_source_unchanged']=all(sha256((REPO/path).read_bytes()).hexdigest()==want
            for path,want in accepted['ui_source_files'].items())
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['consumer_exact_preuse_restore']=consumer.uninstall_preuse(cur,transport.STATE)
                    report['qualified_predecessor_restored']=predecessor.full.verify(cur,full_state)
                    predecessor.full.rollback_preuse(cur,full_state);conn.commit()
                    report['cp6_restored']=predecessor.restore_state.prove(cur,before,package.boundary.snapshot,core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=transport.advisor_delta(transport.advisors(package.boundary.PG),report['advisors_with_consumer'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        report['observed_case_count']=sum(sum(report.get(k,{}).get('counts',{}).values())for k in('native','retained_http','races','http','browser'))
        current_native=report.get('native',{});current_races=report.get('races',{})
        report['retained_native_current_source_pass']=current_native.get('status')=='PASS'and current_native.get('counts')=={'PASS':18}\
            and set(current_native.get('cases',{}))==set(native_business.IDS)and all(r['full_boundary_restored']and r['public_schema_unchanged']\
            and r['session_leaks']=={'advisory_locks':0,'advisory_lock_keys':[],'other_sessions':[]}for r in current_native.get('cases',{}).values())
        report['retained_races_current_source_pass']=current_races.get('status')in('PASS','RUN_COMPLETE')and current_races.get('counts')=={'PASS':2}\
            and set(current_races.get('races',{}))==set(race_business.IDS)and current_races.get('database_remaining',1)==0
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['frontend_source_unchanged']\
            and report['retained_native_current_source_pass']and report['retained_races_current_source_pass']\
            and group_pass(report.get('retained_http',{}),transport.business.IDS)\
            and group_pass(report.get('http',{}),business.IDS)and group_pass(report.get('browser',{}),business.BROWSER_IDS,True)\
            and report.get('actual_product_browser_loopback_proven'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    qualified_source()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
