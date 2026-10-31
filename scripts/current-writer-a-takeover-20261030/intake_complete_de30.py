"""Read-only D1/E Native30 intake, closed until its actual owning run exists.

Prepared-source admission grants no case credit. Activation must replace the
prepared base with the accepted permanent6 parent and bind its exact receipt.
"""
from pathlib import Path
from hashlib import file_digest,sha256
from collections import defaultdict
from types import ModuleType
import argparse,ast,json,re,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,group,full_census,declared_files

HEAD=None
TREE=None
RUN=None
JOB=None
PARENT_HEAD=None
PARENT_TREE=None
PREPARED_HEAD='674a700096eab400e9b75700e4a2704f799d69b8'
PREPARED_TREE='02e0e9bf7254054f37ca5d08c706d4e4cc4b603a'
PREPARED_BASE='a6cc41ec58e4d0d0c8191f1b1fe5c27309fff559'
PREPARED_BASE_TREE='48c5e13acdb5d8fb9529f2ce1661e4fee09e2a5b'
NS='scripts/current-complete-de-integration-preparation/'
PRODUCT='scripts/cp7_complete_credit_de/'
BUSINESS='scripts/cp7_credit_correction_de/'
NATIVE_HEAD='928246e5f62637c7c6457e57d73d0699196e3408'
NATIVE_TREE='581303d5f0df8a6ae40f6d7ec0fab7c06678ed9a'
CASE='CURRENT_COMPLETE_D1_E_NATIVE30'
MAIN='CP7_CURRENT_COMPLETE_D1_E_NATIVE30.json'
RAW='CP7_CURRENT_COMPLETE_D1_E_NATIVE30_CASES.json'
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)


def source(g):
    base_head=PARENT_HEAD or PREPARED_BASE
    base_tree=PARENT_TREE or PREPARED_BASE_TREE
    declaration=strict(g.read(NS+'SOURCE.json'))
    fields(declaration,dict(classification='CLOSED_D1_E_ON_COMPLETE_SOURCE_PREPARATION_NOT_QUALIFICATION',
        base_head=base_head,base_tree=base_tree,actual_Native_cases=0,production_go=False,
        independent_acceptance=False),'DE30_SOURCE_PREPARATION_IS_NOT_RUNTIME')
    exact(g.git('rev-parse',base_head+'^{tree}').decode().strip(),base_tree,'DE30_EXACT_PARENT_TREE')
    base=g.entries(base_head)
    for name,value in base.items():exact(g.tree.get(name),value,'DE30_UNCHANGED_PARENT_BLOB_AND_MODE:'+name)
    allowed=set(declaration['files'])|{NS+'SOURCE.json'}
    require(all(name.startswith((NS,PRODUCT,BUSINESS))for name in allowed),'DE30_ONLY_THREE_OWN_NAMESPACES')
    exact(set(g.tree)-set(base),allowed,'DE30_CLOSED_ADDITIVE_SOURCE')
    for name,value in declaration['files'].items():g.verify_pin(name,value)
    if PARENT_HEAD is None:
        exact(len(base),14092,'DE30_PREPARED_PARENT14092');exact(len(allowed),61,'DE30_PREPARED_OWN61')
        exact(literal(g,NS+'admission.py','PARENT_HEAD'),None,'DE30_PREPARED_PARENT_GATE_CLOSED')
        exact(literal(g,NS+'admission.py','PARENT_RECEIPT'),None,'DE30_PREPARED_RECEIPT_GATE_CLOSED')
    product=strict(g.read(PRODUCT+'SOURCE.json'))
    fields(product,dict(contract='cp7.current-complete-credit-de.v1',actual_Native_cases=0,
        D_complete=False,E_complete=False,global_eight_hook_runtime_opened=False,
        production_go=False,independent_acceptance=False),'DE30_PRODUCT_SOURCE_NOT_COMPLETE_SCOPE_CREDIT')
    for name,value in product['files'].items():g.verify_pin(name,value)
    original=strict(g.read(NS+'NATIVE_CALLBACK_ORIGIN.json'))
    fields(original,dict(source_head=NATIVE_HEAD,source_tree=NATIVE_TREE,source_callbacks_changed=0,
        actual_Native_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False),
        'DE30_UNCHANGED_ORIGINAL_NATIVE_CALLBACK_SOURCES')
    exact(g.git('rev-parse',NATIVE_HEAD+'^{tree}').decode().strip(),NATIVE_TREE,'DE30_EXACT_CALLBACK_ORIGIN_TREE')
    exact(set(original['files']),{BUSINESS+name for name in('cases.py','e_cases.py','native_fixture.py')},
        'DE30_EXACT_THREE_BUSINESS_SOURCES')
    for name,value in original['files'].items():
        raw=g.verify_pin(name,value);exact(raw,g.read(name,NATIVE_HEAD),'DE30_ORIGINAL_CALLBACK_BYTES:'+name)
    d1=list(literal(g,BUSINESS+'cases.py','IDS'));e=list(literal(g,BUSINESS+'e_cases.py','IDS'))
    exact([len(d1),len(e),len(set(d1+e))],[13,17,30],'DE30_ORIGINAL_13_PLUS17_UNIQUE_IDS')
    exact(d1,original['D1_case_ids'],'DE30_EXACT_D1_IDS');exact(e,original['E_case_ids'],'DE30_EXACT_E_IDS')
    fixture=literal(g,BUSINESS+'native_fixture.py','SOURCES');exact(len(fixture),4,'DE30_FOUR_FROZEN_FIXTURE_INPUTS')
    for name,digest in fixture.values():g.verify_pin(name,digest)
    recorded=strict(g.read(PRODUCT+'RECORDED_NATIVE_CAPTURES.json'))['functions']
    exact(len(recorded),32,'DE30_RECORDED_PREDECESSOR32')
    require(all(type(row)is list and len(row)==19 for row in recorded.values()),'DE30_RECORDED_FULL19_ROWS')
    _,_,queries=raw_metadata_sources(g)
    return dict(source_pins=len(declaration['files']),own_paths=len(allowed),unchanged_base=len(base),
        D1_ids=d1,E_ids=e,source_manifest=pin(g.read(NS+'SOURCE.json')),
        unchanged_business_source_files=3,frozen_fixture_inputs=4,recorded_predecessor_functions=32,
        unchanged_global_metadata_source_files=4,unchanged_raw_metadata_queries=len(queries),
        actual_case_credit=0,parent_qualification_pending=PARENT_HEAD is None)


