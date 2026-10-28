"""New B source declaration; historical 113-host/91-B proofs remain untouched."""
from hashlib import sha256
import ast,importlib.util,json,subprocess
BASE='3efecab381578cb12b06b9bedd97b31b7a20b26a'
B_HEAD='1dd83782dcaa4500bace7bf392a76f58be0271c3'
DRIVER='8a0ed68aed839684014a3f3756a8060608696921'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def check(repo,here,*,overrides=None):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    assert cfg['backend_head']=='3194b9c56be7af86ee45ccb1c6605204a712f91b'and cfg['driver_head']==DRIVER
    assert cfg['backend_tree']=='dd98cd5bbbafb3f257668d22317ab4b237c2fea8'
    assert git('rev-parse',BASE+'^{tree}').decode().strip()=='c27e220d2e92d6732faf70c95b51c598103738b4'
    allowed={'src/nativeStagedJob.ts','src/nativeStagedJob.initial.test.ts','.github/workflows/cp7-d17-18-combined-finance-browser.yml'}
    changed=git('diff','--name-only',BASE,'HEAD').decode().splitlines()
    assert all(p in allowed or p.startswith(('scripts/current-finance-combined-browser-qualification/','docs/cp7/d17-18/b-initial-driver-20261028/','docs/cp7/d17-18/b-qualified3194-browser-20261028/'))for p in changed),'UNDECLARED_B_SCOPE_CHANGE'
    for path in ('src/nativeStagedJob.ts','src/nativeStagedJob.initial.test.ts'):
        assert(repo/path).read_bytes()==git('show',DRIVER+':'+path),path
    ui=load('B_actual_A279_panel_binding',repo/'scripts/current-ui-tooling-source-successor/ui_binding.py').checked()
    frozen=repo/'scripts/current-progress-finance-ui-browser-qualification'
    old=load('B_retained_original_host_guards',frozen/'source_guard.py').check(repo,frozen)
    rules=json.loads((here/'SUCCESSOR_ORIGIN.json').read_bytes());proof={}
    for name,rule in rules.items():
        original=git('show',rule['head']+':'+rule['path'])
        assert sha256(original).hexdigest()==rule['before_sha256']
        actual=(overrides or{}).get(name,(here/name).read_text())
        assert sha256(actual.encode()).hexdigest()==rule['after_sha256'],'COMBINED_UI_UNDECLARED_ORACLE_CHANGE:'+name
        if name in ('browser.mjs','browser_fixture.py','probe.py'):
            # Keep every original business assertion verbatim, even where the
            # selected source paths and imports have changed.
            for line in original.decode().splitlines():
                if 'assert.'in line or line.lstrip().startswith('assert '):
                    if name=='browser.mjs'and 'const get=async()'in line:
                        line=line.replace('readFileSync(p)','readFileSync(resolve(browserRoot,p))').replace("readFileSync('scripts/cp7_current_progress_finance_ui/BUILD_SOURCE.json')","readFileSync(resolve(browserRoot,'scripts/current-finance-combined-browser-qualification/BUILD_SOURCE_3194.json'))")
                    assert line in actual,(name,line)
            if name.endswith('.py'):assert sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(actual)))>=rule['original_assertions']
        proof[name]=dict(exact_successor_sha256=True,before_sha256=rule['before_sha256'],after_sha256=rule['after_sha256'])
    graph=json.loads((here/'BUILD_SOURCE_3194.json').read_bytes())
    assert graph['runtime_replacements']==['src/NativeAnalysisFinancePanel.tsx','src/nativeStagedJob.ts']
    assert len(graph['files'])==79
    for f in graph['files']:
        raw=(repo/f['path']).read_bytes();assert len(raw)==f['bytes']and sha256(raw).hexdigest()==f['sha256'],f['path']
    workflow=load('B_3194_workflow',here/'workflow_guard.py').check(repo,here)
    return dict(host_exact_files=113,current_B_exact_files=91,current_B_head=B_HEAD,original_host_guards=old,A279_panel=ui,
        driver_head=DRIVER,declared_runtime_replacements=graph['runtime_replacements'],derivation=proof,workflow=workflow,
        actual_browser_executed=False,historical_manifests_rewritten=False,production_go=False)
