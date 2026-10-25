// @vitest-environment jsdom
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey,persistFrozenAnalysisRequest,replaceFrozenAnalysisRequest,readFrozenAnalysisRequest} from '../../cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
import {driveFrozenQuantity,readFrozenQuantity,readFrozenQuantityPage,checkFrozenQuantity,readFrozenQuantityFinanceStatus,frozenQuantityAnalogContext,frozenQuantityCuttingContext,type FrozenQuantitySession} from './nativeFrozenQuantity'
import {frozenFinanceFixture} from '../../../tests/fixtures/frozenAnalysisFinance'
import {parseStagedJob} from '../../../src/nativeStagedJob'
import {stagedRun} from '../../../tests/fixtures/nativeAnalysisPages'

let f:Awaited<ReturnType<typeof stagedRun>>,s:FrozenQuantitySession
beforeEach(async()=>{
 const tails=new Map<string,Promise<void>>()
 vi.stubGlobal('navigator',{locks:{request:async(name:string,_options:unknown,fn:()=>unknown)=>{
  const prior=tails.get(name)??Promise.resolve();let release!:()=>void
  const held=new Promise<void>(resolve=>{release=resolve}),tail=prior.then(()=>held);tails.set(name,tail)
  await prior;try{return await fn()}finally{release();if(tails.get(name)===tail)tails.delete(name)}
 }}})
 f=await stagedRun({targets:120,pageSizes:[60,60]});s={actor:f.actor,scope:'quantity',request:{id:f.pageSet.request_id,actor:f.actor,q:f.query,method:FROZEN_ANALYSIS_REQUEST}}
 await persistFrozenAnalysisRequest(s.actor,s.scope,s.request)
})
afterEach(()=>{localStorage.clear();vi.restoreAllMocks();vi.unstubAllGlobals()})
const done=()=>parseStagedJob(f.job('DONE'),s.request.id,{id:s.request.id,q:s.request.q})
const route=async(name:string,args:{p_index:number})=>({data:name==='erp_cp7_request_bounded_staged_analysis_v2'?f.job('DONE'):name==='erp_cp7_read_staged_analysis_pages_v1'?f.pageSet:name==='erp_cp7_check_staged_analysis_source_v1'?{source_state:'ARCHIVED_STALE',checked_at:'2026-10-25T19:00:00.123456Z'}:f.page(args.p_index),error:null})

