"""B browser interface to A's exact selected backend checkout; no backend edits."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
_PARENT=None

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def gate(config):
    if config.get('allow_database_execution')is not True or config.get('backend_acceptance')!='six-retained-one-fresh-3194':
        raise ValueError('COMBINED_BROWSER_ACTUAL_COMBINED_RUNTIME_REQUIRED')
    assert config['production_go']is config['independent_acceptance']is False
    return config

def backend_root():
    config=gate(json.loads((HERE/'CONFIG.json').read_bytes()))
    root=Path(os.environ['D17_18_SELECTED_BACKEND_ROOT']).resolve()
    assert root!=ROOT and root.name=='auditor','SEPARATE_FROZEN_BACKEND_REQUIRED'
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==config['backend_head']
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD^{tree}'],text=True).strip()==config['backend_tree']
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no']).strip()
    return root

def parent():
    global _PARENT
    root=backend_root()
    if _PARENT is None:_PARENT=load('browser_exact_3194_backend',root/'scripts/current-factory-initial-stage/composition.py')
    return _PARENT

def qualification():
    gate(json.loads((HERE/'CONFIG.json').read_bytes()))
    manifest=ROOT/'scripts/current-backend-acceptance-3194/SOURCE.json'
    assert sha256(manifest.read_bytes()).hexdigest()=='bd51267b454b3255a006002cae31988302334ede1027cc1600aa95286346dea6'
    for path,digest in json.loads(manifest.read_bytes())['files'].items():assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    cfg=json.loads((ROOT/'scripts/current-backend-acceptance-3194/CONFIG.json').read_bytes())
    directory=Path(os.environ['D17_18_BROWSER_BACKEND_ORIGINALS'])
    current=parent().sources()
    verifier=load('browser_A_six_plus_one_verifier',ROOT/'scripts/current-backend-acceptance-3194/verify.py')
    raw=[(directory/label/cfg[label][key]).read_bytes()for label in ('retained','fresh')for key in ('name','package_name')]
    accepted=verifier.checked(*raw,current)
    return current,accepted

def sources():
    current,proof=qualification()
    return dict(contract='cp7.current-combined-finance-real-auth-browser2.v2',
        combined_installation=current,accepted_combined=proof,
        files={name:sha256((HERE/name).read_bytes()).hexdigest()for name in ('composition.py','CONFIG.json')})

def install(cur):
    qualification();return parent().install(cur)

def verify(cur,state):
    qualification();return parent().verify(cur,state)

def rollback_preuse(cur,state):
    qualification();return parent().rollback_preuse(cur,state)

def __getattr__(name):
    if name=='catalog':
        qualification();return parent().runtime()[4]
    raise AttributeError(name)
