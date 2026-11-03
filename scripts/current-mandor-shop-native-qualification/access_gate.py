"""Resolve original race observations; a prepared count cannot pass this gate."""
from hashlib import sha256
from pathlib import Path
from decimal import Decimal
import gzip,importlib.util,re
import access_cases,access_runtime

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ALL22={'schemas','relations','columns','constraints','indexes','triggers','functions','aggregates',
    'types','enums','sequences','policies','extensions','roles','memberships','event_triggers','rules',
    'inheritance','default_privileges','database_authority','type_implementation','sequence_ownership'}


def require(value,message):
    if not value:raise ValueError(message)


def observation(p,directory,proof,expected_allowed):
    p.fields(proof,dict(status='PASS',actual_all22_groups=22,allowed_tables=sorted(expected_allowed)),
        'MANDOR_ACCESS_GATE_EXACT_PROOF_SCOPE')
    reference=proof['original'];name=reference['name']
    require(type(name)is str and re.fullmatch(r'MANDOR_ACCESS_(SAME|COMPETING|RETRY|ACCESS_FIXTURE|CACHED_REVOKED|HTTP_READ_RIGHTS|HTTP_RESERVE|HTTP_REPLAY|HTTP_RELEASE|HTTP_RELEASE_REPLAY|HTTP_REVOKE_RESERVE|HTTP_ACTOR_REVOKED|HTTP_CACHED_REVOKED)_[0-9a-f]{32}\.json\.gz',name),
        'MANDOR_ACCESS_GATE_FIXED_ORIGINAL_NAME')
    path=directory/name;require(not path.is_symlink(),'MANDOR_ACCESS_GATE_NO_ORIGINAL_SYMLINK')
    packed=path.read_bytes();p.exact(dict(bytes=len(packed),sha256=sha256(packed).hexdigest()),
        dict(bytes=reference['gzip_bytes'],sha256=reference['gzip_sha256']),'MANDOR_ACCESS_GATE_PACKED_ORIGINAL')
    raw=gzip.decompress(packed);p.exact(dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),
        dict(bytes=reference['raw_bytes'],sha256=reference['raw_sha256']),'MANDOR_ACCESS_GATE_FULL_ORIGINAL')
    value=p.strict(raw);p.exact(set(value),{'before','after'},'MANDOR_ACCESS_GATE_BOTH_COMPLETE_OBSERVATIONS')
    before,after=value['before'],value['after']
    expected={'actual_all22','full_data_and_sequences','actor','actor_audits','invoice','allocation_states','requests','deductions','payroll'}
    p.exact(set(before),expected,'MANDOR_ACCESS_GATE_FULL_BEFORE_KEYS');p.exact(set(after),expected,'MANDOR_ACCESS_GATE_FULL_AFTER_KEYS')
    p.exact(set(before['actual_all22']),ALL22,'MANDOR_ACCESS_GATE_EXACT22_NAMES')
    p.exact(before['actual_all22'],after['actual_all22'],'MANDOR_ACCESS_GATE_UNCHANGED_INSTALLED_AUTHORITY')
    left,right=before['full_data_and_sequences'],after['full_data_and_sequences']
    require(bool(left)and any(k.startswith('sequence:')for k in left),'MANDOR_ACCESS_GATE_COMPLETE_ROWS_AND_SEQUENCES')
    p.exact(set(left),set(right),'MANDOR_ACCESS_GATE_SAME_DATA_SEQUENCE_UNIVERSE')
    changed=sorted(k for k in left if left[k]!=right[k])
    p.exact(proof['changed_tables'],changed,'MANDOR_ACCESS_GATE_ACTUAL_CHANGED_TABLES')
    require(set(changed)<=set(expected_allowed),'MANDOR_ACCESS_GATE_UNDECLARED_WRITES')
    if not expected_allowed:p.exact(before,after,'MANDOR_ACCESS_GATE_EXACT_NO_EFFECT_ORIGINALS')
    p.exact(before['invoice'],after['invoice'],'MANDOR_ACCESS_GATE_NO_INVOICE_SETTLEMENT')
    return dict(name=name,original=reference,changed_tables=changed),before,after


