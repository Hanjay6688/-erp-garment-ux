"""Use the private managed request identity for the existing payroll commands."""

from psycopg import sql
from psycopg.pq import TransactionStatus

import cp7_enteng_managed_identity as identity
from cp7_enteng_managed_credit_corrections import function_identity, temporary_roles


PINS = {
    'cp7_payroll.access_now(text)': (
        'cp7_payroll_read', 'cp7_payroll_read', '19b6450b670deda12be40987cc81aa4a6aa52f39a6b651dde6b0e119615ccd11'),
    'cp7_payroll.note_command(text,jsonb,uuid,text)': (
        'cp7_nota_write', 'cp7_payroll_read', '02b5bcd354ed827299aee6b1d44009068e0b38edaaa88f82e8fda9308ad4f6eb'),
    'cp7_payroll.settlement_command(text,jsonb,uuid,text)': (
        'cp7_payroll_write', 'cp7_payroll_read', '3b49dc8f2b03b3c65e216db6658ab9464b3949ab91401d9e1db669a8a39fc86a'),
    'cp7_installment.command(text,jsonb,uuid,text)': (
        'cp7_installment_write', 'cp7_installment_read', '669e1bc02664a25c06ed745b238a9402c0061cc3be3aeb8ccc265fb1df1174cf'),
    'cp7_misc.command(text,jsonb,uuid,text)': (
        'cp7_misc_write', 'cp7_misc_read', '35a551a06d21405f852a2cf7b110fb9c27b2d35af0ad580f82681f7a057af85b'),
    'cp7_attendance.access_now()': (
        'cp7_attendance_read', 'cp7_attendance_read', 'ffed1c93bdf5602ef8199d69cb8af1c029019ebd04cfa2dc90fe7ba95dfa9ea7'),
    'cp7_attendance.attendance_command(text,jsonb,uuid,text)': (
        'cp7_attendance_write', 'cp7_attendance_read', 'aaa23795e894be44d95375ca84e6648971b6c04c8b7aaa116ec85b2cdc775eff'),
    'cp7_attendance.roster_command(text,jsonb,uuid,text)': (
        'cp7_roster_write', 'cp7_attendance_read', '6d444ac1b536cde5daffe38c78ffee9815faf82d9e8ca25ed5cd9c4f061987f2'),
}


def bind(cur, signature, owner, schema_owner, expected_hash):
    current = cur.execute("""
        select p.proowner::regrole::text,p.prosecdef,p.prosrc,pg_get_functiondef(p.oid),
               n.nspname,n.nspowner::regrole::text,n.nspacl::text,
               has_schema_privilege(p.proowner,n.oid,'CREATE'),
               array(select r.rolname from pg_roles r
                      where r.rolname<>'postgres' and has_schema_privilege(r.oid,n.oid,'USAGE')
                            and has_function_privilege(r.oid,p.oid,'EXECUTE') order by r.rolname)
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace
         where p.oid=to_regprocedure(%s)
    """, (signature,)).fetchone()
    identity.require(current is not None, 'Payroll routine missing: ' + signature)
    app_owner, definer, body, ddl, schema, app_schema_owner, acl, can_create, callers = current
    allowed_callers = {owner, 'supabase_admin', 'pg_database_owner'}
    identity.require(app_owner == owner and app_schema_owner == schema_owner and not definer
                     and acl is not None and set(callers) <= allowed_callers
                     and identity.digest(body) == expected_hash and ddl.count(body) == 1,
                     'Payroll routine authority or source changed: ' + signature)
    calls = set(identity.IDENTITY_CALL.findall(body))
    identity.require(calls and calls <= {'uid', 'jwt'}, 'Payroll identity calls changed: ' + signature)
    updated = identity.IDENTITY_CALL.sub(lambda m: 'cp7_request_context.' + m[1] + '()', body)

    with temporary_roles(cur, tuple(sorted({owner, schema_owner}))):
        if not can_create:
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(schema_owner)))
            cur.execute(sql.SQL('grant create on schema {} to {}').format(sql.Identifier(schema), sql.Identifier(owner)))
        cur.execute(sql.SQL('set local role {}').format(sql.Identifier(owner)))
        cur.execute(ddl.replace(body, updated, 1))
        if not can_create:
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(schema_owner)))
            cur.execute(sql.SQL('revoke create on schema {} from {}').format(sql.Identifier(schema), sql.Identifier(owner)))
        cur.execute('reset role')
    identity.require(cur.execute('select nspacl::text from pg_namespace where nspname=%s', (schema,)).fetchone() == (acl,),
                     'Payroll schema ACL changed: ' + schema)
    cur.execute(sql.SQL('grant usage on schema cp7_request_context to {}').format(sql.Identifier(owner)))
    for call in sorted(calls):
        cur.execute(sql.SQL('grant execute on function cp7_request_context.{}() to {}').format(
            sql.Identifier(call), sql.Identifier(owner)))


def apply(cur):
    """Bind existing invokers atomically, retaining their owner, OID and ACL."""
    identity.require(cur.connection.info.transaction_status == TransactionStatus.INTRANS,
                     'An explicit payroll maintenance transaction is required')
    with cur.connection.transaction():
        actor = cur.execute("select session_user,current_user,rolsuper from pg_roles where rolname=current_user").fetchone()
        identity.require(actor == ('postgres', 'postgres', False), 'Managed postgres installer identity required')
        identity.validate_context(cur.connection)
        before = function_identity(cur, PINS)
        for signature, pin in PINS.items():
            bind(cur, signature, *pin)
        identity.validate_context(cur.connection)
        identity.require(function_identity(cur, PINS) == before, 'Existing payroll routine owner, OID or ACL changed')
        return {'updated_payroll_routines': len(before), 'temporary_role_memberships_closed': True}
