"""Exact predecessor admission plus separately qualified B input continuity.

B's newer source files are checked in B's immutable checkout. They are never
silently accepted as the old common files retained by the full A predecessor.
"""
from pathlib import Path
from hashlib import sha256
import ast,importlib.util,json,os,subprocess,sys

HERE=Path(__file__).resolve().parent
CONTRACT='cp7.current-versioned-performance-native36-qualification.v1'
B_HEAD='c7f06b855512e0c8d450522c36e84f4cab570a2a'
B_CONTRACTS=json.loads((HERE/'B_COMPONENT_CONTRACTS.json').read_bytes())
A_NATIVE='CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT'
A_RESTORE='CURRENT_VERSIONED_TARGET_RESTORE_ORIGINAL_REPORT'
VARIABLES=set(B_CONTRACTS)|{A_NATIVE,A_RESTORE}


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def verify_B(actual,proof,contract,root):
    assert proof==contract['proof']
    assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
    assert actual['production_go']is actual['independent_acceptance']is False
    expected=contract['case_ids'];assert actual['required_case_ids']==expected
    assert actual['required_case_ids_pass']and actual['required_case_counts_pass']
    assert actual['observed_case_count']==sum(map(len,expected.values()))
    assert actual['restore_components']and all(actual['restore_components'].values())
    maps={k:v for k,v in actual.items()if k.endswith('source_sha256')and isinstance(v,dict)}
    assert maps==contract['source_maps']and maps
    for values in maps.values():
        for path,digest in values.items():
            relative=path if path.startswith(('scripts/','src/'))else'scripts/'+path
            assert sha256((root/relative).read_bytes()).hexdigest()==digest,relative
    for group,names in expected.items():
        row=actual[group];cases=row['races'if group=='races'else'cases']
        assert set(cases)==set(names)and row['counts']=={'PASS':len(names)}
        for case in cases.values():
            assert case['status']=='PASS'
            if group=='native':
                assert case['full_boundary_restored']and case['public_schema_unchanged']
                assert all(v in(0,[],{})for v in case.get('session_leaks',{}).values())
            else:assert not case.get('session_leaks')
        if group!='native':
            assert row['status']=='RUN_COMPLETE'and row['database_remaining']==0 and not row.get('cleanup_failures')
            if group in('http','browser'):
                assert row['real_auth']and not row['jwt_signed_by_runtime']and not row['test_only_usage_grant']
                assert row['auth_counts']==dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)
            if group=='browser':assert row['host_exit']==0 and row['console_errors']==0 and not row['auth_cleanup_failures']
    if 'SCALE' in actual['label']:
        assert actual['model_target_v2_scale_qualified']and actual['official_finance_included']is False
        assert actual['full_factory3600_qualified']is False
    return dict(qualified_head=proof['head'],continuity_head=B_HEAD,source_maps=len(maps),case_count=actual['observed_case_count'],new_runtime_credit=False)


def business_continuity(repo,root):
    path='scripts/cp7_ow11_model_target_consumer_v2_cases.py'
    def functions(base):
        return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse((base/path).read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name!='sources'}
    before,after=functions(repo),functions(root)
    assert before==after and {'cases','call','capture','read'}<=set(before),'B_BUSINESS_BODY_CHANGED'
    return dict(all_business_function_bodies_unchanged=True,functions=len(before),source_declaration_checked_separately=True)


def admitted(repo,here,ids,product,business):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==CONTRACT and pins['case_ids']==list(ids)and len(ids)==len(set(ids))==36
    assert set(pins['actual_qualification_originals'])==VARIABLES and pins['B_frozen_head']==B_HEAD
    predecessor=load('qualified_versioned_native36',here/'frozen_admission.py').invoke(pins)
    assert predecessor['current_installation']==product.predecessor.sources()
    declaration=pins['frozen_declaration']
    assert declaration==dict(path='scripts/current-versioned-target-native-qualification/SOURCE.json',head=predecessor['frozen_head'],sha256=predecessor['source_manifest_sha256'])
    assert sha256((repo/declaration['path']).read_bytes()).hexdigest()==declaration['sha256']
    # No predecessor source exception is allowed for the late two-body adapter.
    for path,digest in predecessor['qualification']['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    root=Path(os.environ['B_PERFORMANCE_FROZEN_SOURCE_ROOT']).resolve()
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==B_HEAD
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],text=True).strip()
    originals={};B_results={};actuals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw);actuals[variable]=actual
        assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        assert actual['production_go']is actual['independent_acceptance']is False
        if variable in B_CONTRACTS:B_results[variable]=verify_B(actual,proof,B_CONTRACTS[variable],root)
        else:
            assert(actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
            if variable==A_NATIVE:
                assert proof['head']==declaration['head']
                assert actual['source_declaration']['qualification']==predecessor['qualification']
                assert actual['label']=='CP7_CURRENT_VERSIONED_TARGET_NATIVE36'
                assert actual['required_case_ids']==list(ids)and actual['required_case_ids_pass']
                assert actual['observed_case_count']==36 and actual['native']['counts']=={'PASS':36}and actual['complete_preuse_removal']
                assert all(row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']for row in actual['native']['cases'].values())
            else:
                assert actual['label']=='CP7_CURRENT_VERSIONED_TARGET_USED_RESTORE8'
                assert actual['required_steps_pass']and len(actual['steps'])==8 and actual['restore_raw_public_equal']
                assert [row['step']for row in actual['steps']]==actual['required_steps']
                assert all(row['status']=='PASS'for row in actual['steps'])
                assert actual['source_declaration']['qualification']['actual_qualification_originals'][A_NATIVE]==pins['actual_qualification_originals'][A_NATIVE]
        originals[variable]=dict(proof,observed_status=actual['status'])
    manifest=json.loads((product.performance.ROOT/'BOUND_B_SOURCES.json').read_bytes())
    assert manifest['B_head']==B_HEAD and manifest['actual_component_proof']==pins['actual_qualification_originals']['B_PERFORMANCE_SCALE_ORIGINAL_REPORT']
    for name,record in manifest['files'].items():
        assert(root/record['qualified_path']).read_bytes()==(product.performance.ROOT/name).read_bytes()
    continuity=business_continuity(repo,root)
    a=pins['actual_qualification_originals']['B_PERFORMANCE_TRANSPORT_A_ORIGINAL_REPORT'];b=pins['actual_qualification_originals']['B_PERFORMANCE_TRANSPORT_B_ORIGINAL_REPORT']
    assert a['head']==b['head']and a['run_id']==b['run_id']
    unique={name for v in ('B_PERFORMANCE_TRANSPORT_A_ORIGINAL_REPORT','B_PERFORMANCE_TRANSPORT_B_ORIGINAL_REPORT')for names in actuals[v]['required_case_ids'].values()for name in names}
    assert len(unique)==11
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__);assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name];loaded.append(name)
    return dict(qualified_current_versioned_target=predecessor,current_installation=product.sources(),qualification=pins,
        actual_originals_verified=originals,B_component_source_continuity=B_results,B_business_continuity=continuity,
        exact_B_inputs=product.performance.sources(),actual_loaded_modules_verified=loaded,retained_business_cases=business.source_binding(),
        full_factory3600_qualified=False,production_go=False,independent_acceptance=False)
