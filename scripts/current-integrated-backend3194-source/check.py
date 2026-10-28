"""Exact selective adoption of tested component bytes, preserving B ownership."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def check():
    cfg=json.loads((HERE/'CONFIG.json').read_bytes())
    assert git('rev-parse',cfg['qualified_component_head']+'^{tree}').decode().strip()==cfg['qualified_component_tree']
    assert cfg['default_adopted']is cfg['production_go']is cfg['independent_acceptance']is cfg['frontend_Auth_browser_accepted']is False
    assert not git('status','--porcelain','--untracked-files=no').strip()
    allowed={i['path']for i in cfg['imports']}|set(cfg['status_paths'])
    changed=git('diff','--name-only',cfg['base_head'],'HEAD').decode().splitlines()
    assert all(p in allowed or p.startswith(('scripts/current-backend-acceptance-3194/','scripts/current-integrated-backend3194-source/'))for p in changed),'UNDECLARED_INTEGRATION_CHANGE'
    for item in cfg['imports']:
        p=item['path']
        if item['status']=='D':assert not git('ls-files','--',p).strip(),p
        else:
            assert (ROOT/p).read_bytes()==git('show',cfg['qualified_component_head']+':'+p),p
            assert git('hash-object',p).decode().strip()==item['blob'],p
    assert not git('diff',cfg['qualified_component_head'],'HEAD','--','src','supabase','scripts/cp7-src','.github/workflows','package.json','package-lock.json','vite.config.ts','scripts/cp6_t3_aligned_install.py').strip(),'PRODUCT_OR_WORKFLOW_DIFFERS_FROM_QUALIFIED_COMPONENT'
    manifest=json.loads((ROOT/'scripts/current-backend-acceptance-3194/SOURCE.json').read_bytes())
    for p,digest in manifest['files'].items():assert sha256((ROOT/p).read_bytes()).hexdigest()==digest,p
    history=load('integrated_exact_history',ROOT/'scripts/current-workflow-history-isolation/materialize.py').materialize()
    source=load('integrated_UI_JS_source',ROOT/'scripts/current-ui-tooling-source-successor/check.py').check()
    for ns in ('current-finance-factory-progress-followup-qualification','current-factory-operational-profile-qualification','current-factory-initial-stage','current-factory-live-heartbeat'):
        declaration=json.loads((ROOT/'scripts'/ns/'SOURCE.json').read_bytes())
        for p,digest in declaration['files'].items():assert sha256((ROOT/p).read_bytes()).hexdigest()==digest,p
    return dict(status='PASS_SELECTIVE_A_COMPONENT_INTEGRATION_SOURCE',head=git('rev-parse','HEAD').decode().strip(),qualified_component_head=cfg['qualified_component_head'],exact_component_entries=len(cfg['imports']),source=source,history=history,B_browser_and_driver_unchanged=True,actual_new_DB_Auth_browser_cases=0,default_adopted=False,production_go=False,independent_acceptance=False)
if __name__=='__main__':print(json.dumps(check()))
