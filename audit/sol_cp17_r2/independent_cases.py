"""Sol's literal contract oracles on the pinned, unchanged CP17 stack.

Synthetic master rows reuse the existing fixture builders. Money expectations
below are constants, never calculated by the guard or command being audited.
Business calls are public SQL facades as the fixture OWNER, except the explicit
Native journal reversal. This module does not claim real Auth/browser coverage.
"""
from datetime import timedelta
from decimal import Decimal as D
import json, uuid
import psycopg
import cp7_cp17_fix_cases as c
import cp7_supplier_payment_create_cases as pay
import cp7_cash_funding as funding
import cp7_payment_correction_cases as edit

IDS = [
 'SOL_R1_EMPTY_BANK_ATOMIC_REFUSAL',
 'SOL_R1_FUNDED_PUBLIC_INCOME_PAYMENT_CONTROL',
 'SOL_R1_BACKDATE_BEFORE_FUNDING',
 'SOL_R1_LATER_DAY_CASH_PREFIX',
 'SOL_R1_USED_FUNDING_REVERSAL',
 'SOL_R1_CUSTOMER_PAYMENT_CORRECTION_FINAL_POSITIVE',
 'SOL_R1_SEWING_PARTIAL_REVERSE_DIMENSIONS',
]

def factory(cur, today):
 def finish(d):
  return dict(d,evidence_origin='INDEPENDENT_NATIVE_RERUN',
   oracle_origin='SOL_LITERAL_D14_3_AND_IMMUTABLE_ATOMIC_CORRECTION_CONTRACT',
   fixture_origin='SYNTHETIC_REUSED_NATIVE_BUILDERS',session_role='OWNER',
   setup_role='postgres',production_go=False)
 def empty():
  f=pay.fixture(cur,today);assert c.balance(cur,f['cash'])==0
  before=pay.b.boundary.snapshot(cur)
  refusal=pay.auth.refused(cur,lambda:pay.command(cur,pay.payload(cur,f,'1.00')),'CP7_CASH_NEGATIVE')
  assert pay.b.boundary.snapshot(cur)==before and c.balance(cur,f['cash'])==0
  assert pay.read(cur,f)['Native_AP']['remaining']=='1000.00'
  return finish(dict(status='PASS',requested='1.00',bank_before='0',bank_after='0',AP='1000.00',refusal=refusal,whole_boundary_unchanged=True))
 def funded():
  f=pay.fixture(cur,today)
  s=edit.fixture(cur,today,amount='34.50',qty='2',price='17.25')
  f['cash']=s['bank'];assert c.balance(cur,f['cash'])==D('34.50')
  r=pay.command(cur,pay.payload(cur,f,'1.00'))
  assert r['status']=='POSTED' and r['remaining_after']=='999.00' and c.balance(cur,f['cash'])==D('33.50')
  return finish(dict(status='PASS',funding='REAL_PUBLIC_SALES_PAYMENT',income='34.50',supplier_payment='1.00',bank_after='33.50',supplier_AP_after='999.00'))
 def backdate():
  f=pay.fixture(cur,today);funding.fund(cur,f['cash'],'10',today)
  day=f['day'];assert day<today
  p=pay.payload(cur,f,'1.00',payment_date=c.wib(day))
  before=pay.b.boundary.snapshot(cur)
  refusal=pay.auth.refused(cur,lambda:pay.command(cur,p),'CP7_CASH_NEGATIVE')
  assert pay.b.boundary.snapshot(cur)==before and c.balance(cur,f['cash'])==10
  return finish(dict(status='PASS',capital_day=str(today),requested_day=str(day),capital='10',refusal=refusal,whole_boundary_unchanged=True))
 def later():
  f=pay.fixture(cur,today);funding.fund(cur,f['cash'],'10',f['day'])
  pay.command(cur,pay.payload(cur,f,'10.00'))
  assert c.balance(cur,f['cash'])==0
  p=pay.payload(cur,f,'1.00',payment_date=c.wib(f['day']))
  before=pay.b.boundary.snapshot(cur)
  refusal=pay.auth.refused(cur,lambda:pay.command(cur,p),'CP7_CASH_NEGATIVE')
  assert pay.b.boundary.snapshot(cur)==before and c.balance(cur,f['cash'])==0
  return finish(dict(status='PASS',first_day_income='10',later_day_payment='10',earlier_additional_payment_refused='1',later_day_would_be='-1',refusal=refusal,whole_boundary_unchanged=True))
 def funding_reverse():
  f=pay.fixture(cur,today);journal=funding.fund(cur,f['cash'],'10',f['day'])
  pay.command(cur,pay.payload(cur,f,'8.00'));assert c.balance(cur,f['cash'])==2
  before=pay.b.boundary.snapshot(cur)
  def reverse():
   pay.b.api.admin(cur)
   return cur.execute('select erp.reverse_journal(%s,%s)',(journal,'Sol used funding reversal')).fetchone()[0]
  refusal=pay.auth.refused(cur,reverse,'CP7_CASH_NEGATIVE')
  assert pay.b.boundary.snapshot(cur)==before and c.balance(cur,f['cash'])==2
  return finish(dict(status='PASS',capital='10',paid='8',bank='2',reverse_would_be='-8',refusal=refusal,whole_boundary_unchanged=True))
 def correction():
  # Positive control: the same lawful public correction with an unspent receipt.
  control=edit.fixture(cur,today,amount='30.01')
  p,v=edit.payload(cur,control,'25.01');answer=edit.correct(cur,p,v)
  edit.check(cur,control,p,answer);assert c.balance(cur,control['bank'])==D('25.01')
  # Critical difference: 20 of the 30.01 receipt has paid a supplier. Correcting
  # the receipt to 25.01 leaves 5.01, on the SAME economic day. No overdraft.
  f=edit.fixture(cur,today,amount='30.01');out=pay.fixture(cur,today);out['cash']=f['bank']
  pay.command(cur,pay.payload(cur,out,'20.00'));assert c.balance(cur,f['bank'])==D('10.01')
  p,v=edit.payload(cur,f,'25.01')
  # Tool qualification: the P09 fixture above leaves the caller in Jakarta.
  # The actual correction screen uses its own UTC-pinned public workspace,
  # rather than the generic sales reader's caller-zone-dependent token.
  workspace=edit.workspace(cur,f)
  p['review_token'],v=workspace['review_token'],workspace['row_version']
  before=pay.b.boundary.snapshot(cur)
  cur.execute('savepoint sol_positive_correction')
  result=None;error=None
  try:result=edit.correct(cur,p,v)
  except psycopg.Error as exc:
   error=dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary,context=exc.diag.context)
   cur.execute('rollback to savepoint sol_positive_correction')
  finally:cur.execute('release savepoint sol_positive_correction');pay.b.api.admin(cur)
  if result is None:
   unchanged=pay.b.boundary.snapshot(cur)==before
   assert unchanged and c.balance(cur,f['bank'])==D('10.01')
   status='COUNTEREXAMPLE' if error and 'CP7_CASH_NEGATIVE' in error['message'] else 'INCOMPLETE'
   return finish(dict(status=status,positive_control=answer,original_receipt='30.01',supplier_payment='20.00',replacement_receipt='25.01',expected_final_bank='5.01',actual_bank='10.01',error=error,whole_boundary_unchanged=unchanged,valid_replacement_refused=True))
  edit.check(cur,f,p,result);assert c.balance(cur,f['bank'])==D('5.01')
  return finish(dict(status='PASS',original_receipt='30.01',supplier_payment='20.00',replacement_receipt='25.01',expected_final_bank='5.01',actual_bank='5.01',original_facts_kept=True))
 def sewing():
  g=c.pickup_fixture(cur,today);components=c.work_rates(cur,g)
  w=c.sewing_workspace(cur,g);a=c.sewing_command(cur,w,qty=4,at=g['at'](10))
  w=c.sewing_workspace(cur,g);b=c.sewing_command(cur,w,qty=6,at=g['at'](11))
  assert a['result']['wage_amount']==16 and b['result']['wage_amount']==24
  w=c.sewing_workspace(cur,g);assert (w['sewn_pcs'],w['max_qty'],w['ready_unsent_pcs'])==(10,0,10)
  rows=cur.execute("select l.work_component_id::text,sum(l.qty_payable),sum(l.amount_payable) from erp.work_completion_lines l join erp.work_completion_events e on e.id=l.completion_id where e.cutting_group_id=%s and e.status='POSTED' group by 1",(g['group'],)).fetchall()
  assert {i:(D(q),D(m))for i,q,m in rows}=={components['component']:(D(10),D(30)),components['obras']:(D(10),D(10))},rows
  c.sewing_command(cur,w,event=a['result']['sewing_event_id'])
  w=c.sewing_workspace(cur,g);assert (w['sewn_pcs'],w['max_qty'],w['ready_unsent_pcs'])==(6,4,6)
  assert c.wage_journal(cur,b['result']['work_completion_id'])==(D(24),D(24),1)
  return finish(dict(status='PASS',first_pcs=4,first_wage='16',second_pcs=6,second_wage='24',by_component_expected={'mandor':'30','obras':'10'},after_reverse_first={'sewn':6,'ready':6,'remaining':4,'wage':'24'},original_second_completion_unchanged=True))
 return list(zip(IDS,[empty,funded,backdate,later,funding_reverse,correction,sewing]))
