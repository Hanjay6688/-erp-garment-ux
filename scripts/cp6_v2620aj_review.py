#!/usr/bin/env python3
"""AJ writer gate: original oracles, new recovery scenarios, exact restoration."""
from pathlib import Path
from datetime import date,timedelta
from decimal import Decimal
import argparse,hashlib,importlib.util,json,os,sys,traceback,uuid
sys.path.insert(0,str(Path.cwd()/'scripts'))
import psycopg
import cp6_v2620aj_runtime as runtime
import cp6_v2620ai_family as original
import cp6_ai_independent_review as work
import cp6_final_crossflow_review as invoices
import cp6_final_gap_native as gaps
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

ROOT=Path('cp6-proof/writer-aj')
URL='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
ADMIN=URL.replace('postgres:postgres@','supabase_admin:postgres@')
actors,base,prior,peer=original.actors,original.base,original.prior,original.peer
production=gaps.production

def save(name,data):
 ROOT.mkdir(parents=True,exist_ok=True)
 (ROOT/(name+'.json')).write_text(json.dumps(data,indent=2,default=str)+'\n')

def normal(value):return json.loads(json.dumps(value,default=str))

def install():
 head,tree=runtime.verify_audit_source()
 with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta'")
  runtime.verify_predecessor(cur)
  save('AI_BASELINE',dict(catalog=function_catalog(cur),boundary=snapshot(cur)))
  cur.execute('set local role postgres')
  cur.execute(original.ah.ag.sql_body(runtime.MIGRATION),prepare=False)
  cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',
   (runtime.STAMP,runtime.NAME,[runtime.MIGRATION.read_text()]))
  assert len(runtime.verified_successor(cur))==690
  conn.commit()
 result=dict(status='PASS',head=head,tree=tree,functions=533,objects=690,production_go=False)
 save('INSTALL',result);return result

def bs_action(cur,kind,payload,version=None,key=None):
 production.owner(cur)
 return cur.execute('select public.erp_save_bs_resolution_action_v1(%s,%s::jsonb,%s,%s)',
  (kind,json.dumps(payload,default=str),key or uuid.uuid4(),version)).fetchone()[0]

def version(cur,table,ident):
 assert table in ('bs_cases','rework_orders')
 actors.admin(cur)
 return cur.execute(f'select row_version from erp.{table} where id=%s',(ident,)).fetchone()[0]

def po_state(cur,po):
 actors.admin(cur)
 return cur.execute("""select jsonb_build_object(
  'fg_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots f on f.id=m.lot_id where f.po_id=%s),
  'fg',(select fg_value from erp.po_hpp_gl_state where po_id=%s),
  'wip',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l where l.po_id=%s and l.account_id=erp.account_id('WIP')),
  'hpp',(select md5(coalesce(string_agg(to_jsonb(h)::text,'' order by h.id),'')) from erp.hpp_versions h join erp.fg_lots f on f.id=h.lot_id where f.po_id=%s),
  'entitlements',(select count(*) from erp.contractor_accessory_reimbursement_entitlements e join erp.fg_lots f on f.id=e.lot_id where f.po_id=%s))""",(po,)*5).fetchone()[0]

