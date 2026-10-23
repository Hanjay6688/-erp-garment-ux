// Actual SQL kernels and global conservation guard; controlled source inputs.
// This is not Native, a fresh-cache adapter, or an installed ROP caller.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8')
await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;')
for(const p of['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql',
 'scripts/cp7_production_stage/sql/cp7_baseline__net.sql','scripts/cp7_reorder_supply/projection.sql'])await db.exec(await read(p))
const refs=[{kind:'CONTROLLED_GLOBAL_SOURCE',id:'source-1',revision:'1'}],snapshot='snapshot-1',size='M'
const query={from_date:'2026-09-23',through_date:'2026-10-22',group_mode:'AS_SOLD'}
const budget=(physical='CUT:group-1:M',qty='80',eta='2026-10-26T00:00:00Z')=>({physical_key:physical,snapshot_id:snapshot,size_id:size,projected_good_pcs:qty,eta,eligible:true})
const supply=(target='root-a:M',qty='30',physical='CUT:group-1:M',kind='ALLOCATED_CANDIDATE',eta='2026-10-26T00:00:00Z')=>
 ({physical_key:physical,snapshot_id:snapshot,target_key:target,size_id:size,kind,qty_pcs:qty,eta,eligible:true,refs})
const target=(key='root-a:M',supplies=[supply(key)],fg='2')=>({target_key:key,size_id:size,reorder_point_pcs:'40',target_pcs:'100',available_fg_pcs:fg,
 lead_deadline:'2026-10-26T00:00:00Z',deadline:'2026-11-02T00:00:00Z',supplies,refs})
const fixture=()=>({contract_version:'cp7.reorder-supply-input.v1',snapshot_id:snapshot,scope_id:'GLOBAL_NATIVE_PLANNING',scenario_id:'schedule-1',
 captured_at:'2026-10-23T00:00:00Z',checked_at:'2026-10-23T00:00:01Z',source_hash:'a'.repeat(64),current_source_hash:'a'.repeat(64),
 source_state:'CURRENT',complete_scope:true,wip_status:'COMPLETE',allocation_status:'SCENARIO',query,expected_query:query,
 budgets:[budget()],targets:[target(),target('root-b:M',[supply('root-b:M','50')],'4')],refs})
