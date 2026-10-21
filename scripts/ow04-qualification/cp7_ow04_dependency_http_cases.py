"""Four real Auth/HTTP readonly controls on the complete owning installation."""
import copy
import re
import time

import cp7_ow04_http_cases as initial

RPC='erp_cp7_get_sales_credit_dependencies_v1'
IDS=(
    'OW04_HTTP_DEPENDENCY_REFUND_DOCUMENT',
    'OW04_HTTP_DEPENDENCY_CREDIT_PROVEN_EMPTY',
    'OW04_HTTP_DEPENDENCY_REVOKED_AND_ANON_DENIED',
    'OW04_HTTP_DEPENDENCY_STALE_AND_QUERY_REFUSED',
)


def fresh_query(http,f):
    with http.connect()as conn,conn.cursor()as cur:
        initial.nf.b.api.admin(cur)
        value=cur.execute("select jsonb_build_object('sale_id',id::text,"
            "'expected_version',row_version::text,'review_token',cp7_sales.review_token(id),"
            "'offset',0,'limit',25)from erp.sales_headers where id=%s",
            (f['x']['f']['sale'],)).fetchone()[0]
        conn.rollback()
    return value


def validate(user,f,committed,query,reply):
    assert set(reply)=={'contract_version','actor_scope_id','read_at','read_only',
        'business_DML','source','dependency_sha256','page','dependencies'}
    assert reply['contract_version']=='cp7.sales-credit-dependencies.v1'
    assert reply['actor_scope_id']==str(user.auth_user_id)
    assert reply['read_only'] is True and reply['business_DML'] is False
    assert re.fullmatch('[0-9a-f]{64}',reply['dependency_sha256'])
    assert reply['source']['sale_id']==str(f['x']['f']['sale'])
    assert reply['source']['row_version']==query['expected_version']==committed['outcome']['row_version']
    assert reply['source']['review_token']==query['review_token']
    refund=f['gold']['mode']=='REFUND'
    assert reply['page']==dict(offset=0,limit=25,total='1'if refund else'0',next_offset=None)
    if refund:
        assert len(reply['dependencies'])==1
        row=reply['dependencies'][0]
        assert row['event_id']==committed['outcome']['refund_event_id']
        assert row['kind']=='REFUND'and row['target_sale'] is None
        assert row['source_return_id']==committed['outcome']['return_id']
        assert row['source_sale_id']==str(f['x']['f']['sale'])
        assert row['source_sale_number']==reply['source']['number']
        assert row['source_return_number']==f['query']['return_payload']['return_number']
        assert row['amount']==f['gold']['current_credit_amount']==committed['quote']['current_credit_amount']
        pair=[f['x']['dates'][key]for key in f['gold']['refund_pair']]
        assert [row['economic_date'],row['book_date']]==pair
    else:
        assert reply['dependencies']==[]


def http_cases(http,today):
    def prepared(mode):
        user=http.login('OWNER',label='ow04-dependency-'+mode.lower())
        fixture=initial.prepared(http,today,paid='1000.00',profile='OPEN',mode=mode)
        committed=initial.committed(http,user,fixture)
        return user,fixture,committed,fresh_query(http,fixture)
    def positive(mode):
        user,fixture,committed,query=prepared(mode)
        before=initial.snapshot(http)
        started=time.perf_counter()
        reply=initial.response(user.rpc(RPC,dict(p_query=query)))
        milliseconds=(time.perf_counter()-started)*1000
        assert initial.snapshot(http)==before,'OW04_HTTP_DEPENDENCY_READ_CHANGED_BUSINESS'
        validate(user,fixture,committed,query,reply)
        return dict(status='PASS',real_Auth_HTTP=True,readonly_business_and_private_boundary=True,
            mode=mode,reply=reply,read_milliseconds=milliseconds,
            timing_scope='Single dependency read on disposable fixture, not whole ERP performance acceptance',
            production_go=False)
    def revoked():
        user,fixture,committed,query=prepared('REFUND')
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,))
            assert cur.rowcount==1
            conn.commit()
        try:
            before=initial.snapshot(http)
            initial.response(user.rpc(RPC,dict(p_query=query)),403,'CP7_SALES_ACCESS_DENIED')
            assert initial.snapshot(http)==before
            anonymous=http.anon_rpc(RPC,dict(p_query=query))
            assert anonymous['status']in(401,403),anonymous
            assert initial.snapshot(http)==before
        finally:
            with http.connect()as conn,conn.cursor()as cur:
                cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(user.auth_user_id,))
                assert cur.rowcount==1
                conn.commit()
        return dict(status='PASS',real_Auth_HTTP=True,current_actor_revocation_and_anon_denied=True,
                    no_partial_business_effect=True,production_go=False)
    def stale():
        user,fixture,committed,query=prepared('REFUND')
        variants=(
            ({**query,'review_token':'0'*32},'CP7_CREDIT_DEPENDENCY_SOURCE_CHANGED'),
            ({**query,'expected_version':str(int(query['expected_version'])+1)},'CP7_CREDIT_DEPENDENCY_SOURCE_CHANGED'),
            ({**query,'offset':1},'CP7_CREDIT_DEPENDENCY_QUERY_INVALID'),
            ({**query,'unexpected':True},'CP7_CREDIT_DEPENDENCY_QUERY_INVALID'),
        )
        for changed,message in variants:
            before=initial.snapshot(http)
            initial.response(user.rpc(RPC,dict(p_query=copy.deepcopy(changed))),400,message)
            assert initial.snapshot(http)==before
        return dict(status='PASS',real_Auth_HTTP=True,stale_revision_review_and_malformed_query_refused=True,
                    variants=len(variants),no_partial_business_effect=True,production_go=False)
    return [(IDS[0],lambda:positive('REFUND')),(IDS[1],lambda:positive('CREDIT')),
            (IDS[2],revoked),(IDS[3],stale)]
