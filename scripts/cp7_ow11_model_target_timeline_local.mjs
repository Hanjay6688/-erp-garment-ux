// Controlled positive vectors exercise arithmetic/selected hooks only.
// No Native historical admission or owner-policy approval is claimed.
import assert from 'node:assert/strict'

export async function timelineCases(f,{block,hooks,fixture,rows}){
 const {db,read,sql,test,ready,rejects}=f
 await db.exec('create schema cp7_netting_native;create schema cp7_analysis_native;create schema cp7_fabric_native')
 await db.exec(await read('scripts/cp7-src/baseline/timeline.sql'))
 await db.exec(await read('scripts/cp7_model_target_consumer/timeline.sql'))
 const original=block(await read('scripts/cp7-src/planning/netting.sql'),'cp7_netting_native.timeline')
 await db.exec(original.replace('cp7_netting_native.timeline(','cp7_netting_native.legacy_timeline('))
 await db.exec(block(hooks,'cp7_netting_native.timeline'))
 const analysis=await read('scripts/cp7-src/planning/analysis.sql')
 for(const name of['cp7_analysis_native.fact','cp7_analysis_native.rounded_suggestion'])await db.exec(block(analysis,name))
 // Unrelated material availability stays UNKNOWN in this controlled report test.
 await db.exec(`create function cp7_analysis_native.material_needs(jsonb,jsonb,jsonb)returns jsonb language sql immutable as $$select null::jsonb$$;
 create function cp7_fabric_native.needs(jsonb,jsonb,jsonb,jsonb)returns jsonb language sql immutable as $$select null::jsonb$$;`)
 await db.exec(block(hooks,'cp7_analysis_stage.analysis_targets'))
 // Full operational report compiler with controlled upstream netting/fabric
 // and fingerprint producers. No Native capture/finance credit from this test.
 await db.exec(`create schema cp7_supply_native;
 create table public.model_timeline_report_fixture(n jsonb);
 create function cp7_netting_native.build(jsonb,jsonb)returns jsonb language sql stable as $$select n from public.model_timeline_report_fixture$$;
 create function cp7_fabric_native.plan(jsonb,jsonb)returns jsonb language sql immutable as $$select '{}'::jsonb$$;
 create function cp7_analysis_native.fingerprint(jsonb)returns text language sql immutable as $$select repeat('b',64)$$;
 create function cp7_supply_native.fingerprint(jsonb)returns text language sql immutable as $$select repeat('c',64)$$;`)
 await db.exec(block(hooks,'cp7_analysis_native.build_operational'))
 await db.exec(block(analysis,'cp7_analysis_native.build').replace('cp7_analysis_native.build(','cp7_analysis_native.legacy_operational('))
 async function sample(){await ready();const x=await fixture();return{x,r:(await rows(x))[0]}}
 async function vector(r,values,config={}){
  r=structuredClone(r);Object.assign(r.profile.config,config)
  const m=r.model_resolution;m.forecast.forecasts=values
  const inputs={...m.baseline_target.inputs,...config}
  const p=await sql('select cp7_model_target_projection.project($1::jsonb,$2::jsonb,$3::date)v',[JSON.stringify(inputs),JSON.stringify({contract_version:'cp7.model-target-vector.v1',forecast_from_date:m.forecast_from_date,forecasts:values}),m.forecast_from_date])
  assert.equal(p.state,'ARITHMETIC_CANDIDATE');m.baseline_target=p.baseline;m.reason=p.reason
  r.target={...p.baseline,...p.projected,reason:p.reason,model_input:m,forecast_applied:true};r.demand_provenance.model=m
  return r
 }
 const line=(x,r,etas=[],edges=[],legacy=false)=>sql('select cp7_netting_native.'+(legacy?'legacy_timeline':'timeline')+'($1::jsonb,$2::jsonb,$3::jsonb,$4::jsonb,$5::jsonb,$6::jsonb)v',[JSON.stringify(x.c),JSON.stringify(r),JSON.stringify(etas),JSON.stringify(edges),'{}',JSON.stringify({snapshot_id:'controlled-model-timeline'})])
 const at=(x,h)=>new Date(Date.parse(x.c.captured_at)+h*3600000).toISOString()
 const demands=t=>t.events.filter(v=>v.event.kind==='DEMAND').map(v=>v.event.qty_pcs)
 const decimal=s=>s.includes('.')?s.replace(/0+$/,'').replace(/\.$/,''):s
 await test('DATED_VECTOR_TIMELINE_FIRST_GAP_DIFFERS_FROM_HISTORICAL_MEAN',async()=>{
  const{x,r}=await sample();r.available_fg_pcs='150';const t=await line(x,r),old=await line(x,r,[],[],true)
  assert.deepEqual(demands(t).map(decimal),['100','100','100']);assert.equal(decimal(t.end_balance_pcs),'-150')
  assert.equal(t.first_known_gap.event_key,'forecast-day-2');assert.equal(old.first_known_gap.event_key,'forecast-day-3')
  assert.equal(r.target.target_pcs,'400');assert.equal(t.buffer_consumed_as_demand,false)
  return{target400_timeline300_one_buffer:true,model_gap_day2_historical_day3:true,observed_mean_unchanged:r.demand_estimate.daily_pcs}
 })
 await test('DATED_VECTOR_LATE_SUPPLY_PRESERVES_PRIOR_GAP',async()=>{
  const{x,r}=await sample();r.available_fg_pcs='150'
  const t=await line(x,r,[{position_key:'late',at:at(x,60)}],[{key:'late',position_key:'late',target_key:r.target_key,projected_good_pcs:'200',refs:r.refs}])
  assert.equal(t.first_known_gap.event_key,'forecast-day-2');assert.equal(decimal(t.end_balance_pcs),'50');assert.equal(decimal(t.unmet_pcs),'50')
  return{positive_final_balance_does_not_erase_day2_gap:true}
 })
 await test('VARIABLE_DATED_VECTOR_PARTIAL_DAY_EXACT_NO_AVERAGING',async()=>{
  const{x,r}=await sample(),v=await vector(r,['5','100','1.25','40'],{lead_days:'2',review_days:'0.5',buffer_days:'1'})
  v.available_fg_pcs='10';const t=await line(x,v)
  assert.deepEqual(demands(t).map(decimal),['5','100','0.625']);assert.equal(decimal(t.end_balance_pcs),'-95.625')
  assert.equal(t.first_known_gap.event_key,'forecast-day-2');assert.equal(v.target.target_pcs,'127')
  return{dated_partial_day_0_625_exact:true,target_buffer_not_consumed:true}
 })
 await test('DATED_VECTOR_SUB_TWELVE_PLACE_PRECISION_RETAINED',async()=>{
  const{x,r}=await sample(),v=await vector(r,['0.000000000000000000000000000001','1'],{lead_days:'0.5',review_days:'0',buffer_days:'0'})
  v.available_fg_pcs='0';const t=await line(x,v)
  assert.equal(decimal(demands(t)[0]),'0.0000000000000000000000000000005');assert.equal(v.target.target_pcs,'1')
  assert.equal(t.first_known_gap.event_key,'forecast-day-1');return{half_day_31_decimal_places_not_rounded_up:true}
 })
 await test('DATED_VECTOR_WIDE_CUMULATIVE_BALANCE_NO_FIXED_NUMERIC_OVERFLOW',async()=>{
  const{x,r}=await sample(),n='999999999999999999999999999999.1',v=await vector(r,[n,n,n,n])
  v.available_fg_pcs='0';const t=await line(x,v)
  assert.equal(decimal(t.end_balance_pcs),'-2999999999999999999999999999997.3');assert.equal(v.target.target_pcs,'3999999999999999999999999999997')
  return{daily30_digits_cumulative31_digits_exact:true}
 })
 await test('DATED_TIMELINE_REFUSES_TARGET_SOURCE_OR_ORIGIN_MISMATCH',async()=>{
  const{x,r}=await sample()
  let v=structuredClone(r);v.target.target_pcs='1';await rejects(()=>line(x,v),/CP7_MODEL_TIMELINE_TARGET_MISMATCH/)
  v=structuredClone(r);v.model_resolution.source_hash='0'.repeat(64);await rejects(()=>line(x,v),/CP7_MODEL_TIMELINE_BINDING/)
  v=structuredClone(r);v.profile.config.review_days='2';await rejects(()=>line(x,v),/CP7_MODEL_TIMELINE_PROFILE/)
  const later=structuredClone(x);later.c.captured_at=at(x,24);await rejects(()=>line(later,r),/CP7_MODEL_TIMELINE_TARGET_MISMATCH/)
  return{exact_target_source_and_business_origin_binding:true}
 })
 await test('LEGACY_TIMELINE_AND_UNKNOWN_SIGNED_GAP_UNCHANGED',async()=>{
  await ready();const x=await fixture();Object.assign(x.c.profiles[0].config,{mean_mode:'SELECTED_MANUAL',daily_pcs:'3'})
  const r=(await rows(x))[0];assert.deepEqual(await line(x,r),await line(x,r,[],[],true))
  r.available_fg_pcs='-1';assert.deepEqual(await line(x,r),await line(x,r,[],[],true));assert.equal((await line(x,r)).status,'UNKNOWN')
  r.available_fg_pcs='7';r.target.status='UNKNOWN';assert.deepEqual(await line(x,r),await line(x,r,[],[],true))
  return{legacy_output_exact_parity:true,UNKNOWN_not_zero:true}
 })
 await test('ACTUAL_ANALYSIS_TARGET_HOOK_LABELS_VECTOR_AND_DATED_TIMELINE',async()=>{
  const{x,r}=await sample();r.production_policy={policy:{state:'ACTIVE'}};r.available_fg_pcs='150';r.timeline=await line(x,r)
  const hist={available_days:100,stockout_days:0,unknown_days:0},stock={availability:{physical_fg_pcs:'150',reserved_pcs:'0'},refs:r.refs}
  const args=[x.c,[r],{[r.target_key.split(':')[0]]:[x.c.facts.products[0]]},{[r.target_key]:[stock]},{[r.target_key]:[hist]},{},{},[],{}]
  const out=await sql('select cp7_analysis_stage.analysis_targets('+args.map((_,i)=>'$'+(i+1)+'::jsonb').join(',')+')v',args.map(v=>JSON.stringify(v)))
  const m=out.targets[0].models[0];assert.equal(m.method_id,'NAIVE');assert.equal(m.mode,'EVALUATED');assert.equal(m.demand_rate.state,'NOT_APPLICABLE');assert.ok(m.selection_reason.includes(r.model_resolution.run_id));assert.deepEqual(m.validation_fold_ids,[])
  assert.deepEqual(out.targets[0].timeline.map(v=>decimal(v.demand.value)),['100','100','100']);assert.ok(out.targets[0].timeline.every(v=>v.timing_policy_id==='dated-model-each24h-from-capture-1'))
  return{actual_report_hook_dated_method_not_historical_fallback:true,no_invented_rate_fold_or_score:true}
 })
 await test('FULL_OPERATIONAL_AND_STAGED_REPORT_MODEL_TIMELINE_PARITY',async()=>{
  const{x,r}=await sample();r.production_policy={policy:{state:'ACTIVE'}};r.available_fg_pcs='150';r.timeline=await line(x,r)
  Object.assign(x.c,{schedule:null,production_sources:{facts:{}},matching_products:[],planning_time_bucket:'CONTROLLED',analysis_engine_signature:'a'.repeat(64),material_source:{},fabric_source:{selected:[]}})
  const hist={target_key:r.target_key,available_days:100,stockout_days:0,unknown_days:0},stock={target_key:r.target_key,availability:{physical_fg_pcs:'150',reserved_pcs:'0'},refs:r.refs}
  const history_run_result={current_stock:[stock],history:{rows:[hist]}}
  const scenario={wip:{status:'COMPLETE',positions:[]},capacity:{status:'UNKNOWN'},etas:[],supply_run_result:{baseline_run_result:{history_run_result}}}
  const n={rows:[r],allocation:{status:'UNKNOWN'},matching:{sources:[]},match_results:[],schedule_run_result:scenario}
  await db.query('insert into public.model_timeline_report_fixture values($1::jsonb)',[JSON.stringify(n)])
  const out=await sql('select cp7_analysis_native.build_operational($1::jsonb,$2::jsonb,$3::uuid,$4::jsonb)v',[JSON.stringify(x.c),JSON.stringify(x.q),f.actor,JSON.stringify({actor:f.actor})])
  const args=[x.c,[r],{[r.target_key.split(':')[0]]:[x.c.facts.products[0]]},{[r.target_key]:[stock]},{[r.target_key]:[hist]},{},{},[],{}]
  const staged=await sql('select cp7_analysis_stage.analysis_targets('+args.map((_,i)=>'$'+(i+1)+'::jsonb').join(',')+')v',args.map(v=>JSON.stringify(v)))
  assert.deepEqual(out.demand_models,staged.targets[0].models);assert.deepEqual(out.timeline,staged.targets[0].timeline)
  assert.deepEqual(out.recommendations,staged.targets[0].recommendations);assert.equal(out.versions.models,'policy-gated-dated-model-target-1')
  assert.equal(out.demand_models[0].method_id,'NAIVE');assert.equal(out.demand_models[0].demand_rate.state,'NOT_APPLICABLE')
  const legacy=await sql('select cp7_analysis_native.legacy_operational($1::jsonb,$2::jsonb,$3::uuid,$4::jsonb)v',[JSON.stringify(x.c),JSON.stringify(x.q),f.actor,JSON.stringify({actor:f.actor})])
  assert.equal(legacy.demand_models[0].mode,'FALLBACK');assert.equal(decimal(legacy.demand_models[0].demand_rate.value),'50.5')
  Object.assign(x.c.profiles[0].config,{mean_mode:'SELECTED_MANUAL',daily_pcs:'3'})
  const manual=(await rows(x))[0];manual.production_policy={policy:{state:'ACTIVE'}};manual.available_fg_pcs='150';manual.timeline=await line(x,manual)
  n.rows=[manual];await db.query('update public.model_timeline_report_fixture set n=$1::jsonb',[JSON.stringify(n)])
  const pair=[]
  for(const name of['build_operational','legacy_operational'])pair.push(await sql('select cp7_analysis_native.'+name+'($1::jsonb,$2::jsonb,$3::uuid,$4::jsonb)v',[JSON.stringify(x.c),JSON.stringify(x.q),f.actor,JSON.stringify({actor:f.actor})]))
  for(const v of pair){delete v.semantic_hash;delete v.versions.models}
  assert.deepEqual(pair[0],pair[1])
  return{actual_full_operational_compiler:true,controlled_netting_fabric_and_fingerprints:true,staged_models_timeline_recommendations_exact:true,legacy_false_mean_reproduced:true,complete_manual_report_unchanged_except_model_engine_version_and_semantic_hash:true,finance_wrapper_unchanged:true}
 })
}
