"""Native queue control without replacing any accepted costing function."""
from pathlib import Path
import cp7_period_bundle
ROOT=Path(__file__).resolve().parents[1]
READ_GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)')
WRITE_GRANTS=READ_GRANTS+('erp.process_cost_recalc_queue(integer)',)
def extension():return (ROOT/'scripts/cp7-src/finance/recost.sql').read_text()
def bundle():return cp7_period_bundle.bundle()+'\n'+extension()
def verify(cur):
 expected={'access_now':('cp7_recost_read',False,'s',['search_path=""']), 'workspace':('cp7_recost_read',True,'s',['search_path=""','TimeZone=UTC']), 'command':('cp7_recost_write',False,'v',['search_path=""'])}
 actual=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_recost'").fetchall()
 assert {r[0]for r in actual}==set(expected)
 for name,*metadata in actual:assert tuple(metadata)==expected[name],(name,metadata)
 for sig,owner,vol in [('public.erp_cp7_get_recost_queue_v1(integer)','cp7_recost_read','s'),('public.erp_cp7_process_recost_v1(jsonb,uuid)','cp7_recost_write','v')]:
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,vol,['search_path=""'])
