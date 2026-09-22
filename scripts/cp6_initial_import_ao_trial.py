#!/usr/bin/env python3
"""Focused AO proposal on genuine AN; all changes and fixtures roll back."""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import json,subprocess,traceback,uuid
import psycopg
import cp6_v2620an_runtime as runtime
import cp6_v2620al_import_review as inherited
import cp6_final_gap_native as calendar
import cp6_foundation_qualification as foundation
from cp6_v2620ao_definitions import FUNCTIONS,PREDECESSOR,SCHEMA,DATE_ID
from cp6_v2620n_rollback_guards import function_catalog
ROOT=Path('cp6-proof/initial-import');ROOT.mkdir(parents=True,exist_ok=True)
actors,base,production=inherited.actors,inherited.base,inherited.production
report=dict(status='INCOMPLETE',cases={},production_go=False,independent_acceptance=False,migration_installed=False,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
def save():(ROOT/'AO_TRIAL.json').write_text(json.dumps(report,indent=2,default=str)+'\n')

def retail(cur,today,factor,price='3.25',qty='7'):
 cat,uom=foundation.category(cur,factor)
 mat=foundation.material(cur,'ACCESSORY',cat);loc,_=foundation.locations(cur)
 foundation.purchase(cur,mat,loc,300,2,foundation.MASTER['t0'])
 cur.execute('insert into erp.contractor_accessory_price_versions(contractor_id,category_id,selling_price,selling_uom_code,effective_from) values(%s,%s,%s,%s,%s)',(foundation.MASTER['contractor'],cat,Decimal(factor)*3,uom,foundation.MASTER['start']))
 payload=dict(issue_number=foundation.tag(),contractor_id=foundation.MASTER['contractor'],location_id=loc,physical_at=foundation.MASTER['t3'],change_reason='AO explicit manual retail price',items=[dict(material_id=mat,qty=qty,manual_retail_unit_price=price)])
 before=foundation.stock(cur,mat)
 result,error=foundation.attempt(cur,lambda:foundation.call(cur,'erp.save_contractor_material_issue_draft_v2',foundation.encode(payload),uuid.uuid4(),None))
 if price in('-1','NaN','0.005') or qty!='7':
  assert error and foundation.stock(cur,mat)==before,(result,error)
  return dict(status='PASS',invalid_refused=error)
 assert error is None,error
 issue=result['contractor_material_issue_id']
 actual=cur.execute('select qty,transaction_qty,base_qty_per_transaction_uom,unit_sale_price_snapshot,total_receivable from erp.contractor_material_issue_items where issue_id=%s',(issue,)).fetchone()
 assert actual==(7,7,1,Decimal(price),Decimal('22.75')),actual
 assert foundation.stock(cur,mat)==before
 foundation.call(cur,'erp.post_contractor_material_issue_v2',issue,uuid.uuid4(),result['row_version'],'AO exact retail post')
 stock=cur.execute('select cached_stock_qty from erp.materials where id=%s',(mat,)).fetchone()[0]
 charge=cur.execute("select sum(l.debit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_id=%s and j.source_type='CONTRACTOR_MATERIAL_RECEIVABLE'",(issue,)).fetchone()[0]
 assert (stock,charge)==(293,Decimal('22.75')),(stock,charge)
 return dict(status='PASS',physical_pcs=7,remaining=293,receivable='22.75',master_basis=factor)

def invoice_date(cur,today,zone,closed):
 received=today-timedelta(days=1);invoice=calendar.months_before(received,2)
 original_rpc=production.rpc
 dated_journals=[]
 def traced_rpc(cursor,name,payload,*args,**kwargs):
  tracked=name=='erp.finalize_material_purchase_invoice_v2'
  if tracked:
   actors.admin(cursor);before={r[0] for r in cursor.execute('select id from erp.journal_entries').fetchall()}
  value=original_rpc(cursor,name,payload,*args,**kwargs)
  if tracked:
   actors.admin(cursor)
   fresh=cursor.execute("select id,source_type,economic_date,transaction_date from erp.journal_entries where source_type in('MATERIAL_COST_REVALUATION','PO_HPP_GL_SYNC','MATERIAL_SUPPLIER_INVOICE','MATERIAL_ADJUSTMENT_REVALUATION')").fetchall()
   fresh=[r for r in fresh if r[0] not in before]
   assert all(r[2]==invoice and r[3]==(today if closed else invoice) for r in fresh),fresh
   dated_journals.extend(fresh)
   pending=cursor.execute("select count(*) from erp.cost_recalc_queue q where q.status in('PENDING','RUNNING','FAILED') and q.entity_id in(select cg.po_id from erp.cutting_groups cg join erp.material_stock_movements m on m.source_id=cg.id and m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') join erp.material_purchase_items i on i.material_id=m.material_id where i.purchase_id=%s)",(payload['purchase_id'],)).fetchone()[0]
   assert pending==0,'Invoice returned before affected HPP was ready'
  return value
 production.rpc=traced_rpc
 try:result=calendar.calendar_case(cur,today,invoice,received,zone,closed)
 finally:production.rpc=original_rpc
 assert len(dated_journals)>=4,dated_journals
 assert result['status'] in('PASS','DATE_POLICY_REVIEW_REQUIRED'),result
 assert result['current_totals_reconciled'] and len(result['observations'])==2
 for o in result['observations']:
  assert not o['mismatches'],o['mismatches']
  assert o['state']['revaluation_events'] and all(r[1]==invoice for r in o['state']['revaluation_events']),o['state']['revaluation_events']
 # Keep initial production GL events at their original economic dates. Only
 # material-recognized invoice deltas must carry the chosen invoice date.
 actors.admin(cur)
 assert cur.execute('select count(*) from erp.invoice_recost_execution_context').fetchone()[0]==0
 return dict(status='PASS',invoice_date=invoice,zone=zone,closed=closed,original_observation=result)

def direct_correction_reversal(cur,today,closed):
 actors.admin(cur)
 mat=production.prior.clone_material(cur,'ao-direct');loc,_=foundation.locations(cur)
 purchase_day=today-timedelta(days=8);invoice_day=today-timedelta(days=2)
 production.prior.set_open_period(cur,purchase_day-timedelta(days=1))
 payload=dict(purchase_number=foundation.tag(),supplier_id=foundation.MASTER['supplier'],location_id=loc,
   supplier_invoice_number=foundation.tag(),physical_at=production.at(purchase_day,10),change_reason='Direct final receipt fixture',
   lines=[dict(material_id=mat,qty=20,unit_price=2,price_state='FINAL',price_source='SUPPLIER_INVOICE',rolls=[dict(roll_number=foundation.tag(),qty=20)])])
 saved=foundation.call(cur,'erp.save_material_purchase_draft_v2',foundation.encode(payload),uuid.uuid4(),None)
 foundation.call(cur,'erp.post_material_purchase_v2',saved['purchase_id'],uuid.uuid4(),saved['row_version'],'Post direct final receipt')
 actors.admin(cur)
 item,roll=cur.execute('select i.id,r.id from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=%s',(saved['purchase_id'],)).fetchone()
 adj=foundation.call(cur,'erp.save_material_adjustment_draft_v2',foundation.encode(dict(adjustment_number=foundation.tag(),reason_code='COUNT_CORRECTION',
   physical_at=production.at(today-timedelta(days=5),10),location_id=loc,change_reason='Direct correction consumed stock',items=[dict(material_id=mat,roll_id=roll,qty_signed=-5)])),uuid.uuid4(),None)
 foundation.call(cur,'erp.post_material_adjustment_v2',adj['material_adjustment_id'],uuid.uuid4(),adj['row_version'],'Post shortage')
 actors.admin(cur)
 corr=cur.execute('insert into erp.material_purchase_cost_corrections(correction_number,purchase_id,invoice_date,reason) values(%s,%s,%s,%s) returning id',(foundation.tag(),saved['purchase_id'],invoice_day,'Authoritative direct invoice correction')).fetchone()[0]
 cur.execute('insert into erp.material_purchase_cost_correction_items(correction_id,purchase_item_id,new_unit_price) values(%s,%s,3)',(corr,item))
 if closed:foundation.call(cur,'erp.close_accounting_through',invoice_day,'Close direct invoice economic date')
 before=production.ledger(cur);actors.admin(cur);ids={r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()}
 foundation.call(cur,'erp.post_material_purchase_cost_correction',corr);actors.admin(cur)
 posted=production.ledger(cur);assert posted['MATERIAL_INVENTORY']-before['MATERIAL_INVENTORY']==15 and posted['AP_SUPPLIER']-before['AP_SUPPLIER']==-20
 fresh=[r for r in cur.execute('select id,economic_date,transaction_date from erp.journal_entries').fetchall() if r[0] not in ids]
 assert len(fresh)>=2 and all(d==invoice_day and t==(today if closed else invoice_day) for _,d,t in fresh),fresh
 ids|={r[0] for r in fresh}
 foundation.call(cur,'erp.reverse_material_purchase_cost_correction',corr,'Reverse direct invoice correction');actors.admin(cur)
 assert production.ledger(cur)==before
 fresh=[r for r in cur.execute('select id,economic_date,transaction_date from erp.journal_entries').fetchall() if r[0] not in ids]
 assert len(fresh)>=2 and all(d==today and t==today for _,d,t in fresh),fresh
 assert cur.execute('select count(*) from erp.invoice_recost_execution_context').fetchone()[0]==0
 return dict(status='PASS',closed=closed,post_invoice_date=invoice_day,reversal_date=today,all_legs_same_date=True,ledger_restored=True)

save()
try:
 with psycopg.connect('postgresql://supabase_admin:postgres@127.0.0.1:54322/postgres') as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='150s';set local lock_timeout='8s'")
  assert len(runtime.verified_successor(cur))==692
  before=actors.boundary(cur);catalog=function_catalog(cur)
  for identity,definition,acl,owner in PREDECESSOR:
   assert cur.execute('select pg_get_functiondef(p.oid),p.proacl::text,pg_get_userbyid(p.proowner) from pg_proc p where p.oid=to_regprocedure(%s)',(identity,)).fetchone()==(definition,acl,owner),identity
  cur.execute('set local role postgres');cur.execute(SCHEMA,prepare=False)
  for identity,definition in FUNCTIONS.items():cur.execute(definition,prepare=False)
  cur.execute(f'revoke all on function {DATE_ID} from public,anon,authenticated,service_role')
  actors.admin(cur);cur.execute('grant usage on schema erp to authenticated')
  actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'));base.load_fixture_foundation(cur);actors.admin(cur)
  today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
  start=production.at(today-timedelta(days=1),0)
  model,contractor=cur.execute("select model_id,contractor_id from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()
  foundation.OWNER=base.OPERATOR_AUTH
  foundation.MASTER=dict(model=model,contractor=contractor,start=start,supplier=cur.execute("select id from erp.suppliers where supplier_code='CP6-RACE-SUP'").fetchone()[0],pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT'").fetchone()[0],t0=start+timedelta(hours=1),t3=start+timedelta(hours=4))
  cases=[('RETAIL:'+str(f),lambda f=f:retail(cur,today,f)) for f in (12,144)]
  cases += [('BAD_PRICE:'+p,lambda p=p:retail(cur,today,12,p)) for p in ('-1','NaN','0.005')]
  cases += [('FRACTIONAL_PCS',lambda:retail(cur,today,12,qty='7.0000001'))]
  cases += [('INVOICE:'+z+':'+str(c),lambda z=z,c=c:invoice_date(cur,today,z,c)) for z in ('UTC','Pacific/Kiritimati') for c in (False,True)]
  cases += [('DIRECT_CORRECTION_REVERSAL:'+str(c),lambda c=c:direct_correction_reversal(cur,today,c)) for c in (False,True)]
  for name,fn in cases:
   actors.admin(cur);baseline=actors.boundary(cur);cur.execute('savepoint ao_case')
   try:r=fn()
   except Exception as exc:r=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint ao_case');actors.admin(cur);cur.execute('release savepoint ao_case')
   r['boundary_restored']=actors.boundary(cur)==baseline
   if not r['boundary_restored']:r['status']='INCOMPLETE'
   report['cases'][name]=r;save();print(json.dumps(dict(case=name,status=r['status'],error=r.get('error'),traceback=r.get('traceback')),default=str),flush=True)
  conn.rollback();cur.execute("set local timezone='Asia/Jakarta'");assert actors.boundary(cur)==before and function_catalog(cur)==catalog
  report['complete_boundary_restored']=True
  report['status']='WRITER_TRIAL_PASS' if all(r['status']=='PASS' for r in report['cases'].values()) else 'INCOMPLETE'
except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
save();print(json.dumps({k:v for k,v in report.items() if k!='cases'},default=str))
raise SystemExit(0 if report['status']=='WRITER_TRIAL_PASS' else 1)
