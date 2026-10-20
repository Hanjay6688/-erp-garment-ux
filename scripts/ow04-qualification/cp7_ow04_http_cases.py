"""Explicit actual Auth/PostgREST settlement cases; not yet executed.

Only Http's real Auth credentials issue requests. All Native stock/sale/payment
setup uses retained fixture writers on the disposable HTTP database. Temporary
fixture-only ERP schema access is restored before any HTTP request can run.
"""
from pathlib import Path
import copy,json,uuid
import cp7_ow04_initial_settlement_cases as initial
nf=initial.native
IDS=tuple('OW04_HTTP_'+x for x in ('CREDIT_COMMIT_REPLAY','REFUND_COMMIT_REPLAY','CHANGED_PAYLOAD_REFUSAL',
 'REVOKED_REPLAY_REFUSAL','QUOTE_DIGEST_REFUSAL','RESERVED_PLAN_REFUSAL','ANON_REFUSAL','NON_OWNER_REFUND_REFUSAL'))
QUOTE='erp_cp7_get_sales_return_settlement_quote_v1'
SETTLE='erp_cp7_settle_sales_return_v1'


def snapshot(http):
    with http.connect()as conn,conn.cursor()as cur:
        nf.b.api.admin(cur)
        schemas=('cp7_credit','ow04_ordinal_wrapper','ow04_source_proposal','ow04_pure_kernel')
        namespaces=[r[0]for r in cur.execute('select nspname from pg_namespace where nspname=any(%s::text[])order by 1',(list(schemas),)).fetchall()]
        assert namespaces==sorted(schemas),'OW04_HTTP_PRIVATE_SCHEMA_INVENTORY_MISSING'
        tables=[r[0]for r in cur.execute(
            "select quote_ident(n.nspname)||'.'||quote_ident(c.relname)from pg_class c join pg_namespace n on n.oid=c.relnamespace "
            "where n.nspname=any(%s::text[])and c.relkind in('r','p')order by 1",(list(schemas),)).fetchall()]
        assert 'cp7_credit.return_requests'in tables,'OW04_HTTP_PRIVATE_TABLE_INVENTORY_MISSING'
        tables+=['cp7_sales.requests','cp7_sales.command_context']
        # Catalog-quoted fixed schemas only. Retain every row's exact JSON text,
        # its hash, and the complete table inventory; no sampling or projection.
        private={table:nf._array(cur,table,'true',())for table in tables}
        value=dict(boundary=nf.b.boundary.snapshot(cur),private_schema_inventory=namespaces,private_table_inventory=tables,private=private)
        conn.rollback()
        return value


def response(reply,status=200,code=None):
    assert reply['status']==status,(status,reply['status'],reply.get('body'))
    if code is not None:
        assert isinstance(reply.get('body'),dict)and reply['body'].get('message')==code,(code,reply.get('body'))
    return reply['body']


def prepared(http,today,*,paid='1000.00',profile='OPEN',mode='CREDIT'):
    gold=next(x for x in initial.expected()['cases']if(x['paid'],x['profile'],x['mode'])==(paid,profile,mode))
    with http.connect()as conn,conn.cursor()as cur:
        nf.b.api.admin(cur);initial._require_installed(cur)
        before=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        x=nf.prepared(cur,today,paid,profile);master=initial._credit_master(cur)
        query=initial._input(x,gold,master)
        x['lot_identity_before']=nf._raw(cur,"select to_jsonb(t)-array['cached_qty_pcs','is_open']from erp.fg_lots t where id=%s",(x['f']['lot'],))
        x['journal_ids_before']={str(r[0])for r in cur.execute('select id from erp.journal_entries').fetchall()}
        original={r['id']:nf._array(cur,'erp.fg_stock_movements','id=%s',(r['id'],))for r in x['source_before']['stock']['document']}
        nf.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==before,'OW04_HTTP_FIXTURE_SCHEMA_ACL_NOT_RESTORED'
        conn.commit()
    return dict(x=x,gold=gold,master=master,query=query,original_movements=original)


def quoted(http,user,f):
    before=snapshot(http)
    q=response(user.rpc(QUOTE,dict(p_query=f['query'])))
    assert snapshot(http)==before,'OW04_HTTP_QUOTE_MUTATED_BUSINESS'
    with http.connect()as conn,conn.cursor()as cur:
        nf.b.api.admin(cur);initial._assert_quote(cur,q,f['query'],f['x'],f['gold'],f['master']);conn.rollback()
    return initial._envelope(f['query'],q),q


def args(envelope,request):
    return dict(p_payload=copy.deepcopy(envelope['document']),p_request=str(request),p_expected=envelope['expected_version'])


def committed(http,user,f):
    envelope,q=quoted(http,user,f);request=uuid.uuid4();a=args(envelope,request)
    result=response(user.rpc(SETTLE,a))
    initial._assert_outcome(result,request,envelope,q,f['gold']['mode'])
    with http.connect()as conn,conn.cursor()as cur:
        nf.b.api.admin(cur)
        actual=initial._assert_actual(cur,f['x'],f['gold'],f['master'],result,request,f['original_movements'])
        nf.assert_payment_unchanged(cur,f['x']);conn.rollback()
    before=snapshot(http)
    replay=response(user.rpc(SETTLE,copy.deepcopy(a)))
    assert replay==result and snapshot(http)==before,'OW04_HTTP_REAL_COMMIT_REPLAY_CHANGED_STATE'
    return dict(envelope=envelope,query=f['query'],request=request,args=a,outcome=result,quote=q,
        actual_return_journal=actual['native_return_journal'],recognition_journal=actual['recognition_journal'],refund_journal=actual['refund_journal'])