def allocation(p,before,after,row,same_request):
    p.exact(before['allocation_states'],[],'MANDOR_ACCESS_GATE_FRESH_UNALLOCATED_SALE')
    p.exact(before['deductions'],[],'MANDOR_ACCESS_GATE_FRESH_UNDEDUCTED_PAYROLL')
    p.exact(before['actor'],after['actor'],'MANDOR_ACCESS_GATE_ALLOCATION_PRESERVES_ACTOR')
    p.exact(before['actor_audits'],after['actor_audits'],'MANDOR_ACCESS_GATE_ALLOCATION_PRESERVES_ACTOR_AUDIT')
    p.exact(after['payroll'][0],'CALCULATED','MANDOR_ACCESS_GATE_ACTUAL_NATIVE_CALCULATED_STATUS')
    require(Decimal(after['payroll'][1])==Decimal('1900000.00'),'MANDOR_ACCESS_GATE_EXACT_ONE_DEDUCTION_NET')
    first=row['first'];p.fields(first,dict(kind='COMMITTED_OUTCOME',action='RESERVE',
        invoice_settled_by_this_command=False),'MANDOR_ACCESS_GATE_DRAFT_RESERVATION_NOT_PAYMENT')
    require(len(after['allocation_states'])==len(after['deductions'])==1,'MANDOR_ACCESS_GATE_SINGLE_ALLOCATION_AND_DEDUCTION')
    p.fields(after['allocation_states'][0],dict(allocation_id=first['allocation_id'],state='RESERVED'),
        'MANDOR_ACCESS_GATE_ONE_ACTUAL_RESERVED_ALLOCATION')
    require(Decimal(after['deductions'][0]['amount'])==Decimal('100000.00'),
        'MANDOR_ACCESS_GATE_EXACT_ACTUAL_NATIVE_DEDUCTION')
    old={r['request_id']:r for r in before['requests']};new={r['request_id']:r for r in after['requests']}
    request=first['request_id'];p.exact(set(new),set(old)|{request},'MANDOR_ACCESS_GATE_ONE_UUID_COMMIT')
    for key,value in old.items():p.exact(new[key],value,'MANDOR_ACCESS_GATE_PRIOR_REQUEST_IMMUTABLE')
    p.exact(new[request]['response'],first,'MANDOR_ACCESS_GATE_ORIGINAL_COMMITTED_OUTCOME')
    if same_request:p.fields(row['retry'],dict(ok=True,reply=first),'MANDOR_ACCESS_GATE_SAME_UUID_EXACT_REPLAY')
    else:p.fields(row['retry'],dict(ok=False,sqlstate='P0001',message='CP7_MANDOR_SHOP_REVIEW_CHANGED'),
        'MANDOR_ACCESS_GATE_COMPETING_UUID_STALE_REFUSAL')
    p.fields(row['changed_intent_refusal'],dict(ok=False,sqlstate='P0001',message='CP7_MANDOR_SHOP_REQUEST_CHANGED'),
        'MANDOR_ACCESS_GATE_CHANGED_INTENT_REFUSAL')


def revocation(p,before,after):
    p.fields(before['actor'],dict(is_active=True),'MANDOR_ACCESS_GATE_ORIGINAL_ACTIVE_ACTOR')
    p.fields(after['actor'],dict(id=before['actor']['id'],is_active=False),'MANDOR_ACCESS_GATE_EXACT_ACTOR_DEACTIVATED')
    old={r['id']:r for r in before['actor_audits']};new={r['id']:r for r in after['actor_audits']}
    require(len(new)==len(old)+1 and set(old)<=set(new),'MANDOR_ACCESS_GATE_ONE_REVOCATION_AUDIT_APPEND')
    for key,value in old.items():p.exact(new[key],value,'MANDOR_ACCESS_GATE_OLD_ACTOR_AUDITS_IMMUTABLE')
    audit=next(v for k,v in new.items()if k not in old)
    p.fields(audit,dict(action='UPDATE',old_data=before['actor'],new_data=after['actor']),
        'MANDOR_ACCESS_GATE_NATIVE_ACTOR_AUDIT_FULL_OLD_NEW')
    for key in('allocation_states','requests','deductions','payroll'):
        p.exact(before[key],after[key],'MANDOR_ACCESS_GATE_ADMIN_FIXTURE_CANNOT_CHANGE_MONEY:'+key)


