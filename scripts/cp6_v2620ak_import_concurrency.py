#!/usr/bin/env python3
"""Four real two-session draft-edit/post schedules, with observed blocking."""
import json,os,threading,time,traceback
from pathlib import Path
import psycopg
import cp6_v2620ak_import_review as review
import cp6_v2620h_maintenance_rollback_matrix as matrix

ROOT=Path('cp6-proof/writer-ak/import-concurrency')

def run():
 head,tree=review.runtime.verify_audit_source()
 assert os.environ['PGURL']==matrix.SOURCE and os.environ['CP6_ROLLBACK_RACE_PGURL']==matrix.CLONE
 report=dict(status='INCOMPLETE',writer_head=head,writer_tree=tree,cases={},production_go=False)
 ROOT.mkdir(parents=True,exist_ok=True)
 def save(): (ROOT/'manifest.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
 try:
  matrix.command(['bash','scripts/clone-cp6-disposable-database.sh',matrix.SOURCE,matrix.MAINTENANCE,
   matrix.CLONE,'cp6_rollback',matrix.CONTAINER,str(ROOT/'PHYSICAL_BOUNDARY')],ROOT/'clone.log')
  with psycopg.connect(matrix.CLONE) as conn,conn.cursor() as cur:
   assert len(review.runtime.verified_successor(cur))==690
   cur.execute('grant usage on schema erp to authenticated')
   review.actors.actors.claims(cur,dict(sub=review.base.OPERATOR_AUTH,role='authenticated'))
   review.base.load_fixture_foundation(cur);review.actors.admin(cur)
  for direction in ('EDIT_POST','POST_EDIT'):
   for commit in (True,False):
    name=direction+('_COMMIT' if commit else '_ABORT');first=second=None;thread=None
    try:
     with psycopg.connect(matrix.CLONE) as seed,seed.cursor() as cur:
      cur.execute("set local timezone='Asia/Jakarta'")
      day=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
      batch,material=review.gaps.raw_batch(cur,day,'VALID');assert review.validate(cur,batch)==(1,1,0)
      ident=review.opening(cur,batch);review.actors.admin(cur)
      payload=cur.execute('select normalized_payload from erp.migration_staging_rows where batch_id=%s',(batch,)).fetchone()[0]
      payload['qty']='20'
     first=psycopg.connect(matrix.CLONE,application_name='ak-import-first')
     second=psycopg.connect(matrix.CLONE,application_name='ak-import-second')
     for conn in (first,second):conn.execute("set statement_timeout='15s';set lock_timeout='12s'");conn.commit()
     def edit(cur):review.stage(cur,batch,'OPENING_BALANCE_ITEM',1,payload)
     def post(cur):review.post(cur,ident)
     fn1,fn2=(edit,post) if direction=='EDIT_POST' else (post,edit)
     fn1(first.cursor());result={}
     def worker():
      try:fn2(second.cursor());second.commit();result.update(success=True)
      except Exception as exc:
       second.rollback();result.update(success=False,sqlstate=getattr(exc,'sqlstate',None),error=str(exc))
     thread=threading.Thread(target=worker,daemon=True);thread.start()
     blocker=first.info.backend_pid;waiter=second.info.backend_pid;blocked=False
     with psycopg.connect(matrix.CLONE,autocommit=True) as observer:
      deadline=time.monotonic()+6
      while time.monotonic()<deadline and thread.is_alive():
       blocked=observer.execute('select %s=any(pg_blocking_pids(%s))',(blocker,waiter)).fetchone()[0]
       if blocked:break
       time.sleep(.03)
     assert blocked,'Second session never observed waiting on first'
     first.commit() if commit else first.rollback()
     thread.join(18);assert not thread.is_alive(),'Worker remained active'
     assert result['success']==(not commit),result
     if commit:assert result['sqlstate']=='P0001',result
     with psycopg.connect(matrix.CLONE) as observer:
      qty=observer.execute('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s',(material,)).fetchone()[0]
      expected=10 if (direction=='POST_EDIT' and commit) or (direction=='EDIT_POST' and not commit) else 0
      assert qty==expected,(qty,expected)
     report['cases'][name]=dict(status='PASS',blocking_observed=blocked,first_committed=commit,second=result,stock_qty=qty)
    except Exception as exc:report['cases'][name]=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
     for conn in (first,second):
      if conn is not None:
       if thread and thread.is_alive():conn.cancel()
       conn.close()
     if thread:thread.join(2)
     save()
 finally:matrix.legacy.drop_clone()
 with psycopg.connect(matrix.MAINTENANCE) as conn:
  report['clone_removed']=conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]==0
 if report['clone_removed'] and len(report['cases'])==4 and all(r['status']=='PASS' for r in report['cases'].values()):report['status']='WRITER_PASS'
 save();return report

if __name__=='__main__':
 r=run();print(json.dumps(r,default=str));raise SystemExit(0 if r['status']=='WRITER_PASS' else 1)
