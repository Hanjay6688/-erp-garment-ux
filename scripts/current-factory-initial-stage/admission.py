from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def gate(config):
    assert config['contract']=='cp7.current-factory-initial-stage.v1'and config['allow_database_execution']is True
    assert (config['initial_statement_limit_ms'],config['ordinary_statement_limit_ms'],config['lock_limit_ms'],config['minimum_targets'],config['added_schedule_count'])==(16000,8000,2000,1000,1)
    assert config['production_go']is config['independent_acceptance']is False
    assert config['retained_profile']['head']=='5b32f4744eef66c2e9cc8619781faee446f360e7'
    return config['retained_profile']
def admitted(repo,here,ids,product,native):
    cfg=json.loads((here/'CONFIG.json').read_bytes());proof=gate(cfg)
    source=json.loads((here/'SOURCE.json').read_bytes());assert source['case_ids']==list(ids)
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    old=load('initial_worker_exact_profile_admission',repo/'scripts/current-factory-operational-profile-qualification/probe.py')
    parent=old.admitted();current=product.sources()
    assert current['predecessor']==parent['current_installation']
    directory=Path(os.environ[cfg['original_directory_variable']])
    retained=load('initial_worker_actual_profile_evidence',here/'evidence.py').checked(proof,
        (directory/proof['name']).read_bytes(),(directory/proof['package_name']).read_bytes(),parent)
    guard=load('initial_worker_derivation_guard',here/'source_guard.py').check(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    return dict(qualification=source,current_installation=current,unchanged_profile_declaration=parent,
        retained_profile=retained,source_guard=guard,production_go=False,independent_acceptance=False)
if __name__=='__main__':
    here=Path(__file__).resolve().parent;d=load('initial_worker_probe',here/'probe.py').admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',pins=len(d['qualification']['files']),actual_cases=0)))
