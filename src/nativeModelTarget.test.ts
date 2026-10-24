import {expect,it} from 'vitest'
import {parseTargetDemand} from './nativeTargetDemand'
import {assertModelTargetBinding} from './nativeModelTarget'
import {parseNativeBaseline} from './nativePlanningProfile'
import {parseFgReorderWorkspace,type ReorderQuery} from './fgReorderContract'
import {reorderWire,type ReorderWireRow} from '../tests/fixtures/fgReorder'
import sql from '../tests/fixtures/nativeModelTargetSql.json'

const copy=<T,>(x:T):T=>structuredClone(x)
const parse=(p:unknown)=>parseTargetDemand(p,{targetKey:sql.rows.projected.target_key})
const direct=()=>({...copy(sql.direct),run_id:'11111111-1111-4111-8111-111111111111',request_id:'22222222-2222-4222-8222-222222222222',source_state:'UNCHANGED'})
const query={...sql.rows.projected.demand_provenance.query,group_mode:'AS_SOLD' as const}
const rq:ReorderQuery={q:'',filter:'ALL',offset:0,limit:25}
const workspace=(rows:unknown[])=>reorderWire(rows as ReorderWireRow[],rq,{contract_version:'cp7.fg-reorder.v2'})
it.each(['reorderProjected','reorderDefaultsRows']as const)('reads actual generated %s SQL and preserves historical demand',key=>{
 const r=parseFgReorderWorkspace(workspace(sql[key]),rq).page.rows[0]
 expect(r.salesPcs).toBe('5050');expect(r.countedDays).toBe(100)
 expect(r.projection?.targetDemand?.model?.state).toBe(key==='reorderProjected'?'MODEL_PROJECTED':'BASELINE_RETAINED')
 expect(r.formulaPoint).toBe(key==='reorderProjected'?'300':'169')
})
it.each(['downgrade','point','days','safety','buffer','lead']as const)('refuses generated model reorder %s mismatch',key=>{
 const rows:Record<string,any>[]=copy(sql.reorderProjected),r=rows[0]
 if(key==='downgrade')r.projection.contract_version='cp7.fg-reorder-projection.v2'
 if(key==='point')r.formula_point='299'
 if(key==='days')r.counted_days=99
 if(key==='safety')r.safety_pcs='101'
 if(key==='buffer')r.buffer_days='2'
 if(key==='lead')r.lead_days='3'
 expect(()=>parseFgReorderWorkspace(workspace(rows),rq)).toThrow()
})
it('accepts generated v3 direct baseline wire with explicit controlled history producer',()=>{
 const r=parseNativeBaseline(direct(),query)
 expect(r.rows[0].target).toBe('400');expect(r.rows[0].daily).toBe('50.500000000000');expect(r.rows[0].targetDemand?.model?.state).toBe('MODEL_PROJECTED')
 expect(r.rows[1].targetDemand?.model?.reason).toBe('NO_OWN_MODEL_EVALUATION')
})
it.each(['downgrade','missing','target','history','resolution','profile','modelBasis']as const)('refuses v3 direct baseline %s mismatch',key=>{
 const v:Record<string,any>=direct(),r=v.rows[0]
 if(key==='downgrade'){v.contract_version='cp7.native-baseline.v2';v.model_basis='BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN'}
 if(key==='missing')delete r.demand_provenance
 if(key==='target')r.target.target_pcs='401'
 if(key==='history')r.demand_provenance.own_total_pcs='5000'
 if(key==='resolution')r.model_resolution.source_hash='a'.repeat(64)
 if(key==='profile')r.profile.config.lead_days='3'
 if(key==='modelBasis')v.model_basis='BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN'
 expect(()=>parseNativeBaseline(v,query)).toThrow()
})
it.each(Object.entries(sql.rows))('reads actual private SQL %s with unchanged observed operands',(name,row)=>{
 const d=parse(row.demand_provenance)
 expect(d.ownTotalPcs).toBe('5050');expect(d.ownAvailableDays).toBe('100')
 expect(d.model?.state).toBe(row.model_resolution.state)
 assertModelTargetBinding(row.target,row.model_resolution,d.model!)
 if(name==='projected'){expect(d.targetPcs).toBe('400');expect(d.model?.baselineTarget).toBe('202');expect(d.reorderPointPcs).toBe('300')}
})
it.each(['downgrade','missing','extra','flag','go','target','point','history','query','date','future','hash','engine','method','params','registry','policy','allowed','training','numberTraining','horizon','negative','numberVector','short','unknown','baseline','baselineInputs']as const)('refuses contradictory model %s',key=>{
 const p:Record<string,any>=copy(sql.rows.projected.demand_provenance),m=p.model
 if(key==='downgrade')p.contract_version='cp7.target-demand-provenance.v1'
 if(key==='missing')delete m.forecast
 if(key==='extra')m.accuracy_proven=true
 if(key==='flag')m.forecast_applied=false
 if(key==='go')m.production_go=true
 if(key==='target')p.target_pcs='401'
 if(key==='point')p.reorder_point_pcs='301'
 if(key==='history')m.history_run_id=null
 if(key==='query')m.history_query.group_mode='RESTATED'
 if(key==='date')m.forecast_from_date='2025-01-01'
 if(key==='future')m.captured_at='2099-01-01T00:00:00Z'
 if(key==='hash')m.source_hash='a'.repeat(32)
 if(key==='engine')m.engine_hash='a'.repeat(64)
 if(key==='method')m.selected_model.method='MEAN'
 if(key==='params')m.forecast.params={alpha:'0.9'}
 if(key==='registry')m.selected_model.registered_at=m.captured_at
 if(key==='policy')m.policy_source.policy.state='SUSPENDED'
 if(key==='allowed')m.policy_source.policy.config.allowed_methods=[]
 if(key==='training')m.forecast.training_count=1
 if(key==='numberTraining')m.forecast.training_count='100'
 if(key==='horizon')m.policy_source.policy.config.maximum_horizon_days='2'
 if(key==='negative')m.forecast.forecasts[0]='-1'
 if(key==='numberVector')m.forecast.forecasts[0]=100
 if(key==='short')m.forecast.forecasts=m.forecast.forecasts.slice(0,3)
 if(key==='unknown')m.baseline_target.status='UNKNOWN'
 if(key==='baseline')m.baseline_target.target_pcs='203'
 if(key==='baselineInputs')m.baseline_target.inputs.daily_total_pcs='400'
 expect(()=>parse(p)).toThrow()
})
it.each(['inputs','kernel','lead','review','safety','model','interval','doubleBuffer','extra']as const)('binds actual target %s to validated provenance',key=>{
 const r:Record<string,any>=copy(sql.rows.projected),m=parse(r.demand_provenance).model!
 if(key==='inputs')r.target.inputs.daily_total_pcs='400'
 if(key==='kernel')r.target.kernel_version='target-unified-2'
 if(key==='lead')r.target.lead_demand_pcs='201'
 if(key==='review')r.target.review_demand_pcs='101'
 if(key==='safety')r.target.horizon_safety_pcs='101'
 if(key==='model')r.model_resolution.run_id='11111111-1111-4111-8111-111111111111'
 if(key==='interval')r.target.calibrated_forecast_interval=true
 if(key==='doubleBuffer')r.target.buffer_basis='STATISTICAL_PLUS_DAYS'
 if(key==='extra')r.target.auto_save=true
 expect(()=>assertModelTargetBinding(r.target,r.model_resolution,m)).toThrow()
})
it('retains UNKNOWN and refuses a baseline result pretending to apply a vector',()=>{
 expect(parse(sql.rows.unknown.demand_provenance).targetPcs).toBeNull()
 const p=copy(sql.rows.manual.demand_provenance);Object.assign(p.model,{forecast:sql.rows.projected.model_resolution.forecast})
 expect(()=>parse(p)).toThrow()
})
it('retains the original unreviewed-profile reorder default and its matching explanation',()=>{
 const r=parse(sql.reorderDefaults.demand_provenance)
 expect(r.targetPcs).toBe('169');expect(r.model?.state).toBe('BASELINE_RETAINED')
 expect(r.model?.reason).toBe('EXISTING_REORDER_DEFAULTS_RETAINED_UNREVIEWED_PROFILE')
 expect(r.model?.baselineTarget).toBe('169')
})
it('keeps dated fractional windows and PCS beyond safe integers exact (synthetic wire mutation)',()=>{
 const p:Record<string,any>=copy(sql.rows.projected.demand_provenance),m=p.model,b=m.baseline_target
 Object.assign(b.inputs,{lead_days:'0.5',review_days:'0.5',buffer_days:'1'})
 Object.assign(b,{horizon_days:'1',lead_demand_pcs:'25.25',review_demand_pcs:'25.25',lead_safety_pcs:'50.5',horizon_safety_pcs:'50.5',reorder_point_pcs:'76',target_pcs:'101'})
 m.forecast.forecasts=['9007199254740993.1','3.2','0','0','0','0','0']
 p.reorder_point_pcs='9007199254740995';p.target_pcs='9007199254740997'
 const r=parse(p);expect(r.targetPcs).toBe('9007199254740997');expect(r.model?.expectedTarget.lead_demand_pcs).toBe('4503599627370496.55')
})
