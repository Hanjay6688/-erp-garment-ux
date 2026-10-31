"""Exact focused Owner-access Native1 intake; never complete37 credit."""
from pathlib import Path
from hashlib import file_digest,sha256
import argparse,json,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,group,literal,declared_files

HEAD='6cb5bfe213fe3ce684244370dec092569705f6ff'
TREE='260cc8e984ae41409b43c62256acbbbf6ee25071'
RUN=41212698704
JOB=124570848589
BASE='b25eaae55a144aa03cc05f8f77109f5d0b02fbfb'
NS='scripts/current-s03-sku-s05-composite-qualification/'
CASE='CURRENT_S05_OWNER_ACCESS_NATIVE1_WITH_EXTRA_OWNER'
ACCESS='S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL'
MAIN='CP7_CURRENT_S03_SKU_S05_OWNER_ACCESS_NATIVE1.json'
RAW='CP7_S05_ON_SKU_OWNER_ACCESS_NATIVE1_CASES.json'
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)


def source(g):
    manifest=strict(g.read(NS+'SOURCE.json'))
    fields(manifest,dict(status='PREPARED_CURRENT_COMPOSITE37_NOT_EXECUTED',base_head=BASE,
        base_tree='e08f5eba90fd9a2deeb53a0a483c49e7a080e31c',actual_cases=0,
        production_go=False,independent_acceptance=False),'FOCUSED_SOURCE_IS_NOT_RESULT_CREDIT')
    exact(len(manifest['files']),69,'FOCUSED_EXACT69_SOURCE_PINS')
    for name,digest in manifest['files'].items():
        exact(sha256(g.read(name)).hexdigest(),digest,'FOCUSED_EXACT_SOURCE:'+name)
    base=g.entries(BASE);exact(len(base),14000,'FOCUSED_UNCHANGED_BASE14000')
    for name,value in base.items():exact(g.tree.get(name),value,'FOCUSED_PARENT_BLOB_AND_MODE:'+name)
    allowed=set(manifest['files'])|{NS+'SOURCE.json'}
    require(all(name.startswith(NS)or name in('.github/workflows/cp7-s03-sku-s05-composite.yml',
        '.github/workflows/cp7-s03-sku-owner-access-native1.yml')for name in allowed),'FOCUSED_ONLY_CLOSED_OWN_SOURCE_SCOPE')
    exact(set(g.tree)-set(base),allowed,'FOCUSED_EXACT70_OWN_PATHS')
    ids=list(literal(g,'scripts/cp7_accessory_standard_report/cases.py','IDS'))
    require(len(ids)==10 and ACCESS in ids,'FOCUSED_ORIGINAL_ACCESS_FROM_TEN_CALLBACKS')
    exact(literal(g,NS+'owner_focus_native.py','ACCESS'),ACCESS,'FOCUSED_EXACT_ORIGINAL_ACCESS_LITERAL')
    exact(literal(g,NS+'owner_focus_native.py','CASE'),CASE,'FOCUSED_EXACT_COMPONENT_LITERAL')
    old=g.read('scripts/current-sku-managed-recovery-native27-qualification/attempt_policy.py')
    current=g.read(NS+'owner_focus_attempt_policy.py')
    exact(current.replace(b'JOB_BUDGET_SECONDS = 90 * 60',b'JOB_BUDGET_SECONDS = 210 * 60',1),
        old,'FOCUSED_ONLY_NINETY_MINUTE_CONSTANT_CHANGE')
    return dict(source_pins=69,own_paths=70,unchanged_base_blobs_and_modes=14000,
        actual_case_credit=0,selected_original_case_id=ACCESS,source_manifest=pin(g.read(NS+'SOURCE.json')))


