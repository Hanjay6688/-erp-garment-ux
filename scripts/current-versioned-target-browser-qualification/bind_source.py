"""Bind exact Native36 and two prior browser Originals; no qualified-file rewrites."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,json
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
VARS={'CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT','CURRENT_MODEL_TARGET_BROWSER_ORIGINAL_REPORT','MODEL_TARGET_BROWSER_V2_ORIGINAL_REPORT'}


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    inputs=json.loads(Path(args.bindings).read_bytes());assert set(inputs)==VARS
    parent_path='scripts/current-versioned-target-native-qualification/SOURCE.json';parent=json.loads((REPO/parent_path).read_bytes())
    proofs={};actuals={}
    for variable,row in inputs.items():
        proof=json.loads(Path(row['proof']).read_bytes());raw=Path(row['original']).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw);assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        proofs[variable]=proof;actuals[variable]=actual
    n=actuals['CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT']
    assert proofs['CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT']['head']==n['qualification_commit']==args.expected_native_head
    assert n['source_declaration']['qualification']==parent and n['native']['counts']=={'PASS':36}and n['required_case_ids_pass']
    assert n['observed_case_count']==36 and n['complete_preuse_removal']and n['baseline_full22_all_rows_all_sequences_equal']and n['baseline_advisors_equal']
    assert proofs['MODEL_TARGET_BROWSER_V2_ORIGINAL_REPORT']==parent['actual_qualification_originals']['MODEL_TARGET_BROWSER_V2_ORIGINAL_REPORT']
    old=actuals['CURRENT_MODEL_TARGET_BROWSER_ORIGINAL_REPORT']
    assert old['candidate_commit']==proofs['CURRENT_MODEL_TARGET_BROWSER_ORIGINAL_REPORT']['head']=='f88c4ee99fb5d18cf11caada5fab86ad161b007a'
    assert old['observed_case_count']==6 and old['required_case_ids_pass']
    module=ast.parse((HERE/'probe.py').read_text());groups=ast.literal_eval(next(x.value for x in module.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='GROUPS'for t in x.targets)))
    ids=[x for values in groups.values()for x in values];assert len(ids)==len(set(ids))==6
    files=set(parent['files'])|{parent_path,'.github/workflows/cp7-current-versioned-target-browser.yml'}
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    pins=dict(contract='cp7.current-versioned-target-browser6-qualification.v1',files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},case_ids=ids,actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as f:f.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),cases=6,actual_originals=3)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bindings',required=True);parser.add_argument('--expected-native-head',required=True);bind(parser.parse_args())
