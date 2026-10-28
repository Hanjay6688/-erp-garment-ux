"""No current private factory trial before full Native45 and six actual baselines."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def admitted(repo,here,ids,product,native):
    config=json.loads((here/'CONFIG.json').read_bytes())
    guard=load('private_frozen_factory_source_guard',here/'source_guard.py').source_binding()
    predecessor=native.admitted()
    assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==config['contract']and pins['case_ids']==list(ids)and len(ids)==1
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    proofs=pins['actual_qualification_originals'];actuals={}
    for variable,proof in proofs.items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actuals[variable]=json.loads(raw)
    sources,verified=load('private_frozen_factory_actual_evidence',here/'evidence.py').validate(repo,config,proofs,actuals,product)
    assert sources['private_native']==predecessor['qualification']
    return dict(qualified_current_frozen_finance=predecessor,current_installation=product.sources(),
        qualification=pins,actual_originals_verified=verified,retained_business_source=guard,
        six_performance_suites_are_baseline_credit_only=True,full_current_Native45_required=True,
        private_request_transport=True,actual_Auth_HTTP_credit=False,public_or_default_adopted=False,
        first_INCOMPLETE_factory_preserved=True,production_go=False,independent_acceptance=False)
