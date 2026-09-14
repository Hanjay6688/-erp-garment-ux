"""Verify AA and historical capsules without weakening rollback admission."""
import hashlib
from pathlib import Path

import cp6_preuse_rollback_maintenance as maintenance


MIGRATION = Path(
    'supabase/migrations/20260914163608_erp_v2_6_20aa_cp6_material_cost_business_day.sql'
)


def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations
        where version='v2.6.20aa'),
      to_regclass('erp.cp6_v2620aa_rollback_capsule') is not null""")
    marker, capsule = cur.fetchone()
    if not marker and not capsule:
        return {}
    if not marker or not capsule:
        raise AssertionError('AA_MARKER_CAPSULE_MISMATCH')
    data = MIGRATION.read_bytes()
    cur.execute("""select version,encode(extensions.digest(convert_to(
      array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations
      where name='erp_v2_6_20aa_cp6_material_cost_business_day'""")
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != '20260914163608' or rows[0][1] not in {
        hashlib.sha256(data).hexdigest(), hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('AA_SOURCE_PLATFORM_MISMATCH')
    observations = maintenance._capsule_snapshot(
        cur.connection, 'AA', maintenance.TARGETS['AA']
    )
    return {item['identity']: item for item in observations}


ROLLBACK = Path('supabase/rollbacks/20260914163608_erp_v2_6_20aa_cp6_material_cost_business_day.rollback.sql')

def verify_extra_objects(cur):
    import cp6_v2620z_runtime as predecessor
    if len(predecessor.verified_successor(cur)) != 1:
        raise AssertionError('AA_REQUIRES_VERIFIED_Z')
    return predecessor.verify_extra_objects(cur)