def rework_case(cur,today,initial_good,first_route,failed_wash,mixed_rates=False):
 f=work.draft(cur,today,Decimal(0));po=f['po']
 peer.ordinary(cur);cur.execute('select erp.post_work_completion(%s)',(f['completion'],))
 production.owner(cur)
 cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',
  (json.dumps(dict(work_completion_id=str(f['completion']),qty_pcs=10,reason='AJ ten original physical pieces')),uuid.uuid4()))
 actors.admin(cur)
 day=cur.execute("select (physical_at at time zone 'Asia/Jakarta')::date from erp.work_completion_events where id=%s",(f['completion'],)).fetchone()[0]
 batch=cur.execute('select b.id from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id=%s',(f['group'],)).fetchone()[0]
 product=base.create_product(cur,'AJ-'+uuid.uuid4().hex[:12])
 f.update(batch=str(batch),group=str(f['group']),product=product)
 production.owner(cur)
 sent=base.post_delivery(cur,f,base.BASE_PROCESS,production.at(day,11).isoformat())['delivery_id']
 if failed_wash:
  base.action(cur,'POST_FAILED_WASH',dict(delivery_id=sent,wash_process_id=base.BASE_PROCESS,
   custody_outcome='RETRY_AT_VENDOR',physical_at=production.at(day,11,30).isoformat(),reason='AJ genuine paid first attempt',
   lines=[dict(delivery_batch_size_line_id=base.delivery_size_line(cur,sent),qty_attempted_pcs=10)]),base.delivery_version(cur,sent))
 if mixed_rates:
  actors.admin(cur);process=str(uuid.uuid4())
  cur.execute("insert into erp.wash_processes(id,process_code,process_name,is_active) values(%s,%s,'AJ actual eleven wash',true)",(process,'AJ-'+uuid.uuid4().hex[:16]))
  cur.execute("insert into erp.laundry_vendor_rate_versions(vendor_id,wash_process_id,rate_per_pcs,effective_from,notes) values(%s,%s,11,%s,'AJ independently priced second receipt')",(base.VENDOR,process,production.at(day,0)))
  receipt_sources=[]
  for i,process_id in enumerate((base.BASE_PROCESS,process)):
   production.owner(cur)
   receipt=base.action(cur,'POST_RECEIPT',dict(delivery_id=sent,wash_process_id=process_id,
    physical_at=production.at(day,12,i*15).isoformat(),reason='AJ two separately priced physical receipt groups',
    lines=[dict(delivery_batch_size_line_id=base.delivery_size_line(cur,sent),qty_good_received=5,qty_bs_laundry=0,bs_product_id=None)]),base.delivery_version(cur,sent))
   actors.admin(cur)
   receipt_sources.append(cur.execute('select x.id,x.receipt_line_id from erp.laundry_receipt_batch_size_lines x join erp.laundry_receipt_lines l on l.id=x.receipt_line_id where l.receipt_id=%s',(receipt['receipt_id'],)).fetchone())
  (rx,rl),(other_rx,other_rl)=receipt_sources
  final_lines=[dict(final_product_id=product,qty_good_pcs=0,qty_bs_pcs=5,source_laundry_receipt_line_id=str(rl),source_laundry_receipt_batch_size_line_id=str(rx)),
   dict(final_product_id=product,qty_good_pcs=5,qty_bs_pcs=0,source_laundry_receipt_line_id=str(other_rl),source_laundry_receipt_batch_size_line_id=str(other_rx))]
 else:
  received,rx,rl=base.post_receipt(cur,sent,base.BASE_PROCESS,production.at(day,12).isoformat())
  final_lines=[dict(final_product_id=product,qty_good_pcs=initial_good,qty_bs_pcs=10-initial_good,
   source_laundry_receipt_line_id=str(rl),source_laundry_receipt_batch_size_line_id=str(rx))]
 production.owner(cur)
 base.action(cur,'POST_FINAL_SKU',dict(cutting_group_id=f['group'],destination_location_id=base.LOCATION,
  physical_at=production.at(day,13).isoformat(),reason='AJ exact original Good and BS split',good_qty_pcs=initial_good,completion_mode='ALL_READY',
  lines=final_lines),base.group_version(cur,f['group']))
 actors.admin(cur)
 bs,qc=cur.execute('select id,qc_item_id from erp.bs_cases where po_id=%s and status=\'OPEN\'',(po,)).fetchone()
 bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=f['component'],completed_before_bs_qty=10-initial_good)],change_reason='Original component already earned before BS'),version(cur,'bs_cases',bs))
 unit=Decimal(24 if failed_wash else 17)
 original_fg=initial_good*(unit+4 if mixed_rates else unit)
 total_cost=unit*10+(20 if mixed_rates else 0)
 orders=[];observations=[];total_good=initial_good
 for index,route in enumerate((first_route,'LAUNDRY' if first_route=='CONTRACTOR' else 'CONTRACTOR')):
  actors.admin(cur)
  component=cur.execute('select id from erp.bs_case_components where bs_case_id=%s and work_component_id=%s',(bs,f['component'])).fetchone()[0]
  bom=cur.execute('select id from erp.accessory_bom_versions where product_id=%s and is_active',(product,)).fetchone()[0]
  sent_qty=min(4,10-initial_good-index*2)
  payload=dict(rework_number='AJ-'+uuid.uuid4().hex[:20],bs_case_id=bs,destination_type=route,
   contractor_id=production.CONTRACTOR if route=='CONTRACTOR' else None,vendor_id=base.VENDOR if route=='LAUNDRY' else None,
   qty_sent=sent_qty,physical_sent_at=production.at(day,14+index),status='IN_PROGRESS',return_fg_location_id=base.LOCATION,
   accessory_bom_version_id=bom,accessory_bom_item_ids=[],change_reason='AJ four physical pieces, no new original work entitlement',
   components=[dict(bs_case_component_id=component,qty_performed=sent_qty)] if route=='CONTRACTOR' else [])
  made=bs_action(cur,'SAVE_REWORK',payload);order=made['result']['rework_order_id'];orders.append(order)
  before=po_state(cur,po)
  bs_action(cur,'SAVE_REWORK',dict(id=order,action='SAVE',qty_good_returned=1,qty_bs_returned=1,
   return_fg_location_id=base.LOCATION,change_reason='AJ two cumulative returns, two still away'),version(cur,'rework_orders',order))
  assert po_state(cur,po)==before,'Partial changed HPP, stock, WIP, or entitlement'
  payload=dict(rework_order_id=order,qty_good=2,qty_bs=sent_qty-2,completed_at=production.at(day,14+index,30),
   return_fg_location_id=base.LOCATION,change_reason='AJ four returned, two recover to Good')
  key=uuid.uuid4();v=version(cur,'rework_orders',order)
  posted=bs_action(cur,'COMPLETE_REWORK',payload,v,key)
  actors.admin(cur);boundary=actors.boundary(cur)
  assert bs_action(cur,'COMPLETE_REWORK',payload,v,key)==posted
  actors.admin(cur);assert actors.boundary(cur)==boundary
  total_good+=2;state=po_state(cur,po)
  assert Decimal(str(state['fg_qty']))==total_good
  expected_fg=original_fg+(total_good-initial_good)*unit
  assert Decimal(str(state['fg']))==expected_fg
  assert Decimal(str(state['wip']))==total_cost-expected_fg
  lot=posted['result']['good_fg_lot_id']
  assert cur.execute('select qc_item_id,cutting_group_id,po_id from erp.fg_lots where id=%s',(lot,)).fetchone()==(None,uuid.UUID(f['group']),po)
  assert cur.execute('select qc_item_id from erp.bs_cases where id=%s',(bs,)).fetchone()[0]==qc
  observations.append(dict(route=route,order=order,lot=lot,expected_unit_cost=unit,state=state,partial_inert=True,replay_exact=True))
 # Linked inverse of one recovery must preserve the other independent output.
 bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=orders[0],change_reason='AJ linked correction of first recovery'),version(cur,'rework_orders',orders[0]))
 total_good-=2;state=po_state(cur,po)
 expected_fg=original_fg+(total_good-initial_good)*unit
 assert Decimal(str(state['fg_qty']))==total_good and Decimal(str(state['fg']))==expected_fg
 assert Decimal(str(state['wip']))==total_cost-expected_fg
 assert cur.execute("select status from erp.rework_orders where id=%s",(orders[1],)).fetchone()[0]=='COMPLETED'
 assert cur.execute('select count(*) from erp.fg_lots where qc_item_id=%s',(qc,)).fetchone()[0]==int(initial_good>0 and not mixed_rates)
 report=peer.confidence(cur,today)
 assert report['data_confidence']['status']=='READY',report
 return dict(status='PASS',initial_good=initial_good,failed_wash=failed_wash,mixed_receipt_rates=mixed_rates,observations=observations,
  linked_reversal_state=state,original_qc_unique=True,cost_source_preserved=True,report=report)

