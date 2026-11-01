"""Read-only actual permanent6 intake; activation identity deliberately pending.

Source-only checks are possible on the prepared tree. Full intake requires
the exact activated head/run/job, canonical artifact and every raw gate.
No product import, SQL, Auth, browser or network operation is supplied here.
"""
from pathlib import Path
from hashlib import file_digest
import argparse,ast,json,re,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,group,full_census,declared_files
from intake_join37 import browser
from intake_s05_focused import browser_assets

HEAD='23e3e77d6dddd48a98d31c35822d637db2cee528'
TREE='0637e2f69fc24cd2a98260210e9c358222ae992b'
RUN=41346386747
JOB=124966984224
PREPARED_HEAD='23e3e77d6dddd48a98d31c35822d637db2cee528'
PREPARED_TREE='0637e2f69fc24cd2a98260210e9c358222ae992b'
BASE='2cb8c9ac85b6111e8bb170de6c2ec5c44f7c798c'
BASE_TREE='5c5111505dafc5a92a79de4d9b52e4d93e37500e'
PARENT_RUN=41333643573
PARENT_JOB=124928771868
PARENT_RECEIPT=dict(bytes=20463,sha256='2d9731cf9cdaed8ed90c0e189e56663a54e3bdd28ba8e24741516c4d1a85d9ba')
NS='scripts/current-final-s03-sku-s05-preparation/'
MAIN='CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2.json'
NATIVE='CP7_PERMANENT_S05_S03_FINANCIAL_NATIVE4.json'
CASE='PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2'
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)

def browser_source_binding(g):
    path=NS+'PERSISTENT_BROWSER_SOURCE.json'
    raw=g.read(path,'92a70c1fbe51208f098e82a27088649add4befd4')
    exact(pin(raw),dict(bytes=2912,sha256='651571e5d8e422d2090fc9b45a8710a35308f42cc4812ce4046a6c9d7e47ceff'),
        'PERMANENT_EXACT_ORIGINAL_BROWSER_INPUT_MANIFEST')
    before=strict(raw);current=g.read(path);after=strict(current)
    exact({k:v for k,v in before.items()if k!='files'},{k:v for k,v in after.items()if k!='files'},
        'PERMANENT_BROWSER_CASE_AND_SOURCE_CONTRACT_UNCHANGED')
    exact(set(before['files']),set(after['files']),'PERMANENT_EXACT_SAME_BROWSER_INPUT_NAMES')
    exact(len(before['files']),19,'PERMANENT_ALL19_BROWSER_INPUTS')
    routed={NS+n for n in('admission.py','component.py','controls.py','fetch_parent37.py','final_gate.py',
        'persistent_financial.py','persistent_source.py','probe.py')}
    require(routed<=set(before['files']),'PERMANENT_EXACT_EIGHT_ROUTED_CALLER_INPUTS')
    text=raw.decode();changes=[]
    for name,old in before['files'].items():
        expected=pin(g.read(name))['sha256']if name in routed else old
        exact(after['files'][name],expected,'PERMANENT_ONLY_EIGHT_CURRENT_CALLER_PIN_ROUTES:'+name)
        g.verify_pin(name,expected)
        if name in routed:
            a=json.dumps(name)+': '+json.dumps(old);b=json.dumps(name)+': '+json.dumps(expected)
            exact(text.count(a),1,'PERMANENT_ONE_BROWSER_INPUT_PIN');text=text.replace(a,b,1);changes.append((a,b))
    exact(text.encode(),current,'PERMANENT_ONLY_COUNTED_BROWSER_MANIFEST_BYTES')
    for a,b in reversed(changes):
        exact(text.count(b),1,'PERMANENT_EXACT_BROWSER_PIN_REVERSE');text=text.replace(b,a,1)
    exact(text.encode(),raw,'PERMANENT_COMPLETE_ORIGINAL_BROWSER_INPUT_MANIFEST_RECOVERED')
    return dict(actual_current_inputs_verified=19,explicit_current_caller_pin_routes=8,
        unchanged_browser_UI_and_fixture_inputs=11,original_manifest_recovered=True,actual_case_credit=0)

