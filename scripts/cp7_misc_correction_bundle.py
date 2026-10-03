"""Atomic posted-misc correction; old Native and reviewed writers unchanged."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extension():return (ROOT/'scripts/cp7-src/finance/misc-correction.sql').read_text()
def verify(cur):
    expected={
        'validate':('cp7_misc_read',False,'i',['search_path=""']),
        'link_value':('cp7_misc_read',False,'s',['search_path=""','TimeZone=UTC']),
        'history':('cp7_misc_read',False,'s',['search_path=""','TimeZone=UTC']),
        'protect_link':('postgres',True,'v',['search_path=""']),
        'apply':('postgres',True,'v',['search_path=""','TimeZone=UTC']),
        'command':('cp7_misc_write',False,'v',['search_path=""']),
    }
    rows=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_misc_correction'").fetchall()
    assert {r[0]for r in rows}==set(expected)
    for name,*meta in rows:assert tuple(meta)==expected[name],(name,meta)
    for sig,owner,vol in [('public.erp_cp7_correct_misc_finance_v1(jsonb,uuid)','cp7_misc_write','v'),('public.erp_cp7_get_misc_correction_history_v1(uuid)','cp7_misc_read','s')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,vol,['search_path=""'])
        assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
        for who in('anon','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
    for who in('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute("select has_schema_privilege(%s,'cp7_misc_correction','USAGE')or has_function_privilege(%s,'cp7_misc_correction.apply(jsonb,uuid)','EXECUTE')or has_table_privilege(%s,'cp7_misc_correction.links','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(who,who,who)).fetchone()[0]
    assert not cur.execute('select exists(select 1 from cp7_misc.command_context)').fetchone()[0]
    return dict(atomic_unchanged_Native_inverse_save_post=True,immutable_actual_correction_links=True,no_app_ERP_DML_or_private_context=True)
