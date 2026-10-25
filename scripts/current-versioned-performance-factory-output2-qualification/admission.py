"""Require all six current performance suites before the official factory trial."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def admitted(repo,here,ids,product,native):
    config=json.loads((here/'CONFIG.json').read_bytes())
    guard=load('performance_factory_source_guard',here/'source_guard.py').source_binding()
    predecessor=native.admitted();assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==config['contract']and pins['case_ids']==list(ids)and len(ids)==1
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,('PERFORMANCE_FACTORY_SOURCE_CHANGED',path)
    worktree=load('factory_generated_evidence_boundary',here/'source_worktree.py').admit(repo)
    proofs=pins['actual_qualification_originals'];actuals={}
    for variable,proof in proofs.items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actuals[variable]=json.loads(raw)
    evidence=load('performance_factory_actual_prerequisites',here/'evidence.py')
    sources,verified=evidence.validate(repo,config,proofs,actuals,product)
    assert sources['native']==predecessor['qualification']
    return dict(qualified_current_versioned_performance=predecessor,current_installation=product.sources(),qualification=pins,
        actual_originals_verified=verified,source_worktree_boundary=worktree,retained_business_source=guard,six_complete_current_suites_required=True,
        synthetic_factory_scope=dict(commercial_skus=1200,sizes_per_sku=3,variants=3600),first_failure_preserved=True,
        independent_acceptance=False,production_go=False)
