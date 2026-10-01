"""Own-user reminder observations in the disposable Native browser clone."""
import os,sys,json
from urllib.parse import urlparse
import psycopg
import cp7_analysis_cases as analysis
def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin);assert op in('state','source')
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  if op=='source':
   # First prove current own-Original authorization through the public reader.
   # Then compare its archived Native facts with the identical read principal,
   # using this actual browser actor's claims. This is a disposable diagnostic.
   served=analysis.read(cur,p['run'],p['actor'])
   stored=cur.execute('select query,facts,dependency_hash from cp7_analysis_native.runs where id=%s and actor=%s',(p['run'],p['actor'])).fetchone()
   assert stored is not None
   cur.execute('set local role cp7_capture')
   current=cur.execute('select cp7_analysis_native.source(%s::jsonb)',(json.dumps(stored[0]),)).fetchone()[0]
   current_hash=cur.execute('select cp7_analysis_native.fingerprint(%s::jsonb)',(json.dumps(current),)).fetchone()[0]
   analysis.b.api.admin(cur)
   print(json.dumps(dict(source_state=served['source_state'],stored_hash=stored[2],current_hash=current_hash,stored=stored[1],current=current),default=str));return
  profile=cur.execute('select id from erp.app_users where auth_user_id=%s',(p['actor'],)).fetchone()[0]
  rows=cur.execute('select id::text,title,status,row_version::text,due_at::text from erp.manual_reminders where owner_user_id=%s order by created_at,id',(profile,)).fetchall()
  out=dict(manual_rows=[dict(zip(('id','title','status','revision','due_at'),r))for r in rows],analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0],request_count=cur.execute('select count(*)from cp7_reminder_native.requests where actor=%s',(p['actor'],)).fetchone()[0])
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
