"""Read-only Native policy state for actual browser receipt assertions."""
from urllib.parse import urlparse
import os,sys,json
import psycopg
def main():
 url=urlparse(os.environ['AUDITOR_BROWSER_DB_URL']);assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(os.environ['AUDITOR_BROWSER_DB_URL'])as conn,conn.cursor()as cur:
  if op!='state':raise ValueError('POLICY_BROWSER_READ_ONLY')
  out=dict(policy_count=cur.execute('select count(*)from cp7_reminder_native.rule_policies').fetchone()[0],analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0],native_manual_count=cur.execute('select count(*)from erp.manual_reminders').fetchone()[0])
 print(json.dumps(out))
if __name__=='__main__':main()
