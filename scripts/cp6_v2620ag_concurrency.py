#!/usr/bin/env python3
"""Eight real two-session schedules: four AF controls and four sale edit/post races."""
from pathlib import Path
from datetime import timedelta
import json,os,threading,traceback,uuid
import psycopg
import cp6_v2620af_concurrency as old
import cp6_v2620ag_runtime as runtime
import cp6_af_independent_review as peer
actors,base,prior=old.actors,old.base,old.prior
ROOT=Path('cp6-proof/writer-ag/concurrency')

def sale_case(mode):
 with old.connect('ag-fixture') as conn,conn.cursor() as cur:
  day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3);f=peer.fixture(cur,day)
 payload=dict(f['payload'],sale_id=f['sale']['sale_id'],reason='AG concurrent official edit',items=[dict(f['payload']['items'][0],product_id=f['products'][1])])
 def edit(cur,unused):
  peer.ordinary(cur);cur.execute('select erp.save_sale_draft_v2(%s::jsonb,%s,%s)',(json.dumps(payload),uuid.uuid4(),f['sale']['row_version']))
 def post(cur,unused):
  peer.ordinary(cur);cur.execute('select erp.post_sale_v2(%s,%s,%s)',(f['sale']['sale_id'],uuid.uuid4(),f['sale']['row_version']))
 response={};thread=None;editing=mode.startswith('EDIT')
 with old.connect('ag-first') as first,old.connect('ag-second') as second:
  try:
   with first.cursor() as cur:(edit if editing else post)(cur,f)
   thread=threading.Thread(target=old.worker,args=(second,post if editing else edit,f,response),daemon=True);thread.start();lock=old.await_lock(second.info.backend_pid)
   if mode.endswith('ABORT'):first.rollback()
   else:first.commit()
   thread.join(30);assert not thread.is_alive(),'AG_SECOND_SESSION_STUCK'
  finally:
   first.rollback()
   if thread is not None and thread.is_alive():second.cancel();thread.join(5)
 if mode.endswith('ABORT'):assert response.get('committed'),response
 else:
  assert not response.get('committed') and response.get('sqlstate')=='P0001',response
  assert ('STALE_VERSION' if editing else 'Only a DRAFT sale') in response.get('error',''),response
 with old.connect('ag-observe') as conn,conn.cursor() as cur:
  state=peer.observe(cur,f['sale']['sale_id']);assert not state['mismatches'] and state['active_stock_qty']==3,state
  if state['header']['status']=='DRAFT':
   r=peer.operation(cur,'select erp.post_sale_v2(%s,%s,%s)',(f['sale']['sale_id'],uuid.uuid4(),state['header']['row_version']));assert not r['refused'],r
  final=peer.observe(cur,f['sale']['sale_id']);assert not final['mismatches'] and final['journal_count']==1
  assert final['items'][0]['product_id']==f['products'][1 if mode in ('EDIT_FIRST','POST_ABORT') else 0]
 return dict(status='PASS',mode=mode,observed_lock=lock,second=response,final=final)

def run():
 head,tree=runtime.verify_audit_source();assert os.environ.get('PGURL')==old.SOURCE and os.environ.get('CP6_AG_CONFIRM')=='postgres'
 ROOT.mkdir(parents=True,exist_ok=True);result=dict(status='INCOMPLETE',head=head,tree=tree,cases=[],production_go=False,http_ui_csv_reachability_proven=False,schema_usage_fixture_grant=True)
 with psycopg.connect(old.SOURCE) as conn,conn.cursor() as cur:assert len(runtime.verified_successor(cur))==690
 try:
  old.matrix.command(['bash','scripts/clone-cp6-disposable-database.sh',old.SOURCE,old.matrix.MAINTENANCE,old.matrix.CLONE,'cp6_rollback',old.matrix.CONTAINER,str(ROOT/'PHYSICAL_BOUNDARY')],ROOT/'clone.log')
  with old.connect('ag-foundation') as conn,conn.cursor() as cur:
   cur.execute('grant usage on schema erp to authenticated');cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),));base.load_fixture_foundation(cur);actors.admin(cur)
   day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3);prior.set_open_period(cur,day-timedelta(days=4))
  cases=[('AF_'+m,lambda m=m:old.run_case('AF',m)) for m in ('POST_FIRST','POST_ABORT','CHILD_FIRST','DOUBLE_POST')]+[('AG_'+m,lambda m=m:sale_case(m)) for m in ('EDIT_FIRST','EDIT_ABORT','POST_FIRST','POST_ABORT')]
  for name,fn in cases:
   try:r=fn()
   except Exception as exc:r=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc())
   r['name']=name;result['cases'].append(r);print(json.dumps(dict(name=name,status=r['status'],error=r.get('error'))),flush=True)
   (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
 finally:old.matrix.legacy.drop_clone()
 with psycopg.connect(old.matrix.MAINTENANCE) as conn:result['clone_removed']=conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]==0
 if result['clone_removed'] and len(result['cases'])==8 and all(r['status']=='PASS' for r in result['cases']):result['status']='PASS'
 (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2,default=str)+'\n');return result

if __name__=='__main__':
 try:r=run()
 except Exception as exc:r=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc());ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items() if k!='cases'}));raise SystemExit(0 if r['status']=='PASS' else 1)
