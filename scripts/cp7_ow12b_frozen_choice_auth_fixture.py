"""Actual frozen snapshots and readback on the isolated browser database only."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_ow12b_frozen_choice_cases as choice

def capture(cur,today,actor,target):
 observed={};f=choice.native.capture(cur,today,actor,observed)
 read=choice.reader.call(cur,f,target,observed)
 return dict(context=dict(actor=actor,requestId=f['key'],runId=f['done']['run_id'],targetKey=target,
   query=f['row']['query'],reference=dict(capturedAt=read['reference']['captured_at'],sourceHash=read['reference']['source_hash']),
   identityHash=read['identity_hash'],accessEpoch=read['access_epoch'],sourceMethod='FROZEN_V2'),
   exact_read=read,observations=observed,actual_Native_frozen_DONE=True)

def main():
 url=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(url)
 assert u.hostname in('localhost','127.0.0.1')and u.path=='/cp6_auditor_browser'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(url)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   today=date.fromisoformat(p['today']);x=choice.plan.fixture(cur,today)
   imported=choice.reader.reader.volume.import_batch(cur,today,11,choice.reader.reader.volume.Phases())
   historical=choice.reader.reader.historical.seed(cur,imported);target=imported[0]['target']
   source=next(x['target']for x in historical if x['target'].split(':')[1]==target.split(':')[1])
   choice.consumer.profile(cur,imported[0]['root'])
   out=dict(capture(cur,today,p['actor'],target),root=x['root'],source=source)
  elif op=='capture':out=capture(cur,date.fromisoformat(p['today']),p['actor'],p['target'])
  elif op=='state':
   choice.plan.b.api.admin(cur)
   out=dict(physical=choice.plan.monetary_state(cur),metadata=choice.choice.metadata(cur),
    choices=cur.execute('select count(*)from cp7_product_analog_choice.choices where actor=%s',(p['actor'],)).fetchone()[0],
    commands=cur.execute('select count(*)from cp7_product_analog_choice.commands where actor=%s',(p['actor'],)).fetchone()[0])
  elif op=='stock':choice.plan.found_fg(cur,dict(root=p['root']),'1');out=dict(actual_Native_stock_writer=True)
  elif op in('deactivate','restore'):
   cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_FROZEN_CHOICE_BROWSER_CONTROL')
  choice.plan.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