def raw_metadata_sources(g):
    """Compile only immutable metadata validators and the query dictionary."""
    prefix=NS+'retained-global-census/'
    origin=strict(g.read(prefix+'ORIGIN.json'))
    fields(origin,dict(head='3d7066b852176d9f343ec831d2f63aee6665579b',
        pure_selected_functions=['replace_exact','capture'],financial_SQL_or_business_callbacks_changed=False,
        metadata_SQL_queries_changed=False,actual_Native_cases=0,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False),'DE30_EXACT_RECORDED_RAW_METADATA_SOURCES')
    exact(set(origin['files']),{'capture.py','census.py','multiset.py','derive.py.txt'},'DE30_FOUR_RAW_METADATA_ORIGINALS')
    for name,value in origin['files'].items():
        raw=g.verify_pin(prefix+name,{k:value[k]for k in('bytes','sha256')})
        exact(raw,g.read(value['path'],origin['head']),'DE30_RETAINED_RAW_METADATA_ORIGINAL:'+name)
    qenv={};nodes=[]
    for node in ast.parse(g.read(prefix+'capture.py')).body:
        if not isinstance(node,ast.Assign):continue
        target=node.targets[0]
        name=target.id if isinstance(target,ast.Name)else(
            target.value.id if isinstance(target,ast.Subscript)and isinstance(target.value,ast.Name)else None)
        if name in('SCOPE','RELATION','RELATION_SCOPE','FUNCTION_SCOPE','QUERIES'):nodes.append(node)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'root_DE30_pure_readonly_query_dictionary','exec'),qenv)
    queries=qenv['QUERIES'];exact(len(queries),19,'DE30_NINETEEN_ORIGINAL_RAW_METADATA_QUERIES')
    cenv=dict(defaultdict=defaultdict,sha256=sha256,json=json);nodes=[]
    for node in ast.parse(g.read(prefix+'census.py')).body:
        if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id in('ALL22','WIDTHS')for t in node.targets):nodes.append(node)
        elif isinstance(node,ast.FunctionDef)and node.name in('require','canonical','digest','validate_catalog'):nodes.append(node)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'root_DE30_pure_full22_metadata_validator','exec'),cenv)
    codec=ModuleType('root_DE30_pure_recorded_lossless_codec');codec.__file__='recorded_3d706_multiset.py'
    exec(compile(g.read(prefix+'multiset.py'),codec.__file__,'exec'),codec.__dict__)
    return cenv,codec,queries


