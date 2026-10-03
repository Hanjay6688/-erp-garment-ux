"""Bounded combined-stack compatibility, not full F03 coverage."""
from datetime import timedelta
import uuid
import cp7_finance_cases as finance
import cp7_sales_return_cases as returns
import cp7_opening_payroll_cases as opening
import cp7_procurement_cases as procurement
import cp7_fg_adjustment_cases as fg
import cp7_nota_cases as nota
import cp7_attendance_write_cases as attendance
import cp7_f03_bundle as bundle
s=opening.s

def pick(rows,name):
 assert len([n for n,_ in rows if n==name])==1,('F03_UNKNOWN_OR_DUPLICATE_CASE',name)
 return next(fn for n,fn in rows if n==name)

def previous_day_sale_fixture(cur,today):
 # An explicit late-recorded Native sale, not a replaced clock or mocked source.
 # Its stock is also received on the prior day through the accepted writer.
 source=finance.source;ax=source.fg.ax;b=source.b
 now=ax.r1.now(cur);received=now-timedelta(days=1,minutes=50)
 product,_=ax.owner_only_model_product(cur)
 posted=ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,
  location_id=source.fg.base.LOCATION,qty_pcs=10,physical_at=received.isoformat(),
  reason='F03 explicit prior-day physical stock fixture',owner_unit_value='10',
  owner_value_reason='F03 independently supplied fixture value'))
 f=dict(product=str(product),location=source.fg.base.LOCATION,at=received.isoformat(),
  receipt=posted['receipt_id'],sku=b.one(cur,'select sku from erp.products where id=%s',product),
  lot=b.one(cur,'select lot_id::text from erp.fg_unsourced_receipts_v1 where id=%s',posted['receipt_id']))
 f['tag']='F03CROSS-'+uuid.uuid4().hex[:12]
 f['customer']=str(source.fg.base.create_customer(cur,f['tag']))
 f['sale_at']=(now-timedelta(days=1,minutes=10)).isoformat()
 f['draft']=b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(
  sale_number=f['tag'],customer_id=f['customer'],source_location_id=f['location'],
  sale_date=f['sale_at'],reason='F03 explicit prior-day invoice/current-day return fixture',
  items=[dict(product_id=f['product'],qty_pcs=4,unit_price_snapshot='20',discount_amount='0')]),uuid.uuid4(),None)
 f['sale']=f['draft']['sale_id'];b.api.admin(cur)
 actual=cur.execute('select sale_date from erp.sales_headers where id=%s',(f['sale'],)).fetchone()[0]
 assert actual==now-timedelta(days=1,minutes=10),'F03_PRIOR_DAY_NATIVE_SALE_TIMESTAMP'
 f['sale_at']=actual.isoformat()
 return f

