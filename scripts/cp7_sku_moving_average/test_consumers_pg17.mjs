// Execute exact candidate consumer SQL against synthetic rows and explicit
// provider models. This is an early regression gate, never ERP Native credit.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {runCreditControls} from './test_credit_projection_pg17.mjs';
const {PGlite} = await import(process.env.CP7_PGLITE_MODULE);
const here = dirname(fileURLToPath(import.meta.url));
const input = JSON.parse(await readFile(process.env.CP7_CONSUMER_MODEL_INPUT, 'utf8'));
assert.equal(input.classification, 'MODELED_EXACT_CONSUMER_SQL_NOT_NATIVE_ERP');
const ddl = await readFile(join(here, 'valuation.sql'), 'utf8');
const db = new PGlite(), results = [], fractionalObservations = [];
const id = n => '73000000-0000-4000-8000-' + String(n).padStart(12, '0');
const x = Object.fromEntries(['source','target','outside','location','otherLocation','root10','root30',
 'root50','converted','root90','group','conversion','allocation','hpp10','hpp30','hpp50','hppConverted','hpp90',
 'sale','saleItem','saleA','saleB','returned','returnItem','po'].map((n,i)=>[n,id(i+1)]));
const q = s => '"' + s.replaceAll('"','""') + '"';
const scalar = async (sql, args=[]) => Object.values((await db.query(sql,args)).rows[0])[0];
const query = (sql,args=[]) => db.query(sql,args);
async function insert(table, row) {
 await query('insert into '+table+'('+Object.keys(row).map(q).join(',')+')values('
  +Object.keys(row).map((_,i)=>'$'+(i+1)).join(',')+')',Object.values(row));
}
const control = async (label, operation) => {
 console.log(JSON.stringify({control:label,state:'ENTER'}));
 await db.exec('begin');
 try { await operation(); results.push({label,result:'PASS'}); console.log(JSON.stringify({control:label,state:'PASS'})); }
 finally { await db.exec('rollback'); }
};
async function movement(lot,product,quantity,type='OPENING',unit=0) {
 await insert('erp.fg_stock_movements',{id:id(++serial),lot_id:lot,product_id:product,location_id:x.location,
  quality_grade:'GRADE_A',qty_signed:quantity,movement_type:type,unit_hpp_snapshot:unit,
  physical_at:'2026-01-01T00:00:00Z',system_created_at:'2026-01-01T00:00:00Z'});
}
async function values(product) {
 const row=(await query('select hpp_total_cost::text hpp,fg_value::text fg,cogs_value::text cogs,other_out_value::text other from erp.compute_non_po_product_hpp_targets_v2620f($1)',[product])).rows[0];
 return Object.fromEntries(Object.entries(row).map(([k,v])=>[k,Number(v)]));
}
async function saleSetup(product=x.target, lots=[x.root50,x.converted], quantities=[1,1]) {
 await insert('erp.sales_headers',{id:x.sale,status:'DRAFT',sale_date:'2026-01-02T00:00:00Z'});
 await insert('erp.sales_items',{id:x.saleItem,sale_id:x.sale,product_id:product});
 for(let i=0;i<lots.length;i++)await insert('erp.sale_stock_allocations',{id:i?x.saleB:x.saleA,
  sale_item_id:x.saleItem,lot_id:lots[i],location_id:x.location,qty_pcs:quantities[i]});
}
async function postSaleModel() {
 await query('select cp7_sku_conversion.prepare_sale_values_v2($1)',[x.sale]);
 // Native post_sale checks source/book after preparation, before changing
 // DRAFT reservations into posted movements. Pending components have no value.
 await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[x.target]);
 for(const [lot,quantity] of (await query('select lot_id,qty_pcs from erp.sale_stock_allocations where sale_item_id=$1',[x.saleItem])).rows.map(r=>[r.lot_id,r.qty_pcs]))
  await movement(lot,x.target,-quantity,'SALE_OUT');
 await query("update erp.sales_headers set status='POSTED'where id=$1",[x.sale]);
 await query('update public.model_book set fg=0,cogs=70 where product_id=$1',[x.target]);
}
async function returnSetup() {
 await insert('erp.sales_returns',{id:x.returned,status:'DRAFT',physical_at:'2026-01-03T00:00:00Z'});
 await insert('erp.sales_return_items',{id:x.returnItem,return_id:x.returned,sale_stock_allocation_id:x.saleA,
  product_id:x.target,lot_id:x.root50,location_id:x.location,quality_grade:'GRADE_A',qty_pcs:1});
}
async function fractionalSale() {
 await query('update erp.hpp_versions set total_cost=10 where id=$1',[x.hpp90]);
 await query("update erp.fg_stock_movements set unit_hpp_snapshot=10::numeric/3 where lot_id=$1 and movement_type='OPENING'",[x.root90]);
 await query('update public.model_book set fg=10,cogs=0,other_value=0 where product_id=$1',[x.outside]);
 await insert('erp.sales_headers',{id:x.sale,status:'DRAFT',sale_date:'2026-01-02T00:00:00Z',source_location_id:x.location,customer_id:id(900)});
 for(const [item,allocation,quantity]of[[x.saleItem,x.saleA,1],[id(700),x.saleB,2]]) {
  await insert('erp.sales_items',{id:item,sale_id:x.sale,product_id:x.outside,qty_pcs:quantity,unit_price_snapshot:185000,discount_amount:0});
  await insert('erp.sale_stock_allocations',{id:allocation,sale_item_id:item,lot_id:x.root90,location_id:x.location,qty_pcs:quantity});
  await insert('erp.fg_stock_movements',{id:id(++serial),lot_id:x.root90,product_id:x.outside,
   location_id:x.location,quality_grade:'GRADE_A',qty_signed:-quantity,movement_type:'SALE_RESERVE',
   customer_id:id(900),source_type:'SALE_ITEM',source_id:item,
   physical_at:'2026-01-02T00:00:00Z',system_created_at:'2026-01-02T00:00:00Z'});
 }
 await query('select erp.post_sale($1)',[x.sale]);
 assert.equal(Number(await scalar('select effective_value from cp7_sku_conversion.sale_allocation_values_v2 where sale_stock_allocation_id=$1',[x.saleB])),6.67);
 await query('update erp.fg_lots set cached_qty_pcs=0,produced_at=$1 where id=$2',['2026-01-01T00:00:00Z',x.root90]);
}
async function fractionalReturn(label, sequence, allocations, destination=x.location) {
 const returned=id(2000+sequence);
 await insert('erp.sales_returns',{id:returned,sale_id:x.sale,customer_id:id(900),status:'DRAFT',physical_at:'2026-01-03T00:00:00Z'});
 for(let i=0;i<allocations.length;i++) {
  const [allocation,quantity]=allocations[i];
  await insert('erp.sales_return_items',{id:id(3000+sequence*10+i),return_id:returned,sale_stock_allocation_id:allocation,
   product_id:x.outside,lot_id:x.root90,location_id:destination,quality_grade:'GRADE_A',qty_pcs:quantity,refund_amount:185000*quantity});
 }
 await query('select erp.post_sales_return($1)',[returned]);
 const amounts=(await query('select effective_value::text value from cp7_sku_conversion.sales_return_values_v2 where return_id=$1 order by sales_return_item_id',[returned])).rows.map(r=>Number(r.value));
 const target=await values(x.outside),book=(await query('select fg::text,cogs::text from public.model_book where product_id=$1',[x.outside])).rows[0];
 const journal=await scalar("select lines from public.model_journal where source_type='SALES_RETURN'and source_id=$1",[returned]);
 const inventory=journal.filter(r=>r.mapping_key==='FG_INVENTORY').reduce((sum,r)=>sum+r.debit-r.credit,0);
 const snapshot=Number(await scalar('select sum(effective_value)::text from cp7_sku_conversion.sales_return_values_v2 where return_id=$1',[returned]));
 assert.equal(snapshot,inventory,'Return snapshots must equal the exact Native FG journal delta');
 await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[x.outside]);
 const observed={label,returned,amounts,snapshot,target,book,journal};fractionalObservations.push(observed);return observed;
}
let engine,serial=1000;
try {
 engine=await scalar('select version()');assert.match(engine,/^PostgreSQL 17\./);
 await db.exec("create schema erp;create schema cp7_sku_conversion;create role anon;create role authenticated;create role service_role;set check_function_bodies=off;set search_path='';");
 for(const[table,columns]of Object.entries(input.columns)) {
  const primary=table==='cp7_sku_conversion.groups_v1'?'request_id':table==='erp.opening_lot_hpp_gl_state'?'lot_id':'id';
  await db.exec('create table '+table+'('+columns.map(c=>q(c[0])+' '+c[2]
   +(c[5]==='s'?' generated always as ('+c[13]+') stored':c[0]==='id'&&c[2]==='uuid'?' default gen_random_uuid()':'')
   +(c[0]===primary&&c[2]==='uuid'?' primary key':'')).join(',')+')');
  const actual=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
  assert.deepEqual(actual,Object.fromEntries(columns.map(c=>[c[0],c[2]])));
 }
 await db.exec(`create table public.model_book(product_id uuid primary key,fg numeric,cogs numeric,other_value numeric);
 create table public.model_journal(id uuid,source_type text,source_id uuid,effective_date date,lines jsonb);
 create function erp.require_internal()returns void language plpgsql as $$begin return;end$$;
 create function erp.require_owner_admin()returns void language plpgsql as $$begin return;end$$;
 create function erp.require_permission(text)returns void language plpgsql as $$begin return;end$$;
 create function erp.bd_assert_sale_laundry_known_v1(uuid)returns void language plpgsql as $$begin return;end$$;
 create function erp.lock_current_hpp_per_pcs(uuid)returns numeric language sql stable as $$select hpp_per_pcs from erp.hpp_versions where lot_id=$1 and is_current$$;
 create function erp.current_app_user_id()returns uuid language sql as $$select '${id(900)}'::uuid$$;
 create function erp.bd_lot_laundry_unknown_v1(uuid)returns boolean language sql stable as $$select false$$;
 create function erp.get_hpp_completeness(uuid)returns table(pending_reason_count integer)language sql stable as $$select 0$$;
 create function erp.be_nonpo_admitted_v1(uuid)returns boolean language sql stable as $$select true$$;
 create function erp.be_nonpo_in_sync_v1()returns boolean language sql stable as $$select true$$;
 create function erp.be_po_extra_v1(uuid)returns numeric language sql stable as $$select 0::numeric$$;
 create function cp7_sku_conversion.immutable_v1()returns trigger language plpgsql as $$begin raise exception 'MODEL_IMMUTABLE';end$$;
 create function erp.compute_non_po_product_hpp_book_v2620f(uuid)
 returns table(hpp_total_cost numeric,fg_value numeric,cogs_value numeric,other_out_value numeric)
 language sql stable as $$select fg+cogs+other_value,fg,cogs,other_value from public.model_book where product_id=$1$$;
 create function erp.post_journal(p_type text,p_id uuid,p_date date,p_reason text,p_lines jsonb)returns uuid language plpgsql as $$
 declare entry jsonb;amount numeric;jid uuid:=gen_random_uuid();begin
 if(select sum((e->>'debit')::numeric-(e->>'credit')::numeric)from jsonb_array_elements(p_lines)e)<>0 then raise exception 'MODEL_JOURNAL_UNBALANCED';end if;
 for entry in select *from jsonb_array_elements(p_lines)loop
  amount:=(entry->>'debit')::numeric-(entry->>'credit')::numeric;
  if entry->>'mapping_key'='FG_INVENTORY'then update public.model_book set fg=fg+amount where product_id=(entry->>'product_id')::uuid;
  elsif entry->>'mapping_key'='COGS'then update public.model_book set cogs=cogs+amount where product_id=(entry->>'product_id')::uuid;
  elsif entry->>'mapping_key'in('OTHER_EXPENSE','OTHER_INCOME')then update public.model_book set other_value=other_value+amount where product_id=(entry->>'product_id')::uuid;
  elsif entry->>'mapping_key'not in('OPENING_EQUITY','AR_CUSTOMER','SALES_REVENUE')then raise exception 'MODEL_UNEXPECTED_ACCOUNT';end if;
 end loop;
 insert into public.model_journal values(jid,p_type,p_id,p_date,p_lines);return jid;end$$;
 create view erp.v_current_hpp as select id hpp_version_id,lot_id,hpp_per_pcs from erp.hpp_versions where is_current;
 `);
 await db.exec(ddl);
 await db.exec(input.inventory_unique);
 for(const definition of input.transaction_uniques)await db.exec(definition);
 for(const definition of Object.values(input.native_return_helpers))await db.exec(definition);
 // Credit policy and journal storage remain explicit model providers. The
 // Native return, movement and cumulative HPP/journal calculations are exact.
 await db.exec(`create schema cp7_credit;
 create function cp7_credit.native_return_enter(uuid)returns void language plpgsql as $$begin return;end$$;
 create function cp7_credit.native_return_guard(uuid,numeric,numeric,numeric)returns numeric language sql as $$select $4$$;
 create function cp7_credit.post_return_journal(text,uuid,date,text,jsonb)returns uuid language sql as $$select erp.post_journal($1,$2,$3,$4,$5)$$;
 create function cp7_credit.flush_opening_return_hpp_v1(uuid)returns void language plpgsql as $$begin return;end$$;
 create function cp7_credit.native_return_complete(uuid,numeric,numeric)returns numeric language sql as $$select 0::numeric$$;
 create function cp7_credit.native_return_leave(uuid)returns void language plpgsql as $$begin return;end$$;
 `);
 for(const sig of ['erp.post_sale(uuid)','erp.post_sales_return(uuid)','erp.compute_non_po_product_hpp_targets_v2620f(uuid)',
  'erp.compute_po_hpp_gl_targets_v2620d(uuid)',
  'erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)',
  'erp.post_opening_hpp_correction(uuid,numeric,text,date)',
  'erp.sync_opening_lot_hpp_to_gl(uuid,date)'])await db.exec(input.definitions[sig]);
 await db.exec(input.assert_nonpo);
 await db.exec(input.old_opening_sync.replace('erp.sync_opening_lot_hpp_to_gl(', 'erp.failed_opening_sync('));
 for(const product of[x.source,x.target,x.outside])await insert('erp.products',{id:product});
 for(const location of[x.location,x.otherLocation])await insert('erp.locations',{id:location,is_active:true,location_type:'FG_WAREHOUSE'});
 await insert('erp.production_orders',{id:x.po});
 for(const[lot,product,qty,cost,hpp,origin]of[
  [x.root10,x.source,2,10,x.hpp10,'OPENING'],[x.root30,x.source,2,30,x.hpp30,'OPENING'],
  [x.root50,x.target,1,50,x.hpp50,'OPENING'],[x.converted,x.target,1,10,x.hppConverted,'CONVERSION'],
  [x.root90,x.outside,3,90,x.hpp90,'OPENING']]) {
  await insert('erp.fg_lots',{id:lot,product_id:product,initial_qty_pcs:qty,lot_origin:origin,lot_number:'MODEL-'+lot.slice(-4)});
  await insert('erp.hpp_versions',{id:hpp,lot_id:lot,version_no:1,cost_state:'ADJUSTED',qty_basis_pcs:qty,total_cost:qty*cost,is_current:true});
  await movement(lot,product,qty,'OPENING',cost);
 }
 await movement(x.root10,x.source,-1,'REBRAND_OUT',10);
 await insert('erp.product_conversions',{id:x.conversion,from_product_id:x.source,to_product_id:x.target,status:'POSTED'});
 await insert('erp.product_conversion_allocations',{id:x.allocation,conversion_id:x.conversion,source_lot_id:x.root10,destination_lot_id:x.converted,qty_pcs:1,original_hpp_per_pcs:10});
 await insert('cp7_sku_conversion.groups_v1',{request_id:x.group});
 await insert('cp7_sku_conversion.members_v1',{group_id:x.group,conversion_id:x.conversion});
 await insert('cp7_sku_conversion.valuation_quotes_v2',{group_id:x.group,source_product_id:x.source,
  target_product_id:x.target,location_id:x.location,quality_grade:'GRADE_A',qty_pcs:1,
  physical_at:'2026-01-01T00:00:00Z',source_before_qty:4,source_before_value:80,source_before_average:20,
  target_before_qty:1,target_before_value:50,target_before_average:50,transfer_value:20,valuation_revision:'MODEL'});
 let line=0;
 for(const[side,product,lot,units]of[['SOURCE',x.source,x.root10,.5],['SOURCE',x.source,x.root30,-.5],
  ['TARGET',x.target,x.root10,.5],['TARGET',x.target,x.root30,.5],['TARGET',x.target,x.converted,-1]])
  await insert('cp7_sku_conversion.component_events_v2',{id:id(++serial),group_id:x.group,source_type:'SKU_CONVERSION',source_id:x.group,
   line_no:++line,phase:'POST',side,product_id:product,location_id:x.location,quality_grade:'GRADE_A',root_lot_id:lot,units_delta:units,
   physical_at:'2026-01-01T00:00:00Z',economic_date:'2026-01-01'});
 await db.exec(`insert into public.model_book values('${x.source}',60,0,0),('${x.target}',70,0,0),('${x.outside}',270,0,0);`);
 assert.deepEqual(await values(x.source),{hpp:60,fg:60,cogs:0,other:0});
 assert.deepEqual(await values(x.target),{hpp:70,fg:70,cogs:0,other:0});
 results.push({label:'Exact typed base tables and full candidate component DDL reproduce the 60/70 converted source pools',result:'PASS'});
 await control('Retained opening sync reproduces the exact 20 versus 15 refusal',async()=>{
  await query('update erp.hpp_versions set total_cost=80 where id=$1',[x.hpp30]);
  await assert.rejects(()=>query("select erp.failed_opening_sync($1,'2026-01-03')",[x.root30]),e=>e.message.includes('OPENING_SOURCE_CHANGE_NOT_EXACT')&&e.message.includes('20.00')&&e.message.includes('15.00'));
 });
 await control('Root recost posts source 15 plus target 5 against equity 20 and preserves component history',async()=>{
  const before=await scalar('select jsonb_agg(to_jsonb(e)order by id)from cp7_sku_conversion.component_events_v2 e');
  await query("select erp.post_opening_hpp_correction($1,40,'MODEL root recost','2026-01-03')",[x.root30]);
  assert.deepEqual(await values(x.source),{hpp:75,fg:75,cogs:0,other:0});
  assert.deepEqual(await values(x.target),{hpp:75,fg:75,cogs:0,other:0});
  assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(e)order by id)from cp7_sku_conversion.component_events_v2 e'),before);
  const journal=(await query('select *from public.model_journal')).rows;assert.equal(journal.length,1);
  assert.equal(journal[0].source_type,'OPENING_HPP_SOURCE_V2620G');
  assert.deepEqual(journal[0].lines.map(r=>[r.mapping_key,r.product_id??null,r.debit-r.credit]),[
   ['FG_INVENTORY',x.source,15],['FG_INVENTORY',x.target,5],['OPENING_EQUITY',null,-20]]);
  await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[x.source]);
  await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[x.target]);
 });
 await control('Opposite pre-existing source/book discrepancies refuse before changing root HPP',async()=>{
  await query('update public.model_book set fg=fg+case when product_id=$1 then 1 else -1 end where product_id in($1,$2)',[x.source,x.target]);
  await db.exec('savepoint refusal');
  await assert.rejects(()=>query("select erp.post_opening_hpp_correction($1,40,'MODEL corrupt books','2026-01-03')",[x.root30]),e=>e.message.includes('NON_PO_HPP_TARGET_BOOK_MISMATCH'));
  await db.exec('rollback to savepoint refusal');
  assert.equal(await scalar('select hpp_per_pcs::text from erp.hpp_versions where id=$1',[x.hpp30]),'30.000000');
  assert.equal(await scalar('select count(*)from public.model_journal'),0);
 });
 await control('The exact aggregate source guard still refuses an unexplained cent',async()=>{
  await query('update erp.hpp_versions set total_cost=80 where id=$1',[x.hpp30]);
  await query('update public.model_book set fg=fg+0.01 where product_id=$1',[x.target]);
  await assert.rejects(()=>query("select erp.sync_opening_lot_hpp_to_gl($1,'2026-01-03')",[x.root30]),e=>e.message.includes('OPENING_SOURCE_CHANGE_NOT_EXACT'));
 });
 await control('Both physical sale allocations retain the same proportional roots and 35 value',async()=>{
  await saleSetup();await postSaleModel();
  const rows=(await query('select sale_stock_allocation_id,root_lot_id,component_units::text units,booked_value::text value from cp7_sku_conversion.sale_allocation_components_v2 order by sale_stock_allocation_id,root_lot_id')).rows;
  for(const allocation of[x.saleA,x.saleB])assert.deepEqual(rows.filter(r=>r.sale_stock_allocation_id===allocation).map(r=>[r.root_lot_id,Number(r.units),Number(r.value)]),[[x.root10,.25,2.5],[x.root30,.25,7.5],[x.root50,.5,25]]);
  assert.deepEqual(await values(x.target),{hpp:70,fg:0,cogs:70,other:0});
 });
 await control('Exact Native post_sale body consumes prepared components in the real reservation/status/journal order',async()=>{
  await saleSetup();
  await query('update erp.sales_headers set source_location_id=$1,customer_id=$2 where id=$3',[x.location,id(900),x.sale]);
  await query('update erp.sales_items set qty_pcs=2,unit_price_snapshot=185000,discount_amount=0 where id=$1',[x.saleItem]);
  for(const lot of[x.root50,x.converted])await insert('erp.fg_stock_movements',{
   id:id(++serial),lot_id:lot,product_id:x.target,location_id:x.location,quality_grade:'GRADE_A',
   qty_signed:-1,movement_type:'SALE_RESERVE',customer_id:id(900),source_type:'SALE_ITEM',source_id:x.saleItem,
   physical_at:'2026-01-02T00:00:00Z',system_created_at:'2026-01-02T00:00:00Z'});
  await query('select erp.post_sale($1)',[x.sale]);
  assert.equal(await scalar('select status from erp.sales_headers where id=$1',[x.sale]),'POSTED');
  assert.deepEqual(await values(x.target),{hpp:70,fg:0,cogs:70,other:0});
  const lines=await scalar("select lines from public.model_journal where source_type='SALE'and source_id=$1",[x.sale]);
  assert.deepEqual(Object.fromEntries(lines.map(r=>[r.mapping_key,r.debit-r.credit])),
   {AR_CUSTOMER:370000,SALES_REVENUE:-370000,FG_INVENTORY:-70,COGS:70});
 });
 await control('Partial return restores 35 and status inverse cancels only its component and value events',async()=>{
  await saleSetup();await postSaleModel();await returnSetup();
  await query('select cp7_sku_conversion.prepare_return_values_v2($1)',[x.returned]);
  await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[x.target]);
  assert.equal(Number(await scalar('select effective_value from cp7_sku_conversion.sales_return_values_v2 where return_id=$1',[x.returned])),35);
  await movement(x.root50,x.target,1,'SALES_RETURN');
  await query("update erp.sales_returns set status='POSTED'where id=$1",[x.returned]);
  assert.deepEqual(await values(x.target),{hpp:70,fg:35,cogs:35,other:0});
  await query("update erp.sales_returns set status='REVERSED'where id=$1",[x.returned]);
  await movement(x.root50,x.target,-1,'RETURN_REVERSAL');
  assert.deepEqual(await values(x.target),{hpp:70,fg:0,cogs:70,other:0});
  assert.equal(Number(await scalar("select sum(effective_value_delta)from cp7_sku_conversion.valuation_events_v2 where source_type='SALES_RETURN'and source_id=$1",[x.returned])),0);
  await query("update erp.sales_headers set status='REVERSED'where id=$1",[x.sale]);
  await movement(x.root50,x.target,1,'SALE_REVERSAL');await movement(x.converted,x.target,1,'SALE_REVERSAL');
  assert.deepEqual(await values(x.target),{hpp:70,fg:70,cogs:0,other:0});
 });
 await control('Pre-installation Native sale history remains COGS and never becomes other expense',async()=>{
  await saleSetup(x.source,[x.root10],[1]);
  await query("update erp.sales_headers set status='POSTED'where id=$1",[x.sale]);
  await movement(x.root10,x.source,-1,'SALE_OUT');
  assert.deepEqual(await values(x.source),{hpp:60,fg:50,cogs:10,other:0});
 });
 await control('Ordinary one-lot sale produces value 90 and no synthetic component adjustment',async()=>{
  await saleSetup(x.outside,[x.root90],[1]);
  await query('select cp7_sku_conversion.prepare_sale_values_v2($1)',[x.sale]);
  assert.equal(Number(await scalar('select sum(effective_value)from cp7_sku_conversion.sale_allocation_values_v2 where sale_id=$1',[x.sale])),90);
  assert.equal(await scalar("select count(*)from cp7_sku_conversion.component_events_v2 where source_type='SALE'and source_id=$1",[x.sale]),0);
  assert.deepEqual(await values(x.target),{hpp:70,fg:70,cogs:0,other:0});
 });
 await control('Two one-piece returns preserve the same cents as a batched two-piece return using exact Native journals',async()=>{
  await fractionalSale();await db.exec('savepoint sold');
  const first=await fractionalReturn('split first',1,[[x.saleB,1]]);
  const second=await fractionalReturn('split second',2,[[x.saleB,1]],x.otherLocation);
  assert.deepEqual([first.snapshot,second.snapshot],[3.33,3.34]);
  assert.deepEqual(second.target,{hpp:10,fg:6.67,cogs:3.33,other:0});
  await db.exec('rollback to savepoint sold');
  const batch=await fractionalReturn('same two pieces batched',3,[[x.saleB,2]]);
  assert.equal(batch.snapshot,6.67);assert.deepEqual(batch.target,second.target);
 });
 await control('Two legal draft allocations carry the pending scope cent into the next line',async()=>{
  await fractionalSale();
  const result=await fractionalReturn('one document two allocations',4,[[x.saleA,1],[x.saleB,1]]);
  assert.deepEqual(result.amounts,[3.33,3.34]);assert.equal(result.snapshot,6.67);
 });
 await control('Interleaved allocations share the official financial scope cent rather than losing or duplicating it',async()=>{
  await fractionalSale();
  const a=await fractionalReturn('interleaved B1',5,[[x.saleB,1]]);
  const b=await fractionalReturn('interleaved A1',6,[[x.saleA,1]]);
  const c=await fractionalReturn('interleaved B2',7,[[x.saleB,1]]);
  assert.deepEqual([a.snapshot,b.snapshot,c.snapshot],[3.33,3.34,3.33]);
  assert.deepEqual(c.target,{hpp:10,fg:10,cogs:0,other:0});
 });
 await control('A root recost between returns does not charge previous returned stock to the next return',async()=>{
  await fractionalSale();await fractionalReturn('before recost',8,[[x.saleB,1]]);
  await query("select erp.post_opening_hpp_correction($1,4.5,'MODEL return recost','2026-01-03')",[x.root90]);
  assert.deepEqual(await values(x.outside),{hpp:13.5,fg:4.5,cogs:9,other:0});
  await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[x.outside]);
  const result=await fractionalReturn('after recost',9,[[x.saleB,1]]);
  assert.equal(result.snapshot,4.5);assert.deepEqual(result.target,{hpp:13.5,fg:9,cogs:4.5,other:0});
 });
 await control('After an earlier return is reversed, replacement cents use remaining actual stock without rewriting history',async()=>{
  await fractionalSale();const first=await fractionalReturn('before inverse first',10,[[x.saleB,1]]);
  await fractionalReturn('before inverse second',11,[[x.saleB,1]]);
  const frozen=await scalar('select jsonb_agg(to_jsonb(v)order by sales_return_item_id)from cp7_sku_conversion.sales_return_values_v2 v');
  // Explicit inverse provider: exact status trigger and exact physical writer,
  // with the cumulative book modeled here. This is not Native reversal credit.
  await query("update erp.sales_returns set status='REVERSED'where id=$1",[first.returned]);
  await query("select erp.post_fg_movement($1,$2,$3,'GRADE_A','MODEL_RETURN_INVERSE',-1,3.33,$4,'MODEL_RETURN_INVERSE',$5,'2026-01-04T00:00:00Z','modeled inverse',false)",[x.outside,x.root90,x.location,id(900),first.returned]);
  await query('update public.model_book b set fg=t.fg_value,cogs=t.cogs_value,other_value=t.other_out_value from erp.compute_non_po_product_hpp_targets_v2620f($1)t where b.product_id=$1',[x.outside]);
  assert.deepEqual(await values(x.outside),{hpp:10,fg:3.33,cogs:6.67,other:0});
  assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(v)order by sales_return_item_id)from cp7_sku_conversion.sales_return_values_v2 v'),frozen);
  const replacement=await fractionalReturn('after inverse replacement',12,[[x.saleB,1]]);
  assert.equal(replacement.snapshot,3.34);assert.deepEqual(replacement.target,{hpp:10,fg:6.67,cogs:3.33,other:0});
 });

 await control('Mixed PO and non-PO return components preserve each official scope cent including stock in another product',async()=>{
  await query("update erp.fg_lots set po_id=$1,lot_origin='PRODUCTION'where id=$2",[x.po,x.root30]);
  await query('update erp.hpp_versions set total_cost=60.02 where id=$1',[x.hpp30]);
  await saleSetup();await query('select cp7_sku_conversion.prepare_sale_values_v2($1)',[x.sale]);
  await movement(x.root50,x.target,-1,'SALE_OUT');await movement(x.converted,x.target,-1,'SALE_OUT');
  await query("update erp.sales_headers set status='POSTED'where id=$1",[x.sale]);
  for(const [n,allocation,lot]of[[1,x.saleA,x.root50],[2,x.saleB,x.converted]]) {
   const beforeNonpo=(await values(x.target)).fg;
   const beforePo=Number(await scalar('select fg_value from erp.compute_po_hpp_gl_targets_v2620d($1)',[x.po]));
   const returned=id(800+n),item=id(810+n);
   await insert('erp.sales_returns',{id:returned,status:'DRAFT',physical_at:'2026-01-03T00:00:00Z'});
   await insert('erp.sales_return_items',{id:item,return_id:returned,sale_stock_allocation_id:allocation,
    product_id:x.target,lot_id:lot,location_id:x.location,quality_grade:'GRADE_A',qty_pcs:1});
   await query('select cp7_sku_conversion.prepare_return_values_v2($1)',[returned]);
   const attribution=(await query('select po_id,effective_value::text value from cp7_sku_conversion.sales_return_attributions_v2 where sales_return_item_id=$1',[item])).rows;
   await movement(lot,x.target,1,'SALE_RETURN');
   await query("update erp.sales_returns set status='POSTED'where id=$1",[returned]);
   const afterNonpo=(await values(x.target)).fg;
   const afterPo=Number(await scalar('select fg_value from erp.compute_po_hpp_gl_targets_v2620d($1)',[x.po]));
   assert.equal(Number(attribution.find(r=>r.po_id===null).value),Number((afterNonpo-beforeNonpo).toFixed(2)));
   assert.equal(Number(attribution.find(r=>r.po_id===x.po).value),Number((afterPo-beforePo).toFixed(2)));
   assert.deepEqual(attribution.map(r=>Number(r.value)).sort((a,b)=>a-b),[7.5,27.5]);
  }
 });
 await control('Known zero HPP returns preserve explicit zero while refund journals remain valid',async()=>{
  await fractionalSale();
  await query('update erp.hpp_versions set total_cost=0 where id=$1',[x.hpp90]);
  await query('update public.model_book set fg=0,cogs=0 where product_id=$1',[x.outside]);
  const result=await fractionalReturn('known zero HPP',13,[[x.saleB,1]]);
  assert.equal(result.snapshot,0);assert.deepEqual(result.target,{hpp:0,fg:0,cogs:0,other:0});
 });
 await control('Unknown root HPP refuses before any prepared value or posted effect',async()=>{
  await fractionalSale();await query("update erp.hpp_versions set cost_state='ESTIMATED'where id=$1",[x.hpp90]);
  const before=await scalar('select jsonb_build_object(\'returns\',(select count(*)from erp.sales_returns),\'values\',(select count(*)from cp7_sku_conversion.sales_return_values_v2),\'movements\',(select count(*)from erp.fg_stock_movements),\'journals\',(select count(*)from public.model_journal))');
  await db.exec('savepoint unknown_return');
  await assert.rejects(()=>fractionalReturn('unknown must refuse',14,[[x.saleB,1]]),e=>e.message.includes('CP7_SKU_RETURN_COMPONENT_HPP_UNKNOWN'));
  await db.exec('rollback to savepoint unknown_return');
  assert.deepEqual(await scalar('select jsonb_build_object(\'returns\',(select count(*)from erp.sales_returns),\'values\',(select count(*)from cp7_sku_conversion.sales_return_values_v2),\'movements\',(select count(*)from erp.fg_stock_movements),\'journals\',(select count(*)from public.model_journal))'),before);
 });
 const creditObservations=await runCreditControls({db,input,x,id,query,scalar,insert,movement,control,
  saleSetup,postSaleModel,returnSetup,fractionalSale,fractionalReturn,values});
 const report={status:'POSTGRES17_EXACT_CONSUMER_SQL_CONTROLS_PASS_NOT_NATIVE',engine,results,fractionalObservations,creditObservations,
  valuation_source:{bytes:Buffer.byteLength(ddl),sha256:createHash('sha256').update(ddl).digest('hex')},
  model_providers:['authority helpers','credit policy lifecycle (the added credit controls execute exact initial HPP projection, proof and line semantics)','inverse cumulative book only in explicitly labeled inverse control','book and journal storage','known laundry/PO completeness','admitted conversion and sync context','current root HPP lookup'],
  actual_Native_cases:0,actual_Auth_HTTP_cases:0,production_go:false,independent_acceptance:false};
 if(process.env.CP7_CONSUMER_MODEL_REPORT)await writeFile(process.env.CP7_CONSUMER_MODEL_REPORT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,checks:results.length,actual_Native_cases:0}));
}catch(error){
 if(process.env.CP7_CONSUMER_MODEL_REPORT)await writeFile(process.env.CP7_CONSUMER_MODEL_REPORT,JSON.stringify({status:'FAILED',engine,results,fractionalObservations,error:{message:error.message,SQLSTATE:error.code??null,context:error.where??null,detail:error.detail??null},actual_Native_cases:0},null,2)+'\n');
 console.error(JSON.stringify({status:'FAILED',checks:results.length,message:error.message,SQLSTATE:error.code??null,context:error.where??null}));process.exitCode=1;
}finally{await db.close();}
