"""Full actual Afui canonical packet gate. Pending parent never earns credit."""
from hashlib import sha256,file_digest
from pathlib import Path,PurePosixPath
import gzip,importlib.util,json,re,subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN='CP7_AFUI_GOOD_NONPAYABLE_FULL15.json'
RAW='CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9.json'
CASE='CURRENT_AFUI_GOOD_NONPAYABLE_NATIVE9_HTTP2_SESSION2_BROWSER2'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def supervisor(p,value,head,run_id):
    if type(run_id)is not str or re.fullmatch('[1-9][0-9]*',run_id)is None:
        raise ValueError('NONPAYABLE_ACTUAL_PACKAGE_RUN_ID_REQUIRED')
    p.fields(value,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=head,
        github_run_id=run_id,github_run_attempt='1',worker_exit=0,deadline_reached=False,
        external_signal=None,orphaned_child=False,process_group_empty=True,process_tree_empty=True,
        signals=[],actual_case_credit=0,production_go=False,job_budget_seconds=21600,
        work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600),
        'NONPAYABLE_ACTUAL_COMPLETE_OWNED_PROCESS_AND_UNCHANGED_BUDGETS')
    return dict(status='ACTUAL_PROCESS_TREE_COMPLETELY_REAPED',actual_case_credit=0)

def asset_file(directory,reference):
    from cp7_accessory_nonpayable import admission
    name=reference.get('name')
    if(type(name)is not str or len(PurePosixPath(name).parts)!=1 or name in('.','..')or'\\'in name
        or'\x00'in name or PurePosixPath(name).is_absolute()):
        raise ValueError('NONPAYABLE_CANONICAL_ORIGINAL_SAFE_BASENAME_REQUIRED')
    path=directory/name
    if path.is_symlink()or path.parent.resolve()!=directory.resolve():
        raise ValueError('NONPAYABLE_CANONICAL_ORIGINAL_SYMLINK_OR_ESCAPE')
    return path

def verify_reference(directory,reference):
    from cp7_accessory_nonpayable import admission
    path=asset_file(directory,reference)
    with path.open('rb')as stream:
        actual=dict(bytes=path.stat().st_size,sha256=file_digest(stream,'sha256').hexdigest())
    if 'gzip_sha256'in reference:
        if actual!=admission.require_pin(dict(bytes=reference.get('gzip_bytes'),sha256=reference.get('gzip_sha256'))):
            raise ValueError('NONPAYABLE_COMPRESSED_RAW_CENSUS_CHANGED')
        digest=sha256();count=0
        with gzip.open(path,'rb')as stream:
            while chunk:=stream.read(1024*1024):count+=len(chunk);digest.update(chunk)
        actual=dict(bytes=count,sha256=digest.hexdigest())
    if actual!=admission.require_pin({k:reference.get(k)for k in('bytes','sha256')}):
        raise ValueError('NONPAYABLE_COMPLETE_RAW_ORIGINAL_BYTES_CHANGED:'+reference['name'])
    return path

def artifact(directory,reference):
    path=verify_reference(directory,reference);packed=path.read_bytes()
    raw=gzip.decompress(packed)if'gzip_sha256'in reference else packed
    return raw

