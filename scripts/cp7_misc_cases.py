"""Actual native miscellaneous documents/accounting; no mocked business writer."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import hashlib,json,uuid,threading,time
import psycopg
import cp7_finance_analysis_cases as source
import cp7_misc_bundle as bundle
b,auth=source.b,source.auth

def read(cur,query=None,subject=None):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_misc_finance_v1(%s)',(json.dumps(query or {}),)).fetchone()[0];b.api.admin(cur);return r
def command(cur,action,payload,key=None,subject=None,expected=None):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_save_misc_finance_v1(%s,%s,%s,%s)',(action,json.dumps(payload),key or uuid.uuid4(),expected)).fetchone()[0];b.api.admin(cur);return r
def stock_cost(cur):
    return {t:cur.execute('select md5(coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),\'[]\')::text)from erp.'+t+' t').fetchone()[0]for t in('material_stock_movements','fg_stock_movements','production_orders','po_hpp_gl_state','cost_recalc_queue')}
def cash_balance(cur,bank):
    return cur.execute("select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED')and l.account_id=(select coa_account_id from erp.cash_accounts where id=%s)",(bank,)).fetchone()[0]
def fixture(cur,today):
    b.api.admin(cur);source.receipt.aa.prior.set_open_period(cur,today-timedelta(days=3));tag='F03MISC'+uuid.uuid4().hex[:10];categories={}
    for kind,mapping in [('OTHER_INCOME','OTHER_INCOME'),('OTHER_EXPENSE','OTHER_EXPENSE')]:
        categories[kind]=str(cur.execute('insert into erp.misc_finance_categories(category_code,category_name,category_type,default_account_id)values(%s,%s,%s,erp.account_id(%s))returning id',(tag+kind,tag+' '+kind,kind,mapping)).fetchone()[0])
    bank=str(cur.execute("select c.id from erp.cash_accounts c join erp.chart_accounts a on a.id=c.coa_account_id where c.is_active and a.is_active and a.is_postable and a.account_type='ASSET'and not exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id and m.mapping_key not in('CASH','BANK'))order by c.cash_account_code,c.id limit 1").fetchone()[0])
    opts={kind:cur.execute('select cp7_misc.category(%s)',(ident,)).fetchone()[0]for kind,ident in categories.items()};cash=cur.execute('select cp7_misc.cash(%s)',(bank,)).fetchone()[0]
    return dict(tag=tag,categories=opts,cash=cash,today=str(today),physical=str(today-timedelta(days=1))+'T08:00:00+07:00',stock_cost=stock_cost(cur),cash_before=str(cash_balance(cur,bank)))
def save_payload(f,kind='OTHER_EXPENSE',amount='12.34'):
    c=f['categories'][kind];bank=f['cash']
    return dict(transaction_id=None,review_token=None,transaction_number=f['tag']+'-'+uuid.uuid4().hex[:8],transaction_type=kind,category_id=c['id'],category_review_token=c['review_token'],cash_account_id=bank['id'],cash_review_token=bank['review_token'],physical_at=f['physical'],amount=amount,counterparty_name='Disposable audited counterparty',reference_number='Audited reference',notes='Actual native misc source',change_reason='Native source and exact money reviewed')
def intent(r):return dict(transaction_id=r['transaction_id'],review_token=r['document']['review_token'],change_reason='Native source and financial effect reviewed')
def native_document(cur,ident):return cur.execute('select cp7_misc.source(%s)',(ident,)).fetchone()[0]
def compare(a,n):
    a=dict(a);n=dict(n);a.pop('captured_at',None);n.pop('captured_at',None);assert a==n
def cases(cur,today):
    def draft():
        f=fixture(cur,today);money='9007199254740993.01';p=save_payload(f,amount=money);before_cash=cash_balance(cur,f['cash']['id']);r=command(cur,'SAVE',p);d=r['document']
        assert d==native_document(cur,r['transaction_id'])and d['amount']==money and d['status']=='DRAFT'and d['journals']==[]
        assert cur.execute("select count(*)from erp.audit_logs where entity_type='misc_finance_transactions'and entity_id=%s and action='INSERT'and change_reason=%s",(d['id'],p['change_reason'])).fetchone()[0]==1
        p.update(transaction_id=d['id'],review_token=d['review_token'],amount='12.34',notes='Corrected reviewed draft');changed=command(cur,'SAVE',p)
        assert changed['document']['amount']=='12.34'and changed['document']['review_token']!=d['review_token']and cash_balance(cur,f['cash']['id'])==before_cash and stock_cost(cur)==f['stock_cost']
        return dict(status='PASS',actual_native_draft_create_edit_exact_large_money=True,no_draft_cash_journal_or_physical_cost_effect=True)
    def accounting():
        f=fixture(cur,today);before=cash_balance(cur,f['cash']['id']);ids=[]
        for kind,value in [('OTHER_INCOME','200.00'),('OTHER_EXPENSE','50.01')]:
            saved=command(cur,'SAVE',save_payload(f,kind,value));r=command(cur,'POST',intent(saved));d=r['document'];ids.append(d['id']);assert d['status']=='POSTED'and len(d['journals'])==1
            rows=cur.execute('select account_id,debit,credit from erp.journal_lines where journal_entry_id=%s',(d['journals'][0]['id'],)).fetchall();expected={f['cash']['account_id']:(D(value),D(0))if kind=='OTHER_INCOME'else(D(0),D(value)),f['categories'][kind]['account_id']:(D(0),D(value))if kind=='OTHER_INCOME'else(D(value),D(0))}
            assert {str(i):(debit,credit)for i,debit,credit in rows}==expected
        assert cash_balance(cur,f['cash']['id'])-before==D('149.99')and stock_cost(cur)==f['stock_cost']
        return dict(status='PASS',native_income200_expense50_01_cash_delta149_99=True,actual_two_account_lines_each_match_native=True,no_stock_or_production_cost_effect=True)
    def inverse():
        f=fixture(cur,today);before=cash_balance(cur,f['cash']['id']);saved=command(cur,'SAVE',save_payload(f));posted=command(cur,'POST',intent(saved));orig=posted['document']['journals'][0];r=command(cur,'REVERSE',intent(posted));d=r['document']
        assert d['status']=='REVERSED'and len(d['journals'])==2;old=next(j for j in d['journals']if j['id']==orig['id']);new=next(j for j in d['journals']if j['reversal_of_id']==old['id'])
        assert old['status']=='REVERSED'and old['economic_date']==old['transaction_date']==f['physical'][:10]and new['transaction_date']==str(today)and D(new['debit'])==D(new['credit'])==D('12.34')and cash_balance(cur,f['cash']['id'])==before
        assert old['id']==orig['id']and old['posting_at']==orig['posting_at']and d['amount']=='12.34'and d['physical_at']==posted['document']['physical_at']and stock_cost(cur)==f['stock_cost']
        return dict(status='PASS',original_source12_34_and_prior_journal_date_retained=True,linked_native_inverse12_34_today_restores_cash=True,no_source_or_stock_rewrite=True)
    def stale():
        f=fixture(cur,today);p=save_payload(f);cur.execute('update erp.misc_finance_categories set category_name=category_name||\' changed\'where id=%s',(p['category_id'],));before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'SAVE',p),'CP7_MISC_OPTIONS_CHANGED');assert b.boundary.snapshot(cur)==before
        f['categories']['OTHER_EXPENSE']=cur.execute('select cp7_misc.category(%s)',(p['category_id'],)).fetchone()[0];saved=command(cur,'SAVE',save_payload(f));old=intent(saved);edit=save_payload(f);edit.update(transaction_id=saved['transaction_id'],review_token=old['review_token'],amount='22.22');command(cur,'SAVE',edit);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,'POST',old),'CP7_MISC_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',actual_master_change_and_document_change_retire_review=True,no_money_or_request_effect_on_stale_refusal=True)
    def fields():
        f=fixture(cur,today);p=save_payload(f);before=b.boundary.snapshot(cur)
        for change in({'amount':12.34},{'amount':'0'},{'amount':'1.234'},{'amount':'-1'},{'amount':'1e3'},{'cash_account_id':'bad'},{'physical_at':'2026-02-30T08:00:00Z'},{'physical_at':str(today+timedelta(days=1))+'T08:00:00Z'},{'physical_at':str(today)+'T08:00:00'},{'change_reason':'x'},{'force':True}):
            auth.refused(cur,lambda:command(cur,'SAVE',dict(p,**change)),'CP7_MISC_')
        auth.refused(cur,lambda:command(cur,'SAVE',p,expected='1'),'CP7_MISC_COMMAND_FIELDS');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',closed_decimal_uuid_date_fields_and_no_invented_revision=True,atomic_refusals=True)
    def protected():
        f=fixture(cur,today);category=f['categories']['OTHER_INCOME']['id'];before=b.boundary.snapshot(cur)
        # The accepted native master trigger refuses the unsafe category itself.
        # Keep that guard active; an unlawful fixture is not an allowed setup.
        auth.refused(cur,lambda:cur.execute("update erp.misc_finance_categories set default_account_id=erp.account_id('SALES_REVENUE')where id=%s",(category,)),'reserved for a core ERP workflow');assert b.boundary.snapshot(cur)==before
        core=str(cur.execute("select erp.account_id('SALES_REVENUE')").fetchone()[0]);assert not cur.execute('select exists(select 1 from erp.misc_finance_categories where id=%s)',(core,)).fetchone()[0]
        p=save_payload(f,'OTHER_INCOME');p['category_id']=core;auth.refused(cur,lambda:command(cur,'SAVE',p),'CP7_MISC_SOURCE_UNAVAILABLE');assert b.boundary.snapshot(cur)==before
        assert all(c['account_id']!=core for c in read(cur)['categories']['rows'])
        return dict(status='PASS',actual_native_master_guard_refuses_core_sales_category=True,facade_refuses_raw_core_account_instead_of_category=True,no_misc_route_for_core_stock_HPP_AP_AR_workflows=True)
    def replay():
        f=fixture(cur,today);key=uuid.uuid4();p=save_payload(f);saved=command(cur,'SAVE',p,key);before=b.boundary.snapshot(cur);assert command(cur,'SAVE',p,key)==saved and b.boundary.snapshot(cur)==before
        auth.refused(cur,lambda:command(cur,'SAVE',dict(p,amount='22.22'),key),'CP7_MISC_REQUEST_CHANGED');assert b.boundary.snapshot(cur)==before
        key=uuid.uuid4();p=intent(saved);posted=command(cur,'POST',p,key);before=b.boundary.snapshot(cur);assert command(cur,'POST',p,key)==posted and b.boundary.snapshot(cur)==before
        assert cur.execute('select count(*)from cp7_misc.requests where request_id=%s',(key,)).fetchone()[0]==1
        return dict(status='PASS',identical_UUID_intent_returns_exact_saved_outcome_with_one_effect=True,changed_intent_refused_atomically=True)
    def access():
        f=fixture(cur,today);subject,role=auth.custom_actor(cur)
        for permission in('finance.journal.view','finance.cash.view'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,permission))
        auth.refused(cur,lambda:read(cur,subject=subject),'CP7_MISC_OWNER_ADMIN_REQUIRED');auth.refused(cur,lambda:command(cur,'SAVE',save_payload(f),subject=subject),'CP7_MISC_OWNER_ADMIN_REQUIRED')
        bundle.verify(cur);return dict(status='PASS',custom_role_with_both_view_permissions_cannot_write=True,no_app_ERP_DML_native_EXEC_or_private_context=True)
    def pages():
        f=fixture(cur,today);ids=[]
        for _ in range(30):ids.append(command(cur,'SAVE',save_payload(f))['transaction_id'])
        before=b.boundary.snapshot(cur);q=dict(q=f['tag'],offset=0,status='DRAFT');a=read(cur,q);z=read(cur,dict(q,offset=25));assert a['page']['total']==z['page']['total']=='30'and[len(x['page']['rows'])for x in(a,z)]==[25,5]and{x['id']for page in(a,z)for x in page['page']['rows']}==set(ids)
        chosen=read(cur,dict(q,transaction_id=ids[0]))['detail'];assert chosen==native_document(cur,ids[0]);assert b.boundary.snapshot(cur)==before
        cur.execute("set local timezone='America/Los_Angeles'");compare(read(cur,q),a)
        return dict(status='PASS',actual_native30_drafts_pages25_plus5_exact_source=True,detail_and_caller_timezone_native_source_unchanged=True,no_read_business_effect=True)
    return [('F03_MISC_'+name,fn)for name,fn in [('DRAFT_EXACT',draft),('POST_ACCOUNTING',accounting),('INVERSE_DATES',inverse),('STALE_REVIEW',stale),('FIELDS',fields),('PROTECTED_ACCOUNTS',protected),('REPLAY',replay),('CURRENT_ACCESS_PRIVATE',access),('PAGES',pages)]]

def races(tools,today):
    def duplicate():
        with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);saved=command(cur,'SAVE',save_payload(f));conn.commit()
        gate=threading.Barrier(2);key=uuid.uuid4();p=intent(saved)
        def send():
            with tools.connect()as conn,conn.cursor()as cur:gate.wait();r=command(cur,'POST',p,key);conn.commit();return r
        with ThreadPoolExecutor(max_workers=2)as pool:jobs=[pool.submit(send)for _ in range(2)];rows=[j.result(30)for j in jobs]
        assert rows[0]==rows[1]
        with tools.connect()as conn,conn.cursor()as cur:
            assert cur.execute('select count(*)from cp7_misc.requests where request_id=%s',(key,)).fetchone()[0]==1
            assert cur.execute("select count(*)from erp.journal_entries where source_type='MISC_FINANCE'and source_id=%s",(saved['transaction_id'],)).fetchone()[0]==1
        return dict(status='PASS',two_real_transactions_one_UUID_one_native_journal=True)
    def revoke():
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            for permission in('finance.journal.view','finance.cash.view'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
            cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));p=save_payload(f);key=uuid.uuid4();saved=command(cur,'SAVE',p,key,subject);conn.commit()
        with tools.connect()as holder,holder.cursor()as cur:
            cur.execute('select 1 from cp7_misc.requests where actor=%s and request_id=%s for update',(subject,key))
            def send():
                with tools.connect()as conn,conn.cursor()as cur:
                    try:r=command(cur,'SAVE',p,key,subject);conn.commit();return r
                    except psycopg.Error as e:conn.rollback();return str(e)
            with ThreadPoolExecutor(max_workers=1)as pool:
                job=pool.submit(send);waiting=False;deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    with tools.connect()as conn,conn.cursor()as cur:waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event_type='Lock'and query like 'select public.erp_cp7_save_misc_finance_v1%')").fetchone()[0]
                    if waiting:break
                    time.sleep(.05)
                try:
                    assert waiting,'Cached request wait was not observed'
                    with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.cash.view'",(role,));conn.commit()
                finally:holder.rollback()
                result=job.result(30)
        assert isinstance(result,str)and'CP7_MISC_ACCESS_DENIED'in result,result
        with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select response from cp7_misc.requests where request_id=%s',(key,)).fetchone()[0]==saved
        return dict(status='PASS',current_revocation_during_observed_request_lock_blocks_cached_reply=True,original_outcome_retained=True)
    return [('F03_MISC_RACE_REPLAY',duplicate),('F03_MISC_RACE_CURRENT_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','f03-misc-owner')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);conn.commit()
        payload=save_payload(f);args=dict(p_action='SAVE',p_payload=payload,p_request=str(uuid.uuid4()),p_expected=None)
        assert http.anon_rpc('erp_cp7_save_misc_finance_v1',args)['status']in(401,403)
        r=owner.rpc('erp_cp7_save_misc_finance_v1',args);assert r['status']==200,r;saved=r['body'];assert owner.rpc('erp_cp7_save_misc_finance_v1',args)['body']==saved
        post=dict(p_action='POST',p_payload=intent(saved),p_request=str(uuid.uuid4()),p_expected=None);r=owner.rpc('erp_cp7_save_misc_finance_v1',post);assert r['status']==200,r;posted=r['body'];assert owner.rpc('erp_cp7_save_misc_finance_v1',post)['body']==posted
        q=dict(q=f['tag'],transaction_id=posted['transaction_id']);r=owner.rpc('erp_cp7_get_misc_finance_v1',dict(p_query=q));assert r['status']==200,r
        with http.connect()as conn,conn.cursor()as cur:compare(r['body'],read(cur,q));assert D(cash_balance(cur,f['cash']['id']))-D(f['cash_before'])==D('-12.34');assert stock_cost(cur)==f['stock_cost'];conn.rollback()
        inverse=dict(p_action='REVERSE',p_payload=intent(posted),p_request=str(uuid.uuid4()),p_expected=None);r=owner.rpc('erp_cp7_save_misc_finance_v1',inverse);assert r['status']==200 and r['body']['document']['status']=='REVERSED',r
        with http.connect()as conn,conn.cursor()as cur:assert cash_balance(cur,f['cash']['id'])==D(f['cash_before']);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_misc_finance_v1',post)['status']==403 and owner.rpc('erp_cp7_get_misc_finance_v1',dict(p_query=q))['status']==403
        return dict(status='PASS',actual_Auth_save_post_inverse_exact_replay_and_native_read=True,expense12_34_and_inverse_restore_cash=True,current_deactivation_blocks_cached_reply=True)
    return [('F03_MISC_REAL_HTTP',flow)]
