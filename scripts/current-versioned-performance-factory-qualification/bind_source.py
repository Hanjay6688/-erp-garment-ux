"""Bind six actual PASS suites and the retained first INCOMPLETE factory receipt."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    sys.argv=sys.argv[:1];sys.dont_write_bytecode=True;sys.path[:0]=[str(HERE),str(REPO/'scripts')]
    import evidence,source_guard
    import cp7_current_versioned_performance_installation as product
    config=json.loads((HERE/'CONFIG.json').read_bytes());rows=json.loads(Path(args.bindings).read_bytes())
    source_guard.source_binding();proofs={};actuals={}
    for variable,row in rows.items():
        proof=json.loads(Path(row['proof']).read_bytes());raw=Path(row['original']).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        proofs[variable]=proof;actuals[variable]=json.loads(raw)
    assert proofs[config['native_variable']]['head']==args.expected_native_head
    assert proofs[config['cron_variable']]['head']==args.expected_cron_head
    sources,verified=evidence.validate(REPO,config,proofs,actuals,product)
    tree=ast.parse((HERE/'runner.py').read_text())
    case=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='CASE'for t in n.targets)))
    files={'.github/workflows/cp7-current-versioned-performance-factory.yml'}
    for kind,source in sources.items():files.update(source['files']);files.add(evidence.declaration_path(kind))
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    pins=dict(contract=config['contract'],case_ids=[case],files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},
        actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as f:f.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),cases=1,actual_originals=len(verified),failed_original_preserved=True)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('bindings','expected-native-head','expected-cron-head'):parser.add_argument('--'+name,required=True)
    bind(parser.parse_args())