def import_variant(cur,today,field,value):
 batch,material=gaps.raw_batch(cur,today,'VALID')
 actors.admin(cur)
 cur.execute("update erp.migration_staging_rows set normalized_payload=jsonb_set(normalized_payload,array[%s],%s::jsonb) where batch_id=%s",
  (field,json.dumps(value),batch))
 production.owner(cur)
 result=cur.execute('select * from erp.validate_migration_batch(%s)',(batch,)).fetchall()
 actors.admin(cur)
 rows=cur.execute('select validation_status,validation_errors from erp.migration_staging_rows where batch_id=%s',(batch,)).fetchall()
 assert result==[(1,0,1)] and rows[0][0]=='ERROR' and rows[0][1],(result,rows)
 assert cur.execute('select status from erp.migration_batches where id=%s',(batch,)).fetchone()[0]=='DRAFT'
 # Correcting an unposted input must clear old diagnostics and remain inert.
 cur.execute("update erp.migration_staging_rows set normalized_payload=jsonb_set(normalized_payload,array[%s],%s::jsonb) where batch_id=%s",
  (field,json.dumps('10' if field=='qty' else '1.25'),batch))
 before=production.ledger(cur);production.owner(cur)
 assert cur.execute('select * from erp.validate_migration_batch(%s)',(batch,)).fetchall()==[(1,1,0)]
 assert production.ledger(cur)==before
 return dict(status='PASS',field=field,value=value,errors=rows,corrected_preview_valid=True,ledger_unchanged=True)

