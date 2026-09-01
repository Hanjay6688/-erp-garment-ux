#!/usr/bin/env python3
import json
import os
import traceback
from pathlib import Path

import psycopg

ROOT = Path('restore')
REPORT = Path('cp2-free-local-restore-report.json')
PGURL = os.environ.get('PGURL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)


def main():
    catalog = json.loads((ROOT / 'ERP_ENTENG_CATALOG_SNAPSHOT.json').read_text())
    expected_counts = json.loads((ROOT / 'expected.json').read_text())
    manifest = json.loads((ROOT / 'RECOVERY_MANIFEST.json').read_text())
    conn = psycopg.connect(PGURL)

    def rows(query):
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [description.name for description in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def identity_set(items, keys):
        return {tuple(str(item.get(key, '')) for key in keys) for item in items}

    actual = {
        'tables': rows("select n.nspname schema_name,c.relname table_name,c.relrowsecurity rls_enabled,c.relforcerowsecurity rls_forced from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in ('r','p') order by 1,2"),
        'views': rows("select n.nspname schema_name,c.relname view_name from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='v' and (n.nspname='erp' or (n.nspname='public' and c.relname like 'v_erp_%')) order by 1,2"),
        'functions': rows("select n.nspname schema_name,p.proname function_name,pg_get_function_identity_arguments(p.oid) identity_arguments from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' or (n.nspname='public' and p.proname like 'erp_%') order by 1,2,3"),
        'triggers': rows("select n.nspname schema_name,c.relname table_name,t.tgname trigger_name from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and not t.tgisinternal order by 1,2,3"),
        'indexes': rows("select n.nspname schema_name,c.relname table_name,i.relname index_name from pg_index x join pg_class i on i.oid=x.indexrelid join pg_class c on c.oid=x.indrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' order by 1,2,3"),
        'constraints': rows("select n.nspname schema_name,c.relname table_name,con.conname constraint_name from pg_constraint con join pg_class c on c.oid=con.conrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' order by 1,2,3"),
        'policies': rows("select schemaname schema_name,tablename table_name,policyname policy_name from pg_policies where schemaname='erp' or (schemaname='public' and tablename like 'v_erp_%') order by 1,2,3"),
        'columns': rows("select n.nspname schema_name,c.relname table_name,a.attnum::text attnum,a.attname column_name,format_type(a.atttypid,a.atttypmod) data_type,a.attnotnull not_null,a.attidentity::text attidentity,a.attgenerated::text attgenerated,pg_get_expr(ad.adbin,ad.adrelid) default_expression from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace left join pg_attrdef ad on ad.adrelid=a.attrelid and ad.adnum=a.attnum where n.nspname='erp' and c.relkind in ('r','p') and a.attnum>0 and not a.attisdropped order by 1,2,a.attnum"),
    }

    expected_indexes = [
        {'schema_name': item['schema_name'], 'table_name': item['table_name'], 'index_name': item['index_name']}
        for item in catalog['indexes']
    ] + [
        {'schema_name': item['schema_name'], 'table_name': item['table_name'], 'index_name': item['constraint_name']}
        for item in catalog['constraints'] if item['contype'] in ('p', 'u', 'x')
    ]

    object_specs = {
        'tables': (catalog['tables'], ('schema_name', 'table_name', 'rls_enabled', 'rls_forced')),
        'views': (catalog['views'], ('schema_name', 'view_name')),
        'functions': (catalog['functions'], ('schema_name', 'function_name', 'identity_arguments')),
        'triggers': (catalog['triggers'], ('schema_name', 'table_name', 'trigger_name')),
        'indexes': (expected_indexes, ('schema_name', 'table_name', 'index_name')),
        'constraints': (catalog['constraints'], ('schema_name', 'table_name', 'constraint_name')),
        'policies': (catalog['policies'], ('schema_name', 'table_name', 'policy_name')),
        'columns': (catalog['columns'], ('schema_name', 'table_name', 'attnum', 'column_name', 'data_type', 'not_null', 'attidentity', 'attgenerated', 'default_expression')),
    }

    object_mismatches = {}
    for label, (expected_items, keys) in object_specs.items():
        expected_set = identity_set(expected_items, keys)
        actual_set = identity_set(actual[label], keys)
        if expected_set != actual_set:
            object_mismatches[label] = {
                'missing': sorted(expected_set - actual_set)[:100],
                'unexpected': sorted(actual_set - expected_set)[:100],
                'expected_count': len(expected_set),
                'actual_count': len(actual_set),
            }

    count_actual = {
        'tables': len(actual['tables']),
        'views': len(actual['views']),
        'functions': len(actual['functions']),
        'triggers': len(actual['triggers']),
        'indexes': len(actual['indexes']),
        'constraints': len(actual['constraints']),
        'policies': len(actual['policies']),
        'platform_migrations': rows('select count(*)::int n from supabase_migrations.schema_migrations')[0]['n'],
        'application_migrations': rows('select count(*)::int n from erp.schema_migrations')[0]['n'],
        'cron_jobs': rows('select count(*)::int n from cron.job')[0]['n'],
        'auth_users': rows('select count(*)::int n from auth.users')[0]['n'],
        'app_users': rows('select count(*)::int n from erp.app_users')[0]['n'],
    }

    data_mismatches = []
    total_rows = 0
    with conn.cursor() as cur:
        for item in manifest['table_data']:
            table = item['table']
            safe = table.replace('"', '""')
            cur.execute(f'SELECT to_jsonb(t)::text FROM erp."{safe}" t ORDER BY to_jsonb(t)::text')
            payload = [json.loads(row[0]) for row in cur.fetchall()]
            backup_payload = json.loads((ROOT / item['path']).read_text())
            total_rows += len(payload)
            if canonical(payload) != canonical(backup_payload):
                data_mismatches.append({
                    'table': table,
                    'expected_rows': len(backup_payload),
                    'actual_rows': len(payload),
                })
    count_actual['erp_rows'] = total_rows

    expected_platform = [
        {'version': str(item['version']), 'name': item['name'], 'statements': item.get('statements') or []}
        for item in catalog['platform_migrations']
    ]
    actual_platform = rows('select version::text version,name,statements from supabase_migrations.schema_migrations order by version')
    platform_ledger_match = canonical(expected_platform) == canonical(actual_platform)

    expected_application = [
        {'version': item['version'], 'description': item['description']}
        for item in catalog['application_migrations']
    ]
    actual_application = rows('select version,description from erp.schema_migrations order by installed_at,version')
    application_ledger_match = canonical(expected_application) == canonical(actual_application)

    count_mismatches = {
        key: {'expected': value, 'actual': count_actual.get(key)}
        for key, value in expected_counts.items() if count_actual.get(key) != value
    }

    integrity = rows("select check_code,severity,violation_count,details from erp.run_integrity_checks() where violation_count > 0 order by severity desc,check_code")
    integrity_errors = [item for item in integrity if str(item['severity']).upper() == 'ERROR']

    status = 'PASS' if (
        not object_mismatches
        and not count_mismatches
        and not data_mismatches
        and not integrity_errors
        and count_actual['auth_users'] == 0
        and count_actual['app_users'] == 0
        and platform_ledger_match
        and application_ledger_match
    ) else 'FAIL'

    report = {
        'status': status,
        'mode': 'FREE_LOCAL_SUPABASE_RESTORE',
        'postgres_image': '17.6.1.165',
        'source_commit_sha': manifest['source_commit_sha'],
        'expected_schema_fingerprint': manifest['expected_schema_fingerprint'],
        'expected_counts': expected_counts,
        'actual_counts': count_actual,
        'object_mismatches': object_mismatches,
        'count_mismatches': count_mismatches,
        'data_mismatches': data_mismatches,
        'platform_ledger_match': platform_ledger_match,
        'application_ledger_match': application_ledger_match,
        'integrity_findings': integrity,
        'integrity_errors': integrity_errors,
        'auth_empty_state_verified': count_actual['auth_users'] == 0 and count_actual['app_users'] == 0,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    conn.close()
    if status != 'PASS':
        raise SystemExit('Free local database restore verification failed')


def write_crash_report(exc):
    if REPORT.exists():
        return
    report = {
        'status': 'ERROR',
        'mode': 'FREE_LOCAL_SUPABASE_RESTORE',
        'stage': 'DATABASE_VERIFIER',
        'exception_type': type(exc).__name__,
        'exception': str(exc),
        'traceback': traceback.format_exc(),
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + '\n')


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        traceback.print_exc()
        write_crash_report(exc)
        raise