def product_source_binding(g):
    prefix='scripts/cp7_current_s03_sku_s05/'
    raw=g.read(prefix+'SOURCE.json');value=strict(raw)
    fields(value,dict(contract='cp7.current-s03-sku-s05.v1',actual_new_Native_cases=0,
        actual_new_browser_cases=0,production_go=False,independent_acceptance=False),
        'PERMANENT_NESTED_PRODUCT_MANIFEST_CONTRACT')
    exact(set(value['files']),{prefix+n for n in('README.md','__init__.py','composition.py')},
        'PERMANENT_EXACT_THREE_NESTED_PRODUCT_SOURCE_PATHS')
    for name,digest in value['files'].items():g.verify_pin(name,digest)
    return dict(actual_source_files=3,source_manifest=pin(raw),actual_case_credit=0)

def parent_receipt_source(g):
    actual=literal(g,NS+'persistent_financial.py','PARENT_RECEIPT')
    exact(actual,PARENT_RECEIPT,'PERMANENT_EXACT_ROOT_ACCEPTED_PARENT_RECEIPT_BINDING')
    if actual is None:return None
    raw=g.read(NS+'JOIN37_ROOT_ACTUAL_INTAKE.json')
    exact(pin(raw),actual,'PERMANENT_EXACT_ORIGINAL_ROOT_ACCEPTED_PARENT_RECEIPT_BYTES')
    value=strict(raw)
    fields(value,dict(status='ROOT_VERIFIED_CURRENT_JOIN_RETAINED35_FRESH_S05_BROWSER2_ALL5',
        head=BASE,tree=BASE_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,complete37_qualified=True,
        package_all_five=True,fresh_cases=2,retained_cases=35,retained_cases_are_not_fresh=True,
        candidate_case_coverage=37,failed_run_relabelled_PASS=False,production_go=False,
        independent_acceptance=False),'PERMANENT_ACTUAL_PARENT_QUALIFICATION_BEFORE_OWN_RUNTIME')
    return actual

