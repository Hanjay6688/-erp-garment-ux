"""Full unchanged Native45 source gate, its actual PASS and exact B facade8 PASS."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess

CONTRACT='cp7.current-frozen-public-finance-native52-qualification.v1'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def admitted(repo,here,ids,product,business):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==CONTRACT and pins['case_ids']==list(ids)
    assert len(ids)==len(set(ids))==52
    old_path=repo/'scripts/current-frozen-finance-native-qualification/probe.py'
    old=load('unchanged_full_private_finance_admission',old_path).admitted()
    assert old['current_installation']==product.predecessor.sources()
    assert pins['retained_declaration_sha256']==sha256(old_path.with_name('SOURCE.json').read_bytes()).hexdigest()
    for path,digest in old['qualification']['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    proofs=pins['actual_qualification_originals'];actuals={}
    for variable,proof in proofs.items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actuals[variable]=json.loads(raw)
    verified=load('public_native_actual_prerequisites',here/'evidence.py').validate(repo,here,proofs,actuals,product)
    extra=set(business.public.IDS)|set(business.public_finance.IDS)
    assert len(extra)==7 and set(ids)==set(old['qualification']['case_ids'])|extra
    assert not(set(old['qualification']['case_ids'])&extra)
    return dict(qualified_current_frozen_finance=old,current_installation=product.sources(),qualification=pins,
        actual_originals_verified=verified,retained_business_cases=business.source_binding(),
        retained_private_cases=45,new_public_boundary_cases=7,
        B_actual_Auth_HTTP_credit_is_component_only=True,actual_Auth_HTTP_credit=False,
        public_or_default_adopted=False,full_factory3600_finance_qualified=False,
        production_go=False,independent_acceptance=False)