def run_cases():
 head,tree=runtime.verify_audit_source()
 result=dict(status='INCOMPLETE',head=head,tree=tree,base_head=runtime.PREDECESSOR_HEAD,
  cases={},production_go=False,independent_acceptance=False)
 with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
  assert len(runtime.verified_successor(cur))==690
  untouched,catalog=actors.boundary(cur),function_catalog(cur)
  usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not usage:cur.execute('grant usage on schema erp to authenticated')
  actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'));base.load_fixture_foundation(cur);actors.admin(cur)
  today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
  day=today-timedelta(days=3);prior.set_open_period(cur,date(2026,8,31))
  specs=[('CROSS:'+n,lambda c,fn=fn:fn(c,day)) for n,fn in original.phase_cases('crossflow')]
  specs += [('WORK:'+n,lambda c,fn=fn:fn(c,day)) for n,fn in work.cases()]
  for z in ('UTC','Asia/Jakarta','Pacific/Kiritimati','America/Los_Angeles'):
   for q in (4,7):
    for closed in (False,True):specs.append((f'INVOICE:{z}:{q}:{closed}',lambda c,z=z,q=q,closed=closed:invoices.case(c,today,z,q,closed)))
  received=today-timedelta(days=1)
  dates=[(gaps.months_before(received,m),received,f'{m}_MONTHS') for m in (1,2,3)]
  dates += [(date(2026,1,31),date(2026,4,30),'JAN31'),(date(2026,2,28),date(2026,5,28),'FEB28'),(date(2026,5,31),date(2026,8,31),'MAY31')]
  for start,end,label in dates:
   for zone in ('UTC','Pacific/Kiritimati'):
    for closed in (False,True):specs.append((f'CALENDAR:{label}:{zone}:{closed}',lambda c,s=start,e=end,z=zone,k=closed:gaps.calendar_case(c,today,s,e,z,k)))
  for v in ('VALID','MISSING_LOCATION','NEGATIVE_QTY','DUPLICATE_SOURCE','NONNUMERIC_QTY','MISSING_COST'):
   specs.append(('IMPORT:'+v,lambda c,v=v:gaps.import_case(c,today,v)))
  for field,value in [('qty','NaN'),('qty','Infinity'),('qty','-Infinity'),('unit_cost','NaN'),('unit_cost','ten'),('unit_cost','-1'),('unit_cost',' ')]:
   specs.append((f'IMPORT_VALUE:{field}:{value}',lambda c,f=field,v=value:import_variant(c,today,f,v)))
  for good in (0,4):
   for route in ('CONTRACTOR','LAUNDRY'):
    for failed in (False,True):specs.append((f'REWORK:{good}:{route}:failed={failed}',lambda c,g=good,r=route,f=failed:rework_case(c,today,g,r,f)))
  for route in ('CONTRACTOR','LAUNDRY'):
   for failed in (False,True):specs.append((f'REWORK:MIXED_RATES:{route}:failed={failed}',lambda c,r=route,f=failed:rework_case(c,today,5,r,f,True)))
  result['planned_case_ids']=[n for n,_ in specs];save('BUSINESS',result)
  for name,fn in specs:
   actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint aj_case')
   try:row=fn(cur)
   except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint aj_case');actors.admin(cur);cur.execute('release savepoint aj_case')
   row['full_boundary_restored']=actors.boundary(cur)==before
   if not row['full_boundary_restored']:row['status']='INCOMPLETE'
   result['cases'][name]=row;save('BUSINESS',result)
   print(json.dumps(dict(case=name,status=row['status'],error=row.get('error'))),flush=True)
  result['catalog_unchanged']=function_catalog(cur)==catalog
  conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
  result['boundary_restored']=actors.boundary(cur)==untouched
  result['schema_usage_restored']=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
  result['auth_users'],result['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
  conn.rollback()
 result['counts']={s:sum(r['status']==s for r in result['cases'].values()) for s in ('PASS','CONTROL_PASS','BUG_PROVEN','GAP_PROVEN','DATE_POLICY_REVIEW_REQUIRED','INCOMPLETE','FAIL')}
 clean=all(result[k] for k in ('catalog_unchanged','boundary_restored','schema_usage_restored')) and result['auth_users']==result['app_users']==0
 if clean and not any(result['counts'][k] for k in ('BUG_PROVEN','GAP_PROVEN','INCOMPLETE','FAIL')):
  result['status']='HOLD' if result['counts']['DATE_POLICY_REVIEW_REQUIRED'] else 'WRITER_PASS'
 result['repair_cases_passed']=all(r['status']=='PASS' for n,r in result['cases'].items() if n.startswith(('REWORK:','IMPORT:','IMPORT_VALUE:')))
 save('BUSINESS',result);return result

def original_schedules(head,tree):
 import cp6_v2620ai_concurrency as schedules
 old=schedules.old
 folder=ROOT/'original-concurrency';folder.mkdir(parents=True,exist_ok=True)
 result=dict(status='INCOMPLETE',head=head,tree=tree,cases=[],production_go=False,independent_acceptance=False)
 try:
  old.matrix.command(['bash','scripts/clone-cp6-disposable-database.sh',old.SOURCE,old.matrix.MAINTENANCE,old.matrix.CLONE,'cp6_rollback',old.matrix.CONTAINER,str(folder/'PHYSICAL_BOUNDARY')],folder/'clone.log')
  with old.connect('aj-original-foundation') as conn,conn.cursor() as cur:
   assert len(runtime.verified_successor(cur))==690
   cur.execute('grant usage on schema erp to authenticated')
   actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'))
   base.load_fixture_foundation(cur);actors.admin(cur)
   day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
   prior.set_open_period(cur,day-timedelta(days=5))
  modes=[(kind+'_'+ending,schedules.run_case) for kind in ('HEADER_POST','POST_HEADER','CHILD_HEADER','HEADER_CHILD') for ending in ('COMMIT','ABORT')]
  modes += [(mode,schedules.ah.run_case) for mode in ('ALLOCATION_MAIN_COMMIT','ALLOCATION_MAIN_ABORT','ALLOCATION_OTHER_COMMIT','ALLOCATION_OTHER_ABORT','RETURN_COMMIT','RETURN_ABORT','SALE_REVERSE_COMMIT','SALE_REVERSE_ABORT')]
  for mode,fn in modes:
   try:record=fn(mode)
   except Exception as exc:record=dict(status='FAIL',mode=mode,error=str(exc),traceback=traceback.format_exc())
   result['cases'].append(record);save('ORIGINAL_CONCURRENCY',result)
   print(json.dumps(dict(mode=mode,status=record['status'],error=record.get('error'))),flush=True)
 finally:old.matrix.legacy.drop_clone()
 with psycopg.connect(old.matrix.MAINTENANCE) as conn:result['clone_removed']=conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]==0
 if result['clone_removed'] and len(result['cases'])==16 and all(c['status']=='PASS' for c in result['cases']):result['status']='PASS'
 save('ORIGINAL_CONCURRENCY',result);return result

