from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def admitted(repo,here,ids,product,native):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.d17-18.choice-finance-cron1.v1'
    assert pins['case_ids']==list(ids)and len(ids)==1
    assert pins['production_go']is pins['independent_acceptance']is False
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    changes=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',pins['merge_head'],'HEAD'],text=True).splitlines()
    assert all(p.startswith('scripts/current-choice-finance-cron-qualification/')or p=='.github/workflows/cp7-d17-18-choice-finance-cron.yml'for p in changes)
    guard=load('choice_finance_cron_source_guard',here/'source_guard.py').check(repo,here)
    parent=load('choice_finance_cron_UI_parent',repo/'scripts/current-progress-finance-ui-browser-qualification/probe.py').admitted()
    assert parent['current_installation']==product.sources()
    checker=load('choice_finance_cron_exact_evidence',here/'evidence.py')
    checked={k:checker.checked(repo,p,os.environ[p['directory_variable']],product,parent)for k,p in pins['actual_originals'].items()}
    return dict(qualification=pins,qualified_current_UI=parent,current_installation=product.sources(),
        actual_originals_verified=checked,retained_cron_guards=guard,actual_cron_claim=False,
        finance_optimization_adopted=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    here=Path(__file__).resolve().parent;probe=load('choice_finance_cron_probe',here/'probe.py')
    result=probe.admitted();print(json.dumps(dict(status='SOURCE_ADMITTED',pins=len(result['qualification']['files']),cases=1,actual_cron_claim=False)))
