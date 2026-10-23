// Actual initial-analysis SQL, real hooks/install/catalog, actual staged job
// creation and access guard. ERP/source/Auth/WA-unit adapters are controlled.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {createHash,randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8')
const block=(s,name)=>{const a=s.indexOf('create function '+name+'(');assert.ok(a>=0,name);const b=s.indexOf('$$;',s.indexOf('as $$',a)+5);return s.slice(a,b+3)}
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`
const owner=id(1),second=id(2),admin=id(3),inactive=id(4),root=id(10),product=id(11),size=id(12)
await db.exec(`create role cp7_capture nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
 create role cp7_alert nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
 create role anon nologin;create role authenticated nologin;create role service_role nologin;
 create schema auth;create schema erp;create schema extensions;create schema cp7_private;create schema cp7_schedule_native;
 create schema cp7_analysis_stage;create schema cp7_analysis_native;create schema cp7_analysis_jobs;create schema cp7_planning;
 create schema cp7_supply_native;create schema cp7_stock_formula;create schema cp7_profile;create schema cp7_alert_native;
 create table public.fixture_access(actor uuid primary key,role_code text,allowed boolean);
 insert into public.fixture_access values('${owner}','OWNER',true),('${second}','ADMIN',true),('${admin}','STAFF',true),('${inactive}','OWNER',false);
 create table public.fixture_source(value jsonb);
 create table cp7_profile.profiles(actor uuid,recorded_at timestamptz);
 create table cp7_analysis_native.runs(actor uuid,request_id uuid);create table cp7_analysis_jobs.jobs(actor uuid,request_id uuid);
 alter table cp7_analysis_native.runs owner to cp7_capture;alter table cp7_analysis_jobs.jobs owner to cp7_capture;
 create function auth.jwt()returns jsonb language sql stable as $$select coalesce(nullif(current_setting('request.jwt.claim',true),''),nullif(current_setting('request.jwt.claims',true),''))::jsonb$$;
 create function auth.uid()returns uuid language sql stable as $$select coalesce(nullif(current_setting('request.jwt.claim.sub',true),''),auth.jwt()->>'sub')::uuid$$;
 create function erp.get_my_access_v1()returns jsonb language sql volatile security definer set search_path=''as $$
  select jsonb_build_object('allowed',coalesce(f.allowed,false),'profile',jsonb_build_object('role_code',f.role_code,'id',f.actor,'row_version',coalesce(current_setting('ow13a.epoch',true),'before')),
   'permissions',jsonb_build_array('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view'),
   'epoch',coalesce(current_setting('ow13a.epoch',true),'before'))from public.fixture_access f where f.actor=auth.uid()$$;
 create function erp.has_permission(k text)returns boolean language sql stable security definer set search_path=''as $$
  select coalesce((select f.allowed from public.fixture_access f where f.actor=auth.uid()),false)
   and coalesce(current_setting('ow13a.deny',true),'')<>k$$;
 create function extensions.digest(v bytea,algorithm text)returns bytea language sql immutable as $$select sha256(v)$$;
 create function cp7_analysis_native.fingerprint(c jsonb)returns text language sql immutable as $$select encode(sha256(convert_to(c::text,'UTF8')),'hex')$$;
 create function cp7_analysis_stage.bounds()returns jsonb language sql immutable as $$select '{"job_targets":5000,"job_matching_products":10000}'::jsonb$$;
 create function cp7_analysis_native.source_within(integer,integer)returns jsonb language plpgsql volatile as $$begin
  if current_setting('ow13a.poison_source',true)='yes'then raise exception 'CONTROLLED_SOURCE_REFUSAL';end if;
  if current_setting('ow13a.source_revoke',true)='yes'then perform set_config('ow13a.epoch','after',true);end if;
  return(select value from public.fixture_source);end$$;
 create function cp7_stock_formula.current_settings()returns jsonb language sql stable as $$select jsonb_build_object('window_days',coalesce(nullif(current_setting('ow13a.window',true),''),'30')::integer)$$;
 grant usage on schema auth,erp,extensions,cp7_analysis_stage,cp7_analysis_native,cp7_analysis_jobs,cp7_planning,cp7_schedule_native,cp7_supply_native,cp7_stock_formula,cp7_profile,cp7_private to cp7_capture;
 grant select on public.fixture_source,cp7_profile.profiles to cp7_capture;
 grant usage on schema auth,erp,cp7_alert_native to cp7_alert;
 grant select on public.fixture_source to cp7_alert;
