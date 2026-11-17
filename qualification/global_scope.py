"""Read and check the reviewed candidate relation and routine observations."""

from snapshot_prerequisites import ROUTES


DECIMAL = 'cp7_procurement."decimal"(jsonb,boolean)'
PGCRYPTO = {
    'extensions.digest(bytea,text)': 'pg_digest',
    'extensions.digest(text,text)': 'pg_digest',
    'extensions.gen_random_uuid()': 'pg_random_uuid',
}
ROLES = ('postgres', 'supabase_admin', 'authenticated', 'anon', 'service_role', 'cp7_procure_read', 'cp7_procure_write')
SECTIONS = ('identity', 'pgcrypto', 'relations', 'outside_origin_RI', 'routine_authority', 'relation_authority')



def read_queries(cur, queries, parameters):
    result = {}
    for section, query in queries.items():
        bound = {name: value for name, value in parameters.items() if '%(' + name + ')s' in query}
        executed = cur.execute(query, bound) if bound else cur.execute(query)
        keys = tuple(column.name for column in executed.description)
        result[section] = [dict(zip(keys, row, strict=True)) for row in executed.fetchall()]
    return result



def errors(observed, installed_relations):
    """Fail closed on missing or changed identities and preserve raw findings."""
    issues = []
    names = set(installed_relations)
    identity = observed['identity']
    if (len(identity) != 1 or identity[0]['database_name'] != 'cp6_rollback'
            or identity[0]['trigger_mode'] != 'origin' or identity[0]['isolation'] != 'read committed'
            or identity[0]['server_version'] != '170006'):
        issues.append('GLOBAL_SCOPE_DISPOSABLE_ORIGIN_READ_COMMITTED_REQUIRED')
    by_name = {row['qualified_name']: row for row in observed['relations']}
    if len(by_name) != len(observed['relations']) or set(by_name) != names or any(
            row['relation_oid'] is None or row['relkind'] not in ('r', 'p') or row['relpersistence'] != 'p'
            for row in by_name.values()):
        issues.append('GLOBAL_SCOPE_COMPLETE_PERMANENT_RELATION_OIDS_REQUIRED')
    crypto = {row['signature']: row for row in observed['pgcrypto']}
    if len(crypto) != len(observed['pgcrypto']) or set(crypto) != set(PGCRYPTO) or any(
            row['routine_oid'] is None or row['observed_language'] != 'c' or row['security_definer'] is not False
            or row['observed_shared_library'] != '$libdir/pgcrypto' or row['observed_symbol'] != PGCRYPTO[name]
            or row['observed_extension_member_of'] != 'pgcrypto' or row['extension_schema'] != 'extensions'
            or row['extension_owner'] != 'supabase_admin' or row['extension_version'] != '1.3'
            for name, row in crypto.items()):
        issues.append('GLOBAL_SCOPE_EXACT_PGCRYPTO_EXTENSION_MEMBERSHIP_REQUIRED')
    routines = {(row['role_name'], row['signature']): row for row in observed['routine_authority']}
    expected = set(ROUTES) | {DECIMAL} | set(PGCRYPTO)
    resolved = {signature for _, signature in routines}
    if (len(routines) != len(observed['routine_authority']) or not expected <= resolved
            or set(routines) != {(role, signature) for role in ROLES for signature in resolved}
            or any(row['caller_oid'] is None or row['routine_oid'] is None for row in routines.values())):
        issues.append('GLOBAL_SCOPE_COMPLETE_ROUTINE_OIDS_AND_ROLE_MATRIX_REQUIRED')
    required_execute = {('authenticated', signature) for signature in ROUTES}
    required_execute.update((role, DECIMAL) for role in ('postgres', 'cp7_procure_read', 'cp7_procure_write'))
    for role, signature in sorted(required_execute):
        row = routines.get((role, signature))
        if not row or row['effective_schema_usage'] is not True or row['effective_execute'] is not True:
            issues.append(f'GLOBAL_SCOPE_REQUIRED_EFFECTIVE_EXECUTE_MISSING:{role}:{signature}')
    relation_roles = {(row['role_name'], row['qualified_name']): row for row in observed['relation_authority']}
    if (len(relation_roles) != len(observed['relation_authority'])
            or set(relation_roles) != {(role, name) for role in ROLES for name in names}
            or any(row['caller_oid'] is None or row['relation_oid'] is None
                   or row['relation_oid'] != by_name.get(name, {}).get('relation_oid')
                   for (_, name), row in relation_roles.items())):
        issues.append('GLOBAL_SCOPE_COMPLETE_RELATION_AUTHORITY_MATRIX_REQUIRED')
    return sorted(set(issues))

