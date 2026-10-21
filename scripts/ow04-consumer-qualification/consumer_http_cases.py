"""Bounded real Auth/PostgREST consumer commands; declarations are not passes.

Only genuine Auth sessions send the financial consumer RPCs. Native setup uses
the accepted disposable stock/sale/payment/initial-return writers, with exact
fixture-only ERP schema ACL restoration before the HTTP request begins.
"""
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import copy
import json
import uuid

import native_basic_cases as basic
import native_refund_cases as refund
import cp7_ow04_http_cases as retained_http

fixture,native=basic.fixture,basic.native
QUOTE='erp_cp7_get_customer_credit_review_v1'
COMMAND='erp_cp7_customer_credit_command_v1'
IDS=tuple('OW04_CONSUMER_HTTP_'+name for name in (
 'APPLY_COMMIT_REPLAY','REFUND_COMMIT_REPLAY','APPLY_NAMED_UNDO_REPLAY','REFUND_NAMED_UNDO_REPLAY',
 'CHANGED_REQUEST_REFUSAL','STALE_REVIEW_REFUSAL','ANON_REFUSAL','REVOKED_FRESH_REPLAY_REFUSAL',
 'RESERVED_BOOK_DATE_REFUSAL','UNDO_AMOUNT_REFUSAL','SECOND_UNDO_REFUSAL','NON_OWNER_REFUND_REFUSAL',
 'OVERDRAW_ATOMIC_REFUSAL','INITIAL_REFUND_NAMED_UNDO_REPLAY'))
assert len(IDS)==len(set(IDS))==14
EXPECTED_SHA256='92778955ab1ac7d6947797f01a3abe366437918bc1b0dfb0477dbd54982b5081'


def expected():
    raw=Path(__file__).with_name('HTTP_EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256,'CONSUMER_HTTP_EXPECTATIONS_CHANGED'
    value=json.loads(raw)
    assert value['classification']=='PREDECLARED_REAL_AUTH_HTTP_CASES_NOT_EXECUTED_NOT_INDEPENDENT_ACCEPTANCE'
    assert value['expected_count']==len(IDS)==14 and tuple(value['required_case_ids'])==IDS
    assert value['original_frozen_nine_sha256']==fixture.EXPECTED_SHA256
    assert value['frozen_refund_nine_sha256']==refund.EXPECTED_SHA256
    return value


snapshot=retained_http.snapshot
response=retained_http.response


def prepared(http,today,mode='CREDIT'):
    with http.connect()as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        before=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        pair=fixture.prepare(cur,today,mode)
        native.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==before
        conn.commit()
    return pair


def profiles(http,pair):
    with http.connect()as conn,conn.cursor()as cur:
        answer=fixture.profiles(cur,pair);conn.rollback()
    return answer


def payload(pair,action='APPLY',amount='80.00',original=None):
    p=basic.payload(pair,action,amount,original)
    if action=='REFUND':p['cash_account_id']=str(pair['source']['f']['bank'])
    return p


def quoted(http,user,p):
    before=snapshot(http)
    q=response(user.rpc(QUOTE,dict(p_payload=copy.deepcopy(p))))
    assert snapshot(http)==before,'CONSUMER_HTTP_REVIEW_CHANGED_BUSINESS_STATE'
    assert q['contract_version']=='cp7.customer-credit-review.v1'and q['read_only']is True
    assert len(q['quote_sha256'])==64 and q['expected_versions']
    return dict(p_payload={**p,'quote_sha256':q['quote_sha256']},p_expected_versions=q['expected_versions'])


def committed(http,user,envelope,request=None):
    request=request or uuid.uuid4();args={**copy.deepcopy(envelope),'p_request':str(request)}
    result=response(user.rpc(COMMAND,args))
    assert result['kind']=='COMMITTED_OUTCOME'and result['request_id']==str(request)
    with http.connect()as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        # The actual HTTP login owns this receipt, not the SQL fixture actor.
        row=cur.execute('select action,payload,expected_versions,response from cp7_credit.consumer_requests_v1 where actor=%s and request_id=%s',
                         (user.auth_user_id,request)).fetchone()
        assert row==(args['p_payload']['action'],args['p_payload'],args['p_expected_versions'],result)
        operation=cur.execute('select actor,request_id,actor_app_user_id,id from cp7_credit.consumer_operations_v1 where id=%s',
                              (result['operation_id'],)).fetchone()
        assert str(operation[0])==str(user.auth_user_id)and str(operation[1])==str(request)
        assert operation[2]==cur.execute('select id from erp.app_users where auth_user_id=%s',(user.auth_user_id,)).fetchone()[0]
        event=cur.execute('select actor,request_id,amount,journal_id from cp7_credit.consumption_events where id=%s',
                          (result['consumption_event_id'],)).fetchone()
        assert str(event[0])==str(user.auth_user_id)and str(event[1])==str(request)
        assert event[2]==Decimal(result['amount'])and str(event[3])==result['journal_id']
        cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(result['operation_id'],))
        conn.rollback()
    return result,args


