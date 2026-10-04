"""Predeclared Native payment-edit oracles. Every financial effect is posted
by accepted Native writers, including historical receipts and later payments.
Only explicit disposable identity, period and last-post fault controls differ.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import copy,json,threading,time,uuid
import psycopg
import cp7_sales_payment_cases as payments
import cp7_note_correction_cases as note
import cp7_transaction_source_cases as navigation
import cp7_sales_payment_correction_bundle as bundle
cmd,source,b,auth=payments.cmd,payments.source,payments.b,payments.auth
RPC='erp_cp7_correct_sales_payment_v1'
READ='erp_cp7_get_sales_payment_correction_v1'
REQUIRED=dict(native=14,races=4,http=3,browser=2)
EXPECTED=sum(REQUIRED.values())

def workspace(cur,f,payment_id=None,subject=None,**query):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_sales_payment_correction_v1(%s)',(json.dumps(dict(sale_id=f['sale'],payment_id=payment_id or f['payment'],**query)),)).fetchone()[0]
    b.api.admin(cur);return r

def correct(cur,p,version,key=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_correct_sales_payment_v1(%s,%s,%s)',(json.dumps(p),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return r

def private_state(cur):
    b.api.admin(cur)
    return {table:cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),'[]')::text)from "+table+' t').fetchone()[0]
            for table in('cp7_payment_correction.requests','cp7_payment_correction.context','cp7_payment_correction.links','cp7_sales.requests','cp7_sales.command_context')}

def unchanged_stock(cur,f):
    return cur.execute("select md5(jsonb_build_object('movements',(select jsonb_agg(to_jsonb(m)order by id)from erp.fg_stock_movements m where lot_id=%s),'allocations',(select jsonb_agg(to_jsonb(a)order by a.id)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s),'items',(select jsonb_agg(to_jsonb(i)order by id)from erp.sales_items i where sale_id=%s))::text)",(f['lot'],f['sale'],f['sale'])).fetchone()[0]

def payment_fact(cur,ident):
    return cur.execute("select to_jsonb(p)-'status',to_jsonb(f)from erp.sales_payments p join erp.sales_payment_posting_facts f on f.payment_id=p.id where p.id=%s",(ident,)).fetchone()

def fixture(cur,today,amount='30.01',historical=False,qty='4',price='20'):
    if historical:
        at=(source.fg.ax.r1.now(cur)-timedelta(days=366,hours=3)).replace(microsecond=123456)
        source.fg.ax.boundary.historical.prior.set_open_period(cur,at.date()-timedelta(days=1))
        f=note.stock(cur,today,1000,at);note.posted(cur,f,qty,price)
        f['bank']=str(source.bc.bank_account(cur,'PAYEDIT-'+uuid.uuid4().hex[:8]))
        payment_at=at+timedelta(hours=2)
    else:
        f=payments.fixture(cur,today,qty=int(qty),price=price)
        payment_at=source.fg.ax.r1.now(cur).replace(microsecond=123456)
    p,v=payments.payment_payload(cur,f,amount);p['payment_date']=payment_at.isoformat()
    f['payment']=cmd.command(cur,'PAYMENT',p,v)['payment_id']
    f['original']=workspace(cur,f)['document'];f['original_fact']=payment_fact(cur,f['payment'])
    f['stock_hash']=unchanged_stock(cur,f);f['accounts']=cmd.accounts(cur);f['sale_fact']=note.unchanged_facts(cur,f['sale'])
    return f

def payload(cur,f,amount='20.01',payment_id=None,**changes):
    w=workspace(cur,f,payment_id);d=w['document'];p,v=cmd.review(cur,f)
    p.update(payment_id=d['id'],replacement=dict(payment_number=d['number'],payment_date=d['physical_at'],amount=amount,
            cash_account_id=d['cash_account_id'],payment_method=d['method'],reference_number=d['reference'],notes=d['notes']))
    p['replacement'].update(changes);p['change_reason']='Pembayaran sumber dan pengganti diperiksa di lapangan'
    return p,v

def check(cur,f,p,r,key=None):
    assert r['contract_version']=='cp7.sales-payment-correction.v1'and r['action']=='PAYMENT_CORRECT'and r['kind']=='COMMITTED_OUTCOME'
    assert r['sale_id']==f['sale']and r['original_payment_id']==p['payment_id']and r['original_payment_status']=='REVERSED'and r['payment_status']=='POSTED'
    assert r['payment_id']!=p['payment_id']and r['link']['original_id']==p['payment_id']and r['link']['replacement_id']==r['payment_id']and r['link']['sale_id']==f['sale']
    if key is not None:assert r['request_id']==r['link']['request_id']==str(key)
    w=workspace(cur,f,r['payment_id']);d=w['document'];old=workspace(cur,f,p['payment_id'])
    assert old['document']['status']=='REVERSED'and w['previous']['document']==old['document']and old['next']['document']==d
    assert D(d['amount'])==D(p['replacement']['amount'])and d['cash_account_id']==p['replacement']['cash_account_id']and d['method']==p['replacement']['payment_method']and d['replaces_payment_id']is None
    assert cur.execute('select payment_date=%s::timestamptz from erp.sales_payments where id=%s',(p['replacement']['payment_date'],r['payment_id'])).fetchone()[0]
    assert d['reference']==p['replacement']['reference_number']and d['notes']==p['replacement']['notes']
    assert unchanged_stock(cur,f)==f['stock_hash']and note.unchanged_facts(cur,f['sale'])==f['sale_fact']
    assert not cur.execute('select exists(select 1 from cp7_sales.command_context)or exists(select 1 from cp7_payment_correction.context)').fetchone()[0]
    t=r['link']['time_restatement']
    original,original_day,inverse,inverse_day=cur.execute('select o.id,o.economic_date,r.id,r.economic_date from erp.sales_payment_posting_facts f join erp.journal_entries o on o.id=f.original_journal_entry_id join erp.sales_payment_reversal_facts rf on rf.payment_id=f.payment_id join erp.journal_entries r on r.id=rf.reversal_journal_entry_id where f.payment_id=%s',(p['payment_id'],)).fetchone()
    if original==inverse:raise AssertionError('Original and inverse journals cannot share identity')
    # Actual Native lines, all dimensions and descriptions are compared. The
    # time entries relocate the inverse; their whole-ledger effect is zero.
    if original_day==inverse_day:assert t is None
    else:
        assert t and t['effective_economic_date']==str(original_day)and t['neutral_economic_date']==str(inverse_day)
        def lines(ident):return sorted(cur.execute('select account_id,debit,credit,description,customer_id,vendor_id,contractor_id,po_id,product_id from erp.journal_lines where journal_entry_id=%s',(ident,)).fetchall(),key=str)
        inv=lines(inverse);assert lines(t['effective_journal_id'])==inv
        assert lines(t['neutral_journal_id'])==sorted([(a,c,d,*rest)for a,d,c,*rest in inv],key=str)
    return w

def cash_prefixes(cur,f,days):
    bank=payments.bank_account(cur,f)
    return [(str(day),str(value))for day,value in cur.execute("select d.day,coalesce(sum(l.debit-l.credit),0)from unnest(%s::date[])d(day)left join erp.journal_entries j on j.economic_date<=d.day and j.status in('POSTED','REVERSED')left join erp.journal_lines l on l.journal_entry_id=j.id and l.account_id=%s group by d.day order by d.day",(days,bank)).fetchall()]

def year_fixture(cur,today):
    f=fixture(cur,today,'60',True,qty='10',price='100.01')
    original_at=cur.execute('select payment_date from erp.sales_payments where id=%s',(f['payment'],)).fetchone()[0]
    days=[]
    for n in range(1,365):
        at=original_at+timedelta(days=n)
        # Native fixture writer, never a pre-filled posted payment or balance.
        ident=cur.execute("insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,status)values(%s,%s,%s,1,%s,'CASH','DRAFT')returning id",(f['sale'],'PAY-LATER-'+uuid.uuid4().hex,at,f['bank'])).fetchone()[0]
        source.native(cur,'select erp.post_sales_payment(%s)',(ident,))
        days.append(cur.execute('select j.economic_date from erp.sales_payment_posting_facts p join erp.journal_entries j on j.id=p.original_journal_entry_id where p.payment_id=%s',(ident,)).fetchone()[0])
    f['days']=days;f['stock_hash']=unchanged_stock(cur,f);f['prefix_before']=cash_prefixes(cur,f,days)
    return f

def year_check(cur,f,p,r):
    check(cur,f,p,r);after=cash_prefixes(cur,f,f['days'])
    assert len(after)==len(f['prefix_before'])==364
    assert all(a[0]==b[0]and D(a[1])-D(b[1])==D('-12')for a,b in zip(after,f['prefix_before']))
    assert payment_fact(cur,f['payment'])==f['original_fact']
    return dict(status='PASS',later_cash_prefixes_checked=364,each_cash_prefix_delta='-12',raw_before=f['prefix_before'],raw_after=after,
                unchanged_original_receipt_clock_amount_and_posting_fact=True,stock_HPP_and_sale_items_unchanged=True)

def cases(cur,today):
    def exact():
        f=fixture(cur,today);p,v=payload(cur,f);key=uuid.uuid4();r=correct(cur,p,v,key);check(cur,f,p,r,key)
        assert cmd.delta(f['accounts'],cmd.accounts(cur))=={payments.bank_account(cur,f):D('-10'),cmd.mapping(cur,'AR_CUSTOMER'):D('10')}
        assert source.read(cur,f)['detail']['financial']['paid_total']=='20.01'and payment_fact(cur,f['payment'])==f['original_fact']
        return dict(status='PASS',one_atomic_original30_01_new20_01=True,cash_minus10_AR_plus10=True,stock_HPP_revenue_unchanged=True,immutable_original=True)
    def full():
        f=fixture(cur,today,'80');assert source.read(cur,f)['detail']['status']=='PAID';p,v=payload(cur,f,'79.99');r=correct(cur,p,v);check(cur,f,p,r)
        assert source.read(cur,f)['detail']['financial']['open_balance']=='0.01'and r['status']=='PARTIAL_PAID'
        return dict(status='PASS',fully_paid_invoice_can_correct_original_payment_atomically=True,one_cent_receivable=True)
    def account():
        f=fixture(cur,today);bank=str(source.bc.bank_account(cur,'PAYEDIT-NEW-'+uuid.uuid4().hex[:8]));coa=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(bank,)).fetchone()[0]);p,v=payload(cur,f,cash_account_id=bank,payment_method='CASH',reference_number='Correct reference',notes='Correct notes');r=correct(cur,p,v);check(cur,f,p,r)
        assert cmd.delta(f['accounts'],cmd.accounts(cur))=={payments.bank_account(cur,f):D('-30.01'),coa:D('20.01'),cmd.mapping(cur,'AR_CUSTOMER'):D('10')}
        return dict(status='PASS',actual_new_cash_account_method_reference_notes=True,original_bank_minus30_01_new_bank_plus20_01_AR_plus10=True)
    def micros():
        f=fixture(cur,today,'9007199254740993.01',qty='1',price='9007199254740993.03');p,v=payload(cur,f,'9007199254740993.02');r=correct(cur,p,v);w=check(cur,f,p,r)
        assert '123456'in w['document']['physical_at']and w['document']['physical_at']==f['original']['physical_at']and payment_fact(cur,f['payment'])==f['original_fact']
        assert w['document']['amount']=='9007199254740993.02'and cmd.delta(f['accounts'],cmd.accounts(cur))=={payments.bank_account(cur,f):D('0.01'),cmd.mapping(cur,'AR_CUSTOMER'):D('-0.01')}
        return dict(status='PASS',Native_money_above_JS_safe_integer_plus_one_exact_cent=True,unchanged_microseconds=True)
    def date_move():
        f=fixture(cur,today,historical=True);old=cur.execute('select payment_date from erp.sales_payments where id=%s',(f['payment'],)).fetchone()[0];p,v=payload(cur,f,'30.01',payment_date=(old+timedelta(days=1)).isoformat());original_day=cur.execute('select j.economic_date from erp.sales_payment_posting_facts p join erp.journal_entries j on j.id=p.original_journal_entry_id where p.payment_id=%s',(f['payment'],)).fetchone()[0];days=[original_day,original_day+timedelta(days=1),cur.execute("select (statement_timestamp()at time zone 'Asia/Jakarta')::date").fetchone()[0]];before=cash_prefixes(cur,f,days);r=correct(cur,p,v);check(cur,f,p,r);after=cash_prefixes(cur,f,days)
        assert [D(a[1])-D(z[1])for a,z in zip(after,before)]==[D('-30.01'),D('0'),D('0')]
        return dict(status='PASS',old_date_cash_removed_and_true_new_date_added=True,all_time_cash_AR_unchanged=True,before=before,after=after)
    def year():
        f=year_fixture(cur,today);p,v=payload(cur,f,'48');r=correct(cur,p,v);return year_check(cur,f,p,r)
    def late_failure():
        f=fixture(cur,today,historical=True);p,v=payload(cur,f);key=uuid.uuid4()
        cur.execute("create function cp7_payment_correction.test_last_post()returns trigger language plpgsql as $$begin if new.source_type='SALES_PAYMENT'and new.source_id<>'"+f['payment']+"'::uuid then raise exception 'CP7_TEST_PAYMENT_FINAL_NATIVE_POST';end if;return new;end $$",prepare=False)
        cur.execute('create trigger cp7_test_payment_last_post before insert on erp.journal_entries for each row execute function cp7_payment_correction.test_last_post()',prepare=False)
        try:
            before=b.boundary.snapshot(cur);private=private_state(cur);auth.refused(cur,lambda:correct(cur,p,v,key),'CP7_TEST_PAYMENT_FINAL_NATIVE_POST')
            assert b.boundary.snapshot(cur)==before and private_state(cur)==private and workspace(cur,f)['document']==f['original']
        finally:cur.execute('drop trigger cp7_test_payment_last_post on erp.journal_entries;drop function cp7_payment_correction.test_last_post()',prepare=False)
        return dict(status='PASS',explicit_disposable_fault_at_final_replacement_journal=True,inverse_time_pair_replacement_link_UUID_all_rolled_back=True)
    def stale():
        f=fixture(cur,today);p,v=payload(cur,f);payments.pay(cur,f,'1');before=b.boundary.snapshot(cur);private=private_state(cur);auth.refused(cur,lambda:correct(cur,p,v),'CP7_SALES_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        g=fixture(cur,today);p,v=payload(cur,g);p['payment_id']=f['payment'];before=b.boundary.snapshot(cur);auth.refused(cur,lambda:correct(cur,p,v),'CP7_SALES_PAYMENT_SOURCE_CHANGED');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',later_native_payment_retires_original_review=True,foreign_parent_child_refused_atomically=True)
    def fields():
        f=fixture(cur,today);p,v=payload(cur,f);before=b.boundary.snapshot(cur);private=private_state(cur)
        for change in[dict(amount='1.001'),dict(amount=20),dict(amount='0'),dict(payment_method='OPENING_ADVANCE'),dict(cash_account_id=None),dict(notes=3),dict(unit_hpp='1')]:
            q=copy.deepcopy(p);q['replacement'].update(change);auth.refused(cur,lambda:correct(cur,q,v),'CP7_')
        auth.refused(cur,lambda:correct(cur,dict(p,force=True),v),'CP7_PAYMENT_CORRECTION_FIELDS')
        q=copy.deepcopy(p);q['replacement']['amount']='30.01';auth.refused(cur,lambda:correct(cur,q,v),'CP7_PAYMENT_CORRECTION_UNCHANGED')
        q=copy.deepcopy(p);q['replacement']['amount']='80.01';auth.refused(cur,lambda:correct(cur,q,v),'exceeds exact remaining receivable')
        assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        cur.execute('update erp.cash_accounts set is_active=false where id=%s',(f['bank'],));before=b.boundary.snapshot(cur);auth.refused(cur,lambda:correct(cur,p,v),'CP7_SALES_CASH_UNAVAILABLE');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        return dict(status='PASS',no_rounding_overpayment_force_or_caller_identity=True,noop_refused=True,inactive_account_rolls_back_inverse_and_UUID=True)
    def chain():
        f=fixture(cur,today,historical=True);p,v=payload(cur,f);key=uuid.uuid4();first=correct(cur,p,v,key);check(cur,f,p,first,key)
        q,v2=payload(cur,f,'30.01',payment_id=first['payment_id']);second=correct(cur,q,v2);check(cur,f,q,second)
        before=b.boundary.snapshot(cur);private=private_state(cur);assert correct(cur,p,v,key)==first and b.boundary.snapshot(cur)==before and private_state(cur)==private
        middle=workspace(cur,f,first['payment_id']);assert middle['previous']['document']['id']==f['payment']and middle['next']['document']['id']==second['payment_id']
        assert cmd.accounts(cur)==f['accounts']and payment_fact(cur,f['payment'])==f['original_fact']
        changed=copy.deepcopy(p);changed['replacement']['amount']='21';auth.refused(cur,lambda:correct(cur,changed,v,key),'CP7_SALES_REQUEST_CHANGED')
        return dict(status='PASS',two_immutable_corrections_restore_original_cash_AR=True,unchanged_old_UUID_after_later_correction=True,changed_UUID_intent_denied=True)
    def permissions():
        f=fixture(cur,today);subject,role=auth.custom_actor(cur)
        for permission in('sales.invoice.view','finance.ar.view','sales.payment.view','sales.payment.create','sales.payment.post','sales.payment.reverse'):
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
        p,v=payload(cur,f);before=b.boundary.snapshot(cur);auth.refused(cur,lambda:correct(cur,p,v,subject=subject),'CP7_SALES_OWNER_ADMIN_REQUIRED');assert b.boundary.snapshot(cur)==before
        assert workspace(cur,f,subject=subject)['eligible']
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.payment.view'",(role,));auth.refused(cur,lambda:workspace(cur,f,subject=subject),'CP7_SALES_CASH_DENIED')
        return dict(status='PASS',current_OWNER_ADMIN_and_all_existing_payment_permissions_required=True,read_only_role_cannot_write=True,current_view_retirement_denies_read=True)
    def ordinary():
        f,w=note.wallet_note(cur,today);ident=str(cur.execute("select p.id from erp.sales_payments p join erp.initial_import_prepayment_payments l on l.sales_payment_id=p.id where p.sale_id=%s and p.status='POSTED'",(f['sale'],)).fetchone()[0]);f['payment']=ident
        assert not workspace(cur,f)['eligible'];p,v=payload(cur,f);p['replacement'].update(cash_account_id=f['bank'],payment_method='CASH');before=b.boundary.snapshot(cur);private=private_state(cur);auth.refused(cur,lambda:correct(cur,p,v),'CP7_PAYMENT_CORRECTION_ORDINARY_ONLY');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        ordinary=fixture(cur,today);target=dict(ordinary,tag='PAY-REALLOCATION-'+uuid.uuid4().hex[:8],sale_at=source.fg.ax.r1.now(cur).isoformat());note.posted(cur,target,'1','80')
        payments.inverse(cur,ordinary,ordinary['payment'])
        moved=str(cur.execute("insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,replaces_payment_id,status)select %s,%s,payment_date,amount,cash_account_id,payment_method,id,'DRAFT'from erp.sales_payments where id=%s returning id",(target['sale'],'REALLOCATION-'+uuid.uuid4().hex,ordinary['payment'])).fetchone()[0])
        source.native(cur,'select erp.post_sales_payment(%s)',(moved,));target['payment']=moved;assert not workspace(cur,target)['eligible']
        p,v=payload(cur,target);before=b.boundary.snapshot(cur);private=private_state(cur);auth.refused(cur,lambda:correct(cur,p,v),'CP7_PAYMENT_CORRECTION_ORDINARY_ONLY');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        return dict(status='PASS',actual_Native_opening_advance_and_linked_invoice_reallocation_excluded=True,wallet_original_and_GL_unchanged=True)
    def history():
        f=fixture(cur,today,historical=True);p,v=payload(cur,f);r=correct(cur,p,v);check(cur,f,p,r);bundle.verify(cur)
        before=b.boundary.snapshot(cur);private=private_state(cur)
        for sql in('update cp7_payment_correction.links set reason=reason','delete from cp7_payment_correction.links','truncate cp7_payment_correction.links'):
            auth.refused(cur,lambda:cur.execute(sql),'CP7_PAYMENT_CORRECTION_LINK_IMMUTABLE')
        assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        t=r['link']['time_restatement'];assert t
        for kind in('PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE'):
            navigation.exact(cur,kind,f['payment'],'SALE',f['sale'],('SALES_PAYMENT',f['payment']))
        auth.refused(cur,lambda:navigation.read(cur,'PAYMENT_CORRECTION_EFFECTIVE',r['payment_id']),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
        assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        return dict(status='PASS',immutable_history_update_delete_truncate_refused=True,all_reads_preserve_Native_and_private_facts=True,actual_time_entries_resolve_exact_original_payment_UUID_and_page=True,fake_time_source_refused=True)
    def closed():
        f=fixture(cur,today,historical=True);through=today-timedelta(days=1);source.fg.ax.boundary.historical.prior.set_open_period(cur,through)
        before=cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall();p,v=payload(cur,f);r=correct(cur,p,v);check(cur,f,p,r)
        assert cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall()==before
        assert cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]==through
        assert r['link']['time_restatement']['effective_transaction_date']>str(through)
        return dict(status='PASS',closed_daily_GL_books_not_reopened_or_rewritten=True,old_economic_date_kept_Native_open_posting_date_used=True)
    names=[('EXACT_CENTS',exact),('FULLY_PAID',full),('NEW_ACCOUNT_METHOD',account),('MICROSECONDS',micros),('DATE_MOVE',date_move),('YEAR_364',year),('FINAL_POST_FAILURE',late_failure),('STALE_FOREIGN_SOURCE',stale),('CLOSED_FIELDS_INACTIVE',fields),('REPLAY_RESTORE_CHAIN',chain),('CURRENT_PERMISSIONS',permissions),('ADVANCE_EXCLUSION',ordinary),('IMMUTABLE_HISTORY_SOURCE',history),('CLOSED_BOOKS',closed)]
    assert len(names)==REQUIRED['native'];return [('CP7_PAYMENT_CORRECTION_'+name,fn)for name,fn in names]

def wait_for(tools):
    deadline=time.monotonic()+15
    with tools.connect()as conn,conn.cursor()as cur:
        while time.monotonic()<deadline:
            cur.execute('select pg_stat_clear_snapshot()')
            if cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event_type='Lock'and pid<>pg_backend_pid())").fetchone()[0]:return
            time.sleep(.03)
    raise AssertionError('PAYMENT_CORRECTION_REAL_SOURCE_WAIT_NOT_OBSERVED')

def races(tools,today):
    def compete(same=False):
        with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        gate=threading.Barrier(2);keys=[uuid.uuid4(),uuid.uuid4()]
        if same:keys[1]=keys[0]
        def send(key):
            with tools.connect()as conn,conn.cursor()as cur:
                gate.wait()
                try:r=correct(cur,p,v,key);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e)
        with ThreadPoolExecutor(max_workers=2)as pool:rows=[j.result(60)for j in[pool.submit(send,k)for k in keys]]
        wins=[r for r in rows if isinstance(r,dict)];losers=[r for r in rows if isinstance(r,str)]
        if same:assert len(wins)==2 and wins[0]==wins[1]
        else:assert len(wins)==len(losers)==1 and'CP7_SALES_REVIEW_CHANGED'in losers[0],rows
        with tools.connect()as conn,conn.cursor()as cur:
            check(cur,f,p,wins[0]);assert cur.execute('select count(*)from cp7_payment_correction.links where original_id=%s',(f['payment'],)).fetchone()[0]==1
            assert cur.execute('select count(*)from cp7_payment_correction.requests where request_id=any(%s::uuid[])',(keys,)).fetchone()[0]==1
        return dict(status='PASS',real_concurrent_requests=True,same_UUID=same,one_atomic_inverse_replacement_and_link=True)
    def changed_wait(bank=False):
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);p,v=payload(cur,f);key=uuid.uuid4();subject=None
            if not bank:
                subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
            conn.commit()
        with tools.connect()as holder,holder.cursor()as held:
            held.execute('select 1 from erp.sales_headers where id=%s for update',(f['sale'],))
            def send():
                with tools.connect()as conn,conn.cursor()as cur:
                    try:r=correct(cur,p,v,key,subject);conn.commit();return r
                    except psycopg.Error as e:conn.rollback();return str(e)
            with ThreadPoolExecutor(max_workers=1)as pool:
                job=pool.submit(send)
                try:
                    wait_for(tools)
                    with tools.connect()as conn,conn.cursor()as cur:
                        if bank:cur.execute('update erp.cash_accounts set is_active=false where id=%s',(f['bank'],))
                        else:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.payment.post'",(role,))
                        conn.commit()
                finally:holder.rollback()
                result=job.result(60)
        assert isinstance(result,str)and('CP7_SALES_CASH_UNAVAILABLE'if bank else'CP7_SALES_WRITE_DENIED')in result,result
        with tools.connect()as conn,conn.cursor()as cur:
            assert workspace(cur,f)['document']==f['original']and payment_fact(cur,f['payment'])==f['original_fact']and cmd.accounts(cur)==f['accounts']and unchanged_stock(cur,f)==f['stock_hash']
            assert not cur.execute('select exists(select 1 from cp7_payment_correction.requests where request_id=%s)',(key,)).fetchone()[0]
        return dict(status='PASS',actual_invoice_lock_wait_observed=True,bank_retired=bank,current_permission_retired=not bank,whole_correction_no_effect_and_no_receipt=True)
    return [('CP7_PAYMENT_CORRECTION_RACE_SAME_UUID',lambda:compete(True)),('CP7_PAYMENT_CORRECTION_RACE_COMPETING',compete),('CP7_PAYMENT_CORRECTION_RACE_AUTH_RETIRE',changed_wait),('CP7_PAYMENT_CORRECTION_RACE_BANK_RETIRE',lambda:changed_wait(True))]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','payment-correction-owner')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today,historical=True);p,v=payload(cur,f);conn.commit()
        key=uuid.uuid4();args=dict(p_payload=p,p_request=str(key),p_expected=v);assert http.anon_rpc(RPC,args)['status']in(401,403)
        response=owner.rpc(RPC,args);assert response['status']==200,response;r=response['body'];assert owner.rpc(RPC,args)['body']==r
        w=owner.rpc(READ,dict(p_query=dict(sale_id=f['sale'],payment_id=r['payment_id'])));assert w['status']==200 and w['body']['previous']['document']['id']==f['payment'],w
        with http.connect()as conn,conn.cursor()as cur:check(cur,f,p,r,key);assert cmd.delta(f['accounts'],cmd.accounts(cur))=={payments.bank_account(cur,f):D('-10'),cmd.mapping(cur,'AR_CUSTOMER'):D('10')};conn.rollback()
        changed=copy.deepcopy(args);changed['p_payload']['replacement']['amount']='21.01';assert owner.rpc(RPC,changed)['status']>=400
        return dict(status='PASS',actual_Auth_atomic_payment_edit_and_exact_UUID_replay=True,real_previous_next_history=True,anonymous_and_changed_intent_refused=True)
    def year():
        owner=http.login('OWNER','payment-correction-year-owner')
        with http.connect()as conn,conn.cursor()as cur:f=year_fixture(cur,today);p,v=payload(cur,f,'48');conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=v);start=time.monotonic_ns();response=owner.rpc(RPC,args);elapsed=(time.monotonic_ns()-start)/1_000_000
        assert response['status']==200,response
        with http.connect()as conn,conn.cursor()as cur:r=year_check(cur,f,p,response['body']);conn.rollback()
        assert owner.rpc(RPC,args)['body']==response['body'];return dict(r,actual_Auth_committed_year_readback=True,actual_HTTP_ms=round(elapsed,3),production_SLA=False)
    def revoke():
        admin=http.login('ADMIN','payment-correction-admin')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=v);response=admin.rpc(RPC,args);assert response['status']==200,response
        with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin.auth_user_id,));conn.commit()
        assert admin.rpc(RPC,args)['status']==403 and admin.rpc(READ,dict(p_query=dict(sale_id=f['sale'],payment_id=response['body']['payment_id'])))['status']==403
        return dict(status='PASS',current_actual_Auth_deactivation_denies_cached_write_and_source_history=True)
    return [('CP7_PAYMENT_CORRECTION_HTTP_ATOMIC_REPLAY',flow),('CP7_PAYMENT_CORRECTION_HTTP_YEAR_364',year),('CP7_PAYMENT_CORRECTION_HTTP_CURRENT_RETIRE',revoke)]
