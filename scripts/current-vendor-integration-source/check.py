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
        result['status']='PASS_QUALIFIED_SELECTIVE_VENDOR_INTEGRATION'
    return result


if __name__=='__main__':
    assert sys.argv[1:]in([] ,['--sources-only'])
    print(json.dumps(check(bool(sys.argv[1:]))))
