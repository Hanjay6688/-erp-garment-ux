"""Read-only publication observer in the authorized disposable browser clone."""
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_analysis_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 assert sys.argv[1]=='state';p=json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  cur.execute('set transaction read only')
  out=dict(publication_count=cur.execute('select count(*)from cp7_analysis_native.publications where actor=%s',(p['actor'],)).fetchone()[0],requests=cur.execute('select request_id::text,status from cp7_analysis_native.report_requests where actor=%s order by request_id',(p['actor'],)).fetchall(),business=cases.b.boundary.snapshot(cur));conn.rollback()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
