"""Own current payroll82.82 plus accepted opening sources; transport helpers explicitly inherited."""
import uuid
from decimal import Decimal as D
import cases_business as b
import cp7_opening_payroll_cases as opening
from cases_stage import wrap,check,admin,refusal

def cases(cur,today):
 def carry():
  f=b.production(cur,today);f['component']=b.prod.COMPONENT;f['cash']=f['bank']
  cards=b.nota.read(cur,'SOURCES',contractor_id=f['contractor'])['page']['rows']
  n=b.nota.command(cur,'SAVE',dict(contractor_id=f['contractor'],note_date=str(today),period_start=str(f['production_day']),period_end=str(today),cards=[dict(card_key=c['card_key'],source_token=c['source_token']) for c in cards],notes='Astra actual41x1.13 plus41x.89'))
  n=b.nota.act(cur,'POST',n);f['payroll']=n['payroll_id'];pid=f['payroll']
  rows=opening.rows(cur,f,today);batch,code,cutover=opening.bb.post_batch(cur,today,rows,prefix='AS20PAY')
  f.update(opening.sources(cur,batch),code=code,cutover=str(cutover))
  initial=opening.state(cur,f);before=b.gl(cur);qty=b.fg_qty(cur,f)
  for name in ('UPAH-OLD','REIMB-OLD','KASBON-OLD'):opening.allocate(cur,f,name)
  action,p=opening.payload(cur,f,'CARRY','3');key=uuid.uuid4();one=opening.bb.api.call(cur,action,p,key)
  check(opening.bb.api.call(cur,action,p,key)==one,'Carry allocation replay has one source claim')
  for _ in range(2):b.settlement.act(cur,'PREPARE',b.settlement.doc(cur,pid))
  d=b.settlement.doc(cur,pid)
  check(D(d['net_payable'])==D('145.32'),'Current labor46.33+accessory36.49+old85+carry7.50-oldadvance30=145.32',payroll=d)
  check(D(opening.state(cur,f)['carry'])==1,'Three of four carry units reserved once')
  b.settlement.act(cur,'APPROVE',d);approved=b.settlement.doc(cur,pid);paykey=uuid.uuid4()
  paid=b.settlement.act(cur,'PAY',approved,paykey,payment_date=str(today),cash_account_id=f['cash'])
  after=b.gl(cur);check(b.settlement.act(cur,'PAY',approved,paykey,payment_date=str(today),cash_account_id=f['cash'])==paid and b.gl(cur)==after,'Cash payment UUID replay exactly once')
  check(b.delta(before,after).get(f['cash_coa'])==D('-145.32'),'Bank decrease equals exact independent payroll net')
  used=opening.state(cur,f);check(all(D(v)==0 for v in used['remaining'].values()) and D(used['carry'])==1,'Old cash rights settled once, unused carry1 retained',remaining=used['remaining'],carry=used['carry'])
  check(b.fg_qty(cur,f)==qty==41,'Payroll and old rights do not manufacture stock')
  b.settlement.act(cur,'REVERSE',b.settlement.doc(cur,pid));restored=opening.state(cur,f)
  check(restored['remaining']==initial['remaining'] and D(restored['carry'])==4,'Inverse restores old rights and all carry units')
  check(b.delta(before,b.gl(cur))=={} and b.fg_qty(cur,f)==41,'Inverse restores all money and stock exactly')
  return dict(current_labor='46.33',current_accessories='36.49',opening_payable='85',carry_units=3,carry_rate='2.50',opening_advance='30',cash_paid='145.32',unused_carry=1,replay_once=True,inverse_restored=True,fixture_origin='ASTRA_PRODUCTION_AND_ORACLE_PLUS_WRITER_OPENING_IMPORT_ROWS')
 return [wrap('AS20-18_19_OPENING_CARRY_PAYROLL',carry)]