const project=async v=>(await db.query('select cp7_reorder_supply.project($1::jsonb)v',[JSON.stringify(v)])).rows[0].v
const results=[]
const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,2500)})}}
await test('OW10_SUPPLY_ONE_RAW_POOL_NOT_CREDITED_TO_BOTH_VARIANTS',async()=>{
 const v=fixture(),r=await project(v),a=r.rows[0].net,b=r.rows[1].net
 assert.equal(r.status,'SCENARIO');assert.equal(a.lead_position_base_pcs,'2');assert.equal(b.lead_position_base_pcs,'4')
 assert.equal(a.lead_position_conditional_pcs,'32');assert.equal(b.lead_position_conditional_pcs,'54')
 assert.equal(a.base_reorder_state,'AT_OR_BELOW');assert.equal(b.base_reorder_state,'AT_OR_BELOW');assert.equal(b.conditional_reorder_state,'ABOVE')
 const projected=80n,allocated=v.targets.reduce((n,t)=>n+t.supplies.reduce((z,s)=>z+BigInt(s.qty_pcs),0n),0n)
 assert.equal(allocated,projected);assert.equal(a.lead_net.candidate_on_time_pcs,'30');assert.equal(b.lead_net.candidate_on_time_pcs,'50')
 assert.notEqual(a.lead_position_base_pcs,'82');assert.notEqual(b.lead_position_base_pcs,'84')
 return{controlled_raw_pieces:100,source_projected_good:80,unique_candidate_shares:[30,50],base_positions:[2,4],conditional_positions:[32,54],candidate_never_suppresses_base:true}
})
await test('OW10_SUPPLY_DIRECTED_ONLY_EXACT_TARGET_AND_TWO_HORIZONS',async()=>{
 const v=fixture();v.budgets=[budget('CUT:bound:M','60')];v.targets=[target('root-a:M',[supply('root-a:M','60','CUT:bound:M','DIRECTED')]),target('root-b:M',[],'4')]
 const r=await project(v);assert.equal(r.rows[0].net.lead_position_base_pcs,'62');assert.equal(r.rows[0].net.base_reorder_state,'ABOVE');assert.equal(r.rows[1].net.lead_position_base_pcs,'4')
 const late=structuredClone(v);late.budgets[0].eta='2026-10-27T00:00:00Z';late.targets[0].supplies[0].eta=late.budgets[0].eta
 const l=await project(late);assert.equal(l.rows[0].net.lead_position_base_pcs,'2');assert.equal(l.rows[0].net.directed_on_time_pcs,'60');assert.equal(l.rows[0].net.base_reorder_state,'AT_OR_BELOW')
 late.budgets[0].eta='2026-11-03T00:00:00Z';late.targets[0].supplies[0].eta=late.budgets[0].eta
 const beyond=await project(late);assert.equal(beyond.rows[0].net.directed_on_time_pcs,'0')
 return{exact_target_only:true,after_lead_does_not_hide_reorder:true,after_horizon_excluded:true}
})
await test('OW10_SUPPLY_REJECTS_DOUBLE_DIRECTED_OVERALLOCATED_AND_MIXED_POOL',async()=>{
 const doubled=fixture();for(const r of doubled.targets){r.supplies[0].kind='DIRECTED';r.supplies[0].qty_pcs='80'}
 await assert.rejects(()=>project(doubled),/CP7_REORDER_PHYSICAL_SOURCE_CONFLICT/)
 const over=fixture();for(const r of over.targets)r.supplies[0].qty_pcs='80'
 await assert.rejects(()=>project(over),/CP7_REORDER_GLOBAL_BUDGET_EXCEEDED/)
 const mixed=fixture();mixed.targets[0].supplies[0].kind='DIRECTED'
 await assert.rejects(()=>project(mixed),/CP7_REORDER_PHYSICAL_SOURCE_CONFLICT/)
 return{copied_model_pool_refused:true,overallocated_split_refused:true,directed_plus_candidate_same_source_refused:true}
})
await test('OW10_SUPPLY_EXACT_REPLAY_IS_ONCE_CONFLICTING_REPLAY_REFUSED',async()=>{
 const v=fixture(),original=await project(v);v.targets[0].supplies.push(structuredClone(v.targets[0].supplies[0]))
 // The official kernel preserves submitted inputs. Only those two input
 // arrays change; every computed number/state and all other metadata agree.
 const expected=structuredClone(original)
 expected.rows[0].net.inputs.supplies=structuredClone(v.targets[0].supplies)
 expected.rows[0].net.lead_net.inputs.supplies=structuredClone(v.targets[0].supplies)
 assert.deepEqual(await project(v),expected)
 v.targets[0].supplies[1].qty_pcs='29';await assert.rejects(()=>project(v),/CP7_BASELINE_PHYSICAL_SOURCE_CONFLICT/)
 return{identical_replay_numbers_and_states_unchanged:true,submitted_duplicate_inputs_preserved:true,conflicting_replay_refused:true}
})
await test('OW10_SUPPLY_SOURCE_PERIOD_SCOPE_AND_WIP_CHANGE_NEVER_ZERO',async()=>{
 const changes=[v=>{v.current_source_hash='b'.repeat(64)},v=>{v.source_state='ARCHIVED_STALE'},v=>{v.source_state='UNKNOWN'},
  v=>{v.expected_query={...v.query,from_date:'2026-09-24'}},v=>{v.expected_query={...v.query,group_mode:'RESTATED'}},v=>{v.complete_scope=false},v=>{v.wip_status='UNKNOWN'}]
 for(const change of changes){const v=fixture();change(v);const r=await project(v);assert.equal(r.status,'UNKNOWN');for(const x of r.rows){assert.equal(x.net,null);assert.equal(x.status,'UNKNOWN');assert.ok(x.reason)}}
 return{stale_and_incomplete_variants:changes.length,old_snapshot_never_presented_as_current:true}
})
await test('OW10_SUPPLY_UNKNOWN_YIELD_ETA_AND_UNPROVEN_CANDIDATES',async()=>{
 for(const field of['qty_pcs','eta']){const v=fixture();for(const t of v.targets)t.supplies[0][field]=null;v.budgets[0][field==='qty_pcs'?'projected_good_pcs':'eta']=null
  const r=await project(v);assert.equal(r.status,'UNKNOWN');for(const t of r.rows){assert.equal(t.net.status,'UNKNOWN');assert.equal(t.net.lead_position_base_pcs,null)}}
 const fake=fixture();fake.budgets[0].projected_good_pcs=null;await assert.rejects(()=>project(fake),/CP7_REORDER_BUDGET_UNKNOWN_CREDIT/)
 const unproven=fixture();unproven.allocation_status='UNKNOWN';await assert.rejects(()=>project(unproven),/CP7_REORDER_UNPROVEN_ALLOCATION/)
 const directed=fixture();directed.allocation_status='UNKNOWN';directed.targets=[target('root-a:M',[supply('root-a:M','80',undefined,'DIRECTED')])]
 const d=await project(directed);assert.equal(d.rows[0].net.lead_position_base_pcs,'82');assert.equal(d.status,'PARTIAL')
 assert.equal(d.rows[0].net.q_conditional_pcs,null);assert.equal(d.rows[0].net.candidate_on_time_pcs,null)
 assert.equal(d.rows[0].net.lead_net.candidate_on_time_pcs,null);assert.equal(d.rows[0].net.lead_position_conditional_pcs,null)
 assert.equal(d.rows[0].net.conditional_reorder_state,'UNKNOWN')
 return{unknown_not_zero:true,unproven_candidate_refused:true,directed_independent_of_candidate_allocation:true}
})
await test('OW10_SUPPLY_WRONG_SIZE_SOURCE_SNAPSHOT_TIME_AND_ELIGIBILITY_REFUSED',async()=>{
 const changes=[v=>{v.targets[0].supplies[0].size_id='L'},v=>{v.targets[0].supplies[0].snapshot_id='older'},
  v=>{v.targets[0].supplies[0].target_key='root-b:M'},v=>{v.targets[0].supplies[0].physical_key='absent'},
  v=>{v.targets[0].supplies[0].eta='2026-10-25T00:00:00Z'},v=>{v.budgets[0].eligible=false},v=>{v.budgets[0].snapshot_id='older'}]
 for(const change of changes){const v=fixture();change(v);await assert.rejects(()=>project(v),/CP7_REORDER_(SUPPLY|POSITION|BUDGET)_BINDING/)}
 return{conflicting_bindings_refused:changes.length}
})
await test('OW10_SUPPLY_INELIGIBLE_STAYS_EXCLUDED',async()=>{
 const v=fixture();v.budgets[0].eligible=false;for(const t of v.targets)t.supplies[0].eligible=false
 const r=await project(v);assert.equal(r.rows[0].net.lead_position_base_pcs,'2');assert.equal(r.rows[1].net.lead_position_conditional_pcs,'4')
 assert.equal(r.rows[0].net.lead_net.excluded[0].reason,'INELIGIBLE');return{ineligible_source_never_available_stock:true}
})
await test('OW10_SUPPLY_SIGNED_STOCK_ZERO_POINT_AND_BIG_INTEGER_EXACT',async()=>{
 const v=fixture();v.budgets=[];v.targets=[target('a:M',[],'-7')];const a=(await project(v)).rows[0].net
 assert.equal(a.lead_position_base_pcs,'-7');assert.equal(a.lead_net.q_base_pcs,'47')
 v.targets[0].reorder_point_pcs='0';assert.equal((await project(v)).rows[0].net.base_reorder_state,'NO_POINT')
 const big='99999999999999999999999999999';v.budgets=[budget('large:M',big)];v.targets=[target('large:M',[supply('large:M',big,'large:M','DIRECTED')],'-7')]
 assert.equal((await project(v)).rows[0].net.lead_position_base_pcs,(BigInt(big)-7n).toString())
 return{negative_available_preserved:true,explicit_zero_point_preserved:true,large_integer_without_JS_rounding:true}
})
await test('OW10_SUPPLY_MISSING_HORIZON_NOT_AN_EMPTY_WIP_ZERO',async()=>{
 const v=fixture();v.budgets=[];v.targets=[target('unknown:M',[])];v.targets[0].lead_deadline=null;v.targets[0].deadline=null
 const r=await project(v);assert.equal(r.rows[0].net,null);assert.equal(r.rows[0].reason,'TARGET_HORIZON_UNKNOWN')
 v.budgets=[budget()];v.targets[0].supplies=[supply('unknown:M')];await assert.rejects(()=>project(v),/CP7_REORDER_TARGET_HORIZON_UNKNOWN_SUPPLY/)
 return{missing_time_not_guessed:true}
})
await test('OW10_SUPPLY_INDEPENDENT_INTEGER_ORACLE_64_GLOBAL_SCENARIOS',async()=>{
 const at=['2026-10-26T00:00:00Z','2026-10-29T00:00:00Z','2026-11-05T00:00:00Z']
 for(let i=0;i<64;i++){
  const shareA=BigInt((i*13)%81),shareB=BigInt((i*7)%Number(81n-shareA)),directed=BigInt(i%17)
  const eta=at[i%3],deta=at[(i+1)%3],v=fixture(),fg=[BigInt(i%23-7),BigInt(i%19-4)]
  v.budgets=[budget(undefined,'80',eta),budget('DIRECTED:M',directed.toString(),deta)]
  v.targets=[target('root-a:M',[supply('root-a:M',shareA.toString(),undefined,undefined,eta),supply('root-a:M',directed.toString(),'DIRECTED:M','DIRECTED',deta)],fg[0].toString()),
   target('root-b:M',[supply('root-b:M',shareB.toString(),undefined,undefined,eta)],fg[1].toString())]
  const r=await project(v);assert.equal(r.status,'SCENARIO')
  const shares=[shareA,shareB]
  for(let j=0;j<2;j++){
   const n=r.rows[j].net,d=j===0?directed:0n,leadDirected=deta<=v.targets[j].lead_deadline?d:0n,
    horizonDirected=deta<=v.targets[j].deadline?d:0n,leadCandidate=eta<=v.targets[j].lead_deadline?shares[j]:0n,
    horizonCandidate=eta<=v.targets[j].deadline?shares[j]:0n,base=fg[j]+leadDirected,conditional=base+leadCandidate,
    gap=100n-fg[j]-horizonDirected,baseGap=gap>0n?gap:0n,conditionalGap=baseGap>horizonCandidate?baseGap-horizonCandidate:0n
   assert.equal(n.lead_position_base_pcs,base.toString());assert.equal(n.lead_position_conditional_pcs,conditional.toString())
   assert.equal(n.q_base_pcs,baseGap.toString());assert.equal(n.q_conditional_pcs,conditionalGap.toString())
   assert.equal(n.base_reorder_state,base<=40n?'AT_OR_BELOW':'ABOVE');assert.equal(n.conditional_reorder_state,conditional<=40n?'AT_OR_BELOW':'ABOVE')
  }
  assert.ok(shareA+shareB<=80n)
 }
 return{controlled_scenarios:64,targets_per_scenario:2,independent_BigInt_quantities_gaps_states_and_conservation:true}
})
await test('OW10_SUPPLY_CLOSED_SHAPES_AND_BOUNDS',async()=>{
 const cases=[v=>{v.extra=true},v=>{v.budgets[0].raw_pcs='100'},v=>{v.targets[0].target_pcs=100},v=>{v.complete_scope=null},
  v=>{v.targets.push(structuredClone(v.targets[0]))},v=>{v.budgets.push(structuredClone(v.budgets[0]))},
  v=>{v.targets[0].supplies[0].kind='INCOMING'},v=>{v.query={...query,through_date:'2026-10-23'}},
  v=>{v.budgets[0].projected_good_pcs='-1'},v=>{v.checked_at='2026-10-22T00:00:00Z'},v=>{v.current_source_hash=null},
  v=>{v.targets[0].lead_deadline='2026-10-22T00:00:00Z'},
  v=>{v.targets=Array.from({length:5001},(_,i)=>target('t'+i,[]))},v=>{v.budgets=Array.from({length:1001},(_,i)=>budget('p'+i))},
  v=>{v.targets[0].supplies=Array.from({length:10001},()=>supply())}]
 for(const change of cases){const v=fixture();change(v);await assert.rejects(()=>project(v),/CP7_/)}
 return{invalid_shape_identity_quantity_and_bound_controls:cases.length}
})
await test('OW10_SUPPLY_PRIVATE_NO_PUBLIC_AUTHORITY',async()=>{
 for(const role of['anon','authenticated','service_role']){const r=(await db.query("select has_schema_privilege($1,'cp7_reorder_supply','USAGE')s,has_function_privilege($1,'cp7_reorder_supply.project(jsonb)','EXECUTE')f",[role])).rows[0];assert.deepEqual(r,{s:false,f:false})}
 const r=(await db.query("select pg_get_userbyid(proowner)owner,prosecdef,provolatile,proconfig from pg_proc where oid='cp7_reorder_supply.project(jsonb)'::regprocedure")).rows[0]
 assert.equal(r.owner,'cp7_capture');assert.equal(r.prosecdef,false);assert.equal(r.provolatile,'i');assert.deepEqual(r.proconfig,['search_path=""','TimeZone=UTC'])
 return{private_only:true,no_definer_privilege_or_business_writes:true}
})
const sql=await read('scripts/cp7_reorder_supply/projection.sql'),report={classification:'LOCAL_REAL_SQL_KERNEL_WITH_CONTROLLED_GLOBAL_ALLOCATION_INPUT_NOT_NATIVE_NOT_ROP_CALLER',
 status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',passed:results.filter(x=>x.status==='PASS').length,total:results.length,
 sql_sha256:createHash('sha256').update(sql).digest('hex'),results,live_ROP_caller_changed:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true});await writeFile('docs/cp7/d17-14/ow10/local-supply-projection.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
