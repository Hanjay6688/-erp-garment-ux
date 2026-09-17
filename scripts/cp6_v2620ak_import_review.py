#!/usr/bin/env python3
"""Ordinary native import transactions; writer regression, not CSV transport."""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import argparse,json,os,sys,traceback,uuid
sys.path.insert(0,str(Path.cwd()/'scripts'))
import psycopg
import cp6_v2620ak_runtime as runtime
import cp6_v2620aj_runtime as predecessor
import cp6_v2620ak_review as setup
import cp6_final_independent_acceptance as residual
from cp6_v2620n_rollback_guards import function_catalog

actors,base,production,gaps=setup.actors,setup.base,setup.production,setup.gaps
ROOT=Path('cp6-proof/writer-ak')

def owner(cur): production.owner(cur)
def stage(cur,batch,entity,n,payload):
 owner(cur)
 return cur.execute('select erp.stage_migration_row(%s,%s,%s,%s,%s::jsonb,%s::jsonb)',
  (batch,entity,n,entity+'-'+str(n),json.dumps(payload),json.dumps(payload))).fetchone()[0]

def validate(cur,batch):
 owner(cur);value=cur.execute('select * from erp.validate_migration_batch(%s)',(batch,)).fetchone()
 actors.admin(cur);return value

def refused(cur,operation):
 actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint ak_reject');error=None
 try: operation()
 except psycopg.Error as exc:error=dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary)
 finally:cur.execute('rollback to savepoint ak_reject');actors.admin(cur);cur.execute('release savepoint ak_reject')
 assert error and actors.boundary(cur)==before,(error,'non-atomic refusal')
 return error

def opening(cur,batch):
 owner(cur);return cur.execute('select erp.prepare_migration_opening_balance(%s,null)',(batch,)).fetchone()[0]

def post(cur,ident):
 owner(cur);cur.execute('select erp.post_opening_balance(%s)',(ident,));actors.admin(cur)

def batch_new(cur,today):
 owner(cur);return cur.execute('select erp.create_migration_batch(%s,%s,null,null)',
  ('AK-'+uuid.uuid4().hex,gaps.production.at(today-timedelta(days=1),0))).fetchone()[0]

def unknown_opening(cur,today,field,old):
 batch,material=gaps.raw_batch(cur,today,'VALID');actors.admin(cur)
 good=cur.execute('select normalized_payload from erp.migration_staging_rows where batch_id=%s',(batch,)).fetchone()[0]
 bad=dict(good);bad[field]='MISSING-'+uuid.uuid4().hex
 stage(cur,batch,'OPENING_BALANCE_ITEM',2,bad);actors.admin(cur);ledger=production.ledger(cur)
 counts=validate(cur,batch)
 details=cur.execute('select source_row_no,validation_status,validation_errors from erp.migration_staging_rows where batch_id=%s order by source_row_no',(batch,)).fetchall()
 assert production.ledger(cur)==ledger
 rejected=refused(cur,lambda:opening(cur,batch))
 if not old:assert counts==(2,1,1) and details[1][1]=='ERROR' and details[1][2],(counts,details)
 stage(cur,batch,'OPENING_BALANCE_ITEM',2,good)
 assert validate(cur,batch)==(2,2,0)
 ident=opening(cur,batch);actors.admin(cur);prepared=actors.boundary(cur)
 assert opening(cur,batch)==ident;actors.admin(cur);assert actors.boundary(cur)==prepared
 post(cur,ident);owner(cur);cur.execute('select erp.finalize_migration_batch(%s)',(batch,));actors.admin(cur)
 values=cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s',(material,)).fetchone()
 assert values==(20,Decimal('25.00')),values
 return dict(status='GAP_PROVEN' if old and counts==(2,2,0) else 'PASS',field=field,preview=counts,
  rows=details,refusal=rejected,posted=values,preview_ledger_inert=True,prepare_replay_exact=True)