def raw_metadata_observation(g,original,raw_pins,value,directory):
    fields(value,dict(classification='READONLY_CURRENT_DE_RAW_DEPENDENCIES_NOT_WRITER_CLOSURE',actual_Native_cases=0,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False),
        'DE30_RAW_DEPENDENCY_OBSERVATION_NOT_GLOBAL_ACCEPTANCE')
    expected_name=directory+'/CALLER_RAW_BOUNDARY_OBSERVATION.json';reference=value['observation']
    exact(reference['name'],expected_name,'DE30_EXACT_RAW_METADATA_BOUNDARY_MEMBER')
    observed=original(expected_name)
    exact({k:reference[k]for k in('bytes','sha256')},raw_pins[expected_name],
        'DE30_EXACT_CANONICAL_RAW_METADATA_BOUNDARY_REFERENCE')
    fields(observed,dict(classification=value['classification'],permanent_parent_head=PARENT_HEAD,
        transaction_writes=False,observed_catalog_includes_qualification_overlays=True,
        global_hook_installation_or_explicit_LOCK_statement=False,provider_or_system_call_closure_proven=False,
        actual_Native_cases=0,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False),'DE30_RAW_METADATA_SCOPE_AND_AUTHORITY')
    exact(observed['status'],value['status'],'DE30_RAW_METADATA_STATUS_EQUALS_CANONICAL_OBSERVATION')
    exact(observed['source'],value['source'],'DE30_RAW_METADATA_SOURCE_EQUALS_CANONICAL_OBSERVATION')
    cenv,codec,queries=raw_metadata_sources(g)
    fields(observed['source'],dict(origin_head='3d7066b852176d9f343ec831d2f63aee6665579b',
        byte_exact_original_files=4,selected_original_pure_functions=2,unchanged_SQL_queries=19,
        query_sha256={k:sha256(v.encode()).hexdigest()for k,v in queries.items()},
        prior_runtime_loader_or_admission_used=False,prior_runtime_guards_modified=False,
        actual_Native_cases=0,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False),'DE30_UNCHANGED_RAW_QUERY_SOURCE_AND_OPEN_CLOSURE')
    if observed['status']=='RAW_READONLY_METADATA_UNAVAILABLE':
        fields(observed,dict(error_text_or_connection_details_retained=False),'DE30_UNAVAILABLE_RAW_METADATA')
        return dict(status=observed['status'],actual_Native_cases=0,global_qualified=False)
    exact(observed['status'],'RAW_READONLY_METADATA_CAPTURED','DE30_RAW_METADATA_CAPTURE_STATUS')
    fields(observed,dict(all22_ALL_rows_ALL_sequences_equal=True,all19_queries_captured=True),
        'DE30_EACH_RAW_METADATA_READONLY_FULL_BOUNDARY')
    before=observed['before'];exact(before,observed['after'],'DE30_RAW_METADATA_FULL_TYPED_NO_EFFECT')
    cenv['validate_catalog'](before['actual_all22'])
    census=full_census(before['actual_all22'],before['full_data_and_sequences'])
    supplement=observed['supplement'];ref=supplement['raw_capture_reference'];codec.reference(ref)
    raw_name=directory+'/'+ref['name'];exact(observed['raw_original'],raw_name,'DE30_EXACT_RAW_PAIR_MEMBER')
    raw=original(raw_name)
    exact(raw_pins[raw_name],{k:ref[k]for k in('bytes','sha256')},'DE30_RAW_PAIR_ORIGINAL_REFERENCE')
    codec.validate_raw(raw,queries,before['actual_all22'])
    fields(raw,dict(status='ALL_QUERIES_CAPTURED_BEFORE_VALIDATION',captured_groups=list(queries),query_failure=None),
        'DE30_EVERY_ORIGINAL_RAW_QUERY_COMPLETED')
    exact(codec.digest(raw),ref['raw_capture_sha256'],'DE30_RAW_PAIR_PAYLOAD_DIGEST')
    exact(cenv['digest'](before['actual_all22']),ref['catalogue_sha256'],'DE30_RAW_PAIR_CATALOGUE_DIGEST')
    fields(supplement,dict(contract='cp7.global.actual-writer-census.supplement.multiset.v2',
        catalogue_sha256=ref['catalogue_sha256'],identity=raw['identity'],transaction_writes=False,
        caller_full_catalogue_data_sequence_bracket_required=True,caller_outer_restoration_required=True,
        runtime_entry=None,actual_Native_credit=0,production_go=False,independent_acceptance=False),
        'DE30_RAW_SUPPLEMENT_REMAINS_METADATA_ONLY')
    exact(supplement['groups'],{name:codec.encode_group(name,rows)for name,rows in raw['raw_groups'].items()},
        'DE30_LOSSLESS_RAW_PAIRS_EQUAL_EVERY_SUPPLEMENT_GROUP')
    require(type(observed['repeatable_read_snapshot'])is str and bool(observed['repeatable_read_snapshot']),
        'DE30_EXPLICIT_READONLY_REPEATABLE_SNAPSHOT')
    return dict(status=observed['status'],raw_original=raw_name,raw_boundary=census,query_count=19,
        raw_pairs_and_catalogue_bound=True,repeated_dependency_identities_preserved=True,
        actual_Native_cases=0,global_qualified=False)


