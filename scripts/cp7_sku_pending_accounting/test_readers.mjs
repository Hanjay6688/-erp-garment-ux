// Exact prepared readers on typed synthetic rows; zero ERP/Auth acceptance.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE);
const input=JSON.parse(await readFile(process.env.CP7_PENDING_MODEL_INPUT,'utf8'));
assert.equal(input.classification,'TYPED_READER_MODEL_NOT_NATIVE_ERP');
const db=new PGlite(),results=[];
const id=n=>'74000000-0000-4000-8000-'+String(n).padStart(12,'0');
const x=Object.fromEntries(['po','product','location','lot','hpp','conversion','allocation','event',
 'sale','saleAllocation','return','returnItem','document'].map((k,i)=>[k,id(i+1)]));
const quote=s=>'"'+s.replaceAll('"','""')+'"';
const q=(sql,args=[])=>db.query(sql,args);
const scalar=async(sql,args=[])=>Object.values((await q(sql,args)).rows[0])[0];
async function insert(table,row){
 const keys=Object.keys(row);await q('insert into '+table+'('+keys.map(quote).join(',')+')values('
  +keys.map((_,i)=>'$'+(i+1)).join(',')+')',Object.values(row));
}
async function snapshot(){
 const rows={};for(const {name}of(await q("select schemaname||'.'||tablename name from pg_tables where schemaname in('erp','cp7_sku_conversion','public')order by 1")).rows)
  rows[name]=await scalar("select coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),'[]'::jsonb)from "+name+' t');
 return rows;
}
async function deny(operation,pattern){
 const before=await snapshot();await db.exec('savepoint expected_refusal');let caught;
 try{await operation();}catch(error){caught=error;}
 await db.exec('rollback to savepoint expected_refusal;release savepoint expected_refusal');
 assert.ok(caught,'Expected a refusal');assert.match(caught.message,pattern);assert.deepEqual(await snapshot(),before);
 return {SQLSTATE:caught.code,message:caught.message};
}
async function control(name,operation){
 await db.exec('begin');try{await operation();results.push({name,status:'PASS'});}
 finally{await db.exec('rollback');}
 assert.deepEqual(await snapshot(),baseline,name+' must restore every modeled row');
 console.log(JSON.stringify({control:name,status:'PASS'}));
}
const value=kind=>scalar('select cp7_sku_conversion.cost_scope_value_v3($1,$2,$3)::text',[x.product,x.po,kind]);
const unit=()=>scalar('select unit_value::text from cp7_sku_conversion.cost_accounting_root_v5($1)',[x.lot]);
const strict=()=>q('select *from cp7_sku_conversion.cost_root_v3($1)',[x.lot]);
const unknown=/CP7_SKU_POOL_HPP_UNKNOWN:/;
let engine,baseline;
try{
 engine=await scalar('select version()');assert.match(engine,/^PostgreSQL 17\./);
 await db.exec("create schema erp;create schema cp7_sku_conversion;create role anon;create role authenticated;create role service_role;set search_path='';set check_function_bodies=off;");
 for(const[table,columns]of Object.entries(input.columns)){
  const primary=table==='cp7_sku_conversion.groups_v1'?'request_id':table==='erp.opening_lot_hpp_gl_state'?'lot_id':'id';
  await db.exec('create table '+table+'('+columns.map(c=>quote(c[0])+' '+c[2]
   +(c[5]==='s'?' generated always as ('+c[13]+') stored':c[0]==='id'&&c[2]==='uuid'?' default gen_random_uuid()':'')
   +(c[0]===primary&&c[2]==='uuid'?' primary key':'')).join(',')+')');
  const observed=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
  assert.deepEqual(observed,Object.fromEntries(columns.map(c=>[c[0],c[2]])));
 }
 for(const sql of input.tables)await db.exec(sql);
 await db.exec(`create table public.model_pending(po_id uuid primary key,pending_count integer,unknown_laundry boolean);
 create function erp.get_hpp_completeness(uuid)returns table(pending_reason_count integer)language sql stable as
 $$select pending_count from public.model_pending where po_id=$1$$;
 create function erp.bd_lot_laundry_unknown_v1(uuid)returns boolean language sql stable as
 $$select coalesce((select p.unknown_laundry from public.model_pending p join erp.fg_lots l on l.po_id=p.po_id where l.id=$1),false)$$;`);
 for(const sql of Object.values(input.extra))await db.exec(sql);
 for(const sql of[input.original_root,input.cells,input.original_unit,input.original_scope])await db.exec(sql);
 await db.exec('revoke all on function cp7_sku_conversion.cost_root_v3(uuid),cp7_sku_conversion.cost_current_unit_v3(uuid,uuid),cp7_sku_conversion.cost_scope_value_v3(uuid,uuid,text)from public,anon,authenticated,service_role;');
 await insert('erp.production_orders',{id:x.po,status:'IN_PROGRESS'});
 await insert('erp.products',{id:x.product});await insert('erp.locations',{id:x.location});
 await insert('erp.fg_lots',{id:x.lot,po_id:x.po,product_id:x.product,initial_qty_pcs:2,lot_origin:'CONVERSION'});
 await insert('erp.hpp_versions',{id:x.hpp,lot_id:x.lot,version_no:1,cost_state:'ADJUSTED',qty_basis_pcs:2,total_cost:100,is_current:true});
 await insert('erp.product_conversions',{id:x.conversion,status:'POSTED'});
 await insert('erp.product_conversion_allocations',{id:x.allocation,conversion_id:x.conversion,destination_lot_id:x.lot,qty_pcs:2,conversion_cost_allocated:20});
 await insert('public.model_pending',{po_id:x.po,pending_count:0,unknown_laundry:false});
 await insert('cp7_sku_conversion.cost_events_v3',{id:x.event,source_type:'SKU_CONVERSION',source_id:x.conversion,line_no:1,phase:'POST',side:'ORIGIN',product_id:x.product,location_id:x.location,quality_grade:'GRADE_A',root_lot_id:x.lot,units_delta:2,physical_at:'2026-01-01',economic_date:'2026-01-01'});
 await insert('erp.sales_headers',{id:x.sale,status:'POSTED'});await insert('erp.sale_stock_allocations',{id:x.saleAllocation});
 await insert('cp7_sku_conversion.sale_allocation_values_v2',{sale_stock_allocation_id:x.saleAllocation,sale_id:x.sale,product_id:x.product,lot_id:x.lot,location_id:x.location,quality_grade:'GRADE_A',qty_pcs:1,effective_value:50,legacy_value:50,effective_unit_value:50,pool_revision:'MODEL'});
 await insert('cp7_sku_conversion.sale_cost_components_v3',{sale_stock_allocation_id:x.saleAllocation,line_no:1,root_lot_id:x.lot,po_id:x.po,component_units:1,booked_value:10});
 await insert('erp.sales_returns',{id:x.return,status:'POSTED'});await insert('erp.sales_return_items',{id:x.returnItem});
 await insert('cp7_sku_conversion.sales_return_values_v2',{sales_return_item_id:x.returnItem,return_id:x.return,sale_stock_allocation_id:x.saleAllocation,product_id:x.product,lot_id:x.lot,location_id:x.location,quality_grade:'GRADE_A',qty_pcs:1,effective_value:50,legacy_value:50,effective_unit_value:50});
 await insert('cp7_sku_conversion.return_cost_components_v3',{sales_return_item_id:x.returnItem,line_no:1,root_lot_id:x.lot,po_id:x.po,component_units:1,booked_value:10});
 const strictBefore=await scalar("select jsonb_build_array(prosrc,prosecdef,provolatile,proconfig,proacl)from pg_proc where oid='cp7_sku_conversion.cost_root_v3(uuid)'::regprocedure");
 const firstBaseline=await snapshot();
 await db.exec('begin');await q("update erp.hpp_versions set cost_state='ESTIMATED'where id=$1",[x.hpp]);
 await deny(()=>value('OWNED'),unknown);await db.exec('rollback');assert.deepEqual(await snapshot(),firstBaseline);
 await db.exec(input.product.ddl);
 const strictAfter=await scalar("select jsonb_build_array(prosrc,prosecdef,provolatile,proconfig,proacl)from pg_proc where oid='cp7_sku_conversion.cost_root_v3(uuid)'::regprocedure");
 assert.deepEqual(strictAfter,strictBefore);baseline=await snapshot();
 await control('Known PO amount and full source proof stay exact',async()=>{
  assert.equal(Number(await unit()),10);assert.equal(Number(await value('OWNED')),20);
  const proof=await scalar('select source_revision from cp7_sku_conversion.cost_accounting_root_v5($1)',[x.lot]);
  assert.equal(proof.accounting_only,true);assert.equal(proof.final_cost_ready,true);
 });
 for(const state of['ESTIMATED','UNKNOWN_LAUNDRY','INCOMPLETE_PO'])await control('Provisional PO '+state+' keeps numeric accounting and strict price refusal',async()=>{
  if(state==='ESTIMATED')await q("update erp.hpp_versions set cost_state='ESTIMATED'where id=$1",[x.hpp]);
  if(state==='UNKNOWN_LAUNDRY')await q('update public.model_pending set unknown_laundry=true');
  if(state==='INCOMPLETE_PO')await q('update public.model_pending set pending_count=2');
  await deny(strict,unknown);assert.equal(Number(await value('OWNED')),20);
  const proof=await scalar('select source_revision from cp7_sku_conversion.cost_accounting_root_v5($1)',[x.lot]);
  assert.equal(proof.final_cost_ready,false);
 });
 await control('All four accounting scopes follow current PO source amounts',async()=>{
  await q('update public.model_pending set pending_count=2,unknown_laundry=true');
  await q("update erp.hpp_versions set cost_state='ESTIMATED'where id=$1",[x.hpp]);
  for(const[kind,expected]of[['OWNED',20],['CONVERSION',20],['SOLD',10],['RETURNED',10]])assert.equal(Number(await value(kind)),expected);
  await deny(strict,unknown);
 });
 await control('Later invoice cents use retained exact source events while readiness stays pending',async()=>{
  await q('update public.model_pending set pending_count=1');
  await insert('erp.be_conversion_cost_sources_v1',{document_id:x.document,conversion_id:x.conversion,kind:'USAGE'});
  await insert('erp.be_conversion_cost_events_v1',{id:id(200),document_id:x.document,previous_amount:0,target_amount:10.01});
  assert.equal(Number(await value('OWNED')),30.01);assert.equal(Number(await value('SOLD')),15.005);
  await deny(strict,unknown);await q('update public.model_pending set pending_count=0');
  assert.equal(Number((await strict()).rows[0].unit_value),15.005);
 });
 await control('Present zero and signed cost credit remain source facts',async()=>{
  await q('update public.model_pending set pending_count=1');
  await q('update erp.product_conversion_allocations set conversion_cost_allocated=0 where id=$1',[x.allocation]);
  assert.equal(Number(await value('OWNED')),0);
  await q('update erp.product_conversion_allocations set conversion_cost_allocated=-4.02 where id=$1',[x.allocation]);
  assert.equal(Number(await value('OWNED')),-4.02);
 });
 const invalid=[
  ['missing HPP',()=>q('delete from erp.hpp_versions where id=$1',[x.hpp]),unknown],
  ['missing numeric HPP',()=>q('update erp.hpp_versions set qty_basis_pcs=0 where id=$1',[x.hpp]),unknown],
  ['nonfinite extra',()=>q("update erp.product_conversion_allocations set conversion_cost_allocated='NaN'where id=$1",[x.allocation]),unknown],
  ['missing extra',()=>q('update erp.product_conversion_allocations set conversion_cost_allocated=null where id=$1',[x.allocation]),unknown],
  ['zero allocation quantity',()=>q('update erp.product_conversion_allocations set qty_pcs=0 where id=$1',[x.allocation]),unknown],
  ['unposted conversion',()=>q("update erp.product_conversions set status='DRAFT'where id=$1",[x.conversion]),unknown],
  ['duplicate allocation',()=>insert('erp.product_conversion_allocations',{id:id(201),conversion_id:x.conversion,destination_lot_id:x.lot,qty_pcs:2,conversion_cost_allocated:20}),/ALLOCATION_NOT_UNIQUE/]
 ];
 for(const[name,alter,pattern]of invalid)await control('Accounting still refuses '+name,async()=>{await alter();await deny(()=>unit(),pattern);});
 await control('Non-PO estimated cost remains refused',async()=>{
  await q('update erp.fg_lots set po_id=null where id=$1',[x.lot]);
  await q("update erp.hpp_versions set cost_state='ESTIMATED'where id=$1",[x.hpp]);await deny(()=>unit(),unknown);
 });
 await control('Non-PO current cents and tampered custody keep original guards',async()=>{
  await q('update erp.fg_lots set po_id=null where id=$1',[x.lot]);
  await insert('cp7_sku_conversion.cost_money_events_v3',{id:id(202),kind:'ORIGIN',source_id:x.conversion,root_lot_id:x.lot,product_id:x.product,amount_delta:20,revision:'MODEL',source_proof:{modeled:true},economic_date:'2026-01-01'});
  assert.equal(Number(await scalar('select cp7_sku_conversion.cost_accounting_unit_v5($1,$2)',[x.lot,x.product])),10);
  await q('update cp7_sku_conversion.cost_money_events_v3 set amount_delta=19');
  await deny(()=>scalar('select cp7_sku_conversion.cost_accounting_unit_v5($1,$2)',[x.lot,x.product]),/COST_MONEY_SOURCE_NOT_EXACT/);
 });
 await control('New accounting functions expose no direct role grants',async()=>{
  for(const role of['anon','authenticated','service_role'])for(const fn of['cost_accounting_root_v5(uuid)','cost_accounting_unit_v5(uuid,uuid)'])
   assert.equal(await scalar('select has_function_privilege($1,$2,\'EXECUTE\')',[role,'cp7_sku_conversion.'+fn]),false);
 });
 await control('Invalid accounting scope still refuses',async()=>{await deny(()=>value('FORGED'),/COST_SCOPE_KIND/);});
 const report={status:'PENDING_PO_ACCOUNTING_READER_CONTROLS_PASS_MODEL_NOT_ERP',engine,controls:results,
  old_reader_pending_PO_refusal_reproduced:true,strict_reader_source_metadata_unchanged:true,all_modeled_rows_restored:true,
  pending_readiness_provenance_retained:true,actual_ERP_cases:0,actual_Auth_cases:0,
  automatic_rework_completion_executed:false,automatic_redye_completion_executed:false,
  production_go:false,independent_acceptance:false};
 await writeFile(process.env.CP7_PENDING_MODEL_REPORT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,controls:results.length}));
}finally{await db.close();}
