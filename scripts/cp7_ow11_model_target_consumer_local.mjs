// End-to-end private SQL: immutable v2 -> current source -> existing baseline
// -> dated model target. History/policy/access/source remain controlled fixtures.
import {writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
import {modelTargetSourceFixture} from './cp7_ow11_model_target_source_local_fixture.mjs'
import {timelineCases} from './cp7_ow11_model_target_timeline_local.mjs'
execFileSync('python',['-B','-c','import cp7_model_target_consumer as c;c.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
const root='22222222-2222-4222-8222-222222222222',size='33333333-3333-4333-8333-333333333333',other='44444444-4444-4444-8444-444444444444'
const products=[root,other].map((id,i)=>({id,root_id:id,model_id:id,is_active:true,size_id:size,sku:'CONTROLLED-'+i,product_name:'Synthetic target '+i,commercial:[]}))
const f=await modelTargetSourceFixture({extraFacts:{products,stock:[]}})
const {db,read,sql,key,day,today,cases,seed,test,rejects,ready,capture,current,setting,stored}=f
await db.exec('create role cp7_alert;create schema cp7_product_analog_choice;create table cp7_product_analog_choice.choices(id uuid,target_key text,revision bigint,action text,evidence jsonb,reason text,actor uuid,request_id uuid,recorded_at timestamptz)')
const block=(s,n)=>{const r=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(r?.length,1,n);return r[0]}
await db.exec(block(await read('scripts/cp7_product_analog_choice_stage/choice.sql'),'cp7_product_analog_choice.source_at'))
for(const p of['scripts/cp7-src/demand/estimate.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql','scripts/cp7_product_analog_consumer/kernel.sql','scripts/cp7_product_analog_consumer/baseline.sql','scripts/cp7_product_analog_provenance_stage/provenance.sql','scripts/cp7_model_target_projection/projection.sql','scripts/cp7_model_target_consumer/consumer.sql'])await db.exec(await read(p))
await db.exec(block(await read('scripts/cp7_product_analog_provenance_stage/hooks.sql'),'cp7_product_analog_consumer.baseline_rows'))
const keys=products.map(p=>p.root_id+':'+p.size_id),ref={kind:'EXPLICIT_SYNTHETIC',id:'model-consumer',revision:'1'}
const hash='b'.repeat(64)
const wire={contract:'cp7.model-target-synthetic-sql-fixtures.v1',explicit_synthetic_history_policy:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,rows:{},direct:null}
async function fixture(){
 const s=await current(keys),c={status:'COMPLETE',captured_at:s.known_as_of,facts:{sentinel:'original',products,stock:[]},model_target_source:s,production_policies:{rows:[]},profiles:products.map(p=>({root_id:p.root_id,product_version_id:p.id,size_id:p.size_id,sku:p.sku,product_name:p.product_name,reason:'Explicit synthetic fixture',profile_id:p.id,revision:'1',quality:'SELECTED_ASSUMPTION',config:{mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,minimum_available_days:'20',lead_days:'2',review_days:'1',buffer_days:'1'}}))}
 c.product_analog_choices=await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(c)])
 const history=keys.map(target_key=>({target_key,size_id:size,available_days:100,days:Array.from({length:100},(_,i)=>({date:day(i),state:'AVAILABLE',gross_observed_pcs:String(i+1),training_pcs:String(i+1)})),refs:[ref]}))
 const stock=products.map(p=>({target_key:p.root_id+':'+p.size_id,sku:p.sku,product_name:p.product_name,native_available_pcs:'7'}))
 return{c,history,stock,q:{from_date:day(0),through_date:day(99),group_mode:'AS_SOLD'}}
}
const context=x=>sql('select cp7_product_analog_consumer.prepare($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(x.c),JSON.stringify(x.history),JSON.stringify(x.q)])
async function rows(x,subset=x.history,legacy=false){return sql('select '+(legacy?'cp7_product_analog_consumer.baseline_rows':'cp7_model_target_consumer.rows')+'($1::jsonb,$2::jsonb,$3::jsonb,$4,$5::jsonb)v',[JSON.stringify(x.c),JSON.stringify(subset),JSON.stringify(x.stock),hash,JSON.stringify(await context(x))])}
await test('ACTUAL_V2_CURRENT_SOURCE_TO_ONE_SHARED_TARGET_KERNEL',async()=>{
 const r=await ready(),before=await stored(r.run_id),x=await fixture(),old=(await rows(x,x.history,true))[0],out=(await rows(x))[0]
 assert.equal(out.model_resolution.state,'MODEL_PROJECTED');assert.equal(out.target.target_pcs,'400');assert.equal(out.target.reorder_point_pcs,'300')
 assert.equal(old.target.target_pcs,'202');assert.equal(old.target.reorder_point_pcs,'152');assert.deepEqual(out.model_resolution.baseline_target,old.target)
 wire.rows.projected=out
 assert.deepEqual(out.demand_estimate,old.demand_estimate);assert.equal(out.demand_provenance.own_total_pcs,'5050');assert.equal(out.demand_provenance.own_available_days,'100')
 assert.equal(out.target.inputs.daily_total_pcs,'5050');assert.deepEqual(await stored(r.run_id),before);return{actual_private_pipeline:true,model_target400_ROP300:true,baseline202_ROP152_retained:true,observed_totals_not_rewritten:true}
})
await test('EXPLICIT_MANUAL_RETAINS_PRIORITY_AND_EXACT_TARGET',async()=>{
 await ready();const x=await fixture();Object.assign(x.c.profiles[0].config,{mean_mode:'SELECTED_MANUAL',daily_pcs:'3'})
 const out=(await rows(x))[0],old=(await rows(x,x.history,true))[0];assert.deepEqual(out.target,old.target);assert.equal(out.target.target_pcs,'12');assert.equal(out.model_resolution.reason,'EXPLICIT_MANUAL_DEMAND_RETAINS_PRIORITY');assert.equal(out.model_resolution.forecast_applied,false)
 wire.rows.manual=out
 return{manual_target12_not_overridden:true}
})
await test('PROFILE_MINIMUM_NEVER_BYPASSED_BY_MODEL_ELIGIBILITY',async()=>{
 await ready();const x=await fixture();x.c.profiles[0].config.minimum_available_days='101';const out=(await rows(x))[0]
 assert.equal(out.target.target_pcs,null);assert.equal(out.model_resolution.reason,'OWN_HISTORY_MINIMUM_REQUIRED_BEFORE_MODEL');assert.equal(out.model_resolution.forecast_applied,false)
 wire.rows.unknown=out
 return{UNKNOWN_not_zero:true,profile_minimum_retained:true}
})
await test('BASELINE_ONLY_POLICY_RETURNS_ORIGINAL_KERNEL_UNCHANGED',async()=>{
 await seed({methods:[]});await capture();const x=await fixture(),out=(await rows(x))[0],old=(await rows(x,x.history,true))[0]
 wire.rows.empty=out
 assert.deepEqual(out.target,old.target);assert.equal(out.model_resolution.forecast,null);assert.equal(out.model_resolution.forecast_applied,false);return{no_invented_challenger:true,baseline202:true}
})
await test('EXACT_HISTORY_QUERY_REQUIRED_NOT_ONLY_PHYSICAL_SOURCE',async()=>{
 await ready();const x=await fixture();x.q.group_mode='RESTATED';const out=(await rows(x))[0];assert.equal(out.model_resolution.reason,'MODEL_HISTORY_QUERY_DIFFERS_FROM_TARGET');assert.deepEqual(out.target,(await rows(x,x.history,true))[0].target)
 wire.rows.queryDiffers=out
 return{AS_SOLD_model_never_reused_for_RESTATED_target:true}
})
await test('FULL_TARGET_VECTOR_COVERAGE_REQUIRED',async()=>{
 await ready();const x=await fixture();Object.assign(x.c.profiles[0].config,{lead_days:'7',review_days:'1',buffer_days:'0'});const out=(await rows(x))[0]
 wire.rows.shortVector=out
 assert.equal(out.model_resolution.reason,'FULL_DATED_TARGET_AND_REORDER_VECTOR_REQUIRED');assert.deepEqual(out.target,(await rows(x,x.history,true))[0].target);return{no_vector_extrapolation:true}
})
await test('STATISTICAL_SAFETY_REUSES_EXISTING_EXPLICIT_ASSUMPTION',async()=>{
 await ready();const x=await fixture();Object.assign(x.c.profiles[0].config,{buffer_mode:'STATISTICAL',buffer_days:null,service_level:'0.95'});const out=(await rows(x))[0],old=(await rows(x,x.history,true))[0]
 assert.equal(out.target.lead_safety_pcs,old.target.lead_safety_pcs);assert.equal(out.target.horizon_safety_pcs,old.target.horizon_safety_pcs);assert.equal(out.target.lead_demand_pcs,'200.000000000000');assert.equal(out.target.review_demand_pcs,'100.000000000000');assert.equal(out.target.calibrated_forecast_interval,false)
 wire.rows.statistical=out
 return{same_historical_SD_and_service:true,one_buffer:true,no_calibrated_interval_claim:true}
})
await test('CURRENT_POLICY_WITHDRAWAL_RETIRES_PRIVATE_CONSUMPTION',async()=>{
 const r=await ready(),before=await stored(r.run_id);await seed({revision:'2',state:'SUSPENDED',at:await sql('select cp7_planning.utc(clock_timestamp())v')});const x=await fixture(),out=(await rows(x))[0]
 wire.rows.withdrawn=out;assert.equal(out.model_resolution.reason,'ACTIVATION_POLICY_CHANGED');assert.deepEqual(out.target,(await rows(x,x.history,true))[0].target);assert.deepEqual(await stored(r.run_id),before);return{current_policy_enforced:true,immutable_result_retained:true}
})
await test('MIXED_BASELINE_PHYSICAL_SOURCE_AND_CURRENT_MODEL_REFUSED',async()=>{
 await ready();const x=await fixture();x.c.facts.stock.push({qty:'1'});await rejects(()=>rows(x),/CP7_MODEL_CONSUMER_PHYSICAL_SOURCE_MISMATCH/);return{no_mixed_snapshot:true}
})
await test('SOURCE_DIGEST_AND_CAPTURE_CLOCK_BINDING',async()=>{
 await ready();const x=await fixture(),bad=structuredClone(x);bad.c.model_target_source.rows[0].forecast.forecasts[0]='999';await rejects(()=>rows(bad),/CP7_MODEL_CONSUMER_SOURCE_DIGEST/)
 x.c.captured_at=today+'T00:00:00.000000Z';await rejects(()=>rows(x),/CP7_MODEL_CONSUMER_SOURCE_CLOCK/);return{tampered_vector_and_mixed_clock_refused:true}
})
await test('TARGET_CHUNK_USES_FULL_CURRENT_SOURCE_WITH_EXACT_PARITY',async()=>{
 await ready();const x=await fixture(),all=await rows(x);assert.deepEqual(await rows(x,[x.history[0]]),[all[0]]);assert.deepEqual(await rows(x,[x.history[1]]),[all[1]])
 assert.equal(all[1].model_resolution.reason,'NO_OWN_MODEL_EVALUATION');assert.equal(all[1].model_resolution.forecast_applied,false);assert.deepEqual(all[1].target,(await rows(x,x.history,true))[1].target)
 return{one_target_chunk_same_as_all:true,other_target_no_model_not_invented:true}
})
await test('INCOMPLETE_LIVE_HISTORY_RETAINS_BASELINE',async()=>{
 await ready();await setting('history_state','INCOMPLETE');const x=await fixture(),out=(await rows(x))[0];assert.equal(out.model_resolution.reason,'NATIVE_HISTORY_SOURCE_CHANGED');assert.deepEqual(out.target,(await rows(x,x.history,true))[0].target)
 return{Native1000_scope_limit_not_bypassed:true}
})
await test('PRIVATE_CONSUMER_ENGINE_BOUND_WITHOUT_NEW_PUBLIC_ENTRY',async()=>{
 await ready();const before=await current(keys);await db.exec('create function cp7_model_target_consumer.engine_marker()returns integer language sql as $$select 1$$');const after=await current(keys)
 assert.equal(before.engine_hash,after.engine_hash);assert.notEqual(before.consumer_engine_hash,after.consumer_engine_hash);assert.notEqual(before.source_hash,after.source_hash)
 for(const role of['anon','authenticated','service_role'])assert.equal(await sql("select has_function_privilege($1,'cp7_model_target_consumer.rows(jsonb,jsonb,jsonb,text,jsonb)','EXECUTE')v",[role]),false)
 return{consumer_version_bound_separately:true,public_caller_integrated:false}
})
// Exercise selected generated hooks with controlled source/history producers.
// This does not install the complete stage or claim Native/catalog qualification.
execFileSync('python',['-B','-c','import cp7_model_target_consumer_stage as s;s.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
await db.exec(`create schema cp7_profile;create schema cp7_identity;create schema cp7_baseline_native;
 create schema cp7_analysis_stage;create schema cp7_reorder_inputs;create schema cp7_bounded_analysis_stage;
 create table public.model_consumer_source_fixture(c jsonb,h jsonb);
 create table cp7_baseline_native.runs(id uuid,actor uuid,request_id uuid,result jsonb,dependency_hash text);
 create function cp7_planning.history_source_within(integer)returns jsonb language sql stable as $$select c from public.model_consumer_source_fixture$$;
 create function cp7_reorder_inputs.capture_history(integer)returns jsonb language sql stable as $$select c from public.model_consumer_source_fixture$$;
 create function cp7_profile.source(uuid[],timestamptz)returns jsonb language sql stable as $$select c->'profiles'from public.model_consumer_source_fixture$$;
 create function cp7_identity.workspace_data(uuid[],timestamptz)returns jsonb language sql stable as $$select c->'production_policies'from public.model_consumer_source_fixture$$;
 create function cp7_planning.history_build(jsonb,jsonb)returns jsonb language sql stable as $$select h from public.model_consumer_source_fixture$$;`)
await db.exec(block(await read('scripts/cp7_product_analog_consumer_stage/confirmation.sql'),'cp7_product_analog_consumer.engine_hash'))
const hooks=await read('scripts/cp7_model_target_consumer_stage/hooks.sql')
for(const name of['cp7_baseline_native.source_within','cp7_reorder_inputs.capture_baseline','cp7_baseline_native.build','cp7_baseline_native.serve','cp7_analysis_stage.baseline_rows','cp7_bounded_analysis_stage.native_work_fingerprint'])await db.exec(block(hooks,name))
await db.exec('create function cp7_baseline_native.source()returns jsonb language sql volatile as $$select cp7_baseline_native.source_within(1000)$$')
await db.exec(block(hooks,'cp7_reorder_inputs.points'))
await db.exec('create schema cp7_reorder_caller')
await db.exec(block(hooks,'cp7_reorder_caller.evaluate'))
await db.exec(block(await read('scripts/cp7-src/stock-formula/formula.sql'),'cp7_stock_formula.z'))
async function wireReorder(input,points){
 const snapshot={contract_version:'cp7.reorder-reader-snapshot.v1',captured_at:input.captured_at,query:input.query,points,products,threshold_source_hash:input.source_hash,input_path:'EXPLICIT_CONTROLLED_SQL_FIXTURE',history_statistics:Object.fromEntries(keys.map(k=>[k,{sale_days:100}])),defaults:{service_level:'0.95',window_days:'100'},leads:[],manuals:[],current_stock:input.current_stock.map((x,i)=>({...x,root_id:products[i].root_id,size_id:size})),threshold_hash:input.source_hash,threshold_captured_at:input.captured_at,context_hash:input.source_hash,engine_hash:'c'.repeat(32),native_capture_status:'COMPLETE',cache_hit:false,live_ROP_caller_changed:false,apply_enabled:false,production_go:false}
 const supply={contract_version:'cp7.reorder-supply-cache.v1',checked_at:input.captured_at,query:input.query,status:'UNKNOWN',reason:'GLOBAL_ANALYSIS_NEEDED',job:null,projection:null,apply_enabled:false,production_go:false}
 return sql('select cp7_reorder_caller.evaluate($1::jsonb,$2::jsonb)v',[JSON.stringify(snapshot),JSON.stringify(supply)])
}
async function hookFixture(){
 const x=await fixture();await db.exec('truncate public.model_consumer_source_fixture')
 const c=structuredClone(x.c);delete c.model_target_source
 const scope='GLOBAL_CURRENT_PHYSICAL_ROOTS',historyHash='a'.repeat(64),at=c.captured_at
 const current_stock=x.stock.map((v,i)=>({...v,root_id:products[i].root_id,size_id:size,is_active:true,grade_basis:'NATIVE_SELLABLE_GRADE_A_AND_B',projection_basis:'CURRENT_STOCK_ONLY_NO_FORECAST',refs:[ref],availability:{status:'KNOWN',kernel_version:'availability-1',physical_fg_pcs:'7',reserved_pcs:'0',available_fg_pcs:'7',projected_residual_pcs:'7',inputs:{snapshot_id:historyHash,scope_id:scope,target_key:v.target_key,size_id:size,residual_future_pcs:'0'}}}))
 const history={contract_version:'cp7.demand-result.v1',kernel_version:'demand-1',snapshot_id:historyHash,scope_id:scope,known_as_of:at,effective_as_of:at,...x.q,status:'CAPTURE_COMPLETE',rows:x.history.map(v=>({...v,gross_observed_pcs:'5050',draft_reserved_pcs:'0',unknown_days:0,stockout_days:0,calendar_sales_mean:'50.5',available_sales_mean:'50.5',days:v.days.map(d=>({...d,returned_pcs:'0'}))})),group_events:[],selected_events:[]}
 const historyWire={contract_version:'cp7.native-demand-history.v1',scope,capture_complete:true,captured_at:at,source_hash:historyHash,history,current_stock,availability_knowledge_basis:'CURRENT_CAPTURE_RESTATED_LEDGER',training_known_at:at,model_eligibility:'HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED',versions:{producer:'native-demand-1',history:'demand-1',availability:'availability-1'},production_go:false}
 await db.query('insert into public.model_consumer_source_fixture values($1::jsonb,$2::jsonb)',[JSON.stringify(c),JSON.stringify(historyWire)]);return x
}
const hookSource=()=>sql('select cp7_baseline_native.source_within(5000)v')
const direct=(c,q)=>sql('select cp7_baseline_native.build($1::jsonb,$2::jsonb)v',[JSON.stringify(c),JSON.stringify(q)])
await test('HOOK_BASELINE_REORDER_CAPTURE_SHARE_MODEL_SOURCE_IDENTITY',async()=>{
 await ready();await hookFixture();const a=await hookSource(),b=await sql('select cp7_reorder_inputs.capture_baseline(5000)v')
 assert.equal(a.model_target_source.source_hash,b.model_target_source.source_hash);assert.equal(a.model_target_source.rows[0].state,'ELIGIBLE');assert.deepEqual(a.facts,b.facts)
 return{actual_generated_capture_hooks:true,same_server_owned_model_selection:true}
})
await test('HOOK_DIRECT_AND_STAGED_CHUNK_HAVE_IDENTICAL_MODEL_TARGETS',async()=>{
 await ready();const x=await hookFixture(),c=await hookSource(),d=await direct(c,x.q);x.c=c
 const staged=await sql('select cp7_analysis_stage.baseline_rows($1::jsonb,$2::jsonb,$3::jsonb,$4)v',[JSON.stringify({...c,analog_consumer_context:await context(x)}),JSON.stringify([x.history[0]]),JSON.stringify(x.stock),d.source_hash])
 assert.deepEqual(staged,[d.rows[0]]);assert.equal(staged[0].target.target_pcs,'400');assert.equal(staged[0].target.reorder_point_pcs,'300')
 wire.direct=d;assert.equal(d.contract_version,'cp7.native-baseline.v3');return{actual_direct_and_staged_row_hooks:true,one_shared_model_target:true}
})
await test('HOOK_DIRECT_READER_USES_EXACT_NEW_PRODUCER_IDENTITY',async()=>{
 const r=await ready(),x=await hookFixture(),c=await hookSource(),d=await direct(c,x.q)
 await db.query('insert into cp7_baseline_native.runs values($1,$2,$3,$4::jsonb,$5)',[r.run_id,f.actor,r.request_id,JSON.stringify(d),d.source_hash])
 const a=await sql('select cp7_baseline_native.serve($1::uuid)v',[r.run_id]);assert.equal(a.source_state,'UNCHANGED');assert.deepEqual(a.rows,d.rows)
 await seed({revision:'2',state:'SUSPENDED',at:await sql('select cp7_planning.utc(clock_timestamp())v')})
 const b=await sql('select cp7_baseline_native.serve($1::uuid)v',[r.run_id]);assert.equal(b.source_state,'ARCHIVED_STALE');assert.deepEqual(b.rows,d.rows)
 return{actual_reader_current_then_stale:true,old_model_target400_immutable:true}
})
await test('HOOK_EXISTING_REORDER_POINTS_REUSE_EXACT_KERNEL_AND_MANUAL_TRIGGER',async()=>{
 await ready();const x=await hookFixture(),c=await hookSource(),d=await direct(c,x.q)
 const input={contract_version:'cp7.reorder-native-inputs.v1',captured_at:c.captured_at,query:x.q,source_hash:d.source_hash,history_hash:'a'.repeat(64),target_engine:'EXISTING_NATIVE_STAGED_BASELINE',products,history:x.history,current_stock:x.stock,targets:d.rows,apply_enabled:false,production_go:false}
 const points=manuals=>sql('select cp7_reorder_inputs.points($1::jsonb,$2::jsonb,$3::jsonb,$4::jsonb)v',[JSON.stringify(input),JSON.stringify({service_level:'0.95',window_days:'100'}),'[]',JSON.stringify(manuals)])
 const allPoints=await points([]);wire.reorderProjected=(await wireReorder(input,allPoints)).rows;const a=allPoints.rows[0];assert.deepEqual(a.target,d.rows[0].target);assert.equal(a.point_pcs,'300');assert.equal(a.available_total_pcs,'5050');assert.equal(a.available_days,'100');assert.equal(a.demand_provenance.model.state,'MODEL_PROJECTED')
 const b=(await points([{root_id:root,product_version_id:root,size_id:size,revision:'1',reorder_point_pcs:'15'}])).rows[0]
 assert.equal(b.point_pcs,'15');assert.equal(b.formula_point_pcs,'300');assert.equal(b.point_basis,'MANUAL');assert.equal(b.target.target_pcs,'400')
 return{actual_existing_ROP_kernel_reuse:true,manual_trigger15_formula300_target400:true,own_history_not_forecast_sales:true}
})
await test('HOOK_BASELINE_AND_WORK_IDENTITIES_INCLUDE_CURRENT_MODEL_AUTHORITY',async()=>{
 await ready();const x=await hookFixture(),before=await hookSource(),d1=await direct(before,x.q)
 const work=c=>sql('select cp7_bounded_analysis_stage.native_work_fingerprint($1::jsonb)v',[JSON.stringify(c)])
 const w1=await work(before);await seed({revision:'2',state:'SUSPENDED',at:await sql('select cp7_planning.utc(clock_timestamp())v')})
 const after=await hookSource(),d2=await direct(after,x.q);assert.deepEqual(before.facts,after.facts);assert.notEqual(d1.source_hash,d2.source_hash);assert.notEqual(w1,await work(after))
 assert.equal(d1.rows[0].target.target_pcs,'400');assert.equal(d2.rows[0].target.target_pcs,'202');return{policy_only_change_retires_work_and_baseline:true,original_baseline202_restored_for_new_capture:true}
})
await test('UNREVIEWED_PROFILE_KEEPS_EXISTING_REORDER_DEFAULTS_AND_MATCHING_PROVENANCE',async()=>{
 await ready();const x=await fixture();for(const p of x.c.profiles)Object.assign(p,{quality:'UNREVIEWED',config:null,revision:'0',profile_id:null,reason:null})
 const targets=await rows(x),input={contract_version:'cp7.reorder-native-inputs.v1',captured_at:x.c.captured_at,query:x.q,source_hash:hash,history_hash:'a'.repeat(64),target_engine:'EXISTING_NATIVE_STAGED_BASELINE',products,history:x.history,current_stock:x.stock,targets,apply_enabled:false,production_go:false}
 const leads=products.map(p=>({model_id:p.model_id,lead_days:'2',lot_count:'3',group_count:'3'}))
 const points=await sql('select cp7_reorder_inputs.points($1::jsonb,$2::jsonb,$3::jsonb,$4::jsonb)v',[JSON.stringify(input),JSON.stringify({service_level:'0.95',window_days:'100'}),JSON.stringify(leads),'[]'])
 const a=points.rows[0];assert.equal(a.source_kind,'NATIVE_HISTORY_WITH_EXISTING_DEFAULTS');assert.equal(a.target.status,'SCENARIO');assert.equal(a.demand_provenance.model.state,'BASELINE_RETAINED');assert.equal(a.demand_provenance.model.forecast,null)
 assert.deepEqual(a.demand_provenance.model.baseline_target,a.target);wire.reorderDefaults=a;wire.reorderDefaultsRows=(await wireReorder(input,points)).rows
 return{unreviewed_profile_no_model:true,existing_native_defaults_preserved:true,provenance_matches_actual_reorder_target:true}
})
await test('WAREHOUSE_CAPTURE_HOOK_PRESERVES_BASELINE_WITHOUT_MODEL_READ_ACCESS',async()=>{
 await ready();const x=await hookFixture();await setting('model_access','false')
 const c=await sql('select cp7_reorder_inputs.capture_baseline(5000)v'),d=await direct(c,x.q)
 assert.equal(c.model_target_source.policy_source,null);assert.equal(c.model_target_source.rows[0].run_id,null)
 assert.equal(d.rows[0].target.target_pcs,'202');assert.equal(d.rows[0].model_resolution.reason,'MODEL_CURRENT_ACCESS_REQUIRED');wire.rows.warehouse=d.rows[0]
 await rejects(hookSource,/CONTROLLED_ACCESS_DENIED/)
 await setting('warehouse_access','false');await rejects(()=>sql('select cp7_reorder_inputs.capture_baseline(5000)v'),/CONTROLLED_WAREHOUSE_ACCESS_DENIED/)
 return{actual_generated_reorder_capture_hook:true,baseline202_no_model_leak:true,full_model_and_revoked_warehouse_denied:true}
})
await timelineCases(f,{block,hooks,fixture,rows})
await writeFile('tests/fixtures/nativeModelTargetSql.json',JSON.stringify(wire,null,2)+'\n')
const report={contract:'cp7.model-target-consumer-local.v1',status:cases.every(x=>x.status==='PASS')?'PASS':'FAIL',expected:28,counts:cases.reduce((a,x)=>(a[x.status]=(a[x.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_target_consumer/consumer.sql')).digest('hex'),hooks_sql_sha256:createHash('sha256').update(hooks).digest('hex'),actual_private_SQL_pipeline:true,selected_actual_SQL_hooks:true,explicit_synthetic_history_policy:true,controlled_access_live_source:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,complete_stage_installer_qualified:false,public_client_qualified:false,public_caller_integrated:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-target-consumer-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
