// @vitest-environment jsdom
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey,readFrozenAnalysisRequest,persistFrozenAnalysisRequest,
 clearFrozenAnalysisRequest,replaceFrozenAnalysisRequest,requestFrozenAnalysis,type FrozenAnalysisRequest} from './nativeFrozenAnalysis'
import {BOUNDED_ANALYSIS_REQUEST,boundedAnalysisRequestKey,persistBoundedAnalysisRequest} from '../../../src/nativeBoundedAnalysis'
import {planningQuery} from '../../../tests/fixtures/nativeProductionPlanning'
import {demandRequest} from '../../../tests/fixtures/nativeDemandHistory'

const actor='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222'
const request=():FrozenAnalysisRequest=>({id:demandRequest,actor,q:{...planningQuery},method:FROZEN_ANALYSIS_REQUEST})
// A controlled lock manager exercises queue ordering. This is not a real
// multi-tab browser qualification; that remains an actual-browser obligation.
beforeEach(()=>{
 const tails=new Map<string,Promise<void>>()
 const locks={request:vi.fn(async(name:string,_options:unknown,action:()=>unknown)=>{
  const prior=tails.get(name)??Promise.resolve();let release!:()=>void
  const hold=new Promise<void>(resolve=>{release=resolve}),tail=prior.then(()=>hold);tails.set(name,tail)
  await prior
  try{return await action()}finally{release();if(tails.get(name)===tail)tails.delete(name)}
 })}
 vi.stubGlobal('navigator',{locks})
})
afterEach(()=>{localStorage.clear();vi.restoreAllMocks();vi.unstubAllGlobals()})

it('cannot issue a new request before its exact method/query/UUID/actor is durable',async()=>{
 const rpc=vi.fn();await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow('belum tersimpan');expect(rpc).not.toHaveBeenCalled()
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{})
 await expect(persistFrozenAnalysisRequest(actor,'work',request())).rejects.toThrow('belum tersimpan')
 await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
})
it('retries the same retained v2 method and arguments after a lost reply without clearing bytes',async()=>{
 const rpc=vi.fn().mockRejectedValueOnce(Error('reply lost')).mockResolvedValue({data:{state:'RUNNING'},error:null})
 await persistFrozenAnalysisRequest(actor,'work',request());const bytes=localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))
 await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow('reply lost')
 expect(localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))).toBe(bytes)
 await requestFrozenAnalysis({rpc},actor,'work');expect(rpc.mock.calls[0]).toEqual(rpc.mock.calls[1])
 expect(rpc).toHaveBeenCalledWith('erp_cp7_request_bounded_staged_analysis_v2',{p_query:planningQuery,p_request:demandRequest})
 expect(rpc.mock.calls[0][1]).not.toHaveProperty('actor')
 expect(localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))).toBe(bytes)
})
it('keeps actors and old v1 recovery separate even when their request UUID is the same',async()=>{
 persistBoundedAnalysisRequest('work',{id:demandRequest,q:planningQuery,method:BOUNDED_ANALYSIS_REQUEST})
 const old=localStorage.getItem(boundedAnalysisRequestKey('work'));await persistFrozenAnalysisRequest(actor,'work',request())
 const rpc=vi.fn();await expect(requestFrozenAnalysis({rpc},other,'work')).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
 await persistFrozenAnalysisRequest(other,'work',{...request(),actor:other,q:{...planningQuery,group_mode:'RESTATED'}})
 await clearFrozenAnalysisRequest(actor,'work',request())
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
 await expect(persistFrozenAnalysisRequest(actor,'work',request())).rejects.toThrow()
 await expect(clearFrozenAnalysisRequest(actor,'work',request())).rejects.toThrow()
 const rpc=vi.fn();await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow();expect(rpc).not.toHaveBeenCalled()
 expect(localStorage.getItem(key)).toBe(bytes)
})
it('refuses clearing or replacing a different retained query from another tab',async()=>{
 const old=request(),changed={...old,q:{...planningQuery,group_mode:'RESTATED' as const}}
 await persistFrozenAnalysisRequest(actor,'work',changed)
 await expect(clearFrozenAnalysisRequest(actor,'work',old)).rejects.toThrow()
 await expect(replaceFrozenAnalysisRequest(actor,'work',old,{...old,id:other})).rejects.toThrow()
 expect(readFrozenAnalysisRequest(actor,'work').pending).toEqual(changed)
})
it('leaves the original finished pointer recoverable after a failed replacement write',async()=>{
 const old=request();await persistFrozenAnalysisRequest(actor,'work',old)
 const bytes=localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('storage full')})
 await expect(replaceFrozenAnalysisRequest(actor,'work',old,{...old,id:other})).rejects.toThrow('storage full')
 expect(localStorage.getItem(frozenAnalysisRequestKey(actor,'work'))).toBe(bytes)
})
it('requires a new UUID and same actor for an intentional replacement',async()=>{
 const old=request();await persistFrozenAnalysisRequest(actor,'work',old)
 await expect(replaceFrozenAnalysisRequest(actor,'work',old,{...old,q:{...planningQuery,group_mode:'RESTATED'}})).rejects.toThrow('nomor permintaan baru')
 await expect(replaceFrozenAnalysisRequest(actor,'work',old,{...old,id:other,actor:other})).rejects.toThrow()
 const next={...old,id:other};await replaceFrozenAnalysisRequest(actor,'work',old,next)
 expect(readFrozenAnalysisRequest(actor,'work').pending).toEqual(next)
})

