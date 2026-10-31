"""Preserve exact regproc references beside the unchanged system27 metadata.

JSON serialization of a regproc can omit its argument signature. Two overloads
can therefore produce the same name. These four catalog-only queries capture
numeric OIDs in the existing readonly snapshot; they never call those routines.
"""
from hashlib import sha256
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent


def oid(value, *, zero=True):
    if (type(value) is not str or not value or not value.isascii()
            or not value.isdecimal() or str(int(value)) != value
            or not (0 if zero else 1) <= int(value) <= 4294967295):
        raise ValueError('DE_EXECUTION_CANONICAL_OID_REQUIRED')
    return value


def validate(groups, schema, original_groups):
    if type(groups) is not dict or set(groups) != set(schema):
        raise ValueError('DE_ALL_FOUR_EXECUTION_OID_GROUPS_REQUIRED')
    def identities(name):
        rows = original_groups[name]['rows']
        values = [oid(str(row['oid']), zero=False) for row in rows]
        if len(set(values)) != len(values):
            raise ValueError('DE_ORIGINAL_METADATA_DUPLICATE_OID:'+name)
        return set(values)
    routines = identities('routines');types = identities('types')
    languages = identities('languages')
    counts = {}
    for name, spec in schema.items():
        rows = groups[name]
        if type(rows) is not list:
            raise ValueError('DE_EXECUTION_METADATA_ROWS_REQUIRED:'+name)
        keys = []
        for row in rows:
            if type(row) is not dict or set(row) != set(spec['fields']):
                raise ValueError('DE_EXECUTION_METADATA_EXACT_FIELDS_REQUIRED:'+name)
            for field, value in row.items():
                oid(value, zero=field != spec['identity'])
            keys.append(row[spec['identity']])
            for field in spec['routine_fields']:
                if row[field] != '0' and row[field] not in routines:
                    raise ValueError('DE_EXECUTION_ROUTINE_IDENTITY_MISSING:'+name+':'+field)
            for field in spec['type_fields']:
                if row[field] not in types:
                    raise ValueError('DE_EXECUTION_TYPE_IDENTITY_MISSING:'+name+':'+field)
            if name == 'transform_execution_oids' and row['trflang'] not in languages:
                raise ValueError('DE_EXECUTION_LANGUAGE_IDENTITY_MISSING')
        if len(keys) != len(set(keys)):
            raise ValueError('DE_EXECUTION_DUPLICATE_IDENTITY:'+name)
        if spec['base_group'] and set(keys) != identities(spec['base_group']):
            raise ValueError('DE_EXECUTION_COMPLETE_ORIGINAL_MEMBERSHIP_REQUIRED:'+name)
        counts[name] = len(rows)
    return counts


def capture(cur, base):
    # Only the owning caller supplies this cursor, after its pending-parent gate.
    if (base['classification'] != 'ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE'
            or cur.connection.autocommit or cur.connection.info.host not in ('localhost','127.0.0.1')
            or cur.connection.info.port != 54322):
        raise ValueError('DE_OWNING_READONLY_SYSTEM_SNAPSHOT_REQUIRED')
    identity = (base['database'],base['current_role'],base['session_role'],
                'on','repeatable read',base['snapshot'],'pg_catalog')
    statement = ("select pg_catalog.current_database(),current_user::pg_catalog.text,session_user::pg_catalog.text,"
                 "pg_catalog.current_setting('transaction_read_only'),pg_catalog.current_setting('transaction_isolation'),"
                 "pg_catalog.pg_current_snapshot()::pg_catalog.text,pg_catalog.current_setting('search_path')")
    if tuple(cur.execute(statement).fetchone()) != identity:
        raise ValueError('DE_EXECUTION_METADATA_SNAPSHOT_CHANGED_BEFORE_READ')
    raw = (HERE/'EXECUTION_OID_QUERIES.json').read_bytes();declaration = json.loads(raw)
    if declaration['original_27_queries_changed'] is not False or len(declaration['groups']) != 4:
        raise ValueError('DE_FOUR_ADDITIVE_EXECUTION_METADATA_QUERIES_REQUIRED')
    groups = {name:cur.execute(row['query']).fetchone()[0] for name,row in declaration['groups'].items()}
    counts = validate(groups,declaration['groups'],base['groups'])
    if tuple(cur.execute(statement).fetchone()) != identity:
        raise ValueError('DE_EXECUTION_METADATA_SNAPSHOT_CHANGED_AFTER_READ')
    return dict(classification=declaration['classification'],groups=groups,group_counts=counts,
        declaration_sha256=sha256(raw).hexdigest(),
        query_sha256={name:sha256(row['query'].encode()).hexdigest() for name,row in declaration['groups'].items()},
        same_original_readonly_snapshot=True,original_27_groups_rewritten=False,
        unresolved=declaration['unresolved'],writer_closure=False,permission_closure=False,
        actual_Native_case_credit=0,production_go=False,independent_acceptance=False)
