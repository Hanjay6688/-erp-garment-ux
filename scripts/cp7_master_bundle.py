"""Owner D15-3 (FABLE-017, ASTRA-C17-04, KNOWN-DAILY-MASTER): daily master data and Mandor work rates from the app.

master.sql: customers, suppliers, laundry vendors, Mandor (with the attendance HPP policy that marks a Special Mandor),
warehouses and locations, fabric (with the benchmark price) and accessories (category with the Mandor accessory price,
and variant) are created, changed and deactivated through one closed facade. Nothing is deleted; a used record keeps its
code; deactivation is refused with the Native stock predicates; Native writers are used where they exist.
rates.sql: Mandor work rates per model x work component with the date they apply from, and the model's work components
(Work BOM), through the Native guards (overlap, used-version immutability) and erp.save_work_bom_edit.
No Native definition changes; table DML only on the master rows listed in verify().
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_master_write', 'cp7_master_read')
SCHEMA = 'cp7_master'
TABLES = ('requests', 'history')
SOURCES = ('master.sql', 'rates.sql')
PUBLIC = {
    'public.erp_cp7_get_master_v1(text,jsonb)': 'cp7_master_read',
    'public.erp_cp7_get_work_rates_v1(jsonb)': 'cp7_master_read',
    'public.erp_cp7_save_master_v1(text,jsonb,uuid)': 'cp7_master_write',
    'public.erp_cp7_save_work_rate_v1(text,jsonb,uuid)': 'cp7_master_write',
}
# name -> (security definer, volatility, TimeZone=UTC)
EXPECTED = {
    'permission': (False, 'i', False), 'access_now': (True, 'v', False), 'immutable': (False, 'v', False),
    'entity': (True, 's', True), 'usage': (True, 's', False), 'used': (True, 's', False), 'deactivate_blockers': (True, 's', False),
    'audit': (True, 's', True), 'rows': (True, 's', False), 'options': (True, 's', False), 'workspace': (True, 'v', True),
    'fields': (False, 'i', False), 'content': (False, 'i', False), 'code_taken': (True, 's', False), 'policy_at': (True, 's', False),
    'save': (True, 'v', True), 'rate_versions': (True, 's', True), 'bom': (True, 's', True), 'bom_at': (True, 's', False),
    'rate_workspace': (True, 'v', True), 'save_rate': (True, 'v', True),
}
ENTRY = {'cp7_master_read': ('workspace', 'rate_workspace'), 'cp7_master_write': ('save', 'save_rate')}
OUTSIDERS = ('anon', 'authenticated', 'service_role', 'cp7_capture')


def extension():
    return '\n'.join((ROOT / 'scripts/cp7-src/master' / name).read_text() for name in SOURCES)


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
    assert cur.execute('select count(*) from pg_trigger where tgrelid=%s::regclass and tgfoid=%s::regprocedure and not tgisinternal',
                       (SCHEMA + '.history', SCHEMA + '.immutable()')).fetchone()[0] == 2
    for signature, owner in PUBLIC.items():
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',
                           (signature,)).fetchone() == (owner, True, 'v', ['search_path=""']), signature
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0], signature
        for who in ('anon', 'service_role', 'cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, signature)).fetchone()[0], (who, signature)
    return dict(closed_private_master_facade=True, no_direct_Native_grants=True, immutable_history=True, Native_definitions_unchanged=True,
                table_DML=['erp.customers', 'erp.suppliers', 'erp.laundry_vendors', 'erp.contractors (contractor_type MANDOR)', 'erp.locations',
                           'erp.contractor_work_rates', 'erp.work_components (insert)', 'erp.work_bom_versions + erp.work_bom_items (first version only)'],
                Native_writers=['erp.save_fabric_master_v2', 'erp.set_fabric_benchmark_price_v2', 'erp.save_accessory_category_v2',
                                'erp.save_accessory_material_v2', 'erp.set_accessory_selling_price_v2', 'erp.set_contractor_hpp_policy_v1',
                                'erp.save_work_bom_edit'],
                no_delete=True, permissions=dict(read='master.<kind>.view', write='OWNER/ADMIN + master.<kind>.manage',
                                                 price='write + master.price.edit_draft'))
