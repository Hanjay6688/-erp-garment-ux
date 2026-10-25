// Actual work DDL/cache guards/K3 with controlled compiler/producer identity.
// No actual Auth, parent installer, Native PG17 or reader-scale qualification.
import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8'),j=JSON.stringify,cases=[]
const block=(s,n)=>{const m=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(m?.length,1,n);return m[0]}
const value=async(s,a=[])=>(await db.query(s,a)).rows[0]?.v
const id=n=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`
const query={from_date:'2026-10-01',through_date:'2026-10-02',group_mode:'AS_SOLD'}
const reference={bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2',bounded_capture_state:'FROZEN',bounded_capsule_hash:'a'.repeat(64),bounded_producer_hash:'b'.repeat(64),captured_at:'2026-10-25T05:06:07.123456Z',status:'INCOMPLETE',bounded_history_inputs:null,bounded_input_coverage:'PENDING'}
const inputs={coverage:'COMPLETE',captured_at:reference.captured_at,query,raw_native_capture_status:'INCOMPLETE',inputs:{targets:[{target_key:'CONTROLLED_ONE',quantity:'9007199254740993'}]}}
const setting=(k,v)=>db.query('select set_config($1,$2,false)',['frozen_reader_control.'+k,typeof v==='string'?v:j(v)])
const job=()=>value('select to_jsonb(x)v from cp7_analysis_stage.jobs x where id=$1',[id(1)])
const call=a=>value('select cp7_frozen_analysis_readers_v2.reference(jsonb_populate_record(null::cp7_analysis_stage.jobs,$1::jsonb))v',[j(a)])
async function test(name,fn){await fn();cases.push({id:name,status:'PASS'})}
try{
 await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create role cp7_alert;create schema extensions;create schema cp7_private;create schema cp7_analysis_stage authorization cp7_capture;create schema cp7_frozen_analysis_v2 authorization cp7_capture;revoke create on schema public from public;')
 await db.exec("create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)where $2='sha256'$$;grant usage on schema extensions to cp7_capture")
 await db.exec(block(await read('scripts/cp7-src/snapshot/bootstrap.sql'),'cp7_private.immutable_run'))
 await db.exec(await read('scripts/cp7-src/wip/bootstrap.sql'))
 const native=await read('scripts/cp7-src/planning/analysis-stages.sql')
 const ddl=native.slice(native.indexOf('create table cp7_analysis_stage.jobs('),native.indexOf('-- Declared bounds, once.'))
 await db.exec(ddl)
 for(const name of['bounds','purge_intermediates'])await db.exec(block(native,'cp7_analysis_stage.'+name))
 await db.exec(`create function cp7_frozen_analysis_v2.prepare(c jsonb,q jsonb,n integer)returns jsonb language plpgsql stable as $$begin
 if current_setting('frozen_reader_control.prepare_forbidden',true)='true'then raise exception 'CONTROLLED_PREPARE_FORBIDDEN';end if;
 if c is distinct from current_setting('frozen_reader_control.reference')::jsonb or q is distinct from current_setting('frozen_reader_control.query')::jsonb or n<>5000 then raise exception 'CONTROLLED_FROZEN_ARGUMENTS_CHANGED';end if;
 return current_setting('frozen_reader_control.inputs')::jsonb;end$$;`)
 await db.exec(await read('scripts/cp7_frozen_analysis_units_v2/cache.sql'))
 await db.exec(block(await read('scripts/cp7_frozen_analysis_units_v2/source.prepared.sql'),'cp7_frozen_analysis_units_v2.coverage'))
 await db.exec("create function cp7_frozen_analysis_units_v2.producer_hash()returns text language sql stable as $$select current_setting('frozen_reader_control.producer')$$")
 const referenceSql=await read('scripts/cp7_frozen_analysis_readers_v2/reference.sql'),readerSql=await read('scripts/cp7_frozen_analysis_readers_v2/reader.prepared.sql')
 await db.exec(referenceSql);await db.exec(readerSql)
 await setting('reference',reference);await setting('query',query);await setting('inputs',inputs);await setting('producer','b'.repeat(64))
 await db.exec('set role cp7_capture')
 await db.query(`insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,captured_at,source_hash,state,unit_count,created_at,updated_at)
 values($1,$2,$3,$4::jsonb,$5::jsonb,$6,'{}',$7,repeat('c',64),'RUNNING',1,now(),now())`,[id(1),id(2),id(3),j(query),j(reference),id(4),reference.captured_at])
 await db.query("insert into cp7_analysis_stage.units(job_id,idx,kind,chunk,lo,hi)values($1,0,'HIST_PREP',0,0,0)",[id(1)])
 const running=await job()
 await test('RUNNING_PENDING_IS_NOT_PROMOTED_TO_FINISHED_READER',async()=>{await assert.rejects(()=>call(running),/CP7_FROZEN_READER_REFERENCE_REQUIRED/)})
 await value('select cp7_frozen_analysis_units_v2.unit_reference(j,u)v from cp7_analysis_stage.jobs j join cp7_analysis_stage.units u on u.job_id=j.id where j.id=$1',[id(1)])
 await db.query("update cp7_analysis_stage.jobs set state='DONE',units_done=unit_count,plan_final=true where id=$1",[id(1)])
 const done=await job(),snapshot=()=>value("select jsonb_build_object('jobs',(select jsonb_agg(to_jsonb(x)order by id)from cp7_analysis_stage.jobs x),'cache',(select jsonb_agg(to_jsonb(x)order by job_id,kind,ord)from cp7_analysis_stage.target_rows x),'units',(select jsonb_agg(to_jsonb(x)order by job_id,idx)from cp7_analysis_stage.units x))v")
 const before=await snapshot()
 await test('BOUND_CACHE_READS_EXACT_INPUTS_WITHOUT_COMPILER_OR_WRITES',async()=>{
  await setting('prepare_forbidden','true')
  const out=await call(done)
  assert.deepEqual(out,{...reference,bounded_history_inputs:inputs,bounded_input_coverage:'COMPLETE'})
  assert.deepEqual(await snapshot(),before)
 })
 await test('FOREIGN_ACTOR_REQUEST_RUN_QUERY_BINDINGS_REFUSED',async()=>{
  for(const mutate of[x=>{x.actor=id(9)},x=>{x.request_id=id(9)},x=>{x.run_id=id(9)},x=>{x.query.group_mode='RESTATED'}]){
   const forged=structuredClone(done);mutate(forged);await assert.rejects(()=>call(forged),/CP7_FROZEN_UNIT_CACHE_BINDING/)
  }
  await assert.rejects(()=>call({...done,reference:{...reference,bounded_request_contract:'cp7.bounded-analysis-request.v1'}}),/CP7_FROZEN_READER_REFERENCE_REQUIRED/)
  assert.deepEqual(await snapshot(),before)
 })
 await test('CHANGED_PRODUCER_REFUSES_BEFORE_CACHE_OR_COMPILATION',async()=>{
  await setting('producer','e'.repeat(64));await assert.rejects(()=>call(done),/CP7_PRODUCT_ANALOG_PRODUCER_CHANGED/)
  await setting('producer','b'.repeat(64));assert.deepEqual(await snapshot(),before)
 })
 await test('ACTUAL_K3_THEN_PURE_FROZEN_RECOMPILE_KEEPS_REFERENCE_AND_NO_NEW_CACHE',async()=>{
  const removed=await value('select cp7_analysis_stage.purge_intermediates($1)v',[id(1)]);assert.equal(removed.removed.target_rows,1)
  await assert.rejects(()=>call(done),/CONTROLLED_PREPARE_FORBIDDEN/)
  const afterPurge=await snapshot();await setting('prepare_forbidden','false')
  assert.deepEqual((await call(done)).bounded_history_inputs,inputs)
  assert.deepEqual(await snapshot(),afterPurge);assert.deepEqual(await job(),done)
 })
 await db.exec('reset role')
 await test('EXPLICIT_PUBLIC_OWNER_ACL_AND_PRIVATE_REFERENCE_CLOSED',async()=>{
  const publicSig='public.erp_cp7_read_product_analog_candidates_v2(uuid,text,integer,integer,text)'
  const authority=await value("select jsonb_build_object('owner',pg_get_userbyid(proowner),'definer',prosecdef,'settings',proconfig)v from pg_proc where oid=$1::regprocedure",[publicSig])
  assert.deepEqual(authority,{owner:'cp7_capture',definer:true,settings:['search_path=""','TimeZone=UTC']})
  assert.equal(await value("select has_schema_privilege('cp7_capture','public','CREATE')v"),false)
  for(const role of['anon','authenticated','service_role','cp7_alert']){
   assert.equal(await value("select has_function_privilege($1,$2,'EXECUTE')v",[role,publicSig]),role==='authenticated')
   await db.exec('set role '+role);await assert.rejects(()=>call(done),/permission denied/);await db.exec('reset role')
  }
 })
 const report={contract:'cp7.frozen-reader-local-controls.v2',status:'PASS',cases,counts:{PASS:cases.length},
  reference_sql_sha256:createHash('sha256').update(referenceSql).digest('hex'),reader_sql_sha256:createHash('sha256').update(readerSql).digest('hex'),
  server_version:await value('select version()v'),controlled_compiler_and_producer:true,actual_Native:false,actual_Auth_HTTP_credit:false,
  Python_catalog_installer_qualified:false,actual_candidate_math_or_scale_qualified:false,public_or_default_request_adopted:false,production_go:false}
 if(process.env.CP7_FROZEN_READER_REPORT)await writeFile(process.env.CP7_FROZEN_READER_REPORT,j(report)+'\n')
 console.log(j(report))
}finally{await db.close()}