def source(g):
    declaration=strict(g.read(NS+'PREPARATION.json'))
    fields(declaration,dict(base_head=BASE,actual_new_Native_cases=0,production_go=False,
        independent_acceptance=False),'PERMANENT_SOURCE_PREPARATION_NOT_CASE_CREDIT')
    exact(g.git('rev-parse',BASE+'^{tree}').decode().strip(),BASE_TREE,'EXACT_CORRECTED_S05_SOURCE_PARENT_TREE')
    base=g.entries(BASE);exact(len(base),14107,'PERMANENT_UNCHANGED_SOURCE_RELEASE_FINANCIAL_BASE14107')
    for name,value in base.items():exact(g.tree.get(name),value,'PERMANENT_BASE_BLOB_AND_MODE:'+name)
    allowed=set(declaration['files'])|{NS+'PREPARATION.json'}
    require(all(name.startswith(('scripts/cp7_current_s03_sku_s05/',NS))
        or name=='.github/workflows/cp7-final-s03-sku-s05.yml'for name in allowed),'PERMANENT_ONLY_OWN_SOURCE_SCOPE')
    exact(set(g.tree)-set(base),allowed,'PERMANENT_EXACT_CLOSED_ADDITIVE_SOURCE')
    for name,value in declaration['files'].items():g.verify_pin(name,value)
    nested_product=product_source_binding(g)
    current_browser=browser_source_binding(g)
    for name,value in dict(PARENT_HEAD=BASE,PARENT_TREE=BASE_TREE,PARENT_RUN=PARENT_RUN,PARENT_JOB=PARENT_JOB).items():
        exact(literal(g,NS+'persistent_financial.py',name),value,'PERMANENT_EXACT_ACTUAL_PARENT_BINDING:'+name)
    parent_receipt=parent_receipt_source(g)
    exact(len(allowed),57 if parent_receipt is not None else 56,'EXACT_PERMANENT_OWN_PATHS_AND_OPTIONAL_ACTUAL_PARENT_RECEIPT')
    fields(declaration,dict(owning_job_and_real_WIB_guard_minutes=360,
        expected_parent_qualification='ROOT_VERIFIED_CURRENT_JOIN_RETAINED35_FRESH_S05_BROWSER2_ALL5',
        retained_parent_case_credit_is_not_fresh=True),'HONEST_PARENT_REUSE_AND_ACTUAL_JOB_BUDGET')
    originals=list(literal(g,NS+'persistent_financial.py','ORIGINAL_IDS'))
    all_financial=list(literal(g,'scripts/current-s03-sku-native14-binding/retained-s03-f42e/cases.py','IDS'))
    require(len(originals)==4 and set(originals)<=set(all_financial),'PERMANENT_EXACT_FOUR_ORIGINAL_FINANCIAL_CALLBACKS')
    native=['PERMANENT_S05_'+name for name in originals]
    text=g.read(NS+'persistent_browser.mjs').decode()
    match=re.search(r'export const IDS\s*=\s*(\[.*?\])',text,re.S)
    require(match is not None,'PERMANENT_EXPLICIT_BROWSER_IDS_REQUIRED')
    brows=ast.literal_eval(match.group(1));exact(len(brows),2,'PERMANENT_EXACT_TWO_BROWSER_IDS')
    exact(len(set(native+brows)),6,'PERMANENT_EXACT_SIX_UNIQUE_SOURCE_IDS')
    return dict(source_pins=len(declaration['files']),own_paths=len(allowed),unchanged_base=14107,
        expected_parent_head=BASE,expected_parent_run=PARENT_RUN,expected_parent_job=PARENT_JOB,
        parent_root_acceptance_pending=parent_receipt is None,parent_root_receipt=parent_receipt,
        retained_parent_case_credit_is_not_fresh=True,
        native_ids=native,browser_ids=brows,current_browser_source_binding=current_browser,
        nested_product_source_binding=nested_product,
        source_manifest=pin(g.read(NS+'PREPARATION.json')),actual_case_credit=0)


def supervision(value):
    require(HEAD is not None and RUN is not None,'PERMANENT_SUPERVISION_ACTUAL_IDENTITY_PENDING')
    fields(value,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=HEAD,
        github_run_id=str(RUN),github_run_attempt='1',worker_exit=0,signals=[],
        deadline_reached=False,external_signal=None,orphaned_child=False,
        process_group_empty=True,process_tree_empty=True,job_budget_seconds=21600,
        work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600,
        actual_case_credit=0,production_go=False),'PERMANENT_ACTUAL_CURRENT_WORKER_COMPLETE_AND_REAPED')
    return dict(status='EXACT_PERMANENT_SUPERVISION_REQUIRED_NOT_BUSINESS_ACCEPTANCE',
        run_id=RUN,worker_completed_before_database_stop=True,actual_case_credit=0)


