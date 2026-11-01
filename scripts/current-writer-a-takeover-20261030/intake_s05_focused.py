"""Exact canonical focused intake: fresh2 plus invariant retained35, never fresh37."""
from pathlib import Path
from hashlib import sha256,file_digest
import argparse,ast,json,re,zipfile
import intake_join37 as original_join
import intake_join_layout as css_parent
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,full_census,declared_files,ALL22

HEAD='49f8f1697e7777cf9542f131c7d3c5d135cc1ec7'
TREE='179ef11defd62439371689ffaf766b5c83da4325'
RUN=41329176840  # Actual reader49 attempt 1 observed after owning-window activation.
JOB=124915457260
ARTIFACT=None  # Arm only after the actual terminal artifact is observed.
BASE='50c77207e088af16988d7d91a5b06f72e8e30ecc'
BASE_TREE='28295dd44a59f1832bebb86af24bd85df4471f4b'
NS='scripts/current-s05-css-followup-qualification/'
OLD='scripts/current-s03-sku-s05-composite-qualification/'
WORKFLOW='.github/workflows/cp7-s05-css-followup.yml'
ROOT_HEAD='dd5011d1453f5d8ac75bb11520e0e2c7cf38459b'
ROOT_TREE='186c94227610e202629c5d321ecbcea8b75c9f62'
ROOT_PATH='docs/cp7/d17-14/ow15/CURRENT38_ROOT_RETAINED35_20261101.json'
ROOT_PIN=dict(bytes=10877,sha256='4743e60ed6fdf33682a9e576ce180675923ed7287fda5a6372f56509a89f39c0')
MAIN='CP7_CURRENT_S05_CSS_RETAIN35_BROWSER2.json'
CASE='CURRENT_S05_CSS_RETAINED35_FRESH_BROWSER2'
GATES=original_join.GATES
READER_MANIFEST='scripts/cp7_s05_s03_sku_composition/SOURCE.json'
FOUNDATION_IDS={
    'erp.materials':'c8c30000-0000-4000-8000-000000000002',
    'erp.suppliers':'c8c30000-0000-4000-8000-000000000001',
    'erp.product_models':'a2000000-0000-0000-0000-000000000001',
    'erp.contractors':'a1000000-0000-0000-0000-000000000001',
    'erp.production_patterns':'c8c10000-0000-4000-8000-000000000001',
    'erp.sizes':'c8c10000-0000-4000-8000-000000000002',
    'erp.products':'c8c10000-0000-4000-8000-000000000004',
    'erp.locations':'c8c20000-0000-4000-8000-000000000001',
    'erp.laundry_vendors':'c8c20000-0000-4000-8000-000000000002',
    'erp.wash_processes':'c8c20000-0000-4000-8000-000000000003',
    'erp.po_work_component_snapshots':'a4100000-0000-0000-0000-000000000001',
}

def foundation_source(g):
    origin=strict(g.read(NS+'FOUNDATION_ORIGIN.json'))
    fields(origin,dict(status='EXACT_EXISTING_FIXTURE_SETUP_SOURCE_NOT_NEW_FINANCIAL_FIXTURE',
        source_commit=BASE,seed='cp6_ao_ap_installed.seed',original_condition='no erp.app_users',
        original_committed_witness='scripts/current-s03-sku-native14-binding/retained-s03-f42e/native_runner.py',
        historical_cutting_compatibility_trigger='trg_06_require_pattern_identity',
        trigger_suspension='EXACT_ORIGINAL_SEED_ONLY_MUST_RESTORE',new_Native_case_credit=0,production_go=False),
        'ONLY_THE_EXISTING_COMMITTED_FOUNDATION_SEED')
    expected={'scripts/cp6_ao_ap_installed.py','scripts/cp6_v2620e_counterexample_regression.py',
        'scripts/current-s03-sku-native14-binding/retained-s03-f42e/native_runner.py',
        OLD+'browser_prepare.py','supabase/tests/cp3_r4_full_schema_seed.sql',
        'supabase/tests/cp3_r3_full_schema_seed.sql','supabase/tests/cp6_laundry_qc_concurrency_seed.sql'}
    exact(set(origin['files']),expected,'ENTIRE_ORIGINAL_SEED_AND_INCLUDE_CLOSURE')
    for name,expected_pin in origin['files'].items():
        raw=g.read(name);exact(raw,g.read(name,BASE),'FOUNDATION_ORIGINAL_BYTES_UNCHANGED:'+name)
        exact(pin(raw),expected_pin,'EXACT_ORIGINAL_FOUNDATION_PIN:'+name)
    assignments={node.targets[0].id:ast.literal_eval(node.value)for node in ast.parse(g.read(NS+'foundation.py')).body
        if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
        and node.targets[0].id in('REQUIRED','SEED','OPERATOR_AUTH')}
    exact(assignments,dict(REQUIRED=FOUNDATION_IDS,SEED='cp6_ao_ap_installed.seed',
        OPERATOR_AUTH='c8c00000-0000-4000-8000-000000000101'),'EXACT_EXISTING_FOUNDATION_IDENTITIES')
    return dict(status='EXACT_ORIGINAL_FOUNDATION_SOURCE_AND_INCLUDE_CLOSURE',seed=origin['seed'],
        source_commit=BASE,files=origin['files'],Native_case_credit=0)

