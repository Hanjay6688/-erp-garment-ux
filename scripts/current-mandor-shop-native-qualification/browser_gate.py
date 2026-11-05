"""Resolve real browser observations, screenshots and complete Auth cleanup."""
from decimal import Decimal
from hashlib import sha256
from pathlib import PurePosixPath
import gzip,importlib.util,json,re,struct
import access_cases,access_gate,access_runtime,browser_preflight


def require(value,message):
    if not value:raise ValueError(message)


def pinned(p,directory,reference,expected_name):
    p.exact(reference['name'],expected_name,'MANDOR_BROWSER_EXACT_INPUT_NAME')
    path=directory/expected_name;require(not path.is_symlink(),'MANDOR_BROWSER_NO_ORIGINAL_SYMLINK')
    return p.pinned(path.read_bytes(),{k:reference[k]for k in('bytes','sha256')},'MANDOR_BROWSER_EXACT_OWNING_ORIGINAL')


def snapshot(p,directory,reference,state):
    name=reference['name']
    require(type(name)is str and re.fullmatch(r'MANDOR_(DESKTOP|MOBILE390)_[A-Z0-9_]+_FULL_CENSUS\.json\.gz',name),
        'MANDOR_BROWSER_FIXED_RAW_CENSUS_PATH')
    path=directory/name;require(not path.is_symlink(),'MANDOR_BROWSER_NO_CENSUS_SYMLINK')
    packed=path.read_bytes();p.exact(dict(bytes=len(packed),sha256=sha256(packed).hexdigest()),
        dict(bytes=reference['gzip_bytes'],sha256=reference['gzip_sha256']),'MANDOR_BROWSER_PACKED_ORIGINAL')
    value=p.pinned(gzip.decompress(packed),{k:reference[k]for k in('bytes','sha256')},'MANDOR_BROWSER_COMPLETE_RAW_ORIGINAL')
    p.exact(set(value),{'actual_all22','full_data_and_sequences','actor','actor_audits','invoice',
        'allocation_states','requests','deductions','payroll'},'MANDOR_BROWSER_COMPLETE_OBSERVATION_KEYS')
    p.exact(set(value['actual_all22']),access_gate.ALL22,'MANDOR_BROWSER_EXACT22_NAMES')
    p.exact(value['actual_all22'],state['after'],'MANDOR_BROWSER_ALL22_MATCHES_OWNING_INSTALLATION')
    require(any(k.startswith('sequence:')for k in value['full_data_and_sequences']),
        'MANDOR_BROWSER_ALL_SEQUENCES_REQUIRED')
    return value


def pair(p,directory,proof,state,allowed):
    p.fields(proof,dict(status='PASS',allowed_tables=sorted(allowed)),'MANDOR_BROWSER_EXACT_OBSERVATION_SCOPE')
    before=snapshot(p,directory,proof['original_before'],state)
    after=snapshot(p,directory,proof['original_after'],state)
    for key in('actual_all22','actor','actor_audits','invoice'):
        p.exact(before[key],after[key],'MANDOR_BROWSER_UNCHANGED_AUTHORITY_AND_INVOICE:'+key)
    left,right=before['full_data_and_sequences'],after['full_data_and_sequences']
    p.exact(set(left),set(right),'MANDOR_BROWSER_COMPLETE_DATA_AND_SEQUENCE_UNIVERSE')
    changed=sorted(k for k in left if left[k]!=right[k])
    p.exact(changed,proof['changed_tables'],'MANDOR_BROWSER_ACTUAL_CHANGED_TABLES')
    require(set(changed)<=set(allowed),'MANDOR_BROWSER_UNDECLARED_FINANCIAL_WRITES')
    if not allowed:p.exact(before,after,'MANDOR_BROWSER_REAL_REPLAY_REFUSAL_NO_EFFECT')
    return before,after


