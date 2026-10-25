"""Exact current public Native52 plus full prior browser/transport Original."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def admitted(repo,here,ids,product,native,business):
    cfg=json.loads((here/'CONFIG.json').read_bytes());parent=native.admitted()
    assert parent['current_installation']==product.sources()
    retained=load('public_retained_browser_transport_guard',here/'source_guard.py').check(repo,here)
    pins=json.loads((here/'SOURCE.json').read_bytes());assert pins['contract']==cfg['contract']and pins['case_ids']==list(ids)
    assert pins['retained_declaration_sha256']==sha256((repo/cfg['native_path']).read_bytes()).hexdigest()
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    proofs=pins['actual_qualification_originals'];actuals={}
    for key,p in proofs.items():
        raw=Path(os.environ[key]).read_bytes();assert len(raw)==p['bytes']and sha256(raw).hexdigest()==p['sha256'];actuals[key]=json.loads(raw)
    verified=load('public_browser_transport_evidence',here/'evidence.py').validate(repo,here,proofs,actuals,product,ids)
    if cfg['kind']=='transport':retained['retained_body_binding']=business.source_binding()
    return dict(qualified_current_frozen_public=parent,current_installation=product.sources(),qualification=pins,
        actual_originals_verified=verified,retained_business_source_binding=retained,
        retained_business_routes_only=True,new_public_finance_UI_claim=False,default_adopted=False,
        production_go=False,independent_acceptance=False)