def intake(root,path,metadata):
    require(all(value is not None for value in(HEAD,TREE,RUN,JOB)),'PERMANENT_ACTIVATED_EXACT_RUN_INTAKE_NOT_YET_PINNED')
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,
        conclusion='success',expired=False),'PERMANENT_EXACT_TERMINAL_API_METADATA')
    expected=metadata['archive']
    require(type(expected['bytes'])is int and expected['bytes']>0,'PERMANENT_POSITIVE_CANONICAL_ARCHIVE_BYTES')
    require(type(expected['sha256'])is str and re.fullmatch('[0-9a-f]{64}',expected['sha256'])is not None,
        'PERMANENT_CANONICAL_ARCHIVE_SHA256')
    path=Path(path);exact(path.stat().st_size,expected['bytes'],'PERMANENT_CANONICAL_ARCHIVE_SIZE')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),expected['sha256'],'PERMANENT_CANONICAL_ARCHIVE_DIGEST')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(set(names)),len(names),'PERMANENT_NO_DUPLICATE_ARCHIVE_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'PERMANENT_CANONICAL_ARCHIVE_CRC')
        admitted=source(g);pins={}
        def original(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=original(MAIN);package=original('T3_PACKAGE_INSTALL.json');backup=original('T3_BACKUP_RESTORE_DRILL.json')
        supervised=supervision(original('PERMANENT_RUNTIME_SUPERVISION.json'))
        fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[CASE],required_case_ids_pass=True,
            actual_Native_cases=4,actual_browser_cases=2,actual_business_cases=6,actual_Auth_HTTP_cases=0,
            actual_two_session_races=0,retained_join37_fresh_case_credit=0,used_guard_refused_before_DDL=True,
            baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
            baseline_advisors_equal=True,advisor_gate=True,production_go=False,independent_acceptance=False),
            'PERMANENT_CURRENT_FRESH6_AND_FULL_RESTORE')
        exact(set(main['committed']),{CASE},'PERMANENT_ONE_ACTUAL_COMPONENT')
        part=main['committed'][CASE]
        fields(part,dict(status='PASS',business_counts={'PASS':6},actual_Native_cases=4,actual_browser_cases=2,
            retained_join37_fresh_case_credit=0,permanent_reader_remains_installed=True,
            global_writer_or_permission_or_lock_closure=False,Afui_positive_HPP_zero_reimbursement_coverage=False),
            'PERMANENT_COMPONENT_NO_UNPROVEN_CREDIT')
        ids=admitted['native_ids'];browser_ids=admitted['browser_ids']
        exact(set(part['business_cases']),set(ids+browser_ids),'PERMANENT_SIX_ACTUAL_CASE_IDENTITIES')
        for row in part['business_cases'].values():fields(row,dict(status='PASS'),'PERMANENT_ACTUAL_CASE')
        first=part['fresh_permanent_financial4'];fields(first,dict(status='PASS',actual_Native_cases=4),'PERMANENT_NATIVE4_COMPONENT')
        native=original(NATIVE);exact(native,first['native'],'PERMANENT_RAW_NATIVE4_EQUALS_EMBEDDED');group(native,ids)
        for row in native['cases'].values():
            read=row['permanent_S05_read']
            fields(read,dict(status='PASS',reader_remained_installed=True,business_DML=False,all_fields_retained=True),
                'PERMANENT_EVERY_ACTUAL_PUBLIC_READER')
            exact(read['before'],read['after'],'PERMANENT_EVERY_READER_RAW_ZERO_EFFECT')
            full_census(read['before']['actual_all22'],read['before']['full_data_and_sequences'])
        witness=part['separate_committed_Native_use']
        fields(witness,dict(status='NATIVE_BUSINESS_COMMITTED',Native_case_credit=0,
            used_inverse_guard_refused_before_DDL=True,reader_remains_installed=True),'PERMANENT_REAL_COMMITTED_NATIVE_USE')
        exact(witness['before'],witness['after'],'PERMANENT_USED_REFUSAL_RAW_ZERO_EFFECT')
        used=full_census(witness['before']['actual_all22'],witness['before']['full_data_and_sequences'])
        browser(part['fresh_permanent_browser2']['browser'],browser_ids,g,NS+'persistent_browser.mjs','PERMANENT_REAL_AUTH_BROWSER2')
        raw_browser_assets=browser_assets(z,part['fresh_permanent_browser2'],g,
            source_path=NS+'PERSISTENT_BROWSER_SOURCE.json')
        exact(package['gate'],GATES,'PERMANENT_ALL_FIVE_PACKAGE_GATES')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
            'PERMANENT_EXACT_CURRENT_OWNING_RUN')
        fields(backup,dict(status='RESTORED_IDENTICAL'),'PERMANENT_ACTUAL_BACKUP_DRILL')
        require(bool(backup['checks'])and all(type(x)is bool and x for x in backup['checks'].values()),
            'PERMANENT_ALL_TYPED_BACKUP_CHECKS')
        exact(backup['data']['differ'],{},'PERMANENT_BACKUP_NO_ROW_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'PERMANENT_EXACT_ROLE_RESTORE')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'PERMANENT_OUTER_RESTORE')
        graph=main['source_declaration']['current_installation'];maps=declared_files(g,graph)
        parent_raw=g.read(NS+'JOIN37_ROOT_ACTUAL_INTAKE.json');parent=strict(parent_raw)
        g.verify_pin(NS+'JOIN37_ROOT_ACTUAL_INTAKE.json',literal(g,NS+'persistent_financial.py','PARENT_RECEIPT'))
        fields(parent,dict(status='ROOT_VERIFIED_CURRENT_JOIN_RETAINED35_FRESH_S05_BROWSER2_ALL5',
            head=BASE,tree=BASE_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,complete37_qualified=True,
            package_all_five=True,actual_Native_cases=0,actual_browser_cases=2,fresh_cases=2,
            retained_Native_cases=31,retained_S03_browser_cases=4,retained_cases=35,
            retained_cases_are_not_fresh=True,qualified_candidate_Native_coverage=31,
            qualified_candidate_browser_coverage=6,candidate_case_coverage=37,fresh37_one_attempt=False,
            prior_runs_aggregated=True,source_invariant_reuse=True,retained_original_run_conclusion='failure',
            failed_run_relabelled_PASS=False,production_go=False,independent_acceptance=False),
            'PERMANENT_EXACT_QUALIFIED_PARENT_RETAINED35_PLUS_FRESH2')
        exact(pin(json.dumps(graph['financial_parent'],sort_keys=True,separators=(',',':')).encode()),
            parent['qualified_financial_sources'],'PERMANENT_WHOLE_FINANCIAL_PARENT_EQUALS_ROOT_QUALIFIED_SOURCE')
        return dict(status='ROOT_VERIFIED_PERMANENT_S05_NATIVE4_BROWSER2_ALL5',head=HEAD,tree=TREE,
            run_id=RUN,job_id=JOB,artifact_id=metadata['artifact_id'],archive=dict(expected,members=len(names)),originals=pins,
            source_admission=admitted,actual_product_source_maps=maps,
            qualified_complete_sources=pin(json.dumps(graph,sort_keys=True,separators=(',',':')).encode()),
            qualified_parent37=dict(head=parent['head'],run_id=parent['run_id'],root_intake=pin(parent_raw)),
            actual_Native_cases=4,actual_browser_cases=2,complete6_qualified=True,package_all_five=True,
            actual_current_browser_raw_assets=raw_browser_assets,
            fresh6_one_attempt=True,parent_qualification_uses_retained35=True,
            runtime_supervision=supervised,
            prior_runs_aggregated=False,retained_join37_fresh_case_credit=0,reader_remains_installed=True,
            actual_used_refusal_raw_boundary=used,global_writer_or_permission_or_lock_closure=False,
            Afui_positive_HPP_zero_reimbursement_coverage=False,D1_E_qualified=False,
            production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--check-source',action='store_true')
    p.add_argument('--archive',type=Path);p.add_argument('--artifact-metadata',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check_source:
        with GitBytes(a.source,HEAD or PREPARED_HEAD,TREE or PREPARED_TREE)as g:value=source(g)
        print(json.dumps(dict(status='EXACT_PERMANENT_SOURCE_AND_SIX_IDS_ONLY',source=value,actual_Native_cases=0)))
    else:
        require(all((a.archive,a.artifact_metadata,a.output)),'PERMANENT_CANONICAL_ARCHIVE_API_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(a.source,a.archive,strict(a.artifact_metadata.read_bytes()))
        a.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(status=value['status'],complete6_qualified=True)))
