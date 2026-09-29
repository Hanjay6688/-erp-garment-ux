"""Native period close/reopen adapter, separate from the financial read principal."""
from pathlib import Path
import cp7_finance_bundle
ROOT=Path(__file__).resolve().parents[1]
READ_GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.accounting_close_preflight_v1(date)','cp7_finance.exact_numbers(jsonb)')
WRITE_GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.close_accounting_through(date,text)','erp.reopen_accounting_through(date,text)')
def extension():return (ROOT/'scripts/cp7-src/finance/period.sql').read_text()
def bundle():return cp7_finance_bundle.bundle()+'\n'+extension()

def verify(cur):
    expected={'access_now':('cp7_period_read',False,'s',['search_path=""']), 'workspace':('cp7_period_read',True,'s',['search_path=""','TimeZone=UTC']), 'lock_current':('postgres',True,'v',['search_path=""']), 'command':('cp7_period_write',False,'v',['search_path=""'])}
    actual=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_period'").fetchall()
    assert {r[0]for r in actual}==set(expected)
    for name,*metadata in actual:assert tuple(metadata)==expected[name],(name,metadata)
    # The native-lock owner is deliberately not a superuser in Supabase.
    assert cur.execute("select has_function_privilege('postgres','cp7_period.access_now()','EXECUTE')").fetchone()[0]
    for sig,owner,vol in [('public.erp_cp7_get_period_control_v1(date)','cp7_period_read','s'),('public.erp_cp7_save_period_control_v1(text,jsonb,uuid)','cp7_period_write','v')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,vol,['search_path=""'])
