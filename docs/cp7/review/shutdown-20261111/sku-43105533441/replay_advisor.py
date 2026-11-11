"""Reproduce the authority comparison with actual PostgreSQL catalogue ACLs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import psycopg
from psycopg import sql


repo = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2])
relative = 'scripts/current-sku-automatic-composite-preparation/advisor_review.py'
old_head = 'd08032a28b9f00d0ee70a6f98c6b7d0f5b770c4a'
revised_head = 'a1652a808f5f9e7a5bcc3fe0ea0feb081075adc3'
assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip() == revised_head
assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=no']).strip()
assert sys.argv[3].isdigit()
spec = importlib.util.spec_from_file_location('advisor_new', repo / relative)
new = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new)
old = ModuleType('advisor_old')
old.__file__ = str(repo / relative)
old_source = new.assembly.git('show', old_head + ':' + relative)
exec(compile(old_source, old.__file__, 'exec', dont_inherit=True), old.__dict__)
expected = new.source()
reader_source = new.assembly.git('show', new.assembly.prepared_sources()[0]['unchanged_money_product']['public_head']
                                 + ':' + new.READER_SOURCE)
assert new.assembly.admission.pin(reader_source) == new.READER_PIN
reader = ModuleType('actual_frozen_moving_reader')
exec(compile(reader_source, new.READER_SOURCE, 'exec', dont_inherit=True), reader.__dict__)
parent = SimpleNamespace(capture=lambda _: {'fixture_parent': 'retained'},
                         require_closed=lambda value: new.assembly.require(
                             value == {'fixture_parent': 'retained'}, 'PARENT_CHANGED'))
old_reviewer = old.compose(parent, old.source())
new_reviewer = new.compose(parent, expected)
names = sorted(expected['tables'])


def identifier(name):
    return sql.Identifier(*name.split('.'))


def rejection(operation):
    try:
        operation()
    except ValueError as error:
        assert str(error).startswith('SKU_ADVISOR_EXACT_PRIVATE_LIVE_AUTHORITY_REQUIRED'), str(error)
        return str(error)
    raise AssertionError('Unsafe authority accepted')


def capture(cur):
    return dict(cur.execute(new.CAPTURE_SQL, (names, list(new.ROLES))).fetchall())


with psycopg.connect(host='127.0.0.1', port=int(sys.argv[3]), dbname='postgres', user='postgres') as conn:
    with conn.cursor() as cur:
        version = cur.execute('select version()').fetchone()[0]
        assert version.startswith('PostgreSQL 17.6')
        for role in (*new.ROLES, 'unexpected_grantee'):
            cur.execute(sql.SQL('create role {} nologin nosuperuser nobypassrls').format(identifier(role)))
        cur.execute('create schema cp7_sku_conversion authorization postgres')
        for name in names:
            table = identifier(name)
            cur.execute(sql.SQL('create table {}(id uuid, private_value text)').format(table))
            cur.execute(sql.SQL('alter table {} enable row level security').format(table))
            for policy, *_ in expected['tables'][name]['policies']:
                cur.execute(sql.SQL('create policy {} on {} as permissive for all to public using(false) with check(false)')
                            .format(identifier(policy), table))
        cur.execute("create function cp7_sku_conversion.position_value_v2(uuid,uuid,text,numeric)"
                    " returns integer language sql as 'select 1'")
        cur.execute('revoke all on function ' + reader.FUNCTION + ' from public')
        old_reviewer.capture(cur)
        before = capture(cur)
        reader.grant(cur)
        first = rejection(lambda: old_reviewer.capture(cur))
        proof = new_reviewer.capture(cur)
        after = capture(cur)
        assert after == proof['SKU']
        for name in names:
            changed = sorted(field for field in before[name] if before[name][field] != after[name][field])
            assert changed == ['nonowner_schema_acl', 'schema_usage']
        for role in (*new.ROLES, 'unexpected_grantee'):
            actual = cur.execute('select has_function_privilege(%s,%s,%s)', (role, reader.FUNCTION, 'EXECUTE')).fetchone()[0]
            assert actual is (role == reader.ROLE)
        snapshots = [dict(name='baseline', authority=after, must_refuse=False)]
        info = identifier(expected['eligible'][0])
        denied_name = next(name for name in names if expected['tables'][name]['policies'])
        deny = identifier(denied_name)
        policy = identifier(expected['tables'][denied_name]['policies'][0][0])
        mutations = [
            ('public_schema_usage', 'grant usage on schema cp7_sku_conversion to public'),
            ('unknown_role_schema_usage', 'grant usage on schema cp7_sku_conversion to unexpected_grantee'),
            ('reader_missing_schema_usage', 'revoke usage on schema cp7_sku_conversion from cp7_fg_read'),
            ('reader_grantable_schema_usage', 'grant usage on schema cp7_sku_conversion to cp7_fg_read with grant option'),
            ('reader_system_column_grant', sql.SQL('grant select(xmin) on {} to cp7_fg_read').format(info)),
            ('unknown_role_table_grant', sql.SQL('grant select on {} to unexpected_grantee').format(info)),
            ('public_column_grant', sql.SQL('grant select(private_value) on {} to public').format(info)),
            ('service_column_grant', sql.SQL('grant select(private_value) on {} to service_role').format(info)),
            ('rls_disabled', sql.SQL('alter table {} disable row level security').format(info)),
            ('force_rls_changed', sql.SQL('alter table {} force row level security').format(info)),
            ('new_allow_policy', sql.SQL('create policy unexpected_allow on {} using(true)').format(info)),
            ('original_deny_policy_changed', sql.SQL('alter policy {} on {} using(true)').format(policy, deny)),
            ('owner_changed', sql.SQL('alter table {} owner to unexpected_grantee').format(info)),
            ('schema_owner_changed', 'alter schema cp7_sku_conversion owner to unexpected_grantee'),
            ('missing_table', sql.SQL('drop table {}').format(info)),
        ]
        mutations.extend((role + '_select', sql.SQL('grant select on {} to {}').format(info, identifier(role)))
                         for role in new.ROLES)
        for name, command in mutations:
            cur.execute('savepoint mutation')
            cur.execute(command)
            authority = capture(cur)
            reason = rejection(lambda: new_reviewer.require_closed(dict(parent=proof['parent'], SKU=authority)))
            snapshots.append(dict(name=name, authority=authority, must_refuse=True, reason=reason))
            cur.execute('rollback to savepoint mutation')
            cur.execute('release savepoint mutation')
            assert capture(cur) == after
    conn.rollback()
    assert conn.execute("select to_regnamespace('cp7_sku_conversion') is null").fetchone()[0]
    assert conn.execute("select count(*) from pg_roles where rolname = any(%s)", (list(new.ROLES),)).fetchone()[0] == 0

raw = (json.dumps(dict(version=version, snapshots=snapshots), indent=2) + '\n').encode()
output.write_bytes(raw)
print(json.dumps(dict(engine=version, base_head=old_head, revised_head=revised_head, old_failure=first, tables=len(names),
                      deny_policies=len(names)-len(expected['eligible']), eligible_infos=len(expected['eligible']),
                      exact_granted_function=reader.FUNCTION, rejected_mutations=len(mutations),
                      current_reviewer='PASS', rollback='PASS', hosted_database_touched=False,
                      observations=dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())), sort_keys=True))
