"""Exact current Native15 source and actual runtime admission before Auth/races."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys


def admitted(repo,here,ids,product,native):
    predecessor=native.admitted()
    assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==10
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_FINANCE_TRANSPORT_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    assert set(pins['actual_qualification_originals'])=={'CURRENT_FINANCE_MODEL_ORIGINAL_REPORT','FIRST_FINANCE_TRANSPORT_ORIGINAL_REPORT'}
    proof=pins['actual_qualification_originals']['CURRENT_FINANCE_MODEL_ORIGINAL_REPORT']
    raw=Path(os.environ['CURRENT_FINANCE_MODEL_ORIGINAL_REPORT']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
    assert actual['native']['counts']=={'PASS':15}and actual['observed_case_count']==15 and actual['required_case_ids_pass']
    assert actual['required_case_ids']==predecessor['qualification']['case_ids']
    assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
    assert actual['source_declaration']['current_installation']==product.sources()
    first=pins['actual_qualification_originals']['FIRST_FINANCE_TRANSPORT_ORIGINAL_REPORT']
    raw_first=Path(os.environ['FIRST_FINANCE_TRANSPORT_ORIGINAL_REPORT']).read_bytes()
    assert len(raw_first)==first['bytes']and sha256(raw_first).hexdigest()==first['sha256']
    failed=json.loads(raw_first)
    assert failed['status']=='INCOMPLETE'and failed['cp6_restored']and failed['advisor_gate']
    assert failed['transport_groups']['finance_auth']['counts']=={'PASS':3}
    races=failed['transport_groups']['finance_races']
    assert races['counts']=={'PASS':6,'INCOMPLETE':1}
    assert[k for k,v in races['races'].items()if v['status']!='PASS']==['CURRENT_FINANCE_RACE_REPLAY_PERMISSION_AFTER_REQUEST']
    for path,digest in failed['source_declaration']['qualification']['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('FIRST_TRANSPORT_SOURCE_CHANGED',path)
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__)
            assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name]
            loaded.append(name)
    return dict(qualified_current_finance_model=predecessor,current_installation=product.sources(),
        qualification=pins,actual_originals_verified=dict(CURRENT_FINANCE_MODEL_ORIGINAL_REPORT=dict(proof,observed_status='PASS'),FIRST_FINANCE_TRANSPORT_ORIGINAL_REPORT=dict(first,observed_status='INCOMPLETE')),
        actual_loaded_modules_verified=loaded,new_finance_transport_cases=True,original_predecessor_cases_unchanged=True)
