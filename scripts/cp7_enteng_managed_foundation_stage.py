"""Install the managed CP7 foundation separately, with its new RPCs closed."""

import argparse
from hashlib import sha256

import cp7_enteng_managed_change_fence as fence
import cp7_enteng_managed_wip_foundation as wip


MIGRATION_NAME = 'enteng_uji_cp7_managed_wip_foundation'
SCHEMAS = ('cp7_request_context', 'cp7_private', 'cp7_identity', 'cp7_wip')
ROLES = ('cp7_capture', 'cp7_policy')
RPCS = (
    'public.erp_cp7_capture_snapshot_v1(uuid,uuid)',
    'public.erp_cp7_read_snapshot_v1(uuid,text,text,integer)',
    'public.erp_cp7_get_production_policy_v1(uuid[])',
    'public.erp_cp7_get_source_identity_v1(uuid)',
    'public.erp_cp7_set_production_policy_v1(jsonb,uuid)',
    'public.erp_cp7_capture_cutting_wip_v1(uuid[],uuid)',
    'public.erp_cp7_read_cutting_wip_v1(uuid)',
    'public.erp_cp7_capture_production_wip_v1(jsonb,uuid)',
    'public.erp_cp7_read_production_wip_v1(uuid)',
)
TABLES = (
    'cp7_private.analysis_runs', 'cp7_identity.production_policy', 'cp7_identity.commands',
    'cp7_wip.runs', 'cp7_wip.production_runs',
)
CATALOGUE_SHA256 = '65bc9b0b60c0edea43ce0c2b69f6b4f09a02c3f6188a75d96ddba0642c79c8c1'


def sql_list(values):
    return ','.join("'" + value + "'" for value in values)


def facade_grant(enable):
    clause = 'grant execute on function {} to authenticated' if enable else 'revoke execute on function {} from authenticated'
    return clause.format(','.join(RPCS)) + ';\n'


def catalogue_sql():
    # Reuse the portable backup catalogue, scoped to these four schemas and nine RPCs.
    import cp7_ow04_restore_bundle as backup

    groups = ('schemas', 'relations', 'columns', 'constraints', 'indexes', 'triggers',
              'functions', 'types', 'policies', 'rules')
    schema_filter = f'n.nspname in ({sql_list(SCHEMAS)})'
    facade_filter = ','.join(f"to_regprocedure('{rpc}')" for rpc in RPCS)
    queries = []
    for group in groups:
        where = schema_filter
        if group == 'functions':
            where = f'({where} or p.oid in ({facade_filter}))'
        source = backup.QUERIES[group]
        if source.count(backup.NAMESPACE) != 1:
            raise ValueError('Foundation catalogue scope changed: ' + group)
        built = source.replace(backup.NAMESPACE, where)
        queries.append(f"select '{group}'::text as category, item, attrs from ({built}) x(item,attrs)")
    union = '\nunion all\n'.join(queries)
    return f"""with foundation_catalogue as ({union})
    select encode(sha256(convert_to(jsonb_agg(jsonb_build_array(category,item,attrs)
                  order by category collate "C",item collate "C",attrs::text collate "C")::text,'UTF8')),'hex')
      from foundation_catalogue"""


def scope_condition():
    empty_tables = ' and '.join(f'not exists (select from {name})' for name in TABLES)
    return f"""(select array_agg(rolname::text order by rolname) from pg_roles where left(rolname,4)='cp7_')
        is not distinct from array[{sql_list(ROLES)}] and
    not exists (select from pg_roles where rolname in ({sql_list(ROLES)}) and
       (rolcanlogin or rolsuper or rolinherit or rolcreatedb or rolcreaterole or rolreplication
        or not rolbypassrls or rolconnlimit<>-1 or rolconfig is not null)) and
    (select count(*) from pg_auth_members m where m.roleid in ('cp7_capture'::regrole,'cp7_policy'::regrole)
       and m.member='postgres'::regrole and m.grantor<>'postgres'::regrole
       and m.admin_option and not m.inherit_option and not m.set_option)=2 and
    not exists (select from pg_auth_members m where m.roleid in ('cp7_capture'::regrole,'cp7_policy'::regrole)
       and (m.member<>'postgres'::regrole or m.grantor='postgres'::regrole
            or not m.admin_option or m.inherit_option or m.set_option)) and
    not exists (select from pg_auth_members m where m.member in ('cp7_capture'::regrole,'cp7_policy'::regrole)) and
    not exists (select from unnest(array[{sql_list(ROLES)}]) r
       cross join unnest(array['postgres','anon','authenticated','service_role']) caller
       where pg_has_role(caller,r,'USAGE') or pg_has_role(caller,r,'SET')) and
    not exists (select from unnest(array[{sql_list(RPCS)}]) f
       cross join unnest(array['anon','authenticated','service_role']) caller
       where to_regprocedure(f) is null or has_function_privilege(caller,f,'EXECUTE')) and
    {empty_tables}"""


