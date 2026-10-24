"""Exact current Native20 source and actual runtime admission before actual cron."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys


def admitted(repo,here,ids,product,native):
    predecessor=native.admitted()
    assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==1
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_FINANCE_CRON_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    assert set(pins['actual_qualification_originals'])=={'CURRENT_MODEL_TARGET_ORIGINAL_REPORT','CURRENT_FINANCE_MODEL_CRON_ORIGINAL_REPORT'}
    original=repo/'scripts/current-finance-model-cron-qualification/runner.py'
    assert(here/'runner.py').read_text()==original.read_text().replace('import cp7_current_finance_model_installation as product','import cp7_current_model_target_installation as product')
    prior=pins['actual_qualification_originals']['CURRENT_FINANCE_MODEL_CRON_ORIGINAL_REPORT']
    oldraw=Path(os.environ['CURRENT_FINANCE_MODEL_CRON_ORIGINAL_REPORT']).read_bytes()
    assert len(oldraw)==prior['bytes']and sha256(oldraw).hexdigest()==prior['sha256']
    old=json.loads(oldraw)
    assert old['status']=='PASS'and old['cp6_restored']and old['advisor_gate']and old['actual_cron_claim']
    assert old['source_declaration']['current_installation']==product.predecessor.sources()
    assert old['source_declaration']['qualification']['files']['scripts/current-finance-model-cron-qualification/runner.py']==sha256(original.read_bytes()).hexdigest()
    assert old['required_case_ids_pass']and old['required_case_ids']==list(ids)and old['observed_case_count']==1
    assert old['manual_steps']==0 and not old['changed_schedule']and old['baseline_full22_all_rows_all_sequences_equal']and old['baseline_advisors_equal']
    proof=pins['actual_qualification_originals']['CURRENT_MODEL_TARGET_ORIGINAL_REPORT']
    raw=Path(os.environ['CURRENT_MODEL_TARGET_ORIGINAL_REPORT']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
    assert actual['native']['counts']=={'PASS':20}and actual['observed_case_count']==20 and actual['required_case_ids_pass']
    assert actual['required_case_ids']==predecessor['qualification']['case_ids']
    assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
    assert actual['source_declaration']['current_installation']==product.sources()
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__)
            assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name]
            loaded.append(name)
    return dict(qualified_current_model_target=predecessor,current_installation=product.sources(),
        qualification=pins,actual_originals_verified=dict(CURRENT_MODEL_TARGET_ORIGINAL_REPORT=dict(proof,observed_status='PASS'),CURRENT_FINANCE_MODEL_CRON_ORIGINAL_REPORT=dict(prior,observed_status='PASS')),
        actual_loaded_modules_verified=loaded,actual_cron_qualification=True,original_predecessor_cases_unchanged=True)
