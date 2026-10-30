"""Supplement the next disposable composite capture; no installer or DB URL.

Call capture(cur, exact_all22) from the existing restoration runner after that
runner sets READ ONLY, search_path='', TimeZone='UTC'. It must bracket this
read with its own full catalogue/data/sequence comparisons and outer restore.
No hosted connections, commit, rollback, grant, LOCK, DDL, or business call.
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('global_actual_census_reader', HERE / 'census.py')
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)

CONTRACT = 'cp7.global.actual-writer-census.supplement.v1'
SCOPE = "n.nspname=any(%(schemas)s::text[])"
RELATION = "n.nspname||'.'||c.relname"
RELATION_SCOPE = RELATION + '=any(%(relations)s::text[])'
FUNCTION_SCOPE = 'p.oid::regprocedure::text=any(%(functions)s::text[])'

QUERIES = {
    'schemas': "select n.nspname,jsonb_build_array(n.oid::text,pg_get_userbyid(n.nspowner),n.nspacl::text) from pg_namespace n where " + SCOPE,
    'relations': "select " + RELATION + ",jsonb_build_array(c.oid::text,n.nspname,c.relname,pg_get_userbyid(c.relowner),c.relkind,c.relpersistence,c.relrowsecurity,c.relforcerowsecurity,c.relispartition,c.relacl::text) from pg_class c join pg_namespace n on n.oid=c.relnamespace where " + RELATION_SCOPE,
    'columns': "select " + RELATION + "||':'||a.attname,jsonb_build_array(c.oid::text,a.attnum,a.attname,format_type(a.atttypid,a.atttypmod),a.attacl::text) from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace where a.attnum>0 and not a.attisdropped and " + RELATION_SCOPE,
    'functions': "select p.oid::regprocedure::text,jsonb_build_array(p.oid::text,n.nspname,pg_get_userbyid(p.proowner),p.proacl::text) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where " + FUNCTION_SCOPE,
    'roles': "select r.rolname,jsonb_build_array(r.oid::text,r.rolsuper,r.rolinherit,r.rolcreaterole,r.rolcreatedb,r.rolcanlogin,r.rolreplication,r.rolbypassrls,r.rolconnlimit,r.rolvaliduntil::text,encode(sha256(convert_to(coalesce(r.rolconfig::text,''),'UTF8')),'hex')) from pg_roles r",
    'memberships': "select pg_get_userbyid(m.roleid)||':'||pg_get_userbyid(m.member)||':'||pg_get_userbyid(m.grantor),jsonb_build_array(m.roleid::text,m.member::text,m.grantor::text,m.admin_option,m.inherit_option,m.set_option) from pg_auth_members m",
    'foreign_keys': "select " + RELATION + "||':'||k.conname,jsonb_build_array(k.oid::text," + RELATION + ",rn.nspname||'.'||rc.relname,k.conkey::int[],k.confkey::int[],k.confupdtype,k.confdeltype,k.confmatchtype,k.condeferrable,k.condeferred,k.convalidated,k.conparentid::text) from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace join pg_class rc on rc.oid=k.confrelid join pg_namespace rn on rn.oid=rc.relnamespace where k.contype='f' and " + RELATION_SCOPE,
    'triggers': "select t.oid::text,jsonb_build_array(" + RELATION + ",t.tgname,t.tgfoid::text,t.tgfoid::regprocedure::text,t.tgconstraint::text,t.tgconstrrelid::text,t.tgenabled,t.tgisinternal,t.tgtype,t.tgdeferrable,t.tginitdeferred,t.tgparentid::text,k.conname,k.conrelid::regclass::text,case when t.tgconstrrelid=0 then null else t.tgconstrrelid::regclass::text end) from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace left join pg_constraint k on k.oid=t.tgconstraint where " + RELATION_SCOPE,
    'view_relation_dependencies': "select r.oid::text||':'||d.refobjid::text||':'||d.refobjsubid::text||':'||d.deptype::text,jsonb_build_array(" + RELATION + ",r.rulename,r.ev_type,r.ev_enabled,r.is_instead,rn.nspname||'.'||rc.relname,d.refobjsubid,d.deptype) from pg_rewrite r join pg_class c on c.oid=r.ev_class join pg_namespace n on n.oid=c.relnamespace join pg_depend d on d.classid='pg_rewrite'::regclass and d.objid=r.oid and d.refclassid='pg_class'::regclass join pg_class rc on rc.oid=d.refobjid join pg_namespace rn on rn.oid=rc.relnamespace where " + RELATION_SCOPE,
    'inheritance': "select i.inhrelid::text||':'||i.inhseqno::text,jsonb_build_array(" + RELATION + ",pn.nspname||'.'||pc.relname,i.inhseqno,i.inhdetachpending) from pg_inherits i join pg_class c on c.oid=i.inhrelid join pg_namespace n on n.oid=c.relnamespace join pg_class pc on pc.oid=i.inhparent join pg_namespace pn on pn.oid=pc.relnamespace where " + RELATION_SCOPE,
    'database_authority': "select 'CURRENT',jsonb_build_array(d.oid::text,pg_get_userbyid(d.datdba),d.datacl::text) from pg_database d where d.datname=current_database()",
    'default_privileges': "select pg_get_userbyid(d.defaclrole)||':'||coalesce(n.nspname,'GLOBAL')||':'||d.defaclobjtype::text,jsonb_build_array(d.oid::text,d.defaclacl::text) from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace where d.defaclnamespace=0 or " + SCOPE,
    'effective_schema_privileges': "select r.rolname||':'||n.nspname||':'||p.privilege,to_jsonb(has_schema_privilege(r.oid,n.oid,p.privilege)) from pg_roles r cross join pg_namespace n cross join unnest(array['USAGE','CREATE'])p(privilege) where " + SCOPE,
    'effective_table_privileges': "select r.rolname||':'||" + RELATION + "||':'||p.privilege,to_jsonb(has_table_privilege(r.oid,c.oid,p.privilege)) from pg_roles r cross join pg_class c join pg_namespace n on n.oid=c.relnamespace cross join unnest(array['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'])p(privilege) where c.relkind in('r','p','f','v','m') and " + RELATION_SCOPE,
    'effective_function_privileges': "select r.rolname||':'||p.oid::regprocedure::text,to_jsonb(has_function_privilege(r.oid,p.oid,'EXECUTE')) from pg_roles r cross join pg_proc p where " + FUNCTION_SCOPE,
    'effective_sequence_privileges': "select r.rolname||':'||" + RELATION + "||':'||p.privilege,to_jsonb(has_sequence_privilege(r.oid,c.oid,p.privilege)) from pg_roles r cross join pg_class c join pg_namespace n on n.oid=c.relnamespace cross join unnest(array['SELECT','UPDATE','USAGE'])p(privilege) where c.relkind='S' and " + RELATION_SCOPE,
    # NULL attacl means no column-specific entries. Preserve EVERY raw column;
    # capture effective column grants for all columns with explicit ACLs.
    # Table-derived access remains independently captured above. No RLS or
    # current app-user authorization is inferred from these booleans.
    'effective_explicit_column_privileges': "select r.rolname||':'||" + RELATION + "||':'||a.attname||':'||p.privilege,to_jsonb(has_column_privilege(r.oid,c.oid,a.attnum,p.privilege)) from pg_roles r cross join pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace cross join unnest(array['SELECT','INSERT','UPDATE','REFERENCES'])p(privilege) where a.attnum>0 and not a.attisdropped and a.attacl is not null and c.relkind in('r','p','f','v','m') and " + RELATION_SCOPE,
    'effective_database_privileges': "select r.rolname||':'||p.privilege,to_jsonb(has_database_privilege(r.oid,d.oid,p.privilege)) from pg_roles r cross join pg_database d cross join unnest(array['CREATE','CONNECT','TEMPORARY'])p(privilege) where d.datname=current_database()",
}

# Explicit OID-based dependencies for selected namespaces, including functions,
# view rules, defaults, constraints, policies, triggers, types and relations.
# pg_depend does NOT exhaust PL/pgSQL/string function bodies (PostgreSQL 17
# ddl-depend). A zero edge count is never a no-write/no-call proof.
QUERIES['dependencies'] = """with scoped(classid,objid) as (
 select 'pg_class'::regclass,c.oid from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=any(%(schemas)s::text[])
 union all select 'pg_proc'::regclass,p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=any(%(schemas)s::text[])
 union all select 'pg_rewrite'::regclass,r.oid from pg_rewrite r join pg_class c on c.oid=r.ev_class join pg_namespace n on n.oid=c.relnamespace where n.nspname=any(%(schemas)s::text[])
 union all select 'pg_attrdef'::regclass,a.oid from pg_attrdef a join pg_class c on c.oid=a.adrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname=any(%(schemas)s::text[])
 union all select 'pg_constraint'::regclass,k.oid from pg_constraint k join pg_namespace n on n.oid=k.connamespace where n.nspname=any(%(schemas)s::text[])
 union all select 'pg_policy'::regclass,p.oid from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname=any(%(schemas)s::text[])
 union all select 'pg_trigger'::regclass,t.oid from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname=any(%(schemas)s::text[])
 union all select 'pg_type'::regclass,t.oid from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname=any(%(schemas)s::text[])
)
select d.classid::text||':'||d.objid::text||':'||d.objsubid::text||':'||d.refclassid::text||':'||d.refobjid::text||':'||d.refobjsubid::text||':'||d.deptype::text,
 jsonb_build_array(d.classid::regclass::text,d.objid::text,d.objsubid,
 d.refclassid::regclass::text,d.refobjid::text,d.refobjsubid,d.deptype,
 pg_describe_object(d.classid,d.objid,d.objsubid),
 pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid))