def guard_condition():
    pairs = ','.join(f"('{fence.SCHEMA}.{name}','{digests[1]}')" for name, digests in fence.GUARD_DIGESTS.items())
    return f"""(select encode(sha256(convert_to(array_to_json(statements)::text,'UTF8')),'hex')
      from supabase_migrations.schema_migrations where name='{fence.MIGRATION_NAME}')
       is not distinct from '{fence.MIGRATION_STATEMENT_SHA256}' and
    (select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='{fence.SCHEMA}')=4 and
    not exists (select from (values {pairs}) expected(signature,digest)
      left join pg_proc p on p.oid=to_regprocedure(expected.signature)
      where encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex') is distinct from expected.digest
         or p.proowner is distinct from 'postgres'::regrole
         or (select count(*) from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
           where a.grantee='postgres'::regrole and a.privilege_type='EXECUTE' and not a.is_grantable)<>1
         or exists (select from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
           where a.grantee<>'postgres'::regrole))"""


def snapshot_sql():
    return f"select ({scope_condition()}) as closed, ({catalogue_sql()}) as catalogue_sha256"


def migration_body():
    before = f"""do $foundation_before$
declare saved_path text:=current_setting('search_path');
begin
  perform set_config('search_path','',true);
  if session_user<>'postgres' or current_user<>'postgres' or current_setting('is_superuser')<>'off'
     or current_setting('server_version_num')::int not between 170000 and 179999
     or (select version from erp.schema_migrations order by installed_at desc,version desc limit 1)
          is distinct from 'v2.6.20bf'
     or (select count(*) from supabase_migrations.schema_migrations)<>139
     or exists (select from pg_roles where left(rolname,4)='cp7_')
     or exists (select from unnest(array[{sql_list(SCHEMAS)}]) n where to_regnamespace(n) is not null)
     or not ({guard_condition()}) then
    raise exception 'Expected the guarded Enteng Uji BF profile for the CP7 foundation';
  end if;
  perform {fence.SCHEMA}.enter_release();
  perform set_config('search_path',saved_path,true);
end $foundation_before$;
"""
    closing = 'revoke cp7_capture,cp7_policy from postgres granted by postgres restrict;\n'
    return before + wip.body() + '\n' + facade_grant(False) + closing


def migration():
    if len(CATALOGUE_SHA256) != 64:
        raise ValueError('The staged foundation catalogue must be pinned first')
    return migration_body() + f"""do $foundation_after$
declare saved_path text:=current_setting('search_path');
begin
  perform set_config('search_path','',true);
  if not ({scope_condition()}) or ({catalogue_sql()}) is distinct from '{CATALOGUE_SHA256}' then
    raise exception 'The closed CP7 foundation does not match the reviewed catalogue';
  end if;
  perform {fence.SCHEMA}.assert_ddl_fence();
  perform set_config('search_path',saved_path,true);
end $foundation_after$;
"""


def verify(conn):
    receipts = conn.execute("""
        select encode(sha256(convert_to(statements[1],'UTF8')),'hex')
          from supabase_migrations.schema_migrations
         where name=%s and cardinality(statements)=1
    """, (MIGRATION_NAME,)).fetchall()
    if receipts != [(sha256(migration().encode()).hexdigest(),)]:
        raise ValueError('The staged foundation migration receipt differs')
    path = conn.execute('show search_path').fetchone()[0]
    conn.execute("set local search_path=''")
    if conn.execute(snapshot_sql()).fetchone() != (True, CATALOGUE_SHA256):
        raise ValueError('The staged foundation is changed or available to application users')
    conn.execute("select set_config('search_path',%s,true)", (path,))


def reopen(conn):
    """Resume with transaction-scoped access to the two existing owners."""
    verify(conn)
    conn.execute("set local createrole_self_grant='set,inherit'")
    conn.execute('grant cp7_capture,cp7_policy to postgres with inherit true, set true granted by postgres')
    conn.execute(facade_grant(True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(migration(), end='')
