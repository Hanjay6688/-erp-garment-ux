// Actual SQL over explicitly synthetic history; shared fixture does not grant Native credit.
import {writeFile} from 'node:fs/promises'
import {randomUUID,createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {modelRegistryFixture} from './cp7_ow11_model_registry_local_fixture.mjs'
const {db,read,cases,sql,root,key,day,q,native,legacyBefore,legacyResult,dataset,source,registry,bind,context,assess,seed,test,rejects,template}=await modelRegistryFixture()
await test('LEGACY_DATASET_RESULT_AND_NAMESPACE_UNCHANGED',async()=>{
 assert.deepEqual(await native(),legacyBefore);assert.deepEqual(await sql('select cp7_model_native.build($1::jsonb)v',[JSON.stringify(await native())]),legacyResult)
 assert.equal(await sql('select count(*)::integer v from cp7_model_native.runs'),0)
 return{v1_dataset_and_result_byte_meaning_unchanged:true,no_v1_run_insert_or_UUID_reuse:true}
})
await test('NO_POLICY_RETAINS_BASELINE_WITHOUT_DEFAULT',async()=>{
 const d=await dataset(),r=await assess(d);assert.equal(d.policy_source,null);assert.equal(r.activation.reason,'EXPLICIT_ACTIVATION_POLICY_REQUIRED');assert.equal(r.activation.forecast,null)
 assert.deepEqual(d.series,legacyBefore.series);assert.equal(r.forecast_applied,false)
 return{same_capture_knowledge_and_series:true,no_policy_invented:true}
})
await test('EXPLICIT_PROSPECTIVE_ALLOWED_MODEL_AND_DATED_VECTOR',async()=>{
 const p=await seed(),d=await dataset(),r=await assess(d)
 assert.deepEqual(d.policy_source,p);assert.equal(d.configuration.challengers.length,1);assert.equal(d.configuration.challengers[0].method,'NAIVE')
 assert.equal(r.activation.state,'ELIGIBLE');assert.equal(r.activation.selected_model.method,'NAIVE');assert.deepEqual(r.activation.forecast.forecasts,Array(7).fill('100.000000000000'))
 assert.equal(r.activation.forecast_from_date,day(100));assert.equal(r.current_consumption_recheck_required,true)
 assert.equal(r.evaluation.evaluation.challengers[0].summary.mae,'4.0000000000000000');assert.equal(r.activation.forecast_applied,false)
 return{explicit_synthetic_NAIVE100_each_day:true,paired_MAE:'4',only_allowed_candidates_compete:true,no_forecast_consumer_changed:true}
})
await test('ACTUAL_POLICY_WRITE_CANNOT_APPROVE_OLDER_CAPTURE',async()=>{
 const before=await dataset(),w=await sql('select cp7_model_policy.workspace()v')
 const command={contract_version:'cp7.model-activation-policy-command.v1',action:'SET',config:{minimum_training_days:'20',maximum_horizon_days:'90',allowed_methods:['NAIVE'],promotion:template.policy},template_hash:w.model_template.hash,reason:'Explicit actual-clock controlled access test',reviewed:true,expected_revision:'0',access_epoch:w.access_epoch}
 const saved=await sql('select public.erp_cp7_save_model_activation_policy_v1($1::jsonb,$2::uuid)v',[JSON.stringify(command),randomUUID()])
 assert.ok(Date.parse(saved.policy.recorded_at)>Date.parse(before.known_as_of));assert.deepEqual(await dataset(),before)
 assert.equal(await source(before.known_as_of),null);assert.equal((await assess(before)).activation.reason,'EXPLICIT_ACTIVATION_POLICY_REQUIRED')
 return{actual_clock_write_not_backdated:true,old_capture_hash_and_admission_unchanged:true,controlled_access_only:true}
})
await test('ONE_MICROSECOND_SOURCE_CUTOFF',async()=>{
 const p=await seed({at:day(100)+'T01:00:00.123457Z'});assert.equal((await dataset()).policy_source,null)
 assert.deepEqual(await source(p.policy.recorded_at),p)
 const n=await native()
 await rejects(()=>registry(p.policy.registry_id).then(r=>bind(n,p,r,'b'.repeat(32))),/CP7_MODEL_REGISTRY_POLICY_NOT_KNOWN/)
 return{one_microsecond_late_policy_unavailable:true}
})
await test('LATE_REGISTRY_NEVER_BORROWS_OLDER_TECHNICAL_CLOCK',async()=>{
 await seed({at:day(99)+'T01:00:00.123456Z'});const d=await dataset(),r=await assess(d)
 assert.equal(r.activation.reason,'REGISTRY_NOT_KNOWN_BEFORE_VALIDATION');assert.notEqual(d.registered_at,legacyBefore.registered_at)
 return{technical_registration_does_not_approve_later_thresholds:true}
})
await test('SUSPEND_AND_NEW_POLICY_INVALIDATE_CURRENT_ADMISSION_ONLY',async()=>{
 await seed();const d=await dataset(),old=await assess(d);assert.equal(old.activation.state,'ELIGIBLE')
 const p=await seed({revision:'2',state:'SUSPENDED',at:day(100)+'T02:00:00.123456Z'})
 const r=await assess(d,context(d),p);assert.equal(r.activation.reason,'ACTIVATION_POLICY_CHANGED');assert.equal(r.activation.forecast,null);assert.deepEqual(r.evaluation,old.evaluation)
 assert.deepEqual(await dataset(),d);assert.deepEqual(await assess(d),old)
 return{historical_evaluation_retained:true,current_policy_recheck_required_and_fails_closed:true}
})
await test('SUSPENDED_AT_CAPTURE_AND_NO_ALLOWED_METHOD',async()=>{
 await seed({state:'SUSPENDED',methods:[]});const d=await dataset(),r=await assess(d)
 assert.deepEqual(d.configuration.challengers,[]);assert.equal(r.activation.reason,'ACTIVATION_POLICY_SUSPENDED');assert.equal(r.activation.forecast,null)
 return{no_implicit_challenger_permission:true}
})
await test('ACTIVE_POLICY_WITH_NO_ALLOWED_METHOD_IS_EXPLICIT_BASELINE',async()=>{
 await seed({methods:[]});const d=await dataset(),r=await assess(d)
 assert.equal(r.activation.reason,'NO_EXPLICITLY_ALLOWED_CHALLENGER');assert.equal(r.activation.state,'BASELINE_REQUIRED');assert.equal(r.activation.forecast,null)
 assert.equal(r.evaluation,null);assert.equal(r.evaluation_state,'NOT_REQUESTED_NO_ALLOWED_CHALLENGER');assert.deepEqual(r.baseline,{method:'MEAN',daily_mean:'50.5'})
 return{empty_permission_is_supported_without_invented_candidate_or_fake_backtest:true}
})
await test('REGISTRY_ID_CLOCK_POLICY_TEMPLATE_AND_NATIVE_DIGEST_SEALED',async()=>{
 const p=await seed(),n=await native(),r=await registry(p.policy.registry_id)
 for(const mutate of[x=>x.id='wrong',x=>x.registered_at='2026-06-02T00:00:00.123457Z',x=>x.configuration.activation_policy.revision='9',x=>x.configuration.policy.minimum_mae_improvement='1',x=>x.configuration.challengers[0].params={window:'2'}]){
  const copy=structuredClone(r);mutate(copy);await rejects(()=>bind(n,p,copy,'b'.repeat(32)),/CP7_MODEL_REGISTRY_POLICY_BINDING/)
 }
 const changed=structuredClone(n);changed.series[0].value='999';await rejects(()=>bind(changed,p,r,'b'.repeat(32)),/CP7_MODEL_REGISTRY_NATIVE_SOURCE_CHANGED/)
 return{five_registry_mutations_and_native_series_mutation_refused:true}
})
await test('ASSESSMENT_HASH_ENGINE_SOURCE_HORIZON_AND_DAY_BOUND',async()=>{
 await seed();const d=await dataset(),changed=structuredClone(d);changed.configuration.policy.minimum_mae_improvement='1'
 await rejects(()=>assess(changed),/CP7_MODEL_REGISTRY_DATASET_CHANGED/)
 for(const patch of[{source_hash:'c'.repeat(64)},{engine_hash:'d'.repeat(32)}])assert.equal((await assess(d,{...context(d),...patch})).activation.reason,'MODEL_EVIDENCE_NOT_CURRENT')
 assert.equal((await assess(d,{...context(d),horizon_days:'8'})).activation.reason,'MODEL_HORIZON_NOT_QUALIFIED')
 assert.equal((await assess(d,{...context(d),known_as_of:day(101)+'T01:00:00.123456Z',forecast_from_date:day(101)})).activation.reason,'MODEL_FORECAST_ORIGIN_NOT_CURRENT')
 return{no_mutated_dataset_or_stale_vector_used:true}
})
await test('ACTOR_SCOPE_AND_UNKNOWN_SIZE_STAY_NATIVE_FAIL_CLOSED',async()=>{
 await rejects(()=>dataset(q,randomUUID()),/CP7_MODEL_NATIVE_HISTORY_UNAVAILABLE/)
 await rejects(()=>dataset({...q,target_key:root+':'+randomUUID()}),/CP7_MODEL_NATIVE_TARGET_UNAVAILABLE/)
 return{actual_native_dataset_ownership_checks_reused:true,actual_Auth_HTTP_credit:false}
})
await test('SOURCE_HASH_BINDS_QUERY_POLICY_AND_ENGINE_NO_NEW_WRITES',async()=>{
 const p=await seed(),d=await dataset(),n=await native(),r=await registry(p.policy.registry_id)
 const h=await dataset({...q,horizon_days:'8'});assert.notEqual(h.source_hash,d.source_hash)
 assert.notEqual((await bind(n,p,r,'b'.repeat(32))).source_hash,d.source_hash)
 assert.equal(await sql('select count(*)::integer v from cp7_model_native.runs'),0);assert.equal(await sql('select count(*)::integer v from cp7_model_policy.commands'),0)
 const privateRows=(await db.query("select p.proname,pg_get_userbyid(p.proowner)owner,p.prosecdef,p.proconfig,has_function_privilege('authenticated',p.oid,'EXECUTE')allowed from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_model_registry_adapter'")).rows
 assert.equal(privateRows.length,4);for(const f of privateRows){assert.equal(f.owner,'cp7_capture');assert.equal(f.prosecdef,false);assert.equal(f.allowed,false);assert.deepEqual(f.proconfig,['search_path=""','TimeZone=UTC'])}
 return{query_and_engine_in_digest:true,private4_public0_table0_replacement0:true,no_automatic_evaluation_capture:true}
})
const report={contract:'cp7.model-registry-adapter-local.v1',status:cases.every(x=>x.status==='PASS')?'PASS':'FAIL',expected:13,counts:cases.reduce((a,x)=>(a[x.status]=(a[x.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_registry_adapter/adapter.sql')).digest('hex'),actual_SQL:true,actual_existing_native_dataset_and_model_build:true,explicit_synthetic_history_capture_rows_and_past_policy:true,controlled_access_and_sha256_digest_adapter:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,catalog22_qualified:false,public_v2_capture_or_target_consumer:false,forecast_applied:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-registry-adapter-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
