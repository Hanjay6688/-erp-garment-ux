"""Gated browser-harness interface to the exact qualified combined installation."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
_PARENT=None


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def parent():
    global _PARENT
    if _PARENT is None:_PARENT=load('browser_exact_combined_product',ROOT/'scripts/current-finance-combined-composition/composition.py')
    return _PARENT


def qualification():
    evidence=load('browser_exact_combined_runtime_evidence',HERE/'evidence.py')
    config=json.loads((HERE/'CONFIG.json').read_bytes());proof=evidence.gate(config)
    directory=Path(os.environ[config['original_directory_variable']])
    source=json.loads((ROOT/'scripts/current-finance-combined-composition/QUALIFICATION_SOURCE.json').read_bytes())
    for name,digest in source['files'].items():assert sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    value,accepted=evidence.accepted(proof,(directory/proof['name']).read_bytes(),
        (directory/proof['package_name']).read_bytes(),source,parent().sources())
    probe=load('browser_complete_combined_source_admission',ROOT/'scripts/current-finance-combined-composition/qualification_probe.py')
    assert value['source_declaration']==probe.admitted(),'COMBINED_BROWSER_COMPLETE_SOURCE_CHANGED'
    return value,accepted


def sources():
    _,proof=qualification()
    return dict(contract='cp7.current-combined-finance-real-auth-browser2.v1',
        combined_installation=parent().sources(),accepted_combined=proof,
        files={name:sha256((HERE/name).read_bytes()).hexdigest()for name in ('composition.py','evidence.py','CONFIG.json')})


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
