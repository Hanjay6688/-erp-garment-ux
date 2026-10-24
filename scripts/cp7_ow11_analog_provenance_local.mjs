// Actual proposed SQL response bodies over controlled facts, not Native/Auth.
import {readFile,writeFile,access} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),sources=new Map(),read=async p=>{const s=await readFile(p,'utf8');sources.set(p,createHash('sha256').update(s).digest('hex'));return s}
const block=(s,n)=>{const a=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(a?.length,1,n);return a[0]}
const sql=async(q,args=[])=>(await db.query(q,args)).rows[0]?.v
await db.exec(`create role cp7_capture;create role anon;create role authenticated;create role service_role;create role cp7_alert;
 create schema extensions;create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)$$;
 create schema cp7_product_analog_choice;create table cp7_product_analog_choice.choices(id uuid,target_key text,revision bigint,action text,evidence jsonb,reason text,actor uuid,request_id uuid,recorded_at timestamptz);
 create schema cp7_reorder_inputs;create schema cp7_reorder_caller;create schema cp7_stock_formula;create schema cp7_planning;`)
for(const p of ['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7-src/demand/estimate.sql','scripts/cp7_production_stage/sql/cp7_baseline__target.sql'])await db.exec(await read(p))
await db.exec(block(await read('scripts/cp7_product_analog_choice_stage/choice.sql'),'cp7_product_analog_choice.source_at'))
await db.exec(await read('scripts/cp7_product_analog_consumer/kernel.sql'))
await db.exec(await read('scripts/cp7_product_analog_provenance_stage/provenance.sql'))
const hooks=await read('scripts/cp7_product_analog_provenance_stage/hooks.sql')
for(const n of ['cp7_product_analog_consumer.baseline_rows','cp7_reorder_inputs.points','cp7_reorder_caller.evaluate'])await db.exec(block(hooks,n))
await db.exec(block(await read('scripts/cp7-src/stock-formula/formula.sql'),'cp7_stock_formula.z'))
await db.exec(block(await read('scripts/cp7-src/planning/bootstrap.sql'),'cp7_planning.utc'))
const root='11111111-1111-4111-8111-111111111111',source='22222222-2222-4222-8222-222222222222',size='33333333-3333-4333-8333-333333333333',profileId='44444444-4444-4444-8444-444444444444',actor='55555555-5555-4555-8555-555555555555',choiceId='66666666-6666-4666-8666-666666666666',requestId='77777777-7777-4777-8777-777777777777'
const key=root+':'+size,sourceKey=source+':'+size,at='2026-01-20T12:00:00.123456Z',ref={kind:'CONTROLLED_HISTORY',id:source,revision:'1'}
function fixture(n=3,total='1',scale='1'){
 const query={from_date:n===3?'2026-01-01':'2026-01-06',through_date:n===3?'2026-01-03':'2026-01-19',group_mode:'AS_SOLD'}
 const products=[{id:root,root_id:root,size_id:size,sku:'TARGET',product_name:'Produk baru',model_id:null,is_active:true},{id:source,root_id:source,size_id:size,sku:'SOURCE',product_name:'Produk pembanding',model_id:null,is_active:true}]
 const profile={root_id:root,product_version_id:root,profile_id:profileId,revision:'1',quality:'SELECTED_ASSUMPTION',config:{minimum_available_days:'1',mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,lead_days:'3',review_days:'0',buffer_days:'0'}}
 const evidence={contract_version:'cp7.product-analog-material.v1',target_key:key,source_key:sourceKey,reviewed:true,profile_id:profileId,profile_revision:'1',minimum_available_days:'1',target_product:products[0],source_product:products[1],scale_factor:scale}
 const days=Array.from({length:n},(_,i)=>({date:new Date(Date.parse(query.from_date)+i*86400000).toISOString().slice(0,10),state:'AVAILABLE',gross_observed_pcs:i?'0':total,training_pcs:i?'0':total}))
 const h=[{target_key:key,size_id:size,available_days:0,days:days.map(d=>({...d,state:'UNKNOWN',gross_observed_pcs:'0',training_pcs:null})),refs:[ref]},{target_key:sourceKey,size_id:size,available_days:n,days,refs:[ref]}]
 const c={captured_at:at,facts:{products},profiles:[profile,{root_id:source,product_version_id:source,profile_id:null,revision:'0',quality:'UNREVIEWED',config:null}],production_policies:{rows:[]}}
 const stock=products.map(p=>({target_key:p.root_id+':'+p.size_id,root_id:p.root_id,size_id:p.size_id,sku:p.sku,product_name:p.product_name,native_available_pcs:'0'}))
 return{c,h,query,profile,evidence,stock}
}
async function baseline(f,action='CONFIRM'){
 await db.exec('truncate cp7_product_analog_choice.choices')
 await sql('insert into cp7_product_analog_choice.choices values($1,$2,1,$3,$4,$5,$6,$7,$8)',[choiceId,key,action,JSON.stringify(action==='CLEAR'?null:f.evidence),'Ukuran fisik sama; pola penjualan diperiksa',actor,requestId,'2026-01-19T10:00:00.123456Z'])
 f.c.product_analog_choices=await sql('select cp7_product_analog_consumer.capture($1::jsonb)v',[JSON.stringify(f.c)])
 const context=await sql('select cp7_product_analog_consumer.prepare($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(f.c),JSON.stringify(f.h),JSON.stringify(f.query)])
 return sql('select cp7_product_analog_consumer.baseline_rows($1::jsonb,$2::jsonb,$3::jsonb,$4,$5::jsonb)v',[JSON.stringify(f.c),JSON.stringify(f.h),JSON.stringify(f.stock),'a'.repeat(64),JSON.stringify(context)])
}
const cases=[],fixtures={}
const test=async(id,fn)=>{try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,1800)})}}
await test('ANALOG_ACTUAL_KERNEL_INPUTS_OWN_HISTORY_UNCHANGED',async()=>{
 const f=fixture(),rows=await baseline(f),r=rows[0],p=r.demand_provenance
 assert.equal(p.own_total_pcs,'0');assert.equal(p.own_available_days,'0');assert.equal(p.daily_total_pcs,'1');assert.equal(p.counted_days,'3');assert.equal(p.target_pcs,'1')
 assert.equal(p.analog.source_key,sourceKey);assert.equal(p.analog.source_name,'Produk pembanding');assert.equal(p.analog.choice_id,choiceId);assert.equal(p.analog.scaled_total_pcs,'1')
 fixtures.analog=p;return{same_kernel_target:'1',own_PCS:'0',own_days:'0',captured_choice_and_source:true}
})
await test('FRACTIONAL_SCALED_PCS_ABOVE_JS_SAFE_INTEGER',async()=>{
 const p=(await baseline(fixture(3,'9007199254740993','0.5')))[0].demand_provenance
 assert.equal(p.analog.scaled_total_pcs,'4503599627370496.5');assert.equal(p.target_pcs,'4503599627370497');fixtures.huge=p;return{exact_scaled_numerator:p.daily_total_pcs,final_ceil:p.target_pcs}
})
await test('CLEAR_AND_CHANGED_PROFILE_EXPLAIN_UNKNOWN',async()=>{
 const cleared=(await baseline(fixture(),'CLEAR'))[0].demand_provenance;assert.equal(cleared.basis,'UNKNOWN');assert.equal(cleared.target_pcs,null);assert.equal(cleared.analog.source_key,null)
 const f=fixture();f.profile.revision='2';const changed=(await baseline(f))[0].demand_provenance;assert.equal(changed.analog.reason,'ANALOG_PROFILE_CHANGED');assert.equal(changed.daily_total_pcs,null)
 fixtures.cleared=cleared;fixtures.changed=changed;return{withdrawal_and_profile_change_not_zero:true}
})
await test('MANUAL_AND_OWN_PRIORITIES_DO_NOT_CREDIT_ANALOG',async()=>{
 const m=fixture();m.profile.config.mean_mode='SELECTED_MANUAL';m.profile.config.daily_pcs='2';const manual=(await baseline(m))[0].demand_provenance
 assert.equal(manual.target_pcs,'6');assert.equal(manual.analog,null);fixtures.manual=manual
 const o=fixture();o.h[0]={...o.h[0],available_days:3,days:o.h[1].days.map(d=>({...d,gross_observed_pcs:'3'}))};const own=(await baseline(o))[0].demand_provenance
 assert.equal(own.own_total_pcs,'9');assert.equal(own.daily_total_pcs,'9');assert.equal(own.counted_days,'3');assert.equal(own.analog,null);fixtures.own=own
 return{manual_target:'6',own_target:'9',analog_not_used:true}
})
await test('REAL_REORDER_POINTS_AND_EVALUATE_VERSIONED_PROJECTION',async()=>{
 const f=fixture(14),rows=await baseline(f),defaults={service_level:'0.95',window_days:'14'}
 const input={contract_version:'cp7.reorder-native-inputs.v1',captured_at:at,query:f.query,source_hash:'a'.repeat(64),history_hash:'b'.repeat(64),target_engine:'EXISTING_NATIVE_STAGED_BASELINE',products:f.c.facts.products,history:f.h,current_stock:f.stock,targets:rows,apply_enabled:false,production_go:false}
 const points=await sql('select cp7_reorder_inputs.points($1::jsonb,$2::jsonb,\'[]\',\'[]\')v',[JSON.stringify(input),JSON.stringify(defaults)])
 const snapshot={contract_version:'cp7.reorder-reader-snapshot.v1',captured_at:at,query:f.query,defaults,leads:[],manuals:[],products:f.c.facts.products,current_stock:f.stock,points,threshold_source_hash:'a'.repeat(64),input_path:'CONTROLLED_SOURCE',history_statistics:Object.fromEntries(f.h.map(h=>[h.target_key,{sale_days:h.available_days?1:0}])),threshold_hash:'c'.repeat(64),threshold_captured_at:at,context_hash:'d'.repeat(64),engine_hash:'e'.repeat(64),native_capture_status:'COMPLETE',cache_hit:false,live_ROP_caller_changed:false,apply_enabled:false,production_go:false}
 const supply={contract_version:'cp7.reorder-supply-cache.v1',checked_at:at,query:f.query,status:'UNKNOWN',reason:'GLOBAL_ANALYSIS_NEEDED',job:null,projection:null,apply_enabled:false,production_go:false}
 const evaluated=await sql('select cp7_reorder_caller.evaluate($1::jsonb,$2::jsonb)v',[JSON.stringify(snapshot),JSON.stringify(supply)])
 const p=evaluated.rows.find(r=>r.target_key===key),s=evaluated.rows.find(r=>r.target_key===sourceKey)
 assert.equal(p.projection.contract_version,'cp7.fg-reorder-projection.v2');assert.equal(p.sales_pcs,'0');assert.equal(p.counted_days,0);assert.equal(p.point,'1');assert.equal(p.projection.target_demand.counted_days,'14');assert.equal(p.daily_sd,null)
 assert.equal(s.projection.target_demand.basis,'OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE');assert.equal(s.projection.target_demand.own_available_days,'14')
 fixtures.reorder=evaluated.rows;return{actual_points_and_evaluate:true,own_history_stays_zero:true,default_own_source_rebased_to_actual_kernel:true}
})
const report={contract:'cp7.analog-provenance-local.v1',classification:'ACTUAL_SQL_RESPONSE_OVER_CONTROLLED_FACTS_NOT_NATIVE',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',sources:Object.fromEntries(sources),cases,Native_qualified:false,Auth_qualified:false,catalog22_qualified:false,production_go:false}
const dir='docs/cp7/d17-14/ow11';await writeFile(dir+'/provenance-local.json',JSON.stringify(report,null,2)+'\n')
if(report.status==='PASS')await writeFile('tests/fixtures/nativeTargetDemandSql.json',JSON.stringify(fixtures,null,2)+'\n')
else{try{await access(dir+'/provenance-local-first-failure.json')}catch{await writeFile(dir+'/provenance-local-first-failure.json',JSON.stringify(report,null,2)+'\n')}}
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
