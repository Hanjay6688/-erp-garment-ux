// Actual frozen Native history + current target bodies on controlled DTOs.
// The independent comparison uses the whole existing history_build, rather
// than replaying this adapter's chunk orchestration. This is not Native/Auth.
import {readFile, writeFile, mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite} = await import(process.env.CP7_PGLITE_MODULE ?? '@electric-sql/pglite')
const db = new PGlite(), read = path => readFile(path, 'utf8')
const block = (sql, name) => {
  const start = sql.search(new RegExp('create(?: or replace)? function ' + name.replaceAll('.', '\\.') + '\\('))
  assert.ok(start >= 0, name)
  const end = sql.indexOf('$$;', sql.indexOf('as $$', start))
  assert.ok(end >= 0, name)
  return sql.slice(start, end + 3)
}
await db.exec(`create role cp7_capture nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
 create role anon nologin;create role authenticated nologin;create role service_role nologin;
 create schema cp7_planning;create schema cp7_analysis_stage;create schema cp7_baseline_native;create schema extensions;
 create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)$$;`)
for (const file of ['wip/bootstrap.sql', 'demand/bootstrap.sql', 'demand/history.sql', 'demand/estimate.sql', 'baseline/target.sql']) {
  await db.exec(await read('scripts/cp7-src/' + file))
}
await db.exec(await read('scripts/cp7_production_stage/sql/cp7_baseline__target.sql'))
await db.exec(block(await read('scripts/cp7-src/planning/bootstrap.sql'), 'cp7_planning.utc'))
await db.exec(block(await read('scripts/cp7-src/planning/history-source.sql'), 'cp7_planning.history_events'))
const history = await read('scripts/cp7-src/planning/history.sql')
for (const name of ['cp7_planning.history_availability', 'cp7_planning.history_build']) await db.exec(block(history, name))
const staged = await read('scripts/cp7-src/planning/analysis-stages.sql')
for (const name of ['castable', 'events_clean', 'availability_clean', 'history_prep', 'events_validate',
  'history_validate', 'history_rows', 'history_stock', 'bounds']) {
  await db.exec(block(staged, 'cp7_analysis_stage.' + name))
}
await db.exec(await read('scripts/cp7_target_policy_stage/sql/cp7_analysis_stage__baseline_rows.sql'))
await db.exec(await read('scripts/cp7_reorder_inputs/history.sql'))
await db.exec(`grant usage on schema cp7_planning,cp7_analysis_stage,cp7_baseline_native,extensions,cp7_wip,cp7_demand,cp7_baseline to cp7_capture;`)
const id = n => `${String(n).padStart(8, '0')}-1111-4111-8111-111111111111`
const clock = '2026-10-23T00:00:00Z', query = {from_date:'2026-09-23', through_date:'2026-10-22', group_mode:'AS_SOLD'}
const product = n => ({id:id(n), root_id:id(n), size_id:id(9000), model_id:id(9001), sku:'CONTROL-' + n,
  product_name:'Controlled source ' + n, is_active:true, effective_from:'2020-01-01T00:00:00Z',
  effective_to:null, established_at:'2020-01-01T00:00:00Z', commercial:[]})
const profile = (n, daily=null) => ({root_id:id(n), product_version_id:id(n), quality:'SELECTED_ASSUMPTION',
  profile_id:id(n+1000), revision:'1', config:{mean_mode:daily === null?'OWN_AVAILABLE_HISTORY':'SELECTED_MANUAL',
    daily_pcs:daily, minimum_available_days:'14', lead_days:'3', review_days:'7', buffer_days:'2'}})
const movement = (n, root, qty, at, order=1) => ({id:id(n), root_id:id(root), size_id:id(9000), product_id:id(root),
  qty_signed:qty, physical_at:at, system_created_at:at, quality_grade:'GRADE_A', movement_type:'ADJUSTMENT',
  book_order:String(order), reversal_of_id:null})
