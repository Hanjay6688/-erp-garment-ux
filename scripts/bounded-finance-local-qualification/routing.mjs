// Actual generated routes, closed query validator and finance capture.start.
// Access, bounded source, job/status storage are CONTROLLED DEPENDENCIES.
// No Native, Auth, race/wait, full-chain, official report or factory3600 claim.
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),sources={},cases=[]
async function source(path){const s=await readFile(path,'utf8');sources[path]=createHash('sha256').update(s).digest('hex');return s}
function block(s,name){const escaped=name.replaceAll('.','\\.');const m=s.match(new RegExp('create function '+escaped+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(m?.length,1,name);return m[0]}
const actor='00000000-0000-4000-8000-000000000001'
const uuid=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0')
const query={from_date:'2026-01-01',through_date:'2026-01-03',group_mode:'AS_SOLD'}
const staged={...query,finance_mode:'STAGED'}
const route='public.erp_cp7_request_bounded_finance_analysis_v1'
const operational='cp7_bounded_analysis_stage.request'
const one=async(sql,params=[]) => (await db.query(sql,params)).rows[0]
const call=async(q,id,fn=route)=>(await one('select '+fn+'($1::jsonb,$2::uuid) v',[JSON.stringify(q),id])).v
const counts=async()=>one('select (select count(*)::int from cp7_analysis_stage.jobs) jobs,(select count(*)::int from cp7_finance_capture.captures) captures,(select count(*)::int from cp7_analysis_stage.capture_marks) marks')
async function refusal(id,fn,error){const before=await counts();await assert.rejects(fn,e=>e.message.includes(error));assert.deepEqual(await counts(),before);cases.push({id,status:'PASS',expected_refusal:error,all_three_row_counts_unchanged:true})}
async function controls(changes=''){
 await db.exec('update test_control set calls=0,change_access_at=0,revoke_finance_at=0,finance_allowed=true,product_count=1')
 if(changes)await db.exec('update test_control set '+changes.slice(1))
}
try{
 await db.exec(`create role cp7_capture;create role anon;create role authenticated;create role service_role;
 create schema cp7_wip authorization cp7_capture;create schema cp7_demand authorization cp7_capture;
 create schema cp7_planning authorization cp7_capture;create schema cp7_schedule_native authorization cp7_capture;
 create schema cp7_analysis_stage authorization cp7_capture;create schema cp7_analysis_native authorization cp7_capture;
 create schema cp7_analysis_jobs authorization cp7_capture;create schema cp7_bounded_analysis_stage authorization cp7_capture;
 create schema cp7_finance_capture authorization cp7_capture;
 create table test_control(calls int,change_access_at int,revoke_finance_at int,finance_allowed boolean,product_count int);
 insert into test_control values(0,0,0,true,1);
 create table cp7_analysis_stage.jobs(id uuid primary key,actor uuid,request_id uuid,query jsonb,reference jsonb,unique(actor,request_id));
 create table cp7_analysis_stage.capture_marks(job_id uuid primary key,source_snapshot pg_snapshot);
 create table cp7_analysis_native.runs(actor uuid,request_id uuid);
 create table cp7_analysis_jobs.jobs(actor uuid,request_id uuid);
 create function cp7_schedule_native.access_now(boolean)returns jsonb language plpgsql as $$declare x public.test_control;begin
 update public.test_control set calls=calls+1 returning *into x;
 return jsonb_build_object('actor','${actor}','revision',case when x.change_access_at>0 and x.calls>=x.change_access_at then 2 else 1 end);end$$;
 create function cp7_analysis_stage.report_finance_access(jsonb,boolean)returns boolean language sql as $$
 select finance_allowed and(revoke_finance_at=0 or calls<revoke_finance_at)from public.test_control$$;
 create function cp7_analysis_stage.bounds()returns jsonb language sql as $$select '{"job_targets":3600}'::jsonb$$;
 create function cp7_analysis_stage.job_of(a uuid,r uuid)returns uuid language sql as $$select id from cp7_analysis_stage.jobs where actor=a and request_id=r$$;
 create function cp7_bounded_analysis_stage.source(jsonb,boolean)returns jsonb language sql as $$
 select jsonb_build_object('bounded_request_contract','cp7.bounded-analysis-request.v1','captured_at','2026-01-04T00:00:00Z','facts',
 jsonb_build_object('products',(select jsonb_agg(jsonb_build_object('id',n))from generate_series(1,(select product_count from public.test_control))n)))$$;
 create function cp7_analysis_stage.create_job(a uuid,r uuid,q jsonb,x jsonb,c jsonb)returns uuid language plpgsql as $$declare id uuid:=gen_random_uuid();begin
 insert into cp7_analysis_stage.jobs values(id,a,r,q,c);return id;end$$;
 create function cp7_analysis_stage.status(j uuid)returns jsonb language sql as $$
 select jsonb_build_object('id',id,'reference',reference)from cp7_analysis_stage.jobs where id=j$$;`)
 for(const [path,name]of[
  ['scripts/cp7-src/wip/bootstrap.sql','cp7_wip.fields'],
  ['scripts/cp7-src/demand/bootstrap.sql','cp7_demand.day'],
  ['scripts/cp7-src/planning/bootstrap.sql','cp7_planning.history_query']
 ])await db.exec(block(await source(path),name))
 const cap=await source('scripts/cp7_finance_capture/finance_capture.sql')
 const table=cap.match(/create table cp7_finance_capture\.captures\([\s\S]*?;\n/)
 assert.ok(table);await db.exec(table[0]+block(cap,'cp7_finance_capture.start'))
 await db.exec(`grant select,insert,update on public.test_control to cp7_capture;
 grant all on all tables in schema cp7_analysis_stage,cp7_analysis_native,cp7_analysis_jobs,cp7_finance_capture to cp7_capture;`)
 const original=execFileSync('python3',['-c',"import sys;sys.dont_write_bytecode=True;sys.path.insert(0,'scripts');from cp7_bounded_finance_bridge.render import original;print(original())"],{encoding:'utf8'})
 await db.exec(original)
 await db.exec(await source('scripts/cp7_bounded_finance_bridge/bridge.sql'))
 for(const role of ['anon','authenticated','service_role']){
  const r=await one(`select has_function_privilege($1,$2,'EXECUTE') public,has_function_privilege($1,'cp7_bounded_analysis_stage.request_finance(jsonb,uuid)','EXECUTE') private`,[role,route+'(jsonb,uuid)'])
  assert.equal(r.public,role==='authenticated');assert.equal(r.private,false)
 }
 cases.push({id:'PUBLIC_FACADE_EXACT_EXECUTE_AUTHORITY',status:'PASS'})
 await refusal('MISSING_EXPLICIT_MODE',()=>call(query,uuid(10)),'CP7_BOUNDED_FINANCE_EXPLICIT_STAGED_REQUIRED')
 await refusal('DEFERRED_NOT_STAGED',()=>call({...query,finance_mode:'DEFERRED'},uuid(11)),'CP7_BOUNDED_FINANCE_EXPLICIT_STAGED_REQUIRED')
 await refusal('MODE_MUST_BE_STRING',()=>call({...query,finance_mode:true},uuid(12)),'CP7_ANALYSIS_FINANCE_MODE')
 await refusal('UNKNOWN_FIELD_REFUSED',()=>call({...staged,trusted_scope:'invented'},uuid(13)),'CP7_WIP_FIELDS')
 await refusal('OPERATIONAL_QUERY_STAYS_THREE_FIELDS',()=>call(staged,uuid(14),operational),'CP7_WIP_FIELDS')
 await controls()
 await db.exec('set role authenticated')
 const first=await call(staged,uuid(20))
 await db.exec('reset role')
 const binding=await one('select j.actor=c.actor actor_equal,j.id=c.owner_id job_equal,j.query=c.query query_equal,c.owner_kind,c.dates,c.access_at_start,c.state,j.reference from cp7_analysis_stage.jobs j join cp7_finance_capture.captures c on c.owner_id=j.id')
 assert.equal(binding.actor_equal,true);assert.equal(binding.job_equal,true);assert.equal(binding.query_equal,true)
 assert.equal(binding.owner_kind,'STAGED_ANALYSIS');assert.equal(binding.state,'RUNNING')
 assert.equal(binding.reference.finance_sidecar_mode,'STAGED');assert.equal(binding.dates.as_of,'2026-01-04')
 assert.deepEqual(await counts(),{jobs:1,captures:1,marks:1})
 assert.deepEqual(await call(staged,uuid(20)),first);assert.deepEqual(await counts(),{jobs:1,captures:1,marks:1})
 cases.push({id:'EXACT_ONCE_ACTOR_JOB_QUERY_CAPTURE_DATE_BINDING',status:'PASS',job_count:1,capture_count:1,mark_count:1})
 await refusal('STAGED_UUID_CANNOT_REPLAY_OPERATIONAL',()=>call(query,uuid(20),operational),'CP7_ANALYSIS_REQUEST_CHANGED')
 await refusal('STAGED_UUID_QUERY_IMMUTABLE',()=>call({...staged,through_date:'2026-01-02'},uuid(20)),'CP7_ANALYSIS_REQUEST_CHANGED')
 await controls()
 await call(query,uuid(21),operational)
 assert.deepEqual(await counts(),{jobs:2,captures:1,marks:2})
 cases.push({id:'OPERATIONAL_CREATES_NO_FINANCE_CAPTURE',status:'PASS'})
 await refusal('OPERATIONAL_UUID_CANNOT_REPLAY_STAGED',()=>call(staged,uuid(21)),'CP7_ANALYSIS_REQUEST_CHANGED')
 await controls(',finance_allowed=false')
 await refusal('REVOKED_FINANCE_REPLAY_REFUSED',()=>call(staged,uuid(20)),'CP7_ANALYSIS_FINANCE_ACCESS_CHANGED')
 await controls(',change_access_at=2')
 await refusal('INJECTED_ACCESS_CHANGE_AT_POST_LOCK_CHECK',()=>call(staged,uuid(22)),'CP7_ANALYSIS_FINANCE_ACCESS_CHANGED')
 await controls(',revoke_finance_at=2')
 await refusal('INJECTED_FINANCE_CHANGE_AT_POST_LOCK_CHECK',()=>call(staged,uuid(23)),'CP7_ANALYSIS_FINANCE_ACCESS_CHANGED')
 await controls(',revoke_finance_at=5')
 await refusal('INJECTED_FINAL_PERMISSION_FAILURE_ATOMIC_ROLLBACK',()=>call(staged,uuid(24)),'CP7_ANALYSIS_FINANCE_ACCESS_CHANGED')
 await controls(',product_count=3601')
 await refusal('CAPACITY_REFUSED_BEFORE_JOB_OR_CAPTURE',()=>call(staged,uuid(25)),'CP7_ANALYSIS_STAGED_TARGET_LIMIT')
 await controls()
 await db.query('insert into cp7_analysis_native.runs values($1::uuid,$2::uuid)',[actor,uuid(26)])
 await refusal('LEGACY_DIRECT_UUID_REFUSED',()=>call(staged,uuid(26)),'CP7_ANALYSIS_REQUEST_CHANGED')
 const report={status:'PASS',classification:'ACTUAL_ROUTE_AND_CAPTURE_START_OVER_CONTROLLED_DEPENDENCIES_PGLITE_NOT_NATIVE',
  sources,cases,count:cases.length,actual_sql:['both request routes','public facade','history_query','fields','day','finance_capture.start','finance_capture.captures table'],
  controlled_dependencies:['access_now','report_finance_access','bounded source','bounds','job_of','create_job','status','minimal job tables'],
  no_actual_wait_or_concurrency:true,official_finance_report_not_executed:true,full_A_chain_qualified:false,factory3600_financial_parity:false,production_go:false}
 if(process.argv[2])await writeFile(process.argv[2],JSON.stringify(report,null,2)+'\n')
 console.log(JSON.stringify(report))
}catch(error){
 const report={status:'INCOMPLETE',classification:'LOCAL_CONTROLLED_SQL',sources,cases,error:{message:error.message,code:error.code,where:error.where,query:error.query},production_go:false}
 if(process.argv[2])await writeFile(process.argv[2],JSON.stringify(report,null,2)+'\n')
 console.error(JSON.stringify(report));process.exitCode=1
}finally{await db.close()}
