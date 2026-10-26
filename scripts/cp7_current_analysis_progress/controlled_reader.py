"""Actual PostgreSQL reader mechanics with controlled dependencies, not ERP/Auth acceptance."""
from pathlib import Path
from urllib.parse import urlparse
from time import perf_counter
import hashlib,json,os,subprocess,traceback
import psycopg

ROOT=Path(__file__).resolve().parent
URL=os.environ['PROGRESS_CONTROLLED_PGURL'];parsed=urlparse(URL)
assert parsed.hostname=='127.0.0.1' and parsed.port==5432 and parsed.path=='/cp7_progress_controlled'
ACTOR='00000000-0000-0000-0000-000000000001';REQUEST='00000000-0000-0000-0000-000000000002'
JOB='00000000-0000-0000-0000-000000000003';CAPTURE='00000000-0000-0000-0000-000000000004'
SQL=ROOT/'progress.prepared.sql'
SETUP="""
create role cp7_capture nologin;
create role authenticated nologin;
create role anon nologin;
create role service_role nologin;
create schema cp7_schedule_native authorization cp7_capture;
create schema cp7_analysis_stage authorization cp7_capture;
create schema cp7_finance_capture authorization cp7_capture;
create table cp7_analysis_stage.jobs(id uuid primary key,actor uuid not null,request_id uuid not null,
 reference jsonb not null,state text not null,created_at timestamptz not null,updated_at timestamptz not null,
 unique(actor,request_id));
create table cp7_finance_capture.captures(id uuid primary key,actor uuid not null,owner_kind text not null,owner_id uuid not null,
 created_at timestamptz not null,updated_at timestamptz not null,finished_at timestamptz,
 unit_attempts integer not null,report_ms numeric,unique(owner_kind,owner_id));
alter table cp7_analysis_stage.jobs owner to cp7_capture;
alter table cp7_finance_capture.captures owner to cp7_capture;
create function cp7_schedule_native.access_now(boolean)returns jsonb language sql volatile as $$
 select jsonb_build_object('actor',current_setting('test.actor'),'identity','controlled')$$;
create function cp7_analysis_stage.report_finance_access(jsonb,boolean)returns boolean language sql volatile as $$
 select current_setting('test.finance_allowed')='true'$$;
create function cp7_analysis_stage.status(p_job uuid)returns jsonb language plpgsql volatile as $$
declare j cp7_analysis_stage.jobs%rowtype;c cp7_finance_capture.captures%rowtype;s jsonb;
begin
 select *into j from cp7_analysis_stage.jobs where id=p_job;
 select *into c from cp7_finance_capture.captures where owner_id=p_job;
 s:=jsonb_build_object('request_id',j.request_id,'state',j.state);
 if j.reference->>'finance_sidecar_mode'='STAGED'then
  s:=s||jsonb_build_object('finance_capture',case when current_setting('test.finance_allowed')='true'
   then jsonb_build_object('state','RUNNING','capture',jsonb_build_object('capture_id',c.id))
   else jsonb_build_object('state','ACCESS_REVOKED','capture',null,'result',null)end);
 end if;
 if current_setting('test.revoke_during_read',true)='true'then perform set_config('test.finance_allowed','false',true);end if;
 return s;
end$$;
grant execute on function cp7_schedule_native.access_now(boolean),cp7_analysis_stage.report_finance_access(jsonb,boolean),cp7_analysis_stage.status(uuid)to cp7_capture;
"""

def context(cur,actor=ACTOR,finance=True,role='authenticated'):
    cur.execute('set local statement_timeout=\'8s\'')
    cur.execute('select set_config(\'test.actor\',%s,true),set_config(\'test.finance_allowed\',%s,true)',(actor,str(finance).lower()))
    assert role in ('authenticated','anon','service_role')
    cur.execute('set local role '+role)

def read(cur):return cur.execute('select public.erp_cp7_get_frozen_analysis_progress_v1(%s)',(REQUEST,)).fetchone()[0]
def stored(cur):
    return {table:cur.execute('select to_jsonb(t)from '+table+' t order by id').fetchall()
            for table in ('cp7_analysis_stage.jobs','cp7_finance_capture.captures')}

