"""Disposable Native BOM masters only; UI quantities come from actual RPCs."""
from datetime import date,timedelta,datetime
from urllib.parse import urlparse
import os,sys,json
import psycopg
import cp7_analysis_cases as parent
import cp7_material_need_cases as material

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   _,root,_,payload=parent.setup(cur,date.fromisoformat(p['today']),False)
   load=sum(int(step['remaining_minutes'])for w in payload['config']['positions']for step in w['remaining_steps']);start=datetime.fromisoformat(payload['config']['windows'][0]['starts_at'].replace('Z','+00:00'))
   payload['config']['windows'][0]['ends_at']=parent.schedule.stamp(start+timedelta(minutes=load+120));payload['config']['through_at']=parent.schedule.stamp(start+timedelta(minutes=load+180));parent.schedule.save(cur,payload)
   category=material.master(cur,date.fromisoformat(p['today']),parent);version=material.bom(cur,root,parent,category);material.review_schedule(cur,date.fromisoformat(p['today']),parent);out=dict(today=p['today'],product=root,category_id=category['category_id'],unit=category['unit'],bom_id=version['id'])
  elif op=='successor':
   stored=cur.execute('select result from cp7_analysis_native.runs where id=%s and actor=%s',(p['run'],p['actor'])).fetchone();assert stored is not None
   row=next(m for m in stored[0]['material_needs']if m['target_key'].split(':')[0]==p['product']and m['material_key']=='ACCESSORY_CATEGORY:'+p['category_id']);assert any(r['kind']=='erp.accessory_bom_versions'and r['id']==p['bom_id']for r in row['gross']['refs'])
   out=material.bom(cur,p['product'],parent,dict(category_id=p['category_id'],unit=p['unit']),qty='3')
   material.review_schedule(cur,date.fromisoformat(p['today']),parent)
  elif op=='state':out=dict(analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0],business=parent.b.boundary.snapshot(cur))
  elif op in('deactivate','restore'):cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_MATERIAL_BROWSER_FIXTURE_ACTION')
  parent.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
