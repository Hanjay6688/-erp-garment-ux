// Actual proposed source/getter/fingerprint/target hooks with controlled sources.
// This is not Native, Auth, catalog22 or public-wire qualification.
import {readFile,writeFile,access} from 'node:fs/promises'
import {createHash,randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),sources=new Map(),read=async path=>{const s=await readFile(path,'utf8');sources.set(path,createHash('sha256').update(s).digest('hex'));return s}
const block=(s,n)=>{const a=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(a?.length,1,n);return a[0]}
const sql=async(q,args=[])=>(await db.query(q,args)).rows[0]?.v
await db.exec(`create role cp7_capture;create role anon;create role authenticated;create role service_role;
 create schema extensions;create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)$$;
 create schema cp7_planning;create schema cp7_profile;create schema cp7_identity;create schema cp7_baseline_native;create schema cp7_analysis_stage;
 create schema cp7_supply_native;create schema cp7_schedule_native;create schema cp7_netting_native;create schema cp7_analysis_native;create schema cp7_bounded_analysis_stage;create schema cp7_reorder_inputs;
 create schema cp7_product_analog_choice;create table cp7_product_analog_choice.choices(id uuid,target_key text,revision bigint,action text,evidence jsonb,reason text,actor uuid,request_id uuid,recorded_at timestamptz);
 create table public.local_fixture(c jsonb,h jsonb);
 create function cp7_planning.history_source_within(integer)returns jsonb language sql stable as $$select c from public.local_fixture$$;
 create function cp7_reorder_inputs.capture_history(integer)returns jsonb language sql stable as $$select c from public.local_fixture$$;
 create function cp7_profile.source(uuid[],timestamptz)returns jsonb language sql stable as $$select c->'profiles'from public.local_fixture$$;
 create function cp7_identity.workspace_data(uuid[],timestamptz)returns jsonb language sql stable as $$select c->'production_policies'from public.local_fixture$$;
 create function cp7_planning.history_build(jsonb,jsonb)returns jsonb language sql stable as $$select h from public.local_fixture$$;`)
