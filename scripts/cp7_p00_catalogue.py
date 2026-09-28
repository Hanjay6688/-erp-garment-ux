"""P00 catalogue on the accepted package in an isolated database.

This is developer discovery, not the CP7 actor-facing read facade. A catalogue
PASS neither satisfies E14/E22 nor certifies snapshot/demand semantics.
"""
from pathlib import Path
import hashlib
import json
import re

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
BASE = "10a834712e515af86c6d8baa89bbe40cff9793e3"
READERS = (
    "erp_get_sku_workspace_v1", "erp_get_sku_hpp_v1",
    "erp_get_wip_control_v1", "erp_get_laundry_qc_workspace_v1",
    "erp_get_product_conversion_workspace_v1", "erp_get_bs_resolution_workspace_v1",
)

FUNCTIONS = """
select p.oid, n.nspname as schema, p.proname as name,
 p.oid::regprocedure::text as signature,
 pg_get_function_result(p.oid) as result_type,
 pg_get_userbyid(p.proowner) as owner,
 p.prosecdef as security_definer, p.provolatile as volatility,
 p.proconfig as settings, l.lanname as language,
 pg_get_functiondef(p.oid) as definition,
 (select jsonb_agg(jsonb_build_object(
   'grantee',case when a.grantee=0 then 'PUBLIC' else pg_get_userbyid(a.grantee) end,
   'privilege',a.privilege_type,'grantable',a.is_grantable)
   order by a.grantee,a.privilege_type)
  from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a) as acl
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 join pg_language l on l.oid=p.prolang
where n.nspname in ('erp','public') and p.prokind in ('f','p')
order by n.nspname,p.proname,p.oid::regprocedure::text
"""

RELATIONS = """
select c.oid,n.nspname as schema,c.relname as name,c.relkind as kind,
 pg_get_userbyid(c.relowner) as owner,
 c.relrowsecurity as rls_enabled,c.relforcerowsecurity as rls_forced,
 c.relacl::text as acl,
 case when c.relkind in ('v','m') then pg_get_viewdef(c.oid,true) end as view_definition,
 (select jsonb_agg(jsonb_build_object('name',a.attname,
  'type',format_type(a.atttypid,a.atttypmod),'nullable',not a.attnotnull,
  'default',pg_get_expr(d.adbin,d.adrelid)) order by a.attnum)
  from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
  where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped) as columns
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname in ('erp','public') and c.relkind in ('r','p','v','m')
order by n.nspname,c.relname
"""

TRIGGERS = """
select n.nspname as schema,c.relname as relation,t.tgname as name,
 t.tgenabled as enabled,t.tgfoid::regprocedure::text as function,
 pg_get_triggerdef(t.oid,true) as definition
from pg_trigger t join pg_class c on c.oid=t.tgrelid
 join pg_namespace n on n.oid=c.relnamespace
where n.nspname in ('erp','public') and not t.tgisinternal
order by n.nspname,c.relname,t.tgname
"""

POLICIES = """
select schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check
from pg_policies where schemaname in ('erp','public')
order by schemaname,tablename,policyname
"""


