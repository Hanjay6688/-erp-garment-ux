"""Verify the assembled tree, materialize historical evidence, preserve closed UI."""
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
    assert cfg['production_go']is cfg['independent_acceptance']is False
    assert not git('status','--porcelain','--untracked-files=no').strip()
    changed=git('diff','--name-status','--no-renames',cfg['base_head'],'HEAD').decode().splitlines()
    deleted={line.split('\t',1)[1]for line in changed if line.startswith('D\t')}
    assert deleted==set(cfg['deleted_workflows'])
    for line in changed:
        status,path=line.split('\t',1)
        assert path in deleted or path in cfg['exact_files'] or path.startswith('scripts/current-integration-assembly-preparation/')or path=='.github/workflows/cp7-d17-18-integration-assembly.yml',line
    for path,item in cfg['exact_files'].items():
        raw=(ROOT/path).read_bytes()
        assert len(raw)==item['bytes']and sha256(raw).hexdigest()==item['sha256'],path
        assert raw==git('show',item['head']+':'+path),path
    history=load('assembly_historical_proof_inputs',ROOT/'scripts/current-workflow-history-isolation/materialize.py').materialize()
    source=load('assembly_unchanged_source',ROOT/'scripts/current-source-closure-preparation/check.py').check()
    for ns,manifest in [('current-finance-factory-progress-followup-qualification','SOURCE.json'),('current-finance-combined-browser-qualification','PREPARED_SOURCE.json')]:
        q=ROOT/'scripts'/ns;s=json.loads((q/manifest).read_bytes())
        for path,digest in s['files'].items():assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    ui=ROOT/'scripts/current-finance-combined-browser-qualification'
    cfgui=json.loads((ui/'CONFIG.json').read_bytes())
    assert cfgui['allow_database_execution']is False and cfgui['accepted_combined']is None
    assert not(ui/'SOURCE.json').exists()
    guards=load('assembly_UI_source_guards',ui/'source_guard.py').check(ROOT,ui)
    for path in ('src/App.tsx','package.json','package-lock.json','vite.config.ts','scripts/cp6_t3_aligned_install.py'):
        assert(ROOT/path).read_bytes()==git('show',cfg['base_head']+':'+path),path
    return dict(status='PASS_EXACT_ASSEMBLY_SOURCE_ONLY',head=git('rev-parse','HEAD').decode().strip(),base_head=cfg['base_head'],exact_component_files=len(cfg['exact_files']),retired_workflows=len(deleted),history=history,source=source,UI_host_files=guards['host_exact_files'],B_UI_exact_files=guards['current_B_exact_files'],factory_pins=31,closed_UI_pins=23,backend_runtime_head=cfg['factory_head'],backend_runtime_qualified=False,browser_configuration_closed=True,actual_DB_Auth_browser_cases=0,full_shell_acceptance=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    value=check();out=ROOT/'cp6-proof/current-integration-assembly/SOURCE.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
