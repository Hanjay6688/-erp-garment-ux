from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def admitted(repo,here,ids,product,native,groups):
    cfg=json.loads((here/'CONFIG.json').read_bytes());parent=native.admitted()
    assert parent['current_installation']==product.sources() and groups==cfg['groups']
    guard=load('A_finance_UI_source_guard',here/'source_guard.py').check(repo,here)
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==cfg['contract'] and pins['case_ids']==list(ids)
    for kind in ('native','finance'):assert pins[kind+'_declaration_sha256']==sha256((repo/cfg[kind+'_path']).read_bytes()).hexdigest()
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    proofs=pins['actual_qualification_originals'];actuals={}
    for key,p in proofs.items():
        raw=Path(os.environ[key]).read_bytes();assert len(raw)==p['bytes'] and sha256(raw).hexdigest()==p['sha256'];actuals[key]=json.loads(raw)
    verified=load('A_finance_UI_actual_evidence',here/'evidence.py').validate(repo,here,proofs,actuals,product,ids)
    return dict(qualified_current_frozen_public=parent,current_installation=product.sources(),qualification=pins,
                actual_originals_verified=verified,source_guard=guard,new_public_finance_UI_qualification=True,
                actual_cron_claim=False,default_adopted=False,production_go=False,independent_acceptance=False)