def compare_census(before,after,declared,installed_catalog):
    from cp7_accessory_nonpayable import access_cases
    allowed=set(declared)
    if not allowed.issubset(access_cases.ALLOWED_DATE_TABLES):
        raise ValueError('NONPAYABLE_RAW_CENSUS_MAY_ONLY_CHANGE_DECLARED_DATE_TABLES')
    changed=access_cases.require_changes(before,after,allowed)
    if before['catalog']!=installed_catalog or after['catalog']!=installed_catalog:
        raise ValueError('NONPAYABLE_EVERY_RAW_COPY_CENSUS_MUST_EQUAL_FULL_CURRENT_INSTALLED_CATALOG')
    expected=[]
    for section,key,table in(('date_versions','id','cp7_accessory_nonpayable.category_versions_v1'),
        ('date_requests','request_id','cp7_accessory_nonpayable.date_requests_v1')):
        old={r[key]for r in before[section]};new={r[key]for r in after[section]}
        access_cases.require_append(before,after,section,key,new-old)
        if before[section]!=after[section]:expected.append(table)
    if sorted(changed)!=sorted(expected):raise ValueError('NONPAYABLE_PRIVATE_ROW_FINGERPRINT_AND_RAW_APPEND_HISTORY_DISAGREE')
    if('active_good'in before or'active_good'in after)and before.get('active_good')!=after.get('active_good'):
        raise ValueError('NONPAYABLE_RAW_BROWSER_CENSUS_CHANGED_POSTED_GOOD_HPP_OR_STOCK')
    return changed

def race_facts(row,*,same):
    results=row.get('results');versions=row.get('actual_versions');requests=row.get('actual_requests')
    if(type(results)is not list or len(results)!=2 or any(type(r.get('backend_pid'))is not int or r['backend_pid']<1 for r in results)
        or len({r['backend_pid']for r in results})!=2 or type(versions)is not list or len(versions)!=1
        or type(requests)is not list or len(requests)!=1):
        raise ValueError('NONPAYABLE_RAW_TWO_BACKENDS_AND_ONE_IMMUTABLE_EFFECT_REQUIRED')
    winners=[r for r in results if r.get('ok')is True];losers=[r for r in results if r.get('ok')is False]
    if same:
        if(len(winners)!=2 or winners[0]['request_id']!=winners[1]['request_id']or winners[0]['result']!=winners[1]['result']):
            raise ValueError('NONPAYABLE_RAW_SAME_REQUEST_REQUIRES_IDENTICAL_TWO_SESSION_REPLY')
    elif(len(winners)!=1 or len(losers)!=1 or winners[0]['request_id']==losers[0]['request_id']
        or losers[0].get('sqlstate')!='P0001'or not losers[0].get('message','').startswith('NONPAYABLE_TIMELINE_STALE:')):
        raise ValueError('NONPAYABLE_RAW_DISTINCT_REQUESTS_REQUIRE_ONE_EXACT_STALE_LOSER')
    first=winners[0]
    if(first['result'].get('status')!='SAVED'or requests[0]['response']!=first['result']
        or requests[0]['request_id']!=first['request_id']or versions[0]['id']!=first['result']['id']
        or versions[0]['request_id']!=first['request_id']):
        raise ValueError('NONPAYABLE_RAW_WINNING_REQUEST_DATE_AND_LEDGER_MUST_BE_THE_SAME')

