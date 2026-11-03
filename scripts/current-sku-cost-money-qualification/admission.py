"""Closed declarations and exact accepted parents before the full runtime."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util
import json
import os
import subprocess

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def ids(path,name):
    tree=ast.parse(path.read_text())
    return ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in n.targets)))

def source_only(repo,here):
    cfg=json.loads((here/'CONFIG.json').read_bytes());source=json.loads((here/'SOURCE.json').read_bytes())
    if cfg['contract']!='cp7.sku-cost-money-native19.v1':raise ValueError('SKU_MONEY_CONTRACT_CHANGED')
    errors=[]
    for path,digest in source['files'].items():
        if not(repo/path).is_file()or sha256((repo/path).read_bytes()).hexdigest()!=digest:errors.append('SOURCE:'+path)
    for path,digest in cfg['parent_runtime_files'].items():
        if not(repo/path).is_file()or sha256((repo/path).read_bytes()).hexdigest()!=digest:errors.append('PARENT:'+path)
    product=json.loads((repo/'scripts/cp7_sku_cost_components/SOURCE.json').read_bytes())
    own=repo/'scripts/cp7_sku_cost_components'
    actual={str(p.relative_to(repo)):dict(bytes=len(p.read_bytes()),sha256=sha256(p.read_bytes()).hexdigest())
        for p in own.iterdir()if p.is_file()and p.name!='SOURCE.json'and p.suffix in('.py','.sql','.json','.md','.mjs','.inc')}
    if actual!=product['files']:errors.append('COMPLETE_PRODUCT_SOURCE_MANIFEST')
    if any(v is not None for v in product['gates'].values())or len(product['gates'])!=12:errors.append('UNQUALIFIED_PRODUCT_GATES_CHANGED')
    retained=tuple(ids(repo/'scripts/cp7_sku_moving_average/qualification_cases.py','IDS'))
    planned=retained+tuple(ids(here/'native_cases.py','NEW_IDS'))
    if list(retained)!=cfg['retained_native_case_ids']or list(planned)!=cfg['native_case_ids']or len(set(planned))!=19:errors.append('NATIVE19_CASE_PLAN')
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    changed=git('diff','--name-only',cfg['baseline_tree'],'HEAD^{tree}').decode().splitlines()
    if not set(changed)<=set(source['allowed_changes']):errors.append('UNDECLARED_SUCCESSOR_CHANGE')
    if git('status','--porcelain','--untracked-files=no').strip():errors.append('TRACKED_WORKTREE_DIRTY')
    for key in('CP7_SKU_PARENT_ORIGINALS','CP7_SKU_MOVING_PARENT_ORIGINALS'):
        if not os.environ.get(key):errors.append('MISSING_PARENT_DIRECTORY:'+key)
    if errors:raise ValueError(dict(status='SOURCE_PREFLIGHT_REFUSED',errors=errors,actual_ERP_cases=0))
    parents=load('sku_money_exact_parent_proofs',here/'parent_proofs.py').check(
        os.environ['CP7_SKU_PARENT_ORIGINALS'],os.environ['CP7_SKU_MOVING_PARENT_ORIGINALS'],cfg)
    if parents['moving_source']['files']!=cfg['parent_runtime_files']:raise ValueError('SKU_MONEY_ACTUAL_PARENT_SOURCE_DIFFERS')
    return dict(status='EXACT_SOURCE_AND_PARENT_ORIGINALS_NOT_RUNTIME_ADMISSION',parents=parents,
        declared_source=source,case_ids=list(planned),actual_ERP_cases=0,production_go=False)

def admitted(repo,here,product,derivation):
    proof=source_only(repo,here);cfg=json.loads((here/'CONFIG.json').read_bytes())
    current=product.sources()
    if current['predecessor']!=proof['parents']['moving_source']:raise ValueError('SKU_MONEY_COMPLETE_QUALIFIED_PARENT_CHANGED')
    if current['files']!=cfg['runtime_files']:raise ValueError('SKU_MONEY_RUNTIME_SOURCE_CHANGED')
    if derivation!=cfg['runner_derivation']:raise ValueError('SKU_MONEY_WHOLE_PACKAGE_DERIVATION_CHANGED')
    return dict(proof,status='EXACT_NATIVE27_MOVING6_AND_MONEY19_GRAPH_ADMITTED',current_installation=current,
        runner_derivation=derivation,actual_Native_case_ids=cfg['native_case_ids'],
        current_installation_entrypoint=dict(module='cp7_sku_cost_components.composition',install='install',verify='verify',rollback_preuse='rollback_preuse'),
        independent_acceptance=False)