def replay(http,user,args,result):
    before=snapshot(http)
    assert response(user.rpc(COMMAND,copy.deepcopy(args)))==result
    assert snapshot(http)==before,'CONSUMER_HTTP_COMMITTED_REPLAY_CREATED_ANOTHER_EFFECT'


def refused(http,user,args,code,status=400):
    before=snapshot(http)
    denied=response(user.rpc(COMMAND,copy.deepcopy(args)),status,code)
    assert snapshot(http)==before,'CONSUMER_HTTP_REFUSAL_CHANGED_NATIVE_OR_PRIVATE_STATE'
    return denied


def http_cases(http,today):
    expected()
    users={}
    def owner():
        if 'owner'not in users:users['owner']=http.login('OWNER',label='ow04-consumer-owner')
        return users['owner']
    def apply(user,pair,amount='80.00',action='APPLY'):
        return committed(http,user,quoted(http,user,payload(pair,action,amount)))
    def base_commit(action):
        user=owner();pair=prepared(http,today);result,args=apply(user,pair,action=action)
        replay(http,user,args,result)
        gold=basic.GOLD['cases'][0]['expected']if action=='APPLY'else refund.GOLD['cases'][0]['expected']
        assert profiles(http,pair)==gold
        return dict(status='PASS',actual_Auth_HTTP=True,actual_login_actor_proven=True,committed_replay_one_effect=True,
                    expected=gold,observed=profiles(http,pair))
    def undo(action,second=False):
        user=owner();pair=prepared(http,today);first,_=apply(user,pair,action=action);apply(user,pair,'120.00',action)
        e=quoted(http,user,payload(pair,'UNDO',original=first['consumption_event_id']))
        result,args=committed(http,user,e);replay(http,user,args,result)
        if second:refused(http,user,{**args,'p_request':str(uuid.uuid4())},'CP7_CREDIT_CONSUMER_ORIGINAL_ALREADY_UNDONE')
        gold=basic.GOLD['cases'][3]['expected']if action=='APPLY'else refund.GOLD['cases'][3]['expected']
        assert profiles(http,pair)==gold
        return dict(status='PASS',actual_Auth_HTTP=True,exact_named_undo=True,committed_replay_one_effect=True,
                    second_undo_refused=second,expected=gold,observed=profiles(http,pair))
    def changed():
        user=owner();pair=prepared(http,today);result,args=apply(user,pair);replay(http,user,args,result)
        changed=copy.deepcopy(args);changed['p_payload']['reason']+=' diubah'
        refused(http,user,changed,'CP7_CREDIT_CONSUMER_REQUEST_CHANGED')
        return dict(status='PASS',exact_original_request_payload_required=True,no_partial_effect=True)
    def stale():
        user=owner();pair=prepared(http,today)
        a=quoted(http,user,payload(pair));b=quoted(http,user,payload(pair,amount='120.00'))
        committed(http,user,a)
        refused(http,user,{**b,'p_request':str(uuid.uuid4())},'CP7_CREDIT_CONSUMER_REVIEW_CHANGED')
        assert profiles(http,pair)==basic.GOLD['cases'][0]['expected']
        return dict(status='PASS',stale_source_target_review_refused=True,no_partial_effect=True)
    def anonymous():
        user=owner();pair=prepared(http,today);p=payload(pair);e=quoted(http,user,p);before=snapshot(http)
        for name,args in((QUOTE,dict(p_payload=p)),(COMMAND,{**e,'p_request':str(uuid.uuid4())})):
            answer=http.anon_rpc(name,args);assert answer['status']in(401,403),answer
        assert snapshot(http)==before
        return dict(status='PASS',anonymous_review_and_write_denied=True,no_partial_effect=True)
    def revoked():
        user=owner();pair=prepared(http,today);result,args=apply(user,pair)
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
        try:
            for request in(args,{**args,'p_request':str(uuid.uuid4())}):
                refused(http,user,request,'CP7_SALES_ACCESS_DENIED',403)
        finally:
            with http.connect()as conn,conn.cursor()as cur:
                cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
        replay(http,user,args,result)
        return dict(status='PASS',actual_ERP_membership_revoked=True,fresh_and_replay_denied=True,no_partial_effect=True)
    def reserved():
        user=owner();pair=prepared(http,today);e=quoted(http,user,payload(pair));e['p_payload']['book_date']=str(today)
        refused(http,user,{**e,'p_request':str(uuid.uuid4())},'CP7_CREDIT_CONSUMER_PAYLOAD_FIELDS')
        return dict(status='PASS',client_book_date_refused=True,no_partial_effect=True)
    def undo_amount():
        user=owner();pair=prepared(http,today);first,_=apply(user,pair)
        e=quoted(http,user,payload(pair,'UNDO',original=first['consumption_event_id']))
        e['p_payload']['amount']='-1.00'
        refused(http,user,{**e,'p_request':str(uuid.uuid4())},'CP7_CREDIT_CONSUMER_UNDO_NAMES_ORIGINAL_ONLY')
        return dict(status='PASS',partial_or_arbitrary_negative_undo_refused=True,no_partial_effect=True)
    def non_owner():
        user=owner();pair=prepared(http,today);e=quoted(http,user,payload(pair,'REFUND'))
        # Explicit disposable role-policy fixture. Retain a genuine STAFF role
        # and all OWNER permission keys, so Native's OWNER/ADMIN role predicate
        # itself must refuse cash-out. No JWT or role claim is fabricated.
        with http.connect()as conn,conn.cursor()as cur:
            row=cur.execute("select id,is_active from erp.app_roles where role_code='STAFF'").fetchone()
            if row is None:
                role=uuid.uuid4();cur.execute("insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active)values(%s,'STAFF','Disposable consumer non-owner',false,false,true)",(role,))
            else:
                role=row[0];cur.execute('update erp.app_roles set is_active=true where id=%s',(role,))
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            cur.execute("insert into erp.app_role_permissions(role_id,permission_key)select %s,p.permission_key from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id where r.role_code='OWNER'",(role,))
            conn.commit()
        staff=http.login('STAFF',label='ow04-consumer-non-owner')
        quoted(http,staff,payload(pair))
        before=snapshot(http)
        response(staff.rpc(QUOTE,dict(p_payload=payload(pair,'REFUND'))),400,'OWNER or ADMIN access required')
        assert snapshot(http)==before
        refused(http,staff,{**e,'p_request':str(uuid.uuid4())},'OWNER or ADMIN access required')
        return dict(status='PASS',real_STAFF_with_all_permission_keys=True,same_user_apply_quote_succeeded=True,
                    Native_owner_guard_refused_refund=True,no_partial_effect=True)
    def overdraw():
        user=owner();pair=prepared(http,today);first=quoted(http,user,payload(pair));committed(http,user,first)
        apply(user,pair,'120.00');bad=copy.deepcopy(first);bad['p_payload']['amount']='0.01'
        denied=refused(http,user,{**bad,'p_request':str(uuid.uuid4())},'CP7_CREDIT_CONSUMER_INSUFFICIENT_DATED_SOURCE_CAPACITY')
        assert denied['code']=='P0001'
        assert profiles(http,pair)==basic.GOLD['cases'][2]['expected']
        return dict(status='PASS',one_cent_overdraw_refused_atomically=True,observed=profiles(http,pair))
    def initial_refund_undo():
        user=owner();pair=prepared(http,today,'REFUND')
        e=quoted(http,user,payload(pair,'UNDO',original=pair['initial_result']['refund_event_id']))
        result,args=committed(http,user,e);replay(http,user,args,result)
        gold=refund.GOLD['cases'][7]['expected'];assert profiles(http,pair)==gold
        return dict(status='PASS',actual_initial_refund_named_undo=True,committed_replay_one_effect=True,expected=gold,observed=profiles(http,pair))
    operations=(lambda:base_commit('APPLY'),lambda:base_commit('REFUND'),lambda:undo('APPLY'),lambda:undo('REFUND'),
                changed,stale,anonymous,revoked,reserved,undo_amount,lambda:undo('APPLY',True),non_owner,overdraw,initial_refund_undo)
    assert len(operations)==len(IDS)
    return list(zip(IDS,operations))