const fixture = () => ({captured_at:clock, status:'COMPLETE', facts:{products:[product(1),product(2),product(3)],
  stock:[movement(100,1,'100','2026-09-20T00:00:00Z'), movement(101,1,'-10','2026-09-24T02:00:00Z'),
    movement(102,1,'-90','2026-09-26T01:00:00Z',1),movement(103,1,'90','2026-09-26T02:00:00Z',2),
    movement(104,2,'50','2026-09-20T00:00:00Z')],
  sales:[{id:id(200),sale_id:id(201),root_id:id(1),size_id:id(9000),qty_pcs:'10',status:'POSTED',revision:'1',
    sale_date:'2026-09-24T02:00:00Z',created_at:'2026-09-24T02:00:00Z',updated_at:'2026-09-24T02:00:00Z',sold_commercial:[]}],
  sale_journals:[{id:id(202),sale_id:id(201),status:'POSTED',posting_at:'2026-09-24T02:00:00Z',
    transaction_date:'2026-09-24',reversal_of_id:null}],returns:[],return_journals:[]},
  profiles:[profile(1),profile(2,'2'),profile(3,'0')],production_policies:{rows:[]}})
const invoke = async (source, q=query) => (await db.query('select cp7_reorder_inputs.history($1::jsonb,$2::jsonb)v',
  [JSON.stringify(source),JSON.stringify(q)])).rows[0].v
const whole = async (source, q=query) => (await db.query('select cp7_planning.history_build($1::jsonb,$2::jsonb)v',
  [JSON.stringify(source),JSON.stringify(q)])).rows[0].v
