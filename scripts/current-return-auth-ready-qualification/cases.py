"""Real Auth settlement/replay/inverse while an invalid sibling DRAFT remains."""
from copy import deepcopy
from decimal import Decimal
import uuid
import cp7_sales_return_cases as retained
import cp7_current_return_installation as installation

IDS=('CURRENT_RETURN_HTTP_BAD_DRAFT_GRADE_A','CURRENT_RETURN_HTTP_BAD_DRAFT_GRADE_B')
QUOTE='erp_cp7_get_sales_return_settlement_quote_v1'
SETTLE='erp_cp7_settle_sales_return_v1'
catalog=installation.catalog


def response(reply,status=200,message=None):
    assert reply['status']==status,reply
    if message is not None:assert reply['body']['message']==message,reply
    return reply['body']


def snapshot(http):
    with http.connect()as conn,conn.cursor()as cur:
        retained.b.api.admin(cur)
        result=dict(data=catalog._data(cur),catalog=catalog._catalog_rows(cur))
        conn.rollback();return result


def bad_draft(cur,rid):
    return dict(header=cur.execute('select to_jsonb(r)from erp.sales_returns r where id=%s',(rid,)).fetchone()[0],
        items=cur.execute('select to_jsonb(i)from erp.sales_return_items i where return_id=%s order by id',(rid,)).fetchall())


