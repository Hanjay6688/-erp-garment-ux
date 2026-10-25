"""Full public Native52 source gate, retained restore source and exact actual reports."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def admitted(repo,here,steps,product,recovery):
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    native=load('full_public_restore_native52_admission',repo/'scripts/current-frozen-public-native-qualification/probe.py')
    predecessor=native.admitted();assert predecessor['current_installation']==product.sources()
    binding=load('full_public_restore_source_binding',here/'source_binding.py').verify()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==cfg['contract']and pins['required_steps']==list(steps)
    assert pins['retained_declaration_sha256']==sha256((repo/cfg['native_path']).read_bytes()).hexdigest()
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    proofs=pins['actual_qualification_originals'];actuals={}
    for key,p in proofs.items():
        raw=Path(os.environ[key]).read_bytes();assert len(raw)==p['bytes']and sha256(raw).hexdigest()==p['sha256'];actuals[key]=json.loads(raw)
    actuals=load('full_public_restore_actual_evidence',here/'evidence.py').validate(repo,here,proofs,actuals,product,steps)
    return dict(qualified_current_frozen_public=predecessor,current_installation=product.sources(),
        recovery=recovery.sources(),qualification=pins,actual_originals_verified=actuals,
        retained_business_source_binding=binding,production_go=False,independent_acceptance=False)
