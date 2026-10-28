// Scoped immutable evaluation SQL on controlled ERP
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
// Legacy table below is only an independent mathematical oracle. The tested
// adapter reads actual immutable scoped captures made by the runtime above.
await db.exec(`create table cp7_planning.history_runs(id uuid primary key,actor uuid,query jsonb,captured_at timestamptz,result jsonb,dependency_hash text);
 create schema cp7_schedule_native;
 create function cp7_schedule_native.access_now(boolean)returns jsonb language sql volatile as $$select cp7_private.access_now()$$;
 grant usage on schema cp7_schedule_native to cp7_capture;`)
for(const p of['models/kernels.sql','models/evaluation.sql','model-native/bootstrap.sql','model-native/source.sql'])await db.exec(await read('scripts/cp7-src/'+p))
await db.exec(block(await read('scripts/cp7-src/model-native/evaluation.sql'),'cp7_model_native.build'))
for(const p of['cp7_model_activation_gate/gate.sql','cp7_model_policy_stage/policy.sql','cp7_model_registry_adapter/adapter.sql','cp7_model_scoped_dataset/dataset.sql'])await db.exec(await read('scripts/'+p))
const mq=run=>({history_run_id:run,target_key:key,horizon_days:'7'})
const dataset=(p,who=actor)=>sql('select cp7_model_scoped_dataset.dataset($1::jsonb,$2::uuid)v',[JSON.stringify(p),who])
const original=p=>sql('select cp7_model_native.dataset($1::jsonb,$2::uuid)v',[JSON.stringify(p),actor])
const mirror=()=>db.exec("insert into cp7_planning.history_runs select id,actor,query-'target_key',captured_at,result,dependency_hash from cp7_model_history_runtime.runs on conflict(id)do nothing")
const semanticSeries=rows=>rows.map(r=>({...r,refs:r.refs.map(ref=>({...ref,kind:'CAPTURE_ORACLE'}))}))
await db.exec(block(await read('scripts/cp7_model_evaluation_v2_stage/runtime.sql'),'cp7_model_registry_adapter.current_guard'))
await db.exec(await read('scripts/cp7_model_scoped_evaluation/runtime.sql'))
const evaluate=(p,request=randomUUID())=>sql('select public.erp_cp7_capture_model_evaluation_v3($1::jsonb,$2::uuid)v',[JSON.stringify(p),request])
const readModel=run=>sql('select public.erp_cp7_read_model_evaluation_v3($1::uuid)v',[run])
const modelStored=run=>sql('select to_jsonb(r)v from cp7_model_scoped_evaluation.runs r where id=$1::uuid',[run])
const clientWire={actual_SQL:true,controlled_ERP_auth_primitives:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,actor}
const modelCount=()=>sql('select count(*)::integer v from cp7_model_scoped_evaluation.runs')
await test('SCOPED_HISTORY_EVALUATES_WITH_SAME_POLICY_KERNEL_AND_ACTUAL_CLOCK',async()=>{
 const h=await capture(),m=await evaluate(mq(h.run_id)),r=await modelStored(m.run_id)
 Object.assign(clientWire,{history:h,model:m});
 assert.equal(m.contract_version,'cp7.scoped-model-run.v3');assert.equal(m.assessment.activation.state,'BASELINE_REQUIRED')
 assert.equal(m.assessment.activation.reason,'EXPLICIT_ACTIVATION_POLICY_REQUIRED')
 assert.equal(r.input.known_as_of,h.captured_at);assert.equal(r.input.no_retrospective_availability_backfill,true)
 assert.ok(r.input.series.every(x=>x.refs[0].kind==='NATIVE_SCOPED_HISTORY_RUN'))
 assert.equal(r.input.engine_hash,await sql('select cp7_model_scoped_evaluation.engine()v'))
 assert.notEqual(r.input.engine_hash,await sql('select cp7_model_scoped_dataset.engine()v'))
 assert.equal(r.result.source_hash,r.dependency_hash);assert.equal(new Date(r.captured_at).getTime(),new Date(m.captured_at).getTime())
 const context={target_key:key,size_id:key.split(':')[1],source_hash:r.input.source_hash,engine_hash:r.input.engine_hash,
  known_as_of:m.captured_at,horizon_days:'7',forecast_from_date:m.assessment.activation.forecast_from_date}
 assert.deepEqual(r.result,await sql('select cp7_model_registry_adapter.assess($1::jsonb,$2::jsonb,null)v',[JSON.stringify(r.input),JSON.stringify(context)]))
 assert.deepEqual((await readModel(m.run_id)).assessment,m.assessment);assert.equal(await modelCount(),1)
 return{actual_runtime_capture_and_shared_assessment_SQL:true,controlled_ERP_primitives:true,known_at:h.captured_at,model_captured_at:m.captured_at,no_invented_policy_or_forecast:true}
})
await test('EXACT_UUID_PAYLOAD_REPLAY_AND_SEPARATE_METHOD_NAMESPACE',async()=>{
 const request=randomUUID(),h=await capture(q,request),p=mq(h.run_id),m=await evaluate(p,request)
 sameArchive(m,await evaluate(p,request));sameArchive(m,await readModel(m.run_id))
 await rejects(()=>evaluate({...p,horizon_days:'8'},request),/CP7_SCOPED_EVALUATION_REQUEST_CHANGED/)
 await rejects(()=>evaluate({...p,actor_scope_id:actor}),/CP7_/)
 await rejects(()=>evaluate({...p,engine_hash:'forged'}),/CP7_/)
 await rejects(()=>evaluate(p,null),/CP7_SCOPED_EVALUATION_REQUEST_REQUIRED/)
 assert.equal(await modelCount(),1);assert.equal(await count(),1)
 return{same_UUID_distinct_history_and_model_methods:true,exact_payload_replay:true,forged_actor_and_engine_rejected:true}
})
await test('CURRENT_SOURCE_CORRECTION_RETIRES_OLD_MODEL_PRESERVES_BOTH_CLOCKS',async()=>{
 const h=await capture(),m=await evaluate(mq(h.run_id)),frozen=await modelStored(m.run_id)
 await db.query('update erp.sales_items set qty_pcs=20 where id=$1',[id(200)])
 const old=await readModel(m.run_id);sameArchive(m,old)
 Object.assign(clientWire,{beforeSourceChange:m,afterSourceChange:old});
 assert.equal(old.current_guard.source_state,'ARCHIVED_STALE');assert.equal(old.current_guard.reason,'NATIVE_HISTORY_SOURCE_CHANGED')
 await rejects(()=>evaluate(mq(h.run_id)),/CP7_SCOPED_EVALUATION_HISTORY_STALE/)
 const freshHistory=await capture(),fresh=await evaluate(mq(freshHistory.run_id)),r=await modelStored(fresh.run_id)
 assert.deepEqual(r.input.series.filter(x=>x.date==='2026-09-24').map(x=>[x.value,x.known_at]),[['10',h.captured_at],['20',freshHistory.captured_at]])
 assert.deepEqual(await modelStored(m.run_id),frozen)
 return{controlled_source_correction:true,latest_corrected_revision_wins_without_backdating:true,immutable_old_model_and_history:true}
})
await test('FOREIGN_ACTOR_REVOKED_ACCESS_AND_WRONG_HISTORY_TARGET_FAIL_CLOSED',async()=>{
 const h=await capture(),m=await evaluate(mq(h.run_id)),frozen=await modelStored(m.run_id)
 await rejects(()=>evaluate({...mq(h.run_id),target_key:id(2)+':'+id(9000)}),/CP7_SCOPED_MODEL_TARGET_BINDING/)
 await setting('actor',randomUUID());await rejects(()=>readModel(m.run_id),/CP7_SCOPED_EVALUATION_RUN_UNAVAILABLE/)
 await rejects(()=>evaluate(mq(h.run_id)),/CP7_MODEL_HISTORY_RUN_UNAVAILABLE/)
 await setting('actor',actor);await setting('active',false)
 await rejects(()=>readModel(m.run_id),/CP7_ACCESS_DENIED/)
 await rejects(()=>evaluate(mq(h.run_id),m.request_id),/CP7_ACCESS_DENIED/)
 assert.deepEqual(await modelStored(m.run_id),frozen);assert.equal(await modelCount(),1)
 return{current_actor_and_access_before_read_replay_and_capture:true,no_cross_actor_disclosure_or_orphan:true}
})
await test('MODEL_ENGINE_CHANGE_ARCHIVES_ORIGINAL_ASSESSMENT',async()=>{
 const h=await capture(),m=await evaluate(mq(h.run_id)),frozen=await modelStored(m.run_id)
 await db.exec('create function cp7_model_scoped_evaluation.fixture_engine_change()returns boolean language sql as $$select true$$')
 const old=await readModel(m.run_id);sameArchive(m,old)
 assert.equal(old.current_guard.reason,'MODEL_ENGINE_CHANGED');assert.equal(old.current_guard.state,'BASELINE_REQUIRED')
 const fresh=await evaluate(mq(h.run_id));assert.notEqual(fresh.assessment.engine_hash,m.assessment.engine_hash)
 assert.deepEqual(await modelStored(m.run_id),frozen)
 return{v3_runtime_engine_is_part_of_retained_model_identity:true,read_does_not_recalculate_archive:true}
})
await test('FINAL_INSERT_FAULT_AND_ACCESS_CHANGE_ROLL_BACK_MODEL',async()=>{
 const h=await capture(),p=mq(h.run_id)
 await db.exec(`create function public.scoped_evaluation_test_fault()returns trigger language plpgsql as $$begin
 raise exception 'CONTROLLED_FINAL_MODEL_INSERT_FAULT';end$$;
 create trigger scoped_evaluation_test_fault before insert on cp7_model_scoped_evaluation.runs for each row execute function public.scoped_evaluation_test_fault()`)
 await rejects(()=>evaluate(p),/CONTROLLED_FINAL_MODEL_INSERT_FAULT/);assert.equal(await modelCount(),0)
 await db.exec('drop trigger scoped_evaluation_test_fault on cp7_model_scoped_evaluation.runs')
 await db.exec(`create function public.scoped_evaluation_test_revoke()returns trigger language plpgsql as $$begin
 perform set_config('history_runtime_test.active','false',true);return new;end$$;
 create trigger scoped_evaluation_test_revoke after insert on cp7_model_scoped_evaluation.runs for each row execute function public.scoped_evaluation_test_revoke()`)
 await rejects(()=>evaluate(p),/CP7_ACCESS_DENIED/);assert.equal(await modelCount(),0);assert.equal(await count(),1)
 return{controlled_fault_and_after_insert_revocation:true,entire_model_insert_rolled_back:true,no_actual_concurrency_credit:true}
})
await test('IMMUTABLE_PRIVATE_TABLE_AND_FACADE_ONLY_AUTHORITY',async()=>{
 const h=await capture(),m=await evaluate(mq(h.run_id))
 await rejects(()=>db.query('update cp7_model_scoped_evaluation.runs set captured_at=clock_timestamp()where id=$1',[m.run_id]),/CP7_RUN_IMMUTABLE/)
 await rejects(()=>db.query('delete from cp7_model_scoped_evaluation.runs where id=$1',[m.run_id]),/CP7_RUN_IMMUTABLE/)
 for(const role of['anon','authenticated','service_role','cp7_alert']){
  assert.equal(await sql("select has_schema_privilege($1,'cp7_model_scoped_evaluation','USAGE')v",[role]),false)
  assert.equal(await sql("select has_table_privilege($1,'cp7_model_scoped_evaluation.runs','SELECT,INSERT,UPDATE,DELETE')v",[role]),false)
  assert.equal(await sql("select has_function_privilege($1,'cp7_model_scoped_evaluation.capture(jsonb,uuid)','EXECUTE')v",[role]),false)
  for(const sig of['public.erp_cp7_capture_model_evaluation_v3(jsonb,uuid)','public.erp_cp7_read_model_evaluation_v3(uuid)'])
   assert.equal(await sql("select has_function_privilege($1,$2,'EXECUTE')v",[role,sig]),role==='authenticated')
 }
 return{private4_public2_table1:true,immutable_update_and_delete:true,only_authenticated_facade:true}
})
await test('LARGE_UNIVERSE_SCOPED_EVALUATION_RETAINS_TARGET_BOUND',async()=>{
 await db.exec("insert into erp.products(id)select(lpad(i::text,8,'0')||'-1111-4111-8111-111111111111')::uuid from generate_series(20000,25500)i")
 const h=await capture(),m=await evaluate(mq(h.run_id))
 assert.equal((await sql('select cp7_planning.history_source_within(1000)v')).status,'INCOMPLETE')
 assert.equal(m.assessment.source.history_run_id,h.run_id);assert.equal(m.assessment.source.target_key,key)
 assert.equal(m.assessment.activation.state,'BASELINE_REQUIRED');assert.equal(await modelCount(),1)
 return{controlled_products:5504,global1000_limit_unchanged:true,scoped_model_evaluation_not_blocked_by_unrelated_products:true}
})
const report={contract:'cp7.model-scoped-evaluation-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',expected:8,
 counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,
 sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_scoped_evaluation/runtime.sql')).digest('hex'),
 actual_SQL_and_scoped_capture:true,controlled_ERP_auth_primitives:true,actual_Native_capture:false,
 actual_Auth_HTTP_credit:false,actual_concurrency:false,model_target_caller_integrated:false,
 exact_catalog_installer_qualified:false,forecast_applied:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-scoped-evaluation-local.json',JSON.stringify(report,null,2)+'\n')
await writeFile('tests/fixtures/nativeScopedModelSql.json',JSON.stringify(clientWire,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
