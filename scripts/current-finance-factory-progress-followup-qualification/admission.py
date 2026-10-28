"""Admit exact D3 failure and unchanged backend before progress-aware all7."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def gate(config):
    evidence=load('factory_progress_runtime_AF_gate',Path(__file__).with_name('evidence.py'))
    return evidence.gate(config)


def admitted(repo,here,ids,product,native):
    gate(json.loads((here/'CONFIG.json').read_bytes()))
    evidence=load('factory_progress_retained_D3',here/'retained_d3.py')
    config=json.loads((here/'D3_PREREQUISITE.json').read_bytes());proof=evidence.gate(config)
    source=json.loads((here/'SOURCE.json').read_bytes());assert source['case_ids']==list(ids)
    assert source['production_go']is source['independent_acceptance']is False
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    old=repo/'scripts/current-finance-reader-stream-followup-qualification'
    assert sha256((old/'SOURCE.json').read_bytes()).hexdigest()==source['unchanged_D3_source_sha256']
    original_probe=load('factory_progress_exact_D3_probe',old/'probe.py');declaration=original_probe.admitted()
    assert product.sources()==declaration['current_installation'],'FACTORY_PROGRESS_BACKEND_SQL_CHANGED'
    directory=Path(os.environ[config['original_directory_variable']])
    retained=evidence.checked(proof,(directory/proof['name']).read_bytes(),
        (directory/proof['package_name']).read_bytes(),declaration)
    guard=load('factory_progress_source_guard',here/'source_guard.py').check(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    return dict(qualification=source,current_installation=product.sources(),unchanged_D3_declaration=declaration,
        retained_D3_first_failure=retained,source_guard=guard,
        qualification_observation_only=True,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    here=Path(__file__).resolve().parent;probe=load('factory_progress_admission_probe',here/'probe.py');result=probe.admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',own_pins=len(result['qualification']['files']),actual_DB_cases_executed=False)))
