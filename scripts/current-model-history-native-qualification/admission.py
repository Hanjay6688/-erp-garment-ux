"""Require actual current Native20 and complete scoped-history component proofs."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,sys
import cp7_ow11_model_history_scope_cases as scoped
import cp7_ow11_model_history_runtime_transport_cases as transport

VARIABLES={'CURRENT_MODEL_TARGET_ORIGINAL_REPORT','MODEL_HISTORY_SCOPE_ORIGINAL_REPORT',
 'MODEL_HISTORY_NATIVE_ORIGINAL_REPORT','MODEL_HISTORY_TRANSPORT_ORIGINAL_REPORT',
 'FIRST_MODEL_HISTORY_TRANSPORT_ORIGINAL_REPORT'}


def admitted(repo,here,ids,product,business):
    spec=importlib.util.spec_from_file_location('qualified_current_target_native20',here/'frozen_admission.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    predecessor=frozen.invoke()
    assert predecessor['current_installation']==product.predecessor.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.current-model-history-native25-qualification.v1'
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==25
    declaration=pins['frozen_declaration']
    assert declaration==dict(path='scripts/current-model-target-native-qualification/SOURCE.json',
        head=frozen.FROZEN_HEAD,sha256=predecessor['source_manifest_sha256'])
    assert sha256((repo/declaration['path']).read_bytes()).hexdigest()==declaration['sha256']
    changes={path:dict(frozen_sha256=digest,current_sha256=sha256((repo/path).read_bytes()).hexdigest())
        for path,digest in predecessor['qualification']['files'].items()
        if sha256((repo/path).read_bytes()).hexdigest()!=digest}
    assert changes==pins['explicit_current_source_changes']
    assert set(changes)=={'scripts/cp7_ow11_model_history_runtime_transport_cases.py',
                          'scripts/cp7_ow11_model_history_runtime_transport_probe.py'}
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_SCOPED_HISTORY_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    assert set(pins['actual_qualification_originals'])==VARIABLES
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw);first=variable=='FIRST_MODEL_HISTORY_TRANSPORT_ORIGINAL_REPORT'
        assert actual['status']==proof['status']==('INCOMPLETE'if first else'PASS')
        assert actual['cp6_restored']and actual['advisor_gate'],variable
        if variable=='CURRENT_MODEL_TARGET_ORIGINAL_REPORT':
            assert proof['head']==frozen.FROZEN_HEAD
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
            assert actual['source_declaration']['qualification']==predecessor['qualification']
            assert actual['required_case_ids']==list(business.previous.IDS)and actual['required_case_ids_pass']
            assert actual['native']['counts']=={'PASS':20}and actual['observed_case_count']==20
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        elif first:
            assert proof['head']=='aca11228dac03c2949b8c3f275007de018f05bfd'
            assert actual['observed_case_count']==1 and actual['native']['counts']=={'PASS':1}
            assert not actual['required_case_ids_pass']and not actual['required_case_counts_pass']
            for group in ('http','races'):
                row=actual[group]
                assert row['status']=='INCOMPLETE'and row['database_remaining']==0
                assert row['error']=="OW13A_LEGACY_ORACLE_NOT_EXACT_PREDECESSOR_22: {'database_authority': ['CURRENT']}"
                assert not row.get('counts')and not row.get('cases')and not row.get('races')
            assert actual['http']['auth_counts']==dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)
        else:
            provider=(scoped if variable=='MODEL_HISTORY_SCOPE_ORIGINAL_REPORT'else
                      business.history if variable=='MODEL_HISTORY_NATIVE_ORIGINAL_REPORT'else transport)
            assert actual['required_case_ids']==provider.IDS
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']
            assert actual['observed_case_count']==sum(map(len,provider.IDS.values()))
            expected_sources=product.scope.verify_sources()if provider is scoped else product.runtime.verify_sources()
            key='model_history_scope_source_sha256'if provider is scoped else'model_history_runtime_source_sha256'
            assert actual[key]==expected_sources
            for group,names in provider.IDS.items():
                row=actual[group];cases=row.get('races'if group=='races'else'cases',{})
                assert row['counts']=={'PASS':len(names)}and set(cases)==set(names)
                assert all(c['status']=='PASS'for c in cases.values())
                if group=='native':
                    assert row['complete_boundary_restored']
                    assert all(c['full_boundary_restored']and c['public_schema_unchanged']for c in cases.values())
                else:
                    assert row['status']=='RUN_COMPLETE'and row['database_remaining']==0
                    assert not row.get('cleanup_failures')and not row.get('session_leaks')
            if provider is transport:
                assert actual['transport_source_sha256']==transport.sources()
                assert actual['model_history_runtime_transport_qualified']
                http=actual['http']
                assert http['real_auth']and not http['jwt_signed_by_runtime']and not http['test_only_usage_grant']
                assert http['auth_counts']==dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)
                assert not http.get('auth_cleanup_failures')
        originals[variable]=dict(proof,observed_status=actual['status'])
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__);assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name]
            loaded.append(name)
    return dict(qualified_current_target=predecessor,current_installation=product.sources(),qualification=pins,
        actual_originals_verified=originals,actual_loaded_modules_verified=loaded,
        retained_business_cases=business.source_binding(),production_go=False,independent_acceptance=False)
