// Actual scoped source/runtime SQL and Native access body on controlled ERP
// tables and auth primitives. No actual Native/Auth/concurrent acceptance.
import {randomUUID,createHash} from 'node:crypto'
import {writeFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
import {createNativeReorderFixture} from './cp7_ow10_reorder_local_fixture.mjs'
const {db,stageAudit,id,query,sourceFixture,block,read}=await createNativeReorderFixture()
await db.exec(block(await read('scripts/cp7-src/planning/bootstrap.sql'),'cp7_planning.history_query'))
await db.exec(await read('scripts/cp7_history_reference/digest.sql'))
await db.exec(await read('scripts/cp7_model_history_scope/scope.sql'))
await stageAudit.afterUse()
await db.exec(`create schema cp7_private authorization cp7_capture;create schema auth;
 create function auth.uid()returns uuid language sql stable as $$select current_setting('history_runtime_test.actor')::uuid$$;
 create function auth.jwt()returns jsonb language sql stable as $$select '{"role":"authenticated"}'::jsonb$$;
 create function erp.get_my_access_v1()returns jsonb language plpgsql volatile as $$declare n integer;epoch text;begin
 n:=current_setting('history_runtime_test.access_calls')::integer+1;
 perform set_config('history_runtime_test.access_calls',n::text,true);
 epoch:=case when n>=current_setting('history_runtime_test.change_at')::integer then'CHANGED'else'CURRENT'end;
 return jsonb_build_object('allowed',current_setting('history_runtime_test.active')='true',
  'profile',jsonb_build_object('role_code','OWNER','epoch',epoch),'permissions','["CONTROLLED_FOUR_OPERATIONAL_PERMISSIONS"]'::jsonb);end$$;
 create function erp.has_permission(text)returns boolean language sql stable as $$select $1<>'finance.hpp.view'and current_setting('history_runtime_test.active')='true'$$;
 grant usage on schema auth,cp7_private to cp7_capture;`)
const accessSource=await read('scripts/cp7-src/snapshot/bootstrap.sql')
await db.exec(block(accessSource,'cp7_private.immutable_run'))
await db.exec(block(accessSource,'cp7_private.access_now'))
const runtime=await read('scripts/cp7_model_history_runtime/runtime.sql')
await db.exec(runtime)
const sql=async(s,p=[])=>(await db.query(s,p)).rows[0]?.v
const setting=(k,v)=>sql('select set_config($1,$2,true)v',['history_runtime_test.'+k,String(v)])
const actor=randomUUID(),key=id(1)+':'+id(9000),q={...query,target_key:key},cases=[]
const capture=(p=q,request=randomUUID())=>sql('select public.erp_cp7_capture_model_history_v1($1::jsonb,$2::uuid)v',[JSON.stringify(p),request])
const serve=run=>sql('select public.erp_cp7_read_model_history_v1($1::uuid)v',[run])
const count=()=>sql('select count(*)::integer v from cp7_model_history_runtime.runs')
const stored=run=>sql('select to_jsonb(r)v from cp7_model_history_runtime.runs r where id=$1::uuid',[run])
const sameArchive=(a,b)=>{a=structuredClone(a);b=structuredClone(b);delete a.current_guard;delete b.current_guard;assert.deepEqual(a,b)}
const rejects=async(fn,re)=>{await db.exec('savepoint expected_refusal');try{await assert.rejects(fn,re)}finally{await db.exec('rollback to savepoint expected_refusal;release savepoint expected_refusal')}}
const test=async(name,fn)=>{await db.exec('begin');try{
 await sourceFixture();for(const[k,v]of Object.entries({actor,active:true,access_calls:0,change_at:999999}))await setting(k,v)
 cases.push({id:name,status:'PASS',observed:await fn()})
 }catch(e){cases.push({id:name,status:'FAIL',error:String(e.stack).slice(0,2200)})}
 finally{await db.exec('rollback')}console.log(name+': '+cases.at(-1).status)}
await test('EXACT_UUID_ONE_IMMUTABLE_SCOPED_CAPTURE',async()=>{
 const request=randomUUID(),one=await capture(q,request),row=await stored(one.run_id),again=await capture(q,request)
 assert.equal(one.current_guard.source_state,'UNCHANGED');sameArchive(one,again)
 assert.equal(await count(),1);assert.deepEqual(await stored(one.run_id),row)
 assert.equal(one.history.history.rows.length,1);assert.equal(one.history.history.rows[0].gross_observed_pcs,'10')
 assert.equal(one.history.scope,'SINGLE_CURRENT_PHYSICAL_ROOT');assert.equal(one.history.training_known_at,one.captured_at)
 assert.equal(one.history.model_eligibility,'HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED')
 assert.deepEqual(row.payload,q);assert.equal(row.source.result,undefined)
 return{same_UUID_same_payload_one_row:true,server_known_at_not_backdated:true,actual_scoped_source_and_history_kernel:true}
})
await test('SAME_REQUEST_CHANGED_QUERY_REFUSED',async()=>{
 const request=randomUUID(),one=await capture(q,request),row=await stored(one.run_id)
 for(const p of[{...q,group_mode:'RESTATED'},{...q,target_key:id(2)+':'+id(9000)},{...q,from_date:'2026-09-24'}])await rejects(()=>capture(p,request),/CP7_MODEL_HISTORY_REQUEST_CHANGED/)
 assert.equal(await count(),1);assert.deepEqual(await stored(one.run_id),row)
 for(const p of[{...q,scope:'GLOBAL'},{...q,target_key:'invalid'},{...q,from_date:'2020-01-01'}])await rejects(()=>capture(p),/CP7_WIP_FIELDS|CP7_MODEL_HISTORY_QUERY/)
 await rejects(()=>capture(q,null),/CP7_MODEL_HISTORY_REQUEST_REQUIRED/)
 return{exact_payload_namespace:true,closed_single_target_query:true,no_refusal_rows:true}
})
await test('CHANGED_SOURCE_ARCHIVE_REPLAY_UNCHANGED_NEW_CAPTURE_CURRENT',async()=>{
 const first=await capture(),old=await stored(first.run_id)
 await db.query("update erp.fg_stock_movements set source_type='CONTROLLED_EQUAL_TOTAL_CHANGE'where id=$1",[id(100)])
 const stale=await serve(first.run_id);assert.equal(stale.current_guard.source_state,'ARCHIVED_STALE')
 assert.equal(stale.current_guard.reason,'CURRENT_SCOPED_SOURCE_CHANGED');sameArchive(first,stale)
 sameArchive(first,await capture(q,first.request_id));assert.deepEqual(await stored(first.run_id),old)
 const fresh=await capture();assert.equal(fresh.current_guard.source_state,'UNCHANGED');assert.notEqual(fresh.source_hash,first.source_hash)
 assert.deepEqual(fresh.history.history.rows,first.history.history.rows)
 return{full_row_change_detected_despite_equal_totals:true,old_row_immutable:true,current_capture_separate:true}
})
await test('ABSENT_OR_CHANGED_SIZE_TARGET_RETIRES_ARCHIVE_WITHOUT_ZERO',async()=>{
 const first=await capture(),old=await stored(first.run_id)
 await db.query('update erp.products set size_id=$1 where id=$2',[id(9002),id(1)])
 const stale=await serve(first.run_id);assert.equal(stale.current_guard.reason,'CURRENT_SCOPED_SOURCE_UNAVAILABLE');sameArchive(first,stale)
 await rejects(()=>capture(),/CP7_MODEL_HISTORY_SCOPE_NON_STOCK_INCOMPLETE/)
 assert.equal(await count(),1);assert.deepEqual(await stored(first.run_id),old)
 return{unavailable_not_known_zero:true,no_recalculated_old_result:true}
})
await test('CURRENT_REVOKED_ACCESS_AND_FOREIGN_ACTOR_PRECEDE_REPLAY',async()=>{
 const first=await capture(),old=await stored(first.run_id)
 await setting('active',false)
 await rejects(()=>serve(first.run_id),/CP7_ACCESS_DENIED/);await rejects(()=>capture(q,first.request_id),/CP7_ACCESS_DENIED/)
 await setting('active',true);await setting('actor',randomUUID())
 await rejects(()=>serve(first.run_id),/CP7_MODEL_HISTORY_RUN_UNAVAILABLE/)
 assert.equal(await count(),1);assert.deepEqual(await stored(first.run_id),old)
 return{actual_Native_access_body_controlled_auth_primitives:true,revoked_and_foreign_no_history_disclosure:true}
})
await test('ACCESS_CHANGE_AT_EACH_ADMISSION_BOUNDARY_LEAVES_NO_ROW',async()=>{
 for(const n of[2,3,4,6]){
  await setting('access_calls',0);await setting('change_at',n)
  await rejects(()=>capture(),/CP7_MODEL_HISTORY_ACCESS_CHANGED/);assert.equal(await count(),0)
 }
 return{after_envelope_after_request_before_insert_and_after_insert_rechecked:true,controlled_counter_not_actual_concurrency:true,no_orphan:true}
})
await test('SOURCE_CHANGE_DURING_COMPUTATION_REFUSED_BEFORE_INSERT',async()=>{
 await db.exec(`alter function cp7_model_history_scope.capture(text,jsonb,boolean)rename to original_capture;
 grant update on erp.products to cp7_capture;
 create function cp7_model_history_scope.capture(k text,q jsonb,inputs boolean)returns jsonb language plpgsql volatile as $$declare r jsonb;begin
 r:=cp7_model_history_scope.original_capture(k,q,inputs);
 if inputs then update erp.products set product_name='CONTROLLED_MID_CAPTURE_CHANGE'where id=split_part(k,':',1)::uuid;end if;
 return r;end$$;`)
 await rejects(()=>capture(),/CP7_MODEL_HISTORY_SOURCE_CHANGED/);assert.equal(await count(),0)
 return{actual_runtime_detects_controlled_source_change:true,no_orphan_capture:true}
})
await test('RUNTIME_ENGINE_CHANGE_RETIRES_IMMUTABLE_HISTORY',async()=>{
 const first=await capture(),old=await stored(first.run_id)
 await db.exec('create function cp7_model_history_runtime.controlled_engine_revision()returns boolean language sql as $$select true$$')
 const stale=await serve(first.run_id);assert.equal(stale.current_guard.reason,'HISTORY_RUNTIME_ENGINE_CHANGED')
 sameArchive(first,stale);assert.deepEqual(await stored(first.run_id),old)
 return{runtime_engine_bound_separately_from_physical_source:true}
})
await test('UNEXPECTED_SOURCE_ERROR_IS_NOT_DOWNGRADED_TO_STALE',async()=>{
 const first=await capture()
 await db.exec("create or replace function cp7_model_history_scope.capture(p_target text,p_query jsonb,p_with_inputs boolean)returns jsonb language plpgsql stable as $$begin raise exception 'CONTROLLED_UNEXPECTED_SOURCE_FAULT';end$$")
 await rejects(()=>serve(first.run_id),/CONTROLLED_UNEXPECTED_SOURCE_FAULT/)
 return{unknown_failure_propagates:true}
})
await test('IMMUTABILITY_FINAL_INSERT_FAULT_AND_PRIVATE_ACL',async()=>{
 const first=await capture(),old=await stored(first.run_id)
 for(const s of['update cp7_model_history_runtime.runs set query=query','delete from cp7_model_history_runtime.runs'])await rejects(()=>db.exec(s),/CP7_RUN_IMMUTABLE/)
 await db.exec("create function cp7_model_history_runtime.controlled_last_fault()returns trigger language plpgsql as $$begin raise exception 'CONTROLLED_FINAL_ROW_FAULT';end$$;create trigger controlled_last_fault before insert on cp7_model_history_runtime.runs for each row execute function cp7_model_history_runtime.controlled_last_fault()")
 await rejects(()=>capture(),/CONTROLLED_FINAL_ROW_FAULT/);assert.equal(await count(),1);assert.deepEqual(await stored(first.run_id),old)
 for(const role of['anon','authenticated','service_role','cp7_alert']){
  assert.equal(await sql("select has_table_privilege($1,'cp7_model_history_runtime.runs','SELECT,INSERT,UPDATE,DELETE,TRUNCATE')v",[role]),false)
  assert.equal(await sql("select has_function_privilege($1,'cp7_model_history_runtime.capture(jsonb,uuid)','EXECUTE')v",[role]),false)
  assert.equal(await sql("select has_function_privilege($1,'public.erp_cp7_capture_model_history_v1(jsonb,uuid)','EXECUTE')v",[role]),role==='authenticated')
 }
 return{immutable_private_RLS_table:true,authenticated_facade_only:true,last_row_fault_atomic:true}
})
await test('LARGE_PRODUCT_UNIVERSE_PERSISTS_ONLY_EXPLICIT_ROOT',async()=>{
 const first=await capture()
 await db.exec("insert into erp.products(id)select(lpad(i::text,8,'0')||'-1111-4111-8111-111111111111')::uuid from generate_series(20000,25500)i")
 const again=await capture();assert.equal(again.source_hash,first.source_hash)
 assert.equal(again.history.history.rows.length,1);assert.equal(again.current_guard.source_state,'UNCHANGED')
 assert.equal((await sql('select cp7_planning.history_source_within(1000)v')).status,'INCOMPLETE')
 return{controlled_products:5504,old_global_bound_unchanged:true,explicit_root_persisted:true}
})
const report={contract:'cp7.model-history-runtime-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',expected:11,
 counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,
 runtime_sql_sha256:createHash('sha256').update(runtime).digest('hex'),actual_SQL:true,
 actual_scoped_source_and_history:true,controlled_ERP_auth_primitives_and_interleavings:true,
 actual_Native_capture:false,actual_Auth_HTTP_credit:false,actual_concurrency:false,
 exact_catalog_installer_qualified:false,model_caller_integrated:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-history-runtime-local.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
