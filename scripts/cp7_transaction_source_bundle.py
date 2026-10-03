"""Read-only exact Native parent resolution, explicitly composed after F03."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
ROLE='cp7_transaction_source_read'
GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)')
TABLES=('material_purchase_headers','material_purchase_items','material_rolls','material_supplier_invoices',
 'material_supplier_invoice_lines','supplier_payments','material_transfers','material_transfer_items',
 'material_adjustments','material_adjustment_items','fg_adjustments','fg_adjustment_items','sales_headers','sales_items',
 'sales_payments','sales_returns','sales_return_items','misc_finance_transactions','journal_entries','payroll_settlements')

def extension():return (ROOT/'scripts/cp7-src/transactions/source.sql').read_text()
def verify(cur):
    assert cur.execute("select rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication from pg_roles where rolname=%s",(ROLE,)).fetchone()==(False,False,False,False,False)
    rows=cur.execute("select proname,pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_transaction_source'").fetchall()
    assert {r[0]for r in rows}=={'authority','resolve'}
    for name,owner,secdef,vol,config in rows:
        assert (owner,secdef,vol,config)==(ROLE,False,'s',['search_path=""']+(['TimeZone=UTC']if name=='resolve'else[]))
    assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid='public.erp_cp7_resolve_transaction_source_v1(jsonb)'::regprocedure").fetchone()==(ROLE,True,'s',['search_path=""'])
    assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and has_table_privilege(%s,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))",(ROLE,)).fetchone()[0]
    for table in TABLES:assert cur.execute('select has_table_privilege(%s,%s,\'SELECT\')',(ROLE,'erp.'+table)).fetchone()[0]
    assert cur.execute("select has_schema_privilege(%s,'cp7_installment','USAGE')and has_table_privilege(%s,'cp7_installment.payments','SELECT')and not has_table_privilege(%s,'cp7_installment.payments','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(ROLE,ROLE,ROLE)).fetchone()[0]
    for who in ('anon','authenticated','service_role'):
        assert not cur.execute('select has_schema_privilege(%s,\'cp7_transaction_source\',\'USAGE\')or has_function_privilege(%s,\'cp7_transaction_source.resolve(jsonb)\',\'EXECUTE\')',(who,who)).fetchone()[0]
    return dict(read_only_exact_source_owned=True,source_sha256=hashlib.sha256(extension().encode()).hexdigest())
