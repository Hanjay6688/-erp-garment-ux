"""Fable smoke scenario on the full CP7 composition (d0b9e9c2): validates the Fable runtime end to end and carries four
real oracles of the area "Akses dan pemulihan" / "Jadwal server":
  * no function in any cp7_* schema is reachable (schema USAGE and EXECUTE) by anon, authenticated or service_role;
  * every zero-argument function of cp7_ops refuses anon/authenticated/service_role at the SQL level (42501);
  * cp7_ops.schedules() equals the declaration docs/cp7/k3/K3_CLEANUP.json#schedules byte for byte (as JSON);
  * the staged analysis request is idempotent per request UUID (sequential and concurrent): one job, same run.
Fixtures reuse the writer's helpers (cp7_p19_staged_cases.query/request/status, auth, b); oracles are Fable's."""
from concurrent.futures import ThreadPoolExecutor
import json,uuid
import psycopg
import cp7_p19_staged_cases as staged
import cp7_analysis_bundle as bundle
auth,b=staged.auth,staged.b
PRINCIPALS=['anon','authenticated','service_role']
OPS_FUNCTIONS=('schedules','cleanup_tick','retention_tick','analysis_tick','proof_tick')

def cases(cur,today):
    def reach():
        b.api.admin(cur)
        schemas=cur.execute("""select n.nspname,coalesce(array_agg(r order by r) filter (where has_schema_privilege(r,n.oid,'USAGE')),'{}')
            from pg_namespace n cross join unnest(%s::text[]) r where n.nspname like 'cp7%%' group by 1 order by 1""",(PRINCIPALS,)).fetchall()
        reachable=cur.execute("""select n.nspname,p.oid::regprocedure::text,array_agg(r order by r)
            from pg_proc p join pg_namespace n on n.oid=p.pronamespace cross join unnest(%s::text[]) r
            where n.nspname like 'cp7%%' and has_schema_privilege(r,n.oid,'USAGE') and has_function_privilege(r,p.oid,'EXECUTE')
            group by 1,2 order by 1,2""",(PRINCIPALS,)).fetchall()
        tables=cur.execute("""select n.nspname,c.relname,array_agg(r order by r)
            from pg_class c join pg_namespace n on n.oid=c.relnamespace cross join unnest(%s::text[]) r
            where n.nspname like 'cp7%%' and c.relkind in ('r','v','m','p') and has_schema_privilege(r,n.oid,'USAGE')
              and (has_table_privilege(r,c.oid,'SELECT') or has_table_privilege(r,c.oid,'INSERT') or has_table_privilege(r,c.oid,'UPDATE') or has_table_privilege(r,c.oid,'DELETE'))
            group by 1,2 order by 1,2""",(PRINCIPALS,)).fetchall()
        return dict(status='PASS' if not reachable and not tables else 'FAIL',cp7_schemas=len(schemas),
            schema_usage_by_public_roles={s:list(by) for s,by in schemas if by},
            reachable_functions=[dict(schema=s,function=f,by=list(by)) for s,f,by in reachable],
            reachable_tables=[dict(schema=s,table=t,by=list(by)) for s,t,by in tables])
    def ops_refuse():
        b.api.admin(cur)
        present=[r[0] for r in cur.execute("select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_ops' and p.pronargs=0 order by 1").fetchall()]
        outcomes={};ok=True
        for role in PRINCIPALS:
            for fn in present:
                cur.execute('savepoint fable_ops')
                try:
                    cur.execute('set local role '+role);cur.execute('select cp7_ops.'+fn+'()')
                    outcomes[role+':'+fn]='EXECUTED';ok=False
                except psycopg.Error as e:
                    outcomes[role+':'+fn]=(e.sqlstate or '?')+' '+str(e).splitlines()[0][:80]
                    if e.sqlstate!='42501':ok=False
                finally:
                    cur.execute('rollback to savepoint fable_ops');cur.execute('reset role');b.api.admin(cur);cur.execute('release savepoint fable_ops')
        missing=sorted(set(OPS_FUNCTIONS)-set(present))
        return dict(status='PASS' if ok and not missing else 'FAIL',functions_present=present,missing_declared=missing,outcomes=outcomes)
    def schedules_match():
        b.api.admin(cur)
        decl=json.loads((bundle.ROOT/'docs/cp7/k3/K3_CLEANUP.json').read_text())['schedules']
        got=cur.execute('select cp7_ops.schedules()').fetchone()[0]
        same=json.dumps(got,sort_keys=True)==json.dumps(decl,sort_keys=True)
        names=[s.get('name') for s in (got if isinstance(got,list) else [])]
        return dict(status='PASS' if same and len(names)==4 and len(set(names))==4 else ('COUNTEREXAMPLE' if type(got)!=type(decl) else 'FAIL'),
            declared_names=[s['name'] for s in decl],returned_names=names,equal_as_json=same,returned=got if not same else None)
    def same_key_sequential():
        key=uuid.uuid4()
        first=staged.checked(staged.request(cur,today,key),key,'RUNNING')
        second=staged.checked(staged.request(cur,today,key),key)
        b.api.admin(cur)
        n=cur.execute('select count(*) from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()[0]
        return dict(status='PASS' if n==1 and first['request_id']==second['request_id'] and second['units_done']>=first['units_done'] else 'FAIL',jobs=n,
            first_state=first['state'],second_state=second['state'])
    def cron_not_installed():
        b.api.admin(cur)
        has=cur.execute("select exists(select 1 from pg_namespace where nspname='cron')").fetchone()[0]
        n=cur.execute("select count(*) from cron.job where jobname like 'cp7-%%'").fetchone()[0] if has else None
        return dict(status='PASS' if (not has or n==0) else 'FAIL',cron_schema_present=has,cp7_jobs_scheduled=n)
    return [('FABLE_SMOKE:CP7_SCHEMAS_UNREACHABLE_BY_PUBLIC_ROLES',reach),('FABLE_SMOKE:CP7_OPS_REFUSES_PUBLIC_ROLES_42501',ops_refuse),
            ('FABLE_SMOKE:SCHEDULES_EQUAL_K3_DECLARATION',schedules_match),('FABLE_SMOKE:STAGED_SAME_KEY_SEQUENTIAL_ONE_JOB',same_key_sequential),
            ('FABLE_SMOKE:NO_CP7_PG_CRON_JOB_IN_COPY',cron_not_installed)]

def races(tools,today):
    def same_key_concurrent():
        key=uuid.uuid4();outcomes=[]
        def op(i):
            try:
                with tools.connect() as conn,conn.cursor() as cur:
                    r=staged.request(cur,tools.today,key);conn.commit();return ('OK',r['request_id'],r['state'])
            except psycopg.Error as e:return ('ERR',e.sqlstate,str(e).splitlines()[0][:120])
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=[f.result(90) for f in [pool.submit(op,0),pool.submit(op,1)]]
        with tools.connect() as conn,conn.cursor() as cur:
            b.api.admin(cur);n=cur.execute('select count(*) from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()[0];conn.commit()
        raw_unique=[o for o in outcomes if o[0]=='ERR' and o[1]=='23505']
        return dict(status='PASS' if n==1 and not raw_unique else 'FAIL',jobs=n,outcomes=outcomes,raw_unique_violation_leaked=bool(raw_unique))
    return [('FABLE_SMOKE:RACE_SAME_KEY_CONCURRENT_ONE_JOB',same_key_concurrent)]

def http_cases(http,today):
    def ops_unreachable():
        owner=http.login('OWNER','fable-smoke');statuses={}
        for fn in OPS_FUNCTIONS:
            a=owner.rpc(fn,{});n=http.anon_rpc(fn,{});statuses[fn]=dict(owner=a['status'],anon=n['status'])
        ok=all(v['owner']>=400 and v['anon']>=400 for v in statuses.values())
        return dict(status='PASS' if ok else 'FAIL',statuses=statuses)
    def owner_request_running():
        owner=http.login('OWNER','fable-smoke-2');key=str(uuid.uuid4())
        first=owner.rpc('erp_cp7_request_staged_analysis_v1',dict(p_query=staged.query(today),p_request=key))
        got=owner.rpc('erp_cp7_get_staged_analysis_v1',dict(p_request=key))
        ok=first['status']==200 and first['body'].get('state')=='RUNNING' and got['status']==200 and got['body'].get('request_id')==key
        return dict(status='PASS' if ok else 'FAIL',first_status=first['status'],first_state=first['body'].get('state') if isinstance(first.get('body'),dict) else first.get('body'),get_status=got['status'])
    return [('FABLE_SMOKE:HTTP_CP7_OPS_UNREACHABLE',ops_unreachable),('FABLE_SMOKE:HTTP_OWNER_STAGED_REQUEST_RUNNING',owner_request_running)]