from pg_depend d where exists(select 1 from scoped s where (s.classid=d.classid and s.objid=d.objid)or(s.classid=d.refclassid and s.objid=d.refobjid))"""


def capture(cur, catalog, *, progress=None):
    census.validate_catalog(catalog)
    info = cur.connection.info
    census.require(info.host in ('127.0.0.1', 'localhost') and info.port == 54322,
                   'GLOBAL_CENSUS_LOCAL_DISPOSABLE_ONLY')
    identity = cur.execute("select current_database(),current_user,current_setting('transaction_read_only'),current_setting('search_path'),current_setting('TimeZone'),current_setting('server_version_num')").fetchone()
    census.require(identity[0] == 'cp6_rollback' and identity[1] in ('postgres', 'supabase_admin'),
                   'GLOBAL_CENSUS_EXACT_DISPOSABLE_IDENTITY_REQUIRED')
    census.require(identity[2:5] == ('on', '', 'UTC'), 'GLOBAL_CENSUS_CALLER_READ_ONLY_EMPTY_PATH_UTC_REQUIRED')
    census.require(170000 <= int(identity[5]) < 180000, 'GLOBAL_CENSUS_POSTGRES17_REQUIRED')
    params = dict(schemas=sorted(catalog['schemas']), relations=sorted(catalog['relations']), functions=sorted(catalog['functions']))
    groups = {}
    if progress is None:
        progress = lambda event: print(json.dumps(event, sort_keys=True), flush=True)
    for name, query in QUERIES.items():
        progress(dict(component='GLOBAL_CENSUS_READ_ONLY', phase=name, status='STARTED'))
        try:
            rows = cur.execute(query, params).fetchall()
        except Exception as error:
            progress(dict(component='GLOBAL_CENSUS_READ_ONLY', phase=name, status='FAILED',
                          sqlstate=getattr(error, 'sqlstate', None)))
            raise
        values = dict(rows)
        census.require(len(values) == len(rows), 'GLOBAL_CENSUS_DUPLICATE_SUPPLEMENT_IDENTITY:' + name)
        groups[name] = values
        progress(dict(component='GLOBAL_CENSUS_READ_ONLY', phase=name, status='CAPTURED', rows=len(values)))
    result = dict(contract=CONTRACT, catalogue_sha256=census.digest(catalog),
                  identity=list(identity), groups=groups, transaction_writes=False,
                  caller_full_catalogue_data_sequence_bracket_required=True,
                  caller_outer_restoration_required=True, runtime_entry=None,
                  actual_Native_credit=0, production_go=False, independent_acceptance=False)
    validate(result, catalog)
    return result


def validate(supplement, catalog):
    """Exact captured scope only; raw permission observations do not grant use."""
    census.require(type(supplement) is dict, 'GLOBAL_CENSUS_SUPPLEMENT_OBJECT_REQUIRED')
    census.require(supplement.get('contract') == CONTRACT and supplement.get('catalogue_sha256') == census.digest(catalog),
                   'GLOBAL_CENSUS_SUPPLEMENT_CATALOGUE_IDENTITY_CHANGED')
    census.require('runtime_entry' in supplement and supplement['runtime_entry'] is None
                   and supplement.get('production_go') is False
                   and supplement.get('independent_acceptance') is False
                   and type(supplement.get('actual_Native_credit')) is int
                   and supplement['actual_Native_credit'] == 0,
                   'GLOBAL_CENSUS_SUPPLEMENT_MUST_STAY_CLOSED')
    census.require(supplement.get('transaction_writes') is False
                   and supplement.get('caller_full_catalogue_data_sequence_bracket_required') is True
                   and supplement.get('caller_outer_restoration_required') is True,
                   'GLOBAL_CENSUS_SUPPLEMENT_REQUIRED_CALLER_PROOFS_CHANGED')
    groups = supplement['groups']
    census.require(set(groups) == set(QUERIES) and all(type(v) is dict for v in groups.values()),
                   'GLOBAL_CENSUS_COMPLETE_SUPPLEMENT_GROUPS_REQUIRED')
    for group in ('schemas', 'relations', 'columns', 'functions', 'roles', 'memberships', 'default_privileges'):
        census.require(set(groups[group]) == set(catalog[group]), 'GLOBAL_CENSUS_SUPPLEMENT_COVERAGE:' + group)
    for name, row in groups['roles'].items():
        census.require(type(row) is list and len(row) == 11 and row[1:] == catalog['roles'][name], 'GLOBAL_CENSUS_SUPPLEMENT_ROLE_DRIFT:' + name)
    for name, row in groups['memberships'].items():
        census.require(type(row) is list and len(row) == 6 and row[3:] == catalog['memberships'][name], 'GLOBAL_CENSUS_SUPPLEMENT_MEMBERSHIP_DRIFT:' + name)
    for name, row in groups['schemas'].items():
        census.require(len(row) == 3 and row[1] == catalog['schemas'][name][0]
                       and (row[2] is None or type(row[2]) is str), 'GLOBAL_CENSUS_SUPPLEMENT_SCHEMA_DRIFT:' + name)
    for name, row in groups['relations'].items():
        expected = catalog['relations'][name]
        census.require(len(row) == 10 and row[1] + '.' + row[2] == name
                       and row[3:9] == expected[:6] and (row[9] is None or type(row[9]) is str),
                       'GLOBAL_CENSUS_SUPPLEMENT_RELATION_DRIFT:' + name)
    for name, row in groups['columns'].items():
        expected = catalog['columns'][name]
        census.require(len(row) == 5 and row[2:4] == [expected[0], expected[2]]
                       and (row[4] is None or type(row[4]) is str)
                       and (row[4] is None) == (expected[12] is None),
                       'GLOBAL_CENSUS_SUPPLEMENT_COLUMN_DRIFT:' + name)
    for name, row in groups['functions'].items():
        census.require(len(row) == 4 and row[2] == catalog['functions'][name][1]
                       and (row[3] is None or type(row[3]) is str),
                       'GLOBAL_CENSUS_SUPPLEMENT_FUNCTION_DRIFT:' + name)
    expected_fk = {name for name, row in catalog['constraints'].items() if row[0] == 'f'}
    census.require(set(groups['foreign_keys']) == expected_fk, 'GLOBAL_CENSUS_SUPPLEMENT_FK_COVERAGE')
    for name, row in groups['foreign_keys'].items():
        census.require(len(row) == 12 and row[1] == name.split(':', 1)[0]
                       and row[2] in catalog['relations'] and row[8:11] == catalog['constraints'][name][1:4],
                       'GLOBAL_CENSUS_SUPPLEMENT_FK_ENDPOINT_OR_METADATA_CHANGED:' + name)
    trigger_keys = set()
    for oid, row in groups['triggers'].items():
        census.require(type(row) is list and len(row) == 15 and type(row[7]) is bool,
                       'GLOBAL_CENSUS_SUPPLEMENT_TRIGGER_ABI:' + oid)
        identity = row[0] + ':' + (row[13] + ':' + row[12] + ':' + row[3] + ':' + str(row[8]) if row[7] else row[1])
        census.require(identity not in trigger_keys and identity in catalog['triggers'],
                       'GLOBAL_CENSUS_SUPPLEMENT_TRIGGER_IDENTITY:' + oid)
        trigger_keys.add(identity)
        expected = catalog['triggers'][identity]
        census.require([row[7], row[6], row[8], row[9], row[10], row[3], row[12], row[14], row[13]] ==
                       [expected[0], expected[1], expected[2], expected[6], expected[7], expected[8], expected[12], expected[13], expected[15]],
                       'GLOBAL_CENSUS_SUPPLEMENT_TRIGGER_DRIFT:' + identity)
    census.require(trigger_keys == set(catalog['triggers']), 'GLOBAL_CENSUS_SUPPLEMENT_TRIGGER_COVERAGE')
    rule_keys = set()
    for row in groups['view_relation_dependencies'].values():
        census.require(type(row) is list and len(row) == 8 and row[0] in catalog['relations']
                       and row[5] in catalog['relations'], 'GLOBAL_CENSUS_SUPPLEMENT_VIEW_DEPENDENCY_ABI')
        identity = row[0] + ':' + row[1]
        census.require(identity in catalog['rules'] and row[2:5] == catalog['rules'][identity][:3],
                       'GLOBAL_CENSUS_SUPPLEMENT_RULE_DRIFT')
        rule_keys.add(identity)
    census.require(rule_keys == set(catalog['rules']), 'GLOBAL_CENSUS_SUPPLEMENT_VIEW_RULE_COVERAGE')
    inherited = {}
    for row in groups['inheritance'].values():
        census.require(type(row) is list and len(row) == 4 and type(row[2]) is int and type(row[3]) is bool,
                       'GLOBAL_CENSUS_SUPPLEMENT_INHERITANCE_ABI')
        key = row[0] + ':' + str(row[2])
        census.require(key not in inherited, 'GLOBAL_CENSUS_SUPPLEMENT_DUPLICATE_INHERITANCE')
        inherited[key] = row[1]
    census.require(inherited == catalog['inheritance'], 'GLOBAL_CENSUS_SUPPLEMENT_INHERITANCE_COVERAGE')
    census.require(bool(groups['dependencies']) and all(type(row) is list and len(row) == 9
                   for row in groups['dependencies'].values()), 'GLOBAL_CENSUS_SUPPLEMENT_UNKNOWN_EMPTY_DEPENDENCIES')
    function_oids = {row[0] for row in groups['functions'].values()}
    dependency_function_oids = {row[1] for row in groups['dependencies'].values() if row[0] == 'pg_proc'}
    census.require(function_oids <= dependency_function_oids,
                   'GLOBAL_CENSUS_SUPPLEMENT_FUNCTION_DEPENDENCY_IDENTITY_COVERAGE')
    census.require(set(groups['database_authority']) == {'CURRENT'}
                   and len(groups['database_authority']['CURRENT']) == 3
                   and groups['database_authority']['CURRENT'][1] == catalog['database_authority']['CURRENT'][0],
                   'GLOBAL_CENSUS_SUPPLEMENT_DATABASE_AUTHORITY')
    roles = set(catalog['roles'])
    table_privs = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER', 'MAINTAIN')
    tables = {name for name, row in catalog['relations'].items() if row[1] in ('r', 'p', 'f', 'v', 'm')}
    sequences = {name for name, row in catalog['relations'].items() if row[1] == 'S'}
    explicit_columns = {name for name, row in catalog['columns'].items()
                        if row[12] is not None and name.rpartition(':')[0] in tables}
    matrices = {
        'effective_schema_privileges': {r + ':' + s + ':' + p for r in roles for s in catalog['schemas'] for p in ('USAGE', 'CREATE')},
        'effective_table_privileges': {r + ':' + t + ':' + p for r in roles for t in tables for p in table_privs},
        'effective_function_privileges': {r + ':' + f for r in roles for f in catalog['functions']},
        'effective_sequence_privileges': {r + ':' + s + ':' + p for r in roles for s in sequences for p in ('SELECT', 'UPDATE', 'USAGE')},
        'effective_explicit_column_privileges': {r + ':' + c + ':' + p for r in roles for c in explicit_columns for p in ('SELECT', 'INSERT', 'UPDATE', 'REFERENCES')},
        'effective_database_privileges': {r + ':' + p for r in roles for p in ('CREATE', 'CONNECT', 'TEMPORARY')},
    }
    for group, expected in matrices.items():
        census.require(set(groups[group]) == expected and all(type(v) is bool for v in groups[group].values()),
                       'GLOBAL_CENSUS_SUPPLEMENT_EFFECTIVE_MATRIX:' + group)
    return dict(status='EXACT_SUPPLEMENTAL_METADATA_ONLY', raw_ACL_null_empty_preserved=True,
                dependency_completeness='UNKNOWN_PROCEDURAL_AND_DYNAMIC_BODY_EDGES',
                writer_or_phantom_lock_closed=False, runtime_entry=None,
                actual_Native_credit=0, production_go=False, independent_acceptance=False)
