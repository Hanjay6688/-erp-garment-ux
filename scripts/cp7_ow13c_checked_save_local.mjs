// Actual new SQL/roles/RLS/UUID/transaction and Python installer/catalog APIs.
// Existing plan preflight/source/writer boundaries are controlled below, then
// their exact Native bodies are restored. NOT Native/Auth/race qualification.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8'),id=randomUUID
const actor=id(),run=id(),root=id(),size=id(),roll=id(),target=root+':'+size,identity='a'.repeat(64)
const block=(s,name)=>{const a=s.search(new RegExp('create(?: or replace)? function '+name.replaceAll('.','\\.')+'\\('));assert.ok(a>=0,name);const b=s.indexOf('$$;',s.indexOf('as $$',a));assert.ok(b>=0,name);return s.slice(a,b+3)}
await db.exec(`create role cp7_plan_writer nologin noinherit bypassrls;create role cp7_capture nologin noinherit bypassrls;
 create role anon nologin;create role authenticated nologin;create role service_role nologin;
 create schema auth;create schema erp;create schema cp7_private;create schema cp7_analysis_stage;create schema cp7_plan_native authorization cp7_plan_writer;
 grant usage on schema auth,erp,public,cp7_private to cp7_plan_writer,cp7_capture;
 grant usage on schema cp7_plan_native,cp7_analysis_stage to cp7_capture;
 create table public.ow13c_control(allowed boolean,feasible boolean,stale boolean,revoke_after_write boolean,stale_after_write boolean,refuse_after_write boolean,previews integer);
 insert into public.ow13c_control values(true,true,false,false,false,false,0);
 grant select,update on public.ow13c_control to cp7_plan_writer,cp7_capture;
 create function auth.uid()returns uuid language sql stable as $$select '${actor}'::uuid$$;
 create function auth.jwt()returns jsonb language sql stable as $$select '{"role":"authenticated"}'::jsonb$$;
 create function erp.get_my_access_v1()returns jsonb language sql volatile as $$select jsonb_build_object('allowed',allowed,'profile','{}'::jsonb,'permissions','[]'::jsonb)from public.ow13c_control$$;
 create function erp.has_permission(text)returns boolean language sql volatile as $$select allowed from public.ow13c_control$$;
 create function cp7_private.access_now()returns jsonb language plpgsql volatile as $$begin
  if not(select allowed from public.ow13c_control)then raise exception using errcode='42501',message='CONTROLLED_ACCESS_REVOKED';end if;
  return jsonb_build_object('actor',auth.uid());end$$;
 create function cp7_private.immutable_run()returns trigger language plpgsql as $$begin raise exception 'CP7_RUN_IMMUTABLE';end$$;
 create table erp.production_orders(id uuid);create table erp.production_patterns(id uuid);create table erp.material_rolls(id uuid);
 create table cp7_analysis_stage.jobs(id uuid);create table cp7_analysis_stage.page_sets(id uuid);create table cp7_analysis_stage.capture_marks(id uuid);
 create table cp7_plan_native.staged_drafts(draft_id uuid);`)
const bootstrap=await read('scripts/cp7-src/plan-native/bootstrap.sql')
const start=bootstrap.indexOf('create table cp7_plan_native.drafts(')
await db.exec(bootstrap.slice(start,bootstrap.indexOf(');',start)+2))
await db.exec('alter table cp7_plan_native.drafts owner to cp7_plan_writer')
const manifest=JSON.parse(await read('scripts/cp7_cutting_checked_save/MANIFEST.json')),canonical=[]
for(const[sig,m]of Object.entries(manifest.dependencies)){
 const sql=block(await read('scripts/cp7-src/'+m.source),sig.split('(')[0]);canonical.push(sql)
 await db.exec(sql+`;alter function ${sig} owner to ${m.owner};`)
}
await db.exec(`revoke all on all functions in schema cp7_plan_native from public,anon,authenticated,service_role;
 revoke all on function cp7_analysis_stage.check_source(uuid)from public,anon,authenticated,service_role;
 grant execute on function cp7_plan_native.staged_source(uuid,text)to cp7_plan_writer;`)
