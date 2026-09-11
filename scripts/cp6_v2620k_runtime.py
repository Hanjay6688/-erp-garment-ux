"""Read-only, source-pinned K successor verification for older business suites.

Predecessor capsules remain immutable. Evidence distinguishes their installed
hash from the effective successor hash instead of treating metadata as runtime.
"""
import hashlib
from pathlib import Path
import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620m_runtime as m_runtime

MIGRATION = Path('supabase/migrations/20260911023222_erp_v2_6_20k_cp6_payment_date_conservation.sql')

def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations where version='v2.6.20k'),
      to_regclass('erp.cp6_v2620k_rollback_capsule') is not null""")
    marker, capsule = cur.fetchone()
    if not marker and not capsule:
        return {}
    if not marker or not capsule:
        raise AssertionError('K_MARKER_CAPSULE_MISMATCH')
    data = MIGRATION.read_bytes()
    cur.execute("""select version,encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
      'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
      where name='erp_v2_6_20k_cp6_payment_date_conservation'""")
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != '20260911023222' or rows[0][1] not in {
        hashlib.sha256(data).hexdigest(), hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('K_SOURCE_PLATFORM_MISMATCH')
    successor = m_runtime.verified_successor(cur)
    observations = m_runtime.predecessor_snapshot(cur, 'K', successor)
    return {item['identity']: item for item in observations}

def effective_hash(successor, identity, predecessor):
    item = successor.get(identity)
    if item is None:
        return predecessor
    if predecessor != item['predecessor_sha256']:
        raise AssertionError('K_PREDECESSOR_CHAIN_MISMATCH')
    return item['installed_sha256']

def extend_items(successor, items):
    for item in items:
        if item['identity'] in successor:
            old = item['installed_sha256']
            item['installed_sha256'] = effective_hash(successor, item['identity'], old)
            item['j_installed_sha256'] = old
            item['expected_generation'] = 'K'

def extend_rows(successor, rows):
    return [tuple([r[0], r[1], effective_hash(successor, r[0], r[2]), *r[3:]]) for r in rows]
