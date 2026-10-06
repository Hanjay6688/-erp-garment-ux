"""Actual native-sale operands and cash posting dates, never a second money engine."""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp7_finance_cases as finance
import cp7_procurement_cases as receipt
import cp7_invoice_cases as invoice
b,auth,source,cmd=finance.b,finance.auth,finance.source,finance.cmd

def query(day,**kw):return dict({'from':str(day),'to':str(day),'as_of':str(day),'compare_from':str(day-timedelta(days=1)),'compare_to':str(day-timedelta(days=1))},**kw)
def read(cur,q,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_finance_analysis_v1(%s)',(json.dumps(q),)).fetchone()[0];b.api.admin(cur);return r
def fixture_journal_call(cur,sql,args):
 # Internal journal primitives are deliberately not executable by app roles.
 # Only disposable source preparation uses the database owner, retaining the
 # real OWNER claims required by the unchanged native business guard. No grant
 # is added; all report/HTTP/browser calls still use their actual app identity.
 auth.actor(cur);b.api.admin(cur)
 assert cur.execute('select current_user').fetchone()[0] in ('postgres','supabase_admin')
 return cur.execute(sql,args).fetchone()[0]
def journal(cur,day,lines,label='P13_ANALYSIS_FIXTURE'):
 return fixture_journal_call(cur,'select erp.post_journal(%s,%s,%s,%s,%s)',(label,uuid.uuid4(),day,'P13 source through accepted native journal',json.dumps(lines)))
def dated_sale(cur,day,price,cost):
 product,_=source.fg.ax.owner_only_model_product(cur,effective_from=day-timedelta(days=10))
 found=source.fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=source.fg.base.LOCATION,qty_pcs=1,physical_at=receipt.aa.at(day,8).isoformat(),reason='P13 dated found stock',owner_unit_value=cost,owner_value_reason='P13 explicit source cost'))
 b.api.admin(cur);tag='P13-'+uuid.uuid4().hex[:10];customer=str(source.fg.base.create_customer(cur,tag))
 draft=b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number=tag,customer_id=customer,source_location_id=source.fg.base.LOCATION,sale_date=receipt.aa.at(day,10).isoformat(),reason='P13 recorded comparison',items=[dict(product_id=product,qty_pcs=1,unit_price_snapshot=price,discount_amount='0')]),uuid.uuid4(),None)
 source.fg.post_sale(cur,draft);b.api.admin(cur)
 return dict(product=product,sale=draft['sale_id'],draft=draft,tag=tag,receipt=found['receipt_id'])
def fixture(cur,today):
 day=today-timedelta(days=1);receipt.aa.prior.set_open_period(cur,day-timedelta(days=4));q=query(day)
 before=read(cur,q);assert D(before['comparison']['current']['performance']['sales_revenue_gl'])==D(before['comparison']['baseline']['performance']['sales_revenue_gl'])==0,'P13_ORACLE_REQUIRES_EMPTY_SALES_PERIODS'
 old=dated_sale(cur,day-timedelta(days=1),'1000','730');current=dated_sale(cur,day,'1200','912')
 return dict(day=day,query=q,old=old,current=current)
def cash_fixture(cur,today):
 f=fixture(cur,today);day=f['day'];bank1=source.bc.bank_account(cur,'P13A'+uuid.uuid4().hex[:8]);bank2=source.bc.bank_account(cur,'P13B'+uuid.uuid4().hex[:8])
 coa1=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(bank1,)).fetchone()[0]);coa2=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(bank2,)).fetchone()[0])
 journal(cur,day-timedelta(days=1),[dict(account_id=coa1,debit='1000'),dict(mapping_key='OPENING_EQUITY',credit='1000')],'P13_CASH_FIXTURE_CAPITAL')
 before=read(cur,f['query']);transfer=journal(cur,day,[dict(account_id=coa1,credit='1000'),dict(account_id=coa2,debit='1000')],'P13_CASH_FIXTURE_TRANSFER')
 p=str(cur.execute("insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method) values(%s,%s,%s,300,%s,'BANK_TRANSFER') returning id",(f['current']['sale'],'P13PAY-'+uuid.uuid4().hex[:8],receipt.aa.at(day,11),bank1)).fetchone()[0]);source.native(cur,'select erp.post_sales_payment(%s)',(p,))
 purchase=invoice.fixture(cur,today,price='20',final=True);supplier_payment=source.bc.supplier_payment(cur,purchase['receipt']['purchase_id'],'200',bank2,day);source.bc.internal(cur,'post_supplier_payment',supplier_payment);b.api.admin(cur)
 f.update(bank1=bank1,bank2=bank2,coa1=coa1,coa2=coa2,transfer=transfer,payment=p,supplier_payment=supplier_payment,before=before)
 return f

