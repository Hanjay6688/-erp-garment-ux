import {PGlite} from '/workspace/scratch/1d31852998a4/erp-test-runtime/node_modules/@electric-sql/pglite/dist/index.js'
import {readFileSync,writeFileSync} from 'node:fs'
import assert from 'node:assert/strict'
const db=new PGlite(); await db.waitReady
const checks=[]
const product='11111111-1111-4111-8111-111111111111'
const location='22222222-2222-4222-8222-222222222222'
const lot='33333333-3333-4333-8333-333333333333'
const sale='44444444-4444-4444-8444-444444444444'
const key='55555555-5555-4555-8555-555555555555'
const payload={items:[{product_id:product}],source_location_id:location,sale_id:sale}
const signatures=['public.cp7_note_actual_http_diagnostic(text,jsonb,uuid,text)','public.cp7_note_actual_http_observe(jsonb,jsonb)']
const snapshot=async()=>(await db.query(`select jsonb_build_object(
 'movements',(select jsonb_agg(to_jsonb(m)order by qty_signed)from erp.fg_stock_movements m),
 'money',(select jsonb_agg(to_jsonb(m))from erp.money m),
 'requests',(select coalesce(jsonb_agg(to_jsonb(m)),'[]')from cp7_note.requests m))as r`)).rows[0].r
