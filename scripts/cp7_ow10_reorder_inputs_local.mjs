// Actual frozen Native history + current target bodies on controlled DTOs.
// The independent comparison uses the whole existing history_build, rather
// than replaying this adapter's chunk orchestration. This is not Native/Auth.
import {readFile, writeFile, mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
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
 create role anon nologin;create role authenticated nologin;create role service_role nologin;create role cp7_alert nologin;
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
// Native history_source_within and baseline source bodies are loaded exactly.
// ERP tables contain controlled test facts; profile/identity adapters remain
// controlled. These local SQL checks do not claim a Native/Auth journey.
await db.exec(`create schema erp;create schema cp7_identity;create schema cp7_profile;create schema cp7_stock_formula;
 create table public.reorder_native_fixture(c jsonb);
 create function cp7_profile.source(uuid[],timestamptz)returns jsonb language sql stable as $$select c->'profiles'from public.reorder_native_fixture$$;
 create function cp7_identity.workspace_data(uuid[],timestamptz)returns jsonb language sql stable as $$select c->'production_policies'from public.reorder_native_fixture$$;
 create table erp.production_orders(id uuid,model_id uuid,status text);
 create table erp.products(id uuid primary key,identity_root_id uuid,size_id uuid default '00009000-1111-4111-8111-111111111111',
  model_id uuid default '00009001-1111-4111-8111-111111111111',brand_id uuid,sku text default 'CONTROLLED',
  product_name text default 'Controlled SQL product',is_active boolean default true,
  effective_from timestamptz default '2020-01-01T00:00:00Z',effective_to timestamptz,created_at timestamptz default '2020-01-01T00:00:00Z');
 create table erp.fg_stock_movements(id uuid primary key,product_id uuid,qty_signed numeric,physical_at timestamptz,
  system_created_at timestamptz,quality_grade text,movement_type text,reversal_of_id uuid,book_order bigint,
  lot_id uuid,location_id uuid,source_type text,source_id uuid);
 create table erp.bf_sku_members_v1(product_root uuid,version_id uuid);
 create table erp.bf_sku_versions_v1(id uuid,sku_id uuid,revision integer,effective_from timestamptz,effective_to timestamptz);
 create table erp.bf_skus_v1(id uuid,sku text);
 create table erp.sales_items(id uuid,sale_id uuid,product_id uuid,qty_pcs numeric);
 create table erp.sales_headers(id uuid,status text,row_version integer,sale_date timestamptz,created_at timestamptz,updated_at timestamptz);
 create table erp.journal_entries(id uuid,source_id uuid,source_type text,status text,posting_at timestamptz,
  transaction_date date,economic_date date,reversal_of_id uuid);
 create table erp.sales_return_items(id uuid,return_id uuid,sale_stock_allocation_id uuid,qty_pcs numeric);
 create table erp.sales_returns(id uuid,sale_id uuid,status text,physical_at timestamptz,created_at timestamptz);
 create table erp.sale_stock_allocations(id uuid,sale_item_id uuid);
 create table erp.cutting_groups(id uuid,po_id uuid,cut_at timestamptz,material_issue_posted boolean);
 create table erp.fg_lots(id uuid,cutting_group_id uuid,qc_item_id uuid,produced_at timestamptz,lot_origin text);
 create table erp.qc_inspection_items(id uuid,inspection_id uuid);
 create table erp.qc_inspections(id uuid,status text);`)
const formula=await read('scripts/cp7-src/stock-formula/formula.sql')
for(const table of['settings','manual_points']){
 const start=formula.indexOf('create table cp7_stock_formula.'+table+'(')
 await db.exec(formula.slice(start,formula.indexOf(');',start)+2))
}
await db.exec(block(formula,'cp7_stock_formula.current_settings'))
const nativeSourceSQL=block(await read('scripts/cp7-src/planning/history-source.sql'),'cp7_planning.history_source_within')
await db.exec(nativeSourceSQL)
await db.exec(block(await read('scripts/cp7-src/planning/baseline-source.sql'),'cp7_baseline_native.source_within'))
await db.exec(`grant usage on schema erp,cp7_identity,cp7_profile,cp7_stock_formula to cp7_capture;
 grant select on public.reorder_native_fixture to cp7_capture;grant select on all tables in schema erp,cp7_stock_formula to cp7_capture;`)
await db.exec(`grant usage on schema cp7_planning,cp7_analysis_stage,cp7_baseline_native,extensions,cp7_wip,cp7_demand,cp7_baseline to cp7_capture;`)
const manifest=JSON.parse(await read('scripts/cp7_reorder_inputs/MANIFEST.json'))
for(const signature of Object.keys(manifest.existing_body_sha256))await db.exec('alter function '+signature+' owner to cp7_capture')
const stageAudit=await beginLocalStageAudit(db,'cp7_reorder_inputs')
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
const defaults = {service_level:'0.95',window_days:'30'}
const lead = (days='3',groups='3') => [{model_id:id(9001),lead_days:days,lot_count:'5',group_count:groups}]
const points = async (input, measured=lead(), manual=[], policy=defaults) =>
  (await db.query('select cp7_reorder_inputs.points($1::jsonb,$2::jsonb,$3::jsonb,$4::jsonb)v',
    [JSON.stringify(input),JSON.stringify(policy),JSON.stringify(measured),JSON.stringify(manual)])).rows[0].v
const serverSource=async(bound=5000)=>(await db.query('select cp7_reorder_inputs.source_within($1)v',[bound])).rows[0].v
const readPoints=async(bound=5000)=>(await db.query('select cp7_reorder_inputs.read_points($1)v',[bound])).rows[0].v
const addMovement=async m=>db.query('insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,reversal_of_id,book_order)values($1,$2,$3,$4,$5,$6,$7,$8,$9)',
 [m.id,m.product_id,m.qty_signed,m.physical_at,m.system_created_at,m.quality_grade,m.movement_type,m.reversal_of_id,m.book_order])
const stockSummary=async(products=fixture().facts.products,at=clock,q=query)=>(await db.query(
 'select cp7_reorder_inputs.stock_summary($1::jsonb,$2::timestamptz,$3::jsonb)v',[JSON.stringify(products),at,JSON.stringify(q)])).rows[0].v
const sourceFixture=async()=>{
 await db.exec('truncate public.reorder_native_fixture,erp.production_orders,erp.products,erp.fg_stock_movements,erp.cutting_groups,erp.fg_lots,erp.qc_inspection_items,erp.qc_inspections,erp.sales_items,erp.sales_headers,erp.journal_entries,erp.sales_return_items,erp.sales_returns,erp.sale_stock_allocations,erp.bf_sku_members_v1,erp.bf_sku_versions_v1,erp.bf_skus_v1,cp7_stock_formula.settings,cp7_stock_formula.manual_points')
 await db.query('insert into public.reorder_native_fixture values($1::jsonb)',[JSON.stringify(fixture())])
 for(const p of fixture().facts.products)await db.query('insert into erp.products(id,identity_root_id,size_id,model_id,sku,product_name)values($1,$2,$3,$4,$5,$6)',[p.id,p.root_id,p.size_id,p.model_id,p.sku,p.product_name])
 for(const m of fixture().facts.stock)await addMovement(m)
 for(const s of fixture().facts.sales){
  await db.query('insert into erp.sales_items values($1,$2,$3,$4)',[s.id,s.sale_id,s.root_id,s.qty_pcs])
  await db.query('insert into erp.sales_headers values($1,$2,$3,$4,$5,$6)',[s.sale_id,s.status,s.revision,s.sale_date,s.created_at,s.updated_at])
 }
 for(const j of fixture().facts.sale_journals)await db.query('insert into erp.journal_entries values($1,$2,\'SALE\',$3,$4,$5,null,$6)',
  [j.id,j.sale_id,j.status,j.posting_at,j.transaction_date,j.reversal_of_id])
 await db.query('insert into erp.production_orders values($1,$2,\'FINISHED\')',[id(10001),id(9001)])
 for(const [n,cut]of[[1,'2026-10-01'],[2,'2026-10-02'],[3,'2026-10-03']])await db.query('insert into erp.cutting_groups values($1,$2,$3,true)',[id(11000+n),id(10001),cut+'T00:00:00Z'])
 let index=0
 for(const [group,at,status,origin]of[[1,'2026-10-04','POSTED','PRODUCTION'],[1,'2026-10-04','POSTED','PRODUCTION'],
   [2,'2026-10-06','POSTED','PRODUCTION'],[2,'2026-10-06','POSTED','PRODUCTION'],[3,'2026-10-08','POSTED','PRODUCTION'],
   [3,'2026-10-20','DRAFT','PRODUCTION'],[3,'2026-10-21','REVERSED','PRODUCTION'],[3,'2026-10-24','POSTED','PRODUCTION'],
   [3,'2026-10-22','POSTED','PURCHASE']]){
  ++index
  await db.query('insert into erp.qc_inspections values($1,$2)',[id(12000+index),status])
  await db.query('insert into erp.qc_inspection_items values($1,$2)',[id(13000+index),id(12000+index)])
  await db.query('insert into erp.fg_lots values($1,$2,$3,$4,$5)',[id(14000+index),id(11000+group),id(13000+index),at+'T00:00:00Z',origin])
 }
}
const results=[]
const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,3000)})}console.log(id+': '+results.at(-1).status)}
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
await test('OW10_POINTS_REVIEWED_PROFILE_EXACT_TARGET_AND_NO_DOUBLE_BUFFER',async()=>{
  const input=await invoke(fixture()),a=await points(input,lead('9'))
  for(const r of a.rows){
    assert.deepEqual(r.target,input.targets.find(t=>t.target_key===r.target_key).target)
    assert.equal(r.point_pcs,r.target.reorder_point_pcs);assert.equal(r.formula_point_pcs,r.point_pcs)
    assert.equal(r.lead_days,'3');assert.equal(r.lead_basis,'PROFILE');assert.equal(r.supply_alignment,'NATIVE_TARGET')
  }
  assert.deepEqual(a.rows.map(r=>r.point_pcs),['2','10','0'])
  await db.exec('set role cp7_capture');assert.deepEqual(await points(input,lead('9')),a);await db.exec('reset role')
  return{same_full_Native_target_JSON:true,reviewed_lead3_wins_over_measured9:true,
    profile_manual_mean_and_known_zero_respected:true,no_second_buffer:true,non_superuser:true}
})
await test('OW10_POINTS_UNREVIEWED_DEFAULTS_USE_NATIVE_AVAILABLE_HISTORY',async()=>{
  const source=fixture();source.profiles=source.profiles.map(p=>({...p,quality:'UNREVIEWED',profile_id:null,revision:'0',config:null}))
  const input=await invoke(source),a=await points(input),r=a.rows[0]
  assert.equal(r.source_kind,'NATIVE_HISTORY_WITH_EXISTING_DEFAULTS');assert.equal(r.available_days,'29')
  assert.equal(r.available_total_pcs,'10');assert.equal(r.lead_basis,'MEASURED')
  // Independent arithmetic: 10/29*3 +1.6449*(10/sqrt29)*sqrt3 =6.323..., ceil7.
  assert.equal(r.point_pcs,'7');assert.equal(r.target.inputs.review_days,'0')
  assert.equal(r.supply_alignment,'NEEDS_EXPLICIT_BINDING')
  assert.equal(a.rows[1].point_pcs,'0');assert.equal(a.rows[1].point_basis,'FORMULA')
  assert.equal(a.rows[2].point_pcs,null);assert.equal(a.rows[2].reason,'FEWER_THAN_14_NATIVE_AVAILABLE_DAYS')
  const missing=await points(input,[]);assert.equal(missing.rows[0].point_pcs,null);assert.equal(missing.rows[0].reason,'NO_PROVEN_LEAD_TIME')
  const measuredZero=await points(input,lead('0'));assert.equal(measuredZero.rows[0].point_pcs,'0')
  await assert.rejects(()=>points(input,lead('3','2')),/CP7_REORDER_LEAD_UNPROVEN/)
  return{exact_independent_point7_from29_Native_days:true,existing14_day95pct_rule_only:true,
    known_zero_not_unknown:true,default_only_not_claimed_full_production_target:true,insufficient_lead_never_guessed:true}
})
await test('OW10_POINTS_MANUAL_REPLACES_CLEARS_OR_REQUIRES_IDENTITY_REVIEW',async()=>{
  const input=await invoke(fixture()),manual={root_id:id(1),product_version_id:id(1),size_id:id(9000),revision:'1',reorder_point_pcs:'25'}
  const active=(await points(input,lead(),[manual])).rows[0]
  assert.equal(active.point_basis,'MANUAL');assert.equal(active.point_pcs,'25');assert.equal(active.formula_point_pcs,'2')
  assert.equal(active.target.target_pcs,'5');assert.equal(active.supply_alignment,'NEEDS_EXPLICIT_BINDING')
  const zero=(await points(input,lead(),[{...manual,reorder_point_pcs:'0'}])).rows[0];assert.equal(zero.point_pcs,'0');assert.equal(zero.manual_state,'ACTIVE')
  const cleared=(await points(input,lead(),[{...manual,reorder_point_pcs:null}])).rows[0]
  assert.equal(cleared.point_pcs,'2');assert.equal(cleared.manual_state,'CLEARED')
  const stale=(await points(input,lead(),[{...manual,product_version_id:id(999)}])).rows[0]
  assert.equal(stale.point_pcs,null);assert.equal(stale.reason,'MANUAL_POINT_VERSION_CHANGED');assert.equal(stale.manual_reference.reorder_point_pcs,'25')
  await assert.rejects(()=>points(input,lead(),[{...manual,reorder_point_pcs:'10000001'}]),/CP7_REORDER_MANUAL_RANGE/)
  return{manual25_replaces_formula2_without_changing_target5:true,manual_zero_and_clear_distinct:true,
    changed_product_version_does_not_silently_activate_formula:true,existing_manual_limit_retained:true}
})
await test('OW10_POINTS_POLICY_HASH_UNKNOWN_PROFILE_AND_CLOSED_SCOPE',async()=>{
  const input=await invoke(fixture()),a=await points(input)
  assert.notEqual((await points(input,lead('4'))).selection_hash,a.selection_hash)
  assert.notEqual((await points(input,lead(),[],{...defaults,service_level:'0.99'})).selection_hash,a.selection_hash)
  const oldProfile=structuredClone(input);oldProfile.targets[0].profile.quality='PHYSICAL_VERSION_CHANGED'
  const stale=(await points(oldProfile)).rows[0];assert.equal(stale.point_pcs,null);assert.equal(stale.reason,'PROFILE_IDENTITY_OR_VERSION_CHANGED')
  await assert.rejects(()=>points(input,lead(),[],{...defaults,window_days:'31'}),/CP7_REORDER_INPUT_PERIOD/)
  await assert.rejects(()=>points(input,lead(),[],{...defaults,service_level:'0.96'}),/CP7_REORDER_INPUT_POLICY/)
  const filtered=structuredClone(input);filtered.targets=filtered.targets.slice(0,1)
  await assert.rejects(()=>points(filtered),/CP7_REORDER_HISTORY_SCOPE_MISMATCH/)
  const mismatched=structuredClone(input);mismatched.targets[0].profile.product_version_id=id(999)
  await assert.rejects(()=>points(mismatched),/CP7_REORDER_TARGET_PRODUCT_BINDING/)
  for(const role of['anon','authenticated','service_role'])assert.equal((await db.query("select has_function_privilege($1,'cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)','EXECUTE')f",[role])).rows[0].f,false)
  return{lead_and_defaults_in_selection_hash:true,stale_profile_unknown:true,closed_policy_period_identity_and_full_scope:true,private_only:true}
})
await test('OW10_SOURCE_ACTUAL_SQL_LEAD_SETTINGS_AND_NATIVE_CAPTURE_CLOCK',async()=>{
 await sourceFixture();const r=await serverSource()
 assert.equal(r.status,'COMPLETE');assert.equal(r.captured_at,r.native.captured_at);assert.deepEqual(r.query,query);assert.deepEqual(r.defaults,defaults)
 assert.deepEqual(r.leads,[{model_id:id(9001),lead_days:'4.00',lot_count:'5',group_count:'3'}])
 assert.deepEqual(r.manuals,[]);assert.equal(r.native.facts.products.length,3);assert.equal(r.native.facts.stock.length,5)
 assert.equal(r.native.facts.sales[0].qty_pcs,'10');assert.equal(r.native.facts.sale_journals[0].id,id(202))
 const compiled=await points(await invoke(r.native,r.query),r.leads,r.manuals,r.defaults)
 assert.equal(compiled.rows[0].lead_days,'3');assert.equal(compiled.rows[0].point_pcs,'2')
 await db.exec('set role cp7_capture');const again=await serverSource();await db.exec('reset role')
 assert.equal(again.context_hash,r.context_hash);assert.deepEqual(again.native.facts,r.native.facts)
 return{actual_Native_baseline_and_history_source_bodies:true,profile_and_identity_adapters_controlled:true,
  actual_SQL_median4_from5_lots3_groups:true,draft_reversed_future_and_nonproduction_lots_excluded:true,
  current_settings_defaults_actual_SQL:true,same_capture_clock_and_read_only_capture_role:true}
})
await test('OW10_SOURCE_LATEST_MANUAL_AS_OF_CAPTURE_AND_PROVEN_LEAD_GUARD',async()=>{
 await sourceFixture()
 for(const [revision,point,at]of[[1,'0','2026-10-21'],[2,'25','2026-10-22'],[3,'99','2026-10-24']])await db.query(`
  insert into cp7_stock_formula.manual_points(root_id,revision,size_id,product_version_id,reorder_point_pcs,reason,actor,request_id,request_hash,recorded_at)
  values($1,$2,$3,$1,$4,'CONTROLLED_FIXTURE',$5,$6,$7,$8)`,[id(1),revision,id(9000),point,id(999),id(15000+revision),'a'.repeat(64),at+'T00:00:00Z'])
 const r=await serverSource();assert.deepEqual(r.manuals,[{root_id:id(1),product_version_id:id(1),size_id:id(9000),revision:'2',reorder_point_pcs:'25'}])
 const p=await points(await invoke(r.native),r.leads,r.manuals,r.defaults);assert.equal(p.rows[0].point_pcs,'25')
 await db.query('update erp.cutting_groups set material_issue_posted=false where id=$1',[id(11003)])
 const two=await serverSource();assert.equal(two.leads[0].group_count,'2');assert.equal(two.leads[0].lead_days,null)
 assert.notEqual(two.context_hash,r.context_hash)
 return{latest_revision_at_Native_capture_only:true,future_manual_not_active:true,manual25_from_server_only:true,
  fewer_than3_issued_groups_not_proven_lead:true,source_change_changes_context_hash:true}
})
await test('OW10_SOURCE_CLOSED_CAP_INCOMPLETE_AND_ENGINE_CURRENTNESS',async()=>{
 await sourceFixture();const r=await serverSource();assert.match(r.engine_hash,/^[a-f0-9]{64}$/);assert.match(r.context_hash,/^[a-f0-9]{64}$/)
 assert.equal((await serverSource(1)).status,'INCOMPLETE')
 await assert.rejects(()=>serverSource(0),/CP7_REORDER_SOURCE_PRODUCT_BOUND/)
 await assert.rejects(()=>serverSource(5001),/CP7_REORDER_SOURCE_PRODUCT_BOUND/)
 const sql=await read('scripts/cp7_reorder_inputs/points.sql')
 await db.exec(sql.replace('create function ','create or replace function ').replaceAll('CP7_REORDER_INPUT_POLICY','CP7_REORDER_INPUT_POLICY_CONTROL'))
 const changed=await serverSource();assert.notEqual(changed.engine_hash,r.engine_hash);assert.notEqual(changed.context_hash,r.context_hash)
 await db.exec(sql.replace('create function ','create or replace function '));assert.equal((await serverSource()).context_hash,r.context_hash)
 return{existing5000_product_bound_not_raised:true,incomplete_source_not_empty_success:true,
  actual_catalog_code_in_engine_and_context_hash:true,exact_private_body_restored:true}
})
await test('OW10_READ_COMPLETE_NATIVE_FULL_INPUTS_AND_POINTS_EQUAL',async()=>{
 await sourceFixture();const r=await readPoints(),source=await serverSource();source.native.captured_at=r.captured_at
 const native=await invoke(source.native,r.query)
 assert.deepEqual(r.inputs,native)
 assert.deepEqual(r.points,await points(native,source.leads,source.manuals,source.defaults))
 assert.equal(r.native_capture_status,'COMPLETE');assert.equal(r.input_path,'COMPLETE_NATIVE_CAPTURE')
 await db.exec('set role cp7_capture');const again=await readPoints();await db.exec('reset role')
 assert.equal(again.context_hash,r.context_hash);assert.equal(again.points.selection_hash,r.points.selection_hash)
 await db.query('update erp.fg_stock_movements set qty_signed=qty_signed+1 where id=$1',[id(100)])
 assert.notEqual((await readPoints()).context_hash,r.context_hash)
 await assert.rejects(()=>readPoints(1),/CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE/)
 return{actual_history_source_and_baseline_source:true,full_input_and_point_JSON_equal:true,
  read_only_capture_role:true,clock_only_change_same_cache_key:true,visible_stock_change_new_key:true,
  incomplete_product_universe_refused:true}
})
await test('OW10_COMPILE_ONE_CLOSED_SNAPSHOT_NO_SECOND_DATABASE_READ',async()=>{
 await sourceFixture();const source=await serverSource()
 const compile=async s=>(await db.query('select cp7_reorder_inputs.compile($1::jsonb)v',[JSON.stringify(s)])).rows[0].v
 const original=await compile(source)
 await addMovement(movement(730,1,'3','2026-10-22T00:00:00Z'))
 assert.deepEqual(await compile(source),original)
 const fresh=await serverSource();assert.notEqual(fresh.context_hash,source.context_hash)
 assert.notEqual((await compile(fresh)).context_hash,original.context_hash)
 await assert.rejects(()=>compile({...source,client_values:{}}),/CP7_/)
 await assert.rejects(()=>compile({...source,captured_at:'2026-10-22T00:00:00Z'}),/CP7_REORDER_SOURCE_SNAPSHOT_BINDING/)
 return{exact_same_snapshot_same_full_result_after_DB_change:true,fresh_snapshot_changes_key:true,
  no_second_source_read_in_immutable_compile:true,closed_snapshot_and_clock_binding:true,
  cache_key_not_freshness_proof:true}
})
await test('OW10_READ_OVERFLOW_RETAINS_ALL_OTHER_NATIVE_COMPLETENESS_GUARDS',async()=>{
 await sourceFixture()
 // Explicit fault injection into the lower source, not a Native qualification:
 // compact stock is never allowed to excuse a second missing collection or
 // an identity/journal conflict. Restore the pinned real body in finally.
 const injected=fixture();injected.status='INCOMPLETE';injected.facts.stock=Array(50001).fill({})
 const controlledSource=`create or replace function cp7_planning.history_source_within(p_products integer)returns jsonb
  language sql stable security invoker set search_path=''set TimeZone='UTC'as $$select c from public.reorder_native_fixture$$;`
 const denied=[]
 await db.exec(controlledSource)
 try{
  const reject=async(name,change,pattern=/CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE/)=>{
   const c=structuredClone(injected);change(c)
   await db.query('update public.reorder_native_fixture set c=$1::jsonb',[JSON.stringify(c)])
   await assert.rejects(()=>readPoints(),pattern);denied.push(name)
  }
  await reject('SQL stock has fewer rows than raw capture',()=>{},/CP7_REORDER_STOCK_SNAPSHOT_MISMATCH/)
  for(const name of['sales','sale_journals','returns','return_journals'])await reject(name+' overflow',c=>{c.facts[name]=Array(50001).fill({})})
  await reject('duplicate current root',c=>{c.facts.products.push(c.facts.products[0])})
  await reject('ambiguous current commercial',c=>{c.facts.products[0].commercial=[{},{}]})
  await reject('ambiguous sold commercial',c=>{c.facts.sales[0].sold_commercial=[{},{}]})
  await reject('missing posted original journal',c=>{c.facts.sale_journals=[]})
  await reject('duplicate original journal',c=>{c.facts.sale_journals.push({...c.facts.sale_journals[0],id:id(90002)})})
  await reject('unknown Native status',c=>{c.status='UNKNOWN'})
 }finally{
  await db.exec(nativeSourceSQL.replace('create function ','create or replace function '))
  await db.query('update public.reorder_native_fixture set c=$1::jsonb',[JSON.stringify(fixture())])
 }
 const body=(await db.query("select prosrc from pg_proc where oid='cp7_planning.history_source_within(integer)'::regprocedure")).rows[0].prosrc
 assert.equal(createHash('sha256').update(body).digest('hex'),manifest.existing_body_sha256['cp7_planning.history_source_within(integer)'])
 return{fault_injected_denials:denied,Native_body_exactly_restored:true,Native_qualification:false}
})
let installer
await test('OW10_INPUTS_REAL_INSTALLER_22_AND_CALLER_DEPENDENCY_REFUSAL',async()=>{
  // Actual SQL caller declaration, controlled fixture; no Native transaction
  // or persisted ERP use is claimed for this stateless helper's boundary.
  await db.exec(`create function cp7_analysis_stage.local_reorder_inputs_consumer(jsonb,jsonb)returns jsonb
    language sql immutable as $$select cp7_reorder_inputs.history($1,$2)$$;
    alter function cp7_analysis_stage.local_reorder_inputs_consumer(jsonb,jsonb)owner to cp7_capture;`)
  installer=await stageAudit.afterUse()
  assert.equal(installer.catalog_groups,22);assert.equal(installer.apply_rollback_reapply_exact,true)
  assert.equal(installer.after_use_refused_before_first_DDL,true)
  return{apply_admit_inverse_reapply_all22_exact:true,actual_installed_SQL_caller_requires_removal_first:true,
    caller_guard_before_DDL:true,persisted_Native_use_qualified:false}
})
await test('OW10_STOCK_SUMMARY_FULL_NATIVE_AVAILABILITY_AND_BOTH_CLOCKS',async()=>{
 await sourceFixture();const r=await stockSummary(),source={...fixture(),captured_at:r.captured_at}
 const expected=(await db.query('select cp7_planning.history_availability($1::jsonb,$2::jsonb)v',[JSON.stringify(source),JSON.stringify(query)])).rows[0].v
 assert.deepEqual(r.availability,expected);assert.equal(r.raw_rows_read,5)
 const current=(await whole(source)).current_stock
 for(const row of r.current_stock){const native=current.find(x=>x.target_key===row.target_key)
  assert.equal(row.free_pcs,native.native_available_pcs);assert.equal(row.physical_pcs,native.availability.inputs.fg_pcs)
 }
 for(const m of[{...movement(700,1,'999','2026-10-24T00:00:00Z'),system_created_at:'2026-10-22T00:00:00Z'},
   {...movement(701,1,'999','2026-10-22T00:00:00Z'),system_created_at:'2026-10-24T00:00:00Z'}])await addMovement(m)
 assert.deepEqual(await stockSummary(),r)
 await db.exec('set role cp7_capture');assert.deepEqual(await stockSummary(),r);await db.exec('reset role')
 return{complete_actual_Native_availability_JSON_equal:true,current_free_and_physical_same:true,
  future_physical_and_later_known_rows_both_excluded:true,non_superuser_read:true,canonical_Native_clock:true}
})
await test('OW10_STOCK_SUMMARY_RESERVATION_INVERSE_AND_INTRADAY_UNKNOWN',async()=>{
 await sourceFixture();const source=fixture()
 const reserve={...movement(710,1,'-4','2026-10-20T03:00:00Z'),movement_type:'SALE_RESERVE'}
 await addMovement(reserve);source.facts.stock.push(reserve)
 source.facts.sales.push({id:id(711),sale_id:id(712),root_id:id(1),size_id:id(9000),qty_pcs:'4',status:'DRAFT',revision:'1',
  sale_date:'2026-10-20T03:00:00Z',created_at:'2026-10-20T03:00:00Z',updated_at:'2026-10-20T03:00:00Z',sold_commercial:[]})
 let r=await stockSummary();source.captured_at=r.captured_at
 let native=await whole(source);assert.equal(r.current_stock[0].free_pcs,'86');assert.equal(r.current_stock[0].physical_pcs,'90')
 assert.equal(native.current_stock[0].native_available_pcs,'86')
 const inverse={...movement(713,1,'4','2026-10-21T03:00:00Z'),reversal_of_id:reserve.id}
 await addMovement(inverse);source.facts.stock.push(inverse);source.facts.sales.at(-1).status='CANCELLED'
 r=await stockSummary();native=await whole(source);assert.equal(r.current_stock[0].physical_pcs,'90');assert.equal(native.current_stock[0].native_available_pcs,'90')
 for(const m of[movement(714,1,'-100','2026-10-18T01:00:00Z',1),movement(715,1,'100','2026-10-18T02:00:00Z',2)]){
  await addMovement(m);source.facts.stock.push(m)
 }
 r=await stockSummary();assert.deepEqual(r.availability,(await db.query('select cp7_planning.history_availability($1::jsonb,$2::jsonb)v',
  [JSON.stringify(source),JSON.stringify(query)])).rows[0].v)
 assert.equal(r.availability.find(x=>x.target_key.startsWith(id(1))&&x.date==='2026-10-18').state,'UNKNOWN')
 return{reservation_subtracted_once_inverse_excluded_from_physical:true,
  negative_intraday_state_UNKNOWN_never_zero:true,full_Native_availability_JSON_equal:true}
})
await test('OW10_STOCK_SUMMARY_202000_ROWS_2000_PRODUCTS_NO_TRUNCATION',async()=>{
 await db.exec('truncate erp.products,erp.fg_stock_movements')
 const products=Array.from({length:2000},(_,i)=>product(i+1))
 await db.query('insert into erp.products(id,identity_root_id)select (p->>\'id\')::uuid,(p->>\'root_id\')::uuid from jsonb_array_elements($1::jsonb)p',[JSON.stringify(products)])
 await db.exec(`insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,reversal_of_id,book_order)
  select md5('opening'||p.id::text)::uuid,p.id,800,'2026-06-15T00:00:00Z','2026-06-15T00:00:00Z','GRADE_A','OPENING',null,1 from erp.products p;
  insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,reversal_of_id,book_order)
  select md5(p.id::text||':'||g::text)::uuid,p.id,-(1+g%6),'2026-10-23T00:00:00Z'::timestamptz-g*interval'1 day'-interval'2 hours',
   '2026-10-22T00:00:00Z','GRADE_A','SALE',null,g+1 from erp.products p cross join generate_series(1,100)g;`)
 const t=performance.now(),r=await stockSummary(products),ms=Math.round(performance.now()-t)
 assert.equal(r.raw_rows_read,202000);assert.equal(r.current_stock.length,2000);assert.equal(r.availability.length,60000)
 assert.ok(r.availability.every(x=>x.state==='AVAILABLE'))
 const free=String(800-Array.from({length:100},(_,i)=>1+(i+1)%6).reduce((a,b)=>a+b,0))
 assert.ok(r.current_stock.every(x=>x.free_pcs===free&&x.physical_pcs===free))
 assert.equal(r.raw_rows_truncated,false);assert.equal(r.Native_capture_status_overridden,false)
 return{controlled_SQL_rows:202000,products:2000,complete_days:60000,all_free_pcs:free,
  local_SQL_ms:ms,no_source_row_sampled:true,Native_Auth_or_factory_SLA:false}
})
await test('OW10_READ_202000_SQL_ROWS_FULL_NATIVE_HISTORY_TARGETS_AND_POINTS',async()=>{
 // Reuse the complete 202000-row SQL fixture above. These products have a
 // genuinely old test created_at, so Native knowledge covers the whole grid.
 await db.exec('truncate erp.sales_items,erp.sales_headers,erp.journal_entries')
 const source=fixture();source.profiles=Array.from({length:2000},(_,i)=>profile(i+1,'0'))
 await db.query('update public.reorder_native_fixture set c=$1::jsonb',[JSON.stringify(source)])
 const raw=await serverSource();assert.equal(raw.status,'INCOMPLETE');assert.equal(raw.native.facts.stock.length,50001)
 const t=performance.now(),r=await readPoints(),ms=Math.round(performance.now()-t)
 assert.equal(r.native_capture_status,'INCOMPLETE');assert.equal(r.input_path,'COMPLETE_SQL_STOCK_SUMMARY_RAW_NATIVE_INCOMPLETE')
 assert.equal(r.complete_stock_raw_rows_read,202000);assert.equal(r.inputs.history.length,2000)
 assert.equal(r.inputs.targets.length,2000);assert.equal(r.inputs.current_stock.length,2000);assert.equal(r.points.rows.length,2000)
 assert.ok(r.inputs.history.every(x=>x.available_days===30&&x.days.length===30&&x.gross_observed_pcs==='0'))
 assert.ok(r.inputs.current_stock.every(x=>x.native_available_pcs==='450'))
 assert.ok(r.inputs.targets.every(x=>x.target.reorder_point_pcs==='0'&&x.target.target_pcs==='0'))
 assert.ok(r.points.rows.every(x=>x.point_pcs==='0'&&x.available_days==='30'&&x.lead_basis==='PROFILE'))
 assert.notEqual(r.inputs.source_hash,raw.context_hash)
 const outside=(await db.query('select id from erp.fg_stock_movements order by id desc limit 1')).rows[0].id
 assert.ok(!raw.native.facts.stock.some(m=>m.id===outside))
 await db.query('update erp.fg_stock_movements set qty_signed=qty_signed+1 where id=$1',[outside])
 const changed=await serverSource();assert.deepEqual(changed.native.facts.stock,raw.native.facts.stock)
 assert.notEqual(changed.stock_summary.data_hash,raw.stock_summary.data_hash);assert.notEqual(changed.context_hash,raw.context_hash)
 const wrong=structuredClone(raw);wrong.stock_summary.captured_at='2026-10-22T00:00:00Z'
 await assert.rejects(()=>db.query('select cp7_reorder_inputs.compile($1::jsonb)',[JSON.stringify(wrong)]),/CP7_REORDER_STOCK_SNAPSHOT_MISMATCH/)
 return{actual_Native_source_cap_still50001:true,Native_status_still_INCOMPLETE:true,SQL_rows:202000,
  full_targets:2000,full_history_days:60000,full_points:2000,free450_exact:true,known_zero_profile_not_unknown:true,
  local_full_pipeline_ms:ms,outside_raw_prefix_change_invalidates_context:true,summary_clock_binding_refused:true,
  Native_Auth_or_factory_SLA:false,live_ROP_caller_changed:false}
})
await test('OW10_STOCK_SUMMARY_SCOPE_REFUSED_AND_DATA_HASH_EXCLUDES_ONLY_CLOCK',async()=>{
 await sourceFixture();const a=await stockSummary(),b=await stockSummary(fixture().facts.products,'2026-10-23T00:01:00Z')
 assert.notEqual(a.captured_at,b.captured_at);assert.equal(a.data_hash,b.data_hash)
 await addMovement(movement(720,1,'3','2026-10-22T00:00:00Z'))
 assert.notEqual((await stockSummary()).data_hash,a.data_hash)
 await assert.rejects(()=>stockSummary(fixture().facts.products,clock,{...query,through_date:'2026-10-23'}),/CP7_REORDER_STOCK_SCOPE_BOUND/)
 await assert.rejects(()=>stockSummary(Array.from({length:1400},(_,i)=>product(i+1)),clock,{...query,from_date:'2025-10-23'}),/CP7_REORDER_STOCK_SCOPE_BOUND/)
 return{clock_only_change_not_data_change:true,actual_visible_stock_change_changes_hash:true,
  existing_grid_and_closed_day_caps_preserved:true,not_a_complete_Native_capture_claim:true}
})
const report={classification:'LOCAL_ACTUAL_NATIVE_HISTORY_AND_STAGED_TARGET_KERNELS_CONTROLLED_SOURCE_NOT_NATIVE_OR_LIVE_ROP',
  status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',passed:results.filter(x=>x.status==='PASS').length,total:results.length,
  sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/history.sql')).digest('hex'),
  points_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/points.sql')).digest('hex'),results,
  source_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/source.sql')).digest('hex'),
  stock_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/stock.sql')).digest('hex'),
  read_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/read.sql')).digest('hex'),
  installer,
  ROP_caller_changed:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true})
await writeFile('docs/cp7/d17-14/ow10/local-reorder-inputs.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
