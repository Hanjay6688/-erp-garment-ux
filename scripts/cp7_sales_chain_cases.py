"""Predeclared Native sale-chain oracles; no synthetic business-effect credit."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import copy,json,threading,time,uuid
import psycopg
import cp7_sales_return_cases as returns
import cp7_note_correction_cases as note
import cp7_sales_chain_bundle as bundle
payments=returns.payments
cmd,source,b,auth=returns.cmd,returns.source,returns.b,returns.auth
READ='erp_cp7_get_sales_chain_v1'
RPC='erp_cp7_reverse_sales_chain_v1'
REQUIRED=dict(native=16,races=4,http=3,browser=2)
EXPECTED=sum(REQUIRED.values())
NAMES=('EXACT','NO_CHILDREN','FULLY_PAID','ALL_26_PAYMENTS','MULTI_RETURNS','OLD_CLOCKS',
    'FINAL_INVOICE_FAILURE','STALE_CHILD','STALE_STOCK','CURRENT_AUTH','CLOSED_FIELDS',
    'PRIVATE_IMMUTABLE','REPLAY','PENDING_DRAFT','DOWNSTREAM_RETURN','CLOSED_BOOKS')

def workspace(cur,f,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_sales_chain_v1(%s)',(f['sale'],)).fetchone()[0]
    b.api.admin(cur);return r

def payload(cur,f,subject=None):
    w=workspace(cur,f,subject);s=w['source']
    return dict(sale_id=s['sale_id'],review_token=s['review_token'],chain_token=w['chain_token'],
        payment_ids=[p['id']for p in s['payments']],return_ids=[r['id']for r in s['returns']],
        change_reason='Semua dokumen pembayaran retur invoice dan barang diperiksa'),s['row_version']

def reverse(cur,p,version,key=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_reverse_sales_chain_v1(%s,%s,%s)',(json.dumps(p),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return r

def private_state(cur):
    b.api.admin(cur)
    return {t:cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]')::text)from "+t+' x').fetchone()[0]
        for t in [bundle.SCHEMA+'.'+t for t in bundle.TABLES]+['cp7_sales.requests','cp7_sales.command_context']}

def facts(cur,f):
    b.api.admin(cur);old=cur.execute('show TimeZone').fetchone()[0];cur.execute("select set_config('TimeZone','UTC',true)")
    try:
        return dict(sale=note.unchanged_facts(cur,f['sale']),
            payments=cur.execute("select jsonb_agg(to_jsonb(p)-array['status','updated_at']order by p.id)from erp.sales_payments p where sale_id=%s",(f['sale'],)).fetchone()[0],
            returns=cur.execute("select jsonb_agg(to_jsonb(r)-array['status','row_version','updated_at']order by r.id)from erp.sales_returns r where sale_id=%s",(f['sale'],)).fetchone()[0],
            items=cur.execute('select jsonb_agg(to_jsonb(i)order by i.id)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s',(f['sale'],)).fetchone()[0])
    finally:cur.execute("select set_config('TimeZone',%s,true)",(old,))

def fixture(cur,today,children=True,historical=False,full=False):
    if historical:
        at=(source.fg.ax.r1.now(cur)-timedelta(days=366,hours=3)).replace(microsecond=123456)
        source.fg.ax.boundary.historical.prior.set_open_period(cur,at.date()-timedelta(days=2))
        f=note.stock(cur,today,10,at);f['before_sale']=cmd.accounts(cur);note.posted(cur,f,'4','20')
        f['destination']=returns.location(cur);f['bank']=str(source.bc.bank_account(cur,'CHAIN-'+uuid.uuid4().hex[:8]))
        f['allocations']=returns.read(cur,f)['page']['rows']
    else:f=returns.fixture(cur,today)
    if children:
        p,v=returns.payload(cur,f,qty='2',refund='40')
        if historical:p['physical_at']=(at+timedelta(hours=2)).isoformat()
        f['return']=cmd.command(cur,'RETURN',p,v)['return_id']
        p,v=payments.payment_payload(cur,f,'40'if full else'20')
        if historical:p['payment_date']=(at+timedelta(hours=1)).isoformat()
        f['payment']=cmd.command(cur,'PAYMENT',p,v)['payment_id']
    f['original_facts']=facts(cur,f);f['before_available']=cmd.available(cur,f)
    return f

def check(cur,f,p,r,key=None):
    assert r['contract_version']=='cp7.sales-chain-outcome.v1'and r['kind']=='COMMITTED_OUTCOME'and r['action']=='SALE_CHAIN_REVERSE'
    assert r['sale_id']==f['sale']and r['status']=='REVERSED'and r['row_version'].isdigit()
    if key is not None:assert r['request_id']==str(key)
    expected=[dict(action='PAYMENT_REVERSE',id=i,status='REVERSED')for i in p['payment_ids']]
    expected += [dict(action='RETURN_REVERSE',id=i,status='REVERSED')for i in p['return_ids']]+[dict(action='SALE_REVERSE',id=f['sale'],status='REVERSED')]
    assert r['steps']==expected,(r['steps'],expected)
    d=source.read(cur,f)['detail'];assert d['status']=='REVERSED'and d['reserved_qty']==d['returned_qty']=='0'
    assert d['financial']['open_balance']is None and d['financial']['paid_total']=='0.00'
    assert cmd.available(cur,f)==10 and returns.positions(cur,f)=={(f['location'],'GRADE_A'):10}
    assert cmd.accounts(cur)==f['before_sale'],cmd.delta(f['before_sale'],cmd.accounts(cur))
    assert not cur.execute("select exists(select 1 from erp.sales_payments where sale_id=%s and status='POSTED')or exists(select 1 from erp.sales_returns where sale_id=%s and status='POSTED')",(f['sale'],f['sale'])).fetchone()[0]
    assert facts(cur,f)==f['original_facts'],(facts(cur,f),f['original_facts'])
    h=cur.execute('select reviewed_source,steps,reason,request_id::text from '+bundle.SCHEMA+'.history where sale_id=%s',(f['sale'],)).fetchone()
    assert h and h[1]==expected and h[2]==p['change_reason']and h[3]==r['request_id']
    assert [x['id']for x in h[0]['payments']]==p['payment_ids']and [x['id']for x in h[0]['returns']]==p['return_ids']
    assert not cur.execute('select exists(select 1 from cp7_sales.command_context)').fetchone()[0]
    return d

def unchanged_refusal(cur,p,v,code='',key=None,subject=None):
    before=b.boundary.snapshot(cur);private=private_state(cur)
    detail=auth.refused(cur,lambda:reverse(cur,p,v,key,subject),code)
    assert b.boundary.snapshot(cur)==before and private_state(cur)==private
    return detail

def cases(cur,today):
    def exact():
        f=fixture(cur,today);p,v=payload(cur,f);key=uuid.uuid4();r=reverse(cur,p,v,key);check(cur,f,p,r,key)
        assert cur.execute('select count(*)from erp.sales_payment_posting_facts where payment_id=%s',(f['payment'],)).fetchone()[0]==1
        assert cur.execute('select count(*)from erp.sales_payment_reversal_facts where payment_id=%s',(f['payment'],)).fetchone()[0]==1
        return dict(status='PASS',actual_Native_payment20_return2_PCS40_invoice4_PCS80_all_inverse_stock10_and_GL_neutral=True)
    def empty():
        f=fixture(cur,today,children=False);p,v=payload(cur,f);assert p['payment_ids']==p['return_ids']==[];check(cur,f,p,reverse(cur,p,v))
        return dict(status='PASS',no_child_one_Native_sale_inverse=True)
    def full():
        f=fixture(cur,today,full=True);assert source.read(cur,f)['detail']['status']=='PAID';p,v=payload(cur,f);check(cur,f,p,reverse(cur,p,v))
        return dict(status='PASS',fully_paid_with_active_return_complete_cash_AR_stock_HPP_neutral=True)
    def pages():
        f=fixture(cur,today,children=False)
        for _ in range(26):payments.pay(cur,f,'1')
        f['original_facts']=facts(cur,f);p,v=payload(cur,f);assert len(p['payment_ids'])==26;check(cur,f,p,reverse(cur,p,v))
        assert cur.execute('select count(*)from erp.sales_payment_reversal_facts f join erp.sales_payments p on p.id=f.payment_id where p.sale_id=%s',(f['sale'],)).fetchone()[0]==26
        return dict(status='PASS',actual26_Native_payments_all_in_one_chain_no_first_page_truncation=True)
    def multiple():
        f=fixture(cur,today,children=False);returns.returned(cur,f,qty='1',refund='20');returns.returned(cur,f,qty='1',refund='0',destination=f['location'])
        payments.pay(cur,f,'10');payments.pay(cur,f,'20');f['original_facts']=facts(cur,f)
        p,v=payload(cur,f);assert len(p['payment_ids'])==len(p['return_ids'])==2;check(cur,f,p,reverse(cur,p,v))
        return dict(status='PASS',all_two_payments_two_returns_locations_exact_order_Native_stock_and_GL_neutral=True)
    def clocks():
        f=fixture(cur,today,historical=True);p,v=payload(cur,f);before=f['original_facts'];check(cur,f,p,reverse(cur,p,v))
        assert '123456'in json.dumps(before)and source.read(cur,f)['detail']['physical_at'].startswith(f['sale_at'][:10])
        return dict(status='PASS',Native366_day_old_sale_payment_return_exact_original_microseconds_and_inputs_unchanged=True)
    def failure():
        f=fixture(cur,today);p,v=payload(cur,f)
        cur.execute("create function public.cp7_chain_last_fail()returns trigger language plpgsql as $$begin if new.id='"+f['sale']+"'::uuid and new.status='REVERSED'then raise exception 'CP7_TEST_CHAIN_LAST_INVOICE_FAILURE';end if;return new;end$$;create trigger cp7_chain_last_fail before update on erp.sales_headers for each row execute function public.cp7_chain_last_fail()",prepare=False)
        unchanged_refusal(cur,p,v,'CP7_TEST_CHAIN_LAST_INVOICE_FAILURE')
        assert source.read(cur,f)['detail']['status']=='PARTIAL_PAID'and facts(cur,f)==f['original_facts']
        return dict(status='PASS',actual_last_Native_invoice_failure_rolls_back_prior_payment_and_return_stock_HPP_GL_private_child_and_outer_receipts=True)
    def stale_child():
        f=fixture(cur,today);p,v=payload(cur,f)
        cur.execute("insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method)values(%s,%s,%s,1,%s,'CASH')",(f['sale'],'NEW-AFTER-REVIEW-'+f['tag'],source.fg.ax.r1.now(cur),f['bank']))
        assert source.read(cur,f)['detail']['row_version']==v;unchanged_refusal(cur,p,v,'CP7_SALES_CHAIN_STALE_REVIEW')
        return dict(status='PASS',child_change_without_header_version_bump_rejected_before_any_inverse=True)
    def stock():
        f=fixture(cur,today);p,v=payload(cur,f);later=dict(f,tag=f['tag']+'-LATER',sale_at=source.fg.ax.r1.now(cur).isoformat());note.posted(cur,later,'1','20')
        unchanged_refusal(cur,p,v,'CP7_SALES_CHAIN_STALE_REVIEW')
        return dict(status='PASS',actual_same_lot_later_sale_invalidates_complete_stock_token=True)
    def authority():
        f=fixture(cur,today);subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
        cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));p,v=payload(cur,f,subject);key=uuid.uuid4();r=reverse(cur,p,v,key,subject);check(cur,f,p,r,key)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.payment.reverse'",(role,))
        unchanged_refusal(cur,p,v,'CP7_SALES_WRITE_DENIED',key,subject)
        return dict(status='PASS',current_all_three_owner_permissions_required_before_cached_outer_outcome=True)
    def fields():
        f=fixture(cur,today);p,v=payload(cur,f)
        for bad in (dict(p,unit_hpp='0'),dict(p,payment_ids=p['payment_ids']*2),dict(p,return_ids=None),dict(p,chain_token=''),dict(p,change_reason=''),dict(p,sale_id=3)):
            unchanged_refusal(cur,bad,v,'CP7_SALES_CHAIN_FIELDS')
        for bad in (dict(p,payment_ids=[]),dict(p,return_ids=[])):
            unchanged_refusal(cur,bad,v,'CP7_SALES_CHAIN_CHILDREN_CHANGED')
        unchanged_refusal(cur,p,str(int(v)+1),'CP7_SALES_CHAIN_STALE_REVIEW')
        return dict(status='PASS',closed_fields_no_client_HPP_duplicate_missing_or_unreviewed_child_refused_no_effect=True)
    def private():
        f=fixture(cur,today);p,v=payload(cur,f);check(cur,f,p,reverse(cur,p,v));bundle.verify(cur)
        before=b.boundary.snapshot(cur);saved=private_state(cur)
        for sql in('update '+bundle.SCHEMA+'.history set reason=reason','delete from '+bundle.SCHEMA+'.history','truncate '+bundle.SCHEMA+'.history'):
            auth.refused(cur,lambda:cur.execute(sql),'CP7_SALES_CHAIN_HISTORY_IMMUTABLE')
        assert b.boundary.snapshot(cur)==before and private_state(cur)==saved
        return dict(status='PASS',private_no_app_ERP_DML_reviewed_original_and_steps_immutable_update_delete_truncate=True)
    def replay():
        f=fixture(cur,today);p,v=payload(cur,f);key=uuid.uuid4();r=reverse(cur,p,v,key);check(cur,f,p,r,key);before=b.boundary.snapshot(cur);saved=private_state(cur)
        assert reverse(cur,p,v,key)==r and b.boundary.snapshot(cur)==before and private_state(cur)==saved
        unchanged_refusal(cur,dict(p,change_reason='Different command intent must never replay'),v,'CP7_SALES_CHAIN_REQUEST_CHANGED',key)
        subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
        unchanged_refusal(cur,p,v,'CP7_SALES_CHAIN_STALE_REVIEW',key,subject)
        return dict(status='PASS',exact_outer_UUID_original_receipt_no_second_effect_changed_intent_and_other_actor_refused=True)
    def draft():
        f=fixture(cur,today);cur.execute("insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method)values(%s,%s,%s,1,%s,'CASH')",(f['sale'],'PENDING-'+f['tag'],source.fg.ax.r1.now(cur),f['bank']))
        w=workspace(cur,f);assert not w['eligible']and w['source']['pending_children'][0]['number']=='PENDING-'+f['tag'];p,v=payload(cur,f);unchanged_refusal(cur,p,v,'CP7_SALES_CHAIN_PENDING_CHILD')
        return dict(status='PASS',pending_draft_exact_number_not_omitted_and_complete_no_effect_refusal=True)
    def downstream():
        f=fixture(cur,today);later=dict(f,tag=f['tag']+'-USED',location=f['destination'],sale_at=source.fg.ax.r1.now(cur).isoformat());note.posted(cur,later,'2','20');p,v=payload(cur,f)
        unchanged_refusal(cur,p,v);assert source.read(cur,f)['detail']['status']=='PARTIAL_PAID'
        return dict(status='PASS',Native_already_consumed_return_stock_refusal_rolls_back_payment_already_reversed_in_same_attempt=True)
    def closed():
        f=fixture(cur,today,historical=True);through=today-timedelta(days=1);source.fg.ax.boundary.historical.prior.set_open_period(cur,through)
        before=cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall()
        p,v=payload(cur,f);check(cur,f,p,reverse(cur,p,v))
        assert cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall()==before
        assert cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]==through
        return dict(status='PASS',closed_daily_GL_and_period_unchanged_Native_current_open_inverse_date_and_original_economic_inputs_preserved=True)
    functions=(exact,empty,full,pages,multiple,clocks,failure,stale_child,stock,authority,fields,private,replay,draft,downstream,closed)
    assert len(functions)==len(NAMES)==REQUIRED['native']
    return [('CP7_SALES_CHAIN_'+n,f)for n,f in zip(NAMES,functions)]

def races(tools,today):
    def compete(same=False):
        with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        gate=threading.Barrier(2);keys=[uuid.uuid4(),uuid.uuid4()]
        if same:keys[1]=keys[0]
        def send(key):
            with tools.connect()as conn,conn.cursor()as cur:
                gate.wait()
                try:r=reverse(cur,p,v,key);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e)
        with ThreadPoolExecutor(max_workers=2)as pool:rows=[j.result(60)for j in[pool.submit(send,k)for k in keys]]
        wins=[r for r in rows if isinstance(r,dict)];losses=[r for r in rows if isinstance(r,str)]
        if same:assert len(wins)==2 and wins[0]==wins[1]
        else:assert len(wins)==len(losses)==1 and'CP7_SALES_CHAIN_STALE_REVIEW'in losses[0],rows
        with tools.connect()as conn,conn.cursor()as cur:
            check(cur,f,p,wins[0]);assert cur.execute('select count(*)from '+bundle.SCHEMA+'.history where sale_id=%s',(f['sale'],)).fetchone()[0]==1
            assert cur.execute('select count(*)from '+bundle.SCHEMA+'.requests where request_id=any(%s::uuid[])',(keys,)).fetchone()[0]==1
        return dict(status='PASS',real_concurrent_requests=True,same_UUID=same,one_complete_Native_chain_and_outer_history=True)
    def changed_wait(stock=False):
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);subject=None;role=None
            if not stock:
                subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
            p,v=payload(cur,f,subject);key=uuid.uuid4();conn.commit()
        with tools.connect()as holder,holder.cursor()as held:
            held.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))");holder_pid=held.execute('select pg_backend_pid()').fetchone()[0];pid=[];started=threading.Event()
            def send():
                with tools.connect()as conn,conn.cursor()as cur:
                    pid.append(cur.execute('select pg_backend_pid()').fetchone()[0]);started.set()
                    try:r=reverse(cur,p,v,key,subject);conn.commit();return r
                    except psycopg.Error as e:conn.rollback();return str(e)
            with ThreadPoolExecutor(max_workers=1)as pool:
                job=pool.submit(send);assert started.wait(5);observed=False
                try:
                    deadline=time.monotonic()+8
                    while time.monotonic()<deadline:
                        held.execute('select pg_stat_clear_snapshot()')
                        if holder_pid in held.execute('select pg_blocking_pids(%s)',(pid[0],)).fetchone()[0]:observed=True;break
                        time.sleep(.02)
                    assert observed,'SALES_CHAIN_ACTUAL_FG_LOCK_WAIT_NOT_OBSERVED'
                    if stock:
                        later=dict(f,tag=f['tag']+'-RACE',sale_at=source.fg.ax.r1.now(held).isoformat());note.posted(held,later,'1','20')
                    else:held.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.return.reverse'",(role,))
                    b.api.admin(held);before=b.boundary.snapshot(held);saved=private_state(held);holder.commit()
                finally:holder.rollback()
                result=job.result(60)
        assert isinstance(result,str)and('CP7_SALES_CHAIN_STALE_REVIEW'if stock else'CP7_SALES_WRITE_DENIED')in result,result
        with tools.connect()as conn,conn.cursor()as cur:
            assert b.boundary.snapshot(cur)==before and private_state(cur)==saved
        return dict(status='PASS',exact_holder_worker_actual_lock_wait_observed=True,current_permission_retire=not stock,actual_same_lot_Native_stock_change=stock,complete_no_effect_post_change_boundary=True)
    return [('CP7_SALES_CHAIN_RACE_SAME_UUID',lambda:compete(True)),('CP7_SALES_CHAIN_RACE_COMPETING',compete),('CP7_SALES_CHAIN_RACE_AUTH_RETIRE',changed_wait),('CP7_SALES_CHAIN_RACE_STOCK_CHANGE',lambda:changed_wait(True))]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','sales-chain-owner')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today,historical=True);p,v=payload(cur,f);conn.commit()
        key=uuid.uuid4();args=dict(p_payload=p,p_request=str(key),p_expected=v)
        assert http.anon_rpc(RPC,args)['status']in(401,403)and http.anon_rpc(READ,dict(p_sale=f['sale']))['status']in(401,403)
        response=owner.rpc(RPC,args);assert response['status']==200,response;r=response['body'];assert owner.rpc(RPC,args)['body']==r
        with http.connect()as conn,conn.cursor()as cur:check(cur,f,p,r,key);conn.rollback()
        changed=copy.deepcopy(args);changed['p_payload']['payment_ids']=[];assert owner.rpc(RPC,changed)['status']>=400
        return dict(status='PASS',actual_Auth_all_Native_chain_committed_exact_UUID_replay_anonymous_and_changed_intent_refused=True)
    def read():
        owner=http.login('OWNER','sales-chain-reader')
        with http.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today,children=False)
            for _ in range(26):payments.pay(cur,f,'1')
            before=b.boundary.snapshot(cur);saved=private_state(cur);conn.commit()
        r=owner.rpc(READ,dict(p_sale=f['sale']));assert r['status']==200 and len(r['body']['source']['payments'])==26,r
        with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before and private_state(cur)==saved;conn.rollback()
        return dict(status='PASS',actual_Auth_reader_all26_payment_identities_no_business_or_private_receipt_effect=True)
    def revoke():
        admin=http.login('ADMIN','sales-chain-admin')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=v);response=admin.rpc(RPC,args);assert response['status']==200,response
        with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin.auth_user_id,));conn.commit()
        assert admin.rpc(RPC,args)['status']==403 and admin.rpc(READ,dict(p_sale=f['sale']))['status']==403
        return dict(status='PASS',actual_current_Auth_deactivation_denies_cached_chain_and_private_read=True)
    return [('CP7_SALES_CHAIN_HTTP_COMMIT_REPLAY',flow),('CP7_SALES_CHAIN_HTTP_ALL26_READONLY',read),('CP7_SALES_CHAIN_HTTP_CURRENT_AUTH',revoke)]