def run():
    report=dict(status='INCOMPLETE',policy_id='D17-18-20261026',candidate_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_sha256=hashlib.sha256(SQL.read_bytes()).hexdigest(),controlled_dependencies=True,actual_PostgreSQL=True,
        actual_Auth_HTTP=False,full_ERP_composition=False,production_go=False,cases={})
    try:
        with psycopg.connect(URL)as db,db.cursor()as cur:
            assert cur.execute('select current_database()').fetchone()==('cp7_progress_controlled',)
            report['postgres_version']=cur.execute('show server_version').fetchone()[0]
            cur.execute(SETUP,prepare=False)
            cur.execute("insert into cp7_analysis_stage.jobs values(%s,%s,%s,%s,'RUNNING','2026-10-26T00:00:00Z','2026-10-26T00:00:02Z')",(JOB,ACTOR,REQUEST,json.dumps(dict(bounded_request_contract='cp7.bounded-analysis-request.v2',finance_sidecar_mode='STAGED'))))
            cur.execute("insert into cp7_finance_capture.captures values(%s,%s,'STAGED_ANALYSIS',%s,'2026-10-26T00:00:00Z','2026-10-26T00:00:02Z',null,0,null)",(CAPTURE,ACTOR,JOB))
            cur.execute(SQL.read_text(),prepare=False);before=stored(cur);db.commit()
            context(cur);start=perf_counter();value=read(cur);elapsed=(perf_counter()-start)*1000
            assert elapsed<8000 and value['contract_version']=='cp7.frozen-analysis-progress.v1'
            assert value['finance']['capture_id']==CAPTURE and value['finance']['worker_observation']=='NO_LOCK_OBSERVED'
            assert value['operational']['worker_observation']=='NOT_EXPOSED'
            assert value['status']['request_id']==REQUEST and value['production_go']is False
            report['cases']['OWN_STATUS_AND_SERVER_CLOCK']=dict(status='PASS',milliseconds=elapsed,result=value);db.rollback()
            context(cur,finance=False);value=read(cur)
            assert value['finance']is None and value['status']['finance_capture']['state']=='ACCESS_REVOKED'
            report['cases']['FINANCE_DENIAL_REDACTS_ALL_TELEMETRY']=dict(status='PASS');db.rollback()
            for role in ('anon','service_role'):
                context(cur,role=role)
                try:read(cur)
                except psycopg.errors.InsufficientPrivilege:pass
                else:raise AssertionError('UNAUTHENTICATED_EXECUTE_ALLOWED:'+role)
                report['cases']['DENY_'+role]=dict(status='PASS');db.rollback()
            context(cur,actor='00000000-0000-0000-0000-000000000009')
            try:read(cur)
            except psycopg.errors.RaiseException as error:assert error.diag.message_primary=='CP7_ANALYSIS_JOB_UNAVAILABLE'
            else:raise AssertionError('FOREIGN_REQUEST_VISIBLE')
            report['cases']['FOREIGN_REQUEST_REFUSED']=dict(status='PASS');db.rollback()
            context(cur);cur.execute("select set_config('test.revoke_during_read','true',true)")
            try:read(cur)
            except psycopg.errors.InsufficientPrivilege:pass
            else:raise AssertionError('CURRENT_FINANCE_ACCESS_NOT_RECHECKED')
            report['cases']['DEPENDENCY_REVOCATION_RECHECK']=dict(status='PASS',controlled_dependency=True);db.rollback()
            with psycopg.connect(URL)as worker,worker.cursor()as holder:
                holder.execute("set local statement_timeout='8s'")
                holder.execute("select pg_advisory_xact_lock(hashtextextended('CP7:FINANCE_CAPTURE_STEP:'||%s,0))",(CAPTURE,))
                context(cur);value=read(cur)
                assert value['finance']['worker_observation']=='LOCK_HELD'
                report['cases']['ACTUAL_OTHER_BACKEND_WORKER_LOCK']=dict(status='PASS');db.rollback();worker.rollback()
            context(cur);value=read(cur);assert value['finance']['worker_observation']=='NO_LOCK_OBSERVED';db.rollback()
            cur.execute("set transaction isolation level repeatable read");context(cur)
            try:read(cur)
            except psycopg.errors.RaiseException as error:assert error.diag.message_primary=='CP7_FRESH_ACCESS_REQUIRED'
            else:raise AssertionError('STALE_ACCESS_ISOLATION_ALLOWED')
            report['cases']['REPEATABLE_READ_REFUSED']=dict(status='PASS');db.rollback()
            assert stored(cur)==before
            report['cases']['ALL_CONTROLLED_ROWS_UNCHANGED']=dict(status='PASS')
            report['status']='PASS_CONTROLLED_SQL_ONLY'
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    (ROOT/'CONTROLLED_SQL_RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k)for k in ('status','candidate_commit','error','production_go')}|{'cases':len(report['cases'])}))
    return 0 if report['status']=='PASS_CONTROLLED_SQL_ONLY'else 1

if __name__=='__main__':raise SystemExit(run())
