// Real yield/timing/budget/net SQL and the real patched ANA_META scope INSERT.
// Source/history/job fixtures are controlled; no Native/Auth/K3 deployment claim.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const read=p=>readFile(p,'utf8'),db=new PGlite()
await db.exec(`create role cp7_capture;create role anon;create role authenticated;create role service_role;
 create schema cp7_planning;create schema cp7_analysis_stage;create schema cp7_analysis_native;create schema cp7_netting_native;
 create schema cp7_fabric_native;create schema erp;create schema extensions;
 create table cp7_analysis_stage.jobs(id uuid primary key);
 create table cp7_analysis_stage.plan_scope(job_id uuid primary key references cp7_analysis_stage.jobs(id),scope jsonb not null);
 create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)$$;`)
for(const p of['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7-src/wip/yield.sql','scripts/cp7-src/wip/timing.sql',
 'scripts/cp7_production_stage/sql/cp7_baseline__net.sql','scripts/cp7_reorder_supply/projection.sql'])await db.exec(await read(p))
const planning=await read('scripts/cp7-src/planning/bootstrap.sql'),start=planning.indexOf('create function cp7_planning.utc(')
await db.exec(planning.slice(start,planning.indexOf('$$;',planning.indexOf('as $$',start))+3))
const capture=await read('scripts/cp7_reorder_supply/capture.sql');await db.exec(capture)
const hook=JSON.parse(execFileSync('python',['-B','-c',`import sys,json
from pathlib import Path
sys.path.insert(0,'scripts')
from cp7_reorder_supply.patches import RUN,SOURCE,patched
old={}
for sig,file,name in [(RUN,'scripts/cp7-src/planning/analysis-stages.sql','cp7_analysis_stage.run_unit'),(SOURCE,'scripts/cp7-src/planning/analysis.sql','cp7_analysis_native.source_within')]:
 s=Path(file).read_text();a=s.index('create function '+name+'(');b=s.index('$$;',s.index('as $$',a))+3;old[sig]=s[a:b]
new=patched(old)
print(json.dumps(dict(run_original=old[RUN],run_patched=new[RUN],source_original=old[SOURCE],source_patched=new[SOURCE])))`],{encoding:'utf8',maxBuffer:1000000}))
const scopeInsert=s=>s.slice(s.indexOf('   insert into cp7_analysis_stage.plan_scope'),s.indexOf('   insert into cp7_analysis_stage.plan_groups'))
for(const [name,definition]of[['legacy',hook.run_original],['new',hook.run_patched]]){
 const sql=scopeInsert(definition);assert.ok(sql.startsWith('   insert into'));assert.ok(sql.trimEnd().endsWith(';'))
 await db.exec(`create function public.controlled_${name}_scope(arg jsonb)returns void language plpgsql as $$
 declare j cp7_analysis_stage.jobs;wip jsonb:=arg->'wip';c jsonb:=arg->'c';scenario jsonb:=arg->'scenario';
 alloc jsonb:=arg->'alloc';skel jsonb:=arg->'skel';begin j.id:=(arg->>'job_id')::uuid;
 ${sql}
 end $$;`)
}
const refs=[{kind:'CONTROLLED_POSTED_SOURCE',id:'cut-group',revision:'1'}],snapshot='controlled-snapshot',physical='CUT:group-1:M'
const baseWip=()=>({contract_version:'cp7.wip-position.v1',status:'COMPLETE',snapshot_id:snapshot,scope_id:'GLOBAL_NATIVE_PLANNING',
 positions:[{key:physical,size_id:'M',remaining_pcs:'100',eligible_company_wip:true}],
 totals:[{pool_key:'CUT:group-1',ownership:'COMPANY',size_id:'M',wip_pcs:'100'}]})
