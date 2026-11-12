"""Replay the failed preflight with actual catalogue ACL and base actor metadata."""
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID
from zipfile import ZipFile
from zoneinfo import ZoneInfo

from psycopg import sql
from single_postgres import SinglePostgres

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / 'sku-a165-terminal/SKU_43105533441_ORIGINAL_FAILURE.zip'
ACTOR = {
    'OWNER': UUID('00000000-0000-4000-8000-000000007111'),
    'ADMIN': UUID('00000000-0000-4000-8000-000000007112'),
    'STAFF': UUID('00000000-0000-4000-8000-000000007113'),
    'GUDANG': UUID('00000000-0000-4000-8000-000000007116'),
}
LOCATION = UUID('00000000-0000-4000-8000-000000007114')
PRODUCT = UUID('00000000-0000-4000-8000-000000007115')
AUTH_TABLES = ('app_roles', 'app_permissions', 'app_role_permissions', 'app_users')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def catalog_fixture(cur, catalogue, dump, required):
    definitions = dict(catalogue['functions'])
    schemas = dict(catalogue['schemas'])
    relevant_schemas = {sig.split('.')[0] for sig in required}
    roles = {'authenticated', 'anon', 'service_role'}
    for sig in required:
        row = definitions[sig]
        roles.add(row[1])
        roles.update(acl[0] for acl in row[-1])
    for name in sorted(roles - {'postgres', 'PUBLIC', 'pg_database_owner'}):
        cur.execute(sql.SQL('create role {} nologin').format(sql.Identifier(name)))
    for name in sorted(relevant_schemas - {'public'}):
        cur.execute(sql.SQL('create schema {}').format(sql.Identifier(name)))
    for name in sorted(relevant_schemas):
        for grantee, _, privilege, grantable in schemas[name][1]:
            if grantee in roles and privilege == 'USAGE':
                assert grantable is False
                recipient = sql.SQL('public') if grantee == 'PUBLIC' else sql.Identifier(grantee)
                cur.execute(sql.SQL('grant usage on schema {} to {}').format(sql.Identifier(name), recipient))
    for name in AUTH_TABLES:
        ddl = re.search(r'^CREATE TABLE erp\.' + name + r' \(\n.*?\n\);', dump, re.M | re.S)[0]
        cur.execute(ddl)
        copy = re.search(r'^COPY erp\.' + name + r' \([^\n]+\) FROM stdin;\n(.*?)^\\\.$', dump, re.M | re.S)
        if copy[1]:
            with cur.copy(copy[0].splitlines()[0]) as target:
                target.write(copy[1].encode())
    cur.execute('set check_function_bodies = off')
    for sig in sorted(required):
        definition, owner, *rest = definitions[sig]
        cur.execute(definition)
        cur.execute(sql.SQL('alter function {} owner to {}').format(sql.SQL(sig), sql.Identifier(owner)))
        cur.execute(sql.SQL('revoke all on function {} from public').format(sql.SQL(sig)))
        for grantee, _, privilege, grantable in rest[-1]:
            assert privilege == 'EXECUTE' and grantable is False
            recipient = sql.SQL('public') if grantee == 'PUBLIC' else sql.Identifier(grantee)
            cur.execute(sql.SQL('grant execute on function {} to {}').format(sql.SQL(sig), recipient))
    cur.execute('set check_function_bodies = on')
    for role, auth in ACTOR.items():
        cur.execute(
            'insert into erp.app_users (auth_user_id,full_name,role,role_id) '
            'select %s,%s,role_code,id from erp.app_roles where role_code=%s',
            (auth, 'Disposable replay ' + role, role),
        )


def reference_fixture(cur, mapping_keys):
    cur.execute("""
        create table erp.uom_definitions(unit_code text, dimension text, is_active boolean);
        insert into erp.uom_definitions values ('PCS','COUNT',true);
        create table erp.chart_accounts(id int, account_code text, is_active boolean, is_postable boolean, account_type text);
        insert into erp.chart_accounts values (1,'4100',true,true,'REVENUE'),(2,'5100',true,true,'EXPENSE');
        create table erp.accounting_account_mappings(mapping_key text, account_id int);
        create table erp.locations(id uuid, is_active boolean, location_type text);
        create table erp.products(id uuid, is_active boolean, model_id uuid, brand_id uuid, size_id uuid, effective_from timestamptz);
        create table erp.accounting_period_control(singleton_id int, closed_through date);
        insert into erp.accounting_period_control values (1,null);
    """)
    for key in mapping_keys:
        cur.execute('insert into erp.accounting_account_mappings values (%s,1)', (key,))
    cur.execute("insert into erp.locations values (%s,true,'FG_WAREHOUSE')", (LOCATION,))
    cur.execute("insert into erp.products values (%s,true,%s,%s,%s,clock_timestamp()-interval '1 hour')", (PRODUCT,) * 4)