def assets(directory,part,installed_catalog):
    from cp7_accessory_nonpayable import admission
    originals={};screens=[];censuses=[]
    def visit(value):
        if type(value)is dict:
            if {'original_before','original_after','actual_changed_tables'}<=set(value):
                before=admission.strict(artifact(directory,value['original_before']))
                after=admission.strict(artifact(directory,value['original_after']))
                changed=compare_census(before,after,value['actual_changed_tables'],installed_catalog)
                if sorted(changed)!=sorted(value['actual_changed_tables']):raise ValueError('NONPAYABLE_BROWSER_DECLARED_CHANGE_DIFFERS_FROM_RAW_CENSUS')
                censuses.append(changed)
            elif {'original','actual_changed_tables','allowed_tables'}<=set(value):
                raw=admission.strict(artifact(directory,value['original']))
                changed=compare_census(raw['before'],raw['after'],value['allowed_tables'],installed_catalog)
                if changed!=value['actual_changed_tables']:raise ValueError('NONPAYABLE_ACCESS_DECLARED_CHANGE_DIFFERS_FROM_RAW_CENSUS')
                censuses.append(changed)
            if {'name','bytes','sha256'}<=set(value):
                if value['name']in originals and originals[value['name']]!=value:
                    raise ValueError('NONPAYABLE_CONFLICTING_CANONICAL_ORIGINAL_REFERENCES')
                if value['name']not in originals:verify_reference(directory,value);originals[value['name']]=value
            for child in value.values():visit(child)
        elif type(value)is list:
            for child in value:visit(child)
    # These are the current component originals, not parent archive aggregates.
    for key in('strict_group_originals','browser_fixture_original','browser_settings_state_original','browser_settings_cache_original','http','races','browser'):
        visit(part[key])
    for row in part['browser']['cases'].values():
        for name in row['screenshots']:
            p=PurePosixPath(name)
            if len(p.parts)!=3 or p.parts[:2]!=('cp6-proof','t3')or not p.name.startswith('AFUI_')or p.suffix!='.png':
                raise ValueError('NONPAYABLE_EXACT_CURRENT_BROWSER_SCREENSHOT_PATH_REQUIRED')
            path=directory/p.name
            if path.is_symlink()or not path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('NONPAYABLE_ACTUAL_CURRENT_BROWSER_PNG_REQUIRED')
            screens.append(p.name)
    if not originals or not censuses or len(screens)<4:raise ValueError('NONPAYABLE_COMPLETE_ACTUAL_ORIGINALS_CENSUSES_AND_SCREENSHOTS_REQUIRED')
    return dict(complete_raw_originals_verified=len(originals),actual_screenshots_verified=screens,
        independently_recomputed_raw_census_intervals=len(censuses),no_projected_or_dropped_census_bytes=True)

