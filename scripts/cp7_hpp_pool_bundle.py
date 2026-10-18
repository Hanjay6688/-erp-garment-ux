"""R3-04 (Sol KNOWN-R2-POOL-UI S1, Astra ASTRA-C17-07 remainder; owner D16-1): the attendance HPP pool lifecycle facade.

pool.sql: a bounded read (pools newest first, attendance payroll periods, the closed-through date, the Native preview of a
chosen period or its refusal as a plain blocker) and one command (CREATE, ACTIVATE, CANCEL) that writes only through the
accepted Native writers erp.create/activate/cancel_attendance_hpp_pool_v1. The command refuses a period ending on or before
the closed-through date, a changed review token, a missing reason, and anyone but an Owner/Admin holding finance.hpp.view and
finance.hpp.manage (read: finance.hpp.view), and keeps one answer per (actor, request) in an insert-only table. No Native
definition or grant changes; every private function is owned by postgres; uninstall drops both roles' objects.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_hpp_pool_write', 'cp7_hpp_pool_read')
SCHEMA = 'cp7_hpp_pool'
TABLES = ('requests',)
PUBLIC = {
    'public.erp_cp7_get_hpp_pools_v1(integer,integer,date,date)': 'cp7_hpp_pool_read',
    'public.erp_cp7_save_hpp_pool_v1(text,jsonb,uuid)': 'cp7_hpp_pool_write',
}
# name -> (security definer, volatility)
EXPECTED = {
    'immutable': (False, 'v'), 'iso': (False, 's'), 'pool_token': (False, 's'), 'preview_token': (False, 's'),
    'access_now': (True, 'v'), 'preview': (True, 'v'), 'pool_json': (True, 'v'), 'workspace': (True, 'v'), 'command': (True, 'v'),
}
ENTRY = {'cp7_hpp_pool_read': ('workspace',), 'cp7_hpp_pool_write': ('command',)}
TRIGGERS = {('requests_immutable', SCHEMA, 'requests'), ('requests_immutable_truncate', SCHEMA, 'requests')}
OUTSIDERS = ('anon', 'authenticated', 'service_role', 'cp7_capture')
# The accepted Native writers the command calls; they stay closed to the browser role (the facade is the only route it uses).
NATIVE = ('erp.preview_attendance_hpp_pool_v1(date,date)', 'erp.create_attendance_hpp_pool_v1(jsonb,uuid)',
          'erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)', 'erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint)',
          'erp.validate_attendance_hpp_pool_v1(uuid)')
# The CP4 (v2.6.16) owner/admin wrappers of the same writers. They skip this facade's closed-books refusal, review token
# and request table; Astra (ASTRA-R3-01) proved them reachable through the Data API, so R4-01 closes them to it
# (cp7_public_routes_bundle.py: first statement refuses a Data API session; grants unchanged). verify() still reports
# whether `authenticated` can execute them (a database session can; the revoke batch stays CP7C, FABLE-012 / D14-9).
CP4_WRAPPERS = ('public.erp_preview_attendance_hpp_pool_v1(date,date)', 'public.erp_create_attendance_hpp_pool_v1(jsonb,uuid)',
                'public.erp_activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)', 'public.erp_cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint)')
PERMISSIONS = ('finance.hpp.view', 'finance.hpp.manage')
STATUSES = ('DRAFT', 'ACTIVE', 'CANCELLED', 'VOIDED')


def extension():
    return (ROOT / 'scripts/cp7-src/hpp-pool/pool.sql').read_text()


def verify(cur):
    rows = cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig "
                       "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s", (SCHEMA,)).fetchall()
    assert {r[1] for r in rows} == set(EXPECTED), rows
    for sig, name, owner, secdef, vol, config in rows:
        security, volatility = EXPECTED[name]
        assert (owner, secdef, vol, config) == ('postgres', security, volatility, ['search_path=""']), sig
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
        assert not cur.execute("select exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp'"
                               " and has_function_privilege(%s,p.oid,'EXECUTE') and not has_function_privilege('public',p.oid,'EXECUTE'))",
                               (who,)).fetchone()[0], ('CP7_HPP_POOL_ROLE_HAS_ERP_EXECUTE', who)
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
    assert triggers == TRIGGERS, ('CP7_HPP_POOL_TRIGGERS', triggers)
    for signature, owner in PUBLIC.items():
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',
                           (signature,)).fetchone() == (owner, True, 'v', ['search_path=""']), signature
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0], signature
        for who in ('anon', 'service_role', 'cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, signature)).fetchone()[0], (who, signature)
    for signature in NATIVE:
        assert not cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0], ('CP7_HPP_POOL_NATIVE_OPEN', signature)
    # The permission keys the facade checks exist and are active in the Native catalog (v2.6.17).
    assert cur.execute('select count(*) from erp.app_permissions where permission_key=any(%s) and is_active', (list(PERMISSIONS),)).fetchone()[0] == len(PERMISSIONS)
    # The Native status vocabulary the screen words follow (attendance_hpp_pools_status_check, v2.6.14c).
    check = cur.execute("select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.attendance_hpp_pools'::regclass"
                        " and conname='attendance_hpp_pools_status_check'").fetchone()[0]
    assert all("'" + s + "'" in check for s in STATUSES), ('CP7_HPP_POOL_STATUS_VOCABULARY', check)
    cp4_open = [s for s in CP4_WRAPPERS
                if cur.execute("select coalesce(has_function_privilege('authenticated',to_regprocedure(%s),'EXECUTE'),false)", (s,)).fetchone()[0]]
    return dict(closed_private_hpp_pool_facade=True, writes_only_through_native=list(NATIVE[1:4]), owner_admin_with_finance_hpp_manage=True,
                insert_only_requests=True, Native_definitions_unchanged=True, status_vocabulary=list(STATUSES),
                observation_cp4_wrappers_executable_by_authenticated=cp4_open)
