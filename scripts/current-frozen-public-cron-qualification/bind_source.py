"""Bind only complete PASS Originals for the exact public Native52 and prior finance10."""
from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.dont_write_bytecode=True;sys.path.insert(0,str(REPO/'scripts'))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    cfg=json.loads((HERE/'CONFIG.json').read_bytes());proofs={};actuals={}
    for kind,key in [('native',cfg['native_variable']),('prior',cfg['prior_variable'])]:
        p=json.loads(Path(getattr(args,kind+'_proof')).read_bytes());raw=Path(getattr(args,kind+'_original')).read_bytes()
        assert len(raw)==p['bytes']and sha256(raw).hexdigest()==p['sha256'];proofs[key]=p;actuals[key]=json.loads(raw)
    probe=load('public_cron_binding_probe',HERE/'probe.py')
    load('public_cron_binding_guard',HERE/'source_guard.py').check(REPO,HERE)
    load('public_cron_binding_evidence',HERE/'evidence.py').validate(REPO,HERE,proofs,actuals,probe.product,probe.IDS)
    parent=json.loads((REPO/cfg['native_path']).read_bytes())
    files=set(parent['files'])|{cfg['native_path'],'.github/workflows/cp7-current-frozen-public-cron.yml'}
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    pins=dict(contract=cfg['contract'],case_ids=list(probe.IDS),
        retained_declaration_sha256=sha256((REPO/cfg['native_path']).read_bytes()).hexdigest(),
        files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},
        actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as out:out.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),cases=1,actual_originals=2)))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in('native-proof','native-original','prior-proof','prior-original'):p.add_argument('--'+name,required=True)
    bind(p.parse_args())
