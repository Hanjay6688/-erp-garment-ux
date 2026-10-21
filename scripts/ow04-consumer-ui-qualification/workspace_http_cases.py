"""Four declared actual Auth workspace/read/continuation cases; not execution.

Retain the qualified financial commands and exact literal money expectations.
Every workspace read is bracketed by a complete fresh Native/private snapshot.
"""
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
import copy
import json
import uuid

import consumer_http_cases as business

fixture,native=business.fixture,business.native
EXPECTED_SHA256='cd8eef92f46b10dbf746125c1c7dccc87fdfb907992809154f5a41a2317927c8'
IDS=('OW04_CONSUMER_WORKSPACE_FRESH_READONLY_PAGES','OW04_CONSUMER_WORKSPACE_APPLY_NAMED_UNDO_HISTORY',
     'OW04_CONSUMER_WORKSPACE_INITIAL_REFUND_UNDO_HISTORY','OW04_CONSUMER_WORKSPACE_ACCESS_STALE_AND_PAGE_LEASE_REFUSALS')
BROWSER_IDS=('OW04_CONSUMER_BROWSER_APPLY_LOST_REPLY_DESKTOP','OW04_CONSUMER_BROWSER_REFUND_MOBILE',
             'OW04_CONSUMER_BROWSER_INITIAL_REFUND_UNDO_MOBILE','OW04_CONSUMER_BROWSER_REVOKED_PENDING_REPLAY')
WORKSPACE='erp_cp7_get_customer_credit_workspace_v1'