def cases(cur,today):
 def ledger_cycle(previous_day=False):
  f=opening.fixture(cur,today);sale=(previous_day_sale_fixture if previous_day else finance.source.fixture)(cur,today);sale['destination']=returns.location(cur);sale['bank']=str(s.cash(cur));before=finance.fixture_read(cur,today,sale['sale_at']);gl=finance.cmd.accounts(cur)
  narrow_before=finance.read(cur,today) if previous_day else None
  opening.all_sources(cur,f);s.act(cur,'PREPARE',s.doc(cur,f['payroll']));s.act(cur,'APPROVE',s.doc(cur,f['payroll']))
  p,v=finance.cmd.review(cur,sale);finance.cmd.command(cur,'POST',p,v);sale['allocations']=returns.read(cur,sale)['page']['rows'];ret=returns.returned(cur,sale);pay=returns.payments.pay(cur,sale,'30')
  return_at=cur.execute('select physical_at from erp.sales_returns where id=%s',(ret['return_id'],)).fetchone()[0]
  s.act(cur,'PAY',s.doc(cur,f['payroll']),payment_date=str(today),cash_account_id=f['cash']);after=finance.fixture_read(cur,today,sale['sale_at'])
  if previous_day:
   narrow_after=finance.read(cur,today)
   # The valid single-day report excludes yesterday's sale80 but includes
   # today's return20. It must not be used as this combined-cycle oracle.
   assert finance.change(narrow_before,narrow_after,'performance','sales_revenue_gl')==-20
   assert finance.change(narrow_before,narrow_after,'performance','cogs_gl')==-10
   basis=after['snapshot']['basis']
   assert basis['period_from']<basis['period_to'],'F03_CROSS_DATE_WINDOW_REQUIRED'
  for section,key,amount in [('financial_position','cash',-6030),('financial_position','customer_ar',30),('financial_position','fg_inventory',-30),('performance','sales_revenue_gl',60),('performance','cogs_gl',30),('performance','gross_profit',30),('performance','operating_and_other_expense',5),('performance','net_profit',25)]:
   assert finance.change(before,after,section,key)==amount,(section,key,amount,finance.change(before,after,section,key))
  assert s.doc(cur,f['payroll'])['net_payable']=='6060.00';opening.assert_remaining(opening.state(cur,f),0,0,0,2)
  returns.payments.inverse(cur,sale,pay['payment_id']);returns.inverse(cur,sale,ret['return_id']);returns.reverse_sale(cur,sale);s.act(cur,'REVERSE',s.doc(cur,f['payroll']));final=finance.fixture_read(cur,today,sale['sale_at'])
  assert finance.cmd.accounts(cur)==gl and final['snapshot']['financial_position']==before['snapshot']['financial_position'] and final['snapshot']['performance']==before['snapshot']['performance']
  opening.assert_remaining(opening.state(cur,f),65,20,30,4);assert finance.cmd.available(cur,sale)==10
  # The sale draft's reservation existed at baseline; compare ledger meaning,
  # not a row-count equality that would erase legitimate reversal history.
  for table in ('cp7_sales.command_context','cp7_payroll.execution_context','cp7_payroll.settlement_context','cp7_attendance.command_context'):
   assert cur.execute('select count(*) from '+table).fetchone()[0]==0,table
  return dict(status='PASS',same_installed_stack_sale80_return20_cash30_and_opening_payroll6060=True,net_cash_change='-6030',AR='30',FG='-30',revenue='60',COGS='30',new_expense='5',net_profit='25',all_final_GL_and_report_values_neutral=True,opening_balances_and_entitlement_restored=True,transaction_admission_contexts_empty=True,
   report_window_from_existing_actual_Native_clock_and_source_physical_date=True,
   Native_fixture_sale_physical_at=sale['sale_at'],Native_fixture_return_physical_at=return_at.isoformat(),actual_Native_report_before=before['snapshot'],
   actual_Native_report_after=after['snapshot'],actual_Native_report_final=final['snapshot'],
   explicit_prior_day_sale_current_day_return=previous_day,
   actual_Native_single_day_before=narrow_before['snapshot'] if previous_day else None,
   actual_Native_single_day_after=narrow_after['snapshot'] if previous_day else None)
 def combined_ledger():
  original=ledger_cycle()
  original['declared_prior_day_Native_cycle']=ledger_cycle(True)
  original['all_original_commands_assertions_and8_expected_deltas_run_in_both_cycles']=True
  original['new_unique_case_credit']=0
  original['historic_b5_missing_raw_dates_retroactively_proven']=False
  return original
 def contexts():
  for table,owners in [('cp7_sales.command_context',('cp7_sales_write','postgres')),('cp7_payroll.execution_context',('cp7_nota_write','postgres')),('cp7_payroll.settlement_context',('cp7_payroll_write','postgres')),('cp7_attendance.command_context',('cp7_attendance_write','postgres'))]:
   # Read access needed by native security-definer admission does not confer
   # context creation. Every other facade/browser role must lack DML here.
   for role in (*bundle.ROLES,'anon','authenticated','service_role'):
    if role not in owners:assert not cur.execute("select has_table_privilege(%s,%s,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(role,table)).fetchone()[0],(role,table)
  before=finance.b.boundary.snapshot(cur);finance.auth.refused(cur,lambda:cur.execute(bundle.sales.admission(),prepare=False),'CP7_SALES_ADMISSION_PREDECESSOR_CHANGED');assert finance.b.boundary.snapshot(cur)==before
  return dict(status='PASS',combined_roles_cannot_forge_another_command_context=True,no_cross_family_private_write_admission=True,standalone_guard_refuses_wrong_combined_predecessor_atomically=True)
 selected=[(procurement,'P09_FINAL_EXACT_VALUE'),(fg,'P10_ADJUST_NEGATIVE_VALUE'),(nota,'P12_NOTA_EXACT_ACCESS'),(s,'P12_SETTLEMENT_ACCESS'),(attendance,'P12_ATTENDANCE_WRITE_ACCESS'),(returns,'P11_RETURN_PERMISSIONS'),(finance,'P13_REPORT_READ_ONLY_PRIVATE'),(finance,'P13_REPORT_FILED_LATE_CORRECTION')]
 return [('F03_'+name,pick(module.cases(cur,today),name)) for module,name in selected]+[('F03_COMBINED_LEDGER',combined_ledger),('F03_PRIVATE_CONTEXT_ISOLATION',contexts)]

def races(tools,today):
 return [('F03_'+name,pick(module.races(tools,today),name)) for module,name in [(returns,'P11_RETURN_RACE_REVOKE'),(s,'P12_SETTLEMENT_RACE_REVOKE')]]
def http_cases(http,today):
 return [('F03_'+name,fn) for module in (procurement,s,returns,finance) for name,fn in module.http_cases(http,today)]
