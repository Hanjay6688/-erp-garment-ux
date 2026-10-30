/** Exact Native journal-source identity, local typed facts only; Native0. */
import assert from'node:assert/strict';
import {setup,inspect,snapshot,uuid}from'./model.mjs';
import {cost}from'./identity_fixtures.mjs';
const db=await setup(),cases=[],fields=[];
async function fixture({mixed=false,reversal=false,sourceType='MATERIAL_ADJUSTMENT',status='POSTED'}={}){
 await cost(db,{product:null});
 await db.exec(`insert into erp.chart_accounts(id,account_code)values('${uuid(505)}','LOCAL_MATERIAL_INVENTORY');
  insert into erp.accounting_account_mappings values('MATERIAL_INVENTORY','${uuid(505)}');
  update erp.material_adjustments set status='POSTED'where id='${uuid(902)}';
  insert into erp.journal_entries(id,status,source_type,source_id,description)values('${uuid(612)}','${status}','${sourceType}','${uuid(902)}','Native-source account-only original');
  insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,product_id,po_id)values
  ('${uuid(714)}','${uuid(612)}','${uuid(503)}',1,0,null,null),
  ('${uuid(715)}','${uuid(612)}','${uuid(505)}',0,1,${mixed?`'${uuid(21)}'`:'null'},null);`);
 if(reversal)await db.exec(`insert into erp.journal_entries(id,status,source_type,reversal_of_id)values('${uuid(613)}','POSTED','JOURNAL_REVERSAL','${uuid(612)}');
  insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,product_id)values
  ('${uuid(716)}','${uuid(613)}','${uuid(503)}',0,1,null),('${uuid(717)}','${uuid(613)}','${uuid(505)}',1,0,'${uuid(21)}')`);
}
function guarded(r){assert.equal(r.qualified_for_runtime,false);assert.equal(r.runtime_entry,null);assert.equal(r.writer_or_phantom_lock_closed,false)}
function captured(r){
 assert(r.global_source.facts.material_adjustments.some(x=>x.id===uuid(902)));
 assert(r.global_source.facts.journals.some(x=>x.id===uuid(612)));
 assert.equal(r.global_source.facts.journal_lines.filter(x=>x.journal_entry_id===uuid(612)).length,2);
 assert(!r.global_source.facts.document_links.some(x=>x.link_kind==='JOURNAL'&&x.link_id===uuid(612)));
}
async function check(name,prepare,verify){
 await db.exec('begin');try{
  await db.exec("set local local_model.inspecting='off'");await fixture(prepare);
  await db.exec("set local local_model.inspecting='on'");const before=await snapshot(db),r=await inspect(db),after=await snapshot(db);
  assert.deepEqual(before,after);guarded(r);await verify(r);cases.push({name,status:'PASS',observed:r.status,direct_before:before,direct_after:after});
 }finally{await db.exec('rollback')}
}
let failure;
try{
 await check('NATIVE_ACCOUNT_ONLY_ORIGINAL_JOURNAL_CAPTURED_WITHOUT_BC_JOURNAL_LINK',{},r=>{
  captured(r);assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');
  assert(r.scope.outside.journal_ids.includes(uuid(612)));assert(r.outside_source.facts.journals.some(x=>x.id===uuid(612)));
  assert(r.outside_source.facts.journal_lines.filter(x=>x.journal_entry_id===uuid(612)).every(x=>x.product_id===null&&x.po_id===null));
 });
 await check('NULL_CONVERSION_SIDE_MIXED_SIBLING_PULLS_ADJUSTMENT_CONVERSION_INTO_R',{mixed:true},r=>{
  captured(r);assert(r.issues.includes('RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED'));
  assert(r.scope.relevant.adjustment_ids.includes(uuid(902)));assert(r.scope.relevant.product_ids.includes(uuid(22)));assert(r.scope.relevant.product_ids.includes(uuid(23)));
  assert.deepEqual(r.scope.outside.product_ids,[]);
 });
 await check('MIXED_REVERSAL_SIBLING_FOLLOWS_ORIGINAL_ADJUSTMENT_IDENTITY',{reversal:true,status:'REVERSED'},r=>{
  captured(r);assert(r.scope.relevant.journal_ids.includes(uuid(612)));assert(r.scope.relevant.journal_ids.includes(uuid(613)));
  assert(r.issues.includes('RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED'));
 });
 await check('SAME_UUID_OTHER_NATIVE_SOURCE_KIND_IS_NOT_ADJUSTMENT_IDENTITY',{mixed:true,sourceType:'LOCAL_UNRELATED'},r=>{
  assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');assert.deepEqual(r.scope.relevant.product_ids,[uuid(21)]);
  assert.deepEqual(r.scope.outside.product_ids,[uuid(22),uuid(23)]);assert(!r.scope.outside.journal_ids.includes(uuid(612)));
 });
 await check('REVERSED_ACCOUNT_ONLY_ORIGINAL_HISTORY_STILL_CAPTURED',{status:'REVERSED'},r=>{
  captured(r);assert.equal(r.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');
  assert.equal(r.outside_source.facts.journals.find(x=>x.id===uuid(612)).status,'REVERSED');
 });
 let counter=0;
 for(const [table,id]of [['journal_entries',612],['journal_lines',714]]){
  const columns=(await db.query("select a.attname,format_type(a.atttypid,a.atttypmod)type,a.attgenerated from pg_attribute a where a.attrelid=$1::regclass and a.attnum>0 and not a.attisdropped order by a.attnum",['erp.'+table])).rows;
  for(const {attname,type,attgenerated}of columns){
   await db.exec('begin');try{
    await db.exec("set local local_model.inspecting='off'");await fixture();const baseline=await inspect(db);captured(baseline);
    const column='"'+attname+'"';let expression;
    if(attgenerated)expression='economic_date=transaction_date+1';
    else if(type==='uuid')expression=column+`='${uuid(980000+(++counter))}'`;
    else if(/^(numeric|integer|bigint)/.test(type))expression=column+'=coalesce('+column+',0)+1';
    else if(type==='boolean')expression=column+'=not coalesce('+column+',false)';
    else if(type==='date'||type.startsWith('timestamp'))expression=column+"=coalesce("+column+",'2026-10-20')+interval'1 day'";
    else expression=column+"='"+(attname==='status'?'REVERSED':'LOCAL_CHANGED')+"'";
    await db.exec(`update erp.${table} set ${expression} where id='${uuid(id)}';set local local_model.inspecting='on'`);
    const before=await snapshot(db),changed=await inspect(db),after=await snapshot(db);assert.deepEqual(before,after);guarded(changed);
    assert.notEqual(changed.basis_sha256,baseline.basis_sha256,'NATIVE_ORIGINAL_JOURNAL_FIELD_NOT_BOUND:'+table+'.'+attname);
    fields.push({table,column:attname,generated_driver:attgenerated?'economic_date':null,status:'PASS',basis_changed:true,observed:changed.status,direct_before:before,direct_after:after});
   }finally{await db.exec('rollback')}
  }
 }
}catch(error){failure=error}
console.log(JSON.stringify({classification:'LOCAL_TYPED_NATIVE_JOURNAL_IDENTITY_CONTROLS_NOT_NATIVE_BUSINESS',status:failure?'FAIL':'PASS',source_pins:db.localSourcePins,
 counts:{directed_PASS:cases.length,original_journal_field_sensitivity_PASS:fields.length,FAIL:failure?1:0},cases,fields,
 actual_Native:0,actual_DB_server:0,runtime_entry:null,required_final_composition_parent:null,writer_or_phantom_lock_closed:false,production_go:false,independent_acceptance:false},null,2));
await db.close();if(failure){console.error(failure);process.exitCode=1}
