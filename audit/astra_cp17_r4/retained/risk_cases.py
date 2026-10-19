"""Astra r3 independent arithmetic and alternate-route probes, predeclared before execution.
Fixture/transport helpers are writer-owned; assertions and scenarios below are Astra's.
No hosted endpoint, credential, product mutation or current-round auditor evidence.
"""
from decimal import Decimal as D
from datetime import timedelta
import json, uuid
import cp7_cp17_fix_cases as f
import cp7_r3_rate_cases as rate
import cp7_r3_hpp_pool_cases as pool
import cp7_nota_cases as nota
import cp7_cash_funding as funding

NATIVE=['ASTRA_R3_REOPEN_POSITIVE_ADJUSTMENT_INVERSE',
        'ASTRA_R3_MIXED_RATES_NOTA_PAYROLL_HPP']
HTTP=['ASTRA_R3_POOL_PUBLIC_CLOSED_PERIOD',
      'ASTRA_R3_POOL_PUBLIC_REVOKED_MANAGE']
EXPECTED=len(NATIVE)+len(HTTP)

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]

def cases(cur,today):
 def positive_inverse():
  g=f.finish_fixture(cur,today,label='ASTRA-R3-FG-POSITIVE')
  f.finish_command(cur,f.finish_workspace(cur,g['po']),reason='Astra all ten pieces finished')
  def qty():
   f.b.api.admin(cur)
   return one(cur,'select sum(qty_signed) from erp.fg_stock_movements where lot_id=%s',(g['lot'],))
  assert qty()==10 and f.reopen_workspace(cur,g['po'])['eligible']
  hpp=f.po_hpp(cur,g['po'])
  loc=one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(g['lot'],))
  draft,_=f.fgadj.draft(cur,dict(location=loc,lot=g['lot'],product=g['product']),'2')
  posted=f.fgadj.action(cur,'POST',draft);assert qty()==12
  f.fgadj.action(cur,'REVERSE',posted)
  assert qty()==10 and f.po_hpp(cur,g['po'])==hpp
  w=f.reopen_workspace(cur,g['po']);before=f.b.boundary.snapshot(cur)
  movements=[list(x)for x in cur.execute('select id::text,qty_signed,reversal_of_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id',(g['lot'],)).fetchall()]
  evidence=dict(stock=[10,12,10],hpp_before_after=[str(x)for x in hpp],movements=movements,blockers=w['blockers'],expected='positive adjustment and its own inverse leave no active downstream use')
  if not w['eligible']:
   refusal=f.refused(cur,lambda:f.reopen_command(cur,w,reason='Astra positive child already reversed'),'CP7_PO_REOPEN_BLOCKED')
   f.unchanged(cur,before,'positive adjustment inverse reopen refusal')
   return dict(status='COUNTEREXAMPLE',refusal=refusal,**evidence)
  r=f.reopen_command(cur,w,reason='Astra positive child already reversed')
  assert r['result']['status']!='FINISHED' and qty()==10 and f.po_hpp(cur,g['po'])==hpp
  return dict(status='PASS',result=r,**evidence)

 def mixed_rates():
  g=rate.fixture(cur,today);initial=f.po_wip_balance(cur,g['po'])
  first=rate.record(cur,rate.read(cur,g),2,g['at'](10))
  rate.raise_rate(cur,g,5,g['day']+timedelta(days=1))
  nextday=g['day']+timedelta(days=1)
  at=lambda h:f.cut.cutting.qc.physical.b.chain.production.at(nextday,h,0)
  second=rate.record(cur,rate.read(cur,g),3,at(10),'NEW')
  third=rate.record(cur,rate.read(cur,g),1,at(11),'OLD')
  w=rate.read(cur,g);rate.send(cur,w,rate.switch_body(w,reason='Astra use new rates for this PO'))
  last=rate.record(cur,rate.read(cur,g),4,at(12))
  results=[first,second,third,last];expected=[D(8),D(18),D(4),D(24)]
  details=[]
  for r,want in zip(results,expected):
   cid=r['result']['work_completion_id'];lines=rate.lines(cur,cid)
   got=sum(D(x[3])for x in lines)
   assert got==want and f.wage_journal(cur,cid)==(want,want,1),(lines,want)
   details.append(dict(completion=cid,lines=lines,amount=str(got)))
  assert f.sewn_ready(cur,g)==(10,10) and f.po_wip_balance(cur,g['po'])==initial+54
  # The selected Nota is administrative: do not earn the same 54 again.
  cards=nota.read(cur,'SOURCES',contractor_id=g['mandor'])['page']['rows']
  assert cards and sum(D(c['remaining_amount'])for c in cards)==54,cards
  p=dict(contractor_id=g['mandor'],note_date=str(today),period_start=str(g['day']),period_end=str(today),notes='Astra mixed rates',
         cards=[dict(card_key=c['card_key'],source_token=c['source_token'])for c in cards])
  n=nota.command(cur,'SAVE',p);posted=nota.act(cur,'POST',n);pid=posted['payroll_id']
  assert one(cur,'select labor_total from erp.payroll_settlements where id=%s',(pid,))==54
  assert cur.execute('select sum(qty_payable),sum(amount) from erp.payroll_work_items where payroll_id=%s',(pid,)).fetchone()==(20,D(54))
  assert f.po_wip_balance(cur,g['po'])==initial+54
  bank=str(f.bc.bank_account(cur,'A3R'+uuid.uuid4().hex[:10]));funding.fund(cur,bank,'54.00',g['day']);f.b.api.admin(cur)
  f.s.act(cur,'PREPARE',f.s.doc(cur,pid));f.s.act(cur,'APPROVE',f.s.doc(cur,pid))
  approved=f.s.doc(cur,pid);key=uuid.uuid4()
  paid=f.s.act(cur,'PAY',approved,key,payment_date=str(today),cash_account_id=bank)
  assert f.s.act(cur,'PAY',approved,key,payment_date=str(today),cash_account_id=bank)==paid and paid['status']=='PAID'
  balance=one(cur,"select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and l.account_id=(select coa_account_id from erp.cash_accounts where id=%s)",(bank,))
  payable=one(cur,"select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_PAYABLE')",(g['mandor'],))
  assert balance==payable==0 and f.po_wip_balance(cur,g['po'])==initial+54
  wash=dict(f.laundry_for(cur,dict(g,day=nextday,at=at)),po=g['po'])
  delivery=f.bd.post_priced(cur,wash,{},qty=10,hour=13)['delivery_id']
  receipt=f.bd.receive(cur,delivery,wash,10,14)['receipt_id'];f.b.api.admin(cur)
  f.bd.finish_goods(cur,wash,receipt,10,15);f.b.api.admin(cur)
  f.finish_command(cur,f.finish_workspace(cur,g['po']),reason='Astra mixed old and new wages reconciled')
  hpp,pcs=f.po_hpp(cur,g['po'])
  assert (hpp,pcs,f.po_wip_balance(cur,g['po']))==(initial+54+20,10,D(0))
  # Reading and preparing the source must not mutate its retained rates.
  assert [sum(D(x[3])for x in rate.lines(cur,r['result']['work_completion_id']))for r in results]==expected
  return dict(status='PASS',pieces=[2,3,1,4],rate_choice=['LOCKED','NEW','OLD','ALWAYS_NEW'],per_piece=[4,6,4,6],
              wages=['8','18','4','24'],wages_total='54',payroll_component_qty=20,physical_pcs=10,payment='54',bank=0,mandor_payable=0,
              material=str(initial),laundry='20',hpp=str(hpp),hpp_expected=str(initial+74),wip=0,details=details)
 return list(zip(NATIVE,[positive_inverse,mixed_rates]))

