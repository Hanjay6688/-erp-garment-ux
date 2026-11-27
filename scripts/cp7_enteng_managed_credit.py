"""Managed PostgreSQL ownership and request identity for the OW04 installer."""

from hashlib import sha256

from psycopg import sql
from psycopg.pq import TransactionStatus

import cp7_enteng_managed_identity as identity

READER = 'readers/01_current_reader_capability.proposal.sql'
PRECLAIM = 'admission/01_typed_context_and_preclaim.proposal.sql'
EXECUTE = 'admission/02_owning_wrapper.proposal.sql'
CAPABILITIES = 'coordinator/07_capabilities_and_quote.sql'
SETTLEMENT = 'coordinator/08_outer_wrapper.sql'
SQL_PINS = {
    READER: 'a7b70a3610b04916ed5a9756e420ce7be1c990b58c2740bb1aaf9362b4954ece',
    PRECLAIM: '8adcc5c61b277cdda9ab7d93f6e7f0d0d2c3b217f477ea9744ffd46c4e4ce6fc',
    EXECUTE: 'd38458ea75ed82d5ad865f3fa7a04ae0852dd7ed9bdc5a92bc9f6a9931bc05c0',
    CAPABILITIES: 'ef232a4a691aa926c7644bcaa2fc8139d49df12c33c80dbbd7b8217bb29f9711',
    SETTLEMENT: 'a2b66ac9f967786cbec2eed1fa714e41ab153fb7d685c3e19fd062bbc62f2e95',
}
# Expected BYPASSRLS for each role defined by the existing CP7 predecessor.
EXISTING_OWNERS = {
    'cp7_customer_history_read': False,
    'cp7_plan_writer': True,
    'cp7_sales_read': True,
    'cp7_sales_write': False,
}
NEW_OWNERS = ('cp7_credit_visible_read', 'cp7_credit_write')
PROTECTED_SCHEMAS = ('erp', 'public', 'cp7_sales', 'cp7_customer_history')
SETTLEMENT_ROUTINE = 'cp7_credit.return_settlement_command'
VISIBILITY_ROUTINE = 'erp._cp7_current_credit_adjustment_visible(uuid)'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('OW04_MANAGED_SQL_ANCHOR_CHANGED: ' + old)
    return text.replace(old, new)


def private_identity(text, function, calls):
    marker = 'create function ' + function + '('
    if marker not in text:
        marker = 'create or replace function ' + function + '('
    if text.count(marker) != 1:
        raise ValueError('OW04_MANAGED_ROUTINE_CHANGED: ' + function)
    before, tail = text.split(marker, 1)
    body, separator, after = tail.partition('end $$;')
    changed, count = identity.IDENTITY_CALL.subn(
        lambda match: 'cp7_request_context.' + match[1].lower() + '()', body
    )
    if not separator or count != calls:
        raise ValueError('OW04_MANAGED_IDENTITY_CALLS_CHANGED: ' + function)
    return before + marker + changed + separator + after


def transfer_sales_routine(text, name, calls):
    function = 'cp7_sales.' + name
    text = private_identity(text, function, calls)
    create = 'create function ' + function + '('
    transfer = 'alter function ' + function + '(uuid,jsonb,text)owner to cp7_sales_write;'
    text = replace_once(text, create, 'grant create on schema cp7_sales to cp7_sales_write;\n' + create)
    return replace_once(text, transfer, transfer + '\nrevoke create on schema cp7_sales from cp7_sales_write;')


