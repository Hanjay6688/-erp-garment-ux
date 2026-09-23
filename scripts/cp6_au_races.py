"""Ordinary master API versus WIP output: observed two-session blocking."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import queue
import psycopg
import cp6_au_cases as cases
import cp6_at_races as at
import cp6_ao_ap_installed as api
import cp6_initial_import_production_trial as production
import cp6_successor_regression as boundary

def run(today,first,commit):
 with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
  f,s,p=cases.fixture(cur,today)
  effective=cur.execute("select clock_timestamp()+interval '1 day'").fetchone()[0]
  payload=dict(batch_id=f['batch'],opening_item_id=s['WIP']['opening_item_id'],expected_remaining='8',operation='COMPLETE',qty_pcs='4',
      product_sku=p[1],product_id=str(p[0]),location_code=f['code']+'F',date=str(today-timedelta(days=3)),reason='AU concurrent master identity')
  initial=production.effects(api,cur)
 ready=queue.Queue()
 def action(cur,kind):
  return api.call(cur,'WIP_OUTPUT',payload) if kind=='OUTPUT' else cases.edit(cur,p,effective)
 def worker(kind):
  try:
   with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
    cur.execute("set local lock_timeout='15s';set local statement_timeout='30s'")
    ready.put(cur.execute('select pg_backend_pid()').fetchone()[0])
    return dict(ok=True,result=action(cur,kind))
  except psycopg.Error as exc:return dict(ok=False,sqlstate=exc.sqlstate,message=exc.diag.message_primary)
 with psycopg.connect(boundary.ADMIN) as holder,holder.cursor() as cur,ThreadPoolExecutor(max_workers=1) as pool:
  holder_pid=cur.execute('select pg_backend_pid()').fetchone()[0]
  posted=action(cur,first);api.admin(cur)
  future=pool.submit(worker,'OUTPUT' if first=='MASTER' else 'MASTER')
  waiter=ready.get(timeout=10);observed=at.blocking(cur,waiter,holder_pid)
  (holder.commit if commit else holder.rollback)()
  result=future.result(timeout=35)
 assert result['ok'],result
 with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
  rows=cur.execute('select id,color_name,effective_to,supersedes_product_id from erp.products where identity_root_id=%s order by effective_from',(p[0],)).fetchall()
  lot=cur.execute('''select l.product_id,l.initial_qty_pcs from erp.initial_import_wip_outputs o
      join erp.initial_import_production_sources s on s.opening_item_id=o.opening_item_id
      join erp.fg_lots l on l.id=o.lot_id where s.batch_id=%s''',(f['batch'],)).fetchall()
  output_committed=first=='MASTER' or commit
  assert lot==([(p[0],4)] if output_committed else []),lot
  if first=='OUTPUT' and commit:
   assert len(rows)==2 and rows[0][0]==p[0] and rows[0][1]=='Blue' and rows[0][2]==effective and rows[1][1]=='Green' and rows[1][3]==p[0],rows
  else:
   color='Blue' if first=='MASTER' and not commit else 'Green'
   assert rows==[(p[0],color,None,None)],rows
  assert cur.execute('select count(*) from erp.product_identity_mutation_context_v1').fetchone()==(0,)
  production.truth(cur)
  if output_committed:
   output=result['result'] if first=='MASTER' else posted
   production.reverse_output(api,cur,f,output)
   assert production.effects(api,cur)==initial
 return dict(status='PASS',first=first,first_committed=commit,blocking_observed=observed,
     both_actions='ordinary authenticated API',output_posted=output_committed,identity_history_preserved=True,
     output_linked_inverse_restores_net_ledger=output_committed,unused_authority_rows=0)
