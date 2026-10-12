"""Fable core scenario on the full CP7 composition (d0b9e9c2). Own oracles; writer helpers only for fixtures/RPC plumbing.
Native (savepoint group):
  WILSON_PERMILLE_ONE_SIDED_90_FLOOR   PL-5 B: Fable recomputes the one-sided 90% Wilson lower bound, floored to 0.1%; never 100%.
  PL5_NO_POLICY_IS_PENDING             fresh install: policy state PENDING_POLICY_VALUE (no invented yield).
  RUN_NEXT_REFUSES_WITHOUT_8S_LIMIT    K4 runner refuses when statement_timeout is 0 or > 8 s (CP7_RUNNER_STATEMENT_LIMIT_REQUIRED).
  AI_BRIEF_RUNS_READ_ONLY              Tanya AI v2 brief completes inside a read-only transaction (any write would raise 25006).
  REPORT_V2_SEALED_ONCE_IMMUTABLE      Business Report v2: publication rows immutable (55000 CP7_RUN_IMMUTABLE), replay adds no job.
Races (fresh copy each):
  F01_V1_HOLDS_V2_REFUSED / F01_V2_HOLDS_V1_REFUSED  one capacity lock across plan v1 and v2; committed total never exceeds capacity.
  BACKUP_VERIFY_UNDER_LIVE_WRITES      cp7_nightly_backup compares the LIVE source after restore (suspected D1): a runner heartbeat
                                       during the backup is expected to make restore_verified=false.
  BACKUP_SCRATCH_DROPS_FOREIGN_DB      --scratch naming an existing unrelated database drops it (suspected D2).
  CLEANUP_LOCK_VS_RUNNING_STEP         clean_done holds SHARE ROW EXCLUSIVE on intermediates; a RUNNING job's step under 8 s waits/cancels (D5).
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import json,math,os,tempfile,threading,time,uuid
from pathlib import Path
from urllib.parse import urlparse
import psycopg
import cp7_p19_staged_cases as staged
import cp7_p19_plan_v2_cases as planv2
import cp7_plan_native_cases as plan
import cp7_p19_report_v2_cases as reportv2
import cp7_p19_ai_v2_cases as aiv2
import cp7_k4_runner_cases as k4
import cp7_nightly_backup as nightly
auth,b=staged.auth,staged.b
Z=1.2815515655446004  # one-sided 90% normal quantile

def wilson_floor_permille(k,n):
    if n<=0:return 0
    p=k/n;z2=Z*Z
    lo=(p+z2/(2*n)-Z*math.sqrt(p*(1-p)/n+z2/(4*n*n)))/(1+z2/n)
    return max(0,math.floor(lo*1000+1e-9))

def refusal(cur,sql,params=None):
    """Run sql inside a savepoint; return (sqlstate, first line) or ('OK', repr(result))."""
    cur.execute('savepoint fable_ref')
    try:
        r=cur.execute(sql,params).fetchone();cur.execute('release savepoint fable_ref');return ('OK',repr(r)[:200])
    except psycopg.Error as e:
        cur.execute('rollback to savepoint fable_ref');b.api.admin(cur);return (e.sqlstate,str(e).splitlines()[0][:160])

def cases(cur,today):
    def wilson():
        b.api.admin(cur);rows={}
        for k,n in ((180,200),(200,200),(1,1),(0,200),(5,5),(190,200),(1000000,1000000),(7,9)):
            got=cur.execute('select cp7_plan_native.wilson_permille(%s,%s)',(k,n)).fetchone()[0];exp=wilson_floor_permille(k,n)
            rows[f'{k}/{n}']=dict(product=got,fable=exp,delta=(got-exp) if got is not None else None)
        never_100=all(r['product'] is not None and r['product']<1000 for r in rows.values())
        exact=all(r['delta']==0 for r in rows.values());close=all(r['delta'] is not None and abs(r['delta'])<=1 for r in rows.values())
        return dict(status='PASS' if exact and never_100 else ('COUNTEREXAMPLE' if close and never_100 else 'FAIL'),rows=rows,never_100=never_100,z=Z)
    def pending():
        p=staged.limited(cur,'erp_cp7_get_history_yield_policy_v1',())
        return dict(status='PASS' if p.get('state')=='PENDING_POLICY_VALUE' else 'FAIL',state=p.get('state'),revision=p.get('revision'))
    def limit_required():
        b.api.admin(cur);prior=cur.execute('show statement_timeout').fetchone()[0];out={}
        for t in ('0','9s','8001ms','8s'):
            cur.execute("select set_config('statement_timeout',%s,true)",(t,))
            out[t]=refusal(cur,'select cp7_analysis_stage.run_next()')
            cur.execute("select set_config('statement_timeout',%s,true)",(prior,))
        ok=all(out[t][0]=='55000' and 'CP7_RUNNER_STATEMENT_LIMIT_REQUIRED' in out[t][1] for t in ('0','9s','8001ms')) and out['8s'][0]=='OK'
        return dict(status='PASS' if ok else 'FAIL',outcomes=out)
    def ai_read_only():
        key,_,done,_=staged.staged_done(cur,today);run=done['run_id']
        job=staged.job_row(cur,key)['id']
        try:keys=[k for _,k,_,_ in aiv2.index_rows(cur,dict(run=run,job=job))][:3]
        except Exception as e:keys=[];print('FABLE_AI_KEYS_FALLBACK',str(e)[:120],flush=True)
        b.api.admin(cur);cur.execute("select set_config('transaction_read_only','on',true)")
        try:
            brief=staged.limited(cur,'erp_cp7_get_staged_ai_brief_v1',(run,json.dumps(keys)))
            out=dict(status='PASS',read_only_call_ok=True,data_as_of=brief.get('data_as_of'),finance=brief.get('finance'),priority_len=len(brief.get('priority') or []))
        except psycopg.Error as e:
            out=dict(status='FAIL' if e.sqlstate=='25006' else 'INCOMPLETE',sqlstate=e.sqlstate,error=str(e).splitlines()[0][:200])
        finally:cur.execute("select set_config('transaction_read_only','off',true)");b.api.admin(cur)
        return out
    def report_sealed():
        r=reportv2.staged_run(cur,today);key,done,_=reportv2.published(cur,r);pid=done['publication_id']
        b.api.admin(cur)
        upd=refusal(cur,"update cp7_analysis_stage.report_publications set published_at=published_at where id=%s",(pid,))
        dele=refusal(cur,"delete from cp7_analysis_stage.report_publications where id=%s",(pid,))
        again=reportv2.step(cur,key);replay=reportv2.publish(cur,reportv2.payload(r),key)
        b.api.admin(cur);jobs=cur.execute('select count(*) from cp7_analysis_stage.report_jobs where request_id=%s',(key,)).fetchone()[0]
        pubs=cur.execute('select count(*) from cp7_analysis_stage.report_publications where job_id=(select id from cp7_analysis_stage.report_jobs where request_id=%s)',(key,)).fetchone()[0]
        ok=upd[0]=='55000' and dele[0]=='55000' and again['state']=='DONE' and again['publication_id']==pid and replay['publication_id']==pid and jobs==1 and pubs==1
        return dict(status='PASS' if ok else 'FAIL',update=upd,delete=dele,step_after_done=again['state'],replay_same_publication=replay.get('publication_id')==pid,jobs=jobs,publications=pubs)
    return [('FABLE_CORE:WILSON_PERMILLE_ONE_SIDED_90_FLOOR',wilson),('FABLE_CORE:PL5_NO_POLICY_IS_PENDING',pending),
            ('FABLE_CORE:RUN_NEXT_REFUSES_WITHOUT_8S_LIMIT',limit_required),('FABLE_CORE:AI_BRIEF_RUNS_READ_ONLY',ai_read_only),
            ('FABLE_CORE:REPORT_V2_SEALED_ONCE_IMMUTABLE',report_sealed)]

def races(tools,today):
    def wait_blocked(pid,seconds=10):
        with tools.connect(autocommit=True) as c,c.cursor() as cur:
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                w=cur.execute("select wait_event_type,wait_event from pg_stat_activity where pid=%s",(pid,)).fetchone()
                if w and w[0]=='Lock':return w[1]
                time.sleep(.05)
        return None
    def f01(first_kind,second_kind):
        with tools.connect() as conn,conn.cursor() as cur:
            first,second=planv2.two(cur,today);c=int(D(first['options']['capacity_pcs']));a,b_=planv2.capacity_split(first,second)
            mk=lambda kind,x,pcs:planv2.v1_draft(cur,x,pcs,today) if kind=='v1' else planv2.save(cur,planv2.with_pcs(x['payload'],pcs))
            d1,d2=mk(first_kind,first,a),mk(second_kind,second,b_);conn.commit()
        ap=lambda kind:(plan.apply if kind=='v1' else planv2.apply)
        holder=tools.connect();hc=holder.cursor();held=ap(first_kind)(hc,plan.action(d1))
        assert held['state']=='NATIVE_DRAFT_CREATED',held
        pid={}
        def second_apply():
            with tools.connect() as conn,conn.cursor() as cur:
                pid['v']=cur.execute('select pg_backend_pid()').fetchone()[0]
                try:r=ap(second_kind)(cur,plan.action(d2));conn.commit();return dict(state=r.get('state'))
                except psycopg.Error as e:conn.rollback();return dict(sqlstate=e.sqlstate,error=e.diag.message_primary,detail=e.diag.message_detail)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                job=pool.submit(second_apply)
                for _ in range(100):
                    if 'v' in pid:break
                    time.sleep(.05)
                waited=wait_blocked(pid['v'])
                holder.commit();result=job.result(90)
        finally:holder.close()
        with tools.connect() as conn,conn.cursor() as cur:
            total=int(planv2.planned_pcs(cur,[d1,d2]));intents=planv2.intents(cur)
        refused=result.get('sqlstate')=='40001'
        ok=total<=c and refused and waited is not None
        return dict(status='PASS' if ok else 'FAIL',capacity=c,first=(first_kind,a),second=(second_kind,b_),second_waited_on=waited,second_result=result,committed_total=total,intents=intents)
    def backup_live():
        u=urlparse(tools.admin);database=u.path.lstrip('/');container=os.environ.get('CP6_DATABASE_CONTAINER','supabase_db_cp5-local')
        stop=threading.Event();ticks=[]
        def heartbeat():
            with tools.connect() as conn,conn.cursor() as cur:
                while not stop.is_set():
                    try:ticks.append(k4.tick(cur)['outcome']);conn.commit()
                    except Exception as e:ticks.append('ERR '+str(e)[:80]);conn.rollback()
                    time.sleep(.3)
        t=threading.Thread(target=heartbeat,daemon=True);t.start();time.sleep(1)
        try:
            with tempfile.TemporaryDirectory(prefix='fable-nightly-') as dest:
                rec=nightly.backup(tools.admin,database,'fable_backup_verify',dest,keep=14,container=container)
        finally:stop.set();t.join(30)
        differ=(rec.get('data') or {}).get('differ') or {}
        return dict(status='PASS' if rec.get('restore_verified') is True else 'FAIL',restore_verified=rec.get('restore_verified'),differ_tables=sorted(differ),
                    unexplained=(rec.get('restore')or{}).get('unexplained'),error=rec.get('error'),heartbeats=len(ticks),tick_outcomes=sorted(set(ticks))[:5])
    def backup_scratch():
        u=urlparse(tools.admin);database=u.path.lstrip('/');container=os.environ.get('CP6_DATABASE_CONTAINER','supabase_db_cp5-local')
        victim='fable_victim_db'
        with tools.connect(autocommit=True) as c,c.cursor() as cur:
            cur.execute('drop database if exists '+victim);cur.execute('create database '+victim)
        try:
            with tools.connect(autocommit=True) as c,c.cursor() as cur:
                before=cur.execute("select count(*) from pg_database where datname=%s",(victim,)).fetchone()[0]
            with tempfile.TemporaryDirectory(prefix='fable-nightly-') as dest:
                rec=nightly.backup(tools.admin,database,victim,dest,keep=14,container=container)
            with tools.connect(autocommit=True) as c,c.cursor() as cur:
                after=cur.execute("select count(*) from pg_database where datname=%s",(victim,)).fetchone()[0]
        finally:
            with tools.connect(autocommit=True) as c,c.cursor() as cur:cur.execute('drop database if exists '+victim+' with (force)')
        return dict(status='PASS' if (before==1 and after==1) else 'FAIL',victim_existed_before=before==1,victim_exists_after=after==1,backup_error=rec.get('error'),restore_verified=rec.get('restore_verified'))
    def cleanup_lock():
        with tools.connect() as conn,conn.cursor() as cur:
            dkey,_,done,_=staged.staged_done(cur,today);conn.commit();djob=staged.job_row(cur,dkey)['id']
            rkey=uuid.uuid4();staged.checked(staged.request(cur,today,rkey),rkey,'RUNNING');conn.commit()
        holder=tools.connect();hc=holder.cursor();b.api.admin(hc)
        try:
            cleaned=hc.execute('select cp7_analysis_stage.clean_done(%s)',(djob,)).fetchone()[0]
            with tools.connect() as conn,conn.cursor() as cur:
                t0=time.monotonic()
                try:s=staged.step(cur,rkey);conn.commit();outcome=dict(state=s['state'],units_done=s['units_done'],unit_attempts=s.get('unit_attempts'))
                except psycopg.Error as e:conn.rollback();outcome=dict(sqlstate=e.sqlstate,error=str(e).splitlines()[0][:160])
                seconds=round(time.monotonic()-t0,2)
        finally:holder.rollback();holder.close()
        blocked=seconds>2 or outcome.get('sqlstate')=='57014' or (outcome.get('unit_attempts') or 0)>0
        return dict(status='FAIL' if blocked else 'PASS',cleanup_state=cleaned.get('state'),step_seconds=seconds,step_outcome=outcome,blocked_by_cleanup=blocked)
    return [('FABLE_CORE:F01_V1_HOLDS_V2_REFUSED',lambda:f01('v1','v2')),('FABLE_CORE:F01_V2_HOLDS_V1_REFUSED',lambda:f01('v2','v1')),
            ('FABLE_CORE:BACKUP_VERIFY_UNDER_LIVE_WRITES',backup_live),('FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB',backup_scratch),
            ('FABLE_CORE:CLEANUP_LOCK_VS_RUNNING_STEP',cleanup_lock)]
