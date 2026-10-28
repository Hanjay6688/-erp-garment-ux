"""Selective A money intake; static source matching never grants acceptance."""
from pathlib import Path
from hashlib import sha256
import gzip,json,subprocess,sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
RUNTIME=('scripts/cp7_vendor_receivable/receivable.sql','scripts/cp7_vendor_receivable/native_delta.py','scripts/cp7_vendor_receivable/composition.py')


def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])


def verify_files(overrides=None):
    config=json.loads((HERE/'CONFIG.json').read_bytes())
    def read(path):return overrides[path]if overrides and path in overrides else(ROOT/path).read_bytes()
    for entry in config['imports']:
        raw=read(entry['path'])
        assert len(raw)==entry['bytes']and sha256(raw).hexdigest()==entry['sha256'],entry['path']
        assert raw==git('show',config['prepared_component']+':'+entry['path']),entry['path']
    graph=json.loads(read('scripts/current-finance-combined-browser-qualification/BUILD_SOURCE_3194.json'))
    assert len(graph['files'])==79
    imports={e['path']for e in config['imports']};changed=[]
    for row in graph['files']:
        raw=read(row['path'])
        if row['path']in imports:changed.append(row['path'])
        else:assert len(raw)==row['bytes']and sha256(raw).hexdigest()==row['sha256'],row['path']
    for path in ('src/nativeStagedJob.ts','src/nativeStagedJob.initial.test.ts'):
        assert read(path)==git('show',config['B_browser_qualified_on_old_source']+':'+path),path
    return config,changed


