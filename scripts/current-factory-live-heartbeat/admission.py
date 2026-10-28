from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def gate(config):
    assert config['contract']=='cp7.factory-live-heartbeat-closure.v1'and config['allow_database_execution']is True
    assert config['backend_head']=='11c95c4ee2c784247e1be22ce0a582f4d85632c5'
    assert config['backend_tree']=='688a4ac63208e000602a30d406b4e080d2203a28'
    assert config['production_go']is config['independent_acceptance']is False
    assert config['retained']['head']==config['backend_head']and config['retained']['tree']==config['backend_tree']
    return config['retained']
def admitted(repo,here,ids,product,native):
    cfg=json.loads((here/'CONFIG.json').read_bytes());proof=gate(cfg)
    source=json.loads((here/'SOURCE.json').read_bytes());assert source['case_ids']==list(ids)
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    old=load('live_unchanged_initial_admission',repo/'scripts/current-factory-initial-stage/probe.py')
    parent=old.admitted();current=product.sources()
    assert current==parent['current_installation'],'ENTIRE_BACKEND_INSTALLATION_CHANGED'
    directory=Path(os.environ[cfg['original_directory_variable']])
    retained=load('live_retained_actual',here/'retained.py').checked(proof,(directory/proof['name']).read_bytes(),(directory/proof['package_name']).read_bytes(),parent)
    guard=load('live_source_guard',here/'source_guard.py').check(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    return dict(qualification=source,current_installation=current,unchanged_11c_declaration=parent,retained_six=retained,source_guard=guard,production_go=False,independent_acceptance=False)
if __name__=='__main__':
    here=Path(__file__).resolve().parent;d=load('live_probe',here/'probe.py').admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',pins=len(d['qualification']['files']),fresh_database_cases=0,retained_groups=6)))
