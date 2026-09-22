#!/usr/bin/env python3
"""Proposed AP RPCs on the exact disposable AN runtime, fully rolled back.
This is a writer trial, never production or independent acceptance.
"""
from pathlib import Path
from datetime import timedelta
import hashlib,json,os,subprocess,traceback,uuid
import psycopg
import cp6_v2620an_runtime as runtime
import cp6_v2620al_import_review as inherited
from cp6_v2620ap_definitions import FUNCTIONS,PREDECESSOR
from cp6_v2620n_rollback_guards import function_catalog

ROOT=Path('cp6-proof/initial-import');ROOT.mkdir(parents=True,exist_ok=True)
actors,base,production=inherited.actors,inherited.base,inherited.production
URL='postgresql://supabase_admin:postgres@127.0.0.1:54322/postgres'
report=dict(status='INCOMPLETE',head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cases={},production_go=False,independent_acceptance=False,migration_installed=False)
def save(): (ROOT/'NATIVE_TRIAL.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
def admin(cur):actors.admin(cur)
def call(cur,action,payload,key=None):
 production.owner(cur)
 value=cur.execute('select public.erp_save_initial_import_action_v1(%s,%s::jsonb,%s)',(action,json.dumps(payload,default=str),key or uuid.uuid4())).fetchone()[0]
 admin(cur);return value

def read(cur,batch=None):
 production.owner(cur);value=cur.execute('select public.erp_get_initial_import_workspace_v1(%s)',(batch,)).fetchone()[0];admin(cur);return value

def invoke(cur,action,batch,**extra):
 return call(cur,action,dict(batch_id=batch,expected_revision=read(cur,batch)['batch']['revision'],**extra))
def upload(cur,batch,entity,rows):return invoke(cur,'SAVE_FILE',batch,entity=entity,filename=entity+'.csv',rows=[dict(source_row_no=n+2,payload=r) for n,r in enumerate(rows)])

def valid(cur,today):
 batch=call(cur,'CREATE',dict(batch_code='AP-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=1))))['batch_id']
 code='AP-'+uuid.uuid4().hex[:14]
 upload(cur,batch,'CUSTOMER',[dict(customer_code=code,customer_name='AP ordinary owner')])
 rows=[dict(balance_type='CUSTOMER_RECEIVABLE',customer_code=code,amount='14.25',control_key='AR')]
 upload(cur,batch,'OPENING_BALANCE_ITEM',rows)
 upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='14.25')])
 return batch,code,rows

def lifecycle(cur,today):
 before=production.ledger(cur);batch,code,rows=valid(cur,today)
 assert production.ledger(cur)==before
 assert invoke(cur,'VALIDATE',batch)['error_rows']==0
 old=read(cur,batch)['batch']['revision']
 rows[0]['amount']='17.25';upload(cur,batch,'OPENING_BALANCE_ITEM',rows)
 assert invoke(cur,'FINALIZE',batch)['status']=='DRAFT'
 assert production.ledger(cur)==before
 assert any('amount:' in e for r in read(cur,batch)['batch']['rows'] for e in r['errors'])
 inherited.refused(cur,lambda:call(cur,'FINALIZE',dict(batch_id=batch,expected_revision=old)))
 upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='17.25')])
 assert invoke(cur,'VALIDATE',batch)['error_rows']==0
 payload=dict(batch_id=batch,expected_revision=read(cur,batch)['batch']['revision']);key=uuid.uuid4()
 result=call(cur,'FINALIZE',payload,key);assert result['status']=='POSTED',result
 boundary=actors.boundary(cur);assert call(cur,'FINALIZE',payload,key)==result and actors.boundary(cur)==boundary
 rows=cur.execute("select s.original_amount from erp.opening_subledger_balances s join erp.opening_balance_items i on i.id=s.opening_item_id join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s",(batch,)).fetchall()
 assert rows==[(inherited.Decimal('17.25'),)],rows
 assert cur.execute('select count(*) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s',(batch,)).fetchone()[0]==1
 inherited.refused(cur,lambda:invoke(cur,'SAVE_FILE',batch,entity='CUSTOMER',rows=[]))
 return dict(status='PASS',draft_ledger_inert=True,latest_value='17.25',control_not_posted=True,replay_identical=True)

