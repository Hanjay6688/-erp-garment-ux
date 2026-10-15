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


# Owner D14-9 (15 Oct 2026, verbatim): "Ya, pencabutan 82 fungsi boleh ditunda ke CP7C, berdasarkan bukti auditor bahwa
# jalur tersebut tidak dapat dijangkau dari internet. Catat sebagai pekerjaan keamanan yang belum selesai. Jika
# konfigurasi akses berubah sehingga fungsi itu bisa dijangkau, pencabutannya menjadi prasyarat sebelum jalur tersebut
# diaktifkan."
GATE_REFUSAL = 'CP7_FABLE012_REVOKE_BEFORE_EXPOSING_ERP'
RUNBOOK_SCHEMAS = ('public', 'graphql_public')
RUNBOOK_EXTRA_SEARCH_PATH = ('public', 'extensions')
STORED = r"""
select split_part(c,'=',1),substr(c,strpos(c,'=')+1)
from pg_db_role_setting s join pg_roles r on r.oid=s.setrole cross join unnest(s.setconfig) c
where r.rolname='authenticator' and s.setdatabase in(0,(select oid from pg_database where datname=current_database()))
 and split_part(c,'=',1) in('pgrst.db_schemas','pgrst.db_extra_search_path')
order by s.setdatabase,1
"""


def _names(value):
    return [x.strip().strip('"') for x in value.split(',') if x.strip()]


def exposure_gate(cur, declared_schemas=RUNBOOK_SCHEMAS, declared_extra_search_path=RUNBOOK_EXTRA_SEARCH_PATH):
    """Gate to run before the Data API setting changes (read only). `declared_*` is the setting about to be applied
    (Dashboard / PostgREST config, which the database cannot see); a PostgREST override stored in the database on the
    `authenticator` role (`ALTER ROLE ... SET pgrst.db_schemas`, the runbook forbids it) is read and counted too. When
    schema `erp` would be served or put on the search path while `authenticated` can still execute erp writers that
    nothing running with the caller's rights refers to, the gate refuses with GATE_REFUSAL and names them."""
    stored = {}
    for key, value in cur.execute(STORED).fetchall():
        stored.setdefault(key, []).extend(_names(value))
    schemas = sorted(set(declared_schemas) | set(stored.get('pgrst.db_schemas', [])))
    search = sorted(set(declared_extra_search_path) | set(stored.get('pgrst.db_extra_search_path', [])))
    exposed = 'erp' in schemas or 'erp' in search
    inv = inventory(cur)
    blocking = inv['writers_without_invoker_reference'] if exposed else []
    return dict(gate='FABLE-012 (owner D14-9)', declared_schemas=sorted(declared_schemas),
                declared_extra_search_path=sorted(declared_extra_search_path), stored_in_database=stored,
                served_schemas=schemas, extra_search_path=search, erp_exposed=exposed,
                writers_without_invoker_reference=len(inv['writers_without_invoker_reference']),
                ok=not blocking, refusal=GATE_REFUSAL if blocking else None, revoke_first=blocking, changed_anything=False)


if __name__ == '__main__':
    # Local use only: the database URL comes from the environment (local authentication), never from chat.
    import argparse, json, os
    import psycopg
    parser = argparse.ArgumentParser(description='FABLE-012 exposure gate (owner D14-9), read only')
    parser.add_argument('--schemas', default=','.join(RUNBOOK_SCHEMAS), help='Data API exposed schemas about to be applied')
    parser.add_argument('--extra-search-path', default=','.join(RUNBOOK_EXTRA_SEARCH_PATH), help='Data API extra search path about to be applied')
    args = parser.parse_args()
    with psycopg.connect(os.environ['CP7_ACCESS_GATE_PGURL']) as conn, conn.cursor() as cur:
        conn.read_only = True
        result = exposure_gate(cur, _names(args.schemas), _names(args.extra_search_path))
        conn.rollback()
    print(json.dumps({k: v for k, v in result.items()}, indent=1, default=str))
    raise SystemExit(0 if result['ok'] else 3)
