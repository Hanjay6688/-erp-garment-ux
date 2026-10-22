// Actual private kernel SQL with actual existing validators; no Native proof.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite()
await db.exec('create role cp7_capture nologin;create role anon nologin;create role authenticated nologin;create role service_role nologin;')
for(const path of['wip/bootstrap.sql','demand/bootstrap.sql','wip/matching.sql','baseline/target.sql','baseline/allocation.sql'])await db.exec(await readFile('scripts/cp7-src/'+path,'utf8'))
for(const name of['cp7_baseline__target.sql','cp7_baseline__net.sql'])await db.exec(await readFile('scripts/cp7_production_stage/sql/'+name,'utf8'))
const before=execFileSync('git',['show','245b59505274ab7df6d15ed5d63080267da42988:scripts/cp7-src/baseline/target.sql'],{encoding:'utf8'})
await db.exec(before.slice(0,before.indexOf('-- Supply here')).replace('cp7_baseline.target(v','cp7_baseline.target_before(v'))
await db.exec(before.slice(before.indexOf('create function cp7_baseline.net(')).replace('cp7_baseline.net(v','cp7_baseline.net_before(v'))
const results=[]
const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,2200)})}}
const call=async(v,fn='target')=>(await db.query('select cp7_baseline.'+fn+'($1::jsonb) value',[JSON.stringify(v)])).rows[0].value
const base={contract_version:'cp7.target-input.v1',snapshot_id:'same-snapshot',scope_id:'same-scope',mode:'DAYS',daily_mean:'1',lead_days:'3',review_days:'7',buffer_days:'2',quantile:null,horizon_samples:[],refs:[{kind:'LOCAL_TEST',id:'source',revision:'1'}]}
await test('OW10_LEGACY_DAYS_EXACT_EQUIVALENCE',async()=>{
 let count=0
 for(const daily of['0','0.1','1','7.666666666667','1000000000000'])for(const lead of['0','0.5','3','7.25'])for(const review of['1','7'])for(const buffer of['0','0.1','2']){
  const v={...base,daily_mean:daily,lead_days:lead,review_days:review,buffer_days:buffer}
  assert.deepEqual(await call(v),await call(v,'target_before'));++count
 }
 for(const v of[{...base,lead_days:null},{...base,buffer_days:null},{...base,daily_mean:null},{...base,daily_mean:'invalid',buffer_days:null}]){
  assert.deepEqual(await call(v),await call(v,'target_before'));++count
 }
 // The old contract keeps its rejection of a zero horizon; only v2 permits it.
 for(const fn of['target','target_before'])await assert.rejects(()=>call({...base,lead_days:'0',review_days:'0'},fn),/CP7_BASELINE_HORIZON/)
 return {identical_full_JSON:count}
})
await test('OW10_LEGACY_EMPIRICAL_EXACT_EQUIVALENCE',async()=>{
 for(const quantile of['0.5','0.90','0.95','0.99','1']){
  const v={...base,mode:'STATISTICAL',daily_mean:null,buffer_days:null,quantile,horizon_samples:['1','30','4','100','20']}
  assert.deepEqual(await call(v),await call(v,'target_before'))
 }
 return {identical_full_JSON:5}
})
await test('OW10_INDEPENDENT_RATIONAL_AND_DECIMAL_ORACLE',async()=>{
 const rows=JSON.parse(execFileSync('python',['scripts/cp7_ow10_target_oracle.py'],{encoding:'utf8'}))
 for(const {input,expected}of rows){const got=await call(input);assert.equal(got.status,'SCENARIO');assert.equal(got.reorder_point_pcs,expected.reorder_point_pcs,JSON.stringify(input));assert.equal(got.target_pcs,expected.target_pcs,JSON.stringify(input))}
 return{independent_cases:rows.length,exact_repeating_mean_whole_PCS:true,separate_reorder_and_target:true}
})
await test('OW10_UNKNOWN_AND_DOUBLE_SAFETY_REFUSAL',async()=>{
 const v=JSON.parse(execFileSync('python',['scripts/cp7_ow10_target_oracle.py'],{encoding:'utf8'}))[1].input
 for(const delta of[{daily_sd:null},{service_level:null},{counted_days:'13'},{lead_days:null}]){
  const got=await call({...v,...delta});assert.equal(got.status,'UNKNOWN');assert.equal(got.reorder_point_pcs,null);assert.equal(got.target_pcs,null)
 }
 for(const delta of[{buffer_days:'2'},{service_level:'0.96'},{daily_sd:'NaN'},{extra:'smuggle'}])await assert.rejects(()=>call({...v,...delta}))
 return{unknown_not_zero:4,invalid_or_double_buffer_refused:4}
})
await test('OW10_ONE_GLOBAL_ALLOCATION_TWO_VARIANTS_TWO_HORIZONS',async()=>{
 const ref=id=>[{kind:'SYNTHETIC_TEST_ONLY',id,revision:'1'}],snapshot='allocation-snapshot',size='M'
 const when=day=>`2026-10-${String(day).padStart(2,'0')}T00:00:00Z`,constraints=[{field:'brand',value:'A',required:true,basis:'FACT'},{field:'color',value:'BLUE',required:true,basis:'FACT'}]
 const targets=['SKU-A','SKU-B'].map((key,i)=>({key,size_id:size,need_pcs:'15',deadline:when(12),risk_at:when(3+i),helps_at:when(2),production_status:'ACTIVE',refs:ref(key)}))
 const input={contract_version:'cp7.allocation-input.v1',snapshot_id:snapshot,scope_id:'whole-factory',scenario_id:'same-scenario',complete_scope:true,
  positions:{contract_version:'cp7.wip-position.v1',snapshot_id:snapshot,status:'COMPLETE',allocation_review_required:false,
   positions:[{key:'physical-cut',pool_key:'only-pool',size_id:size,remaining_pcs:'20',eligible_company_wip:true,refs:ref('physical-cut'),projection:{quality:'SCENARIO',numerator:'1',denominator:'1',eligible_input_pcs:'20',projected_good_pcs:'20'}}],
   totals:[{pool_key:'only-pool',wip_pcs:'20'}]},
  matching:{snapshot_id:snapshot,sources:[{key:'physical-cut',quality:'COMPLETE',size_id:size,confirmed_target:null,constraints,refs:ref('physical-cut')}],
   targets:targets.map(t=>({key:t.key,size_id:size,constraints,refs:t.refs}))},
  etas:[{position_key:'physical-cut',at:when(3),refs:ref('eta')}],targets,capacity_pcs:'20',refs:ref('capacity')}
 const allocated=await call(input,'allocate')
 assert.equal(allocated.status,'SCENARIO');assert.equal(allocated.allocation.status,'FEASIBLE')
 assert.deepEqual(allocated.rows.map(r=>[r.target_key,r.allocated_good_pcs,r.unresolved_pcs]),[['SKU-A','15','0'],['SKU-B','5','10']])
 const edges=allocated.allocation.edges;assert.equal(edges.reduce((n,e)=>n+BigInt(e.input_pcs),0n),20n)
 const make=(key,eta)=>({contract_version:'cp7.net-input.v2',snapshot_id:snapshot,scope_id:'whole-factory',scenario_id:'same-scenario',target_key:key,size_id:size,
  deadline:when(12),lead_deadline:when(2),target_pcs:'20',reorder_point_pcs:'10',available_fg_pcs:'5',
  supplies:edges.filter(e=>e.target_key===key).map(e=>({physical_key:e.position_key,snapshot_id:snapshot,target_key:key,size_id:size,kind:'ALLOCATED_CANDIDATE',qty_pcs:e.projected_good_pcs,eta,eligible:true,refs:e.refs})),refs:ref(key)})
 const late=await Promise.all(targets.map(t=>call(make(t.key,when(3)),'net')))
 assert.deepEqual(late.map(n=>[n.q_conditional_pcs,n.lead_position_conditional_pcs,n.conditional_reorder_state]),[['0','5','AT_OR_BELOW'],['10','5','AT_OR_BELOW']])
 const early=await Promise.all(targets.map(t=>call(make(t.key,when(2)),'net')))
 assert.deepEqual(early.map(n=>[n.lead_position_conditional_pcs,n.conditional_reorder_state]),[['20','ABOVE'],['10','AT_OR_BELOW']])
 for(const supplies of[[],make('SKU-A',when(2)).supplies,make('SKU-A',when(3)).supplies,make('SKU-A',null).supplies])for(const fg of['-5','0','5']){
  const v={...make('SKU-A',when(2)),contract_version:'cp7.net-input.v1',available_fg_pcs:fg,supplies}
  delete v.reorder_point_pcs;delete v.lead_deadline
  assert.deepEqual(await call(v,'net'),await call(v,'net_before'))
 }
 // Identical physical/size key replay is idempotent. Changed quantity refuses.
 const duplicate=make('SKU-A',when(2));duplicate.supplies.push(structuredClone(duplicate.supplies[0]))
 assert.deepEqual(await call(duplicate,'net'),{...early[0],inputs:duplicate,lead_net:{...early[0].lead_net,inputs:{...early[0].lead_net.inputs,supplies:duplicate.supplies}}})
 duplicate.supplies[1].qty_pcs='16';await assert.rejects(()=>call(duplicate,'net'),/CP7_BASELINE_PHYSICAL_SOURCE_CONFLICT/)
 const unknown=await call(make('SKU-A',null),'net');assert.equal(unknown.status,'UNKNOWN');assert.equal(unknown.lead_position_base_pcs,null);assert.equal(unknown.base_reorder_state,'UNKNOWN')
 await assert.rejects(()=>call({...make('SKU-A',when(2)),lead_deadline:when(13)},'net'),/CP7_BASELINE_LEAD_AFTER_HORIZON/)
 await assert.rejects(()=>call({...make('SKU-A',when(2)),reorder_point_pcs:'21'},'net'),/CP7_BASELINE_POINT_ABOVE_TARGET/)
 // A confirmed destination never transfers unused WIP to the other variant.
 input.matching.sources[0].confirmed_target='SKU-A'
 const confirmed=await call(input,'allocate');assert.deepEqual(confirmed.rows.map(r=>r.allocated_good_pcs),['15','0'])
 return{physical_pool_pcs:'20',global_candidate_allocation:{'SKU-A':'15','SKU-B':'5'},late_supply_does_not_cover_lead:true,
  at_lead_boundary_included:true,equality_still_at_point:true,confirmed_other_variant_excluded:true,unknown_not_safe:true,identical_replay_not_double_counted:true,legacy_net_identical_full_JSON:12}
})
const report={classification:'LOCAL_ACTUAL_KERNEL_SQL_NOT_NATIVE_OR_HTTP',status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',
 source_sha256:createHash('sha256').update(await readFile('scripts/cp7_production_stage/sql/cp7_baseline__target.sql')).update(await readFile('scripts/cp7_production_stage/sql/cp7_baseline__net.sql')).digest('hex'),source_layout:'FROZEN_PREDECESSOR_PLUS_COUNTED_PRODUCTION_STAGE',cases:results,OW10_complete:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true});await writeFile('docs/cp7/d17-14/ow10/local-kernel.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
