"""Owner D15-5 (Fable FABLE-011): the official cutover date (WIB) and the server floor for new operational rows.

cutover.sql: the owner sets the official date in the app (immutable history, idempotent per actor and request, refused
after the earliest operational row or the earliest import batch cutover). Until set, nothing changes. Once set, BEFORE
INSERT triggers on erp.journal_entries (economic date), erp.material_stock_movements and erp.fg_stock_movements (WIB date
of physical_at) refuse rows dated before it, except the opening/migration postings and inverses of existing rows; an
import batch may not take a cutover date before it. No Native definition changes; the triggers are dropped with the
schema (role cp7_cutover_read owns it) on uninstall.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_cutover_write', 'cp7_cutover_read')
SCHEMA = 'cp7_cutover'
TABLES = ('control', 'history', 'requests')
PUBLIC = {
    'public.erp_cp7_get_cutover_v1()': 'cp7_cutover_read',
    'public.erp_cp7_set_cutover_v1(jsonb,uuid)': 'cp7_cutover_write',
}
# name -> (security definer, volatility, TimeZone=UTC)
EXPECTED = {
    'immutable': (False, 'v', False), 'exempt': (False, 'i', False), 'floor': (True, 'v', False), 'refuse': (True, 'v', False),
    'guard_journal': (True, 'v', False), 'guard_movement': (True, 'v', False), 'guard_batch': (True, 'v', False),
    'limits': (True, 's', True), 'access_now': (True, 'v', False), 'workspace': (True, 'v', True), 'command': (True, 'v', True),
}
ENTRY = {'cp7_cutover_read': ('workspace',), 'cp7_cutover_write': ('command',)}
TRIGGERS = {('cp7_cutover_journal', 'erp', 'journal_entries'), ('cp7_cutover_material', 'erp', 'material_stock_movements'),
            ('cp7_cutover_fg', 'erp', 'fg_stock_movements'), ('cp7_cutover_batch', 'erp', 'migration_batches'),
            ('immutable_history', SCHEMA, 'history'), ('immutable_history_truncate', SCHEMA, 'history'),
            ('control_kept', SCHEMA, 'control'), ('control_kept_truncate', SCHEMA, 'control')}
OUTSIDERS = ('anon', 'authenticated', 'service_role', 'cp7_capture')


def extension():
    return (ROOT / 'scripts/cp7-src/cutover/cutover.sql').read_text()


def verify(cur):
    rows = cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig "
                       "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s", (SCHEMA,)).fetchall()
    assert {r[1] for r in rows} == set(EXPECTED), rows
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
                               " and c.relkind in('r','p','v') and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",
                               (who,)).fetchone()[0], who
    for table in TABLES:
        relation = SCHEMA + '.' + table
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass', (relation,)).fetchone() == ('postgres', True)
        assert cur.execute("select count(*) from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'"
                           " and pg_get_expr(polwithcheck,polrelid)='false'", (relation,)).fetchone()[0] == 1
        for who in OUTSIDERS + ROLES:
            assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')", (who, relation)).fetchone()[0], (who, relation)
    triggers = set(cur.execute("select t.tgname,tn.nspname,c.relname from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace tn on tn.oid=c.relnamespace"
                               " join pg_proc p on p.oid=t.tgfoid join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and not t.tgisinternal and t.tgenabled='O'",
                               (SCHEMA,)).fetchall())
    assert triggers == TRIGGERS, ('CP7_CUTOVER_TRIGGERS', triggers)
    assert cur.execute('select count(*) from cp7_cutover.control where singleton_id=1').fetchone()[0] == 1
    for signature, owner in PUBLIC.items():
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',
                           (signature,)).fetchone() == (owner, True, 'v', ['search_path=""']), signature
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0], signature
        for who in ('anon', 'service_role', 'cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, signature)).fetchone()[0], (who, signature)
    return dict(closed_private_cutover_facade=True, owner_only_set=True, immutable_history=True, Native_definitions_unchanged=True,
                guarded_tables=['erp.journal_entries (economic_date)', 'erp.material_stock_movements (physical_at WIB)',
                                'erp.fg_stock_movements (physical_at WIB)', 'erp.migration_batches (cutover_at WIB)'],
                inactive_until_set=True)