def metadata_observation(g,value):
    """Inspect availability and source identity; metadata never grants closure."""
    fields(value,dict(classification='READONLY_CURRENT_DE_SYSTEM_AND_PRIMARY_SCHEDULER_METADATA_NOT_CLOSURE',
        permanent_parent_head=PARENT_HEAD,separate_snapshots_not_atomic=True,
        qualification_actors_and_overlays_may_be_observed=True,actual_Native_case_credit=0,
        writer_closure=False,permission_closure=False,lockset_approved=False,
        production_go=False,independent_acceptance=False),'DE30_READONLY_METADATA_NO_CLOSURE')
    prefix='scripts/current-final-s03-sku-s05-preparation/metadata/'
    manifest=strict(g.read(prefix+'SOURCE.json'))
    fields(value['source'],dict(commit='a83f87d76abbd3d94b5e75a50391d1d202b837c9',
        prefix='scripts/current-global-system-cron-profile-preparation/',
        manifest=pin(g.read(prefix+'SOURCE.json')),byte_exact_original_files=len(manifest['files'])+1,
        query_count=27),'DE30_EXACT_INHERITED_METADATA_SOURCE')
    queries=strict(g.read(prefix+'QUERIES.json'))['queries'];exact(len(queries),27,'DE30_ALL_METADATA_QUERY_IDENTITIES')
    exact(set(value['snapshots']),{'candidate','primary_scheduler'},'DE30_TWO_SEPARATE_METADATA_SNAPSHOTS')
    captured={}
    for kind,database in(('candidate','cp6_rollback'),('primary_scheduler','postgres')):
        row=value['snapshots'][kind]
        if row.get('status')=='READONLY_METADATA_UNAVAILABLE':
            fields(row,dict(error_text_or_connection_details_retained=False,writer_closure=False),
                'DE30_UNAVAILABLE_METADATA_IS_NOT_CLOSURE')
            captured[kind]=False;continue
        fields(row,dict(classification='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE',
            database=database,search_path='pg_catalog',Native_cases=0,
            primary_scheduler_database=kind=='primary_scheduler',separate_database_snapshots_are_not_atomic_writer_closure=True,
            writer_closure=False,permission_closure=False,lockset_approved=False,
            production_go=False,independent_acceptance=False),'DE30_ACTUAL_READONLY_METADATA_CONTRACT')
        require(row['current_role']in('postgres','supabase_admin')and row['session_role']in('postgres','supabase_admin'),
            'DE30_ACTUAL_METADATA_ADMINISTRATIVE_CONTEXT')
        exact(set(row['groups']),set(queries),'DE30_ALL27_METADATA_GROUPS')
        exact(set(row['group_counts']),set(queries),'DE30_ALL27_TYPED_METADATA_COUNTS')
        for name,item in row['groups'].items():
            require(type(item['rows'])is list,'DE30_METADATA_TYPED_ROWS:'+name)
            exact(row['group_counts'][name],len(item['rows']),'DE30_METADATA_ACTUAL_COUNT:'+name)
            require(item['status']=='CAPTURED'or(name=='cron_jobs'and item['status']=='RELATION_ABSENT'and not item['rows']),
                'DE30_METADATA_GROUP_CAPTURE_OR_EXPLICIT_ABSENCE:'+name)
        captured[kind]=True
    exact(value['all_metadata_captured'],all(captured.values()),'DE30_METADATA_AVAILABILITY_IS_NOT_ACCEPTANCE')
    return dict(captured=captured,query_count=27,separate_snapshots_not_atomic=True,
        writer_closure=False,permission_closure=False,lockset_approved=False,actual_Native_case_credit=0)