def foundation_mode(value):
    require(type(value)is dict and set(value)=={'app_users','active_owner_roles','original_owner','required'},'EXACT_FOUNDATION_STATE_FIELDS')
    require(type(value['app_users'])is int and value['app_users']>=0,'INTEGER_FOUNDATION_USER_COUNT')
    exact(value['active_owner_roles'],1,'ONE_ACTUAL_ACTIVE_OWNER_ROLE')
    require(type(value['original_owner'])is int,'INTEGER_ORIGINAL_OWNER_COUNT')
    exact(set(value['required']),set(FOUNDATION_IDS),'ALL_ELEVEN_FOUNDATION_DEPENDENCIES')
    require(all(type(v)is bool for v in value['required'].values()),'BOOLEAN_MASTER_EXISTENCE')
    if value['app_users']==0 and value['original_owner']==0 and not any(value['required'].values()):
        return 'ORIGINAL_EMPTY_DATABASE_SEED_REQUIRED'
    if value['app_users']>0 and value['original_owner']==1 and all(value['required'].values()):
        return 'ORIGINAL_FOUNDATION_ALREADY_PRESENT'
    raise ValueError('ROOT_PARTIAL_OR_FOREIGN_FOUNDATION_REFUSED')

def check_foundation(main,part,source_proof):
    check=main['fixture_foundation_precheck'];setup=part['fixture_foundation']
    fields(check,dict(status='READ_ONLY_FOUNDATION_PRECHECK',database_mutated=False,Native_case_credit=0),
        'READ_ONLY_CHECK_BEFORE_EXPENSIVE_PARENT')
    exact(check['source'],source_proof,'ACTUAL_PRECHECK_ORIGINAL_SOURCE')
    mode=foundation_mode(check['initial']);exact(check['mode'],mode,'EXACT_INITIAL_FOUNDATION_MODE')
    fields(setup,dict(status='EXACT_RETAINED_FIXTURE_FOUNDATION_READY',source=source_proof,mode=mode,
        initial=check['initial'],seed='cp6_ao_ap_installed.seed',Native_case_credit=0,retained_cases_rerun=False,
        production_go=False,seed_called=mode=='ORIGINAL_EMPTY_DATABASE_SEED_REQUIRED',all22_equal=True,
        original_seed_schema_ACL_equal=True,protected_role_data_equal=True,
        only_existing_Native_SQL_harness_usage_overlay=True,connection_and_commit_owned_by_component=True),
        'EXACT_EXISTING_FOUNDATION_COMMITTED_WITHOUT_NEW_CASE_CREDIT')
    exact(foundation_mode(setup['final']),'ORIGINAL_FOUNDATION_ALREADY_PRESENT','EVERY_ORIGINAL_DEPENDENCY_READY')
    exact(setup['actual_all22_before'],setup['actual_all22_after'],'ALL22_CATALOG_UNCHANGED_BY_SETUP')
    exact(set(setup['actual_all22_before']),set(ALL22),'EVERY_FOUNDATION_CATALOG_CLASS_RETAINED')
    exact(setup['protected_role_data_before'],setup['protected_role_data_after'],'ALL_PROTECTED_ROLE_DATA_UNCHANGED')
    exact(set(setup['protected_role_data_before']),{'erp.app_roles','erp.app_role_permissions'},'BOTH_AUTHORITY_TABLES_RAW')
    return dict(actual_original_seed_mode=mode,setup_has_no_Native_case_credit=True,
        all22_catalog_and_protected_role_rows_unchanged=True,partial_or_foreign_foundation_refused=True)

