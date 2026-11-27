"""Verify a reviewed ERP table inventory on a restored PostgreSQL 17 rehearsal copy.

Supply a psycopg connection as managed postgres and a separate read-only witness.
The checker rolls back its view creation and all locks before returning.
No database contents or credentials are read into the inventory.
"""
from collections import defaultdict
from hashlib import sha256
from psycopg import sql

LOCK_SCHEMA = "cp7_global_relation_locks"

TABLES = """
select n.nspname, c.relname, c.relkind::text, c.relpersistence::text,
       pg_get_userbyid(c.relowner), c.relrowsecurity, c.relforcerowsecurity,
       c.relacl::text, has_table_privilege('postgres', c.oid, 'MAINTAIN')
                     or pg_has_role('postgres', c.relowner, 'USAGE') as may_lock
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where c.relkind in ('r','p') and
      (n.nspname='erp' or left(n.nspname,4) in ('cp7_','cp8_'))
order by n.nspname collate "C", c.relname collate "C"
"""
MEMBERSHIPS = """
select roleid, member, grantor, admin_option, inherit_option, set_option
from pg_auth_members order by roleid, member, grantor
"""


def presented_name(row):
    return ".".join(row[:2])


def lock_view(table):
    suffix = sha256(table.encode("utf-8")).hexdigest()[:24]
    return sql.Identifier(LOCK_SCHEMA, "lock_" + suffix)


def check_scope(cursor, reviewed):
    tables = cursor.execute(TABLES).fetchall()
    actual = [presented_name(row) for row in tables]
    if not reviewed or reviewed != sorted(set(reviewed)):
        raise ValueError("The reviewed table list must be nonempty, unique and sorted")
    if set(actual) != set(reviewed):
        missing = sorted(set(reviewed) - set(actual))
        added = sorted(set(actual) - set(reviewed))
        raise ValueError(f"ERP table inventory changed. Missing {missing}. Added {added}.")
    return tables


def make_owner_views(cursor, by_owner):
    schema = sql.Identifier(LOCK_SCHEMA)
    cursor.execute(sql.SQL("create schema {} authorization postgres").format(schema))
    cursor.execute(sql.SQL("revoke all on schema {} from public,anon,authenticated,service_role").format(schema))
    for owner, rows in sorted(by_owner.items()):
        if not owner.startswith("cp7_") or cursor.execute(
            "select rolcanlogin or rolsuper or pg_has_role('postgres',oid,'SET') or pg_has_role('postgres',oid,'USAGE') from pg_roles where rolname=%s",
            (owner,),
        ).fetchone() != (False,):
            raise RuntimeError(f"Unexpected ownership or existing role membership for {owner}")
        role = sql.Identifier(owner)
        cursor.execute(sql.SQL("grant {} to postgres with inherit false, set true granted by postgres").format(role))
        cursor.execute(sql.SQL("grant usage,create on schema {} to {}").format(schema, role))
        cursor.execute(sql.SQL("set local role {}").format(role))
        for row in rows:
            view = lock_view(presented_name(row))
            table = sql.Identifier(row[0], row[1])
            cursor.execute(sql.SQL("create view {} as select count(*) as reserved from only {} where false having false").format(view, table))
            cursor.execute(sql.SQL("revoke all on {} from public,anon,authenticated,service_role").format(view))
            cursor.execute(sql.SQL("grant maintain on {} to postgres").format(view))
        cursor.execute("reset role")
        cursor.execute(sql.SQL("revoke usage,create on schema {} from {}").format(schema, role))
        cursor.execute(sql.SQL("revoke {} from postgres granted by postgres restrict").format(role))


def prove_erp_scope(cursor, witness, reviewed):
    """Use a disposable physical clone. The witness performs read-only queries."""
    with cursor.connection.transaction(force_rollback=True):
        return _observe_managed_scope(cursor, witness, reviewed)


