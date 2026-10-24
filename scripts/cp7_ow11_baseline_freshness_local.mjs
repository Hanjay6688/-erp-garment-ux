// Actual predecessor/replacement reader SQL; source/access are controlled.
import {readFile,writeFile} from 'node:fs/promises'
import {randomUUID,createHash} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
execFileSync('python',['-B','-c','import cp7_baseline_freshness_stage as s;s.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
const db=new PGlite(),read=p=>readFile(p,'utf8'),cases=[]
const sql=async(q,args=[])=>(await db.query(q,args)).rows[0]?.v
const actor=randomUUID(),run=randomUUID(),request=randomUUID()
const c={status:'COMPLETE',captured_at:'2026-10-24T00:00:00.123456Z',facts:{stock:[{qty:'7'}]},profiles:[{revision:'1'}],production_policies:{rows:[{revision:'1'}]},product_analog_choices:[{revision:'1',state:'CONFIRMED_ASSUMPTION'}],analog_consumer_engine:'a'.repeat(64)}
await db.exec(`create role cp7_capture;create role anon;create role authenticated;create role service_role;
 create schema cp7_private;create schema cp7_baseline_native;create schema extensions;
 create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)$$;
 create table public.source_fixture(c jsonb);
 create table cp7_baseline_native.runs(id uuid,actor uuid,request_id uuid,result jsonb,dependency_hash text);
 create function cp7_baseline_native.source()returns jsonb language sql stable as $$select c from public.source_fixture$$;
 create function cp7_private.access_now()returns jsonb language plpgsql volatile as $$begin
  if current_setting('freshness_fixture.active',true)is distinct from'true'then raise exception using errcode='42501',message='CONTROLLED_ACCESS_DENIED';end if;
  return jsonb_build_object('actor',current_setting('freshness_fixture.actor'));
 end$$;`)
await sql("select set_config('freshness_fixture.actor',$1,false)v",[actor]);await sql("select set_config('freshness_fixture.active','true',false)v")
await sql('insert into public.source_fixture values($1::jsonb)',[JSON.stringify(c)])
const old=await read('scripts/cp7_production_stage/sql/cp7_baseline_native__serve.sql'),fix=await read('scripts/cp7_baseline_freshness_stage/reader.sql')
await db.exec(old);await db.exec('alter function cp7_baseline_native.serve(uuid)owner to cp7_capture;revoke all on function cp7_baseline_native.serve(uuid)from public,anon,authenticated,service_role')
const producer=await read('scripts/cp7_product_analog_consumer_stage/hooks.sql'),start=producer.indexOf('create or replace function cp7_baseline_native.build(')
const expression=producer.slice(start).split(' hash:=')[1].split(';')[0]
const hash=await sql('select '+expression+' v from public.source_fixture')
const result={source_hash:hash,rows:[{target_pcs:'7',demand_basis:'CONTROLLED'}],production_go:false}
await sql('insert into cp7_baseline_native.runs values($1,$2,$3,$4::jsonb,$5)',[run,actor,request,JSON.stringify(result),hash])
async function rejects(fn,pattern){await db.exec('savepoint expected_refusal');try{await assert.rejects(fn,pattern)}finally{await db.exec('rollback to savepoint expected_refusal;release savepoint expected_refusal')}}
const serve=(id=run)=>sql('select cp7_baseline_native.serve($1::uuid)v',[id])
const source=value=>sql('update public.source_fixture set c=$1::jsonb',[JSON.stringify(value)])
const stored=()=>sql('select to_jsonb(r)v from cp7_baseline_native.runs r where id=$1',[run])
const authority=()=>sql("select jsonb_build_array(proowner,prosecdef,provolatile,proconfig,proacl::text)v from pg_proc where oid='cp7_baseline_native.serve(uuid)'::regprocedure")
async function test(id,fn){await db.exec('begin');try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,2200)})}finally{await db.exec('rollback')}}
await test('PREDECESSOR_FRESH_CAPTURE_WRONGLY_REPORTED_STALE',async()=>{
 const r=await serve();assert.equal(r.source_state,'ARCHIVED_STALE');assert.equal(r.source_hash,hash)
 return{defect_reproduced_in_actual_predecessor_SQL:true,unchanged_source_and_producer_hash:true}
})
const beforeAuthority=await authority();await db.exec(fix);assert.deepEqual(await authority(),beforeAuthority)
await test('CORRECTED_READER_RECOGNIZES_SAME_IMMUTABLE_CAPTURE',async()=>{
 const before=await stored(),r=await serve();assert.equal(r.source_state,'UNCHANGED');assert.deepEqual(r,{...result,run_id:run,request_id:request,source_state:'UNCHANGED'});assert.deepEqual(await stored(),before)
 return{actual_reader_fix:true,stored_result_and_request_unchanged:true}
})
await test('NEW_READ_CLOCK_ALONE_DOES_NOT_INVALIDATE_SOURCE',async()=>{
 await source({...c,captured_at:'2026-10-24T12:00:00.123456Z'});assert.equal((await serve()).source_state,'UNCHANGED');return{check_clock_excluded_from_identity:true}
})
await test('CHOICE_CLEAR_OR_ENGINE_CHANGE_RETIRES_CAPTURE_WITHOUT_REWRITE',async()=>{
 const before=await stored()
 for(const patch of[{product_analog_choices:[{revision:'2',state:'CLEARED'}]},{analog_consumer_engine:'b'.repeat(64)}]){
  await source({...c,...patch});assert.equal((await serve()).source_state,'ARCHIVED_STALE');assert.deepEqual(await stored(),before)
 }return{both_new_consumer_dependencies_bound:true}
})
await test('EXISTING_PHYSICAL_PROFILE_POLICY_AND_INCOMPLETE_GUARDS_RETAINED',async()=>{
 for(const patch of[{facts:{stock:[{qty:'8'}]}},{profiles:[{revision:'2'}]},{production_policies:{rows:[{revision:'2'}]}},{status:'INCOMPLETE'}]){
  await source({...c,...patch});assert.equal((await serve()).source_state,'ARCHIVED_STALE')
 }return{old_source_guards_retained:true}
})
await test('FOREIGN_RUN_AND_CURRENT_REVOKED_ACCESS_STILL_REFUSED',async()=>{
 await sql("select set_config('freshness_fixture.actor',$1,true)v",[randomUUID()]);await rejects(()=>serve(),/CP7_BASELINE_RUN_UNAVAILABLE/)
 await sql("select set_config('freshness_fixture.actor',$1,true)v",[actor]);await sql("select set_config('freshness_fixture.active','false',true)v");await rejects(()=>serve(),/CONTROLLED_ACCESS_DENIED/)
 return{current_access_and_actor_binding_preserved:true}
})
await test('PRE_CONSUMER_CAPTURE_NOT_RELABELED_AS_CURRENT',async()=>{
 await sql('update cp7_baseline_native.runs set dependency_hash=$1 where id=$2',['c'.repeat(64),run]);const before=await stored()
 assert.equal((await serve()).source_state,'ARCHIVED_STALE');assert.deepEqual(await stored(),before);return{older_contract_history_kept:true}
})
await test('EXACT_OLD_AUTHORITY_AND_NO_NEW_ENTRY',async()=>{
 assert.deepEqual(await authority(),beforeAuthority)
 for(const role of['anon','authenticated','service_role'])assert.equal(await sql("select has_function_privilege($1,'cp7_baseline_native.serve(uuid)','EXECUTE')v",[role]),false)
 return{owner_ACL_volatility_GUC_unchanged:true,public_RPCS_added:0}
})
const report={contract:'cp7.baseline-freshness-local.v1',status:cases.every(x=>x.status==='PASS')?'PASS':'FAIL',expected:8,counts:cases.reduce((a,x)=>(a[x.status]=(a[x.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(fix).digest('hex'),actual_reader_SQL:true,controlled_access_and_source:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/baseline-freshness-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
