"""Admit full Native15 and both unchanged B browser2 prerequisites."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys


def admitted(repo,here,ids,product,native,groups):
    predecessor=native.admitted()
    assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==4
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_MODEL_BROWSER_SOURCE_CHANGED',path)
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
        elif variable in('MODEL_POLICY_BROWSER_ORIGINAL_REPORT','MODEL_V2_BROWSER_ORIGINAL_REPORT'):
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']and actual['observed_case_count']==2
            group='policy'if variable=='MODEL_POLICY_BROWSER_ORIGINAL_REPORT'else'evaluation'
            assert actual['required_case_ids']['browser']==groups[group]and actual['browser']['counts']=={'PASS':2}
            assert actual['model_policy_source_sha256']==product.policy.verify_sources()
            if group=='evaluation':assert actual['model_evaluation_v2_source_sha256']==product.evaluation.verify_sources()
        else:raise ValueError('CURRENT_MODEL_BROWSER_UNDECLARED_ORIGINAL: '+variable)
        originals[variable]=dict(proof,observed_status='PASS')
    assert set(originals)=={'CURRENT_FINANCE_MODEL_ORIGINAL_REPORT','MODEL_POLICY_BROWSER_ORIGINAL_REPORT','MODEL_V2_BROWSER_ORIGINAL_REPORT'}
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__);assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name]
            loaded.append(name)
    return dict(qualified_current_finance_model=predecessor,current_installation=product.sources(),
        qualification=pins,actual_originals_verified=originals,actual_loaded_modules_verified=loaded,
        original_B_case_bodies_and_fixtures_unchanged=True)