const audit=await beginLocalStageAudit(db,'cp7_cutting_checked_save')
// Controlled existing-plan boundaries. This test does not claim their logic
// is exercised; it proves the new wrapper delegates and rolls back correctly.
await db.exec(`create or replace function cp7_plan_native.staged_source(p_run uuid,p_target text)returns jsonb
 language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$begin
  return jsonb_build_object('run_id',p_run,'target_key',p_target,'identity_hash','${identity}',
   'source_hash','${'b'.repeat(64)}','data_as_of','2026-10-23T00:00:00Z');end$$;
 create or replace function cp7_analysis_stage.check_source(p_run uuid)returns jsonb
 language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$begin
  return jsonb_build_object('source_state',case when(select stale from public.ow13c_control)then'ARCHIVED_STALE'else'UNCHANGED'end,
   'checked_at','2026-10-23T01:00:00Z');end$$;
 create or replace function cp7_plan_native.preflight_v2(p jsonb,p_mode text,p_draft uuid)returns jsonb
 language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$begin
  if p_mode<>'PREVIEW'then raise exception 'CONTROLLED_WRONG_PREFLIGHT_MODE';end if;
  update public.ow13c_control set previews=previews+1;
  return jsonb_build_object('live',jsonb_build_object('apply_ready',(select feasible from public.ow13c_control),
   'verdicts',jsonb_build_array(jsonb_build_object('check','WIP','status','REFUSED','code','CP7_PLAN_V2_WIP_UNKNOWN'))));end$$;
 create or replace function cp7_plan_native.save_v2(p jsonb,p_request uuid)returns jsonb
 language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$declare d uuid:=gen_random_uuid();begin
  insert into cp7_plan_native.drafts(id,plan_id,revision,actor,request_id,payload,run_id,target_key,source_hash,core_hash,composition_hash)
  values(d,coalesce((p->>'plan_id')::uuid,gen_random_uuid()),1,auth.uid(),p_request,p,(p->>'run_id')::uuid,p->>'target_key',
   '${'b'.repeat(64)}','${identity}','${'c'.repeat(64)}');
  update public.ow13c_control set allowed=not revoke_after_write,stale=stale_after_write,feasible=not refuse_after_write;
  return jsonb_build_object('contract_version','cp7.plan-draft.v2','actor_scope_id',auth.uid(),'draft_id',d,'plan_id',d,
   'revision','1','run_id',p->'run_id','target_key',p->'target_key','identity_hash',p->'identity_hash',
   'request_id',p_request,'state','SAVED','reservation_created',false,'production_go',false);end$$;`)
await db.exec('begin')
const payload=()=>({cutting_save_contract:'cp7.cutting-checked-save.v1',run_id:run,target_key:target,identity_hash:identity,
 plan_id:null,expected_revision:null,cutting:{rolls:[{roll_id:roll}]},reviewed_assumption_ids:[],reason:'Controlled wrapper fixture'})
