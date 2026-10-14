"""FABLE-012 inventory (read only): which erp functions the browser role `authenticated` can execute, and why it
might need them, on the installed combined stack.

Fable (addendum A3, run 38571378585): `authenticated` has USAGE on schema erp and EXECUTE on 160 of 940 erp
functions, 108 of them writers, although every public facade is SECURITY DEFINER. Before any EXECUTE is revoked,
this lists for each such function whether something that runs with the caller's own rights refers to it:
RLS policies, views the role may read, column defaults, and SECURITY INVOKER functions the role may execute.
A function with no such reference is reachable only directly (bypassing the facades). Nothing is changed here.
"""
SQL = r"""
with fx as(
 select p.oid,p.oid::regprocedure::text sig,p.proname,p.prosecdef,pg_get_function_result(p.oid)='trigger' is_trigger,
  exists(select 1 from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a where a.grantee=0 and a.privilege_type='EXECUTE') via_public,
  exists(select 1 from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a where a.grantee='authenticated'::regrole and a.privilege_type='EXECUTE') via_grant
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='erp' and p.prokind in('f','p') and has_function_privilege('authenticated',p.oid,'EXECUTE')),
pol as(select pg_get_expr(polqual,polrelid)||' '||coalesce(pg_get_expr(polwithcheck,polrelid),'') e from pg_policy),
vw as(select pg_get_viewdef(c.oid) e from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where c.relkind in('v','m') and n.nspname not in('pg_catalog','information_schema') and has_table_privilege('authenticated',c.oid,'SELECT')),
df as(select pg_get_expr(d.adbin,d.adrelid) e from pg_attrdef d),
inv as(select q.prosrc e from pg_proc q join pg_namespace qn on qn.oid=q.pronamespace
 where not q.prosecdef and qn.nspname not in('pg_catalog','information_schema') and has_function_privilege('authenticated',q.oid,'EXECUTE'))
select fx.sig,fx.prosecdef,fx.is_trigger,fx.via_public,fx.via_grant,
 exists(select 1 from pol where pol.e ~ ('\m'||fx.proname||'\M')) in_policy,
 exists(select 1 from vw where vw.e ~ ('\m'||fx.proname||'\M')) in_readable_view,
 exists(select 1 from df where df.e ~ ('\m'||fx.proname||'\M')) in_default,
 exists(select 1 from inv where inv.e ~ ('\m'||fx.proname||'\M')) in_invoker_function
from fx order by fx.sig
"""
WRITER = ('post_', 'reverse_', 'save_', 'set_', 'approve_', 'close_', 'reopen_', 'process_', 'apply_', 'cancel_', 'delete_',
          'create_', 'update_', 'insert_', 'complete_', 'resolve_', 'allocate_', 'finalize_', 'import_', 'record_', 'merge_')


def inventory(cur):
    rows = cur.execute(SQL).fetchall()
    out = []
    for sig, secdef, trigger, public, granted, policy, view, default, invoker in rows:
        name = sig.split('.', 1)[1].split('(', 1)[0]
        needed = policy or view or default or invoker
        out.append(dict(signature=sig, security_definer=secdef, trigger=trigger, via_public=public, via_grant=granted,
                        writer_name=name.startswith(WRITER), in_policy=policy, in_readable_view=view, in_default=default,
                        in_invoker_function=invoker, invoker_reference=needed))
    usage = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    tables = [r[0] for r in cur.execute(
        "select c.oid::regclass::text from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' "
        "and c.relkind in('r','p','v','m') and has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE') order by 1").fetchall()]
    return dict(authenticated_erp_usage=usage, executable=len(out),
                writers=sum(1 for x in out if x['writer_name']),
                no_invoker_reference=sum(1 for x in out if not x['invoker_reference'] and not x['trigger']),
                writers_without_invoker_reference=sorted(x['signature'] for x in out if x['writer_name'] and not x['invoker_reference']),
                with_invoker_reference=sorted(x['signature'] for x in out if x['invoker_reference']),
                authenticated_erp_relations=tables, functions=out, changed_anything=False)
