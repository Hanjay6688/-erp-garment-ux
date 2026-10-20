// LOCAL_PGLITE18_DEV: original dispatcher, SYNTHETIC job/step contracts.
// Development only. Not Native, concurrent-session or pg_cron evidence.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {resolve} from 'node:path'
const {PGlite}=await import(process.env.PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),repo=resolve(process.argv[2]??'.')
const one=async(sql,args=[])=>Object.values((await db.query(sql,args)).rows[0]??{})[0]
let checks=0
await db.exec(`
 create role cp7_capture;create role cp7_reminder;create role anon;create role authenticated;create role service_role;
 create schema cp7_analysis_stage authorization cp7_capture;
 create schema cp7_analysis_jobs authorization cp7_capture;
 create schema cp7_reminder_native authorization cp7_reminder;
 create schema cp7_ops authorization cp7_capture;
 create table public.dev_actor(actor uuid primary key,enabled boolean,fail_mid boolean default false);
 create table public.dev_units(family text,id uuid,unit int,primary key(family,id,unit));
 create function public.dev_access()returns uuid language plpgsql security definer as $$
 declare a uuid:=(current_setting('request.jwt.claims')::jsonb->>'sub')::uuid;
 begin if not coalesce((select enabled from public.dev_actor where actor=a),false)then raise exception using errcode='42501',message='DENIED';end if;return a;end$$;
 create function public.dev_after(a uuid)returns void language plpgsql security definer as $$
 begin if(select fail_mid from public.dev_actor where actor=a)then raise exception using errcode='42501',message='ACCESS_CHANGED';end if;end$$;
 create table cp7_analysis_stage.runner(id boolean primary key,last_tick_at timestamptz,statement_timeout_ms int);
 create table cp7_analysis_stage.jobs(id uuid primary key,actor uuid,state text,updated_at timestamptz);
 create table cp7_analysis_stage.report_jobs(id uuid primary key,actor uuid,request_id uuid,state text,updated_at timestamptz,
  units_done int default 0,unit_count int default 2,unit_attempts int default 0,failure_unit int,failure_sqlstate text,failure_code text,failure_message text);
 create table cp7_reminder_native.staged_condition_sets(run_id uuid primary key,actor uuid,state text,updated_at timestamptz,
  units_done int default 0,unit_count int default 2,unit_attempts int default 0,failure_unit int,failure_sqlstate text,failure_code text,failure_message text);
 create table cp7_analysis_jobs.jobs(actor uuid,request_id uuid,state text,started_at timestamptz,finished_at timestamptz,
  failure_sqlstate text,failure_code text,primary key(actor,request_id));
 alter table cp7_analysis_stage.runner owner to cp7_capture;
 alter table cp7_analysis_stage.jobs owner to cp7_capture;
 alter table cp7_analysis_stage.report_jobs owner to cp7_capture;
 alter table cp7_reminder_native.staged_condition_sets owner to cp7_reminder;
 alter table cp7_analysis_jobs.jobs owner to cp7_capture;
 create function cp7_analysis_stage.report_step(k uuid)returns jsonb language plpgsql security definer as $$
 declare a uuid:=public.dev_access();begin
  insert into public.dev_units select 'REPORT',id,units_done from cp7_analysis_stage.report_jobs where actor=a and request_id=k;
  update cp7_analysis_stage.report_jobs set units_done=units_done+1,updated_at=clock_timestamp(),state=case when units_done+1=unit_count then 'DONE'else state end where actor=a and request_id=k;
  perform public.dev_after(a);return '{}';end$$;
 create function cp7_reminder_native.staged_set_step(k uuid)returns jsonb language plpgsql security definer as $$
 declare a uuid:=public.dev_access();begin
  insert into public.dev_units select 'REMINDER',run_id,units_done from cp7_reminder_native.staged_condition_sets where actor=a and run_id=k;
  update cp7_reminder_native.staged_condition_sets set units_done=units_done+1,updated_at=clock_timestamp(),state=case when units_done+1=unit_count then 'DONE'else state end where actor=a and run_id=k;
  perform public.dev_after(a);return '{}';end$$;
 create function cp7_analysis_jobs.compute_key(a uuid,k uuid)returns bigint language sql immutable as $$select hashtextextended('CP7:ANALYSIS:'||a::text||':'||k::text,0)$$;
 create function cp7_analysis_jobs.run(k uuid)returns jsonb language plpgsql security definer as $$
 declare a uuid:=public.dev_access();begin
  insert into public.dev_units values('ANALYSIS',k,0);
  update cp7_analysis_jobs.jobs set state='DONE',finished_at=clock_timestamp()where actor=a and request_id=k;
  perform public.dev_after(a);return '{}';end$$;
 create function cp7_analysis_stage.run_next()returns jsonb language plpgsql security definer as $$
 declare k uuid;begin select id into k from cp7_analysis_stage.jobs where state='RUNNING'order by updated_at,id limit 1 for update skip locked;
  if not found then return '{"ran":false,"outcome":"IDLE"}';end if;
  insert into public.dev_units values('STAGED',k,0);update cp7_analysis_stage.jobs set state='DONE'where id=k;
  return jsonb_build_object('ran',true,'outcome','JOB_DONE');end$$;
 create function cp7_ops.analysis_tick()returns jsonb language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select cp7_analysis_stage.run_next()$$;
 alter function cp7_ops.analysis_tick()owner to cp7_capture;
`)
await db.exec(readFileSync(repo+'/scripts/cp7-src/ops/background.sql','utf8'))
console.log(JSON.stringify({runtime:'LOCAL_PGLITE18_DEV',original_dispatcher_sql_installed:true,synthetic_job_contracts:true,native_acceptance:false}))
const actor='10000000-0000-4000-8000-000000000001'
await db.query('insert into public.dev_actor values($1,true,false)',[actor])
const prior=JSON.stringify({sub:'20000000-0000-4000-8000-000000000001',role:'caller'})
await db.query("select set_config('request.jwt.claims',$1,false)",[prior])
await db.exec("set statement_timeout='9s'")
await assert.rejects(()=>one('select cp7_ops.analysis_tick()'),/CP7_RUNNER_STATEMENT_LIMIT_REQUIRED/);checks++
await db.exec("set statement_timeout='8s'")
assert.equal((await one('select cp7_ops.analysis_tick()')).outcome,'IDLE');checks++
async function seed(offset){
 const id=n=>'10000000-0000-4000-8000-'+String(offset+n).padStart(12,'0')
 await db.query("insert into cp7_analysis_stage.report_jobs(id,actor,request_id,state,updated_at)values($1,$2,$1,'RUNNING',now()-interval'1 minute')",[id(1),actor])
 await db.query("insert into cp7_reminder_native.staged_condition_sets(run_id,actor,state,updated_at)values($1,$2,'RUNNING',now()-interval'1 minute')",[id(2),actor])
 await db.query("insert into cp7_analysis_jobs.jobs(actor,request_id,state,started_at)values($1,$2,'WAITING',now()-interval'1 minute')",[actor,id(3)])
 return id
}
const ids=await seed(100)
await db.query("insert into cp7_analysis_stage.jobs values($1,$2,'RUNNING',now()-interval'1 minute')",[ids(4),actor])
const seen=[]
for(let i=0;i<4;i++)seen.push((await one('select cp7_ops.analysis_tick()')).family??'STAGED')
assert.deepEqual(new Set(seen),new Set(['REPORT','REMINDER','ANALYSIS','STAGED']));checks++
for(let i=0;i<2;i++)assert.equal((await one('select cp7_ops.analysis_tick()')).outcome,'JOB_DONE')
assert.equal((await one('select cp7_ops.analysis_tick()')).outcome,'IDLE');checks++
assert.equal(await one('select count(*)::int from public.dev_units'),6);checks++
assert.equal(await one("select current_setting('request.jwt.claims')"),prior);checks++
for(const [offset,enabled,mid]of[[200,false,false],[300,true,true]]){
 const id=await seed(offset)
 await db.query('update public.dev_actor set enabled=$1,fail_mid=$2',[enabled,mid])
 for(let i=0;i<3;i++)assert.equal((await one('select cp7_ops.analysis_tick()')).outcome,'JOB_FAILED')
 assert.equal(await one('select count(*)::int from public.dev_units where id=any($1::uuid[])',[[id(1),id(2),id(3)]]),0);checks++
 assert.equal((await one('select cp7_ops.analysis_tick()')).outcome,'IDLE');checks++
 assert.equal(await one("select current_setting('request.jwt.claims')"),prior);checks++
}
for(const who of['anon','authenticated','service_role']){
 assert.equal(await one("select bool_or(has_function_privilege($1,p.oid,'EXECUTE'))from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_background'",[who]),false);checks++
}
console.log(JSON.stringify({status:'PASS',checks,real_sql:true,synthetic_steps:true,native_acceptance:false,concurrency_proven:false}))
await db.close()
