"""Exact private capabilities of the new supplier payment entry; no App ERP DML or Native-definition change."""
def verify(cur):
    ns='cp7_supplier_payment_create'
    expected={'access_now':('cp7_invoice_read',False,'s',['search_path=""']),
      'validate':('cp7_invoice_read',False,'i',['search_path=""']),
      'review':('postgres',True,'v',['search_path=""','TimeZone=UTC']),
      'workspace':('postgres',True,'v',['search_path=""','TimeZone=UTC']),
      'apply':('postgres',True,'v',['search_path=""','TimeZone=UTC']),
      'command':('cp7_invoice_write',False,'v',['search_path=""'])}
    rows=cur.execute('select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s',(ns,)).fetchall()
    assert {r[0]for r in rows}==set(expected),rows
    for name,*actual in rows:assert tuple(actual)==expected[name],(name,actual)
    for sig,owner in [('public.erp_cp7_create_supplier_payment_v1(jsonb,uuid)','cp7_invoice_write'),('public.erp_cp7_get_supplier_payment_create_v1(jsonb)','cp7_invoice_read')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,'v',['search_path=""'])
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')",(sig,)).fetchone()[0]
        for who in('anon','service_role','cp7_capture'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
    for who in('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')',(who,ns)).fetchone()[0]
        for table in('requests','context'):assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER\')',(who,ns+'.'+table)).fetchone()[0]
    for table in('erp.supplier_payments','erp.material_purchase_headers','erp.journal_entries','erp.journal_lines'):
        for who in('cp7_invoice_read','cp7_invoice_write'):assert not cur.execute('select has_table_privilege(%s,%s,\'INSERT,UPDATE,DELETE\')',(who,table)).fetchone()[0]
    assert cur.execute("select has_table_privilege('postgres','cp7_supplier_payment_create.context','SELECT')").fetchone()[0]
    assert cur.execute("select count(*) from pg_policies where schemaname=%s",(ns,)).fetchone()[0]==2
    assert not cur.execute('select exists(select 1 from cp7_supplier_payment_create.context)').fetchone()[0]
    return dict(supplier_payment_create_Native_post_only=True,private_context=True,App_ERP_DML=False,Native_definition_change=False)