`)
await db.exec(await read('scripts/cp7-src/wip/bootstrap.sql'))
await db.exec(await read('scripts/cp7-src/demand/bootstrap.sql'))
for(const [path,fn]of[
 ['scripts/cp7-src/snapshot/bootstrap.sql','cp7_private.access_now'],
 ['scripts/cp7-src/snapshot/bootstrap.sql','cp7_private.immutable_run'],
 ['scripts/cp7-src/planning/schedule.sql','cp7_schedule_native.access_now'],
 ['scripts/cp7-src/planning/bootstrap.sql','cp7_planning.utc'],
 ['scripts/cp7-src/planning/bootstrap.sql','cp7_planning.history_query'],
 ['scripts/cp7-src/planning/supply-source.sql','cp7_supply_native.fingerprint']])await db.exec(block(await read(path),fn))
const staged=await read('scripts/cp7-src/planning/analysis-stages.sql')
for(const table of['jobs','units','runner','capture_marks']){
 const a=staged.indexOf('create table cp7_analysis_stage.'+table+'(');assert.ok(a>=0,table)
 await db.exec(staged.slice(a,staged.indexOf(';',a)+1))
 await db.exec('alter table cp7_analysis_stage.'+table+' owner to cp7_capture')
}
for(const fn of['retention_days','retention','status','job_of','create_job','request'])await db.exec(block(staged,'cp7_analysis_stage.'+fn))
await db.exec(block(staged,'public.erp_cp7_request_staged_analysis_v1'))
await db.exec('alter function public.erp_cp7_request_staged_analysis_v1(jsonb,uuid)owner to cp7_capture')
await db.exec(`create type cp7_alert_native.settings as(revision bigint,actor uuid,actor_user_id uuid);
 create table cp7_alert_native.settings_adapter(value cp7_alert_native.settings);
 create table cp7_alert_native.ticks(job text primary key,at timestamptz,outcome jsonb);
 alter table cp7_alert_native.settings_adapter owner to cp7_alert;alter table cp7_alert_native.ticks owner to cp7_alert;
 create function cp7_alert_native.current_settings()returns cp7_alert_native.settings language sql stable security definer set search_path=''set TimeZone='UTC'as $$select value from cp7_alert_native.settings_adapter limit 1$$;
 create function cp7_alert_native.analysis_unit(s cp7_alert_native.settings,t0 timestamptz)returns jsonb language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select jsonb_build_object('outcome','CONTROLLED_LEGACY_ANALYSIS_UNIT','ran',true)$$;
