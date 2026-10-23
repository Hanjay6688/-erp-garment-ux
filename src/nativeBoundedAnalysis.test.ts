// @vitest-environment jsdom
import {afterEach,it,expect,vi} from 'vitest'
import {BOUNDED_ANALYSIS_REQUEST,boundedAnalysisRequestKey,readBoundedAnalysisRequest,persistBoundedAnalysisRequest,clearBoundedAnalysisRequest,requestBoundedAnalysis,type BoundedAnalysisRequest} from './nativeBoundedAnalysis'
import {nativeDemandRequestKey,persistNativeDemandRequest,readNativeDemandRequest} from './nativeDemandHistory'
import {parseStagedScheduleWorkspace,schedulePayload,checkScheduleOutcome,readScheduleRequest,persistScheduleRequest,scheduleRequestKey} from './nativeProductionPlanning'
import {boundedWorkspaceWire,boundedScheduleOutcome,stagedWorkspaceWire,stagedScheduleOutcome,scheduleConfig,planningQuery} from '../tests/fixtures/nativeProductionPlanning'
import {demandRequest} from '../tests/fixtures/nativeDemandHistory'

const request=():BoundedAnalysisRequest=>({id:demandRequest,q:{...planningQuery},method:BOUNDED_ANALYSIS_REQUEST})
const parseWork=(wire:unknown=boundedWorkspaceWire())=>{const w=boundedWorkspaceWire();return parseStagedScheduleWorkspace(wire,demandRequest,{capturedAt:w.captured_at,sourceHash:w.analysis_source_hash},w.source_run,'BOUNDED')}
afterEach(()=>{localStorage.clear();vi.restoreAllMocks()})