def gate(p,directory,part,frozen):
    reference=part['session4_original'];p.exact(reference['name'],'MANDOR_SESSION4_ORIGINAL.json','MANDOR_ACCESS_GATE_ORIGINAL_FILE')
    path=directory/reference['name'];require(not path.is_symlink(),'MANDOR_ACCESS_GATE_NO_REPORT_SYMLINK')
    actual=p.pinned(path.read_bytes(),{k:reference[k]for k in('bytes','sha256')},'MANDOR_SESSION4_EXACT_ORIGINAL')
    spec=importlib.util.spec_from_file_location('mandor_final_typed_copy_gate',frozen/'scripts/cp7_accessory_nonpayable/qualification_gate.py')
    typed=importlib.util.module_from_spec(spec);spec.loader.exec_module(typed)
    gate_result=typed.copies(actual,access_cases.RACE_IDS,mode='RACE')
    p.exact(part['session4_gate'],gate_result,'MANDOR_SESSION4_TYPED_COMPLETE_COPY_GATE')
    copies=part['access_copy_authority'];_,source=access_runtime.derive((frozen/access_runtime.ORIGINAL).read_bytes())
    p.exact(copies['source'],source,'MANDOR_ACCESS_GATE_EXACT_COPY_AUTHORITY_DERIVATION')
    require(len(copies['actual_copy_admissions'])==4,'MANDOR_ACCESS_GATE_FOUR_DISTINCT_FRESH_COPIES')
    for row in copies['actual_copy_admissions']:
        p.fields(row,dict(all22_groups_equal_original_install=True,product_state_modified=False,
            Native_or_schema_or_RPC_permissions_changed=False),'MANDOR_ACCESS_GATE_PRESERVED_ALL22_COPY')
    originals=[]
    for index,name in enumerate(access_cases.RACE_IDS):
        row=actual['races'][name]
        p.fields(row,dict(status='PASS',actual_two_database_sessions=True,administrative_actor_not_real_Auth=True,
            actual_Native_case_credit=0,actual_Auth_HTTP_case_credit=0,actual_browser_case_credit=0,
            full_copy_restore_required=True),'MANDOR_ACCESS_GATE_CURRENT_REAL_TWO_BACKEND_CASE')
        require(len(row['proofs'])==2,'MANDOR_ACCESS_GATE_COMPLETE_POSITIVE_AND_NOEFFECT_OBSERVATIONS')
        first_allowed=access_cases.ALLOCATION_TABLES if index<2 else{'erp.app_users','erp.audit_logs','sequence:erp.audit_logs_id_seq'}
        first,before,after=observation(p,directory,row['proofs'][0],first_allowed)
        second,retry_before,retry_after=observation(p,directory,row['proofs'][1],set())
        p.exact(after,retry_before,'MANDOR_ACCESS_GATE_CONTIGUOUS_POSITIVE_AND_RETRY_ORIGINALS')
        originals.extend([first,second])
        if index<2:allocation(p,before,after,row,index==0)
        else:revocation(p,before,after)
        peer=row['contender']if index<2 else row['pending_revocation']
        require(type(row['holder_pid'])is int and type(peer['backend_pid'])is int
            and row['holder_pid']!=peer['backend_pid'],'MANDOR_ACCESS_GATE_DISTINCT_ACTUAL_BACKENDS')
        require(peer['ok']is False and peer['sqlstate']=='55P03'and 0<=peer['elapsed']<3,
            'MANDOR_ACCESS_GATE_ACTUAL_PROMPT_CONTENTION_REFUSAL')
        if index>=2:
            p.fields(row,dict(permission_checked_before_cached_reply=True),'MANDOR_ACCESS_GATE_CURRENT_REPLAY_RIGHTS')
            message='CP7_MANDOR_SHOP_ACCESS_DENIED'if index==2 else'CP7_SALES_ACCESS_DENIED'
            p.fields(row['committed_revocation'],dict(ok=False,sqlstate='42501',message=message),
                'MANDOR_ACCESS_GATE_ACTUAL_CURRENT_REVOKED_PERMISSION')
    require(len({item['name']for item in originals})==8,'MANDOR_ACCESS_GATE_EIGHT_DISTINCT_ACTUAL_OBSERVATIONS')
    return dict(status='ACTUAL_MANDOR_SESSION4_ALL_COPIES_RESTORED',actual_two_session_races=4,
        original_observations=originals,actual_Auth_HTTP_cases=0,actual_browser_cases=0,actual_Native_case_credit=0)
