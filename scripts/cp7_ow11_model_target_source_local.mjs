// Actual v2 and current-source SQL with explicitly controlled history/access.
import {writeFile} from 'node:fs/promises'
import {randomUUID,createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {modelTargetSourceFixture} from './cp7_ow11_model_target_source_local_fixture.mjs'
const {db,read,cases,sql,actor,key,history,q,seed,test,rejects,capture,current,reset,setting,stored,ready}=await modelTargetSourceFixture()
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
await test('WAREHOUSE_ONLY_READ_PRESERVED_WITHOUT_MODEL_POLICY_OR_HISTORY',async()=>{
 await ready();const optional=()=>sql('select cp7_model_target_source.capture_for_reorder($1::text[],clock_timestamp())v',[[key]])
 assert.equal((await optional()).source_hash,(await current()).source_hash)
 await setting('model_access','false');await reset();await rejects(()=>current(),/CONTROLLED_ACCESS_DENIED/)
 const a=await optional(),b=await optional();assert.equal(a.source_hash,b.source_hash);assert.equal(a.policy_source,null);assert.equal(a.live_history_source_hash,null);assert.equal(a.rows[0].reason,'MODEL_CURRENT_ACCESS_REQUIRED');assert.equal(a.rows[0].run_id,null);assert.equal(a.rows[0].forecast,null)
 assert.equal(await sql("select current_setting('model_target_test.history_calls')v"),'0')
 await setting('warehouse_access','false');await rejects(optional,/CONTROLLED_WAREHOUSE_ACCESS_DENIED/)
 return{existing_warehouse_read_retained:true,no_private_model_disclosed:true,full_model_reader_still_denied:true,revoked_warehouse_denied:true}
})
const report={contract:'cp7.model-target-source-local.v1',status:cases.every(x=>x.status==='PASS')?'PASS':'FAIL',expected:14,counts:cases.reduce((a,x)=>(a[x.status]=(a[x.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_target_source/source.sql')).digest('hex'),actual_SQL:true,explicit_synthetic_history_and_policy:true,actual_v2_and_original_serve_history_SQL:true,controlled_access_and_history_source:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,caller_integrated:false,bounded_factory_model_history_adapter_qualified:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-target-source-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
