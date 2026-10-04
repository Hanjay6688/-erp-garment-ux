"""Exact private capabilities for ordinary payment inverse plus replacement."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def verify(cur):
    expected={
        'access_now':('cp7_sales_read',False,'s',['search_path=""']),
        'validate':('cp7_sales_read',False,'i',['search_path=""']),
        'document':('cp7_sales_read',False,'s',['search_path=""','TimeZone=UTC']),
        'link_value':('postgres',True,'s',['search_path=""','TimeZone=UTC']),
        'workspace':('postgres',True,'s',['search_path=""','TimeZone=UTC']),
        'protect_link':('postgres',True,'v',['search_path=""']),
        'apply':('postgres',True,'v',['search_path=""','TimeZone=UTC']),
        'command':('cp7_sales_write',False,'v',['search_path=""']),
    }
    rows=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_payment_correction'").fetchall()
    assert {r[0]for r in rows}==set(expected)
    for name,*metadata in rows:assert tuple(metadata)==expected[name],(name,metadata)
    for sig,owner,vol in [('public.erp_cp7_correct_sales_payment_v1(jsonb,uuid,text)','cp7_sales_write','v'),('public.erp_cp7_get_sales_payment_correction_v1(jsonb)','cp7_sales_read','s')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,vol,['search_path=""'])
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')",(sig,)).fetchone()[0]
        for who in('anon','service_role','cp7_capture'):assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,sig)).fetchone()[0]
    for who in('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute("select has_schema_privilege(%s,'cp7_payment_correction','USAGE')or has_function_privilege(%s,'cp7_payment_correction.apply(jsonb,uuid,text)','EXECUTE')",(who,who)).fetchone()[0]
        for table in('requests','context','links'):
            assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(who,'cp7_payment_correction.'+table)).fetchone()[0]
    for table,privileges in [('cp7_sales.command_context',('SELECT','INSERT','DELETE')),('cp7_payment_correction.context',('SELECT',)),('cp7_payment_correction.links',('SELECT','INSERT'))]:
        for privilege in privileges:assert cur.execute("select has_table_privilege('postgres',%s,%s)",(table,privilege)).fetchone()[0],(table,privilege)
    for sig in('cp7_sales.command_access(text)','cp7_sales.review_token(uuid)','cp7_sales.apply_command(text,jsonb,uuid,text)',
               'cp7_sales.validate_payment(jsonb,boolean)','cp7_sales.access_now()','cp7_sales.cash_workspace(jsonb)',
               'cp7_payment_correction.access_now()','cp7_payment_correction.validate(jsonb)','cp7_payment_correction.document(erp.sales_payments)',
               'cp7_payment_correction.link_value(cp7_payment_correction.links)'):
        assert cur.execute("select has_function_privilege('postgres',%s,'EXECUTE')",(sig,)).fetchone()[0],sig
    assert not cur.execute("select has_function_privilege('cp7_sales_write','erp.post_sales_payment(uuid)','EXECUTE')or has_table_privilege('cp7_sales_write','erp.sales_payments','INSERT,UPDATE,DELETE')").fetchone()[0]
    assert not cur.execute('select exists(select 1 from cp7_sales.command_context)or exists(select 1 from cp7_payment_correction.context)').fetchone()[0]
    return dict(ordinary_payment_atomic_Native_inverse_post=True,existing_Native_guard_admission_unchanged=True,private_immutable_lineage=True,no_app_ERP_DML=True)
