"""Read the exact real-Auth originals and full copy/primary-Auth restoration."""
from decimal import Decimal
import importlib.util
import access_cases,access_gate,access_runtime,http_cases


def require(value,message):
    if not value:raise ValueError(message)


def gate(p,directory,part,frozen):
    ref=part['HTTP2_original'];p.exact(ref['name'],'MANDOR_HTTP2_ORIGINAL.json','MANDOR_HTTP_FIXED_ORIGINAL')
    path=directory/ref['name'];require(not path.is_symlink(),'MANDOR_HTTP_NO_SYMLINK_ORIGINAL')
    actual=p.pinned(path.read_bytes(),{k:ref[k]for k in('bytes','sha256')},'MANDOR_HTTP_EXACT_ORIGINAL')
    spec=importlib.util.spec_from_file_location('mandor_final_real_Auth_copy_gate',frozen/'scripts/cp7_accessory_nonpayable/qualification_gate.py')
    typed=importlib.util.module_from_spec(spec);spec.loader.exec_module(typed)
    result=typed.copies(actual,http_cases.HTTP_IDS,mode='HTTP')
    p.exact(part['HTTP2_gate'],result,'MANDOR_HTTP_ORIGINAL_TYPED_GATE')
    _,source=access_runtime.derive((frozen/access_runtime.ORIGINAL).read_bytes())
    copies=part['http_copy_authority'];p.exact(copies['source'],source,'MANDOR_HTTP_EXACT_COPY_AUTHORITY')
    require(len(copies['actual_copy_admissions'])==1,'MANDOR_HTTP_ONE_COMPLETE_FRESH_COPY')
    p.fields(copies['actual_copy_admissions'][0],dict(all22_groups_equal_original_install=True,
        product_state_modified=False,Native_or_schema_or_RPC_permissions_changed=False),'MANDOR_HTTP_UNCHANGED_AUTHORITY')
    originals=[]
    for index,name in enumerate(http_cases.HTTP_IDS):
        row=actual['cases'][name]
        p.fields(row,dict(status='PASS',real_Auth_HTTP=True,invoice_settled=False,actual_Native_case_credit=0,
            actual_two_session_case_credit=0,actual_browser_case_credit=0),'MANDOR_HTTP_ACTUAL_REAL_AUTH_CASE')
        proofs=row['complete_census_proofs']
        scopes=[set(),access_cases.ALLOCATION_TABLES,set(),access_cases.ALLOCATION_TABLES,set()]if index==0 else[
            access_cases.ALLOCATION_TABLES,{'erp.app_users','erp.audit_logs','sequence:erp.audit_logs_id_seq'},set()]
        require(len(proofs)==len(scopes),'MANDOR_HTTP_ALL_POSITIVE_AND_REFUSAL_ORIGINALS')
        pairs=[]
        for proof,allowed in zip(proofs,scopes):
            record,before,after=access_gate.observation(p,directory,proof,allowed)
            if pairs:p.exact(pairs[-1][1],before,'MANDOR_HTTP_CONTIGUOUS_ACTUAL_OBSERVATIONS')
            pairs.append((before,after));originals.append(record)
        if index==0:
            before,held=pairs[1]
            access_gate.allocation(p,before,held,dict(first=row['first'],retry=dict(ok=True,reply=row['replay']),
                changed_intent_refusal=dict(ok=False,sqlstate=row['changed_intent_refusal']['body']['code'],
                    message=row['changed_intent_refusal']['body']['message'])),True)
            for key in('stale_refusal','other_actor_same_UUID_refusal'):
                http_cases.denied(row[key],'CP7_MANDOR_SHOP_REVIEW_CHANGED','P0001')
            for key in('warehouse_read_refusal','warehouse_write_refusal'):
                http_cases.denied(row[key],'CP7_MANDOR_SHOP_ACCESS_DENIED','42501')
            require(row['anonymous_status']>=400,'MANDOR_HTTP_ANONYMOUS_DENIAL')
            _,released=pairs[3]
            p.exact(released['deductions'],before['deductions'],'MANDOR_HTTP_RELEASE_REMOVES_EXACT_DEDUCTION')
            require(Decimal(released['payroll'][1])==Decimal('2000000.00'),'MANDOR_HTTP_RELEASE_RESTORES_EXACT_NET')
            selected=[r for r in released['allocation_states']if r['allocation_id']==row['first']['allocation_id']]
            require(len(selected)==1 and selected[0]['state']=='RELEASED','MANDOR_HTTP_LINKED_RELEASE_STATE')
        else:
            access_gate.revocation(p,*pairs[1])
            http_cases.denied(row['pending_revocation'],'could not obtain lock on relation "app_users"','55P03')
            require(0<=row['pending_elapsed']<3,'MANDOR_HTTP_PROMPT_PENDING_ACCESS_REFUSAL')
            for key in('committed_revocation','revoked_read_refusal'):
                http_cases.denied(row[key],'CP7_MANDOR_SHOP_ACCESS_DENIED','42501')
            p.fields(row,dict(original_Auth_token_used_after_app_access_revocation=True,
                fixture_actor_restored_by_copy_disposal=True),'MANDOR_HTTP_CURRENT_ACCESS_AFTER_AUTH_LOGIN')
    require(len({r['name']for r in originals})==8,'MANDOR_HTTP_EIGHT_DISTINCT_ORIGINALS')
    return dict(status='ACTUAL_MANDOR_HTTP2_AND_COMPLETE_AUTH_COPY_RESTORATION',actual_Auth_HTTP_cases=2,
        original_observations=originals,primary_Auth_counts_restored=True,actual_Native_case_credit=0,
        actual_two_session_case_credit=0,actual_browser_cases=0)