def master_reference(cur,today,entity,field):
 batch=batch_new(cur,today);actors.admin(cur);tag='AK-'+uuid.uuid4().hex[:14]
 product=base.create_product(cur,tag)
 values=cur.execute('select b.brand_code,m.model_code,s.size_code,p.color_name from erp.products p join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes s on s.id=p.size_id where p.id=%s',(product,)).fetchone()
 if entity=='PRODUCT':payload=dict(sku=tag+'N',product_name='Synthetic staged product',brand_code=values[0],model_code=values[1],size_code=values[2],color_name=values[3])
 elif entity=='MATERIAL':payload=dict(material_sku=tag,material_name='Synthetic staged material',material_type='OTHER',unit_code='PCS')
 elif entity=='OPEN_PO':payload=dict(po_number=tag,model_code=values[1],status='DRAFT',current_stage='CUTTING')
 else:raise AssertionError(entity)
 payload[field]='MISSING-'+uuid.uuid4().hex
 stage(cur,batch,entity,1,payload);actors.admin(cur);ledger=production.ledger(cur)
 counts=validate(cur,batch);assert counts==(1,0,1),counts
 errors=cur.execute('select validation_errors from erp.migration_staging_rows where batch_id=%s',(batch,)).fetchone()[0]
 assert any(field in e for e in errors),errors
 assert production.ledger(cur)==ledger
 return dict(status='PASS',entity=entity,field=field,preview=counts,errors=errors)

def draft_edit(cur,today,old=False):
 batch,material=gaps.raw_batch(cur,today,'VALID');assert validate(cur,batch)==(1,1,0)
 actors.admin(cur);payload=cur.execute('select normalized_payload from erp.migration_staging_rows where batch_id=%s',(batch,)).fetchone()[0]
 ident=opening(cur,batch);actors.admin(cur);ledger=production.ledger(cur)
 payload['qty']='20';stage(cur,batch,'OPENING_BALANCE_ITEM',1,payload)
 if not old:refused(cur,lambda:post(cur,ident))
 assert validate(cur,batch)==(1,1,0)
 if not old:refused(cur,lambda:post(cur,ident))
 assert opening(cur,batch)==ident;actors.admin(cur)
 assert production.ledger(cur)==ledger
 prepared=actors.boundary(cur);assert opening(cur,batch)==ident;actors.admin(cur);assert actors.boundary(cur)==prepared
 post(cur,ident)
 values=cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s',(material,)).fetchone()
 if old:return dict(status='BUG_PROVEN' if values!=(20,Decimal('25')) else 'PASS',latest_draft_qty=20,posted=values)
 assert values==(20,Decimal('25')),values
 refuse_stage=refused(cur,lambda:stage(cur,batch,'OPENING_BALANCE_ITEM',1,payload))
 refuse_validate=refused(cur,lambda:validate(cur,batch))
 owner(cur);cur.execute('select erp.finalize_migration_batch(%s)',(batch,));actors.admin(cur);posted=actors.boundary(cur)
 owner(cur);cur.execute('select erp.finalize_migration_batch(%s)',(batch,));actors.admin(cur);assert actors.boundary(cur)==posted
 refused(cur,lambda:validate(cur,batch))
 return dict(status='PASS',latest_draft_qty=20,posted=values,same_header=True,prepare_replay_exact=True,
  posted_stage_refusal=refuse_stage,posted_validation_refusal=refuse_validate,finalize_replay_exact=True)

