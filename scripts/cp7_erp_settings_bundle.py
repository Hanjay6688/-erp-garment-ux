"""R3-03 (owner D16-1): the Pengaturan ERP screen (admin-settings) connected in the Enteng build.

erp-settings/settings.sql: one bounded read facade, public.erp_cp7_get_erp_settings_v1(), over the owner policy settings of the
accessory (BC) and laundry (BD) workflows and the official cutover date. It writes nothing; the screen changes a policy only
through the accepted Native writers erp_save_accessory_service_action_v1 / erp_save_laundry_bd_action_v1 (SET_POLICY), the same
calls the Aksesori and Laundry pages make. No Native definition or grant changes; no table of its own. The schema is owned by
cp7_erp_settings_read and dropped with it on uninstall. Must be installed after cp7_cutover_bundle (it reads cp7_cutover.control
and cp7_cutover.history).
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLE = 'cp7_erp_settings_read'
ROLES = (ROLE,)
SCHEMA = 'cp7_erp_settings'
PUBLIC = {'public.erp_cp7_get_erp_settings_v1()': ROLE}
# name -> (security definer, volatility, TimeZone=UTC)
EXPECTED = {
    'catalog': (True, 'i', False), 'access_now': (True, 's', False), 'stamp': (True, 'i', False), 'user_name': (True, 's', False),
    'family_json': (True, 's', False), 'choices': (True, 's', False), 'cutover': (True, 's', False), 'workspace': (True, 's', True),
}
ENTRY = {ROLE: ('workspace',)}
OUTSIDERS = ('anon', 'authenticated', 'service_role', 'cp7_capture')


def extension():
    return (ROOT / 'scripts/cp7-src/erp-settings/settings.sql').read_text()


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
    # No table, view or sequence of its own: the facade only reads Native rows.
    assert cur.execute("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=%s", (SCHEMA,)).fetchone()[0] == 0
    assert cur.execute('select pg_get_userbyid(nspowner) from pg_namespace where nspname=%s', (SCHEMA,)).fetchone()[0] == ROLE
    for who in OUTSIDERS:
        assert not cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (who, SCHEMA)).fetchone()[0], (who, SCHEMA)
    for who in ROLES:
        assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',
                           (who,)).fetchone() == (False, False, False, False, False, False, False), who
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'"
                               " and c.relkind in('r','p','v','m') and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",
                               (who,)).fetchone()[0], who
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_cutover'"
                               " and c.relkind in('r','p','v','m') and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",
                               (who,)).fetchone()[0], who
        assert not cur.execute("select has_schema_privilege(%s,'public','CREATE')", (who,)).fetchone()[0], who
        # It owns only its schema and its one public wrapper.
        owned = cur.execute("select n.nspname||'.'||p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace"
                            " where p.proowner=(select oid from pg_roles where rolname=%s)", (who,)).fetchall()
        assert [r[0] for r in owned] == ['public.erp_cp7_get_erp_settings_v1'], owned
    for signature, owner in PUBLIC.items():
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',
                           (signature,)).fetchone() == (owner, True, 's', ['search_path=""']), signature
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0], signature
        for who in ('anon', 'service_role', 'cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, signature)).fetchone()[0], (who, signature)
    return dict(closed_private_settings_facade=True, read_only=True, own_tables=0, Native_definitions_unchanged=True,
                writers=['public.erp_save_accessory_service_action_v1 SET_POLICY', 'public.erp_save_laundry_bd_action_v1 SET_POLICY'])