def expected():
    raw=Path(__file__).with_name('EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256
    value=json.loads(raw)
    assert value['classification']=='PREDECLARED_CONSUMER_WORKSPACE_AUTH_AND_PRODUCT_BROWSER_NOT_EXECUTED'
    assert tuple(value['http_case_ids'])==IDS and tuple(value['browser_case_ids'])==BROWSER_IDS
    assert value['original_nine_sha256']==fixture.EXPECTED_SHA256
    assert value['refund_nine_sha256']==business.refund.EXPECTED_SHA256
    assert value['initial_credit']==value['after_named_full_undo']==fixture.INITIAL
    assert value['after_apply80']==business.basic.GOLD['cases'][0]['expected']
    assert value['after_refund80']==business.refund.GOLD['cases'][0]['expected']
    return value


def source_query(http,pair,kind,q='',offset=0,dataset=None):
    with http.connect()as conn,conn.cursor()as cur:
        row=cur.execute('select row_version::text,cp7_sales.review_token(id)from erp.sales_headers where id=%s',
                        (pair['source']['f']['sale'],)).fetchone()
        conn.rollback()
    return dict(kind=kind,sale_id=str(pair['source']['f']['sale']),expected_version=row[0],review_token=row[1],
                q=q,offset=offset,limit=25,dataset_sha256=dataset)


def page(http,user,pair,kind,q=''):
    query=source_query(http,pair,kind,q)
    before=business.snapshot(http)
    result=business.response(user.rpc(WORKSPACE,dict(p_query=copy.deepcopy(query))))
    assert business.snapshot(http)==before,'CONSUMER_WORKSPACE_READ_CHANGED_NATIVE_OR_PRIVATE_STATE'
    assert result['contract_version']=='cp7.customer-credit-workspace.v1'
    assert result['actor_scope_id']==str(user.auth_user_id)and result['read_only']and result['business_DML']is False
    assert result['kind']==kind and result['q']==q and len(result['dataset_sha256'])==64
    for key in ('sale_id','row_version','review_token'):
        assert result['source'][key]==query[{'row_version':'expected_version'}.get(key,key)]
    assert result['source']['customer_id']==str(pair['source']['f']['customer'])
    rows=result['page'];assert rows['offset']==0 and rows['limit']==25
    assert len(rows['rows'])==min(25,int(rows['total']))
    return result,query


def bank(http,pair):
    with http.connect()as conn,conn.cursor()as cur:
        row=cur.execute('select id::text,cash_account_code,cash_account_name from erp.cash_accounts where id=%s',
                        (pair['source']['f']['bank'],)).fetchone()
        conn.rollback();return row


def target_number(http,pair):
    with http.connect()as conn,conn.cursor()as cur:
        value=cur.execute('select sale_number from erp.sales_headers where id=%s',(pair['target']['sale'],)).fetchone()[0]
        conn.rollback();return value


def assert_current(http,user,pair,available,target_ar,event_amounts):
    cohort,_=page(http,user,pair,'COHORTS')
    assert cohort['page']['total']=='1'
    row=cohort['page']['rows'][0]
    assert row['id']==str(pair['initial_result']['credit_id'])and row['return_id']==str(pair['initial_result']['return_id'])
    assert row['available_credit']==available
    target,_=page(http,user,pair,'TARGETS',target_number(http,pair))
    assert target['page']['total']=='1'
    assert target['page']['rows'][0]['id']==str(pair['target']['sale'])
    assert target['page']['rows'][0]['customer_id']==str(pair['source']['f']['customer'])
    assert target['page']['rows'][0]['open_balance']==target_ar
    events,_=page(http,user,pair,'EVENTS')
    assert events['page']['total']==str(len(event_amounts))
    assert sorted(r['amount']for r in events['page']['rows'])==sorted(event_amounts)
    return dict(source_available=available,target_AR=target_ar,history=events['page']['rows'])


def http_cases(http,today):
    gold=expected();users={}
    def owner():
        if 'owner'not in users:users['owner']=http.login('OWNER',label='ow04-consumer-workspace-owner')
        return users['owner']
    def fresh():
        user=owner();pair=business.prepared(http,today)
        assert business.profiles(http,pair)==gold['initial_credit']
        actual=assert_current(http,user,pair,'200.00','500.00',[])
        cash,_=page(http,user,pair,'CASH',bank(http,pair)[1])
        assert cash['page']['total']=='1'and cash['page']['rows'][0]['id']==bank(http,pair)[0]
        return dict(status='PASS',real_Auth_HTTP=True,all_four_fresh_pages_readonly=True,actual=actual,
                    exact_before=gold['initial_credit'],no_native_or_private_DML=True)
    def apply_undo():
        user=owner();pair=business.prepared(http,today)
        p=business.payload(pair)
        first,args=business.committed(http,user,business.quoted(http,user,p));business.replay(http,user,args,first)
        day=str(datetime.fromisoformat(p['physical_at']).astimezone(ZoneInfo('Asia/Jakarta')).date())
        assert first['economic_date']==first['transaction_date']==day
        assert business.profiles(http,pair)==gold['after_apply80']
        after=assert_current(http,user,pair,'120.00','420.00',['80.00'])
        undo,args=business.committed(http,user,business.quoted(http,user,business.payload(pair,'UNDO',original=first['consumption_event_id'])))
        business.replay(http,user,args,undo)
        assert undo['restores_event_id']==first['consumption_event_id']and undo['amount']=='-80.00'
        assert business.profiles(http,pair)==gold['after_named_full_undo']
        final=assert_current(http,user,pair,'200.00','500.00',['80.00','-80.00'])
        original=next(r for r in final['history']if r['id']==first['consumption_event_id'])
        inverse=next(r for r in final['history']if r['id']==undo['consumption_event_id'])
        assert original['undone_by']==inverse['id']and original['restores_event_id']is None
        assert inverse['restores_event_id']==original['id']and inverse['undone_by']is None
        return dict(status='PASS',real_Auth_HTTP=True,after_apply=after,after_named_undo=final,
                    exact_frozen_finances=True,original_and_signed_inverse_retained=True)
    def initial_refund_undo():
        user=owner();pair=business.prepared(http,today,'REFUND')
        assert_current(http,user,pair,'0.00','500.00',['200.00'])
        event=pair['initial_result']['refund_event_id']
        result,args=business.committed(http,user,business.quoted(http,user,business.payload(pair,'UNDO',original=event)))
        business.replay(http,user,args,result)
        assert result['restores_event_id']==str(event)and result['amount']=='-200.00'
        assert business.profiles(http,pair)==gold['after_named_full_undo']
        actual=assert_current(http,user,pair,'200.00','500.00',['200.00','-200.00'])
        return dict(status='PASS',real_Auth_HTTP=True,actual=actual,exact_initial_refund_full_undo=True,
                    original_cash_account_restored=True,exact_frozen_finances=True)
    def refusals():
        user=owner();pair=business.prepared(http,today);_,query=page(http,user,pair,'COHORTS')
        before=business.snapshot(http)
        anon=http.anon_rpc(WORKSPACE,dict(p_query=query));assert anon['status']in(401,403)
        business.response(user.rpc(WORKSPACE,dict(p_query={**query,'book_date':str(today)})),400,'CP7_CREDIT_WORKSPACE_QUERY_INVALID')
        business.response(user.rpc(WORKSPACE,dict(p_query={**query,'offset':25})),400,'CP7_CREDIT_WORKSPACE_QUERY_INVALID')
        assert business.snapshot(http)==before
        old,old_query=page(http,user,pair,'COHORTS')
        business.committed(http,user,business.quoted(http,user,business.payload(pair)))
        before=business.snapshot(http)
        business.response(user.rpc(WORKSPACE,dict(p_query=old_query)),400,'CP7_CREDIT_WORKSPACE_SOURCE_CHANGED')
        next_query=source_query(http,pair,'COHORTS',offset=25,dataset=old['dataset_sha256'])
        business.response(user.rpc(WORKSPACE,dict(p_query=next_query)),400,'CP7_CREDIT_WORKSPACE_LIST_CHANGED')
        assert business.snapshot(http)==before
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
        try:
            before=business.snapshot(http)
            business.response(user.rpc(WORKSPACE,dict(p_query=source_query(http,pair,'EVENTS'))),403,'CP7_SALES_ACCESS_DENIED')
            assert business.snapshot(http)==before
        finally:
            with http.connect()as conn,conn.cursor()as cur:
                cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
        return dict(status='PASS',real_Auth_HTTP=True,anonymous_and_real_revocation_denied=True,
                    exact_source_and_all_row_page_lease_required=True,caller_extra_field_refused=True,no_business_or_private_DML_on_refusal=True)
    return list(zip(IDS,(fresh,apply_undo,initial_refund_undo,refusals)))