`)
const alerts=await read('scripts/cp7-src/alerts/alerts.sql')
for(const fn of['require_tick_limit','record_tick','jwt','uid','claims_enter','claims_leave','owner_access','analysis_tick'])await db.exec(block(alerts,'cp7_alert_native.'+fn))
for(const sig of['cp7_alert_native.current_settings()','cp7_alert_native.analysis_unit(cp7_alert_native.settings,timestamp with time zone)',
 'cp7_alert_native.require_tick_limit()','cp7_alert_native.record_tick(text,jsonb)','cp7_alert_native.jwt()','cp7_alert_native.uid()',
 'cp7_alert_native.claims_enter(uuid)','cp7_alert_native.claims_leave(jsonb)','cp7_alert_native.owner_access(uuid)','cp7_alert_native.analysis_tick()']){
 await db.exec('alter function '+sig+' owner to cp7_alert;revoke all on function '+sig+' from public,anon,authenticated,service_role,cp7_capture')
}
await db.exec('alter function cp7_analysis_stage.request(jsonb,uuid)owner to cp7_capture;revoke all on function cp7_analysis_stage.request(jsonb,uuid)from public,anon,authenticated,service_role')
const stageAudit=await beginLocalStageAudit(db,'cp7_initial_analysis_stage')
const set=async(k,v)=>db.query('select set_config($1,$2,false)',[k,v])
const login=async actor=>{await set('request.jwt.claim','');await set('request.jwt.claim.sub','');await set('request.jwt.claims',JSON.stringify({sub:actor,role:'authenticated'}));await set('ow13a.epoch','before');await set('ow13a.deny','');await set('ow13a.source_revoke','')}
await login(owner)
const query=(await db.query(`select jsonb_build_object('from_date',(((clock_timestamp()at time zone'Asia/Jakarta')::date)-30)::text,'through_date',(((clock_timestamp()at time zone'Asia/Jakarta')::date)-1)::text,'group_mode','AS_SOLD')v`)).rows[0].v
const profile={root_id:root,product_version_id:product,size_id:size,quality:'SELECTED_ASSUMPTION',config:{mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,minimum_available_days:'14',lead_days:'3',review_days:'7',buffer_days:'2'}}
const source={contract_version:'cp7.native-demand-facts.v1',status:'COMPLETE',captured_at:'2026-10-23T00:00:00Z',facts:{products:[],sales:[],stock:[]},profiles:[],production_policies:{rows:[]},schedule:null,matching_products:[],material_source:{captured_at:'2026-10-23T00:00:00Z',rows:[]},fabric_source:{captured_at:'2026-10-23T00:00:00Z',rows:[]},analysis_engine_signature:'a'.repeat(64)}
await db.query('insert into public.fixture_source values($1::jsonb)',[JSON.stringify(source)])
const put=async()=>db.query('update public.fixture_source set value=$1::jsonb',[JSON.stringify(source)])
const call=async(ensure=false)=>(await db.query('select public.erp_cp7_request_staged_analysis_v1($1::jsonb,null)v',[JSON.stringify({initial_auto:ensure?'ENSURE':'STATUS'})])).rows[0].v
const counts=async()=>(await db.query(`select(select count(*)from cp7_initial_analysis.intents)::integer intents,(select count(*)from cp7_analysis_stage.jobs)::integer jobs,(select count(*)from cp7_analysis_stage.units)::integer units,(select count(*)from cp7_analysis_stage.capture_marks)::integer marks`)).rows[0]
const failed=async()=>db.exec(`update cp7_analysis_stage.jobs set state='FAILED',failure_unit=0,failure_sqlstate='P0001',failure_code='CP7_CONTROLLED_FAILURE',failure_message='CONTROLLED_LOCAL_FIXTURE'where state='RUNNING'`)
const results=[]
const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,1600)})}}
let initial
await test('OW13A_LOCAL_MISSING_DATA_NO_JOB',async()=>{
 const a=await call(),b=await call(true);assert.equal(a.state,'NOT_READY');assert.deepEqual(a.readiness.reasons,['NO_ACTIVE_PRODUCTS']);assert.equal(b.state,'NOT_READY');assert.deepEqual(await counts(),{intents:0,jobs:0,units:0,marks:0})
 await set('statement_timeout','8000');const tick=(await db.query('select cp7_alert_native.analysis_tick()v')).rows[0].v;assert.equal(tick.initial_analysis.outcome,'NO_CURRENT_PLANNING_ACTOR')
 return{missing_products:true,no_job:true,no_profile_actor_no_impersonation:true}
})
await test('OW13A_LOCAL_MISSING_AND_STALE_PROFILE',async()=>{
 source.facts.products=[{id:product,root_id:root,size_id:size,sku:'LOCAL-INITIAL',product_name:'Controlled initial analysis',is_active:true}];await put()
 let r=await call(true);assert.deepEqual(r.readiness.reasons,['PLANNING_PROFILE_INCOMPLETE']);assert.equal(r.readiness.candidates[0].root_id,root)
 source.profiles=[{...profile,product_version_id:id(99)}];await put();assert.equal((await call(true)).state,'NOT_READY')
 source.profiles=[profile,profile];await put();assert.equal((await call(true)).state,'NOT_READY')
 source.profiles=[profile];source.status='INCOMPLETE';await put();assert.deepEqual((await call(true)).readiness.reasons,['SOURCE_INCOMPLETE'])
 source.status='COMPLETE';await put();assert.deepEqual(await counts(),{intents:0,jobs:0,units:0,marks:0});return{missing_and_wrong_version_and_ambiguous_profile_refused:true,incomplete_source_refused:true}
})
await test('OW13A_LOCAL_READY_READ_ONLY_THEN_ENSURE_EXACT_JOB',async()=>{
 const status=await call();assert.equal(status.state,'READY');assert.deepEqual(await counts(),{intents:0,jobs:0,units:0,marks:0})
 await writeFile('tests/fixtures/initialAnalysisReadyActual.json',JSON.stringify(status,null,2)+'\n')
 initial=await call(true);assert.equal(initial.state,'RUNNING');assert.deepEqual(initial.query,query);assert.deepEqual(initial.job_query,query)
 assert.equal(initial.job.request_id,(await db.query('select request_id::text from cp7_initial_analysis.intents')).rows[0].request_id)
 assert.equal(initial.job.reference.source_hash,(await db.query('select source_hash from cp7_analysis_stage.jobs')).rows[0].source_hash)
 assert.equal((await db.query('select reference from cp7_analysis_stage.jobs')).rows[0].reference.financial_capture,'DEFERRED')
 assert.deepEqual(await counts(),{intents:1,jobs:1,units:1,marks:1});await writeFile('tests/fixtures/initialAnalysisRunningActual.json',JSON.stringify(initial,null,2)+'\n')
 return{real_create_job_and_status:true,operational_only:true,single_UUID_and_capture:true}
})
await test('OW13A_LOCAL_REPEATED_CLOCK_AND_SOURCE_NEVER_RESPAWN',async()=>{
 for(let i=0;i<4;i++){source.captured_at=`2026-10-23T0${i+1}:00:00Z`;source.planning_time_bucket=source.captured_at;source.material_source.captured_at=source.captured_at;source.fabric_source.captured_at=source.captured_at;await put();const r=await call(true);assert.equal(r.job.request_id,initial.job.request_id);assert.equal(r.source_changed,false)}
 source.facts.stock=[{id:id(40),qty_signed:'10'}];await put();const changed=await call(true);assert.equal(changed.source_changed,true);assert.equal(changed.job.request_id,initial.job.request_id)
 await failed();assert.equal((await call(true)).state,'FAILED');assert.deepEqual(await counts(),{intents:1,jobs:1,units:1,marks:1})
 await db.exec(`update cp7_analysis_stage.jobs set updated_at=clock_timestamp()-interval'8 days'`);assert.equal((await call(true)).state,'EXPIRED');assert.equal((await counts()).jobs,1)
 return{unchanged_minutes_no_repeat:true,changed_source_is_labelled:true,failed_or_expired_no_retry_loop:true}
})
await test('OW13A_LOCAL_CLOSED_MODE_AND_LEGACY_REQUEST_REPLAY',async()=>{
 for(const [q,req]of[[{initial_auto:'STATUS',finance_mode:'STAGED'},null],[{initial_auto:null},null],[{initial_auto:true},null],[{initial_auto:'NO'},null],[{initial_auto:'ENSURE'},randomUUID()],['initial_auto',null],[['initial_auto'],null]]){
  await assert.rejects(()=>db.query('select cp7_analysis_stage.request($1::jsonb,$2::uuid)',[JSON.stringify(q),req]),/CP7_INITIAL_MODE/)
 }
 const req=randomUUID(),first=(await db.query('select cp7_analysis_stage.request($1::jsonb,$2::uuid)v',[JSON.stringify(query),req])).rows[0].v
 const again=(await db.query('select cp7_analysis_stage.request($1::jsonb,$2::uuid)v',[JSON.stringify(query),req])).rows[0].v;assert.deepEqual(first,again);assert.ok(!Object.hasOwn(first,'automatic_scope'))
 await assert.rejects(()=>db.query('select cp7_analysis_stage.request($1::jsonb,$2::uuid)',[JSON.stringify({...query,group_mode:'RESTATED'}),req]),/CP7_ANALYSIS_REQUEST_CHANGED/)
 await failed();return{mixed_or_nonobject_modes_refused:7,legacy_full_JSON_replay:true,changed_legacy_body_refused:true}
})
await test('OW13A_LOCAL_CURRENT_OWNER_AND_FRESH_RIGHTS',async()=>{
 for(const actor of[admin,inactive]){await login(actor);await assert.rejects(()=>call(true),/CP7_(INITIAL_OWNER_OR_ADMIN_REQUIRED|ACCESS_DENIED)/)}
 await login(second);await set('ow13a.deny','sales.invoice.view');await assert.rejects(()=>call(true),/CP7_ACCESS_DENIED/)
 await login(second);const before=await counts();await set('ow13a.source_revoke','yes');await assert.rejects(()=>call(true),/CP7_INITIAL_ACCESS_CHANGED/);await set('ow13a.source_revoke','');assert.deepEqual(await counts(),before)
 await login(owner);await set('ow13a.source_revoke','yes');await assert.rejects(()=>call(),/CP7_INITIAL_ACCESS_CHANGED/);await login(owner)
 return{wrong_role_inactive_missing_right_refused:true,revocation_after_source_no_orphan:true,existing_facts_withheld_on_changed_access:true}
})
await test('OW13A_LOCAL_EXISTING_OWN_JOB_HOLDS_INITIAL',async()=>{
 await login(second);await db.query('select cp7_analysis_stage.request($1::jsonb,$2::uuid)',[JSON.stringify({...query,group_mode:'RESTATED'}),randomUUID()])
 const before=await counts(),r=await call(true);assert.equal(r.state,'BUSY');assert.equal(r.job,null);assert.deepEqual(await counts(),before)
 await failed();await login(owner);return{own_running_job_for_different_query_holds_initial_without_duplication:true}
})
await test('OW13A_LOCAL_REUSES_IDENTICAL_EXISTING_MANUAL_JOB',async()=>{
 await db.query("insert into public.fixture_access values($1,'OWNER',true)",[id(6)]);await login(id(6))
 const key=randomUUID(),manual=(await db.query('select public.erp_cp7_request_staged_analysis_v1($1::jsonb,$2::uuid)v',[JSON.stringify(query),key])).rows[0].v
 const before=await counts(),r=await call(true);assert.equal(r.job.request_id,manual.request_id)
 const after=await counts();assert.equal(after.jobs,before.jobs);assert.equal(after.units,before.units);assert.equal(after.marks,before.marks);assert.equal(after.intents,before.intents+1)
 await failed();await login(owner);return{same_owner_query_access_and_semantic_source_reuses_manual_UUID:true,no_extra_job_or_unit_or_capture_mark:true}
})
await test('OW13A_LOCAL_SERVER_TICK_WITHOUT_WA_AND_CLAIMS_RESTORED',async()=>{
 await db.query('insert into cp7_profile.profiles values($1,clock_timestamp())',[second])
 await db.query("insert into cp7_profile.profiles values($1,clock_timestamp()+interval'1 minute'),($2,clock_timestamp()+interval'2 minutes')",[admin,inactive])
 await set('statement_timeout','8000');await set('request.jwt.claims','{"sub":"'+owner+'","role":"authenticated","sentinel":true}');await set('request.jwt.claim.sub',owner);await set('request.jwt.claim','{"sub":"'+owner+'","role":"authenticated","legacy":true}')
 const settings=async()=>(await db.query("select current_setting('request.jwt.claims',true)claims,current_setting('request.jwt.claim.sub',true)sub,current_setting('request.jwt.claim',true)claim")).rows[0]
 const before=await settings(),countBefore=await counts(),r=(await db.query('select cp7_alert_native.analysis_tick()v')).rows[0].v
 assert.equal(r.outcome,'NOT_CONFIGURED');assert.equal(r.initial_analysis.state,'RUNNING');assert.equal(r.initial_analysis.actor,second);assert.deepEqual(await settings(),before)
 assert.equal((await counts()).jobs,countBefore.jobs+1)
 await set('ow13a.poison_source','yes')
 const again=(await db.query('select cp7_alert_native.analysis_tick()v')).rows[0].v;assert.equal(again.initial_analysis.outcome,'INITIAL_ALREADY_REQUESTED');assert.equal(again.initial_analysis.request_id,r.initial_analysis.job.request_id);assert.deepEqual(await settings(),before)
 await set('ow13a.poison_source','');assert.equal((await counts()).jobs,countBefore.jobs+1);await failed()
 return{real_tick_before_WA_configuration:true,all_three_claim_settings_restored:true,no_browser_or_WA_request:true,second_tick_same_UUID_and_no_source_recapture:true,revoked_and_nonowner_profile_actors_skipped:true}
})
await test('OW13A_LOCAL_LEGACY_TICK_CONTINUES_AND_FAILED_INITIAL_IS_VISIBLE',async()=>{
 await db.query('insert into cp7_alert_native.settings_adapter values(row(1,$1::uuid,$1::uuid)::cp7_alert_native.settings)',[owner])
 const r=(await db.query('select cp7_alert_native.analysis_tick()v')).rows[0].v;assert.equal(r.outcome,'CONTROLLED_LEGACY_ANALYSIS_UNIT');assert.equal(r.initial_analysis.state,'FAILED')
 await db.query("insert into public.fixture_access values($1,'OWNER',true)",[id(5)]);await db.query("insert into cp7_profile.profiles values($1,clock_timestamp()+interval'3 minutes')",[id(5)])
 await set('ow13a.poison_source','yes');const bad=(await db.query('select cp7_alert_native.analysis_tick()v')).rows[0].v
 assert.equal(bad.outcome,'CONTROLLED_LEGACY_ANALYSIS_UNIT');assert.equal(bad.initial_analysis.outcome,'INITIAL_ANALYSIS_ERROR');assert.equal(bad.initial_analysis.sqlstate,'P0001');await set('ow13a.poison_source','')
 return{legacy_unit_still_called:true,initial_error_observable_without_breaking_legacy_unit:true}
})
await test('OW13A_LOCAL_IMMUTABLE_INTENT_AND_PRIVATE_GRANTS',async()=>{
 await assert.rejects(()=>db.exec('update cp7_initial_analysis.intents set semantic_hash=repeat(\'b\',64)'),/CP7_RUN_IMMUTABLE/)
 await assert.rejects(()=>db.exec('delete from cp7_initial_analysis.intents'),/CP7_RUN_IMMUTABLE/)
 for(const role of['authenticated','anon','service_role']){
  const r=(await db.query("select has_schema_privilege($1,'cp7_initial_analysis','USAGE')u,has_table_privilege($1,'cp7_initial_analysis.intents','SELECT,INSERT,UPDATE,DELETE')t,has_function_privilege($1,'cp7_initial_analysis.tick()','EXECUTE')f",[role])).rows[0];assert.deepEqual(r,{u:false,t:false,f:false})
 }
 return{intent_append_only:true,public_roles_have_no_private_access:true}
})
await login(owner)
const fixture=await call()
await mkdir('tests/fixtures',{recursive:true});await writeFile('tests/fixtures/initialAnalysisActual.json',JSON.stringify(fixture,null,2)+'\n')
const installer=await stageAudit.afterUse()
const sql=await read('scripts/cp7_initial_analysis_stage/initial.sql')
const report={classification:'LOCAL_REAL_INITIAL_SQL_AND_STAGED_JOB_WITH_CONTROLLED_ERP_SOURCE_IDENTITY_AND_WA_UNIT_NOT_NATIVE',
 status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',passed:results.filter(r=>r.status==='PASS').length,total:results.length,
 sql_sha256:createHash('sha256').update(sql).digest('hex'),installer,results,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow13a',{recursive:true});await writeFile('docs/cp7/d17-14/ow13a/local-initial.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
