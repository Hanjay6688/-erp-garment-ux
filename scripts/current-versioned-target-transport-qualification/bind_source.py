"""Bind four exact actual reports once; never alter already qualified files."""
from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    sys.argv=sys.argv[:1];sys.path.insert(0,str(REPO/'scripts'))
    spec=importlib.util.spec_from_file_location('versioned_transport_cases_binding',HERE/'cases.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
    spec=importlib.util.spec_from_file_location('versioned_transport_admission_binding',HERE/'admission.py');admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
    inputs=json.loads(Path(args.bindings).read_bytes());assert set(inputs)==admission.VARS
    parent_path='scripts/current-versioned-target-native-qualification/SOURCE.json';parent=json.loads((REPO/parent_path).read_bytes());proofs={};actuals={}
    for variable,row in inputs.items():
        proof=json.loads(Path(row['proof']).read_bytes());raw=Path(row['original']).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw);assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        proofs[variable]=proof;actuals[variable]=actual
    n=actuals['CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT']
    assert n['qualification_commit']==proofs['CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT']['head']==args.expected_native_head
    assert n['source_declaration']['qualification']==parent and n['native']['counts']=={'PASS':36}and n['observed_case_count']==36
    assert n['required_case_ids_pass']and n['complete_preuse_removal']and n['baseline_full22_all_rows_all_sequences_equal']and n['baseline_advisors_equal']
    old=actuals['CURRENT_MODEL_TARGET_TRANSPORT_ORIGINAL_REPORT']
    assert old['candidate_commit']==proofs['CURRENT_MODEL_TARGET_TRANSPORT_ORIGINAL_REPORT']['head']=='6e30a61b0f6c1bbcc50b3a6a82c0ebd52af47ae3'
    assert old['observed_case_count']==28 and old['required_case_ids_pass']
    for variable in admission.PARTS:assert proofs[variable]==parent['actual_qualification_originals'][variable]
    files=set(parent['files'])|{parent_path,'.github/workflows/cp7-current-versioned-target-transport.yml'}
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file());transport.source_binding()
    pins=dict(contract='cp7.current-versioned-target-transport28-qualification.v1',files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},case_ids=list(transport.IDS),groups=transport.GROUPS,actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as f:f.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),cases=28,actual_originals=4)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bindings',required=True);parser.add_argument('--expected-native-head',required=True);bind(parser.parse_args())
