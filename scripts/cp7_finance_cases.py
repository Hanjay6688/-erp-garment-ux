"""P13 owner report source, immutable filing, dated correction and no-write proofs."""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp7_sales_payment_cases as payments
import cp6_aw_probe as aw
from cp7_native_fixture_window import native_window
cmd,source,b,auth=payments.cmd,payments.source,payments.b,payments.auth

def query(day,**extra):return dict({'from':str(day),'to':str(day),'as_of':str(day)},**extra)
def read(cur,day,subject=None,**extra):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_finance_report_v1(%s)',(json.dumps(query(day,**extra)),)).fetchone()[0];b.api.admin(cur);return r

def fixture_read(cur,day,*physical):
 return read(cur,day,**native_window(cur,day,*physical))

def change(a,z,section,key):return D(z['snapshot'][section][key])-D(a['snapshot'][section][key])

def archive_fixture(cur,today):
 f,_=aw.recost_fixture(cur,today,False);day=f['purchase_day']+timedelta(days=1);quiet=aw.quiet_seed(cur,f['purchase_day'],day);pre=aw.preflight(cur,day);assert pre and pre['status']=='READY',dict(reason='Fixture not ready to file',preflight=pre,quiet=quiet)
 closed=aw.close(cur,day,'P13 native filing after source preparation');assert closed[0]=='ACCEPTED',closed
 b.api.admin(cur);ident=str(cur.execute('select id from erp.accounting_close_filings_v1 order by filed_at desc,id desc limit 1').fetchone()[0]);return f,day,ident