def fixture(http,today):
    with http.connect()as conn,conn.cursor()as cur:
        retained.b.api.admin(cur)
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        f=retained.fixture(cur,today)
        wrong=(str(retained.source.fg.base.create_customer(cur,'HTTP-OTHER-'+uuid.uuid4().hex)),)
        assert wrong[0]!=f['customer']
        assert cur.execute('select is_active from erp.customers where id=%s',wrong).fetchone()==(True,)
        rid=uuid.uuid4()
        retained.b.chain.production.owner(cur)
        cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,status)values(%s,%s,%s,%s,%s,'DRAFT')",
            (rid,'HTTP-BAD-DRAFT-'+rid.hex,f['sale'],f['customer'],f['sale_at']))
        cur.execute('insert into erp.sales_return_items(return_id,sale_stock_allocation_id,location_id,qty_pcs,refund_amount,quality_grade)values(%s,%s,%s,1,20,%s)',
            (rid,f['allocations'][0]['allocation_id'],f['destination'],'GRADE_A'))
        cur.execute('update erp.sales_returns set customer_id=%s where id=%s',(wrong[0],rid));assert cur.rowcount==1
        retained.b.api.admin(cur)
        raw=bad_draft(cur,rid);assert raw['header']['status']=='DRAFT'
        before=retained.cmd.accounts(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    return f,str(rid),raw,before


def detail(user,f):
    return response(user.rpc('erp_cp7_get_sales_v1',dict(p_query=dict(q=f['tag'],sale_id=f['sale']))))['detail']


def inverse(user,f,action,return_id=None):
    d=detail(user,f);p=dict(sale_id=f['sale'],review_token=d['review_token'],change_reason='Exact named inverse after HTTP draft-isolation proof')
    if return_id:p['return_id']=return_id
    return response(user.rpc('erp_cp7_save_sale_v1',dict(p_action=action,p_payload=p,p_request=str(uuid.uuid4()),p_expected=d['row_version'])))


def flow(http,today,grade):
    user=http.login('OWNER',label='current-return-'+grade.lower())
    f,rid,raw,before=fixture(http,today)
    with http.connect()as conn,conn.cursor()as cur:
        now=retained.source.fg.ax.r1.now(cur).isoformat();conn.rollback()
    d=detail(user,f)
    draft=dict(return_number='HTTP-GOOD-'+uuid.uuid4().hex,physical_at=now,notes='Legitimate return beside malformed sibling',
        change_reason='Source, quantity and refund inspected',items=[dict(allocation_id=f['allocations'][0]['allocation_id'],
        location_id=f['destination'],qty_pcs='1',quality_grade=grade,refund_amount='20.00',notes=None)])
    query=dict(sale_id=f['sale'],expected_version=d['row_version'],review_token=d['review_token'],return_payload=draft,
        settlement=dict(mode=None,credit_account_id=None,cash_account_id=None,refund_physical_at=None,reference=None))
    held=snapshot(http)
    q=response(user.rpc(QUOTE,dict(p_query=query)))
    assert snapshot(http)==held,'HTTP_RETURN_QUOTE_CHANGED_ROWS_SEQUENCES_OR_FULL22'
    assert q['kind']=='QUOTE'and q['readiness']==dict(state='READY',issues=[]),q
    assert q['input_echo']==query and q['has_recognition_effect']is False and q['current_credit_amount']=='0.00'
    assert q['totals']['before']['receivable_remaining']=='80.00'and q['totals']['after']['receivable_remaining']=='60.00'
    request=str(uuid.uuid4())
    args=dict(p_payload=dict(draft,sale_id=f['sale'],review_token=d['review_token'],settlement=None,quote_sha256=q['binding']['quote_sha256']),
        p_request=request,p_expected=d['row_version'])
    for name,payload in((QUOTE,dict(p_query=query)),(SETTLE,args)):
        assert http.anon_rpc(name,payload)['status']in(401,403)
    assert snapshot(http)==held,'HTTP_RETURN_ANONYMOUS_REFUSAL_CHANGED_STATE'
    outcome=response(user.rpc(SETTLE,args))
    assert outcome['kind']=='COMMITTED_OUTCOME'and outcome['return_status']=='POSTED'and outcome['request_id']==request
    assert outcome['credit_id']is None and outcome['refund_event_id']is None
    with http.connect()as conn,conn.cursor()as cur:
        retained.b.api.admin(cur)
        assert bad_draft(cur,rid)==raw
        assert cur.execute('select count(*)from erp.journal_entries where source_type=%s and source_id=%s',('SALES_RETURN',rid)).fetchone()==(0,)
        assert retained.positions(cur,f)=={(f['location'],'GRADE_A'):6,(f['destination'],grade):1}
        expected={retained.cmd.mapping(cur,'AR_CUSTOMER'):-20,retained.cmd.mapping(cur,'SALES_REVENUE'):20,
            retained.cmd.mapping(cur,'FG_INVENTORY'):10,retained.cmd.mapping(cur,'COGS'):-10}
        actual=retained.cmd.delta(before,retained.cmd.accounts(cur));assert actual==expected,(actual,expected)
        stored=cur.execute('select payload,expected_version,response from cp7_credit.return_requests where actor=%s and request_id=%s',(user.auth_user_id,request)).fetchone()
        assert stored==(args['p_payload'],args['p_expected'],outcome),'HTTP_RETURN_RECEIPT_NOT_OWNED_BY_REAL_LOGIN'
        assert cur.execute("select count(*)filter(where status='DRAFT'),count(*)filter(where status='POSTED')from erp.sales_returns where sale_id=%s",(f['sale'],)).fetchone()==(1,1)
        conn.rollback()
    assert detail(user,f)['financial']['open_balance']=='60.00'
    held=snapshot(http);assert response(user.rpc(SETTLE,deepcopy(args)))==outcome
    assert snapshot(http)==held,'HTTP_RETURN_REPLAY_CHANGED_STATE'
    changed=deepcopy(args);changed['p_payload']['notes']+=' changed'
    response(user.rpc(SETTLE,changed),400,'CP7_CREDIT_RETURN_REQUEST_CHANGED')
    assert snapshot(http)==held,'HTTP_RETURN_CHANGED_REQUEST_REFUSAL_CHANGED_STATE'
    with http.connect()as conn,conn.cursor()as cur:
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
    try:
        revoked=snapshot(http)
        response(user.rpc(SETTLE,deepcopy(args)),403,'CP7_SALES_ACCESS_DENIED')
        assert snapshot(http)==revoked,'HTTP_RETURN_REVOKED_REPLAY_CHANGED_STATE'
    finally:
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
    # Restoring membership legitimately advances its audit sequence; do not
    # compare it to the pre-revocation snapshot or reset that sequence.
    inverse(user,f,'RETURN_REVERSE',outcome['return_id'])
    with http.connect()as conn,conn.cursor()as cur:
        retained.b.api.admin(cur);assert retained.cmd.accounts(cur)==before
        assert retained.positions(cur,f)=={(f['location'],'GRADE_A'):6};assert bad_draft(cur,rid)==raw;conn.rollback()
    inverse(user,f,'SALE_REVERSE')
    with http.connect()as conn,conn.cursor()as cur:
        retained.b.api.admin(cur);assert retained.cmd.accounts(cur)==f['before_sale']
        assert retained.positions(cur,f)=={(f['location'],'GRADE_A'):10};assert bad_draft(cur,rid)==raw;conn.rollback()
    return dict(status='PASS',grade=grade,real_Auth_actor_receipt_verified=True,malformed_sibling_DRAFT_unchanged=True,
        exact_AR_minus20_revenue_plus20_FG_plus10_COGS_minus10=True,quote_anonymous_changed_request_replay_full22_rows_sequences_exact=True,
        revoked_replay_refused=True,named_return_and_sale_inverse_GL_neutral_stock10=True,real_browser_claim=False)


def http_cases(http,today):
    return [(name,lambda g=grade:flow(http,today,g))for name,grade in zip(IDS,('GRADE_A','GRADE_B'))]
