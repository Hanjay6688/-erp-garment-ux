// Actual Native work-table DDL/triggers, controlled prepare only. No Native credit.
import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8'),j=JSON.stringify,cases=[]
const block=(s,n)=>{const m=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(m?.length,1,n);return m[0]}
const value=async(s,a=[])=>(await db.query(s,a)).rows[0]?.v
const id=n=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`
const query={from_date:'2026-10-01',through_date:'2026-10-02',group_mode:'AS_SOLD'}
const reference={bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_capture_state:'FROZEN',
 bounded_capsule_hash:'a'.repeat(64),bounded_producer_hash:'b'.repeat(64),captured_at:'2026-10-25T05:06:07.123456Z',
 status:'INCOMPLETE',bounded_history_inputs:null,bounded_input_coverage:'PENDING'}
const inputs={coverage:'COMPLETE',captured_at:reference.captured_at,query,raw_native_capture_status:'INCOMPLETE',
 inputs:{targets:[{target_key:'CONTROLLED_ONE',quantity:'9007199254740993'}]}}
const job=async(n)=>value('select to_jsonb(x)v from cp7_analysis_stage.jobs x where id=$1',[id(n)])
const unit=async(n,idx)=>value('select to_jsonb(x)v from cp7_analysis_stage.units x where job_id=$1 and idx=$2',[id(n),idx])
const call=(a,b)=>value('select cp7_frozen_analysis_units_v2.unit_reference(jsonb_populate_record(null::cp7_analysis_stage.jobs,$1::jsonb),jsonb_populate_record(null::cp7_analysis_stage.units,$2::jsonb))v',[j(a),j(b)])
const unpack=(a,p)=>value('select cp7_frozen_analysis_units_v2.unpack(jsonb_populate_record(null::cp7_analysis_stage.jobs,$1::jsonb),$2::jsonb)v',[j(a),j(p)])
const cached=n=>value("select payload v from cp7_analysis_stage.target_rows where job_id=$1 and kind='FROZEN_INPUTS_V2'",[id(n)])
const setting=(k,v)=>db.query('select set_config($1,$2,false)',['frozen_unit_control.'+k,typeof v==='string'?v:j(v)])
async function test(name,fn){await fn();cases.push({id:name,status:'PASS'})}
async function seed(n){
 await db.query(`insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,captured_at,source_hash,state,unit_count,created_at,updated_at)
 values($1,$2,$3,$4::jsonb,$5::jsonb,$6,'{}',$7,repeat('c',64),'RUNNING',2,now(),now())`,[id(n),id(20),id(100+n),j(query),j(reference),id(200+n),reference.captured_at])
 await db.query("insert into cp7_analysis_stage.units(job_id,idx,kind,chunk,lo,hi) values($1,0,'HIST_PREP',0,0,0),($1,1,'HIST_STOCK',0,0,0)",[id(n)])
}
try{
 await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create schema extensions;create schema cp7_private;create schema cp7_analysis_stage authorization cp7_capture;create schema cp7_frozen_analysis_v2 authorization cp7_capture;')
 await db.exec("create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)where $2='sha256'$$;grant usage on schema extensions to cp7_capture")
 await db.exec(block(await read('scripts/cp7-src/snapshot/bootstrap.sql'),'cp7_private.immutable_run'))
 await db.exec(await read('scripts/cp7-src/wip/bootstrap.sql'))
 const native=await read('scripts/cp7-src/planning/analysis-stages.sql')
 const ddl=native.slice(native.indexOf('create table cp7_analysis_stage.jobs('),native.indexOf('-- Declared bounds, once.'))
 assert.ok(ddl.includes('create trigger immutable_stage_jobs'));assert.ok(ddl.includes('work_immutable()'))
 await db.exec(ddl)
 for(const name of['bounds','purge_intermediates'])await db.exec(block(native,'cp7_analysis_stage.'+name))
 await db.exec(`create function cp7_frozen_analysis_v2.prepare(c jsonb,q jsonb,n integer)returns jsonb language plpgsql volatile as $$begin
 if current_setting('frozen_unit_control.prepare_forbidden',true)='true'then raise exception 'CONTROLLED_PREPARE_FORBIDDEN';end if;
 if c is distinct from current_setting('frozen_unit_control.reference')::jsonb or q is distinct from current_setting('frozen_unit_control.query')::jsonb or n<>5000 then raise exception 'CONTROLLED_PREPARE_ARGUMENTS';end if;
 return current_setting('frozen_unit_control.inputs')::jsonb;end$$;`)
 const sql=await read('scripts/cp7_frozen_analysis_units_v2/cache.sql');await db.exec(sql)
 const coverage=block(await read('scripts/cp7_frozen_analysis_units_v2/source.prepared.sql'),'cp7_frozen_analysis_units_v2.coverage')
 await db.exec(coverage)
 await setting('reference',reference);await setting('query',query);await setting('inputs',inputs)
 await db.exec('set role cp7_capture');await seed(1);await seed(2)
 const original=await job(1)
 const covered=n=>value('select cp7_frozen_analysis_units_v2.coverage($1)v',[id(n)])
 await test('COVERAGE_PENDING_BEFORE_FIRST_UNIT_PROGRESS',async()=>{assert.equal(await covered(1),'PENDING')})
 await test('FIRST_UNIT_CACHE_INSERT_AND_FAILED_UNIT_ROLLBACK_ARE_ATOMIC',async()=>{
  await db.exec('begin');assert.deepEqual((await call(original,await unit(1,0))).bounded_history_inputs,inputs)
  assert.ok(await cached(1));await db.exec('rollback');assert.equal(await cached(1),undefined)
  const out=await call(original,await unit(1,0));assert.deepEqual(out.bounded_history_inputs,inputs)
  assert.equal(out.bounded_input_coverage,'COMPLETE');assert.deepEqual((await job(1)).reference,original.reference)
  const unit0=await unit(1,0);await assert.rejects(()=>call(original,unit0),/duplicate key/)
 })
 await db.query('update cp7_analysis_stage.jobs set units_done=1 where id=$1',[id(1)])
 const saved=await cached(1),current=await job(1),unit1=await unit(1,1)
 await test('LATER_UNITS_USE_EXACT_CACHE_WITHOUT_PREPARE_OR_REFERENCE_UPDATE',async()=>{
  await setting('prepare_forbidden','true')
  for(let i=0;i<3;i++)assert.deepEqual((await call(current,unit1)).bounded_history_inputs,inputs)
  assert.deepEqual(await cached(1),saved);assert.deepEqual((await job(1)).reference,original.reference)
  assert.equal(await covered(1),'COMPLETE');assert.equal(await covered(2),'PENDING')
 })
 await test('FOREIGN_JOB_ACTOR_REQUEST_RUN_QUERY_CAPSULE_PRODUCER_REFUSED',async()=>{
  const mutations=[x=>{x.id=id(2)},x=>{x.actor=id(21)},x=>{x.request_id=id(999)},x=>{x.run_id=id(999)},
   x=>{x.query.group_mode='RESTATED'},x=>{x.reference.captured_at='2026-10-25T05:06:08Z'},
   x=>{x.reference.bounded_capsule_hash='e'.repeat(64)},x=>{x.reference.bounded_producer_hash='e'.repeat(64)}]
  for(const mutate of mutations){const changed=structuredClone(current);mutate(changed);await assert.rejects(()=>unpack(changed,saved),/CACHE_BINDING/)}
  await assert.rejects(()=>call({...current,state:'DONE'},unit1),/UNIT_IDENTITY/)
  await assert.rejects(()=>call(current,{...unit1,job_id:id(2)}),/UNIT_IDENTITY/)
  await assert.rejects(()=>call(current,{...unit1,idx:0}),/UNIT_IDENTITY/)
 })
 await test('WHOLE_INPUT_AND_EXACT_CACHE_SHAPE_TAMPER_REFUSED',async()=>{
  for(const mutate of[p=>{p.extra=true},p=>{p.inputs.inputs.targets[0].quantity='9007199254740992'},
   p=>{p.inputs_sha256='e'.repeat(64)},p=>{p.binding.query.group_mode='RESTATED'},p=>{p.inputs=null}]){
   const changed=structuredClone(saved);mutate(changed);await assert.rejects(()=>unpack(current,changed),/CP7_(FROZEN_UNIT_CACHE_BINDING|WIP_FIELDS)/)
  }
  // Even a self-consistent hash does not excuse changed clock/query/raw status/coverage.
  for(const mutate of[x=>{x.query.group_mode='RESTATED'},x=>{x.captured_at='OTHER'},x=>{x.raw_native_capture_status='COMPLETE'},x=>{x.coverage='PENDING'}]){
   const changed=structuredClone(inputs);mutate(changed)
   const p=await value('select cp7_frozen_analysis_units_v2.pack(jsonb_populate_record(null::cp7_analysis_stage.jobs,$1::jsonb),$2::jsonb)v',[j(current),j(changed)])
   await assert.rejects(()=>unpack(current,p),/CACHE_BINDING/)
  }
 })
 await test('MISSING_CACHE_FAILS_WITHOUT_RECAPTURE_LEGACY_REFERENCE_EXACT',async()=>{
  await db.query('update cp7_analysis_stage.jobs set units_done=1 where id=$1',[id(2)])
  const job2=await job(2),unit2=await unit(2,1);await assert.rejects(()=>call(job2,unit2),/CACHE_MISSING/)
  const old={...current,reference:{bounded_request_contract:'cp7.bounded-analysis-request.v1',sentinel:'exact'}}
  assert.deepEqual(await call(old,unit1),old.reference)
 })
 await test('ACTUAL_NATIVE_JOB_AND_WORK_TRIGGERS_REJECT_REWRITES',async()=>{
  await assert.rejects(()=>db.query('update cp7_analysis_stage.jobs set reference=reference where id=$1',[id(1)]),/CP7_RUN_IMMUTABLE/)
  await assert.rejects(()=>db.query('update cp7_analysis_stage.target_rows set payload=payload where job_id=$1',[id(1)]),/CP7_RUN_IMMUTABLE/)
  await assert.rejects(()=>db.query('delete from cp7_analysis_stage.target_rows where job_id=$1',[id(1)]),/CP7_RUN_IMMUTABLE/)
  await assert.rejects(()=>db.query('select cp7_analysis_stage.purge_intermediates($1)',[id(1)]),/CP7_ANALYSIS_STAGE_RUNNING/)
  assert.deepEqual(await cached(1),saved)
 })
 await test('EXISTING_K3_PURGES_FINISHED_CACHE_ONLY_KEEPS_REFERENCE',async()=>{
  await db.query("update cp7_analysis_stage.jobs set state='DONE',units_done=unit_count,plan_final=true where id=$1",[id(1)])
  const done=await job(1),r=await value('select cp7_analysis_stage.purge_intermediates($1)v',[id(1)])
  assert.equal(r.removed.target_rows,1);assert.equal(await cached(1),undefined);assert.deepEqual(await job(1),done)
  assert.equal(await covered(1),'COMPLETE')
  assert.equal((await job(2)).state,'RUNNING');assert.equal(await value("select current_setting('cp7.analysis_work_delete',true)v"),'')
 })
 await db.exec('reset role')
 // Exercise the actual Native step exception subtransaction and terminal
 // progress with a controlled unit body around the real cache adapter.
 for(const name of['retention_days','retention','status','step'])await db.exec(block(native,'cp7_analysis_stage.'+name))
 await db.exec(`create function cp7_analysis_stage.run_unit(a cp7_analysis_stage.jobs,b cp7_analysis_stage.units)returns jsonb language plpgsql volatile as $$declare c jsonb;begin
 c:=cp7_frozen_analysis_units_v2.unit_reference(a,b);
 if current_setting('frozen_unit_control.cancel_after_cache',true)='true'then raise exception using errcode='57014',message='CONTROLLED_CANCEL_AFTER_CACHE';end if;
 if b.idx=1 then update cp7_analysis_stage.jobs set plan_final=true where id=a.id;end if;
 return jsonb_build_object('coverage',c->'bounded_input_coverage');end$$;`)
 await db.exec('set role cp7_capture');await seed(3);await seed(4)
 const step=n=>value('select cp7_analysis_stage.step($1)v',[id(n)])
 await test('ACTUAL_NATIVE_STEP_RETRY_ROLLS_BACK_CACHE_AND_ADVANCES_ONCE',async()=>{
  await setting('prepare_forbidden','false');await setting('cancel_after_cache','true')
  const stopped=await step(3);assert.equal(stopped.state,'RUNNING');assert.equal(stopped.unit_attempts,1);assert.equal(stopped.units_done,0)
  assert.equal(await cached(3),undefined);assert.equal(await covered(3),'PENDING')
  await setting('cancel_after_cache','false');const first=await step(3)
  assert.equal(first.units_done,1);assert.equal(first.unit_attempts,0);assert.equal(await covered(3),'COMPLETE')
  const exact=await cached(3);await setting('prepare_forbidden','true');const done=await step(3)
  assert.equal(done.state,'DONE');assert.equal(done.units_done,2);assert.deepEqual(await cached(3),exact)
  assert.deepEqual(await step(3),done);assert.deepEqual((await job(3)).reference,reference)
 })
 await test('ACTUAL_NATIVE_STEP_CHANGED_ACCESS_FAILS_BEFORE_CACHE',async()=>{
  const out=await value('select cp7_analysis_stage.step($1,$2::jsonb)v',[id(4),j({changed:true})])
  assert.equal(out.state,'FAILED');assert.equal(out.failure.code,'CP7_ANALYSIS_ACCESS_CHANGED')
  assert.equal(out.units_done,0);assert.equal(await cached(4),undefined);assert.equal(await covered(4),'PENDING')
 })
 await db.exec('reset role')
 await test('EXTERNAL_ROLES_CANNOT_READ_OR_EXECUTE_PRIVATE_CACHE',async()=>{
  for(const role of['anon','authenticated','service_role']){
   await db.exec('set role '+role)
   await assert.rejects(()=>db.query('select * from cp7_analysis_stage.target_rows'),/permission denied/)
   await assert.rejects(()=>db.query('select cp7_frozen_analysis_units_v2.binding(null::cp7_analysis_stage.jobs)'),/permission denied/)
   await db.exec('reset role')
  }
 })
 const report={contract:'cp7.frozen-analysis-unit-cache-local-controls.v2',status:'PASS',cases,counts:{PASS:cases.length},
  sql_sha256:createHash('sha256').update(sql).digest('hex'),native_DDL_and_triggers_sha256:createHash('sha256').update(ddl).digest('hex'),
  coverage_function_sha256:createHash('sha256').update(coverage).digest('hex'),
  server_version:await value('select version()v'),controlled_prepare_and_unit_body:true,actual_Native_step_body_and_subtransaction:true,
  actual_Native:false,actual_compiler_arithmetic_parity:false,
  request_or_unit_integrated:false,actual_Auth_HTTP_credit:false,production_go:false}
 if(process.env.CP7_FROZEN_UNITS_LOCAL_REPORT)await writeFile(process.env.CP7_FROZEN_UNITS_LOCAL_REPORT,j(report)+'\n')
 console.log(j(report))
}finally{await db.close()}
