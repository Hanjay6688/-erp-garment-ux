"""Bind actual full Native36/restore8 and five exact B Original reports once."""
from pathlib import Path
from hashlib import sha256
import argparse,json,subprocess,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    sys.argv=sys.argv[:1];sys.dont_write_bytecode=True
    sys.path[:0]=[str(HERE),str(REPO/'scripts')]
    import admission,cases
    import cp7_current_versioned_performance_installation as product
    inputs=json.loads(Path(args.bindings).read_bytes());assert set(inputs)==admission.VARIABLES
    proofs={};actuals={}
    for variable,row in inputs.items():
        proof=json.loads(Path(row['proof']).read_bytes());raw=Path(row['original']).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw);assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        assert actual['production_go']is actual['independent_acceptance']is False
        proofs[variable]=proof;actuals[variable]=actual
        if variable in admission.B_CONTRACTS:assert proof==admission.B_CONTRACTS[variable]['proof']
    p=proofs[admission.A_NATIVE];n=actuals[admission.A_NATIVE];r=actuals[admission.A_RESTORE]
    assert p['head']==n['qualification_commit']==args.expected_native_head
    assert proofs[admission.A_RESTORE]['head']==r['candidate_commit']==args.expected_restore_head
    path='scripts/current-versioned-target-native-qualification/SOURCE.json';parent=json.loads((REPO/path).read_bytes())
    assert n['source_declaration']['qualification']==parent
    assert n['source_declaration']['current_installation']==r['source_declaration']['current_installation']==product.predecessor.sources()
    assert n['native']['counts']=={'PASS':36}and n['observed_case_count']==36 and n['required_case_ids']==list(cases.IDS)and n['required_case_ids_pass']
    assert r['required_steps_pass']and len(r['steps'])==8 and all(row['status']=='PASS'for row in r['steps'])
    assert r['source_declaration']['qualification']['actual_qualification_originals'][admission.A_NATIVE]==p
    for rel,digest in parent['files'].items():assert sha256((REPO/rel).read_bytes()).hexdigest()==digest,rel
    files=set(parent['files'])|{path,'.github/workflows/cp7-current-versioned-performance-native.yml'}
    files.update(subprocess.check_output(['git','-C',str(REPO),'ls-files','scripts','src'],text=True).splitlines())
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    manifest=dict(contract=admission.CONTRACT,files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},case_ids=list(cases.IDS),
        frozen_declaration=dict(path=path,head=p['head'],sha256=sha256((REPO/path).read_bytes()).hexdigest()),
        B_frozen_head=admission.B_HEAD,actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    cases.source_binding();product.sources()
    with(HERE/'SOURCE.json').open('x')as f:f.write(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),cases=36,actual_originals=len(proofs))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bindings',required=True)
    parser.add_argument('--expected-native-head',required=True);parser.add_argument('--expected-restore-head',required=True)
    bind(parser.parse_args())
