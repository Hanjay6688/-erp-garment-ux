"""Admit unchanged selected backend plus explicitly declared B browser successor."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,subprocess

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def admitted(repo,here,ids,product,native,groups):
    config=json.loads((here/'CONFIG.json').read_bytes())
    load('B_selected_backend_gate',here/'composition.py').gate(config)
    assert list(ids)==config['case_ids']and groups==config['groups']and len(ids)==2
    frontend=here.parents[1]
    source=json.loads((here/'SOURCE.json').read_bytes())
    assert source['contract']==config['contract']and source['case_ids']==list(ids)
    assert source['production_go']is source['independent_acceptance']is False
    for path,digest in source['files'].items():assert sha256((frontend/path).read_bytes()).hexdigest()==digest,path
    backend=product.backend_root();assert backend==repo
    # Execute the actual selected checkout's original full admission, including
    # its old failure and six retained groups. No stored declaration substitutes it.
    previous=load('B_actual_selected_3194_probe',backend/'scripts/current-factory-live-heartbeat/probe.py').admitted()
    current,accepted=product.qualification()
    assert current==previous['current_installation'],'SELECTED_BACKEND_DECLARATION_CHANGED'
    guard=load('B_exact_browser_successor_guard',here/'source_guard.py').check(frontend,here)
    assert not subprocess.check_output(['git','-C',str(frontend),'status','--porcelain','--untracked-files=no']).strip()
    return dict(qualification=source,current_installation=product.sources(),accepted_combined_runtime=accepted,
        actual_selected_backend_declaration=previous,source_guard=guard,actual_cron_claim=False,
        default_adopted=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    here=Path(__file__).resolve().parent;result=load('B_3194_browser_probe',here/'probe.py').admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',pins=len(result['qualification']['files']),actual_browser_executed=False,actual_Auth_executed=False)))
