"""Bind complete scoped-model qualification and exact B target-v2 Originals."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,sys
import cp7_ow11_model_selection_cases as selection
import cp7_ow11_model_target_binding_cases as binding
import cp7_ow11_model_target_source_v2_cases as source
import cp7_ow11_model_target_consumer_v2_cases as consumer
import cp7_ow11_model_target_transport_v2_parts as transport
import cp7_ow11_model_target_v2_browser_cases as browser

PROVIDERS={
    'MODEL_SELECTION_ORIGINAL_REPORT':selection,
    'PHYSICAL_BINDING_ORIGINAL_REPORT':binding,
    'MODEL_TARGET_SOURCE_V2_ORIGINAL_REPORT':source,
    'MODEL_TARGET_CONSUMER_V2_ORIGINAL_REPORT':consumer,
    'MODEL_TARGET_BROWSER_V2_ORIGINAL_REPORT':browser,
}
TRANSPORT_VARIABLES={'MODEL_TARGET_TRANSPORT_V2_A_ORIGINAL_REPORT':'A','MODEL_TARGET_TRANSPORT_V2_B_ORIGINAL_REPORT':'B'}
SELECTED_VARIABLES={'CURRENT_SELECTED_RETURN_CONTRACT_ORIGINAL_REPORT','CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT','CURRENT_SELECTED_RETURN_RESTORE_ORIGINAL_REPORT'}
VARIABLES=set(PROVIDERS)|set(TRANSPORT_VARIABLES)|SELECTED_VARIABLES|{'CURRENT_SCOPED_MODEL_ORIGINAL_REPORT','CURRENT_SCOPED_MODEL_RESTORE_ORIGINAL_REPORT'}
CONTRACT='cp7.current-versioned-target-native36-qualification.v1'


def admitted(repo,here,ids,product,business):
    spec=importlib.util.spec_from_file_location('qualified_scoped_model_native30',here/'frozen_admission.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    predecessor=frozen.invoke()
    assert predecessor['current_installation']==product.predecessor.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==CONTRACT and pins['case_ids']==list(ids) and len(ids)==len(set(ids))==36
    declaration=pins['frozen_declaration']
    assert declaration==dict(path='scripts/current-scoped-model-native-qualification/SOURCE.json',head=frozen.FROZEN_HEAD,sha256=predecessor['source_manifest_sha256'])
    assert sha256((repo/declaration['path']).read_bytes()).hexdigest()==declaration['sha256']
    changes={p:dict(frozen_sha256=d,current_sha256=sha256((repo/p).read_bytes()).hexdigest())for p,d in predecessor['qualification']['files'].items()if sha256((repo/p).read_bytes()).hexdigest()!=d}
    assert changes==pins['explicit_current_source_changes']==json.loads((here/'EXPLICIT_CURRENT_SOURCE_CHANGES.json').read_bytes())
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    assert set(pins['actual_qualification_originals'])==VARIABLES
    originals={};transport_ids=set();transport_heads=set();transport_runs=set()
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes'] and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw)
        assert actual['status']==proof['status']=='PASS' and actual['cp6_restored'] and actual['advisor_gate']
        assert actual['production_go']is False and actual['independent_acceptance']is False
        if variable.startswith('CURRENT_SCOPED_MODEL_'):
            assert (actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
            assert actual['baseline_full22_all_rows_all_sequences_equal'] and actual['baseline_advisors_equal']
            if variable=='CURRENT_SCOPED_MODEL_ORIGINAL_REPORT':
                assert proof['head']==frozen.FROZEN_HEAD
                assert actual['source_declaration']['qualification']==predecessor['qualification']
                assert actual['required_case_ids']==list(business.previous.IDS)
                assert actual['required_case_ids_pass'] and actual['native']['counts']=={'PASS':30}
                assert actual['observed_case_count']==30 and actual['complete_preuse_removal']
                assert all(row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']for row in actual['native']['cases'].values())
            else:
                assert actual['label']=='CP7_CURRENT_SCOPED_MODEL_USED_RESTORE8'
                assert actual['required_steps_pass'] and len(actual['steps'])==8
                assert [row['step']for row in actual['steps']]==actual['required_steps']
                assert all(row['status']=='PASS'for row in actual['steps']) and actual['restore_raw_public_equal']
        elif variable in SELECTED_VARIABLES:
            assert(actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']
            assert actual['source_declaration']['current_installation']['delta']==product.selected.delta.sources()
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
            if variable=='CURRENT_SELECTED_RETURN_CONTRACT_ORIGINAL_REPORT':
                assert proof['head']=='e0a4721f586476b36de2f5941d4970ea7de2bb8e'
                assert actual['baseline']['counts']==actual['native']['counts']=={'PASS':6}and actual['execution_count']==12
                assert actual['required_case_ids']==list(business.selected_contract.IDS)and actual['required_case_ids_pass']
                path='scripts/current-cp6-contract-qualification/cases.py'
                assert actual['source_declaration']['qualification']['files'][path]==sha256((repo/path).read_bytes()).hexdigest()
                assert all(row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']for group in('baseline','native')for row in actual[group]['cases'].values())
            elif variable=='CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT':
                assert proof['head']=='8e878ed6c95a7249734f5d53b5d33ee1114ec599'
                assert actual['native']['counts']=={'PASS':20}and actual['observed_case_count']==20
                assert actual['required_case_ids_pass']and actual['complete_preuse_removal']
                assert all(row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']for row in actual['native']['cases'].values())
            else:
                assert actual['label']=='CP7_CURRENT_SELECTED_RETURN_USED_RESTORE8'
                assert actual['required_steps_pass']and len(actual['steps'])==8 and all(row['status']=='PASS'for row in actual['steps'])
                assert actual['restore_raw_public_equal']
                assert actual['source_declaration']['qualification']['actual_qualification_originals']['CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT']==pins['actual_qualification_originals']['CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT']
        else:
            if variable in TRANSPORT_VARIABLES:
                part=TRANSPORT_VARIABLES[variable]
                expected=transport.PARTS[part]
                assert actual['transport_part']==part
                transport_heads.add(proof['head']);transport_runs.add(proof['run_id'])
            else:expected=PROVIDERS[variable].IDS
            assert actual['required_case_ids']==expected
            assert actual['required_case_ids_pass'] and actual['required_case_counts_pass']
            assert actual['observed_case_count']==sum(map(len,expected.values()))
            assert all(actual['restore_components'].values())
            found=0
            for key,values in actual.items():
                if key.endswith('source_sha256')and isinstance(values,dict):
                    found+=1
                    for path,digest in values.items():
                        relative=path if path.startswith(('scripts/','src/'))else'scripts/'+path
                        assert sha256((repo/relative).read_bytes()).hexdigest()==digest,(variable,relative)
            assert found
            for group,names in expected.items():
                row=actual[group];cases=row['races'if group=='races'else'cases']
                assert set(cases)==set(names)and row['counts']=={'PASS':len(names)}
                for case in cases.values():
                    assert case['status']=='PASS'
                    if group=='native':
                        assert case['full_boundary_restored']and case['public_schema_unchanged']
                        assert all(v in(0,[],{})for v in case.get('session_leaks',{}).values())
                    else:assert not case.get('session_leaks')
                if variable in TRANSPORT_VARIABLES:transport_ids.update(names)
                if group!='native':
                    assert row['status']=='RUN_COMPLETE'and row['database_remaining']==0 and not row.get('cleanup_failures')
                    if group in('http','browser'):
                        assert row['real_auth']and not row['jwt_signed_by_runtime']and not row['test_only_usage_grant']
                        assert row['auth_counts']==dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)
                    if group=='browser':assert row['host_exit']==0 and row['console_errors']==0 and not row['auth_cleanup_failures']
        originals[variable]=dict(proof,observed_status=actual['status'])
    assert len(transport_ids)==11 and len(transport_heads)==len(transport_runs)==1
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__);assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name];loaded.append(name)
    return dict(qualified_current_scoped_model=predecessor,current_installation=product.sources(),qualification=pins,
        actual_originals_verified=originals,actual_loaded_modules_verified=loaded,retained_business_cases=business.source_binding(),
        B_transport_unique_cases=11,production_go=False,independent_acceptance=False)
