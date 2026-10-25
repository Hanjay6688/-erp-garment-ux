"""Bind twelve actual PASS inputs; replace only an explicitly retained failed candidate."""
from pathlib import Path
from hashlib import sha256
import argparse,json,subprocess,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def bind(args):
    source_path=HERE/'SOURCE.json';superseded=None
    if args.superseded_original or args.superseded_proof:
        assert args.superseded_original and args.superseded_proof
        proof=json.loads(Path(args.superseded_proof).read_bytes())
        raw=Path(args.superseded_original).read_bytes();failed=json.loads(raw)
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        assert failed['status']==proof['status']=='INCOMPLETE'
        assert failed['qualification_commit']==proof['head']
        superseded=source_path.read_bytes()
        assert json.loads(superseded)==failed['source_declaration']['qualification']
        assert superseded==subprocess.check_output(['git','-C',str(REPO),'show','HEAD:scripts/current-versioned-target-native-qualification/SOURCE.json'])
    else:assert not source_path.exists(),'SOURCE_ALREADY_BOUND'
    sys.argv=sys.argv[:1];sys.dont_write_bytecode=True
    sys.path.insert(0,str(REPO/'scripts'));sys.path.insert(0,str(HERE))
    import admission,cases,frozen_admission
    import cp7_current_versioned_target_installation as product
    inputs=json.loads(Path(args.bindings).read_bytes());assert set(inputs)==admission.VARIABLES
    parent_path='scripts/current-scoped-model-native-qualification/SOURCE.json'
    parent=json.loads((REPO/parent_path).read_bytes());proofs={};actuals={}
    for variable,row in inputs.items():
        proof=json.loads(Path(row['proof']).read_bytes());raw=Path(row['original']).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw)
        assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        assert actual['production_go']is False and actual['independent_acceptance']is False
        proofs[variable]=proof;actuals[variable]=actual
    variable='CURRENT_SCOPED_MODEL_ORIGINAL_REPORT';p=proofs[variable];n=actuals[variable]
    assert p['head']==n['qualification_commit']==frozen_admission.FROZEN_HEAD
    assert n['source_declaration']['qualification']==parent
    assert n['source_declaration']['current_installation']==product.predecessor.sources()
    assert n['native']['counts']=={'PASS':30}and n['observed_case_count']==30
    assert n['required_case_ids']==list(cases.previous.IDS)and n['required_case_ids_pass']and n['complete_preuse_removal']
    assert n['baseline_full22_all_rows_all_sequences_equal']and n['baseline_advisors_equal']
    for row in n['native']['cases'].values():assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']
    variable='CURRENT_SCOPED_MODEL_RESTORE_ORIGINAL_REPORT';p=proofs[variable];r=actuals[variable]
    assert p['head']==r['candidate_commit']==args.expected_restore_head
    assert r['label']=='CP7_CURRENT_SCOPED_MODEL_USED_RESTORE8'
    assert r['source_declaration']['current_installation']==product.predecessor.sources()
    assert r['source_declaration']['qualification']['actual_qualification_originals']['CURRENT_SCOPED_MODEL_ORIGINAL_REPORT']==proofs['CURRENT_SCOPED_MODEL_ORIGINAL_REPORT']
    assert r['required_steps_pass']and len(r['steps'])==8 and all(x['status']=='PASS'for x in r['steps'])
    assert r['baseline_full22_all_rows_all_sequences_equal']and r['baseline_advisors_equal']and r['restore_raw_public_equal']
    for variable in admission.SELECTED_VARIABLES:
        actual=actuals[variable];proof=proofs[variable]
        assert(actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']
        assert actual['source_declaration']['current_installation']['delta']==product.selected.delta.sources()
        assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        if variable=='CURRENT_SELECTED_RETURN_CONTRACT_ORIGINAL_REPORT':
            assert proof['head']=='e0a4721f586476b36de2f5941d4970ea7de2bb8e'
            assert actual['baseline']['counts']==actual['native']['counts']=={'PASS':6}and actual['execution_count']==12
            assert actual['required_case_ids']==list(cases.selected_contract.IDS)and actual['required_case_ids_pass']
        elif variable=='CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT':
            assert proof['head']=='8e878ed6c95a7249734f5d53b5d33ee1114ec599'
            assert actual['native']['counts']=={'PASS':20}and actual['observed_case_count']==20 and actual['required_case_ids_pass']
        else:
            assert proof['head']==args.expected_selected_restore_head
            assert actual['label']=='CP7_CURRENT_SELECTED_RETURN_USED_RESTORE8'
            assert actual['required_steps_pass']and len(actual['steps'])==8 and all(row['status']=='PASS'for row in actual['steps'])
            assert actual['source_declaration']['qualification']['actual_qualification_originals']['CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT']==proofs['CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT']
    for variable,actual in actuals.items():
        if variable.startswith('CURRENT_SCOPED_MODEL_')or variable in admission.SELECTED_VARIABLES:continue
        expected=(admission.transport.PARTS[admission.TRANSPORT_VARIABLES[variable]]if variable in admission.TRANSPORT_VARIABLES else admission.PROVIDERS[variable].IDS)
        assert actual['required_case_ids']==expected and actual['required_case_ids_pass']and actual['required_case_counts_pass']
        assert actual['observed_case_count']==sum(map(len,expected.values()))
        for group,names in expected.items():assert actual[group]['counts']=={'PASS':len(names)}
    changes={p:dict(frozen_sha256=d,current_sha256=sha256((REPO/p).read_bytes()).hexdigest())for p,d in parent['files'].items()if sha256((REPO/p).read_bytes()).hexdigest()!=d}
    assert changes==json.loads((HERE/'EXPLICIT_CURRENT_SOURCE_CHANGES.json').read_bytes())
    files=set(parent['files'])|{parent_path,'.github/workflows/cp7-current-versioned-target-native.yml','scripts/cp7_current_versioned_target_installation.py','scripts/cp7_current_versioned_target_delta.py','scripts/cp7_current_versioned_target_recovery.py'}
    files.update(subprocess.check_output(['git','-C',str(REPO),'ls-files','scripts','src'],text=True).splitlines())
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    files.discard(str((HERE/'SOURCE.json').relative_to(REPO)))
    manifest=dict(contract=admission.CONTRACT,files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},case_ids=list(cases.IDS),
        frozen_declaration=dict(path=parent_path,head=frozen_admission.FROZEN_HEAD,sha256=sha256((REPO/parent_path).read_bytes()).hexdigest()),
        explicit_current_source_changes=changes,actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    cases.source_binding()
    if superseded is not None:
        assert source_path.read_bytes()==superseded,'SUPERSEDED_SOURCE_CHANGED_DURING_BINDING'
        source_path.unlink()
    with source_path.open('x')as f:f.write(json.dumps(manifest,indent=2)+'\n')
    assert len(cases.IDS)==36
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),cases=36,actual_originals=len(proofs))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bindings',required=True);parser.add_argument('--expected-restore-head',required=True)
    parser.add_argument('--expected-selected-restore-head',required=True)
    parser.add_argument('--superseded-proof');parser.add_argument('--superseded-original')
    bind(parser.parse_args())
