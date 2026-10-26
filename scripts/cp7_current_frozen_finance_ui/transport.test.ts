// @vitest-environment jsdom
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {bindFrozenFinanceTransport,OPERATIONAL_RPC,FINANCE_RPC} from './transport'
import {FROZEN_ANALYSIS_REQUEST,persistFrozenAnalysisRequest,readFrozenAnalysisRequest,frozenAnalysisRequestKey,requestFrozenAnalysis} from './vendor/scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
import {driveFrozenQuantity,readFrozenQuantity,readFrozenQuantityPage,readFrozenQuantityFinanceStatus,type FrozenQuantitySession} from './vendor/scripts/cp7_frozen_quantity_ui/client/nativeFrozenQuantity'
import {stagedRun} from './vendor/tests/fixtures/nativeAnalysisPages'
import {frozenFinanceFixture} from './vendor/tests/fixtures/frozenAnalysisFinance'

let f:Awaited<ReturnType<typeof stagedRun>>,s:FrozenQuantitySession
beforeEach(async()=>{
  const tails=new Map<string,Promise<void>>()
  vi.stubGlobal('navigator',{locks:{request:async(name:string,_options:unknown,fn:()=>unknown)=>{
    const prior=tails.get(name)??Promise.resolve();let release!:()=>void
    const held=new Promise<void>(resolve=>{release=resolve}),tail=prior.then(()=>held);tails.set(name,tail)
    await prior;try{return await fn()}finally{release();if(tails.get(name)===tail)tails.delete(name)}
  }}})
  f=await stagedRun({targets:120,pageSizes:[60,60]})
  s={actor:f.actor,scope:'A-finance',request:{id:f.pageSet.request_id,actor:f.actor,q:f.query,method:FROZEN_ANALYSIS_REQUEST,finance:'STAGED'}}
  await persistFrozenAnalysisRequest(s.actor,s.scope,s.request)
})
afterEach(()=>{localStorage.clear();vi.restoreAllMocks();vi.unstubAllGlobals()})
const durable=()=>localStorage.getItem(frozenAnalysisRequestKey(s.actor,s.scope))
const body=()=>({p_request:s.request.id,p_query:{...s.request.q,finance_mode:'STAGED'}})