def cases(cur,today):
 def comparison():
  f=fixture(cur,today);before=b.boundary.snapshot(cur);r=read(cur,f['query']);c=r['comparison']
  assert D(c['current']['performance']['sales_revenue_gl'])==1200 and D(c['baseline']['performance']['sales_revenue_gl'])==1000
  assert D(c['current']['performance']['gross_margin_pct'])==24 and D(c['baseline']['performance']['gross_margin_pct'])==27
  assert D(c['revenue_growth_pct'])==20 and D(c['gross_margin_change_pp'])==-3 and b.boundary.snapshot(cur)==before
  assert c['current']==finance.read(cur,f['day'])['snapshot'] and c['baseline']==finance.read(cur,f['day']-timedelta(days=1))['snapshot']
  from cp7_p19_finance_equivalence import compare as p19_compare
  p19_equivalence=p19_compare(cur,f['query'],b.api,auth,kind='analysis')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',O13_native_found_stock_and_sale=True,revenue=[1000,1200],margin=[27,24],growth_pct='20',margin_change_pp='-3',same_native_readiness_not_fabricated=True,no_read_side_effect=True,p19_full_financial_equivalence=p19_equivalence)
 def zero():
  f=fixture(cur,today);q=dict(f['query'],compare_from=str(f['day']-timedelta(days=3)),compare_to=str(f['day']-timedelta(days=3)));r=read(cur,q)
  assert r['comparison']['revenue_growth_pct']is None and r['comparison']['gross_margin_change_pp']is None
  # Net-negative revenue (sales revenue debited above sales) is not a ratio base:
  # growth on it inverts the sign and a gross loss would read as a positive margin.
  journal(cur,f['day'],[dict(mapping_key='SALES_REVENUE',debit='1500'),dict(mapping_key='OPENING_EQUITY',credit='1500')],'P13_NEGATIVE_REVENUE_FIXTURE')
  c=read(cur,f['query'])['comparison']
  assert D(c['current']['performance']['sales_revenue_gl'])==-300 and D(c['baseline']['performance']['sales_revenue_gl'])==1000
  assert D(c['revenue_growth_pct'])==-130 and c['gross_margin_change_pp']is None
  journal(cur,f['day']-timedelta(days=1),[dict(mapping_key='SALES_REVENUE',debit='3000'),dict(mapping_key='OPENING_EQUITY',credit='3000')],'P13_NEGATIVE_REVENUE_FIXTURE')
  c=read(cur,f['query'])['comparison']
  assert D(c['baseline']['performance']['sales_revenue_gl'])==-2000 and c['revenue_growth_pct']is None and c['gross_margin_change_pp']is None
  return dict(status='PASS',O13_baseline_zero_is_null_not_zero_or_infinity=True,negative_revenue_base_or_current_is_null_not_inverted=True)
 def cash():
  f=cash_fixture(cur,today);r=read(cur,f['query']);a,z=f['before']['cash'],r['cash']
  assert D(z['net_change'])-D(a['net_change'])==100 and D(z['debit'])-D(a['debit'])==1300 and D(z['credit'])-D(a['credit'])==1200 and z['reconciled']
  transfer=next(x for x in z['entries']['rows']if x['id']==str(f['transfer']));assert D(transfer['net'])==0
  assert all(r['comparison'][key]['performance']==f['before']['comparison'][key]['performance']for key in('current','baseline')),'Cash must not repeat revenue or COGS'
  return dict(status='PASS',O14_internal_transfer1000_net0_customer_receipt300_supplier_payment200=True,cash_net100=True,gross_cash_debits1300_credits1200_explicit_not_external_revenue=True,unpaid_invoice_not_cash=True)
 def inverse():
  f=cash_fixture(cur,today);before=read(cur,f['query']);source.native(cur,'select erp.reverse_sales_payment(%s,%s)',(f['payment'],'P13 exact payment inverse'))
  source.bc.internal(cur,'reverse_supplier_payment',f['supplier_payment'],'P13 supplier inverse');b.api.admin(cur);fixture_journal_call(cur,'select erp.reverse_journal(%s,%s)',(f['transfer'],'P13 internal transfer inverse'))
  current=read(cur,query(today));assert current['cash']['reconciled']
  assert D(current['cash']['net_change'])==-100 and D(read(cur,f['query'])['cash']['net_change'])==D(before['cash']['net_change'])
  assert all(x['reversal_of_id'] for x in current['cash']['entries']['rows'])
  return dict(status='PASS',original_prior_day_cash100_remains=True,native_next_day_inverse_minus100=True,reversed_originals_not_erased=True,linked_reversal_sources_kept=True)
 def pages_alias():
  f=cash_fixture(cur,today);baseline=read(cur,f['query']);cur.execute("insert into erp.cash_accounts(cash_account_code,cash_account_name,coa_account_id,account_kind,is_active) values(%s,'P13 shared COA alias',%s,'BANK',false)",('P13ALIAS'+uuid.uuid4().hex[:8],f['coa1']));cur.execute('update erp.cash_accounts set is_active=false where id=%s',(f['bank2'],))
  assert read(cur,f['query'])['cash']==baseline['cash'];ids=[];page=0
  while True:
   r=read(cur,dict(f['query'],offset=page,limit=1))['cash'];assert all(r[k]==baseline['cash'][k] for k in ('opening','closing','debit','credit','net_change','source_difference'));ids.extend(x['id']for x in r['entries']['rows'])
   if r['entries']['next_offset']is None:break
   page=r['entries']['next_offset']
  assert len(ids)==len(set(ids))==int(baseline['cash']['entries']['total'])
  return dict(status='PASS',all_sources_paged_without_page_subtotal=True,duplicate_cash_COA_not_double_counted=True,inactive_historical_bank_still_included=True)
 def dates():
  f=cash_fixture(cur,today);native=read(cur,f['query']);cur.execute("set local timezone='America/Los_Angeles'");other=read(cur,f['query']);native.pop('captured_at');other.pop('captured_at');assert native==other
  before=b.boundary.snapshot(cur)
  for change in ({'as_known':'2020-01-01'},{'compare_to':str(f['day'])},{'limit':'25'},{'offset':-1},{'compare_from':None},{'from':'2026-9-1'}):auth.refused(cur,lambda:read(cur,dict(f['query'],**change)),'CP7_FINANCE_ANALYSIS_QUERY')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',caller_timezone_does_not_change_accounting_dates=True,unimplemented_history_and_invalid_closed_query_refused=True)
 def exact():
  receipt.aa.prior.set_open_period(cur,today-timedelta(days=3));bank=source.bc.bank_account(cur,'P13EX'+uuid.uuid4().hex[:8]);coa=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(bank,)).fetchone()[0]);before=read(cur,query(today));value='9007199254740993.01'
  journal(cur,today,[dict(account_id=coa,debit=value),dict(mapping_key='OPENING_EQUITY',credit=value)])
  after=read(cur,query(today));assert D(after['cash']['net_change'])-D(before['cash']['net_change'])==D(value) and after['cash']['reconciled']
  return dict(status='PASS',cash_exact_above_JS_safe_integer=value,decimal_strings_before_browser=True)
 def access():
  f=fixture(cur,today);subject,role=receipt.custom(cur,());before=b.boundary.snapshot(cur);auth.refused(cur,lambda:read(cur,f['query'],subject),'CP7_FINANCE_ACCESS_DENIED');cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.reports.view')",(role,));auth.refused(cur,lambda:read(cur,f['query'],subject),'CP7_FINANCE_OWNER_ADMIN_REQUIRED')
  for who in ('anon','authenticated','service_role','cp7_capture'):assert not cur.execute("select has_function_privilege(%s,'cp7_finance.analysis(jsonb)','EXECUTE')",(who,)).fetchone()[0]
  assert not cur.execute("select has_function_privilege('cp7_finance_read','erp.post_journal(text,uuid,date,text,jsonb)','EXECUTE')").fetchone()[0]
  return dict(status='PASS',current_financial_access_native_role_boundary_and_private_function_enforced=True,reader_cannot_post_journal=True)
 return [('P13_ANALYSIS_'+name,fn)for name,fn in [('O13',comparison),('ZERO_BASELINE',zero),('O14',cash),('INVERSE_DATES',inverse),('PAGES_COA_SCOPE',pages_alias),('DATES_QUERY',dates),('EXACT_LARGE',exact),('ACCESS',access)]]

