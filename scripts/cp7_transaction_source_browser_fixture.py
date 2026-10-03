"""Disposable source-navigation setup; all economic changes use Native commands."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_misc_cases as misc

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f=misc.fixture(cur,date.fromisoformat(p['today']));saved=misc.command(cur,'SAVE',misc.save_payload(f));posted=misc.command(cur,'POST',misc.intent(saved));ident=posted['transaction_id'];doc=misc.native_document(cur,ident)
   out=dict(fixture=f,transaction_id=ident,document=doc,journal_id=doc['journals'][0]['id'])
  elif op=='state':
   f=p['fixture'];ident=p['transaction_id'];doc=misc.native_document(cur,ident)
   assert misc.stock_cost(cur)==f['stock_cost'],'SOURCE_NAVIGATION_STOCK_HPP_CHANGED'
   out=dict(document=doc,cash_delta=str((misc.cash_balance(cur,f['cash']['id'])-misc.D(f['cash_before'])).quantize(misc.D('.01'))),stock_HPP_unchanged=True)
  else:raise ValueError('Unknown source navigation fixture operation')
  misc.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
