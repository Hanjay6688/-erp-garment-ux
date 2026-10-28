// Actual immutable consumer SQL on explicitly synthetic volume, no Native/SLA credit.
import assert from 'node:assert/strict'
import {randomUUID,createHash} from 'node:crypto'
import {writeFile} from 'node:fs/promises'
import {modelTargetSourceV2Fixture} from './cp7_ow11_model_target_source_v2_local_fixture.mjs'
const total=3600,root='22222222-2222-4222-8222-222222222222',size='33333333-3333-4333-8333-333333333333'
const products=Array.from({length:total},(_,i)=>{const id=i===0?root:randomUUID();return{id,root_id:id,model_id:id,size_id:size,sku:'SYNTHETIC3600-'+i,product_name:'Explicit local volume '+i,commercial:[]}})
const f=await modelTargetSourceV2Fixture({products}),{db,read,sql,captureFacts,currentV2:current}=f
const block=(s,n)=>{const r=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(r?.length,1,n);return r[0]}
const report={contract:'cp7.model-target-v2-volume-synthetic-local.v1',status:'INCOMPLETE',products:total,actual_Native:false,actual_Auth_HTTP_credit:false,factory_SLA_claim:false,full_factory3600_qualified:false,production_go:false,cases:{}}
try{
 await db.exec('create role cp7_alert;create schema cp7_product_analog_choice;create table cp7_product_analog_choice.choices(id uuid,target_key text,revision bigint,action text,evidence jsonb,reason text,actor uuid,request_id uuid,recorded_at timestamptz)')
 await db.exec(block(await read('scripts/cp7_product_analog_choice_stage/choice.sql'),'cp7_product_analog_choice.source_at'))
 const paths=['scripts/cp7-src/demand/estimate.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql','scripts/cp7_product_analog_consumer/kernel.sql','scripts/cp7_product_analog_consumer/baseline.sql','scripts/cp7_product_analog_provenance_stage/provenance.sql','scripts/cp7_model_target_projection/projection.sql','scripts/cp7_model_target_consumer_v2/consumer.sql']
 for(const p of paths)await db.exec(await read(p))
 await db.exec(block(await read('scripts/cp7_product_analog_provenance_stage/hooks.sql'),'cp7_product_analog_consumer.baseline_rows'))
 const c=await captureFacts();c.model_target_source=await current(c);c.model_target_stock_references=[]
 Object.assign(c,{production_policies:{rows:[]},profiles:products.map(p=>({root_id:p.root_id,product_version_id:p.id,size_id:size,sku:p.sku,product_name:p.product_name,reason:'EXPLICIT SYNTHETIC volume assumption; not factory policy',profile_id:p.id,revision:'1',quality:'SELECTED_ASSUMPTION',config:{mean_mode:'SELECTED_MANUAL',daily_pcs:'1000',minimum_available_days:'20',lead_days:'3',review_days:'2',buffer_days:'1'}}))})
 c.product_analog_choices=await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(c)])
 const history=products.map(p=>({target_key:p.root_id+':'+size,size_id:size,available_days:0,days:[],refs:[]}))
 const stock=products.map(p=>({target_key:p.root_id+':'+size,sku:p.sku,product_name:p.product_name,native_available_pcs:'7'}))
 const q={from_date:f.day(0),through_date:f.day(99),group_mode:'AS_SOLD'},hash='b'.repeat(64)
 const context=await sql('select cp7_product_analog_consumer.prepare($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(c),JSON.stringify(history),JSON.stringify(q)])
 async function rows(name,h=history){const start=performance.now();const value=await sql('select '+name+'($1::jsonb,$2::jsonb,$3::jsonb,$4,$5::jsonb)v',[JSON.stringify(c),JSON.stringify(h),JSON.stringify(stock),hash,JSON.stringify(context)]);return{value,millis:Math.round((performance.now()-start)*1000)/1000}}
 const old=await rows('cp7_product_analog_consumer.baseline_rows'),currentRows=await rows('cp7_model_target_consumer_v2.rows')
 assert.equal(old.value.length,total);assert.equal(currentRows.value.length,total)
 for(let i=0;i<total;i++){
  const before=old.value[i],after=currentRows.value[i]
  assert.equal(before.target_key,after.target_key);assert.deepEqual(before.target,after.target);assert.deepEqual(before.demand_estimate,after.demand_estimate)
  assert.equal(after.target.target_pcs,'6000');assert.equal(after.target.reorder_point_pcs,'4000')
  assert.equal(after.model_resolution.state,'BASELINE_RETAINED');assert.equal(after.model_resolution.runtime,null);assert.equal(after.model_resolution.forecast_applied,false)
  assert.equal(after.demand_provenance.own_total_pcs,'0');assert.equal(after.demand_provenance.own_available_days,'0')
 }
 report.cases.ALL3600_KERNELS_AND_OBSERVED_OPERANDS={status:'PASS',baseline_millis:old.millis,current_millis:currentRows.millis,manual_target6000_ROP4000:true,UNKNOWN_model_retains_manual_target:true}
 const subset=history.filter((_,i)=>i%36===0),paged=await rows('cp7_model_target_consumer_v2.rows',subset)
 assert.deepEqual(paged.value,currentRows.value.filter((_,i)=>i%36===0))
 report.cases.SUBSET100_USES_SAME_GLOBAL_CONTEXT={status:'PASS',rows:paged.value.length,millis:paged.millis,global_source_products:products.length}
 report.source_sha256=Object.fromEntries(await Promise.all(paths.map(async p=>[p,createHash('sha256').update(await read(p)).digest('hex')])))
 report.status='PASS';report.counts={PASS:2}
}catch(error){report.error=String(error);report.stack=error.stack;throw error}
finally{await writeFile('docs/cp7/d17-14/ow11/model-target-v2-scale-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));await db.close()}
