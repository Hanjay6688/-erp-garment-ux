"""Exercise the proposed correction/migration interlock on a disposable Enteng BF clone.

Use a localhost PostgreSQL 17 database named enteng_gate_lab, owned by the
ordinary project role, and pass its DSN in ENTENG_GATE_LAB_DSN. This is a
Writer qualification. The production installer and the Global RPCs have
their own admission and are not modified by this exercise.
"""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import errors, sql


PROFILE = Path(__file__).resolve().with_name("cp7_global_nonpo_envelope")
ABSENT_ON_BF = {
    "cp7_credit.cohorts", "cp7_credit.consumption_events",
    "cp7_credit.return_families", "cp7_note.revisions",
}


def require(value, detail):
    if not value:
        raise RuntimeError(detail)


INVENTORY = """
    WITH expected AS (
        SELECT label, to_regclass(name) AS oid
          FROM (SELECT 'parent' AS label, unnest(%s::text[]) AS name
                 UNION ALL SELECT 'global', unnest(%s::text[])) entries
    ), physical AS (
        SELECT e.label, c.oid, c.relowner
          FROM expected AS e JOIN pg_class AS c ON c.oid=e.oid AND c.relkind IN ('r','p')
    ), owners AS (
        SELECT pg_get_userbyid(relowner) AS owner, count(*) AS relations
          FROM physical GROUP BY relowner
    ), routines AS (
        SELECT to_regprocedure(name) AS routine FROM unnest(%s::text[]) AS names(name)
    ), catalog_tables AS (
        SELECT oid FROM pg_class
         WHERE relnamespace='pg_catalog'::regnamespace AND relkind IN ('r','p')
    )
    SELECT jsonb_build_object(
        'parent_expected', (SELECT count(*) FROM expected WHERE label='parent'),
        'parent_present', (SELECT count(*) FROM physical WHERE label='parent'),
        'global_expected', (SELECT count(*) FROM expected WHERE label='global'),
        'global_present', (SELECT count(*) FROM physical WHERE label='global'),
        'present_relations_with_lock_privilege', (SELECT count(*) FROM physical WHERE
            has_table_privilege(current_user,oid,'UPDATE,DELETE,TRUNCATE,MAINTAIN')),
        'existing_relation_owners', (SELECT jsonb_object_agg(owner,relations) FROM owners),
        'native_routines_expected', (SELECT count(*) FROM routines),
        'native_routines_present', (SELECT count(routine) FROM routines),
        'catalog_tables', (SELECT count(*) FROM catalog_tables),
        'catalog_tables_with_lock_privilege', (SELECT count(*) FROM catalog_tables WHERE
            has_table_privilege(current_user,oid,'UPDATE,DELETE,TRUNCATE,MAINTAIN')),
        'session_is_superuser', (SELECT rolsuper FROM pg_roles WHERE rolname=session_user),
        'can_assume_platform_role', (SELECT pg_has_role(session_user,oid,'SET')
                                       FROM pg_roles WHERE rolname='supabase_admin'))
"""


def profile():
    controls = json.loads((PROFILE / 'SYNTAX_AND_SOURCE_CONTROLS.json').read_bytes())
    plan = json.loads((PROFILE / 'INSTALL_PLAN.json').read_bytes())
    native = json.loads((PROFILE / 'NATIVE_OWNING_REFERENCE.json').read_bytes())
    tables = controls['required_actual_accepted15a_relation_keys']
    require(len(tables) == len(set(tables)) == 42 and len(plan['tables']) == 3
            and len(native['functions']) == 8, "Unexpected audited Global profile")
    return tables, plan['tables'], sorted(native['functions'])


def inventory(dsn):
    with psycopg.connect(dsn) as db:
        db.read_only = True
        return db.execute(INVENTORY, profile()).fetchone()[0]


def admitted_connection(dsn):
    db = psycopg.connect(dsn, autocommit=True)
    try:
        info = db.execute("""
            SELECT inet_server_addr() IN ('127.0.0.1'::inet, '::1'::inet),
                   current_database(), session_user, current_user, r.rolsuper,
                   current_setting('server_version_num')::integer / 10000,
                   current_setting('transaction_isolation')
              FROM pg_roles r WHERE r.rolname = session_user
        """).fetchone()
        require(db.info.host in ('127.0.0.1', '::1') and
                info == (True, 'enteng_gate_lab', 'postgres', 'postgres', False, 17, 'read committed'),
                "Expected the isolated PostgreSQL 17 Enteng test database and ordinary installer")
        return db
    except BaseException:
        db.close()
        raise


