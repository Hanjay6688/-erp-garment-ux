"""Catalog privilege facts for the six P0 functions and two registries.

Use the owning candidate's existing readonly RR cursor. These are PostgreSQL
privileges at this snapshot, not application authorization, RLS decisions,
SET ROLE reachability, post-wait freshness, or writer/phantom exclusion.
"""
from hashlib import sha256
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent


def oid(value):
    if type(value)is not str or not value.isascii()or not value.isdecimal():
        raise ValueError('P0_PRIVILEGE_CANONICAL_OID_REQUIRED')
    if str(int(value))!=value or not 1<=int(value)<=4294967295:
        raise ValueError('P0_PRIVILEGE_CANONICAL_OID_REQUIRED')
    return value


def targets(base,selected):
    if (base.get('database')!='cp6_rollback'or base.get('primary_scheduler_database')is not False
        or base.get('classification')!='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE'
        or not 170000<=int(base['server_version_num'])<180000):
        raise ValueError('P0_PRIVILEGE_OWNING_PG17_CANDIDATE_REQUIRED')
    def index(rows,key):
        result={}
        for row in rows:
            identity=oid(str(row[key]))
            if identity in result:raise ValueError('P0_PRIVILEGE_DUPLICATE_BASE_IDENTITY')
            result[identity]=row
        return result
    roles=index(base['groups']['roles']['rows'],'oid')
    functions=index(selected['functions'].values(),'oid')
    relations=index(selected['relations'].values(),'oid')
    schemas=index(base['groups']['schemas']['rows'],'oid')
    if not roles or len(functions)!=6 or len(relations)!=2:
        raise ValueError('P0_PRIVILEGE_COMPLETE_BASE_IDENTITIES_REQUIRED')
    for rows,owner,namespace in ((functions,'proowner','pronamespace'),(relations,'relowner','relnamespace')):
        for row in rows.values():
            if oid(str(row[owner]))not in roles or oid(str(row[namespace]))not in schemas:
                raise ValueError('P0_PRIVILEGE_OWNER_AND_SCHEMA_ROWS_REQUIRED')
    return roles,functions,relations


def validate(groups,declaration,base,selected):
    roles,functions,relations=targets(base,selected)
    specs=declaration['groups']
    if type(groups)is not dict or set(groups)!=set(specs):
        raise ValueError('P0_PRIVILEGE_FOUR_COMPLETE_GROUPS_REQUIRED')
    keys={}
    for name,spec in specs.items():
        rows=groups[name]
        if type(rows)is not list:raise ValueError('P0_PRIVILEGE_TYPED_ROWS_REQUIRED')
        identities=[]
        for row in rows:
            if type(row)is not dict or set(row)!=set(spec['fields']):
                raise ValueError('P0_PRIVILEGE_EXACT_FIELDS_REQUIRED:'+name)
            for field in spec['oid_fields']:
                if name=='columns'and field=='atttypid'and row.get('attisdropped')is True:
                    if row[field]!='0':raise ValueError('P0_PRIVILEGE_DROPPED_COLUMN_TYPE_REQUIRED')
                else:oid(row[field])
            for field in spec['boolean_fields']:
                if type(row[field])is not bool:raise ValueError('P0_PRIVILEGE_BOOLEAN_FACT_REQUIRED')
            if 'attnum'in row and (type(row['attnum'])is not int or not 1<=row['attnum']<=32767):
                raise ValueError('P0_PRIVILEGE_POSITIVE_COLUMN_NUMBER_REQUIRED')
            if name=='columns':
                if type(row['attname'])is not str or not row['attname']:
                    raise ValueError('P0_PRIVILEGE_COLUMN_NAME_REQUIRED')
                if row['attacl']is not None and (type(row['attacl'])is not list
                    or any(type(acl)is not str for acl in row['attacl'])):
                    raise ValueError('P0_PRIVILEGE_RAW_COLUMN_ACL_REQUIRED')
            if name in ('functions','tables'):
                objects,object_key,namespace=(functions,'function_oid','pronamespace')if name=='functions'else(relations,'relation_oid','relnamespace')
                if row[object_key]not in objects or row['schema_oid']!=str(objects[row[object_key]][namespace]):
                    raise ValueError('P0_PRIVILEGE_EXACT_OBJECT_NAMESPACE_REQUIRED')
            identities.append(tuple(row[k]for k in spec['key']))
        if len(identities)!=len(set(identities)):
            raise ValueError('P0_PRIVILEGE_DUPLICATE_FACT:'+name)
        keys[name]=set(identities)
    if keys['functions']!={(r,f)for r in roles for f in functions}:
        raise ValueError('P0_PRIVILEGE_ALL_ROLES_ALL_FUNCTIONS_REQUIRED')
    if keys['tables']!={(r,t)for r in roles for t in relations}:
        raise ValueError('P0_PRIVILEGE_ALL_ROLES_BOTH_TABLES_REQUIRED')
    expected_columns=set()
    for t,row in relations.items():
        if type(row['relnatts'])is not int or not 1<=row['relnatts']<=32767:
            raise ValueError('P0_PRIVILEGE_PHYSICAL_COLUMN_COUNT_REQUIRED')
        expected_columns.update((t,a)for a in range(1,row['relnatts']+1))
    if keys['columns']!=expected_columns:
        raise ValueError('P0_PRIVILEGE_COMPLETE_PHYSICAL_COLUMN_INVENTORY_REQUIRED')
    live_columns={(row['relation_oid'],row['attnum'])for row in groups['columns']if not row['attisdropped']}
    if keys['column_privileges']!={(r,t,a)for r in roles for t,a in live_columns}:
        raise ValueError('P0_PRIVILEGE_ALL_ROLES_ALL_CAPTURED_COLUMNS_REQUIRED')
    return {name:len(rows)for name,rows in groups.items()}


