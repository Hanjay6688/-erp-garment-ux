import {it,expect} from 'vitest'
import {parseTargetDemand} from './nativeTargetDemand'
import {parseAnalogCandidates} from './nativeProductAnalog'
import {parseFgReorderWorkspace,type ReorderQuery} from './fgReorderContract'
import sql from '../tests/fixtures/nativeTargetDemandSql.json'
import {analogContext,analogReply} from '../tests/fixtures/nativeProductAnalog'
import {reorderWire,type ReorderWireRow} from '../tests/fixtures/fgReorder'

const copy=<T,>(v:T):T=>structuredClone(v)
const bind={targetKey:sql.analog.target_key,capturedAt:sql.analog.captured_at,query:sql.analog.query as {from_date:string;through_date:string;group_mode:'AS_SOLD'}}
it.each(['analog','huge','cleared','changed','manual','own']as const)('parses actual SQL %s provenance without inventing own sales',key=>{
 const p=sql[key],r=parseTargetDemand(p,bind)
 expect(r.ownTotalPcs).toBe(p.own_total_pcs);expect(r.targetPcs).toBe(p.target_pcs)
})
it('keeps the fractional numerator beyond JS safe integers exact',()=>{
 const r=parseTargetDemand(sql.huge,bind)
 expect(r.analog?.scaledTotalPcs).toBe('4503599627370496.5');expect(r.targetPcs).toBe('4503599627370497')
})
it.each(['target','size','clock','query','future','revision','scale','source','foreignSize','numerator','denominator','state','basis','missing','extra','ownSales','fractionalOwn','nullAnalog','number','negative','futureClock','invalidDay']as const)('refuses contradictory %s provenance',key=>{
 const r:Record<string,any>=copy(sql.analog)
 if(key==='target')r.target_key=r.analog.source_key
 if(key==='size')r.size_id=r.analog.choice_id
 if(key==='clock')r.captured_at=r.captured_at.replace('123456','123457')
 if(key==='query')r.query.group_mode='RESTATED'
 if(key==='future')r.analog.recorded_at=r.captured_at.replace('123456','123457')
 if(key==='revision')r.analog.choice_revision='0'
 if(key==='scale')r.analog.scale_factor='0'
 if(key==='source')r.analog.source_key=r.target_key
 if(key==='foreignSize')r.analog.source_key=r.analog.source_key.split(':')[0]+':'+r.analog.choice_id
 if(key==='numerator')r.analog.scaled_total_pcs='2'
 if(key==='denominator')r.analog.available_days='2'
 if(key==='state')r.analog.state='UNAVAILABLE'
 if(key==='basis')r.basis='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'
 if(key==='missing')delete r.daily_total_pcs
 if(key==='extra')r.promoted=true
 if(key==='ownSales')r.own_total_pcs='1'
 if(key==='fractionalOwn')r.own_total_pcs='0.5'
 if(key==='nullAnalog')r.analog=null
 if(key==='number')r.daily_total_pcs=1
 if(key==='negative')r.daily_total_pcs='-1'
 if(key==='futureClock')r.query.through_date='2026-01-20'
 if(key==='invalidDay')r.captured_at='2026-02-30T12:00:00Z'
 expect(()=>parseTargetDemand(r,bind)).toThrow()
})
it('binds v2 advisory pagination to the same captured demand and refuses downgrade',()=>{
 const c={...analogContext(),targetKey:bind.targetKey,query:bind.query,reference:{...analogContext().reference,capturedAt:bind.capturedAt}}
 const v={...analogReply(c),contract_version:'cp7.product-analog-candidates-read.v2',consumer_capability:'REVIEWED_ANALOG_FOR_FRESH_CAPTURES',target_demand:copy(sql.analog)}
 const parsed=parseAnalogCandidates(v,c,0);expect(parsed.supportsConsumer).toBe(true);expect(parsed.targetDemand?.targetPcs).toBe('1')
 expect(()=>parseAnalogCandidates({...v,contract_version:'cp7.product-analog-candidates-read.v1'},c,0)).toThrow()
 expect(()=>parseAnalogCandidates({...v,target_demand:null},c,0)).toThrow()
 const changed=copy(v);changed.target_demand.analog.review_reason='Other reason'
 expect(()=>parseAnalogCandidates(changed,c,0,parsed)).toThrow()
})
const query:ReorderQuery={q:'',filter:'ALL',offset:0,limit:25}
const workspace=(rows:unknown[])=>reorderWire(rows as ReorderWireRow[],query,{contract_version:'cp7.fg-reorder.v2'})
it('parses both actual SQL v2 reorder projections and preserves own history',()=>{
 const r=parseFgReorderWorkspace(workspace(sql.reorder),query).page.rows[0]
 expect(r.salesPcs).toBe('0');expect(r.countedDays).toBe(0);expect(r.dailyMean).not.toBe('0')
 expect(r.projection?.targetDemand?.analog?.availableDays).toBe('14')
})
it.each(['ownSales','ownDays','point','target','sd','clock','downgrade','missing']as const)('refuses reorder %s mismatch against actual provenance',key=>{
 const r:Record<string,any>=copy(sql.reorder[0])
 if(key==='ownSales')r.sales_pcs='1'
 if(key==='ownDays')r.counted_days=1
 if(key==='point')r.formula_point='2'
 if(key==='target')r.projection.target_pcs='2'
 if(key==='sd')r.daily_sd='9'
 if(key==='clock')r.projection.threshold_checked_at=r.changed_at.replace('123456','123457')
 if(key==='downgrade')r.projection.contract_version='cp7.fg-reorder-projection.v1'
 if(key==='missing')delete r.projection.target_demand
 expect(()=>parseFgReorderWorkspace(workspace([r]),query)).toThrow()
})
