// Exact Native source projections and history kernels, controlled relational
// facts. No actual Native posting/Auth/immutable capture/model admission credit.
import {writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {createNativeReorderFixture} from './cp7_ow10_reorder_local_fixture.mjs'

const {db,stageAudit,id,query,sourceFixture,block,read}=await createNativeReorderFixture()
await db.exec(block(await read('scripts/cp7-src/planning/bootstrap.sql'),'cp7_planning.history_query'))
await db.exec(await read('scripts/cp7_history_reference/digest.sql'))
const source=await read('scripts/cp7_model_history_scope/scope.sql')
await db.exec(source)
await stageAudit.afterUse()
const key=id(1)+':'+id(9000),cases=[]
const sql=async(q,args=[])=>(await db.query(q,args)).rows[0]?.v
const capture=(target=key,q=query,inputs=true)=>sql('select cp7_model_history_scope.capture($1,$2::jsonb,$3)v',[target,JSON.stringify(q),inputs])
const test=async(id,fn)=>{try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,2200)})}console.log(id+': '+cases.at(-1).status)}
const stockOperands=x=>({...x,availability:{...x.availability,inputs:{...x.availability.inputs,snapshot_id:'HASH',scope_id:'SCOPE'}}})
const frozen=()=>sql("select jsonb_object_agg(t.name,t.rows)v from(select 'products'name,jsonb_agg(to_jsonb(x)order by x.id)rows from erp.products x union all select 'stock',jsonb_agg(to_jsonb(x)order by x.id)from erp.fg_stock_movements x union all select 'sales',jsonb_agg(to_jsonb(x)order by x.id)from erp.sales_headers x) t")

