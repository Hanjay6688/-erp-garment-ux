// Actual B consumer + actual official finance_apply SQL; controlled identity,
// operational-job and A capture adapters. Not Native or factory-scale proof.
import{readFile,writeFile,mkdir}from'node:fs/promises'
import{createHash}from'node:crypto'
import assert from'node:assert/strict'
const{PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),consumer=await readFile('scripts/cp7_analysis_finance_bridge/consumer.sql','utf8')
const block=(s,name)=>{const a=s.indexOf('create function '+name+'(');assert.ok(a>=0,name);const b=s.indexOf('$$;',s.indexOf('as $$',a)+5);return s.slice(a,b+3)}
await db.exec("create role cp7_capture nologin;create role anon nologin;create role authenticated nologin;create role service_role nologin;")
await db.exec(await readFile('scripts/cp7-src/wip/bootstrap.sql','utf8'))
await db.exec(block(await readFile('scripts/cp7-src/wip/normalize.sql','utf8'),'cp7_wip.ref'))
await db.exec(`create schema cp7_schedule_native;create schema cp7_analysis_stage;create schema cp7_finance_capture;create schema cp7_analysis_native;
 create table cp7_analysis_stage.jobs(id uuid,actor uuid,request_id uuid,query jsonb,reference jsonb,captured_at timestamptz,source_hash text);
 create table cp7_finance_capture.adapter(status jsonb,result jsonb);
 create function cp7_schedule_native.access_now(boolean)returns jsonb language sql volatile as $$select jsonb_build_object('actor','11111111-1111-4111-8111-111111111111','epoch',coalesce(current_setting('ow12b.epoch',true),'before'))$$;
 create function cp7_analysis_stage.report_finance_access(jsonb,boolean)returns boolean language sql stable as $$select coalesce(current_setting('ow12b.allow',true),'yes')<>'no'$$;
 create function cp7_finance_capture.status_of(text,uuid)returns jsonb language plpgsql stable as $$begin
 if current_setting('ow12b.poison_status',true)='yes'then raise exception 'STATUS_MUST_NOT_BE_READ';end if;
 return(select status from cp7_finance_capture.adapter);end$$;
 create function cp7_finance_capture.result(uuid)returns jsonb language plpgsql volatile as $$begin
 if(select status->>'state'from cp7_finance_capture.adapter)<>'READY'then raise exception 'RESULT_MUST_NOT_BE_READ_BEFORE_READY';end if;
 if current_setting('ow12b.change_after_result',true)='yes'then perform set_config('ow12b.epoch','after',false);end if;
 return(select result from cp7_finance_capture.adapter);end$$;`)
await db.exec(block(await readFile('scripts/cp7-src/planning/analysis.sql','utf8'),'cp7_analysis_native.fact'))
const official=await readFile('scripts/cp7-src/planning/analysis-finance.sql','utf8')
await db.exec(block(official,'cp7_analysis_native.finance_apply'));await db.exec(consumer)
const job='22222222-2222-4222-8222-222222222222',request='33333333-3333-4333-8333-333333333333',capture='44444444-4444-4444-8444-444444444444'
const dates={from:'2026-09-23',to:'2026-10-22',as_of:'2026-10-23'},query={from_date:dates.from,through_date:dates.to,group_mode:'AS_SOLD'}
const status={contract_version:'cp7.finance-capture-status.v1',capture_id:capture,owner_kind:'STAGED_ANALYSIS',owner_id:job,state:'RUNNING',units_done:0,units_total:null,
 report_read_at:null,dates,readiness:null,failure_code:null,production_go:false}
const source={contract_version:'cp7.native-analysis-finance.v2',dates,capture:{id:capture},book_signature:'a'.repeat(64),source_hash:'b'.repeat(64),report:{snapshot:{data_confidence:{status:'READY'},
 performance:{sales_revenue_gl:'9007199254740993.01',gross_profit:'9007199254740893.00'},financial_position:{cash:'123.45'},basis:{performance_lifecycle_basis:'POSTED_SALES_AND_CORRECTIONS'}}}}
