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
async function test(id,fn){const result=await fn();cases.push({id,status:'PASS',...result})}
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
 await test('ACTUAL_MATERIAL_AND_ADVISORY_REUSE_OUTPUT_REFUSAL_PARITY',async()=>{
  // Only the upstream physical fingerprint is controlled here. Input binding,
  // candidate ranking, integer arithmetic and both material bodies are actual SQL.
  await db.exec("create schema cp7_bounded_analysis_stage;create function cp7_bounded_analysis_stage.work_fingerprint(jsonb)returns text language sql immutable as $$select 'controlled physical fingerprint'::text$$;")
  await db.exec(block(await read('scripts/cp7_bounded_analysis_stage/stage.sql'),'cp7_bounded_analysis_stage.require_inputs'))
  await db.exec(await read('scripts/cp7_product_analog_stage/candidates.sql'))
  await db.exec(block(choice,'cp7_product_analog_choice.material'))
  const target='target:size-1',source='source:size-1',other='other:size-2',q={from_date:'2026-10-01',through_date:'2026-10-01',group_mode:'AS_SOLD'},at='2026-10-25T01:00:00.123456Z'
  const products=[{root_id:'target',size_id:'size-1',sku:'T'},{root_id:'source',size_id:'size-1',sku:'S'},{root_id:'other',size_id:'size-2',sku:'O'}]
  const histories=[target,source,other].map(target_key=>({target_key,available_days:'1',available_sales_mean:'0',days:[{state:'AVAILABLE',gross_observed_pcs:'0'}],refs:[]}))
  const base={captured_at:at,status:'INCOMPLETE',bounded_query:q,facts:{products},profiles:[{root_id:'target',profile_id:'profile-1',revision:'1',quality:'SELECTED_ASSUMPTION',config:{minimum_available_days:'1'}}],bounded_history_inputs:{contract_version:'cp7.bounded-history-inputs.v1',coverage:'COMPLETE',captured_at:at,query:q,raw_native_capture_status:'INCOMPLETE',raw_native_status_overridden:false,inputs:{contract_version:'cp7.reorder-native-inputs.v1',captured_at:at,query:q,products,source_hash:'a'.repeat(64),history_hash:'b'.repeat(64),history:histories,current_stock:[target,source,other].map(target_key=>({target_key})),targets:[target,source,other].map(target_key=>({target_key}))}}}
  const outcomes=[]
  const scenarios=[['zero',()=>{},source],['wide integer',c=>{c.bounded_history_inputs.inputs.history[1].days[0].gross_observed_pcs='9007199254740993'},source],['self',()=>{},target],['missing',()=>{},'missing:size-1'],['other size',()=>{},other],['unknown',c=>{c.bounded_history_inputs.inputs.history[1].available_sales_mean=null},source],['insufficient',c=>{c.profiles[0].config.minimum_available_days='2'},source],['day count',c=>{c.bounded_history_inputs.inputs.history[1].available_days='2'},source],['profile missing',c=>{c.profiles=[]},source],['duplicate history',c=>{c.bounded_history_inputs.inputs.history[2]=c.bounded_history_inputs.inputs.history[1]},source],['binding changed',c=>{c.bounded_history_inputs.query={...q,group_mode:'RESTATED'}},source],['negative PCS',c=>{c.bounded_history_inputs.inputs.history[1].days[0].gross_observed_pcs='-1'},source]]
  for(const[label,change,key]of scenarios){
   const c=structuredClone(base);change(c)
   const capture=async fn=>{try{return{value:await fn()}}catch(e){return{code:e.code,message:e.message}}}
   const old=await capture(()=>value('select cp7_product_analog_choice.material($1::jsonb,$2,$3)v',[j(c),target,key]))
   const next=await capture(async()=>{const envelope=await value('select cp7_product_analog_stage.candidates($1::jsonb,$2,0,1)v',[j(c),target]);return value('select cp7_frozen_analysis_choice_v2.material($1::jsonb,$2,$3,$4::jsonb)v',[j(c),target,key,j(envelope)])})
   assert.deepEqual(next,old,label);if(label==='zero')assert.equal(next.value.available_total_pcs,'0');if(label==='wide integer')assert.equal(next.value.available_total_pcs,'9007199254740993');if(!['zero','wide integer'].includes(label))assert.ok(next.code,label);outcomes.push({label,status:'PASS',refused:!!next.code})
  }
  return{cases:outcomes,actual_old_and_new_material_and_advisory:true,controlled_upstream_physical_fingerprint:true}
 })
 await test('ACTUAL_NEW_OWNER_ACL_EMPTY_PATH_PRIVATE_CLOSED',async()=>{
  const names=['cp7_frozen_analysis_choice_v2.normalize_confirmed_delta(jsonb,jsonb,jsonb)','cp7_frozen_analysis_choice_v2.material(jsonb,text,text,jsonb)','cp7_frozen_analysis_choice_v2.review_context(uuid,text,integer,integer,text)','cp7_frozen_analysis_choice_v2.apply(jsonb,uuid)','public.erp_cp7_save_product_analog_choice_v2(jsonb,uuid)']
  for(const [i,sig]of names.entries()){
   const row=(await db.query('select pg_get_userbyid(proowner)owner,prosecdef,provolatile,proconfig from pg_proc where oid=$1::regprocedure',[sig])).rows[0]
   assert.deepEqual(row,{owner:'cp7_capture',prosecdef:i===4,provolatile:i<2?'i':'v',proconfig:['search_path=""','TimeZone=UTC']})
   for(const role of['anon','authenticated','service_role','cp7_alert'])assert.equal(await value("select has_function_privilege($1,$2,'EXECUTE')v",[role,sig]),i===4&&role==='authenticated')
  }
  for(const role of['anon','authenticated','service_role','cp7_alert'])assert.equal(await value("select has_schema_privilege($1,'cp7_frozen_analysis_choice_v2','USAGE')v",[role]),false)
  assert.equal(await value("select has_schema_privilege('cp7_capture','public','CREATE')v"),false)
 })
 const report={contract:'cp7.frozen-choice-local-preparation.v2',status:'PASS',cases,counts:{PASS:cases.length},sql_sha256:createHash('sha256').update(sql).digest('hex'),server_version:await value('select version()v'),actual_pure_normalizer_and_DDL:true,actual_CONFIRM_or_CLEAR_command_executed:false,actual_Native:false,actual_Auth_HTTP_credit:false,Python_catalog_installer_qualified:false,default_or_UI_adopted:false,production_go:false}
 if(process.env.CP7_FROZEN_CHOICE_LOCAL_REPORT)await writeFile(process.env.CP7_FROZEN_CHOICE_LOCAL_REPORT,j(report)+'\n')
 console.log(j(report))
}finally{await db.close()}
