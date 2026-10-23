// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeInitialAnalysisPanel from './NativeInitialAnalysisPanel'
import ready from '../tests/fixtures/initialAnalysisReadyActual.json'
import running from '../tests/fixtures/initialAnalysisRunningActual.json'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
const open=vi.fn(),configure=vi.fn(),master=vi.fn(),denied=vi.fn()
function auth(actor=running.actor,role='OWNER'){
 const a=structuredClone(recoveryIdentity)
 Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'})
 Object.assign(a.identity.profile,{id:actor,authUserId:actor,role,rowVersion:'1',roleRowVersion:'1'})
 a.identity.permissions.push('master.product.view','warehouse.stock.view','sales.invoice.view')
 state.auth=a
}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});auth();client.rpc.mockReset();for(const f of[open,configure,master,denied])f.mockReset();container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks();vi.useRealTimers()})
async function render(key='1'){await act(async()=>root.render(<NativeInitialAnalysisPanel sourceKey={key} onOpen={open} onConfigure={configure} onOpenMaster={master} onAuthorityLost={denied}/>))}
async function click(name:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===name);expect(b).toBeTruthy();await act(async()=>b!.click())}
const reply=(data:unknown)=>({data,error:null})
const missing=(products=false)=>({...ready,state:'NOT_READY',readiness:{...ready.readiness,ready:false,eligible_targets:0,
 reasons:[products?'NO_ACTIVE_PRODUCTS':'PLANNING_PROFILE_INCOMPLETE'],...(products?{products_total:0,active_products:0,candidates:[]}:{candidates:ready.readiness.candidates.map(p=>({...p,profile_ready:false}))})}})
