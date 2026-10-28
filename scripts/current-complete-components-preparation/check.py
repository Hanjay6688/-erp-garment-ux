"""Exact source assembly only; runtime and B browser acceptance stay separate."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def check():
    cfg=json.loads((HERE/'CONFIG.json').read_bytes())
    origin=json.loads((HERE/'WORKFLOW_ORIGIN.json').read_bytes())
    frozen=git('show',origin['head']+':'+origin['path'])
    assert sha256(frozen).hexdigest()==origin['sha256']
    derived=frozen.decode()
    for old,new in origin['replacements']:
        assert old in derived;derived=derived.replace(old,new)
    assert (ROOT/origin['target']).read_text()==derived
    assert cfg['contract']=='cp7.current-complete-components-preparation.v1'
    assert cfg['production_go']is cfg['independent_acceptance']is cfg['default_adopted']is cfg['backend_runtime_eligible']is False
    assert cfg['browser_owner']=='B'and cfg['browser_files_imported']==cfg['actual_DB_Auth_browser_cases']==0
    assert not git('status','--porcelain','--untracked-files=no').strip()
    changed=git('diff','--name-status','--no-renames',cfg['base_head'],'HEAD').decode().splitlines()
    deleted={line.split('\t',1)[1]for line in changed if line.startswith('D\t')}
    assert deleted==set(cfg['deleted_workflows'])
    for line in changed:
        status,path=line.split('\t',1)
        assert path in deleted or path in cfg['exact_files'] or path.startswith('scripts/current-complete-components-preparation/')or path==origin['target'],line
        if path not in deleted:
            assert status==('M'if path in cfg['existing_replacements']else'A'),('EXISTING_SOURCE_CHANGED',path)
            if path in cfg['existing_replacements']:
                assert sha256(git('show',cfg['base_head']+':'+path)).hexdigest()==cfg['existing_replacements'][path]['old_sha256']
    for path,item in cfg['exact_files'].items():
        raw=(ROOT/path).read_bytes()
        assert len(raw)==item['bytes']and sha256(raw).hexdigest()==item['sha256'],path
        assert raw==git('show',item['head']+':'+path),path
    history=load('backend_assembly_historical_inputs',ROOT/'scripts/current-workflow-history-isolation/materialize.py').materialize()
    source=load('backend_assembly_tested_tooling_source',ROOT/'scripts/current-ui-tooling-source-successor/check.py').check()
    for ns in ('current-finance-factory-progress-followup-qualification','current-factory-operational-profile-qualification','current-factory-initial-stage','current-factory-live-heartbeat'):
        manifest=json.loads((ROOT/'scripts'/ns/'SOURCE.json').read_bytes())
        for path,digest in manifest['files'].items():assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    assert set(git('diff','--name-only',cfg['base_head'],'HEAD','--','src').decode().splitlines())=={'src/NativeAnalysisFinancePanel.tsx','src/NativeAnalysisFinancePanel.progress.dom.test.tsx'}
    assert not git('diff',cfg['base_head'],'HEAD','--','supabase','package.json','package-lock.json','vite.config.ts','scripts/cp6_t3_aligned_install.py').strip()
    return dict(status='PASS_EXACT_COMPLETE_COMPONENTS_SOURCE_ONLY',head=git('rev-parse','HEAD').decode().strip(),
        base_head=cfg['base_head'],exact_component_files=len(cfg['exact_files']),retired_workflows=len(deleted),
        history=history,source=source,proposed_backend_head=cfg['proposed_backend_head'],
        backend_runtime_eligible=False,browser_owner='B',browser_files_imported=0,
        original_manifests_rewritten=0,actual_DB_Auth_browser_cases=0,default_adopted=False,
        production_go=False,independent_acceptance=False)
if __name__=='__main__':
    value=check();out=ROOT/'cp6-proof/current-complete-components/SOURCE.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
