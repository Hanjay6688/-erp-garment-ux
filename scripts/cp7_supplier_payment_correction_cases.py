"""Predeclared supplier cash/AP oracles on genuine Native draft/post/inverse.
No pre-filled posted payment, journal, cash balance or historical prefix.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import copy,json,threading,time,uuid
import psycopg
import cp7_supplier_payment_cases as supplier
import cp7_invoice_cases as invoice
import cp7_misc_cases as misc
import cp7_transaction_source_cases as navigation
import cp7_supplier_payment_correction_bundle as bundle
auth,b,bc=supplier.auth,supplier.b,supplier.bc
RPC='erp_cp7_correct_supplier_payment_v1'
READ='erp_cp7_get_supplier_payment_correction_v1'
REQUIRED=dict(native=14,races=4,http=3,browser=2)
EXPECTED=sum(REQUIRED.values())

def workspace(cur,f,payment=None,subject=None,**query):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_supplier_payment_correction_v1(%s)',(json.dumps(dict(purchase_id=f['receipt']['purchase_id'],payment_id=payment or f['payment'],**query)),)).fetchone()[0]
    b.api.admin(cur);return r

def correct(cur,p,key=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_correct_supplier_payment_v1(%s,%s)',(json.dumps(p),key or uuid.uuid4())).fetchone()[0]
    b.api.admin(cur);return r

def private_state(cur):
    return {table:cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),'[]')::text)from cp7_supplier_payment_correction."+table+' t').fetchone()[0]for table in('requests','context','links')}

def original_fact(cur,ident):
    return supplier.original_payment(cur,ident)

def fixture(cur,today,amount='30.01',historical=False,qty='100',price='10'):
    day=today-timedelta(days=366)if historical else today
    invoice.aa.prior.set_open_period(cur,day-timedelta(days=20))
    f=invoice.fixture(cur,day,qty,price,True);f['cash']=str(bc.bank_account(cur,'SUPEDIT-'+uuid.uuid4().hex[:8]))
    at=invoice.aa.at(f['day']+timedelta(days=2),12).replace(microsecond=123456)
    ident=str(cur.execute('insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id)values(%s,%s,%s,%s,%s)returning id',(f['receipt']['purchase_id'],'S-'+uuid.uuid4().hex,at,amount,f['cash'])).fetchone()[0])
    auth.actor(cur);cur.execute('select erp.post_supplier_payment(%s)',(ident,));b.api.admin(cur)
    f['payment']=ident;f['original']=workspace(cur,f)['document'];f['original_fact']=original_fact(cur,ident)
    f['physical']=supplier.physical_state(cur);f['cash_before']=str(misc.cash_balance(cur,f['cash']))
    return f

def payload(cur,f,amount='20.01',payment=None,subject=None,**changes):
    w=workspace(cur,f,payment,subject);d=w['document']
    p=dict(purchase_id=f['receipt']['purchase_id'],payment_id=d['id'],review_token=d['review_token'],change_reason='Pembayaran supplier asal dan pengganti diperiksa di lapangan',replacement=dict(amount=amount,cash_account_id=d['cash_account_id'],payment_date=d['payment_date']))
    p['replacement'].update(changes);return p

def check(cur,f,p,r,key=None):
    assert r['contract_version']=='cp7.supplier-payment-correction.v1'and r['action']=='CORRECT'and r['kind']=='COMMITTED_OUTCOME'
    assert r['purchase_id']==p['purchase_id']and r['original_payment_id']==p['payment_id']and r['original_status']=='REVERSED'and r['status']=='POSTED'and r['request_payload']==p
    assert r['payment_id']!=p['payment_id']and r['link']['original_id']==p['payment_id']and r['link']['replacement_id']==r['payment_id']
    if key is not None:assert r['request_id']==r['link']['request_id']==str(key)
    w=workspace(cur,f,r['payment_id']);old=workspace(cur,f,p['payment_id']);d=w['document']
    assert old['document']['status']=='REVERSED'and d['status']=='POSTED'and w['previous']['document']==old['document']and old['next']['document']==d
    assert D(d['amount'])==D(p['replacement']['amount'])and d['cash_account_id']==p['replacement']['cash_account_id']
    assert cur.execute('select payment_date=%s::timestamptz from erp.supplier_payments where id=%s',(p['replacement']['payment_date'],r['payment_id'])).fetchone()[0]
    if p['payment_id']==f['payment']:
        old_fact=original_fact(cur,f['payment']);omit=('status','updated_at','row_version')
        assert {k:v for k,v in old_fact.items()if k not in omit}=={k:v for k,v in f['original_fact'].items()if k not in omit}
    assert supplier.physical_state(cur)==f['physical']
    assert not cur.execute('select exists(select 1 from cp7_supplier_payment_correction.context)').fetchone()[0]
    original=old['document']['journal'];inv=old['document']['inverse'];t=r['link']['time_restatement']
    if original['economic_date']==inv['economic_date']:assert t is None
    else:
        assert t and t['effective_economic_date']==original['economic_date']and t['neutral_economic_date']==inv['economic_date']
        def lines(ident):return sorted(cur.execute('select account_id,debit,credit,description,customer_id,vendor_id,contractor_id,po_id,product_id from erp.journal_lines where journal_entry_id=%s',(ident,)).fetchall(),key=str)
        inv_lines=lines(inv['id']);assert lines(t['effective_journal_id'])==inv_lines
        assert lines(t['neutral_journal_id'])==sorted([(a,c,d,*rest)for a,d,c,*rest in inv_lines],key=str)
    return w

def cash_prefixes(cur,f,days):
    bank=cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(f['cash'],)).fetchone()[0]
    return[(str(day),str(value))for day,value in cur.execute("select d.day,coalesce(sum(l.debit-l.credit),0)from unnest(%s::date[])d(day)left join erp.journal_entries j on j.economic_date<=d.day and j.status in('POSTED','REVERSED')left join erp.journal_lines l on l.journal_entry_id=j.id and l.account_id=%s group by d.day order by d.day",(days,bank)).fetchall()]

def year_fixture(cur,today):
    f=fixture(cur,today,'60.00',True);at=cur.execute('select payment_date from erp.supplier_payments where id=%s',(f['payment'],)).fetchone()[0];days=[]
    for n in range(1,365):
        ident=str(cur.execute('insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id)values(%s,%s,%s,1,%s)returning id',(f['receipt']['purchase_id'],'L-'+uuid.uuid4().hex,at+timedelta(days=n),f['cash'])).fetchone()[0])
        auth.actor(cur);cur.execute('select erp.post_supplier_payment(%s)',(ident,));b.api.admin(cur)
        days.append(cur.execute("select economic_date from erp.journal_entries where source_type='SUPPLIER_PAYMENT'and source_id=%s and reversal_of_id is null",(ident,)).fetchone()[0])
    f['days']=days;f['physical']=supplier.physical_state(cur);f['prefix_before']=cash_prefixes(cur,f,days);return f

def year_check(cur,f,p,r):
    w=check(cur,f,p,r);after=cash_prefixes(cur,f,f['days']);before=f['prefix_before'];assert len(before)==len(after)==364
    assert all(x[0]==y[0]and D(y[1])-D(x[1])==D('12')for x,y in zip(before,after))
    assert w['Native_AP']['paid']=='412.00'and w['Native_AP']['remaining']=='588.00'
    return dict(status='PASS',later_cash_prefixes_checked=364,each_cash_prefix_delta='+12',raw_before=before,raw_after=after,original_payment_all_unchanged_non_lifecycle_fields=True,Native_stock_HPP_unchanged=True)

def cases(cur,today):
    def exact():
        f=fixture(cur,today);p=payload(cur,f);r=correct(cur,p);w=check(cur,f,p,r)
        assert w['Native_AP']['paid']=='20.01'and w['Native_AP']['remaining']=='979.99'and misc.cash_balance(cur,f['cash'])-D(f['cash_before'])==10
        return dict(status='PASS',Native_inverse30_01_replacement20_01_cash_plus10_AP_remaining_plus10=True)
    def large():
        f=fixture(cur,today,'90071992547409.91',qty='100',price='900719925474.0993');p=payload(cur,f,'90071992547409.92');r=correct(cur,p);w=check(cur,f,p,r)
        assert w['Native_AP']['paid']=='90071992547409.92'and misc.cash_balance(cur,f['cash'])-D(f['cash_before'])==D('-.01')
        return dict(status='PASS',exact_cent_units_above_JS_safe_integer='9007199254740992',Native_cash_minus_one_cent=True)
    def full():
        f=fixture(cur,today,'1000.00');p=payload(cur,f,'999.99');w=check(cur,f,p,correct(cur,p));assert w['Native_AP']['remaining']=='0.01'
        return dict(status='PASS',fully_paid_receipt_corrected_native_remaining_one_cent=True)
    def account():
        f=fixture(cur,today);other=bc.bank_account(cur,'SUPEDIT-B-'+uuid.uuid4().hex[:8]);p=payload(cur,f,cash_account_id=other);before=misc.cash_balance(cur,other);check(cur,f,p,correct(cur,p))
        assert misc.cash_balance(cur,f['cash'])-D(f['cash_before'])==D('30.01')and misc.cash_balance(cur,other)-before==D('-20.01')
        return dict(status='PASS',old_bank_return30_01_new_bank_out20_01=True)
    def micros():
        f=fixture(cur,today);p=payload(cur,f);w=check(cur,f,p,correct(cur,p));assert w['document']['payment_date']==f['original']['payment_date']and '123456'in w['document']['payment_date']
        return dict(status='PASS',untouched_original_clock_microseconds_preserved=True)
    def date_move():
        f=fixture(cur,today,historical=True);old=workspace(cur,f)['document']['journal']['economic_date'];day=cur.execute('select %s::date+1',(old,)).fetchone()[0];p=payload(cur,f,payment_date=invoice.aa.at(day,12).isoformat());w=check(cur,f,p,correct(cur,p));assert w['document']['journal']['economic_date']==str(day)
        return dict(status='PASS',actual_Native_original_economic_day_plus_one=True)
    def year():
        f=year_fixture(cur,today);p=payload(cur,f,'48.00');return year_check(cur,f,p,correct(cur,p))
    def failure():
        f=fixture(cur,today,historical=True);p=payload(cur,f)
        cur.execute("create function public.cp7_supplier_edit_last_fail()returns trigger language plpgsql as $$begin if new.source_type='SUPPLIER_PAYMENT'and new.source_id<>'"+f['payment']+"'::uuid then raise exception 'CP7_TEST_SUPPLIER_REPLACEMENT_POST_FAILURE';end if;return new;end$$;create trigger cp7_supplier_edit_last_fail before insert on erp.journal_entries for each row execute function public.cp7_supplier_edit_last_fail()",prepare=False)
        before=b.boundary.snapshot(cur);private=private_state(cur);auth.refused(cur,lambda:correct(cur,p),'CP7_TEST_SUPPLIER_REPLACEMENT_POST_FAILURE');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        assert workspace(cur,f)['document']['status']=='POSTED'
        return dict(status='PASS',actual_last_Native_replacement_journal_insert_failure_rolls_back_original_inverse_time_entries_new_draft_and_private_request=True)
    def stale():
        f=fixture(cur,today);other=fixture(cur,today);f['physical']=supplier.physical_state(cur);p=payload(cur,f);bad={**p,'purchase_id':other['receipt']['purchase_id']};before=b.boundary.snapshot(cur);auth.refused(cur,lambda:correct(cur,bad),'CP7_SUPPLIER_PAYMENT_NOT_FOUND');assert b.boundary.snapshot(cur)==before
        ident=bc.supplier_payment(cur,p['purchase_id'],'1.00',f['cash'],f['day']+timedelta(days=2));auth.actor(cur);cur.execute('select erp.post_supplier_payment(%s)',(ident,));b.api.admin(cur);before=b.boundary.snapshot(cur);auth.refused(cur,lambda:correct(cur,p),'CP7_SUPPLIER_PAYMENT_STALE_REVIEW');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',foreign_parent_and_actual_peer_payment_AP_change_stale_no_effect=True)
    def authority():
        f=fixture(cur,today);subject,role=supplier.admin_actor(cur);p=payload(cur,f,subject=subject);key=uuid.uuid4();r=correct(cur,p,key,subject)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,));before=b.boundary.snapshot(cur);auth.refused(cur,lambda:correct(cur,p,key,subject),'CP7_SUPPLIER_PAYMENT_CORRECTION_DENIED');assert b.boundary.snapshot(cur)==before
        other,_=invoice.receipt.custom(cur,supplier.PERMISSIONS);assert workspace(cur,f,r['payment_id'],other)['can_correct']is False;auth.refused(cur,lambda:correct(cur,p,subject=other),'CP7_SUPPLIER_PAYMENT_CORRECTION_DENIED');bundle.verify(cur)
        return dict(status='PASS',current_pay_permission_before_cache_and_custom_role_readonly=True,private_caps_no_App_ERP_DML=True)
    def fields():
        f=fixture(cur,today);p=payload(cur,f);before=b.boundary.snapshot(cur)
        for change in [{'extra':'unowned'},{'amount':'0.00'},{'amount':'1.001'},{'payment_date':None}]:
            bad=copy.deepcopy(p);bad['replacement'].update(change);auth.refused(cur,lambda:correct(cur,bad),'CP7_SUPPLIER_PAYMENT_CORRECTION_FIELDS');assert b.boundary.snapshot(cur)==before
        bad=payload(cur,f,f['original']['amount']);auth.refused(cur,lambda:correct(cur,bad),'CP7_SUPPLIER_PAYMENT_CORRECTION_UNCHANGED');assert b.boundary.snapshot(cur)==before
        bank=bc.bank_account(cur,'SUP-INACTIVE-'+uuid.uuid4().hex[:8]);cur.execute('update erp.cash_accounts set is_active=false where id=%s',(bank,));p['replacement']['cash_account_id']=bank;before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:correct(cur,p),'');assert b.boundary.snapshot(cur)==before
        p=payload(cur,f,'1000.01');auth.refused(cur,lambda:correct(cur,p),'');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',closed_fields_positive_exact_cents_noop_inactive_bank_overpayment_all_atomic=True)
    def replay():
        f=fixture(cur,today,historical=True);p=payload(cur,f);key=uuid.uuid4();one=correct(cur,p,key);check(cur,f,p,one,key);before=b.boundary.snapshot(cur);private=private_state(cur);assert correct(cur,p,key)==one and b.boundary.snapshot(cur)==before and private_state(cur)==private
        changed=copy.deepcopy(p);changed['replacement']['amount']='21.01';auth.refused(cur,lambda:correct(cur,changed,key),'CP7_SUPPLIER_PAYMENT_REQUEST_CHANGED')
        restore=payload(cur,f,'30.01',one['payment_id']);restore['replacement']['payment_date']=f['original']['payment_date'];two=correct(cur,restore);w=check(cur,f,restore,two);assert w['Native_AP']['paid']=='30.01'and misc.cash_balance(cur,f['cash'])==D(f['cash_before'])
        assert cur.execute('select count(*)from cp7_supplier_payment_correction.links where purchase_id=%s',(p['purchase_id'],)).fetchone()[0]==2
        return dict(status='PASS',identical_cached_UUID_no_second_effect_changed_intent_refused_restore_is_second_immutable_link=True)
    def history():
        f=fixture(cur,today,historical=True);p=payload(cur,f);r=correct(cur,p);check(cur,f,p,r)
        for sql in ['update cp7_supplier_payment_correction.links set reason=reason','delete from cp7_supplier_payment_correction.links','truncate cp7_supplier_payment_correction.links']:auth.refused(cur,lambda:cur.execute(sql),'CP7_SUPPLIER_PAYMENT_CORRECTION_LINK_IMMUTABLE')
        for kind in ['SUPPLIER_PAYMENT_CORRECTION_TIME_NEUTRAL','SUPPLIER_PAYMENT_CORRECTION_EFFECTIVE']:
            navigation.exact(cur,kind,f['payment'],'RECEIPT',p['purchase_id'],('SUPPLIER_PAYMENT',f['payment']))
            auth.refused(cur,lambda:navigation.read(cur,kind,str(uuid.uuid4())),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
        return dict(status='PASS',immutable_all_history_DML_and_exact_real_time_journal_sources_no_fake_UUID=True)
    def closed():
        f=fixture(cur,today,historical=True);through=today-timedelta(days=1);cur.execute('update erp.accounting_period_control set closed_through=%s where singleton_id=1',(through,));before=cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall();p=payload(cur,f);r=correct(cur,p);check(cur,f,p,r)
        assert cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall()==before
        assert cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]==through
        assert r['link']['time_restatement']['effective_transaction_date']>str(through)
        return dict(status='PASS',closed_daily_GL_not_rewritten_original_economic_and_Native_open_posting_date=True)
    named=[('EXACT_CENTS',exact),('LARGE_CENTS',large),('FULLY_PAID',full),('NEW_ACCOUNT',account),('MICROSECONDS',micros),('DATE_MOVE',date_move),('YEAR_364',year),('FINAL_POST_FAILURE',failure),('STALE_FOREIGN',stale),('CURRENT_PERMISSIONS',authority),('CLOSED_FIELDS_INACTIVE',fields),('REPLAY_RESTORE',replay),('IMMUTABLE_HISTORY_SOURCE',history),('CLOSED_BOOKS',closed)]
    assert len(named)==REQUIRED['native'];return [('CP7_SUPPLIER_PAYMENT_CORRECTION_'+name,fn)for name,fn in named]

def races(tools,today):
    def double(same):
        with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p=payload(cur,f);conn.commit()
        barrier=threading.Barrier(2);key=str(uuid.uuid4())
        def send(n):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=correct(cur,p,key if same else str(uuid.uuid4()));conn.commit();return ('OK',r)
                except psycopg.Error as e:conn.rollback();return('ERROR',str(e))
        with ThreadPoolExecutor(max_workers=2)as pool:a=pool.submit(send,0);z=pool.submit(send,1);rows=[a.result(30),z.result(30)]
        successes=[r for s,r in rows if s=='OK'];assert len(successes)==(2 if same else 1)
        if same:assert successes[0]==successes[1]
        with tools.connect()as conn,conn.cursor()as cur:check(cur,f,p,successes[0]);assert cur.execute('select count(*)from cp7_supplier_payment_correction.links where purchase_id=%s',(p['purchase_id'],)).fetchone()[0]==1
        return dict(status='PASS',real_concurrent_same_UUID=same,one_Native_inverse_replacement_link=True)
    def retire(bank):
        with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);subject,role=supplier.admin_actor(cur);p=payload(cur,f,subject=subject);conn.commit()
        holder=tools.connect();holder.cursor().execute('select 1 from erp.supplier_payments where id=%s for update',(f['payment'],));ready=threading.Event();pid=[]
        def send():
            with tools.connect()as conn,conn.cursor()as cur:
                pid.append(cur.execute('select pg_backend_pid()').fetchone()[0]);ready.set()
                try:correct(cur,p,subject=subject);conn.commit();return'UNEXPECTED_COMMIT'
                except psycopg.Error as e:conn.rollback();return str(e)
        try:
            with ThreadPoolExecutor(max_workers=1)as pool:
                future=pool.submit(send)
                try:
                    assert ready.wait(5);deadline=time.monotonic()+8;blocked=False
                    with tools.connect()as conn,conn.cursor()as cur:
                        while time.monotonic()<deadline:
                            blocked=bool(cur.execute('select pg_blocking_pids(%s)',(pid[0],)).fetchone()[0]);conn.rollback()
                            if blocked:break
                            time.sleep(.02)
                        assert blocked,'SUPPLIER_CORRECTION_ACTUAL_LOCK_WAIT_NOT_OBSERVED'
                        if bank:cur.execute('update erp.cash_accounts set is_active=false where id=%s',(f['cash'],))
                        else:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,))
                        conn.commit()
                finally:holder.rollback()
                result=future.result(30);assert result!='UNEXPECTED_COMMIT'
        finally:holder.rollback();holder.close()
        with tools.connect()as conn,conn.cursor()as cur:assert original_fact(cur,f['payment'])['status']=='POSTED'and cur.execute('select count(*)from cp7_supplier_payment_correction.requests').fetchone()[0]==0
        return dict(status='PASS',actual_source_lock_observed_before_current_bank_retire=bank,actual_source_lock_observed_before_current_authority_revoke=not bank,no_partial_effect_or_request=True)
    return [('CP7_SUPPLIER_PAYMENT_CORRECTION_RACE_SAME_UUID',lambda:double(True)),('CP7_SUPPLIER_PAYMENT_CORRECTION_RACE_COMPETING',lambda:double(False)),('CP7_SUPPLIER_PAYMENT_CORRECTION_RACE_AUTH_RETIRE',lambda:retire(False)),('CP7_SUPPLIER_PAYMENT_CORRECTION_RACE_BANK_RETIRE',lambda:retire(True))]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','supplier-correction-owner')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today,historical=True);p=payload(cur,f);conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()));assert http.anon_rpc(RPC,args)['status']in(401,403);r=owner.rpc(RPC,args);assert r['status']==200,r;assert owner.rpc(RPC,args)['body']==r['body']
        with http.connect()as conn,conn.cursor()as cur:check(cur,f,p,r['body'],args['p_request']);conn.rollback()
        changed=copy.deepcopy(args);changed['p_payload']['replacement']['amount']='21.01';assert owner.rpc(RPC,changed)['status']>=400
        return dict(status='PASS',actual_Auth_atomic_write_exact_UUID_replay_native_history_changed_intent_and_anon_refused=True)
    def year():
        owner=http.login('OWNER','supplier-correction-year')
        with http.connect()as conn,conn.cursor()as cur:f=year_fixture(cur,today);p=payload(cur,f,'48.00');conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()));start=time.monotonic_ns();r=owner.rpc(RPC,args);elapsed=(time.monotonic_ns()-start)/1_000_000;assert r['status']==200,r
        with http.connect()as conn,conn.cursor()as cur:result=year_check(cur,f,p,r['body']);conn.rollback()
        assert owner.rpc(RPC,args)['body']==r['body'];return dict(result,actual_Auth_committed_year_readback=True,actual_HTTP_ms=round(elapsed,3),production_SLA=False)
    def revoke():
        admin=http.login('ADMIN','supplier-correction-current')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p=payload(cur,f);conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()));r=admin.rpc(RPC,args);assert r['status']==200,r
        with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin.auth_user_id,));conn.commit()
        assert admin.rpc(RPC,args)['status']==403 and admin.rpc(READ,dict(p_query=dict(purchase_id=p['purchase_id'],payment_id=r['body']['payment_id'])))['status']==403
        return dict(status='PASS',current_actual_Auth_deactivation_denies_cached_write_and_history=True)
    return [('CP7_SUPPLIER_PAYMENT_CORRECTION_HTTP_ATOMIC_REPLAY',flow),('CP7_SUPPLIER_PAYMENT_CORRECTION_HTTP_YEAR_364',year),('CP7_SUPPLIER_PAYMENT_CORRECTION_HTTP_CURRENT_RETIRE',revoke)]