const catalog=async()=>(await db.query(`select n.nspname,p.proname,p.prosecdef,p.provolatile,p.proconfig,p.proacl,pg_get_userbyid(p.proowner)as owner,pg_get_functiondef(p.oid)as definition
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('public','erp','cp7_note')order by n.nspname,p.proname,p.oid`)).rows
const become=async(role='authenticated',realSession=true)=>{
 await db.exec('set session authorization postgres;set role postgres')
 if(realSession)await db.exec('set session authorization authenticator')
 await db.exec(`set role ${role};set statement_timeout='8s'`)
}
const admin=async()=>db.exec('set session authorization postgres;set role postgres')
const invoke=async(mode,data=payload)=>(await db.query('select public.cp7_note_actual_http_diagnostic($1,$2,$3,$4)as r',[mode,data,key,'1'])).rows[0].r
try{
 await db.exec(`create role anon;create role authenticated;create role service_role;
 create role authenticator;grant anon,authenticated to authenticator;create role cp7_sales_write;
 create schema erp;create schema cp7_note;
 create table erp.fg_stock_movements(product_id uuid,location_id uuid,quality_grade text,lot_id uuid,qty_signed numeric);
 create table erp.fg_lots(id uuid);create table erp.v_current_hpp(lot_id uuid,hpp_per_pcs numeric);
 create table erp.money(net_total numeric,paid_total numeric,open_balance numeric);
 create table cp7_note.requests(id uuid,payload jsonb);
 insert into erp.fg_stock_movements values('${product}','${location}','GRADE_A','${lot}',45);
 insert into erp.fg_lots values('${lot}');insert into erp.v_current_hpp values('${lot}',15);
 insert into erp.money values(375,200,175);
 create function cp7_note.access_now()returns jsonb language plpgsql security definer set search_path=''as $$begin
 if current_setting('app.owner_allowed',true)='no'then raise exception using errcode='42501',message='DECLARED_MOCK_CURRENT_ACCESS_DENIED';end if;
 return '{"allowed":true}'::jsonb;end$$;
 create function cp7_note.command(p jsonb,k uuid,v text)returns jsonb language plpgsql security definer set search_path=''as $$begin
 perform cp7_note.access_now();
 insert into cp7_note.requests values(k,p);
 insert into erp.fg_stock_movements values('${product}','${location}','GRADE_A','${lot}',4);
 update erp.money set net_total=275,open_balance=75;
 if p->>'fault'='CANCEL'then raise exception using errcode='57014',message='DECLARED_SIMULATED_QUERY_CANCEL_NOT_TIMER';end if;
 if p->>'fault'='PRIVATE_PZ001'then raise exception using errcode='PZ001',message='DECLARED_UNRELATED_PRIVATE_ERROR';end if;
 return jsonb_build_object('kind','COMMITTED_OUTCOME','request_id',k,'previous_sale_id',p->>'sale_id','sale_id',p->>'sale_id','revision','1','observation_fault',p->>'fault'='OBSERVATION');end$$;
 revoke all on all functions in schema cp7_note from public,anon,authenticated,service_role;
 grant usage on schema cp7_note to cp7_sales_write;grant execute on function cp7_note.command(jsonb,uuid,text)to cp7_sales_write;
 create function public.erp_cp7_correct_note_v1(p jsonb,k uuid,v text)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_note.command(p,k,v)$$;
 grant create on schema public to cp7_sales_write;alter function public.erp_cp7_correct_note_v1(jsonb,uuid,text)owner to cp7_sales_write;revoke create on schema public from cp7_sales_write;
 revoke all on function public.erp_cp7_correct_note_v1(jsonb,uuid,text)from public,anon,authenticated,service_role;
 grant execute on function public.erp_cp7_correct_note_v1(jsonb,uuid,text)to authenticated;
 create function public.erp_cp7_get_sales_v1(p jsonb)returns jsonb language plpgsql security definer set search_path=''as $$begin
 if current_setting('app.observation_fault',true)='yes'then raise exception using errcode='P0001',message='DECLARED_OBSERVATION_ERROR';end if;
 return jsonb_build_object('detail',jsonb_build_object('financial',(select to_jsonb(m)from erp.money m)));end$$;
 revoke all on function public.erp_cp7_get_sales_v1(jsonb)from public,anon,authenticated,service_role;`)
 const originalCatalog=await catalog(),before=await snapshot()
 const database=(await db.query('select current_database()as db')).rows[0].db
 // The local in-memory database name alone replaces the disposable-name fence.
 // Auth/Native functions and financial tables above are declared stand-ins.
 const sql=readFileSync('out/note-actual-http-local/diagnostic.sql','utf8').replaceAll("'cp6_auditor_http'",`'${database}'`)
 await db.exec(sql);checks.push('actual_embedded_PLpgSQL_compiles_with_declared_standins')
 await become(); const identity=await invoke('IDENTITY_ONLY')
 assert.equal(identity.session_user,'authenticator');assert.equal(identity.invoker_role,'authenticated');assert.equal(identity.statement_timeout,'8s')
 checks.push('invoker_role_and_authenticator_session_remain_separate')
 for(const mode of ['DEFAULT','JIT_OFF']){
  const result=await invoke(mode)
  assert.equal(result.status,'MEASURED_BEFORE_FORCED_ROLLBACK')
  assert.equal(result.invoker_role,'authenticated');assert.equal(result.session_user,'authenticator')
  assert.equal(result.physical_before_forced_rollback,49);assert.equal(result.FG_value_before_forced_rollback,735)
  assert.deepEqual(result.financial_before_forced_rollback,{net_total:275,paid_total:200,open_balance:75})
  assert.equal(result.outcome_before_forced_rollback.request_id,key)
  assert.equal(result.product_qualification,false);assert.equal(result.Native_exit_case_credit,0)
  assert.equal(result.forced_business_rollback,true);assert.equal(result.statement_timeout,'8s')
  if(mode==='JIT_OFF')assert.equal(result.experiment_jit,'off')
  await admin();assert.deepEqual(await snapshot(),before)
  await become();checks.push(`${mode}_records_state_before_exact_forced_rollback`)
 }
 const cancelled=await invoke('DEFAULT',{...payload,fault:'CANCEL'})
 assert.equal(cancelled.status,'SQL_ERROR_ROLLED_BACK');assert.equal(cancelled.sqlstate,'57014')
 assert.equal(cancelled.failure_stage,'COMMAND');assert.equal(cancelled.command_elapsed_ms,null)
 await admin();assert.deepEqual(await snapshot(),before);checks.push('simulated_query_cancel_retained_and_partial_writes_rolled_back')
 await become();await db.exec("set app.observation_fault='yes'")
 const observation=await invoke('DEFAULT')
 assert.equal(observation.failure_stage,'AFTER_COMMAND_OBSERVATION');assert.equal(observation.sqlstate,'P0001')
 assert.ok(Number.isFinite(observation.command_elapsed_ms))
 await db.exec("set app.observation_fault='no'");await admin();assert.deepEqual(await snapshot(),before)
 checks.push('observation_failure_distinguished_from_original_command_failure')
 await become();await assert.rejects(invoke('DEFAULT',{...payload,fault:'PRIVATE_PZ001'}),e=>e.code==='PZ001')
 await admin();assert.deepEqual(await snapshot(),before);checks.push('unrelated_private_PZ001_not_misreported_as_measurement')
 await become();await db.exec("set app.owner_allowed='no'")
 await assert.rejects(invoke('IDENTITY_ONLY'),e=>e.code==='42501')
 const revoked=await invoke('DEFAULT');assert.equal(revoked.sqlstate,'42501');assert.equal(revoked.status,'SQL_ERROR_ROLLED_BACK')
 await db.exec("set app.owner_allowed='yes'");await admin();assert.deepEqual(await snapshot(),before)
 checks.push('current_authority_refusal_retained_without_business_mutation')
 await become('anon');await assert.rejects(invoke('IDENTITY_ONLY'),e=>e.code==='42501')
 checks.push('anonymous_RPC_execute_refused')
 await become('authenticated',false);await assert.rejects(invoke('DEFAULT'),/DIAGNOSTIC_REAL_DISPOSABLE_POSTGREST_ONLY/)
 checks.push('admin_session_does_not_impersonate_actual_PostgREST_measurement')
 await become();await assert.rejects(invoke('UNREGISTERED_MODE'),/DIAGNOSTIC_CLOSED_EXPERIMENT_REQUIRED/)
 await admin();assert.deepEqual(await snapshot(),before);checks.push('unregistered_experiment_refused')
 for(const signature of signatures)await db.exec('drop function '+signature)
 assert.deepEqual(await catalog(),originalCatalog);checks.push('all_preexisting_function_definitions_owners_ACLs_restored_exactly')
 const receipt={status:'PASS',runtime:'PGLITE_WASM_WITH_DECLARED_AUTH_NATIVE_WRITER_AND_FINANCIAL_TABLE_STANDINS_NOT_NATIVE_PROOF',database_name_fence_substitution_only:true,actual_HTTP_login:false,actual_statement_timer_timeout_tested:false,simulated_cancel_is_not_real_8s_timeout:true,Native_product_qualification:false,Native_exit_case_credit:0,checks}
 writeFileSync('out/note-actual-http-local/LOCAL_CONTROLS.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt))
}catch(error){
 const failure={status:'INCOMPLETE',runtime:'PGLITE_DECLARED_STANDINS_NOT_NATIVE',checks_completed:checks,error:{name:error.name,message:error.message,code:error.code,where:error.where},Native_product_qualification:false}
 writeFileSync('out/note-actual-http-local/LATEST_FAILURE.json',JSON.stringify(failure,null,2)+'\n');console.log(JSON.stringify(failure));process.exitCode=1
}finally{await db.close()}
