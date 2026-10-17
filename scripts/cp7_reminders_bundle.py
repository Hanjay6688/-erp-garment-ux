"""R3-03 (owner D16-1): the Reminder menu (admin-reminders) on real data.

manual-reminders/facade.sql: a thin CP7 facade over the accepted Native own-user manual reminders (v2.6.13,
erp.manual_reminders). It checks the access catalog keys settings.reminder.view / settings.reminder.manage (Native checks
only the OWNER/ADMIN/STAFF actor rule) and then calls the Native list and writers with the screen's request id and expected
version. It holds no table and writes no row itself; no Native definition or ACL changes. Not the same thing as
cp7_reminder_bundle.py (attention rows bound to analysis runs). On uninstall `drop owned by cp7_reminders_read` drops the
schema (that role owns it) with the private functions, and the public wrappers go with their owner roles.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_reminders_write', 'cp7_reminders_read')
SCHEMA = 'cp7_reminders'
AUTHENTICATED = 'authenticated'
OUTSIDERS = ('anon', 'authenticated', 'service_role', 'cp7_capture')
PUBLIC = {
    'public.erp_cp7_get_reminders_v1(jsonb)': 'cp7_reminders_read',
    'public.erp_cp7_save_reminder_v1(text,jsonb,uuid,text)': 'cp7_reminders_write',
}
# name -> (security definer, volatility, TimeZone=UTC)
EXPECTED = {
    'access': (True, 's', False), 'native_list': (True, 's', True), 'native_write': (True, 'v', True),
    'workspace': (True, 's', True), 'command': (True, 'v', True),
}
ENTRY = {'cp7_reminders_read': ('workspace',), 'cp7_reminders_write': ('command',)}
# The accepted Native functions the facade calls; they must exist unchanged in signature (definitions are pinned by the probe).
NATIVE = ('public.erp_list_my_reminders_v1(text,integer)', 'public.erp_save_my_reminder_v1(jsonb,uuid,bigint)',
          'public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)', 'public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)')


def extension():
    return (ROOT / 'scripts/cp7-src/manual-reminders/facade.sql').read_text()


def verify(cur):
    for signature in NATIVE:
        assert cur.execute('select to_regprocedure(%s) is not null', (signature,)).fetchone()[0], ('CP7_REMINDERS_NATIVE_MISSING', signature)
    rows = cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig "
                       "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s", (SCHEMA,)).fetchall()
    assert {r[1] for r in rows} == set(EXPECTED) and len(rows) == len(EXPECTED), rows
    for sig, name, owner, secdef, vol, config in rows:
        security, volatility, utc = EXPECTED[name]
        assert (owner, secdef, vol, config) == ('postgres', security, volatility, ['search_path=""'] + (['TimeZone=UTC'] if utc else [])), sig
        assert not cur.execute("select has_function_privilege('public',%s,'EXECUTE')", (sig,)).fetchone()[0], ('PUBLIC', sig)
        for who in OUTSIDERS:
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
        for who in ROLES:
            assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0] == (name in ENTRY[who]), (who, sig)
    # No own table, view, sequence or trigger: every write is a Native writer call.
    assert cur.execute("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=%s", (SCHEMA,)).fetchone()[0] == 0
    assert cur.execute("select count(*) from pg_trigger t join pg_proc p on p.oid=t.tgfoid join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",
                       (SCHEMA,)).fetchone()[0] == 0
    assert cur.execute("select pg_get_userbyid(nspowner) from pg_namespace where nspname=%s", (SCHEMA,)).fetchone()[0] == 'cp7_reminders_read'
    for who in OUTSIDERS:
        assert not cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (who, SCHEMA)).fetchone()[0], (who, SCHEMA)
    for who in ROLES:
        assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',
                           (who,)).fetchone() == (False, False, False, False, False, False, False), who
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'"
                               " and c.relkind in('r','p','v','m') and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",
                               (who,)).fetchone()[0], who
        assert cur.execute("select count(*) from pg_auth_members m join pg_roles r on r.oid=m.member where r.rolname=%s", (who,)).fetchone()[0] == 0, who
    for signature, owner in PUBLIC.items():
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig,prolang=(select oid from pg_language where lanname=%s) '
                           'from pg_proc where oid=%s::regprocedure', ('sql', signature)).fetchone() == (owner, True, 'v', ['search_path=""'], True), signature
        assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (AUTHENTICATED, signature)).fetchone()[0], signature
        assert not cur.execute("select has_function_privilege('public',%s,'EXECUTE')", (signature,)).fetchone()[0], signature
        for who in OUTSIDERS:
            if who != AUTHENTICATED:
                assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, signature)).fetchone()[0], (who, signature)
    return dict(closed_private_reminders_facade=True, catalog_keys=['settings.reminder.view', 'settings.reminder.manage'],
                native_writers_only=[s.split('(')[0] for s in NATIVE[1:]], own_tables=0, Native_definitions_unchanged=True)
