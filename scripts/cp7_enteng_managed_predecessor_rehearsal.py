"""Rehearse the CP7 WIP and predecessor SQL on the restored BF project role.

Use the repository root as the working directory. The CLI uses libpq connection
settings and rolls back. apply() is the substep tested on disposable clones.
The remaining CP7 installer, Global gate, and migration history are separate.
"""

from hashlib import sha256
import json

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus
from pglast import split

import cp7_enteng_managed_identity as identity
import cp7_enteng_managed_wip_foundation as wip
import cp7_full_owning_install as original


# Reviewed statement positions in the immutable SQL after the WIP foundation.
# A receiving owner needs CREATE on its schema while ownership is transferred.
SCOPES = {
    ('cp7_attendance', 'cp7_attendance_write'): (
        777, 778, 789, 791,
    ),
    ('cp7_attendance', 'cp7_roster_write'): (
        752, 761,
    ),
    ('cp7_fg', 'cp7_fg_read'): (
        571, 572, 582, 583,
    ),
    ('cp7_fg', 'cp7_fg_write'): (
        498, 501,
    ),
    ('cp7_fg', 'postgres'): (
        567, 568, 578, 579,
    ),
    ('cp7_payroll', 'cp7_nota_write'): (
        622, 623, 624, 625,
    ),
    ('cp7_payroll', 'cp7_payroll_read'): (
        672, 673, 674, 675, 698,
    ),
    ('cp7_payroll', 'cp7_payroll_write'): (
        687, 688, 699,
    ),
    ('cp7_payroll', 'postgres'): (
        618, 619, 620, 621, 633, 634, 635, 636, 637, 638, 639, 641, 642, 643, 666, 667, 668,
        669, 685, 686, 692, 693, 694, 695, 696, 713, 717, 718, 719,
    ),
    ('cp7_plan_native', 'cp7_capture'): (
        3108, 3109, 3110, 3122, 3123, 3178, 3179,
    ),
    ('cp7_profile', 'cp7_capture'): (
        2431,
    ),
    ('cp7_reminder_native', 'cp7_capture'): (
        3637, 3640,
    ),
    ('cp7_sales', 'cp7_sales_write'): (
        842, 843, 855,
    ),
    ('cp7_yield_policy', 'cp7_capture'): (
        3092,
    ),
    ('public', 'cp7_capture'): (
        2274, 2275, 2333, 2334, 2335, 2945,
    ),
    ('public', 'cp7_fg_read'): (
        531, 532,
    ),
    ('public', 'cp7_misc_read'): (
        1418,
    ),
    ('public', 'cp7_misc_write'): (
        1414,
    ),
}
SPLIT_HASH = 'e70cfd4dc3cf1b8f608cdc25c0c75bb374a3309ad9b8f30147324210130245a4'
PRIVILEGES = """
    select nspacl::text, has_schema_privilege(%s,oid,'CREATE'),
           has_schema_privilege(current_user,oid,'CREATE WITH GRANT OPTION'),
           pg_has_role(current_user,nspowner,'USAGE')
      from pg_namespace where nspname=%s
"""


def statements():
    manifest = wip.predecessor_manifest()
    canonical = original.f03.procurement.bundle() + '\n' + original.predecessor_extension()
    tail = canonical[len(wip.cp7_wip_bundle.bundle()):]
    wip.checked(tail, manifest['unchanged_tail_sha256'])
    parts = split(tail)
    fingerprint = sha256()
    for statement in parts:
        body = statement.encode('utf-8')
        fingerprint.update(len(body).to_bytes(8, 'big'))
        fingerprint.update(body)
    if len(parts)!=3838 or fingerprint.hexdigest()!=SPLIT_HASH:
        raise ValueError('Reviewed SQL statement boundaries differ')
    return parts


def execute_scoped(conn, statement, schema, role):
    before = conn.execute(PRIVILEGES, (role, schema)).fetchone()
    if not before or not before[2] or not before[3]:
        raise ValueError('Installer does not control application schema ' + schema)
    if role != 'postgres':
        identity.validate_role(conn, role)
    if before[1]:
        # This specific BF profile had no standing CREATE at any of these sites.
        raise ValueError('Unexpected standing CREATE for ' + role + ' on ' + schema)
    names = sql.Identifier(schema), sql.Identifier(role)
    conn.execute(sql.SQL('grant create on schema {} to {}').format(*names))
    conn.execute(statement)
    conn.execute(sql.SQL('revoke create on schema {} from {}').format(*names))
    if conn.execute(PRIVILEGES, (role, schema)).fetchone()!=before:
        raise ValueError('Schema privileges changed after ownership operation in ' + schema)


ROLE_SET_SHA256 = 'fdffa7ac004450b04982811b35aa4e8dfa7f1451bd8602c2d89bdb9cf4a5b283'


