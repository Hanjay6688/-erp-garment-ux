"""Actual Native20, retained UTC finance PASS and preserved first failure."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess

def admitted(repo,here,ids,product,native):
    predecessor=native.admitted();assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes());assert pins['case_ids']==list(ids)and len(set(ids))==len(ids)==10
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_TARGET_FINANCE_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    original=repo/'scripts/current-finance-model-transport-qualification/cases.py'
    assert(here/'cases.py').read_text()==original.read_text().replace('import cp7_current_finance_model_installation as product','import cp7_current_model_target_installation as product')
    assert(here/'utc_snapshot.py').read_bytes()==(repo/'scripts/current-finance-model-transport-utc-qualification/utc_snapshot.py').read_bytes()
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes();assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw);assert actual['cp6_restored']and actual['advisor_gate']and actual['status']==proof['status']
        if variable=='CURRENT_MODEL_TARGET_ORIGINAL_REPORT':
            assert actual['status']=='PASS'and actual['source_declaration']['current_installation']==product.sources()
            assert actual['native']['counts']=={'PASS':20}and actual['observed_case_count']==20 and actual['required_case_ids_pass']
            assert actual['required_case_ids']==predecessor['qualification']['case_ids']
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        elif variable in('CURRENT_FINANCE_UTC_ORIGINAL_REPORT','FIRST_FINANCE_TRANSPORT_ORIGINAL_REPORT'):
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
            assert actual['source_declaration']['qualification']['files']['scripts/current-finance-model-transport-qualification/cases.py']==sha256(original.read_bytes()).hexdigest()
            groups=actual['transport_groups'];assert groups['finance_auth']['counts']=={'PASS':3}
            assert actual['complete_preuse_removal']and actual['observed_case_count']==10
            if variable=='CURRENT_FINANCE_UTC_ORIGINAL_REPORT':
                assert actual['status']=='PASS'and actual['required_case_ids_pass']and actual['required_case_ids']==list(ids)
                assert groups['finance_races']['counts']=={'PASS':7}
                assert len(actual['full_capture_snapshot_observations'])==7
                assert all(o['all_fields_retained']==23 and o['session_timezone_restored']for o in actual['full_capture_snapshot_observations'])
            else:
                assert actual['status']=='INCOMPLETE'and groups['finance_races']['counts']=={'PASS':6,'INCOMPLETE':1}
                assert[k for k,v in groups['finance_races']['races'].items()if v['status']!='PASS']==['CURRENT_FINANCE_RACE_REPLAY_PERMISSION_AFTER_REQUEST']
        else:raise ValueError('UNDECLARED_TARGET_FINANCE_ORIGINAL: '+variable)
        originals[variable]=dict(proof,observed_status=actual['status'])
    assert set(originals)=={'CURRENT_MODEL_TARGET_ORIGINAL_REPORT','CURRENT_FINANCE_UTC_ORIGINAL_REPORT','FIRST_FINANCE_TRANSPORT_ORIGINAL_REPORT'}
    return dict(qualified_current_model_target=predecessor,current_installation=product.sources(),qualification=pins,actual_originals_verified=originals,
        retained_finance_case_file_sha256=sha256(original.read_bytes()).hexdigest(),only_cases_product_import_changed=True,exact_UTC_observer_unchanged=True)
