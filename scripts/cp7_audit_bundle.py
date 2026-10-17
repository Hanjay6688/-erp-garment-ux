"""R3-03 (owner D16-1): the read facade of the Audit Trail screen over the Native audit log (erp.audit_logs).

audit.sql: one closed reader, public.erp_cp7_get_audit_trail_v1(jsonb), owned by the NOLOGIN role cp7_audit_read and
executable by authenticated only; its private functions in schema cp7_audit are owned by postgres. Access is the access
catalog's: settings.audit.view to read; the answer's can_export is settings.audit.export. Read-only: no table, no business
DML and no Native definition change; uninstall drops the schema, the public function and the role.
Paging keeps one listing whole while writes commit (snapshot.as_of + keyset). That relies on the Native id sequence handing
out ids in the order inserts start (one sequence, cache 1), which verify() checks on the installed database.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_audit_read',)
SCHEMA = 'cp7_audit'
PUBLIC = {'public.erp_cp7_get_audit_trail_v1(jsonb)': 'cp7_audit_read'}
# name -> (security definer, volatility, TimeZone=UTC)
EXPECTED = {
    'access_now': (True, 's', False), 'object_of': (False, 'i', False), 'value_text': (False, 'i', False),
    'changed_keys': (False, 'i', False), 'fields': (False, 'i', False), 'entry': (False, 's', True), 'workspace': (True, 's', True),
}
ENTRY = {'cp7_audit_read': ('workspace',)}
OUTSIDERS = ('anon', 'authenticated', 'service_role', 'cp7_capture')
# The Native columns the reader uses and the types it accepts.
COLUMNS = {'id': ('bigint', 'integer'), 'entity_type': ('text', 'character varying'), 'entity_id': ('uuid', 'text'),
           'action': ('text', 'character varying'), 'old_data': ('jsonb',), 'new_data': ('jsonb',), 'changed_by': ('uuid',),
           'change_reason': ('text', 'character varying'), 'changed_at': ('timestamp with time zone',)}


def extension():
    return (ROOT / 'scripts/cp7-src/audit/audit.sql').read_text()


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
    # No state of its own: nothing but functions in the schema.
    assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=%s)", (SCHEMA,)).fetchone()[0], 'CP7_AUDIT_HAS_STATE'
    assert cur.execute('select pg_get_userbyid(nspowner) from pg_namespace where nspname=%s', (SCHEMA,)).fetchone()[0] == 'cp7_audit_read'
    for who in OUTSIDERS:
        assert not cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (who, SCHEMA)).fetchone()[0], (who, SCHEMA)
    for who in ROLES:
        assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',
                           (who,)).fetchone() == (False, False, False, False, False, False, False), who
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'"
                               " and c.relkind in('r','p','v','m') and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",
                               (who,)).fetchone()[0], who
        owned = cur.execute('select count(*) from pg_proc where proowner=(select oid from pg_roles where rolname=%s)', (who,)).fetchone()[0]
        assert owned == len([s for s, o in PUBLIC.items() if o == who]), (who, owned)
    for signature, owner in PUBLIC.items():
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',
                           (signature,)).fetchone() == (owner, True, 's', ['search_path=""']), signature
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0], signature
        for who in ('anon', 'service_role', 'cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, signature)).fetchone()[0], (who, signature)
    # The Native log as the reader assumes it: these columns and types, a unique id from one sequence that hands ids out in
    # the order inserts start (cache 1), so a write that starts after a listing's first page takes a higher id than as_of.
    columns = dict(cur.execute("select a.attname,format_type(a.atttypid,null) from pg_attribute a where a.attrelid='erp.audit_logs'::regclass"
                               " and a.attnum>0 and not a.attisdropped").fetchall())
    for name, types in COLUMNS.items():
        assert columns.get(name) in types, ('CP7_AUDIT_NATIVE_COLUMN', name, columns.get(name))
    assert cur.execute("select exists(select 1 from pg_index i join pg_attribute a on a.attrelid=i.indrelid and a.attnum=i.indkey[0]"
                       " where i.indrelid='erp.audit_logs'::regclass and i.indisunique and i.indnkeyatts=1 and a.attname='id')").fetchone()[0], 'CP7_AUDIT_ID_NOT_UNIQUE'
    sequence = cur.execute("select pg_get_serial_sequence('erp.audit_logs','id')").fetchone()[0]
    if sequence is None:
        default = cur.execute("select pg_get_expr(d.adbin,d.adrelid) from pg_attrdef d join pg_attribute a on a.attrelid=d.adrelid and a.attnum=d.adnum"
                              " where d.adrelid='erp.audit_logs'::regclass and a.attname='id'").fetchone()
        assert default and default[0].startswith("nextval('"), ('CP7_AUDIT_ID_NOT_FROM_A_SEQUENCE', default)
        sequence = default[0].split("'")[1]
    assert cur.execute('select seqcache from pg_sequence where seqrelid=%s::regclass', (sequence,)).fetchone()[0] == 1, ('CP7_AUDIT_SEQUENCE_CACHE', sequence)
    return dict(closed_private_audit_reader=True, read_only_no_state=True, Native_definitions_unchanged=True,
                public='erp_cp7_get_audit_trail_v1(jsonb) -> authenticated', access=dict(read='settings.audit.view', export='settings.audit.export'),
                id_sequence=sequence, sequence_cache=1)
