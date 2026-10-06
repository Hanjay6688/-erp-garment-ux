"""P20 input: read-only catalog scan of legacy direct paths on the aligned clone.

PostgreSQL grants EXECUTE on new functions to PUBLIC unless revoked, and G-01
keeps USAGE on schema erp for authenticated. This lists what the API roles can
reach in erp without a CP7 command, classifies functions by a text heuristic
(writes, explicit permission check, role-only guard) and records table DML and
RLS. Observation only: it changes nothing and decides nothing; every candidate
needs a human/P20 reading of the actual body before any finding is accepted.
"""
import json

FUNCTIONS = r"""
select p.oid::regprocedure::text,p.prosecdef,p.provolatile::text,pg_get_userbyid(p.proowner),
 pg_get_functiondef(p.oid)~*'\m(insert\s+into|update\s+[a-z_."]+\s+set|delete\s+from)\M',
 pg_get_functiondef(p.oid)~*'has_permission',
 pg_get_functiondef(p.oid)~*'require_(internal|owner_admin|owner)\M',
 has_function_privilege('authenticated',p.oid,'EXECUTE'),has_function_privilege('anon',p.oid,'EXECUTE')
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='erp' and p.prokind='f' order by 1"""
TABLES = """
select c.oid::regclass::text,c.relrowsecurity,
 has_table_privilege('authenticated',c.oid,'SELECT'),has_table_privilege('authenticated',c.oid,'INSERT'),
 has_table_privilege('authenticated',c.oid,'UPDATE'),has_table_privilege('authenticated',c.oid,'DELETE'),
 has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE'),
 (select count(*) from pg_policy p where p.polrelid=c.oid and (p.polroles='{0}' or
   (select oid from pg_roles where rolname='authenticated')=any(p.polroles)))
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='erp' and c.relkind in('r','p') order by 1"""


def scan(cur):
    usage = {who: cur.execute("select has_schema_privilege(%s,'erp','USAGE')", (who,)).fetchone()[0] for who in ('anon', 'authenticated')}
    exposed = cur.execute("select rolconfig from pg_roles where rolname='authenticator'").fetchone()
    functions = [dict(signature=r[0], security_definer=r[1], volatility=r[2], owner=r[3], writes=r[4], permission_check=r[5],
                      role_only_guard=r[6] and not r[5], authenticated_execute=r[7], anon_execute=r[8])
                 for r in cur.execute(FUNCTIONS).fetchall()]
    tables = [dict(table=r[0], rls=r[1], select=r[2], insert=r[3], update=r[4], delete=r[5], anon_any=r[6], authenticated_policies=r[7])
              for r in cur.execute(TABLES).fetchall()]
    reachable = [f for f in functions if f['authenticated_execute']]
    writer_without_permission = [f['signature'] for f in reachable if f['writes'] and f['security_definer'] and not f['permission_check']]
    dml = [t for t in tables if t['insert'] or t['update'] or t['delete']]
    report = dict(
        contract='cp7.p20.direct-path-scan.v1', observation_only=True, findings_accepted=False,
        erp_schema_usage=usage, authenticator_rolconfig=exposed[0] if exposed else None,
        erp_functions=len(functions), authenticated_executable=len(reachable),
        anon_executable=[f['signature'] for f in functions if f['anon_execute']],
        definer_writers_without_explicit_permission_check=writer_without_permission,
        definer_writers_role_only_guard=[f['signature'] for f in reachable if f['writes'] and f['security_definer'] and f['role_only_guard']],
        invoker_writers_reachable=[f['signature'] for f in reachable if f['writes'] and not f['security_definer']],
        tables=len(tables), tables_with_authenticated_dml=[dict(t, dml=[k for k in ('insert', 'update', 'delete') if t[k]]) for t in dml],
        tables_with_authenticated_dml_without_rls=[t['table'] for t in dml if not t['rls']],
        anon_table_access=[t['table'] for t in tables if t['anon_any']],
        functions_detail=functions, tables_detail=tables)
    return report


def summary(report):
    keys = ('erp_schema_usage', 'authenticator_rolconfig', 'erp_functions', 'authenticated_executable', 'anon_executable',
            'definer_writers_without_explicit_permission_check', 'definer_writers_role_only_guard', 'invoker_writers_reachable',
            'tables', 'tables_with_authenticated_dml_without_rls', 'anon_table_access')
    out = {k: report[k] for k in keys}
    out['tables_with_authenticated_dml'] = [(t['table'], t['dml'], t['rls'], t['authenticated_policies']) for t in report['tables_with_authenticated_dml']]
    return json.dumps(out, default=str)
