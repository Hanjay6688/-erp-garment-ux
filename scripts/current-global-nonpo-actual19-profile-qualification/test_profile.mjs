/** Actual definitions and metadata over declared local models: zero Native credit. */
import assert from 'node:assert/strict';
import {setup,snapshot,inspect} from './model_profile.mjs';
const db=await setup();const cases=[];
const authority=async()=>(await db.query('select cp7_global_nonpo_native_graph.authority_v1()value')).rows[0].value;
async function check(name,fixture,verify){
 await db.exec('begin');
 try{
  await db.exec("set local local_model.inspecting='off'");if(fixture)await db.exec(fixture);
  await db.exec("set local local_model.inspecting='on'");
  const before=await snapshot(db),catalogue=await authority(),result=await inspect(db);
  assert.deepEqual(await snapshot(db),before);
  assert.deepEqual(await authority(),catalogue);
  await verify(catalogue,result);
  cases.push({name,status:'PASS_LOCAL_SQL_CONTROL',direct_model_rows_sequence_new_catalog_and_known19_equal:true,actual_Native_credit:0});
 }finally{await db.exec('rollback')}
}
function refuse(a,r){assert.equal(a.known_functions_exact,false);assert.equal(r.status,'REFUSE_KNOWN_SOURCE_AUTHORITY')}
let failure;
try{
 await check('EXACT_ACTUAL19_METADATA_VIEW_AND_PRIVATE_ACL',null,(a,r)=>{
  assert.equal(a.known_functions_exact,true);assert.equal(a.known_function_count,19);
  assert(a.functions.every(x=>x.exact_known_source&&x.exact_captured_profile));
  assert.equal(a.view.exact_known_source,true);assert.equal(a.new_private_acl_closed,true);
  assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');assert.equal(r.qualified_for_runtime,false);
  assert.equal(r.runtime_entry,null);assert.equal(r.writer_or_phantom_lock_closed,false);
 });
 await check('COST_METADATA_CHANGED_WITHOUT_BODY_CHANGE',"alter function erp.be_nonpo_admitted_v1(uuid) cost 37",(a,r)=>{
  refuse(a,r);const f=a.functions.find(x=>x.signature==='erp.be_nonpo_admitted_v1(uuid)');
  assert.equal(f.exact_known_source,true);assert.equal(f.exact_captured_profile,false);
 });
 await check('ROWS_METADATA_CHANGED_WITHOUT_BODY_CHANGE','alter function erp.compute_non_po_product_hpp_targets_v2620f(uuid) rows 7',refuse);
 await check('KNOWN_FUNCTION_EXTRA_ANON_GRANT','grant execute on function erp.be_nonpo_admitted_v1(uuid) to anon',refuse);
 await check('REQUIRED_KNOWN_PRIVATE_GRANT_MISSING','revoke execute on function cp7_credit.pg_jsonb_sha256(jsonb) from cp7_credit_write',refuse);
 await check('KNOWN_GRANT_OPTION_CHANGED','grant execute on function erp.require_internal() to service_role with grant option',refuse);
 await check('KNOWN_CONFIG_CHANGED',"alter function erp.be_nonpo_admitted_v1(uuid) set statement_timeout='1s'",refuse);
 await check('KNOWN_STRICT_CHANGED','alter function erp.be_nonpo_admitted_v1(uuid) strict',refuse);
 await check('KNOWN_PARALLEL_CHANGED','alter function erp.be_nonpo_admitted_v1(uuid) parallel safe',refuse);
 await check('VIEW_EXTRA_GRANT_WITHOUT_DEFINITION_CHANGE','grant select on erp.v_current_hpp to anon',(a,r)=>{
  assert.equal(a.known_functions_exact,true);assert.equal(a.view.exact_known_source,false);assert.equal(r.status,'REFUSE_KNOWN_SOURCE_AUTHORITY');
 });
 await check('VIEW_EXTRA_OPTION_WITHOUT_DEFINITION_CHANGE','alter view erp.v_current_hpp set(security_barrier=true)',(a,r)=>{
  assert.equal(a.view.exact_known_source,false);assert.equal(r.status,'REFUSE_KNOWN_SOURCE_AUTHORITY');
 });
 await check('NEW_INSPECTOR_EXPOSURE_REFUSED','grant usage on schema cp7_global_nonpo_native_graph to authenticated;grant execute on function cp7_global_nonpo_native_graph.inspect_v1(uuid[]) to authenticated',(a,r)=>{
  assert.equal(a.new_private_acl_closed,false);assert.equal(r.status,'REFUSE_KNOWN_SOURCE_AUTHORITY');
 });
}catch(error){failure=String(error.stack??error);process.exitCode=1}
finally{await db.close()}
process.stdout.write(JSON.stringify({classification:'LOCAL_SOURCE_AND_CATALOG_MODELS_NOT_ERP_RUNTIME_ACCEPTANCE',
 status:failure?'INCOMPLETE':'PASS',cases,error:failure,standins:db.actual19LocalStandins,
 actual_Native:0,actual_Auth_HTTP_browser_races:0,runtime_entry:null,production_go:false},null,2)+'\n');
