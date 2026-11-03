// Typed read-only graph model. No ERP writer, financial transaction or Auth run.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE);
const raw=await readFile(process.env.CP7_GRAPH_INPUT);
const input=JSON.parse(raw);
assert.equal(input.classification,'MODELED_MONEY_GRAPH_CAPTURE_ONLY_NOT_ERP');
const db=new PGlite(),results=[];
const id=n=>'75000000-0000-4000-8000-'+String(n).padStart(12,'0');
const names=['product','target','lot','rootLot','group','sale','allocation','returnItem','costEvent',
 'oldCostEvent','journal','po','saleItem','hpp','document','rebalance','costMoney','baseMoney','rework','journalLine'];
const fixture=n=>Object.fromEntries(names.map((key,i)=>[key,id(n+i+1)]));
const relevant=fixture(0),outside=fixture(100),unrelated=fixture(200),location=id(999),account=id(998);
const quote=s=>'"'+s.replaceAll('"','""')+'"';
const scalar=async(sql,params=[])=>Object.values((await db.query(sql,params)).rows[0])[0];
const scope=()=>scalar('select cp7_global_nonpo_native_graph.scope_v1($1::uuid[])',[[relevant.sale]]);
const capture=(s,o=true)=>scalar('select cp7_global_nonpo_native_graph.capture_v1($1::jsonb,$2)',[JSON.stringify(s),o]);
const oldCapture=s=>scalar('select cp7_global_nonpo_native_graph.prior_money_capture_model($1::jsonb,true)',[JSON.stringify(s)]);
const keys=part=>new Set(part.identity_keys.map(v=>v.kind+':'+v.id));
const passed=label=>results.push({label,result:'PASS'});
function keyFor(table,x){
 const key=input.money_tables[table][1];
 return [key,{group_id:x.group,sale_stock_allocation_id:x.allocation,sales_return_item_id:x.returnItem,
  id:{cost_events_v3:x.costEvent,cost_source_rebalances_v3:x.rebalance,
   cost_money_events_v3:x.costMoney,base_money_events_v4:x.baseMoney}[table]}[key]];
}
async function insert(table,values){
 const columns=input.columns[table];assert(columns,table);
 const row=Object.fromEntries(columns.map(([name,,type])=>[name,
  type==='uuid'||type.endsWith('[]')?null:type==='date'?'2018-01-02':type==='timestamp with time zone'?'2018-01-02T03:04:05Z':
  type==='timestamp without time zone'?'2018-01-02 03:04:05':type==='xid8'?'1':
  /^(numeric|integer|smallint|bigint)/.test(type)?1:type==='boolean'?false:type==='jsonb'?{}:'M']));
 for(const[key,value]of Object.entries(values)){assert(Object.hasOwn(row,key),table+'.'+key);row[key]=value;}
 for(const[name,,type]of columns){const limit=type.match(/^character(?: varying)?\((\d+)\)$/);
  if(limit&&row[name]!==null)assert([...String(row[name])].length<=Number(limit[1]),table+'.'+name+': text bound');}
 await db.query('insert into '+table+'('+Object.keys(row).map(quote).join(',')+')values('+Object.keys(row).map((_,i)=>'$'+(i+1)).join(',')+')',Object.values(row));
}
let engine;
try{
 engine=await scalar('select version()');assert.match(engine,/^PostgreSQL 17\./);
 await db.exec('create role anon;create role authenticated;create role service_role;create schema erp;create schema cp7_sku_conversion;create schema cp7_credit;create schema cp7_global_nonpo_native_graph;');
 for(const[table,columns]of Object.entries(input.columns)){
  await db.exec('create table '+table+'('+columns.map(([n,,t])=>quote(n)+' '+t).join(',')+')');
  const actual=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
  assert.deepEqual(actual,Object.fromEntries(columns.map(([n,,t])=>[n,t])));
 }
 assert.equal(Object.keys(input.columns).length,80);
 assert.equal(Object.values(input.columns).reduce((n,c)=>n+c.length,0),813);
 await db.exec(`create function cp7_credit.consumer_dependency_graph_v1(uuid)returns jsonb language sql stable as $$select jsonb_build_object('sale_ids',jsonb_build_array($1))$$;
 create function cp7_credit.source_hpp_lot_ids_v1(uuid)returns uuid[]language sql stable as $$select array_agg(a.lot_id order by a.lot_id)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=$1$$;
 create function cp7_credit.initial_hpp_account_facts_v1()returns jsonb language sql stable as $$select '{"model_provider":true}'::jsonb$$;
 create function cp7_credit.pg_jsonb_sha256(jsonb)returns text language sql immutable as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;`);
 for(const sql of Object.values(input.helpers))await db.exec(sql);
 await db.exec(input.prior_helpers.capture.replaceAll('cp7_global_nonpo_native_graph.capture_v1','cp7_global_nonpo_native_graph.prior_money_capture_model'));
 await db.exec(input.prior_helpers.scope.replaceAll('cp7_global_nonpo_native_graph.scope_v1','cp7_global_nonpo_native_graph.prior_money_scope_model'));
 passed('Four derived helpers compile with exact 80 table and 813 column types');
 for(const x of[relevant,outside,unrelated]){
  for(const[lot,product]of[[x.lot,x.product],[x.rootLot,x.target]])
   await insert('erp.fg_lots',{id:lot,product_id:product,po_id:x===unrelated?x.po:null,lot_origin:x===unrelated?'PRODUCTION':'OPENING'});
  await insert('erp.sales_items',{id:x.saleItem,sale_id:x.sale,product_id:x.product});
  await insert('erp.sale_stock_allocations',{id:x.allocation,sale_item_id:x.saleItem,lot_id:x.lot});
  await insert('erp.hpp_versions',{id:x.hpp,lot_id:x.rootLot});
  await insert('erp.journal_entries',{id:x.journal,status:'REVERSED'});
  await insert('erp.journal_lines',{id:x.journalLine,journal_entry_id:x.journal,account_id:account,product_id:null,po_id:null});
  await insert('erp.bc_documents_v1',{id:x.document,status:'REVERSED'});
  for(const table of Object.keys(input.money_tables)){
   const fields={group_id:x.group,root_lot_id:x.rootLot,hpp_version_id:x.hpp,product_id:x.product,
    location_id:location,quality_grade:'GRADE_A',sale_stock_allocation_id:x.allocation,sales_return_item_id:x.returnItem,
    journal_id:x.journal,document_id:x.document,source_lot_id:x.lot,rework_id:x.rework,
    origin_kind:'REDYE',native_request_id:id(800),admission_backend_pid:77,admission_transaction_id:88};
   const values=Object.fromEntries(Object.entries(fields).filter(([k])=>input.columns['cp7_sku_conversion.'+table].some(([n])=>n===k)));
   if(table==='cost_events_v3')Object.assign(values,{id:x.costEvent,source_type:'SALE',source_id:x.sale,phase:'REVERSE',side:'POOL',units_delta:-1,supersedes_event_id:x.oldCostEvent});
   if(table==='cost_source_rebalances_v3')values.id=x.rebalance;
   if(table==='cost_money_events_v3')Object.assign(values,{id:x.costMoney,kind:'SOURCE_PRICE',source_id:x.document,amount_delta:0});
   if(table==='base_money_events_v4')Object.assign(values,{id:x.baseMoney,kind:'SOURCE_PRICE',source_id:x.hpp,amount_delta:0,units_delta:0});
   await insert('cp7_sku_conversion.'+table,values);
  }
 }
 const selected=await scope(),baseline=await capture(selected),support=await capture(selected,false),old=await oldCapture(selected);
 const r=keys(selected.relevant),o=keys(selected.outside),s=keys(selected.support);
 assert([...r].every(k=>!o.has(k)));assert.deepEqual(new Set([...r,...o]),s);
 assert(!r.has('PRODUCT:'+outside.product));assert(!s.has('PRODUCT:'+unrelated.product));
 passed('Disjoint relevant and outside components cover support without shared location or account hubs');
 const oldScope=await scalar('select cp7_global_nonpo_native_graph.prior_money_scope_model($1::uuid[])',[[relevant.sale]]);
 for(const[kind,field]of[['SKU_COST_EVENT','costEvent'],['SKU_COST_EVENT','oldCostEvent'],['SKU_COST_MONEY_EVENT','costMoney'],
  ['SKU_BASE_MONEY_EVENT','baseMoney'],['SKU_SOURCE_REBALANCE','rebalance'],['HPP_VERSION','hpp'],['BC_DOCUMENT','document'],['REWORK','rework'],['JOURNAL','journal']]){
  assert(o.has(kind+':'+outside[field]),kind);assert(!keys(oldScope.outside).has(kind+':'+outside[field]),kind+': prior missing identity');
 }
 assert.equal(baseline.facts.SKU_MONEY_cost_money_events_v3[0].amount_delta,0);
 assert.equal(baseline.facts.SKU_MONEY_base_money_events_v4[0].amount_delta,0);
 assert.equal(baseline.facts.SKU_MONEY_cost_events_v3[0].phase,'REVERSE');
 assert.equal(baseline.facts.SKU_MONEY_legacy_groups_v4[0].origin_kind,'REDYE');
 passed('Zero-money sources, reversed costs, old events and automatic legacy origins remain in the closure');
 for(const table of Object.keys(input.money_tables)){
  const[key,value]=keyFor(table,outside);assert(value,table);
  const expected=await scalar('select jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text collate "C")from cp7_sku_conversion.'+table+' t where '+quote(key)+'=$1',[value]);
  assert.deepEqual(baseline.facts['SKU_MONEY_'+table],expected,table);
  assert.equal(support.facts['SKU_MONEY_'+table].length,2,table);
  assert.deepEqual(Object.keys(expected[0]).sort(),input.columns['cp7_sku_conversion.'+table].map(([n])=>n).sort());
 }
 passed('All nine monetary observations retain every column and exact domain membership');
 const mutations={cost_contributors_v3:'transfer_units',sale_cost_components_v3:'booked_value',return_cost_components_v3:'booked_value',
  cost_events_v3:'units_delta',group_inverse_rebalances_v3:'before_proof',cost_source_rebalances_v3:'source_delta',
  cost_money_events_v3:'amount_delta',base_money_events_v4:'amount_delta',legacy_groups_v4:'original_preview'};
 for(const[table,column]of Object.entries(mutations)){
  const type=input.columns['cp7_sku_conversion.'+table].find(([n])=>n===column)[2];
  const expression=type==='jsonb'?"'{\"changed\":true}'::jsonb":quote(column)+'+1';
  const[key,value]=keyFor(table,outside);
  await db.exec('begin');try{
   await db.query('update cp7_sku_conversion.'+table+' set '+quote(column)+'='+expression+' where '+quote(key)+'=$1',[value]);
   assert.notEqual((await capture(selected)).sha256,baseline.sha256,table);
   assert.deepEqual(await oldCapture(selected),old,table+': old capture omission');
   passed('Detect '+table+'.'+column+' previously omitted by the observer');
  }finally{await db.exec('rollback');}
 }
 for(const table of Object.keys(input.money_tables)){
  const[key,value]=keyFor(table,outside);
  for(const[column,,type]of input.columns['cp7_sku_conversion.'+table]){
   if(type!=='date'&&type!=='timestamp with time zone')continue;
   await db.exec('begin');try{
    await db.query('update cp7_sku_conversion.'+table+' set '+quote(column)+'='+quote(column)+(type==='date'?'+1':"+interval '1 second'")+' where '+quote(key)+'=$1',[value]);
    assert.notEqual((await capture(selected)).sha256,baseline.sha256,table+'.'+column);
    assert.deepEqual(await oldCapture(selected),old);
    passed('Retain temporal-only change '+table+'.'+column);
   }finally{await db.exec('rollback');}
  }
 }
 for(const[table,column,value,kind]of[['cost_events_v3','supersedes_event_id',unrelated.costEvent,'SKU_COST_EVENT'],
  ['cost_money_events_v3','source_id',unrelated.document,'BC_DOCUMENT'],['base_money_events_v4','source_id',unrelated.hpp,'HPP_VERSION']]){
  const[key,where]=keyFor(table,outside);
  await db.exec('begin');try{
   await db.query('update cp7_sku_conversion.'+table+' set '+quote(column)+'=$1 where '+quote(key)+'=$2',[value,where]);
   const expanded=await scope();assert(keys(expanded.outside).has(kind+':'+value));
   assert(keys(expanded.outside).has('PRODUCT:'+unrelated.product));
   assert(!keys(expanded.relevant).has('PRODUCT:'+unrelated.product));
   passed('Follow exact historical/source identity '+table+'.'+column+' to its disconnected economic component');
  }finally{await db.exec('rollback');}
 }
 for(const table of Object.keys(input.money_tables)){
  const[key,value]=keyFor(table,outside);
  await db.exec('begin');try{
   await db.query('insert into cp7_sku_conversion.'+table+' select *from cp7_sku_conversion.'+table+' where '+quote(key)+'=$1',[value]);
   const duplicated=await capture(selected);assert.equal(duplicated.facts['SKU_MONEY_'+table].length,2);
   assert.notEqual(duplicated.sha256,baseline.sha256);passed('Preserve duplicate multiplicity in '+table);
  }finally{await db.exec('rollback');}
 }
 for(const role of['anon','authenticated','service_role']){
  assert.equal(await scalar("select bool_or(has_function_privilege($1,p.oid,'EXECUTE'))from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_global_nonpo_native_graph'",[role]),false);
  passed(role+' has no execution capability on prepared helpers');
 }
 const report={status:'MODELED_POSTGRES17_GLOBAL_MONEY_GRAPH_CAPTURE_PASS_NOT_ERP',engine,results,
  input:{bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')},source_helpers:input.proof.derived_helpers,
  modeled_callbacks:input.modeled_callbacks,column_tables:80,column_count:813,new_full_rowsets:9,new_identity_edges:24,
  row_constraints_owners_RLS_Native_callbacks_and_business_transactions_are_not_tested:true,
  actual_ERP_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,production_go:false,independent_acceptance:false};
 await writeFile(process.env.CP7_GRAPH_REPORT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,checks:results.length,actual_ERP_cases:0}));
}catch(error){
 await writeFile(process.env.CP7_GRAPH_REPORT,JSON.stringify({status:'MODEL_FAILED',engine,results,
  error:{message:error.message,SQLSTATE:error.code??null,stack:error.stack},actual_ERP_cases:0},null,2)+'\n');throw error;
}finally{await db.close();}
