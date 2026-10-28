// @vitest-environment jsdom
// Controlled host integration. Real finance component and parsers; no Auth/DB credit.
import {act,StrictMode} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import Panel from './Panel'
import {PROGRESS_RPC} from './reader'
import {progressFixture} from './progressFixture'
import {recoveryIdentity} from './vendor/tests/fixtures/productionRecovery'
import {parseStagedJob} from './vendor/src/nativeStagedJob'
import {parseAnalysisPageSet,parseAnalysisHeader} from './vendor/src/nativeAnalysisPages'
import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey} from './vendor/scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'

const state=vi.hoisted(()=>({auth:null as any,session:null as any,source:null as any,lost:vi.fn()}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./vendor/src/auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./client',()=>({getUatSupabaseClient:()=>client}))
vi.mock('./vendor/scripts/cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel',()=>({default:({renderFinance}:any)=>renderFinance(state.session,state.source,state.lost)}))
let root:Root,container:HTMLDivElement,f:Awaited<ReturnType<typeof progressFixture>>
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve()}
const idle=()=>{}
const render=async(strict=false)=>act(async()=>{
 const panel=<Panel query={f.source.query} onSourceReadStart={idle} onSourceReadEnd={idle} onClose={idle}/>
 root.render(strict?<StrictMode>{panel}</StrictMode>:panel);await flush()
})
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
const click=async(label:string)=>act(async()=>{expect(button(label)).toBeTruthy();button(label).click();await flush()})
beforeEach(async()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();state.lost.mockReset()
 f=await progressFixture();state.auth=structuredClone(recoveryIdentity);state.auth.runtime.mode='DISPOSABLE_TEST';state.auth.identity.permissions.push('finance.reports.view')
 state.session={actor:f.source.actor,scope:'controlled-current-progress',request:{id:f.request.id,actor:f.source.actor,q:f.request.q,method:FROZEN_ANALYSIS_REQUEST,finance:'STAGED'}}
 localStorage.setItem(frozenAnalysisRequestKey(state.session.actor,state.session.scope),JSON.stringify(state.session.request))
 const set=await parseAnalysisPageSet(f.source.pageSet,f.source.pageSet.run_id,f.request.id)
 const header=await parseAnalysisHeader(set,f.request.q,f.source.actor,{ownerReports:false,preflight:false})
 state.source={job:parseStagedJob(f.wire.status,f.request.id,f.request),staged:{kind:'STAGED',set,header}}
 client.rpc.mockResolvedValue({data:f.wire,error:null});vi.useFakeTimers()
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();expect(vi.getTimerCount()).toBe(0);vi.useRealTimers();localStorage.clear();vi.restoreAllMocks()})