def staged_material(cur,today,invalid=False,duplicate=False):
 batch=batch_new(cur,today);tag='AK-'+uuid.uuid4().hex[:14];actors.admin(cur)
 location='RAW-'+tag
 cur.execute("insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,'Synthetic staged material warehouse','RAW_MATERIAL_WAREHOUSE',true)",(location,))
 parent=dict(material_sku=tag,material_name='Synthetic new master',material_type='OTHER',unit_code='PCS')
 child=dict(balance_type='MATERIAL',material_sku=tag,location_code=location,qty='4',unit_cost='3.25')
 # Deliberately stage consumer first; import order must not become an oracle.
 stage(cur,batch,'OPENING_BALANCE_ITEM',1,child)
 stage(cur,batch,'MATERIAL',9,{k:v for k,v in parent.items() if not invalid or k!='material_name'})
 if duplicate:stage(cur,batch,'MATERIAL',10,parent)
 actors.admin(cur);ledger=production.ledger(cur);counts=validate(cur,batch)
 if duplicate:
  assert counts==(3,0,3),counts
  return dict(status='PASS',preview=counts,duplicate_business_key_rejected=True)
 if invalid:
  assert counts==(2,0,2),counts
  stage(cur,batch,'MATERIAL',9,parent)
  assert validate(cur,batch)==(2,2,0)
 else:assert counts==(2,2,0),counts
 assert production.ledger(cur)==ledger
 owner(cur);assert cur.execute('select erp.apply_migration_master_rows(%s)',(batch,)).fetchone()[0]==1
 assert cur.execute('select erp.apply_migration_master_rows(%s)',(batch,)).fetchone()[0]==0
 ident=opening(cur,batch)
 child['qty']='5';stage(cur,batch,'OPENING_BALANCE_ITEM',1,child)
 assert validate(cur,batch)==(2,2,0)
 assert opening(cur,batch)==ident;post(cur,ident)
 qty,value=cur.execute('select sum(sm.qty_signed),sum(sm.qty_signed*sm.unit_cost_snapshot) from erp.material_stock_movements sm join erp.materials m on m.id=sm.material_id where m.material_sku=%s',(tag,)).fetchone()
 assert (qty,value)==(5,Decimal('16.25'))
 return dict(status='PASS',initial_preview=counts,posted_qty=qty,posted_value=value,
  staged_parent_first_not_required=True,edit_after_prepare_allowed=True,master_replay_no_duplicate=True)

def staged_product(cur,today):
 batch=batch_new(cur,today);tag='AK-'+uuid.uuid4().hex[:14];actors.admin(cur)
 location=cur.execute("select location_code from erp.locations where is_active and location_type='FG_WAREHOUSE' order by id limit 1").fetchone()[0]
 product=dict(sku=tag,product_name='Synthetic new FG',brand_code=tag,model_code=tag,size_code=tag,color_name='NAVY')
 payload=dict(balance_type='FINISHED_GOODS',product_sku=tag,brand_code=tag,model_code=tag,size_code=tag,
  color_name='NAVY',qty='2',unit_cost='1.25',location_code=location)
 for entity,data in [('OPENING_BALANCE_ITEM',payload),('PRODUCT',product),('MODEL',dict(model_code=tag,model_name='Synthetic model')),
   ('BRAND',dict(brand_code=tag,brand_name='Synthetic brand')),('SIZE',dict(size_code=tag))]:stage(cur,batch,entity,1,data)
 actors.admin(cur);ledger=production.ledger(cur);counts=validate(cur,batch)
 assert counts==(5,5,0),cur.execute('select entity_type,validation_errors from erp.migration_staging_rows where batch_id=%s',(batch,)).fetchall()
 assert production.ledger(cur)==ledger
 owner(cur);assert cur.execute('select erp.apply_migration_master_rows(%s)',(batch,)).fetchone()[0]==4
 ident=opening(cur,batch);post(cur,ident)
 values=cur.execute('select sum(m.qty_signed),sum(m.qty_signed*m.unit_hpp_snapshot) from erp.fg_stock_movements m join erp.products p on p.id=m.product_id where p.sku=%s',(tag,)).fetchone()
 assert values==(2,Decimal('2.50')),values
 return dict(status='PASS',preview=counts,posted=values,exact_new_staged_identity=True)

