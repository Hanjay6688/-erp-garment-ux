"""Closed capabilities for one reviewed Native sale-chain transaction."""
SCHEMA='cp7_sales_chain'
TABLES=('requests','history')
def verify(cur):
    expected={'access_now':(True,'v',False),'immutable':(False,'v',False),'snapshot':(True,'s',True),
        'token':(True,'s',False),'workspace':(True,'v',True),'validate':(False,'i',False),'command':(True,'v',True)}
    rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",(SCHEMA,)).fetchall()
    assert {r[1]for r in rows}==set(expected),rows
    for sig,name,owner,secdef,vol,config in rows:
        security,volatility,utc=expected[name]
        assert (owner,secdef,vol,config)==('postgres',security,volatility,['search_path=""']+(['TimeZone=UTC']if utc else[])),(sig,owner,secdef,vol,config)
        for who in ('anon','authenticated','service_role','cp7_capture'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0],(who,sig)
        for who,allowed in [('cp7_sales_read','workspace'),('cp7_sales_write','command')]:
            assert cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]==(name==allowed),(who,sig)
    for sig,owner in [('public.erp_cp7_get_sales_chain_v1(uuid)','cp7_sales_read'),('public.erp_cp7_reverse_sales_chain_v1(jsonb,uuid,text)','cp7_sales_write')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,'v',['search_path=""'])
        assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
        for who in ('anon','service_role','cp7_capture'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0],(who,sig)
    for table in TABLES:
        sig=SCHEMA+'.'+table
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(sig,)).fetchone()==('postgres',True)
        assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(sig,)).fetchone()[0]==1
        for who in ('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write'):
            assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER\')',(who,sig)).fetchone()[0],(who,sig)
    for who in ('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')',(who,SCHEMA)).fetchone()[0]
    assert cur.execute('select count(*)from pg_trigger where tgrelid=%s::regclass and tgfoid=%s::regprocedure and not tgisinternal',(SCHEMA+'.history',SCHEMA+'.immutable()')).fetchone()[0]==2
    assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_sales_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
    assert not cur.execute('select exists(select 1 from cp7_sales.command_context)').fetchone()[0]
    return dict(all_business_effects_existing_Native_commands=True,closed_private_chain_capabilities=True,no_app_ERP_DML=True,immutable_reviewed_source_history=True)