def adapt_sql(name, text):
    if name not in SQL_PINS:
        return text
    if sha256(text.encode()).hexdigest() != SQL_PINS[name]:
        raise ValueError('OW04_MANAGED_SQL_SOURCE_CHANGED: ' + name)
    if name == READER:
        # The three Native RLS policies call the existing ERP identity reader.
        text = replace_once(text, 'grant usage on schema erp,auth to cp7_credit_visible_read;',
                            'grant usage on schema erp to cp7_credit_visible_read;')
        text = replace_once(text, 'erp.current_app_role(),erp.current_app_user_id(),auth.uid(),auth.jwt()',
                            'erp.current_app_role(),erp.current_app_user_id()')
        transfer = 'alter function ' + VISIBILITY_ROUTINE + 'owner to cp7_credit_visible_read;'
        return replace_once(text, transfer, 'grant create on schema erp to cp7_credit_visible_read;\n'
                            + transfer + '\nrevoke create on schema erp from cp7_credit_visible_read;')
    if name == PRECLAIM:
        return transfer_sales_routine(text, 'preclaim_credit_return', 2)
    if name == EXECUTE:
        text = transfer_sales_routine(text, 'execute_preclaimed_credit_return', 1)
        return private_identity(text, SETTLEMENT_ROUTINE, 6)
    if name == CAPABILITIES:
        table = 'alter table cp7_credit.return_requests owner to cp7_credit_write;'
        command = 'alter function ' + SETTLEMENT_ROUTINE + '(jsonb,uuid,text)owner to cp7_credit_write;'
        text = replace_once(text, table, 'grant create on schema cp7_credit to cp7_credit_write;\n' + table)
        text = replace_once(text, command, command + '\nrevoke create on schema cp7_credit from cp7_credit_write;')
        text = replace_once(text, 'grant usage on schema cp7_credit,cp7_sales,auth to cp7_credit_write;',
                            'grant usage on schema cp7_credit,cp7_sales,cp7_request_context to cp7_credit_write;')
        return replace_once(text, 'grant execute on function auth.uid(),auth.jwt()to cp7_credit_write;',
                            'grant execute on function cp7_request_context.uid(),cp7_request_context.jwt()to cp7_credit_write;')
    return private_identity(text, SETTLEMENT_ROUTINE, 6)


def installer_memberships(cur):
    return set(cur.execute("""
        select roleid::regrole::text,grantor::regrole::text,admin_option,inherit_option,set_option
          from pg_auth_members where member='postgres'::regrole
    """).fetchall())


def protected_acl(cur):
    return set(cur.execute("""
        select n.nspname,a.grantor::regrole::text,a.grantee::regrole::text,a.privilege_type,a.is_grantable
          from pg_namespace n cross join lateral aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a
         where n.nspname=any(%s)
    """, (list(PROTECTED_SCHEMAS),)).fetchall())


def verify_closed(cur):
    roles = sorted((*EXISTING_OWNERS, *NEW_OWNERS))
    exposed = cur.execute("""
        select r.rolname
          from pg_roles r
         where r.rolname=any(%s) and (
            pg_has_role('postgres',r.oid,'USAGE') or pg_has_role('postgres',r.oid,'SET')
            or exists (select from unnest(%s::text[]) caller
                        where pg_has_role(caller,r.oid,'USAGE') or pg_has_role(caller,r.oid,'SET')))
    """, (roles, list(identity.CALLER_ROLES))).fetchall()
    if exposed:
        raise ValueError('OW04_MANAGED_OWNERSHIP_SCOPE_REMAINS')
    for name in NEW_OWNERS:
        state = cur.execute("""
            select not (rolcanlogin or rolinherit or rolsuper or rolcreaterole or rolcreatedb
                        or rolreplication or rolbypassrls),
                   not has_schema_privilege(oid,'auth','USAGE'),
                   not has_schema_privilege(oid,'erp','CREATE'),
                   not has_schema_privilege(oid,'public','CREATE'),
                   not has_schema_privilege(oid,'cp7_credit','CREATE')
              from pg_roles where rolname=%s
        """, (name,)).fetchone()
        if state != (True, True, True, True, True):
            raise ValueError('OW04_MANAGED_NEW_OWNER_BOUNDARY_CHANGED: ' + name)
    reader = 'cp7_credit_visible_read'
    for table in ('erp.sales_headers','erp.customers','erp.sales_items'):
        state = cur.execute("""
            select has_table_privilege(%s,%s,'SELECT'),
                   has_table_privilege(%s,%s,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
        """, (reader, table, reader, table)).fetchone()
        if state != (True, False):
            raise ValueError('OW04_MANAGED_NATIVE_RLS_READER_BOUNDARY_CHANGED: ' + table)


