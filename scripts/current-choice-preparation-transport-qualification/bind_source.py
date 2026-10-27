from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.dont_write_bytecode=True
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    cfg=json.loads((HERE/'CONFIG.json').read_bytes())
    assert cfg['choice_head']is not None,'ACTUAL_NATIVE6_PASS_REQUIRED_BEFORE_BINDING'
    proof=json.loads(Path(args.proof).read_bytes());raw=Path(args.original).read_bytes()
    probe=load('choice_transport_binding_probe',HERE/'probe.py')
    load('choice_transport_binding_evidence',HERE/'evidence.py').validate(REPO,HERE,proof,raw,probe.product,probe.qualified_native.admitted())
    parent=json.loads((REPO/cfg['choice_declaration']).read_bytes())
    files=set(parent['files'])|{cfg['choice_declaration'],'.github/workflows/cp7-d17-18-choice-preparation-transport.yml'}
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    pins=dict(contract=cfg['contract'],case_ids=cfg['case_ids'],actual_predecessor=proof,
        files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as out:out.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='BOUND_TO_ACTUAL_NATIVE6_PASS',source_files=len(files),cases=6)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--proof',required=True);p.add_argument('--original',required=True)
    args=p.parse_args();sys.argv=sys.argv[:1];bind(args)