def _observe_managed_scope(cursor, witness, reviewed):
    who = cursor.execute("""select current_user, session_user, current_setting('is_superuser'),
        current_setting('server_version_num')::int / 10000,
        current_setting('transaction_isolation'),to_regnamespace(%s) is null,pg_backend_pid()""", (LOCK_SCHEMA,)).fetchone()
    if who[:6] != ("postgres", "postgres", "off", 17, "read committed", True):
        raise RuntimeError("Expected a fresh managed PostgreSQL 17 rehearsal transaction")
    same_database = cursor.execute("select current_database(),inet_server_addr(),inet_server_port()").fetchone()
    if witness.execute("select current_database(),inet_server_addr(),inet_server_port()").fetchone() != same_database:
        raise RuntimeError("The witness must observe the same database instance")
    if witness.execute("show transaction_read_only").fetchone() != ("on",):
        raise RuntimeError("The witness transaction must be read-only")
    if witness.execute("select pg_backend_pid()").fetchone()[0] == who[6]:
        raise RuntimeError("An independent witness is required")
    tables = check_scope(cursor, reviewed)
    memberships = cursor.execute(MEMBERSHIPS).fetchall()
    by_owner = defaultdict(list)
    for row in tables:
        if not row[8]:
            by_owner[row[4]].append(row)
    make_owner_views(cursor, by_owner)
    if tables != cursor.execute(TABLES).fetchall() or memberships != cursor.execute(MEMBERSHIPS).fetchall():
        raise RuntimeError("Original table authority or role memberships changed")
    for role in ("anon", "authenticated", "service_role"):
        if cursor.execute("select has_schema_privilege(%s,%s,'USAGE')", (role, LOCK_SCHEMA)).fetchone()[0]:
            raise RuntimeError(f"Unexpected access to rehearsal views for {role}")
    for row in tables:
        name = presented_name(row)
        target = sql.Identifier(row[0], row[1])
        if not row[8]:
            target = lock_view(name)
            view = target.as_string(cursor)
            actual = cursor.execute("""select pg_get_userbyid(relowner),pg_relation_is_updatable(oid,false),
                has_table_privilege('postgres',oid,'MAINTAIN'),exists(
                select from aclexplode(coalesce(relacl,acldefault('r',relowner))) a
                where a.grantee not in (relowner,'postgres'::regrole)) from pg_class where oid=%s::regclass""", (view,)).fetchone()
            if actual != (row[4], 0, True, False) or cursor.execute(sql.SQL("select count(*) from {}").format(target)).fetchone() != (0,):
                raise RuntimeError(f"Private rehearsal view failed on {name}")
        cursor.execute(sql.SQL("lock table {} in exclusive mode nowait").format(target))
    seen = set(row[0] for row in witness.execute("""select n.nspname||'.'||c.relname
        from pg_locks l join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace
        where l.pid=%s and l.granted and l.mode='ExclusiveLock' and l.database=(select oid from pg_database where datname=current_database())
        and c.relkind in ('r','p') and (n.nspname='erp' or left(n.nspname,4) in ('cp7_','cp8_'))""", (who[6],)))
    if seen != set(reviewed):
        raise RuntimeError(f"Independent lock evidence differs for {sorted(seen.symmetric_difference(reviewed))}")
    cross = cursor.execute("""select conrelid::regclass::text,confrelid::regclass::text from pg_constraint
        where contype='f' and confrelid=any(%s::regclass[]) and not conrelid=any(%s::regclass[])
        and (confdeltype in ('c','n','d') or confupdtype in ('c','n','d')) order by 1,2""", (reviewed, reviewed)).fetchall()
    if cross:
        raise RuntimeError(f"Uncovered physical cascade destinations {cross}")
    return {"physical_relations": len(seen), "private_relations": sum(map(len, by_owner.values())),
            "private_owners": len(by_owner), "independent_witness": True,
            "unchanged_original_authority": True, "outside_cascade_destinations": len(cross)}