def memberships(conn):
    return set(conn.execute("""
        select roleid::regrole::text, grantor::regrole::text, admin_option, inherit_option, set_option
          from pg_auth_members where member='postgres'::regrole
    """).fetchall())


# The Native internal guard checks only these application context fields. Its
# owner has ordinary database privileges after the installation roles close.
CONTEXT_TABLES = {
    'cp7_material': 'cp7_material_write',
    'cp7_payroll': 'cp7_nota_write',
    'cp7_supplier_return': 'cp7_return_write',
}
CONTEXT_COLUMNS = ('backend_pid','transaction_id','actor','action','permission_key')


def grant_guard_reads(conn):
    row = conn.execute("""
        select prosrc, proowner='postgres'::regrole and prosecdef from pg_proc
         where oid='erp.require_internal()'::regprocedure
    """).fetchone()
    if not row or not row[1] or identity.digest(row[0])!='35396480c31180cb342ec9f995149fa68917d84d0f158a96fa2af7146de064c7':
        raise ValueError('Unexpected Native ERP internal guard')
    columns = sql.SQL(', ').join(map(sql.Identifier, CONTEXT_COLUMNS))
    for schema, owner in CONTEXT_TABLES.items():
        table = sql.Identifier(schema,'execution_context')
        shape = conn.execute("""
            select c.relowner::regrole::text,c.relrowsecurity,
                array(select a.attname::text from pg_attribute a where a.attrelid=c.oid
                      and a.attnum>0 and not a.attisdropped order by a.attnum)
              from pg_class c join pg_namespace n on n.oid=c.relnamespace
             where n.nspname=%s and c.relname='execution_context' and c.relkind='r'
        """, (schema,)).fetchone()
        if shape!=(owner,True,list(CONTEXT_COLUMNS)) or schema+'.execution_context' not in row[0]:
            raise ValueError('Unexpected private ERP context in ' + schema)
        conn.execute(sql.SQL('grant usage on schema {} to postgres').format(sql.Identifier(schema)))
        conn.execute(sql.SQL('grant select ({}) on table {} to postgres').format(columns,table))


def close_installation_roles(conn, before):
    current = memberships(conn)
    added = current - before
    temporary = {r for r in added if r[1:] == ('postgres', False, True, True)}
    admin = {r for r in added if r[1]!='postgres' and r[2:] == (True, False, False)}
    names = sorted(r[0] for r in temporary)
    if (not before <= current or added != temporary | admin or len(admin)!=55 or len(names)!=55
            or names!=sorted(r[0] for r in admin)
            or sha256('\n'.join(names).encode()).hexdigest()!=ROLE_SET_SHA256):
        raise ValueError('Memberships created by the reviewed installation differ')
    for name in names:
        conn.execute(sql.SQL('revoke {} from postgres granted by postgres restrict').format(sql.Identifier(name)))
    if memberships(conn)!=before | admin:
        raise ValueError('Unexpected membership changes after temporary rights were removed')
    remaining = conn.execute("""
        select count(*) from unnest(%s::text[]) r
         where pg_has_role(current_user,r,'USAGE') or pg_has_role(current_user,r,'SET')
    """, (names,)).fetchone()[0]
    if remaining:
        raise ValueError('Installer can still inherit or assume a temporary application role')
    return len(names)


def apply(conn):
    if conn.info.transaction_status!=TransactionStatus.INTRANS:
        raise ValueError('An explicit release transaction is required')
    with conn.transaction():
        state = conn.execute("""
            select current_user, r.rolsuper, (select count(*) from supabase_migrations.schema_migrations),
                   (select version from erp.schema_migrations order by installed_at desc limit 1),
                   to_regnamespace('cp7_request_context') is null, to_regrole('cp7_capture') is null
              from pg_roles r where r.rolname=current_user
        """).fetchone()
        if state!=('postgres', False, 138, 'v2.6.20bf', True, True):
            raise ValueError('This rehearsal starts from the fresh Enteng BF predecessor')
        original_memberships = memberships(conn)
        parts = statements()
        plan = {index: (schema, role) for (schema, role), positions in SCOPES.items() for index in positions}
        if len(plan)!=81 or sum(map(len, SCOPES.values()))!=81:
            raise ValueError('Managed transfer plan is incomplete')
        conn.execute(wip.body(), prepare=False)
        for index, statement in enumerate(parts, start=1):
            if index in plan:
                execute_scoped(conn, statement, *plan[index])
            else:
                conn.execute(statement)
        result = identity.apply(conn)
        grant_guard_reads(conn)
        closed = close_installation_roles(conn, original_memberships)
        return {'statements': len(parts), 'ownership_scopes': len(plan), 'identity': result,
                'temporary_role_memberships_closed': closed,
                'full_cp7_qualified': False}


if __name__ == '__main__':
    with psycopg.connect() as connection, connection.transaction(force_rollback=True):
        print(json.dumps(apply(connection)))
