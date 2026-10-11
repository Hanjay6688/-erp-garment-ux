"""New contract-derived K4/K6 cases; no product function or expected writer verdict reused.
Business setup calls the unchanged Native PL5/plan fixture helpers with auditor quantities.
All intrusive controls are confined to a disposable case and rolled back by the harness.
"""
import json,time,uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from queue import Queue
from psycopg import sql
import psycopg
import cp7_p19_plan_v2_cases as plans
import cp7_pl5_history_yield_cases as history
from cases_planning import wilson
from cases_stage import admin,api,check,save,wrap,refusal,read_pages,digest_rows

def tick(cur,kind='analysis',limit='8s'):
    admin(cur)
    prior=cur.execute('show statement_timeout').fetchone()[0]
    cur.execute("select set_config('statement_timeout',%s,true)",(limit,))
    cur.execute('set local role postgres')
    out=cur.execute(sql.SQL('select cp7_ops.{}()').format(sql.Identifier(kind+'_tick'))).fetchone()[0]
    cur.execute('reset role');admin(cur)
    cur.execute("select set_config('statement_timeout',%s,true)",(prior,))
    return out

def request(cur,today,subject=None):
    key=uuid.uuid4()
    s=api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(plans.staged.query(today)),key,subject=subject)
    check(s['state']=='RUNNING','Valid staged request enters RUNNING',observed=s)
    admin(cur);job=cur.execute('select id::text from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()[0]
    return dict(key=key,job=job,subject=subject)

def finish(cur,r):
    ticks=[]
    for _ in range(2000):
        s=api(cur,'erp_cp7_get_staged_analysis_v1',r['key'],subject=r['subject'])
        if s['state']!='RUNNING':break
        ticks.append(tick(cur))
    check(s['state']=='DONE','Only server ticks finish the requested job',last=s,ticks=ticks[-3:])
    r['run']=s['run_id'];return ticks,s

def prove_pass(cur):
    outcomes=[]
    for _ in range(100):
        out=tick(cur,'proof');outcomes.append(out)
        if out['outcome']=='PASS_DONE':return outcomes
        check(out['outcome']=='WINDOW_PROVEN','A healthy proof pass makes progress',observed=out)
    check(False,'Bounded proof pass must terminate',outcomes=outcomes)

def end_rest(cur):
    admin(cur);cur.execute("update cp7_proof_runner.state set rest_until=clock_timestamp()-interval'1 second' where id")

def proofs(cur,groups):
    admin(cur)
    return cur.execute('select group_id::text,id::text,facts_hash from cp7_supply_native.exhaustion_proofs where group_id=any(%s::uuid[]) order by group_id,captured_at,id',(groups,)).fetchall()

def made_groups(cur,today,label):
    p=history.product(cur,label);builder=history.Production(cur,today)
    cuts=[40,42,43,45,47];goods=[38,40,41,44,44]
    groups=[builder.group(p,a,b) for a,b in zip(cuts,goods)]
    return p,builder,groups,cuts,goods

def cases(cur,today):
    def statement_and_role():
        before={t:digest_rows(cur,s,t) for s,t in [('cp7_analysis_stage','runner'),('cp7_proof_runner','state'),('cp7_proof_runner','passes')]}
        denied=[]
        for kind in ('analysis','proof'):
            for limit in ('0','8001ms'):
                out=refusal(cur,lambda:tick(cur,kind,limit))
                check(out['refused'] and out['sqlstate']=='55000' and out['message']=='CP7_RUNNER_STATEMENT_LIMIT_REQUIRED','Missing/excess statement bound rejected before work',kind=kind,limit=limit,observed=out)
                denied.append(out)
        after={t:digest_rows(cur,s,t) for s,t in [('cp7_analysis_stage','runner'),('cp7_proof_runner','state'),('cp7_proof_runner','passes')]}
        check(before==after,'Bad timeout leaves no runner/state/pass row')
        entries=['cp7_ops.analysis_tick()','cp7_ops.proof_tick()','cp7_analysis_stage.run_next()','cp7_proof_runner.prove_next()','cp7_proof_runner.status()']
        role_checks=[]
        for role in ('anon','authenticated','service_role'):
            for entry in entries:
                def attempt():
                    cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
                    cur.execute('select '+entry)
                out=refusal(cur,attempt)
                check(out['refused'] and out['sqlstate']=='42501','Private runner blocked for API role on actual SQL execution',role=role,entry=entry,observed=out)
                role_checks.append(dict(role=role,entry=entry,sqlstate=out['sqlstate']))
        positive=[tick(cur),tick(cur,'proof')]
        check(positive[0]['outcome']=='IDLE' and positive[1]['outcome'] in ('WINDOW_PROVEN','PASS_DONE'),'Scheduler postgres has positive executable controls',observed=positive)
        return dict(timeout_refusals=denied,sql_role_refusals=role_checks,scheduler_controls=positive)

    def claims_restored():
        plans.fixture(cur,today);subject=history.actor(cur);r=request(cur,today,subject)
        prior=[json.dumps(dict(sub=str(uuid.uuid4()),role='authenticated',marker='AS-FULL prior')),str(uuid.uuid4()),'AS-FULL prior singular claim']
        admin(cur);cur.execute('set local role postgres');cur.execute("select set_config('statement_timeout','8s',true)")
        for k,v in zip(('request.jwt.claims','request.jwt.claim.sub','request.jwt.claim'),prior):cur.execute('select set_config(%s,%s,true)',(k,v))
        out=cur.execute('select cp7_ops.analysis_tick()').fetchone()[0]
        actual=[cur.execute('select current_setting(%s,true)',(k,)).fetchone()[0] for k in ('request.jwt.claims','request.jwt.claim.sub','request.jwt.claim')]
        check(actual==prior,'Server work restores every pre-existing request identity field',before=prior,after=actual)
        check(out['job_id']==r['job'] and out['units_done']==1,'Successful unit ran as stored actor, not sentinel prior identity',observed=out)
        admin(cur);n=cur.execute('select count(*) from cp7_analysis_stage.outputs where job_id=%s',(r['job'],)).fetchone()[0]
        check(n==1,'Exactly one actual output for one runner tick',count=n)
        return dict(before=prior,after=actual,tick=out,outputs=n)

    def denied_queue():
        plans.fixture(cur,today);a,b=history.actor(cur),history.actor(cur)
        first=request(cur,today,a);second=request(cur,today,b)
        admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(a,))
        cur.execute("update cp7_analysis_stage.jobs set updated_at=clock_timestamp()-interval'1 minute' where id=%s",(first['job'],))
        out=tick(cur);admin(cur)
        failed=cur.execute('select state,failure_code,units_done,(select count(*) from cp7_analysis_stage.outputs where job_id=j.id) from cp7_analysis_stage.jobs j where id=%s',(first['job'],)).fetchone()
        check(out['job_id']==first['job'] and failed==('FAILED','CP7_ANALYSIS_ACCESS_CHANGED',0,0),'Revoked oldest actor fails without output',tick=out,state=failed)
        ts,done=finish(cur,second);proof=read_pages(cur,second)
        check(all(t.get('job_id')==second['job'] for t in ts),'Denied job never takes another unit or starves remaining actor')
        replay=api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(plans.staged.query(today)),second['key'],subject=b)
        check(replay['run_id']==done['run_id'] and replay['state']=='DONE','Reopening keeps one completed run')
        return dict(denied=failed,healthy_ticks=len(ts),identity=proof['identity'],healthy_run=done['run_id'])

    def honest_heartbeat():
        plans.fixture(cur,today);r=request(cur,today)
        before=api(cur,'erp_cp7_get_staged_analysis_v1',r['key'])
        check(before['server_runner']['active'] is False,'Without a tick server is not advertised active',observed=before['server_runner'])
        tick(cur);live=api(cur,'erp_cp7_get_staged_analysis_v1',r['key'])
        check(live['server_runner']['active'] is True,'A real successful server tick activates liveness')
        admin(cur);cur.execute("update cp7_analysis_stage.runner set last_tick_at=clock_timestamp()-interval'121 seconds'")
        stale=api(cur,'erp_cp7_get_staged_analysis_v1',r['key'])
        check(stale['server_runner']['active'] is False and stale['units_done']==live['units_done'],'Expired liveness never rewinds or invents progress')
        return dict(absent=before['server_runner'],live=live['server_runner'],stale=stale['server_runner'],synthetic_control='Only heartbeat aged 121 seconds, product clock unchanged')

    def proof_history():
        p,builder,gs,cuts,goods=made_groups(cur,today,'ASTRA217');ids=[g['group'] for g in gs]
        owner=history.actor(cur);history.save(cur,history.payload(reason='Independent owner-approved policy fixture'),owner)
        check(proofs(cur,ids)==[],'Fixture contains real finished groups without precomputed proof')
        rounds=prove_pass(cur);rows=proofs(cur,ids)
        check(len(rows)==5 and {r[0] for r in rows}==set(ids),'Server proves every five real completed groups')
        value,_=history.history(cur,p['target'],p['model'],owner);expected=wilson(sum(goods),sum(cuts))
        check(value['level']=='PRODUCT_SIZE' and D(value['lower_bound'])==D(str(expected)),'207 good of217 cut has independent one-sided Wilson lower bound',observed=value,expected=str(expected))
        for g in gs[:2]:
            history.b.chain.bs_action(cur,'REVERSE_DISPOSITION',dict(resolution_id=g['resolution'],change_reason='Astra reopen two independent groups'),history.b.chain.version(cur,'bs_cases',g['case']))
        stale,_=history.history(cur,p['target'],p['model'],owner)
        check(stale['status']=='INSUFFICIENT_SAMPLE' and proofs(cur,ids)==rows,'Old proofs are retained but two reopened groups cannot support yield',observed=stale)
        end_rest(cur);prove_pass(cur);check(proofs(cur,ids)==rows,'Reopened physical work gets no new exhaustion proof')
        for g in gs[:2]:builder.scrap(g,history.az.chain.production.at(g['day'],13,40))
        pending,_=history.history(cur,p['target'],p['model'],owner)
        check(pending['status']=='INSUFFICIENT_SAMPLE','Reclosed groups need proof of their new facts')
        end_rest(cur);prove_pass(cur);new=proofs(cur,ids)
        check(len(new)==7 and set(rows)<=set(new),'Two successor proofs append; originals never overwritten')
        for g in gs[:2]:check(len({r[2] for r in new if r[0]==g['group']})==2,'Changed group facts produce a new hash',group=g['group'])
        final,_=history.history(cur,p['target'],p['model'],owner)
        check(D(final['lower_bound'])==D(str(expected)) and len(final['proofs'])==5,'Reproved facts restore five groups and exact yield, no duplicate sample',observed=final)
        end_rest(cur);prove_pass(cur);check(proofs(cur,ids)==new,'Next unchanged pass adds no duplicate proof')
        protected=refusal(cur,lambda:cur.execute('delete from cp7_proof_runner.passes'))
        check(protected['refused'] and protected['sqlstate']=='55000','Finished pass history is immutable',refusal=protected)
        return dict(cut=sum(cuts),good=sum(goods),expected=str(expected),original=rows,successors=new,pass_count=len(rounds),final=final,synthetic_control='Advance only rest_until on disposable copy; Native reverse and backdated scrap are real commands')

    def proof_failure_atomic():
        _,_,gs,_,_=made_groups(cur,today,'ASTRA_STOP');ids=[g['group'] for g in gs];fail_at=sorted(ids)[2];notices=[]
        def notice(d):notices.append(d.message_primary)
        cur.connection.add_notice_handler(notice)
        admin(cur)
        cur.execute("create function pg_temp.astra_proof_fault() returns trigger language plpgsql as $$begin raise notice 'ASTRA_PROOF_ATTEMPT %',new.group_id; if new.group_id::text=TG_ARGV[0] then raise exception using errcode='57014',message='ASTRA_TEST_PROOF_STOP';end if;return new;end$$")
        cur.execute(sql.SQL('create trigger astra_proof_fault before insert on cp7_supply_native.exhaustion_proofs for each row execute function pg_temp.astra_proof_fault({})').format(sql.Literal(fail_at)))
        before=proofs(cur,ids);stopped=tick(cur,'proof');after=proofs(cur,ids)
        check(stopped['outcome']=='WINDOW_STOPPED' and stopped['window_size']==100,'Stopped initial window is halved, not declared proven',result=stopped)
        check(any(fail_at in n for n in notices) and sum(any(g in n for g in ids) for n in notices)>=3,'Failure actually reached third test group after earlier attempted inserts',notices=notices)
        check(before==after==[] and stopped['after_id'] is None,'Partial proof inserts roll back, cursor does not skip the stopped window',result=stopped)
        cur.execute('drop trigger astra_proof_fault on cp7_supply_native.exhaustion_proofs');cur.execute('drop function pg_temp.astra_proof_fault()');cur.connection.remove_notice_handler(notice)
        success=prove_pass(cur);check({r[0] for r in proofs(cur,ids)}==set(ids),'After transient injected fault every original group is proven')
        return dict(stopped=stopped,observed_insert_attempts=notices,recovered=success,injection='Additional disposable BEFORE INSERT trigger, SQLSTATE57014 at third real group; no product function changed')

    return [wrap('ASF-01-RUNNER-ACL-TIMEOUT',statement_and_role),wrap('ASF-02-K4-CLAIMS',claims_restored),wrap('ASF-03-K4-DENIED-QUEUE',denied_queue),wrap('ASF-04-K4-HEARTBEAT',honest_heartbeat),wrap('ASF-05-K6-217-PCS',proof_history),wrap('ASF-06-K6-PARTIAL-STOP',proof_failure_atomic)]