def target_tables(db):
    required, _, _ = profile()
    found = db.execute("""
        SELECT q.name, n.nspname, c.relname FROM unnest(%s::text[]) q(name)
          LEFT JOIN pg_class c ON c.oid = to_regclass(q.name) AND c.relkind IN ('r','p')
          LEFT JOIN pg_namespace n ON n.oid = c.relnamespace ORDER BY q.name COLLATE "C"
    """, (required,)).fetchall()
    require({name for name, ns, _ in found if ns is None} == ABSENT_ON_BF,
            "Expected the original BF minimum table set")
    return [(ns, name) for _, ns, name in found if ns is not None]


def verify_blocked(db, operation):
    with db.transaction(force_rollback=True):
        db.execute("SET LOCAL lock_timeout = '400ms'")
        try:
            operation()
        except errors.LockNotAvailable:
            return
        raise RuntimeError("A conflicting operation was admitted")


def check_release(db, release):
    sql_check = sql.SQL("SELECT version FROM {} WHERE id=1 FOR SHARE NOWAIT").format(release)
    row = db.execute(sql_check).fetchone()
    if row != (1,):
        raise ValueError("Stale or unavailable ERP release")


def run(dsn):
    with admitted_connection(dsn) as correction, admitted_connection(dsn) as migration:
        with correction.transaction():
            require(correction.execute("""
                SELECT (SELECT count(*) FROM supabase_migrations.schema_migrations),
                       EXISTS(SELECT FROM erp.schema_migrations WHERE version='v2.6.20bf'),
                       EXISTS(SELECT FROM auth.users), EXISTS(SELECT FROM erp.app_users)
            """).fetchone() == (138, True, False, False), "Expected the restored, unused BF base")
            tables = target_tables(correction)
        schema = sql.Identifier('qualification_' + uuid4().hex)
        release = sql.SQL('{}.release').format(schema)
        with correction.transaction():
            correction.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            correction.execute(sql.SQL("REVOKE ALL ON SCHEMA {} FROM PUBLIC").format(schema))
            correction.execute(sql.SQL("CREATE TABLE {} (id int PRIMARY KEY CHECK(id=1), version int NOT NULL)").format(release))
            correction.execute(sql.SQL("INSERT INTO {} VALUES (1, 1)").format(release))
        try:
            exclusive = sql.SQL('SELECT version FROM {} WHERE id=1 FOR UPDATE NOWAIT').format(release)
            with correction.transaction():
                check_release(correction, release)
                # An ordinary second reader can proceed. An exclusive migration must retry.
                with migration.transaction():
                    check_release(migration, release)
                verify_blocked(migration, lambda: migration.execute(exclusive))
                for names in tables:
                    target = sql.Identifier(*names)
                    correction.execute(sql.SQL('LOCK TABLE {} IN EXCLUSIVE MODE NOWAIT').format(target))
                    # ROW EXCLUSIVE is the table-level lock an INSERT/UPDATE/DELETE takes.
                    verify_blocked(migration, lambda: migration.execute(
                        sql.SQL('LOCK TABLE {} IN ROW EXCLUSIVE MODE NOWAIT').format(target)))
            with migration.transaction():
                migration.execute(exclusive)
                migration.execute(sql.SQL("UPDATE {} SET version=2 WHERE id=1").format(release))
                verify_blocked(correction, lambda: check_release(correction, release))
            with correction.transaction():
                try:
                    check_release(correction, release)
                except ValueError as exc:
                    require(str(exc) == "Stale or unavailable ERP release", "Unexpected refusal")
                else:
                    raise RuntimeError("Old code accepted the new release")
            # Releasing the transaction must restore an ordinary writer's access on every table.
            with migration.transaction():
                for names in tables:
                    migration.execute(sql.SQL('LOCK TABLE {} IN ROW EXCLUSIVE MODE NOWAIT').format(sql.Identifier(*names)))
            return {
                'target': 'local_bf', 'shared_readers': 2, 'migration_during_correction': 'retry',
                'correction_during_migration': 'retry', 'old_release_after_commit': 'refused',
                'existing_erp_relations_locked_and_released': len(tables),
                'missing_parent_relations': sorted(ABSENT_ON_BF),
                'global_installer_or_runtime_admitted': False, 'production_go': False,
            }
        finally:
            with correction.transaction():
                correction.execute(sql.SQL("DROP TABLE {}").format(release))
                correction.execute(sql.SQL("DROP SCHEMA {} RESTRICT").format(schema))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', action='store_true',
                        help='Only read the database capabilities and objects from the audited Global profile')
    args = parser.parse_args()
    if args.inventory:
        result = inventory(os.environ['ENTENG_INVENTORY_DSN'])
    else:
        result = run(os.environ['ENTENG_GATE_LAB_DSN'])
    print(json.dumps(result, indent=2))
