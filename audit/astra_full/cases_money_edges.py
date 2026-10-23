"""Independent money/date continuation: new operands, explicit arithmetic and ordinary commands."""
import uuid
from datetime import timedelta
from decimal import Decimal as D
import cases_business as b
import cp7_receipt_correction_cases as fix
import cp7_note_correction_cases as note
from cases_stage import wrap,check,admin,refusal

def cases(cur,today):
 def supplier_credit():
  f=b.invoices.fixture(cur,today,'17','11.23',True);t=b.invoices.fixture(cur,today,'23','11.23',True)
  bank=b.supplier_pay.bc.fixture(cur,today,zones=False,purchase=False);f['cash']=bank['cash']
  pay=b.supplier_pay.command(cur,b.supplier_pay.payload(cur,f,'190.91'))
  pid=f['receipt']['purchase_id'];original=cur.execute("select to_jsonb(i)-'invoice_match_state' from erp.material_purchase_items i where purchase_id=%s order by id",(pid,)).fetchall()
  before=b.gl(cur);w=fix.ws(cur,pid);p=fix.payload(w,line=lambda n,i:i['rolls'][0].update(qty='15'))
  no_target=refusal(cur,lambda:fix.fix(cur,p,w['purchase']['row_version']))
  check(no_target['refused'] and b.gl(cur)==before,'Overpayment needs explicit other-invoice credit, no automatic cash refund')
  p['credit_allocations']=[dict(purchase_id=t['receipt']['purchase_id'],amount='22.46')]
  key=uuid.uuid4();out=fix.fix(cur,p,w['purchase']['row_version'],key)
  f2=dict(f,receipt=dict(purchase_id=out['purchase_id']))
  ap=b.supplier_pay.read(cur,f2)['Native_AP'];target=b.supplier_pay.read(cur,t)['Native_AP']
  check((D(ap['final_ap']),D(ap['paid']),D(ap['remaining']))==(D('168.45'),D('168.45'),D(0)),'17x11.23 paid, corrected15:source settled168.45',observed=ap)
  check((D(target['final_ap']),D(target['paid']),D(target['remaining']))==(D('258.29'),D('22.46'),D('235.83')),'Exact22.46 credit cuts chosen23x11.23 invoice once',observed=target)
  expected={b.account(cur,'MATERIAL_INVENTORY'):D('-22.46'),b.account(cur,'AP_SUPPLIER'):D('22.46')}
  check(b.delta(before,b.gl(cur))==expected,'Credit correction moves no cash',delta=b.delta(before,b.gl(cur)))
  check(cur.execute("select to_jsonb(i)-'invoice_match_state' from erp.material_purchase_items i where purchase_id=%s order by id",(pid,)).fetchall()==original,'Original receipt line remains historical')
  after=b.gl(cur);check(fix.fix(cur,p,w['purchase']['row_version'],key)==out and b.gl(cur)==after,'Credit replay has no second application')
  check(b.procurement.qty(cur,f)[0]==15 and b.procurement.qty(cur,t)[0]==23,'Physical corrected receipt15, chosen invoice23 unchanged')
  return dict(source=ap,target=target,expected_credit='22.46',cash_changed=False,original_lines_unchanged=True)

 def supplier_up():
  f=b.invoices.fixture(cur,today,'17','11.23',True);f['cash']=b.supplier_pay.bc.fixture(cur,today,zones=False,purchase=False)['cash']
  b.supplier_pay.command(cur,b.supplier_pay.payload(cur,f,'100.17'));before=b.gl(cur)
  w=fix.ws(cur,f['receipt']['purchase_id']);p=fix.payload(w,line=lambda n,i:i['rolls'][0].update(qty='19'))
  out=fix.fix(cur,p,w['purchase']['row_version']);f['receipt']=dict(purchase_id=out['purchase_id']);a=b.supplier_pay.read(cur,f)['Native_AP']
  check((D(a['final_ap']),D(a['paid']),D(a['remaining']))==(D('213.37'),D('100.17'),D('113.20')),'Correction19x11.23 preserves paid100.17',observed=a)
  check(b.delta(before,b.gl(cur))=={b.account(cur,'MATERIAL_INVENTORY'):D('22.46'),b.account(cur,'AP_SUPPLIER'):D('-22.46')},'Upward correction no extra cash payment')
  check(b.procurement.qty(cur,f)[0]==19,'Physical correction17to19 exact')
  return dict(payable=a,cash_changed=False)

 def sale_return_correction():
  f=b.production(cur,today);base=b.gl(cur);note.posted(cur,f,'13','29.91');b.returns.payments.pay(cur,f,'137.03')
  f['allocations']=b.returns.read(cur,f)['page']['rows'];p,v=b.returns.payload(cur,f,qty='4',refund='119.64');b.cmd.command(cur,'RETURN',p,v)
  root=f['sale'];historical=note.unchanged_facts(cur,root);before=b.gl(cur)
  for price in ('31.17','28.63'):
   p,v=note.edit(cur,f,price=price);bad=refusal(cur,lambda:note.correct(cur,p,v))
   check(bad['refused'] and b.gl(cur)==before,'Already returned price cannot silently change original refund',price=price,result=bad)
  p,v=note.edit(cur,f,qty='12');key=uuid.uuid4();out=note.correct(cur,p,v,key);f['sale']=out['sale_id']
  d=b.returns.source.read(cur,f)['detail'];expected={b.account(cur,'AR_CUSTOMER'):D('102.25'),b.account(cur,'SALES_REVENUE'):D('-239.28'),b.account(cur,'FG_INVENTORY'):D('-131.68'),b.account(cur,'COGS'):D('131.68'),f['cash_coa']:D('137.03')}
  check(b.delta(base,b.gl(cur))==expected,'12sold-4returned:8x29.91,8x16.46,paid137.03',observed=b.delta(base,b.gl(cur)))
  check(b.fg_qty(cur,f)==33 and D(d['financial']['open_balance'])==D('102.25'),'Quantity and AR agree after correction')
  check(note.unchanged_facts(cur,root)==historical,'Original posted items and quantities remain immutable')
  after=b.gl(cur);check(note.correct(cur,p,v,key)==out and b.gl(cur)==after,'Correction replay one outcome')
  return dict(net_units=8,FG=33,net_revenue='239.28',COGS='131.68',paid='137.03',AR='102.25')

 def late_partial_invoice():
  f=b.production(cur,today,final=False);f['receipt']=dict(purchase_id=f['purchase']);f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(f['purchase'],)).fetchone()[0]);before=b.gl(cur)
  one=b.invoices.finalize(cur,f,'17','13.11');a=b.invoices.amounts(cur,f)
  check(a[:3]==(D('222.87'),D('692.72'),D(32)),'First17 finalized; remaining56 GRNI at12.37; raw32 unchanged',observed=a)
  two=b.invoices.finalize(cur,f,'56','11.91');z=b.invoices.amounts(cur,f)
  check(z[:3]==(D('889.83'),D(0),D(32)),'Second invoice completes all73 without duplicate receipt',observed=z)
  delta=b.delta(before,b.gl(cur));check(sum(delta.values(),D(0))==0,'Each source delta remains balanced')
  check(delta.get(b.account(cur,'AP_SUPPLIER'))==D('-889.83') and delta.get(b.account(cur,'GRNI_MATERIAL'))==D('903.01'),'GRNI fully reverses estimated903.01 into actualAP889.83',delta=delta)
  check(b.fg_qty(cur,f)==41 and D(b.laundry.wip(cur,f['po']))==0,'Late monetary invoice creates no finished goods or WIP')
  return dict(first_AP='222.87',first_GRNI='692.72',final_AP='889.83',final_GRNI='0',raw=32,FG=41,journal_delta=delta,documents=[one,two])

 def wib_midnight():
  f=b.production(cur,today);yesterday=today-timedelta(days=1)
  before={d:b.finance.read(cur,d,as_of=str(today)) for d in (yesterday,today)};docs=[]
  tag=f['tag']
  for d,h,m,s,qty in ((yesterday,23,59,59,'3'),(today,0,0,1,'7')):
   f['tag']=tag+'-'+str(d)
   f['sale_at']=(b.prod.at(d,h,m)+timedelta(seconds=s)).isoformat();note.posted(cur,f,qty,'19.37')
   dates=cur.execute("select economic_date,transaction_date from erp.journal_entries where source_type='SALE' and source_id=%s and status='POSTED'",(f['sale'],)).fetchall()
   check(dates and all(e==d and t==d for e,t in dates),'Sale date follows WIB on either side of midnight',physical=f['sale_at'],dates=dates)
   docs.append(dict(id=f['sale'],physical=f['sale_at'],dates=dates))
  expected={yesterday:(D('58.11'),D('49.38')),today:(D('135.59'),D('115.22'))}
  for day,(revenue,cogs) in expected.items():
   after=b.finance.read(cur,day,as_of=str(today));x=before[day]['snapshot']['performance'];z=after['snapshot']['performance']
   check(D(z['sales_revenue_gl'])-D(x['sales_revenue_gl'])==revenue and D(z['cogs_gl'])-D(x['cogs_gl'])==cogs,'Dated report places actual money in proper WIB day',day=day,expected=[revenue,cogs],observed=[D(z['sales_revenue_gl'])-D(x['sales_revenue_gl']),D(z['cogs_gl'])-D(x['cogs_gl'])])
  return dict(documents=docs,revenue_yesterday='58.11',revenue_today='135.59',FG=b.fg_qty(cur,f))

 return [wrap('AS20-12_CREDIT_OTHER_INVOICE',supplier_credit),wrap('AS20-12_PAID_UPWARD',supplier_up),wrap('AS20-14_RETURNED_PAID_CORRECTION',sale_return_correction),wrap('AS20-11_50_PARTIAL_LATE_INVOICE',late_partial_invoice),wrap('AS20-09_WIB_MIDNIGHT',wib_midnight)]
