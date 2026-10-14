"""Fable cp17 — CP4/CP4.5 access surface on the full CP7 composition of 0b7049d9 (hosted-faithful G-01 base, which the
read-only hosted check of 14 Oct found identical 16/16). Catalog reads only; no fixture writes.
  FABLE_RBAC:ERP_TABLES_WITHOUT_RLS        names the erp tables with RLS off and whether anon/authenticated hold any table
                                            privilege on them. Oracle (INV-A05): a table without RLS must not be readable or
                                            writable by anon/authenticated.
  FABLE_RBAC:ERP_SCHEMA_REACH              USAGE on schema erp for anon/authenticated and the erp functions they may EXECUTE,
                                            split into writer-like names. Oracle (INV-A05, review R3-07): no erp writer is
                                            executable by anon; writers executable by authenticated are listed (COUNTEREXAMPLE
                                            only if anon can execute a writer or use a table without RLS).
  FABLE_RBAC:PUBLIC_FACADES_SECURITY       every public.erp_* facade: SECURITY DEFINER with a pinned search_path, or invoker.
                                            Oracle: a SECURITY DEFINER facade without search_path is a COUNTEREXAMPLE.
"""
import os,re
WRITER=re.compile(r'(^|_)(post|save|reverse|resolve|create|update|delete|approve|pay|close|reopen|apply|set|cancel|dispose|complete|insert|import|manage|record|correct|run|process)(_|$)')
def q(cur,sql,args=()):return cur.execute(sql,args).fetchall()

def cases(cur,today):
    def tables_without_rls():
        rows=q(cur,"""select c.relname,
              has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE') anon_any,
              has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE') auth_any,
              has_table_privilege('authenticated',c.oid,'SELECT') auth_select,
              has_table_privilege('authenticated',c.oid,'INSERT,UPDATE,DELETE') auth_write
            from pg_class c join pg_namespace n on n.oid=c.relnamespace
            where n.nspname='erp' and c.relkind in ('r','p') and not c.relrowsecurity order by 1""")
        usage=q(cur,"select has_schema_privilege('anon','erp','USAGE'),has_schema_privilege('authenticated','erp','USAGE')")[0]
        exposed=[r for r in rows if (r[1] and usage[0]) or (r[2] and usage[1])]
        return dict(status='COUNTEREXAMPLE' if exposed else 'PASS',tables=[dict(name=r[0],anon_any=r[1],authenticated_any=r[2],authenticated_select=r[3],authenticated_write=r[4]) for r in rows],
                    schema_usage=dict(anon=usage[0],authenticated=usage[1]),exposed=[r[0] for r in exposed])
    def schema_reach():
        usage=q(cur,"select has_schema_privilege('anon','erp','USAGE'),has_schema_privilege('authenticated','erp','USAGE')")[0]
        fns=q(cur,"""select p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',has_function_privilege('anon',p.oid,'EXECUTE'),has_function_privilege('authenticated',p.oid,'EXECUTE'),p.prosecdef
            from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and p.prokind='f' order by 1""")
        anon=[f[0] for f in fns if f[1]];auth=[f[0] for f in fns if f[2]]
        anon_w=[f for f in anon if WRITER.search(f.split('(')[0])];auth_w=[f for f in auth if WRITER.search(f.split('(')[0])]
        bad=bool(usage[0] and anon_w)
        return dict(status='COUNTEREXAMPLE' if bad else 'PASS',schema_usage=dict(anon=usage[0],authenticated=usage[1]),erp_functions=len(fns),
                    anon_execute=len(anon),authenticated_execute=len(auth),anon_writer_like=anon_w[:60],authenticated_writer_like_count=len(auth_w),authenticated_writer_like=auth_w[:200],
                    note='EXECUTE privilege only; reachability from clients also needs the schema in PostgREST db_schemas (CI: public only; hosted: not verified)')
    def facades():
        rows=q(cur,"""select p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',p.prosecdef,coalesce(array_to_string(p.proconfig,','),''),
              has_function_privilege('anon',p.oid,'EXECUTE')
            from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like 'erp\\_%%' and p.prokind='f' order by 1""")
        unpinned=[r[0] for r in rows if r[1] and 'search_path' not in r[2]]
        anon=[r[0] for r in rows if r[3]]
        return dict(status='COUNTEREXAMPLE' if unpinned else 'PASS',facades=len(rows),definer=sum(1 for r in rows if r[1]),definer_without_search_path=unpinned,anon_executable=anon[:80],anon_executable_count=len(anon))
    if os.environ.get('FABLE_RBAC_ONLY')=='facades':return [('FABLE_RBAC:PUBLIC_FACADES_SECURITY',facades)]
    return [('FABLE_RBAC:ERP_TABLES_WITHOUT_RLS',tables_without_rls),('FABLE_RBAC:ERP_SCHEMA_REACH',schema_reach),('FABLE_RBAC:PUBLIC_FACADES_SECURITY',facades)]

def races(tools,today):return []
def http_cases(http,today):return []