def numeric_refusal(cur,today):
 batch,_,_=valid(cur,today)
 return dict(status='PASS',refusal=inherited.refused(cur,lambda:upload(cur,batch,'OPENING_BALANCE_ITEM',[dict(balance_type='CASH_BANK',amount='1.001',control_key='CASH')])) )

def control_refusal(cur,today,kind):
 batch,_,rows=valid(cur,today)
 if kind=='MISSING':upload(cur,batch,'OPENING_CONTROL',[])
 else:upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='14.25')]*2)
 before=production.ledger(cur);value=invoke(cur,'FINALIZE',batch)
 assert value['status']=='DRAFT' and value['error_rows']>0 and production.ledger(cur)==before,value
 return dict(status='PASS',errors=value['error_rows'],ledger_unchanged=True)

def authorization(cur,today):
 batch,_,_=valid(cur,today)
 admin(cur);cur.execute("update erp.app_users set is_active=false where auth_user_id=%s",(base.OPERATOR_AUTH,))
 refused=inherited.refused(cur,lambda:read(cur,batch))
 return dict(status='PASS',revoked_owner_refused=refused)

save()
try:
 with psycopg.connect(URL) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='120s';set local lock_timeout='8s'")
  assert len(runtime.verified_successor(cur))==692
  baseline=actors.boundary(cur);catalog=function_catalog(cur)
  # Persist schema diagnostics from genuine disposable Supabase, no user data.
  (ROOT/'TABLE_COLUMNS.json').write_text(json.dumps(cur.execute("select table_name,column_name,data_type,column_default,is_nullable from information_schema.columns where table_schema='erp' order by table_name,ordinal_position").fetchall(),indent=2,default=str)+'\n')
  for identity,definition,acl,owner in PREDECESSOR:
   found=cur.execute('select pg_get_functiondef(p.oid),p.proacl::text,pg_get_userbyid(p.proowner) from pg_proc p where p.oid=to_regprocedure(%s)',(identity,)).fetchone()
   assert found==(definition,acl,owner),identity
  cur.execute('set local role postgres')
  for identity,definition in FUNCTIONS.items():
   cur.execute(definition,prepare=False)
   if identity not in {r[0] for r in PREDECESSOR}:
    cur.execute(f'revoke all on function {identity} from public,anon,authenticated,service_role')
    if identity.startswith('public.'):cur.execute(f'grant execute on function {identity} to authenticated,service_role')
  admin(cur)
  installed=function_catalog(cur)
  # The inherited seed includes historical native calls: temporary USAGE is
  # fixture-only and rolled back. Neither public RPC requires this grant.
  cur.execute('grant usage on schema erp to authenticated')
  actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'));base.load_fixture_foundation(cur);admin(cur)
  cur.execute('revoke usage on schema erp from authenticated')
  today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
  cases=[('LATEST_DRAFT_TOTALS_REPLAY',lambda:lifecycle(cur,today)),('EXCESS_PRECISION',lambda:numeric_refusal(cur,today)),('MISSING_CONTROL',lambda:control_refusal(cur,today,'MISSING')),('DUPLICATE_CONTROL',lambda:control_refusal(cur,today,'DUPLICATE')),('REVOKED_OWNER',lambda:authorization(cur,today))]
  for name,fn in cases:
   admin(cur);before=actors.boundary(cur);cur.execute('savepoint proposed_case')
   try:result=fn()
   except Exception as exc:result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint proposed_case');admin(cur);cur.execute('release savepoint proposed_case')
   result['boundary_restored']=actors.boundary(cur)==before
   if not result['boundary_restored']:result['status']='INCOMPLETE'
   report['cases'][name]=result;save();print(json.dumps(dict(case=name,**result),default=str),flush=True)
  assert function_catalog(cur)==installed
  conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
  assert actors.boundary(cur)==baseline and function_catalog(cur)==catalog
  report['complete_boundary_restored']=True
  report['status']='WRITER_TRIAL_PASS' if all(r['status']=='PASS' for r in report['cases'].values()) else 'INCOMPLETE'
except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
save();print(json.dumps({k:v for k,v in report.items() if k!='cases'},default=str))
raise SystemExit(0 if report['status']=='WRITER_TRIAL_PASS' else 1)
