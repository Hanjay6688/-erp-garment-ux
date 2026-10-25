// @vitest-environment jsdom
import {afterEach,it,expect,vi} from 'vitest'
import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey,readFrozenAnalysisRequest,persistFrozenAnalysisRequest,
 clearFrozenAnalysisRequest,replaceFrozenAnalysisRequest,requestFrozenAnalysis,type FrozenAnalysisRequest} from './nativeFrozenAnalysis'
import {BOUNDED_ANALYSIS_REQUEST,boundedAnalysisRequestKey,persistBoundedAnalysisRequest} from '../../../src/nativeBoundedAnalysis'
import {planningQuery} from '../../../tests/fixtures/nativeProductionPlanning'
import {demandRequest} from '../../../tests/fixtures/nativeDemandHistory'

const actor='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222'
const request=():FrozenAnalysisRequest=>({id:demandRequest,actor,q:{...planningQuery},method:FROZEN_ANALYSIS_REQUEST})
afterEach(()=>{localStorage.clear();vi.restoreAllMocks()})

it('cannot issue a new request before its exact method/query/UUID/actor is durable',async()=>{
 const rpc=vi.fn();await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow('belum tersimpan');expect(rpc).not.toHaveBeenCalled()
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{})
 expect(()=>persistFrozenAnalysisRequest(actor,'work',request())).toThrow('belum tersimpan')
 await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
})
it('retries the same retained v2 method and arguments after a lost reply without clearing bytes',async()=>{
 const rpc=vi.fn().mockRejectedValueOnce(Error('reply lost')).mockResolvedValue({data:{state:'RUNNING'},error:null})
 persistFrozenAnalysisRequest(actor,'work',request());const bytes=localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))
 await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow('reply lost')
 expect(localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))).toBe(bytes)
 await requestFrozenAnalysis({rpc},actor,'work');expect(rpc.mock.calls[0]).toEqual(rpc.mock.calls[1])
 expect(rpc).toHaveBeenCalledWith('erp_cp7_request_bounded_staged_analysis_v2',{p_query:planningQuery,p_request:demandRequest})
 expect(rpc.mock.calls[0][1]).not.toHaveProperty('actor')
 expect(localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))).toBe(bytes)
})
it('keeps actors and old v1 recovery separate even when their request UUID is the same',async()=>{
 persistBoundedAnalysisRequest('work',{id:demandRequest,q:planningQuery,method:BOUNDED_ANALYSIS_REQUEST})
 const old=localStorage.getItem(boundedAnalysisRequestKey('work'));persistFrozenAnalysisRequest(actor,'work',request())
 const rpc=vi.fn();await expect(requestFrozenAnalysis({rpc},other,'work')).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
 persistFrozenAnalysisRequest(other,'work',{...request(),actor:other,q:{...planningQuery,group_mode:'RESTATED'}})
 clearFrozenAnalysisRequest(actor,'work',request())
 expect(readFrozenAnalysisRequest(other,'work').pending?.q.group_mode).toBe('RESTATED')
 expect(localStorage.getItem(boundedAnalysisRequestKey('work'))).toBe(old)
})
it.each(['actor','method','uuid','date','scope','finance'])('preserves corrupt %s bytes and refuses all calls/overwrites',async kind=>{
 const bad:Record<string,unknown>=structuredClone(request())
 if(kind==='actor')bad.actor=other
 if(kind==='method')bad.method=BOUNDED_ANALYSIS_REQUEST
 if(kind==='uuid')bad.id='different'
 if(kind==='date')bad.q={...planningQuery,from_date:'2026-02-30'}
 if(kind==='scope')bad.q={...planningQuery,source_override:'COMPLETE'}
 if(kind==='finance')bad.finance='READY'
 const bytes=JSON.stringify(bad),key=frozenAnalysisRequestKey(actor,'work');localStorage.setItem(key,bytes)
 expect(readFrozenAnalysisRequest(actor,'work').error).not.toBe('')
 expect(()=>persistFrozenAnalysisRequest(actor,'work',request())).toThrow()
 expect(()=>clearFrozenAnalysisRequest(actor,'work',request())).toThrow()
 const rpc=vi.fn();await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
 expect(localStorage.getItem(key)).toBe(bytes)
})
it('refuses clearing or replacing a different retained query from another tab',()=>{
 const old=request(),changed={...old,q:{...planningQuery,group_mode:'RESTATED' as const}}
 persistFrozenAnalysisRequest(actor,'work',changed)
 expect(()=>clearFrozenAnalysisRequest(actor,'work',old)).toThrow()
 expect(()=>replaceFrozenAnalysisRequest(actor,'work',old,{...old,id:other})).toThrow()
 expect(readFrozenAnalysisRequest(actor,'work').pending).toEqual(changed)
})
it('leaves the original finished pointer recoverable after a failed replacement write',()=>{
 const old=request();persistFrozenAnalysisRequest(actor,'work',old)
 const bytes=localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('storage full')})
 expect(()=>replaceFrozenAnalysisRequest(actor,'work',old,{...old,id:other})).toThrow('storage full')
 expect(localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))).toBe(bytes)
})
it('requires a new UUID and same actor for an intentional replacement',()=>{
 const old=request();persistFrozenAnalysisRequest(actor,'work',old)
 expect(()=>replaceFrozenAnalysisRequest(actor,'work',old,{...old,q:{...planningQuery,group_mode:'RESTATED'}})).toThrow('nomor permintaan baru')
 expect(()=>replaceFrozenAnalysisRequest(actor,'work',old,{...old,id:other,actor:other})).toThrow()
 const next={...old,id:other};replaceFrozenAnalysisRequest(actor,'work',old,next)
 expect(readFrozenAnalysisRequest(actor,'work').pending).toEqual(next)
})
