"""Predeclared actual Native atomic correction controls; no economic seeds.

The late-failure case adds and removes one explicit disposable fault trigger.
All real documents, money and journal lines still use accepted Native writers.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import copy,json,threading,time,uuid
import psycopg
import cp7_misc_cases as misc
import cp7_misc_correction_bundle as bundle
import cp7_transaction_source_cases as navigation

b,auth=misc.b,misc.auth
REQUIRED=dict(native=14,races=2,http=2,browser=2)
EXPECTED=sum(REQUIRED.values())
RPC='erp_cp7_correct_misc_finance_v1'
HISTORY='erp_cp7_get_misc_correction_history_v1'

def correct(cur,p,key=None,subject=None):
 auth.actor(cur,subject)
 r=cur.execute('select public.erp_cp7_correct_misc_finance_v1(%s,%s)',(json.dumps(p),key or uuid.uuid4())).fetchone()[0]
 b.api.admin(cur);return r

def history(cur,ident,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_misc_correction_history_v1(%s)',(ident,)).fetchone()[0];b.api.admin(cur);return r

def private_state(cur):
 return {table:cur.execute('select md5(coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),\'[]\')::text)from '+table+' t').fetchone()[0]
  for table in('cp7_misc.requests','cp7_misc.command_context','cp7_misc_correction.links')}

def posted(cur,f,kind='OTHER_EXPENSE',amount='12.34'):
 saved=misc.command(cur,'SAVE',misc.save_payload(f,kind,amount));return misc.command(cur,'POST',misc.intent(saved))

def payload(f,old,amount='9.99',kind=None):
 p=misc.save_payload(f,kind or old['document']['type'],amount)
 p.update(transaction_number=old['document']['number'],physical_at=old['document']['physical_at'],counterparty_name=old['document']['counterparty_name'],reference_number=old['document']['reference_number'],notes=old['document']['notes'],change_reason='Correct actual posted miscellaneous source')
 return dict(transaction_id=old['transaction_id'],review_token=old['document']['review_token'],replacement=p,change_reason=p['change_reason'])

def managed_actor(cur):
 subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
 for permission in('finance.journal.view','finance.cash.view'):
  cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
 cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));return subject,role

def restatement(cur,r):
 old=r['original_document'];original=next(j for j in old['journals']if j['reversal_of_id']is None);inverse=next(j for j in old['journals']if j['reversal_of_id']==original['id']);t=r['link']['time_restatement']
 if original['economic_date']==inverse['economic_date']:assert t is None;return
 assert t and t['effective_economic_date']==original['economic_date']and t['neutral_economic_date']==inverse['economic_date']
 def lines(ident):return sorted(cur.execute('select account_id,debit,credit,customer_id,vendor_id,contractor_id,po_id,product_id from erp.journal_lines where journal_entry_id=%s',(ident,)).fetchall(),key=str)
 inv=lines(inverse['id']);assert lines(t['effective_journal_id'])==inv
 assert lines(t['neutral_journal_id'])==sorted([(a,c,d,*dimensions)for a,d,c,*dimensions in inv],key=str)
 assert all(cur.execute('select source_type,source_id,status from erp.journal_entries where id=%s',(t[k],)).fetchone()==(kind,uuid.UUID(old['id']),'POSTED')for k,kind in[('neutral_journal_id','MISC_CORRECTION_TIME_NEUTRAL'),('effective_journal_id','MISC_CORRECTION_EFFECTIVE')])

def check(cur,f,old,r,key=None):
 assert r['contract_version']=='cp7.misc-correction.v1'and r['action']=='CORRECT'and r['kind']=='COMMITTED_OUTCOME'
 assert set(r)=={'contract_version','kind','action','request_id','transaction_id','original_review_token','original_document','document','link'}
 assert r['original_review_token']==old['document']['review_token']and r['original_document']['id']==old['transaction_id']and r['original_document']['status']=='REVERSED'
 assert r['document']==misc.native_document(cur,r['transaction_id'])and r['document']['status']=='POSTED'
 assert r['original_document']==misc.native_document(cur,old['transaction_id'])
 assert r['link']['original_id']==old['transaction_id']and r['link']['replacement_id']==r['transaction_id']and r['link']['request_id']==r['request_id']
 assert r['document']['number']==old['document']['number'][:20]+' · K-'+r['request_id'].replace('-','')
 if key:assert r['request_id']==str(key)
 assert misc.stock_cost(cur)==f['stock_cost']and not cur.execute('select exists(select 1 from cp7_misc.command_context)').fetchone()[0]
 for field in('id','number','type','category_id','cash_account_id','physical_at','amount','counterparty_name','reference_number','notes'):
  assert r['original_document'][field]==old['document'][field]
 restatement(cur,r)

def cases(cur,today):
 def expense():
  f=misc.fixture(cur,today);old=posted(cur,f);key=uuid.uuid4();r=correct(cur,payload(f,old),key);check(cur,f,old,r,key)
  assert misc.cash_balance(cur,f['cash']['id'])-D(f['cash_before'])==D('-9.99')
  return dict(status='PASS',Native_expense12_34_to9_99_exact_current_cash=True,old_source_and_journal_immutable=True,economic_inverse_at_original_date=True)
 def income():
  f=misc.fixture(cur,today);old=posted(cur,f,'OTHER_INCOME','200.00');r=correct(cur,payload(f,old,'150.01'));check(cur,f,old,r)
  assert misc.cash_balance(cur,f['cash']['id'])-D(f['cash_before'])==D('150.01')
  return dict(status='PASS',Native_income200_to150_01_exact=True)
 def changed_type_cash():
  f=misc.fixture(cur,today);old=posted(cur,f);bank=misc.source.source.bc.bank_account(cur,'MC'+uuid.uuid4().hex[:8]);cash=cur.execute('select cp7_misc.cash(%s)',(bank,)).fetchone()[0];before=misc.cash_balance(cur,bank)
  p=payload(f,old,'20.01','OTHER_INCOME');p['replacement'].update(cash_account_id=cash['id'],cash_review_token=cash['review_token']);r=correct(cur,p);check(cur,f,old,r)
  assert misc.cash_balance(cur,f['cash']['id'])==D(f['cash_before'])and misc.cash_balance(cur,bank)-before==D('20.01')
  return dict(status='PASS',reviewed_actual_income_category_and_separate_cash_account=True,old_cash_neutral_new_cash20_01=True)
 def year30():
  f=misc.fixture(cur,today);day=today-timedelta(days=365);misc.source.receipt.aa.prior.set_open_period(cur,day-timedelta(days=1));f['physical']=str(day)+'T09:00:59.123456+07:00';old=posted(cur,f);later=[]
  for n in range(1,31):
   source=dict(f,physical=str(day+timedelta(days=n))+'T10:00:00+07:00');later.append(posted(cur,source,amount='1.00'))
  before={r['transaction_id']:copy.deepcopy(r['document'])for r in later}
  balances={n:D(misc.source.read(cur,misc.source.query(day+timedelta(days=n)))['cash']['closing'])for n in range(1,31)}
  r=correct(cur,payload(f,old));check(cur,f,old,r)
  for n in range(1,31):
   after=misc.source.read(cur,misc.source.query(day+timedelta(days=n)))['cash'];assert after['reconciled']and D(after['closing'])-balances[n]==D('2.35')
  assert all(misc.native_document(cur,i)==d for i,d in before.items())and r['document']['physical_at']==old['document']['physical_at']
  return dict(status='PASS',one_year_old_correction_all30_later_Native_cash_closings_shift_plus2_35=True,no_later_document_line_or_source_rewrite=True,original_timestamp_microseconds_preserved=True)
 def closed():
  f=misc.fixture(cur,today);day=today-timedelta(days=365);misc.source.receipt.aa.prior.set_open_period(cur,day-timedelta(days=1));f['physical']=str(day)+'T09:00:00+07:00';old=posted(cur,f);closed_through=today-timedelta(days=1);misc.source.receipt.aa.prior.set_open_period(cur,closed_through)
  source=old['document']['journals'][0];before=cur.execute('select account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(closed_through,)).fetchall()
  r=correct(cur,payload(f,old));check(cur,f,old,r)
  assert cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]==closed_through
  assert cur.execute('select account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(closed_through,)).fetchall()==before
  assert r['original_document']['journals'][0]['economic_date']==source['economic_date']
  assert all(j['transaction_date']>str(closed_through)for j in r['document']['journals'])and r['link']['time_restatement']['effective_transaction_date']>str(closed_through)
  return dict(status='PASS',one_year_old_economic_date_kept_closed_daily_books_unchanged=True,Native_open_GL_date_control_retained_without_reopening=True)
 def precision():
  f=misc.fixture(cur,today);f['physical']=f['physical'].replace('08:00:00','08:00:59.123456');old=posted(cur,f,amount='9007199254740993.01');r=correct(cur,payload(f,old,'9007199254740993.02'));check(cur,f,old,r)
  assert r['document']['amount']=='9007199254740993.02'and r['document']['physical_at']==old['document']['physical_at']and'123456'in r['document']['physical_at']
  return dict(status='PASS',Native_money_above_JS_safe_integer_plus1cent=True,raw_microseconds_preserved=True)
 def late_failure():
  f=misc.fixture(cur,today);old=posted(cur,f);p=payload(f,old);key=uuid.uuid4()
  cur.execute("create function cp7_misc_correction.test_final_native_post()returns trigger language plpgsql as $$begin if new.source_type='MISC_FINANCE'and new.source_id<>'"+old['transaction_id']+"'::uuid then raise exception 'CP7_TEST_FINAL_NATIVE_POST_FAILURE';end if;return new;end $$",prepare=False)
  cur.execute('create trigger cp7_test_final_native_post before insert on erp.journal_entries for each row execute function cp7_misc_correction.test_final_native_post()',prepare=False)
  try:
   before=b.boundary.snapshot(cur);private=private_state(cur);auth.refused(cur,lambda:correct(cur,p,key),'CP7_TEST_FINAL_NATIVE_POST_FAILURE')
   assert b.boundary.snapshot(cur)==before and private_state(cur)==private and misc.native_document(cur,old['transaction_id'])==old['document']
  finally:
   cur.execute('drop trigger cp7_test_final_native_post on erp.journal_entries;drop function cp7_misc_correction.test_final_native_post()',prepare=False)
  assert not cur.execute('select exists(select 1 from cp7_misc.requests where request_id=%s)',(key,)).fetchone()[0]
  return dict(status='PASS',disposable_explicit_fault_at_last_Native_journal_insert=True,inverse_time_pair_replacement_journals_link_UUID_all_rolled_back=True,fault_trigger_removed=True)
 def stale_original():
  f=misc.fixture(cur,today);old=posted(cur,f);p=payload(f,old);misc.command(cur,'REVERSE',misc.intent(old));before=b.boundary.snapshot(cur);private=private_state(cur)
  auth.refused(cur,lambda:correct(cur,p),'CP7_MISC_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
  return dict(status='PASS',stale_or_already_reversed_original_refuses_atomically=True)
 def stale_options():
  f=misc.fixture(cur,today);old=posted(cur,f);p=payload(f,old,kind='OTHER_INCOME');cur.execute("update erp.misc_finance_categories set category_name=category_name||' changed'where id=%s",(p['replacement']['category_id'],));before=b.boundary.snapshot(cur);private=private_state(cur)
  auth.refused(cur,lambda:correct(cur,p),'CP7_MISC_OPTIONS_CHANGED');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
  return dict(status='PASS',new_category_changed_after_review_inverse_and_time_pair_rolled_back=True)
 def replay_chain():
  f=misc.fixture(cur,today);old=posted(cur,f);p=payload(f,old);key=uuid.uuid4();first=correct(cur,p,key);second=correct(cur,payload(f,first,'12.34'));before=b.boundary.snapshot(cur);private=private_state(cur)
  assert correct(cur,p,key)==first and b.boundary.snapshot(cur)==before and private_state(cur)==private
  middle=history(cur,first['transaction_id']);assert middle['previous']['document']['id']==old['transaction_id']and middle['next']['document']['id']==second['transaction_id']and middle['previous']['document']['status']=='REVERSED'
  assert misc.cash_balance(cur,f['cash']['id'])-D(f['cash_before'])==D('-12.34')
  return dict(status='PASS',lost_reply_exact_immutable_receipt_after_further_correction=True,one_linear_history_chain_and_restore_prior_money_atomically=True)
 def fields_request():
  f=misc.fixture(cur,today);old=posted(cur,f);p=payload(f,old);key=uuid.uuid4();correct(cur,p,key);before=b.boundary.snapshot(cur);private=private_state(cur)
  changed=copy.deepcopy(p);changed['replacement']['amount']='8.88';auth.refused(cur,lambda:correct(cur,changed,key),'CP7_MISC_REQUEST_CHANGED')
  for changed in[dict(p,force=True),dict(p,replacement=dict(p['replacement'],transaction_id=str(uuid.uuid4()))),dict(p,replacement=dict(p['replacement'],amount=9.99)),dict(p,replacement=dict(p['replacement'],review_token='a'*32)),dict(p,replacement=dict(p['replacement'],change_reason='Different correction reason'))]:
   auth.refused(cur,lambda:correct(cur,changed),'CP7_MISC_')
  assert b.boundary.snapshot(cur)==before and private_state(cur)==private
  return dict(status='PASS',exact_UUID_changed_intent_and_closed_fields_refused=True,no_caller_replacement_id_numeric_money_or_forged_reason=True)
 def current_auth():
  f=misc.fixture(cur,today);old=posted(cur,f);subject,role=managed_actor(cur);p=payload(f,old);key=uuid.uuid4();r=correct(cur,p,key,subject);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,));before=b.boundary.snapshot(cur);private=private_state(cur)
  auth.refused(cur,lambda:correct(cur,p,key,subject),'CP7_MISC_ACCESS_DENIED');auth.refused(cur,lambda:history(cur,r['transaction_id'],subject),'CP7_MISC_ACCESS_DENIED');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
  return dict(status='PASS',current_deactivation_blocks_cached_receipt_and_link_reader=True,last_active_Owner_guard_preserved=True)
 def immutable_history():
  f=misc.fixture(cur,today);old=posted(cur,f);r=correct(cur,payload(f,old));before=b.boundary.snapshot(cur);private=private_state(cur)
  for sql in["update cp7_misc_correction.links set reason='Changed saved reason'",'delete from cp7_misc_correction.links','truncate cp7_misc_correction.links']:
   auth.refused(cur,lambda:cur.execute(sql),'CP7_MISC_CORRECTION_LINK_IMMUTABLE')
  assert private_state(cur)==private and b.boundary.snapshot(cur)==before
  before=private_state(cur);h=history(cur,old['transaction_id']);assert h['next']['document']==r['document']and h['previous']is None and private_state(cur)==before
  return dict(status='PASS',immutable_insert_only_link_update_delete_truncate_denied=True,actual_bidirectional_current_authorized_history_read_only=True)
 def source_privileges():
  f=misc.fixture(cur,today);old=posted(cur,f);r=correct(cur,payload(f,old));bundle.verify(cur);misc.bundle.verify(cur)
  for kind in('MISC_CORRECTION_TIME_NEUTRAL','MISC_CORRECTION_EFFECTIVE'):navigation.exact(cur,kind,old['transaction_id'],'MISC_FINANCE',old['transaction_id'])
  subject,role=auth.custom_actor(cur)
  for permission in('finance.journal.view','finance.cash.view'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,permission))
  auth.refused(cur,lambda:correct(cur,payload(f,r),subject=subject),'CP7_MISC_OWNER_ADMIN_REQUIRED')
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_function_privilege(%s,'cp7_misc_correction.apply(jsonb,uuid)','EXECUTE')",(who,)).fetchone()[0]
  return dict(status='PASS',time_adjustment_journals_open_exact_owning_source=True,no_custom_role_financial_writer_or_private_context_or_ERP_DML=True)
 tests=[expense,income,changed_type_cash,year30,closed,precision,late_failure,stale_original,stale_options,replay_chain,fields_request,current_auth,immutable_history,source_privileges]
 assert len(tests)==REQUIRED['native'];return [('CP7_MISC_CORRECTION_'+f.__name__.upper(),f)for f in tests]

def wait_for(tools):
 deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  with tools.connect()as conn,conn.cursor()as cur:
   if cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event_type='Lock'and query like 'select public.erp_cp7_correct_misc_finance_v1%')").fetchone()[0]:return
  time.sleep(.05)
 raise AssertionError('Actual correction lock wait not observed')

def races(tools,today):
 def concurrent():
  with tools.connect()as conn,conn.cursor()as cur:f=misc.fixture(cur,today);old=posted(cur,f);p=payload(f,old);conn.commit()
  gate=threading.Barrier(2);keys=[uuid.uuid4(),uuid.uuid4()]
  def send(key):
   with tools.connect()as conn,conn.cursor()as cur:
    gate.wait()
    try:r=correct(cur,p,key);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e)
  with ThreadPoolExecutor(max_workers=2)as pool:jobs=[pool.submit(send,k)for k in keys];rows=[j.result(60)for j in jobs]
  wins=[r for r in rows if isinstance(r,dict)];loss=[r for r in rows if isinstance(r,str)];assert len(wins)==len(loss)==1 and'CP7_MISC_REVIEW_CHANGED'in loss[0],rows
  with tools.connect()as conn,conn.cursor()as cur:
   assert cur.execute('select count(*)from cp7_misc_correction.links where original_id=%s',(old['transaction_id'],)).fetchone()[0]==1
   assert cur.execute('select count(*)from cp7_misc.requests where request_id=any(%s::uuid[])',(keys,)).fetchone()[0]==1
   assert misc.cash_balance(cur,f['cash']['id'])-D(f['cash_before'])==D('-9.99')
  return dict(status='PASS',two_real_current_reviews_one_atomic_winner_one_stale_refusal=True,one_link_receipt_and_replacement_money=True)
 def revoke_wait():
  with tools.connect()as conn,conn.cursor()as cur:f=misc.fixture(cur,today);old=posted(cur,f);subject,role=managed_actor(cur);p=payload(f,old);key=uuid.uuid4();conn.commit()
  with tools.connect()as holder,holder.cursor()as held:
   held.execute('select 1 from erp.misc_finance_transactions where id=%s for update',(old['transaction_id'],))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=correct(cur,p,key,subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send)
    try:
     wait_for(tools)
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.cash.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(60)
  assert isinstance(result,str)and'CP7_MISC_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:
   assert misc.native_document(cur,old['transaction_id'])==old['document']and not cur.execute('select exists(select 1 from cp7_misc.requests where request_id=%s)',(key,)).fetchone()[0]
   assert misc.stock_cost(cur)==f['stock_cost']
  return dict(status='PASS',actual_observed_original_row_wait_current_revoke_refuses_before_inverse=True,old_source_and_money_unchanged_no_receipt=True)
 return [('CP7_MISC_CORRECTION_RACE_ONE_WINNER',concurrent),('CP7_MISC_CORRECTION_RACE_CURRENT_REVOKE',revoke_wait)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','cp7-misc-correct-owner')
  with http.connect()as conn,conn.cursor()as cur:f=misc.fixture(cur,today);old=posted(cur,f);conn.commit()
  args=dict(p_payload=payload(f,old),p_request=str(uuid.uuid4()));assert http.anon_rpc(RPC,args)['status']in(401,403)
  response=owner.rpc(RPC,args);assert response['status']==200,response;r=response['body'];assert owner.rpc(RPC,args)['body']==r and r['link']['actor_scope_id']==owner.auth_user_id
  h=owner.rpc(HISTORY,dict(p_transaction_id=r['transaction_id']));assert h['status']==200 and h['body']['previous']['document']['id']==old['transaction_id'],h
  with http.connect()as conn,conn.cursor()as cur:check(cur,f,old,r);assert misc.cash_balance(cur,f['cash']['id'])-D(f['cash_before'])==D('-9.99');conn.rollback()
  changed=copy.deepcopy(args);changed['p_payload']['replacement']['amount']='8.88';assert owner.rpc(RPC,changed)['status']>=400
  return dict(status='PASS',real_Auth_HTTP_one_atomic_correction_exact_lost_reply_replay=True,actual_history_old_and_new_money=True,anonymous_and_changed_UUID_intent_denied=True)
 def revoke():
  admin=http.login('ADMIN','cp7-misc-correct-admin')
  with http.connect()as conn,conn.cursor()as cur:f=misc.fixture(cur,today);old=posted(cur,f);conn.commit()
  args=dict(p_payload=payload(f,old),p_request=str(uuid.uuid4()));response=admin.rpc(RPC,args);assert response['status']==200,response
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin.auth_user_id,));conn.commit()
  assert admin.rpc(RPC,args)['status']==403 and admin.rpc(HISTORY,dict(p_transaction_id=response['body']['transaction_id']))['status']==403
  return dict(status='PASS',real_Auth_ADMIN_current_deactivation_blocks_cached_correction_and_history=True)
 return [('CP7_MISC_CORRECTION_HTTP_ATOMIC_REPLAY',flow),('CP7_MISC_CORRECTION_HTTP_CURRENT_REVOKE',revoke)]