def races(tools,today):
 def coherent():
  with tools.connect()as conn,conn.cursor()as cur:f=cash_fixture(cur,today);before=read(cur,f['query']);conn.commit()
  with tools.connect()as writer,writer.cursor()as w:
   journal(w,f['day'],[dict(account_id=f['coa1'],debit='1.25'),dict(mapping_key='OPENING_EQUITY',credit='1.25')])
   with tools.connect()as reader,reader.cursor()as c:assert read(c,f['query'])['cash']==before['cash']
   writer.commit()
  with tools.connect()as reader,reader.cursor()as c:
   after=read(c,f['query']);assert D(after['cash']['net_change'])-D(before['cash']['net_change'])==D('1.25') and after['cash']['reconciled'] and int(after['cash']['entries']['total'])==int(before['cash']['entries']['total'])+1
  return dict(status='PASS',uncommitted_cash_hidden=True,committed_balance_flow_and_source_page_visible_together=True)
 return [('P13_ANALYSIS_CONCURRENT_CASH',coherent)]
def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p13-analysis-owner')
  with http.connect()as conn,conn.cursor()as cur:f=cash_fixture(cur,today);conn.commit()
  args=dict(p_query=f['query']);r=owner.rpc('erp_cp7_get_finance_analysis_v1',args);assert r['status']==200 and D(r['body']['comparison']['revenue_growth_pct'])==20 and r['body']['cash']['reconciled'],r
  assert http.anon_rpc('erp_cp7_get_finance_analysis_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_finance_analysis_v1',args)['status']==403
  return dict(status='PASS',real_auth_exact_source_response=True,anonymous_and_current_deactivation_refused=True)
 return [('P13_ANALYSIS_HTTP',flow)]
