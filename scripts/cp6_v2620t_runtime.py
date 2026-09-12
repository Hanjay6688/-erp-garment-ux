"""Verify T and historical capsules without weakening rollback admission."""
import hashlib
from pathlib import Path

from psycopg import sql

import cp6_preuse_rollback_maintenance as maintenance


MIGRATION = Path(
    'supabase/migrations/20260912171034_erp_v2_6_20t_cp6_material_adjustment_revaluation.sql'
)


def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations
        where version='v2.6.20t'),
      to_regclass('erp.cp6_v2620t_rollback_capsule') is not null""")
    marker, capsule = cur.fetchone()
    if not marker and not capsule:
        return {}
    if not marker or not capsule:
        raise AssertionError('T_MARKER_CAPSULE_MISMATCH')
    data = MIGRATION.read_bytes()
    cur.execute("""select version,encode(extensions.digest(convert_to(
      array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations
      where name='erp_v2_6_20t_cp6_material_adjustment_revaluation'""")
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != '20260912171034' or rows[0][1] not in {
        hashlib.sha256(data).hexdigest(), hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('T_SOURCE_PLATFORM_MISMATCH')
    observations = maintenance._capsule_snapshot(
        cur.connection, 'T', maintenance.TARGETS['T']
    )
    return {item['identity']: item for item in observations}


def effective_hash(successor, identity, predecessor):
    item = successor.get(identity)
    if item is None:
        return predecessor
    if predecessor != item['predecessor_sha256']:
        raise AssertionError('T_PREDECESSOR_CHAIN_MISMATCH')
    return item['installed_sha256']


def predecessor_snapshot(cur, generation, successor):
    """Read-only historical evidence; never called by rollback admission."""
    if not successor:
        return maintenance._capsule_snapshot(
            cur.connection, generation, maintenance.TARGETS[generation]
        )
    capsule = sql.Identifier(*maintenance.TARGETS[generation]['capsule'].split('.'))
    cur.execute(sql.SQL("""select c.object_regidentity,c.definition_sha256,
      encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex'),
      c.installed_definition_sha256,c.owner_snapshot,c.acl_snapshot,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(p.proowner),case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end
      from {} c left join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
      order by c.object_regidentity""").format(capsule))
    columns = (
        'identity', 'predecessor_sha256', 'predecessor_definition_sha256',
        'installed_sha256', 'owner', 'acl', 'observed_installed_sha256',
        'observed_installed_owner', 'observed_installed_acl',
    )
    rows = [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
    wanted = {x['identity']: x for x in maintenance.TRUSTED_FUNCTIONS[generation]}
    if len(rows) != len(wanted) or {r['identity'] for r in rows} != set(wanted):
        raise AssertionError('T_HISTORICAL_CAPSULE_CARDINALITY_MISMATCH')
    for row in rows:
        expected = wanted[row['identity']]
        if (
            any(row[k] != expected[k] for k in (
                'predecessor_sha256', 'installed_sha256', 'owner', 'acl'
            ))
            or row['predecessor_definition_sha256'] != expected['predecessor_sha256']
            or row['observed_installed_sha256'] != effective_hash(
                successor, row['identity'], expected['installed_sha256']
            )
            or row['observed_installed_owner'] != expected['owner']
            or row['observed_installed_acl'] != expected['acl']
        ):
            raise AssertionError('T_HISTORICAL_CAPSULE_SOURCE_PIN_MISMATCH')
    return rows


def extend_items(successor, items):
    for item in items:
        if item['identity'] in successor:
            old = item['installed_sha256']
            item['installed_sha256'] = effective_hash(
                successor, item['identity'], old
            )
            item['pre_t_installed_sha256'] = old
            item['expected_generation'] = 'T'


def extend_rows(successor, rows):
    return [
        tuple([r[0], r[1], effective_hash(successor, r[0], r[2]), *r[3:]])
        for r in rows
    ]


import cp6_v2620s_runtime as s_runtime

NEW_FUNCTIONS = [{'acl': ['postgres=X/postgres'],
  'identity': 'erp._cp6_material_adjustment_revaluation_state(uuid)',
  'owner': 'postgres',
  'sha256': '47a2c15955a682040d2c0c6b72f2941eaae8467e2b16fa5c4bbc10dff27a3c2e'},
 {'acl': ['postgres=X/postgres'],
  'identity': 'erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)',
  'owner': 'postgres',
  'sha256': '355246b52dc88e5d91643485fe796f24e7975d0629824c5b28c31074469ed7ba'},
 {'acl': ['postgres=X/postgres'],
  'identity': 'erp.guard_material_adjustment_revaluation_fact_v2620t()',
  'owner': 'postgres',
  'sha256': 'c2cc7ddb076f557d0f71df9170b9d02425fc17c2f33e471bd1af48e61729829e'}]
EXTRA_FUNCTIONS = s_runtime.EXTRA_FUNCTIONS + NEW_FUNCTIONS


def verify_extra_objects(cur):
    """Verify every inherited helper plus T's private append-only document facts."""
    s_runtime.verify_extra_objects(cur)
    maintenance._function_snapshot(cur.connection, NEW_FUNCTIONS)
    cur.execute("""select c.relrowsecurity,pg_get_userbyid(c.relowner),
      exists(select 1 from information_schema.role_table_grants g
        where g.table_schema='erp' and g.table_name='material_adjustment_revaluation_facts'
          and g.grantee in('PUBLIC','anon','authenticated','service_role')),
      (select count(*) from pg_trigger t where t.tgrelid=c.oid and not t.tgisinternal
        and t.tgenabled='O'
        and t.tgfoid='erp.guard_material_adjustment_revaluation_fact_v2620t()'::regprocedure
        and t.tgname in('trg_material_adjustment_revaluation_fact_append_only',
          'trg_material_adjustment_revaluation_fact_no_truncate'))
      from pg_class c where c.oid=to_regclass('erp.material_adjustment_revaluation_facts')""")
    if cur.fetchone() != (True, 'postgres', False, 2):
        raise AssertionError('T_ADJUSTMENT_FACT_SECURITY_MISMATCH')
    return len(EXTRA_FUNCTIONS)
