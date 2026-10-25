// Complete private SQL path on explicitly synthetic historical fixtures.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {writeFile} from 'node:fs/promises'
import {modelTargetSourceV2Fixture} from './cp7_ow11_model_target_source_v2_local_fixture.mjs'
import {modelTargetHooksV2Cases} from './cp7_ow11_model_target_hooks_v2_local.mjs'
const root='22222222-2222-4222-8222-222222222222',size='33333333-3333-4333-8333-333333333333',other='44444444-4444-4444-8444-444444444444'
const products=[root,other].map((id,i)=>({id,root_id:id,model_id:id,is_active:true,size_id:size,sku:'SYNTHETIC-'+i,product_name:'Controlled target '+i,commercial:[]}))
const f=await modelTargetSourceV2Fixture({products}),{db,read,sql,key,day,cases,test,rejects,seedScoped,currentV2:current,captureFacts,now}=f
const block=(s,n)=>{const r=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(r?.length,1,n);return r[0]}
await db.exec('create role cp7_alert;create schema cp7_product_analog_choice;create table cp7_product_analog_choice.choices(id uuid,target_key text,revision bigint,action text,evidence jsonb,reason text,actor uuid,request_id uuid,recorded_at timestamptz)')
await db.exec(block(await read('scripts/cp7_product_analog_choice_stage/choice.sql'),'cp7_product_analog_choice.source_at'))
for(const p of['scripts/cp7-src/demand/estimate.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql','scripts/cp7_product_analog_consumer/kernel.sql','scripts/cp7_product_analog_consumer/baseline.sql','scripts/cp7_product_analog_provenance_stage/provenance.sql','scripts/cp7_model_target_projection/projection.sql','scripts/cp7_model_target_consumer_v2/consumer.sql'])await db.exec(await read(p))
await db.exec(block(await read('scripts/cp7_product_analog_provenance_stage/hooks.sql'),'cp7_product_analog_consumer.baseline_rows'))
// The legacy global reader uses the same controlled six fact arrays here.
const facts=(await captureFacts()).facts
await sql("select set_config('model_target_test.facts_extra',$1,false)v",[JSON.stringify(facts)])
await db.exec(`create or replace function cp7_planning.history_source()returns jsonb language sql volatile as $$
 select jsonb_build_object('status',current_setting('model_target_test.history_state'),'facts',current_setting('model_target_test.facts_extra')::jsonb)$$;
update cp7_planning.history_runs set dependency_hash=encode(sha256(convert_to(current_setting('model_target_test.facts_extra')::jsonb::text,'UTF8')),'hex');`)
const hash='b'.repeat(64),keys=products.map(p=>p.root_id+':'+size),ref={kind:'EXPLICIT_SYNTHETIC',id:'versioned-consumer',revision:'1'}
async function fixture({omitted=false}={}){
 const c=await captureFacts();if(omitted)Object.assign(c,{status:'INCOMPLETE',stock_raw_omitted:true,stock_rows_at_least:50001})
 c.model_target_source=await current(c)
 c.model_target_stock_references=await sql('select cp7_model_target_source_v2.stock_digests($1::jsonb,$2::timestamptz)v',[JSON.stringify(products.filter(p=>c.model_target_source.rows.some(r=>r.runtime==='SCOPED_V3'&&r.target_key===p.root_id+':'+size))),c.captured_at])
 Object.assign(c,{production_policies:{rows:[]},profiles:products.map(p=>({root_id:p.root_id,product_version_id:p.id,size_id:size,sku:p.sku,product_name:p.product_name,reason:'Explicit synthetic fixture',profile_id:p.id,revision:'1',quality:'SELECTED_ASSUMPTION',config:{mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,minimum_available_days:'20',lead_days:'2',review_days:'1',buffer_days:'1'}}))})
 c.product_analog_choices=await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(c)])
 const history=keys.map(target_key=>({target_key,size_id:size,available_days:100,days:Array.from({length:100},(_,i)=>({date:day(i),state:'AVAILABLE',gross_observed_pcs:String(i+1),training_pcs:String(i+1)})),refs:[ref]}))
 return{c,history,stock:products.map(p=>({target_key:p.root_id+':'+size,sku:p.sku,product_name:p.product_name,native_available_pcs:'7'})),q:{from_date:day(0),through_date:day(99),group_mode:'AS_SOLD'}}
}
const context=x=>sql('select cp7_product_analog_consumer.prepare($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(x.c),JSON.stringify(x.history),JSON.stringify(x.q)])
const rows=async(x,subset=x.history,baseline=false)=>sql('select '+(baseline?'cp7_product_analog_consumer.baseline_rows':'cp7_model_target_consumer_v2.rows')+'($1::jsonb,$2::jsonb,$3::jsonb,$4,$5::jsonb)v',[JSON.stringify(x.c),JSON.stringify(subset),JSON.stringify(x.stock),hash,JSON.stringify(await context(x))])
const rehash=async s=>{const copy={...s};for(const k of['source_hash','known_as_of','checked_at','private_prototype','caller_replaced','forecast_applied','production_go'])delete copy[k];s.source_hash=await sql("select encode(sha256(convert_to($1::jsonb::text,'UTF8')),'hex')v",[JSON.stringify(copy)])}
const wire={contract:'cp7.model-target-versioned-consumer-synthetic-wire.v1',explicit_synthetic_history_policy:true,actual_Native:false,rows:{},production_go:false}
await test('SCOPED_V3_TO_ONE_TARGET_KERNEL_EXACT_FORECAST_AND_HISTORY',async()=>{
 const s=await seedScoped({eligible:true}),before=await sql('select to_jsonb(r)v from cp7_model_scoped_evaluation.runs r where id=$1',[s.id]),x=await fixture(),old=(await rows(x,x.history,true))[0],out=(await rows(x))[0]
 assert.equal(out.target.target_pcs,'400');assert.equal(out.target.reorder_point_pcs,'300');assert.equal(old.target.target_pcs,'202');assert.equal(old.target.reorder_point_pcs,'152')
 assert.equal(out.model_resolution.contract_version,'cp7.model-target-resolution.v2');assert.equal(out.demand_provenance.contract_version,'cp7.target-demand-provenance.v3');assert.equal(out.model_resolution.runtime,'SCOPED_V3');assert.equal(out.model_resolution.read_method,'erp_cp7_read_model_evaluation_v3');assert.equal(out.model_resolution.history_scope,'SINGLE_CURRENT_PHYSICAL_ROOT')
 assert.deepEqual(out.demand_estimate,old.demand_estimate);assert.equal(out.demand_provenance.own_total_pcs,'5050');assert.equal(out.target.inputs.daily_total_pcs,'5050');assert.deepEqual(out.model_resolution.baseline_target,old.target)
 assert.deepEqual(await sql('select to_jsonb(r)v from cp7_model_scoped_evaluation.runs r where id=$1',[s.id]),before);wire.rows.projected=out
 return{model400_ROP300_baseline202_ROP152:true,observed_totals_unchanged:true,existing_projection_kernel:true,explicit_scoped_namespace:true,synthetic_positive_only:true}
})
await test('NEWER_GLOBAL_V2_ELIGIBLE_PRESERVES_GLOBAL_NAMESPACE',async()=>{
 await seedScoped({eligible:true});const m=await f.capture(),x=await fixture(),out=(await rows(x))[0]
 assert.equal(out.model_resolution.run_id,m.run_id);assert.equal(out.model_resolution.runtime,'GLOBAL_V2');assert.equal(out.model_resolution.read_method,'erp_cp7_read_model_evaluation_v2');assert.equal(out.model_resolution.history_scope,'GLOBAL_CURRENT_PHYSICAL_ROOTS');assert.equal(out.target.target_pcs,'400');wire.rows.global=out
 return{latest_v2_consumed_without_scoped_alias:true}
})
await test('MANUAL_AND_OWN_HISTORY_MINIMUM_KEEP_PRIORITY',async()=>{
 await seedScoped({eligible:true});const x=await fixture();Object.assign(x.c.profiles[0].config,{mean_mode:'SELECTED_MANUAL',daily_pcs:'3'})
 let out=(await rows(x))[0];assert.equal(out.target.target_pcs,'12');assert.equal(out.model_resolution.reason,'EXPLICIT_MANUAL_DEMAND_RETAINS_PRIORITY');assert.deepEqual(out.target,(await rows(x,x.history,true))[0].target);wire.rows.manual=out
 Object.assign(x.c.profiles[0].config,{mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,minimum_available_days:'101'});out=(await rows(x))[0]
 assert.equal(out.target.target_pcs,null);assert.equal(out.model_resolution.forecast_applied,false);assert.equal(out.model_resolution.reason,'OWN_HISTORY_MINIMUM_REQUIRED_BEFORE_MODEL');wire.rows.unknown=out
 return{manual12_not_overridden:true,insufficient_history_UNKNOWN_not_zero:true}
})
await test('QUERY_AND_COMPLETE_FORECAST_WINDOW_REQUIRED',async()=>{
 await seedScoped({eligible:true});const x=await fixture();x.q.group_mode='RESTATED';let out=(await rows(x))[0]
 assert.equal(out.model_resolution.reason,'MODEL_HISTORY_QUERY_DIFFERS_FROM_TARGET');assert.deepEqual(out.target,(await rows(x,x.history,true))[0].target)
 x.q.group_mode='AS_SOLD';Object.assign(x.c.profiles[0].config,{lead_days:'7',review_days:'1',buffer_days:'0'});out=(await rows(x))[0]
 assert.equal(out.model_resolution.reason,'FULL_DATED_TARGET_AND_REORDER_VECTOR_REQUIRED');assert.deepEqual(out.target,(await rows(x,x.history,true))[0].target)
 return{no_period_alias_or_vector_extrapolation:true}
})
await test('STATISTICAL_SAFETY_IS_THE_EXISTING_EXPLICIT_ASSUMPTION',async()=>{
 await seedScoped({eligible:true});const x=await fixture();Object.assign(x.c.profiles[0].config,{buffer_mode:'STATISTICAL',buffer_days:null,service_level:'0.95'})
 const out=(await rows(x))[0],old=(await rows(x,x.history,true))[0];assert.equal(out.target.lead_safety_pcs,old.target.lead_safety_pcs);assert.equal(out.target.horizon_safety_pcs,old.target.horizon_safety_pcs);assert.equal(out.target.calibrated_forecast_interval,false)
 return{one_buffer_same_observed_SD_and_service:true,no_forecast_calibration_invented:true}
})
await test('SCOPED_BINDING_MAY_USE_OMITTED_GLOBAL_STOCK_WITH_FULL_TARGET_DIGEST',async()=>{
 await seedScoped({eligible:true});const x=await fixture({omitted:true}),out=(await rows(x))[0]
 assert.equal(x.c.status,'INCOMPLETE');assert.equal(x.c.stock_raw_omitted,true);assert.equal(out.target.target_pcs,'400');assert.equal(out.model_resolution.state,'MODEL_PROJECTED')
 return{controlled_global_raw_omission_preserved:true,target_full_digest_independently_checked:true,actual_dense_Native_claim:false}
})
await test('CHANGED_CAPTURE_FACTS_CANNOT_BORROW_ELIGIBLE_SCOPED_SOURCE',async()=>{
 await seedScoped({eligible:true});const x=await fixture();x.c.facts.products[0].product_name='changed after bound source';await rejects(()=>rows(x),/PHYSICAL_SOURCE_MISMATCH/)
 return{same_capture_clock_not_enough_without_exact_physical_inputs:true}
})
await test('SOURCE_VECTOR_DIGEST_AND_REHASHED_RUNTIME_METHOD_REFUSED',async()=>{
 await seedScoped({eligible:true});let x=await fixture();x.c.model_target_source.rows.find(r=>r.target_key===key).forecast.forecasts[0]='999';await rejects(()=>rows(x),/SOURCE_DIGEST/)
 x=await fixture();const s=x.c.model_target_source;s.rows.find(r=>r.target_key===key).read_method='erp_cp7_read_model_evaluation_v2';s.selection.find(r=>r.target_key===key).read_method='erp_cp7_read_model_evaluation_v2';await rehash(s);await rejects(()=>rows(x),/RUNTIME_BINDING/)
 return{source_digest_and_namespace_independently_bound:true}
})
await test('CURRENT_POLICY_WITHDRAWAL_AND_NO_MODEL_RETAIN_BASELINE',async()=>{
 const s=await seedScoped({eligible:true});await f.seed({revision:'2',state:'SUSPENDED',at:await now()});const x=await fixture(),out=await rows(x),old=await rows(x,x.history,true)
 assert.equal(out[0].model_resolution.reason,'ACTIVATION_POLICY_CHANGED');assert.deepEqual(out[0].target,old[0].target);assert.equal(out[1].model_resolution.run_id,null);assert.equal(out[1].model_resolution.runtime,null);assert.equal(out[1].model_resolution.reason,'NO_OWN_MODEL_EVALUATION');assert.deepEqual(out[1].target,old[1].target)
 return{current_policy_not_capture_policy:true,missing_model_explicit_null:true}
})
await test('PAGED_TARGET_CHUNK_EQUALS_WHOLE_SOURCE_AND_PRIVATE_VOLATILITY',async()=>{
 await seedScoped({eligible:true});const x=await fixture(),all=await rows(x);assert.deepEqual(await rows(x,[x.history[0]]),[all[0]]);assert.deepEqual(await rows(x,[x.history[1]]),[all[1]])
 assert.equal(await sql("select provolatile v from pg_proc where oid='cp7_model_target_consumer_v2.rows(jsonb,jsonb,jsonb,text,jsonb)'::regprocedure"),'i')
 for(const role of['anon','authenticated','service_role'])assert.equal(await sql("select has_function_privilege($1,'cp7_model_target_consumer_v2.rows(jsonb,jsonb,jsonb,text,jsonb)','EXECUTE')v",[role]),false)
 return{chunk_parity:true,immutable_captured_stock_binding:true,public_entry_added:false}
})
await modelTargetHooksV2Cases(f,{block,fixture,rows,context,wire,products,keys,hash,ref,root,size})
const report={contract:'cp7.model-target-consumer-v2-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',expected:26,counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,consumer_sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_target_consumer_v2/consumer.sql')).digest('hex'),actual_SQL:true,selected_generated_hooks_SQL:true,synthetic_historical_rows_and_policy:true,actual_Native:false,actual_Auth_HTTP_credit:false,complete_stage_installer_qualified:false,target_caller_integrated:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-target-consumer-v2-local.json',JSON.stringify(report,null,2)+'\n');await writeFile('docs/cp7/d17-14/ow11/model-target-consumer-v2-local-wire.json',JSON.stringify(wire,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
