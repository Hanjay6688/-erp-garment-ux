// @vitest-environment jsdom
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {boundedWorkspaceWire,scheduleJobWire,scheduleConfig,boundedScheduleOutcome} from '../../../tests/fixtures/nativeProductionPlanning'
import {demandRequest,demandRun,demandRoot} from '../../../tests/fixtures/nativeDemandHistory'
import {scheduleRequestKey,checkScheduleOutcome} from '../../../src/nativeProductionPlanning'
import {parseFrozenScheduleWorkspace,prepareFrozenScheduleRequest,parseFrozenScheduleRequest,checkFrozenScheduleOutcome,frozenScheduleRequestKey,persistFrozenScheduleRequest,readFrozenScheduleRequest,clearFrozenScheduleRequest,saveFrozenSchedule,type FrozenWorkContext} from './nativeFrozenWork'

const actor='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222',scope='production:all'
function fixture(){
 const job=scheduleJobWire(),context:FrozenWorkContext={requestId:demandRequest,reference:{capturedAt:job.reference.captured_at,sourceHash:job.reference.source_hash},runId:null,method:'FROZEN_V2'}
 const wire={...boundedWorkspaceWire(),contract_version:'cp7.planning-schedule-staged-bounded.v2',bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2',history_input_coverage:'PENDING'}
 const w=parseFrozenScheduleWorkspace(wire,context),r=prepareFrozenScheduleRequest(w,context,actor,scheduleConfig,'  diperiksa  ',other)
 const outcome={...boundedScheduleOutcome(r.id),contract_version:'cp7.planning-schedule-staged-bounded-outcome.v2',bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2'}
 return{context,wire,w,r,outcome}
}
beforeEach(()=>{
 const tails=new Map<string,Promise<void>>()
 vi.stubGlobal('navigator',{locks:{request:vi.fn(async(name:string,_options:unknown,action:()=>unknown)=>{
  const prior=tails.get(name)??Promise.resolve();let release!:()=>void
  const hold=new Promise<void>(r=>{release=r}),tail=prior.then(()=>hold);tails.set(name,tail)
  await prior
  try{return await action()}finally{release();if(tails.get(name)===tail)tails.delete(name)}
 })}})
})
afterEach(()=>{localStorage.clear();vi.useRealTimers();vi.restoreAllMocks();vi.unstubAllGlobals()})
it.each(['reply','queue'])('bounds a missing schedule %s and replays the exact durable command',async kind=>{
 const{r,outcome}=fixture();await persistFrozenScheduleRequest(scope,r)
 const key=frozenScheduleRequestKey(scope,actor),bytes=localStorage.getItem(key),locks=navigator.locks
 vi.useFakeTimers();if(kind==='queue')vi.stubGlobal('navigator',{locks:{request:()=>new Promise(()=>{})}})
 const rpc=vi.fn(()=>new Promise(()=>{})),pending=saveFrozenSchedule({rpc},scope,actor)
 const rejected=expect(pending).rejects.toThrow(kind==='queue'?'dikunci tab lain':'Hasil permintaan belum diketahui')
 await vi.advanceTimersByTimeAsync(30000);await rejected;expect(localStorage.getItem(key)).toBe(bytes)
 expect(rpc).toHaveBeenCalledTimes(kind==='reply'?1:0)
 vi.stubGlobal('navigator',{locks});const retry=vi.fn(async()=>({data:outcome,error:null}));await saveFrozenSchedule({rpc:retry},scope,actor)
 expect(retry).toHaveBeenCalledWith('erp_cp7_save_staged_production_schedule_v1',{p_payload:r.payload,p_request:r.id})
 expect(localStorage.getItem(key)).toBe(bytes);expect(vi.getTimerCount()).toBe(0)
})
it('prepares physical work while frozen history remains pending without allocating customer stock',()=>{
 const{w,r}=fixture();expect(w.staged.inputCoverage).toBe('PENDING');expect(w.staged.analysisState).toBe('RUNNING')
 expect(r.sourceMethod).toBe('FROZEN_V2');expect(r.payload.reason).toBe('diperiksa');expect(r.payload.config).toEqual(scheduleConfig)
 expect(r.payload.config.positions[1].target_key).toBeNull();expect(r.payload.config.positions[1].yield_numerator).toBeNull()
 expect(r.payload.config.through_at).toBe('2026-10-02T12:00:00.123456Z')
})
it.each(['stale','physical-unknown','old-method','other-request','other-run','other-hash','other-clock'])('refuses unsafe preparation: %s',kind=>{
 const{w,context}=fixture()
 if(kind==='stale')w.state='ARCHIVED_STALE'
 if(kind==='physical-unknown')w.staged.productionState='UNKNOWN'
 if(kind==='old-method')Object.assign(context,{method:'BOUNDED'})
 if(kind==='other-request')context.requestId=other
 if(kind==='other-run')context.runId=other
 if(kind==='other-hash')context.reference.sourceHash='9'.repeat(64)
 if(kind==='other-clock')context.reference.capturedAt='2026-10-02T00:00:00.123456Z'
 expect(()=>prepareFrozenScheduleRequest(w,context,actor,scheduleConfig,'review',other)).toThrow()
})
it.each(['method','actor','extra','contract','revision-overflow','revision-fraction','config-number','blank-reason','wrong-ref'])('refuses corrupted stored command: %s',kind=>{
 const{r}=fixture();const v=structuredClone(r)as unknown as Record<string,any>
 if(kind==='method')v.sourceMethod='BOUNDED'
 if(kind==='actor')v.actor=other
 if(kind==='extra')v.extra=true
 if(kind==='contract')v.payload.staged_review_contract='cp7.schedule-staged-review.v2'
 if(kind==='revision-overflow')v.payload.expected_revision='9223372036854775807'
 if(kind==='revision-fraction')v.payload.expected_revision='0.5'
 if(kind==='config-number')v.payload.config.positions[0].eligible_input_pcs=8
 if(kind==='blank-reason')v.payload.reason=' '
 if(kind==='wrong-ref')v.reference.sourceHash='not-a-hash'
 expect(()=>parseFrozenScheduleRequest(v,actor)).toThrow()
})
it.each(['old-outcome','old-request-contract','old-reference-contract','wrong-request','wrong-run','wrong-hash','wrong-revision','extra','go'])('refuses unbound outcome: %s',kind=>{
 const{r,outcome}=fixture(),v=outcome as Record<string,unknown>
 if(kind==='old-outcome')v.contract_version='cp7.planning-schedule-staged-bounded-outcome.v1'
 if(kind==='old-request-contract')v.bounded_request_contract='cp7.bounded-analysis-request.v1'
 if(kind==='old-reference-contract')v.bounded_reference_contract='cp7.bounded-analysis-reference.v1'
 if(kind==='wrong-request')v.request_id=demandRequest
 if(kind==='wrong-run')v.source_run=other
 if(kind==='wrong-hash')v.source_hash='9'.repeat(64)
 if(kind==='wrong-revision')v.revision='2'
 if(kind==='extra')v.extra=true
 if(kind==='go')v.production_go=true
 expect(()=>checkFrozenScheduleOutcome(v,r)).toThrow()
})
it('accepts exact v2 receipt but the old bounded checker rejects it',()=>{
 const{r,outcome}=fixture();expect(checkFrozenScheduleOutcome(outcome,r)).toMatchObject({sourceMethod:'FROZEN_V2',requestId:r.id,sourceRun:demandRun,revision:'1'})
 expect(()=>checkScheduleOutcome(outcome,{id:r.id,payload:r.payload,sourceMethod:'BOUNDED'})).toThrow()
})
it('retains exact durable actor, method, UUID and payload after reply loss and reload',async()=>{
 const{r,outcome}=fixture(),rpc=vi.fn<(name:string,args:{p_request:string;p_payload:unknown})=>Promise<{data:unknown;error:unknown}>>()
 await expect(saveFrozenSchedule({rpc},scope,actor)).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
 await persistFrozenScheduleRequest(scope,r)
 const key=frozenScheduleRequestKey(scope,actor),bytes=localStorage.getItem(key)
 rpc.mockRejectedValueOnce(Error('reply lost'));await expect(saveFrozenSchedule({rpc},scope,actor)).rejects.toThrow('reply lost')
 expect(localStorage.getItem(key)).toBe(bytes);const original=structuredClone(rpc.mock.calls[0])
 rpc.mockResolvedValueOnce({data:outcome,error:null});await saveFrozenSchedule({rpc},scope,actor)
 expect(rpc.mock.calls[1]).toEqual(original);expect(original).toEqual(['erp_cp7_save_staged_production_schedule_v1',{p_request:r.id,p_payload:r.payload}])
 expect(readFrozenScheduleRequest(scope,actor).pending).toEqual(r);expect(localStorage.getItem(key)).toBe(bytes)
 await clearFrozenScheduleRequest(scope,r);expect(localStorage.getItem(key)).toBeNull()
})
it.each([{code:'42501',message:'CP7_SCHEDULE_ACCESS_CHANGED'},{code:'40001',message:'CP7_SCHEDULE_SOURCE_CHANGED'},{code:'P0001',message:'CP7_SCHEDULE_REVISION_CHANGED'}])('preserves recovery on current server refusal $message',async error=>{
 const{r}=fixture();await persistFrozenScheduleRequest(scope,r);const key=frozenScheduleRequestKey(scope,actor),bytes=localStorage.getItem(key),rpc=vi.fn(async()=>({data:null,error}))
 await expect(saveFrozenSchedule({rpc},scope,actor)).rejects.toBe(error);expect(localStorage.getItem(key)).toBe(bytes);expect(rpc).toHaveBeenCalledTimes(1)
})
it('does not use another actor or old v1 storage and preserves corrupt recovery',async()=>{
 const{r}=fixture(),rpc=vi.fn(),old=JSON.stringify({id:r.id,payload:r.payload,sourceMethod:'BOUNDED'})
 localStorage.setItem(scheduleRequestKey(scope),old);await expect(saveFrozenSchedule({rpc},scope,actor)).rejects.toThrow()
 await persistFrozenScheduleRequest(scope,r);await expect(saveFrozenSchedule({rpc},scope,other)).rejects.toThrow()
 const key=frozenScheduleRequestKey(scope,actor);localStorage.setItem(key,'{"broken":')
 await expect(persistFrozenScheduleRequest(scope,r)).rejects.toThrow();await expect(clearFrozenScheduleRequest(scope,r)).rejects.toThrow();await expect(saveFrozenSchedule({rpc},scope,actor)).rejects.toThrow()
 expect(localStorage.getItem(key)).toBe('{"broken":');expect(localStorage.getItem(scheduleRequestKey(scope))).toBe(old);expect(rpc).not.toHaveBeenCalled()
})
it('fails before sending when locks or durable storage are unavailable',async()=>{
 const{r}=fixture(),rpc=vi.fn();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{})
 await expect(persistFrozenScheduleRequest(scope,r)).rejects.toThrow('belum tersimpan');await expect(saveFrozenSchedule({rpc},scope,actor)).rejects.toThrow()
 vi.stubGlobal('navigator',{});await expect(persistFrozenScheduleRequest(scope,r)).rejects.toThrow('dikunci');await expect(saveFrozenSchedule({rpc},scope,actor)).rejects.toThrow('dikunci');expect(rpc).not.toHaveBeenCalled()
})
it('serializes competing creates, holds the lock through send and rereads queued recovery',async()=>{
 const{r,outcome}=fixture(),second={...structuredClone(r),id:demandRoot}
 const created=await Promise.allSettled([persistFrozenScheduleRequest(scope,r),persistFrozenScheduleRequest(scope,second)])
 expect(created.map(x=>x.status).sort()).toEqual(['fulfilled','rejected']);expect(readFrozenScheduleRequest(scope,actor).pending).toEqual(r)
 let release!:(v:{data:unknown;error:null})=>void,entered!:()=>void
 const started=new Promise<void>(resolve=>{entered=resolve}),reply=new Promise<{data:unknown;error:null}>(resolve=>{release=resolve})
 const rpc=vi.fn(()=>{entered();return reply}),sending=saveFrozenSchedule({rpc},scope,actor);await started
 let cleared=false;const clearing=clearFrozenScheduleRequest(scope,r).then(()=>{cleared=true})
 const next=persistFrozenScheduleRequest(scope,second)
 const nextRpc=vi.fn(async()=>({data:{...outcome,request_id:second.id},error:null})),queued=saveFrozenSchedule({rpc:nextRpc},scope,actor)
 await Promise.resolve();expect(cleared).toBe(false);expect(nextRpc).not.toHaveBeenCalled()
 release({data:outcome,error:null});await sending;await clearing;await next;await queued
 expect(nextRpc).toHaveBeenCalledWith('erp_cp7_save_staged_production_schedule_v1',{p_payload:second.payload,p_request:second.id})
 await expect(clearFrozenScheduleRequest(scope,r)).rejects.toThrow();expect(readFrozenScheduleRequest(scope,actor).pending).toEqual(second)
})
