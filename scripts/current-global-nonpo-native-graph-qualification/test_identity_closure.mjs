/** Additional identity/Native-predicate models. Native business cases remain0. */
import assert from'node:assert/strict';
import fs from'node:fs/promises';
import path from'node:path';
import {setup,inspect,snapshot,uuid,here,runtime}from'./model.mjs';
import {mixedJournal,cost,secondConversion,returns,rich}from'./identity_fixtures.mjs';
const db=await setup(),cases=[],sensitivity=[];
const sql=s=>db.exec(s),ids=x=>x.map(uuid),gated=r=>{assert.equal(r.qualified_for_runtime,false);assert.equal(r.runtime_entry,null);assert.equal(r.writer_or_phantom_lock_closed,false)};
const has=(r,c)=>assert(r.issues?.includes(c),JSON.stringify(r.issues));
const nativeQuery=await fs.readFile(path.join(here,'retained/Native_lineage_guard_query.sql'),'utf8');
const nativeGuard=async()=> (await db.query(nativeQuery)).rows[0].native_guard_refuses;
function partition(r){
 const rKeys=new Set(r.scope.relevant.identity_keys.map(x=>x.kind+'|'+x.id)),oKeys=new Set(r.scope.outside.identity_keys.map(x=>x.kind+'|'+x.id));
 assert([...rKeys].every(x=>!oKeys.has(x)));
 assert.deepEqual(new Set([...rKeys,...oKeys]),new Set(r.scope.support.identity_keys.map(x=>x.kind+'|'+x.id)));
 assert.equal(r.scope.account_or_category_identity_hubs_used,false);
}
async function check(name,fixture,verify){
 await sql('begin');
 try{
  await sql("set local local_model.inspecting='off'");if(fixture)await fixture();
  await sql("set local local_model.inspecting='on'");
  const before=await snapshot(db),result=await inspect(db),after=await snapshot(db);
  assert.deepEqual(after,before);gated(result);partition(result);await verify(result);
  cases.push({name,status:'PASS',direct_before:before,direct_after:after});
 }finally{await sql('rollback')}
}
function pulled(r){
 has(r,'RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED');
 assert(r.scope.relevant.product_ids.includes(uuid(22)));assert(r.scope.relevant.product_ids.includes(uuid(23)));
 assert.deepEqual(r.scope.outside.product_ids,[]);
}
let failure;
try{
 await check('COST_EVENT_NULL_DIMENSION_JOURNAL_SIBLING_PULLS_CONVERSION_INTO_R',()=>cost(db),r=>{
  pulled(r);assert(r.scope.relevant.cost_event_ids.includes(uuid(903)));assert(r.scope.relevant.document_ids.includes(uuid(901)));
  assert(r.global_source.facts.journal_lines.some(l=>l.journal_entry_id===uuid(610)&&l.product_id===null));
 });
 await check('TRANSFER_EVENT_NULL_DIMENSION_JOURNAL_SIBLING_PULLS_CONVERSION_INTO_R',async()=>{
  await mixedJournal(db);await sql(`insert into erp.be_nonpo_transfer_events_v1(id,conversion_id,previous_value,target_value,journal_id,economic_date)
   values('${uuid(920)}','${uuid(201)}',20,20,'${uuid(610)}','2026-10-20')`);
 },r=>{pulled(r);assert.equal(r.transfer_rows[0].delta,0)});
 await check('SHARED_RECEIPT_DOCUMENT_CONNECTS_DISTINCT_CONVERSION_OUTSTANDINGS',()=>returns(db),r=>{
  pulled(r);assert.deepEqual(r.scope.relevant.return_outstanding_ids,ids([906,907]));assert.equal(r.global_source.facts.returned_lots.length,2);
 });
 await check('SHARED_KIND_QUALIFIED_DOCUMENT_LINK_CONNECTS_DOCUMENTS',async()=>{
  await secondConversion(db);await sql(`insert into erp.bc_documents_v1(id,status)values('${uuid(901)}','POSTED'),('${uuid(904)}','REVERSED');
   insert into erp.be_conversion_cost_sources_v1(document_id,conversion_id,kind)values('${uuid(901)}','${uuid(201)}','USAGE'),('${uuid(904)}','${uuid(202)}','RECOVERY');
   insert into erp.bc_document_links_v1 values('${uuid(901)}','TRANSFER','${uuid(990)}'),('${uuid(904)}','TRANSFER','${uuid(990)}')`);
 },r=>{pulled(r);assert(r.scope.relevant.identity_keys.some(x=>x.kind==='BC_LINK_TRANSFER'&&x.id===uuid(990)))});
 await check('ADJUSTMENT_PURPOSE_DOCUMENT_IDENTITY_CONNECTS_COST_HISTORY',async()=>{
  await cost(db,{product:null});await secondConversion(db);await sql(`insert into erp.bc_documents_v1(id,status)values('${uuid(904)}','POSTED');
   insert into erp.be_conversion_cost_sources_v1(document_id,conversion_id,kind)values('${uuid(904)}','${uuid(202)}','USAGE');
   insert into erp.bc_adjustment_purposes_v1 values('${uuid(902)}','${uuid(904)}','FACTORY_USE','${uuid(501)}',null,null)`);
 },pulled);
 await check('OUTSTANDING_SOURCE_DOCUMENT_IDENTITY_RETAINED',async()=>{
  await secondConversion(db);await sql(`insert into erp.bc_documents_v1(id,status)values('${uuid(901)}','POSTED');
   insert into erp.be_conversion_cost_sources_v1(document_id,conversion_id,kind)values('${uuid(901)}','${uuid(202)}','RECOVERY');
   insert into erp.bc_outstanding_returns_v1(id,status,qty_expected,document_id)values('${uuid(906)}','OPEN',5,'${uuid(901)}');
   insert into erp.be_conversion_returns_v1 values('${uuid(906)}','${uuid(201)}',1)`);
 },pulled);
 await check('RETURN_PARENT_LOT_IDENTITY_RETAINED',async()=>{await returns(db,{sharedDocument:false});await sql(`update erp.bc_return_lots_v1 set parent_lot_id='${uuid(908)}'where id='${uuid(909)}'`)},pulled);
 await check('RETURN_PARENT_EVENT_IDENTITY_RETAINED',async()=>{
  await returns(db,{sharedDocument:false});await sql(`insert into erp.bc_lot_events_v1(id,document_id,lot_id,event_kind,qty)values('${uuid(910)}','${uuid(901)}','${uuid(908)}','VALUE',1);
   update erp.bc_return_lots_v1 set parent_event_id='${uuid(910)}'where id='${uuid(909)}'`);
 },pulled);
 await check('LATER_LOT_EVENT_DOCUMENT_CONNECTS_EARLIER_RETURN_HISTORY',async()=>{
  await returns(db,{sharedDocument:false});await sql(`insert into erp.bc_lot_events_v1(id,document_id,lot_id,event_kind,qty)values('${uuid(910)}','${uuid(904)}','${uuid(908)}','VALUE',1)`);
 },pulled);
 await check('JOURNAL_REVERSAL_CONNECTS_FULL_MIXED_ROWS_WITHOUT_DIMENSION_ASSUMPTION',()=>cost(db,{reversal:true}),r=>{
  pulled(r);assert(r.scope.relevant.journal_ids.includes(uuid(610)));assert(r.scope.relevant.journal_ids.includes(uuid(611)));
 });
 await check('NATIVE_HPP_SYNC_EVENT_EXPLICIT_JOURNAL_IDENTITY_RETAINED',async()=>{
  await mixedJournal(db);await sql(`insert into erp.non_po_hpp_gl_sync_events_v2620f(id,product_id,journal_entry_id)values('${uuid(930)}','${uuid(23)}','${uuid(610)}')`);
 },pulled);
 await check('NATIVE_CONVERSION_SOURCE_JOURNAL_IDENTITY_RETAINED',()=>mixedJournal(db,{sourceType:'PRODUCT_CONVERSION',sourceId:201}),pulled);
 await check('SHARED_ACCOUNT_IS_NOT_AN_IDENTITY_HUB',()=>cost(db,{product:null}),r=>{
  assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');assert.deepEqual(r.scope.relevant.product_ids,ids([21]));
  assert.deepEqual(r.scope.outside.product_ids,ids([22,23]));assert(!r.scope.support.identity_keys.some(x=>x.kind==='ACCOUNT'));
 });
 await check('NATIVE_G_DOMAINS_EXACT_WHILE_SUPPORT_PARTITION_BROADENS',async()=>{
  await rich(db);
  const current=await inspect(db),oldScope=await fs.readFile(path.join(here,'retained/4e263_scope.sql'),'utf8'),newScope=await fs.readFile(path.join(runtime,'scope.sql'),'utf8');
  await sql(oldScope.replace(/^create function/m,'create or replace function'));
  const old=(await db.query('select cp7_global_nonpo_native_graph.scope_v1($1::uuid[])value',[[uuid(1)]])).rows[0].value;
  await sql(newScope.replace(/^create function/m,'create or replace function'));
  assert.deepEqual(current.scope.global,old.global);assert.deepEqual(old.relevant.product_ids,ids([21]));
 },pulled);
 await check('NATIVE_FINAL_GUARD_VALID_GRAPH_FALSE',null,async r=>{assert.equal(await nativeGuard(),false);assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY')});
 await check('NATIVE_FINAL_GUARD_DISCONNECTED_CYCLE_TRUE',()=>sql(`
  update erp.fg_lots set lot_origin='CONVERSION',source_lot_id='${uuid(103)}'where id='${uuid(102)}';
  insert into erp.product_conversions(id,from_product_id,to_product_id,status,physical_at,qty_pcs)values('${uuid(202)}','${uuid(23)}','${uuid(22)}','POSTED','2026-10-20T03:00Z',1);
  insert into erp.product_conversion_allocations values('${uuid(302)}','${uuid(202)}','${uuid(103)}','${uuid(102)}',1,10,0);
  insert into erp.be_conversion_sources_v1(conversion_id,source_lot_id,origin_kind)values('${uuid(202)}','${uuid(103)}','FG')`),async r=>{
  assert.equal(await nativeGuard(),true);has(r,'GLOBAL_NATIVE_LINEAGE_ORPHAN_CYCLE_DEPTH_OR_SOURCE_INVALID');
 });
 await check('NATIVE_REACHABLE_BACK_EDGE_REJECTED_BY_SOURCE_ORIGIN_IDENTITY',()=>sql(`
  insert into erp.product_conversions(id,from_product_id,to_product_id,status,physical_at,qty_pcs)values('${uuid(202)}','${uuid(23)}','${uuid(22)}','POSTED','2026-10-20T03:00Z',1);
  insert into erp.product_conversion_allocations values('${uuid(302)}','${uuid(202)}','${uuid(103)}','${uuid(102)}',1,10,0);
  insert into erp.be_conversion_sources_v1(conversion_id,source_lot_id,origin_kind)values('${uuid(202)}','${uuid(103)}','FG')`),async r=>{
  assert.equal(await nativeGuard(),true);has(r,'GLOBAL_NATIVE_LINEAGE_ORPHAN_CYCLE_DEPTH_OR_SOURCE_INVALID');
 });
 await check('DUPLICATE_SAME_PARENT_VISIT_IS_NOT_A_FALSE_CYCLE_OR_WRITE',()=>sql(`
  update erp.product_conversion_allocations set qty_pcs=1 where id='${uuid(301)}';
  insert into erp.product_conversion_allocations values('${uuid(302)}','${uuid(201)}','${uuid(102)}','${uuid(103)}',1,10,0)`),async r=>{
  assert.equal(await nativeGuard(),false);assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');
  assert.equal(r.propagation_visits.length,2);assert(r.propagation_visits.every(x=>x.would_write_HPP===false));assert(r.transfer_rows.every(x=>x.delta===0));
 });
 // Every retained Native shared documentary/journal field in these typed models
 // is changed in isolation. Invalid combinations are structural sensitivity only.
 const targets={journal_entries:610,journal_lines:711,bc_documents_v1:901,bc_document_links_v1:null,
  bc_adjustment_purposes_v1:null,bc_outstanding_returns_v1:906,bc_return_lots_v1:908,bc_lot_events_v1:910,
  be_conversion_sources_v1:null,be_conversion_cost_sources_v1:null,be_conversion_cost_events_v1:903,
  be_nonpo_transfer_events_v1:920,be_conversion_returns_v1:null,non_po_hpp_gl_sync_events_v2620f:930,material_adjustments:902};
 let counter=0;
 for(const [table,key]of Object.entries(targets)){
  const columns=(await db.query("select a.attname,format_type(a.atttypid,a.atttypmod)type,a.attgenerated from pg_attribute a where a.attrelid=$1::regclass and a.attnum>0 and not a.attisdropped order by a.attnum",['erp.'+table])).rows;
  for(const {attname,type,attgenerated}of columns){
   await sql('begin');
   try{
    await sql("set local local_model.inspecting='off'");await rich(db);
    const baseline=await inspect(db);pulled(baseline);
    const column='"'+attname+'"';let expression;
    if(attgenerated)expression="economic_date=transaction_date+1";
    else if(type==='uuid')expression=column+`='${uuid(990000+(++counter))}'`;
    else if(/^(numeric|integer|bigint)/.test(type))expression=column+'=coalesce('+column+',0)+1';
    else if(type==='jsonb')expression=column+"=coalesce("+column+",'{}'::jsonb)||'{\"local_sensitivity\":true}'::jsonb";
    else if(type==='boolean')expression=column+'=not coalesce('+column+',false)';
    else if(type==='date'||type.startsWith('timestamp'))expression=column+"=coalesce("+column+",'2026-10-20')+interval'1 day'";
    else expression=column+"='"+(attname==='origin_kind'?'REWORK':attname==='status'?'REVERSED':'LOCAL_CHANGED')+"'";
    let where=key?`id='${uuid(key)}'`:table==='bc_document_links_v1'?`document_id='${uuid(901)}'and link_kind='JOURNAL'`:
     table==='bc_adjustment_purposes_v1'?`adjustment_id='${uuid(902)}'`:table==='be_conversion_sources_v1'?`conversion_id='${uuid(201)}'`:
     table==='be_conversion_returns_v1'?`outstanding_id='${uuid(906)}'`:`document_id='${uuid(901)}'`;
    await sql(`update erp.${table} set ${expression} where ${where}`);
    await sql("set local local_model.inspecting='on'");
    const before=await snapshot(db),changed=await inspect(db),after=await snapshot(db);assert.deepEqual(before,after);gated(changed);partition(changed);
    assert.notEqual(changed.basis_sha256,baseline.basis_sha256,'SHARED_FIELD_NOT_BOUND:'+table+'.'+attname);
    sensitivity.push({table,column:attname,generated_driver:attgenerated?'economic_date':null,synthetic_model_column:table==='material_adjustments'&&attname==='amount',
     status:'PASS',observed:changed.status,basis_changed:true,direct_before:before,direct_after:after});
   }finally{await sql('rollback')}
  }
 }
}catch(error){failure=error}
const report={classification:'LOCAL_TYPED_IDENTITY_AND_NATIVE_PREDICATE_MODELS_NOT_NATIVE_BUSINESS',status:failure?'FAIL':'PASS',
 source_pins:db.localSourcePins,counts:{directed_PASS:cases.length,field_sensitivity_PASS:sensitivity.length,FAIL:failure?1:0},cases,field_sensitivity:sensitivity,
 Native_guard_execution:'EXACT_FINAL_EXISTS_QUERY_ONLY_NO_NATIVE_WRITER',actual_Native:0,actual_DB_server:0,required_final_composition_parent:null,
 runtime_entry:null,writer_or_phantom_lock_closed:false,production_go:false,independent_acceptance:false};
console.log(JSON.stringify(report,null,2));await db.close();if(failure){console.error(failure);process.exitCode=1}