it('keeps a durable method/query/UUID and sends only the declared three server fields on retry',async()=>{
 const r=request(),rpc=vi.fn().mockRejectedValueOnce(Error('reply lost')).mockResolvedValue({data:{same:'actual reply'},error:null})
 persistBoundedAnalysisRequest('work',r)
 const bytes=localStorage.getItem(boundedAnalysisRequestKey('work'))
 await expect(requestBoundedAnalysis({rpc},readBoundedAnalysisRequest('work').pending!)).rejects.toThrow('reply lost')
 expect(localStorage.getItem(boundedAnalysisRequestKey('work'))).toBe(bytes)
 await requestBoundedAnalysis({rpc},readBoundedAnalysisRequest('work').pending!)
 expect(rpc.mock.calls[0]).toEqual(rpc.mock.calls[1])
 expect(rpc).toHaveBeenCalledWith('erp_cp7_request_bounded_staged_analysis_v1',{p_query:planningQuery,p_request:demandRequest})
 clearBoundedAnalysisRequest('work',r);expect(readBoundedAnalysisRequest('work').pending).toBeNull()
})
it.each(['method','finance','query','date','uuid'])('refuses corrupt %s recovery without erasing it or overwriting with a new request',kind=>{
 const bad:Record<string,unknown>=structuredClone(request())
 if(kind==='method')bad.method='cp7.bounded-analysis-request.v9'
 if(kind==='finance')bad.finance='DEFERRED'
 if(kind==='query')bad.q={...planningQuery,unexpected:'COMPLETE'}
 if(kind==='date')bad.q={...planningQuery,from_date:'2026-02-30'}
 if(kind==='uuid')bad.id='other-request'
 const bytes=JSON.stringify(bad);localStorage.setItem(boundedAnalysisRequestKey('work'),bytes)
 expect(readBoundedAnalysisRequest('work').error).not.toBe('')
 expect(()=>persistBoundedAnalysisRequest('work',request())).toThrow()
 expect(()=>clearBoundedAnalysisRequest('work',request())).toThrow()
 expect(localStorage.getItem(boundedAnalysisRequestKey('work'))).toBe(bytes)
})
it('compares the complete retained request before clearing even when another tab reused its UUID',()=>{
 const old=request();persistBoundedAnalysisRequest('work',old)
 const changed={...old,q:{...planningQuery,group_mode:'RESTATED' as const}}
 localStorage.setItem(boundedAnalysisRequestKey('work'),JSON.stringify(changed))
 expect(()=>clearBoundedAnalysisRequest('work',old)).toThrow()
 expect(readBoundedAnalysisRequest('work').pending).toEqual(changed)
})
it('does not touch old native request bytes in their original namespace',()=>{
 const old={id:demandRequest,q:planningQuery};persistNativeDemandRequest('staged-schedule-source:actor',old)
 const bytes=localStorage.getItem(nativeDemandRequestKey('staged-schedule-source:actor'))
 persistBoundedAnalysisRequest('actor',request());clearBoundedAnalysisRequest('actor',request())
 expect(localStorage.getItem(nativeDemandRequestKey('staged-schedule-source:actor'))).toBe(bytes)
 expect(readNativeDemandRequest('staged-schedule-source:actor').pending).toEqual(old)
})
it.each(['method','finance','query'])('does not call any facade for an invalid %s input',async kind=>{
 const bad:Record<string,unknown>=structuredClone(request())
 if(kind==='method')delete bad.method
 if(kind==='finance')bad.finance='DEFERRED'
 if(kind==='query')bad.q={...planningQuery,finance_mode:'DEFERRED'}
 const rpc=vi.fn();await expect(requestBoundedAnalysis({rpc},bad as BoundedAnalysisRequest)).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
})
it('accepts complete derived input coverage while preserving raw incomplete status and genuine WIP unknowns',()=>{
 const w=parseWork();expect(w.staged).toMatchObject({method:'BOUNDED',inputCoverage:'COMPLETE',historyState:'INCOMPLETE',productionState:'COMPLETE'})
 expect(schedulePayload(w,scheduleConfig,'reviewed work').staged_review_contract).toBe('cp7.schedule-staged-review.v1')
 const unknown=boundedWorkspaceWire();unknown.production_capture_state='UNKNOWN';unknown.position_requirements=[]
 const blocked=parseWork(unknown);expect(()=>schedulePayload(blocked,scheduleConfig,'reviewed work')).toThrow()
})
it.each(['coverage','request','reference','run','extra','legacy'])('rejects mismatched bounded %s work guidance',kind=>{
 const v:Record<string,unknown>=boundedWorkspaceWire()
 if(kind==='coverage')v.history_input_coverage='PARTIAL'
 if(kind==='request')v.bounded_request_contract='another'
 if(kind==='reference')v.bounded_reference_contract='another'
 if(kind==='run')v.source_run='00000000-0000-0000-0000-000000000001'
 if(kind==='extra')v.source_override=true
 if(kind==='legacy')Object.assign(v,stagedWorkspaceWire())
 expect(()=>parseWork(v)).toThrow()
})
it('requires the expected method explicitly and never promotes a legacy response to bounded coverage',()=>{
 const w=boundedWorkspaceWire(),reference={capturedAt:w.captured_at,sourceHash:w.analysis_source_hash}
 expect(()=>parseStagedScheduleWorkspace(w,demandRequest,reference)).toThrow()
 expect(()=>parseWork(stagedWorkspaceWire())).toThrow()
 const legacy=stagedWorkspaceWire();expect(parseStagedScheduleWorkspace(legacy,demandRequest,reference).staged?.method).toBe('NATIVE')
})
it('recovers bounded save metadata and checks only the matching receipt without adding a server payload field',()=>{
 const r={id:demandRequest,payload:schedulePayload(parseWork(),scheduleConfig,'reviewed work'),sourceMethod:'BOUNDED' as const}
 persistScheduleRequest('actor',r);expect(readScheduleRequest('actor').pending).toEqual(r)
 expect(r.payload).not.toHaveProperty('sourceMethod')
 expect(()=>checkScheduleOutcome(boundedScheduleOutcome(r.id),r)).not.toThrow()
 expect(()=>checkScheduleOutcome(stagedScheduleOutcome(r.id),r)).toThrow()
 const legacy={id:r.id,payload:r.payload};expect(()=>checkScheduleOutcome(boundedScheduleOutcome(r.id),legacy)).toThrow()
 localStorage.setItem(scheduleRequestKey('bad'),JSON.stringify({...r,sourceMethod:'unknown'}));expect(readScheduleRequest('bad').error).not.toBe('')
 localStorage.setItem(scheduleRequestKey('old'),JSON.stringify(legacy));expect(readScheduleRequest('old').pending).toEqual(legacy)
})
