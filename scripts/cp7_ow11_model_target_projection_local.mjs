// Actual SQL arithmetic; all vectors/thresholds explicitly synthetic.
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
execFileSync('python',['-B','-c','import cp7_model_target_projection as p;p.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
const db=new PGlite(),read=p=>readFile(p,'utf8'),cases=[]
await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;')
for(const path of['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql','scripts/cp7_model_target_projection/projection.sql'])await db.exec(await read(path))
const sql=async(q,args=[])=>(await db.query(q,args)).rows[0].v
const input=(changes={})=>({contract_version:'cp7.target-input.v2',snapshot_id:'synthetic-projection',scope_id:'SYNTHETIC',mode:'DAYS',daily_total_pcs:'100',counted_days:'20',daily_sd:null,lead_days:'1',review_days:'1',buffer_days:'1',service_level:null,refs:[{kind:'SYNTHETIC',id:'target-projection',revision:'1'}],...changes})
const vector=(values=['10','20','40','80','160'],origin='2026-10-24')=>({contract_version:'cp7.model-target-vector.v1',forecast_from_date:origin,forecasts:values})
const base=v=>sql('select cp7_baseline.target($1::jsonb)v',[JSON.stringify(v)])
const project=(v=input(),f=vector(),day='2026-10-24')=>sql('select cp7_model_target_projection.project($1::jsonb,$2::jsonb,$3::date)v',[JSON.stringify(v),JSON.stringify(f),day])
async function test(id,fn){try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,2500)})}}
await test('DATED_VECTOR_DISTINGUISHES_REORDER_TARGET_AND_ONE_BUFFER',async()=>{
 const v=input(),r=await project(v);assert.deepEqual(r.baseline,await base(v));assert.equal(r.state,'ARITHMETIC_CANDIDATE')
 for(const[k,value]of Object.entries({lead_demand_pcs:'10',review_demand_pcs:'20',lead_safety_pcs:'20',horizon_safety_pcs:'40',reorder_point_pcs:'30',target_pcs:'70'}))assert.equal(r.projected[k],value)
 assert.notEqual(r.projected.target_pcs,r.baseline.target_pcs);return{reorder30_target70:true,one_buffer_each_window:true,no_flat_mean:true}
})
await test('FRACTIONAL_HORIZONS_WEIGHT_ONLY_THEIR_DAY_SEGMENT',async()=>{
 const r=await project(input({lead_days:'1.5',review_days:'0.5',buffer_days:'0.5'}),vector(['2.1','4.2','6.3']))
 for(const[k,value]of Object.entries({lead_demand_pcs:'4.20',review_demand_pcs:'2.10',lead_safety_pcs:'2.10',horizon_safety_pcs:'3.15',reorder_point_pcs:'7',target_pcs:'10'}))assert.equal(r.projected[k],value)
 return{fractional_dates_preserved:true,ceiling_only_at_final_PCS:true}
})
await test('LARGE_DECIMAL_VALUES_NEVER_PASS_THROUGH_FLOAT_OR_DAILY_CEILING',async()=>{
 const r=await project(input({lead_days:'1',review_days:'1',buffer_days:'0'}),vector(['9007199254740993.1','0.1']))
 assert.equal(r.projected.reorder_point_pcs,'9007199254740994');assert.equal(r.projected.target_pcs,'9007199254740994')
 const t=await project(input({lead_days:'1',review_days:'2',buffer_days:'0'}),vector(Array(3).fill('0.333333333333')));assert.equal(t.projected.target_pcs,'1')
 return{exact_numeric_above_JS_safe_integer:true,fractional_PCS_rounded_once:true}
})
await test('STATISTICAL_VARIATION_REUSES_QUALIFIED_BASELINE_NO_CALIBRATION_CLAIM',async()=>{
 const v=input({mode:'STATISTICAL',lead_days:'2',review_days:'1',buffer_days:null,daily_sd:'2',service_level:'0.95'}),r=await project(v,vector(['10','20','40'])),b=await base(v)
 assert.equal(r.projected.lead_safety_pcs,b.lead_safety_pcs);assert.equal(r.projected.horizon_safety_pcs,b.horizon_safety_pcs)
 assert.equal(r.projected.reorder_point_pcs,'35');assert.equal(r.projected.target_pcs,'76');assert.equal(r.projected.calibrated_forecast_interval,false)
 return{historical_daily_SD_preserved:true,existing_service_level_only:true,no_days_buffer_added:true}
})
await test('ZERO_FORECAST_AND_ZERO_KNOWN_HORIZON_REMAIN_KNOWN_ZERO',async()=>{
 for(const[v,f]of[[input(),vector(['0','0','0'])],[input({lead_days:'0',review_days:'0',buffer_days:'0'}),vector(['100'])]]){
  const r=await project(v,f);assert.equal(r.projected.target_pcs,'0');assert.equal(r.projected.reorder_point_pcs,'0')
 }return{known_zero_not_missing:true}
})
await test('UNKNOWN_BASELINE_DEMAND_HORIZON_BUFFER_OR_VARIATION_NEVER_FILLED',async()=>{
 const variants=[{daily_total_pcs:null},{lead_days:null},{buffer_days:null},{mode:'STATISTICAL',buffer_days:null,daily_sd:null,service_level:'0.95'},{mode:'STATISTICAL',buffer_days:null,daily_sd:'2',service_level:'0.95',counted_days:'13'}]
 for(const c of variants){const v=input(c),r=await project(v);assert.equal(r.state,'BASELINE_REQUIRED');assert.equal(r.projected,null);assert.deepEqual(r.baseline,await base(v));assert.equal(r.baseline.status,'UNKNOWN')}
 return{unknown_preserved:true,existing_statistical_minimum_preserved:true}
})
await test('SHORT_VECTOR_NEVER_EXTRAPOLATED_TRUNCATED_OR_REPEATED',async()=>{
 for(const c of[{lead_days:'3',review_days:'2',buffer_days:'1'},{lead_days:'1.1',review_days:'0',buffer_days:'0'}]){
  const r=await project(input(c),vector(['10']));assert.equal(r.reason,'FULL_DATED_TARGET_AND_REORDER_VECTOR_REQUIRED');assert.equal(r.projected,null)
 }return{full_fractional_coverage_required:true}
})
await test('OLD_AND_FUTURE_FORECASTS_NEVER_SHIFTED_TO_TODAY',async()=>{
 for(const day of['2026-10-23','2026-10-25']){const r=await project(input(),vector(undefined,day));assert.equal(r.reason,'DATED_FORECAST_ORIGIN_NOT_CURRENT');assert.equal(r.projected,null)}
 return{exact_origin_date_required:true}
})
await test('MALFORMED_VECTOR_AND_DOUBLE_BUFFER_CLOSED_INPUT_REFUSED',async()=>{
 for(const values of[[],Array(91).fill('1'),['1e2'],['-1'],[1],[null],['1','bad']])await assert.rejects(()=>project(input(),vector(values)),/CP7_MODEL_TARGET/)
 await assert.rejects(()=>project(input(),{...vector(),extra:true}),/CP7_WIP_FIELDS/)
 await assert.rejects(()=>project(input({daily_sd:'1'})),/CP7_BASELINE_DOUBLE_BUFFER/)
 await assert.rejects(()=>project(input({mode:'STATISTICAL',daily_sd:'1',service_level:'0.95'})),/CP7_BASELINE_DOUBLE_BUFFER/)
 return{closed_contract_and_numeric_strings:true,no_double_buffer:true}
})
await test('EXISTING_SYNTHETIC_ADMITTED_VECTOR_IS_ARITHMETIC_ONLY',async()=>{
 const wire=JSON.parse(await read('tests/fixtures/nativeModelEvaluationV2Sql.json')),a=wire.eligible.assessment.activation
 assert.equal(wire.actual_Native_capture,false);assert.equal(a.state,'ELIGIBLE')
 const r=await project(input({lead_days:'2',review_days:'1'}),vector(a.forecast.forecasts,a.forecast_from_date),a.forecast_from_date)
 assert.equal(r.projected.reorder_point_pcs,'300');assert.equal(r.projected.target_pcs,'400');assert.equal(r.model_authorized,false);assert.equal(r.forecast_applied,false);assert.equal(r.caller_replaced,false)
 return{synthetic_NAIVE100_vector_only:true,prototype_never_authorizes_model:true}
})
await test('PRIVATE_FUNCTIONS_HAVE_NO_AUTHENTICATED_ENTRY_OR_BUSINESS_TABLE',async()=>{
 for(const role of['anon','authenticated','service_role'])for(const sig of['cp7_model_target_projection.project(jsonb,jsonb,date)','cp7_model_target_projection.sum_window(jsonb,numeric,numeric)'])assert.equal(await sql('select has_function_privilege($1,$2,\'EXECUTE\')v',[role,sig]),false)
 assert.equal(await sql("select count(*)::integer v from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_model_target_projection'"),0)
 return{private2_public0_tables0_replacements0:true}
})
const report={contract:'cp7.model-target-projection-local.v1',status:cases.every(x=>x.status==='PASS')?'PASS':'FAIL',expected:11,counts:cases.reduce((a,x)=>(a[x.status]=(a[x.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_target_projection/projection.sql')).digest('hex'),actual_SQL:true,explicit_synthetic_values:true,model_admission_proved:false,actual_Native_capture:false,actual_Auth_HTTP_credit:false,caller_integrated:false,calibrated_forecast_interval:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-target-projection-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