def http_cases(http,today):
 def legacy_closed():
  user=http.login('OWNER','astra-r3-pool-closed')
  with http.connect()as conn,conn.cursor()as cur:
   g=pool.fixture(cur,today,offset=3);day=g['day'];pool.set_closed(cur,day)
   pv=pool.read(cur,user.auth_user_id,day,day)['preview'];before=f.b.boundary.snapshot(cur);conn.commit()
  current=user.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=pool.create_body(pv),p_request=str(uuid.uuid4())))
  assert current['status']>=400 and 'CP7_HPP_POOL_PERIOD_CLOSED' in json.dumps(current['body']),current
  with http.connect()as conn,conn.cursor()as cur:assert f.b.boundary.snapshot(cur)==before
  cr=user.rpc('erp_create_attendance_hpp_pool_v1',dict(p_payload=dict(period_start=str(day),period_end=str(day),reason='Astra closed period old public route'),p_client_request_id=str(uuid.uuid4())))
  if cr['status']>=400:
   with http.connect()as conn,conn.cursor()as cur:assert f.b.boundary.snapshot(cur)==before
   return dict(status='PASS',new_route=current,old_route=cr,closed_boundary_unchanged=True)
  with http.connect()as conn,conn.cursor()as cur:
   rows=pool.native_pools(cur,day);assert len(rows)==1 and rows[0]['status']=='DRAFT',rows
   pid=rows[0]['id'];version=rows[0]['row_version']
  ac=user.rpc('erp_activate_attendance_hpp_pool_v1',dict(p_pool_id=pid,p_reason='Astra old public activation closed books',p_client_request_id=str(uuid.uuid4()),p_expected_version=version))
  with http.connect()as conn,conn.cursor()as cur:
   rows=pool.native_pools(cur,day);cost=pool.active_view(cur,g['po_a'])
   journals=[list(x)for x in cur.execute("select status,source_type,economic_date,transaction_date from erp.journal_entries where source_id=%s order by economic_date,id",(pid,)).fetchall()]
   grants={n:one(cur,"select has_function_privilege('authenticated',%s,'EXECUTE')",(n,))for n in ('public.erp_create_attendance_hpp_pool_v1(jsonb,uuid)','public.erp_activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)')}
  return dict(status='COUNTEREXAMPLE',expected='closed-period pool actions refused through every reachable public route',
              real_Auth=True,public_Data_API=True,test_only_schema_grant=False,cp7_refused=current,legacy_create=cr,legacy_activate=ac,
              native_rows=rows,po_active_cost=str(cost),journals=journals,grants=grants,
              owner_boundary='D14-9 deferral explicitly conditioned on functions being unreachable from internet; these are public facades')

 def legacy_permission():
  user=http.login('ADMIN','astra-r3-pool-permission')
  with http.connect()as conn,conn.cursor()as cur:
   g=pool.fixture(cur,today,offset=1);day=g['day']
   role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(user.auth_user_id,))
   cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')on conflict do nothing",(role,))
   pv=pool.read(cur,user.auth_user_id,day,day)['preview']
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.manage'",(role,))
   before=f.b.boundary.snapshot(cur);conn.commit()
  new=user.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=pool.create_body(pv),p_request=str(uuid.uuid4())))
  assert new['status']>=400 and 'CP7_HPP_POOL_DENIED' in json.dumps(new['body']),new
  with http.connect()as conn,conn.cursor()as cur:assert f.b.boundary.snapshot(cur)==before
  old=user.rpc('erp_create_attendance_hpp_pool_v1',dict(p_payload=dict(period_start=str(day),period_end=str(day),reason='Astra public route after manage revoked'),p_client_request_id=str(uuid.uuid4())))
  with http.connect()as conn,conn.cursor()as cur:
   rows=pool.native_pools(cur,day)
   if old['status']>=400:assert f.b.boundary.snapshot(cur)==before
   else:assert len(rows)==1 and rows[0]['status']=='DRAFT'
  return dict(status='COUNTEREXAMPLE' if old['status']==200 else 'PASS',expected='revoked HPP manage right respected by every public pool writer',
              real_Auth=True,public_Data_API=True,test_only_schema_grant=False,cp7_refused=new,legacy=old,native_rows=rows)
 return list(zip(HTTP,[legacy_closed,legacy_permission]))
