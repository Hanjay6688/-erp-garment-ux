"""Bind actual Native36 and exact prior PASS without modifying qualified files."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,json
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def checked(proof_path,raw_path,expected_head):
    proof=json.loads(Path(proof_path).read_bytes());raw=Path(raw_path).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']and actual['restore_raw_public_equal']
    assert(actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']==expected_head
    return proof,actual


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    config=json.loads((HERE/'CONFIG.json').read_bytes())
    proof,n=checked(args.native_proof,args.native_original,args.expected_native_head)
    prior,old=checked(args.prior_proof,args.prior_original,config['old_head'])
    parent_path='scripts/current-versioned-target-native-qualification/SOURCE.json'
    parent=json.loads((REPO/parent_path).read_bytes())
    assert n['source_declaration']['qualification']==parent and n['native']['counts']=={'PASS':36}
    assert n['required_case_ids_pass']and n['observed_case_count']==36 and n['complete_preuse_removal']
    assert n['baseline_full22_all_rows_all_sequences_equal']and n['baseline_advisors_equal']
    tree=ast.parse((HERE/config['helper']).read_text())
    target='IDS'if config['kind']=='finance'else'CASE'
    node=next(x.value for x in tree.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id==target for t in x.targets))
    if target=='IDS':
        assert isinstance(node,ast.Call)and isinstance(node.func,ast.Name)and node.func.id=='dict'and not node.args
        assert [k.arg for k in node.keywords]==['http','races']
        value={k.arg:ast.literal_eval(k.value)for k in node.keywords}
        assert all(isinstance(v,list)and all(isinstance(x,str)for x in v)for v in value.values())
    else:value=ast.literal_eval(node)
    ids=[x for group in value.values()for x in group]if isinstance(value,dict)else[value]
    assert len(ids)==config['count']and old['required_case_ids_pass']and old['required_case_ids']==ids and old['observed_case_count']==len(ids)
    files=set(parent['files'])|{parent_path,'.github/workflows/cp7-current-versioned-target-'+config['kind']+'-admission2.yml'}
    files.add('scripts/cp7_current_transport_original_schema.py')
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    pins=dict(contract=config['contract'],case_ids=ids,files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},
        actual_qualification_originals={config['native_variable']:proof,config['old_variable']:prior},production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as f:f.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),cases=len(ids),actual_originals=2)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('native-proof','native-original','prior-proof','prior-original','expected-native-head'):parser.add_argument('--'+name,required=True)
    bind(parser.parse_args())
