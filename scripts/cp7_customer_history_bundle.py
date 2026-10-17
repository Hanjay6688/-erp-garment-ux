"""R3-03 (owner D16-1): Riwayat Pelanggan reads real data through one read-only CP7 facade.

customer-history.sql: public.erp_cp7_get_customer_history_v1(p_query jsonb), owned by the NOLOGIN role
cp7_customer_history_read and executable by authenticated only, calls the private STABLE workspace of schema
cp7_customer_history (functions owned by postgres, security definer, search_path ''). List mode: customers by code/name,
paged, with document counts and, with finance.ar.view, the open balance. Customer mode: the customer's timeline of invoices,
payments, returns and cancellations (WIB dates, newest first, paged) and the invoices on the page with their status and,
with finance.ar.view, total / returned / paid / balance (the definitions of cp7_sales.header, scripts/cp7-src/sales/read.sql).
Nothing is written; no Native definition changes; the schema (owned by the role) is dropped with the role on uninstall.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_customer_history_read',)
ROLE = ROLES[0]
SCHEMA = 'cp7_customer_history'
PUBLIC = {'public.erp_cp7_get_customer_history_v1(jsonb)': ROLE}
# name -> (security definer, volatility, TimeZone=UTC)
EXPECTED = {
    'access_now': (True, 's', False), 'invoices': (True, 's', False), 'ended_at': (True, 's', False),
    'events': (True, 's', False), 'summary': (True, 's', False), 'workspace': (True, 's', True),
}
ENTRY = {ROLE: ('workspace',)}
OUTSIDERS = ('anon', 'authenticated', 'service_role', 'cp7_capture')


def extension():
    return (ROOT / 'scripts/cp7-src/sales/customer-history.sql').read_text()


def verify(cur):
    rows = cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig "
                       "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s", (SCHEMA,)).fetchall()
    assert {r[1] for r in rows} == set(EXPECTED) and len(rows) == len(EXPECTED), rows
    for sig, name, owner, secdef, vol, config in rows:
        security, volatility, utc = EXPECTED[name]
        assert (owner, secdef, vol, config) == ('postgres', security, volatility, ['search_path=""'] + (['TimeZone=UTC'] if utc else [])), sig
        for who in OUTSIDERS:
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
        for who in ROLES:
            assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0] == (name in ENTRY[who]), (who, sig)
    assert cur.execute('select pg_get_userbyid(nspowner) from pg_namespace where nspname=%s', (SCHEMA,)).fetchone()[0] == ROLE
    for who in OUTSIDERS:
        assert not cur.execute("select has_schema_privilege(%s,%s,'USAGE,CREATE')", (who, SCHEMA)).fetchone()[0], (who, SCHEMA)
    # No table, view or sequence of its own: a reader only.
    assert cur.execute("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=%s", (SCHEMA,)).fetchone()[0] == 0
    for who in ROLES:
        assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',
                           (who,)).fetchone() == (False, False, False, False, False, False, False), who
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'"
                               " and c.relkind in('r','p','v','m') and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",
                               (who,)).fetchone()[0], who
    for signature, owner in PUBLIC.items():
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig,prolang=(select oid from pg_language where lanname=%s) '
                           'from pg_proc where oid=%s::regprocedure', ('sql', signature)).fetchone() == (owner, True, 's', ['search_path=""'], True), signature
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0], signature
        for who in ('anon', 'service_role', 'cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, signature)).fetchone()[0], (who, signature)
    return dict(closed_private_customer_history_facade=True, read_only=True, single_snapshot_stable=True, Native_definitions_unchanged=True,
                public=sorted(PUBLIC), private=sorted(EXPECTED))
