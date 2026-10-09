// Sol's independent comparisons. Fixture transport is reused; the inventory,
// mutations and acceptance assertions below are independently declared.
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {openRuntime,jsonArg} from '../../tests/cp7/families/f04/runtime.mjs'
import {DEFECTS,installNettingControls,nettingInput,orderProbe,suffixed} from '../../tests/cp7/families/f04/netting-fixture.mjs'
import {functionBlocks} from '../../tests/cp7/families/f04/schedule-scenario-fixture.mjs'
const path='scripts/cp7-src/planning/netting.sql',base='aa638356e13aeffe7b2a2aa96f17dbe19676db1f'
const old=execFileSync('git',['show',`${base}:${path}`],{encoding:'utf8'}),current=readFileSync(path,'utf8')
const helpers=s=>[...functionBlocks(s)].filter(([n])=>/^cp7_netting_native\.(bound_product|matching_models_within|matching_models|matching|matches|timeline|build)$/.test(n)).map(([,v])=>v).join('\n')
const hash=s=>createHash('sha256').update(s).digest('hex')
const report={candidate:'8cc1b0818fdba54f3ebeb64e132f7f3e20309e24',oracle:base,source_sha256:hash(current),status:'INCOMPLETE',scope:'REAL_NETTING_SQL_WITH_FIXTURE_SCHEDULE_NOT_FULL_AUTH_APPLICATION',cases:[],mutations:[],production_go:false}
let db
try {
 db=await openRuntime({commandTimeoutMs:600000}); report.runtime={flavor:db.flavor,version:db.version}
 await installNettingControls(db,{mutants:['REUSE_BY_KEY_ONLY']})
 await db.execute(suffixed(helpers(old),'_sol_base'))
 const guard="if line_edges='[]'::jsonb and baseline_rows[(planned_index->>(r->>'target_key'))::integer]=r::text then"
 assert.equal(helpers(current).split(guard).length,2)
 await db.execute(suffixed(helpers(current).replace(guard,"if baseline_rows[(planned_index->>(r->>'target_key'))::integer]=r::text then"),'_sol_ignore_supply'))
 await db.execute(`create function public.sol_compare(c jsonb,fn text,mode text)returns jsonb language plpgsql as $$
 declare a jsonb;b jsonb;sa text:='OK';sb text:='OK';begin
 perform set_config('plan_cache_mode',mode,true);
 begin a:=cp7_netting_native.build_sol_base(c,'{}');exception when others then sa:=sqlstate||':'||sqlerrm;end;
 begin execute format('select cp7_netting_native.%I($1,$2)',fn)into b using c,'{}'::jsonb;exception when others then sb:=sqlstate||':'||sqlerrm;end;
 return jsonb_build_object('same',a::text is not distinct from b::text,'old_error',sa,'new_error',sb,'old_hash',md5(a::text),'new_hash',md5(b::text),
 'events',(select count(*)from jsonb_array_elements(coalesce(a->'rows','[]'))r,jsonb_array_elements(coalesce(r->'timeline'->'inputs'->'events','[]'))e where e->>'kind'='SUPPLY'));end $$;`)
 const cases=[{id:'REFUSAL_ORDER',c:orderProbe(false)},{id:'REFUSAL_ORDER_REVERSED',c:orderProbe(true)}],twins=[],supply=[]
 for(let seed=701;seed<=704;seed++)for(const defect of DEFECTS) {
  if(defect==='BIG_HORIZON'&&seed!==701)continue
  cases.push({id:`FAULT_${seed}_${defect}_${cases.length}`,c:nettingInput(seed,{positions:11,targets:7,roots:4,models:3,complete:true,defect})})
 }
 for(let seed=801;seed<=808;seed++) {
  const c=nettingInput(seed,{positions:0,targets:5,roots:3,models:2,complete:true})
  const rows=c.stub_scenario.supply_run_result.baseline_run_result.rows
  rows.forEach((r,i)=>{r.production_policy={policy:{state:'ACTIVE'}};r.target={status:'SCENARIO',target_pcs:String(20+i)};r.available_fg_pcs=String(i);r.profile.config={lead_days:'2.5',review_days:String(1+i)};r.demand_estimate.daily_pcs=String(1+i/4)})
  cases.push({id:`EMPTY_DISTINCT_${seed}`,c})
  for(const kind of ['UNKNOWN_TARGET','NULL_FG'])for(const before of [true,false]) {
   const v=structuredClone(c),arr=v.stub_scenario.supply_run_result.baseline_run_result.rows,r=structuredClone(arr[0])
   r.refs=[{kind:'PRODUCT_TARGET',id:'independent-skipped-twin',revision:'1'}]
   if(kind==='UNKNOWN_TARGET')r.target={status:'UNKNOWN',target_pcs:null};else r.available_fg_pcs=null
   arr.splice(before?0:1,0,r)
   const row={id:`TWIN_${seed}_${kind}_${before?'FIRST':'LAST'}`,c:v};cases.push(row);twins.push(row)
  }
  const withSupply={id:`SUPPLY_${seed}`,c:nettingInput(seed,{positions:40,targets:8,roots:4,models:2,complete:true})}
  cases.push(withSupply);supply.push(withSupply)
 }
 report.declared=cases.length
 let events=0,ok=0;const refusals=new Set()
 for(const [i,row] of cases.entries()) {
  const mode=['auto','force_generic_plan','force_custom_plan'][i%3]
  const {r}=(await db.query(`select public.sol_compare(${jsonArg(row.c)},'build','${mode}') r`))[0]
  report.cases.push({id:row.id,mode,...r})
  assert.equal(r.same,true,row.id);assert.equal(r.new_error,r.old_error,row.id)
  if(r.old_error==='OK')ok++;else refusals.add(r.old_error)
  events+=Number(r.events)
 }
 assert(ok>30);assert(refusals.size>=8);assert(events>0)
 for(const [name,fn,rows] of [['KEY_ONLY','build_m_reuse_by_key_only',twins],['SUPPLY_IGNORED','build_sol_ignore_supply',supply]]) {
  let witness
  for(const row of rows){const {r}=(await db.query(`select public.sol_compare(${jsonArg(row.c)},'${fn}','auto') r`))[0];if(!r.same||r.old_error!==r.new_error){witness={id:row.id,...r};break}}
  report.mutations.push({name,caught:!!witness,witness});assert(witness,`negative control ${name} escaped`)
 }
 assert.deepEqual(await db.query('select id,amount::text amount from public.f04_ledger_canary'),[{id:1,amount:'12345.67'}])
 report.counts={declared:cases.length,executed:report.cases.length,successes:ok,refusals:cases.length-ok,distinct_refusals:refusals.size,supply_events:events,mutants_caught:report.mutations.length}
 report.status='PASS'
} catch(e){report.error=e.stack;throw e}finally {
 if(db)await db.close();mkdirSync('test-results/sol-p20-k4',{recursive:true});writeFileSync('test-results/sol-p20-k4/PR44.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,counts:report.counts,error:report.error}))
}
