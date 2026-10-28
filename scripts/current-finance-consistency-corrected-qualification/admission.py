"""Exact64's failure and the complete unchanged source precede corrected DB use."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,subprocess


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def admitted(repo,here,ids,product,native):
    config=json.loads((here/'CONFIG.json').read_bytes())
    evidence=load('corrected_consistency_retained64_evidence',here/'evidence.py');evidence.gate(config)
    source=json.loads((here/'SOURCE.json').read_bytes());assert source['case_ids']==list(ids)
    assert source['production_go']is source['independent_acceptance']is False
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    parent_dir=repo/'scripts/current-finance-consistency-followup-qualification'
    assert sha256((parent_dir/'SOURCE.json').read_bytes()).hexdigest()==source['parent_source_sha256']
    parent=load('corrected_consistency_exact64_admission',parent_dir/'admission.py')
    parent_ids=json.loads((parent_dir/'SOURCE.json').read_bytes())['case_ids']
    accepted=parent.admitted(repo,parent_dir,parent_ids,product,native)
    proof=config['retained64'];directory=Path(os.environ[config['original_directory_variable']])
    _,retained=evidence.retained(proof,(directory/proof['name']).read_bytes(),
        (directory/proof['package_name']).read_bytes(),accepted)
    guard=load('corrected_consistency_source_derivation',here/'source_guard.py').check(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    return dict(qualification=source,current_installation=accepted['current_installation'],
        unchanged_actual84_source=accepted['unchanged_actual84_source'],retained_actual84=accepted['retained_actual84'],
        unchanged_focused64_source=accepted,retained_focused64=retained,source_guard=guard,
        focused_execution_only=True,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    here=Path(__file__).resolve().parent
    probe=load('corrected_consistency_admission_probe',here/'probe.py')
    result=probe.admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',own_pins=len(result['qualification']['files']),
        actual_DB_cases_executed=False,retained_whole64_status='INCOMPLETE',focused_groups=2)))
