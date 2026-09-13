"""Verify X and its independent authorization trust roots without weakening rollback admission."""
import hashlib
from pathlib import Path

from psycopg import sql

import cp6_preuse_rollback_maintenance as maintenance


MIGRATION = Path(
    'supabase/migrations/20260913202948_erp_v2_6_20x_cp6_internal_role_fail_closed.sql'
)


def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations
        where version='v2.6.20x'),
      to_regclass('erp.cp6_v2620x_rollback_capsule') is not null""")
    marker, capsule = cur.fetchone()
    if not marker and not capsule:
        return {}
    if not marker or not capsule:
        raise AssertionError('X_MARKER_CAPSULE_MISMATCH')
    data = MIGRATION.read_bytes()
    cur.execute("""select version,encode(extensions.digest(convert_to(
      array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations
      where name='erp_v2_6_20x_cp6_internal_role_fail_closed'""")
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != '20260913202948' or rows[0][1] not in {
        hashlib.sha256(data).hexdigest(), hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('X_SOURCE_PLATFORM_MISMATCH')
    observations = maintenance._capsule_snapshot(
        cur.connection, 'X', maintenance.TARGETS['X']
    )
    return {item['identity']: item for item in observations}


import cp6_v2620w_runtime as w_runtime

AUTH_HELPERS = [{'identity': 'erp._idempotency_actor_key()', 'sha256': '63f9ecea25c22be59917d9153d6686e1cdf6da5a1cf3ede839287aa08c582a92', 'owner': 'postgres', 'acl': ['postgres=X/postgres']}, {'identity': 'erp.current_app_role()', 'sha256': 'ca1a9e2bb44aa8c5f80911728175f923f82472ca170e68b7c21d759601da4022', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']}, {'identity': 'erp.current_app_user_id()', 'sha256': 'b65a4c13983626e8c7a218a2cb68ca24a809f511b8bf20c1f3aa2116b3fd2a10', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']}, {'identity': 'erp.has_permission(text)', 'sha256': 'a9942661396f6c1f3f535720e806a5431db10a11dc1399787a30af733a882d2b', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']}]
EXTRA_FUNCTIONS = w_runtime.EXTRA_FUNCTIONS + AUTH_HELPERS

def verify_extra_objects(cur):
    w_runtime.verify_extra_objects(cur)
    maintenance._function_snapshot(cur.connection, AUTH_HELPERS)
    return len(EXTRA_FUNCTIONS)
