// Actual existing model SQL plus private admission gate on controlled history.
// No Native captures, owner policy write, activation or factory accuracy claim.
import {readFile,writeFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
execFileSync('python',['-B','-c','import cp7_model_activation_gate as g;g.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
const db=new PGlite(),read=p=>readFile(p,'utf8')
await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create schema cp7_model_native;')
const sources=['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7-src/models/kernels.sql','scripts/cp7-src/models/evaluation.sql']
for(const p of sources)await db.exec(await read(p))
const native=await read('scripts/cp7-src/model-native/evaluation.sql')
await db.exec(native.slice(0,native.indexOf('end $$;')+7))
await db.exec(await read('scripts/cp7_model_activation_gate/gate.sql'))
const call=async(sql,args)=>(await db.query(sql,args.map(x=>JSON.stringify(x)))).rows[0].v
const build=d=>call('select cp7_model_native.build($1::jsonb)v',[d])
const decide=async f=>call('select cp7_model_activation_gate.decide($1::jsonb,$2::jsonb,$3::jsonb,$4::jsonb)v',[f.d,f.r??await build(f.d),f.p,f.c])
const day=i=>new Date(Date.UTC(2026,6,1+i)).toISOString().slice(0,10)
function fixture(){
 const key='11111111-1111-4111-8111-111111111111:22222222-2222-4222-8222-222222222222',size=key.split(':')[1]
 const promotion={minimum_complete_folds:'3',minimum_mae_improvement:'0',maximum_bias_worsening:'0',maximum_tail_worsening:'0',season_lag:'7'}
 const ref={kind:'EXPLICIT_SYNTHETIC_MODEL_TEST',id:'model-gate-controlled',revision:'1'}
 const d={history_run_id:'33333333-3333-4333-8333-333333333333',target_key:key,size_id:size,from_date:day(0),through_date:day(99),known_as_of:day(100)+'T12:00:00.123456Z',
  query:{history_run_id:'33333333-3333-4333-8333-333333333333',target_key:key,horizon_days:'7'},
  registry_id:'explicit-test-policy-1',registered_at:'2026-06-01T00:00:00.123456Z',source_hash:'a'.repeat(64),engine_hash:'b'.repeat(32),fallback_daily_mean:'50.5',
  configuration:{baseline:{id:'mean-1',method:'MEAN',params:{}},challengers:[{id:'naive-1',method:'NAIVE',params:{}}],policy:promotion,meaning:'EXPLICIT_OWNER_ACTIVATION_POLICY'},
  series:Array.from({length:100},(_,i)=>({date:day(i),known_at:day(i+1)+'T01:00:00.123456Z',revision:'1',state:'OBSERVED',value:String(i+1),refs:[ref]})),
  refs:[ref],product_sku:'CONTROLLED',product_name:'Explicit synthetic model history',knowledge_basis:'ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES',no_retrospective_availability_backfill:true}
 const p={id:'44444444-4444-4444-8444-444444444444',revision:'1',registry_id:d.registry_id,recorded_at:d.registered_at,state:'ACTIVE',reason:'Explicit controlled policy fixture; not a factory decision',config:{minimum_training_days:'20',maximum_horizon_days:'90',allowed_methods:['NAIVE'],promotion}}
 d.configuration.activation_policy={id:p.id,revision:p.revision,recorded_at:p.recorded_at}
 const c={target_key:key,size_id:size,source_hash:d.source_hash,engine_hash:d.engine_hash,known_as_of:d.known_as_of,horizon_days:'7',forecast_from_date:day(100)}
 return{d,p,c}
}
const cases=[]
async function test(id,fn){try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,2200)})}}
await test('EXPLICIT_PROSPECTIVE_POLICY_AND_PAIRED_WINNER',async()=>{
 const f=fixture();f.r=await build(f.d);const out=await decide(f)
 assert.equal(f.r.selection_status,'CHALLENGER_RECOMMENDED');assert.equal(out.state,'ELIGIBLE');assert.equal(out.selected_model.method,'NAIVE')
 assert.deepEqual(out.forecast.forecasts,Array(7).fill('100.000000000000'));assert.equal(out.forecast.training_count,100)
 assert.equal(out.forecast_applied,false);assert.equal(out.production_go,false)
 assert.equal(f.r.evaluation.challengers[0].summary.mae,'4.0000000000000000')
 return{fixed_naive_expected_each_day:'100',seven_day_vector_preserved:true,paired_MAE:'4',no_registry_or_business_write:true}
})
await test('MISSING_OR_SUSPENDED_POLICY_NEVER_ACTIVATES',async()=>{
 const f=fixture();f.p=null;assert.equal((await decide(f)).reason,'EXPLICIT_ACTIVATION_POLICY_REQUIRED')
 f.p=fixture().p;f.p.state='SUSPENDED';assert.equal((await decide(f)).reason,'ACTIVATION_POLICY_SUSPENDED')
 return{no_default_policy:true}
})
await test('TECHNICAL_PROPOSAL_AND_POSTHOC_POLICY_REFUSED',async()=>{
 for(const mutate of[f=>f.d.configuration.meaning='TECHNICAL_PROPOSAL_NOT_OWNER_SERVICE_TARGET',f=>f.p.recorded_at='2026-06-01T00:00:00.123457Z',f=>f.p.registry_id='another-policy',f=>f.p.id=f.p.id.replace(/^4/,'7'),f=>f.p.revision='2']){
  const f=fixture();mutate(f);assert.equal((await decide(f)).reason,'POLICY_NOT_PROSPECTIVELY_REGISTERED')
 }
 return{one_microsecond_late_policy_is_not_backdated:true,technical_registry_is_not_owner_approval:true}
})
await test('CURRENT_SOURCE_ENGINE_TARGET_SIZE_AND_CLOCK_BOUND',async()=>{
 for(const mutate of[f=>f.c.source_hash='c'.repeat(64),f=>f.c.engine_hash='d'.repeat(32),f=>f.c.target_key=f.c.target_key.replace(/^1/,'9'),f=>{f.c.size_id=f.c.size_id.replace(/^2/,'8');f.c.target_key=f.c.target_key.split(':')[0]+':'+f.c.size_id},f=>f.c.known_as_of=day(100)+'T12:00:00.123455Z']){
  const f=fixture();mutate(f);const out=await decide(f);assert.equal(out.reason,'MODEL_EVIDENCE_NOT_CURRENT');assert.equal(out.forecast,null)
 }
 return{five_stale_or_mismatched_contexts_fail_closed:true}
})
await test('HORIZON_NEVER_EXTRAPOLATED_OR_SMEARED',async()=>{
 const f=fixture();f.c.horizon_days='8';assert.equal((await decide(f)).reason,'MODEL_HORIZON_NOT_QUALIFIED')
 f.c.horizon_days='7';f.p.config.maximum_horizon_days='6';assert.equal((await decide(f)).reason,'MODEL_HORIZON_NOT_QUALIFIED')
 return{only_exact_tested_horizon:true,no_daily_mean_adapter:true}
})
await test('EXPLICIT_METHOD_AND_TRAINING_MINIMUM',async()=>{
 const f=fixture();f.p.config.allowed_methods=[];assert.equal((await decide(f)).reason,'METHOD_NOT_EXPLICITLY_ALLOWED')
 f.p.config.allowed_methods=['NAIVE'];f.p.config.minimum_training_days='101';assert.equal((await decide(f)).reason,'CURRENT_TRAINING_BELOW_POLICY_MINIMUM')
 return{no_invented_factory_threshold:true}
})
await test('RECOMPUTED_RESULT_REJECTS_FORGED_SELECTION_FORECAST_AND_SCORE',async()=>{
 const base=fixture();base.r=await build(base.d)
 for(const mutate of[f=>f.r.forecast.forecasts[0]='999',f=>f.r.selected_model_id='mean-1',f=>f.r.evaluation.challengers[0].summary.mae='0',f=>f.r.evaluation.holdout.used_for_selection=true]){
  const f=structuredClone(base);mutate(f);await assert.rejects(()=>decide(f),/CP7_MODEL_ACTIVATION_RESULT_MISMATCH/)
 }
 return{four_untrusted_result_mutations_refused:true}
})
await test('CHANGED_PROMOTION_POLICY_REQUIRES_MATCHING_REGISTRY',async()=>{
 const f=fixture();f.p=structuredClone(f.p);f.p.config.promotion.minimum_mae_improvement='1'
 assert.equal((await decide(f)).reason,'POLICY_NOT_PROSPECTIVELY_REGISTERED');return{no_retroactive_policy_retuning:true}
})
await test('LATE_REGISTRY_AND_CURRENT_ONLY_HISTORY_RETAIN_BASELINE',async()=>{
 const f=fixture();f.d.registered_at=f.p.recorded_at=day(99)+'T12:00:00.123456Z'
 f.d.configuration.activation_policy.recorded_at=f.p.recorded_at
 assert.equal((await decide(f)).reason,'REGISTRY_NOT_KNOWN_BEFORE_VALIDATION')
 const g=fixture();for(const row of g.d.series)row.known_at=g.d.known_as_of
 assert.equal((await decide(g)).reason,'HISTORICAL_NATIVE_KNOWLEDGE_INSUFFICIENT')
 return{no_fake_past_knowledge_from_current_capture:true}
})
await test('CURRENT_CENSORED_HISTORY_NEVER_ZERO',async()=>{
 const f=fixture();f.d.series.at(-1).state='CENSORED';f.d.series.at(-1).value=null
 const out=await decide(f);assert.equal(out.reason,'CURRENT_TRAINING_NOT_ELIGIBLE');assert.equal(out.forecast,null)
 return{censored_period_not_zero:true}
})
await test('BASELINE_TIE_IS_NOT_A_COMPLEX_MODEL_WIN',async()=>{
 const f=fixture();for(const row of f.d.series)row.value='10'
 const out=await decide(f);assert.equal(out.reason,'BASELINE_RETAINED_BY_PAIRED_PROMOTION_GUARDS');assert.equal(out.forecast,null)
 return{strict_primary_improvement_preserved:true}
})
await test('CLOSED_POLICY_VALIDATION',async()=>{
 const mutations=[p=>p.extra=true,p=>p.config.minimum_training_days='0',p=>p.config.maximum_horizon_days='91',p=>p.config.allowed_methods=['NAIVE','NAIVE'],p=>p.config.allowed_methods=['INVENTED'],p=>p.reason='',p=>p.config.promotion.minimum_mae_improvement='-1']
 for(const mutate of mutations){const f=fixture();mutate(f.p);await assert.rejects(()=>decide(f),/CP7_/)}
 return{invalid_configs:mutations.length}
})
await test('FORECAST_VECTOR_ORIGIN_AND_CANONICAL_CONTEXT',async()=>{
 const f=fixture();f.c.known_as_of=day(101)+'T12:00:00.123456Z';f.c.forecast_from_date=day(101)
 const out=await decide(f);assert.equal(out.reason,'MODEL_FORECAST_ORIGIN_NOT_CURRENT');assert.equal(out.forecast,null)
 for(const mutate of[g=>g.c.forecast_from_date=day(99),g=>g.c.size_id='other-size',g=>g.c.source_hash='g'.repeat(64),g=>g.c.engine_hash='b'.repeat(64)]){
  const g=fixture();mutate(g);await assert.rejects(()=>decide(g),/CP7_MODEL_ACTIVATION_(CONTEXT|CURRENT_DAY)/)
 }
 return{old_vector_never_reused_for_new_day:true,canonical_physical_identity_and_hashes:true}
})
const report={contract:'cp7.model-activation-gate-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',expected:13,counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,gate_sha256:createHash('sha256').update(await read('scripts/cp7_model_activation_gate/gate.sql')).digest('hex'),actual_SQL:true,controlled_synthetic_history:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,installer_catalog22_qualified:false,default_policy_created:false,forecast_applied:false,production_go:false}
const path='docs/cp7/d17-14/ow11/model-gate-local.json';await writeFile(path,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
