// Actual B frozen caller/installer and A's pinned private API bodies.
// Identity, operational source and READY report are controlled; no Native/Auth credit.
import {readFile,writeFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {createHash,randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),manifest=JSON.parse(await readFile('scripts/cp7_frozen_finance_bridge/MANIFEST.json','utf8'))
const official=execFileSync('git',['show',manifest.official_A_head+':scripts/cp7_finance_capture/finance_capture.sql'],{encoding:'utf8'})
assert.equal(createHash('sha256').update(official).digest('hex'),manifest.official_A_finance_SQL_sha256)
const block=(s,name)=>{const a=s.indexOf('create function '+name+'(');assert.ok(a>=0,name);const b=s.indexOf('$$;',s.indexOf('as $$',a)+5);assert.ok(b>a);return s.slice(a,b+3)}
await db.exec('create role cp7_capture nologin;create role anon nologin;create role authenticated nologin;create role service_role nologin;')
for(const p of ['wip/bootstrap.sql','demand/bootstrap.sql'])await db.exec(await readFile('scripts/cp7-src/'+p,'utf8'))
await db.exec(block(await readFile('scripts/cp7-src/wip/normalize.sql','utf8'),'cp7_wip.ref'))
await db.exec(`create schema cp7_schedule_native;create schema cp7_analysis_stage;create schema cp7_analysis_native;create schema cp7_analysis_jobs;create schema cp7_planning;create schema cp7_frozen_analysis_units_v2;create schema local_frozen_finance;
 create table cp7_analysis_native.runs(actor uuid,request_id uuid);create table cp7_analysis_jobs.jobs(actor uuid,request_id uuid);
 create function cp7_schedule_native.access_now(boolean)returns jsonb language sql volatile as $$select jsonb_build_object('actor','11111111-1111-4111-8111-111111111111','epoch',coalesce(current_setting('ow12b.epoch',true),'before'))$$;
 create function cp7_analysis_stage.report_finance_access(jsonb,boolean)returns boolean language sql stable as $$select coalesce(current_setting('ow12b.allow',true),'yes')<>'no'$$;
 create function cp7_analysis_native.fingerprint(jsonb)returns text language sql immutable as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;
 create function cp7_analysis_stage.bounds()returns jsonb language sql immutable as $$select '{"job_targets":5000,"job_matching_products":10000}'::jsonb$$;
 create function cp7_frozen_analysis_units_v2.source(jsonb,boolean)returns jsonb language sql stable as $$select '{"captured_at":"2026-10-23T00:00:00.123456Z","bounded_request_contract":"cp7.bounded-analysis-request.v2","facts":{"products":[]}}'::jsonb$$;`)
const staged=await readFile('scripts/cp7-src/planning/analysis-stages.sql','utf8')
for(const name of ['jobs','units','runner']){
 const a=staged.indexOf('create table cp7_analysis_stage.'+name+'(');assert.ok(a>=0)
 await db.exec(staged.slice(a,staged.indexOf(';',a)+1))
}
await db.exec('create table cp7_analysis_stage.capture_marks(job_id uuid,source_snapshot pg_snapshot);')
await db.exec(block(await readFile('scripts/cp7-src/planning/bootstrap.sql','utf8'),'cp7_planning.history_query'))
for(const name of ['retention_days','retention','status','job_of','create_job'])await db.exec(block(staged,'cp7_analysis_stage.'+name))
await db.exec(await readFile('scripts/cp7_frozen_analysis_units_v2/request.prepared.sql','utf8'))
for(const sig of ['cp7_analysis_stage.status(uuid)','cp7_frozen_analysis_units_v2.request(jsonb,uuid)'])await db.exec('alter function '+sig+' owner to cp7_capture;revoke all on function '+sig+' from public,anon,authenticated,service_role')
// This is A's actual capture-table DDL and five actual bodies, not substitutes.
await db.exec(official.slice(official.indexOf('create schema'),official.indexOf('-- ------------------------------------------------- reads as the finance reader')))
for(const name of ['status_row','status','status_of','start','result'])await db.exec(block(official,'cp7_finance_capture.'+name))
for(const sig of ['cp7_finance_capture.status_row(cp7_finance_capture.captures)','cp7_finance_capture.status(uuid)',...Object.keys(manifest.official_dependencies)])await db.exec('alter function '+sig+' owner to cp7_capture;revoke all on function '+sig+' from public,anon,authenticated,service_role')
await db.exec(block(await readFile('scripts/cp7-src/planning/analysis.sql','utf8'),'cp7_analysis_native.fact'))
await db.exec(block(await readFile('scripts/cp7-src/planning/analysis-finance.sql','utf8'),'cp7_analysis_native.finance_apply'))
await db.exec(`create function local_frozen_finance.insert_control()returns trigger language plpgsql as $$begin
 if current_setting('ow12b.start_fail',true)='yes'then raise exception 'LOCAL_CONTROLLED_START_INSERT_FAILURE';end if;
 if current_setting('ow12b.revoke_after_start',true)='yes'then perform set_config('ow12b.allow','no',false);end if;
 return new;end$$;
 create trigger local_frozen_finance_start_control before insert on cp7_finance_capture.captures for each row execute function local_frozen_finance.insert_control();`)
const audit=await beginLocalStageAudit(db,'cp7_frozen_finance_bridge','scripts/cp7_ow12b_frozen_finance_local_audit.py')
const query={from_date:'2026-09-23',through_date:'2026-10-22',group_mode:'AS_SOLD'}
const request=async(q,id=randomUUID())=>(await db.query('select cp7_frozen_analysis_units_v2.request($1::jsonb,$2::uuid)v',[JSON.stringify(q),id])).rows[0].v
const counts=async()=>(await db.query(`select (select count(*)from cp7_analysis_stage.jobs)::int jobs,(select count(*)from cp7_analysis_stage.units)::int units,(select count(*)from cp7_analysis_stage.capture_marks)::int marks,(select count(*)from cp7_finance_capture.captures)::int finance`)).rows[0]
const results=[]
async function test(id,fn){try{results.push({id,status:'PASS',observed:await fn()})}catch(error){results.push({id,status:'FAIL',error:String(error.stack).slice(0,2200)})}}
await test('FROZEN_FINANCE_LEGACY_DEFAULT_AND_EXPLICIT_DEFERRED',async()=>{
 for(const q of [query,{...query,finance_mode:'DEFERRED'}]){
  const before=await counts(),r=await request(q);assert.equal(Object.hasOwn(r,'finance_capture'),false)
  assert.equal((await counts()).finance,before.finance)
 }
 return {legacy_response_has_no_sidecar:true,official_capture_not_started:true}
})
await test('FROZEN_FINANCE_EXACT_QUERY_MODE_UUID_AND_MICROSECOND_CAPTURE',async()=>{
 const before=await counts(),id=randomUUID(),r=await request({...query,finance_mode:'STAGED'},id)
 assert.equal(r.finance_capture.state,'RUNNING');assert.equal(r.finance_capture.capture.units_total,null)
 const own=(await db.query('select query,reference,captured_at::text from cp7_analysis_stage.jobs where request_id=$1::uuid',[id])).rows[0]
 assert.deepEqual(own.query,query);assert.equal(own.reference.finance_sidecar_mode,'STAGED');assert.ok(own.captured_at.includes('.123456'))
 const replay=await request({...query,finance_mode:'STAGED'},id);assert.equal(replay.finance_capture.capture.capture_id,r.finance_capture.capture.capture_id)
 assert.equal((await counts()).finance,before.finance+1)
 for(const q of [query,{...query,finance_mode:'DEFERRED'},{...query,from_date:'2026-09-24',finance_mode:'STAGED'}])await assert.rejects(()=>request(q,id),/CP7_ANALYSIS_REQUEST_CHANGED/)
 return{actual_A_start_and_status_bodies:true,one_capture_on_exact_replay:true,original_reference_not_updated:true,mode_and_query_identity_closed:true}
})
await test('FROZEN_FINANCE_EXISTING_DEFERRED_UUID_CANNOT_BE_UPGRADED',async()=>{
 const id=randomUUID();await request(query,id);const before=await counts()
 await assert.rejects(()=>request({...query,finance_mode:'STAGED'},id),/CP7_ANALYSIS_REQUEST_CHANGED/);assert.deepEqual(await counts(),before)
 return{no_late_finance_attachment_to_immutable_job:true}
})
await test('FROZEN_FINANCE_INVALID_MODES_AND_CURRENT_PERMISSION_REFUSED',async()=>{
 const before=await counts()
 for(const mode of [null,true,1,'READY',{},[]])await assert.rejects(()=>request({...query,finance_mode:mode}),/CP7_ANALYSIS_FINANCE_MODE/)
 await db.exec("set ow12b.allow='no'")
 await assert.rejects(()=>request({...query,finance_mode:'STAGED'}),/CP7_ANALYSIS_FINANCE_ACCESS_CHANGED/)
 await db.exec("set ow12b.allow='yes'");assert.deepEqual(await counts(),before)
 return{invalid_modes:6,permission_refusal_before_job:true,controlled_access_not_Auth:true}
})
await test('FROZEN_FINANCE_START_FAILURE_AND_POST_START_REVOCATION_ATOMIC',async()=>{
 const before=await counts()
 for(const [flag,code]of [['ow12b.start_fail','LOCAL_CONTROLLED_START_INSERT_FAILURE'],['ow12b.revoke_after_start','CP7_ANALYSIS_FINANCE_ACCESS_CHANGED']]){
  await db.exec("set "+flag+"='yes'")
  await assert.rejects(()=>request({...query,finance_mode:'STAGED'}),new RegExp(code))
  await db.exec("set "+flag+"='no';set ow12b.allow='yes'");assert.deepEqual(await counts(),before)
 }
 return{actual_A_start_with_controlled_insert_fault:true,no_partial_job_units_mark_or_capture:true,current_permission_checked_after_A_start:true,actual_concurrency:false}
})
await test('FROZEN_FINANCE_READY_USES_A_RESULT_AND_EXISTING_OFFICIAL_OVERLAY',async()=>{
 const r=await request({...query,finance_mode:'STAGED'}),id=r.finance_capture.capture.capture_id
 const report={snapshot:{data_confidence:{status:'READY'},performance:{sales_revenue_gl:'9007199254740993.01',gross_profit:'9007199254740893.00'},financial_position:{cash:'123.45'},basis:{performance_lifecycle_basis:'POSTED_SALES_AND_CORRECTIONS'}}}
 await db.query(`update cp7_finance_capture.captures set report=$1::jsonb,units_done=2,units_total=2,book_signature=$2,source_hash=$3,state='READY',report_read_at='2026-10-23T00:03:00.654321Z',finished_at=clock_timestamp()where id=$4::uuid`,[JSON.stringify(report),'a'.repeat(64),'b'.repeat(64),id])
 const read=await request({...query,finance_mode:'STAGED'},r.request_id),money=read.finance_capture.result
 assert.equal(money.capture_id,id);assert.equal(money.readiness,'READY');assert.equal(money.source_hash,'b'.repeat(64))
 assert.equal(money.metrics.find(m=>m.metric_id.endsWith(':sales_revenue_gl')).value.value,'9007199254740993.01')
 const source=(await db.query('select cp7_finance_capture.result($1::uuid)v',[id])).rows[0].v
 const direct=(await db.query(`select cp7_analysis_native.finance_apply('{"metrics":[],"dependencies":[],"generation_warnings":[],"quality":{"financial":"NONE"},"snapshot":{"fact_count":0},"financial_readiness":"BLOCKED"}'::jsonb,jsonb_build_object('financial_source',$1::jsonb))v`,[JSON.stringify(source)])).rows[0].v
 assert.deepEqual(money.metrics,direct.metrics);assert.deepEqual(money.dependencies,direct.dependencies)
 await db.exec("set ow12b.allow='no'")
 const hidden=(await db.query('select cp7_analysis_finance.status($1::uuid)v',[r.finance_capture.job_id])).rows[0].v
 assert.equal(hidden.state,'ACCESS_REVOKED');assert.equal(hidden.capture,null);assert.equal(hidden.result,null)
 await db.exec("set ow12b.allow='yes'")
 return{actual_A_result_body:true,actual_existing_finance_apply:true,large_decimal_preserved:true,revocation_hides_capture_and_figures:true,READY_report_explicitly_controlled_not_actual_report_read:true}
})
await test('FROZEN_FINANCE_PURGED_OPERATIONAL_JOBS_KEEP_AFTER_USE_GUARD',async()=>{
 await db.exec('delete from cp7_analysis_stage.capture_marks;delete from cp7_analysis_stage.units;delete from cp7_analysis_stage.jobs;')
 assert.ok((await counts()).finance>0);return await audit.afterUse()
})
const status=results.every(r=>r.status==='PASS')?'PASS_LOCAL_PREPARATION_ONLY':'INCOMPLETE'
const output={contract:'cp7.frozen-finance-local-controls.v2',status,results,counts:{PASS:results.filter(r=>r.status==='PASS').length,FAIL:results.filter(r=>r.status==='FAIL').length},engine:(await db.query('select version()v')).rows[0].v,official_A_head:manifest.official_A_head,official_A_finance_SQL_sha256:manifest.official_A_finance_SQL_sha256,actual_A_three_API_bodies_and_capture_table:true,identity_and_operational_source_controlled:true,READY_report_controlled:true,actual_Native:false,actual_Auth_HTTP_credit:false,official_report_factory_parity:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow12b/frozen-finance-local.json',JSON.stringify(output,null,2)+'\n')
console.log(JSON.stringify(output));await db.close();if(status==='INCOMPLETE')process.exitCode=1
