// Independent bounded performance check, no application SLA inference.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'
import {openRuntime,jsonArg} from '../../tests/cp7/families/f04/runtime.mjs'
import {installNettingControls,nettingInput,suffixed} from '../../tests/cp7/families/f04/netting-fixture.mjs'
import {functionBlocks} from '../../tests/cp7/families/f04/schedule-scenario-fixture.mjs'
const base='aa638356e13aeffe7b2a2aa96f17dbe19676db1f',path='scripts/cp7-src/planning/netting.sql'
const old=execFileSync('git',['show',`${base}:${path}`],{encoding:'utf8'})
const blocks=[...functionBlocks(old)].filter(([n])=>/^cp7_netting_native\.(bound_product|matching_models_within|matching_models|matching|matches|timeline|build)$/.test(n)).map(([,v])=>v).join('\n')
const report={candidate:'8cc1b0818fdba54f3ebeb64e132f7f3e20309e24',oracle:base,status:'INCOMPLETE',scope:'ISOLATED_SQL_TIMING_NO_AUTH_SLA',cases:[],production_go:false}
let db
try{
 db=await openRuntime({commandTimeoutMs:600000});report.runtime={flavor:db.flavor,version:db.version}
 await installNettingControls(db);await db.execute(suffixed(blocks,'_sol_perf'))
 await db.execute(`create table public.sol_perf_input(id integer primary key,c jsonb);
 create function public.sol_time(fn text,id integer)returns jsonb language plpgsql as $$
 declare c jsonb;r jsonb;t timestamptz;begin
 select x.c into c from public.sol_perf_input x where x.id=sol_time.id;
 t:=clock_timestamp();execute format('select cp7_netting_native.%I($1,$2)',fn)into r using c,'{}'::jsonb;
 return jsonb_build_object('fn',fn,'ms',extract(epoch from clock_timestamp()-t)*1000,'hash',md5(r::text),'bytes',octet_length(r::text),'targets',jsonb_array_length(r->'rows'));end $$;`)
 for(const [id,positions]of [0,40].entries()){
  const c=nettingInput(9181+id,{targets:300,positions,roots:100,models:20,complete:true})
  c.stub_scenario.supply_run_result.baseline_run_result.rows.forEach(r=>{r.profile.config={lead_days:'3',review_days:'7'};r.demand_estimate.daily_pcs='2.125';r.production_policy={policy:{state:'ACTIVE'}}})
  await db.execute(`insert into public.sol_perf_input values(${id},${jsonArg(c)})`)
  const samples=(await db.query(`select public.sol_time(x.fn,${id}) r from unnest(array['build_sol_perf','build','build_sol_perf','build','build','build_sol_perf'])with ordinality x(fn,o)order by o`)).slice(2).map(x=>x.r)
  samples.forEach(r=>{assert.equal(r.hash,samples[0].hash);assert.equal(r.bytes,samples[0].bytes)})
  const mean=fn=>samples.filter(r=>r.fn===fn).reduce((s,r)=>s+Number(r.ms),0)/2
  const oldMs=mean('build_sol_perf'),newMs=mean('build')
  report.cases.push({positions,targets:samples[0].targets,old_ms:oldMs,new_ms:newMs,reduction_percent:100*(oldMs-newMs)/oldMs,samples})
 }
 report.status='PASS';console.log(JSON.stringify(report))
}catch(e){report.error=e.stack;throw e}finally{
 if(db)await db.close();mkdirSync('test-results/sol-p20-k4',{recursive:true});writeFileSync('test-results/sol-p20-k4/PR44_BENCHMARK.json',JSON.stringify(report,null,2)+'\n')
}