def reader_source(g):
    raw=g.read(READER_MANIFEST,BASE)
    original=dict(bytes=5351,sha256='344d0248e341826978e4aad76bb1c3311bba2e69ac87cb1ad07785c06df7c237')
    exact(pin(raw),original,'EXACT_ORIGINAL_CURRENT_READER_MANIFEST')
    name='src/accessory-standard-report.css'
    before='a9d62618178521d25fa392e6497e24ebc1e8146277b9cda33a9d76e7ea76d16a'
    after='0ca870ad603a4654d44b4f9b8905f4e91c47d26ff45947d8017d17a1b8b3bcdf'
    a=json.dumps(name)+': '+json.dumps(before);b=json.dumps(name)+': '+json.dumps(after)
    text=raw.decode();exact(text.count(a),1,'ONE_CURRENT_READER_CSS_PIN')
    derived=text.replace(a,b,1).encode();exact(g.read(READER_MANIFEST),derived,'ONLY_REVIEWED_CURRENT_READER_CSS_PIN_CHANGED')
    exact(derived.decode().replace(b,a,1).encode(),raw,'ORIGINAL_READER_MANIFEST_RECOVERED_EXACTLY')
    manifest=strict(derived);old=strict(raw)
    exact({k:v for k,v in manifest.items()if k!='files'},{k:v for k,v in old.items()if k!='files'},'CURRENT_READER_CONTRACT_METADATA_UNCHANGED')
    exact(len(manifest['files']),41,'ALL41_CURRENT_READER_INPUTS')
    for path,digest in manifest['files'].items():
        g.verify_pin(path,digest)
        if path!=name:exact(digest,old['files'][path],'ALL_OTHER_FORTY_READER_PINS_UNCHANGED')
    functions=re.findall(r'create function\s+([\w.]+)\([^$]*?as \$\$(.*?)\$\$;',
        g.read('scripts/cp7_accessory_standard_report/report.sql').decode(),re.I|re.S)
    exact(len(functions),5,'EXACT_FIVE_UNCHANGED_READER_FUNCTION_SOURCES')
    proof=dict(path=READER_MANIFEST,original=original,derived=pin(derived),counted_changes=1,
        current_CSS_path=name,current_CSS_sha256=after,other_reader_source_pins_unchanged=40,
        complete_original_recovered=True,historical_manifests_changed=False,reader_SQL_or_Native_changes=False)
    full=dict(status='EXACT_CURRENT_READER_CSS_BINDING_AND_ALL41_INPUTS',**proof,
        actual_reader_inputs_checked=41,all_current_reader_source_pins_match=True,reader_function_sources=5,actual_case_credit=0)
    return manifest,proof,full

