"""Real-Auth HTTP cases. No connection or case execution on import.

Retains the actual14 consumer cases and adds the two already-frozen monetary
corrections. The eventual transport admission must bind actual Native20 first.
"""
from copy import deepcopy
from pathlib import Path
import json
import uuid

import consumer_http_cases as credit

READ='erp_cp7_get_sales_payment_correction_v1'
COMMAND='erp_cp7_correct_sales_payment_v1'
NEW_IDS=('OW04_PAYMENT_SOURCE_HTTP_ACTIVE_APPLY80_CORRECT_REPLAY_REVOKE',
         'OW04_PAYMENT_SOURCE_HTTP_ACTIVE_REFUND80_CORRECT_REPLAY_REVOKE')
IDS=credit.IDS+NEW_IDS
assert len(IDS)==len(set(IDS))==16
GOLD_PATH=Path(__file__).resolve().parent.parent/'ow04-payment-source-qualification/EXPECTED.json'


def correction_review(http,user,pair):
    f=pair['source']['f'];before=credit.snapshot(http)
    workspace=credit.response(user.rpc(READ,dict(p_query=dict(sale_id=str(f['sale']),payment_id=str(f['payment'])))))
    assert credit.snapshot(http)==before
    assert workspace['eligible']and workspace['document']['status']=='POSTED'
    d=workspace['document']
    payload=dict(sale_id=str(f['sale']),payment_id=str(f['payment']),review_token=workspace['review_token'],
        change_reason='Koreksi nominal setelah pemakaian kredit diperiksa di lapangan',
        replacement=dict(payment_number=d['number'],payment_date=d['physical_at'],amount='900.00',
            cash_account_id=d['cash_account_id'],payment_method=d['method'],reference_number=d['reference'],notes=d['notes']))
    return dict(p_payload=payload,p_expected=workspace['row_version'],p_request=str(uuid.uuid4()))


def refused_unchanged(http,user,args,code,status=400):
    before=credit.snapshot(http)
    answer=credit.response(user.rpc(COMMAND,deepcopy(args)),status,code)
    assert credit.snapshot(http)==before,'CORRECTION_HTTP_REFUSAL_CHANGED_NATIVE_OR_PRIVATE_STATE'
    return answer


def one_case(http,today,index):
    gold=json.loads(GOLD_PATH.read_bytes())['positive'][index]
    user=http.login('OWNER',label='payment-source-http-'+gold['action'].lower())
    pair=credit.prepared(http,today)
    first,consumer_args=credit.committed(http,user,credit.quoted(http,user,credit.payload(pair,gold['action'],'80.00')))
    assert credit.profiles(http,pair)==gold['before']
    args=correction_review(http,user,pair)
    result=credit.response(user.rpc(COMMAND,deepcopy(args)))
    assert result['action']=='PAYMENT_CORRECT'and result['kind']=='COMMITTED_OUTCOME'
    assert result['request_id']==args['p_request']and result['original_payment_status']=='REVERSED'
    assert credit.profiles(http,pair)==gold['after']
    with http.connect()as conn,conn.cursor()as cur:
        credit.native.b.api.admin(cur)
        actual=cur.execute('select payload,expected_version,response from cp7_payment_correction.requests where actor=%s and request_id=%s',
            (user.auth_user_id,args['p_request'])).fetchone()
        assert actual==(args['p_payload'],args['p_expected'],result)
        operation=cur.execute("select operation_id,actor,request_id from cp7_credit.source_operation_materializations_v1 where action='PAYMENT_CORRECT'and actor=%s and request_id=%s",
            (user.auth_user_id,args['p_request'])).fetchone()
        assert str(operation[1])==str(user.auth_user_id)and str(operation[2])==args['p_request']
        cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(operation[0],))
        conn.rollback()
    before=credit.snapshot(http)
    assert credit.response(user.rpc(COMMAND,deepcopy(args)))==result
    assert credit.snapshot(http)==before,'CORRECTION_HTTP_REPLAY_CREATED_EFFECTS'
    credit.replay(http,user,consumer_args,first)
    assert credit.snapshot(http)==before,'OLD_CONSUMER_RECEIPT_REPLAY_AFTER_CORRECTION_CREATED_EFFECTS'
    changed=deepcopy(args);changed['p_payload']['replacement']['amount']='899.99'
    refused_unchanged(http,user,changed,'CP7_SALES_REQUEST_CHANGED')
    stale=deepcopy(args);stale['p_request']=str(uuid.uuid4())
    refused_unchanged(http,user,stale,'CP7_SALES_REVIEW_CHANGED')
    before=credit.snapshot(http)
    for name,p in ((READ,dict(p_query=dict(sale_id=args['p_payload']['sale_id'],payment_id=result['payment_id']))),(COMMAND,args)):
        answer=http.anon_rpc(name,deepcopy(p));assert answer['status']in(401,403),answer
    assert credit.snapshot(http)==before
    with http.connect()as conn,conn.cursor()as cur:
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,))
        assert cur.rowcount==1;conn.commit()
    try:
        refused_unchanged(http,user,args,'CP7_SALES_ACCESS_DENIED',403)
        refused_unchanged(http,user,stale,'CP7_SALES_ACCESS_DENIED',403)
    finally:
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(user.auth_user_id,))
            assert cur.rowcount==1;conn.commit()
    before=credit.snapshot(http)
    assert credit.response(user.rpc(COMMAND,deepcopy(args)))==result
    assert credit.snapshot(http)==before
    assert credit.profiles(http,pair)==gold['after']
    return dict(status='PASS',actual_Auth_and_PostgREST=True,actual_login_owns_correction_and_source_operation=True,
        exact_replay_zero_effects=True,old_consumer_receipt_replay_zero_effects=True,changed_UUID_payload_and_stale_refused=True,
        anonymous_read_and_write_denied=True,actual_revoked_ERP_member_fresh_and_replay_denied=True,
        expected=gold['after'],observed=credit.profiles(http,pair),production_go=False)


def http_cases(http,today):
    return credit.http_cases(http,today)+[(name,lambda index=index:one_case(http,today,index))for index,name in enumerate(NEW_IDS)]
