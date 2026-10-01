"""Own-user reminder observations in the disposable Native browser clone."""
import os,sys,json
from urllib.parse import urlparse
import psycopg
def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin);assert op=='state'
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  profile=cur.execute('select id from erp.app_users where auth_user_id=%s',(p['actor'],)).fetchone()[0]
  rows=cur.execute('select id::text,title,status,row_version::text,due_at::text from erp.manual_reminders where owner_user_id=%s order by created_at,id',(profile,)).fetchall()
  out=dict(manual_rows=[dict(zip(('id','title','status','revision','due_at'),r))for r in rows],analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0],request_count=cur.execute('select count(*)from cp7_reminder_native.requests where actor=%s',(p['actor'],)).fetchone()[0])
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