it('fails closed before storage or network if a shared browser lock is unavailable',async()=>{
 vi.stubGlobal('navigator',{})
 const rpc=vi.fn()
 await expect(persistFrozenAnalysisRequest(actor,'work',request())).rejects.toThrow('dikunci')
 await expect(requestFrozenAnalysis({rpc},actor,'work')).rejects.toThrow('dikunci')
 expect(localStorage.length).toBe(0);expect(rpc).not.toHaveBeenCalled()
})
it('serializes competing creates so a second UUID cannot replace an unresolved request',async()=>{
 const first=request(),second={...first,id:other}
 const results=await Promise.allSettled([persistFrozenAnalysisRequest(actor,'work',first),persistFrozenAnalysisRequest(actor,'work',second)])
 expect(results.map(r=>r.status)).toEqual(['fulfilled','rejected'])
 expect(readFrozenAnalysisRequest(actor,'work').pending).toEqual(first)
})
it('keeps a send and competing replacement in one shared ordering boundary',async()=>{
 const first=request(),second={...first,id:other};await persistFrozenAnalysisRequest(actor,'work',first)
 let started!:()=>void,finish!:(value:{data:unknown;error:null})=>void
 const entered=new Promise<void>(resolve=>{started=resolve})
 const rpc=vi.fn(()=>{started();return new Promise<{data:unknown;error:null}>(resolve=>{finish=resolve})})
 const send=requestFrozenAnalysis({rpc},actor,'work');await entered
 let replaced=false
 const next=replaceFrozenAnalysisRequest(actor,'work',first,second).then(()=>{replaced=true})
 await Promise.resolve();await Promise.resolve()
 expect(replaced).toBe(false);expect(readFrozenAnalysisRequest(actor,'work').pending).toEqual(first)
 finish({data:{state:'DONE'},error:null});await send;await next
 expect(readFrozenAnalysisRequest(actor,'work').pending).toEqual(second)
 expect(rpc).toHaveBeenCalledTimes(1)
})
it.each(['STAGED','DEFERRED'] as const)('keeps the explicit %s finance choice durable and replays it without changing the operational query',async finance=>{
 const r={...request(),finance},rpc=vi.fn().mockRejectedValueOnce(Error('reply lost')).mockResolvedValue({data:{state:'RUNNING'},error:null})
 await persistFrozenAnalysisRequest(actor,'finance',r)
 const bytes=localStorage.getItem(frozenAnalysisRequestKey(actor,'finance'))
 await expect(requestFrozenAnalysis({rpc},actor,'finance')).rejects.toThrow('reply lost')
 expect(localStorage.getItem(frozenAnalysisRequestKey(actor,'finance'))).toBe(bytes)
 await requestFrozenAnalysis({rpc},actor,'finance')
 expect(rpc.mock.calls[0]).toEqual(rpc.mock.calls[1])
 expect(rpc).toHaveBeenCalledWith('erp_cp7_request_bounded_staged_analysis_v2',{p_query:{...planningQuery,finance_mode:finance},p_request:demandRequest})
 expect(readFrozenAnalysisRequest(actor,'finance').pending).toEqual(r)
 await expect(clearFrozenAnalysisRequest(actor,'finance',request())).rejects.toThrow()
})
