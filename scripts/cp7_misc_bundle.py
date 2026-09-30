"""Bounded native misc-finance lifecycle; exact source/replay/current authority."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
READ_GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)')
WRITE_GRANTS=('auth.uid()',)
def extension():return (ROOT/'scripts/cp7-src/finance/misc.sql').read_text()
def verify(cur):
    expected={
        'access_now':('cp7_misc_read',True,'s',['search_path=""']),
        'category':('cp7_misc_read',True,'s',['search_path=""']),
        'cash':('cp7_misc_read',True,'s',['search_path=""']),
        'source':('cp7_misc_read',True,'s',['search_path=""','TimeZone=UTC']),
        'workspace':('cp7_misc_read',False,'s',['search_path=""','TimeZone=UTC']),
        'validate':('cp7_misc_read',False,'i',['search_path=""']),
        'apply_command':('postgres',True,'v',['search_path=""','TimeZone=UTC']),
        'command':('cp7_misc_write',False,'v',['search_path=""']),
    }
    rows=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_misc'").fetchall()
    assert {r[0]for r in rows}==set(expected)
    for name,*metadata in rows:assert tuple(metadata)==expected[name],(name,metadata)
    for sig,owner,vol in [('public.erp_cp7_get_misc_finance_v1(jsonb)','cp7_misc_read','s'),('public.erp_cp7_save_misc_finance_v1(text,jsonb,uuid,text)','cp7_misc_write','v')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,vol,['search_path=""'])
    for role in ('cp7_misc_read','cp7_misc_write'):
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege(%s,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))",(role,)).fetchone()[0]
        for sig in ('erp.post_journal(text,uuid,date,text,jsonb)','erp.post_misc_finance(uuid)','erp.reverse_misc_finance(uuid,text)'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,sig)).fetchone()[0]
    for who in ('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute("select has_schema_privilege(%s,'cp7_misc','USAGE')or has_function_privilege(%s,'cp7_misc.apply_command(text,jsonb,uuid)','EXECUTE')",(who,who)).fetchone()[0]
    assert not cur.execute('select exists(select 1 from cp7_misc.command_context)').fetchone()[0]
    return dict(native_writer_only_in_private_postgres_context=True,no_app_DML_or_private_writer=True)