it('replays explicit v2 on every reopen and drives only the original durable query/UUID',async()=>{
 const calls:string[]=[],rpc=vi.fn(async(name:string,args:{p_request:string;p_query?:unknown})=>{
  calls.push(name);expect(args.p_request).toBe(s.request.id)
  if(name==='erp_cp7_request_bounded_staged_analysis_v2'){expect(args.p_query).toEqual(f.query);return{data:f.job('RUNNING',{targets_done_in_stage:0}),error:null}}
  expect(name).toBe('erp_cp7_step_staged_analysis_v1');return{data:f.job('DONE'),error:null}
 })
 await driveFrozenQuantity({rpc},s,{});await driveFrozenQuantity({rpc},s,{})
 expect(calls).toEqual(['erp_cp7_request_bounded_staged_analysis_v2','erp_cp7_step_staged_analysis_v1','erp_cp7_request_bounded_staged_analysis_v2','erp_cp7_step_staged_analysis_v1'])
 expect(readFrozenAnalysisRequest(s.actor,s.scope).pending).toEqual(s.request)
})
it('keeps selected finance mode through DONE and reads its separate status without reloading pages',async()=>{
 localStorage.clear();s.request={...s.request,finance:'STAGED'};await persistFrozenAnalysisRequest(s.actor,s.scope,s.request)
 const raw=f.job('DONE',{finance_capture:frozenFinanceFixture(f)}),rpc=vi.fn(async(name:string,args:any)=>name==='erp_cp7_request_bounded_staged_analysis_v2'||name==='erp_cp7_get_staged_analysis_v1'?{data:raw,error:null}:route(name,args))
 const job=await driveFrozenQuantity({rpc},s,{});expect(job?.financeCapture?.state).toBe('READY')
 expect(rpc).toHaveBeenCalledWith('erp_cp7_request_bounded_staged_analysis_v2',{p_request:s.request.id,p_query:{...f.query,finance_mode:'STAGED'}})
 const source=await readFrozenQuantity({rpc},s,job!);rpc.mockClear()
 const status=await readFrozenQuantityFinanceStatus({rpc},s,source);expect((status.data as any).finance_capture.result.metrics).toHaveLength(3)
 expect(rpc.mock.calls).toEqual([['erp_cp7_get_staged_analysis_v1',{p_request:s.request.id}]])
 const bytes=localStorage.getItem(frozenAnalysisRequestKey(s.actor,s.scope))
 rpc.mockImplementation(async()=>{
  localStorage.setItem(frozenAnalysisRequestKey(s.actor,s.scope),JSON.stringify({...s.request,finance:'DEFERRED'}))
  return{data:raw,error:null}
 })
 await expect(readFrozenQuantityFinanceStatus({rpc},s,source)).rejects.toThrow()
 expect(localStorage.getItem(frozenAnalysisRequestKey(s.actor,s.scope))).not.toBe(bytes)
})
it('requires server v2 method acceptance again before any result page and binds the verified source to analog v2',async()=>{
 const rpc=vi.fn(route),v=await readFrozenQuantity({rpc},s,done()),p=await readFrozenQuantityPage({rpc},s,v,1)
 expect([p.targetLo,p.targetHi]).toEqual([61,120])
 expect(rpc.mock.calls.map(c=>c[0])).toEqual(['erp_cp7_request_bounded_staged_analysis_v2','erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1'])
 expect(rpc.mock.calls[2][1]).toEqual({p_run:f.runId,p_index:1,p_access:f.pageSet.access_epoch})
 expect(frozenQuantityAnalogContext(s,v,v.header.labels[0].key)).toMatchObject({actor:s.actor,sourceMethod:'FROZEN_V2',requestId:s.request.id,identityHash:f.identityHash,reference:{capturedAt:f.reference.captured_at}})
 expect((await checkFrozenQuantity({rpc},s,v)).sourceState).toBe('ARCHIVED_STALE')
 expect(()=>frozenQuantityAnalogContext(s,v,'00000000-0000-4000-8000-000000000999:00000000-0000-4000-8000-000000000888')).toThrow()
})
it('does not relabel an old-method DONE or fall back after a server method refusal',async()=>{
 const rpc=vi.fn(async()=>({data:null,error:{code:'P0001',message:'CP7_ANALYSIS_REQUEST_CHANGED'}}))
 await expect(readFrozenQuantity({rpc},s,done())).rejects.toMatchObject({message:'CP7_ANALYSIS_REQUEST_CHANGED'})
 expect(rpc).toHaveBeenCalledOnce();expect(rpc.mock.calls[0]).toEqual(['erp_cp7_request_bounded_staged_analysis_v2',{p_request:s.request.id,p_query:s.request.q}])
})
it.each(['request','method','actor','query','corrupt'])('refuses %s changes without network or discarding durable bytes',async field=>{
 const key=frozenAnalysisRequestKey(s.actor,s.scope),other=structuredClone(s.request)
 if(field==='request')other.id='00000000-0000-4000-8000-000000000999'
 if(field==='method')(other as {method:string}).method='cp7.bounded-analysis-request.v1'
 if(field==='actor')other.actor='00000000-0000-4000-8000-000000000999'
 if(field==='query')other.q.group_mode='RESTATED'
 const bytes=field==='corrupt'?'{not json':JSON.stringify(other);localStorage.setItem(key,bytes)
 const rpc=vi.fn();await expect(driveFrozenQuantity({rpc},s,{})).rejects.toThrow();expect(rpc).not.toHaveBeenCalled();expect(localStorage.getItem(key)).toBe(bytes)
})
it.each(['run','count','clock','hash','expired'])('refuses mismatched server %s before pages',async field=>{
 const raw=f.job('DONE')
 if(field==='run')raw.run_id='00000000-0000-4000-8000-000000000999'
 if(field==='count')raw.targets_total=121
 if(field==='clock')raw.reference={...raw.reference,captured_at:'2026-10-07T09:00:00.000001Z'}
 if(field==='hash')raw.reference={...raw.reference,source_hash:'f'.repeat(64)}
 if(field==='expired')Object.assign(raw,{retention:{days:7,state:'EXPIRED',kept_until:'2026-10-14T09:00:00.000000Z'}})
 const rpc=vi.fn(async()=>({data:raw,error:null}))
 await expect(readFrozenQuantity({rpc},s,done())).rejects.toThrow();expect(rpc).toHaveBeenCalledOnce()
})
it('refuses a copied/unadmitted page set before page, source-check or analog reads',async()=>{
 const rpc=vi.fn(route),v=await readFrozenQuantity({rpc},s,done()),copy=structuredClone(v);rpc.mockClear()
 await expect(readFrozenQuantityPage({rpc},s,copy,0)).rejects.toThrow()
 await expect(checkFrozenQuantity({rpc},s,copy)).rejects.toThrow()
 expect(()=>frozenQuantityAnalogContext(s,copy,copy.header.labels[0].key)).toThrow();expect(rpc).not.toHaveBeenCalled()
})
it('does not render a page with a changed exact hash even when other metadata matches',async()=>{
 const rpc=vi.fn(route),v=await readFrozenQuantity({rpc},s,done())
 rpc.mockResolvedValue({data:{...f.page(0),body:f.page(0).body+' '},error:null})
 await expect(readFrozenQuantityPage({rpc},s,v,0)).rejects.toThrow()
})
it('holds each in-flight unit against a competing replacement and never steps its new UUID',async()=>{
 let entered!:()=>void,release!:(v:{data:unknown;error:null})=>void
 const started=new Promise<void>(r=>{entered=r}),rpc=vi.fn(async(name:string)=>{
  if(name==='erp_cp7_request_bounded_staged_analysis_v2')return{data:f.job('RUNNING',{targets_done_in_stage:0}),error:null}
  entered();return new Promise<{data:unknown;error:null}>(r=>{release=r})
 })
 const drive=driveFrozenQuantity({rpc},s,{});await started
 let replaced=false;const next={...s.request,id:'00000000-0000-4000-8000-000000000999'}
 const replacement=replaceFrozenAnalysisRequest(s.actor,s.scope,s.request,next).then(()=>{replaced=true})
 await Promise.resolve();expect(replaced).toBe(false)
 release({data:f.job('DONE'),error:null});await drive;await replacement
 expect(rpc).toHaveBeenCalledTimes(2);expect(readFrozenAnalysisRequest(s.actor,s.scope).pending).toEqual(next)
 await expect(readFrozenQuantity({rpc},s,done())).rejects.toThrow();expect(rpc).toHaveBeenCalledTimes(2)
})
it('retires an answer if storage is changed outside the lock while its request is in flight',async()=>{
 const rpc=vi.fn(async()=>{
  localStorage.setItem(frozenAnalysisRequestKey(s.actor,s.scope),JSON.stringify({...s.request,id:'00000000-0000-4000-8000-000000000999'}))
  return{data:f.job('DONE'),error:null}
 }),onStatus=vi.fn()
 await expect(driveFrozenQuantity({rpc},s,{onStatus})).rejects.toThrow();expect(onStatus).not.toHaveBeenCalled()
})
it('backs off for an active worker and cancels before reading another status',async()=>{
 let stopped=false;const rpc=vi.fn(async()=>({data:f.job('RUNNING',{worker_active:true,targets_done_in_stage:0}),error:null})),sleep=vi.fn(async()=>{stopped=true})
 expect(await driveFrozenQuantity({rpc},s,{sleep,aborted:()=>stopped})).toBeNull();expect(rpc).toHaveBeenCalledOnce();expect(sleep).toHaveBeenCalledWith(2000)
})
it('retains exact request after lost response and denies all RPC when locks are unavailable',async()=>{
 const bytes=localStorage.getItem(frozenAnalysisRequestKey(s.actor,s.scope)),rpc=vi.fn().mockRejectedValueOnce(Error('reply lost'))
 await expect(driveFrozenQuantity({rpc},s,{})).rejects.toThrow('reply lost');expect(localStorage.getItem(frozenAnalysisRequestKey(s.actor,s.scope))).toBe(bytes)
 vi.stubGlobal('navigator',{});await expect(driveFrozenQuantity({rpc},s,{})).rejects.toThrow('dikunci');expect(rpc).toHaveBeenCalledOnce()
})

it('hands an admitted v2 result to checked cutting with exact identity, target and original microseconds',async()=>{
 const rpc=vi.fn(route),v=await readFrozenQuantity({rpc},s,done()),target=v.header.labels[0].key
 expect(frozenQuantityCuttingContext(s,v,target)).toEqual({kind:'STAGED',runId:f.runId,targetKey:target,identityHash:f.identityHash,dataAsOf:f.reference.captured_at})
 expect(()=>frozenQuantityCuttingContext(s,structuredClone(v),target)).toThrow()
 expect(()=>frozenQuantityCuttingContext(s,v,'00000000-0000-4000-8000-000000000999:00000000-0000-4000-8000-000000000888')).toThrow()
 localStorage.setItem(frozenAnalysisRequestKey(s.actor,s.scope),JSON.stringify({...s.request,id:crypto.randomUUID()}))
 expect(()=>frozenQuantityCuttingContext(s,v,target)).toThrow()
 expect(rpc).toHaveBeenCalledTimes(2)
})
