"""Missing system/cron metadata, only on the caller's disposable readonly snapshot.

This is not an installer, executor, lockset, writer closure or acceptance gate.
It never opens a connection or runs a provider routine. No hosted operation.
"""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent


def queries():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    for name,pin in source['files'].items():
        path=HERE/name;raw=path.read_bytes()
        if path.is_symlink()or len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('GLOBAL_SYSTEM_CRON_PROFILE_SOURCE_CHANGED:'+name)
    declaration=json.loads((HERE/'QUERIES.json').read_bytes())
    if(declaration['collect_all_namespaces']is not True or declaration['Native_cases']!=0
       or declaration['raw_cron_commands_collected']is not False
       or declaration['foreign_user_mappings_collected']is not False):
        raise ValueError('GLOBAL_SYSTEM_CRON_EXACT_METADATA_ONLY_CONTRACT_REQUIRED')
    return declaration['queries']


def _capture(cur,expected_database):
    if cur.connection.autocommit:
        raise ValueError('GLOBAL_SYSTEM_CRON_ONE_EXISTING_READONLY_TRANSACTION_REQUIRED')
    query=queries()
    info=cur.connection.info
    if info.host not in('127.0.0.1','localhost')or info.port!=54322:
        raise ValueError('GLOBAL_SYSTEM_CRON_LOCAL_DISPOSABLE_ONLY')
    if cur.execute("select pg_catalog.current_setting('search_path')").fetchone()[0]!='pg_catalog':
        raise ValueError('GLOBAL_SYSTEM_CRON_CALLER_MUST_SET_LOCAL_SEARCH_PATH_PG_CATALOG')
    row=cur.execute("select pg_catalog.current_database(),current_user::pg_catalog.text,session_user::pg_catalog.text,"
        "pg_catalog.current_setting('transaction_read_only'),pg_catalog.current_setting('transaction_isolation'),"
        "pg_catalog.current_setting('server_version_num'),pg_catalog.version(),pg_catalog.pg_current_snapshot()::pg_catalog.text,"
        "pg_catalog.current_setting('search_path')").fetchone()
    if(row[0]!=expected_database or row[1]not in('postgres','supabase_admin')
       or row[2]not in('postgres','supabase_admin')or row[3]!='on'or row[4]!='repeatable read'):
        raise ValueError('GLOBAL_SYSTEM_CRON_EXISTING_READONLY_REPEATABLE_ADMINISTRATIVE_SNAPSHOT_REQUIRED')
    result=dict(classification='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE',
        database=row[0],current_role=row[1],session_role=row[2],server_version_num=row[5],
        server_version=row[6],snapshot=row[7],search_path=row[8],groups={},Native_cases=0,
        primary_scheduler_database=expected_database=='postgres',
        separate_database_snapshots_are_not_atomic_writer_closure=True,
        writer_closure=False,permission_closure=False,lockset_approved=False,
        production_go=False,independent_acceptance=False)
    cron=cur.execute("select pg_catalog.to_regclass('cron.job')is not null").fetchone()[0]
    for name,sql in query.items():
        if name=='cron_jobs'and not cron:
            result['groups'][name]=dict(status='RELATION_ABSENT',rows=[])
            continue
        value=cur.execute(sql).fetchone()[0]
        if type(value)is not list:raise ValueError('GLOBAL_SYSTEM_CRON_TYPED_METADATA_ROWS_REQUIRED:'+name)
        result['groups'][name]=dict(status='CAPTURED',rows=value)
    after=cur.execute("select pg_catalog.current_database(),current_user::pg_catalog.text,session_user::pg_catalog.text,"
        "pg_catalog.current_setting('transaction_read_only'),pg_catalog.current_setting('transaction_isolation'),"
        "pg_catalog.pg_current_snapshot()::pg_catalog.text,pg_catalog.current_setting('search_path')").fetchone()
    if tuple(after)!=tuple(row[:5])+(row[7],row[8]):
        raise ValueError('GLOBAL_SYSTEM_CRON_READONLY_SNAPSHOT_OR_AUTHORITY_CHANGED')
    result['unresolved']=['SYSTEM_BINARY_AND_PROVIDER_BODY_TRUST_BOUNDARY_NOT_EXECUTION_PROOF',
        'CRON_FOREIGN_RULE_TRIGGER_ROLE_ENTRIES_REQUIRE_CALLER_REVIEW',
        'LIVE_BACKENDS_AND_LOGICAL_REPLICATION_METADATA_ARE_NOT_ATOMIC_WRITER_PROOF',
        'CURRENT_AUTHORITY_AFTER_WAITS_AND_OWNING_HOOKS_NOT_PROVEN',
        'NO_TWO_SESSION_WRITER_OR_PHANTOM_PROOF_FROM_METADATA']
    result['group_counts']={name:len(value['rows'])for name,value in result['groups'].items()}
    return result


def capture(cur):
    """Caller supplies the existing readonly candidate transaction."""
    return _capture(cur,'cp6_rollback')


def capture_scheduler(cur):
    """Readonly primary scheduler metadata, not primary ERP writes.

    pg_cron can schedule writes into the candidate from its primary database.
    Absence of cron.job in the candidate alone does not exclude that writer.
    """
    return _capture(cur,'postgres')


if __name__=='__main__':
    print(json.dumps(dict(status='SYSTEM_CRON_READONLY_QUERY_BUNDLE_PREPARED_NOT_EXECUTED',
        query_names=list(queries()),Native_cases=0,writer_closure=False,production_go=False)))
