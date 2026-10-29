// Complete actual materialize_v1, local typed/guard doubles only. No DB server.
import { createRequire } from 'node:module'
import { readFile, writeFile, access } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import assert from 'node:assert/strict'
const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../..')
const modulePath=process.env.CP7_PGLITE_MODULE,dump=process.env.D1_RETAINED_ERP_DUMP,destination=process.env.D1_MATERIALIZE_LOCAL_RECEIPT
if(!modulePath||!dump||!destination)throw Error('Explicit installed PGlite, retained ERP dump and new receipt path required; no download/DB-server fallback')
try{await access(destination);throw Error('Receipt exists; refusing overwrite')}catch(e){if(e.code!=='ENOENT')throw e}
const {PGlite}=createRequire(import.meta.url)(modulePath),db=new PGlite()
const sha=raw=>createHash('sha256').update(raw).digest('hex')
const report={classification:'LOCAL_PGLITE_FULL_MATERIALIZE_SQL_WITH_TYPED_GUARD_DOUBLES_NOT_NATIVE',Native_executions:0,actual_financial_Native_cases:0,DB_server:false,remote_calls:0,production_go:false,independent_acceptance:false,cases:[],steps:[]}
const q=async(sql,params=[])=>{try{return(await db.query(sql,params,{rowMode:'array'})).rows}catch(e){report.last_SQL={sql,params,error:{code:e.code,message:e.message,detail:e.detail,where:e.where}};throw e}}
const exec=async sql=>{try{return await db.exec(sql,{rowMode:'array'})}catch(e){report.last_SQL={sql,error:{code:e.code,message:e.message,detail:e.detail,where:e.where}};throw e}}
const scalar=async(sql,params=[])=>(await q(sql,params))[0][0]
const ident=s=>'"'+s.replaceAll('"','""')+'"'
const id=n=>'00000000-0000-4000-8000-'+BigInt(n).toString(16).padStart(12,'0')
const ids=Object.fromEntries(['operation','actor','request','sale','old_return','replacement','customer','location','allocation','ar','credit_account','family','cohort','old_plan','old_component','old_part','old_credit_journal','replacement_journal','link','before_journal','added_journal','old_return_journal','product','lot','old_materialization'].map((k,i)=>[k,id(i+1)]))
const beforeRaw=await readFile(resolve(here,'evidence/BEFORE_materialize.sql'),'utf8')
const afterRaw=await readFile(resolve(root,'scripts/cp7_credit_correction_de/materialize.sql'),'utf8')
const declaration=text=>text.slice(0,text.indexOf('$$;',text.indexOf('as $$')+5)+3)
const before=declaration(beforeRaw),after=declaration(afterRaw)
const fixture=JSON.parse(execFileSync('python3',[resolve(here,'fixture.py'),dump],{encoding:'utf8',maxBuffer:15e6,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}}))
let base
async function census(){
 const session=(await q("select current_user::text,session_user::text,current_setting('role'),current_setting('search_path'),current_setting('TimeZone')"))[0]
 await q("select set_config('search_path','',false),set_config('TimeZone','UTC',false)")
 try{
  const catalog={}
  for(const [key,sql]of Object.entries(fixture.catalog_queries))catalog[key]=Object.fromEntries(await q(sql))
  const tables=await q("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p','m')and n.nspname<>all(array['pg_catalog','information_schema','cron'])and n.nspname!~'^pg_'order by 1,2")
  const rows={}
  for(const [schema,name]of tables)rows[schema+'.'+name]=await scalar('select coalesce(jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text),\'[]\'::jsonb)from '+ident(schema)+'.'+ident(name)+' r')
  const sequences={}
  for(const [schema,name]of await q("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='S'and n.nspname!~'^pg_'and n.nspname<>'information_schema'order by 1,2"))sequences[schema+'.'+name]=(await q('select last_value::text,is_called from '+ident(schema)+'.'+ident(name)))[0]
  const other=await q('select pid,usename::text,application_name,state from pg_stat_activity where pid<>pg_backend_pid()order by pid')
  const advisory=await scalar("select count(*)from pg_locks where locktype='advisory'")
  return {catalog,rows,sequences,session,other_sessions:other,advisory_locks:advisory}
 }finally{await q("select set_config('search_path',$1,false),set_config('TimeZone',$2,false)",[session[3],session[4]])}
}
async function put(table,value){
 const columns=Object.keys(value),args=columns.map(k=>value[k])
 await q('insert into '+table+'('+columns.join(',')+')values('+columns.map((_,i)=>'$'+(i+1)).join(',')+')',args)
}
async function seed({components=['50.00'],partMax='100.00',failFinal=false}={}){
 const date='2026-10-02',physical='2026-10-02T05:00:00.123456+00:00'
 const pieces=components.map((amount,i)=>({amount,economic_date:date,transaction_date:date,previous_economic_date:null,previous_transaction_date:null,corners:{LOCAL_STRUCTURAL_CORNER:i+1}}))
 const event=(kind,journal,amount)=>({id:'journal:'+journal,kind,amount,economic_date:date,transaction_date:date,source_sha256:'a'.repeat(64)})
 const kernel={kernel_version:'LOCAL_DECLARED_KERNEL_NOT_FINANCIAL_PROOF',net_current_k:'50.00',components:pieces,before_events:[event('NET',ids.before_journal,'200.00')],added_events:[event('NET',ids.added_journal,'50.00')],before_source_sha256:'b'.repeat(64),after_source_sha256:'c'.repeat(64),support:{LOCAL_ONLY:true}}
 const family={registration:{family_id:ids.family},has_reconciliation_effect:true,plan_kind:'ADJUSTMENT',reconciliation_components:pieces,LOCAL_DECLARED_KERNEL:kernel}
 const review={requires_undo:false,credit_delta:'50.00',review_token:'a'.repeat(64),families:[{family_id:ids.family,vector:pieces,needs_cohort_configuration:false}]}
 const beforeSource={LOCAL_SOURCE_DOUBLE:true,sale:{id:ids.sale,customer_id:ids.customer},state:'BEFORE'}
 const actualSource={...beforeSource,state:'AFTER_NATIVE_REPLACEMENT_DECLARED_NOT_EXECUTED'}
 const retained={object_kind:'PART_JOURNAL',object_id:ids.old_part,fact_sha256:'d'.repeat(64)}
 const control={...ids,part_max:partMax,fail_final:failFinal,before_source:beforeSource,actual_source:actualSource,before_input:{LOCAL_INPUT:'BEFORE'},after_input:{LOCAL_INPUT:'AFTER'},result:{families:[family]},review,before_profile:{actual_objects:[retained]}}
 await put('local_materialize_fixture.settings',{value:control})
 await put('erp.sales_returns',{id:ids.old_return,sale_id:ids.sale,customer_id:ids.customer,physical_at:physical,notes:null,status:'REVERSED',return_number:'LOCAL-OLD'})
 await put('erp.sales_returns',{id:ids.replacement,sale_id:ids.sale,customer_id:ids.customer,physical_at:physical,notes:null,status:'POSTED',return_number:'K-'+ids.request})
 await put('erp.sales_return_items',{id:id(50),return_id:ids.replacement,sale_stock_allocation_id:ids.allocation,product_id:ids.product,lot_id:ids.lot,location_id:ids.location,qty_pcs:2,quality_grade:'GRADE_A',refund_amount:'250.00',unit_hpp_snapshot:'10.000000',notes:null})
 await put('cp7_sales_return_correction.links',{id:ids.link,original_id:ids.old_return,replacement_id:ids.replacement,sale_id:ids.sale,actor:ids.actor,request_id:ids.request,reason:'LOCAL_ONLY'})
 await put('cp7_credit.return_families',{id:ids.family,family_root_sale_id:ids.sale,family_ordinal:1,first_return_id:ids.old_return})
 await put('cp7_credit.return_family_members',{family_id:ids.family,return_id:ids.old_return,member_kind:'ORIGINAL',source_journal_id:ids.old_return_journal,financial_state:'JOURNAL'})
 await put('cp7_credit.cohorts',{id:ids.cohort,family_id:ids.family,ar_account_id:ids.ar,credit_account_id:ids.credit_account})
 await put('cp7_credit.recognition_plans',{id:ids.old_plan,cohort_id:ids.cohort,plan_kind:'INITIAL'})
 await put('cp7_credit.recognition_components',{id:ids.old_component,plan_id:ids.old_plan,ordinal:1,amount:'200.00'})
 await put('cp7_credit.component_parts',{id:ids.old_part,component_id:ids.old_component,ordinal:1,amount:'200.00'})
 await put('cp7_credit.component_journals',{part_id:ids.old_part,journal_id:ids.old_credit_journal,economic_date:date,transaction_date:date,lines_sha256_pg:'a'.repeat(64)})
 await put('cp7_credit.financial_materialization_objects',{object_kind:'PART_JOURNAL',object_id:ids.old_part,materialization_id:ids.old_materialization,fact_sha256:retained.fact_sha256})
 for(const journal of [ids.before_journal,ids.added_journal,ids.old_credit_journal,ids.replacement_journal,ids.old_return_journal])await put('erp.journal_entries',{id:journal,source_type:journal===ids.replacement_journal?'SALES_RETURN':'LOCAL_DECLARED_SOURCE',source_id:journal===ids.replacement_journal?ids.replacement:ids.old_part,status:'POSTED',economic_date:date,transaction_date:date})
 const [pid,transaction]=(await q('select pg_backend_pid(),txid_current()'))[0]
 const payload={change_reason:'LOCAL typed materialize runtime check',replacement:{physical_at:physical,notes:null,items:[{allocation_id:ids.allocation,location_id:ids.location,qty_pcs:'2',quality_grade:'GRADE_A',refund_amount:'250.00',notes:null}]}}
 await put('cp7_credit_correction_de.work_v1',{operation_id:ids.operation,operation_ordinal:1,predecessor_id:null,backend_pid:pid,transaction_id:transaction,actor:ids.actor,request_id:ids.request,sale_id:ids.sale,return_id:ids.old_return,replacement_id:ids.replacement,expected_version:'1',payload,authority:{LOCAL_AUTHORITY_DOUBLE:true},period:{LOCAL_PERIOD_DOUBLE:true},before_source:beforeSource,before_input:control.before_input,before_profile:control.before_profile,review,phase:'POSTED'})
 return {control,kernel,components:pieces}
}
async function install(source){await exec('drop function if exists cp7_credit_correction_de.materialize_v1(uuid)');await exec(source)}
async function scenario(name,{original=false,expectedError=null,privateHook=false,...options}={}){
 await install(original?before:after)
 const globalBefore=await census()
 await exec('begin');await seed(options)
 if(privateHook)await exec(fixture.failure_hook)
 const initial=await census();await exec('savepoint local_materialize_call')
 const row={name,original,source_sha256:sha(original?before:after),expected_error:expectedError,scope:'FULL_ACTUAL_MATERIALIZE_SQL_WITH_DECLARED_DOUBLES',before:initial}
 try{
  await q('select cp7_credit_correction_de.materialize_v1($1)',[ids.replacement])
  if(expectedError)throw Error('Expected error did not occur:'+expectedError)
  const state=await census();row.after=state
  const work=state.rows['cp7_credit_correction_de.work_v1'][0]
  assert.equal(work.phase,'MATERIALIZED');assert.equal(work.manifest.length,1)
  assert.equal(work.manifest[0].components.length,(options.components||['50.00']).length)
  assert.equal(state.rows['cp7_credit.plan_support_events'].length,2)
  assert.deepEqual(state.rows['cp7_credit.plan_support_events'].map(r=>r.phase).sort(),['ADDED','BEFORE'])
  const newParts=state.rows['cp7_credit_correction_de.parts_v1'];assert.equal(newParts.length,work.manifest[0].parts.length)
  assert.equal(state.rows['cp7_credit.financial_materializations'].length,1)
  assert.equal(state.rows['cp7_credit.financial_materialization_objects'].length,1+newParts.length)
  assert.equal(state.rows['cp7_credit_correction_de.posting_v1'].length,0)
  assert.deepEqual(state.sequences,initial.sequences);assert.deepEqual(state.session,initial.session)
  assert.equal(state.advisory_locks,0);assert.deepEqual(state.other_sessions,[])
  assert.deepEqual(state.catalog,initial.catalog)
  row.observed={phase:work.phase,plans:work.manifest.length,components:work.manifest[0].components.length,parts:newParts.length,support_phases:['BEFORE','ADDED'],journal_links:state.rows['cp7_credit.component_journals'].length-1,objects:newParts.length,full_actual_function_returned:true,Native_guards:'LOCAL_DOUBLES_ONLY'}
  row.status='PASS_LOCAL_TYPED_RUNTIME'
 }catch(error){
  row.error={code:error.code,message:error.message,detail:error.detail,where:error.where}
  if(!expectedError||!(error.code===expectedError||error.message===expectedError))throw Object.assign(error,{local_case:name})
  if(privateHook){const detail=JSON.parse(error.detail);assert.equal(detail.actual_Native_credit_journal_inserted,true);row.retained_hook_detail_LOCAL_GUARDS_ARE_DOUBLES=detail}
  row.status='PASS_EXPECTED_LOCAL_ERROR'
 }finally{
  await exec('rollback to savepoint local_materialize_call');await exec('release savepoint local_materialize_call')
  const restored=await census();assert.deepEqual(restored,initial,'FULL_LOCAL_ROWS_CATALOG_SEQUENCES_SESSIONS_NOT_RESTORED:'+name)
  row.after_rollback=restored;row.full_local_rows_catalog22_sequences_sessions_restored=true
  await exec('rollback');assert.deepEqual(await census(),globalBefore,'WHOLE_LOCAL_SCENARIO_NOT_REMOVED:'+name)
  report.cases.push(row)
 }
}
try{
 report.version=await scalar('select version()');report.PGlite_version=JSON.parse(await readFile(resolve(modulePath,'package.json'),'utf8')).version
 report.fixture={...fixture};delete report.fixture.ddl;delete report.fixture.catalog_queries;delete report.fixture.failure_hook
 await exec(fixture.ddl)
 await exec(await readFile(resolve(root,'scripts/cp7_credit_correction_de/facts.sql'),'utf8'))
 await exec(await readFile(resolve(here,'doubles.sql'),'utf8'))
 await exec("set timezone='Asia/Tokyo'")
 await scenario('ORIGINAL_42702_REPRO',{original:true,expectedError:'42702'})
 await scenario('REPAIRED_FULL_SINGLE_COMPONENT')
 await scenario('REPAIRED_FULL_TWO_COMPONENT_THREE_PART',{components:['17.35','32.65'],partMax:'20.00'})
 await scenario('REPAIRED_REAL_RETAINED_PRIVATE_HOOK_LOCAL_GUARDS',{privateHook:true,expectedError:'CP7_CREDIT_DE_TEST_PART_FAILURE'})
 await scenario('REPAIRED_FINAL_PROFILE_DOUBLE_ERROR_ATOMIC',{failFinal:true,expectedError:'LOCAL_AFTER_FINAL_PROFILE_FAILURE'})
 report.status='PASS_LOCAL_TYPED_RUNTIME_ONLY'
}catch(error){report.status='FAIL_LOCAL_TYPED_RUNTIME_ONLY';report.error={code:error.code,message:error.message,detail:error.detail,where:error.where,case:error.local_case};process.exitCode=1}
finally{
 await db.close()
 report.sources={}
 for(const path of [resolve(here,'runtime.mjs'),resolve(here,'fixture.py'),resolve(here,'doubles.sql'),resolve(here,'evidence/BEFORE_materialize.sql'),resolve(root,'scripts/cp7_credit_correction_de/materialize.sql'),resolve(root,'scripts/cp7_credit_correction_de/facts.sql'),resolve(root,'scripts/cp7_credit_correction_de/cases.py')]){const raw=await readFile(path);report.sources[path.startsWith(root+'/')?path.slice(root.length+1):path]={bytes:raw.length,sha256:sha(raw)}}
 await writeFile(destination,JSON.stringify(report,null,2)+'\n',{flag:'wx'})
 process.stdout.write(JSON.stringify({status:report.status,cases:report.cases.map(r=>({name:r.name,status:r.status,error:r.error,observed:r.observed})),error:report.error,Native_executions:0,receipt:destination})+'\n')
}
