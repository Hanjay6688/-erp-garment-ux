"""Source-only journal reader; no native writer or guard delta."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)')
def extension():return (ROOT/'scripts/cp7-src/finance/journal.sql').read_text()

def verify(cur):
    got=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_journal'").fetchall()
    assert {r[0]for r in got}=={'access_now','header','workspace'}
    for name,owner,secdef,vol,config in got:assert (owner,secdef,vol,config)==('cp7_journal_read',False,'s',['search_path=""']+(['TimeZone=UTC']if name=='workspace'else[])),name
    assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid='public.erp_cp7_get_journal_book_v1(jsonb)'::regprocedure").fetchone()==('cp7_journal_read',True,'s',['search_path=""'])
    assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_journal_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
    for who in ('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute("select has_schema_privilege(%s,'cp7_journal','USAGE') or has_function_privilege(%s,'cp7_journal.workspace(jsonb)','EXECUTE')",(who,who)).fetchone()[0]
    for sig in ('erp.post_journal(text,uuid,date,text,jsonb)','erp.reverse_journal(uuid,text)','erp.post_misc_finance(uuid)'):
        assert not cur.execute("select has_function_privilege('cp7_journal_read',%s,'EXECUTE')",(sig,)).fetchone()[0]
    return dict(private_functions_owned=True,reader_has_no_business_writer=True)
