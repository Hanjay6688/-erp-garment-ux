"""Exact private capabilities; no App ERP DML or Native-definition change."""
def verify(cur):
    ns='cp7_supplier_payment_correction'
    expected={'access_now':('cp7_invoice_read',False,'s',['search_path=""']),
      'validate':('cp7_invoice_read',False,'i',['search_path=""']),
      'link_value':('postgres',True,'s',['search_path=""','TimeZone=UTC']),
      'workspace':('postgres',True,'v',['search_path=""','TimeZone=UTC']),
      'protect_link':('postgres',True,'v',['search_path=""']),
      'apply':('postgres',True,'v',['search_path=""','TimeZone=UTC']),
      'command':('cp7_invoice_write',False,'v',['search_path=""'])}
    rows=cur.execute('select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s',(ns,)).fetchall()
    assert {r[0]for r in rows}==set(expected)
    for name,*actual in rows:assert tuple(actual)==expected[name],(name,actual)
    for sig,owner in [('public.erp_cp7_correct_supplier_payment_v1(jsonb,uuid)','cp7_invoice_write'),('public.erp_cp7_get_supplier_payment_correction_v1(jsonb)','cp7_invoice_read')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,'v',['search_path=""'])
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')",(sig,)).fetchone()[0]
        for who in('anon','service_role','cp7_capture'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
    for who in('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')or has_function_privilege(%s,\'cp7_supplier_payment_correction.apply(jsonb,uuid)\',\'EXECUTE\')',(who,ns,who)).fetchone()[0]
        for table in('requests','context','links'):assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER\')',(who,ns+'.'+table)).fetchone()[0]
    for table in('erp.supplier_payments','erp.material_purchase_headers','erp.journal_entries','erp.journal_lines'):
        for who in('cp7_invoice_read','cp7_invoice_write'):assert not cur.execute('select has_table_privilege(%s,%s,\'INSERT,UPDATE,DELETE\')',(who,table)).fetchone()[0]
    assert cur.execute("select has_table_privilege('postgres','cp7_supplier_payment_correction.context','SELECT')and has_table_privilege('postgres','cp7_supplier_payment_correction.links','SELECT,INSERT')").fetchone()[0]
    assert not cur.execute('select exists(select 1 from cp7_supplier_payment_correction.context)').fetchone()[0]
    return dict(ordinary_supplier_payment_atomic_Native_inverse_post=True,immutable_link_private_context=True,App_ERP_DML=False,Native_definition_change=False)
