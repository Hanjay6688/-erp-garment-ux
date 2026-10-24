// Actual private SQL and existing demand/target kernels with controlled inputs.
// No Native capture, Auth, installer/inverse or full-chain credit.
import {readFile,writeFile,mkdir,access} from 'node:fs/promises'
import {createHash,randomUUID} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
execFileSync('python',['-B','-c','import cp7_product_analog_consumer as c;c.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
const db=new PGlite(),read=p=>readFile(p,'utf8')
const block=(s,name)=>{const start=s.indexOf('create function '+name+'(');assert.ok(start>=0,name);return s.slice(start,s.indexOf('$$;',start)+3)}
await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;')
const sources=['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7-src/demand/estimate.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql']
for(const p of sources)await db.exec(await read(p))
const choiceSql=await read('scripts/cp7_product_analog_choice_stage/choice.sql')
await db.exec(`create schema cp7_product_analog_choice;
 create table cp7_product_analog_choice.choices(id uuid,target_key text,revision bigint,action text,evidence jsonb,reason text,actor uuid,request_id uuid,recorded_at timestamptz);`)
await db.exec(block(choiceSql,'cp7_product_analog_choice.source_at'))
sources.push('scripts/cp7_product_analog_consumer/kernel.sql','scripts/cp7_product_analog_consumer/baseline.sql','scripts/cp7_target_policy_stage/sql/cp7_analysis_stage__baseline_rows.sql')
await db.exec('create schema cp7_analysis_stage')
for(const path of sources.slice(-3))await db.exec(await read(path))
const root='11111111-1111-4111-8111-111111111111',source='22222222-2222-4222-8222-222222222222',size='33333333-3333-4333-8333-333333333333',profileId='44444444-4444-4444-8444-444444444444',actor='55555555-5555-4555-8555-555555555555',key=root+':'+size,sourceKey=source+':'+size
const stamp='2026-01-20T12:00:00.123456Z',recorded='2026-01-19T10:00:00.123456Z',ref={kind:'CONTROLLED_HISTORY',id:source,revision:'1'}
const sql=async(q,args=[])=>(await db.query(q,args)).rows[0]?.v
function fixture(values=['1','0','0'],states=values.map(()=>'AVAILABLE')){
 const query={from_date:'2026-01-01',through_date:'2026-01-'+String(values.length).padStart(2,'0'),group_mode:'AS_SOLD'}
 const products=[{id:root,root_id:root,size_id:size,sku:'TARGET',name:'Controlled target'},{id:source,root_id:source,size_id:size,sku:'SOURCE',name:'Controlled source'}]
 const profile={root_id:root,product_version_id:root,profile_id:profileId,revision:'1',quality:'SELECTED_ASSUMPTION',config:{minimum_available_days:'1',mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,lead_days:'3',review_days:'0',buffer_days:'0'}}
 const evidence={contract_version:'cp7.product-analog-material.v1',target_key:key,source_key:sourceKey,reviewed:true,profile_id:profileId,profile_revision:'1',minimum_available_days:'1',target_product:products[0],source_product:products[1],scale_factor:'1',available_total_pcs:'999',available_days:'1'}
 const c={captured_at:stamp,facts:{products},profiles:[profile],production_policies:{rows:[]},product_analog_choices:[]}
 const days=values.map((n,i)=>({date:'2026-01-'+String(i+1).padStart(2,'0'),state:states[i],gross_observed_pcs:n,training_pcs:states[i]==='AVAILABLE'?n:null}))
 const h=[{target_key:key,size_id:size,available_days:0,days:days.map(d=>({...d,state:'UNKNOWN',training_pcs:null})),refs:[ref]},
  {target_key:sourceKey,size_id:size,available_days:states.filter(s=>s==='AVAILABLE').length,days,refs:[ref]}]
 return{c,h,query,profile,evidence}
}
async function capture(f,action='CONFIRM',at=recorded){
 await db.exec('truncate cp7_product_analog_choice.choices')
 await sql('insert into cp7_product_analog_choice.choices values($1,$2,1,$3,$4,$5,$6,$7,$8)',[randomUUID(),key,action,JSON.stringify(action==='CLEAR'?null:f.evidence),'Explicit controlled fixture choice',actor,randomUUID(),at])
 f.c.product_analog_choices=await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(f.c)]);return f
}
const prepare=async f=>sql('select cp7_product_analog_consumer.prepare($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(f.c),JSON.stringify(f.h),JSON.stringify(f.query)])
const resolve=async f=>sql('select cp7_product_analog_consumer.resolve($1::jsonb,$2,$3::jsonb)v',[JSON.stringify(await prepare(f)),key,JSON.stringify(f.profile)])
const estimate=async(r,own=null,manual=null)=>sql('select cp7_demand.estimate($1::jsonb)v',[JSON.stringify({contract_version:'cp7.demand-estimate-input.v1',snapshot_id:'local',scope_id:'LOCAL_CONTROLLED',target_key:key,size_id:size,minimum_own_available_days:'1',own,analog:r.analog,manual,refs:r.refs.length?r.refs:[ref]})])
const target=async(r,mode='DAYS',days='3')=>sql('select cp7_baseline.target($1::jsonb)v',[JSON.stringify({contract_version:'cp7.target-input.v2',snapshot_id:'local',scope_id:'LOCAL_CONTROLLED',mode,daily_total_pcs:r.scaled_total_pcs,counted_days:r.available_days,daily_sd:mode==='STATISTICAL'?r.scaled_daily_sd:null,lead_days:days,review_days:'0',buffer_days:mode==='DAYS'?'0':null,service_level:mode==='STATISTICAL'?'0.95':null,refs:r.refs.length?r.refs:[ref]})])
const baseline=async(f,rows=f.h,legacy=false)=>{
 const stock=f.c.facts.products.map(p=>({target_key:p.root_id+':'+p.size_id,sku:p.sku,product_name:p.name,native_available_pcs:'0'}))
 const args=[JSON.stringify(f.c),JSON.stringify(rows),JSON.stringify(stock),'b'.repeat(64)]
 if(legacy)return sql('select cp7_analysis_stage.baseline_rows($1::jsonb,$2::jsonb,$3::jsonb,$4)v',args)
 return sql('select cp7_product_analog_consumer.baseline_rows($1::jsonb,$2::jsonb,$3::jsonb,$4,$5::jsonb)v',[...args,JSON.stringify(await prepare(f))])
}
const cases=[];const test=async(id,fn)=>{try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,1800)})}}
await test('CURRENT_QUERY_EXACT_NUMERATOR_AND_FINAL_CEIL',async()=>{
 const f=await capture(fixture());f.h[1].refs.push(ref);const r=await resolve(f),e=await estimate(r),t=await target(r)
 assert.equal(r.state,'READY');assert.equal(r.analog.available_total_pcs,'1');assert.equal(r.available_days,'3');assert.equal(e.daily_pcs,'0.333333333333');assert.equal(t.target_pcs,'1')
 assert.equal(r.refs.length,2);return{current_query_replaces_old_evidence_total999:true,exact_one_third_times_three:'1',refs_deduplicated:true}
})
await test('ZERO_AVAILABLE_IS_ZERO_NOT_UNKNOWN',async()=>{
 const r=await resolve(await capture(fixture(['0'])));assert.equal(r.state,'READY');assert.equal((await target(r)).target_pcs,'0');return{available_zero:true}
})
await test('UNKNOWN_STOCKOUT_EXCLUDED_AND_MINIMUM',async()=>{
 const f=fixture(['3','900','800'],['AVAILABLE','STOCKOUT','UNKNOWN']);f.profile.config.minimum_available_days='2';f.evidence.minimum_available_days='2';await capture(f)
 const r=await resolve(f);assert.equal(r.reason,'ANALOG_CURRENT_HISTORY_INSUFFICIENT');assert.equal((await estimate(r)).status,'UNKNOWN');assert.equal((await target(r)).target_pcs,null)
 f.profile.config.minimum_available_days='1';f.evidence.minimum_available_days='1';await capture(f);const ready=await resolve(f);assert.equal(ready.analog.available_total_pcs,'3');assert.equal(ready.available_days,'1');return{unknown_and_stockout_never_zero_training:true}
})
await test('RECORDED_CLOCK_AND_LATEST_CLEAR',async()=>{
 const f=await capture(fixture(),'CONFIRM','2026-01-21T00:00:00Z');assert.equal((await resolve(f)).reason,'NO_REVIEWED_ANALOG_CHOICE')
 await capture(f);const before=structuredClone(f.c.product_analog_choices)
 await sql('insert into cp7_product_analog_choice.choices values($1,$2,2,\'CLEAR\',\'null\'::jsonb,\'Later clear\',$3,$4,\'2026-01-20T13:00:00Z\')',[randomUUID(),key,actor,randomUUID()])
 assert.deepEqual(await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(f.c)]),before)
 f.c.captured_at='2026-01-20T14:00:00Z';f.c.product_analog_choices=await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(f.c)]);assert.equal((await resolve(f)).reason,'ANALOG_CHOICE_CLEARED');return{recorded_future_excluded:true,latest_clear_visible_after_clock:true}
})
await test('PROFILE_PRODUCT_AND_SOURCE_INVALIDATION',async()=>{
 const base=await capture(fixture());const outcomes=[]
 for(const [change,expected]of[[f=>f.profile.revision='2','ANALOG_PROFILE_CHANGED'],[f=>f.profile.quality='UNREVIEWED','ANALOG_PROFILE_UNREVIEWED'],[f=>f.c.facts.products[1].name='Changed','ANALOG_PRODUCT_IDENTITY_CHANGED'],[f=>f.c.product_analog_choices[0].evidence.reviewed=false,'CP7_ANALOG_CONSUMER_EVIDENCE']]){
  const f=structuredClone(base);change(f);if(expected.startsWith('CP7_'))await assert.rejects(()=>resolve(f),new RegExp(expected));else assert.equal((await resolve(f)).reason,expected);outcomes.push(expected)
 }
 return outcomes
})
await test('ALL_HISTORY_REQUIRED_AND_ORDER_INDEPENDENT',async()=>{
 const f=await capture(fixture()),r=await resolve(f);f.c.facts.products.reverse();f.c.product_analog_choices.reverse();f.h.reverse();assert.deepEqual(await resolve(f),r)
 f.h.pop();await assert.rejects(()=>resolve(f),/ALL_HISTORY_REQUIRED/);return{all_sources_required_even_outside_target_chunk:true,permutation_identical:true}
})
await test('STRICT_HISTORY_DATE_COUNT_AND_PCS',async()=>{
 const base=await capture(fixture());let refused=0
 for(const [change,expected]of[[f=>f.h[1].days[1].date='2026-01-03',/HISTORY_DAYS/],[f=>f.h[1].available_days=2,/HISTORY_COUNT/],[f=>f.h[1].days[0].gross_observed_pcs='1.5',/CP7_WIP_PCS/],[f=>f.h[1].days[0].state='FUTURE',/HISTORY_DAYS/],[f=>f.h.push(f.h[1]),/ALL_HISTORY_REQUIRED/]]){
  const f=structuredClone(base);change(f);await assert.rejects(()=>resolve(f),expected);refused++
 }return{refused}
})
await test('DEMAND_PRIORITY_MANUAL_OWN_ANALOG',async()=>{
 const r=await resolve(await capture(fixture(['3']))),own={available_total_pcs:'7',available_days:'1',capture_complete:true,refs:[ref]},manual={daily_pcs:'9',assumption_id:profileId,selected:true,refs:[ref]}
 assert.equal((await estimate(r,own,manual)).basis,'SELECTED_MANUAL_ASSUMPTION');assert.equal((await estimate(r,own)).basis,'OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE');assert.equal((await estimate(r)).basis,'REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION');return{existing_priority_preserved:true}
})
await test('SCALE_AND_STATISTICAL_SAME_HISTORY_ONE_BUFFER',async()=>{
 const f=fixture(Array.from({length:14},(_,i)=>i%2?'10':'0'));f.evidence.scale_factor='1.25';await capture(f);const r=await resolve(f),t=await target(r,'STATISTICAL','10')
 const oracle=JSON.parse(execFileSync('python',['-c',`from decimal import Decimal,localcontext,ROUND_CEILING
import json
with localcontext()as c:
 c.prec=80;ys=[Decimal(i%2*10)*Decimal('1.25')for i in range(14)];m=sum(ys)/14;sd=(sum((v-m)**2 for v in ys)/13).sqrt();v=m*10+Decimal('1.6449')*sd*Decimal(10).sqrt()
 print(json.dumps({'target':str(v.to_integral_value(rounding=ROUND_CEILING))}))`],{encoding:'utf8'}))
 assert.equal(r.scaled_total_pcs,'87.50');assert.equal(t.target_pcs,oracle.target);assert.equal(t.inputs.buffer_days,null);assert.equal(t.inputs.counted_days,'14');return{independent_80_digit_decimal_target:oracle.target,one_buffer:true}
})
await test('STATISTICAL_INSUFFICIENT_NOT_ZERO_SD',async()=>{
 const r=await resolve(await capture(fixture(['3'])));assert.equal(r.scaled_daily_sd,null);assert.equal((await target(r,'STATISTICAL')).target_pcs,null);return{missing_sd_preserved:true}
})
await test('LARGE_PCS_AND_DECIMAL_SCALE_NO_FLOAT',async()=>{
 const f=fixture(['9007199254740993']);f.evidence.scale_factor='0.5';await capture(f);const r=await resolve(f);assert.equal(r.scaled_total_pcs,'4503599627370496.5');assert.equal((await target(r,'DAYS','1')).target_pcs,'4503599627370497');return{above_js_safe_integer_exact:true}
})
await test('LONG_REVIEW_REASON_PRESERVED_OUTSIDE_KERNEL_KEY',async()=>{
 const f=await capture(fixture());f.c.product_analog_choices.find(c=>c.target_key===key).reason='x'.repeat(1000);const r=await resolve(f);assert.equal(r.review_reason.length,1000);assert.ok(r.analog.reason.length<200);assert.equal((await estimate(r)).status,'SCENARIO');return{no_truncation:true}
})
await test('ADAPTER_NO_CHOICE_LEGACY_FULL_JSON_PARITY',async()=>{
 const f=await capture(fixture(),'CONFIRM','2026-01-21T00:00:00Z');assert.deepEqual(await baseline(f),await baseline(f,f.h,true));return{all_rows_exact_legacy_JSON:true}
})
await test('ADAPTER_CROSS_CHUNK_TARGET_SAME_FULL_CONTEXT',async()=>{
 const f=await capture(fixture());const all=await baseline(f),one=await baseline(f,[f.h[0]])
 assert.deepEqual(one,[all[0]]);assert.equal(one[0].target.target_pcs,'1');assert.equal(one[0].target.inputs.daily_total_pcs,'1');assert.equal(one[0].target.inputs.counted_days,'3')
 assert.equal(one[0].demand_estimate.basis,'REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION');assert.equal(one[0].analog_resolution.review_reason,'Explicit controlled fixture choice')
 return{source_outside_target_chunk_same_target:'1',existing_target_kernel:true}
})
await test('ADAPTER_MANUAL_AND_OWN_FULL_JSON_PARITY',async()=>{
 const f=await capture(fixture());f.profile.config.mean_mode='SELECTED_MANUAL';f.profile.config.daily_pcs='5';assert.deepEqual(await baseline(f),await baseline(f,f.h,true))
 f.profile.config.mean_mode='OWN_AVAILABLE_HISTORY';f.profile.config.daily_pcs=null;f.h[0].available_days=3;f.h[0].days.forEach(d=>{d.state='AVAILABLE';d.gross_observed_pcs='7';d.training_pcs='7'})
 assert.deepEqual(await baseline(f),await baseline(f,f.h,true));assert.equal((await baseline(f))[0].target.target_pcs,'21');return{manual_and_own_full_JSON_equal:true}
})
await test('ADAPTER_STATISTICAL_AND_CLEARED_UNKNOWN',async()=>{
 const f=fixture(Array.from({length:14},(_,i)=>i%2?'10':'0'));f.evidence.scale_factor='1.25';Object.assign(f.profile.config,{lead_days:'10',buffer_days:null,buffer_mode:'STATISTICAL',service_level:'0.95'});await capture(f)
 const a=(await baseline(f))[0];assert.equal(a.target.target_pcs,'97');assert.equal(a.target.inputs.daily_total_pcs,'87.50');assert.equal(a.target.inputs.counted_days,'14');assert.equal(a.target.inputs.buffer_days,null)
 await capture(f,'CLEAR');const clear=(await baseline(f))[0];assert.equal(clear.target.target_pcs,null);assert.equal(clear.analog_resolution.reason,'ANALOG_CHOICE_CLEARED');return{statistical_target97:true,clear_unknown_not_zero:true}
})
await test('SOURCE_REMOVAL_AND_PHYSICAL_SIZE_CHANGE',async()=>{
 const base=await capture(fixture()),removed=structuredClone(base);removed.c.facts.products.pop();removed.h.pop();removed.c.product_analog_choices=removed.c.product_analog_choices.filter(c=>c.target_key===key)
 assert.equal((await resolve(removed)).reason,'ANALOG_SOURCE_UNAVAILABLE')
 const changed=structuredClone(base);changed.c.facts.products[1].size_id=profileId;changed.h[1].size_id=profileId;changed.h[1].target_key=source+':'+profileId;changed.c.product_analog_choices[1].target_key=source+':'+profileId
 assert.equal((await resolve(changed)).reason,'ANALOG_SOURCE_UNAVAILABLE');return{removed_and_new_physical_size_unavailable:true}
})
await test('CAPTURE_CLOCK_MICROSECONDS_AND_INVALID_METADATA',async()=>{
 const base=await capture(fixture());let rejected=0
 for(const [field,value,expected]of[['recorded_at','2026-01-20T12:00:00.123457+00:00',/RECORDED_CHOICE/],['recorded_at','2026-01-19T10:00:00+07:00',/INSTANT_UTC/],['choice_id','not-a-uuid',/uuid/],['reason',' ',/CONSUMER_REASON/]]){
  const f=structuredClone(base);f.c.product_analog_choices[0][field]=value;await assert.rejects(()=>resolve(f),expected);rejected++
 }return{microsecond_future_not_truncated:true,refusals:rejected}
})
await test('REF_BOUND_AND_MISMATCHED_ROW_CONTEXT_FAIL_CLOSED',async()=>{
 const f=await capture(fixture());f.h[1].refs=Array.from({length:1000},(_,i)=>({...ref,id:String(i)}));await assert.rejects(()=>resolve(f),/CP7_WIP_REFS/)
 const ok=await capture(fixture()),bad=structuredClone(ok.h[0]);bad.days[0].gross_observed_pcs='99';await assert.rejects(()=>baseline(ok,[bad]),/ROW_CONTEXT/);return{over1000_refs_not_dropped:true,row_from_other_context_refused:true}
})
await test('CONTROLLED2000_TARGETS_SOURCE_IN_LAST_POSITION',async()=>{
 const f=await capture(fixture()),seed=structuredClone(f.h[0]),empty=structuredClone(f.c.product_analog_choices[1])
 for(let i=0;i<1998;i++){
  const id='60000000-0000-4000-8000-'+String(i).padStart(12,'0'),targetKey=id+':'+size
  f.c.facts.products.splice(f.c.facts.products.length-1,0,{id,root_id:id,size_id:size,sku:'EXTRA-'+i,name:'Controlled extra'})
  f.h.splice(f.h.length-1,0,{...structuredClone(seed),target_key:targetKey});f.c.product_analog_choices.push({...empty,target_key:targetKey})
 }
 assert.equal(f.c.facts.products.length,2000);assert.equal(f.h.at(-1).target_key,sourceKey)
 const r=(await baseline(f,[f.h[0]]))[0];assert.equal(r.target.target_pcs,'1');return{controlled_products:2000,source_position:2000,target_chunk_size:1,Native_scale_credit:false}
})
sources.push('scripts/cp7_product_analog_choice_stage/choice.sql')
const report={contract:'cp7.analog-consumer-local.v1',classification:'LOCAL_ACTUAL_PRIVATE_SQL_AND_EXISTING_KERNELS_WITH_CONTROLLED_HISTORY_NOT_NATIVE',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',sources:Object.fromEntries(await Promise.all(sources.map(async p=>[p,createHash('sha256').update(await read(p)).digest('hex')]))),cases,Native_qualified:false,Auth_qualified:false,installer_inverse_qualified:false,full_A_chain_qualified:false,forecast_activated:false,production_go:false}
const dir='docs/cp7/d17-14/ow11';await mkdir(dir,{recursive:true});await writeFile(dir+'/consumer-local.json',JSON.stringify(report,null,2)+'\n')
if(report.status!=='PASS'){try{await access(dir+'/consumer-local-first-failure.json')}catch{await writeFile(dir+'/consumer-local-first-failure.json',JSON.stringify(report,null,2)+'\n')}}
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
