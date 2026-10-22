// @vitest-environment jsdom
import {beforeEach,expect,it} from 'vitest'
import {parsePlanningConfig,parseNativeBaseline,persistPlanningRequest,readPlanningRequest,planningPayload,parsePlanningProfile} from './nativePlanningProfile'
import {baselineWire,planningConfig,profileWire} from '../tests/fixtures/nativePlanningProfile'
import {demandRoot,demandSize} from '../tests/fixtures/nativeDemandHistory'
import fixture from '../tests/fixtures/targetStatisticalAdapter.json'
import {parseFgReorderWorkspace,reorderFormulaLines,reorderReasonText,type ReorderRow} from './fgReorderContract'
import minimumRow from '../tests/fixtures/fgStatisticalMinimum.json'
import {reorderWire,type ReorderWireRow} from '../tests/fixtures/fgReorder'
const config={...planningConfig,mean_mode:'OWN_AVAILABLE_HISTORY' as const,daily_pcs:null,buffer_days:null,buffer_mode:'STATISTICAL' as const,service_level:'0.95' as const}
beforeEach(()=>localStorage.clear())
it('reads the actual ROP SQL row when a stricter profile minimum is not met, without saying fourteen days are missing',()=>{
 const q={q:'',filter:'ALL' as const,offset:0,limit:25}
 const row=parseFgReorderWorkspace(reorderWire([minimumRow as ReorderWireRow],q),q).page.rows[0]
 expect(row.point).toBeNull();expect(row.countedDays).toBe(14);expect(row.reason).toBe('PROFILE_MINIMUM_NOT_MET')
 expect(reorderReasonText(row)).toContain('minimal hari di profil');expect(reorderReasonText(row)).not.toContain('perlu 14')
})
it('labels the effective per-product service from the same server z instead of the different general setting',()=>{
 const row={leadDays:'3',leadBasis:'PROFILE',bufferMode:'STATISTICAL',bufferDays:null,dailyMean:'5',dailySd:'5.1887',countedDays:14,saleDays:7,salesPcs:'70',safetyPcs:'14.782',formulaPoint:30,z:'1.6449'}as ReorderRow
 expect(reorderFormulaLines(row,14,'0.90').join(' ')).toContain('tingkat layanan 95%')
 expect(reorderFormulaLines(row,14,'0.90').join(' ')).not.toContain('tingkat layanan 90%')
})
it('keeps legacy config bytes and an explicitly selected statistical policy through lost-reply storage',()=>{
 expect(parsePlanningConfig(planningConfig)).toEqual(planningConfig)
 const p=parsePlanningProfile(profileWire(false),demandRoot,demandSize),request={id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',payload:planningPayload(p,config,'Pilihan cadangan diperiksa')}
 persistPlanningRequest('local-stat',request);expect(readPlanningRequest('local-stat').pending).toEqual(request)
 expect(request.payload.config.buffer_days).toBeNull()
})
it.each([{...config,buffer_days:'1'},{...config,service_level:'0.97'},{...config,buffer_mode:'OTHER'}, {...config,mean_mode:'SELECTED_MANUAL',daily_pcs:'5'}, {...planningConfig,buffer_mode:'DAYS'}, {...planningConfig,buffer_mode:'DAYS',service_level:'0.95'},{...planningConfig,buffer_mode:'DAYS',service_level:null,buffer_days:null}])('rejects a double, partial or unproved statistical policy %j',v=>expect(()=>parsePlanningConfig(v)).toThrow())
function wire(){
 const w=baselineWire()as any,h=w.history_run_result,hr=h.history.rows[0],r=w.rows[0]
 w.contract_version='cp7.native-baseline.v2';w.target_basis='UNIFIED_TARGET_WITH_SELECTED_PROFILE_ASSUMPTIONS'
 const captured=new Date(Date.parse(fixture.query.through_date+'T00:00:00Z')+86400000+12*3600000).toISOString().replace('.000Z','.000001Z')
 w.captured_at=h.captured_at=h.training_known_at=h.history.known_as_of=h.history.effective_as_of=captured
 Object.assign(h.history,{from_date:fixture.query.from_date,through_date:fixture.query.through_date})
 Object.assign(hr,{gross_observed_pcs:'70',available_days:14,unknown_days:0,stockout_days:0,available_sales_mean:'5',days:fixture.days})
 r.profile.config={...config,minimum_available_days:'1'}
 Object.assign(r.demand_estimate,{basis:'OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE',daily_pcs:'5'})
 Object.assign(r.demand_estimate.inputs,{minimum_own_available_days:'1',own:{available_total_pcs:'70',available_days:'14',capture_complete:true,refs:r.refs},manual:null})
 r.target=structuredClone(fixture.target);r.target.inputs.snapshot_id=w.source_hash;r.target.inputs.refs=r.refs
 return w
}
it('reads the actual SQL statistical target while keeping the old v1 baseline parser',()=>{
 const w=wire(),r=parseNativeBaseline(w,fixture.query as {from_date:string;through_date:string;group_mode:'AS_SOLD'}).rows[0]
 expect(r).toMatchObject({reorderPoint:'30',target:'77',statisticalServiceLevel:'0.95',statisticalDays:14})
 expect(parseNativeBaseline(baselineWire(),{from_date:'2026-09-29',through_date:'2026-09-29',group_mode:'AS_SOLD'}).rows[0]).not.toHaveProperty('statisticalServiceLevel')
})
it.each(['level','double','version','mode'])('rejects a mismatched statistical result: %s',kind=>{
 const w=wire();if(kind==='level')w.rows[0].target.inputs.service_level='0.99'
 if(kind==='double')w.rows[0].target.inputs.buffer_days='1'
 if(kind==='version')w.contract_version='cp7.native-baseline.v1'
 if(kind==='mode')w.rows[0].target.inputs.mode='DAYS'
 expect(()=>parseNativeBaseline(w,fixture.query as {from_date:string;through_date:string;group_mode:'AS_SOLD'})).toThrow()
})