def races(tools,today):
    def cold_k4():
        with tools.connect() as conn,conn.cursor() as cur:
            check(cur.execute('select count(*) from cp7_analysis_stage.runner').fetchone()[0]==0,'Fresh installed clone has no heartbeat, no trigger bypass')
            plans.fixture(cur,today);a=request(cur,today);b=request(cur,today);conn.commit()
        q=Queue();observed=[]
        def work():
            with tools.connect() as conn,conn.cursor() as cur:
                q.put(cur.execute('select pg_backend_pid()').fetchone()[0]);out=tick(cur);conn.commit();return out
        holder=tools.connect()
        try:
            with holder.cursor() as cur:cur.execute('lock cp7_analysis_stage.outputs in access exclusive mode')
            with ThreadPoolExecutor(max_workers=2) as pool:
                one=pool.submit(work);pid1=q.get(timeout=5)
                with tools.connect(autocommit=True) as obs,obs.cursor() as cur:
                    def waiting(pid):
                        return cur.execute("select locktype,mode,relation::regclass::text from pg_locks where pid=%s and not granted",(pid,)).fetchall()
                    until=time.monotonic()+2
                    while not waiting(pid1) and time.monotonic()<until:time.sleep(.02)
                    two=pool.submit(work);pid2=q.get(timeout=5);until=time.monotonic()+2
                    while not waiting(pid2) and time.monotonic()<until:time.sleep(.02)
                    observed=[dict(pid=pid1,waits=waiting(pid1)),dict(pid=pid2,waits=waiting(pid2))]
                holder.commit();results=[one.result(15),two.result(15)]
        finally:holder.rollback();holder.close()
        save('ASF-07-K4-COLD-LOCKS',dict(observed=observed,results=results))
        check(all(any(r[0]=='relation' and r[2]=='cp7_analysis_stage.outputs' for r in x['waits']) and not any(r[0]=='transactionid' for r in x['waits']) for x in observed),'Both ticks reach distinct output inserts without waiting for heartbeat transaction',observed=observed)
        check({x['job_id'] for x in results}=={a['job'],b['job']} and all(x['units_done']==1 for x in results),'Two concurrent ticks store one unit in each of two jobs',results=results)
        return dict(lock_barrier='ACCESS EXCLUSIVE outputs only, released before 8-second statement bound',observed=observed,results=results)

    def k6_busy():
        with tools.connect() as hold,hold.cursor() as cur:
            check(cur.execute('select count(*) from cp7_proof_runner.state').fetchone()[0]==0,'Fresh K6 state empty')
            cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:K6_PROOF_RUNNER',0))")
            with tools.connect() as other,other.cursor() as q:
                start=time.monotonic();out=tick(q,'proof');ms=(time.monotonic()-start)*1000
                check(out['outcome']=='BUSY' and out['ran'] is False,'Busy proof lock skips immediately',observed=out)
                check(q.execute('select count(*) from cp7_proof_runner.state').fetchone()[0]==0,'Busy tick reads no source and creates no state')
                other.commit()
            hold.rollback()
        return dict(result=out,elapsed_ms=ms,holder_released_after_second_tick_return=True)

    return [wrap('ASF-07-K4-COLD-LOCKS',cold_k4),wrap('ASF-08-K6-BUSY',k6_busy)]