def http_cases(http,today):
    expected=json.loads(Path(__file__).with_name('EXPECTED.json').read_text())
    assert tuple(x['id']for x in expected['cases'])==IDS
    users={}
    def owner():
        if 'owner'not in users:users['owner']=http.login('OWNER',label='ow04-http-owner')
        return users['owner']
    def commit_case(mode):
        user=owner();f=prepared(http,today,paid='1000.00'if mode=='CREDIT'else'900.00',profile='OPEN'if mode=='CREDIT'else'REOPENED',mode=mode)
        result=committed(http,user,f)
        return dict(status='PASS',actual_auth=True,actual_HTTP_commit_and_fresh_connection_proof=True,mode=mode,
            exact_original_financial_and_date_oracles=True,committed_replay_identical=True,original_payment_unchanged=True,
            actual_outcome=result['outcome'],actual_return_journal=result['actual_return_journal'],
            recognition_journal=result['recognition_journal'],refund_journal=result['refund_journal'],production_go=False)
    def changed():
        user=owner();f=prepared(http,today);c=committed(http,user,f);a=copy.deepcopy(c['args'])
        a['p_payload']['change_reason']+=' changed after commit'
        before=snapshot(http);response(user.rpc(SETTLE,a),400,'CP7_CREDIT_RETURN_REQUEST_CHANGED')
        assert snapshot(http)==before
        return dict(status='PASS',committed_request_payload_immutable=True,no_partial_effect=True)
    def revoked():
        user=owner();f=prepared(http,today);c=committed(http,user,f)
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
        before=snapshot(http)
        try:
            response(user.rpc(SETTLE,c['args']),403,'CP7_SALES_ACCESS_DENIED');assert snapshot(http)==before
        finally:
            with http.connect()as conn,conn.cursor()as cur:
                cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
        return dict(status='PASS',actual_Auth_ERP_membership_revoked_replay_denied=True,no_partial_effect=True)
    def invalid(kind):
        user=owner();f=prepared(http,today);envelope,q=quoted(http,user,f);a=args(envelope,uuid.uuid4())
        if kind=='digest':a['p_payload']['quote_sha256']='0'*64;code='CP7_CREDIT_COMPLETE_QUOTE_CHANGED'
        else:a['p_payload']['book_date']=str(today);code='CP7_SALES_RETURN_FIELDS'
        before=snapshot(http);response(user.rpc(SETTLE,a),400,code);assert snapshot(http)==before
        return dict(status='PASS',invalid_kind=kind,exact_code=code,no_partial_effect=True)
    def anonymous():
        user=owner();f=prepared(http,today);envelope,q=quoted(http,user,f);before=snapshot(http)
        for name,payload in[(QUOTE,dict(p_query=f['query'])),(SETTLE,args(envelope,uuid.uuid4()))]:
            r=http.anon_rpc(name,payload);assert r['status']in(401,403),r
        assert snapshot(http)==before
        return dict(status='PASS',anonymous_read_and_write_denied=True,no_partial_effect=True)
    def staff():
        user=owner();f=prepared(http,today,mode='REFUND');envelope,q=quoted(http,user,f)
        # Explicit disposable role-policy fixture: same permission keys are
        # not an OWNER/ADMIN role. The original Native role guard must decide.
        with http.connect()as conn,conn.cursor()as cur:
            row=cur.execute("select id,is_active from erp.app_roles where role_code='STAFF'").fetchone()
            created=row is None
            if created:
                role=uuid.uuid4()
                cur.execute("insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active)values(%s,'STAFF','OW04 disposable non-owner fixture',false,false,true)",(role,))
                row=(role,True)
            assert row[1]is True,'OW04_HTTP_STAFF_ROLE_REQUIRED'
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(row[0],))
            cur.execute("insert into erp.app_role_permissions(role_id,permission_key)select %s,p.permission_key from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id where r.role_code='OWNER'",(row[0],))
            keys={r[0]for r in cur.execute('select permission_key from erp.app_role_permissions where role_id=%s',(row[0],)).fetchall()}
            assert {'sales.invoice.view','finance.ar.view','sales.return.create','sales.return.post','sales.return.view','finance.cash.view'}<=keys,'OW04_HTTP_STAFF_PERMISSION_FIXTURE_INCOMPLETE'
            conn.commit()
        s=http.login('STAFF',label='ow04-http-non-owner')
        credit=copy.deepcopy(f['query']);credit['settlement'].update(mode='CREDIT',cash_account_id=None,refund_physical_at=None,reference=None)
        before=snapshot(http)
        permitted=response(s.rpc(QUOTE,dict(p_query=credit)))
        assert permitted['capabilities']['record_return']and permitted['capabilities']['recognize_credit']
        assert snapshot(http)==before,'OW04_HTTP_STAFF_CREDIT_READ_MUTATED_BUSINESS'
        for name,payload in [(QUOTE,dict(p_query=f['query'])),(SETTLE,args(envelope,uuid.uuid4()))]:
            denied=response(s.rpc(name,payload),400,'OWNER or ADMIN access required')
            assert denied.get('code')=='P0001',denied
        assert snapshot(http)==before
        return dict(status='PASS',disposable_STAFF_role_fixture_created=created,
            successful_same_user_CREDIT_quote_before_refund=True,
            real_non_owner_with_all_permission_keys_denied_refund=True,Native_owner_guard_not_forged=True,no_partial_effect=True)
    operations=[lambda:commit_case('CREDIT'),lambda:commit_case('REFUND'),changed,revoked,lambda:invalid('digest'),lambda:invalid('reserved'),anonymous,staff]
    return list(zip(IDS,operations))
