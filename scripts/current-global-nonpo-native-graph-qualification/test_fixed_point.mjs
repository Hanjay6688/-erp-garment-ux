/** Exact Native SELECT predicates plus immediate no-write induction models only. */
import assert from'node:assert/strict';
import fs from'node:fs/promises';
import path from'node:path';
import {createHash}from'node:crypto';
import {setup,inspect,snapshot,uuid,here}from'./model.mjs';
const db=await setup(),cases=[];
const guardQuery=await fs.readFile(path.join(here,'retained/Native_lineage_guard_query.sql'),'utf8');
const visitFile=await fs.readFile(path.join(here,'retained/Native_propagation_visits_query.sql'),'utf8');
const visits=visitFile.replace(/^--[^\n]*\n/,'').trim().replace(/;$/,'');
const nativeQueryPins={};
for(const [name,value]of Object.entries({'retained/Native_lineage_guard_query.sql':guardQuery,'retained/Native_propagation_visits_query.sql':visitFile}))
 nativeQueryPins[name]={bytes:Buffer.byteLength(value),sha256:createHash('sha256').update(value).digest('hex')};
const compareQuery=`with native_visits as(${visits})select v.id,v.source_depth,s.hpp_per_pcs source_hpp,d.hpp_per_pcs current_hpp,
 (s.hpp_per_pcs::numeric(18,6)+erp.be_allocation_extra_v1(v.id)/v.qty_pcs)::numeric(18,6)desired_hpp,
 d.hpp_version_id is null or abs(coalesce(d.hpp_per_pcs,0)-(s.hpp_per_pcs::numeric(18,6)+erp.be_allocation_extra_v1(v.id)/v.qty_pcs)::numeric(18,6))>0.000001 would_write
 from native_visits v left join erp.v_current_hpp s on s.lot_id=v.source_lot_id left join erp.v_current_hpp d on d.lot_id=v.destination_lot_id order by v.source_depth,v.id`;
async function chain(){await db.exec(`
 insert into erp.fg_lots(id,product_id,source_lot_id,lot_origin,initial_qty_pcs)values('${uuid(104)}','${uuid(24)}','${uuid(103)}','CONVERSION',1);
 insert into erp.hpp_versions(id,lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current)values('${uuid(114)}','${uuid(104)}',1,'ADJUSTED',1,10,true);
 insert into erp.product_conversions(id,from_product_id,to_product_id,status,physical_at,qty_pcs)values('${uuid(202)}','${uuid(23)}','${uuid(24)}','POSTED','2026-10-20T03:00Z',1);
 insert into erp.product_conversion_allocations values('${uuid(302)}','${uuid(202)}','${uuid(103)}','${uuid(104)}',1,10,0);
 insert into erp.be_conversion_sources_v1(conversion_id,source_lot_id,origin_kind)values('${uuid(202)}','${uuid(103)}','FG');
 insert into erp.fg_stock_movements values('${uuid(405)}','${uuid(103)}',-1,'CONVERSION_OUT',null),('${uuid(406)}','${uuid(104)}',1,'CONVERSION_IN',null);
 insert into erp.journal_entries(id,status,source_type,source_id)values('${uuid(612)}','POSTED','PRODUCT_CONVERSION','${uuid(202)}');
 insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,product_id)values
 ('${uuid(714)}','${uuid(612)}','${uuid(501)}',0,10,'${uuid(23)}'),('${uuid(715)}','${uuid(612)}','${uuid(501)}',10,0,'${uuid(24)}');`)}
