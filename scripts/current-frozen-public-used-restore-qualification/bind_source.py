"""Bind the complete public Native52 and prior full used restore8 Originals."""
from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];sys.path.insert(0,str(REPO/'scripts'))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    cfg=json.loads((HERE/'CONFIG.json').read_bytes());proofs={};actuals={}
    for name,key in [('native',cfg['native_variable']),('prior',cfg['prior_variable'])]:
        proof=json.loads(Path(getattr(args,name+'_proof')).read_bytes());raw=Path(getattr(args,name+'_original')).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'];proofs[key]=proof;actuals[key]=json.loads(raw)
    probe=load('public_restore_binding_probe',HERE/'probe.py')
    load('public_restore_binding_source',HERE/'source_binding.py').verify()
    load('public_restore_binding_evidence',HERE/'evidence.py').validate(REPO,HERE,proofs,actuals,probe.composed,probe.STEPS)
    parent=json.loads((REPO/cfg['native_path']).read_bytes())
    files=set(parent['files'])|{cfg['native_path'],'.github/workflows/cp7-current-frozen-public-restore.yml'}
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    files.update(str(p.relative_to(REPO))for p in(REPO/'scripts').glob('cp7_current_frozen_public_recovery*')if p.is_file())
    pins=dict(contract=cfg['contract'],required_steps=list(probe.STEPS),
        retained_declaration_sha256=sha256((REPO/cfg['native_path']).read_bytes()).hexdigest(),
        files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},
        actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as out:out.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),steps=8,actual_originals=2)))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in('native-proof','native-original','prior-proof','prior-original'):p.add_argument('--'+name,required=True)
    args=p.parse_args()
    # Imported qualification probes enforce their own zero-argument contract.
    sys.argv=sys.argv[:1]
    bind(args)
