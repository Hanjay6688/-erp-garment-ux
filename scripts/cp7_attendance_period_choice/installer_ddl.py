"""Bounded existing-schema CREATE envelope; never persistent authority changes.

The qualified outer installer supplies its existing SET ROLE authority. Function
ownership alone does not permit CREATE OR REPLACE inside another role's schema.
USAGE must already exist. Only two known schema owners may grant temporary
CREATE; exact raw ACLs, actor/session/role and privileges are restored before
any installed state is exposed. Error transactions are rolled back by the
mandatory enclosing owning atomic boundary, as in qualified OW05.
"""
from contextlib import contextmanager
from psycopg.pq import TransactionStatus

SCHEMAS={'cp7_payroll':'cp7_payroll_read','cp7_hpp_pool':'cp7_hpp_pool_read'}
KEYS=('schema','actor','session_actor','role_setting','owner','raw_acl','usage','create',
      'actor_can_set_owner','session_can_set_owner','actor_superuser','session_superuser')
INVENTORY_SQL="""select n.nspname as "schema",current_user as actor,session_user as session_actor,current_setting('role')as role_setting,
 pg_get_userbyid(n.nspowner)as owner,n.nspacl::text as raw_acl,
 has_schema_privilege(current_user,n.oid,'USAGE')as usage,has_schema_privilege(current_user,n.oid,'CREATE')as "create",
 pg_has_role(current_user,n.nspowner,'SET')as actor_can_set_owner,pg_has_role(session_user,n.nspowner,'SET')as session_can_set_owner,
 (select r.rolsuper from pg_roles r where r.rolname=current_user)as actor_superuser,
 (select r.rolsuper from pg_roles r where r.rolname=session_user)as session_superuser
 from pg_namespace n where n.nspname=any(%s::text[])order by n.nspname"""


def inventory(cur):
    return [dict(zip(KEYS,row))for row in cur.execute(INVENTORY_SQL,(sorted(SCHEMAS),)).fetchall()]


def plan_inventory(rows):
    """Pure closed inventory/SQL plan, shared by actual context and local probes."""
    if(len(rows)!=len(SCHEMAS)or {row['schema']for row in rows}!=set(SCHEMAS)
       or any(set(row)!=set(KEYS)for row in rows)):
        raise ValueError('CP7_S03_PRIVATE_SCHEMA_EXACT_INVENTORY_REQUIRED')
    ordered=sorted(rows,key=lambda row:row['schema'])
    sessions={(row['session_actor'],row['role_setting'])for row in ordered}
    if len(sessions)!=1:raise ValueError('CP7_S03_PRIVATE_SCHEMA_INSTALLER_CONTEXT_CHANGED')
    for row in ordered:
        if row['actor']!='postgres'or row['owner']!=SCHEMAS[row['schema']]:
            raise ValueError('CP7_S03_PRIVATE_SCHEMA_INSTALLER_AUTHORITY_CHANGED')
        if not row['session_actor']or row['role_setting']not in('postgres','none'):
            raise ValueError('CP7_S03_PRIVATE_SCHEMA_INSTALLER_CONTEXT_CHANGED')
        if any(type(row[key])is not bool for key in KEYS[6:]):
            raise ValueError('CP7_S03_PRIVATE_SCHEMA_EXACT_BOOLEAN_INVENTORY_REQUIRED')
        if row['usage']is not True:
            raise ValueError('CP7_S03_PRIVATE_SCHEMA_PREEXISTING_USAGE_REQUIRED:'+row['schema'])
        if not row['create']:
            # SET ROLE permission is checked against session_user, not merely
            # current_user. A lawful existing outer SU session must stay valid.
            if not row['session_can_set_owner']:
                raise ValueError('CP7_S03_PRIVATE_SCHEMA_EXISTING_SET_AUTHORITY_REQUIRED:'+row['schema'])
            # GRANT/REVOKE can materialize raw NULL as owner-default nonNULL.
            # Never normalize that state or write pg_catalog to conceal it.
            if row['raw_acl']is None:
                raise ValueError('CP7_S03_PRIVATE_SCHEMA_RAW_NULL_GRANT_NOT_ADMITTED:'+row['schema'])
    needed=[row for row in ordered if not row['create']]
    enter=[];leave=[]
    for row in needed:
        enter.extend([(f"set local role {row['owner']}",()),
                      (f"grant create on schema {row['schema']} to postgres",()),
                      ('set local role postgres',())])
    for row in reversed(needed):
        leave.extend([(f"set local role {row['owner']}",()),
                      (f"revoke create on schema {row['schema']} from postgres",()),
                      ('set local role postgres',())])
    if needed:
        leave.append(("select set_config('role',%s,true)",(ordered[0]['role_setting'],)))
    return dict(before=ordered,temporary_CREATE_schemas=[row['schema']for row in needed],enter=enter,leave=leave)


@contextmanager
def existing_schema_ddl(cur):
    """Must run inside the owning atomic install/undo and as_owner(postgres)."""
    plan=plan_inventory(inventory(cur))
    for statement,args in plan['enter']:cur.execute(statement,args)
    try:
        yield plan
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            for statement,args in plan['leave']:cur.execute(statement,args)
            if inventory(cur)!=plan['before']:
                raise ValueError('CP7_S03_PRIVATE_SCHEMA_EXACT_RAW_AUTHORITY_NOT_RESTORED')
        # In INERROR, cleanup SQL is forbidden. Re-raise the original error and
        # let the enclosing owning atomic rollback restore DDL+ACL+role changes.
