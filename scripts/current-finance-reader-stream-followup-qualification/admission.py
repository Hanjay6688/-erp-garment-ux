"""Exact AF first outcome and complete new source are required before database."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def gate(config):
    evidence=load('reader_stream_preDB_gate',Path(__file__).with_name('evidence.py'))
    return evidence.gate(config)


def admitted(repo,here,ids,product,native):
    gate(json.loads((here/'CONFIG.json').read_bytes()))
    source=json.loads((here/'SOURCE.json').read_bytes());assert source['case_ids']==list(ids)
    assert source['production_go']is source['independent_acceptance']is False
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    parent_dir=repo/'scripts/current-finance-combined-composition'
    assert sha256((parent_dir/'QUALIFICATION_SOURCE.json').read_bytes()).hexdigest()==source['parent_source_sha256']
    admission=load('reader_stream_exact_AF_admission',parent_dir/'qualification_admission.py')
    parent_source=json.loads((parent_dir/'QUALIFICATION_SOURCE.json').read_bytes())
    exact=admission.admitted(repo,parent_dir,parent_source['case_ids'],product.base(),native)
    original,retained=product.qualification()
    assert original['source_declaration']==exact,'READER_STREAM_FULL_AF_SOURCE_CHANGED'
    guard=load('reader_stream_source_derivation',here/'source_guard.py').check(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    return dict(qualification=source,current_installation=product.sources(),unchanged_AF_declaration=exact,
        retained_AF=retained,source_guard=guard,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    here=Path(__file__).resolve().parent;probe=load('reader_stream_admission_probe',here/'probe.py');result=probe.admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',own_pins=len(result['qualification']['files']),actual_DB_cases_executed=False)))