for(const p of ['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7-src/demand/estimate.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql'])await db.exec(await read(p))
await db.exec(block(await read('scripts/cp7_product_analog_choice_stage/choice.sql'),'cp7_product_analog_choice.source_at'))
for(const p of ['scripts/cp7_product_analog_consumer/kernel.sql','scripts/cp7_product_analog_consumer/baseline.sql','scripts/cp7_product_analog_consumer_stage/confirmation.sql'])await db.exec(await read(p))
const hooks=await read('scripts/cp7_product_analog_consumer_stage/hooks.sql')
for(const n of ['cp7_baseline_native.source_within','cp7_reorder_inputs.capture_baseline','cp7_baseline_native.build','cp7_analysis_stage.baseline_rows','cp7_bounded_analysis_stage.native_work_fingerprint'])await db.exec(block(hooks,n))
await db.exec(block(await read('scripts/cp7_bounded_analysis_stage/source.sql'),'cp7_bounded_analysis_stage.work_fingerprint'))
await db.exec(block(hooks,'cp7_supply_native.fingerprint'))
for(const [p,n]of [['scripts/cp7-src/planning/schedule-scenario.sql','cp7_schedule_native.fingerprint'],['scripts/cp7_production_stage/sql/cp7_netting_native__fingerprint.sql','cp7_netting_native.fingerprint'],['scripts/cp7-src/planning/analysis.sql','cp7_analysis_native.fingerprint']])await db.exec(block(await read(p),n))
const root='11111111-1111-4111-8111-111111111111',source='22222222-2222-4222-8222-222222222222',size='33333333-3333-4333-8333-333333333333',profileId='44444444-4444-4444-8444-444444444444',actor='55555555-5555-4555-8555-555555555555',key=root+':'+size,sourceKey=source+':'+size
const at='2026-01-20T12:00:00.123456Z',query={from_date:'2026-01-01',through_date:'2026-01-03',group_mode:'AS_SOLD'},ref={kind:'CONTROLLED_HISTORY',id:source,revision:'1'}
const products=[{id:root,root_id:root,size_id:size,sku:'TARGET',product_name:'Target',commercial:[]},{id:source,root_id:source,size_id:size,sku:'SOURCE',product_name:'Source',commercial:[]}]
const profile={root_id:root,product_version_id:root,profile_id:profileId,revision:'1',quality:'SELECTED_ASSUMPTION',config:{minimum_available_days:'1',mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,lead_days:'3',review_days:'0',buffer_days:'0'}}
const c={captured_at:at,profiles:[profile],production_policies:{rows:[]},facts:{products,stock:[]},production_sources:{scope:'CONTROLLED',facts:{}}}
const days=Array.from({length:3},(_,i)=>({date:'2026-01-0'+(i+1),state:'AVAILABLE',gross_observed_pcs:i?'0':'1',training_pcs:i?'0':'1'}))
const history=[{target_key:key,size_id:size,available_days:0,days:days.map(d=>({...d,state:'UNKNOWN',training_pcs:null})),refs:[ref]},{target_key:sourceKey,size_id:size,available_days:3,days,refs:[ref]}]
const h={history:{rows:history},current_stock:products.map(p=>({target_key:p.root_id+':'+p.size_id,sku:p.sku,product_name:p.product_name,native_available_pcs:'0'}))}
await sql('insert into public.local_fixture values($1::jsonb,$2::jsonb)',[JSON.stringify(c),JSON.stringify(h)])
const capture=()=>sql('select cp7_baseline_native.source_within(5000)v'),reorder=()=>sql('select cp7_reorder_inputs.capture_baseline(5000)v')
const fingerprint=x=>sql('select cp7_analysis_native.fingerprint($1::jsonb)v',[JSON.stringify(x)])
const normalize=(b,a,r)=>sql('select cp7_product_analog_consumer.normalize_confirmed_delta($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(b),JSON.stringify(a),JSON.stringify(r)])
const evidence={contract_version:'cp7.product-analog-material.v1',target_key:key,source_key:sourceKey,reviewed:true,profile_id:profileId,profile_revision:'1',minimum_available_days:'1',target_product:products[0],source_product:products[1],scale_factor:'1'}
const before=await capture();let receipt,after
const cases=[];const test=async(id,fn)=>{try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,1800)})}}
await test('GETTERS_SAME_CAPTURE_CHOICES_AND_ENGINE',async()=>{
 assert.deepEqual(await reorder(),before);assert.equal(before.product_analog_choices.length,2);assert.equal(before.product_analog_choices[0].state,'UNREVIEWED');assert.match(before.analog_consumer_engine,/^[a-f0-9]{64}$/);return{baseline_reorder_same_capture:true}
})
await test('EXACT_OWN_DELTA_NORMALIZES_FULL_FINGERPRINT',async()=>{
 await sql('insert into cp7_product_analog_choice.choices values($1,$2,1,\'CONFIRM\',$3,\'Controlled review\',$4,$5,\'2026-01-19T10:00:00.123456Z\')',[randomUUID(),key,JSON.stringify(evidence),actor,randomUUID()])
 after=await capture();receipt={contract_version:'cp7.product-analog-choice-outcome.v1',...after.product_analog_choices.find(x=>x.target_key===key),forecast_applied:false,production_go:false}
 assert.notEqual(await fingerprint(after),await fingerprint(before));assert.deepEqual(await normalize(before,after,receipt),before);assert.equal(await fingerprint(await normalize(before,after,receipt)),await fingerprint(before));return{own_only_change_allowed:true,unmodified_choice_fingerprint_changes:true}
})
await test('SECOND_CHECK_STILL_SEES_ALL_OTHER_SOURCE_FIELDS',async()=>{
 let n=0;for(const mutate of [a=>a.facts.stock.push({qty:'1'}),a=>a.profiles[0].revision='2',a=>a.production_sources.facts={changed:true},a=>a.analog_consumer_engine='f'.repeat(64)]){
  const a=structuredClone(after);mutate(a);assert.notEqual(await fingerprint(await normalize(before,a,receipt)),await fingerprint(before));n++
 }return{other_source_changes_still_detected:n}
})
await test('SIBLING_CHOICE_AND_WRONG_RECEIPT_REFUSED',async()=>{
 let n=0;for(const mutate of [a=>a.product_analog_choices[1].reason='tampered',a=>a.product_analog_choices[0].reason='other write',a=>a.product_analog_choices[0].actor_scope_id=source,a=>a.product_analog_choices[0].request_id=source,a=>a.product_analog_choices[0].recorded_at='2026-01-19T10:00:00.123457+00:00',a=>a.product_analog_choices.push(a.product_analog_choices[1]),a=>a.product_analog_choices.reverse()]){
  const a=structuredClone(after);mutate(a);await assert.rejects(()=>normalize(before,a,receipt),/UNEXPECTED_CHOICE_DELTA/);n++
 }
 await assert.rejects(()=>normalize(before,after,{...receipt,revision:'2'}),/OWN_DELTA_REVISION/);return{unexpected_deltas_refused:n,revision_jump_refused:true}
})
await test('BOUNDED_FINGERPRINT_RETAINS_EXACT_CHOICE_DELTA',async()=>{
 const extra={bounded_request_contract:'cp7.bounded-analysis-request.v1',bounded_reference_contract:'cp7.bounded-analysis-reference.v1',bounded_producer_hash:'a'.repeat(64),bounded_stock_reference:{contract_version:'cp7.native-stock-row-digest.v1',scope:'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS',captured_at:at,rows_sha256:'b'.repeat(64),row_count:'202000',raw_rows_truncated:false,raw_native_capture_status_overridden:false}}
 const b={...before,...extra},a={...after,...extra};assert.notEqual(await fingerprint(a),await fingerprint(b));assert.equal(await fingerprint(await normalize(b,a,receipt)),await fingerprint(b))
 a.bounded_stock_reference={...extra.bounded_stock_reference,rows_sha256:'c'.repeat(64)};assert.notEqual(await fingerprint(await normalize(b,a,receipt)),await fingerprint(b));return{actual_existing_bounded_work_fingerprint:true,stock_digest_still_checked:true}
})
await test('DIRECT_AND_STAGED_HOOKS_USE_ONE_ADAPTER',async()=>{
 const direct=await sql('select cp7_baseline_native.build($1::jsonb,$2::jsonb)v',[JSON.stringify(after),JSON.stringify(query)])
 const context=await sql('select cp7_product_analog_consumer.prepare($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(after),JSON.stringify(history),JSON.stringify(query)])
 const staged=await sql('select cp7_analysis_stage.baseline_rows($1::jsonb,$2::jsonb,$3::jsonb,$4)v',[JSON.stringify({...after,analog_consumer_context:context}),JSON.stringify([history[0]]),JSON.stringify(h.current_stock),direct.source_hash])
 assert.deepEqual(staged,[direct.rows[0]]);assert.equal(staged[0].target.target_pcs,'1');assert.equal(staged[0].target.inputs.counted_days,'3');assert.equal(staged[0].target.inputs.daily_total_pcs,'1');return{direct_and_target_chunk_same_full_JSON:true,exact_repeating_fraction:true}
})
await test('ENGINE_SIGNATURE_BINDS_PRIVATE_IMPLEMENTATION',async()=>{
 const old=await sql('select cp7_product_analog_consumer.engine_hash()v');await db.exec("create function cp7_product_analog_consumer.local_test_marker()returns text language sql immutable as $$select 'LOCAL_TEST_ONLY'$$")
 assert.notEqual(await sql('select cp7_product_analog_consumer.engine_hash()v'),old);await db.exec('drop function cp7_product_analog_consumer.local_test_marker()');assert.equal(await sql('select cp7_product_analog_consumer.engine_hash()v'),old);return{function_change_changes_signature:true,drop_restores_signature:true}
})
await test('DIRECT_ORDER_PRESERVES_QUALIFIED_TARGET_SORT',async()=>{
 const reversed={...h,history:{rows:[...history].reverse()}};await sql('update public.local_fixture set h=$1::jsonb',[JSON.stringify(reversed)])
 const result=await sql('select cp7_baseline_native.build($1::jsonb,$2::jsonb)v',[JSON.stringify(after),JSON.stringify(query)]);assert.deepEqual(result.rows.map(r=>r.target_key),[key,sourceKey])
 await sql('update public.local_fixture set h=$1::jsonb',[JSON.stringify(h)]);return{old_sort_preserved:true}
})
// Controlled history producers isolate the real two-pass orchestration. The
// historical algebra itself was qualified in predecessor suites, not here.
await db.exec(`create schema cp7_history_bounded;
 create function cp7_analysis_stage.bounds()returns jsonb language sql immutable as $$select '{"job_targets":5000,"job_history_cells":1000000,"sales_per_events_unit":100,"history_cells_per_unit":1}'::jsonb$$;
 create function cp7_analysis_stage.events_clean(jsonb)returns boolean language sql immutable as $$select false$$;
 create function cp7_analysis_stage.availability_clean(jsonb,jsonb)returns boolean language sql immutable as $$select false$$;
 create function cp7_planning.history_events(jsonb)returns jsonb language sql immutable as $$select '[]'::jsonb$$;
 create function cp7_planning.history_availability(jsonb,jsonb)returns jsonb language sql stable as $$select h->'history'->'rows'from public.local_fixture$$;
 create function cp7_analysis_stage.events_validate(jsonb)returns jsonb language sql immutable as $$select '{"events":[],"by_target":{}}'::jsonb$$;
 create function cp7_analysis_stage.history_validate(v jsonb)returns jsonb language sql immutable as $$select jsonb_build_object('key_order',(select jsonb_agg(i::text order by i)from generate_series(1,jsonb_array_length(v->'targets'))i))$$;
 create function cp7_analysis_stage.history_stock(jsonb,jsonb,text)returns jsonb language sql stable as $$select h->'current_stock'from public.local_fixture$$;
 create function cp7_reorder_inputs.current_stock(jsonb,jsonb,text)returns jsonb language sql stable as $$select h->'current_stock'from public.local_fixture$$;
 create function cp7_analysis_stage.history_rows(v jsonb)returns jsonb language sql immutable as $$select coalesce(jsonb_agg(x order by ord),'[]')from jsonb_array_elements(v->'availability')with ordinality a(x,ord)where(v->'keys')?(x->>'target_key')$$;
 create function cp7_planning.utc(timestamptz)returns text language sql immutable as $$select to_char($1 at time zone'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')$$;`)
for(const n of ['cp7_analysis_stage.history_prep','cp7_reorder_inputs.history','cp7_reorder_inputs.compile','cp7_history_bounded.compile','cp7_reorder_inputs.points'])await db.exec(block(hooks,n))
const q14={from_date:'2026-01-06',through_date:'2026-01-19',group_mode:'AS_SOLD'},c14=structuredClone(after)
c14.status='COMPLETE';c14.contract_version='cp7.native-demand-facts.v1';c14.scope='GLOBAL_CURRENT_PHYSICAL_ROOTS'
Object.assign(c14.facts,{sales:[],sale_journals:[],returns:[],return_journals:[]});c14.profiles[0].config.lead_days='14'
c14.profiles.push({root_id:source,product_version_id:source,profile_id:null,revision:'0',quality:'UNREVIEWED',config:null})
const days14=Array.from({length:14},(_,i)=>({date:'2026-01-'+String(i+6).padStart(2,'0'),state:'AVAILABLE',gross_observed_pcs:i?'0':'1',training_pcs:i?'0':'1'}))
const history14=[{...history[0],days:days14.map(d=>({...d,state:'UNKNOWN',training_pcs:null}))},{...history[1],available_days:14,days:days14}]
await sql('update public.local_fixture set h=$1::jsonb',[JSON.stringify({...h,history:{rows:history14}})])
const defaults={window_days:'14',service_level:'0.95'},summary={contract_version:'cp7.reorder-stock-summary.v1',captured_at:at,query:q14,products:2,raw_rows_read:50001,raw_rows_truncated:false,Native_capture_status_overridden:false,data_hash:'d'.repeat(64),availability:history14}
const large={...c14,status:'INCOMPLETE',stock_raw_omitted:true,stock_rows_at_least:50001}
const sourceEnvelope=native=>({contract_version:'cp7.reorder-native-source.v1',status:native.status,captured_at:at,query:q14,native,defaults,product_bound:5000,stock_summary:native.status==='INCOMPLETE'?summary:null,leads:[],manuals:[],engine_hash:'a'.repeat(64),context_hash:'b'.repeat(64),threshold_hash:'c'.repeat(64),apply_enabled:false,production_go:false})
await test('COMPLETE_HISTORY_TWO_PASS_CROSS_CHUNK',async()=>{
 const r=await sql('select cp7_reorder_inputs.history($1::jsonb,$2::jsonb)v',[JSON.stringify(c14),JSON.stringify(q14)])
 assert.equal(r.targets.length,2);assert.equal(r.targets[0].target.target_pcs,'1');assert.equal(r.targets[0].target.inputs.counted_days,'14');assert.equal(r.targets[0].analog_resolution.analog.source_key,sourceKey);return{one_target_per_chunk:true,source_in_second_chunk:true,target:'1'}
})
await test('BOUNDED_SUMMARY_TWO_PASS_KEEP_RAW_INCOMPLETE',async()=>{
 const r=await sql('select cp7_history_bounded.compile($1::jsonb,$2::jsonb,$3::jsonb,5000)v',[JSON.stringify(large),JSON.stringify(q14),JSON.stringify(summary)])
 assert.equal(r.raw_native_capture_status,'INCOMPLETE');assert.equal(r.coverage,'COMPLETE');assert.equal(r.inputs.targets[0].target.target_pcs,'1');assert.equal(r.raw_native_status_overridden,false);return{controlled_summary_branch:true,source_in_second_chunk:true,raw_status_unchanged:true,Native_credit:false}
})
await test('REORDER_COMPLETE_AND_SUMMARY_SAME_TARGET_PROVENANCE',async()=>{
 for(const native of [c14,large]){
  const r=await sql('select cp7_reorder_inputs.compile($1::jsonb)v',[JSON.stringify(sourceEnvelope(native))]),point=r.points.rows.find(p=>p.target_key===key)
  assert.equal(point.point_pcs,'1');assert.equal(point.formula_point_pcs,'1');assert.equal(point.target.target_pcs,'1');assert.equal(point.demand_basis,'REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION');assert.equal(point.analog_resolution.available_days,'14')
  assert.equal(point.available_total_pcs,'0');assert.equal(point.available_days,'0');assert.equal(point.target.inputs.daily_total_pcs,'1');assert.equal(point.target.inputs.counted_days,'14')
 }return{both_paths_one_target_engine:true,actual_own_sales_remain_zero:true,analog_demand_separate_provenance:true}
})
const report={contract:'cp7.analog-consumer-hooks-local.v1',classification:'ACTUAL_SELECTED_PROPOSED_HOOKS_WITH_CONTROLLED_SOURCE_NOT_NATIVE',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',sources:Object.fromEntries(sources),cases,all18_hooks_runtime_tested:false,Native_qualified:false,Auth_qualified:false,catalog22_qualified:false,frontend_provenance_integrated:false,production_go:false}
const dir='docs/cp7/d17-14/ow11';await writeFile(dir+'/consumer-hooks-local.json',JSON.stringify(report,null,2)+'\n');if(report.status!=='PASS'){try{await access(dir+'/consumer-hooks-local-first-failure.json')}catch{await writeFile(dir+'/consumer-hooks-local-first-failure.json',JSON.stringify(report,null,2)+'\n')}}
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