def reservation(p,before,after,row):
    first,request=row['actual_first_reply'],row['actual_first_request']
    p.fields(first,dict(kind='COMMITTED_OUTCOME',request_id=request['p_request'],action='RESERVE',
        invoice_settled_by_this_command=False),'MANDOR_BROWSER_ACTUAL_RESERVATION_OUTCOME')
    p.exact(request['p_action'],'RESERVE','MANDOR_BROWSER_EXACT_FIRST_ACTION')
    require(Decimal(request['p_payload']['amount'])==Decimal('100000.00'),'MANDOR_BROWSER_REVIEWED_EXACT_CENTS')
    require(len(after['deductions'])==len(before['deductions'])+1 and Decimal(after['payroll'][1])==Decimal('1900000.00'),
        'MANDOR_BROWSER_ONE_ACTUAL_DEDUCTION_AND_EXACT_NET')
    old={r['allocation_id']:r for r in before['allocation_states']};new={r['allocation_id']:r for r in after['allocation_states']}
    p.exact(set(new),set(old)|{first['allocation_id']},'MANDOR_BROWSER_ONE_NEW_ALLOCATION')
    for key,value in old.items():p.exact(new[key],value,'MANDOR_BROWSER_OLD_ALLOCATION_HISTORY_UNCHANGED')
    p.fields(new[first['allocation_id']],dict(state='RESERVED'),'MANDOR_BROWSER_RESERVED_STATE')
    old={r['request_id']:r for r in before['requests']};new={r['request_id']:r for r in after['requests']}
    p.exact(set(new),set(old)|{first['request_id']},'MANDOR_BROWSER_ONE_IMMUTABLE_UUID_REQUEST')
    for key,value in old.items():p.exact(new[key],value,'MANDOR_BROWSER_OLD_REQUEST_HISTORY_UNCHANGED')
    p.fields(new[first['request_id']],dict(payload=request['p_payload'],response=first),'MANDOR_BROWSER_STORED_INTENT_AND_REPLY')


