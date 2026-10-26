// Actual optional work SQL/Native DDL/cache/retention. Controlled access,
// producer and compiler; no Native17, two-session, Auth or factory credit.
import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8'),json=JSON.stringify,cases=[]
const block=(s,n)=>{const m=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(m?.length,1,n);return m[0]}
const value=async(s,a=[])=>(await db.query(s,a)).rows[0]?.v
const id=n=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`,actor=id(20)
const query={from_date:'2026-10-01',through_date:'2026-10-02',group_mode:'AS_SOLD'}
const reference={bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2',bounded_query:query,bounded_capture_state:'FROZEN',bounded_capsule_hash:'a'.repeat(64),bounded_producer_hash:'b'.repeat(64),captured_at:'2026-10-25T05:06:07.123456Z',status:'INCOMPLETE',bounded_history_inputs:null,bounded_input_coverage:'PENDING'}
const inputs={coverage:'COMPLETE',captured_at:reference.captured_at,query,raw_native_capture_status:'INCOMPLETE',inputs:{targets:[{target_key:'CONTROLLED_ONE',quantity:'9007199254740993'}]}}
const setting=(k,v)=>db.query('select set_config($1,$2,false)',['choice_prep_control.'+k,typeof v==='string'?v:json(v)])
const access=()=>value("select encode(sha256(convert_to(cp7_schedule_native.access_now(false)::text,'UTF8')),'hex')v")
const jobId=n=>value('select cp7_analysis_stage.job_of($1,$2)v',[actor,id(n)])
const job=async n=>value('select to_jsonb(j)v from cp7_analysis_stage.jobs j where id=$1',[await jobId(n)])
const call=async(verb,n,epoch)=>value(`select public.erp_cp7_${verb}_frozen_choice_preparation_v1($1,$2)v`,[id(n),epoch??await access()])
const ref=async n=>value('select cp7_frozen_choice_preparation.reference(j)v from cp7_analysis_stage.jobs j where id=$1',[await jobId(n)])
const row=async n=>value('select to_jsonb(w)v from cp7_frozen_choice_preparation.work w where job_id=$1',[await jobId(n)])
async function test(id,fn){const extra=await fn();cases.push({id,status:'PASS',...extra})}
async function seed(n,{cached=false,expired=false}={}){
 const key=id(2000+n)
 await db.query(`insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,captured_at,source_hash,state,unit_count,created_at,updated_at)
 values($1,$2,$3,$4::jsonb,$5::jsonb,$6,'{}',$7,repeat('c',64),'RUNNING',1,now(),now())`,[key,actor,id(n),json(query),json(reference),id(1000+n),reference.captured_at])
 await db.query("insert into cp7_analysis_stage.units(job_id,idx,kind,chunk,lo,hi)values($1,0,'HIST_PREP',0,0,0)",[key])
 if(cached)await db.query("insert into cp7_analysis_stage.target_rows(job_id,kind,ord,key,payload)select id,'FROZEN_INPUTS_V2',1,reference->>'bounded_capsule_hash',cp7_frozen_analysis_units_v2.pack(j,$2::jsonb)from cp7_analysis_stage.jobs j where id=$1",[key,json(inputs)])
 await db.query("update cp7_analysis_stage.jobs set state='DONE',units_done=unit_count,plan_final=true,updated_at=now()-($2::integer*interval'1 day')where id=$1",[key,expired?8:0])
 return key
}
try{
 await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create role cp7_alert;create schema extensions;create schema cp7_private;create schema cp7_analysis_stage authorization cp7_capture;create schema cp7_frozen_analysis_v2 authorization cp7_capture;create schema cp7_schedule_native authorization cp7_capture;revoke create on schema public from public;')
 await db.exec("create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)where $2='sha256'$$;grant usage on schema extensions to cp7_capture")
 await db.exec(block(await read('scripts/cp7-src/snapshot/bootstrap.sql'),'cp7_private.immutable_run'))
 await db.exec(await read('scripts/cp7-src/wip/bootstrap.sql'))
 const native=await read('scripts/cp7-src/planning/analysis-stages.sql')
 await db.exec(native.slice(native.indexOf('create table cp7_analysis_stage.jobs('),native.indexOf('-- Declared bounds, once.')))
 for(const name of['bounds','job_of','purge_intermediates','retention_days','retention','require_kept'])await db.exec(block(native,'cp7_analysis_stage.'+name))
 await db.exec(`create function cp7_schedule_native.access_now(boolean)returns jsonb language plpgsql volatile as $$begin
 if current_setting('choice_prep_control.access_cancel',true)='true'then raise exception using errcode='57014',message='CONTROLLED_ACCESS_CANCEL';end if;
 if current_setting('choice_prep_control.denied',true)='true'then raise exception using errcode='42501',message='CP7_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',current_setting('choice_prep_control.actor'),'epoch',coalesce(current_setting('choice_prep_control.epoch',true),'old'));end$$;
 create function cp7_frozen_analysis_v2.prepare(c jsonb,q jsonb,n integer)returns jsonb language plpgsql volatile as $$begin
 if current_setting('choice_prep_control.cancel',true)='true'then raise exception using errcode='57014',message='CONTROLLED_TIMEOUT';end if;
 if current_setting('choice_prep_control.error',true)='true'then raise exception using errcode='22012',message='private internal text must not leak';end if;
 if current_setting('choice_prep_control.forbidden',true)='true'then raise exception 'CONTROLLED_PREPARE_FORBIDDEN';end if;
 if c is distinct from current_setting('choice_prep_control.reference')::jsonb or q is distinct from current_setting('choice_prep_control.query')::jsonb or n<>5000 then raise exception 'CONTROLLED_FROZEN_ARGUMENTS_CHANGED';end if;
 return current_setting('choice_prep_control.inputs')::jsonb;end$$;`)
 await db.exec(await read('scripts/cp7_frozen_analysis_units_v2/cache.sql'))
 await db.exec(block(await read('scripts/cp7_frozen_analysis_units_v2/source.prepared.sql'),'cp7_frozen_analysis_units_v2.coverage'))
 await db.exec("create function cp7_frozen_analysis_units_v2.producer_hash()returns text language sql stable as $$select current_setting('choice_prep_control.producer')$$")
 const choice=await read('scripts/cp7_product_analog_choice_stage/choice.sql')
 await db.exec(choice.slice(0,choice.indexOf('create function cp7_product_analog_choice.material(')))
 await db.exec(await read('scripts/cp7_frozen_analysis_choice_v2/choice.prepared.sql'))
 await db.exec(await read('scripts/cp7_frozen_analysis_readers_v2/reference.sql'))
 await db.exec(await read('scripts/cp7_frozen_analysis_readers_v2/reader.prepared.sql'))
 const sql=await read('scripts/cp7_frozen_choice_preparation/preparation.prepared.sql');await db.exec(sql)
 for(const[k,v]of Object.entries({reference,query,inputs,producer:'b'.repeat(64),actor}))await setting(k,v)
 await db.exec("set role cp7_capture;set statement_timeout='8s'")
 const key=await seed(1,{cached:true}),original=await job(1)
 await test('CHEAP_REQUEST_AND_REOPEN_DEDUP_ORIGINAL_SOURCE_WITHOUT_COMPILATION',async()=>{
  await setting('forbidden','true');const first=await call('request',1)
  assert.equal(first.state,'QUEUED');assert.equal(first.units_done,0);assert.equal(first.choice_saved,false)
  assert.deepEqual(await call('request',1),first);assert.deepEqual(await call('get',1),first)
  assert.equal(await value('select count(*)::integer v from cp7_frozen_choice_preparation.work'),1)
 })
 await test('STATUS_OBSERVES_REAL_WORKER_KEY_WITHOUT_TAKING_A_LOCK',async()=>{
  await db.exec('begin');assert.equal((await call('get',1)).state,'QUEUED')
  assert.equal(await value("select count(*)::integer v from pg_locks where locktype='advisory'and pid=pg_backend_pid()"),0)
  await db.query("select pg_advisory_xact_lock(hashtextextended('CP7:FROZEN_CHOICE_PREP:'||$1::text,0))",[key])
  const s=await call('get',1);assert.equal(s.state,'RUNNING');assert.equal(s.worker_active,true);assert.equal(s.units_done,0)
  await db.exec('commit');assert.equal((await call('get',1)).state,'QUEUED')
 })
 await test('EXISTING_VALID_CACHE_REUSED_AND_READY_NEVER_SAVES_A_CHOICE',async()=>{
  const ready=await call('step',1);assert.equal(ready.state,'READY');assert.equal(ready.units_done,1)
  assert.equal(ready.choice_saved,false);assert.equal(ready.production_go,false)
  const w=await row(1);assert.deepEqual(await call('step',1),ready);assert.deepEqual(await row(1),w)
  assert.deepEqual(await job(1),original);assert.deepEqual((await ref(1)).bounded_history_inputs,inputs)
 })
 await test('K3_REUSES_EXPLICIT_PREPARATION_WITHOUT_COMPILER_OR_OLD_CACHE_REWRITE',async()=>{
  await value('select cp7_analysis_stage.purge_intermediates($1)v',[key])
  assert.deepEqual((await ref(1)).bounded_history_inputs,inputs)
  assert.equal(await value('select count(*)::integer v from cp7_analysis_stage.target_rows where job_id=$1',[key]),0)
  assert.deepEqual(await job(1),original)
 })
 await test('MISSING_PREPARATION_REFUSES_SAVE_REFERENCE_THEN_SEPARATE_UNIT_PREPARES',async()=>{
  await seed(2);await assert.rejects(()=>ref(2),/CP7_CHOICE_PREPARATION_REQUIRED/)
  await call('request',2);await assert.rejects(()=>ref(2),/CP7_CHOICE_PREPARATION_REQUIRED/)
  await setting('forbidden','false');assert.equal((await call('step',2)).state,'READY')
  await setting('forbidden','true');assert.deepEqual((await ref(2)).bounded_history_inputs,inputs)
 })
 await test('CURRENT_ACCESS_ACTOR_EPOCH_AND_PRODUCER_GUARDS_STILL_APPLY',async()=>{
  const epoch=await access();await setting('epoch','changed')
  await assert.rejects(()=>call('get',1,epoch),/CP7_ANALYSIS_ACCESS_CHANGED/)
  await setting('actor',id(99));await assert.rejects(()=>call('request',1),/CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE/)
  await setting('actor',actor);await setting('denied','true');await assert.rejects(()=>call('step',1,epoch),/CP7_ACCESS_DENIED/)
  await setting('denied','false');await setting('producer','f'.repeat(64));await assert.rejects(()=>call('get',1),/CP7_PRODUCT_ANALOG_PRODUCER_CHANGED/)
  await assert.rejects(()=>ref(1),/CP7_PRODUCT_ANALOG_PRODUCER_CHANGED/);await setting('producer','b'.repeat(64))
 })
 await test('THREE_REAL_CANCELLATIONS_FAIL_WITHOUT_PARTIAL_RESULT_OR_ENDLESS_RETRY',async()=>{
  await seed(3);await call('request',3);await setting('cancel','true')
  for(let i=1;i<=3;i++){
   const s=await call('step',3);assert.equal(s.unit_attempts,i);assert.equal(s.units_done,0);assert.equal(s.state,i<3?'QUEUED':'FAILED');assert.equal((await row(3)).payload,null)
  }
  assert.equal((await call('step',3)).unit_attempts,3);assert.equal((await call('get',3)).failure_code,'CP7_CHOICE_PREPARATION_TIME_LIMIT')
  await assert.rejects(()=>ref(3),/CP7_CHOICE_PREPARATION_REQUIRED/);await setting('cancel','false')
 })
 await test('ONE_CANCEL_THEN_RECOVERY_KEEPS_SAME_ORIGINAL_WORK_ID',async()=>{
  await seed(4);await call('request',4);await setting('cancel','true');await call('step',4)
  const before=await row(4);await setting('cancel','false');await setting('forbidden','false')
  assert.equal((await call('step',4)).state,'READY');assert.equal((await row(4)).job_id,before.job_id)
  assert.equal((await row(4)).created_at,before.created_at);assert.deepEqual((await ref(4)).bounded_history_inputs,inputs)
 })
 await test('UNKNOWN_ERROR_IS_FAILED_NOT_TIMEOUT_AND_INTERNAL_DETAIL_IS_PRIVATE',async()=>{
  await seed(5);await call('request',5);await setting('error','true');const s=await call('step',5)
  assert.equal(s.state,'FAILED');assert.equal(s.unit_attempts,1);assert.equal(s.failure_sqlstate,'22012');assert.equal(s.failure_code,'CP7_CHOICE_PREPARATION_FAILED')
  assert.ok(!json(s).includes('private internal'));await setting('error','false')
 })
 await test('INVALID_COMPILED_INPUTS_NEVER_BECOME_READY',async()=>{
  await seed(6);await call('request',6);await setting('inputs',{...inputs,coverage:'PENDING'})
  const s=await call('step',6);assert.equal(s.state,'FAILED');assert.equal(s.failure_code,'CP7_FROZEN_UNIT_CACHE_BINDING')
  assert.equal((await row(6)).payload,null);await setting('inputs',inputs)
 })
 await test('PRIVATE_RUNNER_REUSES_STEP_AND_RESTORES_CALLER_CLAIMS',async()=>{
  await seed(7);await call('request',7)
  await db.query("select set_config('request.jwt.claims',$1,false),set_config('request.jwt.claim.sub','prior-sub',false),set_config('request.jwt.claim','prior-claim',false)",[json({scope:'original'})])
  const s=await value('select cp7_frozen_choice_preparation.run_next()v');assert.equal(s.state,'READY');assert.equal(s.job_id,await jobId(7))
  assert.deepEqual(await value("select current_setting('request.jwt.claims')::jsonb v"),{scope:'original'})
  assert.equal(await value("select current_setting('request.jwt.claim.sub')v"),'prior-sub')
  assert.equal(await value("select current_setting('request.jwt.claim')v"),'prior-claim')
  assert.equal((await value('select cp7_frozen_choice_preparation.run_next()v')).outcome,'IDLE')
 })
 const callerClaims=()=>value("select jsonb_build_array(current_setting('request.jwt.claims'),current_setting('request.jwt.claim.sub'),current_setting('request.jwt.claim'))v")
 await test('RUNNER_PRESTEP_CANCELLATIONS_ARE_BOUNDED_AND_RESTORE_CALLER_CLAIMS',async()=>{
  await seed(9);await call('request',9);const before=await row(9),claims=await callerClaims()
  await setting('access_cancel','true')
  for(let i=1;i<=3;i++){
   const s=await value('select cp7_frozen_choice_preparation.run_next()v'),w=await row(9)
   assert.equal(s.state,i<3?'QUEUED':'FAILED');assert.equal(s.job_id,before.job_id)
   assert.equal(w.attempts,i);assert.equal(w.payload,null);assert.equal(w.created_at,before.created_at)
   assert.deepEqual(await callerClaims(),claims)
  }
  await setting('access_cancel','false');assert.equal((await call('get',9)).failure_code,'CP7_CHOICE_PREPARATION_TIME_LIMIT')
  assert.equal((await value('select cp7_frozen_choice_preparation.run_next()v')).outcome,'IDLE')
  return{injected_SQL57014_not_wall_clock_timeout:true}
 })
 await test('RUNNER_PRESTEP_CANCEL_THEN_RECOVERY_USES_SAME_WORK',async()=>{
  await seed(10);await call('request',10);const before=await row(10),claims=await callerClaims()
  await setting('access_cancel','true');assert.equal((await value('select cp7_frozen_choice_preparation.run_next()v')).state,'QUEUED')
  await setting('access_cancel','false');assert.equal((await value('select cp7_frozen_choice_preparation.run_next()v')).state,'READY')
  const w=await row(10);assert.equal(w.job_id,before.job_id);assert.equal(w.created_at,before.created_at);assert.equal(w.attempts,1)
  assert.deepEqual((await ref(10)).bounded_history_inputs,inputs);assert.deepEqual(await callerClaims(),claims)
 })
 await test('RUNNER_ACCESS_REFUSAL_IS_TERMINAL_AND_RESTORES_CALLER_CLAIMS',async()=>{
  await seed(11);await call('request',11);const claims=await callerClaims()
  await setting('denied','true');assert.equal((await value('select cp7_frozen_choice_preparation.run_next()v')).state,'FAILED')
  assert.deepEqual(await callerClaims(),claims);await setting('denied','false')
  const w=await row(11);assert.equal(w.attempts,0);assert.equal(w.payload,null);assert.equal(w.failure_code,'CP7_ACCESS_DENIED');assert.equal(w.failure_sqlstate,'42501')
 })
 await test('EXPIRED_SOURCE_REFUSED_AND_ONLY_EXPIRED_PAYLOAD_CLEARED',async()=>{
  const old=await seed(8,{expired:true});await assert.rejects(()=>call('request',8),/CP7_ANALYSIS_RESULT_EXPIRED/)
  await db.query("insert into cp7_frozen_choice_preparation.work(job_id,actor,source_request,source_hash,capsule_hash,producer_hash,query,captured_at,state,payload)select id,actor,request_id,source_hash,reference->>'bounded_capsule_hash',reference->>'bounded_producer_hash',query,captured_at,'READY',cp7_frozen_analysis_units_v2.pack(j,$2::jsonb)from cp7_analysis_stage.jobs j where id=$1",[old,json(inputs)])
  await assert.rejects(()=>ref(8),/CP7_ANALYSIS_RESULT_EXPIRED/)
  assert.equal(await value('select cp7_frozen_choice_preparation.purge_expired(10)v'),1)
  assert.equal((await row(8)).state,'EXPIRED');assert.equal((await row(8)).payload,null)
  assert.equal(await value('select cp7_frozen_choice_preparation.purge_expired(10)v'),0)
  assert.equal((await row(1)).state,'READY');assert.deepEqual(await job(1),original)
 })
 await test('UNIT_LIMIT_AND_REPEATABLE_READ_REFUSED_WITHOUT_WORK',async()=>{
  await db.exec('set statement_timeout=0');await assert.rejects(()=>call('step',1),/CP7_RUNNER_STATEMENT_LIMIT_REQUIRED/);await db.exec("set statement_timeout='8s'")
  const epoch=await access();await db.exec('begin isolation level repeatable read')
  await assert.rejects(()=>call('get',1,epoch),/CP7_FRESH_ACCESS_REQUIRED/);await db.exec('rollback')
 })
 await test('READY_PAYLOAD_AND_IDENTITY_IMMUTABLE_UNTIL_ACTUAL_EXPIRY',async()=>{
  await assert.rejects(()=>db.query('update cp7_frozen_choice_preparation.work set payload=payload where job_id=$1',[key]),/CP7_CHOICE_PREPARATION_IMMUTABLE/)
  await assert.rejects(()=>db.query('delete from cp7_frozen_choice_preparation.work where job_id=$1',[key]),/CP7_CHOICE_PREPARATION_IMMUTABLE/)
  await assert.rejects(()=>db.query("update cp7_frozen_choice_preparation.work set state='EXPIRED',payload=null where job_id=$1",[key]),/CP7_CHOICE_PREPARATION_NOT_EXPIRED/)
  assert.deepEqual((await ref(1)).bounded_history_inputs,inputs)
 })
 await db.exec('reset role')
 await test('PRIVATE_OWNER_RLS_CLOSED_AND_ONLY_THREE_AUTHENTICATED_WRAPPERS',async()=>{
  const functions=(await db.query("select p.oid::regprocedure::text sig,pg_get_userbyid(proowner)owner,prosecdef,proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_frozen_choice_preparation'or proname like 'erp_cp7_%_frozen_choice_preparation_v1'order by 1")).rows
  assert.equal(functions.length,13)
  for(const f of functions){const pub=f.sig.startsWith('erp_cp7_');assert.equal(f.owner,'cp7_capture');assert.equal(f.prosecdef,pub);assert.deepEqual(f.proconfig,['search_path=""','TimeZone=UTC'])
   for(const role of['anon','authenticated','service_role','cp7_alert'])assert.equal(await value("select has_function_privilege($1,$2,'EXECUTE')v",[role,f.sig]),pub&&role==='authenticated')
  }
  for(const role of['anon','authenticated','service_role','cp7_alert']){
   assert.equal(await value("select has_schema_privilege($1,'cp7_frozen_choice_preparation','USAGE')v",[role]),false)
   for(const permission of['SELECT','INSERT','UPDATE','DELETE','TRUNCATE'])assert.equal(await value("select has_table_privilege($1,'cp7_frozen_choice_preparation.work',$2)v",[role,permission]),false)
  }
  assert.equal(await value("select relrowsecurity v from pg_class where oid='cp7_frozen_choice_preparation.work'::regclass"),true)
 })
 const report={contract:'cp7.frozen-choice-preparation.local.v1',status:'PASS',cases,counts:{PASS:cases.length},sql_sha256:createHash('sha256').update(sql).digest('hex'),server_version:await value('select version()v'),controlled_access_producer_and_compiler:true,actual_Native:false,actual_Auth_HTTP_credit:false,two_session_concurrency:false,actual_factory_performance:false,Python_installer_qualified:false,default_adopted:false,production_go:false}
 if(process.env.CP7_CHOICE_PREPARATION_REPORT)await writeFile(process.env.CP7_CHOICE_PREPARATION_REPORT,json(report)+'\n')
 console.log(json(report))
}finally{await db.close()}