def cases(cur,today):
 def lifecycle():
  f=source.fixture(cur,today);before=fixture_read(cur,today,f['sale_at']);gl=cmd.accounts(cur);boundary=b.boundary.snapshot(cur);assert fixture_read(cur,today,f['sale_at'])['snapshot']==before['snapshot'] and b.boundary.snapshot(cur)==boundary
  source.fg.post_sale(cur,f['draft']);rid=source.returned(cur,f);unpaid=fixture_read(cur,today,f['sale_at']);pid=source.payment(cur,f,today,'30');paid=fixture_read(cur,today,f['sale_at'])
  assert change(before,paid,'financial_position','customer_ar')==30 and change(before,paid,'financial_position','cash')==30 and change(before,paid,'financial_position','fg_inventory')==-30
  assert change(before,paid,'performance','sales_revenue_gl')==60 and change(before,paid,'performance','cogs_gl')==30 and change(before,paid,'performance','gross_profit')==30
  assert unpaid['snapshot']['performance']==paid['snapshot']['performance'] and paid['snapshot']['performance']['sales_revenue_reconciled']
  source.native(cur,'select erp.reverse_sales_payment(%s,%s)',(pid,'P13 native inverse payment'));source.native(cur,'select erp.reverse_sales_return(%s,%s)',(rid,'P13 native inverse return'));source.native(cur,'select erp.reverse_sale(%s,%s)',(f['sale'],'P13 native inverse invoice'))
  after=fixture_read(cur,today,f['sale_at']);assert after['snapshot']['financial_position']==before['snapshot']['financial_position'] and after['snapshot']['performance']==before['snapshot']['performance'] and cmd.accounts(cur)==gl
  return dict(status='PASS',native_sale80_return20_cash30=True,AR30_cash30_FG_minus30_revenue60_COGS30_profit30=True,payment_does_not_repeat_revenue_or_HPP=True,all_GL_and_report_amounts_restored_after_inverse=True,read_has_no_business_effect=True)
 def exact_large():
  f=source.fixture(cur,today,qty=1000,stock=1001,price='9007199254741.01',discount='0.01');before=fixture_read(cur,today,f['sale_at']);source.fg.post_sale(cur,f['draft']);after=fixture_read(cur,today,f['sale_at']);expected=D('9007199254741009.99')
  assert change(before,after,'financial_position','customer_ar')==expected and change(before,after,'performance','sales_revenue_gl')==expected
  assert isinstance(after['snapshot']['performance']['gross_margin_pct'],str) or after['snapshot']['performance']['gross_margin_pct'] is None
  # The accepted numeric report is serialized before JS. No Number conversion.
  assert cur.execute("select cp7_finance.exact_numbers('{\"amount\":9007199254740993.01,\"loss\":-0.01,\"missing\":null,\"flag\":true}'::jsonb)").fetchone()[0]==dict(amount='9007199254740993.01',loss='-0.01',missing=None,flag=True)
  return dict(status='PASS',native_invoice_exact_above_JS_safe_integer=str(expected),financial_values_are_decimal_strings=True,negative_and_null_preserved=True)
 def invalid():
  before=b.boundary.snapshot(cur)
  for extra in ({'as_known':'2020-01-01'},{'limit':101},{'limit':'25'},{'offset':-1},{'from':str(today+timedelta(days=1))},{'as_of':str(today+timedelta(days=1))},{'to':None},{'from':'2026-9-1'}):auth.refused(cur,lambda:read(cur,today,**extra),'CP7_FINANCE_QUERY')
  auth.refused(cur,lambda:read(cur,today,filing_id=str(uuid.uuid4())),'CP7_FINANCE_FILING_NOT_FOUND');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',unknown_history_invalid_dates_and_pages_refused=True,missing_filing_explicit=True,atomic_read_refusal=True)
 def access():
  subject,role=auth.custom_actor(cur);before=b.boundary.snapshot(cur);auth.refused(cur,lambda:read(cur,today,subject),'CP7_FINANCE_ACCESS_DENIED');assert b.boundary.snapshot(cur)==before
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.reports.view')",(role,));auth.refused(cur,lambda:read(cur,today,subject),'CP7_FINANCE_OWNER_ADMIN_REQUIRED')
  return dict(status='PASS',report_permission_required=True,accepted_native_owner_admin_boundary_preserved=True,no_custom_role_bypass_claim=True)
 def archive(late):
  f,day,ident=archive_fixture(cur,today);old=read(cur,day,filing_id=ident);original=old['filing'];assert original['readiness']['status']=='READY' and not old['snapshot']['data_confidence']['changed_since_filing']
  if late:
   aw.chain.prior.post_purchase(cur,f['material'],aw.chain.production.at(f['purchase_day'],22),unit_price=12);b.api.admin(cur);aw.chain.production.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');b.api.admin(cur)
  cur.execute("set local timezone='America/Los_Angeles'");current=read(cur,day,filing_id=ident);assert current['filing']==original and current['snapshot']['financial_position']==old['snapshot']['financial_position']
  assert current['snapshot']['data_confidence']['status']=='READY' and current['snapshot']['data_confidence']['changed_since_filing'] is late
  assert current['close_preflight']['status']=='READY' and current['close_preflight']['through']==str(day)
  return dict(status='PASS',late_change=late,as_filed_amounts_readiness_hash_unchanged=True,closed_day_GL_unchanged=True,corrected_READY_does_not_erase_later_correction_marker=late,caller_timezone_does_not_change_filing=True,native_preflight_source_matches=True)
 def archive_pages():
  f,day,ident=archive_fixture(cur,today)
  for _ in range(2):
   source.native(cur,'select erp.reopen_accounting_through(%s,%s)',(day-timedelta(days=1),'P13 native archive paging fixture'))
   assert aw.close(cur,day,'P13 native reclose filing fixture')[0]=='ACCEPTED';b.api.admin(cur)
  seen=[]
  for off in range(3):
   r=read(cur,day,limit=1,offset=off);assert r['filings']['total']=='3' and r['filings']['next_offset']==(off+1 if off<2 else None);seen.append(r['filings']['rows'][0]['id'])
  assert len(set(seen))==3;auth.refused(cur,lambda:read(cur,day+timedelta(days=1),filing_id=ident),'CP7_FINANCE_FILING_DATE_MISMATCH')
  return dict(status='PASS',three_actual_native_close_filings_distinct_and_complete=True,filing_must_match_its_actual_cutoff=True)
 def private():
  assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_finance_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
  for who in ('anon','authenticated','service_role','cp7_capture'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_finance','USAGE') or has_function_privilege(%s,'cp7_finance.workspace(jsonb)','EXECUTE')",(who,who)).fetchone()[0]
  for signature in ('erp.close_accounting_through(date,text)','erp.reopen_accounting_through(date,text)','erp.process_cost_recalc_queue(integer)','erp.post_sales_payment(uuid)'):
   assert not cur.execute("select has_function_privilege('cp7_finance_read',%s,'EXECUTE')",(signature,)).fetchone()[0]
  return dict(status='PASS',no_reader_business_DML_or_close_reopen_recost_native_execution=True,private_projection_unreachable=True)
 return [('P13_REPORT_'+name,fn) for name,fn in [('LEDGER_LIFECYCLE',lifecycle),('EXACT_LARGE',exact_large),('QUERY',invalid),('ACCESS',access),('FILED_LATE_CORRECTION',lambda:archive(True)),('FILED_UNCHANGED_CONTROL',lambda:archive(False)),('FILING_PAGES',archive_pages),('READ_ONLY_PRIVATE',private)]]

def races(tools,today):
 def coherent():
  with tools.connect() as conn,conn.cursor() as cur:f=payments.fixture(cur,today);before=read(cur,today);conn.commit()
  with tools.connect() as writer,writer.cursor() as w:
   payments.pay(w,f,'30')
   with tools.connect() as reader,reader.cursor() as c:old=read(c,today);assert old['snapshot']['financial_position']==before['snapshot']['financial_position'] and old['snapshot']['performance']==before['snapshot']['performance']
   writer.commit()
  with tools.connect() as reader,reader.cursor() as c:
   after=read(c,today);assert change(before,after,'financial_position','customer_ar')==-30 and change(before,after,'financial_position','cash')==30 and after['snapshot']['performance']==before['snapshot']['performance']
  return dict(status='PASS',concurrent_uncommitted_native_cash_hidden=True,committed_cash30_and_ARminus30_visible_together=True,no_partial_or_duplicate_cost=True)
 return [('P13_REPORT_CONCURRENT_CASH',coherent)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p13-report-owner');args=dict(p_query=query(today));assert http.anon_rpc('erp_cp7_get_finance_report_v1',args)['status'] in(401,403)
  r=owner.rpc('erp_cp7_get_finance_report_v1',args);assert r['status']==200 and r['body']['snapshot']['basis']['balance_sheet_as_of']==str(today),r
  assert isinstance(r['body']['snapshot']['financial_position']['cash'],str)
  with http.connect() as conn,conn.cursor() as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_finance_report_v1',args)['status']==403
  return dict(status='PASS',real_auth_source_dates_and_decimal_strings=True,anonymous_and_deactivated_identity_refused=True)
 return [('P13_REPORT_HTTP',flow)]