class InstallScope:
    """Open only the application owners needed for the approved DDL and close them atomically."""

    def __init__(self, cur):
        if cur.connection.info.transaction_status != TransactionStatus.INTRANS:
            raise ValueError('OW04_MANAGED_EXPLICIT_INSTALL_TRANSACTION_REQUIRED')
        self.cur = cur

    def open(self):
        cur = self.cur
        state = cur.execute("""
            select session_user,current_user,rolsuper,rolcreaterole,rolbypassrls,
                   current_setting('createrole_self_grant')
              from pg_roles where rolname=current_user
        """).fetchone()
        if state[:5] != ('postgres','postgres',False,True,True):
            raise ValueError('OW04_MANAGED_PROJECT_INSTALLER_REQUIRED')
        self.setting = state[5]
        identity.validate_context(cur.connection)
        self.before = installer_memberships(cur)
        self.acl_before = protected_acl(cur)
        for name, bypass_rls in EXISTING_OWNERS.items():
            flags = cur.execute("""
                select not (rolcanlogin or rolsuper or rolcreaterole or rolcreatedb or rolreplication),
                       r.rolbypassrls, pg_has_role(current_user,r.oid,'USAGE'),pg_has_role(current_user,r.oid,'SET')
                  from pg_roles r where rolname=%s
            """, (name,)).fetchone()
            if flags != (True, bypass_rls, False, False) or not any(
                edge[0]==name and edge[2:]==(True,False,False) for edge in self.before
            ):
                raise ValueError('OW04_MANAGED_PREDECESSOR_OWNER_CHANGED: ' + name)
            cur.execute(sql.SQL('grant {} to postgres with inherit true, set true granted by postgres')
                        .format(sql.Identifier(name)))
        if any(cur.execute('select to_regrole(%s) is not null', (name,)).fetchone()[0] for name in NEW_OWNERS):
            raise ValueError('OW04_MANAGED_NEW_OWNER_ALREADY_EXISTS')
        cur.execute("select set_config('createrole_self_grant','set,inherit',true)")

    def close(self):
        cur = self.cur
        current = installer_memberships(cur)
        temporary = {(role,'postgres',False,True,True) for role in (*EXISTING_OWNERS,*NEW_OWNERS)}
        permanent = current - self.before - temporary
        if (current != self.before | temporary | permanent or len(permanent)!=len(NEW_OWNERS)
                or {row[0] for row in permanent}!=set(NEW_OWNERS)
                or any(row[1]=='postgres' or row[2:]!=(True,False,False) for row in permanent)):
            raise ValueError('OW04_MANAGED_UNEXPECTED_INSTALL_MEMBERSHIPS')
        for role, *_ in sorted(temporary):
            cur.execute(sql.SQL('revoke {} from postgres granted by postgres restrict').format(sql.Identifier(role)))
        cur.execute("select set_config('createrole_self_grant',%s,true)", (self.setting,))
        if installer_memberships(cur)!=self.before | permanent:
            raise ValueError('OW04_MANAGED_MEMBERSHIPS_CHANGED_AFTER_CLOSE')
        expected_acl = self.acl_before | {
            ('erp','postgres','cp7_credit_visible_read','USAGE',False),
            ('cp7_sales','cp7_sales_read','cp7_credit_write','USAGE',False),
        }
        if protected_acl(cur)!=expected_acl:
            raise ValueError('OW04_MANAGED_EXISTING_SCHEMA_ACL_CHANGED')
        verify_closed(cur)
        return {'temporary_memberships_removed': len(temporary)}
