import {expect,it} from 'vitest'
import {parseTargetDemand} from './nativeTargetDemand'
import {assertModelTargetBinding} from './nativeModelTarget'
import {parseNativeBaseline} from './nativePlanningProfile'
import {parseFgReorderWorkspace,type ReorderQuery} from './fgReorderContract'
import {reorderWire,type ReorderWireRow} from '../tests/fixtures/fgReorder'
import sql from '../tests/fixtures/nativeModelTargetV2Sql.json'
import legacy from '../tests/fixtures/nativeModelTargetSql.json'

const copy=<T,>(x:T):T=>structuredClone(x)
const parse=(value:unknown)=>parseTargetDemand(value,{targetKey:sql.rows.projected.target_key})

it.each(Object.entries(sql.rows))('reads actual versioned SQL %s with original observed operands',(_name,row)=>{
 const d=parse(row.demand_provenance)
 expect(d.ownTotalPcs).toBe('5050');expect(d.ownAvailableDays).toBe('100')
 expect(d.model?.state).toBe(row.model_resolution.state)
 if(row.model_resolution.runtime===null)expect(d.model?.reference).toBeNull()
 else{
  expect(d.model?.reference?.runtime).toBe(row.model_resolution.runtime)
  expect(d.model?.reference?.readMethod).toBe(row.model_resolution.read_method)
  expect(d.model?.reference?.historyScope).toBe(row.model_resolution.history_scope)
 }
 assertModelTargetBinding(row.target,row.model_resolution,d.model!)
})

it('keeps global and scoped identities explicit and retains legacy interpretation',()=>{
 const scoped=parse(sql.rows.projected.demand_provenance),global=parse(sql.rows.global.demand_provenance)
 expect(scoped.model?.reference?.runtime).toBe('SCOPED_V3')
 expect(global.model?.reference?.runtime).toBe('GLOBAL_V2')
 expect(scoped.targetPcs).toBe('400');expect(global.targetPcs).toBe('400')
 const old=parse(legacy.rows.projected.demand_provenance)
 expect(old.targetPcs).toBe('400');expect(old.model?.reference).toBeUndefined()
})

it.each(['provenanceVersion','resolutionVersion','runtime','method','scope','historyHash','physicalHash','engine','globalEngine','scopedEngine','historyEngine','consumerEngine','missingRuntime','extra','nullRun','future','vector','target','flag']as const)('refuses versioned %s contradiction',change=>{
 const p:Record<string,any>=copy(sql.rows.projected.demand_provenance),m=p.model
 if(change==='provenanceVersion')p.contract_version='cp7.target-demand-provenance.v2'
 if(change==='resolutionVersion')m.contract_version='cp7.model-target-resolution.v1'
 if(change==='runtime')m.runtime='GLOBAL_V2'
 if(change==='method')m.read_method='erp_cp7_read_model_evaluation_v2'
 if(change==='scope')m.history_scope='GLOBAL_CURRENT_PHYSICAL_ROOTS'
 if(change==='historyHash')m.history_source_hash='0'.repeat(64)
 if(change==='physicalHash')m.physical_source_hash='0'.repeat(64)
 if(change==='engine')m.engine_hash=m.global_engine_hash
 if(change==='globalEngine')m.global_engine_hash='0'.repeat(64)
 if(change==='scopedEngine')m.scoped_engine_hash='0'.repeat(32)
 if(change==='historyEngine')m.history_engine_hash='0'.repeat(32)
 if(change==='consumerEngine')m.consumer_engine_hash='0'.repeat(32)
 if(change==='missingRuntime')delete m.runtime
 if(change==='extra')m.accuracy_proven=true
 if(change==='nullRun')m.run_id=null
 if(change==='future')m.captured_at='2099-01-01T00:00:00Z'
 if(change==='vector')m.forecast.forecasts[0]='101'
 if(change==='target')p.target_pcs='401'
 if(change==='flag')m.forecast_applied=false
 expect(()=>parse(p)).toThrow()
})

it('does not permit a global run to claim the scoped history namespace',()=>{
 const p=copy(sql.rows.global.demand_provenance)
 p.model.history_scope='SINGLE_CURRENT_PHYSICAL_ROOT'
 expect(()=>parse(p)).toThrow()
})

const query={...sql.rows.projected.demand_provenance.query,group_mode:'AS_SOLD' as const}
const direct=()=>({...copy(sql.direct),run_id:'11111111-1111-4111-8111-111111111111',request_id:'22222222-2222-4222-8222-222222222222',source_state:'UNCHANGED'})
const rq:ReorderQuery={q:'',filter:'ALL',offset:0,limit:25}
it('accepts generated v4 direct baseline and refuses a namespace downgrade',()=>{
 const wire=direct(),r=parseNativeBaseline(wire,query)
 expect(r.rows[0].target).toBe('400');expect(r.rows[0].targetDemand?.model?.reference?.runtime).toBe('SCOPED_V3')
 wire.contract_version='cp7.native-baseline.v3'
 expect(()=>parseNativeBaseline(wire,query)).toThrow()
})
it.each(['reorderProjected','reorderDefaultsRows']as const)('reads generated v4 %s with exact historical totals',key=>{
 const w=reorderWire(copy(sql[key]) as ReorderWireRow[],rq,{contract_version:'cp7.fg-reorder.v2'})
 const row=parseFgReorderWorkspace(w,rq).page.rows[0]
 expect(row.salesPcs).toBe('5050');expect(row.countedDays).toBe(100)
 expect(row.projection?.targetDemand?.model?.reference?.runtime).toBe('SCOPED_V3')
 expect(row.formulaPoint).toBe(key==='reorderProjected'?'300':'169')
})
it('refuses a legacy projection label on a versioned model reference',()=>{
 const rows:Record<string,any>[]=copy(sql.reorderProjected)
 rows[0].projection.contract_version='cp7.fg-reorder-projection.v3'
 expect(()=>parseFgReorderWorkspace(reorderWire(rows as ReorderWireRow[],rq,{contract_version:'cp7.fg-reorder.v2'}),rq)).toThrow()
})