def gate(p,directory,part,frozen):
    actual=pinned(p,directory,part['browser2_original'],'MANDOR_BROWSER2_ORIGINAL.json')
    fixture=pinned(p,directory,part['browser_fixture_original'],'MANDOR_BROWSER_FIXTURE.json')
    state_io=access_runtime.load('mandor_final_complete_state_io',access_runtime.ROOT/'scripts/current-mandor-afui-preparation/state_io.py')
    state=state_io.verified(p,directory,part['browser_state_original'],part['browser_state_cache_original'])
    spec=importlib.util.spec_from_file_location('mandor_final_actual_browser_copy_gate',frozen/'scripts/cp7_accessory_nonpayable/qualification_gate.py')
    typed=importlib.util.module_from_spec(spec);spec.loader.exec_module(typed)
    result=typed.copies(actual,browser_preflight.IDS,mode='BROWSER')
    p.exact(result,part['browser2_gate'],'MANDOR_BROWSER_COMPLETE_TYPED_COPY_GATE')
    _,source=access_runtime.derive((frozen/access_runtime.ORIGINAL).read_bytes())
    copies=part['browser_copy_authority'];p.exact(copies['source'],source,'MANDOR_BROWSER_EXACT_COPY_AUTHORITY')
    require(len(copies['actual_copy_admissions'])==1,'MANDOR_BROWSER_ONE_COMPLETE_AUTH_COPY')
    p.fields(copies['actual_copy_admissions'][0],dict(all22_groups_equal_original_install=True,
        product_state_modified=False,Native_or_schema_or_RPC_permissions_changed=False),'MANDOR_BROWSER_PRODUCT_AUTHORITY_PRESERVED')
    assets={};screens=[]
    for index,name in enumerate(browser_preflight.IDS):
        row=actual['cases'][name]
        p.fields(row,dict(status='PASS',normal_App_menu=True,real_Auth=True,invoice_settled=False,
            product_responses_mocked=False,exact_future_payroll_id=fixture['payroll_id'],
            actual_Native_case_credit=0,actual_Auth_HTTP_case_credit=0,actual_two_session_case_credit=0),
            'MANDOR_BROWSER_REAL_APP_TRANSACTION_CASE')
        proofs=row['complete_census_proofs'];scopes=[set(),access_cases.ALLOCATION_TABLES,set(),access_cases.ALLOCATION_TABLES]
        require(len(proofs)==len(scopes),'MANDOR_BROWSER_COMPLETE_FOUR_OBSERVATION_PAIRS')
        pairs=[]
        for proof,allowed in zip(proofs,scopes):
            before,after=pair(p,directory,proof,state,allowed)
            if pairs:p.exact(pairs[-1][1],before,'MANDOR_BROWSER_CONTIGUOUS_ACTUAL_OBSERVATIONS')
            pairs.append((before,after))
            for key in('original_before','original_after'):
                ref=proof[key]
                if ref['name']in assets:p.exact(assets[ref['name']],ref,'MANDOR_BROWSER_SAME_ORIGINAL_REUSED_EXACTLY')
                assets[ref['name']]=ref
        before,held=pairs[1];reservation(p,before,held,row)
        released=pairs[3][1]
        p.exact(released['deductions'],before['deductions'],'MANDOR_BROWSER_RELEASE_REMOVES_EXACT_DEDUCTION')
        require(Decimal(released['payroll'][1])==Decimal('2000000.00'),'MANDOR_BROWSER_RELEASE_RETURNS_EXACT_NET')
        allocation=row['actual_first_reply']['allocation_id']
        selected=[r for r in released['allocation_states']if r['allocation_id']==allocation]
        require(len(selected)==1 and selected[0]['state']=='RELEASED','MANDOR_BROWSER_SAME_LINKED_ALLOCATION_RELEASED')
        p.fields(row['actual_release'],dict(status=200),'MANDOR_BROWSER_REAL_RELEASE_HTTP_SUCCESS')
        p.fields(row['actual_release']['body'],dict(allocation_id=allocation,action='RELEASE'),
            'MANDOR_BROWSER_EXACT_SAME_RELEASE_OUTCOME')
        if index==0:
            replay=row['journey']['exact_second_tab_replay']
            p.fields(replay,dict(status=200,body=row['actual_first_reply'],request=row['actual_first_request']),
                'MANDOR_BROWSER_LOST_REPLY_SAME_UUID_AND_INTENT')
            p.fields(row['journey'],dict(second_tab_new_input_removed=True),'MANDOR_BROWSER_PENDING_INPUT_RETIRED')
        else:
            stale=row['journey']['actual_stale_response']
            p.fields(stale,dict(status=400),'MANDOR_BROWSER_REAL_STALE_HTTP_ERROR')
            p.fields(stale['body'],dict(code='P0001',message='CP7_MANDOR_SHOP_REVIEW_CHANGED'),'MANDOR_BROWSER_ACTUAL_STALE_REFUSAL')
            p.fields(row['journey'],dict(stale_input_removed=True),'MANDOR_BROWSER_STALE_INPUT_RETIRED')
        require(row['console_evidence'],'MANDOR_BROWSER_CONSOLE_EVIDENCE_REQUIRED')
        for console in row['console_evidence']:
            p.fields(console,dict(unexpected_errors=[],page_errors=[]),'MANDOR_BROWSER_NO_UNEXPLAINED_CONSOLE_ERROR')
        widths=set()
        for visual in row['visuals']:
            size=visual['size'];widths.add(size['viewport'])
            require(size['width']<=size['viewport'],'MANDOR_BROWSER_NO_HORIZONTAL_OVERFLOW')
            contrast=visual['contrast']['rows'];require(contrast and all(r['ratio']>=4.5 for r in contrast),
                'MANDOR_BROWSER_ACTUAL_READABLE_OPAQUE_TEXT')
        p.exact(widths,{1440}if index==0 else{320,390,768},'MANDOR_BROWSER_EXACT_REVIEWED_WIDTHS')
        for name in row['screenshots']:
            parts=PurePosixPath(name).parts
            require(len(parts)==3 and parts[:2]==('cp6-proof','t3')and re.fullmatch(r'MANDOR_(DESKTOP|MOBILE390)_[A-Z0-9_]+\.png',parts[2]),
                'MANDOR_BROWSER_FIXED_SCREENSHOT_ORIGINAL')
            path=directory/parts[2];require(not path.is_symlink(),'MANDOR_BROWSER_NO_SCREENSHOT_SYMLINK')
            raw=path.read_bytes();require(raw[:8]==b'\x89PNG\r\n\x1a\n','MANDOR_BROWSER_REAL_PNG')
            width,height=struct.unpack('>II',raw[16:24]);require(width in widths and height>0,'MANDOR_BROWSER_SCREENSHOT_ACTUAL_DIMENSIONS')
            screens.append(dict(name=parts[2],bytes=len(raw),sha256=sha256(raw).hexdigest(),width=width,height=height))
    return dict(status='ACTUAL_MANDOR_BROWSER2_AND_COMPLETE_AUTH_COPY_RESTORATION',actual_browser_cases=2,
        original_observations=assets,screenshots=screens,primary_Auth_counts_restored=True,
        actual_Native_case_credit=0,actual_Auth_HTTP_case_credit=0,actual_two_session_case_credit=0)
