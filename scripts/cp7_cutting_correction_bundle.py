"""Closed current-authority facade over the accepted pre-sewing cutting inverse."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROLES=('cp7_cutting_write','cp7_cutting_read')
SCHEMA='cp7_cutting_correction'
TABLES=('requests','history')
def extension():return (ROOT/'scripts/cp7-src/cutting-correction/reopen.sql').read_text()
def verify(cur):
    expected={'access_now':(True,'v',False),'immutable':(False,'v',False),
        'snapshot':(True,'s',True),'workspace':(True,'v',False),'command':(True,'v',False)}
    rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",(SCHEMA,)).fetchall()
    assert {r[1]for r in rows}==set(expected),rows
    for sig,name,owner,secdef,vol,config in rows:
        security,volatility,utc=expected[name]
        assert(owner,secdef,vol,config)==('postgres',security,volatility,['search_path=""']+(['TimeZone=UTC']if utc else[])),sig
        for who in('anon','authenticated','service_role','cp7_capture','cp7_transaction_source_read'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0],(who,sig)
        for who,allowed in(('cp7_cutting_read','workspace'),('cp7_cutting_write','command')):
            assert cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]==(name==allowed),(who,sig)
    for who in ROLES:
        assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',(who,)).fetchone()==(False,False,False,False,False,False,False)
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",(who,)).fetchone()[0],who
        assert not cur.execute("select has_function_privilege(%s,'erp.reverse_cutting_material_flow_before_sewing_v2(uuid,text,uuid,bigint)','EXECUTE')",(who,)).fetchone()[0],who
    for table in TABLES:
        relation=SCHEMA+'.'+table
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(relation,)).fetchone()==('postgres',True)
        assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(relation,)).fetchone()[0]==1
        for who in('anon','authenticated','service_role','cp7_capture','cp7_transaction_source_read')+ROLES:
            assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER\')',(who,relation)).fetchone()[0],(who,relation)
    assert cur.execute('select count(*)from pg_trigger where tgrelid=%s::regclass and tgfoid=%s::regprocedure and not tgisinternal',(SCHEMA+'.history',SCHEMA+'.immutable()')).fetchone()[0]==2
    for signature,owner in(('public.erp_cp7_get_cutting_correction_v1(uuid)','cp7_cutting_read'),('public.erp_cp7_reopen_cutting_v1(jsonb,uuid,text)','cp7_cutting_write')):
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()==(owner,True,'v',['search_path=""'])
        assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(signature,)).fetchone()[0]
        for who in('anon','service_role','cp7_capture','cp7_transaction_source_read'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,signature)).fetchone()[0],(who,signature)
    return dict(current_owner_authority_before_after_waits=True,Native_inverse_unchanged=True,
        closed_private_cutting_facades=True,no_new_ERP_DML_or_direct_Native_grants=True,immutable_original_source=True)
