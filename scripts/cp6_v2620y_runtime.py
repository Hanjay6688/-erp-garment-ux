"""Verify Y and historical capsules without weakening rollback admission."""
import hashlib
from pathlib import Path

from psycopg import sql

import cp6_preuse_rollback_maintenance as maintenance


MIGRATION = Path(
    'supabase/migrations/20260914043146_erp_v2_6_20y_cp6_cash_business_dates.sql'
)


def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations
        where version='v2.6.20y'),
      to_regclass('erp.cp6_v2620y_rollback_capsule') is not null""")
    marker, capsule = cur.fetchone()
    if not marker and not capsule:
        return {}
    if not marker or not capsule:
        raise AssertionError('Y_MARKER_CAPSULE_MISMATCH')
    data = MIGRATION.read_bytes()
    cur.execute("""select version,encode(extensions.digest(convert_to(
      array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations
      where name='erp_v2_6_20y_cp6_cash_business_dates'""")
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != '20260914043146' or rows[0][1] not in {
        hashlib.sha256(data).hexdigest(), hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('Y_SOURCE_PLATFORM_MISMATCH')
    import cp6_v2620x_runtime as x_runtime
    x_runtime.verified_successor(cur)
    observations = maintenance._capsule_snapshot(
        cur.connection, 'Y', maintenance.TARGETS['Y']
    )
    return {item['identity']: item for item in observations}


def effective_hash(successor, identity, predecessor):
    item = successor.get(identity)
    if item is None:
        return predecessor
    if predecessor != item['predecessor_sha256']:
        raise AssertionError('Y_PREDECESSOR_CHAIN_MISMATCH')
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
        raise AssertionError('Y_HISTORICAL_CAPSULE_CARDINALITY_MISMATCH')
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
            raise AssertionError('Y_HISTORICAL_CAPSULE_SOURCE_PIN_MISMATCH')
    return rows


def extend_items(successor, items):
    for item in items:
        if item['identity'] in successor:
            old = item['installed_sha256']
            item['installed_sha256'] = effective_hash(
                successor, item['identity'], old
            )
            item['pre_y_installed_sha256'] = old
            item['expected_generation'] = 'Y'



import cp6_v2620x_runtime as x_runtime


def verify_extra_objects(cur):
    """Y creates no callable object; verify inherited facts and the admitted X guard."""
    x_runtime.verified_successor(cur)
    return x_runtime.verify_extra_objects(cur)