def source(g):
    with GitBytes(g.root,BASE,BASE_TREE)as parent:prior=css_parent.source(parent)
    manifest=strict(g.read(OLD+'SOURCE.json'));before=strict(g.read(OLD+'SOURCE.json',BASE))
    fields(manifest,dict(actual_cases=0,production_go=False,independent_acceptance=False),'SOURCE_IS_NOT_ACCEPTANCE')
    exact(len(manifest['files']),108,'CLOSED_108_SOURCE_PINS')
    for name,digest in manifest['files'].items():g.verify_pin(name,digest)
    exact({k:v for k,v in manifest.items()if k!='files'},{k:v for k,v in before.items()if k!='files'},
        'OLD_FULL37_PREPARATION_METADATA_NOT_REWRITTEN')
    routing={OLD+'source.py',OLD+'freeze.py'};changed=routing|{OLD+'SOURCE.json',READER_MANIFEST}
    base=g.entries(BASE);exact(len(base),14086,'EXACT_CSS_CANDIDATE_BASE')
    for name,entry in base.items():
        if name not in changed:exact(g.tree.get(name),entry,'UNCHANGED_PRODUCT_AND_PREPARED_ORACLE:'+name)
    added={name for name in manifest['files']if name.startswith(NS)or name==WORKFLOW}
    exact(len(added),21,'EXACT_FOCUSED_NAMESPACE_AND_ONE_WORKFLOW')
    exact(set(g.tree)-set(base),added,'NO_OTHER_PRODUCT_OR_QUALIFIER_ADDITION')
    exact(set(manifest['files'])-set(before['files']),added|{READER_MANIFEST},'ONLY_CLOSED_NEW_SOURCE_PINS_AND_CURRENT_READER_MANIFEST')
    for name,digest in before['files'].items():
        if name not in routing:exact(manifest['files'].get(name),digest,'UNCHANGED_PRIOR_SOURCE_PIN:'+name)
    origin=strict(g.read(NS+'ROUTING_ORIGIN.json'))
    exact(set(origin['files']),routing,'ONLY_TWO_OLD_ADMISSION_ROUTERS')
    for name,item in origin['files'].items():
        raw=g.read(name,BASE);exact(sha256(raw).hexdigest(),item['original_sha256'],'EXACT_ROUTING_ORIGINAL')
        text=raw.decode()
        for a,b in item['changes']:
            exact(text.count(a),1,'EXACT_ONE_ROUTING_ANCHOR');text=text.replace(a,b,1)
        exact(text.encode(),g.read(name),'ONLY_DECLARED_ROUTING_HUNKS')
        exact(sha256(text.encode()).hexdigest(),item['derived_sha256'],'EXACT_ROUTING_DERIVED')
        for a,b in reversed(item['changes']):
            exact(text.count(b),1,'EXACT_ONE_ROUTING_INVERSE');text=text.replace(b,a,1)
        exact(text.encode(),raw,'EXACT_ROUTING_ORIGINAL_RECOVERED')
    with GitBytes(g.root,ROOT_HEAD,ROOT_TREE)as root:
        raw=root.read(ROOT_PATH);exact(pin(raw),ROOT_PIN,'EXACT_PUBLIC_RETAINED_ROOT_RECEIPT')
    exact(g.read(NS+'ROOT_RETAINED35.json'),raw,'UNMODIFIED_COPIED_ACTUAL_ROOT_RETENTION')
    receipt=strict(raw)
    fields(receipt,dict(status='ROOT_RETAINED_CURRENT38_NATIVE31_S03_BROWSER4_NOT_AGGREGATE_PASS',
        head='08ef3bee814e6452b9193b53efc05d53abca2d9d',tree='abf7e8b78bd56907ace9fb30211d956b63d68797',
        run_id=41291621885,job_id=124803871870,artifact_id=13082560860,original_run_conclusion='failure',
        retained_Native_cases=31,retained_S03_browser_cases=4,fresh_case_credit=0,
        retained_cases_require_successor_source_invariance=True,original_restore_and_backup_valid=True,
        failed_run_relabelled_PASS=False,full37_qualified=False,package_all_five=False,
        production_go=False,independent_acceptance=False),'ACTUAL_OLD35_NOT_AGGREGATE_PASS')
    ids=receipt['source_admission']['case_ids']
    retained={case for label,values in ids.items()if label!='S05_browser2'for case in values}
    exact(len(retained),35,'EXACT_35_SOURCE_BOUND_OLD_CASES')
    exact(set(receipt['retained_cases']),retained,'EXACT_VALID_RETAINED_SET')
    for row in receipt['retained_cases'].values():fields(row,dict(status='PASS',retained=True,fresh_case_credit=0),'OLD_PASS_NEVER_FRESH')
    exact(receipt['missing_case_ids'],ids['S05_browser2'],'ONLY_MISSING_TWO_FRESH_IDS')
    exact(manifest['browser_case_ids'],ids['S05_browser2'],'UNCHANGED_S05_BROWSER_ASSERTION_IDENTITIES')
    reader_manifest,reader_derivation,reader_binding=reader_source(g)
    whole=dict(status='EXACT_CURRENT_S03_SKU_S05_BASE_AND_CLOSED_QUALIFIER_SOURCE',
        base_head=original_join.BASE,base_tree='e08f5eba90fd9a2deeb53a0a483c49e7a080e31c',
        unchanged_base_blobs_and_modes=13998,reviewed_S05_css_derivation=prior['reviewed_CSS_derivation'],
        reviewed_current_reader_manifest_derivation=reader_derivation,
        current_qualifier_files=109,current_own_source_hashes_verified=True,tracked_physical_changes_refused=True,
        untracked_executable_sources_refused=True,generated_outputs_are_not_source_waivers=True,
        actual_Native_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)
    invariance=dict(status='EXACT_S05_ONLY_CSS_PRODUCT_AND_RETAINED35_SOURCE_INVARIANCE',
        base_head=BASE,base_tree=BASE_TREE,unchanged_base_blobs_and_modes=14082,modified_old_qualification_files=3,
        added_focused_paths=21,modified_current_reader_manifests=1,current_reader_source_binding=reader_binding,
        whole_current_source=whole,backend_and_all_UI_unchanged_from_CSS_candidate=True,
        retained35_source_invariance=True,actual_new_cases=0,production_go=False,independent_acceptance=False)
    proof=dict(source_invariance=invariance,receipt=receipt,root_head=ROOT_HEAD,root_receipt=ROOT_PIN)
    return dict(source_pins=108,unchanged_product_parent_blobs=14082,qualified_routing_files=3,added_focused_paths=21,
        current_reader_manifest=reader_manifest,current_reader_source_binding=reader_binding,
        foundation_setup_source=foundation_source(g),
        prior_CSS_source=prior,expected_runtime_retention=proof,retained_ids=retained,fresh_ids=ids['S05_browser2'],
        actual_case_credit=0)

