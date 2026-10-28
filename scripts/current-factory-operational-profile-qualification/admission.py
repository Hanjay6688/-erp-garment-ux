from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def admitted(repo,here,ids,product,native):
    cfg=json.loads((here/'CONFIG.json').read_bytes());assert cfg['allow_diagnostic_execution']is True
    assert (cfg['diagnostic_statement_limit_ms'],cfg['small_statement_limit_ms'],cfg['lock_limit_ms'])==(30000,8000,2000)
    assert cfg['product_or_schedule_limits_changed']is cfg['production_go']is cfg['independent_acceptance']is False
    source=json.loads((here/'SOURCE.json').read_bytes());assert source['case_ids']==list(ids)
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    old=load('current_profile_actual_factory_admission',repo/'scripts/current-finance-factory-progress-followup-qualification/probe.py');parent=old.admitted()
    assert parent['current_installation']==product.sources()
    directory=Path(os.environ[cfg['original_directory_variable']]);proof=cfg['retained_4ac']
    evidence=load('current_profile_retained_actual_4ac',here/'evidence.py').checked(proof,(directory/proof['name']).read_bytes(),(directory/proof['package_name']).read_bytes(),parent)
    derivation=load('current_profile_exact_derivation',here/'source_guard.py').check(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    return dict(qualification=source,current_installation=product.sources(),unchanged_4ac_declaration=parent,
        retained_4ac=evidence,source_guard=derivation,diagnostic_only=True,actual_cron_claim=False,production_go=False,independent_acceptance=False)
if __name__=='__main__':
    p=load('current_profile_probe',HERE/'probe.py');d=p.admitted();print(json.dumps(dict(status='SOURCE_ADMITTED',pins=len(d['qualification']['files']),diagnostic_only=True,actual_cases=0)))
