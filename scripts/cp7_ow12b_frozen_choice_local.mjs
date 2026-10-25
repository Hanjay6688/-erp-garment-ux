// Actual v2 pure normalization and catalog authority; not command execution.
import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8'),j=JSON.stringify,cases=[]
const block=(s,n)=>{const m=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(m?.length,1,n);return m[0]}
const value=async(s,a=[])=>(await db.query(s,a)).rows[0]?.v
const call=(a,b,c)=>value('select cp7_frozen_analysis_choice_v2.normalize_confirmed_delta($1::jsonb,$2::jsonb,$3::jsonb)v',[j(a),j(b),j(c)])
const previous={target_key:'target-A:size-1',choice_id:null,revision:'0',action:null,evidence:null,reason:null,actor_scope_id:null,recorded_at:null,request_id:null,state:'UNREVIEWED'}
const other={...previous,target_key:'target-B:size-1'}
const receipt={contract_version:'cp7.product-analog-choice-outcome.v2',target_key:previous.target_key,choice_id:'choice-1',revision:'1',action:'CONFIRM',evidence:{immutable:'captured evidence'},reason:'Reviewed same physical size',actor_scope_id:'actor-1',recorded_at:'2026-10-25T01:02:03.123456Z',request_id:'command-1',state:'CONFIRMED_ASSUMPTION',forecast_applied:false,production_go:false}
const chosen=Object.fromEntries(Object.entries(receipt).filter(([k])=>!['contract_version','forecast_applied','production_go'].includes(k)))
const before={captured_at:'2026-10-25T01:00:00Z',facts:{stock:'9007199254740993'},product_analog_choices:[previous,other]}
const after={...before,captured_at:'2026-10-25T01:02:03.123457Z',product_analog_choices:[chosen,other]}
async function test(id,fn){await fn();cases.push({id,status:'PASS'})}
try{
 await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create role cp7_alert;create schema cp7_private;create schema cp7_analysis_stage authorization cp7_capture;revoke create on schema public from public;')
 await db.exec(block(await read('scripts/cp7-src/snapshot/bootstrap.sql'),'cp7_private.immutable_run'))
 await db.exec(await read('scripts/cp7-src/wip/bootstrap.sql'))
 const native=await read('scripts/cp7-src/planning/analysis-stages.sql')
 await db.exec(native.slice(native.indexOf('create table cp7_analysis_stage.jobs('),native.indexOf('-- Declared bounds, once.')))
 const choice=await read('scripts/cp7_product_analog_choice_stage/choice.sql')
 await db.exec(choice.slice(0,choice.indexOf('create function cp7_product_analog_choice.material(')))
 const sql=await read('scripts/cp7_frozen_analysis_choice_v2/choice.prepared.sql');await db.exec(sql)
 await db.exec('set role cp7_capture')
 await test('EXACT_V2_OWN_CHOICE_DELTA_NORMALIZES_ONLY_OWN_METADATA',async()=>{
  assert.deepEqual(await call(before,after,receipt),{...after,product_analog_choices:before.product_analog_choices})
  const changed={...after,facts:{stock:'9007199254740994'}}
  const normalized=await call(before,changed,receipt);assert.deepEqual(normalized.facts,changed.facts);assert.notDeepEqual(normalized.facts,before.facts)
 })
 await test('OLD_RECEIPT_CANNOT_MASQUERADE_AS_V2',async()=>{await assert.rejects(()=>call(before,after,{...receipt,contract_version:'cp7.product-analog-choice-outcome.v1'}),/CP7_ANALOG_CONSUMER_OWN_DELTA_SHAPE/)})
 await test('SKIPPED_REVISION_AND_DUPLICATE_TARGET_REFUSED',async()=>{
  await assert.rejects(()=>call(before,after,{...receipt,revision:'2'}),/CP7_ANALOG_CONSUMER_OWN_DELTA_REVISION/)
  await assert.rejects(()=>call({...before,product_analog_choices:[previous,previous,other]},after,receipt),/CP7_ANALOG_CONSUMER_OWN_DELTA_SCOPE/)
 })
 await test('OTHER_CHOICE_CHANGE_INSERTION_OR_REORDER_NOT_HIDDEN',async()=>{
  for(const choices of[[chosen,{...other,revision:'1'}],[chosen,other,{...other,target_key:'target-C:size-1'}],[other,chosen]]){
   await assert.rejects(()=>call(before,{...after,product_analog_choices:choices},receipt),/CP7_ANALOG_CHOICE_UNEXPECTED_CHOICE_DELTA/)
  }
 })
 await test('OWN_EVIDENCE_REASON_ACTOR_OR_CLOCK_NOT_REPLACED',async()=>{
  for(const delta of[{evidence:{immutable:'changed'}},{reason:'changed'},{actor_scope_id:'actor-2'},{recorded_at:'2026-10-25T01:02:03.123457Z'}]){
   await assert.rejects(()=>call(before,{...after,product_analog_choices:[{...chosen,...delta},other]},receipt),/CP7_ANALOG_CHOICE_UNEXPECTED_CHOICE_DELTA/)
  }
 })
 await test('EXTRA_RECEIPT_FIELD_AND_APPLIED_FORECAST_REFUSED',async()=>{
  await assert.rejects(()=>call(before,after,{...receipt,extra:true}),/CP7_WIP_FIELDS/)
  await assert.rejects(()=>call(before,after,{...receipt,forecast_applied:true}),/CP7_ANALOG_CONSUMER_OWN_DELTA_SHAPE/)
 })
 await db.exec('reset role')
 await test('ACTUAL_NEW_OWNER_ACL_EMPTY_PATH_PRIVATE_CLOSED',async()=>{
  const names=['cp7_frozen_analysis_choice_v2.normalize_confirmed_delta(jsonb,jsonb,jsonb)','cp7_frozen_analysis_choice_v2.apply(jsonb,uuid)','public.erp_cp7_save_product_analog_choice_v2(jsonb,uuid)']
  for(const [i,sig]of names.entries()){
   const row=(await db.query('select pg_get_userbyid(proowner)owner,prosecdef,provolatile,proconfig from pg_proc where oid=$1::regprocedure',[sig])).rows[0]
   assert.deepEqual(row,{owner:'cp7_capture',prosecdef:i===2,provolatile:i===0?'i':'v',proconfig:['search_path=""','TimeZone=UTC']})
   for(const role of['anon','authenticated','service_role','cp7_alert'])assert.equal(await value("select has_function_privilege($1,$2,'EXECUTE')v",[role,sig]),i===2&&role==='authenticated')
  }
  for(const role of['anon','authenticated','service_role','cp7_alert'])assert.equal(await value("select has_schema_privilege($1,'cp7_frozen_analysis_choice_v2','USAGE')v",[role]),false)
  assert.equal(await value("select has_schema_privilege('cp7_capture','public','CREATE')v"),false)
 })
 const report={contract:'cp7.frozen-choice-local-preparation.v2',status:'PASS',cases,counts:{PASS:cases.length},sql_sha256:createHash('sha256').update(sql).digest('hex'),server_version:await value('select version()v'),actual_pure_normalizer_and_DDL:true,actual_CONFIRM_or_CLEAR_command_executed:false,actual_Native:false,actual_Auth_HTTP_credit:false,Python_catalog_installer_qualified:false,default_or_UI_adopted:false,production_go:false}
 if(process.env.CP7_FROZEN_CHOICE_LOCAL_REPORT)await writeFile(process.env.CP7_FROZEN_CHOICE_LOCAL_REPORT,j(report)+'\n')
 console.log(j(report))
}finally{await db.close()}