it('routes persisted STAGED requests, reopen and DONE revalidation to finance before reading pages',async()=>{
  const bytes=durable(),raw=f.job('DONE',{finance_capture:frozenFinanceFixture(f)})
  const rpc=vi.fn(async(name:string,args:Record<string,unknown>)=>{
    if(name===FINANCE_RPC){expect(args).toEqual(body());return{data:raw,error:null}}
    if(name==='erp_cp7_get_staged_analysis_v1')return{data:raw,error:null}
    if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:f.pageSet,error:null}
    if(name==='erp_cp7_read_staged_analysis_page_v1')return{data:f.page(Number(args.p_index)),error:null}
    throw Error('unexpected route '+name)
  }),client=bindFrozenFinanceTransport({rpc})
  await requestFrozenAnalysis(client,s.actor,s.scope)
  const job=await driveFrozenQuantity(client,s,{})
  const reopened=await driveFrozenQuantity(client,s,{})
  expect(reopened?.requestId).toBe(job?.requestId)
  const source=await readFrozenQuantity(client,s,job!)
  await readFrozenQuantityPage(client,s,source,1)
  await readFrozenQuantityFinanceStatus(client,s,source)
  expect(rpc.mock.calls.map(x=>x[0])).toEqual([FINANCE_RPC,FINANCE_RPC,FINANCE_RPC,FINANCE_RPC,'erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1','erp_cp7_get_staged_analysis_v1'])
  expect(durable()).toBe(bytes)
})
it('retains the UUID, mode and exact bytes after a lost finance response and retries only that route',async()=>{
  const bytes=durable(),rpc=vi.fn().mockRejectedValueOnce(Error('reply lost')).mockResolvedValue({data:f.job('DONE',{finance_capture:frozenFinanceFixture(f)}),error:null}),client=bindFrozenFinanceTransport({rpc})
  await expect(driveFrozenQuantity(client,s,{})).rejects.toThrow('reply lost')
  expect(durable()).toBe(bytes)
  await driveFrozenQuantity(client,s,{})
  expect(rpc.mock.calls).toEqual([[FINANCE_RPC,body()],[FINANCE_RPC,body()]])
  expect(readFrozenAnalysisRequest(s.actor,s.scope).pending).toEqual(s.request)
})
it.each([undefined,'DEFERRED'] as const)('keeps %s operational with no finance capture and leaves durable mode unchanged',async finance=>{
  localStorage.clear();s.request={...s.request};delete s.request.finance
  if(finance)s.request.finance=finance
  await persistFrozenAnalysisRequest(s.actor,s.scope,s.request)
  const bytes=durable(),rpc=vi.fn(async()=>({data:f.job('DONE'),error:null})),client=bindFrozenFinanceTransport({rpc})
  await driveFrozenQuantity(client,s,{})
  expect(rpc.mock.calls).toEqual([[OPERATIONAL_RPC,{p_request:s.request.id,p_query:s.request.q}]])
  expect(durable()).toBe(bytes)
})
it.each(['FORBIDDEN','AUTH_REQUIRED','CP7_ANALYSIS_REQUEST_CHANGED'])('preserves %s without switching methods or discarding the request',async message=>{
  const bytes=durable(),error={code:message,message},rpc=vi.fn(async()=>({data:null,error})),client=bindFrozenFinanceTransport({rpc})
  await expect(driveFrozenQuantity(client,s,{})).rejects.toMatchObject({message})
  expect(rpc.mock.calls).toEqual([[FINANCE_RPC,body()]])
  expect(durable()).toBe(bytes)
})
it.each([null,undefined,'AUTO','staged',0])('refuses an explicit invalid mode %s before any RPC',finance_mode=>{
  const rpc=vi.fn(),client=bindFrozenFinanceTransport({rpc})
  expect(()=>client.rpc(OPERATIONAL_RPC,{...body(),p_query:{...s.request.q,finance_mode}})).toThrow('permintaan tersimpan')
  expect(rpc).not.toHaveBeenCalled()
})
it('passes all nonrequest calls and their options unchanged, preserving receiver and identity',async()=>{
  const answer={data:null,error:null},rpc=vi.fn(function(this:unknown,..._args:unknown[]){expect(this).toBe(original);return Promise.resolve(answer)}),original={rpc,marker:17},client=bindFrozenFinanceTransport(original)
  const args=Object.freeze({p_request:s.request.id}),options=Object.freeze({head:false})
  expect(bindFrozenFinanceTransport(original)).toBe(client)
  expect(await client.rpc('erp_cp7_get_staged_analysis_v1',args,options)).toBe(answer)
  expect(rpc.mock.calls[0]).toEqual(['erp_cp7_get_staged_analysis_v1',args,options])
  expect(rpc.mock.calls[0][1]).toBe(args);expect(client.marker).toBe(17)
})
it('does not mutate frozen payloads during explicit DEFERRED syntax conversion',()=>{
  const rpc=vi.fn(),client=bindFrozenFinanceTransport({rpc}),q=Object.freeze({...s.request.q,finance_mode:'DEFERRED'}),args=Object.freeze({p_request:s.request.id,p_query:q})
  client.rpc(OPERATIONAL_RPC,args)
  expect(args.p_query).toBe(q);expect(q.finance_mode).toBe('DEFERRED')
  expect(rpc.mock.calls[0]).toEqual([OPERATIONAL_RPC,{p_request:s.request.id,p_query:s.request.q}])
})
it('does not bypass the original cross-tab lock or durable-request checks',async()=>{
  const rpc=vi.fn(),client=bindFrozenFinanceTransport({rpc})
  localStorage.setItem(frozenAnalysisRequestKey(s.actor,s.scope),JSON.stringify({...s.request,finance:'DEFERRED'}))
  await expect(driveFrozenQuantity(client,s,{})).rejects.toThrow()
  expect(rpc).not.toHaveBeenCalled()
})
