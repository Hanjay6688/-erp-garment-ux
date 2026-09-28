"""Exact BF installation over delivered AC..BE. No writer tests executed."""
from pathlib import Path
import sys,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'audit-results';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'audits/independent_be_20260928'))
import audit_state

def state():
 r=audit_state.snapshot()
 import psycopg
 with psycopg.connect(audit_state.DSN) as c:
  for key,query in {
   'constraints':"select n.nspname,t.relname,c.conname,pg_get_constraintdef(c.oid) from pg_constraint c join pg_class t on t.oid=c.conrelid join pg_namespace n on n.oid=t.relnamespace where n.nspname in ('erp','public') order by 1,2,3",
   'indexes':"select schemaname,tablename,indexname,indexdef from pg_indexes where schemaname in ('erp','public') order by 1,2,3",
   'triggers':"select n.nspname,t.relname,g.tgname,pg_get_triggerdef(g.oid) from pg_trigger g join pg_class t on t.oid=g.tgrelid join pg_namespace n on n.oid=t.relnamespace where n.nspname in ('erp','public') and not g.tgisinternal order by 1,2,3",
   'policies':"select * from pg_policies where schemaname in ('erp','public') order by schemaname,tablename,policyname"
  }.items():r[key]=audit_state.digest(c.execute(query).fetchall())
 r['limits']='Sequence counters excluded; data, functions, permissions, relations, columns, constraints, indexes, triggers and RLS policies compared.'
 return r

def apply(path):
 import psycopg
 with psycopg.connect(audit_state.DSN,autocommit=True) as c:c.execute((ROOT/path).read_text(),prepare=False)

if __name__=='__main__':
 subprocess.run([sys.executable,str(ROOT/'audits/independent_be_20260928/install_be.py')],check=True)
 before=state();(OUT/'sku-before-bf.json').write_text(json.dumps(before,indent=2,default=str))
 p='supabase/dev/cp6_bf_t1_family.sql';apply(p)
 (OUT/'sku-installation.json').write_text(json.dumps({'candidate':'23e9c9830c32dce10604c43d17e4476d2707b55d','scope':'Exact AC..BE release package plus unchanged BF dev installer','BF_sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),'status':'INSTALLED'},indent=2))
 print('BF installed; ready for own tests')