const call=async(p=payload(),request=id())=>{
 await db.exec('set local role authenticated')
 try{return(await db.query('select public.erp_cp7_save_cutting_suggestion_v1($1::jsonb,$2::uuid)v',[JSON.stringify(p),request])).rows[0].v}
 finally{try{await db.exec('reset role')}catch{/* outer savepoint restores role after refusal */}}
}
const counts=async()=> (await db.query('select(select count(*)::integer from cp7_plan_native.drafts)d,(select count(*)::integer from cp7_cutting_checked.receipts)r')).rows[0]
const refused=async(fn,code)=>{
 await db.exec('savepoint refusal')
 let error
 try{await fn()}catch(e){error=e}
 await db.exec('rollback to savepoint refusal;release savepoint refusal;reset role')
 assert.ok(error,'Expected refusal');assert.match(String(error.message),code)
}
const results=[]
const test=async(name,fn)=>{
 await db.exec('savepoint each_case')
 try{await fn();results.push({id:name,status:'PASS'})}catch(e){results.push({id:name,status:'FAIL',error:String(e.stack).slice(0,2500)})}
 finally{await db.exec('rollback to savepoint each_case;release savepoint each_case;reset role')}
 console.log(name+': '+results.at(-1).status)
}
await test('OW13C_LOCAL_VALID_TWO_LIVE_CHECKS_SAME_NATIVE_DRAFT',async()=>{
 const r=await call();assert.equal(r.cutting_save_guard.feasible,true);assert.equal(r.cutting_save_guard.identity_hash,identity)
 assert.deepEqual(await counts(),{d:1,r:1});assert.equal((await db.query('select previews from public.ow13c_control')).rows[0].previews,2)
})
await test('OW13C_LOCAL_SAME_UUID_EXACT_RESULT_AND_CHANGED_PAYLOAD_REFUSED',async()=>{
 const p=payload(),request=id(),a=await call(p,request);assert.deepEqual(await call(p,request),a)
 await refused(()=>call({...p,reason:'Changed'},request),/CP7_PLAN_REQUEST_CHANGED/);assert.deepEqual(await counts(),{d:1,r:1})
})
await test('OW13C_LOCAL_STALE_BEFORE_SAVE_NO_DRAFT',async()=>{
 await db.exec('update public.ow13c_control set stale=true');await refused(()=>call(),/CP7_CUTTING_SUGGESTION_SOURCE_CHANGED/)
 assert.deepEqual(await counts(),{d:0,r:0})
})
await test('OW13C_LOCAL_UNKNOWN_WIP_REFUSED_NOT_ZERO',async()=>{
 await db.exec('update public.ow13c_control set feasible=false');await refused(()=>call(),/CP7_PLAN_V2_WIP_UNKNOWN/)
 assert.deepEqual(await counts(),{d:0,r:0})
})
await test('OW13C_LOCAL_SOURCE_CHANGED_AFTER_DELEGATED_WRITE_ATOMIC_ROLLBACK',async()=>{
 await db.exec('update public.ow13c_control set stale_after_write=true');await refused(()=>call(),/CP7_CUTTING_SUGGESTION_SOURCE_CHANGED/)
 assert.deepEqual(await counts(),{d:0,r:0})
})
await test('OW13C_LOCAL_FEASIBILITY_CHANGED_AFTER_WRITE_ATOMIC_ROLLBACK',async()=>{
 await db.exec('update public.ow13c_control set refuse_after_write=true');await refused(()=>call(),/CP7_CUTTING_SUGGESTION_NOT_FEASIBLE/)
 assert.deepEqual(await counts(),{d:0,r:0})
})
await test('OW13C_LOCAL_REVOKED_AFTER_WRITE_ATOMIC_ROLLBACK',async()=>{
 await db.exec('update public.ow13c_control set revoke_after_write=true');await refused(()=>call(),/CONTROLLED_ACCESS_REVOKED|CP7_PLAN_ACCESS/)
 assert.deepEqual(await counts(),{d:0,r:0})
})
await test('OW13C_LOCAL_REPLAY_REQUIRES_CURRENT_PERMISSION',async()=>{
 const p=payload(),request=id();await call(p,request);await db.exec('update public.ow13c_control set allowed=false')
 await refused(()=>call(p,request),/CP7_PLAN_ACCESS_DENIED/);assert.deepEqual(await counts(),{d:1,r:1})
})
await test('OW13C_LOCAL_OLD_ROUTE_UUID_NOT_RELABELLED_CHECKED',async()=>{
 const p=payload(),request=id();delete p.cutting_save_contract
 await db.query('select cp7_plan_native.save_v2($1::jsonb,$2)',[JSON.stringify(p),request])
 await refused(()=>call({...p,cutting_save_contract:'cp7.cutting-checked-save.v1'},request),/CP7_PLAN_REQUEST_CHANGED/)
 assert.deepEqual(await counts(),{d:1,r:0})
})
await test('OW13C_LOCAL_RECEIPT_IMMUTABLE_INCLUDING_TRUNCATE',async()=>{
 await call()
 for(const sql of ['update cp7_cutting_checked.receipts set result=result','delete from cp7_cutting_checked.receipts','truncate cp7_cutting_checked.receipts']){
  await refused(()=>db.exec('set local role cp7_plan_writer;'+sql),/CP7_RUN_IMMUTABLE/)
 }
 assert.deepEqual(await counts(),{d:1,r:1})
})
await test('OW13C_LOCAL_MISSING_OR_WRONG_MODE_NO_DRAFT',async()=>{
 const p=payload();delete p.cutting_save_contract;await refused(()=>call(p),/CP7_CUTTING_SUGGESTION_REQUEST/)
 await refused(()=>call({...p,cutting_save_contract:'OTHER'}),/CP7_CUTTING_SUGGESTION_REQUEST/);assert.deepEqual(await counts(),{d:0,r:0})
})
// One durable local receipt exercises the real installer's after-use guard.
await call()
for(const sql of canonical)await db.exec(sql.replace('create function ','create or replace function '))
await db.exec('commit')
const installer=await audit.afterUse()
const report={classification:'LOCAL_NEW_CHECKED_SAVE_SQL_AND_INSTALLER_CONTROLLED_EXISTING_PLAN_BOUNDARIES_NOT_NATIVE_AUTH_OR_RACES',
 status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',passed:results.filter(x=>x.status==='PASS').length,total:results.length,
 results,installer,old_plan_save_changed:false,Native_qualified:false,UI_integrated:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow13c',{recursive:true});await writeFile('docs/cp7/d17-14/ow13c/local-checked-save.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report));await db.close();if(report.status!=='PASS')process.exitCode=1
