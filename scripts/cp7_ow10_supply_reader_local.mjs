// Actual private reader, official fingerprint wrapper, netting and K3 SQL.
// Native facts/hash adapter and private completed-job data are controlled.
import {writeFile,mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {controlledSupplyDb,read,block} from './cp7_ow10_supply_local_fixture.mjs'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const db=await controlledSupplyDb(),stages=await read('scripts/cp7-src/planning/analysis-stages.sql')
await db.exec(`create schema cp7_private;
 create function cp7_private.immutable_run()returns trigger language plpgsql as $$begin raise exception 'CP7_RUN_IMMUTABLE';end$$;
 create function cp7_netting_native.fingerprint(c jsonb)returns text language sql immutable as $$
  select encode(sha256(convert_to((c-'captured_at')::text,'UTF8')),'hex')$$;`)
const analysis=await read('scripts/cp7-src/planning/analysis.sql')
await db.exec(block(analysis,'cp7_analysis_native.fingerprint'));await db.exec(block(analysis,'cp7_analysis_native.finance_mode'))
await db.exec(stages.slice(stages.indexOf('create table cp7_analysis_stage.retention_log('),stages.indexOf('create function cp7_analysis_stage.purge_expired(')))
await db.exec(stages.slice(stages.indexOf('create table cp7_analysis_stage.cleanups('),stages.indexOf('create function cp7_analysis_stage.cleanup_due(')))
for(const name of['cp7_analysis_stage.work_immutable','cp7_analysis_stage.cleanup_due','cp7_analysis_stage.verify_final','cp7_analysis_stage.clean_done'])await db.exec(block(stages,name))
for(const table of['outputs','target_rows','pair_rows','pair_lists','fragments'])await db.exec(`create trigger controlled_work_immutable before update or delete on cp7_analysis_stage.${table} for each row execute function cp7_analysis_stage.work_immutable()`)
const audit=await beginLocalStageAudit(db,'cp7_reorder_supply')
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`,job=id(1),actor=id(2),request=id(3),run=id(4),snapshot='controlled-wip'
const query={from_date:'2026-09-23',through_date:'2026-10-22',group_mode:'AS_SOLD'},refs=[{kind:'CONTROLLED_SOURCE',id:'cut-1',revision:'1'}]
const current=()=>({status:'COMPLETE',reorder_supply_engine:'cp7.reorder-supply.v1',analysis_engine_signature:'CONTROLLED_NATIVE_ENGINE',captured_at:'2026-10-23T00:00:01Z',facts:{products:[{root_id:'a',size_id:'M'},{root_id:'b',size_id:'M'}]}})
const fp=async c=>(await db.query('select cp7_analysis_native.fingerprint($1::jsonb)v',[JSON.stringify({...c,financial_source:null,financial_capture:'DEFERRED'})])).rows[0].v
const sha=s=>createHash('sha256').update(s).digest('hex')
const cap=()=>({contract_version:'cp7.reorder-supply-budget.v1',status:'COMPLETE',snapshot_id:snapshot,reason:null,
 rows:[{physical_key:'CUT:one:M',snapshot_id:snapshot,size_id:'M',projected_good_pcs:'80',eta:'2026-10-26T00:00:00.000000Z',eligible:true}]})
const row=(key,share,fg)=>({target_key:key,size_id:'M',available_fg_pcs:fg,
 target:{status:'SCENARIO',reorder_point_pcs:'40',target_pcs:'100',inputs:{contract_version:'cp7.target-input.v2',lead_days:'3',review_days:'7',refs}},
 supplies:[{physical_key:'CUT:one:M',snapshot_id:snapshot,target_key:key,size_id:'M',kind:'ALLOCATED_CANDIDATE',qty_pcs:share,
  eta:'2026-10-26T00:00:00.000000Z',eligible:true,refs}]})
async function seed(options={}){
 const c=options.current??current(),hash=await fp(c),reference={...c,captured_at:'2026-10-23T00:00:00Z',financial_source:null,financial_capture:'DEFERRED'},state=options.state??'DONE'
 await db.query(`insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,captured_at,source_hash,state,
  unit_count,units_done,plan_final,targets_total,created_at,updated_at,failure_code)values($1,$2,$3,$4::jsonb,$5::jsonb,$6,'{}',
  '2026-10-23T00:00:00Z',$7,$8,1,$9,$10,2,'2026-10-23T00:00:00Z',clock_timestamp()-make_interval(days=>$11),$12)`,
  [job,actor,request,JSON.stringify(query),JSON.stringify(reference),run,hash,state,state==='DONE'?1:0,state==='DONE',options.expired?8:0,state==='FAILED'?'CONTROLLED_FAILURE':null])
 const body='{"controlled":"valid-hashed-header"}',page='{"controlled":"valid-hashed-page"}',h=sha(body),p=sha(page)
 if(!options.noMark)await db.query('insert into cp7_analysis_stage.capture_marks values($1,null)',[job])
 await db.query(`insert into cp7_analysis_stage.headers(run_id,job_id,body,utf8_bytes,sha256,paged,targets_total,page_count,cuts)
  values($1,$2,$3,$4,$5,'{}',2,1,'[[1,2]]')`,[run,job,body,Buffer.byteLength(body),h])
 await db.query(`insert into cp7_analysis_stage.pages(run_id,idx,target_lo,target_hi,counts,offsets,summary,body,utf8_bytes,sha256)
  values($1,0,1,2,'{}','{}','{}',$2,$3,$4)`,[run,page,Buffer.byteLength(page),p])
 if(!options.noPageSet)await db.query("insert into cp7_analysis_stage.page_sets values($1,$2,'{\"targets\":2}',clock_timestamp())",[run,sha(h+'\n'+p)])
 const scope={alloc_status:options.allocation??'SCENARIO',wip_status:'COMPLETE',schedule_state:options.noSchedule?'UNREVIEWED':'SELECTED_ASSUMPTIONS',
  schedule:options.noSchedule?null:{plan_id:'controlled-global-calendar',revision:'1'},reorder_supply_budget:options.budget??cap()}
 if(!options.noScope)await db.query('insert into cp7_analysis_stage.plan_scope values($1,$2::jsonb)',[job,JSON.stringify(scope)])
 const values=options.rows??[row('a:M','30','2'),row('b:M','50','4')]
 for(let i=0;i<values.length;i++)await db.query('insert into cp7_analysis_stage.plan_targets values($1,$2,$3,$4::jsonb)',[job,i+1,options.indexKeys?.[i]??values[i].target_key,JSON.stringify(values[i])])
 return{c,reference,hash,scope}
}
const call=async(c=current(),q=query)=>{
 await db.exec('savepoint controlled_reader_call')
 try{
  await db.exec('set role cp7_capture')
  const value=(await db.query('select cp7_reorder_supply.read_job($1::jsonb,$2::jsonb)v',[JSON.stringify(c),JSON.stringify(q)])).rows[0].v
  await db.exec('reset role;release savepoint controlled_reader_call');return value
 }catch(error){
  // PostgreSQL refuses RESET ROLE in an aborted transaction. Restore the
  // savepoint first so the original product error remains the observation.
  await db.exec('rollback to savepoint controlled_reader_call;release savepoint controlled_reader_call')
  throw error
 }
}
const tables=['jobs','capture_marks','headers','pages','page_sets','plan_scope','plan_targets','outputs','target_rows','pair_rows','pair_lists','fragments']
const data=async()=>{const out={};for(const t of tables)out[t]=(await db.query(`select count(*)n,md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]'::jsonb)::text)h from cp7_analysis_stage.${t} x`)).rows[0];return out}
const results=[],test=async(id,fn)=>{
 await db.exec('begin')
 try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,2600)})}
 finally{await db.exec('rollback;reset role')}
}
await test('OW10_CACHE_NO_MATCHING_ANALYSIS_NOT_WIP_ZERO',async()=>{
 const before=await data(),r=await call();assert.equal(r.status,'UNKNOWN');assert.equal(r.reason,'GLOBAL_ANALYSIS_NEEDED');assert.equal(r.projection,null);assert.equal(r.job,null)
 assert.deepEqual(await data(),before);return{missing_cache_unknown:true,no_new_job_or_business_write:true}
})
await test('OW10_CACHE_FRESH_COMPLETE_SNAPSHOT_CONSERVED_AND_READ_ONLY',async()=>{
 await seed();const before=await data(),r=await call();assert.equal(r.status,'SCENARIO');assert.equal(r.job.run_id,run)
 assert.equal(r.job.captured_at,'2026-10-23T00:00:00.000000Z');assert.equal(r.checked_at,'2026-10-23T00:00:01.000000Z')
 assert.deepEqual(r.projection.rows.map(x=>x.net.lead_position_base_pcs),['2','4']);assert.deepEqual(r.projection.rows.map(x=>x.net.lead_position_conditional_pcs),['32','54'])
 assert.deepEqual(await data(),before);return{actual_reader_and_kernel:true,kept_DONE_job_with_capture_header_page_set:true,whole_global_allocation_once:true,private_cache_read_no_write:true}
})
await test('OW10_CACHE_CHANGED_FACTS_ENGINE_PERIOD_AND_GROUPING_REFUSED',async()=>{
 await seed();const before=await data(),variants=[{c:{...current(),facts:{products:[]}}},{c:{...current(),analysis_engine_signature:'different'}},
  {q:{...query,from_date:'2026-09-24'}},{q:{...query,group_mode:'RESTATED'}},{c:{...current(),status:'PARTIAL'}},{c:{...current(),reorder_supply_engine:null}}]
 for(const v of variants){const r=await call(v.c??current(),v.q??query);assert.equal(r.status,'UNKNOWN');assert.equal(r.projection,null);assert.ok(r.reason)}
 assert.deepEqual(await data(),before);return{changed_contexts:variants.length,never_reuses_old_snapshot_as_current:true}
})
await test('OW10_CACHE_RUNNING_PROGRESS_WITHOUT_CREATING_OR_ADVANCING_JOB',async()=>{
 await seed({state:'RUNNING'});const before=await data(),r=await call();assert.equal(r.reason,'GLOBAL_ANALYSIS_IN_PROGRESS');assert.equal(r.projection,null)
 assert.deepEqual(r.job,{state:'RUNNING',units_done:0,unit_count:1});assert.deepEqual(await data(),before);return{server_progress_only:true,no_request_or_worker_side_effect:true}
})
await test('OW10_CACHE_FAILED_OR_EXPIRED_RESULT_NEVER_CURRENT',async()=>{
 await db.exec('savepoint controlled_cache')
 for(const options of[{state:'FAILED'},{expired:true}]){
  await seed(options);const r=await call();assert.equal(r.status,'UNKNOWN');assert.equal(r.projection,null)
  await db.exec('rollback to savepoint controlled_cache')
 }
 await db.exec('release savepoint controlled_cache');return{failed_and_expired_ignored:true,no_automatic_retry:true}
})
await test('OW10_CACHE_MISSING_OR_CONFLICTING_CAPTURE_INDEX_REFUSED',async()=>{
 const mutations=[{noMark:true},{noPageSet:true},{noScope:true},{rows:[row('a:M','30','2')]},
  {indexKeys:['other:M','b:M']},{rows:[row('a:M','30','2'),row('a:M','50','4')]},
  {rows:[row('a:M','80','2'),row('b:M','80','4')]},
  {budget:{...cap(),contract_version:'foreign'}}]
 await db.exec('savepoint controlled_cache')
 for(const options of mutations){await seed(options);await assert.rejects(()=>call(),/CP7_(REORDER|WIP)/);await db.exec('rollback to savepoint controlled_cache')}
 await db.exec('release savepoint controlled_cache');return{malformed_or_ambiguous_private_indexes_refused:mutations.length}
})
await test('OW10_CACHE_UNKNOWN_WIP_SCHEDULE_AND_ROW_STAY_UNKNOWN',async()=>{
 const nullRow=row('a:M','30','2');nullRow.supplies=null
 const variants=[{budget:{...cap(),status:'UNKNOWN',rows:null}},{noSchedule:true},{rows:[nullRow,row('b:M','50','4')]}]
 await db.exec('savepoint controlled_cache')
 for(const options of variants){await seed(options);const r=await call();assert.equal(r.status,'UNKNOWN');if(options.rows){assert.equal(r.projection.rows[0].net,null);assert.equal(r.projection.rows[0].reason,'TARGET_SUPPLY_UNKNOWN')}else assert.equal(r.projection,null)
  await db.exec('rollback to savepoint controlled_cache')}
 await db.exec('release savepoint controlled_cache');return{unknown_contexts:3,no_missing_to_zero:true}
})
await test('OW10_CACHE_ACTUAL_K3_CLEAN_DONE_PRESERVES_RETAINED_BUDGET_AND_REPLY',async()=>{
 await seed();await db.query("insert into cp7_analysis_stage.units values($1,0,'CONTROLLED',0,null,null)",[job])
 await db.query("insert into cp7_analysis_stage.outputs values($1,0,'{\"temporary\":true}',1,clock_timestamp())",[job])
 await db.query("insert into cp7_analysis_stage.target_rows values($1,'CONTROLLED',1,'temporary','{\"temporary\":true}')",[job])
 const before=await call(),scope=(await db.query('select scope from cp7_analysis_stage.plan_scope where job_id=$1',[job])).rows[0].scope
 const cleaned=(await db.query('select cp7_analysis_stage.clean_done($1)v',[job])).rows[0].v
 assert.equal(cleaned.state,'CLEANED');assert.equal(cleaned.removed.outputs,1);assert.equal(cleaned.removed.target_rows,1)
 assert.equal((await db.query('select count(*)n from cp7_analysis_stage.outputs')).rows[0].n,0)
 assert.deepEqual((await db.query('select scope from cp7_analysis_stage.plan_scope where job_id=$1',[job])).rows[0].scope,scope)
 assert.deepEqual(await call(),before);const again=(await db.query('select cp7_analysis_stage.clean_done($1)v',[job])).rows[0].v;assert.equal(again.state,'ALREADY_CLEANED')
 return{actual_frozen_K3_clean_done_executed:true,actual_work_immutable_delete_guard_used:true,all_retained_budget_and_reader_JSON_unchanged:true,cleanup_replay_idempotent:true,full_run_unit_not_executed:true}
})
await test('OW10_CACHE_PRIVATE_STABLE_INVOKER_AND_CURRENT_QUERY_GUARDS',async()=>{
 for(const role of['anon','authenticated','service_role','cp7_alert'])assert.equal((await db.query("select has_function_privilege($1,'cp7_reorder_supply.read_job(jsonb,jsonb)','EXECUTE')f",[role])).rows[0].f,false)
 const cases=[{c:{...current(),captured_at:'tomorrow'}},{q:{...query,extra:true}},{q:{...query,through_date:'2026-10-23'}},{q:{...query,group_mode:'foreign'}}]
 for(const x of cases)await assert.rejects(()=>call(x.c??current(),x.q??query))
 const r=(await db.query("select pg_get_userbyid(proowner)o,prosecdef d,provolatile v,proconfig c from pg_proc where oid='cp7_reorder_supply.read_job(jsonb,jsonb)'::regprocedure")).rows[0]
 assert.deepEqual(r,{o:'cp7_capture',d:false,v:'s',c:['search_path=""','TimeZone=UTC']});return{actual_runtime_invoker_cp7_capture_non_superuser:true,outsiders_denied:true,invalid_clock_or_query_refused:true}
})
await seed();const installer=await audit.afterUse()
const report={classification:'LOCAL_REAL_PRIVATE_CACHE_READER_FINGERPRINT_WRAPPER_NETTING_AND_K3_SQL_WITH_CONTROLLED_NATIVE_HASH_AND_JOB_DATA_NOT_NATIVE',
 status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',passed:results.filter(x=>x.status==='PASS').length,total:results.length,installer,
 sql_sha256:sha(await read('scripts/cp7_reorder_supply/read.sql')),results,full_run_unit_executed:false,live_ROP_caller_changed:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true});await writeFile('docs/cp7/d17-14/ow10/local-supply-reader.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
