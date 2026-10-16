"""Astra r2 independent oracles. Synthetic fixtures; unchanged pinned product.

The first three cases are byte-preserved Astra physical/HPP oracles from r1.
Additional cases use writer setup/transport, but expected arithmetic, boundary
conditions and downstream-correction scenarios are declared by Astra.
"""
from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal as D
from datetime import timedelta
import sys, os, json, uuid

sys.path.insert(0, str(Path(os.environ['ASTRA_CANDIDATE_ROOT']).resolve() / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import psycopg
import retained_physical as prior
import cp7_cp17_fix_cases as f
import cp7_auto_po_cases as auto
import cp7_master_cases as master
import cp7_cutover_cases as cutover
import cp7_wave_sewing_cases as wave
import cp7_sales_draft_cases as drafts
import cp7_p18_full_cycle_probe as runner
import cp7_cp17_fix_probe as cp17_runner

NEW_IDS = [
 'ASTRA_R2_REOPEN_AFTER_REVERSED_FG_ADJUSTMENT',
 'ASTRA_R2_REOPEN_AFTER_CANCELLED_SALES_DRAFT',
 'ASTRA_R2_AUTO_PO_NUMBER_999_TO_1000',
 'ASTRA_R2_CASH_COMPOUND_EXACT_CENTS',
 'ASTRA_R2_CUTOVER_UTC_WIB_AND_OWNER_AUTHORITY',
 'ASTRA_R2_MASTER_BLOCKER_RELEASE_AND_REVOKED_REPLAY',
 'ASTRA_R2_DETECTOR_TWO_BASES_CONTROL_AND_RESTORE',
 'ASTRA_R2_WAVE_REVERSED_INPUT_ORDER_EXACT_WAGES',
]
IDS = prior.IDS + NEW_IDS

def one(cur, sql, args=()):
 return cur.execute(sql, args).fetchone()[0]

def all_findings(cur):
 f.b.api.admin(cur)
 return [list(r) for r in cur.execute('select * from cp7_guard.findings()').fetchall()]

def cases(cur, today):
 def lot_qty(lot):
  f.b.api.admin(cur)
  return one(cur, 'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s', (lot,))

 def finished():
  g=f.finish_fixture(cur,today,label='ASTRA-R2-REOPEN')
  f.finish_command(cur,f.finish_workspace(cur,g['po']),reason='Astra complete production control')
  assert lot_qty(g['lot'])==10 and f.reopen_workspace(cur,g['po'])['eligible']
  return g

 def test_reopen_after_adjustment():
  g=finished();hpp=f.po_hpp(cur,g['po']);accounts=f.fgadj.accounts(cur)
  loc=one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(g['lot'],))
  draft,_=f.fgadj.draft(cur,dict(location=loc,lot=g['lot'],product=g['product']),'-2')
  posted=f.fgadj.action(cur,'POST',draft)
  blocked=f.reopen_workspace(cur,g['po'])
  assert lot_qty(g['lot'])==8 and blocked['blockers']==[dict(kind='FG_USED',qty=2)],blocked
  f.fgadj.action(cur,'REVERSE',posted)
  assert lot_qty(g['lot'])==10 and f.fgadj.accounts(cur)==accounts and f.po_hpp(cur,g['po'])==hpp
  fresh=f.reopen_workspace(cur,g['po']);before=f.b.boundary.snapshot(cur)
  if not fresh['eligible']:
   refusal=f.refused(cur,lambda:f.reopen_command(cur,fresh,reason='Astra reopen after child reversal'),'CP7_PO_REOPEN_BLOCKED')
   f.unchanged(cur,before,'reopen after reversed child')
   return dict(status='COUNTEREXAMPLE',expected='reversed adjustment no longer blocks reopening',stock=[10,8,10],
               hpp_before_after=[str(x)for x in hpp],all_accounts_restored=True,blockers=fresh['blockers'],refusal=refusal)
  r=f.reopen_command(cur,fresh,reason='Astra reopen after child reversal')
  assert r['result']['status']!='FINISHED' and lot_qty(g['lot'])==10 and f.po_hpp(cur,g['po'])==hpp
  return dict(status='PASS',stock=[10,8,10],result=r)

 def test_reopen_after_sales_cancel():
  g=finished();accounts=drafts.cmd.accounts(cur)
  loc=one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(g['lot'],))
  customer=str(drafts.source.fg.base.create_customer(cur,'ASTRA-R2-'+uuid.uuid4().hex[:8]))
  sale=dict(g,location=loc,customer=customer,tag='ASTRA-R2-'+uuid.uuid4().hex[:10],
            sale_at=(drafts.source.fg.ax.r1.now(cur)-timedelta(minutes=1)).isoformat())
  drafts.create(cur,sale,drafts.payload(sale,qty='2',price='13.37'))
  assert lot_qty(g['lot'])==8
  blocked=f.reopen_workspace(cur,g['po']);assert not blocked['eligible']
  p,v=drafts.cmd.review(cur,sale);out=drafts.cmd.command(cur,'CANCEL',p,v)
  assert out['status']=='CANCELLED' and lot_qty(g['lot'])==10 and drafts.cmd.accounts(cur)==accounts
  fresh=f.reopen_workspace(cur,g['po'])
  if not fresh['eligible']:
   before=f.b.boundary.snapshot(cur)
   refusal=f.refused(cur,lambda:f.reopen_command(cur,fresh,reason='Astra reopen after cancelled sales draft'),'CP7_PO_REOPEN_BLOCKED')
   f.unchanged(cur,before,'cancelled draft still blocking reopen')
   return dict(status='COUNTEREXAMPLE',expected='cancelled draft reservation no longer blocks reopening',
               draft_status=out['status'],stock=[10,8,10],all_accounts_restored=True,blockers=fresh['blockers'],refusal=refusal)
  r=f.reopen_command(cur,fresh,reason='Astra reopen after cancelled sales draft')
  assert r['result']['status']!='FINISHED' and lot_qty(g['lot'])==10
  return dict(status='PASS',draft_status=out['status'],stock=[10,8,10])

 def test_auto_po_carry():
  g=auto.receipt(cur,today);body=auto.post_body(g,qty=2,pieces=2)
  pre=auto.prefix(cur,body['cutting']['cut_at']);f.b.api.admin(cur)
  assert one(cur,'select count(*) from erp.production_orders where po_number like %s',(pre+'%',))==0
  # Isolation fixture of 998 lawful, unused DRAFT POs, no stock or journal.
  cur.execute("""insert into erp.production_orders(po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
    select %s||lpad(n::text,3,'0'),%s,1,'DRAFT','CUTTING',%s::timestamptz,'Astra numbering boundary fixture'
    from generate_series(1,998)n""",(pre,body['model_id'],body['cutting']['cut_at']))
  control=auto.command(cur,body)
  assert control['po_number']==pre+'999' and auto.roll_stock(cur,g)==8,control
  before=f.b.boundary.snapshot(cur);private=one(cur,'select count(*) from cp7_cutting_correction.auto_po_history')
  timeout=one(cur,'show statement_timeout');cur.execute("select set_config('statement_timeout','10s',true)")
  cur.execute('savepoint astra_number_carry')
  try:
   result=auto.command(cur,body)
  except psycopg.errors.QueryCanceled as exc:
   error=str(exc);cur.execute('rollback to savepoint astra_number_carry');f.b.api.admin(cur)
   cur.execute('select set_config(\'statement_timeout\',%s,true)',(timeout,))
   cur.execute('release savepoint astra_number_carry')
   f.unchanged(cur,before,'number carry timeout')
   assert auto.roll_stock(cur,g)==8 and one(cur,'select count(*) from cp7_cutting_correction.auto_po_history')==private
   return dict(status='COUNTEREXAMPLE',expected=pre+'1000',control=control['po_number'],
               failure=error,sqlstate='57014',statement_timeout='10s (declared before execution)',stock_before_after=8,boundary_unchanged=True)
  else:
   cur.execute('release savepoint astra_number_carry');cur.execute('select set_config(\'statement_timeout\',%s,true)',(timeout,))
   assert result['po_number']==pre+'1000' and auto.roll_stock(cur,g)==6,result
   return dict(status='PASS',numbers=[control['po_number'],result['po_number']],stock=[10,8,6])

 def test_cash_cents():
  zone=one(cur,'show timezone');g=f.edit.fixture(cur,today,amount='37.13');p=f.pay.fixture(cur,today);p['cash']=g['bank']
  f.pay.command(cur,f.pay.payload(cur,p,'20.11'));cur.execute("select set_config('TimeZone',%s,false)",(zone,))
  assert f.balance(cur,g['bank'])==D('17.02')
  bad,v=f.spent_payload(cur,g,'20.10');before=f.b.boundary.snapshot(cur)
  refused=f.refused(cur,lambda:f.edit.correct(cur,bad,v),'CP7_CASH_NEGATIVE');f.unchanged(cur,before,'minus one cent correction')
  assert f.balance(cur,g['bank'])==D('17.02')
  good,v=f.spent_payload(cur,g,'31.15');r=f.edit.correct(cur,good,v);f.b.api.admin(cur)
  assert f.balance(cur,g['bank'])==D('11.04')
  assert one(cur,'select count(*) from cp7_guard.compound_scope')==0 and one(cur,'select count(*) from cp7_guard.compound_touch')==0
  relevant=[x for x in all_findings(cur)if str(x[1])==g['bank']];assert relevant==[],relevant
  return dict(status='PASS',receipt='37.13',spent='20.11',before='17.02',rejected_replacement='20.10',
              expected_rejected_balance='-0.01',refusal=refused,replacement='31.15',after='11.04',result=r,detector=relevant)

 def test_cutover_wib():
  owner=cutover.owner(cur);admin=master.role_actor(cur,'ADMIN');L,_,_=cutover.latest(cur)
  r=cutover.put(cur,owner,L,0,'Astra official WIB date boundary')
  forbidden=f.refused(cur,lambda:cutover.put(cur,admin,L-timedelta(days=1),1),'CP7_CUTOVER_DENIED')
  assert cutover.control(cur)==(1,L)
  g=f.misc.fixture(cur,today);before_day=L-timedelta(days=1)
  before=f.b.boundary.snapshot(cur)
  def income(at):
   p=cutover.income(g,'13.37',at)
   return f.misc.command(cur,'POST',f.misc.intent(f.misc.command(cur,'SAVE',p)))
  refusal=f.refused(cur,lambda:income(f'{before_day}T16:59:59Z'),'CP7_CUTOVER_BEFORE')
  f.unchanged(cur,before,'one second before WIB cutover')
  out=income(f'{before_day}T17:00:00Z');rows=cutover.misc_journals(cur,out['transaction_id'])
  assert len(rows)==1 and rows[0][:2]==[str(L),'POSTED'],rows
  return dict(status='PASS',official_date=str(L),utc_boundary=f'{before_day}T17:00:00Z',
              admin_refused=forbidden,before_second_refused=refusal,exact_boundary=rows,owner_result=r)

 def test_master_release():
  g=drafts.fixture(cur,today);code='ASTRA-'+uuid.uuid4().hex[:8].upper()
  subject=master.role_actor(cur,'ADMIN');key=uuid.uuid4();fields=master.customer_fields(code,'Toko Astra')
  c=master.create(cur,'CUSTOMER',fields,key=key,subject=subject);g['customer']=c['id']
  drafts.create(cur,g,drafts.payload(g,qty='1'));before=f.b.boundary.snapshot(cur)
  refused=f.refused(cur,lambda:master.act(cur,'CUSTOMER',c['id'],'DEACTIVATE'),'CP7_MASTER_BLOCKED');f.unchanged(cur,before,'customer with active draft')
  p,v=drafts.cmd.review(cur,g);drafts.cmd.command(cur,'CANCEL',p,v)
  off=master.act(cur,'CUSTOMER',c['id'],'DEACTIVATE');assert not off['entity']['active']
  assert drafts.options(cur,'CUSTOMER',g['sale_at'],q=code)['rows']==[]
  f.b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
  before=f.b.boundary.snapshot(cur)
  replay=f.refused(cur,lambda:master.create(cur,'CUSTOMER',fields,key=key,subject=subject),'CP7_MASTER_DENIED')
  f.unchanged(cur,before,'revoked master creator replay')
  return dict(status='PASS',active_draft_blocked=refused,cancelled_draft_allows_deactivation=True,hidden_from_sales_picker=True,revoked_replay=replay)

 def test_detector_restore():
  g=f.misc.fixture(cur,today);f.b.api.admin(cur);bank=g['cash']['id'];start=D(str(f.misc.cash_balance(cur,bank)))
  clean=all_findings(cur);before=f.b.boundary.snapshot(cur)
  trigger_before=one(cur,"select tgenabled::text from pg_trigger where tgrelid='erp.journal_lines'::regclass and tgname='cp7_guard_cash_not_negative'")
  cur.execute('savepoint astra_detector_injection')
  try:
   cur.execute('alter table erp.journal_lines disable trigger cp7_guard_cash_not_negative')
   p=f.misc.save_payload(g,'OTHER_EXPENSE',str(start+D('9.37')))
   f.misc.command(cur,'POST',f.misc.intent(f.misc.command(cur,'SAVE',p)));f.b.api.admin(cur)
   cur.execute('alter table erp.journal_lines enable trigger cp7_guard_cash_not_negative')
   dirty=all_findings(cur);added=[x for x in dirty if x not in clean]
   assert len(added)==2 and {x[0]for x in added}=={'CASH_NEGATIVE','CASH_NEGATIVE_BOOK_DATE'},added
   assert all(str(x[1])==bank and D(x[4])==D('-9.37')for x in added),added
  finally:
   cur.execute('rollback to savepoint astra_detector_injection');cur.execute('release savepoint astra_detector_injection');f.b.api.admin(cur)
  restored=all_findings(cur);assert restored==clean
  f.unchanged(cur,before,'detector controlled injection rollback')
  assert one(cur,"select tgenabled::text from pg_trigger where tgrelid='erp.journal_lines'::regclass and tgname='cp7_guard_cash_not_negative'")==trigger_before
  return dict(status='PASS',before=clean,during=dirty,after=restored,added=added,
              injection='only cp7_guard_cash_not_negative temporarily disabled within savepoint; entire injection rolled back',
              security_acceptance=False,guard_restored=True)

 def test_wave_order():
  g=wave.fixture(cur,today);A,B=g['A']['id'],g['B']['id'];w=wave.read(cur,g)
  at=wave.now(cur)-timedelta(seconds=30);key=uuid.uuid4()
  r=wave.record(cur,w,[(B,1),(A,2)],at,key=key)
  assert wave.record(cur,w,[(B,1),(A,2)],at,key=key)==r
  rows={x['sku_id']:x for x in r['result']['lines']};assert set(rows)=={A,B}
  actual={k:sum(D(x[4])for x in wave.lines_of(cur,v['work_completion_id']))for k,v in rows.items()}
  assert actual=={A:D('22'),B:D('31')} and D(str(r['result']['wage_amount']))==D('53'),(actual,r)
  assert wave.sewn_ready(cur,g)==(3,3)
  assert f.wage_journal(cur,rows[A]['work_completion_id'])==(D(22),D(22),1)
  assert f.wage_journal(cur,rows[B]['work_completion_id'])==(D(31),D(31),1)
  return dict(status='PASS',input_order=['B','A'],pieces={'A':2,'B':1},per_piece={'A':'10+1','B':'30+1'},
              wages={'A':'22','B':'31'},total='53',physical=[3,3],same_uuid_same_answer=True)

 extra=[test_reopen_after_adjustment,test_reopen_after_sales_cancel,test_auto_po_carry,test_cash_cents,
        test_cutover_wib,test_master_release,test_detector_restore,test_wave_order]
 return prior.cases(cur,today)+list(zip(NEW_IDS,extra))

if __name__=='__main__':
 manifest=json.loads(Path(__file__).with_name('OWN_ORACLES.json').read_text())
 assert manifest['candidate']=='2e9d6a468c110684c278d585418eb404250d1150' and manifest['native_ids']==IDS
 runner.cases=SimpleNamespace(EXPECTED=len(IDS),cases=cases)
 runner.verify=cp17_runner.verify
 runner.OUT=runner.bundle.ROOT/'cp6-proof/t3/ASTRA_R2_OWN_NATIVE.json'
 runner.package._writer_runtime=lambda browser_mode=False:runner.run()
 runner.package.run('install')
