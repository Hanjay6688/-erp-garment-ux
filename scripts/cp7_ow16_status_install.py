"""Isolated OW16 test-stage declaration; default bundles stay with integrator A."""
from hashlib import sha256
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT/'scripts/cp7-src/cutting-yield/automatic-status.sql'
PUBLIC = {
    'public.erp_cp7_get_cutting_status_v1(uuid)': 'cp7_capture',
    'public.erp_cp7_save_cutting_status_policy_v1(jsonb,uuid)': 'cp7_policy',
    'public.erp_cp7_get_cutting_status_policy_request_v1(jsonb,uuid)': 'cp7_policy',
}
PRIVATE = {
    'cp7_cutting_status.immutable()': ('cp7_policy', False, 'v'),
    'cp7_cutting_status.access(boolean)': ('cp7_capture', True, 'v'),
    'cp7_cutting_status.policy_json(cp7_cutting_status.policies)': ('cp7_policy', False, 'i'),
    'cp7_cutting_status.capture(uuid,timestamp with time zone)': ('cp7_capture', False, 's'),
    'cp7_cutting_status.workspace(uuid)': ('cp7_capture', False, 'v'),
    'cp7_cutting_status.payload(jsonb)': ('cp7_policy', False, 'i'),
    'cp7_cutting_status.command(jsonb,uuid,boolean)': ('cp7_policy', False, 'v'),
}
ROLES = ('anon', 'authenticated', 'service_role')


def extension():
    return PATH.read_text()


def verify(cur):
    expected = {name: body for name, body in re.findall(
        r'create function ((?:cp7_cutting_status|public)\.[a-z0-9_]+)\([^;]*?\).*?as \$\$(.*?)\$\$;',
        extension(), re.S)}
    assert len(expected) == 10, ('OW16_DECLARED_BODY_SET_CHANGED', list(expected))
    for signature, (owner, definer, volatility) in dict(PRIVATE, **{
            sig: (role, True, 'v') for sig, role in PUBLIC.items()}).items():
        body, actual_owner, actual_definer, actual_volatility, config = cur.execute(
            'select prosrc,pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig '
            'from pg_proc where oid=%s::regprocedure', (signature,)).fetchone()
        assert body == expected[signature.split('(')[0]], ('OW16_INSTALLED_BODY_CHANGED', signature)
        assert (actual_owner, actual_definer, actual_volatility, config) == \
               (owner, definer, volatility, ['search_path=""']), ('OW16_AUTHORITY_CHANGED', signature)
        for role in ROLES:
            allowed = signature in PUBLIC and role == 'authenticated'
            assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",
                               (role, signature)).fetchone()[0] == allowed, (signature, role)
    actual = set(cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                             "where n.nspname='cp7_cutting_status'").fetchall())
    # regprocedure may omit the schema of the composite argument according to
    # session search_path; compare OIDs rather than projecting function bodies.
    actual_oids = {cur.execute('select %s::regprocedure::oid', (row[0],)).fetchone()[0] for row in actual}
    assert actual_oids == {cur.execute('select %s::regprocedure::oid', (sig,)).fetchone()[0] for sig in PRIVATE}
    for role in ROLES:
        assert not cur.execute("select has_schema_privilege(%s,'cp7_cutting_status','USAGE')", (role,)).fetchone()[0]
        for table in ('policies', 'requests'):
            assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                                   (role, 'cp7_cutting_status.'+table)).fetchone()[0]
    for table in ('policies', 'requests'):
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',
                           ('cp7_cutting_status.'+table,)).fetchone() == ('cp7_policy', True)
        triggers = cur.execute("select tgtype,tgenabled,tgfoid='cp7_cutting_status.immutable()'::regprocedure "
                               "from pg_trigger where tgrelid=%s::regclass and not tgisinternal order by tgtype",
                               ('cp7_cutting_status.'+table,)).fetchall()
        assert triggers == [(27, 'O', True), (34, 'O', True)], (table, triggers)
    for role in ('cp7_capture', 'cp7_policy'):
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                               "where n.nspname='erp'and c.relkind in('r','p')and "
                               "has_table_privilege(%s,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",
                               (role,)).fetchone()[0], ('OW16_NATIVE_DML', role)
    return dict(stage='OW16_EXACT_SOURCE_PRIVATE_FACTORY_POLICY_AND_READ_ONLY_NATIVE_STATUS',
                source_sha256=sha256(PATH.read_bytes()).hexdigest(), private_functions=7, public_rpcs=list(PUBLIC),
                default_installer_changed=False, OW16_complete=False, production_go=False)