const results=[]
const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,3000)})}}
await test('OW10_INPUTS_ACTUAL_WHOLE_NATIVE_HISTORY_AND_STOCK_EQUAL',async()=>{
  const source=fixture(),a=await invoke(source),b=await whole(source)
  assert.deepEqual(a.history,b.history.rows);assert.deepEqual(a.current_stock,b.current_stock)
  const targets=(await db.query('select cp7_analysis_stage.baseline_rows($1::jsonb,$2::jsonb,$3::jsonb,$4)v',
    [JSON.stringify(source),JSON.stringify(b.history.rows),JSON.stringify(b.current_stock),a.source_hash])).rows[0].v
  assert.deepEqual(a.targets,targets)
  await db.exec('set role cp7_capture');assert.deepEqual(await invoke(source),a);await db.exec('reset role')
  return{whole_history_and_current_stock_full_JSON_equal:true,actual_staged_targets_full_JSON_equal:true,real_non_superuser_read:true}
})
await test('OW10_INPUTS_INTRADAY_STOCKOUT_NOT_LEGACY_START_DAY_AVAILABLE',async()=>{
  const a=await invoke(fixture()),row=a.history.find(x=>x.target_key.startsWith(id(1)))
  assert.equal(row.days.find(x=>x.date==='2026-09-26').state,'STOCKOUT')
  assert.equal(row.available_days,29);assert.equal(row.stockout_days,1);assert.equal(row.gross_observed_pcs,'10')
  const net=a.targets.find(x=>x.target_key===row.target_key).target
  assert.equal(net.reorder_point_pcs,'2');assert.equal(net.target_pcs,'5')
  return{start90_zero_then90_still_stockout:true,available_days:29,exact_total10_over29_point2_target5:true}
})
await test('OW10_INPUTS_PROFILE_MANUAL_AND_KNOWN_ZERO_REMAIN_NATIVE_CHOICES',async()=>{
  const a=await invoke(fixture()),two=a.targets.find(x=>x.target_key.startsWith(id(2))),zero=a.targets.find(x=>x.target_key.startsWith(id(3)))
  assert.equal(two.target.reorder_point_pcs,'10');assert.equal(two.target.target_pcs,'24')
  assert.equal(two.demand_estimate.basis,'SELECTED_MANUAL_ASSUMPTION')
  assert.equal(zero.target.reorder_point_pcs,'0');assert.equal(zero.target.target_pcs,'0')
  assert.equal(zero.target.status,'SCENARIO');assert.equal(a.history.find(x=>x.target_key===zero.target_key).available_days,0)
  return{selected_mean2_exact_native_point10_target24:true,selected_zero_known_despite_no_available_days:true}
})
await test('OW10_INPUTS_POSTED_REVERSED_AND_RETURN_GROSS_RULE_SAME',async()=>{
  const source=fixture();source.facts.returns.push({id:id(210),return_id:id(211),sale_item_id:id(200),qty_pcs:'4',physical_at:'2026-10-01T02:00:00Z'})
  source.facts.return_journals.push({id:id(212),return_id:id(211),posting_at:'2026-10-01T02:00:00Z',reversal_of_id:null})
  const a=await invoke(source),b=await whole(source);assert.deepEqual(a.history,b.history.rows)
  const first=a.history.find(x=>x.target_key.startsWith(id(1)));assert.equal(first.gross_observed_pcs,'10')
  assert.equal(first.days.find(x=>x.date==='2026-09-24').returned_pcs,'4')
  source.facts.sale_journals.push({id:id(220),sale_id:id(201),posting_at:'2026-10-02T02:00:00Z',
    transaction_date:'2026-10-02',reversal_of_id:id(202)})
  const reversed=await invoke(source);assert.deepEqual(reversed.history,(await whole(source)).history.rows)
  assert.equal(reversed.history.find(x=>x.target_key.startsWith(id(1))).gross_observed_pcs,'0')
  return{return4_not_subtracted_from_gross10:true,actual_journal_inverse_removes_gross:true,whole_history_equal_on_both:true}
})
await test('OW10_INPUTS_MULTIPLE_CHUNKS_KEEP_EVERY_PRODUCT_AND_DAY',async()=>{
  const source=fixture();source.facts.products=Array.from({length:420},(_,i)=>product(i+1));source.facts.sales=[];source.facts.sale_journals=[]
  source.facts.stock=source.facts.products.map((p,i)=>movement(i+10000,i+1,'100','2026-09-20T00:00:00Z'))
  source.profiles=source.facts.products.map((p,i)=>profile(i+1,'0'))
  const a=await invoke(source),b=await whole(source);assert.equal(a.history.length,420);assert.equal(a.targets.length,420)
  assert.deepEqual(a.history,b.history.rows);assert.deepEqual(a.current_stock,b.current_stock)
  assert.equal(a.history.reduce((n,r)=>n+r.days.length,0),12600)
  return{controlled_products:420,complete_days:12600,chunks:2,whole_history_full_JSON_equal:true,factory_SLA:false}
})
await test('OW10_INPUTS_CHANGED_PERIOD_SOURCE_UNKNOWN_CAPS_AND_ACL',async()=>{
  const source=fixture(),a=await invoke(source),q={...query,from_date:'2026-09-24'},changed=await invoke(source,q)
  assert.deepEqual(changed.history,(await whole(source,q)).history.rows);assert.notDeepEqual(changed.query,a.query)
  source.profiles[0].config.lead_days='4';assert.notEqual((await invoke(source)).source_hash,a.source_hash)
  await assert.rejects(()=>invoke({...source,status:'INCOMPLETE'}),/CP7_PLANNING_CAPTURE_INCOMPLETE/)
  await assert.rejects(()=>invoke(source,{...query,through_date:'2026-10-23'}),/CP7_DEMAND_COMPLETE_DAYS_REQUIRED/)
  await assert.rejects(()=>invoke(source,{...query,scope:'FILTERED_VARIANT'}),/CP7_WIP_FIELDS/)
  const tooMany=structuredClone(source);tooMany.facts.products=Array.from({length:1400},(_,i)=>product(i+1))
  await assert.rejects(()=>invoke(tooMany,{...query,from_date:'2025-10-23'}),/CP7_PLANNING_HISTORY_GRID_LIMIT/)
  for(const role of['anon','authenticated','service_role']){
    const r=(await db.query("select has_schema_privilege($1,'cp7_reorder_inputs','USAGE')s,has_function_privilege($1,'cp7_reorder_inputs.history(jsonb,jsonb)','EXECUTE')f",[role])).rows[0]
    assert.equal(r.s,false);assert.equal(r.f,false)
  }
  return{changed_query_and_profile_visible:true,incomplete_future_and_full_grid_refused:true,private_only:true}
})
const report={classification:'LOCAL_ACTUAL_NATIVE_HISTORY_AND_STAGED_TARGET_KERNELS_CONTROLLED_SOURCE_NOT_NATIVE_OR_LIVE_ROP',
  status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',passed:results.filter(x=>x.status==='PASS').length,total:results.length,
  sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/history.sql')).digest('hex'),results,
  ROP_caller_changed:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true})
await writeFile('docs/cp7/d17-14/ow10/local-reorder-inputs.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
