// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeBoundedQuantityPanel from './NativeBoundedQuantityPanel'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {stagedRun} from '../tests/fixtures/nativeAnalysisPages'
import {BOUNDED_ANALYSIS_REQUEST,boundedAnalysisRequestKey,readBoundedAnalysisRequest,persistBoundedAnalysisRequest,type BoundedAnalysisRequest} from './nativeBoundedAnalysis'

const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
type Fixture=Awaited<ReturnType<typeof stagedRun>>
let root:Root,container:HTMLDivElement,f:Fixture
const scope='quantity:cp6-disposable:actor-1',start=vi.fn(),end=vi.fn(),close=vi.fn()
const macrotask=()=>new Promise<void>(resolve=>(globalThis as unknown as {setImmediate:(f:()=>void)=>void}).setImmediate(resolve))
async function until(done:()=>boolean){const from=Date.now();while(!done()&&Date.now()-from<10000)await act(async()=>{await macrotask()});expect(done()).toBe(true)}
beforeEach(async()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();start.mockClear();end.mockClear();close.mockClear()
 f=await stagedRun({targets:1200,pageSizes:[500,450,250]})
 const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:f.actor})
 a.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=a
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()})
const request=():BoundedAnalysisRequest=>({id:f.pageSet.request_id,q:f.query,method:BOUNDED_ANALYSIS_REQUEST})
const button=(text:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===text)!
async function click(text:string){expect(button(text)).toBeTruthy();await act(async()=>button(text).click())}
async function render(){await act(async()=>root.render(<NativeBoundedQuantityPanel query={f.query} onSourceReadStart={start} onSourceReadEnd={end} onClose={close}/>))}
function server(){return async(name:string,args:{p_request:string;p_index:number})=>{
 if(name==='erp_cp7_request_bounded_staged_analysis_v1'){f=await stagedRun({targets:1200,pageSizes:[500,450,250],requestId:args.p_request});return{data:f.job('DONE'),error:null}}
 if(name==='erp_cp7_get_staged_analysis_v1')return{data:f.job('DONE'),error:null}
 if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:f.pageSet,error:null}
 if(name==='erp_cp7_read_staged_analysis_page_v1')return{data:f.page(args.p_index),error:null}
 if(name==='erp_cp7_check_staged_analysis_source_v1')return{data:null,error:{status:403,message:'CP7_ACCESS_DENIED'}}
 throw Error('unexpected RPC '+name)
}}
it('shows server whole-run totals with only50 displayed suggestions and verifies every selected source page',async()=>{
 client.rpc.mockImplementation(server());await render();await until(()=>container.querySelectorAll('tbody tr').length===50)
 expect(container.textContent).toContain('1.200 target');expect(container.textContent).toContain('Target 1–500 dari 1.200')
 const original=readBoundedAnalysisRequest(scope).pending;expect(original?.method).toBe(BOUNDED_ANALYSIS_REQUEST)
 await click('50 saran berikutnya');expect(container.querySelectorAll('tbody tr')).toHaveLength(50);expect(container.textContent).toContain('Saran 51–100')
 await click('Sumber berikutnya');await until(()=>container.textContent!.includes('Target 501–950 dari 1.200'))
 expect(container.querySelectorAll('tbody tr')).toHaveLength(50);expect(container.textContent).toContain('1.200 target');expect(readBoundedAnalysisRequest(scope).pending).toEqual(original)
 expect(client.rpc.mock.calls.some(([name])=>name==='erp_cp7_capture_netting_v1')).toBe(false)
 await click('Periksa sumber kebutuhan');expect(container.querySelector('table')).toBeNull();expect(readBoundedAnalysisRequest(scope).pending).toEqual(original)
})
it('keeps an uncertain request across close and resumes the same method/query/UUID on retry',async()=>{
 client.rpc.mockResolvedValue({data:null,error:Error('reply lost')});await render();await until(()=>Boolean(container.querySelector('[role="alert"]')))
 const first=structuredClone(client.rpc.mock.calls[0]),held=readBoundedAnalysisRequest(scope).pending
 expect(held?.id).toBe(first[1].p_request);expect(button('Hitung kebutuhan terbaru').disabled).toBe(true)
 await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockImplementation(server());await render()
 // GET may report the actual committed result; it never issues another request.
 await until(()=>Boolean(container.querySelector('[role="alert"]')))
 await click('Buka perhitungan tersimpan');await until(()=>container.querySelectorAll('tbody tr').length===50)
 const retried=client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_request_bounded_staged_analysis_v1')
 expect(retried).toHaveLength(2);expect(retried[1]).toEqual(first);expect(readBoundedAnalysisRequest(scope).pending).toEqual(held)
})
it('ignores a held reply after cross-tab replacement without erasing the replacement',async()=>{
 const held=request();persistBoundedAnalysisRequest(scope,held)
 let release:(r:unknown)=>void=()=>{};client.rpc.mockImplementation(()=>new Promise(resolve=>release=resolve))
 await render();const changed={...held,id:crypto.randomUUID()};localStorage.setItem(boundedAnalysisRequestKey(scope),JSON.stringify(changed))
 await act(async()=>dispatchEvent(new StorageEvent('storage',{key:boundedAnalysisRequestKey(scope)})))
 await act(async()=>release({data:f.job('DONE'),error:null}))
 expect(container.querySelector('table')).toBeNull();expect(readBoundedAnalysisRequest(scope).pending).toEqual(changed)
})
it('permits an explicit new period only after a known constructor refusal, preserving the old request until replacement',async()=>{
 client.rpc.mockResolvedValue({data:null,error:{code:'P0001',message:'CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE'}})
 await render();await until(()=>Boolean(container.querySelector('[role="alert"]')))
 const first=readBoundedAnalysisRequest(scope).pending;expect(first).toBeTruthy();expect(button('Hitung kebutuhan terbaru').disabled).toBe(false)
 client.rpc.mockImplementation(server());await click('Hitung kebutuhan terbaru');await until(()=>container.querySelectorAll('tbody tr').length===50)
 expect(readBoundedAnalysisRequest(scope).pending?.id).not.toBe(first?.id)
})
