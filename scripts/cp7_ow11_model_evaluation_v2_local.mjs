// Immutable v2 SQL with controlled access/history freshness, synthetic history.
import {writeFile} from 'node:fs/promises'
import {randomUUID,createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {modelRegistryFixture} from './cp7_ow11_model_registry_local_fixture.mjs'
const {db,read,cases,sql,actor,history,q,seed,test,rejects,day}=await modelRegistryFixture({currentDay:true})
await db.exec(`alter table cp7_planning.history_runs owner to cp7_capture;
grant usage on schema extensions to cp7_capture;
create function cp7_private.access_now()returns jsonb language plpgsql volatile as $$begin
 if current_setting('model_v2_test.active',true)is distinct from'true'then raise exception using errcode='42501',message='CONTROLLED_CURRENT_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',current_setting('model_v2_test.actor'),'profile',jsonb_build_object('role_code','OWNER'));
end $$;
create function cp7_planning.serve_history(p uuid)returns jsonb language plpgsql volatile as $$declare a jsonb;begin
 a:=cp7_private.access_now();if not exists(select 1 from cp7_planning.history_runs where id=p and actor=(a->>'actor')::uuid)then raise exception using errcode='42501',message='CONTROLLED_HISTORY_UNAVAILABLE';end if;
 return jsonb_build_object('run_id',p,'source_state',current_setting('model_v2_test.history_state'));
end $$;`)
await sql("select set_config('model_v2_test.actor',$1,false)v",[actor]);await db.exec("select set_config('model_v2_test.active','true',false);select set_config('model_v2_test.history_state','UNCHANGED',false)")
await db.exec(await read('scripts/cp7_model_evaluation_v2_stage/runtime.sql'))
const fkRows=(await db.query(`select t.tgrelid::regclass::text||':'||k.conrelid::regclass::text||':'||k.conname||':'||t.tgfoid::regprocedure::text||':'||t.tgtype::text as key from pg_trigger t join pg_constraint k on k.oid=t.tgconstraint where k.conrelid='cp7_model_registry_adapter.runs'::regclass and t.tgrelid in('cp7_model_native.registry'::regclass,'cp7_planning.history_runs'::regclass)`)).rows
const manifest=JSON.parse(await read('scripts/cp7_model_evaluation_v2_stage/MANIFEST.json'))
assert.deepEqual(fkRows.map(x=>x.key).sort(),manifest.parent_fk_triggers)
const capture=(p=q,k=randomUUID())=>sql('select public.erp_cp7_capture_model_evaluation_v2($1::jsonb,$2::uuid)v',[JSON.stringify(p),k])
const serve=id=>sql('select public.erp_cp7_read_model_evaluation_v2($1::uuid)v',[id])
const rows=()=>sql('select count(*)::integer v from cp7_model_registry_adapter.runs')
const row=id=>sql('select to_jsonb(r)v from cp7_model_registry_adapter.runs r where id=$1::uuid',[id])
const unchanged=(x,y)=>{const a=structuredClone(x),b=structuredClone(y);delete a.current_guard;delete b.current_guard;assert.deepEqual(a,b)}
await test('EMPTY_POLICY_CAPTURE_REPLAY_OWNS_ONE_IMMUTABLE_RUN',async()=>{
 const k=randomUUID(),r=await capture(q,k),before=await row(r.run_id),again=await capture(q,k)
 assert.equal(r.assessment.activation.reason,'EXPLICIT_ACTIVATION_POLICY_REQUIRED');assert.equal(r.current_guard.state,'BASELINE_REQUIRED')
 unchanged(r,again);assert.deepEqual(await row(r.run_id),before);assert.equal(await rows(),1)
 assert.equal(await sql('select count(*)::integer v from cp7_model_native.runs'),0)
 await rejects(()=>capture({...q,horizon_days:'8'},k),/CP7_MODEL_V2_REQUEST_CHANGED/)
 return{exact_UUID_and_immutable_assessment:true,one_v2_row_no_v1_write:true}
})
await test('EXPLICIT_SYNTHETIC_WINNER_CAPTURE_READER_DATED_VECTOR',async()=>{
 await seed();const r=await capture(),stored=await row(r.run_id),again=await serve(r.run_id)
 assert.equal(r.assessment.activation.state,'ELIGIBLE');assert.equal(r.current_guard.state,'ELIGIBLE')
 assert.deepEqual(r.assessment.activation.forecast.forecasts,Array(7).fill('100.000000000000'));assert.equal(r.assessment.activation.forecast_from_date,day(100))
 unchanged(r,again);assert.deepEqual(await row(r.run_id),stored);assert.equal(r.forecast_applied,false)
 return{synthetic_history_only:true,immutable_NAIVE100x7:true,read_does_not_recompute_or_apply_forecast:true}
})
await test('CURRENT_POLICY_WITHDRAWAL_PRESERVES_ORIGINAL_RESULT',async()=>{
 await seed();const r=await capture(),before=await row(r.run_id)
 const at=await sql('select cp7_planning.utc(clock_timestamp())v');await seed({revision:'2',state:'SUSPENDED',at})
 const stale=await serve(r.run_id);assert.equal(stale.current_guard.reason,'ACTIVATION_POLICY_CHANGED');assert.equal(stale.current_guard.state,'BASELINE_REQUIRED')
 assert.equal(stale.assessment.activation.state,'ELIGIBLE');unchanged(r,stale);assert.deepEqual(await row(r.run_id),before)
 const replay=await capture(q,r.request_id);unchanged(r,replay);assert.equal(replay.current_guard.reason,'ACTIVATION_POLICY_CHANGED')
 return{original_eligibility_is_history_only:true,current_guard_retires_policy_without_rewrite:true}
})
await test('STALE_HISTORY_NEW_CAPTURE_REFUSED_OLD_READ_RETIRED',async()=>{
 await seed();const r=await capture(),before=await row(r.run_id)
 await db.exec("select set_config('model_v2_test.history_state','ARCHIVED_STALE',true)")
 const stale=await serve(r.run_id);assert.equal(stale.current_guard.reason,'NATIVE_HISTORY_SOURCE_CHANGED');unchanged(r,stale)
 await rejects(()=>capture(),/CP7_MODEL_V2_HISTORY_STALE/);assert.equal(await rows(),1);assert.deepEqual(await row(r.run_id),before)
 return{controlled_history_freshness_standin:true,new_stale_capture_does_not_insert:true}
})
await test('REVOKED_ACTOR_PRECEDES_COMMITTED_REPLAY_AND_FOREIGN_READ',async()=>{
 const r=await capture(),before=await rows();await db.exec("select set_config('model_v2_test.active','false',true)")
 await rejects(()=>serve(r.run_id),/CONTROLLED_CURRENT_ACCESS_DENIED/);await rejects(()=>capture(q,r.request_id),/CONTROLLED_CURRENT_ACCESS_DENIED/)
 await db.exec("select set_config('model_v2_test.active','true',true)");await sql("select set_config('model_v2_test.actor',$1,true)v",[randomUUID()])
 await rejects(()=>serve(r.run_id),/CP7_MODEL_V2_RUN_UNAVAILABLE/);await rejects(()=>capture(),/CONTROLLED_HISTORY_UNAVAILABLE/);assert.equal(await rows(),before)
 return{controlled_current_access_standin:true,actual_Auth_HTTP_credit:false}
})
await test('CURRENT_GUARD_DAY_ENGINE_AND_CLOCK_NEVER_REQUALIFY_HISTORY',async()=>{
 await seed();const r=await capture(),stored=await row(r.run_id)
 const check=(engine,at)=>sql('select cp7_model_registry_adapter.current_guard($1::jsonb,$2::jsonb,$3::jsonb,$4::jsonb,$5,$6::timestamptz)v',[JSON.stringify(stored.input),JSON.stringify(stored.result),JSON.stringify({run_id:history,source_state:'UNCHANGED'}),JSON.stringify(stored.input.policy_source),engine,at])
 assert.equal((await check('b'.repeat(32),r.current_guard.checked_at)).reason,'MODEL_ENGINE_CHANGED')
 assert.equal((await check(stored.input.engine_hash,day(101)+'T01:00:00.123456Z')).reason,'MODEL_FORECAST_ORIGIN_NOT_CURRENT')
 assert.equal((await check(stored.input.engine_hash,day(99)+'T01:00:00.123456Z')).reason,'CURRENT_CLOCK_PRECEDES_EVALUATION')
 assert.deepEqual(await row(r.run_id),stored);return{old_vector_not_shifted_to_new_day:true,changed_engine_never_reuses_old_admission:true}
})
await test('EXACT_RAW_PAYLOAD_METHOD_NAMESPACE_AND_IMMUTABILITY',async()=>{
 const p={...q,history_run_id:q.history_run_id.toUpperCase()},k=randomUUID(),r=await capture(p,k)
 await rejects(()=>capture(q,k),/CP7_MODEL_V2_REQUEST_CHANGED/)
 for(const s of['update cp7_model_registry_adapter.runs set query=query','delete from cp7_model_registry_adapter.runs'])await rejects(()=>db.exec(s),/CP7_RUN_IMMUTABLE/)
 const saved=await row(r.run_id);assert.deepEqual(saved.payload,p);assert.deepEqual(saved.query,q);assert.equal(await rows(),1)
 return{raw_payload_bound_even_when_canonical_query_equal:true,v2_has_distinct_request_table_and_lock_namespace:true}
})
await test('FINAL_ROW_FAULT_AND_PRIVATE_ACL',async()=>{
 await db.exec("create function cp7_model_registry_adapter.test_fault()returns trigger language plpgsql as $$begin raise exception 'V2_LAST_ROW_FAULT';end$$;create trigger test_fault before insert on cp7_model_registry_adapter.runs for each row execute function cp7_model_registry_adapter.test_fault()")
 await rejects(()=>capture(),/V2_LAST_ROW_FAULT/);assert.equal(await rows(),0)
 await db.exec('drop trigger test_fault on cp7_model_registry_adapter.runs;drop function cp7_model_registry_adapter.test_fault()')
 for(const role of['anon','authenticated','service_role']){
  assert.equal(await sql("select has_table_privilege($1,'cp7_model_registry_adapter.runs','SELECT,INSERT,UPDATE,DELETE,TRUNCATE')v",[role]),false)
  assert.equal(await sql("select has_function_privilege($1,'public.erp_cp7_capture_model_evaluation_v2(jsonb,uuid)','EXECUTE')v",[role]),role==='authenticated')
 }
 return{fault_rolls_back_whole_capture:true,private_immutable_RLS_table:true,authenticated_only_facade:true}
})
const report={contract:'cp7.model-evaluation-v2-local.v1',status:cases.every(x=>x.status==='PASS')?'PASS':'FAIL',expected:8,counts:cases.reduce((a,x)=>(a[x.status]=(a[x.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_evaluation_v2_stage/runtime.sql')).digest('hex'),actual_SQL:true,explicit_synthetic_history_and_policy:true,controlled_access_history_freshness_and_sha256_adapter:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,catalog22_qualified:false,actual_concurrency:false,forecast_applied:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-evaluation-v2-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
