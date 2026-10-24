// Actual selector SQL; explicitly synthetic rows/readers/access. No Native/Auth credit.
import assert from 'node:assert/strict'
import {randomUUID,createHash} from 'node:crypto'
import {readFile,writeFile} from 'node:fs/promises'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),actor=randomUUID(),other=randomUUID(),key=randomUUID()+':'+randomUUID(),key2=randomUUID()+':'+randomUUID(),cases=[]
await db.exec(`create role cp7_capture;create role anon;create role authenticated;create role service_role;
create schema cp7_planning;create schema cp7_private;create schema cp7_model_registry_adapter;create schema cp7_model_scoped_evaluation;
create table cp7_model_registry_adapter.runs(id uuid primary key,actor uuid,query jsonb,captured_at timestamptz,result jsonb);
create table cp7_model_scoped_evaluation.runs(like cp7_model_registry_adapter.runs including all);
create function cp7_planning.utc(t timestamptz)returns text language sql immutable as $$select to_char(t at time zone'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')$$;
create function cp7_private.access_now()returns jsonb language plpgsql volatile as $$begin
 if current_setting('model_selection_test.active')<>'true'then raise exception using errcode='42501',message='CONTROLLED_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',current_setting('model_selection_test.actor'),'epoch',current_setting('model_selection_test.epoch'));end$$;
create function public.controlled_model_reader(v integer,p_id uuid)returns jsonb language plpgsql volatile as $$
declare r record;n integer;outcome jsonb;state text;begin
 n:=current_setting('model_selection_test.reads')::integer+1;perform set_config('model_selection_test.reads',n::text,true);
 if v=2 then select *into r from cp7_model_registry_adapter.runs where id=p_id;
 else select *into r from cp7_model_scoped_evaluation.runs where id=p_id;end if;
 if r.actor::text<>current_setting('model_selection_test.actor')then raise exception 'CONTROLLED_FOREIGN_READER';end if;
 state:=case when current_setting('model_selection_test.change_guard')='true'and n>=2 then'BASELINE_REQUIRED'else r.result->>'state'end;
 if current_setting('model_selection_test.revoke')='true'then perform set_config('model_selection_test.epoch','CHANGED',true);end if;
 if current_setting('model_selection_test.newer')='true'and n=1 then
  insert into cp7_model_scoped_evaluation.runs values(gen_random_uuid(),r.actor,r.query,clock_timestamp(),'{"state":"BASELINE_REQUIRED"}');end if;
 outcome:=jsonb_build_object('contract_version',case v when 2 then'cp7.native-model-run.v2'else'cp7.scoped-model-run.v3'end,
  'run_id',r.id,'actor_scope_id',r.actor,'captured_at',cp7_planning.utc(r.captured_at),'query',r.query,
  'assessment',r.result,'current_guard',jsonb_build_object('state',state,'checked_at',cp7_planning.utc(clock_timestamp())),
  'forecast_applied',false,'production_go',false);
 if current_setting('model_selection_test.wrong_reader')='true'then outcome:=outcome||jsonb_build_object('contract_version','cp7.native-model-run.v1');end if;
 return outcome;end$$;
create function cp7_model_registry_adapter.serve(uuid)returns jsonb language sql volatile as $$select public.controlled_model_reader(2,$1)$$;
create function cp7_model_scoped_evaluation.serve(uuid)returns jsonb language sql volatile as $$select public.controlled_model_reader(3,$1)$$;`)
const source=await readFile('scripts/cp7_model_evaluation_selection/selection.sql','utf8');await db.exec(source)
const sql=async(s,p=[])=>(await db.query(s,p)).rows[0]?.v
const setting=(k,v)=>sql('select set_config($1,$2,true)v',['model_selection_test.'+k,String(v)])
const instant=offset=>sql("select cp7_planning.utc(clock_timestamp()+$1::integer*interval'1 second')v",[offset])
const seed=async(version,{id=randomUUID(),who=actor,target=key,at,state='ELIGIBLE'}={})=>{at??=await instant(-10);await db.query(`insert into ${version===2?'cp7_model_registry_adapter':'cp7_model_scoped_evaluation'}.runs values($1,$2,$3::jsonb,$4::timestamptz,$5::jsonb)`,[id,who,JSON.stringify({target_key:target}),at,JSON.stringify({state})]);return id}
const latest=async(targets=[key],who=actor,at=null)=>sql('select cp7_model_evaluation_selection.latest($1::text[],$2::uuid,coalesce($3::timestamptz,clock_timestamp()))v',[targets,who,at])
const current=(target=key,at=null)=>sql('select cp7_model_evaluation_selection.current($1,coalesce($2::timestamptz,clock_timestamp()))v',[target,at])
const rejects=async(fn,re)=>{await db.exec('savepoint refusal');try{await assert.rejects(fn,re)}finally{await db.exec('rollback to savepoint refusal;release savepoint refusal')}}
const test=async(id,fn)=>{await db.exec('begin');try{for(const[k,v]of Object.entries({actor,active:true,epoch:'CURRENT',reads:0,change_guard:false,revoke:false,newer:false,wrong_reader:false}))await setting(k,v);cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,2400)})}finally{await db.exec('rollback')}console.log(id+': '+cases.at(-1).status)}
await test('NO_EVALUATION_NO_READER_NO_FAKE_ZERO',async()=>{
 const a=await current(),b=await current();assert.equal(a.selection.run_id,null);assert.equal(a.selection.runtime,null);assert.equal(a.model,null);assert.equal(a.source_hash,b.source_hash);assert.equal(await sql("select current_setting('model_selection_test.reads')v"),'0');assert.deepEqual(await latest([]),[])
 return{empty_reference_no_reader:true}
})
await test('UUID_COLLISION_KEEPS_RUNTIME_AND_EXACT_READER',async()=>{
 const id=randomUUID();await seed(2,{id,at:await instant(-20)});await seed(3,{id,at:await instant(-10),state:'BASELINE_REQUIRED'})
 const r=await current();assert.equal(r.selection.run_id,id);assert.equal(r.selection.runtime,'SCOPED_V3');assert.equal(r.selection.read_method,'erp_cp7_read_model_evaluation_v3');assert.equal(r.model.contract_version,'cp7.scoped-model-run.v3');assert.equal(r.model.assessment.state,'BASELINE_REQUIRED')
 return{same_UUID_distinct_namespace:true,no_old_winner_reused:true}
})
await test('NEWER_GLOBAL_BASELINE_BEATS_OLDER_SCOPED_WINNER',async()=>{
 await seed(3,{at:await instant(-20)});const id=await seed(2,{state:'BASELINE_REQUIRED'}),r=await current()
 assert.equal(r.selection.run_id,id);assert.equal(r.selection.runtime,'GLOBAL_V2');assert.equal(r.model.assessment.state,'BASELINE_REQUIRED');return{time_precedes_version_preference:true}
})
await test('DETERMINISTIC_EXACT_TIMESTAMP_TIES',async()=>{
 const at=await instant(-10);await seed(2,{id:'ffffffff-ffff-4fff-8fff-ffffffffffff',at});await seed(3,{id:'11111111-1111-4111-8111-111111111111',at});const id=await seed(3,{id:'22222222-2222-4222-8222-222222222222',at})
 const r=(await latest())[0];assert.equal(r.run_id,id);assert.equal(r.runtime,'SCOPED_V3');return{version_then_UUID_breaks_exact_time_ties:true}
})
await test('ACTOR_TARGET_AND_KNOWLEDGE_CUTOFF',async()=>{
 const old=await seed(2,{at:await instant(-20)}),cutoff=await instant(-15);await seed(3);await seed(3,{who:other,at:await instant(-1)});await seed(3,{target:key2,at:await instant(-1)})
 assert.equal((await latest([key],actor,cutoff))[0].run_id,old)
 await rejects(()=>current(key,cutoff),/CP7_MODEL_SELECTION_NEWER_EVALUATION/)
 const foreign=(await latest([key],randomUUID()))[0];assert.equal(foreign.run_id,null)
 const rows=await latest([key2,key]);assert.deepEqual(rows.map(r=>r.target_key),[key,key2].sort());assert.equal(rows.length,2);return{closed_actor_target_cutoff:true}
})
await test('CHANGED_ACCESS_AND_SOURCE_REFUSE_REFERENCE',async()=>{
 await seed(3);await setting('revoke',true);await rejects(()=>current(),/CP7_MODEL_SELECTION_ACCESS_CHANGED/)
 await setting('revoke',false);await setting('change_guard',true);await rejects(()=>current(),/CP7_MODEL_SELECTION_SOURCE_CHANGED_DURING_READ/)
 return{current_access_after_read:true,source_changes_between_reads_refused:true}
})
await test('NEWER_EVALUATION_DURING_READER_REFUSES_WHOLE_REFERENCE',async()=>{
 await seed(2);await setting('newer',true);await rejects(()=>current(),/CP7_MODEL_SELECTION_CHANGED_DURING_READ/);return{post_read_selection_rechecked:true}
})
await test('WRONG_READER_CONTRACT_NEVER_RELABELLED',async()=>{
 await seed(3);await setting('wrong_reader',true);await rejects(()=>current(),/CP7_MODEL_SELECTION_READER_BINDING/);return{runtime_contract_bound:true}
})
await test('BOUNDED_QUERY_AND_PRIVATE_ACL',async()=>{
 for(const targets of[[key,key],['bad'],[null],Array(5001).fill(key)])await rejects(()=>latest(targets),/CP7_MODEL_SELECTION_QUERY/)
 await rejects(()=>latest([key],actor,'infinity'),/CP7_MODEL_SELECTION_QUERY/)
 const future=await instant(60)
 await rejects(()=>latest([key],actor,future),/CP7_MODEL_SELECTION_QUERY/)
 for(const role of['anon','authenticated','service_role']){
  assert.equal(await sql("select has_function_privilege($1,'cp7_model_evaluation_selection.current(text,timestamp with time zone)','EXECUTE')v",[role]),false)
  assert.equal(await sql("select has_schema_privilege($1,'cp7_model_evaluation_selection','USAGE')v",[role]),false)
 }
 assert.equal(await sql("select bool_and(not p.prosecdef and pg_get_userbyid(p.proowner)='cp7_capture')v from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_model_evaluation_selection'"),true)
 return{bounded_inputs_no_public_entry:true}
})
const report={contract:'cp7.model-evaluation-selection-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',expected:9,counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(source).digest('hex'),actual_SQL:true,synthetic_rows_and_controlled_readers_access:true,actual_Native:false,actual_Auth_HTTP_credit:false,actual_concurrency:false,target_caller_integrated:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-evaluation-selection-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
