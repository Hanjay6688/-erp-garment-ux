"""Exact catalogue support references, never invocation or authority closure."""
from hashlib import sha256
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent


def oid(value,zero=False):
    if(type(value)is not str or not value or not value.isascii()or not value.isdecimal()
            or str(int(value))!=value or not(0 if zero else 1)<=int(value)<=4294967295):
        raise ValueError('DE_DISPATCH_CANONICAL_OID_REQUIRED')
    return value


def validate(groups,schema,original,execution):
    if type(groups)is not dict or set(groups)!=set(schema):
        raise ValueError('DE_ALL_SEVEN_DISPATCH_GROUPS_REQUIRED')
    targets={}
    for name in('routines','types','operators'):
        rows=original[name]['rows'];keys=[oid(str(row['oid']))for row in rows]
        if len(keys)!=len(set(keys)):raise ValueError('DE_DISPATCH_DUPLICATE_ORIGINAL_IDENTITY:'+name)
        targets[name]=set(keys)
    for name,spec in schema.items():
        rows=groups[name]
        if type(rows)is not list:raise ValueError('DE_DISPATCH_ROWS_REQUIRED:'+name)
        keys=[]
        for row in rows:
            if type(row)is not dict or set(row)!=set(spec['fields']):
                raise ValueError('DE_DISPATCH_EXACT_FIELDS_REQUIRED:'+name)
            for field,rule in spec['fields'].items():
                value=row[field]
                if rule['type']=='oid':oid(value,rule['zero'])
                elif rule['type']=='smallint':
                    if type(value)is not int or not 1<=value<=32767:
                        raise ValueError('DE_DISPATCH_POSITIVE_SMALLINT_REQUIRED')
                elif rule['type']=='choice':
                    if type(value)is not str or value not in rule['values']:
                        raise ValueError('DE_DISPATCH_EXACT_CHOICE_REQUIRED')
                else:raise ValueError('DE_DISPATCH_UNKNOWN_SCHEMA_TYPE')
            keys.append(row[spec['identity']])
        if len(keys)!=len(set(keys)):raise ValueError('DE_DISPATCH_DUPLICATE_IDENTITY:'+name)
        targets[name]=set(keys)
    for name,spec in schema.items():
        for row in groups[name]:
            for field,rule in spec['fields'].items():
                target=rule.get('target')
                if target and row[field]!='0' and row[field]not in targets[target]:
                    raise ValueError('DE_DISPATCH_MISSING_TARGET:'+name+':'+field)
    if targets['routine_support_oids']!=targets['routines']:
        raise ValueError('DE_DISPATCH_ALL_ORIGINAL_ROUTINES_REQUIRED')
    aggregates={oid(str(row['oid']))for row in original['routines']['rows']if row['prokind']=='a'}
    if targets['aggregate_support_oids']!=aggregates:
        raise ValueError('DE_DISPATCH_EXACT_AGGREGATE_MEMBERSHIP_REQUIRED')
    families={row['oid']:row for row in groups['operator_family_oids']}
    for name,family,method in(('operator_class_oids','opcfamily','opcmethod'),
                             ('family_operator_oids','amopfamily','amopmethod')):
        for row in groups[name]:
            if row[method]!=families[row[family]]['opfmethod']:
                raise ValueError('DE_DISPATCH_OPERATOR_FAMILY_METHOD_MISMATCH')
    for row in execution['range_execution_oids']:
        if row['rngsubopc']not in targets['operator_class_oids']:
            raise ValueError('DE_DISPATCH_RANGE_OPERATOR_CLASS_MISSING')
    for row in original['relations']['rows']:
        method=oid(str(row['relam']),True)
        if method!='0'and method not in targets['access_method_oids']:
            raise ValueError('DE_DISPATCH_RELATION_ACCESS_METHOD_MISSING')
    return {name:len(rows)for name,rows in groups.items()}


def capture(cur,base):
    if(base['classification']!='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE'
            or cur.connection.autocommit or cur.connection.info.host not in('localhost','127.0.0.1')
            or cur.connection.info.port!=54322):
        raise ValueError('DE_DISPATCH_OWNING_READONLY_SNAPSHOT_REQUIRED')
    identity=(base['database'],base['current_role'],base['session_role'],
        'on','repeatable read',base['snapshot'],'pg_catalog')
    statement=("select pg_catalog.current_database(),current_user::pg_catalog.text,session_user::pg_catalog.text,"
        "pg_catalog.current_setting('transaction_read_only'),pg_catalog.current_setting('transaction_isolation'),"
        "pg_catalog.pg_current_snapshot()::pg_catalog.text,pg_catalog.current_setting('search_path')")
    if tuple(cur.execute(statement).fetchone())!=identity:
        raise ValueError('DE_DISPATCH_SNAPSHOT_CHANGED_BEFORE_READ')
    raw=(HERE/'DISPATCH_OID_QUERIES.json').read_bytes();declaration=json.loads(raw)
    if(declaration['original_27_queries_changed']is not False
            or declaration['original_four_execution_queries_changed']is not False
            or len(declaration['groups'])!=7):
        raise ValueError('DE_SEVEN_ADDITIVE_DISPATCH_QUERIES_REQUIRED')
    groups={name:cur.execute(spec['query']).fetchone()[0]for name,spec in declaration['groups'].items()}
    counts=validate(groups,declaration['groups'],base['groups'],base['execution_oid_supplement']['groups'])
    if tuple(cur.execute(statement).fetchone())!=identity:
        raise ValueError('DE_DISPATCH_SNAPSHOT_CHANGED_AFTER_READ')
    return dict(classification=declaration['classification'],groups=groups,group_counts=counts,
        declaration_sha256=sha256(raw).hexdigest(),
        query_sha256={name:sha256(spec['query'].encode()).hexdigest()for name,spec in declaration['groups'].items()},
        same_original_readonly_snapshot=True,original_27_groups_rewritten=False,
        original_four_execution_queries_rewritten=False,unresolved=declaration['unresolved'],
        routine_execution_observed=False,writer_closure=False,permission_closure=False,
        actual_Native_case_credit=0,production_go=False,independent_acceptance=False)