await db.query(`insert into cp7_analysis_stage.jobs values($1,'11111111-1111-4111-8111-111111111111',$2,$3::jsonb,'{"finance_sidecar_mode":"STAGED"}','2026-10-23T00:00:00Z',$4)`,[job,request,JSON.stringify(query),'c'.repeat(64)])
await db.query('insert into cp7_finance_capture.adapter values($1::jsonb,$2::jsonb)',[JSON.stringify(status),JSON.stringify(source)])
const set=async(s,f=source)=>db.query('update cp7_finance_capture.adapter set status=$1::jsonb,result=$2::jsonb',[JSON.stringify(s),JSON.stringify(f)])
const read=async()=>(await db.query('select cp7_analysis_finance.status($1::uuid)v',[job])).rows[0].v
const results=[];async function test(id,fn){try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,1600)})}}
await test('OW12B_LEGACY_DEFERRED_DOES_NOT_READ_FINANCE',async()=>{
 await db.exec("update cp7_analysis_stage.jobs set reference='{}';set ow12b.poison_status='yes'")
 assert.equal(await read(),null)
 await db.exec("update cp7_analysis_stage.jobs set reference='{\"finance_sidecar_mode\":\"STAGED\"}';set ow12b.poison_status='no'")
 return{legacy_shape_preserved:true,no_capture_status_or_amount_read:true}
})
await test('OW12B_RUNNING_NEVER_CALLS_RESULT',async()=>{
 const r=await read();assert.equal(r.state,'RUNNING');assert.equal(r.result,null);assert.equal(r.capture.units_total,null)
 assert.equal(r.request_id,request);assert.equal(r.job_id,job);return{operations_not_waiting:true,unknown_total_not_zero:true,no_early_financial_facts:true}
})
await test('OW12B_CURRENT_PERMISSION_BEFORE_STATUS',async()=>{
 await db.exec("set ow12b.allow='no';set ow12b.poison_status='yes'")
 const r=await read();assert.equal(r.state,'ACCESS_REVOKED');assert.equal(r.capture,null);assert.equal(r.result,null)
 await db.exec("set ow12b.allow='yes';set ow12b.poison_status='no'")
 return{financial_metadata_and_amounts_hidden:true,private_status_reader_not_called:true,actual_Auth_not_claimed:true}
})
const ready={...status,state:'READY',units_done:5,units_total:5,report_read_at:'2026-10-23T00:03:00Z',readiness:'READY'}
await test('OW12B_OFFICIAL_FINANCE_APPLY_EXACT_VALUES',async()=>{
 await set(ready);const r=await read();assert.equal(r.state,'READY');assert.equal(r.result.source_hash,source.source_hash);assert.deepEqual(r.result.dates,dates)
 const metrics=Object.fromEntries(r.result.metrics.map(m=>[m.metric_id,m]))
 assert.equal(metrics['NATIVE_FINANCE:performance:sales_revenue_gl'].value.value,'9007199254740993.01')
 assert.equal(metrics['NATIVE_FINANCE:financial_position:cash'].value.value,'123.45')
 assert.ok(r.result.metrics.every(m=>m.version==='accepted-owner-report-1'&&m.value.unit==='IDR'&&m.value.refs.every(x=>x.id===source.source_hash&&x.revision===source.source_hash)))
 await mkdir('tests/fixtures',{recursive:true});await writeFile('tests/fixtures/analysisFinanceSidecar.json',JSON.stringify(r,null,2)+'\n')
 return{same_official_SQL_function:true,large_IDR_decimal_unchanged:true,financial_math_added:false,captured_operations_and_report_times_distinct:true}
})
await test('OW12B_BLOCKED_PROFIT_STAYS_UNKNOWN',async()=>{
 await set({...ready,readiness:'BLOCKED'},{...source,report:{snapshot:{...source.report.snapshot,data_confidence:{status:'BLOCKED'}}}})
 const r=await read(),p=r.result.metrics.find(m=>m.metric_id==='NATIVE_FINANCE:performance:gross_profit')
 assert.equal(r.result.readiness,'BLOCKED');assert.equal(p.value.state,'UNKNOWN');assert.ok(!('value'in p.value))
 return{official_report_confidence_preserved:true,unproved_profit_not_zero:true}
})
await test('OW12B_BINDING_AND_CLOSED_OWNER_DATE_SOURCE',async()=>{
 let refused=0
 for(const delta of[{owner_id:'55555555-5555-4555-8555-555555555555'},{owner_id:null},{owner_kind:null},{contract_version:null},{state:null},{dates:{...dates,as_of:'2026-10-22'}}]){
  await set({...ready,...delta});await assert.rejects(read,/CP7_ANALYSIS_FINANCE_CAPTURE_CHANGED/);refused++
 }
 for(const delta of[{source_hash:'not-a-hash'},{dates:{...dates,to:'2026-10-21'}},{contract_version:null}]){
  await set(ready,{...source,...delta});await assert.rejects(read,/CP7_ANALYSIS_FINANCE_CAPTURE_CHANGED/);refused++
 }
 return{owner_job_and_date_source_refusals:refused}
})
await test('OW12B_FAILED_AND_ACCESS_CHANGED_NO_RESULT',async()=>{
 await set({...status,state:'FAILED',failure_code:'CP7_FINANCE_CAPTURE_SOURCE_CHANGED'});const r=await read();assert.equal(r.state,'FAILED');assert.equal(r.result,null)
 await set(ready);await db.exec("set ow12b.change_after_result='yes';set ow12b.epoch='before'")
 await assert.rejects(read,/CP7_ANALYSIS_FINANCE_ACCESS_CHANGED/)
 await db.exec("set ow12b.change_after_result='no';set ow12b.epoch='before'")
 return{failed_capture_has_no_figures:true,second_access_check_fences_reply:true,controlled_change_not_Native_race:true}
})
const report={classification:'LOCAL_ACTUAL_CONSUMER_AND_OFFICIAL_OVERLAY_WITH_CONTROLLED_JOB_IDENTITY_AND_A_CAPTURE_ADAPTERS_NOT_NATIVE',status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',
 consumer_sha256:createHash('sha256').update(consumer).digest('hex'),official_overlay_sha256:createHash('sha256').update(block(official,'cp7_analysis_native.finance_apply')).digest('hex'),cases:results,
 OW12b_complete:false,full_A_chain_qualified:false,factory_scale_proven:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow12b',{recursive:true});await writeFile('docs/cp7/d17-14/ow12b/local-finance.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
