"""Read-only D1/E Native30 intake, closed until its actual owning run exists.

Prepared-source admission grants no case credit. Activation must replace the
prepared base with the accepted permanent6 parent and bind its exact receipt.
"""
from pathlib import Path
from hashlib import file_digest,sha256
import argparse,json,re,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,group,full_census,declared_files

HEAD=None
TREE=None
RUN=None
JOB=None
PARENT_HEAD=None
PARENT_TREE=None
PREPARED_HEAD='a93bd2be7d8fb04ae379dbf34e39b08d1eaeddf7'
PREPARED_TREE='505b3b0f240f000f3ab38a440f2a1517d80afcd0'
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
        exact(len(base),14092,'DE30_PREPARED_PARENT14092');exact(len(allowed),55,'DE30_PREPARED_OWN55')
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
    return dict(source_pins=len(declaration['files']),own_paths=len(allowed),unchanged_base=len(base),
        D1_ids=d1,E_ids=e,source_manifest=pin(g.read(NS+'SOURCE.json')),
        unchanged_business_source_files=3,frozen_fixture_inputs=4,recorded_predecessor_functions=32,
        actual_case_credit=0,parent_qualification_pending=PARENT_HEAD is None)


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
            actual_used_refusal_raw_boundary=used,read_only_system_metadata=system_metadata,D_complete=False,E_complete=False,
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