def admit(pin,original,package,runtime_files,parent_digest):
    if pin is None:raise ValueError('VENDOR_INTEGRATION_CLOSED_ACTUAL_COMBINED11_REQUIRED')
    for key,raw in (('original',original),('package',package)):
        assert len(raw)==pin[key]['bytes']and sha256(raw).hexdigest()==pin[key]['sha256'],key
    actual=json.loads(original);pkg=json.loads(package)
    if actual.get('label')!='CP7_VENDOR_RECEIVABLE_COMBINED11'or actual.get('status')!='PASS'or actual.get('qualification_commit')!=pin['head']:
        raise ValueError('VENDOR_INTEGRATION_COMPLETE_COMBINED11_REQUIRED')
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','used_guard_refused_before_DDL','required_case_ids_pass'):
        assert actual.get(key)is True,key
    case=actual['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']
    assert case['status']=='PASS'and case['business_counts']=={'PASS':11}and len(case['business_cases'])==11
    assert all(v['status']=='PASS'for v in case['business_cases'].values())
    assert case['fresh_native7']['native']['counts']=={'PASS':7}
    follow=case['followup4'];assert follow['races']['counts']=={'PASS':3}and follow['http']['counts']=={'PASS':1}
    assert follow['http']['auth_counts']['restored']is True
    assert follow['races']['database_remaining']==follow['http']['database_remaining']==0
    assert not follow['races'].get('cleanup_failures')and not follow['http'].get('cleanup_failures')
    assert case['native_to_followup_handoff']['all22_equal_installed_product']is True
    assert case['native_to_followup_handoff']['committed_Native_business_data_unchanged']is True
    installation=actual['source_declaration']['current_installation']
    assert installation['files']==runtime_files,'OTHER_VENDOR_RUNTIME_REFUSED'
    assert sha256(json.dumps(installation['predecessor'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==parent_digest
    keys=('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')
    assert pkg['gate']=={key:True for key in keys}and pkg['run_identity']['tool_head']==pin['head']
    assert pkg['writer_runtime']['status']=='PASS'and pkg['auth_users_before']==pkg['auth_users_after']
    return dict(status='EXACT_ACTUAL_COMBINED11_ACCEPTABLE_TO_INTEGRATOR',head=pin['head'],fresh_Native=7,fresh_races=3,fresh_Auth_HTTP=1,fresh_browser=0)



def admit_browser(pin,original,package,backend_head,imports,runtime_files,entrypoint):
    if pin is None:raise ValueError('VENDOR_INTEGRATION_CLOSED_ACTUAL_MONEY_BROWSER2_REQUIRED')
    for key,raw in (('original',original),('package',package)):
        assert len(raw)==pin[key]['bytes']and sha256(raw).hexdigest()==pin[key]['sha256'],key
    actual=json.loads(original);pkg=json.loads(package)
    if actual.get('label')!='CP7_VENDOR_MONEY_BROWSER2'or actual.get('status')!='PASS'or actual.get('qualification_commit')!=pin['head']:
        raise ValueError('VENDOR_INTEGRATION_COMPLETE_MONEY_BROWSER2_REQUIRED')
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','required_case_ids_pass','real_Auth_browser_claim','new_vendor_money_UI_qualified'):
        assert actual.get(key)is True,key
    assert actual['actual_browser_cases']==2 and actual['retained_backend11_cases']==11
    source=actual['source_declaration']
    assert source['prerequisite']['head']==backend_head
    assert source['current_installation']['files']==runtime_files
    assert source['current_installation_entrypoint']==entrypoint
    for row in imports:
        if row['path'].startswith('src/'):
            assert source['client_sources'][row['path']]==row['sha256'],row['path']
    group=actual['committed']['VENDOR_MONEY_BROWSER2'];browser=group['browser']
    assert group['status']=='PASS'and browser['counts']=={'PASS':2}
    assert browser['real_auth']is True and browser['test_only_usage_grant']is False and browser['jwt_signed_by_runtime']is False
    assert browser['host_status']=='RUN_COMPLETE'and browser['host_exit']==0 and browser['console_errors']==0
    assert browser['auth_counts']['restored']is True and browser['database_remaining']==0
    assert not any(browser.get(k)for k in ('cleanup_failures','auth_cleanup_failures','session_leaks'))
    assert len(group['copy_catalog_admissions'])==1 and group['copy_catalog_admissions'][0]['all22_groups_equal_original_install']is True
    ids=('VENDOR_MONEY_BROWSER_DESKTOP_REFUND_INVERSE_HISTORY','VENDOR_MONEY_BROWSER_MOBILE_REFUND_ACCESS_HIDDEN')
    assert set(browser['cases'])==set(ids)
    desktop,mobile=(browser['cases'][key]for key in ids)
    for row in (desktop,mobile):
        assert row['status']=='PASS'and row['actual_Auth_login_and_public_RPC']is True and row['actual_refund_posted_from_screen']is True
        assert row['console_evidence']['unexpected_errors']==[]and row['width']['page']<=row['width']['viewport']
        assert row['financial_truth_report_checks_no_new_issues']is True and row['financial_truth_evidence']
        for observation in row['financial_truth_evidence']:
            assert set(observation['counts'])==set(row['financial_truth_before'])
            assert all(v<=row['financial_truth_before'][k]for k,v in observation['counts'].items())
    assert desktop['actual_refund_inverse_from_screen']is True and desktop['actual_committed_reply_lost_reload_same_UUID_once']is True
    assert desktop['actual_next_invoice_credit_from_screen']is True
    assert mobile['actual_access_revoked_and_money_hidden']is True
    assert pkg['gate']=={key:True for key in ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')}
    assert pkg['run_identity']['tool_head']==pin['head']and pkg['writer_runtime']['status']=='PASS'
    assert pkg['auth_users_before']==pkg['auth_users_after']
    return dict(status='EXACT_ACTUAL_MONEY_BROWSER2_ACCEPTABLE_TO_INTEGRATOR',head=pin['head'],backend_head=backend_head,fresh_browser=2,
        direct_existing_complete_installer=True,actual_both_credit_and_refund_inverse_loss_recovery_and_access_revoke=True)

def check(sources_only=False):
    config,changed=verify_files()
    assert not git('status','--porcelain','--untracked-files=no').strip()
    paths=git('diff','--name-only',config['base_head'],'HEAD','--','src','supabase','scripts','package.json','package-lock.json').decode().splitlines()
    allowed={e['path']for e in config['imports']}
    assert all(p in allowed or p.startswith('scripts/current-vendor-integration-source/')for p in paths),'UNDECLARED_VENDOR_INTEGRATION_CHANGE'
    result=dict(status='PREPARED_EXACT_SOURCE_ONLY_NOT_QUALIFIED',head=git('rev-parse','HEAD').decode().strip(),selected_entries=len(config['imports']),
        original_B_graph_files=79,declared_changed_B_graph_files=changed,B_driver_unchanged=True,historical_manifests_rewritten=False,
        new_DB_or_Auth_browser_cases=0,production_go=False,independent_acceptance=False)
    if not sources_only:
        pin=config['qualified_combined11']
        if pin is None:raise ValueError('VENDOR_INTEGRATION_CLOSED_ACTUAL_COMBINED11_REQUIRED')
        def raw(kind):return gzip.decompress((ROOT/pin[kind]['path']).read_bytes())
        result['qualified_component']=admit(pin,raw('original'),raw('package'),
            {p:sha256((ROOT/p).read_bytes()).hexdigest()for p in RUNTIME},config['parent_backend_sha256'])
        browser_pin=config['qualified_money_browser2']
        if browser_pin is None:raise ValueError('VENDOR_INTEGRATION_CLOSED_ACTUAL_MONEY_BROWSER2_REQUIRED')
        result['qualified_money_browser']=admit_browser(browser_pin,
            gzip.decompress((ROOT/browser_pin['original']['path']).read_bytes()),
            gzip.decompress((ROOT/browser_pin['package']['path']).read_bytes()),pin['head'],config['imports'],
            {p:sha256((ROOT/p).read_bytes()).hexdigest()for p in RUNTIME},config['current_installation_entrypoint'])
        result['status']='PASS_QUALIFIED_SELECTIVE_VENDOR_INTEGRATION'
    return result


if __name__=='__main__':
    assert sys.argv[1:]in([] ,['--sources-only'])
    print(json.dumps(check(bool(sys.argv[1:]))))
