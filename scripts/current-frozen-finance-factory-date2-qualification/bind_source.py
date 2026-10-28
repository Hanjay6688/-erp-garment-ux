"""Require all six exact baseline suites, failed factory and actual private Native45."""
from hashlib import sha256
from pathlib import Path
import argparse
import ast
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    sys.argv=sys.argv[:1];sys.path[:0]=[str(HERE),str(REPO/'scripts')]
    native=load('private_frozen_finance_factory_binding_graph',REPO/'scripts/current-frozen-finance-native-qualification/probe.py')
    evidence=load('private_frozen_factory_binding_evidence',HERE/'evidence.py')
    guard=load('private_frozen_factory_binding_guard',HERE/'source_guard.py')
    guard.source_binding()
    config=json.loads((HERE/'CONFIG.json').read_bytes())
    rows=json.loads(Path(args.bindings).read_bytes());proofs={};actuals={}
    for variable,row in rows.items():
        proof=json.loads(Path(row['proof']).read_bytes());raw=Path(row['original']).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        proofs[variable]=proof;actuals[variable]=json.loads(raw)
    variable=config['private_native_variable'];proof=proofs[variable]
    assert proof['head']==args.expected_private_native_head
    intake=json.loads(Path(args.private_native_intake).read_bytes())
    assert all(intake.get(k)==v for k,v in proof.items())
    assert intake['status']=='PASS'and intake['counts']=={'PASS':45}
    assert intake['full22_all_rows_all_sequences_restored']
    assert intake['package_gate']==dict(installed=True,primary_unchanged=True,
        backup_restore_drill=True,security_advisors=True,writer_runtime=True)
    assert intake['production_go']is intake['independent_acceptance']is False
    sources,verified=evidence.validate(REPO,config,proofs,actuals,native.product)
    assert len(verified)==9
    files={'.github/workflows/cp7-current-frozen-finance-factory-date2.yml',
        'scripts/current-frozen-finance-native-qualification/SOURCE.json'}
    for pins in sources.values():files.update(pins['files'])
    previous=load('retained_factory_declaration_paths',REPO/'scripts/current-versioned-performance-factory-qualification/evidence.py')
    for kind in config['followups']:files.add(previous.declaration_path(kind))
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    case=ast.literal_eval(next(n.value for n in ast.parse((HERE/'runner.py').read_bytes()).body
        if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='CASE'for t in n.targets)))
    pins=dict(contract=config['contract'],case_ids=[case],files={path:sha256((REPO/path).read_bytes()).hexdigest()for path in sorted(files)},
        actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as out:out.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND_ACTUAL_NATIVE45_AND_BASELINES',source_pins=len(files),
        actual_prerequisites=9,retained_first_failure=True,production_go=False)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('bindings','expected-private-native-head','private-native-intake'):
        parser.add_argument('--'+name,required=True)
    bind(parser.parse_args())
