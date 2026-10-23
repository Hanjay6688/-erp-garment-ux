// Shared controlled ERP fixture; actual Native source/history/target bodies.
// Actual frozen Native history + current target bodies on controlled DTOs.
// The independent comparison uses the whole existing history_build, rather
// than replaying this adapter's chunk orchestration. This is not Native/Auth.
import {readFile, writeFile, mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'

export async function createNativeReorderFixture(){
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
// Reorder is composed above production18, not the frozen predecessor alone.
// Use its actual history-prep body in both the adapter and independent whole
// history comparison. The installer still requires its one exact body hash.
await db.exec(await read('scripts/cp7_production_stage/sql/cp7_analysis_stage__history_prep.sql'))
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
const readerSnapshot=async()=>(await db.query(`with s as materialized(select cp7_reorder_inputs.source_within(5000)v)
 select cp7_reorder_reader.snapshot(s.v)v from s`)).rows[0].v
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
return {db,stageAudit,id,clock,query,product,profile,movement,fixture,invoke,whole,defaults,lead,points,serverSource,readPoints,readerSnapshot,addMovement,stockSummary,sourceFixture,block,read,formula,nativeSourceSQL,manifest}
}
