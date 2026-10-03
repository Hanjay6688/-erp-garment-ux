"""Bounded combined-stack compatibility, not full F03 coverage."""
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

def cases(cur,today):
 def combined_ledger():
  f=opening.fixture(cur,today);sale=finance.source.fixture(cur,today);sale['destination']=returns.location(cur);sale['bank']=str(s.cash(cur));before=finance.fixture_read(cur,today,sale['sale_at']);gl=finance.cmd.accounts(cur)
  opening.all_sources(cur,f);s.act(cur,'PREPARE',s.doc(cur,f['payroll']));s.act(cur,'APPROVE',s.doc(cur,f['payroll']))
  p,v=finance.cmd.review(cur,sale);finance.cmd.command(cur,'POST',p,v);sale['allocations']=returns.read(cur,sale)['page']['rows'];ret=returns.returned(cur,sale);pay=returns.payments.pay(cur,sale,'30')
  s.act(cur,'PAY',s.doc(cur,f['payroll']),payment_date=str(today),cash_account_id=f['cash']);after=finance.fixture_read(cur,today,sale['sale_at'])
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
   Native_fixture_sale_physical_at=sale['sale_at'],actual_Native_report_before=before['snapshot'],
   actual_Native_report_after=after['snapshot'],actual_Native_report_final=final['snapshot'])
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
