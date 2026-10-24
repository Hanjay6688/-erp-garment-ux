"""Admit actual current Native15 and both retained B transport10 Originals."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys


def admitted(repo,here,ids,product,native,transport):
    predecessor=native.admitted()
    assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==18
    assert pins['groups']==transport.GROUPS
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_RETAINED_MODEL_TRANSPORT_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw)
        assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate'],variable
        if variable=='CURRENT_FINANCE_MODEL_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation']==product.sources()
            assert actual['native']['counts']=={'PASS':15}and actual['observed_case_count']==15
            assert actual['required_case_ids_pass']and actual['required_case_ids']==predecessor['qualification']['case_ids']
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        elif variable in('MODEL_POLICY_TRANSPORT_ORIGINAL_REPORT','MODEL_V2_TRANSPORT_ORIGINAL_REPORT'):
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']and actual['observed_case_count']==10
            component='policy'if variable=='MODEL_POLICY_TRANSPORT_ORIGINAL_REPORT'else'evaluation'
            assert actual['required_case_ids']==transport.MODULES[component].IDS
            assert actual['native']['counts']=={'PASS':1}
            assert actual['races']['counts']=={'PASS':6}and actual['http']['counts']=={'PASS':3}
            assert actual['model_policy_source_sha256']==product.policy.verify_sources()
            if component=='evaluation':assert actual['model_evaluation_v2_source_sha256']==product.evaluation.verify_sources()
        else:raise ValueError('CURRENT_RETAINED_MODEL_TRANSPORT_UNDECLARED_ORIGINAL: '+variable)
        originals[variable]=dict(proof,observed_status='PASS')
    assert set(originals)=={'CURRENT_FINANCE_MODEL_ORIGINAL_REPORT','MODEL_POLICY_TRANSPORT_ORIGINAL_REPORT','MODEL_V2_TRANSPORT_ORIGINAL_REPORT'}
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__);assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name]
            loaded.append(name)
    return dict(qualified_current_finance_model=predecessor,current_installation=product.sources(),
        qualification=pins,actual_originals_verified=originals,actual_loaded_modules_verified=loaded,
        retained_business_source_binding=transport.source_binding(),original_B_case_bodies_unchanged=True)