await test('SCOPED_ROWS_MATCH_WHOLE_NATIVE_HISTORY_AND_RESERVATIONS',async()=>{
 await sourceFixture();const before=await frozen(),a=await capture()
 const old=await sql('select cp7_planning.history_build(cp7_planning.history_source_within(1000),$1::jsonb)v',[JSON.stringify(query)])
 assert.deepEqual(a.result.history.rows,old.history.rows.filter(x=>x.target_key===key))
 assert.deepEqual(a.result.history.group_events,old.history.group_events.filter(x=>x.lineage_key===id(200)))
 assert.deepEqual(a.result.current_stock.map(stockOperands),old.current_stock.filter(x=>x.target_key===key).map(stockOperands))
 assert.equal(a.result.history.scope_id,'SINGLE_CURRENT_PHYSICAL_ROOT')
 assert.equal(a.result.current_stock[0].availability.inputs.scope_id,'SINGLE_CURRENT_PHYSICAL_ROOT')
 assert.equal(a.result.training_known_at,a.captured_at)
 assert.equal(a.result.history.rows[0].available_days,29)
 assert.equal(a.result.history.rows[0].gross_observed_pcs,'10')
 assert.deepEqual(await frozen(),before)
 return{whole_Native_row_and_stock_exact:true,capture_clock_not_backdated:true,zero_DML:true}
})
await test('MORE_THAN_5000_UNRELATED_PRODUCTS_DO_NOT_TRUNCATE_SINGLE_ROOT',async()=>{
 await sourceFixture();const before=await capture()
 await db.exec("insert into erp.products(id)select (lpad(i::text,8,'0')||'-1111-4111-8111-111111111111')::uuid from generate_series(20000,25500)i")
 assert.equal((await sql('select cp7_planning.history_source_within(1000)v')).status,'INCOMPLETE')
 const after=await capture();assert.equal(after.source_hash,before.source_hash)
 assert.equal(after.source.facts.products.length,1);assert.deepEqual(after.result.history.rows,before.result.history.rows)
 assert.equal(after.raw_capture_status,'COMPLETE')
 return{controlled_factory_products:5504,old_global_limit_unchanged:true,explicit_single_root_only:true}
})
await test('AMBIGUOUS_ACTIVE_ROOT_AND_WRONG_SIZE_REFUSED',async()=>{
 await sourceFixture()
 await assert.rejects(()=>capture(id(1)+':'+id(9002)),/CP7_MODEL_HISTORY_SCOPE_NON_STOCK_INCOMPLETE/)
 await db.query('insert into erp.products(id,identity_root_id,size_id)values($1,$2,$3)',[id(10),id(1),id(9002)])
 await assert.rejects(()=>capture(),/CP7_HISTORY_REFERENCE_ROOTS|CP7_MODEL_HISTORY_SCOPE_TARGET/)
 await assert.rejects(()=>capture(id(999)+':'+id(9000)),/CP7_MODEL_HISTORY_SCOPE_TARGET/)
 return{no_size_filter_hides_duplicate_root:true,no_absent_target_as_zero:true}
})
await test('ALL_IDENTITY_VERSIONS_AND_BOTH_VISIBILITY_CLOCKS_RETAINED',async()=>{
 await sourceFixture()
 await db.query("insert into erp.products(id,identity_root_id,effective_to)values($1,$2,'2021-01-01')",[id(10),id(1)])
 await db.query('update erp.fg_stock_movements set product_id=$1 where id=$2',[id(10),id(100)])
 const first=await capture();assert.equal(first.source.stock_reference.row_count,'4')
 assert.equal(first.result.current_stock[0].native_available_pcs,'90')
 await db.query("insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,book_order)values($1,$2,7,'2026-09-01','2099-01-01','GRADE_A','ADJUSTMENT',100),($3,$2,9,'2099-01-01','2026-09-01','GRADE_A','ADJUSTMENT',101)",[id(800),id(10),id(801)])
 const future=await capture();assert.equal(future.source_hash,first.source_hash)
 await db.query("update erp.fg_stock_movements set system_created_at='2026-09-02'where id=$1",[id(800)])
 const visible=await capture();assert.notEqual(visible.source_hash,first.source_hash)
 assert.equal(visible.result.current_stock[0].native_available_pcs,'97')
 return{old_identity_stock_included:true,physical_and_system_clock_both_filter:true,explicit_controlled_clock_fixture:true}
})
await test('FULL_ROW_DIGEST_DETECTS_EQUAL_TOTAL_METADATA_CHANGE',async()=>{
 await sourceFixture();const before=await capture()
 await db.query("update erp.fg_stock_movements set source_type='CONTROLLED_CHANGE'where id=$1",[id(100)])
 const after=await capture();assert.notEqual(after.source_hash,before.source_hash)
 assert.deepEqual(after.result.history.rows,before.result.history.rows)
 assert.deepEqual(after.result.current_stock.map(stockOperands),before.result.current_stock.map(stockOperands))
 const reread=await capture(key,query,false);assert.equal(reread.source_hash,after.source_hash);assert.equal(reread.result,null)
 return{equal_totals_not_same_source:true,full_stock_reference_read_without_history_recalculation:true}
})
await test('DENSE_SINGLE_ROOT_FULL_SUMMARY_EQUALS_WHOLE_RAW_CALCULATION',async()=>{
 await sourceFixture()
 await db.exec("insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,book_order)select(lpad((50000+i)::text,8,'0')||'-1111-4111-8111-111111111111')::uuid,'00000001-1111-4111-8111-111111111111',0,'2026-09-21','2026-09-21','GRADE_A','ADJUSTMENT',i from generate_series(1,50001)i")
 const a=await capture();assert.equal(a.raw_capture_status,'INCOMPLETE');assert.equal(a.source.facts.stock.length,0)
 assert.equal(a.source.stock_reference.row_count,'50005');assert.equal(a.result.capture_complete,true)
 assert.equal(a.raw_status_overridden,false);assert.equal(a.result.raw_capture_status,'INCOMPLETE')
 // Controlled independent full-array oracle only: original whole Native
 // formula, with every test row supplied. This is not a production source
 // bound override or an admitted Native capture.
 const full=structuredClone(a.source)
 full.facts.stock=await sql("select jsonb_agg(to_jsonb(x)order by x.id)v from(select m.id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,m.product_id,m.lot_id,m.location_id,m.quality_grade,m.qty_signed::text qty_signed,m.physical_at,m.system_created_at,m.movement_type,m.source_type,m.source_id,m.reversal_of_id,m.book_order from erp.fg_stock_movements m join erp.products p on p.id=m.product_id where coalesce(p.identity_root_id,p.id)=$1::uuid)x",[id(1)])
 full.status='COMPLETE';const old=await sql('select cp7_planning.history_build($1::jsonb,$2::jsonb)v',[JSON.stringify(full),JSON.stringify(query)])
 assert.deepEqual(a.result.history.rows,old.history.rows)
 assert.deepEqual(a.result.current_stock.map(stockOperands),old.current_stock.map(stockOperands))
 return{all_selected_stock_rows:50005,no_raw_prefix_used:true,exact_full_array_formula_parity:true,controlled_oracle_not_Native_admission:true}
})
await test('NON_STOCK_INCOMPLETENESS_NEVER_ACCEPTED_AS_STOCK_OVERFLOW',async()=>{
 await sourceFixture();await db.exec('delete from erp.journal_entries')
 await assert.rejects(()=>capture(),/CP7_MODEL_HISTORY_SCOPE_NON_STOCK_INCOMPLETE/)
 await sourceFixture();const c=(await capture()).source
 c.status='INCOMPLETE';c.stock_raw_omitted=true;c.stock_rows_at_least=50001;c.facts.stock=[]
 await assert.rejects(()=>sql('select cp7_model_history_scope.identity($1::jsonb)v',[JSON.stringify(c)]),/CP7_MODEL_HISTORY_SCOPE_STOCK_BOUND/)
 return{missing_posting_journal_refused:true,incomplete_without_full_stock_reference_refused:true}
})
await test('CLOSED_QUERY_PRIVATE_ACL_AND_KNOWN_ZERO',async()=>{
 await sourceFixture()
 const zero=await capture(id(2)+':'+id(9000));assert.equal(zero.result.history.rows[0].gross_observed_pcs,'0');assert.notEqual(zero.result.history.rows[0].available_sales_mean,null)
 const unavailable=await capture(id(3)+':'+id(9000));assert.equal(unavailable.result.history.rows[0].available_sales_mean,null)
 for(const [target,q]of[['wrong',query],[key,{...query,from_date:'2020-01-01'}],[key,{...query,extra:true}],[key,{...query,through_date:'2099-01-01'}]])await assert.rejects(()=>capture(target,q))
 for(const role of['anon','authenticated','service_role','cp7_alert'])assert.equal(await sql("select has_function_privilege($1,'cp7_model_history_scope.capture(text,jsonb,boolean)','EXECUTE')v",[role]),false)
 await db.exec('set role cp7_capture');const privateResult=await capture();await db.exec('reset role');assert.equal(privateResult.result.history.rows[0].gross_observed_pcs,'10')
 return{known_zero_separate_from_unavailable:true,private_invoker_only:true,old_global_history_unchanged:true}
})
const report={contract:'cp7.model-history-scope-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',cases,counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),source_sha256:createHash('sha256').update(source).digest('hex'),actual_SQL:true,controlled_relational_fixtures:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,immutable_capture_runtime_qualified:false,model_caller_integrated:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-history-scope-local.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
