"""Verify Z and historical capsules without weakening rollback admission."""
import hashlib
from pathlib import Path

import cp6_preuse_rollback_maintenance as maintenance


MIGRATION = Path(
    'supabase/migrations/20260914085912_erp_v2_6_20z_cp6_accounting_close_business_date.sql'
)


def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations
        where version='v2.6.20z'),
      to_regclass('erp.cp6_v2620z_rollback_capsule') is not null""")
    marker, capsule = cur.fetchone()
    if not marker and not capsule:
        return {}
    if not marker or not capsule:
        raise AssertionError('Z_MARKER_CAPSULE_MISMATCH')
    data = MIGRATION.read_bytes()
    cur.execute("""select version,encode(extensions.digest(convert_to(
      array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations
      where name='erp_v2_6_20z_cp6_accounting_close_business_date'""")
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != '20260914085912' or rows[0][1] not in {
        hashlib.sha256(data).hexdigest(), hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('Z_SOURCE_PLATFORM_MISMATCH')
    observations = maintenance._capsule_snapshot(
        cur.connection, 'Z', maintenance.TARGETS['Z']
    )
    return {item['identity']: item for item in observations}


ROLLBACK = Path('supabase/rollbacks/20260914085912_erp_v2_6_20z_cp6_accounting_close_business_date.rollback.sql')

def verify_extra_objects(cur):
    import cp6_v2620y_runtime as predecessor
    if len(predecessor.verified_successor(cur)) != 6:
        raise AssertionError('Z_REQUIRES_VERIFIED_Y')
    return predecessor.verify_extra_objects(cur)