async function check(name,fixture,verify){
 await db.exec('begin');try{
  await db.exec("set local local_model.inspecting='off'");if(fixture)await fixture();await db.exec("set local local_model.inspecting='on'");
  const before=await snapshot(db),result=await inspect(db),nativeGuard=(await db.query(guardQuery)).rows[0].native_guard_refuses,
   nativeOrderedComparisons=(await db.query(compareQuery)).rows,after=await snapshot(db);assert.deepEqual(before,after);
  assert.equal(result.qualified_for_runtime,false);assert.equal(result.runtime_entry,null);assert.equal(result.writer_or_phantom_lock_closed,false);
  await verify(result,nativeGuard,nativeOrderedComparisons);
  cases.push({name,status:'PASS',native_final_guard_refuses:nativeGuard,native_ordered_current_state_comparisons:nativeOrderedComparisons,
   direct_before:before,direct_after:after});
 }finally{await db.exec('rollback')}
}
let failure;
try{
 await check('IMMEDIATE_NO_WRITE_INDUCTION_TWO_LEVEL_CHAIN',chain,(r,g,v)=>{
  assert.equal(g,false);assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');assert.equal(v.length,2);
  assert(v.every(x=>x.would_write===false));assert(r.transfer_rows.every(x=>x.delta===0));
  assert.deepEqual(v.map(x=>[x.id,x.source_depth]),r.propagation_visits.map(x=>[x.id,x.source_depth]));
  for(const x of r.outside_alignment)assert.deepEqual(x.target,x.book);
 });
 await check('DIRTY_ANCESTOR_REFUSED_BEFORE_DOWNSTREAM_START_STATE_CAN_MASK_IT',async()=>{await chain();await db.exec(`update erp.hpp_versions set total_cost=110 where id='${uuid(112)}'`)},(r,g,v)=>{
  assert.equal(g,false);assert.deepEqual(v.map(x=>x.would_write),[true,false]);assert.deepEqual(v.map(x=>x.desired_hpp),['11.000000','10.000000']);
  assert(r.issues.includes('GLOBAL_PROPAGATION_REQUIRES_HPP_WRITE'));
 });
 await check('REACHABLE_DESCENDANT_BACK_EDGE_FAILS_SOURCE_IDENTITY_NOT_REACHABILITY_ALONE',async()=>{
  await chain();await db.exec(`insert into erp.product_conversions(id,from_product_id,to_product_id,status,physical_at,qty_pcs)values('${uuid(203)}','${uuid(24)}','${uuid(23)}','POSTED','2026-10-20T04:00Z',1);
   insert into erp.product_conversion_allocations values('${uuid(303)}','${uuid(203)}','${uuid(104)}','${uuid(103)}',1,10,0);
   insert into erp.be_conversion_sources_v1(conversion_id,source_lot_id,origin_kind)values('${uuid(203)}','${uuid(104)}','FG')`);
 },(r,g,v)=>{assert.equal(g,true);assert(v.some(x=>x.id===uuid(303)));assert(r.issues.includes('GLOBAL_NATIVE_LINEAGE_ORPHAN_CYCLE_DEPTH_OR_SOURCE_INVALID'))});
 await check('INSPECTOR_STRICTER_NULL_DESTINATION_UNKNOWN_IS_NOT_NATIVE_GUARD_EQUIVALENCE',()=>db.exec(`update erp.product_conversion_allocations set destination_lot_id=null`),(r,g,v)=>{
  assert.equal(g,false);assert.deepEqual(v,[]);assert(r.issues.includes('GLOBAL_NATIVE_LINEAGE_ORPHAN_CYCLE_DEPTH_OR_SOURCE_INVALID'));
 });
}catch(error){failure=error}
console.log(JSON.stringify({classification:'LOCAL_NATIVE_SELECT_AND_NUMERIC_MODELS_NO_NATIVE_WRITER_EXECUTION',status:failure?'FAIL':'PASS',source_pins:db.localSourcePins,native_query_inputs:nativeQueryPins,
 counts:{PASS:cases.length,FAIL:failure?1:0},cases,proof_scope:'Immediate branch no-write induction only; Native context DML and early UUID evaluation remain real dispatcher behavior, unexecuted here.',
 actual_Native:0,actual_DB_server:0,runtime_entry:null,required_final_composition_parent:null,writer_or_phantom_lock_closed:false,production_go:false},null,2));
await db.close();if(failure){console.error(failure);process.exitCode=1}
