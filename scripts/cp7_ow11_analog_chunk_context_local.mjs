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
const report={contract:'cp7.analog-chunk-context-benchmark-synthetic-local.v1',status:'INCOMPLETE',products:total,actual_Native:false,actual_Auth_HTTP_credit:false,factory_SLA_claim:false,full_factory3600_qualified:false,production_go:false,cases:{}}
try{
 await db.exec('create role cp7_alert;create schema cp7_product_analog_choice;create table cp7_product_analog_choice.choices(id uuid,target_key text,revision bigint,action text,evidence jsonb,reason text,actor uuid,request_id uuid,recorded_at timestamptz)')
 await db.exec(block(await read('scripts/cp7_product_analog_choice_stage/choice.sql'),'cp7_product_analog_choice.source_at'))
 const paths=['scripts/cp7-src/demand/estimate.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql','scripts/cp7_product_analog_consumer/kernel.sql','scripts/cp7_product_analog_consumer/baseline.sql','scripts/cp7_product_analog_provenance_stage/provenance.sql','scripts/cp7_model_target_projection/projection.sql','scripts/cp7_model_target_consumer_v2/consumer.sql']
 for(const p of paths)await db.exec(await read(p))
 const frozenHead='5a90076062cbae91f03549c0839519a44ed5d2a5'
 const frozenBaseline=execFileSync('git',['show',frozenHead+':scripts/cp7_product_analog_provenance_stage/hooks.sql'],{encoding:'utf8'})
 const currentSql=block(frozenBaseline,'cp7_product_analog_consumer.baseline_rows')
 report.baseline_source_head=frozenHead
 report.reproduces_target_loop_pattern_only=true
 report.full_capture_path_qualified=false
 report.frozen_chunking_renderer_sha256=createHash('sha256').update(execFileSync('git',['show',frozenHead+':scripts/cp7_product_analog_consumer_stage/render.py'])).digest('hex')
 await db.exec(currentSql)
 await db.exec(`create schema cp7_analysis_stage; create function cp7_analysis_stage.baseline_rows(c jsonb,history_rows jsonb,current_stock jsonb,hash text)returns jsonb language plpgsql immutable as $$begin return cp7_product_analog_consumer.baseline_rows(c,history_rows,current_stock,hash,c->'analog_consumer_context');end$$;
 create function public.b_current_chunked(c jsonb,h jsonb,stock jsonb,hash text,context jsonb)returns jsonb language plpgsql immutable as $$declare rows_out jsonb[]:=array(select value from jsonb_array_elements(h));targets_out jsonb[]:='{}';chunk_rows jsonb;chunk_targets jsonb;item jsonb;offset_at integer:=0;per integer:=125;n integer:=jsonb_array_length(h);begin
 c:=c||jsonb_build_object('analog_consumer_context',context);
 while offset_at<n loop
  select coalesce(jsonb_agg(x order by ord),'[]')into chunk_rows from jsonb_array_elements(to_jsonb(rows_out))with ordinality all_history(x,ord)where ord>offset_at and ord<=offset_at+per;
  chunk_targets:=cp7_analysis_stage.baseline_rows(c,chunk_rows,stock,hash);
  for item in select value from jsonb_array_elements(chunk_targets)loop targets_out:=array_append(targets_out,item);end loop;
  offset_at:=offset_at+per;
 end loop;return to_jsonb(targets_out);end$$;
 create function public.b_once_context(c jsonb,h jsonb,stock jsonb,hash text,context jsonb)returns jsonb language plpgsql immutable as $$begin return cp7_analysis_stage.baseline_rows(c||jsonb_build_object('analog_consumer_context',context),h,stock,hash);end$$;`)
 report.frozen_current_baseline_body_sha256=createHash('sha256').update(currentSql).digest('hex')
 report.current_chunking_body_source='scripts/cp7_product_analog_consumer_stage/render.py:two_pass'
 report.chunk_targets=125
 const c=await captureFacts();c.model_target_source=await current(c);c.model_target_stock_references=[]
 Object.assign(c,{production_policies:{rows:[]},profiles:products.slice(0,2).map(p=>({root_id:p.root_id,product_version_id:p.id,size_id:size,sku:p.sku,product_name:p.product_name,reason:'EXPLICIT SYNTHETIC volume assumption; not factory policy',profile_id:p.id,revision:'1',quality:'SELECTED_ASSUMPTION',config:{mean_mode:'SELECTED_MANUAL',daily_pcs:'1000',minimum_available_days:'20',lead_days:'3',review_days:'2',buffer_days:'1'}}))})
 c.product_analog_choices=await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(c)])
 const history=products.map(p=>({target_key:p.root_id+':'+size,size_id:size,available_days:55,days:Array.from({length:55},(_,i)=>({date:f.day(i),state:'AVAILABLE',gross_observed_pcs:'0',training_pcs:'0'})),refs:[{kind:'PRODUCT',id:p.id,revision:'1'}]}))
 const stock=products.map(p=>({target_key:p.root_id+':'+size,sku:p.sku,product_name:p.product_name,native_available_pcs:'7'}))
 const q={from_date:f.day(0),through_date:f.day(99),group_mode:'AS_SOLD'},hash='b'.repeat(64)
 const context=await sql('select cp7_product_analog_consumer.prepare($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(c),JSON.stringify(history),JSON.stringify(q)])
 async function rows(name,h=history){const start=performance.now();const value=await sql('select '+name+'($1::jsonb,$2::jsonb,$3::jsonb,$4,$5::jsonb)v',[JSON.stringify(c),JSON.stringify(h),JSON.stringify(stock),hash,JSON.stringify(context)]);return{value,millis:Math.round((performance.now()-start)*1000)/1000}}
 console.log(JSON.stringify({phase:'baseline',products:total,history_days:55,input_bytes:JSON.stringify({c,history,stock,context}).length}))
 const old=await rows('public.b_current_chunked')
 console.log(JSON.stringify({phase:'baseline_complete',millis:old.millis}))
 const fast=await rows('public.b_once_context')
 assert.equal(old.value.length,total);assert.deepEqual(fast.value,old.value)
 report.cases.COMPLETE_JSON_PARITY={status:'PASS',baseline_millis:old.millis,optimized_millis:fast.millis,ratio:old.millis/fast.millis,rows:total,all_JSON_fields_refs_and_quantities_identical:true}
 const bad=structuredClone(history);bad[0].available_days=54
 for(const name of ['public.b_current_chunked','public.b_once_context'])await assert.rejects(()=>rows(name,bad),/CP7_ANALOG_CONSUMER_ROW_CONTEXT/)
 report.cases.ROW_CONTEXT_GUARD_RETAINED={status:'PASS',both_variants_refuse_changed_row:true}
 report.source_sha256=Object.fromEntries(await Promise.all(paths.map(async p=>[p,createHash('sha256').update(await read(p)).digest('hex')])))
 report.status='PASS';report.counts={PASS:2}
}catch(error){report.error=String(error);report.stack=error.stack;throw error}
finally{await writeFile('docs/cp7/d17-14/ow11/analog-chunk-context-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));await db.close()}
