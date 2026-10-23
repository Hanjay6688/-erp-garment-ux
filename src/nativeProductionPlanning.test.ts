// @vitest-environment jsdom
import {beforeEach,it,expect,vi} from 'vitest'
import {parseNativeSupply,parseScheduleWorkspace,parseNativeNetting,schedulePayload,checkScheduleOutcome,persistScheduleRequest,readScheduleRequest,clearScheduleRequest,scheduleRequestKey,instantToWibInput,wibInputToInstant} from './nativeProductionPlanning'
import {supplyWire,workspaceWire,stagedWorkspaceWire,stagedScheduleOutcome,scheduleJobWire,nettingWire,dualHorizonNettingWire,scheduleConfig,scheduleOutcome,planningQuery,workKey} from '../tests/fixtures/nativeProductionPlanning'
import {parseStagedScheduleWorkspace,STAGED_SCHEDULE_CONTRACT} from './nativeProductionPlanning'
import {readStagedSchedule,saveStagedSchedule} from './nativeStagedSchedule'
import {demandRequest} from '../tests/fixtures/nativeDemandHistory'
beforeEach(()=>localStorage.clear())
it('retains the lead trigger separately when later supply reduces the target quantity',()=>{
 const n=parseNativeNetting(dualHorizonNettingWire(),planningQuery)
 expect(n.rows[0]).toMatchObject({reorderPoint:'80',target:'100',directed:'7',baseGap:'17',timing:{basePosition:'76',baseState:'AT_OR_BELOW',conditionalPosition:'76',conditionalState:'AT_OR_BELOW',deadline:'2026-10-08T12:00:00.000001Z'}})
 expect(parseNativeNetting(nettingWire(),planningQuery).rows[0].timing).toBeNull()
})
it.each(['point','snapshot','deadline','available','different-supplies','unknown-with-position','partial-position','version'])('refuses misbound lead timing: %s',kind=>{
 const value=dualHorizonNettingWire(),n=value.rows[0].net
 if(kind==='point')n.inputs.reorder_point_pcs='79'
 if(kind==='snapshot')n.lead_net.inputs.snapshot_id='other'
 if(kind==='deadline')n.lead_net.inputs.deadline='2026-10-09T12:00:00Z'
 if(kind==='available')n.lead_net.inputs.available_fg_pcs='77'
 if(kind==='different-supplies')n.lead_net.inputs.supplies=[]
 if(kind==='unknown-with-position')n.lead_net.status='UNKNOWN'
 if(kind==='partial-position')Object.assign(n,{lead_position_conditional_pcs:null})
 if(kind==='version')n.inputs.contract_version='cp7.net-input.v3'
 expect(()=>parseNativeNetting(value,planningQuery)).toThrow()
})
it('does not show a conditional trigger while the global allocation remains unknown',()=>{
 const v=dualHorizonNettingWire();v.allocation.status='UNKNOWN';Object.assign(v.rows[0],{conditional_gap_pcs:null,candidate_allocated_good_pcs:null})
 expect(parseNativeNetting(v,planningQuery).rows[0].timing).toMatchObject({baseState:'AT_OR_BELOW',basePosition:'76',conditionalState:'UNKNOWN',conditionalPosition:null})
})
it('retains physical quantities, customer work, selected good, signed shortage and capacity as separate server values',()=>{const s=parseNativeSupply(supplyWire(),planningQuery),w=parseScheduleWorkspace(workspaceWire(),s),n=parseNativeNetting(nettingWire(),planningQuery);expect(s.positions.map(x=>[x.remaining,x.eligible])).toEqual([['8',true],['8',false]]);expect(w.requirements[1].targets).toEqual([]);expect(n.rows[0]).toMatchObject({available:'76',rawGap:'24',directed:'7',baseGap:'17',conditionalGap:'17'});expect(n.capacity).toBe('15');expect(n.positions).toHaveLength(2)})
it('preserves unknown yield, shared time and global allocation as unknown values',()=>{const n=parseNativeNetting(nettingWire(demandRequest,true),planningQuery);expect(n.rows[0].baseGap).toBeNull();expect(n.rows[0].directed).toBeNull();expect(n.rows[0].conditionalGap).toBeNull();expect(n.capacity).toBeNull();expect(n.etas.every(x=>x.at===null)).toBe(true)})
it('reads the PL-8 v2 supply contract and runs archived as v1, never another version',()=>{const v1=supplyWire();v1.contract_version='cp7.native-supply.v1';expect(parseNativeSupply(v1,planningQuery).positions).toHaveLength(2);const v3=supplyWire();v3.contract_version='cp7.native-supply.v3';expect(()=>parseNativeSupply(v3,planningQuery)).toThrow()})
it('accepts the native timing kernel UTC offset serialization while keeping selected metadata UTC-Z only',()=>{const n=nettingWire();n.schedule_run_result.etas[0].result.eta='2026-10-01T01:45:00.123456+00:00';expect(parseNativeNetting(n,planningQuery).etas[0].at).toBe('2026-10-01T01:45:00.123456+00:00');const s=parseNativeSupply(supplyWire(),planningQuery),w=parseScheduleWorkspace(workspaceWire(),s),c=structuredClone(scheduleConfig);c.through_at='2026-10-02T12:00:00.123456+00:00';expect(()=>schedulePayload(w,c,'explicit')).toThrow()})
it.each(['run','hash','qty','ownership','candidate','version'])('refuses misbound schedule guidance: %s',kind=>{const s=parseNativeSupply(supplyWire(),planningQuery),w=workspaceWire();if(kind==='run')w.source_run=demandRequest;if(kind==='hash')w.source_hash='a'.repeat(64);if(kind==='qty')w.position_requirements[0].remaining_pcs='9';if(kind==='ownership')w.position_requirements[1].eligible_company_wip=true;if(kind==='candidate')w.position_requirements[0].target_candidates[0].target_key='wrong';if(kind==='version'){w.revision='1'}expect(()=>parseScheduleWorkspace(w,s)).toThrow()})
it.each(['query','target','available','net','conditional','apply','duplicate','customer','eta'])('refuses inconsistent netting receiver: %s',kind=>{const w=nettingWire();if(kind==='query')w.schedule_run_result.supply_run_result.baseline_run_result.history_run_result.history.from_date='2026-09-28';if(kind==='target')w.rows[0].target_key='wrong';if(kind==='available')w.rows[0].available_fg_pcs='77';if(kind==='net')w.rows[0].net.inputs.target_key='wrong';if(kind==='conditional'){w.allocation.status='UNKNOWN'}if(kind==='apply')w.apply_enabled=true;if(kind==='duplicate')w.rows.push(structuredClone(w.rows[0]));if(kind==='customer')w.schedule_run_result.wip.positions[1].eligible_company_wip=true;if(kind==='eta')w.schedule_run_result.etas[0].result.eta='wrong';expect(()=>parseNativeNetting(w,planningQuery)).toThrow()})
it('keeps original metadata revision and exact microsecond timestamps for retry despite newer source',()=>{const s=parseNativeSupply(supplyWire(),planningQuery),w=parseScheduleWorkspace(workspaceWire(),s),request={id:demandRequest,payload:schedulePayload(w,scheduleConfig,'explicit review')};persistScheduleRequest('actor-project',request);expect(readScheduleRequest('actor-project').pending).toEqual(request);expect(()=>persistScheduleRequest('actor-project',request)).toThrow();expect(()=>clearScheduleRequest('actor-project',crypto.randomUUID())).toThrow();checkScheduleOutcome(scheduleOutcome(request.id),request);clearScheduleRequest('actor-project',request.id);expect(readScheduleRequest('actor-project').pending).toBeNull()})
it('refuses new saves against a stale source and preserves corrupt pending state',()=>{const s=parseNativeSupply(supplyWire(),planningQuery),raw=workspaceWire();raw.current_source_hash='f'.repeat(64);raw.source_state='ARCHIVED_STALE';const w=parseScheduleWorkspace(raw,s);expect(()=>schedulePayload(w,scheduleConfig,'review')).toThrow();localStorage.setItem(scheduleRequestKey('actor'),'broken');expect(readScheduleRequest('actor').error).not.toBe('');expect(localStorage.getItem(scheduleRequestKey('actor'))).toBe('broken')})
it('converts WIB independently of computer timezone while preserving an unchanged original microsecond wire value',()=>{const original='2026-10-01T01:00:00.123456Z';expect(instantToWibInput(original)).toBe('2026-10-01T08:00:00');expect(wibInputToInstant('2026-10-01T08:00',original)).toBe(original);expect(wibInputToInstant('2026-10-01T08:01')).toBe('2026-10-01T01:01:00.000Z');expect(()=>wibInputToInstant('2026-02-30T10:00')).toThrow();expect(()=>wibInputToInstant('')).toThrow();expect(workKey).toBeTruthy()})
it.each(['RUNNING','DONE','FAILED'] as const)('reads genuine %s work metadata without inventing completed history',analysis_state=>{
 const wire={...stagedWorkspaceWire(),analysis_state,history_capture_state:'INCOMPLETE'},w=parseStagedScheduleWorkspace(wire,demandRequest,{capturedAt:scheduleJobWire().reference.captured_at,sourceHash:'a'.repeat(64)})
 expect(w.staged).toMatchObject({analysisState:analysis_state,historyState:'INCOMPLETE',productionState:'COMPLETE'});expect(w.requirements[1].targets).toEqual([])
 const payload=schedulePayload(w,scheduleConfig,'work metadata only');expect(payload.staged_review_contract).toBe(STAGED_SCHEDULE_CONTRACT)
 const r={id:demandRequest,payload};persistScheduleRequest('staged',r);expect(readScheduleRequest('staged').pending).toEqual(r);checkScheduleOutcome(stagedScheduleOutcome(r.id),r);expect(()=>checkScheduleOutcome(scheduleOutcome(r.id),r)).toThrow()
})
it.each(['request','reference-hash','microsecond','run','unchanged-hash','customer-target','target-size','unknown-with-guidance','history-state','state','contract','extra'] )('refuses staged work metadata misbinding: %s',kind=>{
 const wire=stagedWorkspaceWire();const reference={capturedAt:wire.captured_at,sourceHash:wire.analysis_source_hash}
 if(kind==='request')wire.source_request_id=crypto.randomUUID()
 if(kind==='reference-hash')reference.sourceHash='b'.repeat(64)
 if(kind==='microsecond')reference.capturedAt=wire.captured_at.replace(/(\d)Z$/,d=>String((Number(d[0])+1)%10)+'Z')
 if(kind==='run')wire.source_run=crypto.randomUUID()
 if(kind==='unchanged-hash')wire.current_source_hash='b'.repeat(64)
 if(kind==='customer-target')wire.position_requirements[1].target_candidates=wire.position_requirements[0].target_candidates
 if(kind==='target-size')wire.position_requirements[0].target_candidates[0].target_key=crypto.randomUUID()+':'+crypto.randomUUID()
 if(kind==='unknown-with-guidance')wire.production_capture_state='UNKNOWN'
 if(kind==='history-state')wire.history_capture_state='UNKNOWN'
 if(kind==='state')wire.analysis_state='COMPLETE'
 if(kind==='contract')wire.staged_review_contract='later-version'
 if(kind==='extra')Object.assign(wire,{apply_enabled:true})
 expect(()=>parseStagedScheduleWorkspace(wire,demandRequest,reference,workspaceWire().source_run)).toThrow()
})
it('keeps an archived staged reference stale even when only the full analysis context changed',()=>{
 const wire={...stagedWorkspaceWire(),source_state:'ARCHIVED_STALE'},w=parseStagedScheduleWorkspace(wire,demandRequest,{capturedAt:wire.captured_at,sourceHash:wire.analysis_source_hash})
 expect(w.currentHash).toBe(w.sourceHash);expect(()=>schedulePayload(w,scheduleConfig,'review')).toThrow()
})
it('allows honest unknown production metadata to be read but refuses saving it',()=>{
 const wire={...stagedWorkspaceWire(),production_capture_state:'UNKNOWN',position_requirements:[]},w=parseStagedScheduleWorkspace(wire,demandRequest,{capturedAt:wire.captured_at,sourceHash:wire.analysis_source_hash})
 expect(w.requirements).toEqual([]);expect(()=>schedulePayload(w,scheduleConfig,'review')).toThrow()
})
it('retains old pending UUID payloads unchanged and rejects unknown route markers or mismatched receipts',async()=>{
 const w=parseScheduleWorkspace(workspaceWire(),parseNativeSupply(supplyWire(),planningQuery)),r={id:demandRequest,payload:schedulePayload(w,scheduleConfig,'old route')}
 persistScheduleRequest('old',r);expect(readScheduleRequest('old').pending).toEqual(r);expect(Object.hasOwn(readScheduleRequest('old').pending!.payload,'staged_review_contract')).toBe(false)
 expect(()=>checkScheduleOutcome(stagedScheduleOutcome(r.id),r)).toThrow();const rpc=vi.fn();await expect(saveStagedSchedule({rpc},r)).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
 localStorage.setItem(scheduleRequestKey('unknown'),JSON.stringify({...r,payload:{...r.payload,staged_review_contract:'unknown'}}));expect(readScheduleRequest('unknown').error).not.toBe('')
 await readStagedSchedule({rpc},demandRequest);expect(rpc).toHaveBeenCalledWith('erp_cp7_get_staged_production_schedule_v1',{p_source_request:demandRequest})
})
