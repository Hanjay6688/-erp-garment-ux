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
await test('ACTUAL_SCOPED_CAPTURE_MATCHES_LEGACY_SERIES_ORACLE',async()=>{
 const run=await capture(),frozen=await stored(run.run_id);await mirror()
 const d=await dataset(mq(run.run_id)),old=await original(mq(run.run_id))
 assert.deepEqual(semanticSeries(d.series),semanticSeries(old.series))
 for(const field of['fallback_daily_mean','from_date','through_date','product_sku','product_name','history_source_hash','known_as_of'])assert.deepEqual(d[field],old[field])
 assert.ok(d.series.every(row=>row.known_at===run.captured_at&&row.refs[0].kind==='NATIVE_SCOPED_HISTORY_RUN'))
 assert.equal(d.knowledge_basis,'ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES');assert.equal(d.no_retrospective_availability_backfill,true)
 assert.equal(d.policy_source,null);assert.deepEqual(await stored(run.run_id),frozen)
 return{actual_scoped_capture_and_legacy_SQL_math:true,controlled_ERP_primitives:true,server_known_at_preserved:true,old_model_history_not_modified_by_dataset:true}
})
await test('REPEATED_MEANING_DEDUPLICATES_AND_CORRECTION_IS_NEW_REVISION',async()=>{
 const one=await capture(),two=await capture();const d1=await dataset(mq(one.run_id)),d2=await dataset(mq(two.run_id))
 assert.deepEqual(d2.series,d1.series)
 await db.query('update erp.sales_items set qty_pcs=20 where id=$1',[id(200)])
 const three=await capture(),d3=await dataset(mq(three.run_id));await mirror();const old=await original(mq(three.run_id))
 assert.deepEqual(semanticSeries(d3.series),semanticSeries(old.series))
 const corrected=d3.series.filter(row=>row.date==='2026-09-24')
 assert.equal(corrected.length,2);assert.deepEqual(corrected.map(x=>[x.revision,x.value]),[['1','10'],['2','20']])
 assert.equal(corrected[0].known_at,one.captured_at);assert.equal(corrected[1].known_at,three.captured_at)
 await rejects(()=>dataset(mq(one.run_id)),/CP7_SCOPED_MODEL_HISTORY_STALE/)
 return{unchanged_snapshots_not_extra_revisions:true,controlled_source_correction_preserves_old_known_at:true,latest_corrected_revision_retained:true}
})
await test('QUERY_TARGET_FOREIGN_ACTOR_AND_CURRENT_REVOKED_ACCESS_REFUSED',async()=>{
 const run=await capture(),frozen=await stored(run.run_id),p=mq(run.run_id)
 await rejects(()=>dataset({...p,target_key:id(2)+':'+id(9000)}),/CP7_SCOPED_MODEL_TARGET_BINDING/)
 await rejects(()=>dataset(p,randomUUID()),/CP7_SCOPED_MODEL_ACTOR_CHANGED/)
 const other=randomUUID();await setting('actor',other);await rejects(()=>dataset(p,other),/CP7_MODEL_HISTORY_RUN_UNAVAILABLE/)
 await setting('actor',actor);await setting('active',false);await rejects(()=>dataset(p),/CP7_ACCESS_DENIED/)
 assert.deepEqual(await stored(run.run_id),frozen)
 return{server_actor_and_target_binding:true,current_access_before_private_source:true}
})
await test('LARGE_UNIVERSE_KEEPS_SINGLE_TARGET_MODEL_INPUT_COMPLETE',async()=>{
 const one=await capture(),d1=await dataset(mq(one.run_id))
 await db.exec("insert into erp.products(id)select(lpad(i::text,8,'0')||'-1111-4111-8111-111111111111')::uuid from generate_series(20000,25500)i")
 const two=await capture(),d2=await dataset(mq(two.run_id))
 assert.deepEqual(d2.series,d1.series);assert.equal(d2.history_source_hash,d1.history_source_hash)
 assert.equal((await sql('select cp7_planning.history_source_within(1000)v')).status,'INCOMPLETE')
 return{controlled_products:5504,global1000_bound_unchanged:true,no_unrelated_target_rows_or_data_loss:true}
})
await test('CAPTURE_BOUND_COUNTS_ONLY_THIS_ACTOR_TARGET_AND_PERIOD',async()=>{
 const other=await capture({...q,target_key:id(2)+':'+id(9000)})
 const copies=run=>db.query(`insert into cp7_model_history_runtime.runs(id,actor,request_id,payload,query,captured_at,access_at_capture,source,result,dependency_hash,engine_hash)
 select gen_random_uuid(),actor,gen_random_uuid(),payload,query,captured_at,access_at_capture,source,result,dependency_hash,engine_hash
 from cp7_model_history_runtime.runs cross join generate_series(1,501)where id=$1::uuid`,[run])
 await copies(other.run_id);const one=await capture();assert.ok((await dataset(mq(one.run_id))).series.length>0)
 await copies(one.run_id);const newer=await capture();await rejects(()=>dataset(mq(newer.run_id)),/CP7_SCOPED_MODEL_CAPTURE_SCOPE_LIMIT/)
 return{explicit_synthetic_duplicate_capture_rows:true,unrelated501_captures_do_not_consume_target_bound:true,selected_over500_refused:true}
})
await test('EXISTING_ASSESSMENT_AND_POLICY_GATE_REMAIN_AUTHORITATIVE',async()=>{
 const run=await capture(),d=await dataset(mq(run.run_id)),p=mq(run.run_id)
 const today=await sql("select(clock_timestamp()at time zone'Asia/Jakarta')::date::text v")
 const context={target_key:key,size_id:key.split(':')[1],source_hash:d.source_hash,engine_hash:d.engine_hash,known_as_of:d.known_as_of,horizon_days:p.horizon_days,forecast_from_date:today}
 const a=await sql('select cp7_model_registry_adapter.assess($1::jsonb,$2::jsonb,null)v',[JSON.stringify(d),JSON.stringify(context)])
 assert.equal(a.activation.state,'BASELINE_REQUIRED');assert.equal(a.activation.reason,'EXPLICIT_ACTIVATION_POLICY_REQUIRED')
 assert.equal(a.activation.forecast,null);assert.equal(a.forecast_applied,false)
 assert.equal(await sql('select count(*)::integer v from cp7_model_native.runs'),0)
 return{same_reviewed_assessment_kernel:true,no_invented_activation_policy:true,no_backdated_training_evidence_or_model_run:true}
})
await test('FINAL_ACCESS_RECHECK_AND_HISTORY_ENGINE_CHANGE_REFUSE',async()=>{
 const run=await capture(),p=mq(run.run_id),frozen=await stored(run.run_id)
 await setting('access_calls',0);await setting('change_at',6)
 await rejects(()=>dataset(p),/CP7_SCOPED_MODEL_ACCESS_CHANGED/)
 await setting('access_calls',0);await setting('change_at',999999)
 await db.exec('create function cp7_model_history_runtime.fixture_dataset_engine_change()returns boolean language sql as $$select true$$')
 await rejects(()=>dataset(p),/CP7_SCOPED_MODEL_HISTORY_STALE/)
 assert.deepEqual(await stored(run.run_id),frozen)
 return{counter_driven_final_access_change_not_concurrency_credit:true,changed_history_runtime_cannot_feed_model:true,no_history_write:true}
})
await test('PRIVATE_ONLY_NO_PUBLIC_RPC_OR_CLIENT_EXECUTE',async()=>{
 for(const role of['anon','authenticated','service_role','cp7_alert']){
  assert.equal(await sql("select has_schema_privilege($1,'cp7_model_scoped_dataset','USAGE')v",[role]),false)
  assert.equal(await sql("select has_function_privilege($1,'cp7_model_scoped_dataset.dataset(jsonb,uuid)','EXECUTE')v",[role]),false)
 }
 assert.equal(await sql("select count(*)::integer v from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_model_scoped_dataset'"),3)
 return{private_functions:3,public_rpcs:0,new_tables:0,old_replacements:0}
})
const report={contract:'cp7.model-scoped-dataset-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',expected:8,
 counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,
 sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_scoped_dataset/dataset.sql')).digest('hex'),
 actual_SQL_and_scoped_capture:true,controlled_ERP_auth_primitives:true,actual_Native_capture:false,
 actual_Auth_HTTP_credit:false,actual_concurrency:false,model_caller_integrated:false,
 exact_catalog_installer_qualified:false,forecast_applied:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-scoped-dataset-local.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
