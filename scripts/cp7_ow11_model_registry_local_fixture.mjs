// Actual Native dataset/build and v2 SQL on explicitly synthetic capture rows.
// Historical timestamps below are test fixtures, never claimed Native evidence.
import {readFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
export async function modelRegistryFixture({currentDay=false}={}){
execFileSync('python',['-B','-c','import cp7_model_registry_adapter as a;a.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
const db=new PGlite(),read=p=>readFile(p,'utf8'),cases=[]
const block=(s,name)=>{const i=s.indexOf('create function '+name+'(');assert.ok(i>=0,name);return s.slice(i,s.indexOf('$$;',i)+3)}
await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create schema cp7_private;create schema cp7_schedule_native;create schema cp7_planning;create schema erp;create schema extensions;')
for(const p of['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7-src/models/kernels.sql','scripts/cp7-src/models/evaluation.sql'])await db.exec(await read(p))
await db.exec(block(await read('scripts/cp7-src/snapshot/bootstrap.sql'),'cp7_private.immutable_run'))
await db.exec(block(await read('scripts/cp7-src/planning/bootstrap.sql'),'cp7_planning.utc'))
await db.exec(`create table cp7_planning.history_runs(id uuid primary key,actor uuid,query jsonb,captured_at timestamptz,result jsonb,dependency_hash text);
create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select pg_catalog.sha256($1)where $2='sha256'$$;
create function cp7_schedule_native.access_now(boolean)returns jsonb language sql stable as $$select jsonb_build_object('actor','11111111-1111-4111-8111-111111111111','profile',jsonb_build_object('role_code','OWNER'))$$;
create function erp.has_permission(text)returns boolean language sql stable as $$select true$$;
grant usage on schema cp7_schedule_native,cp7_private,cp7_planning,erp to cp7_capture;`)
const bootstrap=await read('scripts/cp7-src/model-native/bootstrap.sql'),template=JSON.parse(bootstrap.match(/'({"baseline":.*})'::jsonb/)[1])
await db.exec(bootstrap.slice(0,bootstrap.indexOf('insert into cp7_model_native.registry')))
await db.query('insert into cp7_model_native.registry values($1,$2,$3::jsonb)',['cp7.native-model-policy.v1','2026-06-01T00:00:00.123456Z',JSON.stringify(template)])
await db.exec(await read('scripts/cp7-src/model-native/source.sql'))
await db.exec(block(await read('scripts/cp7-src/model-native/evaluation.sql'),'cp7_model_native.build'))
await db.exec(await read('scripts/cp7_model_activation_gate/gate.sql'))
await db.exec(await read('scripts/cp7_model_policy_stage/policy.sql'))
const sql=async(q,args=[])=>(await db.query(q,args)).rows[0]?.v
const actor='11111111-1111-4111-8111-111111111111',root='22222222-2222-4222-8222-222222222222',size='33333333-3333-4333-8333-333333333333',key=root+':'+size
const today=await sql("select(clock_timestamp()at time zone'Asia/Jakarta')::date::text v")
const start=currentDay?Date.parse(today+'T00:00:00Z')-100*86400000:Date.UTC(2026,6,1)
const day=i=>new Date(start+i*86400000).toISOString().slice(0,10)
const ref={kind:'EXPLICIT_SYNTHETIC_CAPTURE_ROWS',id:'controlled-registry-adapter',revision:'1'}
let history
for(let i=0;i<100;i++){
 history=randomUUID().replace(/^./,'a');const days=Array.from({length:i+1},(_,j)=>({date:day(j),state:'AVAILABLE',training_pcs:String(j+1)}))
 const result={history:{rows:[{target_key:key,size_id:size,days,available_sales_mean:String((i+2)/2),refs:[ref]}]},current_stock:[{target_key:key,sku:'SYNTHETIC',product_name:'Controlled prospective model test'}]}
 await db.query('insert into cp7_planning.history_runs values($1,$2,$3::jsonb,$4,$5::jsonb,$6)',[history,actor,JSON.stringify({from_date:day(0),through_date:day(i),group_mode:'AS_SOLD'}),currentDay&&i===99?await sql("select cp7_planning.utc(clock_timestamp()-interval'1 second')v"):day(i+1)+'T01:00:00.123456Z',JSON.stringify(result),'a'.repeat(64)])
}
const q={history_run_id:history,target_key:key,horizon_days:'7'}
const native=()=>sql('select cp7_model_native.dataset($1::jsonb,$2::uuid)v',[JSON.stringify(q),actor])
const legacyBefore=await native(),legacyResult=await sql('select cp7_model_native.build($1::jsonb)v',[JSON.stringify(legacyBefore)])
await db.exec(await read('scripts/cp7_model_registry_adapter/adapter.sql'))
const dataset=(query=q,who=actor)=>sql('select cp7_model_registry_adapter.dataset($1::jsonb,$2::uuid)v',[JSON.stringify(query),who])
const source=at=>sql('select cp7_model_policy.source_at($1::timestamptz)v',[at])
const registry=id=>sql("select jsonb_build_object('id',id,'registered_at',cp7_planning.utc(registered_at),'configuration',configuration)v from cp7_model_native.registry where id=$1",[id])
const bind=(d,p,r,engine)=>sql('select cp7_model_registry_adapter.bind($1::jsonb,$2::jsonb,$3::jsonb,$4)v',[JSON.stringify(d),JSON.stringify(p),JSON.stringify(r),engine])
const context=d=>({target_key:key,size_id:size,source_hash:d.source_hash,engine_hash:d.engine_hash,known_as_of:d.known_as_of,horizon_days:q.horizon_days,forecast_from_date:day(100)})
const assess=(d,c=context(d),p=d.policy_source)=>sql('select cp7_model_registry_adapter.assess($1::jsonb,$2::jsonb,$3::jsonb)v',[JSON.stringify(d),JSON.stringify(c),JSON.stringify(p)])
async function seed({revision='1',at='2026-06-02T00:00:00.123456Z',state='ACTIVE',methods=['NAIVE'],minimum='20'}={}){
 const id=randomUUID(),request=randomUUID(),rid='cp7.owner-model-policy.'+id
 const config={minimum_training_days:minimum,maximum_horizon_days:'90',allowed_methods:methods,promotion:template.policy}
 const policy={id,revision,registry_id:rid,recorded_at:at,state,reason:'EXPLICIT SYNTHETIC historical fixture, not owner/factory approval',config}
 const configuration={baseline:template.baseline,challengers:template.challengers,policy:template.policy,meaning:'EXPLICIT_OWNER_ACTIVATION_POLICY',activation_policy:{id,revision,recorded_at:at}}
 const templateHash=await sql("select encode(pg_catalog.sha256(convert_to($1::jsonb::text,'UTF8')),'hex')v",[JSON.stringify({baseline:template.baseline,challengers:template.challengers})])
 await db.query('insert into cp7_model_native.registry values($1,$2,$3::jsonb)',[rid,at,JSON.stringify(configuration)])
 await db.query('insert into cp7_model_policy.policies values($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9,$10)',[id,revision,rid,state,JSON.stringify(config),templateHash,policy.reason,actor,request,at])
 return{policy,actor_scope_id:actor,request_id:request,template_hash:templateHash}
}
async function test(id,fn){await db.exec('begin');try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,2500)})}finally{await db.exec('rollback')}}
async function rejects(fn,expected){await db.exec('savepoint expected_refusal');try{await assert.rejects(fn,expected)}finally{await db.exec('rollback to savepoint expected_refusal;release savepoint expected_refusal')}}
return{db,read,cases,sql,actor,root,size,key,day,history,q,native,legacyBefore,legacyResult,dataset,source,registry,bind,context,assess,seed,test,rejects,template,today}
}