def intake(root,path,metadata):
    require(all(value is not None for value in(HEAD,TREE,RUN,JOB,PARENT_HEAD,PARENT_TREE)),
        'DE30_ACTUAL_QUALIFIED_PARENT_AND_OWNING_RUN_NOT_YET_PINNED')
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,
        conclusion='success',expired=False),'DE30_EXACT_TERMINAL_OWNING_API_METADATA')
    expected=metadata['archive']
    require(type(expected['bytes'])is int and expected['bytes']>0,'DE30_POSITIVE_CANONICAL_ARCHIVE_SIZE')
    require(type(expected['sha256'])is str and re.fullmatch('[0-9a-f]{64}',expected['sha256'])is not None,
        'DE30_CANONICAL_ARCHIVE_SHA256')
    path=Path(path);exact(path.stat().st_size,expected['bytes'],'DE30_EXACT_CANONICAL_ARCHIVE_SIZE')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),expected['sha256'],'DE30_EXACT_ARCHIVE_DIGEST')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(set(names)),len(names),'DE30_NO_DUPLICATE_ARCHIVE_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'DE30_COMPLETE_CANONICAL_ARCHIVE_CRC')
        admitted=source(g);pins={}
        def original(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        parent_raw=g.read(NS+'PERMANENT_PARENT_ROOT_ACTUAL_INTAKE.json');parent=strict(parent_raw)
        exact(literal(g,NS+'admission.py','PARENT_HEAD'),PARENT_HEAD,'DE30_EXACT_PARENT_ADMISSION_HEAD')
        exact(literal(g,NS+'admission.py','PARENT_RECEIPT'),pin(parent_raw),'DE30_EXACT_PARENT_RECEIPT_BYTES')
        fields(parent,dict(status='ROOT_VERIFIED_PERMANENT_S05_NATIVE4_BROWSER2_ALL5',head=PARENT_HEAD,
            tree=PARENT_TREE,complete6_qualified=True,actual_Native_cases=4,actual_browser_cases=2,
            retained_join37_fresh_case_credit=0,package_all_five=True,prior_runs_aggregated=False,
            production_go=False,independent_acceptance=False),'DE30_ACTUAL_QUALIFIED_PERMANENT_PARENT')
        main=original(MAIN);package=original('T3_PACKAGE_INSTALL.json');backup=original('T3_BACKUP_RESTORE_DRILL.json')
        fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[CASE],required_case_ids_pass=True,
            actual_Native_cases=30,actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
            actual_business_cases=30,retained_permanent6_fresh_case_credit=0,real_Auth_HTTP_qualified=False,
            real_Auth_browser_claim=False,used_guard_refused_before_DDL=True,
            baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
            baseline_advisors_equal=True,advisor_gate=True,production_go=False,independent_acceptance=False),
            'DE30_FRESH_ORIGINAL_NATIVE30_AND_OUTER_RESTORATION')
        exact(set(main['committed']),{CASE},'DE30_ONE_CURRENT_OWNING_COMPONENT')
        part=main['committed'][CASE]
        fields(part,dict(status='PASS',business_counts={'PASS':30},actual_Native_cases=30,actual_D1_cases=13,
            actual_E_cases=17,actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
            real_Auth=False,retained_permanent6_fresh_case_credit=0,reader_remains_installed=True,
            original_business_callback_changes=0,used_guard_refused_before_DDL=True,D_complete=False,E_complete=False,
            global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False),
            'DE30_EXACT_BUSINESS_SCOPE_NO_GLOBAL_OR_PARENT_CREDIT')
        raw=original(RAW);exact(raw,part['native'],'DE30_RAW_NATIVE_GROUP_EQUALS_EMBEDDED')
        group(raw,admitted['D1_ids']+admitted['E_ids'])
        require(not raw.get('business_day_retried')and not raw.get('business_day_first_attempt'),
            'DE30_UNCHANGED_SINGLE_REAL_BUSINESS_DAY_ATTEMPT')
        require(all(not row.get('business_day_rollover')for row in raw['cases'].values()),'DE30_NO_CASE_ROLLOVER')
        witness=part['separate_committed_E_witness']
        fields(witness,dict(status='NATIVE_E_CORRECTION_COMMITTED',E_Native_case_credit=0,real_Auth=False,
            actual_used_inverse_error='COMPLETE_CREDIT_DE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE',
            same_original_money_event_and_journal_preserved_by_unchanged_E_post=True,
            original_source_sale_and_payment_immutable=True,physical_HPP_cash_and_cost_GL_unchanged=True),
            'DE30_REAL_SEPARATE_COMMITTED_E_USE_WITHOUT_NEW_MONEY')
        exact(witness['before'],witness['after'],'DE30_RAW_USED_REFUSAL_ZERO_EFFECT')
        used=full_census(witness['before']['actual_all22'],witness['before']['full_data_and_sequences'])
        fields(witness['source_derivation'],dict(selected_function_count=2,counted_changes=1,
            complete_original_function_bytes_recovered=True,raw_observation_retention_only=True,
            Native_case_credit=0,actual_SQL_executed=0),'DE30_ORIGINAL_COMMITTED_WITNESS_DERIVATION')
        system_metadata={name:metadata_observation(g,part[key])for name,key in(
            ('before_native30','read_only_system_metadata_before_native30'),
            ('after_native30_and_committed_use','read_only_system_metadata_after_native30_and_committed_use'))}
        raw_metadata={name:raw_metadata_observation(g,original,pins,part[key],directory)for name,key,directory in(
            ('before_native30','raw_global_metadata_before_native30','DE_GLOBAL_BEFORE_NATIVE30'),
            ('after_committed_E_use','raw_global_metadata_after_committed_E_use','DE_GLOBAL_AFTER_COMMITTED_E_USE'))}
        exact(package['gate'],GATES,'DE30_ALL_FIVE_PACKAGE_GATES')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
            'DE30_CURRENT_OWNING_PACKAGE_RUN')
        fields(backup,dict(status='RESTORED_IDENTICAL'),'DE30_ACTUAL_BACKUP_RESTORE_DRILL')
        require(bool(backup['checks'])and all(type(x)is bool and x for x in backup['checks'].values()),
            'DE30_ALL_TYPED_BACKUP_CHECKS')
        exact(backup['data']['differ'],{},'DE30_BACKUP_NO_ROW_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'DE30_BASELINE_ROLES_RESTORED')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'DE30_COMPLETE_OUTER_RESTORE_RECEIPT')
        graph=main['source_declaration']['current_installation'];maps=declared_files(g,graph)
        complete=graph['predecessor']['predecessor']['predecessor']
        complete_pin=pin(json.dumps(complete,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
        exact(complete_pin,parent['qualified_complete_sources'],'DE30_ENTIRE_ACTUAL_PARENT_SOURCE_GRAPH')
        exact(main['source_declaration']['qualified_complete_sources'],complete_pin,'DE30_ADMITTED_PARENT_SOURCE_PIN')
        return dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_D1_E_NATIVE30_ALL5',head=HEAD,tree=TREE,
            run_id=RUN,job_id=JOB,artifact_id=metadata['artifact_id'],archive=dict(expected,members=len(names)),originals=pins,
            source_admission=admitted,actual_product_source_maps=maps,
            qualified_complete_DE_sources=pin(json.dumps(graph,sort_keys=True,separators=(',',':'),allow_nan=False).encode()),
            qualified_permanent6=dict(head=PARENT_HEAD,tree=PARENT_TREE,root_intake=pin(parent_raw)),
            actual_Native_cases=30,actual_D1_cases=13,actual_E_cases=17,actual_browser_cases=0,
            actual_Auth_HTTP_cases=0,actual_two_session_races=0,package_all_five=True,
            prior_runs_aggregated=False,retained_permanent6_fresh_case_credit=0,
            actual_used_refusal_raw_boundary=used,read_only_system_metadata=system_metadata,
            readonly_raw_dependency_metadata=raw_metadata,D_complete=False,E_complete=False,
            global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--check-source',action='store_true')
    p.add_argument('--archive',type=Path);p.add_argument('--artifact-metadata',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check_source:
        with GitBytes(a.source,HEAD or PREPARED_HEAD,TREE or PREPARED_TREE)as g:value=source(g)
        print(json.dumps(dict(status='EXACT_COMPLETE_DE_SOURCE_AND_THIRTY_IDS_ONLY',source=value,actual_Native_cases=0)))
    else:
        require(all((a.archive,a.artifact_metadata,a.output)),'DE30_CANONICAL_ARCHIVE_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(a.source,a.archive,strict(a.artifact_metadata.read_bytes()))
        a.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(status=value['status'],actual_Native_cases=30)))
