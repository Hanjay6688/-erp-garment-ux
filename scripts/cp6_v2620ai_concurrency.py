#!/usr/bin/env python3
"""Eight work-source schedules plus eight unchanged AH return schedules."""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import json,os,threading,traceback
import psycopg
import cp6_v2620af_concurrency as old
import cp6_v2620ah_concurrency as ah
import cp6_v2620ai_runtime as runtime
import cp6_v2620ai_family as family
actors,base,prior,peer,original=family.actors,family.base,family.prior,family.peer,family.original
ROOT=Path('cp6-proof/writer-ai/concurrency')

def fixture():
 with old.connect('ai-work-fixture') as conn,conn.cursor() as cur:
  day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
  return {'first':original.work_draft(cur,day,Decimal('1.25')),'other':original.work_draft(cur,day,Decimal('2.50'))}

def post(cur,f):
 peer.ordinary(cur);cur.execute('select erp.post_work_completion(%s)',(f['first']['completion'],))

def header(cur,f):
 peer.ordinary(cur);cur.execute('update erp.work_completion_events set po_id=%s,cutting_group_id=%s where id=%s',(f['other']['po'],f['other']['group'],f['first']['completion']))

def child(cur,f):
 peer.ordinary(cur);cur.execute('update erp.work_completion_lines set qty_completed=9,qty_payable=9 where completion_id=%s',(f['first']['completion'],))

def run_case(mode):
 f=fixture();response={};thread=None;abort=mode.endswith('ABORT');kind=mode.rsplit('_',1)[0]
 first_op,second_op={'HEADER_POST':(header,post),'POST_HEADER':(post,header),'CHILD_HEADER':(child,header),'HEADER_CHILD':(header,child)}[kind]
 with old.connect('ai-first') as first,old.connect('ai-second') as second:
  try:
   with first.cursor() as cur:first_op(cur,f)
   thread=threading.Thread(target=old.worker,args=(second,second_op,f,response),daemon=True);thread.start()
   lock=old.await_lock(second.info.backend_pid);assert first.info.backend_pid in lock[2],lock
   first.rollback() if abort else first.commit();thread.join(30);assert not thread.is_alive(),'AI_SECOND_SESSION_STUCK'
  finally:
   first.rollback()
   if thread is not None and thread.is_alive():second.cancel();thread.join(5)
 expected_commit=abort or kind=='CHILD_HEADER'
 assert bool(response.get('committed'))==expected_commit,response
 if not expected_commit:
  assert response.get('sqlstate')=='P0001',response
  if kind=='HEADER_POST':assert 'AI_WORK_SOURCE_SNAPSHOT_MISMATCH' in response['error'],response
  if kind=='HEADER_CHILD':assert 'Work component snapshot does not match' in response['error'],response
 with old.connect('ai-observe') as conn,conn.cursor() as cur:
  state=original.work_state(cur,f['first']['completion'])
  posted=(kind=='HEADER_POST' and abort) or (kind=='POST_HEADER' and not abort)
  rebound=(kind=='HEADER_POST' and not abort) or (kind=='POST_HEADER' and abort) or kind=='CHILD_HEADER' or (kind=='HEADER_CHILD' and not abort)
  assert state['header']['status']==('POSTED' if posted else 'DRAFT'),state
  assert state['header']['po_id']==str(f['other']['po'] if rebound else f['first']['po']),state
  if posted:
   assert len(state['journal'])==1 and all(l['snapshot_po']==state['header']['po_id'] for l in state['lines']),state
  elif rebound:
   refusal=original.returns.refusal(cur,'select erp.post_work_completion(%s)',(f['first']['completion'],),'AI_WORK_SOURCE_SNAPSHOT_MISMATCH')
  else:
   post(cur,f)
   resumed=original.work_state(cur,f['first']['completion'])
   assert resumed['header']['status']=='POSTED' and all(l['snapshot_po']==resumed['header']['po_id'] for l in resumed['lines']),resumed
  actors.admin(cur);day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")
  report=family.report(cur,day)
 return dict(status='PASS',mode=mode,observed_lock=lock,second=response,state=state,report=report,
             fixture_admin_changed_posted_data=False,http_ui_csv_reachability_proven=False)

def run():
 head,tree=runtime.verify_audit_source();assert os.environ.get('PGURL')==old.SOURCE and os.environ.get('CP6_AI_CONFIRM')=='postgres'
 ROOT.mkdir(parents=True,exist_ok=True)
 result=dict(status='INCOMPLETE',head=head,tree=tree,cases=[],production_go=False,schema_usage_fixture_grant=True,http_ui_csv_reachability_proven=False)
 with psycopg.connect(old.SOURCE) as conn,conn.cursor() as cur:assert len(runtime.verified_successor(cur))==690
 try:
  old.matrix.command(['bash','scripts/clone-cp6-disposable-database.sh',old.SOURCE,old.matrix.MAINTENANCE,old.matrix.CLONE,'cp6_rollback',old.matrix.CONTAINER,str(ROOT/'PHYSICAL_BOUNDARY')],ROOT/'clone.log')
  with old.connect('ai-foundation') as conn,conn.cursor() as cur:
   cur.execute('grant usage on schema erp to authenticated')
   cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),))
   base.load_fixture_foundation(cur);actors.admin(cur)
   day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3);prior.set_open_period(cur,day-timedelta(days=5))
  modes=[(kind+'_'+ending,run_case) for kind in ('HEADER_POST','POST_HEADER','CHILD_HEADER','HEADER_CHILD') for ending in ('COMMIT','ABORT')]
  modes += [(mode,ah.run_case) for mode in ('ALLOCATION_MAIN_COMMIT','ALLOCATION_MAIN_ABORT','ALLOCATION_OTHER_COMMIT','ALLOCATION_OTHER_ABORT','RETURN_COMMIT','RETURN_ABORT','SALE_REVERSE_COMMIT','SALE_REVERSE_ABORT')]
  for mode,fn in modes:
   try:record=fn(mode)
   except Exception as exc:record=dict(status='FAIL',mode=mode,error=str(exc),traceback=traceback.format_exc())
   result['cases'].append(record);print(json.dumps(dict(mode=mode,status=record['status'],error=record.get('error'))),flush=True)
   (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
 finally:old.matrix.legacy.drop_clone()
 with psycopg.connect(old.matrix.MAINTENANCE) as conn:result['clone_removed']=conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]==0
 if result['clone_removed'] and len(result['cases'])==16 and all(c['status']=='PASS' for c in result['cases']):result['status']='PASS'
 (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2,default=str)+'\n');return result

if __name__=='__main__':
 try:result=run()
 except Exception as exc:
  result=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc(),production_go=False);ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='cases'}));raise SystemExit(0 if result['status']=='PASS' else 1)
