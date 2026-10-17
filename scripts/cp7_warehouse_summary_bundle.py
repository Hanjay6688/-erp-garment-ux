"""R3-03 (owner D16-1): Ringkasan Gudang reads real stock (menu warehouse-dashboard).

summary.sql: one read-only facade public.erp_cp7_get_warehouse_summary_v1(p_query) for warehouse.dashboard.view. Per
location and kind it sums the rows of the detail reads with their own Native tables, filters and rounding (Bahan & Roll
without accessories, Aksesori, Ringkasan Barang Jadi), each section only with its screen's key, values only with
finance.hpp.view, plus an attention list of facts the Native tables state. The private functions are STABLE (one
snapshot per answer; PostgreSQL refuses any write in them), owned by postgres; the public wrapper is owned by the NOLOGIN
role cp7_warehouse_summary_read, which owns the schema and has no table privilege. No table, trigger or Native definition
change; uninstall is `drop owned by cp7_warehouse_summary_read cascade; drop role ...` like every other F03 role.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_warehouse_summary_read',)
SCHEMA = 'cp7_warehouse_summary'
FUNCTIONS = ('erp_cp7_get_warehouse_summary_v1',)
PUBLIC = {'public.erp_cp7_get_warehouse_summary_v1(jsonb)': 'cp7_warehouse_summary_read'}
# name -> (security definer, volatility, TimeZone=UTC)
EXPECTED = {'access_now': (True, 's', False), 'workspace': (True, 's', False)}
ENTRY = {'cp7_warehouse_summary_read': ('workspace',)}
OUTSIDERS = ('anon', 'authenticated', 'service_role', 'cp7_capture')


def extension():
    return (ROOT / 'scripts/cp7-src/warehouse-summary/summary.sql').read_text()


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
    for who in ROLES:
        assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',
                           (who,)).fetchone() == (False, False, False, False, False, False, False), who
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'"
                               " and c.relkind in('r','p','v','m') and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",
                               (who,)).fetchone()[0], who
    assert cur.execute('select pg_get_userbyid(nspowner) from pg_namespace where nspname=%s', (SCHEMA,)).fetchone()[0] == ROLES[0]
    # Read-only: no relation, sequence or trigger of its own, nothing executable by a client but the public wrapper.
    assert cur.execute("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=%s", (SCHEMA,)).fetchone()[0] == 0
    assert cur.execute("select count(*) from pg_trigger t join pg_proc p on p.oid=t.tgfoid join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",
                       (SCHEMA,)).fetchone()[0] == 0
    for who in OUTSIDERS:
        assert not cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (who, SCHEMA)).fetchone()[0], (who, SCHEMA)
    for signature, owner in PUBLIC.items():
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig,prolang=(select oid from pg_language where lanname=%s) '
                           'from pg_proc where oid=%s::regprocedure', ('sql', signature)).fetchone() == (owner, True, 's', ['search_path=""'], True), signature
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0], signature
        for who in ('anon', 'service_role', 'cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, signature)).fetchone()[0], (who, signature)
    assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proowner=%s::regrole",
                       (ROLES[0],)).fetchone()[0] == len(PUBLIC)
    return dict(closed_private_warehouse_summary_facade=True, read_only_stable_one_snapshot=True, no_tables=True, Native_definitions_unchanged=True,
                public_rpcs=list(FUNCTIONS), page_permission='warehouse.dashboard.view',
                sections={'materials': 'warehouse.material.view', 'accessories': 'warehouse.accessory.view', 'finished_goods': 'warehouse.fg.view',
                          'values': 'finance.hpp.view'})
