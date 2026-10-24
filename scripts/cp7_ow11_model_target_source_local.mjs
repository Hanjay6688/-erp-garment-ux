// Actual v2 and current-source SQL with explicitly controlled history/access.
import {writeFile} from 'node:fs/promises'
import {randomUUID,createHash} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
import {modelRegistryFixture} from './cp7_ow11_model_registry_local_fixture.mjs'
execFileSync('python',['-B','-c','import cp7_model_target_source as s;s.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
const {db,read,cases,sql,actor,key,history,q,seed,test,rejects}=await modelRegistryFixture({currentDay:true})
await db.exec(`alter table cp7_planning.history_runs add column request_id uuid default gen_random_uuid();
alter table cp7_planning.history_runs owner to cp7_capture;grant usage on schema extensions to cp7_capture;
create function cp7_private.access_now()returns jsonb language plpgsql volatile as $$begin
 if current_setting('model_target_test.active',true)is distinct from'true'then raise exception using errcode='42501',message='CONTROLLED_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',current_setting('model_target_test.actor'),'profile',jsonb_build_object('revision',current_setting('model_target_test.access_epoch')));
end$$;
create function cp7_planning.history_source()returns jsonb language plpgsql volatile as $$declare n integer;facts jsonb;begin
 n:=coalesce(nullif(current_setting('model_target_test.history_calls',true),''),'0')::integer+1;
 perform set_config('model_target_test.history_calls',n::text,true);
 facts:=jsonb_build_object('sentinel',current_setting('model_target_test.facts'));
 if current_setting('model_target_test.change_second',true)='true'and n>=2 then facts:=jsonb_build_object('sentinel','changed during capture');end if;
 if current_setting('model_target_test.revoke_second',true)='true'and n>=2 then perform set_config('model_target_test.active','false',true);end if;
 return jsonb_build_object('status',current_setting('model_target_test.history_state'),'facts',facts);
end$$;`)
await sql("select set_config('model_target_test.actor',$1,false)v",[actor])
for(const[k,v]of Object.entries({active:'true',access_epoch:'1',facts:'original',history_state:'COMPLETE',history_calls:'0',change_second:'false',revoke_second:'false'}))await sql('select set_config($1,$2,false)v',['model_target_test.'+k,v])
await db.exec("update cp7_planning.history_runs set dependency_hash=encode(pg_catalog.sha256(convert_to(jsonb_build_object('sentinel','original')::text,'UTF8')),'hex')")
const historySql=await read('scripts/cp7-src/planning/history.sql'),i=historySql.indexOf('create function cp7_planning.serve_history(')
assert.ok(i>=0);await db.exec(historySql.slice(i,historySql.indexOf('$$;',i)+3))
await db.exec(await read('scripts/cp7_model_evaluation_v2_stage/runtime.sql'))
await db.exec(await read('scripts/cp7_model_target_source/source.sql'))
const capture=(p=q)=>sql('select public.erp_cp7_capture_model_evaluation_v2($1::jsonb,$2::uuid)v',[JSON.stringify(p),randomUUID()])
const current=(keys=[key],at=null)=>sql('select cp7_model_target_source.capture($1::text[],coalesce($2::timestamptz,clock_timestamp()))v',[keys,at])
const reset=()=>sql("select set_config('model_target_test.history_calls','0',true)v")
const setting=(k,v)=>sql('select set_config($1,$2,true)v',['model_target_test.'+k,v])
const stored=id=>sql('select to_jsonb(r)v from cp7_model_registry_adapter.runs r where id=$1::uuid',[id])
const ready=async()=>{await seed();const r=await capture();assert.equal(r.current_guard.state,'ELIGIBLE');await reset();return r}
await test('NO_OWN_MODEL_NO_SOURCE_SCAN_AND_STABLE_IDENTITY',async()=>{
 await reset();const a=await current(),b=await current();assert.equal(a.rows[0].reason,'NO_OWN_MODEL_EVALUATION');assert.equal(a.rows[0].forecast,null);assert.equal(a.source_hash,b.source_hash)
 assert.equal(await sql("select current_setting('model_target_test.history_calls')v"),'0');return{no_fabricated_model:true,no_unneeded_global_scan:true}
})
await test('ACTUAL_V2_SOURCE_CURRENT_GUARD_AND_SHARED_TWO_SCANS',async()=>{
 const r=await ready(),before=await stored(r.run_id),s=await current()
 assert.equal(s.rows[0].state,'ELIGIBLE');assert.equal(s.rows[0].run_id,r.run_id);assert.equal(s.rows[0].history_run_id,history)
 assert.deepEqual(s.rows[0].forecast,r.assessment.activation.forecast);assert.equal(s.rows[0].history_query.through_date,r.assessment.source.through_date)
 assert.equal(await sql("select current_setting('model_target_test.history_calls')v"),'2');assert.deepEqual(await stored(r.run_id),before)
 return{actual_v2_rows_and_guard:true,source_access_controlled:true,two_global_scans_independent_of_target_count:true}
})
await test('LATEST_BASELINE_RESULT_NEVER_CHERRY_PICKS_OLDER_WINNER',async()=>{
 const older=await ready(),newer=await capture({...q,horizon_days:'90'}),s=await current()
 assert.equal(newer.current_guard.state,'BASELINE_REQUIRED');assert.notEqual(older.run_id,newer.run_id);assert.equal(s.rows[0].run_id,newer.run_id);assert.equal(s.rows[0].state,'BASELINE_REQUIRED');assert.equal(s.rows[0].forecast,null)
 return{newest_evaluation_governs_even_without_winner:true}
})
await test('CHANGED_PHYSICAL_SOURCE_RETIRES_VECTOR_WITHOUT_REWRITING_RUN',async()=>{
 const r=await ready(),before=await stored(r.run_id);await setting('facts','changed before capture');const s=await current()
 assert.equal(s.rows[0].reason,'NATIVE_HISTORY_SOURCE_CHANGED');assert.equal(s.rows[0].forecast,null);assert.deepEqual(await stored(r.run_id),before)
 return{controlled_source_change:true,immutable_result_retained:true}
})
await test('SOURCE_CHANGE_BETWEEN_TWO_READS_REFUSES_WHOLE_CAPTURE',async()=>{
 await ready();await setting('change_second','true');await rejects(()=>current(),/CP7_MODEL_TARGET_HISTORY_CHANGED_DURING_CAPTURE/)
 return{no_mixed_source_allowed:true}
})
await test('CURRENT_POLICY_WITHDRAWAL_NEVER_REUSES_OLD_ADMISSION',async()=>{
 const r=await ready(),before=await stored(r.run_id),at=await sql('select cp7_planning.utc(clock_timestamp())v')
 await seed({revision:'2',state:'SUSPENDED',at});const s=await current();assert.equal(s.rows[0].reason,'ACTIVATION_POLICY_CHANGED');assert.equal(s.rows[0].forecast,null);assert.deepEqual(await stored(r.run_id),before)
 return{current_policy_controls_consumption_reference:true}
})
await test('MODEL_ENGINE_CHANGE_RETIRES_OLD_VECTOR',async()=>{
 await ready();await db.exec('create function cp7_model_native.changed_engine()returns integer language sql as $$select 1$$')
 const s=await current();assert.equal(s.rows[0].reason,'MODEL_ENGINE_CHANGED');assert.equal(s.rows[0].forecast,null)
 return{engine_bound:true}
})
await test('CONSUMER_ENGINE_CHANGES_SOURCE_IDENTITY_WITHOUT_FAKING_MODEL_CHANGE',async()=>{
 await ready();const before=await current();await db.exec('create function cp7_model_target_source.changed_engine()returns integer language sql as $$select 1$$');const after=await current()
 assert.equal(after.rows[0].state,'ELIGIBLE');assert.equal(after.engine_hash,before.engine_hash);assert.notEqual(after.consumer_engine_hash,before.consumer_engine_hash);assert.notEqual(after.source_hash,before.source_hash)
 return{separate_consumer_version_in_source_identity:true}
})
await test('INCOMPLETE_HISTORY_SCOPE_NEVER_TRUNCATES_OR_IMPUTES_ZERO',async()=>{
 await ready();await setting('history_state','INCOMPLETE');const s=await current();assert.equal(s.rows[0].state,'BASELINE_REQUIRED');assert.equal(s.rows[0].forecast,null)
 return{existing_Native_1000_product_bound_explicit:true,factory_bounded_model_history_not_qualified:true}
})
await test('CURRENT_ACCESS_EPOCH_CHANGES_SOURCE_IDENTITY_FOR_SAME_ACTOR',async()=>{
 await ready();const before=await current();await setting('access_epoch','2');const after=await current()
 assert.equal(after.actor_scope_id,before.actor_scope_id);assert.equal(after.rows[0].state,'ELIGIBLE');assert.deepEqual(after.rows,before.rows)
 assert.notEqual(after.access_epoch,before.access_epoch);assert.notEqual(after.source_hash,before.source_hash)
 return{same_actor_permission_or_profile_epoch_bound:true,old_source_identity_not_reused:true}
})
await test('CURRENT_ACTOR_OWNS_MODEL_RUNS_AND_ACCESS_RECHECKS_AFTER_SOURCE',async()=>{
 await ready();await setting('actor',randomUUID());const foreign=await current();assert.equal(foreign.rows[0].run_id,null);assert.equal(foreign.rows[0].forecast,null)
 await setting('actor',actor);await reset();await setting('revoke_second','true');await rejects(()=>current(),/CONTROLLED_ACCESS_DENIED/)
 return{no_cross_actor_model_reuse:true,controlled_current_access_rechecked:true}
})
await test('OLD_CUTOFF_NEWER_RUN_AND_FUTURE_CLOCK_REFUSED',async()=>{
 const before=await sql("select cp7_planning.utc(clock_timestamp()-interval'1 second')v");await ready()
 await rejects(()=>current([key],before),/CP7_MODEL_TARGET_NEWER_EVALUATION_REQUIRES_NEW_CAPTURE/)
 const future=await sql("select cp7_planning.utc(clock_timestamp()+interval'1 minute')v");await rejects(()=>current([key],future),/CP7_MODEL_TARGET_SOURCE_QUERY/)
 return{no_future_or_superseded_evaluation_source:true}
})
await test('CLOSED_TARGET_SET_AND_PRIVATE_ACL',async()=>{
 for(const targets of[[key,key],['invalid'],[null]])await rejects(()=>current(targets),/CP7_MODEL_TARGET_SOURCE_QUERY/)
 for(const role of['anon','authenticated','service_role'])assert.equal(await sql("select has_function_privilege($1,'cp7_model_target_source.capture(text[],timestamp with time zone)','EXECUTE')v",[role]),false)
 return{no_public_entry_no_duplicate_or_unbounded_query:true}
})
const report={contract:'cp7.model-target-source-local.v1',status:cases.every(x=>x.status==='PASS')?'PASS':'FAIL',expected:13,counts:cases.reduce((a,x)=>(a[x.status]=(a[x.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_target_source/source.sql')).digest('hex'),actual_SQL:true,explicit_synthetic_history_and_policy:true,actual_v2_and_original_serve_history_SQL:true,controlled_access_and_history_source:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,caller_integrated:false,bounded_factory_model_history_adapter_qualified:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-target-source-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
