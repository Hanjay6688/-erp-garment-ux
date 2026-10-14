#!/usr/bin/env python3
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path('restore')


def qi(value):
    return '"' + str(value).replace('"', '""') + '"'


def ql(value):
    return "'" + str(value).replace("'", "''") + "'"


def statement(text):
    text = str(text).rstrip()
    return text if text.endswith(';') else text + ';'


def extract_language(definition):
    match = re.search(r'\bLANGUAGE\s+([A-Za-z0-9_]+)', definition, re.I)
    if not match:
        raise ValueError('function language not found')
    return match.group(1).lower()


def extract_body(definition):
    match = re.search(r'\bAS\s+(\$[A-Za-z0-9_]*\$)', definition, re.I)
    if not match:
        return definition
    tag = match.group(1)
    start = match.end()
    end = definition.find(tag, start)
    return definition[start:end] if end >= 0 else definition[start:]


def strip_sql_noise(text):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'--[^\n]*', ' ', text)
    text = re.sub(r"'(?:''|[^'])*'", "''", text)
    return text


def has_relation_reference(text, schema, name):
    qualified = rf'(?<![A-Za-z0-9_]){re.escape(schema)}\s*\.\s*{re.escape(name)}(?![A-Za-z0-9_])'
    unqualified = rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])'
    return re.search(qualified, text, re.I) is not None or re.search(unqualified, text, re.I) is not None


