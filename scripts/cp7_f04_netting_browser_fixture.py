"""Disposable browser fixture: ordinary Native opening + current metadata only."""
from datetime import date,timedelta,datetime
from urllib.parse import urlparse
import os,sys,json,math
import psycopg
import cp7_planning_netting_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f=cases.schedule.opening(cur,date.fromisoformat(p['today']))
   root=cur.execute('select product_id::text from erp.opening_balance_items where id=%s',(f['item'],)).fetchone()[0]
   cases.select_profiles(cur,root,True)
   source=cases.supply.capture(cur,date.fromisoformat(p['today']))
   reviewed=cases.schedule.payload(cur,source)
   load=sum(int(step['remaining_minutes'])for position in reviewed['config']['positions']for step in position['remaining_steps'])
   at=cur.execute('select clock_timestamp()').fetchone()[0].replace(microsecond=0)+timedelta(hours=1)
   # Retain every real WIP origin from earlier journeys. The positive scenario
   # reviews a calendar large enough for the entire queue, plus 120 free minutes.
   out=dict(product=root,source_item=f['item'],window_start=cases.schedule.stamp(at),window_end=cases.schedule.stamp(at+timedelta(minutes=load+120)),through=cases.schedule.stamp(at+timedelta(minutes=load+180)))
  elif op=='state':
   plan=cur.execute('select revision,config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()
   # Independent arithmetic oracle on the actual selected fixture, no planner
   # capacity/netting function called to decide its own expected result.
   remaining=sum(int(s['remaining_minutes'])for w in plan[1]['positions']for s in w['remaining_steps'])if plan else None
   unit=int(plan[1]['unit_minutes'])if plan else None
   calendar=sum(int((datetime.fromisoformat(w['ends_at'].replace('Z','+00:00'))-datetime.fromisoformat(w['starts_at'].replace('Z','+00:00'))).total_seconds())//60-int(w['other_load_minutes'])for w in plan[1]['windows'])if plan else None
   out=dict(plan_count=cur.execute('select count(*)from cp7_schedule_native.plans').fetchone()[0],plan_revision=str(plan[0])if plan else '0',expected_capacity=str(max(0,calendar-remaining)//unit)if plan else None,
    supply_count=cur.execute('select count(*)from cp7_supply_native.runs where actor=%s',(p['actor'],)).fetchone()[0],net_count=cur.execute('select count(*)from cp7_netting_native.runs where actor=%s',(p['actor'],)).fetchone()[0],business=cases.b.boundary.snapshot(cur))
  elif op=='update_schedule':
   plan=cur.execute('select revision,config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()
   run=cases.supply.capture(cur,date.fromisoformat(p['today']));payload=cases.schedule.payload(cur,run,str(plan[0]));payload['config']=plan[1];payload['config']['unit_minutes']='4';payload['reason']='Explicit independent browser fixture schedule review';out=cases.schedule.save(cur,payload)
  elif op in('deactivate','restore'):
   cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_P06_NETTING_BROWSER_FIXTURE_ACTION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