def capture(cur,base):
    selected=base['P0_dependency_supplement']['selected']
    roles,functions,relations=targets(base,selected)
    if (cur.connection.autocommit or cur.connection.info.host not in ('localhost','127.0.0.1')
        or cur.connection.info.port!=54322):
        raise ValueError('P0_PRIVILEGE_EXISTING_LOCAL_READONLY_CURSOR_REQUIRED')
    identity=(base['database'],base['current_role'],base['session_role'],
        'on','repeatable read',base['snapshot'],'pg_catalog')
    statement=("select pg_catalog.current_database(),current_user::pg_catalog.text,session_user::pg_catalog.text,"
        "pg_catalog.current_setting('transaction_read_only'),pg_catalog.current_setting('transaction_isolation'),"
        "pg_catalog.pg_current_snapshot()::pg_catalog.text,pg_catalog.current_setting('search_path')")
    if tuple(cur.execute(statement).fetchone())!=identity:
        raise ValueError('P0_PRIVILEGE_SNAPSHOT_CHANGED_BEFORE_READ')
    raw=(HERE/'P0_PRIVILEGE_QUERIES.json').read_bytes();declaration=json.loads(raw)
    params={'roles':sorted(roles,key=int),'functions':sorted(functions,key=int),'relations':sorted(relations,key=int)}
    groups={name:cur.execute(spec['query'],tuple(params[k]for k in spec['parameters'])).fetchone()[0]
        for name,spec in declaration['groups'].items()}
    counts=validate(groups,declaration,base,selected)
    if tuple(cur.execute(statement).fetchone())!=identity:
        raise ValueError('P0_PRIVILEGE_SNAPSHOT_CHANGED_AFTER_READ')
    return dict(classification=declaration['classification'],groups=groups,group_counts=counts,
        declaration_sha256=sha256(raw).hexdigest(),
        query_sha256={name:sha256(spec['query'].encode()).hexdigest()for name,spec in declaration['groups'].items()},
        same_original_readonly_snapshot=True,original_27_groups_rewritten=False,
        provider_function_calls=0,unresolved=declaration['unresolved'],
        writer_closure=False,permission_closure=False,lockset_approved=False,
        actual_Native_case_credit=0,production_go=False,independent_acceptance=False)
