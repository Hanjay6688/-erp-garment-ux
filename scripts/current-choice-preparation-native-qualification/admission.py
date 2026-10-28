"""Exact complete progress predecessor plus the optional A/B preparation layer."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,subprocess

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def admitted(repo,here,ids,product,business):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.d17-18.choice-preparation-native6-qualification.v1'
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==6
    assert pins['full_final_acceptance']is pins['actual_Auth_HTTP_credit']is pins['production_go']is False
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    business.observation.verify_ready_source()
    fixture=json.loads((here/'B_FIXTURE_SOURCE.json').read_bytes())
    for path,digest in fixture['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert fixture['head']==product.sources()['B_source']['head']
    assert fixture['existing_B_case_routes_replaced']is False
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',pins['product_parent'],'HEAD'],text=True).splitlines()
    for path in changed:
        assert(path.startswith('scripts/current-choice-preparation-native-qualification/')
            or path in fixture['files']or path in pins['retained_progress_files']
            or path=='.github/workflows/cp7-d17-18-choice-preparation-native.yml'),path
    for path,digest in pins['retained_progress_files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    retained=repo/'scripts/current-frozen-progress-native-qualification/SOURCE.json'
    declared=json.loads(retained.read_bytes())
    # Its original admission restricts the old product-to-harness diff. Keep it
    # unchanged; validate its actual PASS and exact sources on this successor.
    for path,digest in declared['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    old=load('qualified_public_choice_parent',repo/'scripts/current-frozen-public-native-qualification/probe.py').admitted()
    assert old['current_installation']==product.predecessor.predecessor.sources()
    proof=pins['actual_predecessor'];raw=Path(os.environ['D17_18_CHOICE_PROGRESS_NATIVE5_ORIGINAL']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']==proof['status']=='PASS'and actual['qualification_commit']==proof['head']
    assert actual['label']=='CP7_D17_18_PROGRESS_NATIVE5'
    source=actual['source_declaration']
    assert source['qualification']==declared
    assert source['current_installation']==product.predecessor.sources()
    assert source['qualified_parent']==old
    assert actual['native']['counts']=={'PASS':5}and actual['required_case_ids_pass']
    assert actual['expected_case_count']==actual['observed_case_count']==5
    assert set(actual['native']['cases'])==set(declared['case_ids'])
    for row in actual['native']['cases'].values():
        assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']
        assert all(v in(0,[],{})for v in row.get('session_leaks',{}).values())
    for key in('baseline_full22_all_rows_all_sequences_equal','cp6_restored','advisor_gate','baseline_advisors_equal'):
        assert actual[key]is True,key
    assert actual['complete_preuse_removal']and actual['production_go']is actual['independent_acceptance']is False
    return dict(qualification=pins,qualified_public_parent=old,current_installation=product.sources(),
                actual_parent_verified=proof,B_fixture_source=fixture,focused_case_count=6,
                retained_progress_native5_rerun=False,full_final_acceptance=False,
                actual_Auth_HTTP_credit=False,production_go=False)

if __name__=='__main__':
    here=Path(__file__).resolve().parent;repo=here.parents[1]
    probe=load('focused_choice_graph',here/'probe.py')
    result=admitted(repo,here,probe.IDS,probe.product,probe.business)
    print(json.dumps(dict(status='ADMITTED_FOCUSED_NATIVE6',source_pins=len(result['qualification']['files']),
                         actual_predecessor=5,production_go=False)))