def owner_observations(g,row,seed):
    fields(row,dict(status='PASS',live_inactive_user_and_revoked_Admin_permission_refused=True,
        staff_with_rights_and_service_JWT_refused=True,
        all_private_ACLs_and_no_new_Native_writer_grants_checked_each_interval=True),
        'FOCUSED_ORIGINAL_ACCESS_ASSERTIONS')
    events=row['original_owner_fixture_observations']
    preparation=[x for x in events if x.get('kind')=='EXPLICIT_ISOLATED_ORIGINAL_LAST_OWNER_ROSTER']
    exact(len(preparation),1,'FOCUSED_ONE_ACTUAL_ROSTER_PREPARATION');prepared=preparation[0]
    fields(prepared,dict(original_last_owner_precondition_retained=True,Native_guard_or_trigger_changes=False,
        roles_permissions_grants_or_Auth_changed=False,synthetic_cleanup_escape=False,Native_case_credit=0),
        'FOCUSED_NO_GUARD_OR_AUTHORITY_BYPASS')
    before,after=prepared['before'],prepared['after'];require(len(before)>=2,'FOCUSED_REAL_MULTIPLE_ACTIVE_OWNER_ROWS')
    exact(len(before),len(after),'FOCUSED_ROSTER_MEMBERSHIP_RETAINED')
    owner=prepared['original_owner_auth'];exact(owner,seed['original_owner_auth'],'FOCUSED_SAME_ORIGINAL_ACTOR')
    require(seed['backup_owner_auth']!=owner and seed['backup_owner_auth']in{x[1]for x in before},
        'FOCUSED_REAL_ADDITIONAL_OWNER_WAS_IN_PREPARED_ROSTER')
    originals=[row for row in before if row[1]==owner];exact(len(originals),1,'FOCUSED_ONE_ORIGINAL_OWNER')
    for old,new in zip(before,after):
        require(len(old)==7,'FOCUSED_FULL_SELECTED_AUTHORITY_ROW')
        exact(old[2:], [True,'OWNER',old[4],'OWNER',True],'FOCUSED_ACTUAL_ACTIVE_EFFECTIVE_OWNER')
        expected=list(old)
        if old[1]!=owner:expected[2]=False
        exact(new,expected,'FOCUSED_ONLY_OTHER_ACTIVE_FLAGS_CHANGED')
    expected_inactive=[row[1]for row in before if row[1]!=owner]
    exact(prepared['temporarily_inactive_other_owner_auth'],expected_inactive,'FOCUSED_COMPLETE_EXTRA_OWNER_IDENTITIES')
    guarded=[x for x in events if x.get('kind')=='ACTUAL_NATIVE_FIXTURE_REFUSAL_NO_EFFECT']
    exact({x['label']for x in guarded},{'LAST_ACTIVE_OWNER_UNCHANGED','PROTECTED_OWNER_ROLE_UNCHANGED'},
        'FOCUSED_EXACT_TWO_ACTUAL_NATIVE_REFUSALS')
    for event in guarded:
        fields(event,dict(case_id=ACCESS,all22_catalog_equal=True,all_rows_and_every_sequence_equal=True,
            actual_parent_verified_before_and_after=True,Native_case_credit=0),'FOCUSED_REFUSAL_FULL_RAW_NO_EFFECT_ASSERTIONS')
        error='LAST_ACTIVE_OWNER_PROTECTED'if event['label']=='LAST_ACTIVE_OWNER_UNCHANGED'else'PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED'
        exact(event['actual_error']['sqlstate'],'42501','FOCUSED_EXACT_NATIVE_REFUSAL_SQLSTATE')
        exact(event['actual_error']['message'].splitlines()[0],error,'FOCUSED_EXACT_NATIVE_REFUSAL_MESSAGE')
    captures=[x for x in events if x.get('kind')=='ACTUAL_FRESH_VERIFIED_PARENT_NATIVE_INPUT_CAPTURE']
    exact(len(captures),1,'FOCUSED_ACTUAL_NATIVE_SOURCE_CAPTURE')
    for signature,name in(('erp.guard_last_active_owner()','guard_last_active_owner'),
        ('erp.guard_protected_role()','guard_protected_role')):
        current=captures[0]['functions'][signature];raw=g.read(NS+'owner-sql-controls/captured_'+name+'.sql')
        exact(current['definition'].encode(),raw,'FOCUSED_UNCHANGED_ACTUAL_NATIVE_GUARD:'+signature)
        exact(current['sha256'],sha256(raw).hexdigest(),'FOCUSED_ACTUAL_NATIVE_GUARD_DIGEST')
    return dict(active_owner_rows_before=len(before),original_actor=owner,
        actual_last_owner_and_protected_role_refusals=True,unchanged_actual_native_guard_sources=2,
        selected_authority_rows_preserved_except_other_active_flags=True,synthetic_cleanup_escape=False)