def run(old=False):
 head,tree=runtime.verify_audit_source();expected=predecessor if old else runtime
 report=dict(status='INCOMPLETE',writer_head=head,writer_tree=tree,runtime_generation='AJ' if old else 'AK',
  cases={},production_go=False,independent_acceptance=False,csv_transport_tested=False)
 ROOT.mkdir(parents=True,exist_ok=True);path=ROOT/('ORIGINAL_IMPORT.json' if old else 'IMPORT.json')
 def save():path.write_text(json.dumps(report,indent=2,default=str)+'\n')
 with psycopg.connect(setup.ADMIN) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
  assert len(expected.verified_successor(cur))==690
  initial,catalog=actors.boundary(cur),function_catalog(cur)
  usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  report['temporary_schema_usage_grant']=not usage
  if not usage:cur.execute('grant usage on schema erp to authenticated')
  actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'));base.load_fixture_foundation(cur);actors.admin(cur)
  today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
  specs=[('OPENING_REF:'+f,lambda c,f=f:unknown_opening(c,today,f,old)) for f in
   ('material_sku','location_code','model_code','contractor_code','customer_code','supplier_code','vendor_code','cash_account_code','product_sku')]
  specs.append(('EDIT_PREPARED_DRAFT',lambda c:draft_edit(c,today,old)))
  if not old:
   specs += [('MASTER_REF:'+entity+':'+field,lambda c,e=entity,f=field:master_reference(c,today,e,f)) for entity,fields in
    [('PRODUCT',('model_code','brand_code','size_code')),('MATERIAL',('unit_code','accessory_category_code')),('OPEN_PO',('model_code','contractor_code'))] for field in fields]
   specs += [('STAGED_MATERIAL',lambda c:staged_material(c,today)),('STAGED_INVALID_PARENT',lambda c:staged_material(c,today,True)),
    ('DUPLICATE_MASTER',lambda c:staged_material(c,today,duplicate=True)),('STAGED_PRODUCT',lambda c:staged_product(c,today))]
   specs += [('RECOVERED_SALE:'+route+':'+str(failed),lambda c,r=route,f=failed:residual.recovered_sale(c,today,r,f))
    for route in ('CONTRACTOR','LAUNDRY') for failed in (False,True)]
  report['planned_case_ids']=[n for n,_ in specs];save()
  for name,fn in specs:
   actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint ak_case')
   try:row=fn(cur)
   except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint ak_case');actors.admin(cur);cur.execute('release savepoint ak_case')
   row['boundary_restored']=actors.boundary(cur)==before
   if not row['boundary_restored']:row['status']='INCOMPLETE'
   report['cases'][name]=row;save();print(json.dumps(dict(case=name,status=row['status'],error=row.get('error'))),flush=True)
  report['catalog_unchanged']=function_catalog(cur)==catalog
  conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
  report['boundary_restored']=actors.boundary(cur)==initial
  report['schema_usage_restored']=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
  report['auth_users'],report['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
  conn.rollback()
 report['counts']={s:sum(r['status']==s for r in report['cases'].values()) for s in ('PASS','GAP_PROVEN','BUG_PROVEN','INCOMPLETE')}
 clean=all(report[k] for k in ('catalog_unchanged','boundary_restored','schema_usage_restored')) and report['auth_users']==report['app_users']==0
 if clean and not report['counts']['INCOMPLETE'] and (old or all(r['status']=='PASS' for r in report['cases'].values())):
  report['status']='PREDECESSOR_PROBES_COMPLETE' if old else 'WRITER_PASS'
 save();return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--original',action='store_true');args=p.parse_args()
 assert os.environ['PGURL']==setup.URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
 r=run(args.original);print(json.dumps({k:v for k,v in r.items() if k not in('cases','planned_case_ids')}))
 raise SystemExit(0 if r['status'] in('PREDECESSOR_PROBES_COMPLETE','WRITER_PASS') else 1)
