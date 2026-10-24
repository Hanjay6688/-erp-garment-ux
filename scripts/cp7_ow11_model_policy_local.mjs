// Actual metadata SQL with controlled access stand-ins. No Native/Auth/race credit.
import {readFile,writeFile} from 'node:fs/promises'
import {randomUUID,createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8')
await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create schema cp7_model_native authorization cp7_capture;create schema cp7_private;create schema cp7_schedule_native;create schema cp7_planning;create schema erp;')
for(const p of['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7-src/models/kernels.sql','scripts/cp7-src/models/evaluation.sql'])await db.exec(await read(p))
const block=(s,name)=>{const i=s.indexOf('create function '+name+'(');assert.ok(i>=0,name);return s.slice(i,s.indexOf('$$;',i)+3)}
await db.exec(block(await read('scripts/cp7-src/snapshot/bootstrap.sql'),'cp7_private.immutable_run'))
const planning=await read('scripts/cp7-src/planning/bootstrap.sql')
await db.exec(block(planning,'cp7_planning.utc'))
await db.exec(await read('scripts/cp7_model_activation_gate/gate.sql'))
await db.exec(`create function cp7_schedule_native.access_now(writing boolean)returns jsonb language plpgsql volatile as $$
begin
 if current_setting('model_test.active',true)is distinct from'true'then raise exception using errcode='42501',message='TEST_ACCESS_DENIED';end if;
 return jsonb_build_object('actor','11111111-1111-4111-8111-111111111111','profile',jsonb_build_object('role_code',current_setting('model_test.role',true)),'permissions',jsonb_build_array('master.product.manage'),'financial',true);
end $$;
create function erp.has_permission(text)returns boolean language sql as $$select true$$;
create table cp7_model_native.registry(id text primary key,registered_at timestamptz not null,configuration jsonb not null);
alter table cp7_model_native.registry owner to cp7_capture;
create trigger immutable_registry before update or delete on cp7_model_native.registry for each row execute function cp7_private.immutable_run();
grant usage on schema cp7_schedule_native,cp7_private,cp7_planning,erp to cp7_capture;`)
const template={baseline:{id:'mean-1',method:'MEAN',params:{}},challengers:[{id:'naive-1',method:'NAIVE',params:{}}],policy:{minimum_complete_folds:'3',minimum_mae_improvement:'0',maximum_bias_worsening:'0',maximum_tail_worsening:'0',season_lag:'7'},meaning:'TECHNICAL_PROPOSAL_NOT_OWNER_SERVICE_TARGET'}
await db.query('insert into cp7_model_native.registry values($1,clock_timestamp(),$2::jsonb)',['cp7.native-model-policy.v1',JSON.stringify(template)])
await db.exec(await read('scripts/cp7_model_policy_stage/policy.sql'))
const sql=async(q,args=[])=>(await db.query(q,args)).rows[0]?.v
const access=async(role='OWNER',active='true')=>{await sql("select set_config('model_test.role',$1,false)v",[role]);await sql("select set_config('model_test.active',$1,false)v",[active])}
await access()
const workspace=()=>sql('select public.erp_cp7_get_model_activation_policy_v1()v')
const save=(p,k=randomUUID())=>sql('select public.erp_cp7_save_model_activation_policy_v1($1::jsonb,$2::uuid)v',[JSON.stringify(p),k])
const counts=()=>sql("select jsonb_build_array((select count(*)from cp7_model_policy.policies),(select count(*)from cp7_model_policy.commands),(select count(*)from cp7_model_native.registry))v")
const config={minimum_training_days:'20',maximum_horizon_days:'90',allowed_methods:['NAIVE'],promotion:template.policy}
const command=async()=>{const w=await workspace();return{contract_version:'cp7.model-activation-policy-command.v1',action:'SET',config:structuredClone(config),template_hash:w.model_template.hash,reason:'Explicit controlled policy fixture',reviewed:true,expected_revision:w.revision,access_epoch:w.access_epoch}}
const cases=[];async function test(id,fn){try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,2300)})}}
let first,firstPayload,firstKey
await test('NO_SEEDED_POLICY_OR_INHERITED_THRESHOLD',async()=>{
 const w=await workspace();assert.equal(w.state,'UNREVIEWED');assert.equal(w.revision,'0');assert.equal(w.current,null)
 assert.deepEqual(Object.keys(w.model_template.models).sort(),['baseline','challengers']);assert.deepEqual(await counts(),[0,0,1])
 return{technical_template_is_not_active_policy:true,thresholds_not_defaulted:true}
})
await test('EXPLICIT_POLICY_AND_PROSPECTIVE_REGISTRY_ATOMIC_PAIR',async()=>{
 firstPayload=await command();firstKey=randomUUID();first=await save(firstPayload,firstKey)
 assert.equal(first.policy.state,'ACTIVE');assert.equal(first.policy.revision,'1');assert.deepEqual(first.policy.config,config)
 const r=await sql('select to_jsonb(r)v from cp7_model_native.registry r where id=$1',[first.policy.registry_id])
 assert.equal(r.configuration.meaning,'EXPLICIT_OWNER_ACTIVATION_POLICY');assert.deepEqual(r.configuration.activation_policy,{id:first.policy.id,revision:'1',recorded_at:first.policy.recorded_at})
 assert.equal(Date.parse(r.registered_at),Date.parse(first.policy.recorded_at));assert.equal(first.forecast_applied,false)
 assert.deepEqual(await counts(),[1,1,2]);return{new_registry_has_actual_recorded_clock:true,no_old_registry_edit:true,forecast_applied:false}
})
await test('EXACT_REPLAY_AND_CHANGED_PAYLOAD_REFUSAL',async()=>{
 assert.deepEqual(await save(firstPayload,firstKey),first)
 await assert.rejects(()=>save({...firstPayload,reason:'different'},firstKey),/CP7_MODEL_POLICY_REQUEST_CHANGED/)
 assert.deepEqual(await counts(),[1,1,2]);return{same_UUID_payload_result:true}
})
await test('REVISION_AND_TEMPLATE_ARE_CURRENT',async()=>{
 await assert.rejects(()=>save(firstPayload),/CP7_MODEL_POLICY_REVISION_CHANGED/)
 const p=await command();p.template_hash='0'.repeat(64);await assert.rejects(()=>save(p),/CP7_MODEL_POLICY_TEMPLATE_CHANGED/)
 assert.deepEqual(await counts(),[1,1,2]);return{stale_revision_and_unreviewed_template_refused:true}
})
await test('LATEST_RECORDED_POLICY_AND_APPEND_SUSPEND',async()=>{
 const before=await sql("select cp7_model_policy.source_at($1::timestamptz-interval'1 microsecond')v",[first.policy.recorded_at]);assert.equal(before,null)
 const p=await command();p.action='SUSPEND';p.config=null;p.template_hash=null;p.reason='Explicit withdrawal';const r=await save(p)
 assert.equal(r.policy.revision,'2');assert.equal(r.policy.state,'SUSPENDED');assert.deepEqual(r.policy.config,first.policy.config)
 assert.deepEqual(await save(firstPayload,firstKey),first);assert.equal((await workspace()).state,'SUSPENDED')
 const old=await sql('select cp7_model_policy.source_at($1::timestamptz)v',[first.policy.recorded_at]);assert.equal(old.policy.id,first.policy.id)
 assert.deepEqual(await counts(),[2,2,3]);return{old_result_and_recorded_clock_unchanged:true,suspend_is_append_only:true}
})
await test('REACTIVATION_REQUIRES_NEW_EXPLICIT_CONFIGURATION',async()=>{
 const p=await command();p.config.minimum_training_days='30';const r=await save(p)
 assert.equal(r.policy.revision,'3');assert.equal(r.policy.state,'ACTIVE');assert.equal(r.policy.config.minimum_training_days,'30')
 assert.notEqual(r.policy.registry_id,first.policy.registry_id);return{new_revision_new_registry:true}
})
await test('CURRENT_ACCESS_PRECEDES_COMMITTED_REPLAY',async()=>{
 const before=await counts();await access('OWNER','false');await assert.rejects(()=>save(firstPayload,firstKey),/TEST_ACCESS_DENIED/);await assert.rejects(()=>workspace(),/TEST_ACCESS_DENIED/)
 await access('STAFF');await assert.rejects(()=>save(firstPayload,firstKey),/CP7_MODEL_POLICY_OWNER_ADMIN_REQUIRED/)
 await access();assert.deepEqual(await counts(),before);return{controlled_access_standin_only:true,actual_Auth_HTTP_credit:false}
})
await test('IMMUTABLE_POLICY_COMMAND_AND_REGISTRY',async()=>{
 for(const q of['update cp7_model_policy.policies set reason=reason','delete from cp7_model_policy.commands','delete from cp7_model_native.registry'])await assert.rejects(()=>db.exec(q),/CP7_RUN_IMMUTABLE/)
 return{all_three_histories_immutable:true}
})
await test('INVALID_EXPLICIT_CONFIGURATION_HAS_NO_EFFECT',async()=>{
 const before=await counts()
 for(const mutate of[p=>p.reviewed=false,p=>p.config.minimum_training_days='0',p=>p.config.allowed_methods=['NAIVE','NAIVE'],p=>p.config.promotion.minimum_mae_improvement='-1',p=>p.access_epoch='0'.repeat(64),p=>p.config.extra='unexpected']){
  const p=await command();mutate(p);await assert.rejects(()=>save(p),/CP7_/)
 }
 assert.deepEqual(await counts(),before);return{invalid_cases:6,no_orphan_registry_or_policy:true}
})
await test('LAST_TABLE_FAULT_ROLLS_BACK_REGISTRY_AND_POLICY',async()=>{
 const before=await counts();await db.exec("create function cp7_model_policy.test_fault()returns trigger language plpgsql as $$begin raise exception 'MODEL_POLICY_LAST_TABLE_FAULT';end;$$;create trigger test_fault before insert on cp7_model_policy.commands for each row execute function cp7_model_policy.test_fault();")
 await assert.rejects(()=>command().then(p=>save(p)),/MODEL_POLICY_LAST_TABLE_FAULT/);assert.deepEqual(await counts(),before)
 await db.exec('drop trigger test_fault on cp7_model_policy.commands;drop function cp7_model_policy.test_fault()');return{registry_policy_command_atomic:true}
})
const report={contract:'cp7.model-policy-local.v1',status:cases.every(x=>x.status==='PASS')?'PASS':'FAIL',expected:10,counts:cases.reduce((a,x)=>(a[x.status]=(a[x.status]??0)+1,a),{}),cases,sql_sha256:createHash('sha256').update(await read('scripts/cp7_model_policy_stage/policy.sql')).digest('hex'),actual_SQL:true,controlled_access_standins:true,actual_Native:false,actual_Auth_HTTP_credit:false,actual_concurrency:false,catalog22_qualified:false,forecast_applied:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-policy-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
