"""Independent r2 boundary oracles. All rows synthetic; product source stays unchanged."""
from datetime import timedelta
from decimal import Decimal as D
import time, uuid
import psycopg
import cp7_auto_po_cases as po
import cp7_wave_sewing_cases as wave
import cp7_cp17_fix_cases as c

IDS=['SOL_R2_AUTO_PO_NUMBER_999_CONTROL','SOL_R2_AUTO_PO_NUMBER_1000_BOUNDED',
     'SOL_R2_WAVE_5_2_9_PARTIAL_REVERSE_REPOST']

def factory(cur,today):
 def number_case(last):
  f=po.receipt(cur,today);body=po.post_body(f);prefix=po.prefix(cur,body['cutting']['cut_at'])
  po.b.api.admin(cur)
  # Native lifecycle permits only DRAFT/CUTTING for new operational rows. These
  # unused PO headers carry no stock, journal, cutting or accounting effect.
  cur.execute("""insert into erp.production_orders(po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
    select %s||lpad(i::text,3,'0'),%s,1,'DRAFT','CUTTING',%s::timestamptz,'Sol synthetic number boundary'
    from generate_series(1,%s)i where not exists(select 1 from erp.production_orders o where o.po_number=%s||lpad(i::text,3,'0'))""",
    (prefix,po.prod().MODEL,body['cutting']['cut_at'],last,prefix))
  numbers=set(x[0] for x in cur.execute('select po_number from erp.production_orders where po_number like %s',(prefix+'%',)))
  n=len(numbers)+1
  while prefix+str(n).zfill(3) in numbers:n+=1
  expected=prefix+str(n).zfill(3)
  assert n==last+1,(n,last)
  assert po.roll_stock(cur,f)==10
  before=po.b.boundary.snapshot(cur);started=time.monotonic();answer=None;error=None
  cur.execute('savepoint sol_number_boundary')
  cur.execute("set local statement_timeout='3s'")
  try:answer=po.command(cur,body)
  except psycopg.Error as exc:
   error=dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary,context=exc.diag.context)
   cur.execute('rollback to savepoint sol_number_boundary')
  finally:
   cur.execute('release savepoint sol_number_boundary');po.b.api.admin(cur)
   cur.execute("set local statement_timeout='240s'")
  elapsed=round(time.monotonic()-started,3)
  if answer is None:
   unchanged=po.b.boundary.snapshot(cur)==before
   assert unchanged and po.roll_stock(cur,f)==10
   return dict(status='COUNTEREXAMPLE' if error['sqlstate']=='57014' else 'INCOMPLETE',
    expected_number=expected,existing_daily_numbers=last,deadline_seconds=3,elapsed_seconds=elapsed,
    error=error,whole_business_boundary_unchanged=unchanged,stock_after='10',session_role='OWNER',
    scope='Native public auto-PO command; synthetic unused Native PO headers only')
  assert answer['po_number']==expected and po.roll_stock(cur,f)==0,answer
  assert po.po_state(cur,expected)['posted']==1
  return dict(status='PASS',expected_number=expected,actual_number=answer['po_number'],
   existing_daily_numbers=last,elapsed_seconds=elapsed,one_posted_cutting=True,stock_after='0',session_role='OWNER')
 def wave_dimensions():
  g=wave.fixture(cur,today,yields=(5,2,9));A,B=g['A']['id'],g['B']['id'];at=wave.now(cur)-timedelta(seconds=30)
  w=wave.read(cur,g);capacity={x['sku_id']:x['max_qty'] for x in w['wave']['skus']}
  assert (capacity[A],capacity[B],w['max_qty'])==(7,9,16)
  r=wave.record(cur,w,[(A,3),(B,5)],at);lines={x['sku_id']:x for x in r['result']['lines']}
  assert D(str(r['result']['wage_amount']))==D('188')
  assert wave.wage_journal(cur,lines[A]['work_completion_id'])==(D('33'),D('33'),1)
  assert wave.wage_journal(cur,lines[B]['work_completion_id'])==(D('155'),D('155'),1)
  w2=wave.read(cur,g);k={x['sku_id']:x for x in w2['wave']['skus']}
  assert (k[A]['max_qty'],k[B]['max_qty'],wave.sewn_ready(cur,g))==(4,4,(8,8))
  c.sewing_command(cur,w2,event=lines[B]['sewing_event_id'],reason='Sol salah jumlah SKU B, dibetulkan')
  w3=wave.read(cur,g);k={x['sku_id']:x for x in w3['wave']['skus']}
  assert (k[A]['max_qty'],k[B]['max_qty'],wave.sewn_ready(cur,g))==(4,9,(3,3))
  again=wave.record(cur,w3,[(A,4),(B,9)],wave.now(cur)-timedelta(seconds=10))
  assert D(str(again['result']['wage_amount']))==D('323')
  assert wave.sewn_ready(cur,g)==(16,16) and wave.read(cur,g)['max_qty']==0
  # 3*A(11) + replacement 4*A(11)+9*B(31)=356; canceled B(155)
  # is excluded by summing every debit including the negative inverse lines.
  po.b.api.admin(cur)
  net=cur.execute("""with source as(select j.id from erp.journal_entries j
   where j.source_type='WORK_COMPLETION' and j.source_id in
    (select id from erp.work_completion_events where cutting_group_id=%s))
   select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
   join erp.journal_entries j on j.id=l.journal_entry_id
   where (j.id in(select id from source) or j.reversal_of_id in(select id from source))
   and l.account_id=erp.account_id('WIP')""",(g['group'],)).fetchone()[0]
  assert net==D('356'),net
  return dict(status='PASS',sizes=[5,2,9],sku_capacity=[7,9],first_qty=[3,5],first_wage='188.00',
   canceled_sku='B',canceled_wage='155.00',replacement_qty=[4,9],replacement_wage='323.00',
   literal_effective_wage='356.00',final_sewn_ready=[16,16],observed_net_wip_with_inverses=str(net),
   session_role='OWNER',oracle='Literal dimensional arithmetic, not workspace totals')
 return list(zip(IDS,[lambda:number_case(998),lambda:number_case(999),wave_dimensions]))
