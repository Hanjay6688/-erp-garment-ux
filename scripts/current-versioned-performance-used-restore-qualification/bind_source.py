"""Bind only complete actual PASS Originals; refuse to replace a prior SOURCE."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,json

CONFIG = {'parent': 'current-versioned-performance-native-qualification', 'workflow': 'cp7-current-versioned-performance-restore.yml', 'recovery': 'cp7_current_versioned_performance_recovery.py', 'contract': 'cp7.current-versioned-performance-used-restore8-qualification.v1', 'count': 36, 'native_variable': 'CURRENT_VERSIONED_PERFORMANCE_NATIVE_ORIGINAL_REPORT', 'restore_variable': 'CURRENT_VERSIONED_TARGET_RESTORE_ORIGINAL_REPORT'}
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def original(proof_path,raw_path,head):
    proof=json.loads(Path(proof_path).read_bytes());raw=Path(raw_path).read_bytes()
    assert len(raw)==proof['bytes'] and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']==proof['status']=='PASS'
    assert (actual.get('qualification_commit') or actual.get('candidate_commit'))==proof['head']==head
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):
        assert actual[key]is True,key
    return proof,actual


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    native,n=original(args.native_proof,args.native_original,args.expected_native_head)
    restore,r=original(args.restore_proof,args.restore_original,args.expected_restore_head)
    parent_path='scripts/'+CONFIG['parent']+'/SOURCE.json'
    parent=json.loads((REPO/parent_path).read_bytes())
    assert n['source_declaration']['qualification']==parent
    assert parent['actual_qualification_originals'][CONFIG['restore_variable']]==restore
    assert n['native']['counts']=={'PASS':CONFIG['count']}
    assert n['observed_case_count']==CONFIG['count'] and n['required_case_ids_pass']
    assert n['required_case_ids']==parent['case_ids'] and n['complete_preuse_removal']
    for case in n['native']['cases'].values():
        assert case['status']=='PASS' and case['full_boundary_restored'] and case['public_schema_unchanged']
    module=ast.parse((HERE/'probe.py').read_text())
    assignment=next(x for x in module.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='STEPS'for t in x.targets))
    steps=list(ast.literal_eval(assignment.value));assert len(steps)==8
    assert r['required_steps_pass'] and r['required_steps']==steps
    assert [row['step']for row in r['steps']]==steps and all(row['status']=='PASS'for row in r['steps'])
    files=set(parent['files'])|{parent_path,'scripts/'+CONFIG['recovery'],'.github/workflows/'+CONFIG['workflow']}
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    declaration=dict(contract=CONFIG['contract'],files={f:sha256((REPO/f).read_bytes()).hexdigest()for f in sorted(files)},
        required_steps=steps,actual_qualification_originals={CONFIG['native_variable']:native,CONFIG['restore_variable']:restore},
        production_go=False,independent_acceptance=False)
    # Exclusive creation is intentional: a failed/new candidate gets a new commit,
    # never an unnoticed overwrite of the previously admitted declaration.
    with(HERE/'SOURCE.json').open('x')as f:f.write(json.dumps(declaration,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),steps=8,native_head=native['head'],restore_head=restore['head'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('native-proof','native-original','restore-proof','restore-original','expected-native-head','expected-restore-head'):parser.add_argument('--'+name,required=True)
    bind(parser.parse_args())