def intake(root,path,metadata):
    require(ARTIFACT is not None,'ACTUAL_TERMINAL_FOCUSED_ARTIFACT_NOT_PINNED')
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,artifact_id=ARTIFACT,
        artifact_name='cp7-s05-css-followup-browser2-1',run_attempt=1,conclusion='success',expired=False),
        'EXACT_ACTUAL_TERMINAL_FOCUSED_METADATA')
    archive=metadata['archive'];require(type(archive)is dict and set(archive)=={'bytes','sha256'},'EXACT_ARCHIVE_PIN')
    require(type(archive['bytes'])is int and archive['bytes']>0,'POSITIVE_EXACT_ARCHIVE_SIZE')
    require(type(archive['sha256'])is str and __import__('re').fullmatch('[0-9a-f]{64}',archive['sha256'])is not None,'EXACT_ARCHIVE_SHA256')
    path=Path(path);exact(path.stat().st_size,archive['bytes'],'CANONICAL_FOCUSED_ZIP_SIZE')
    with path.open('rb')as stream:actual=file_digest(stream,'sha256').hexdigest()
    exact(actual,archive['sha256'],'CANONICAL_FOCUSED_ZIP_DIGEST')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),len(set(names)),'NO_DUPLICATE_CANONICAL_MEMBER')
        for name in names:safe_path(name)
        require(z.testzip()is None,'FULL_FOCUSED_ZIP_CRC')
        prepared=source(g);proof=prepared['expected_runtime_retention'];ids=prepared['fresh_ids'];pins={}
        def original(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=original(MAIN);package=original('T3_PACKAGE_INSTALL.json');backup=original('T3_BACKUP_RESTORE_DRILL.json')
        supervision=original('S05_FOLLOWUP_SUPERVISION.json')
        original('T3_PACKAGE_FILES_INSTALL.json')
        fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[CASE],expected_case_count=1,
            observed_case_count=1,required_case_ids_pass=True,actual_Native_cases=0,actual_browser_cases=2,
            actual_business_cases=2,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
            retained_Native_cases=31,retained_S03_browser_cases=4,retained_cases_are_not_fresh=True,
            baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
            baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
            production_go=False,independent_acceptance=False),'FRESH_BROWSER2_AND_COMPLETE_NEW_RESTORE')
        require(not any(main.get(k)for k in ('error','restore_error','restore_traceback')),'NO_RUNTIME_OR_RESTORE_ERROR')
        fields(main['source_declaration'],dict(status='ACTUAL_RETAINED35_AND_EXACT_CURRENT_PRODUCT_ADMITTED_FOR_FRESH_BROWSER2',
            **proof,retained_case_credit_is_not_fresh=True,actual_new_cases=0,production_go=False,independent_acceptance=False),
            'RUNTIME_ACTUAL_ROOT_AND_SOURCE_INVARIANCE')
        financial=main['source_declaration']['current_installation']
        financial_pin=pin(json.dumps(financial,sort_keys=True,separators=(',',':')).encode())
        exact(financial_pin,proof['receipt']['qualified_financial_sources'],'ENTIRE_RETAINED_FINANCIAL_SOURCE_GRAPH_UNCHANGED')
        fields(main['source_declaration'],dict(current_reader_graph_checked_before_database=True),
            'ACTUAL_FULL_READER_GRAPH_ADMITTED_BEFORE_DATABASE')
        reader_graph=main['source_declaration']['current_reader_installation']
        exact(reader_graph['stage'],prepared['current_reader_manifest'],'ACTUAL_CURRENT_READER_STAGE_SOURCE')
        exact(reader_graph['parent'],financial,'ENTIRE_NATURAL_READER_FINANCIAL_PARENT_UNCHANGED')
        reader_maps=declared_files(g,dict(stage=reader_graph['stage']))
        exact(set(main['committed']),{CASE},'ONE_FOCUSED_COMPONENT')
        part=main['committed'][CASE]
        original_foundation=check_foundation(main,part,prepared['foundation_setup_source'])
        fields(part,dict(status='PASS',business_counts={'PASS':2},actual_Native_cases=0,actual_browser_cases=2,
            actual_Auth_HTTP_cases=0,actual_two_session_races=0,retained_Native_cases=31,retained_S03_browser_cases=4,
            retained_case_count=35,candidate_case_coverage=37,retained_cases_are_not_fresh=True,
            used_guard_refused_before_DDL=True,Afui_positive_HPP_zero_reimbursement_coverage=False,
            global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False),
            'NO_RETAINED35_AS_FRESH_OR_UNPROVEN_SCOPE')
        exact(part['retained35'],proof,'RAW_RUNTIME_ROOT_AND_INVARIANCE_EQUALS_IMMUTABLE_SOURCE')
        exact(set(part['business_cases']),set(ids),'ONLY_MISSING_TWO_CASES_FRESH')
        for row in part['business_cases'].values():fields(row,dict(status='PASS'),'FRESH_CASE_PASS')
        fresh=part['fresh_S05_browser2']
        fields(fresh,dict(status='PASS',actual_browser_cases=2,actual_Native_cases=0),'COMPLETE_REAL_AUTH_BROWSER2')
        original_join.browser(fresh['browser'],ids,g,OLD+'browser.mjs','ACTUAL_FRESH_S05_BROWSER2')
        require(not any(fresh.get(k)for k in ('first_browser_failure','reader_cleanup_failure')),'NO_READER_OR_BROWSER_FAILURE')
        require(bool(fresh.get('reader_post_browser_inverse')),'ACTUAL_READER_POST_BROWSER_INVERSE')
        exact(len(fresh['copy_catalog_admissions']),1,'ONE_ACTUAL_BROWSER_COMMITTED_COPY')
        fields(fresh['copy_catalog_admissions'][0],dict(all22_groups_equal_original_install=True),'RAW_BROWSER_COPY_ALL22')
        before=part['used_inverse_refusal_before'];exact(before,part['used_inverse_refusal_after'],'COMPLETE_USED_INVERSE_ZERO_EFFECT')
        census=full_census(before['actual_all22'],before['full_data_and_sequences'])
        fields(supervision,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=HEAD,github_run_id=str(RUN),
            github_run_attempt='1',worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,
            process_group_empty=True,process_tree_empty=True,signals=[],job_budget_seconds=7200,
            work_budget_seconds=5400,recovery_reserve_seconds=1200,artifact_reserve_seconds=600,
            actual_case_credit=0,production_go=False),'REAL_HARD_JOB_BUDGET_AND_COMPLETE_PROCESS_REAP')
        exact(package['gate'],GATES,'ALL_FIVE_FRESH_OWNING_PACKAGE_GATES')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),'ACTUAL_FOCUSED_PACKAGE_IDENTITY')
        fields(backup,dict(status='RESTORED_IDENTICAL'),'ACTUAL_FRESH_BACKUP_DRILL')
        exact(set(backup['checks']),{'restore_errors_only_pg_cron','catalog_explained','data_identical','engine_answer_present','engine_equal'},
            'ALL_FIVE_BACKUP_CHECKS')
        require(all(type(v)is bool and v for v in backup['checks'].values()),'ALL_TYPED_BACKUP_CHECKS_PASS')
        exact(backup['data']['differ'],{},'NO_BACKUP_ROW_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'ALL_BASELINE_ROLES_RESTORED')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,database_owner_acl_and_settings_preserved=True),
            'COMPLETE_BASELINE_RESTORE')
        maps=declared_files(g,financial);exact(maps,proof['receipt']['actual_product_source_maps'],'ALL_ACTUAL_FINANCIAL_SOURCE_MAPS_UNCHANGED')
        union=prepared['retained_ids']|set(ids);exact(len(union),37,'EXACT_CANDIDATE_37_CASE_COVERAGE')
        return dict(status='ROOT_VERIFIED_CURRENT_JOIN_RETAINED35_FRESH_S05_BROWSER2_ALL5',head=HEAD,tree=TREE,
            run_id=RUN,job_id=JOB,artifact_id=ARTIFACT,archive=dict(archive,members=len(names)),originals=pins,
            source_admission={k:v for k,v in prepared.items()if k not in('retained_ids','expected_runtime_retention')},
            retained_Root_head=ROOT_HEAD,retained_Root_receipt=ROOT_PIN,retained_original_run_id=41291621885,
            retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
            actual_Native_cases=0,actual_browser_cases=2,fresh_cases=2,retained_Native_cases=31,retained_S03_browser_cases=4,
            retained_cases=35,retained_cases_are_not_fresh=True,qualified_candidate_Native_coverage=31,
            qualified_candidate_browser_coverage=6,candidate_case_coverage=37,complete37_qualified=True,
            fresh37_one_attempt=False,prior_runs_aggregated=True,source_invariant_reuse=True,
            qualified_financial_sources=financial_pin,actual_product_source_maps=maps,
            actual_reader_product_source_maps=reader_maps,current_reader_graph_verified_before_database=True,
            package_all_five=True,package_gates=package['gate'],actual_used_refusal_raw_full_boundary=census,
            exact_original_foundation_setup=original_foundation,
            permanent_complete_assembly_qualified=False,global_writer_or_permission_or_lock_closure=False,
            Afui_positive_HPP_zero_reimbursement_coverage=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--check-source',action='store_true');parser.add_argument('--archive',type=Path)
    parser.add_argument('--artifact-metadata',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.check_source:
        with GitBytes(args.source,HEAD,TREE)as git:value=source(git)
        print(json.dumps(dict(status='EXACT_FOCUSED_SOURCE_AND_RETAINED35_INVARIANCE_ONLY',
            source_pins=value['source_pins'],retained_ids=len(value['retained_ids']),fresh_planned_ids=len(value['fresh_ids']),actual_case_credit=0)))
    else:
        require(all((args.archive,args.artifact_metadata,args.output)),'CANONICAL_ARCHIVE_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(args.source,args.archive,strict(args.artifact_metadata.read_bytes()))
        with args.output.open('x')as stream:stream.write(json.dumps(value,indent=2)+'\n')
        print(json.dumps({k:value[k]for k in ('status','fresh_cases','retained_cases','candidate_case_coverage','package_all_five')}))