const yieldPolicy=[{position_key:physical,eligible_input_pcs:'100',numerator:'4',denominator:'5',basis:'HISTORY',assumption_id:null,refs}]
const realWip=async()=>(await db.query('select cp7_wip.project_yield($1::jsonb,$2::jsonb)v',[JSON.stringify(baseWip()),JSON.stringify(yieldPolicy)])).rows[0].v
const realEta=async()=>{
 const work=[{stage:'SEWING',remaining_minutes:'60',basis:'ASSUMED',assumption_id:'controlled-calendar',calendar_version:'controlled-calendar:1',
  windows:[{start:'2026-10-26T00:00:00Z',end:'2026-10-26T02:00:00Z'}],refs}]
 return(await db.query("select cp7_wip.remaining_eta('2026-10-26T00:00:00Z','2026-11-02T00:00:00Z',$1::jsonb)v",[JSON.stringify(work)])).rows[0].v
}
const budgets=async(wip,etas)=>(await db.query('select cp7_reorder_supply.budgets($1::jsonb,$2::jsonb)v',[JSON.stringify(wip),JSON.stringify(etas)])).rows[0].v
const etaRows=async()=>[{position_key:physical,result:await realEta(),refs}]
const results=[],test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,2500)})}}
await test('OW10_BUDGET_ACTUAL_YIELD_AND_UTC_CALENDAR_REPLY',async()=>{
 const wip=await realWip(),etas=await etaRows(),r=await budgets(wip,etas)
 assert.equal(wip.positions[0].projection.projected_good_pcs,'80');assert.equal(etas[0].result.status,'CONDITIONAL')
 assert.equal(etas[0].result.eta,'2026-10-26T01:00:00+00:00')
 assert.deepEqual(r,{contract_version:'cp7.reorder-supply-budget.v1',status:'COMPLETE',snapshot_id:snapshot,reason:null,
  rows:[{physical_key:physical,snapshot_id:snapshot,size_id:'M',projected_good_pcs:'80',eta:'2026-10-26T01:00:00.000000Z',eligible:true}]})
 return{actual_yield_100_times_4_over_5:80,actual_calendar_minutes:60,actual_SQL_offset_reply_canonicalized:true,no_yield_or_queue_recalculation:true}
})
await test('OW10_BUDGET_UNKNOWN_YIELD_TIME_AND_SCOPE_NOT_ZERO',async()=>{
 const w=await realWip(),e=await etaRows();w.positions[0].projection={quality:'UNKNOWN',reason:'CONTROLLED_NO_HISTORY'}
 let r=await budgets(w,e);assert.equal(r.rows[0].projected_good_pcs,null)
 r=await budgets(await realWip(),[]);assert.equal(r.rows[0].eta,null)
 r=await budgets(await realWip(),[{position_key:physical,result:{status:'UNKNOWN',eta:null},refs}]);assert.equal(r.rows[0].eta,null)
 r=await budgets({status:'UNKNOWN'},null);assert.equal(r.status,'UNKNOWN');assert.equal(r.rows,null)
 return{unknown_quantity_and_ETA_preserved:true,incomplete_scope_rows_null_not_empty:true}
})
await test('OW10_BUDGET_EXCLUDES_NON_COMPANY_AND_PRESERVES_EXPLICIT_ZERO',async()=>{
 const w=await realWip();w.positions.push({key:'CUSTOMER:else:M',eligible_company_wip:false})
 const r=await budgets(w,await etaRows());assert.equal(r.rows.length,1)
 w.positions[0].projection.projected_good_pcs='0';assert.equal((await budgets(w,await etaRows())).rows[0].projected_good_pcs,'0')
 w.positions[0].eligible_company_wip=false;assert.deepEqual((await budgets(w,await etaRows())).rows,[])
 return{customer_WIP_not_company_supply:true,explicit_zero_distinct_from_unknown:true}
})
await test('OW10_BUDGET_DUPLICATES_MISSING_ELIGIBILITY_AND_RELATIVE_TIME_REFUSED',async()=>{
 const w=await realWip(),e=await etaRows()
 await assert.rejects(()=>budgets({...w,positions:[...w.positions,...w.positions]},e),/CP7_REORDER_CAPTURE_DUPLICATE_POSITION/)
 await assert.rejects(()=>budgets(w,[...e,...e]),/CP7_REORDER_CAPTURE_DUPLICATE_ETA/)
 const bad=structuredClone(w);delete bad.positions[0].eligible_company_wip
 await assert.rejects(()=>budgets(bad,e),/CP7_REORDER_CAPTURE_ELIGIBILITY_UNKNOWN/)
 for(const at of['tomorrow','2026-02-30T00:00:00Z','2026-10-26T01:00:00+07:00']){
  const badEta=structuredClone(e);badEta[0].result.eta=at;await assert.rejects(()=>budgets(w,badEta))
 }
 return{ambiguous_sources_refused:true,no_relative_or_unexpected_zone_datetime:true}
})
await test('OW10_REAL_COUNTED_ANA_META_INSERT_RETAINS_BUDGET_AND_ALL_OLD_FIELDS',async()=>{
 const wip=await realWip(),etas=await etaRows(),c={production_sources:{facts:{cutting:{groups:[{id:'group-1',model_id:'model-1'}]}}},fabric_source:{selected:[]}}
 const arg={wip,c,scenario:{status:'SCENARIO',capacity:{status:'CONTROLLED_ASSUMPTION'},schedule_state:'SELECTED_ASSUMPTIONS',etas},alloc:{status:'SCENARIO'},skel:{assumptions:[]}}
 for(const [which,id]of[['legacy','00000000-1111-4111-8111-111111111111'],['new','00000000-2222-4222-8222-222222222222']]){
  await db.query('insert into cp7_analysis_stage.jobs values($1::uuid)',[id]);await db.query('select public.controlled_'+which+'_scope($1::jsonb)',[JSON.stringify({...arg,job_id:id})])
 }
 const rows=(await db.query('select scope from cp7_analysis_stage.plan_scope order by job_id')).rows,old=rows[0].scope,now=rows[1].scope
 const {reorder_supply_budget:retained,...unchanged}=now;assert.deepEqual(unchanged,old);assert.deepEqual(retained,await budgets(wip,etas))
 assert.equal(now.wip_by_model_size['model-1:M'],'100');assert.equal(retained.rows[0].projected_good_pcs,'80')
 await db.exec('begin;select count(*)from cp7_analysis_stage.plan_scope;commit;')
 const kept=(await db.query("select scope->'reorder_supply_budget'v from cp7_analysis_stage.plan_scope where job_id='00000000-2222-4222-8222-222222222222'")).rows[0].v
 assert.deepEqual(kept,retained)
 return{actual_patched_scope_INSERT_executed:true,all_old_scope_fields_full_JSON_unchanged:true,raw_report_100_distinct_from_projected_good_80:true,retained_after_commit:true,actual_K3_clean_done_executed:false}
})
await test('OW10_BUDGET_REAL_SOURCE_HOOK_COVERS_PRIVATE_ENGINE_CODE',async()=>{
 await db.exec(`create function cp7_netting_native.source_within(integer,integer)returns jsonb language sql stable as $$select '{"controlled_native":true}'::jsonb$$;
 create function cp7_analysis_native.material_source(jsonb,timestamptz)returns jsonb language sql stable as $$select '{}'::jsonb$$;
 create function cp7_fabric_native.source(jsonb,timestamptz)returns jsonb language sql stable as $$select '{}'::jsonb$$;
 create function erp.get_owner_financial_snapshot_v2(date,date,date)returns jsonb language sql stable as $$select '{}'::jsonb$$;`)
 await db.exec(hook.source_original);const before=(await db.query('select cp7_analysis_native.source_within(5000,10000)v')).rows[0].v
 await db.exec(hook.source_patched.replace('create function ','create or replace function '))
 const now=(await db.query('select cp7_analysis_native.source_within(5000,10000)v')).rows[0].v
 assert.equal(now.reorder_supply_engine,'cp7.reorder-supply.v1');assert.notEqual(now.analysis_engine_signature,before.analysis_engine_signature)
 const clean=x=>{const y={...x};delete y.reorder_supply_engine;delete y.analysis_engine_signature;return y};assert.deepEqual(clean(now),clean(before))
 const changed=capture.replace('create function ','create or replace function ').replace('begin\n','begin\n -- controlled temporary engine mutation\n')
 await db.exec(changed);const after=(await db.query('select cp7_analysis_native.source_within(5000,10000)v')).rows[0].v
 assert.notEqual(after.analysis_engine_signature,now.analysis_engine_signature)
 await db.exec(capture.replace('create function ','create or replace function '));assert.equal((await db.query('select cp7_analysis_native.source_within(5000,10000)v')).rows[0].v.analysis_engine_signature,now.analysis_engine_signature)
 return{actual_source_hook_executed_with_controlled_Native_adapter:true,other_source_fields_full_JSON_unchanged:true,private_budget_code_in_engine_signature:true,restoring_code_restores_signature:true}
})
await test('OW10_BUDGET_PRIVATE_AUTHORITY_ONLY',async()=>{
 for(const role of['anon','authenticated','service_role'])assert.equal((await db.query("select has_function_privilege($1,'cp7_reorder_supply.budgets(jsonb,jsonb)','EXECUTE')f",[role])).rows[0].f,false)
 const r=(await db.query("select pg_get_userbyid(proowner)o,prosecdef d,provolatile v,proconfig c from pg_proc where oid='cp7_reorder_supply.budgets(jsonb,jsonb)'::regprocedure")).rows[0]
 assert.deepEqual(r,{o:'cp7_capture',d:false,v:'i',c:['search_path=""','TimeZone=UTC']});return{private_invoker_immutable_empty_search_path:true,no_Native_DML_grants:true}
})
const report={classification:'LOCAL_REAL_YIELD_TIMING_BUDGET_AND_RETAINED_SCOPE_SQL_WITH_CONTROLLED_SOURCE_AND_JOB_TABLES_NOT_NATIVE',status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',
 passed:results.filter(x=>x.status==='PASS').length,total:results.length,sql_sha256:createHash('sha256').update(capture).digest('hex'),
 hook_body_files_sha256:{run_original:createHash('sha256').update(hook.run_original).digest('hex'),run_patched:createHash('sha256').update(hook.run_patched).digest('hex'),
 source_original:createHash('sha256').update(hook.source_original).digest('hex'),source_patched:createHash('sha256').update(hook.source_patched).digest('hex')},
 results,full_run_unit_and_K3_executed:false,reversible_stage_and_fresh_reader_pending:true,live_ROP_caller_changed:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true});await writeFile('docs/cp7/d17-14/ow10/local-supply-retention.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