def has_function_call(text, schema, name):
    qualified = rf'(?<![A-Za-z0-9_]){re.escape(schema)}\s*\.\s*{re.escape(name)}(?![A-Za-z0-9_])\s*\('
    unqualified = rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])\s*\('
    return re.search(qualified, text, re.I) is not None or re.search(unqualified, text, re.I) is not None


def node_key(kind, schema, name):
    return f'{kind}:{schema}.{name}'


def topological_mixed_order(sql_functions, views, view_dependencies):
    sql_by_key = {(f['schema_name'], f['function_name']): f for f in sql_functions}
    view_by_key = {(v['schema_name'], v['view_name']): v for v in views}
    if len(sql_by_key) != len(sql_functions):
        raise SystemExit('Overloaded SQL functions need signature-aware ordering; none were expected in this snapshot.')

    nodes = {}
    dependencies = defaultdict(set)
    for (schema, name), function in sql_by_key.items():
        key = node_key('F', schema, name)
        nodes[key] = ('function', function)
    for (schema, name), view in view_by_key.items():
        key = node_key('V', schema, name)
        nodes[key] = ('view', view)

    for dep in view_dependencies:
        child = node_key('V', dep['dependent_schema'], dep['dependent_name'])
        parent = node_key('V', dep['referenced_schema'], dep['referenced_name'])
        if child in nodes and parent in nodes and child != parent:
            dependencies[child].add(parent)

    for (schema, name), function in sql_by_key.items():
        key = node_key('F', schema, name)
        body = strip_sql_noise(extract_body(function['definition']))
        for (view_schema, view_name) in view_by_key:
            if has_relation_reference(body, view_schema, view_name):
                dependencies[key].add(node_key('V', view_schema, view_name))
        for (callee_schema, callee_name) in sql_by_key:
            if (callee_schema, callee_name) == (schema, name):
                continue
            if has_function_call(body, callee_schema, callee_name):
                dependencies[key].add(node_key('F', callee_schema, callee_name))

    for (schema, name), view in view_by_key.items():
        key = node_key('V', schema, name)
        definition = strip_sql_noise(view['definition'])
        for (callee_schema, callee_name) in sql_by_key:
            if has_function_call(definition, callee_schema, callee_name):
                dependencies[key].add(node_key('F', callee_schema, callee_name))

    for key in nodes:
        dependencies[key] &= set(nodes)
        dependencies[key].discard(key)

    pending = set(nodes)
    ordered = []
    while pending:
        ready = sorted(key for key in pending if not (dependencies[key] & pending))
        if not ready:
            cycle_report = {key: sorted(dependencies[key] & pending) for key in sorted(pending)}
            raise SystemExit('Unresolved SQL-function/view dependency cycle:\n' + json.dumps(cycle_report, indent=2))
        for key in ready:
            ordered.append(nodes[key])
            pending.remove(key)
    return ordered


def main():
    catalog = json.loads((ROOT / 'ERP_ENTENG_CATALOG_SNAPSHOT.json').read_text())
    manifest = json.loads((ROOT / 'RECOVERY_MANIFEST.json').read_text())

    columns_by_table = defaultdict(list)
    for column in catalog['columns']:
        columns_by_table[(column['schema_name'], column['table_name'])].append(column)

    ddl = [
        r'\set ON_ERROR_STOP on',
        'set client_min_messages = warning;',
        'create extension if not exists pgcrypto with schema extensions;',
        'create extension if not exists "uuid-ossp" with schema extensions;',
        'create extension if not exists pg_stat_statements with schema extensions;',
        'create extension if not exists supabase_vault with schema vault;',
        'create extension if not exists pg_cron with schema pg_catalog;',
        'drop schema if exists erp cascade;',
        'create schema erp authorization postgres;',
    ]

    for custom_type in catalog['custom_types']:
        schema = qi(custom_type['schema_name'])
        name = qi(custom_type['type_name'])
        if custom_type['typtype'] == 'e':
            labels = ','.join(ql(label) for label in custom_type['enum_labels'])
            ddl.append(f'create type {schema}.{name} as enum ({labels});')
        elif custom_type['typtype'] == 'd':
            text = f'create domain {schema}.{name} as {custom_type["domain_base_type"]}'
            if custom_type['domain_default']:
                text += f' default {custom_type["domain_default"]}'
            if custom_type['domain_not_null']:
                text += ' not null'
            ddl.append(text + ';')

    for sequence in catalog['sequences']:
        ddl.append(
            f"create sequence {qi(sequence['schema_name'])}.{qi(sequence['sequence_name'])} "
            f"as {sequence['data_type']} increment by {sequence['seqincrement']} minvalue {sequence['seqmin']} "
            f"maxvalue {sequence['seqmax']} start with {sequence['seqstart']} cache {sequence['seqcache']}"
            + (' cycle;' if sequence['seqcycle'] else ' no cycle;')
        )
        ddl.append(f"alter sequence {qi(sequence['schema_name'])}.{qi(sequence['sequence_name'])} owner to {qi(sequence['owner_name'])};")

    for table in catalog['tables']:
        key = (table['schema_name'], table['table_name'])
        definitions = []
        for column in columns_by_table[key]:
            suffix = ''
            if column['attgenerated'] == 's':
                suffix += f" generated always as ({column['default_expression']}) stored"
            elif column['attidentity'] == 'a':
                suffix += ' generated always as identity'
            elif column['attidentity'] == 'd':
                suffix += ' generated by default as identity'
            elif column['default_expression']:
                suffix += f" default {column['default_expression']}"
            if column['not_null']:
                suffix += ' not null'
            definitions.append(f"{qi(column['column_name'])} {column['data_type']}{suffix}")
        ddl.append(f"create table {qi(table['schema_name'])}.{qi(table['table_name'])} (\n  " + ',\n  '.join(definitions) + '\n);')
        ddl.append(f"alter table {qi(table['schema_name'])}.{qi(table['table_name'])} owner to {qi(table['owner_name'])};")

    for constraint in catalog['constraints']:
        ddl.append(
            f"alter table only {qi(constraint['schema_name'])}.{qi(constraint['table_name'])} "
            f"add constraint {qi(constraint['constraint_name'])} {constraint['definition']};"
        )

    for index in catalog['indexes']:
        ddl.append(statement(index['definition']))

    non_sql_functions = []
    sql_functions = []
    for function in catalog['functions']:
        (sql_functions if extract_language(function['definition']) == 'sql' else non_sql_functions).append(function)

    ddl.append('set check_function_bodies = off;')
    for function in non_sql_functions:
        ddl.append(statement(function['definition']))
        ddl.append(
            f"alter function {qi(function['schema_name'])}.{qi(function['function_name'])}"
            f"({function['identity_arguments']}) owner to {qi(function['owner_name'])};"
        )
    ddl.append('set check_function_bodies = on;')

    mixed_order = topological_mixed_order(sql_functions, catalog['views'], catalog['view_dependencies'])
    order_evidence = []
    for kind, item in mixed_order:
        if kind == 'function':
            ddl.append(statement(item['definition']))
            ddl.append(
                f"alter function {qi(item['schema_name'])}.{qi(item['function_name'])}"
                f"({item['identity_arguments']}) owner to {qi(item['owner_name'])};"
            )
            order_evidence.append({'kind': 'sql_function', 'schema': item['schema_name'], 'name': item['function_name']})
        else:
            options = ''
            if item['reloptions']:
                options = ' with (' + ','.join(item['reloptions']) + ')'
            ddl.append(
                f"create or replace view {qi(item['schema_name'])}.{qi(item['view_name'])}{options} as\n"
                f"{item['definition']};"
            )
            ddl.append(f"alter view {qi(item['schema_name'])}.{qi(item['view_name'])} owner to {qi(item['owner_name'])};")
            order_evidence.append({'kind': 'view', 'schema': item['schema_name'], 'name': item['view_name']})

    for trigger in catalog['triggers']:
        ddl.append(statement(trigger['definition']))

    for table in catalog['tables']:
        relation = f"{qi(table['schema_name'])}.{qi(table['table_name'])}"
        if table['rls_enabled']:
            ddl.append(f'alter table {relation} enable row level security;')
        if table['rls_forced']:
            ddl.append(f'alter table {relation} force row level security;')

    for policy in catalog['policies']:
        roles = ', '.join('public' if str(role).lower() == 'public' else qi(role) for role in policy['roles'])
        permissive = 'permissive' if str(policy['permissive']).upper() == 'PERMISSIVE' else 'restrictive'
        command = str(policy['cmd']).lower()
        text = (
            f"create policy {qi(policy['policy_name'])} on {qi(policy['schema_name'])}.{qi(policy['table_name'])} "
            f"as {permissive} for {command} to {roles}"
        )
        if policy['qual']:
            text += f" using ({policy['qual']})"
        if policy['with_check']:
            text += f" with check ({policy['with_check']})"
        ddl.append(text + ';')

    for grant in catalog['table_grants']:
        grantee = 'public' if str(grant['grantee']).upper() == 'PUBLIC' else qi(grant['grantee'])
        text = (
            f"grant {grant['privilege_type']} on table {qi(grant['schema_name'])}.{qi(grant['table_name'])} "
            f"to {grantee}"
        )
        if grant['is_grantable'] == 'YES':
            text += ' with grant option'
        ddl.append(text + ';')

    for grant in catalog['routine_grants']:
        grantee = 'public' if str(grant['grantee']).upper() == 'PUBLIC' else qi(grant['grantee'])
        ddl.append(
            f"grant {grant['privilege_type']} on function {qi(grant['schema_name'])}.{qi(grant['routine_name'])}"
            f"({grant['identity_arguments']}) to {grantee};"
        )

    ddl.append("select cron.unschedule(jobid) from cron.job;")
    for job in catalog['cron_jobs']:
        ddl.append(f"select cron.schedule({ql(job['jobname'])},{ql(job['schedule'])},{ql(job['command'])});")
        if not job['active']:
            ddl.append(f"update cron.job set active=false where jobname={ql(job['jobname'])};")

    ddl.append("notify pgrst, 'reload schema';")
    (ROOT / 'catalog-schema-restore.sql').write_text('\n\n'.join(ddl) + '\n')
    (ROOT / 'mixed-object-order.json').write_text(json.dumps(order_evidence, indent=2) + '\n')

    migrations = catalog['platform_migrations']
    payload = json.dumps(migrations, separators=(',', ':')).replace('$json$', '$ json $')
    (ROOT / 'platform-ledger-restore.sql').write_text(
        "\\set ON_ERROR_STOP on\n"
        "truncate table supabase_migrations.schema_migrations;\n"
        "insert into supabase_migrations.schema_migrations(version,name,statements)\n"
        f"select version,name,statements from jsonb_to_recordset($json${payload}$json$::jsonb) "
        "as x(version text,name text,statements text[]);\n"
    )

    sequence_lines = [r'\set ON_ERROR_STOP on']
    for sequence in catalog['sequences']:
        owned = []
        for column in catalog['columns']:
            if column['default_expression'] and str(sequence['sequence_name']) in str(column['default_expression']):
                owned.append((column['schema_name'], column['table_name'], column['column_name']))
        if owned:
            schema, table, column = owned[0]
            sequence_lines.append(
                f"select setval({ql(sequence['schema_name'] + '.' + sequence['sequence_name'])},"
                f"coalesce((select max({qi(column)}) from {qi(schema)}.{qi(table)}),1),"
                f"exists(select 1 from {qi(schema)}.{qi(table)}));"
            )
    (ROOT / 'sequence-reseed.sql').write_text('\n'.join(sequence_lines) + '\n')

    expected = {
        'tables': len(catalog['tables']),
        'views': len(catalog['views']),
        'functions': len(catalog['functions']),
        'triggers': len(catalog['triggers']),
        'indexes': len(catalog['indexes']) + sum(1 for c in catalog['constraints'] if c['contype'] in ('p', 'u', 'x')),
        'constraints': len(catalog['constraints']),
        'policies': len(catalog['policies']),
        'platform_migrations': len(catalog['platform_migrations']),
        'application_migrations': len(catalog['application_migrations']),
        'erp_rows': sum(item['rows'] for item in manifest['table_data']),
        'cron_jobs': len(catalog['cron_jobs']),
    }
    (ROOT / 'expected.json').write_text(json.dumps(expected, indent=2) + '\n')

    if catalog['storage_buckets']:
        bucket = catalog['storage_buckets'][0]
        (ROOT / 'storage-bucket.json').write_text(json.dumps({
            'id': bucket['id'],
            'name': bucket['name'],
            'public': bucket['public'],
            'file_size_limit': bucket['file_size_limit'],
            'allowed_mime_types': bucket['allowed_mime_types'],
        }, separators=(',', ':')))

    print(json.dumps({
        'expected': expected,
        'non_sql_functions': len(non_sql_functions),
        'mixed_sql_functions_and_views': len(mixed_order),
        'mixed_order_head': order_evidence[:10],
        'mixed_order_tail': order_evidence[-10:],
    }, indent=2))


if __name__ == '__main__':
    main()
