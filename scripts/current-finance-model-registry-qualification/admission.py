"""Frozen finance gate plus explicit current source changes and actual Originals."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,sys


def admitted(repo,here,ids,product,business):
    spec=importlib.util.spec_from_file_location('current_model_frozen_admission',here/'frozen_admission.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    predecessor=frozen.invoke()
    assert predecessor['current_installation']==product.predecessor.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['case_ids']==list(ids)and len(ids)==15
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_MODEL_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    declaration=pins['frozen_declaration'];root=Path(os.environ['CURRENT_FINANCE_FROZEN_SOURCE_ROOT'])
    path=root/declaration['path'];assert sha256(path.read_bytes()).hexdigest()==declaration['sha256']
    changes={}
    for path,digest in json.loads(path.read_bytes())['files'].items():
        actual=sha256((repo/path).read_bytes()).hexdigest()
        if actual!=digest:changes[path]=dict(frozen_sha256=digest,current_sha256=actual)
    assert changes==pins['explicit_current_source_changes'],'CURRENT_MODEL_UNDECLARED_FROZEN_CHANGE'
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes();assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw)
        if variable=='FIRST_FINANCE_MODEL_ORIGINAL_REPORT':
            assert actual['status']=='INCOMPLETE'and actual['observed_case_count']==0
            assert actual['installation_failed_before_commit']and actual['error']=='Object of type datetime is not JSON serializable'
            assert actual['cp6_restored']and actual['advisor_gate']and actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
            before=dict(actual['source_declaration']['current_installation']);after=dict(product.sources())
            before.pop('entrypoint_sha256');after.pop('entrypoint_sha256');assert before==after
            changed={path:dict(first_sha256=digest,current_sha256=sha256((repo/path).read_bytes()).hexdigest())
                for path,digest in actual['source_declaration']['qualification']['files'].items()
                if sha256((repo/path).read_bytes()).hexdigest()!=digest}
            assert changed==pins['first_failed_source_changes']and set(changed)=={'scripts/cp7_current_finance_model_installation.py'}
            originals[variable]=dict(proof,observed_status='INCOMPLETE')
            continue
        assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        if variable=='CURRENT_BOUNDED_FINANCE_ORIGINAL_REPORT':
            assert actual['native']['counts']=={'PASS':5}and actual['required_case_ids_pass']and actual['observed_case_count']==5
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
        elif variable in('MODEL_POLICY_NATIVE_ORIGINAL_REPORT','MODEL_V2_NATIVE_ORIGINAL_REPORT'):
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']and actual['observed_case_count']==6
            assert actual['native']['counts']=={'PASS':6}
            assert actual['model_policy_source_sha256']==product.policy.verify_sources()
            if variable=='MODEL_POLICY_NATIVE_ORIGINAL_REPORT':
                assert actual['required_case_ids']['native']==business.policy.IDS['native']
            else:
                assert actual['required_case_ids']['native']==business.evaluation.IDS['native']
                assert actual['model_evaluation_v2_source_sha256']==product.evaluation.verify_sources()
        else:raise ValueError('CURRENT_MODEL_UNDECLARED_ORIGINAL: '+variable)
        originals[variable]=dict(proof,observed_status='PASS')
    assert set(originals)=={'CURRENT_BOUNDED_FINANCE_ORIGINAL_REPORT','MODEL_POLICY_NATIVE_ORIGINAL_REPORT','MODEL_V2_NATIVE_ORIGINAL_REPORT','FIRST_FINANCE_MODEL_ORIGINAL_REPORT'}
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            p=Path(module.__file__);assert sha256(p.read_bytes()).hexdigest()==pins['files']['scripts/'+p.name],('CURRENT_MODEL_LOADED_SOURCE_CHANGED',name)
            loaded.append(name)
    return dict(frozen_predecessor=predecessor,current_installation=product.sources(),qualification=pins,
        explicit_current_source_changes=changes,actual_originals_verified=originals,
        retained_business_cases=business.source_binding(),actual_loaded_modules_verified=loaded)
