"""Apply the reviewed batch reversal as its existing application owners."""

from hashlib import sha256

from psycopg import sql
from psycopg.pq import TransactionStatus

from cp7_enteng_managed_credit_corrections import temporary_roles
from cp7_enteng_managed_identity import require, validate_role


OWNED_ROUTINES = {
    'cp7_cutting_correction.pickup_snapshot(uuid)': ('postgres','cp7_cutting_read'),
    'cp7_cutting_correction.sewing_snapshot(uuid)': ('postgres','cp7_cutting_read'),
    'cp7_wip.capture_cutting_sources(uuid[],timestamptz)': ('cp7_capture','cp7_capture'),
    'cp7_wip.normalize_cutting(jsonb)': ('cp7_capture','cp7_capture'),
    'cp7_analysis_stage.change_sources()': ('cp7_capture','cp7_capture'),
}
SOURCE_PINS = {
    '__init__.py': '708f111ac13c869cec3c4d3eb30e9bce126ed45bb82def462d18a3ca988e9a29',
    'schema.sql': 'dae2dabdffbcde4d3e500127035f80e5c9a8c28a6b720798d5493b162d320cf6',
    'command.sql': '01010be639fd3c25e6165e618de600106e8dc167f516a9443e1e16582413ad76',
}


def alter_owned(cur, signature, expected_owners, ddl):
    row = cur.execute("""
        select n.nspname,n.nspowner::regrole::text,n.nspacl::text,p.proowner::regrole::text,
               has_schema_privilege(p.proowner,n.oid,'CREATE')
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace
         where p.oid=to_regprocedure(%s)
    """, (signature,)).fetchone()
    require(row and (row[3],row[1]) == expected_owners, 'Unexpected WIP owner for ' + signature)
    namespace, schema_owner, acl, owner, can_create = row
    roles = tuple(sorted({schema_owner, owner} - {'postgres'}))
    for role in roles:
        validate_role(cur.connection, role)
    names = sql.Identifier(namespace), sql.Identifier(owner)
    with temporary_roles(cur, roles):
        if not can_create:
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(schema_owner)))
            cur.execute(sql.SQL('grant create on schema {} to {}').format(*names))
        cur.execute(sql.SQL('set local role {}').format(sql.Identifier(owner)))
        cur.execute(ddl, prepare=False)
        if not can_create:
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(schema_owner)))
            cur.execute(sql.SQL('revoke create on schema {} from {}').format(*names))
        cur.execute('reset role')
    require(cur.execute('select nspacl::text from pg_namespace where nspname=%s', (namespace,)).fetchone() == (acl,),
            'WIP schema authorization changed for ' + signature)


def install(cur, batch):
    """Use the pinned batch package with the same writable transaction boundary."""
    require(cur.connection.info.transaction_status == TransactionStatus.INTRANS,
            'An explicit WIP release transaction is required')
    require(cur.execute('select session_user,current_user,rolsuper from pg_roles where rolname=current_user').fetchone()
            == ('postgres','postgres',False), 'Managed postgres WIP installer required')
    require(batch.VERSION == 'cp8-wip-batch-v1' and len(batch.PATCHES) == 12 and OWNED_ROUTINES.keys() <= batch.PATCHES.keys(),
            'Reviewed WIP operation set changed')
    for name, expected in SOURCE_PINS.items():
        require(sha256((batch.HERE / name).read_bytes()).hexdigest()==expected, 'Reviewed WIP source changed: ' + name)
    with cur.connection.transaction():
        cur.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))', (batch.VERSION,))
        require(not cur.execute('select exists(select 1 from erp.schema_migrations where version=%s)', (batch.VERSION,)).fetchone()[0],
                'WIP batch migration is already recorded')
        original = {signature: batch.definition(cur, signature) for signature in batch.PATCHES}
        targets = {signature: edit(original[signature][0]) for signature, edit in batch.PATCHES.items()}
        for name in ('schema.sql', 'command.sql'):
            cur.execute((batch.HERE / name).read_text(), prepare=False)
        for signature, ddl in targets.items():
            if signature in OWNED_ROUTINES:
                alter_owned(cur, signature, OWNED_ROUTINES[signature], ddl)
            else:
                require(cur.execute('select proowner::regrole::text from pg_proc where oid=to_regprocedure(%s)',
                                    (signature,)).fetchone() == ('postgres',), 'Unexpected WIP application routine owner')
                cur.execute(ddl, prepare=False)
            require(batch.definition(cur, signature) == (ddl, *original[signature][1:]),
                    'WIP routine identity or authorization changed: ' + signature)
        cur.execute('insert into erp.schema_migrations(version,description) values(%s,%s)',
                    (batch.VERSION, 'Reverse and redistribute an unused pickup batch with conserved per-yield quantities'))
    return {signature: sha256(ddl.encode()).hexdigest() for signature, ddl in targets.items()}