def select_actor(cur, role, db_role='authenticated'):
    cur.execute("select set_config('request.jwt.claims',%s,true)",
                (json.dumps(dict(sub=str(ACTOR.get(role, LOCATION)), role=db_role)),))
    cur.execute(sql.SQL('set local session authorization {}').format(sql.Identifier(db_role)))


def admin(cur):
    cur.execute('set local session authorization postgres')


def capture(cur):
    return tuple(cur.execute(sql.SQL('select to_jsonb(t) from erp.{} t order by to_jsonb(t)::text')
                             .format(sql.Identifier(name))).fetchall() for name in AUTH_TABLES)


def exercise(conn, original, revised, required):
    roles = dict(conversion_and_owner_native='OWNER', accessory_operator='OWNER', sales_owner='OWNER')
    database_roles = {key: 'authenticated' for key in roles}

    def actor(key):
        return lambda cur: select_actor(cur, roles[key], database_roles[key])

    business = SimpleNamespace(
        f=SimpleNamespace(admin=admin, owner=actor('conversion_and_owner_native'),
                          BASE=SimpleNamespace(LOCATION=LOCATION, BASE_PRODUCT=PRODUCT)),
        n=SimpleNamespace(require_local=lambda cur: None, capture=capture,
                          bc=SimpleNamespace(session=actor('accessory_operator'))),
        moving=SimpleNamespace(sales_cmd=SimpleNamespace(auth=SimpleNamespace(actor=lambda cur, _: actor('sales_owner')(cur)))),
    )
    check = revised.retained_money_check(original)
    controls = []
    with conn.cursor() as cur, conn.transaction(force_rollback=True):
        today = cur.execute("select (clock_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        before = capture(cur)
        first = original.check(cur, today, business)
        assert first['errors'] == ['ACTOR_CHECK_REFUSED:' + k for k in roles], first['errors']
        assert all(r['sqlstate'] == '42501' and r['error'] == 'permission denied for function has_permission'
                   for r in first['actors'].values()), first['actors']
        fixed = check(cur, today, business)
        assert fixed['status'] == 'PASS' and not fixed['errors'], fixed['errors']
        assert set(fixed['actors']) == set(first['actors'])
        assert all(r['permission_source'] == 'public.erp_get_my_access_v1()'
                   and tuple(r['database_role']) == ('authenticated', 'authenticated')
                   and r['role'] == 'OWNER' for r in fixed['actors'].values())
        assert capture(cur) == before
        admin_keys = {key for key, in cur.execute("""
            select p.permission_key from erp.app_role_permissions p
            join erp.app_roles r on r.id=p.role_id and r.role_code='ADMIN'
            join erp.app_permissions k on k.permission_key=p.permission_key and k.is_active
        """).fetchall()}
        admin_replay = {}
        for key in roles:
            roles[key] = 'ADMIN'
            alternate = check(cur, today, business)
            expected = ['ACTOR_PERMISSION:' + key + ':' + name
                        for name in original.PERMISSIONS[key] if name not in admin_keys]
            assert alternate['errors'] == expected, (key, alternate['errors'], expected)
            assert alternate['status'] == ('REFUSED' if expected else 'PASS')
            roles[key] = 'OWNER'
            admin_replay[key] = dict(status=alternate['status'], errors=expected)
            controls.append('actual_ADMIN_mapping:' + key)
        for key in roles:
            roles[key] = 'GUDANG'
            refused = check(cur, today, business)
            assert refused['status'] == 'REFUSED'
            assert 'NATIVE_INVOICE_POLICY_AND_INVERSES_REQUIRE_OWNER_ADMIN:' + key in refused['errors']
            assert all(other in refused['actors'] and refused['actors'][other].get('role') == 'OWNER'
                       for other in roles if other != key)
            roles[key] = 'OWNER'
            controls.append('wrong_app_role:' + key)
        roles['accessory_operator'] = 'STAFF'
        assert 'ACTOR_CHECK_REFUSED:accessory_operator' in check(cur, today, business)['errors']
        roles['accessory_operator'] = 'OWNER'
        controls.append('inactive_app_role')
        roles['accessory_operator'] = 'MISSING'
        assert 'ACTOR_CHECK_REFUSED:accessory_operator' in check(cur, today, business)['errors']
        roles['accessory_operator'] = 'OWNER'
        controls.append('missing_app_user')
        database_roles['conversion_and_owner_native'] = 'service_role'
        assert 'ORDINARY_AUTHENTICATED_ACTOR_REQUIRED:conversion_and_owner_native' in check(cur, today, business)['errors']
        database_roles['conversion_and_owner_native'] = 'authenticated'
        controls.append('wrong_database_role')
        perm = 'finance.hpp.manage'
        with conn.transaction(force_rollback=True):
            cur.execute('update erp.app_permissions set is_active=false where permission_key=%s', (perm,))
            refused = check(cur, today, business)
            assert {f'ACTOR_PERMISSION:{key}:{perm}' for key in ('accessory_operator','conversion_and_owner_native')} <= set(refused['errors'])
        controls.append('inactive_required_permission')
        sig = 'erp.post_material_supplier_invoice_v2(uuid,uuid,bigint,text)'
        with conn.transaction(force_rollback=True):
            cur.execute(sql.SQL('revoke execute on function {} from authenticated').format(sql.SQL(sig)))
            assert f'ACTOR_FUNCTION_CAPABILITY:conversion_and_owner_native:{sig}' in check(cur, today, business)['errors']
        controls.append('missing_required_EXECUTE')
        assert capture(cur) == before and cur.execute('select current_user,session_user').fetchone() == ('postgres','postgres')
        return dict(before_errors=first['errors'], sqlstates={k: v['sqlstate'] for k,v in first['actors'].items()},
                    after_status=fixed['status'], actors=fixed['actors'], controls=controls, admin_replay=admin_replay,
                    tested_function_definitions=len(required), fixture_authority_rows_restored=True,
                    native25_business_cases=0, browser_cases=0)


def main():
    bin_dir = Path(sys.argv[1]).resolve()
    original = load('frozen_f167_money', HERE / 'source/f167/native_preflight.py')
    revised = load('current_actor_preflight', HERE / 'candidate/native_preflight.py')
    with ZipFile(ORIGINAL) as z:
        assert z.testzip() is None
        raw = z.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
        catalogue = json.loads(raw)
        dump = z.read('CLONE_install.source-erp.sql').decode()
    required = set(original.REQUIRED_FUNCTIONS) | set(revised.FUNCTIONS) | {
        'erp.has_permission(text)', 'erp.current_app_role()', 'erp.get_my_access_v1()',
        'erp.role_permission_keys(uuid)', 'public.erp_get_my_access_v1()', 'auth.uid()', 'auth.jwt()',
    }
    with SinglePostgres(bin_dir) as conn:
        assert conn.execute("select current_setting('server_version_num')").fetchone() == ('170006',)
        assert conn.execute('select inet_server_addr(),current_database()').fetchone() == (None,'postgres')
        assert conn.execute("select count(*) from pg_namespace where nspname='erp'").fetchone() == (0,)
        with conn.transaction(force_rollback=True), conn.cursor() as cur:
            catalog_fixture(cur, catalogue, dump, required)
            reference_fixture(cur, original.ACCOUNT_MAPPINGS)
            receipt = exercise(conn, original, revised, required)
        assert conn.execute("select count(*) from pg_namespace where nspname='erp'").fetchone() == (0,)
        assert conn.execute("select count(*) from pg_roles where rolname in ('authenticated','anon','service_role')").fetchone() == (0,)
    receipt.update(postgres='17.6', postgres_mode='standalone_without_listener', combined_DB_fixture=False, hosted_database=False,
                   archived_catalogue_sha256=hashlib.sha256(raw).hexdigest(), fixture_role_and_schema_cleanup=True)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