def validate(p,main,raw,package,backup,owned,head,*,source_graph,directory):
    from cp7_accessory_nonpayable import admission,assembly,native_cases,access_cases,browser_prepare,case_boundary,qualification_gate,native_fixture,advisor_review,lossless_state
    receipt=admission.parent_receipt()
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids=[CASE],required_case_ids_pass=True,
        actual_Native_cases=9,actual_browser_cases=2,actual_business_cases=15,actual_Auth_HTTP_cases=2,
        actual_two_session_races=2,retained_FREE3_fresh_case_credit=0,real_Auth_browser_claim=True,
        real_Auth_HTTP_qualified=True,baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,
        cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        production_go=False,independent_acceptance=False),'NONPAYABLE_CURRENT_FIFTEEN_AND_COMPLETE_RESTORATION')
    p.exact(set(main['committed']),{CASE},'NONPAYABLE_ONE_CURRENT_COMPONENT')
    advisor_review.require_closed(main['current_private_info_authority'])
    review=main['advisor_disposition']
    p.fields(review,dict(status='VERIFIED_AFUI_PRIVATE_DEFAULT_DENY_INFO',gate=True,unexplained=[]),
        'NONPAYABLE_EXACT_REVIEWED_PRIVATE_DEFAULT_DENY_INFOS')
    p.exact(sorted(row['metadata']['name']for row in review['reviewed_Afui_private_info']),list(advisor_review.TABLES),
        'NONPAYABLE_EVERY_ACTUAL_AFUI_PRIVATE_INFO_REVIEWED_ONCE')
    p.fields(main['source_declaration'],dict(status='ACTUAL_FREE3_PARENT_AND_COMPLETE_NONPAYABLE_SOURCE_GRAPH_ADMITTED',
        parent_head=receipt['head'],parent_tree=receipt['tree'],parent_run=receipt['run_id']),
        'NONPAYABLE_EXACT_ACTUAL_ACCEPTED_FREE3_PARENT')
    if source_graph is None:raise ValueError('NONPAYABLE_COMPLETE_NATURAL_SOURCE_GRAPH_REQUIRED')
    p.exact(main['source_declaration']['complete_sources'],source_graph,'NONPAYABLE_COMPLETE_ACTUAL_CANDIDATE_SOURCE_GRAPH')
    part=main['committed'][CASE]
    p.fields(part,dict(status='PASS',actual_Native_cases=9,actual_Auth_HTTP_cases=2,actual_two_session_races=2,
        actual_browser_cases=2,actual_business_cases=15,retained_FREE3_fresh_case_credit=0,
        used_guard_refused_before_DDL=True,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False),'NONPAYABLE_CURRENT_GROUP_COUNTS_NOT_GLOBAL_OR_PARENT_CREDIT')
    p.exact(raw,part['native'],'NONPAYABLE_RAW_STRICT_NATIVE9_EQUALS_EMBEDDED')
    qualification_gate.native(raw,native_cases.IDS)
    for name,row in raw['cases'].items():
        boundary=row['actual_full22_case_boundary']
        p.exact(boundary['verification'],case_boundary.validate(boundary,case_id=name,result=row),
            'NONPAYABLE_INDEPENDENT_FULL_CASE_AND_EVERY_NATIVE_SEQUENCE_WITNESS:'+name)
    qualification_gate.copies(part['http'],access_cases.HTTP_IDS,mode='HTTP')
    qualification_gate.copies(part['races'],access_cases.RACE_IDS,mode='RACE')
    qualification_gate.copies(part['browser'],browser_prepare.IDS,mode='BROWSER')
    for index,name in enumerate(access_cases.RACE_IDS):race_facts(part['races']['races'][name],same=index==0)
    waited=part['http']['cases'][access_cases.HTTP_IDS[1]]
    p.fields(waited['administrative_access_fixture'],dict(role='OWNER',before_active=True,after_active=False),
        'NONPAYABLE_ACTUAL_REAL_OWNER_DEACTIVATED_AFTER_OBSERVED_WAIT')
    p.fields(waited['actual_refusal_after_wait'],dict(status=403),'NONPAYABLE_CURRENT_AUTH_WAIT_REFUSAL')
    p.fields(waited['actual_refusal_after_wait']['body'],dict(code='42501',message='NONPAYABLE_SETTINGS_DENIED'),
        'NONPAYABLE_EXACT_REAL_AUTH_CACHED_REPLAY_REFUSED_AFTER_WAIT')
    wait=waited['actual_blocked_PostgREST_backend']
    if(type(wait.get('pid'))is not int or type(waited.get('holder_pid'))is not int or wait['pid']==waited['holder_pid']
        or wait.get('wait_event_type')!='Lock'or 'erp_cp7_save_good_policy_date_v1'not in wait.get('actual_query','')):
        raise ValueError('NONPAYABLE_RAW_ACTUAL_POSTGREST_BACKEND_AND_HOLDER_WAIT_REQUIRED')
    if waited['cached_original']['request_id']!=waited['actual_same_request_uuid']:
        raise ValueError('NONPAYABLE_CACHED_REAL_AUTH_WAIT_MUST_REUSE_ORIGINAL_REQUEST')
    copies=part['copy_authority']['actual_copy_admissions']
    if len(copies)!=4:raise ValueError('NONPAYABLE_ALL_FOUR_AUTHORITY_PRESERVED_FRESH_COPIES_REQUIRED')
    for row in copies:
        p.fields(row,dict(before_changed_catalog_members={'database_authority':['CURRENT']},
            product_state_modified=False,Native_or_schema_or_RPC_permissions_changed=False,
            all22_groups_equal_original_install=True),'NONPAYABLE_RAW_COPY_AUTHORITY_WITHOUT_MASK_OR_NEW_GRANTS')
    prepared=admission.strict(artifact(directory,part['browser_fixture_original']))
    original=part['browser_settings_state_original'];cache=part['browser_settings_cache_original']
    state=lossless_state.read(verify_reference(directory,cache),cache['sha256'],
        verify_reference(directory,original),original['sha256'])
    p.exact(lossless_state.canonical_pin(state),{k:original[k]for k in('bytes','sha256')},
        'NONPAYABLE_ALL_DECODED_STATE_CANONICAL_BYTES_EQUAL_COMPLETE_ORIGINAL')
    if prepared['status']!='ACTUAL_NATIVE_NONPAYABLE_BROWSER_PREREQUISITE_PREPARED':
        raise ValueError('NONPAYABLE_ACTUAL_NATIVE_GOOD_BROWSER_PREREQUISITE_REQUIRED')
    p.exact(prepared.get('observer_catalogue'), dict(after=state['after'], original=original, cache=cache),
        'NONPAYABLE_BROWSER_OBSERVER_INPUT_EQUALS_COMPLETE_DECODED_STATE')
    native_fixture.require_economics(prepared['actual_good'],prepared['fixture'],nonpayable=True,hpp='20')
    used=part['separate_committed_Native_use']
    p.fields(used,dict(status='ACTUAL_POSITIVE_HPP_ZERO_REIMBURSEMENT_GOOD_COMMITTED',
        actual_GOOD_lot=prepared['fixture']['lot'],Native_case_credit=0,used_guard_before_DDL=True,
        actual_used_inverse_error=assembly.USED_ERROR),'NONPAYABLE_ACTUALLY_USED_GOOD_REFUSAL_BEFORE_DDL')
    native_fixture.require_economics(used['actual_economics'],prepared['fixture'],nonpayable=True,hpp='20')
    p.exact(used['before'],used['after'],'NONPAYABLE_USED_INVERSE_FULL_NO_EFFECT')
    p.exact(used['before']['actual_all22'],state['after'],'NONPAYABLE_UNPROJECTED_USED_CATALOG_IS_COMPLETE_INSTALLED_STATE')
    for name,row in raw['cases'].items():
        p.exact(row['actual_full22_case_boundary']['before']['actual_all22'],state['after'],
            'NONPAYABLE_EVERY_NATIVE_CASE_FULL_CURRENT_INSTALLED_CATALOG:'+name)
    p.exact(package['gate'],p.GATES,'NONPAYABLE_ALL_FIVE_ACTUAL_PACKAGE_GATES')
    p.fields(package['run_identity'],dict(tool_head=head,github_sha=head,run_attempt='1'),
        'NONPAYABLE_EXACT_CURRENT_OWNING_PACKAGE')
    process=supervisor(p,owned,head,package['run_identity']['run_id'])
    p.fields(backup,dict(status='RESTORED_IDENTICAL'),'NONPAYABLE_COMPLETE_ACTUAL_BACKUP_DRILL')
    if not backup['checks']or any(type(v)is not bool or not v for v in backup['checks'].values()):
        raise ValueError('NONPAYABLE_EVERY_TYPED_BACKUP_CHECK_MUST_PASS')
    p.exact(backup['data']['differ'],{},'NONPAYABLE_BACKUP_NO_ROW_DIFFERENCE')
    evidence=assets(directory,part,state['after'])
    return dict(status='CURRENT_AFUI_GOOD_NONPAYABLE_NATIVE9_HTTP2_SESSION2_BROWSER2_AND_ALL5_PASS',head=head,
        actual_fresh_cases=15,actual_Native_cases=9,actual_Auth_HTTP_cases=2,actual_two_session_races=2,
        actual_browser_cases=2,retained_FREE3_fresh_case_credit=0,GOOD_eligibility_policy_decided=True,
        raw_assets=evidence,owned_process=process,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False)

def gate(directory,head):
    from cp7_accessory_nonpayable import admission,assembly
    admission.parent_receipt()  # Before reading any purported success artifact.
    p=load('afui_exact_original_typed_packet_validator',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    docs=[admission.strict((directory/name).read_bytes())for name in(MAIN,RAW,'T3_PACKAGE_INSTALL.json',
        'T3_BACKUP_RESTORE_DRILL.json','AFUI_RUNTIME_SUPERVISION.json')]
    return validate(p,*docs,head,source_graph=assembly.sources(),directory=directory)

if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'scripts'))
    head=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    value=gate(ROOT/'cp6-proof/t3',head)
    (ROOT/'cp6-proof/t3/AFUI_FINAL_GATE.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
