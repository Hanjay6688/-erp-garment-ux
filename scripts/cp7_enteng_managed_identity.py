"""Bind reviewed CP7 routines to the Enteng WIP package's private identity functions.

Run from a restored test database after the managed WIP and predecessor SQL.
The command-line rehearsal rolls back. A release transaction may call apply()
to include these changes with its own admission and bookkeeping.
"""

from hashlib import sha256
import json
import re

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus


# Each entry contains the exact input body hash and its owning execution role.
PINS = {
    'cp7_installment.access_now(text)': (
        'cp7_installment_read', '05cd52afa395f33974f24122a1b516d835faa1b70e874579d49fddb515ff9180'),
    'cp7_installment.guard_journal()': (
        'cp7_installment_read', '91808c5f026bd1baf8fefb9a6d4dfc36a9e743288d8f8eefa5b8bd789e723587'),
    'cp7_installment.guard_line()': (
        'cp7_installment_read', 'f53256efab3041cdb8d26694f147717d7788e7cad9bac0aa5d1d4cd8dce7b8a1'),
    'cp7_installment.require_context(uuid)': (
        'cp7_installment_read', '3e1c27f5ef6a186d521470f4a6088cd00188f9f3a6a09e1d48b5d2472c0c6fe9'),
    'cp7_misc.access_now()': (
        'cp7_misc_read', 'b7f9874d04b701b2c406872e76c0fc3d5bfd24c3363bd939c7b2eedab747f944'),
    'cp7_reminder_native.accessory_target_now(uuid,text,text,integer)': (
        'cp7_capture', '6700d84d973b2f34340e945fde0fa3492579dfe74004023683106aa04f337c15'),
    'cp7_reminder_native.original_authority(uuid)': (
        'cp7_capture', '0d343625101adf679ed628d8d08bac3ed26fd4200f8ff8e5f5723e939c24c643'),
    'cp7_reminder_native.payable_source()': (
        'cp7_payable_read', '0d83d5f99cfb61c9cb2fd5ac15fcc4096b01979bfab162fa939b3bea61e14e99'),
    'cp7_sales.access_now()': (
        'cp7_sales_read', '8f34859038b30b954d47a43700693b038de3062a6e096d3030ab647ac8fd573f'),
    'cp7_sales.command(text,jsonb,uuid,text)': (
        'cp7_sales_write', 'e19d02f1abaa18e7b5b7732a16ef7ea74d5c9692119f094b327395d1464fa454'),
    'cp7_sales.command_access(text)': (
        'cp7_sales_read', '6084394a7621a2161876fcd66691afd321a141842020d7d3826055a7d3ee85cc'),
    'cp7_sales.command_allowed(text)': (
        'cp7_sales_read', 'e739e6ef7fe20b36043d8d1f4bae0c82c0d633174e1990474591f2556073ffed'),
    'cp7_stock_formula.access_now(boolean)': (
        'cp7_capture', '4e491e0df691be7370b91d9e0010c6fa779770a41d79e9267c4fbf1a788b8398'),
    'cp7_stock_formula.material_access_now(text,boolean)': (
        'cp7_capture', 'fe2ac8a5fb711ebb86708ea325f706d057c6e5a12c51e10e5f26e3b294023c00'),
    'cp7_stock_formula.save_manual(jsonb,uuid)': (
        'cp7_capture', '942d24cd06a8b03e7aa6db04d5b8379ebf1e3e09ec40d7fecb36cc80b996221b'),
    'cp7_stock_formula.save_material(jsonb,uuid)': (
        'cp7_capture', 'e176a76f8e0c27da6cc502174c212a2c0b690f83da0bcd6286f7b1da900211f7'),
    'cp7_stock_formula.save_settings(jsonb,uuid)': (
        'cp7_capture', '5216f1ab6a2a9e12eca60f6e415cb18947ae6104e3ecb8625678100eb17d546f'),
}
INVOKERS = {
    'cp7_sales.access_now()',
    'cp7_sales.command(text,jsonb,uuid,text)',
    'cp7_sales.command_allowed(text)',
}
CALLER_ROLES = ('anon', 'authenticated', 'service_role')
ACCESSORS = {
    'uid': ('uuid', '9ab5ea099e74ec09e83b1505c51a3647791195aed7c742dcc3f257dfc7d2f300'),
    'jwt': ('jsonb', 'fed2a8ac0349ffaba807c1b574698bfb1348825b8ef5163ad72d8408386f5e3e'),
}
IDENTITY_CALL = re.compile(r'(?<![\w.])auth\.(uid|jwt)\(\)', re.IGNORECASE)
PRIVATE_CALL = re.compile(r'(?<![\w.])cp7_request_context\.(uid|jwt)\(\)', re.IGNORECASE)
METADATA = """
    select oid, proowner, proacl::text, prosecdef, proconfig::text, provolatile, proleakproof
      from pg_proc where oid=to_regprocedure(%s)
"""
ROUTINE = """
    select n.nspname, r.rolname, p.prosecdef, p.prosrc, pg_get_functiondef(p.oid),p.oid
      from pg_proc p join pg_roles r on r.oid=p.proowner
      join pg_namespace n on n.oid=p.pronamespace
      cross join (select %s::text as signature) target
     where n.nspname=split_part(target.signature,'.',1)
       and p.proname=split_part(split_part(target.signature,'.',2),'(',1)
       and n.nspname||'.'||p.proname||'('||replace(oidvectortypes(p.proargtypes),' ','')||')'=target.signature
"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(text):
    return sha256(text.encode('utf-8')).hexdigest()


def validate_context(conn):
    for name, (returns, body_hash) in ACCESSORS.items():
        row = conn.execute("""
            select p.prosrc, not p.prosecdef and p.provolatile='s' and p.pronargs=0
                   and pg_get_userbyid(p.proowner)='postgres'
                   and p.proconfig=array['search_path=""']
                   and p.prorettype::regtype::text=%s
              from pg_proc p where p.oid=to_regprocedure(%s)
        """, (returns, 'cp7_request_context.' + name + '()')).fetchone()
        require(row and row[1] and digest(row[0])==body_hash, 'Private identity function differs: ' + name)
        for role in CALLER_ROLES:
            denied = conn.execute("""
                select not has_schema_privilege(%s,'cp7_request_context','USAGE')
                   and not has_function_privilege(%s,to_regprocedure(%s),'EXECUTE')
            """, (role, role, 'cp7_request_context.' + name + '()')).fetchone()[0]
            require(denied, 'Unexpected direct access to private identity functions: ' + role)


def validate_role(conn, owner):
    role = conn.execute("""
        select not r.rolcanlogin and not r.rolsuper and not r.rolcreaterole and not r.rolcreatedb
           and not exists (select from unnest(%s::text[]) login where pg_has_role(login,r.oid,'SET'))
          from pg_roles r where r.rolname=%s
    """, (list(CALLER_ROLES), owner)).fetchone()
    require(role == (True,), 'Unexpected application role: ' + owner)


def bind_routine(conn, signature, schema, source, changed, ddl):
    before = conn.execute(METADATA, (signature,)).fetchone()
    require(ddl.count(source)==1, 'Could not locate unambiguous function body: ' + signature)
    raw_acl, can_create, can_grant = conn.execute("""
        select nspacl::text, has_schema_privilege(current_user,oid,'CREATE'),
               has_schema_privilege(current_user,oid,'CREATE WITH GRANT OPTION')
          from pg_namespace where nspname=%s
    """, (schema,)).fetchone()
    if not can_create:
        require(can_grant, 'Installer cannot create in application schema ' + schema)
        conn.execute(sql.SQL('grant create on schema {} to postgres').format(sql.Identifier(schema)))
    conn.execute(ddl.replace(source, changed))
    if not can_create:
        conn.execute(sql.SQL('revoke create on schema {} from postgres').format(sql.Identifier(schema)))
    actual_acl = conn.execute('select nspacl::text from pg_namespace where nspname=%s', (schema,)).fetchone()[0]
    require(raw_acl == actual_acl, 'Schema ACL changed in ' + schema)
    require(before == conn.execute(METADATA, (signature,)).fetchone(), 'Metadata changed: ' + signature)


def apply(conn):
    require(conn.info.transaction_status==TransactionStatus.INTRANS, 'An explicit release transaction is required')
    require(conn.execute('select current_user, rolsuper from pg_roles where rolname=current_user').fetchone()
            == ('postgres', False), 'Expected the ordinary postgres project role')
    validate_context(conn)
    for public_name, role in (
        ('public.erp_cp7_save_sale_v1(text,jsonb,uuid,text)', 'cp7_sales_write'),
        ('public.erp_cp7_get_sales_v1(jsonb)', 'cp7_sales_read'),
    ):
        row = conn.execute('select pg_get_userbyid(proowner),prosecdef from pg_proc where oid=to_regprocedure(%s)',
                           (public_name,)).fetchone()
        require(row == (role, True), 'Unexpected sales entry point: ' + public_name)
    changed_count = 0
    for signature, (owner, source_hash) in PINS.items():
        row = conn.execute(ROUTINE, (signature,)).fetchone()
        require(row and row[1:3]==(owner, signature not in INVOKERS), 'Unexpected routine or owner: ' + signature)
        schema, _, _, source, ddl, function_id = row
        require(schema==signature.split('.')[0], 'Unexpected schema: ' + signature)
        validate_role(conn, owner)
        if signature in INVOKERS:
            for role in CALLER_ROLES:
                exposed = conn.execute("""
                    select has_schema_privilege(%s,%s,'USAGE')
                       and has_function_privilege(%s,%s::oid,'EXECUTE')
                """, (role, schema, role, function_id)).fetchone()[0]
                require(not exposed, 'Private invoker reaches operator role: ' + signature)
        original = PRIVATE_CALL.sub(lambda m: 'auth.' + m[1].lower() + '()', source)
        require(digest(original)==source_hash, 'Routine source differs: ' + signature)
        target = IDENTITY_CALL.sub(lambda m: 'cp7_request_context.' + m[1].lower() + '()', original)
        require(source in (original, target) and original!=target, 'Partially changed routine: ' + signature)
        for accessor in sorted(set(IDENTITY_CALL.findall(original))):
            grants = conn.execute("""
                select has_schema_privilege(%s,'cp7_request_context','USAGE'),
                       has_function_privilege(%s,to_regprocedure(%s),'EXECUTE')
            """, (owner, owner, 'cp7_request_context.' + accessor + '()')).fetchone()
            if not grants[0]:
                conn.execute(sql.SQL('grant usage on schema cp7_request_context to {}').format(sql.Identifier(owner)))
            if not grants[1]:
                conn.execute(sql.SQL('grant execute on function cp7_request_context.{}() to {}').format(
                    sql.Identifier(accessor), sql.Identifier(owner)))
        if source==original:
            bind_routine(conn, signature, schema, original, target, ddl)
            changed_count += 1
        require(conn.execute(ROUTINE, (signature,)).fetchone()[3]==target, 'Identity binding differs: ' + signature)
    validate_context(conn)
    return {'qualified_routines': len(PINS), 'changed_routines': changed_count}


if __name__ == '__main__':
    with psycopg.connect() as connection, connection.transaction(force_rollback=True):
        print(json.dumps(apply(connection)))
