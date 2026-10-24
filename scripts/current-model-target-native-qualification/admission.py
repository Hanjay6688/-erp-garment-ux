"""Frozen full Native15 plus exact B freshness/dated target Originals."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,sys

def admitted(repo,here,ids,product,business):
    s=importlib.util.spec_from_file_location('full_model_frozen_admission',here/'frozen_admission.py')
    frozen=importlib.util.module_from_spec(s);s.loader.exec_module(frozen);predecessor=frozen.invoke()
    assert predecessor['current_installation']==product.predecessor.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==20
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_DATED_TARGET_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    declaration=pins['frozen_declaration'];root=Path(os.environ['CURRENT_MODEL_FROZEN_SOURCE_ROOT'])
    path=root/declaration['path'];assert sha256(path.read_bytes()).hexdigest()==declaration['sha256']
    changes={}
    for path,digest in json.loads(path.read_bytes())['files'].items():
        actual=sha256((repo/path).read_bytes()).hexdigest()
        if actual!=digest:changes[path]=dict(frozen_sha256=digest,current_sha256=actual)
    assert changes==pins['explicit_current_source_changes']and len(changes)==9
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes();assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw)
        assert actual['cp6_restored']and actual['advisor_gate'],variable
        assert actual['status']==('INCOMPLETE'if variable in('FIRST_MODEL_TARGET_NATIVE_ORIGINAL_REPORT','GUARDED_MODEL_TARGET_NATIVE_ORIGINAL_REPORT')else'PASS'),variable
        if variable=='CURRENT_FINANCE_MODEL_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
            assert actual['native']['counts']=={'PASS':15}and actual['observed_case_count']==15 and actual['required_case_ids_pass']
            assert actual['required_case_ids']==list(business.previous.IDS)
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        elif variable=='BASELINE_FRESHNESS_ORIGINAL_REPORT':
            assert actual['baseline_freshness_source_sha256']==product.freshness.verify_sources()
            assert actual['native']['counts']=={'PASS':3}and actual['observed_case_count']==3
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']
            assert actual['required_case_ids']['native']==business.target.fresh.IDS['native']
        elif variable=='MODEL_TARGET_NATIVE_ORIGINAL_REPORT':
            assert actual['model_target_source_sha256']==product.target.verify_sources()
            assert actual['native']['counts']=={'PASS':6}and actual['observed_case_count']==6
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']
            assert actual['required_case_ids']['native']==business.target.IDS['native']
        elif variable=='FIRST_MODEL_TARGET_NATIVE_ORIGINAL_REPORT':
            assert actual['native']['counts']=={'INCOMPLETE':6}and actual['observed_case_count']==6
            assert sum(row.get('error')=='AUDITOR_BUSINESS_DAY_ROLLOVER'for row in actual['native']['cases'].values())==5
            warehouse=actual['native']['cases']['OW11_MODEL_TARGET_NATIVE_WAREHOUSE_ONLY_READ']
            assert warehouse['status']=='INCOMPLETE'and 'StopIteration'in warehouse['traceback']
        elif variable=='GUARDED_MODEL_TARGET_NATIVE_ORIGINAL_REPORT':
            assert actual['native']['counts']=={'PASS':5,'INCOMPLETE':1}and actual['observed_case_count']==6
            assert actual['required_case_ids_pass']and not actual['required_case_counts_pass']
            failed={key:row for key,row in actual['native']['cases'].items()if row['status']!='PASS'}
            assert list(failed)==['OW11_MODEL_TARGET_NATIVE_WAREHOUSE_ONLY_READ']
            assert 'MODEL_TARGET_FG_FIXTURE_LOOKUP'in next(iter(failed.values()))['error']
            assert 'AUDITOR_BUSINESS_DAY_ROLLOVER'not in json.dumps(actual)
        else:raise ValueError('CURRENT_DATED_TARGET_UNDECLARED_ORIGINAL: '+variable)
        originals[variable]=dict(proof,observed_status=actual['status'])
    assert set(originals)=={'CURRENT_FINANCE_MODEL_ORIGINAL_REPORT','BASELINE_FRESHNESS_ORIGINAL_REPORT','MODEL_TARGET_NATIVE_ORIGINAL_REPORT','FIRST_MODEL_TARGET_NATIVE_ORIGINAL_REPORT','GUARDED_MODEL_TARGET_NATIVE_ORIGINAL_REPORT'}
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__);assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name]
            loaded.append(name)
    return dict(frozen_predecessor=predecessor,current_installation=product.sources(),qualification=pins,
        explicit_current_source_changes=changes,actual_originals_verified=originals,
        retained_business_cases=business.source_binding(),actual_loaded_modules_verified=loaded)