def concurrency():
 head,tree=runtime.verify_audit_source()
 with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
  assert len(runtime.verified_successor(cur))==690
 original_result=original_schedules(head,tree)
 result=work.concurrency()
 result.update(tested_runtime_head=head,tested_runtime_tree=tree,runtime_generation='AJ',independent_acceptance=False)
 with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
  assert len(runtime.verified_successor(cur))==690
 result['original_sixteen_status']=original_result['status']
 if original_result['status']!='PASS':result['status']='INCOMPLETE'
 save('CONCURRENCY',result)
 return result

def rollback():
 from importlib.util import spec_from_file_location,module_from_spec
 spec=spec_from_file_location('aj_maintenance_controller',runtime.ROOT/'scripts/cp6_preuse_rollback_maintenance.py')
 maintenance=module_from_spec(spec);spec.loader.exec_module(maintenance)
 before=json.loads((ROOT/'AI_BASELINE.json').read_text())
 controls={
  'FUNCTION':("alter function erp.post_rework_completion(uuid) set work_mem='64MB'",'AJ_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
  'ACL':('grant execute on function erp.post_rework_completion(uuid) to anon','AJ_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
  'OWNER':('alter function erp.post_rework_completion(uuid) owner to supabase_admin','AJ_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
  'EXTRA_TABLE':('create table erp.cp6_aj_unexpected(id integer)','AJ_BOUNDARY_SNAPSHOT_MISMATCH'),
  'MISSING_TABLE':('drop table erp.cp6_v2620ab_rollback_capsule','AJ_BOUNDARY_SNAPSHOT_MISMATCH'),
  'POST_USE':("insert into erp.locations(location_code,location_name,location_type) values('AJ-POST-USE','AJ probe','FG_WAREHOUSE')",'AJ_POST_USE_ROLLBACK_REFUSED'),
  'CAPSULE':(f"update {runtime.CAPSULE} set object_definition=object_definition||E'\\n-- changed'",'AJ_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
  'PLATFORM':(f"update supabase_migrations.schema_migrations set statements=array['wrong'] where name='{runtime.NAME}'",'AJ_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR')}
 atomic={}
 with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta'");assert len(runtime.verified_successor(cur))==690
  for name,(statement,expected) in controls.items():
   boundary,catalog=actors.boundary(cur),function_catalog(cur);cur.execute('savepoint aj_refusal')
   try:
    cur.execute(statement)
    row=original.ah.ag.expected_refusal(cur,lambda:cur.execute(original.ah.ag.sql_body(runtime.ROLLBACK),prepare=False),expected)
    row['status']='PASS'
   except Exception as exc:row=dict(status='FAIL',error=str(exc))
   finally:cur.execute('rollback to savepoint aj_refusal;release savepoint aj_refusal')
   row['boundary_restored']=actors.boundary(cur)==boundary and function_catalog(cur)==catalog
   atomic[name]=row
  conn.rollback()
 save('ROLLBACK_REFUSALS',dict(cases=atomic,production_go=False))
 assert all(x['status']=='PASS' and x['boundary_restored'] for x in atomic.values()),atomic
 operation=maintenance.run_maintenance_rollback(target_name='AJ',target_pgurl=URL,
  maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],report_path=ROOT/'MAINTENANCE.json',drain_timeout=10,natural_grace=0,terminate_after_grace=True)
 with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta'");runtime.verify_predecessor(cur)
  actual=normal(dict(catalog=function_catalog(cur),boundary=snapshot(cur)))
 assert before==actual,'AJ rollback did not restore the exact AI boundary'
 result=dict(status='PASS',functions=len(actual['catalog']),tables=len(actual['boundary']['tables']),full_boundary_exact=True,operation=operation,production_go=False)
 save('EXACT_AI_RESTORE',result);return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=('install','business','concurrency','rollback'),required=True);phase=p.parse_args().phase
 try:
  assert os.environ['PGURL']==URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
  result={'install':install,'business':run_cases,'concurrency':concurrency,'rollback':rollback}[phase]()
 except Exception as exc:
  result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),production_go=False);save(phase.upper()+'_FAILURE',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ('cases','operation','planned_case_ids')},default=str))
 raise SystemExit(0 if result['status'] in ('PASS','WRITER_PASS','PASS_REVIEWED_SCOPE') else 1)