it('survives StrictMode cleanup with one active shared read and no early financial figures',async()=>{
 await render(true)
 expect(client.rpc.mock.calls).toEqual([[PROGRESS_RPC,{p_request:f.request.id}]])
 expect(container.querySelector('[data-combined-state]')?.getAttribute('data-combined-state')).toBe('RUNNING')
 expect(container.textContent).toContain('jumlah akhir belum diketahui')
 expect(container.querySelectorAll('[data-finance-metric]')).toHaveLength(0)
})
it('shows official figures only after the real finance component reads READY and then stops polling',async()=>{
 await render();const ready=await progressFixture(true);client.rpc.mockResolvedValue({data:ready.wire,error:null})
 await act(async()=>{await vi.advanceTimersByTimeAsync(5000);await flush()})
 expect(client.rpc).toHaveBeenCalledTimes(2)
 expect(container.querySelector('[data-combined-state]')?.getAttribute('data-combined-state')).toBe('COMPLETED')
 expect(container.querySelectorAll('[data-finance-metric]')).toHaveLength(ready.wire.status.finance_capture.result.metrics.length)
 expect(container.textContent).toContain('Rp9.007.199.254.740.993,01')
 await act(async()=>{await vi.advanceTimersByTimeAsync(60000);await flush()});expect(client.rpc).toHaveBeenCalledTimes(2)
})
it('reopens the same durable UUID without enqueueing, advancing or changing its stored payload',async()=>{
 const key=frozenAnalysisRequestKey(state.session.actor,state.session.scope),before=localStorage.getItem(key)
 await render();await act(async()=>root.unmount());root=createRoot(container);await render()
 expect(client.rpc.mock.calls).toEqual([[PROGRESS_RPC,{p_request:f.request.id}],[PROGRESS_RPC,{p_request:f.request.id}]])
 expect(localStorage.getItem(key)).toBe(before)
})
it('stops after a lost response and permits a read-only retry on the same job',async()=>{
 client.rpc.mockRejectedValueOnce(Error('reply lost'));await render()
 expect(container.textContent).toContain('Status terbaru belum dapat dipastikan')
 await act(async()=>{await vi.advanceTimersByTimeAsync(60000);await flush()});expect(client.rpc).toHaveBeenCalledTimes(1)
 await click('Muat ulang status keuangan')
 expect(client.rpc.mock.calls).toEqual([[PROGRESS_RPC,{p_request:f.request.id}],[PROGRESS_RPC,{p_request:f.request.id}]])
 expect(container.querySelector('[data-combined-state]')).not.toBeNull()
})
it('notifies the owning production panel and retires progress when the current server ACL refuses access',async()=>{
 await render();client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'CP7_ANALYSIS_JOB_UNAVAILABLE'}})
 await click('Periksa kemajuan pekerjaan yang sama')
 expect(state.lost).toHaveBeenCalledTimes(1);expect(container.querySelector('[data-combined-state]')).toBeNull()
 expect(container.textContent).toContain('Status terbaru belum dapat dipastikan')
})
it('hides existing money immediately on local permission loss and rechecks the current server status',async()=>{
 const ready=await progressFixture(true);client.rpc.mockResolvedValue({data:ready.wire,error:null});await render()
 expect(container.querySelectorAll('[data-finance-metric]').length).toBeGreaterThan(0)
 state.auth.identity.permissions=[]
 const revoked=structuredClone(f.wire);revoked.status.finance_capture={...revoked.status.finance_capture,state:'ACCESS_REVOKED',capture:null,result:null};revoked.finance=null as any
 client.rpc.mockResolvedValue({data:revoked,error:null});await render()
 expect(container.querySelectorAll('[data-finance-metric]')).toHaveLength(0);expect(client.rpc).toHaveBeenCalledTimes(2)
})
it('retires an unresolved read when the panel closes and does not poll from its late answer',async()=>{
 let release!:(v:unknown)=>void;client.rpc.mockImplementation(()=>new Promise(resolve=>{release=resolve}))
 await render();expect(client.rpc).toHaveBeenCalledTimes(1)
 await act(async()=>{root.render(null);await flush();release({data:f.wire,error:null});await flush()})
 expect(container.textContent).toBe('');expect(vi.getTimerCount()).toBe(0)
})
it('checks an idle financial capture through GET on the same durable request',async()=>{
 f.wire.observed_at='2026-10-07T10:06:00Z';await render()
 expect(container.textContent).toContain('Belum ada aktivitas keuangan baru')
 const key=frozenAnalysisRequestKey(state.session.actor,state.session.scope),before=localStorage.getItem(key)
 f.wire.finance.last_activity_at='2026-10-07T10:05:30Z'
 await click('Periksa kemajuan pekerjaan yang sama')
 expect(container.textContent).not.toContain('Belum ada aktivitas keuangan baru')
 expect(client.rpc.mock.calls).toEqual([[PROGRESS_RPC,{p_request:f.request.id}],[PROGRESS_RPC,{p_request:f.request.id}]])
 expect(localStorage.getItem(key)).toBe(before)
 expect(container.querySelectorAll('[data-finance-metric]')).toHaveLength(0)
})
