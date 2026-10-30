/** Meaningful local SQL/authority/row-sequence controls; actual Native cases=0. */
import assert from'node:assert/strict';
import fs from'node:fs/promises';
import {setup,inspect,snapshot,uuid,here}from'./model.mjs';
const db=await setup(),rows=[];
async function check(name,fixture,verify){
 await db.exec('begin');
 try{
  await db.exec("set local local_model.inspecting='off'");if(fixture)await fixture();
  await db.exec("set local local_model.inspecting='on'");
  const before=await snapshot(db),result=await inspect(db),after=await snapshot(db);
  assert.deepEqual(after,before,'DIRECT_BEFORE_AFTER_MODEL_ROWS_SEQUENCES_OR_CATALOG_CHANGED');
  await verify(result);rows.push({name,status:'PASS',direct_before_after_rows_sequence_catalog_equal:true,
   direct_before:before,direct_after:after});
 }catch(error){rows.push({name,status:'FAIL',error:String(error),sqlstate:error.code});throw error}
 finally{await db.exec('rollback')}
}
const exec=s=>db.exec(s),ids=x=>x.map(uuid),has=(r,c)=>assert(r.issues?.includes(c),JSON.stringify(r.issues));
const pass=r=>{assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');assert.equal(r.qualified_for_runtime,false);assert.equal(r.runtime_entry,null);assert.equal(r.writer_or_phantom_lock_closed,false)};
async function multi(){
 await exec(`update erp.product_conversion_allocations set qty_pcs=1 where id='${uuid(301)}';
 update erp.fg_lots set initial_qty_pcs=1 where id='${uuid(103)}';
 update erp.hpp_versions set qty_basis_pcs=1,total_cost=10 where id='${uuid(113)}';
 update erp.fg_stock_movements set qty_signed=-1 where id='${uuid(403)}';
 update erp.fg_stock_movements set qty_signed=1 where id='${uuid(404)}';
 insert into erp.fg_lots(id,product_id,lot_origin,initial_qty_pcs)values('${uuid(104)}','${uuid(22)}','OTHER',10);
 insert into erp.fg_lots(id,product_id,source_lot_id,lot_origin,initial_qty_pcs)values('${uuid(105)}','${uuid(23)}','${uuid(104)}','CONVERSION',1);
 insert into erp.hpp_versions(id,lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current)values
 ('${uuid(114)}','${uuid(104)}',1,'ACTUAL',10,100,true),('${uuid(115)}','${uuid(105)}',1,'ADJUSTED',1,10,true);
 insert into erp.product_conversion_allocations values('${uuid(302)}','${uuid(201)}','${uuid(104)}','${uuid(105)}',1,10,0);
 insert into erp.fg_stock_movements values('${uuid(405)}','${uuid(104)}',10,'FG_IN',null),('${uuid(406)}','${uuid(104)}',-1,'CONVERSION_OUT',null),('${uuid(407)}','${uuid(105)}',1,'CONVERSION_IN',null);
 insert into erp.journal_lines values('${uuid(704)}','${uuid(601)}','${uuid(501)}',100,0,'${uuid(22)}',null)`);
}
let failure;
try{
 await check('FULL_ACTUAL_G_R_O_KEYSETS_AND_PRIVATE_SOURCE_AUTHORITY_LOCAL_MODEL',null,r=>{
  pass(r);assert.equal(r.authority.known_function_count,19);assert.equal(r.authority.known_functions_exact,true);
  assert.deepEqual(r.scope.relevant.product_ids,ids([21]));assert.deepEqual(r.scope.outside.product_ids,ids([22,23]));
  assert.equal(r.propagation_visits.length,1);assert.equal(r.transfer_rows.length,1);assert.equal(r.transfer_rows[0].delta,0);
  assert.equal(r.outside_alignment.length,2);assert.equal(r.outside_source.facts.BE_sources.length,1);
 });
 await check('RELEVANT_ALLOCATED_SOURCE_CONVERSION_LINEAGE_REFUSED',()=>exec(`update erp.sales_items set product_id='${uuid(22)}';update erp.sale_stock_allocations set lot_id='${uuid(102)}'`),r=>{
  has(r,'RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED');assert(r.scope.relevant.product_ids.includes(uuid(23)));
 });
 await check('UNALLOCATED_SAME_PRODUCT_IDENTITY_EDGE_IS_RELEVANT',()=>exec(`insert into erp.fg_lots(id,product_id,source_lot_id,lot_origin,initial_qty_pcs)values('${uuid(106)}','${uuid(21)}','${uuid(102)}','OTHER',1)`),r=>{
  has(r,'RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED');assert(r.scope.relevant.lot_ids.includes(uuid(102)));
 });
 await check('MIXED_JOURNAL_PRODUCT_LINK_PREVENTS_FALSE_OUTSIDE_CUT',()=>exec(`insert into erp.journal_lines values('${uuid(705)}','${uuid(601)}','${uuid(501)}',0.01,0,'${uuid(21)}',null)`),r=>{
  has(r,'RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED');assert.deepEqual(r.scope.outside.product_ids,[]);
 });
 await check('REAL_PARENT_FINANCIAL_DEPENDENCY_RETAINS_APPLY_HISTORY',()=>exec(`
 insert into erp.sales_headers values('${uuid(2)}','${uuid(99)}','POSTED','2026-10-20');
 insert into erp.sales_items values('${uuid(12)}','${uuid(2)}','${uuid(22)}',100);
 insert into erp.sale_stock_allocations values('${uuid(32)}','${uuid(12)}','${uuid(102)}',1);
 insert into cp7_credit.return_families values('${uuid(801)}','${uuid(1)}');
 insert into cp7_credit.cohorts values('${uuid(802)}','${uuid(801)}','${uuid(1)}','${uuid(99)}');
 insert into cp7_credit.consumption_events values('${uuid(803)}','${uuid(802)}','APPLY','${uuid(2)}',null,80)`),r=>{
  assert.deepEqual(r.scope.financial_sale_ids,ids([1,2]));has(r,'RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED');
 });
 await check('ROOT_SET_ORDER_HAS_ONE_CANONICAL_SOURCE_BASIS',async()=>{
  await exec(`insert into erp.sales_headers values('${uuid(2)}','${uuid(99)}','POSTED','2026-10-20');
   insert into erp.sales_items values('${uuid(12)}','${uuid(2)}','${uuid(21)}',100);
   insert into erp.sale_stock_allocations values('${uuid(32)}','${uuid(12)}','${uuid(101)}',1)`);
  const first=await inspect(db,ids([1,2])),second=await inspect(db,ids([2,1]));pass(first);pass(second);
  assert.equal(first.basis_sha256,second.basis_sha256);
 },r=>pass(r));
 await check('DIRTY_ANCESTOR_CANNOT_HIDE_BEHIND_OLD_CHILD_HPP',()=>exec(`update erp.hpp_versions set total_cost=110 where id='${uuid(112)}'`),r=>{
  has(r,'GLOBAL_PROPAGATION_REQUIRES_HPP_WRITE');has(r,'GLOBAL_TRANSFER_REQUIRES_EVENT_OR_SOURCE_INVALID');
  assert.equal(r.propagation_visits[0].desired_hpp,11);assert.equal(r.transfer_rows[0].delta,2);
 });
 await check('NATIVE_NUMERIC18_6_EXACT_EPSILON_IS_NO_WRITE',()=>exec(`update erp.hpp_versions set total_cost=20.000002 where id='${uuid(113)}'`),r=>{
  pass(r);assert.equal(r.propagation_visits[0].destination_hpp,10.000001);assert.equal(r.propagation_visits[0].would_write_HPP,false);
 });
 await check('NATIVE_NUMERIC18_6_NEXT_UNIT_REQUIRES_WRITE',()=>exec(`update erp.hpp_versions set total_cost=20.000004 where id='${uuid(113)}'`),r=>has(r,'GLOBAL_PROPAGATION_REQUIRES_HPP_WRITE'));
 await check('TRANSFER_IMMUTABLE_EVENT_SUM_IS_NOT_IGNORED',()=>exec(`insert into erp.be_nonpo_transfer_events_v1 values('${uuid(804)}','${uuid(201)}',20,21,'${uuid(601)}','2026-10-20')`),r=>{
  has(r,'GLOBAL_TRANSFER_REQUIRES_EVENT_OR_SOURCE_INVALID');assert.equal(r.transfer_rows[0].delta,-1);assert.equal(r.outside_source.facts.nonpo_transfers.length,1);
 });
 await check('MULTIPLE_ALLOCATIONS_ALL_NATIVE_PER_ALLOCATION_ZERO',multi,r=>{pass(r);assert.deepEqual(r.transfer_rows.map(x=>x.delta),[0,0])});
 await check('MULTIPLE_ALLOCATIONS_CANNOT_NET_AWAY_NATIVE_ROW_DELTA',async()=>{await multi();await exec(`
 update erp.hpp_versions set total_cost=110 where id='${uuid(114)}';
 insert into erp.be_nonpo_transfer_events_v1 values('${uuid(804)}','${uuid(201)}',20,21,'${uuid(601)}','2026-10-20')`)},r=>{
  has(r,'GLOBAL_TRANSFER_REQUIRES_EVENT_OR_SOURCE_INVALID');assert.deepEqual(r.transfer_rows.map(x=>x.delta),[-1,0]);
 });
 await check('REVERSED_CONVERSION_HISTORY_REMAINS_VISIBLE_AND_QUIESCENT',()=>exec(`
 update erp.product_conversions set status='REVERSED';update erp.journal_entries set status='REVERSED'where id='${uuid(602)}';
 insert into erp.fg_stock_movements values('${uuid(408)}','${uuid(102)}',2,'REVERSAL','${uuid(403)}'),('${uuid(409)}','${uuid(103)}',-2,'REVERSAL','${uuid(404)}');
 insert into erp.journal_entries(id,status,source_type,source_id,reversal_of_id)values('${uuid(603)}','POSTED','JOURNAL_REVERSAL','${uuid(602)}','${uuid(602)}');
 insert into erp.journal_lines values('${uuid(706)}','${uuid(603)}','${uuid(501)}',20,0,'${uuid(22)}',null),('${uuid(707)}','${uuid(603)}','${uuid(501)}',0,20,'${uuid(23)}',null)`),r=>{
  pass(r);assert.equal(r.scope.global.guard_be_source_ids.length,1);assert.equal(r.outside_source.facts.conversions[0].status,'REVERSED');
  assert.deepEqual(r.propagation_visits,[]);assert.deepEqual(r.transfer_rows,[]);
 });
 await check('DISCONNECTED_CONVERSION_CYCLE_REFUSED_BEFORE_WRITER',()=>exec(`
 update erp.fg_lots set lot_origin='CONVERSION',source_lot_id='${uuid(103)}'where id='${uuid(102)}';
 insert into erp.product_conversions values('${uuid(202)}','${uuid(23)}','${uuid(22)}','POSTED','2026-10-20T03:00Z',1);
 insert into erp.product_conversion_allocations values('${uuid(302)}','${uuid(202)}','${uuid(103)}','${uuid(102)}',1,10,0);
 insert into erp.be_conversion_sources_v1 values('${uuid(202)}','${uuid(103)}','FG')`),r=>has(r,'GLOBAL_NATIVE_LINEAGE_ORPHAN_CYCLE_DEPTH_OR_SOURCE_INVALID'));
 await check('ORPHAN_DESTINATION_SOURCE_IDENTITY_REFUSED',()=>exec(`update erp.fg_lots set source_lot_id=null where id='${uuid(103)}'`),r=>has(r,'GLOBAL_NATIVE_LINEAGE_ORPHAN_CYCLE_DEPTH_OR_SOURCE_INVALID'));
 await check('MISSING_DESTINATION_CURRENT_HPP_IS_UNKNOWN_NOT_ZERO',()=>exec(`update erp.hpp_versions set is_current=false where id='${uuid(113)}'`),r=>has(r,'GLOBAL_NATIVE_HPP_SOURCE_MISSING_NONFINITE_OR_AMBIGUOUS'));
 await check('MULTIPLE_CURRENT_SOURCE_HPP_NOT_HIDDEN_BY_DISTINCT_ON',()=>exec(`insert into erp.hpp_versions(id,lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current)values('${uuid(116)}','${uuid(102)}',2,'ACTUAL',10,100,true)`),r=>has(r,'GLOBAL_NATIVE_HPP_SOURCE_MISSING_NONFINITE_OR_AMBIGUOUS'));
 await check('MISSING_ALLOCATION_COST_IS_UNKNOWN_NOT_QUIESCENT',()=>exec(`update erp.product_conversion_allocations set conversion_cost_allocated=null`),r=>has(r,'GLOBAL_NATIVE_HPP_SOURCE_MISSING_NONFINITE_OR_AMBIGUOUS'));
 await check('UNALLOCATED_OUTSIDE_NONVOIDED_LOT_WITHOUT_HPP_IS_UNKNOWN',()=>exec(`insert into erp.fg_lots(id,product_id,lot_origin,initial_qty_pcs)values('${uuid(108)}','${uuid(24)}','OTHER',1)`),r=>has(r,'GLOBAL_NONVOIDED_CURRENT_HPP_UNKNOWN_OR_NONFINITE'));
 await check('NONFINITE_ROOT_HPP_IS_REFUSED',()=>exec(`update erp.hpp_versions set total_cost='NaN'where id='${uuid(112)}'`),r=>has(r,'GLOBAL_NONVOIDED_CURRENT_HPP_UNKNOWN_OR_NONFINITE'));
 await check('NEGATIVE_RECOVERY_DESIRED_HPP_REFUSED',()=>exec(`
 insert into erp.bc_documents_v1 values('${uuid(901)}','POSTED');insert into erp.material_adjustments values('${uuid(902)}',-30);
 insert into erp.be_conversion_cost_sources_v1 values('${uuid(901)}','${uuid(201)}','RECOVERY');
 insert into erp.be_conversion_cost_events_v1 values('${uuid(903)}','${uuid(901)}','${uuid(902)}',0,-30,'${uuid(601)}','2026-10-20')`),r=>has(r,'GLOBAL_NATIVE_HPP_SOURCE_MISSING_NONFINITE_OR_AMBIGUOUS'));
 await check('SAME_VALUE_COST_SOURCE_IDENTITY_CHANGES_BASIS',async()=>{
  const original=await inspect(db);await exec(`insert into erp.bc_documents_v1 values('${uuid(901)}','POSTED');insert into erp.material_adjustments values('${uuid(902)}',0);
  insert into erp.be_conversion_cost_sources_v1 values('${uuid(901)}','${uuid(201)}','USAGE');
  insert into erp.be_conversion_cost_events_v1 values('${uuid(903)}','${uuid(901)}','${uuid(902)}',1,1,'${uuid(601)}','2026-10-20')`);
  const changed=await inspect(db);pass(original);pass(changed);assert.notEqual(changed.basis_sha256,original.basis_sha256);
 },r=>pass(r));
 await check('GLOBAL_SYNC_INCLUDES_PRODUCT_WITH_ONLY_VOIDED_LOT',()=>exec(`insert into erp.fg_lots(id,product_id,lot_origin,initial_qty_pcs)values('${uuid(107)}','${uuid(24)}','VOIDED_PRODUCTION',1)`),r=>{
  pass(r);assert(r.scope.global.sync_product_ids.includes(uuid(24)));assert(!r.scope.global.propagation_lock_lot_ids.includes(uuid(107)));
 });
 await check('ONE_CENT_OUTSIDE_BOOK_MISMATCH_REFUSED',()=>exec(`update erp.journal_lines set debit=100.01 where id='${uuid(701)}'`),r=>has(r,'OUTSIDE_NATIVE_TARGET_BOOK_NOT_EXACT'));
 await check('KNOWN_SAME_RESULT_FUNCTION_SOURCE_CHANGE_REFUSED',async()=>{
  const definition=(await db.query("select pg_get_functiondef('erp.be_conversion_extra_v1(uuid)'::regprocedure)d")).rows[0].d;
  await exec(definition.replace('coalesce(sum(','coalesce( sum('));
 },r=>{assert.equal(r.status,'REFUSE_KNOWN_SOURCE_AUTHORITY');assert.equal(r.qualified_for_runtime,false)});
 await check('SAME_BODY_DIFFERENT_FUNCTION_SEARCH_PATH_REFUSED',()=>exec("alter function erp.be_conversion_extra_v1(uuid)set search_path='erp','public'"),r=>assert.equal(r.status,'REFUSE_KNOWN_SOURCE_AUTHORITY'));
 await check('NATIVE_VIEW_PREDICATE_CHANGE_REFUSED',()=>exec("create or replace view erp.v_current_hpp with(security_invoker=true)as select distinct on(lot_id)lot_id,id as hpp_version_id,version_no,cost_state,qty_basis_pcs,total_cost,hpp_per_pcs,calculated_at from erp.hpp_versions hv where is_current=true and version_no>0 order by lot_id,version_no desc"),r=>assert.equal(r.status,'REFUSE_KNOWN_SOURCE_AUTHORITY'));
 await check('UNEXPECTED_NEW_PRIVATE_EXECUTE_GRANT_REFUSED',()=>exec('grant execute on function cp7_global_nonpo_native_graph.inspect_v1(uuid[])to authenticated'),r=>assert.equal(r.status,'REFUSE_KNOWN_SOURCE_AUTHORITY'));
 await check('AMBIENT_BE_CONTEXT_IS_NOT_A_GLOBAL_BYPASS',()=>exec(`insert into erp.be_execution_context_v1 values(pg_backend_pid(),txid_current(),'${uuid(999)}',true)`),r=>has(r,'AMBIENT_BE_CONTEXT_OR_LEAK_UNQUALIFIED'));
 await check('RETURN_SOURCE_SAME_VALUE_PROGRESS_IS_SEALED',async()=>{
  const before=await inspect(db);await exec(`insert into erp.bc_documents_v1 values('${uuid(905)}','POSTED');
   insert into erp.bc_outstanding_returns_v1 values('${uuid(906)}','OPEN',5);
   insert into erp.be_conversion_returns_v1 values('${uuid(906)}','${uuid(201)}',1);
   insert into erp.bc_return_lots_v1 values('${uuid(907)}','${uuid(906)}','${uuid(905)}',1,'PENDING')`);
  const after=await inspect(db);pass(before);pass(after);assert.notEqual(before.basis_sha256,after.basis_sha256);
 },r=>{assert.equal(r.outside_source.facts.BE_return_sources.length,1);assert.equal(r.outside_source.facts.returned_lots.length,1)});
 await check('DEPTH129_IS_NOT_SILENTLY_TRUNCATED',async()=>{
  for(let i=0;i<128;i++){
   const source=i===0?103:1000+i-1,dest=1000+i,srcProduct=i===0?23:2000+i-1,dstProduct=2000+i,c=3000+i,a=4000+i,h=5000+i;
   await exec(`insert into erp.fg_lots(id,product_id,source_lot_id,lot_origin,initial_qty_pcs)values('${uuid(dest)}','${uuid(dstProduct)}','${uuid(source)}','CONVERSION',1);
    insert into erp.hpp_versions(id,lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current)values('${uuid(h)}','${uuid(dest)}',1,'ADJUSTED',1,10,true);
    insert into erp.product_conversions values('${uuid(c)}','${uuid(srcProduct)}','${uuid(dstProduct)}','POSTED','2026-10-20T04:00Z',1);
    insert into erp.product_conversion_allocations values('${uuid(a)}','${uuid(c)}','${uuid(source)}','${uuid(dest)}',1,10,0);
    insert into erp.be_conversion_sources_v1 values('${uuid(c)}','${uuid(source)}','FG')`);
  }
 },r=>has(r,'GLOBAL_NATIVE_LINEAGE_ORPHAN_CYCLE_DEPTH_OR_SOURCE_INVALID'));
 // Scalar arithmetic is explicitly NOT a valid half-cent Native journal fixture.
 const scalar=(await db.query("select round(0.005::numeric,2)::text p,round(-0.005::numeric,2)::text n,0.005::numeric(20,2)::text stored_native_cent")).rows[0];
 assert.deepEqual(scalar,{p:'0.01',n:'-0.01',stored_native_cent:'0.01'});
 rows.push({name:'HALF_CENT_SCALAR_BOUNDARY_AND_NATIVE_CENT_COLUMN_PRECISION',status:'PASS',symbolic_only_not_valid_Native_halfcent_book:true});
 await db.exec('set role authenticated');let denied;
 try{await inspect(db)}catch(error){denied=error.code}finally{await db.exec('reset role')}
 assert.equal(denied,'42501');rows.push({name:'AUTHENTICATED_HAS_NO_NEW_PRIVATE_SCHEMA_OR_FUNCTION_GRANT',status:'PASS',local_role_DDL_only:true});
}catch(error){failure=error}
const report={classification:'LOCAL_IN_MEMORY_PGLITE_TYPED_STRUCTURAL_MODELS_NOT_NATIVE_BUSINESS',status:failure?'FAIL':'PASS',source_pins:db.localSourcePins,counts:{PASS:rows.filter(x=>x.status==='PASS').length,FAIL:rows.filter(x=>x.status==='FAIL').length},cases:rows,actual_Native:0,actual_DB_server:0,actual_Auth_HTTP:0,production_go:false,independent_acceptance:false};
console.log(JSON.stringify(report,null,2));await db.close();if(failure){console.error(failure);process.exitCode=1}
