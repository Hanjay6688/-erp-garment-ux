import {it,expect,vi} from 'vitest'
import {parseStagedScheduleWorkspace} from '../../../src/nativeProductionPlanning'
import {boundedWorkspaceWire,scheduleJobWire} from '../../../tests/fixtures/nativeProductionPlanning'
import {demandRequest,demandRun} from '../../../tests/fixtures/nativeDemandHistory'
import {parseFrozenScheduleWorkspace,readFrozenScheduleWorkspace,type FrozenWorkContext} from './nativeFrozenWork'

function fixture(){
 const job=scheduleJobWire(),context:FrozenWorkContext={requestId:demandRequest,reference:{capturedAt:job.reference.captured_at,sourceHash:job.reference.source_hash},runId:null,method:'FROZEN_V2'}
 const wire={...boundedWorkspaceWire(),contract_version:'cp7.planning-schedule-staged-bounded.v2',bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2',history_input_coverage:'PENDING'}
 return{context,wire}
}
it.each(['RUNNING','FAILED'])('keeps %s pending history separate from captured physical work',state=>{
 const{context,wire}=fixture();wire.analysis_state=state
 const w=parseFrozenScheduleWorkspace(wire,context)
 expect(w.staged).toMatchObject({analysisState:state,inputCoverage:'PENDING',historyState:'INCOMPLETE',productionState:'COMPLETE',method:'FROZEN_V2'})
 expect(w.requirements.map(p=>[p.remaining,p.eligible])).toEqual([['8',true],['8',false]])
 expect(w.requirements[1].targets).toEqual([]);expect(w.config).toBeNull()
})
it.each(['RUNNING','DONE','FAILED'])('accepts genuinely COMPLETE frozen coverage for %s without rewriting raw history',state=>{
 const{context,wire}=fixture();wire.analysis_state=state;wire.history_input_coverage='COMPLETE';context.runId=demandRun
 const w=parseFrozenScheduleWorkspace(wire,context)
 expect(w.staged.inputCoverage).toBe('COMPLETE');expect(w.staged.historyState).toBe('INCOMPLETE')
})
it.each(['old-workspace','old-request','old-reference','missing-coverage','not-captured','done-pending','actor-data','wrong-run','wrong-source','microsecond','wrong-size','customer-target','duplicate-position'])('refuses %s inconsistency',kind=>{
 const{context,wire}=fixture(),v:Record<string,any>=wire
 if(kind==='old-workspace')v.contract_version='cp7.planning-schedule-staged-bounded.v1'
 if(kind==='old-request')v.bounded_request_contract='cp7.bounded-analysis-request.v1'
 if(kind==='old-reference')v.bounded_reference_contract='cp7.bounded-analysis-reference.v1'
 if(kind==='missing-coverage')delete v.history_input_coverage
 if(kind==='not-captured')v.history_input_coverage='NOT_CAPTURED'
 if(kind==='done-pending')v.analysis_state='DONE'
 if(kind==='actor-data')v.actor='unexpected'
 if(kind==='wrong-run')context.runId=demandRequest
 if(kind==='wrong-source')v.analysis_source_hash='9'.repeat(64)
 if(kind==='microsecond'){
  const before=v.captured_at,[seconds,fraction='']=before.slice(0,-1).split('.')
  const micros=(BigInt(fraction.padEnd(6,'0'))+1n)%1000000n
  v.captured_at=seconds+'.'+micros.toString().padStart(6,'0')+'Z';expect(v.captured_at).not.toBe(before)
 }
 if(kind==='wrong-size')v.position_requirements[0].target_candidates[0].target_key=demandRequest+':'+demandRequest
 if(kind==='customer-target')v.position_requirements[1].target_candidates=v.position_requirements[0].target_candidates
 if(kind==='duplicate-position')v.position_requirements.push(structuredClone(v.position_requirements[0]))
 expect(()=>parseFrozenScheduleWorkspace(wire,context)).toThrow()
})
it('preserves UNKNOWN physical work instead of inventing requirements',()=>{
 const{context,wire}=fixture();wire.production_capture_state='UNKNOWN';wire.position_requirements=[]
 const w=parseFrozenScheduleWorkspace(wire,context);expect(w.staged.productionState).toBe('UNKNOWN');expect(w.requirements).toEqual([])
})
it('does not let the old parser accept a new response or the new parser accept an old response',()=>{
 const{context,wire}=fixture()
 expect(()=>parseStagedScheduleWorkspace(wire,context.requestId,context.reference,null,'BOUNDED')).toThrow()
 expect(()=>parseFrozenScheduleWorkspace(boundedWorkspaceWire(),context)).toThrow()
})
it('reads only the exact stored request and propagates current server access refusals',async()=>{
 const{context,wire}=fixture(),rpc=vi.fn(async()=>({data:wire,error:null}))
 expect((await readFrozenScheduleWorkspace({rpc},context)).staged.inputCoverage).toBe('PENDING')
 expect(rpc).toHaveBeenCalledWith('erp_cp7_get_staged_production_schedule_v1',{p_source_request:demandRequest})
 const denied={code:'42501'},bad=vi.fn(async()=>({data:null,error:denied}))
 await expect(readFrozenScheduleWorkspace({rpc:bad},context)).rejects.toBe(denied)
 const old={...context,method:'BOUNDED'}as unknown as FrozenWorkContext
 await expect(readFrozenScheduleWorkspace({rpc:bad},old)).rejects.toThrow();expect(bad).toHaveBeenCalledTimes(1)
})