def intake(root,path,metadata):
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,conclusion='success',expired=False),
        'FOCUSED_EXACT_SUCCESSFUL_TERMINAL_API_METADATA')
    expected=metadata['archive'];path=Path(path)
    require(type(expected['bytes'])is int and expected['bytes']>0,'FOCUSED_CANONICAL_ARCHIVE_POSITIVE_BYTES')
    exact(path.stat().st_size,expected['bytes'],'FOCUSED_EXACT_CANONICAL_ARCHIVE_SIZE')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),expected['sha256'],'FOCUSED_CANONICAL_ARCHIVE_SHA256')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),len(set(names)),'FOCUSED_NO_DUPLICATE_CANONICAL_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'FOCUSED_COMPLETE_CANONICAL_ZIP_CRC')
        admitted=source(g);pins={}
        def original(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=original(MAIN);package=original('T3_PACKAGE_INSTALL.json');backup=original('T3_BACKUP_RESTORE_DRILL.json')
        fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[CASE],required_case_ids_pass=True,
            actual_Native_cases=1,actual_business_cases=1,actual_browser_cases=0,actual_Auth_HTTP_cases=0,
            actual_two_session_races=0,retained_full37_fresh_case_credit=0,real_Auth_browser_claim=False,
            used_guard_refused_before_DDL=True,baseline_full22_all_rows_all_sequences_equal=True,
            restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
            production_go=False,independent_acceptance=False),'FOCUSED_ACTUAL_ONE_AND_ALL_RESTORES')
        exact(set(main['committed']),{CASE},'FOCUSED_ONE_COMPONENT_ONLY');part=main['committed'][CASE]
        fields(part,dict(status='PASS',actual_Native_cases=1,actual_two_session_races=0,actual_Auth_HTTP_cases=0,
            actual_browser_cases=0,used_guard_refused_before_DDL=True,report_business_DML=False,
            Afui_positive_HPP_zero_reimbursement_actual_coverage=False),'FOCUSED_COMPONENT_EXACT_SCOPE')
        raw=original(RAW);exact(raw,part['native'],'FOCUSED_RAW_STRICT_GROUP_EQUALS_EMBEDDED');group(raw,[ACCESS])
        seed=part['focused_additional_owner_fixture']
        fields(seed,dict(administrative_fixture_only=True,original_second_active_owner_helper=True,
            Native_guard_changes=0,Native_case_credit=0),'FOCUSED_REAL_EXTRA_OWNER_FIXTURE')
        require(type(seed['active_owners_after'])is int and seed['active_owners_after']>=2,'FOCUSED_REAL_MULTIPLE_OWNERS_SEEDED')
        proof=owner_observations(g,raw['cases'][ACCESS],seed)
        fields(part['separate_committed_business_witness'],dict(status='NATIVE_BUSINESS_COMMITTED',
            Native10_case_credit=0,report_business_DML=False),'FOCUSED_ORIGINAL_NATIVE_USED_WITNESS_ZERO_CASE_CREDIT')
        exact(package['gate'],GATES,'FOCUSED_ALL_FIVE_PACKAGE_GATES')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
            'FOCUSED_EXACT_OWNING_RUN_IDENTITY')
        fields(backup,dict(status='RESTORED_IDENTICAL'),'FOCUSED_WHOLE_BACKUP_DRILL')
        require(bool(backup['checks'])and all(type(v)is bool and v for v in backup['checks'].values()),'FOCUSED_ALL_TYPED_BACKUP_CHECKS')
        exact(backup['data']['differ'],{},'FOCUSED_NO_BACKUP_ROW_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'FOCUSED_BASELINE_ROLES_RESTORED')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'FOCUSED_COMPLETE_OUTER_RESTORE_RECEIPT')
        maps=declared_files(g,main['source_declaration']['current_installation'])
        return dict(status='ROOT_VERIFIED_CURRENT_OWNER_ACCESS_NATIVE1_ALL5',head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,
            artifact_id=metadata['artifact_id'],archive=dict(expected,members=len(names)),originals=pins,
            source_admission=admitted,actual_product_source_maps=maps,actual_owner_guard_proof=proof,
            actual_Native_cases=1,actual_browser_cases=0,package_all_five=True,package_gates=package['gate'],
            full37_qualified=False,prior_runs_aggregated=False,retained_current30_fresh_case_credit=0,
            source_bound_original_committed_use_and_used_refusal_assertions=True,
            global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--check-source',action='store_true')
    p.add_argument('--archive',type=Path);p.add_argument('--artifact-metadata',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check_source:
        with GitBytes(a.source,HEAD,TREE)as g:value=source(g)
        print(json.dumps(dict(status='EXACT_CURRENT_OWNER_ACCESS1_SOURCE_ONLY',source=value,actual_Native_cases=0)))
    else:
        require(all((a.archive,a.artifact_metadata,a.output)),'FOCUSED_CANONICAL_ARCHIVE_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(a.source,a.archive,strict(a.artifact_metadata.read_bytes()));a.output.write_text(json.dumps(value,indent=2)+'\n')
        print(json.dumps({k:value[k]for k in('status','actual_Native_cases','full37_qualified')}))