it('shows missing data and opens the supplied Master action without requesting analysis',async()=>{
 client.rpc.mockResolvedValue(reply(missing(true)));await render()
 expect(container.textContent).toContain('Belum ada produk aktif.');await click('Lengkapi produk di Data Master');expect(master).toHaveBeenCalledTimes(1)
 expect(client.rpc.mock.calls).toEqual([['erp_cp7_request_staged_analysis_v1',{p_query:{initial_auto:'STATUS'},p_request:null}]])
})
it('opens the real target form input with server product identity and period',async()=>{
 client.rpc.mockResolvedValue(reply(missing()));await render();await click('Lengkapi target LOCAL-INITIAL')
 expect(configure.mock.calls[0]).toEqual([{rootId:ready.readiness.candidates[0].root_id,productId:ready.readiness.candidates[0].product_id,
  sizeId:ready.readiness.candidates[0].size_id,sku:'LOCAL-INITIAL',productName:'Controlled initial analysis',profileReady:false},ready.query])
 expect(client.rpc).toHaveBeenCalledTimes(1)
})
it('starts automatically only when READY, with a conditional null-UUID ensure, and opens that job',async()=>{
 client.rpc.mockResolvedValueOnce(reply(ready)).mockResolvedValueOnce(reply(running));await render()
 expect(client.rpc.mock.calls).toEqual([['erp_cp7_request_staged_analysis_v1',{p_query:{initial_auto:'STATUS'},p_request:null}],
  ['erp_cp7_request_staged_analysis_v1',{p_query:{initial_auto:'ENSURE'},p_request:null}]])
 expect(container.textContent).toContain('Analisis sudah tersimpan.');expect(container.textContent).not.toContain('Server sedang memproses; halaman boleh ditutup.')
 await click('Buka analisis awal yang berjalan');expect(open.mock.calls[0][0].job.requestId).toBe(running.job.request_id)
})
it('remounts the same running server job with STATUS and never another ensure',async()=>{
 client.rpc.mockResolvedValue(reply(running));await render();await act(async()=>root.unmount());root=createRoot(container);await render()
 expect(client.rpc.mock.calls.every(([,args])=>args.p_query.initial_auto==='STATUS')).toBe(true)
 expect(client.rpc).toHaveBeenCalledTimes(2);await click('Buka analisis awal yang berjalan');expect(open.mock.calls[0][0].job.requestId).toBe(running.job.request_id)
})
it('recovers an ensure reply lost after server commit by reading the existing UUID',async()=>{
 client.rpc.mockResolvedValueOnce(reply(ready)).mockResolvedValueOnce({data:null,error:Error('reply lost')});await render()
 expect(container.textContent).toContain('reply lost');expect(container.textContent).not.toContain('Buka analisis awal yang berjalan')
 client.rpc.mockResolvedValue(reply(running));await act(async()=>window.dispatchEvent(new Event('focus')))
 expect(client.rpc.mock.calls.filter(([,args])=>args.p_query.initial_auto==='ENSURE')).toHaveLength(1)
 await click('Buka analisis awal yang berjalan');expect(open.mock.calls[0][0].job.requestId).toBe(running.job.request_id)
})
it.each([401,403])('clears facts on current %i and suppresses automatic reads until an explicit retry',async status=>{
 client.rpc.mockResolvedValue(reply(running));await render()
 client.rpc.mockResolvedValue({data:null,error:{message:'access refused',status,code:status===403?'42501':'PGRST301'}})
 await act(async()=>window.dispatchEvent(new Event('focus')));expect(container.textContent).not.toContain('Buka analisis awal yang berjalan');expect(denied).toHaveBeenCalledTimes(1)
 const n=client.rpc.mock.calls.length;await act(async()=>window.dispatchEvent(new Event('focus')));expect(client.rpc).toHaveBeenCalledTimes(n)
 client.rpc.mockResolvedValue(reply(running));await click('Periksa kesiapan lagi');expect(container.textContent).toContain('Buka analisis awal yang berjalan')
})
it('drops a late response after a newer source read',async()=>{
 let release:(r:unknown)=>void=()=>{}
 client.rpc.mockImplementationOnce(()=>new Promise(r=>{release=r})).mockResolvedValue(reply(missing()))
 await render();await act(async()=>window.dispatchEvent(new Event('focus')));expect(container.textContent).toContain('Belum ada produk aktif dengan aturan')
 await act(async()=>release(reply(running)));expect(container.textContent).not.toContain('Buka analisis awal yang berjalan');expect(client.rpc).toHaveBeenCalledTimes(2)
})
it('hides facts immediately when the source binding changes and ignores the old read',async()=>{
 client.rpc.mockResolvedValueOnce(reply(running));await render()
 let release:(r:unknown)=>void=()=>{};client.rpc.mockImplementationOnce(()=>new Promise(r=>{release=r}));await render('2')
 expect(container.textContent).not.toContain('Buka analisis awal yang berjalan');await act(async()=>release(reply(missing())))
 expect(container.textContent).toContain('Belum ada produk aktif dengan aturan')
})
it('does not show owner automation to another role or accept another actor reply',async()=>{
 auth(running.actor,'STAFF');await render();expect(container.textContent).toBe('');expect(client.rpc).not.toHaveBeenCalled()
 auth('99999999-1111-4111-8111-111111111111');client.rpc.mockResolvedValue(reply(running));await render()
 expect(container.querySelector('[role=alert]')).toBeTruthy();expect(container.textContent).not.toContain('Buka analisis awal yang berjalan')
})
it('polls progress without starting a second job',async()=>{
 vi.useFakeTimers();client.rpc.mockResolvedValue(reply(running));await render()
 await act(async()=>{await vi.advanceTimersByTimeAsync(5000)})
 expect(client.rpc).toHaveBeenCalledTimes(2);expect(client.rpc.mock.calls.every(([,args])=>args.p_query.initial_auto==='STATUS')).toBe(true)
})
it('keeps the server result available when the parent holds another pending analysis',async()=>{
 open.mockImplementation(()=>{throw Error('Selesaikan analisis bertahap yang tersimpan terlebih dahulu.')})
 client.rpc.mockResolvedValue(reply(running));await render();await click('Buka analisis awal yang berjalan')
 expect(container.textContent).toContain('Selesaikan analisis bertahap yang tersimpan');expect(client.rpc).toHaveBeenCalledTimes(1)
})
