// Actual immutable consumer SQL on explicitly synthetic volume, no Native/SLA credit.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {randomUUID,createHash} from 'node:crypto'
import {writeFile} from 'node:fs/promises'
import {modelTargetSourceV2Fixture} from './cp7_ow11_model_target_source_v2_local_fixture.mjs'
const total=Number(process.env.CP7_ANALOG_VOLUME_N??600),root='22222222-2222-4222-8222-222222222222',size='33333333-3333-4333-8333-333333333333'
const products=Array.from({length:total},(_,i)=>{const id=i===0?root:randomUUID();return{id,root_id:id,model_id:id,size_id:size,sku:'SYNTHETIC3600-'+i,product_name:'Explicit local volume '+i,commercial:[]}})
const f=await modelTargetSourceV2Fixture({products}),{db,read,sql,captureFacts,currentV2:current}=f
const block=(s,n)=>{const r=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(r?.length,1,n);return r[0]}
const report={contract:'cp7.analog-context-path-benchmark-synthetic-local.v1',status:'INCOMPLETE',products:total,actual_Native:false,actual_Auth_HTTP_credit:false,factory_SLA_claim:false,full_factory3600_qualified:false,production_go:false,cases:{}}
try{
 await db.exec('create role cp7_alert;create schema cp7_product_analog_choice;create table cp7_product_analog_choice.choices(id uuid,target_key text,revision bigint,action text,evidence jsonb,reason text,actor uuid,request_id uuid,recorded_at timestamptz)')
 await db.exec(block(await read('scripts/cp7_product_analog_choice_stage/choice.sql'),'cp7_product_analog_choice.source_at'))
 const paths=['scripts/cp7-src/demand/estimate.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql','scripts/cp7_product_analog_consumer/kernel.sql','scripts/cp7_product_analog_consumer/baseline.sql','scripts/cp7_product_analog_provenance_stage/provenance.sql','scripts/cp7_model_target_projection/projection.sql','scripts/cp7_model_target_consumer_v2/consumer.sql']
 for(const p of paths)await db.exec(await read(p))
 const baselineHead='36b81fcee8ee801a96793c89df6e14388263ad33'
 const pinnedSql=execFileSync('git',['show',baselineHead+':scripts/cp7_product_analog_provenance_stage/hooks.sql'],{encoding:'utf8'})
 const baselineSql=block(pinnedSql,'cp7_product_analog_consumer.baseline_rows')
 await db.exec(baselineSql)
 const currentSql=block(await read('scripts/cp7_product_analog_provenance_stage/hooks.sql'),'cp7_product_analog_consumer.baseline_rows')
 assert.ok(currentSql.includes("context#>array['histories',r->>'target_key']"))
 const optimized=currentSql.replace('cp7_product_analog_consumer.baseline_rows','public.b_optimized_baseline_rows')
 await db.exec(optimized)
 report.baseline_source_head=baselineHead
 report.frozen_baseline_body_sha256=createHash('sha256').update(baselineSql).digest('hex')
 report.current_body_sha256=createHash('sha256').update(currentSql).digest('hex')
 const c=await captureFacts();c.model_target_source=await current(c);c.model_target_stock_references=[]
 Object.assign(c,{production_policies:{rows:[]},profiles:products.map(p=>({root_id:p.root_id,product_version_id:p.id,size_id:size,sku:p.sku,product_name:p.product_name,reason:'EXPLICIT SYNTHETIC volume assumption; not factory policy',profile_id:p.id,revision:'1',quality:'SELECTED_ASSUMPTION',config:{mean_mode:'SELECTED_MANUAL',daily_pcs:'1000',minimum_available_days:'20',lead_days:'3',review_days:'2',buffer_days:'1'}}))})
 c.product_analog_choices=await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(c)])
 const history=products.map(p=>({target_key:p.root_id+':'+size,size_id:size,available_days:55,days:Array.from({length:55},(_,i)=>({date:f.day(i),state:'AVAILABLE',gross_observed_pcs:'0',training_pcs:'0'})),refs:[]}))
 const stock=products.map(p=>({target_key:p.root_id+':'+size,sku:p.sku,product_name:p.product_name,native_available_pcs:'7'}))
 const q={from_date:f.day(0),through_date:f.day(99),group_mode:'AS_SOLD'},hash='b'.repeat(64)
 const context=await sql('select cp7_product_analog_consumer.prepare($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(c),JSON.stringify(history),JSON.stringify(q)])
 async function rows(name,h=history){const start=performance.now();const value=await sql('select '+name+'($1::jsonb,$2::jsonb,$3::jsonb,$4,$5::jsonb)v',[JSON.stringify(c),JSON.stringify(h),JSON.stringify(stock),hash,JSON.stringify(context)]);return{value,millis:Math.round((performance.now()-start)*1000)/1000}}
 console.log(JSON.stringify({phase:'baseline',products:total,history_days:55,input_bytes:JSON.stringify({c,history,stock,context}).length}))
 const old=await rows('cp7_product_analog_consumer.baseline_rows')
 console.log(JSON.stringify({phase:'baseline_complete',millis:old.millis}))
 const fast=await rows('public.b_optimized_baseline_rows')
 assert.equal(old.value.length,total);assert.deepEqual(fast.value,old.value)
 report.cases.COMPLETE_JSON_PARITY={status:'PASS',baseline_millis:old.millis,optimized_millis:fast.millis,ratio:old.millis/fast.millis,rows:total,all_JSON_fields_refs_and_quantities_identical:true}
 const bad=structuredClone(history);bad[0].available_days=54
 for(const name of ['cp7_product_analog_consumer.baseline_rows','public.b_optimized_baseline_rows'])await assert.rejects(()=>rows(name,bad),/CP7_ANALOG_CONSUMER_ROW_CONTEXT/)
 report.cases.ROW_CONTEXT_GUARD_RETAINED={status:'PASS',both_variants_refuse_changed_row:true}
 report.source_sha256=Object.fromEntries(await Promise.all(paths.map(async p=>[p,createHash('sha256').update(await read(p)).digest('hex')])))
 report.status='PASS';report.counts={PASS:2}
}catch(error){report.error=String(error);report.stack=error.stack;throw error}
finally{await writeFile('docs/cp7/d17-14/ow11/analog-context-path-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));await db.close()}
