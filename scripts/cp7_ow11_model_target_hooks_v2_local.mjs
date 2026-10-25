// Selected generated hooks on controlled Native-shaped upstreams; not Native CI.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {timelineCases} from './cp7_ow11_model_target_timeline_local.mjs'
export async function modelTargetHooksV2Cases(f,{block,fixture,rows,context,wire,products,keys,hash,ref,root,size}){
const {db,read,sql,test,rejects,seed,setting}=f
const ready=async()=>{const s=await f.seedScoped({eligible:true});return{...s.global,run_id:s.id}}
// Exercise selected generated hooks with controlled source/history producers.
// This does not install the complete stage or claim Native/catalog qualification.
execFileSync('python',['-B','-c','import cp7_model_target_consumer_v2_stage as s;s.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
await db.exec(`create schema cp7_profile;create schema cp7_identity;create schema cp7_baseline_native;
 create schema cp7_analysis_stage;create schema cp7_bounded_analysis_stage;
 create table public.model_consumer_source_fixture(c jsonb,h jsonb);
 create table cp7_baseline_native.runs(id uuid,actor uuid,request_id uuid,result jsonb,dependency_hash text);
 create function cp7_planning.history_source_within(integer)returns jsonb language sql stable as $$select c from public.model_consumer_source_fixture$$;
 create or replace function cp7_reorder_inputs.capture_history(integer)returns jsonb language sql stable as $$select coalesce((select c from public.model_consumer_source_fixture),current_setting('model_source_v2_test.capture')::jsonb)$$;
 create function cp7_profile.source(uuid[],timestamptz)returns jsonb language sql stable as $$select c->'profiles'from public.model_consumer_source_fixture$$;
 create function cp7_identity.workspace_data(uuid[],timestamptz)returns jsonb language sql stable as $$select c->'production_policies'from public.model_consumer_source_fixture$$;
 create function cp7_planning.history_build(jsonb,jsonb)returns jsonb language sql stable as $$select h from public.model_consumer_source_fixture$$;`)
await db.exec(block(await read('scripts/cp7_product_analog_consumer_stage/confirmation.sql'),'cp7_product_analog_consumer.engine_hash'))
const hooks=await read('scripts/cp7_model_target_consumer_v2_stage/hooks.sql')
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
 const c=structuredClone(x.c);delete c.model_target_source;delete c.model_target_stock_references
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
 wire.direct=d;assert.equal(d.contract_version,'cp7.native-baseline.v4');return{actual_direct_and_staged_row_hooks:true,one_shared_model_target:true}
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

await timelineCases({...f,ready,read:p=>read(p==='scripts/cp7_model_target_consumer/timeline.sql'?'scripts/cp7_model_target_consumer_v2/timeline.sql':p)},{block,hooks,fixture,rows,modelVersion:'policy-gated-dated-model-target-2'})
}
