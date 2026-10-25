import assert from 'node:assert/strict'
import {randomUUID,createHash} from 'node:crypto'
import {writeFile} from 'node:fs/promises'
import {modelTargetSourceV2Fixture} from './cp7_ow11_model_target_source_v2_local_fixture.mjs'
const f=await modelTargetSourceV2Fixture(),{db,read,sql,actor,root,size,key,test,rejects,cases,now,captureFacts,sourceSetting,currentV2:current,seedScoped}=f
await test('STOCK_BATCH_EXACT_ROW_FIELDS_VERSIONS_EMPTY_AND_BOTH_CLOCKS',async()=>{
 const version=randomUUID(),empty=randomUUID(),future=await sql("select cp7_planning.utc(clock_timestamp()+interval'1 hour')v"),at=await now()
 await db.query('insert into erp.products values($1,$2,$3),($4,null,$3)',[version,root,size,empty])
 for(const[product,qty,physical,system]of[[root,'100',at,at],[version,'-24',at,at],[root,'8',future,at],[root,'4',at,future]])
  await db.query('insert into erp.fg_stock_movements values($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,null,$12)',[randomUUID(),product,randomUUID(),randomUUID(),'A',qty,physical,system,'OPENING','SYNTHETIC',randomUUID(),'2'])
 const products=[{root_id:root,size_id:size},{root_id:empty,size_id:size}],batch=async clock=>sql('select cp7_model_target_source_v2.stock_digests($1::jsonb,$2::timestamptz)v',[JSON.stringify(products),clock])
 for(const clock of[at,future])for(const row of await batch(clock)){
  const p=products.find(p=>p.root_id+':'+size===row.target_key)
  assert.deepEqual(row.stock_reference,await sql('select cp7_history_reference.stock_digest($1::jsonb,$2::timestamptz)v',[JSON.stringify([p]),clock]))
 }
 assert.equal((await batch(at)).find(r=>r.target_key===key).stock_reference.row_count,'2')
 assert.equal((await batch(future)).find(r=>r.target_key===key).stock_reference.row_count,'4')
 await rejects(()=>sql('select cp7_model_target_source_v2.stock_digests($1::jsonb,$2::timestamptz)v',[JSON.stringify([products[0],products[0]]),at]),/STOCK_ROOTS/)
 return{full_existing_digest_parity:true,product_versions_and_empty_target_retained:true,physical_and_system_cutoffs:true}
})
await test('NONSTOCK_AND_PHYSICAL_BATCH_EXACT_SINGLE_BINDER_PARITY',async()=>{
 const c=await captureFacts(),other=randomUUID(),saleId=randomUUID(),j=randomUUID(),ret=randomUUID(),rj=randomUUID(),producer='1'.repeat(64)
 c.facts.products.push({id:other,root_id:other,size_id:size,commercial:[]})
 c.facts.sales=[root,root,other].map(root_id=>({id:randomUUID(),root_id,sale_id:saleId,status:'REVERSED',qty_pcs:'24',sold_commercial:[]}))
 c.facts.sale_journals=[{id:j,sale_id:saleId,reversal_of_id:null},{id:randomUUID(),sale_id:randomUUID(),reversal_of_id:j}]
 c.facts.returns=c.facts.sales.map(s=>({id:randomUUID(),sale_item_id:s.id,return_id:ret,qty_pcs:'1'}))
 c.facts.return_journals=[{id:rj,return_id:ret,reversal_of_id:null},{id:randomUUID(),return_id:randomUUID(),reversal_of_id:rj}]
 const h=createHash('sha256').update('cp7.native-stock-row-digest.v1\n0\n').digest('hex')
 const stocks=c.facts.products.map(p=>({target_key:p.root_id+':'+size,stock_reference:{contract_version:'cp7.native-stock-row-digest.v1',scope:'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS',captured_at:c.captured_at,row_count:'0',rows_sha256:h,raw_rows_truncated:false,raw_native_capture_status_overridden:false}}))
 const batch=(capture=c,entries=stocks)=>sql('select cp7_model_target_source_v2.physical_rows($1::jsonb,5000,$2::jsonb,$3)v',[JSON.stringify(capture),JSON.stringify(entries),producer])
 for(const row of await batch())assert.deepEqual(row.reference,await sql('select cp7_model_target_binding.reference($1::jsonb,$2,5000,$3::jsonb,$4)v',[JSON.stringify(c),row.target_key,JSON.stringify(stocks.find(x=>x.target_key===row.target_key).stock_reference),producer]))
 const nonstock=await sql('select cp7_model_target_source_v2.non_stock_rows($1::jsonb,5000)v',[JSON.stringify(c)])
 assert.equal(nonstock.find(x=>x.target_key===key).non_stock.sale_journals.length,2)
 assert.deepEqual((await batch({...c,status:'INCOMPLETE',stock_raw_omitted:true,stock_rows_at_least:50001})).map(x=>x.reference.scoped_source_hash),(await batch()).map(x=>x.reference.scoped_source_hash))
 await rejects(()=>batch(c,[stocks[0],stocks[0]]),/TARGET_UNAVAILABLE/)
 await rejects(()=>batch(c,[{...stocks[0],stock_reference:{...stocks[0].stock_reference,rows_sha256:'0'.repeat(64)}}]),/STOCK_MISMATCH/)
 const overflow=structuredClone(c);overflow.facts.sales=Array(50001).fill(overflow.facts.sales[0]);await rejects(()=>batch(overflow),/NON_STOCK_INCOMPLETE/)
 return{same_document_multiple_roots_and_items:true,journals_not_duplicated:true,reversal_links_preserved:true,global_caps_before_filter:true,raw_omission_never_zero:true}
})
await test('EMPTY_COMPLETE_AND_UNKNOWN_BOUNDARY_DIFFER',async()=>{
 const c=await captureFacts();for(const k of Object.keys(c.facts))c.facts[k]=[]
 assert.deepEqual(await sql('select cp7_model_target_source_v2.non_stock_rows($1::jsonb,5000)v',[JSON.stringify(c)]),[])
 await rejects(()=>sql('select cp7_model_target_source_v2.non_stock_rows($1::jsonb,5000)v',[JSON.stringify({...c,status:'INCOMPLETE'})]),/BINDING_SCOPE/)
 return{empty_only_when_complete:true}
})
await test('NO_MODEL_EXPLICIT_NULL_WITHOUT_PHYSICAL_OR_HISTORY_READ',async()=>{
 await sourceSetting('mode','CHANGE_PHYSICAL');const a=await current()
 assert.equal(a.rows.length,1);assert.equal(a.rows[0].runtime,null);assert.equal(a.rows[0].run_id,null);assert.equal(a.rows[0].reason,'NO_OWN_MODEL_EVALUATION');assert.equal(a.rows[0].forecast,null)
 return{missing_model_not_zero_or_forecast:true}
})
await test('GLOBAL_BASELINE_WITHOUT_ACTIVATION_POLICY_IS_VALID',async()=>{
 const m=await f.capture();await f.reset();const a=await current()
 assert.equal(a.policy_source,null);assert.equal(a.rows[0].run_id,m.run_id);assert.equal(a.rows[0].runtime,'GLOBAL_V2');assert.equal(a.rows[0].state,'BASELINE_REQUIRED');assert.equal(a.rows[0].forecast,null)
 return{JSON_null_SQL_null_policy_equivalent:true,unknown_policy_does_not_hide_valid_baseline:true}
})
await test('SCOPED_BASELINE_VERSION_AND_SOURCE_BOUND',async()=>{
 const s=await seedScoped(),a=await current(),r=a.rows[0]
 assert.equal(r.run_id,s.id);assert.equal(r.runtime,'SCOPED_V3');assert.equal(r.read_method,'erp_cp7_read_model_evaluation_v3');assert.equal(r.history_source_hash,s.hash);assert.equal(r.physical_source_hash,s.hash)
 assert.equal(r.state,'BASELINE_REQUIRED');assert.equal(r.forecast,null);assert.equal(r.history_scope,'SINGLE_CURRENT_PHYSICAL_ROOT')
 return{actual_current_guard_SQL:true,unknown_policy_not_invented:true,runtime_namespace_retained:true}
})
await test('CONTROLLED_ELIGIBLE_EXACT_FORECAST_AND_CLOCK_STABLE_IDENTITY',async()=>{
 const s=await seedScoped({eligible:true}),before=await sql('select to_jsonb(r)v from cp7_model_scoped_evaluation.runs r where id=$1',[s.id]),a=await current(),b=await current()
 assert.equal(a.rows[0].state,'ELIGIBLE');assert.deepEqual(a.rows[0].forecast,s.assessment.activation.forecast);assert.equal(a.source_hash,b.source_hash);assert.notEqual(a.checked_at,b.checked_at)
 assert.deepEqual(await sql('select to_jsonb(r)v from cp7_model_scoped_evaluation.runs r where id=$1',[s.id]),before)
 return{synthetic_positive_only:true,actual_assessment_and_guard_SQL:true,immutable_input_result_unchanged:true,clock_not_identity:true}
})
await test('NEWER_GLOBAL_BASELINE_DISPLACES_OLDER_SCOPED_WINNER',async()=>{
 const s=await seedScoped({eligible:true});await f.seed({revision:'2',state:'SUSPENDED',at:await now()});const newer=await f.capture();await f.reset()
 const a=await current();assert.equal(a.rows[0].run_id,newer.run_id);assert.equal(a.rows[0].runtime,'GLOBAL_V2');assert.equal(a.rows[0].read_method,'erp_cp7_read_model_evaluation_v2');assert.equal(a.rows[0].state,'BASELINE_REQUIRED');assert.equal(a.rows[0].forecast,null);assert.notEqual(a.rows[0].run_id,s.id)
 return{latest_unfiltered_across_runtimes:true,no_fallback_to_older_winner:true}
})
await test('CHANGED_CAPTURE_AND_CURRENT_ACCESS_FAIL_CLOSED',async()=>{
 await seedScoped()
 for(const[mode,error]of[['CHANGE_PHYSICAL',/PHYSICAL_SOURCE_CHANGED_DURING_CAPTURE/],['REVOKE',/CONTROLLED_ACCESS_DENIED/],['NEW_MODEL',/AUTHORITY_CHANGED_DURING_CAPTURE/]]){
  await sourceSetting('mode',mode);await rejects(()=>current(),error)
 }
 return{source_access_and_latest_rechecked_after_physical_read:true,actual_concurrency:false}
})
await test('STORED_HISTORY_OR_MODEL_BINDING_TAMPER_REFUSED',async()=>{
 const s=await seedScoped();await db.exec('savepoint original_row');await db.query("update cp7_model_scoped_evaluation.runs set dependency_hash=repeat('0',64)where id=$1",[s.id]);await rejects(()=>current(),/SCOPED_EVALUATION_STORED_BINDING/);await db.exec('rollback to savepoint original_row')
 await db.query("update cp7_model_history_runtime.runs set result=jsonb_set(result,'{scope}',to_jsonb('GLOBAL_CURRENT_PHYSICAL_ROOTS'::text))where id=$1",[s.hid]);await rejects(()=>current(),/MODEL_HISTORY_STORED_BINDING/)
 return{synthetic_corruption_refused:true,no_global_scoped_aliasing:true}
})
await test('WAREHOUSE_ONLY_READ_HAS_NO_MODEL_POLICY_HISTORY_DISCLOSURE',async()=>{
 await seedScoped({eligible:true});await f.setting('model_access','false');const c=await captureFacts(),a=await sql('select cp7_model_target_source_v2.capture_for_reorder($1::jsonb,5000)v',[JSON.stringify(c)])
 assert.equal(a.policy_source,null);assert.equal(a.selection,null);assert.equal(a.live_history_source_hash,null)
 for(const field of['run_id','runtime','read_method','history_run_id','history_scope','history_query','history_source_hash','physical_source_hash','model_source_hash','forecast','selected_model'])assert.equal(a.rows[0][field],null,field)
 assert.equal(a.rows[0].reason,'MODEL_CURRENT_ACCESS_REQUIRED');await rejects(()=>current(),/CONTROLLED_ACCESS_DENIED/)
 return{warehouse_access_preserved:true,model_and_policy_not_disclosed:true,full_capture_requires_model_access:true}
})
const pins={};for(const file of['stock.sql','non-stock.sql','physical.sql','source.sql','reorder.sql'])pins[file]=createHash('sha256').update(await read('scripts/cp7_model_target_source_v2/'+file)).digest('hex')
const report={contract:'cp7.model-target-source-v2-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',expected:11,counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,source_sha256:pins,PGlite:'0.5.11',actual_SQL:true,synthetic_rows_and_controlled_physical_recapture:true,actual_Native:false,actual_Auth_HTTP:false,actual_concurrency:false,target_caller_integrated:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-target-source-v2-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
