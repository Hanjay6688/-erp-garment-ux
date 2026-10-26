"""Complete qualified parent plus exact new reader and five focused cases."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,subprocess

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def admitted(repo,here,ids,product,business):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.d17-18.progress-native5-qualification.v1'
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==5
    assert pins['full_final_acceptance']is pins['actual_Auth_HTTP_credit']is pins['production_go']is False
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',pins['product_parent'],'HEAD'],text=True).splitlines()
    assert all(p.startswith('scripts/current-frozen-progress-native-qualification/')or p=='.github/workflows/cp7-d17-18-progress-native.yml'for p in changed)
    old=load('qualified_public_progress_parent',repo/'scripts/current-frozen-public-native-qualification/probe.py').admitted()
    assert old['current_installation']==product.predecessor.sources()
    proof=pins['actual_predecessor'];raw=Path(os.environ['D17_18_PROGRESS_NATIVE52_ORIGINAL']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']==proof['status']=='PASS'and actual['qualification_commit']==proof['head']
    assert actual['label']=='CP7_CURRENT_FROZEN_PUBLIC_FINANCE_NATIVE52'
    assert actual['source_declaration']['current_installation']==product.predecessor.sources()
    assert actual['source_declaration']['qualification']==old['qualification']
    assert actual['native']['counts']=={'PASS':52}and actual['required_case_ids_pass']
    assert actual['expected_case_count']==actual['observed_case_count']==52
    assert set(actual['native']['cases'])==set(old['qualification']['case_ids'])
    for row in actual['native']['cases'].values():
        assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']
        assert all(v in (0,[],{})for v in row.get('session_leaks',{}).values())
    for k in ('baseline_full22_all_rows_all_sequences_equal','cp6_restored','advisor_gate','baseline_advisors_equal'):assert actual[k]is True,k
    assert actual['production_go']is actual['independent_acceptance']is False
    return dict(qualification=pins,qualified_parent=old,current_installation=product.sources(),
                actual_parent_verified=proof,focused_case_count=5,retained_native52_rerun=False,
                full_final_acceptance=False,actual_Auth_HTTP_credit=False,production_go=False)

if __name__=='__main__':
    here=Path(__file__).resolve().parent;repo=here.parents[1]
    probe=load('focused_progress_graph',here/'probe.py')
    result=admitted(repo,here,probe.IDS,probe.product,probe.business)
    print(json.dumps(dict(status='ADMITTED_FOCUSED_NATIVE5',source_pins=len(result['qualification']['files']),
                         actual_predecessor=52,production_go=False)))
