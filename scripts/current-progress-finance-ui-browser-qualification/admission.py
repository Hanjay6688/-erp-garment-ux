from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def admitted(repo,here,ids,product,native,groups):
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    assert cfg['choice_head'] is not None,'ACTUAL_NATIVE6_PASS_REQUIRED_BEFORE_BINDING'
    assert groups==cfg['groups']and list(ids)==cfg['case_ids']and len(ids)==2
    guard=load('progress_UI_guard',here/'source_guard.py').check(repo,here)
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==cfg['contract']and pins['case_ids']==list(ids)
    assert pins['production_go']is pins['independent_acceptance']is False
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    parent=native.admitted()
    proof=pins['actual_predecessor'];raw=Path(os.environ[cfg['choice_variable']]).read_bytes()
    checked=load('progress_UI_evidence',here/'evidence.py').validate(repo,here,proof,raw,product,parent)
    return dict(qualified_public_parent=parent,current_installation=product.sources(),qualification=pins,
        actual_parent_verified=checked,source_guard=guard,actual_cron_claim=False,default_adopted=False,
        production_go=False,independent_acceptance=False)