def rows(cur, query):
    cur.execute(query)
    keys = [c.name for c in cur.description]
    return [dict(zip(keys, row)) for row in cur.fetchall()]


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def capture(url):
    # Do not permit this discovery runner to target a hosted or primary database.
    from psycopg.conninfo import conninfo_to_dict
    target = conninfo_to_dict(url)
    assert target.get('host') in ('127.0.0.1', 'localhost'), 'P00_LOCAL_DATABASE_ONLY'
    assert target.get('dbname') == 'cp6_rollback', 'P00_DISPOSABLE_DATABASE_ONLY'
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        cur.execute("set local search_path=pg_catalog; set local statement_timeout='120s'; set local lock_timeout='5s'")
        identity = rows(cur, """select current_database() as database,
          current_user as actor,current_setting('server_version') as postgres_version,
          current_setting('transaction_isolation') as isolation,
          current_setting('transaction_read_only') as read_only,
          pg_current_snapshot()::text as snapshot""")[0]
        assert identity['isolation'] == 'repeatable read' and identity['read_only'] == 'on'
        functions = rows(cur, FUNCTIONS)
        relations = rows(cur, RELATIONS)
        triggers = rows(cur, TRIGGERS)
        policies = rows(cur, POLICIES)
        assert functions and relations and triggers, 'P00_EMPTY_CATALOGUE'
        for item in functions:
            item.pop('oid')
            item['definition_sha256'] = digest(item['definition'])
            # PL/pgSQL dependencies are not fully recorded by pg_depend. These
            # candidates require manual review; they are not a complete call graph.
            item['textual_call_candidates'] = sorted(set(re.findall(
                r'\b(?:erp|public)\.[a-zA-Z_][a-zA-Z_0-9]*(?=\s*\()', item['definition'])))
        for item in relations:
            item.pop('oid')
            if item['view_definition'] is not None:
                item['definition_sha256'] = digest(item['view_definition'])
            if item['kind'] in ('r','p'):
                cur.execute(sql.SQL('select count(*) from {}.{}').format(
                    sql.Identifier(item['schema']), sql.Identifier(item['name'])))
                item['row_count'] = cur.fetchone()[0]
        for item in triggers:
            item['definition_sha256'] = digest(item['definition'])
        resolved = {name: [f['signature'] for f in functions
                           if f['schema'] == 'public' and f['name'] == name]
                    for name in READERS}
        assert all(resolved.values()), ('P00_MISSING_CURRENT_READER', resolved)
        cur.execute('savepoint read_only_control')
        try:
            cur.execute('delete from erp.schema_migrations where false')
        except psycopg.errors.ReadOnlySqlTransaction as exc:
            refusal = exc.sqlstate
        else:
            raise AssertionError('P00_READ_ONLY_CONTROL_FAILED')
        finally:
            cur.execute('rollback to savepoint read_only_control')
            cur.execute('release savepoint read_only_control')
        assert cur.execute('select pg_current_snapshot()::text').fetchone()[0] == identity['snapshot']
        conn.rollback()
    return dict(schema_version='cp7.source-catalogue.v1', accepted_base=BASE,
        runtime=identity, functions=functions, relations=relations,
        triggers=triggers, policies=policies, resolved_current_readers=resolved,
        read_only_write_refusal_sqlstate=refusal,
        call_graph_completeness='TEXT_CANDIDATES_ONLY_MANUAL_REVIEW_REQUIRED',
        business_reader_validation='NOT_RUN', production_go=False)


def run(url, boundary):
    out = ROOT/'cp6-proof/t3'
    out.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        conn.read_only = True
        before = boundary.snapshot(cur)
    result = capture(url)
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        conn.read_only = True
        unchanged = before == boundary.snapshot(cur)
    assert unchanged, 'P00_BUSINESS_BOUNDARY_CHANGED'
    payload = json.dumps(result, indent=2, default=str)+'\n'
    (out/'CP7_P00_CATALOGUE.json').write_text(payload)
    summary = dict(label='CP7_P00_CATALOGUE', status='PASS',
        accepted_base=BASE, runtime=result['runtime'],
        counts={kind: len(result[kind]) for kind in ('functions','relations','triggers','policies')},
        catalogue_sha256=digest(payload), resolved_current_readers=result['resolved_current_readers'],
        read_only_write_refusal_sqlstate=result['read_only_write_refusal_sqlstate'],
        business_boundary_unchanged=unchanged,
        actor_facade_tests='NOT_RUN', analysis_capture_tests='NOT_RUN',
        production_go=False, independent_acceptance=False)
    (out/'CP7_P00_RESULT.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    assert hashlib.sha256((ROOT/'supabase/release/cp6-t3/MANIFEST.json').read_bytes()).hexdigest() == (
        '40795c3fce619c5795b427e9aa31836777b687f82eba4ab5654264d57564879f'
    ), 'P00_ACCEPTED_PACKAGE_MANIFEST_DRIFT'
    import cp6_t3_package_run as package_run
    # Keep package install, body/ACL pins, advisors, primary preservation,
    # backup/restore and cleanup gates intact. Only the runtime probe changes.
    package_run._writer_runtime = lambda browser_mode=False: run(
        package_run.boundary.ADMIN, package_run.boundary)
    package_run.run('install')
