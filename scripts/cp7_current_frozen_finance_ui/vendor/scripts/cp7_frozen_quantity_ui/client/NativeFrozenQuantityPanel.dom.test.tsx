// @vitest-environment jsdom
import {act,StrictMode} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeFrozenQuantityPanel from './NativeFrozenQuantityPanel'
import {recoveryIdentity} from '../../../tests/fixtures/productionRecovery'
import {stagedRun} from '../../../tests/fixtures/nativeAnalysisPages'
import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey,persistFrozenAnalysisRequest,readFrozenAnalysisRequest,type FrozenAnalysisRequest} from '../../cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'

const state=vi.hoisted(()=>({auth:null as any}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../../src/auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('../../../src/lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,f:Awaited<ReturnType<typeof stagedRun>>
const scope='frozen-quantity:cp6-disposable:actor-1',start=vi.fn(),end=vi.fn(),close=vi.fn()
const tick=()=>new Promise<void>(resolve=>setTimeout(resolve,0))
async function until(done:()=>boolean){const from=Date.now();while(!done()&&Date.now()-from<3000)await act(async()=>{await tick()});expect(done()).toBe(true)}
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
const click=async(label:string)=>{expect(button(label)).toBeTruthy();await act(async()=>{button(label).click();await tick()})}
const pointer=()=>readFrozenAnalysisRequest(f.actor,scope)
const stored=()=>localStorage.getItem(frozenAnalysisRequestKey(f.actor,scope))
const request=():FrozenAnalysisRequest=>({id:f.pageSet.request_id,actor:f.actor,q:f.query,method:FROZEN_ANALYSIS_REQUEST})
const render=async(query=f.query,strict=false)=>act(async()=>{
 const panel=<NativeFrozenQuantityPanel query={query} onSourceReadStart={start} onSourceReadEnd={end} onClose={close}/>
 root.render(strict?<StrictMode>{panel}</StrictMode>:panel);await tick()
})
const search=async(term:string)=>act(async()=>{
 const input=container.querySelector('input[type=search]')!,setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!
 setter.call(input,term);input.dispatchEvent(new Event('input',{bubbles:true}));await tick()
})
function server(){return async(name:string,args:{p_request:string;p_index:number;p_query:typeof f.query})=>{
 if(name==='erp_cp7_request_bounded_staged_analysis_v2'){
  if(f.pageSet.request_id!==args.p_request)f=await stagedRun({targets:1200,pageSizes:[500,450,250],requestId:args.p_request})
  return{data:f.job('DONE'),error:null}
 }
 if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:f.pageSet,error:null}
 if(name==='erp_cp7_read_staged_analysis_page_v1')return{data:f.page(args.p_index),error:null}
 if(name==='erp_cp7_check_staged_analysis_source_v1')return{data:{source_state:'ARCHIVED_STALE',checked_at:'2026-10-25T19:00:00.123456Z'},error:null}
 throw Error('unexpected RPC '+name)
}}
beforeEach(async()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();start.mockReset();end.mockReset();close.mockReset()
 const tails=new Map<string,Promise<void>>()
 vi.stubGlobal('navigator',{locks:{request:async(name:string,_options:unknown,fn:()=>unknown)=>{
  const prior=tails.get(name)??Promise.resolve();let release!:()=>void
  const held=new Promise<void>(resolve=>{release=resolve}),tail=prior.then(()=>held);tails.set(name,tail)
  await prior;try{return await fn()}finally{release();if(tails.get(name)===tail)tails.delete(name)}
 }}})
 f=await stagedRun({targets:1200,pageSizes:[500,450,250]})
 const auth=structuredClone(recoveryIdentity);Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(auth.identity.profile,{authUserId:f.actor,rowVersion:1,roleRowVersion:1})
 auth.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=auth
 container=document.createElement('div');document.body.append(container);root=createRoot(container);client.rpc.mockImplementation(server())
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks();vi.unstubAllGlobals()})

it('persists before v2 request, shows exact full-run totals, pages and UNKNOWN facts',async()=>{
 const answer=server();client.rpc.mockImplementation(async(name,args)=>{
  if(name==='erp_cp7_request_bounded_staged_analysis_v2')expect(pointer().pending).toMatchObject({id:args.p_request,q:args.p_query,method:FROZEN_ANALYSIS_REQUEST,actor:f.actor})
  return answer(name,args)
 })
 await render();await until(()=>container.querySelectorAll('[data-quantity-target]').length===50)
 expect(container.textContent).toContain('1.200 target');expect(container.textContent).toContain('Target 1–500 dari 1.200')
 const original=stored(),row=container.querySelector('[data-quantity-target]')!
 expect(row.querySelector('[data-label="Produksi baru layak"]')?.textContent).toContain('Belum diketahui')
 expect(row.querySelector('[data-label="Stok fisik"]')?.textContent).toContain('76')
 expect(row.querySelector('[data-label="Kurang sesudah pembagian global"]')?.textContent).toContain('0')
 await click('50 saran berikutnya');expect(container.textContent).toContain('Saran 51–100')
 await click('Sumber berikutnya');await until(()=>container.textContent!.includes('Target 501–950 dari 1.200'))
 expect(container.querySelectorAll('[data-quantity-target]')).toHaveLength(50);expect(stored()).toBe(original)
 await click('Periksa sumber kebutuhan');expect(container.textContent).toContain('sumber sudah berubah; hitung kebutuhan terbaru.')
 expect(stored()).toBe(original);expect(container.querySelectorAll('[data-quantity-target]')).toHaveLength(50)
 expect(client.rpc.mock.calls.some(([name])=>name==='erp_cp7_request_bounded_staged_analysis_v1'||name==='erp_cp7_capture_netting_v1')).toBe(false)
 expect(start).toHaveBeenCalledOnce();expect(end).toHaveBeenCalledOnce()
})
it('reopens a lost-response UUID through v2 with its original period and leaves the durable record intact',async()=>{
 client.rpc.mockRejectedValue(Error('reply lost'));await render();await until(()=>Boolean(container.querySelector('[role=alert]')))
 const first=structuredClone(client.rpc.mock.calls[0]),bytes=stored(),old=pointer().pending!
 expect(button('Hitung kebutuhan terbaru').disabled).toBe(true)
 await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockImplementation(server())
 await render({...f.query,from_date:'2026-01-01'});await until(()=>container.querySelectorAll('[data-quantity-target]').length===50)
 const calls=client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_request_bounded_staged_analysis_v2')
 expect(calls).toHaveLength(3);expect(calls[1]).toEqual(first);expect(calls[2]).toEqual(first)
 expect(stored()).toBe(bytes);expect(pointer().pending).toEqual(old)
})
it('keeps a StrictMode double mount on one durable UUID with no losing request sent',async()=>{
 await render(f.query,true);await until(()=>container.querySelectorAll('[data-quantity-target]').length===50)
 const ids=client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_request_bounded_staged_analysis_v2').map(([,args])=>args.p_request)
 expect(new Set(ids).size).toBe(1);expect(ids[0]).toBe(pointer().pending!.id);expect(start).toHaveBeenCalledOnce();expect(end).toHaveBeenCalledOnce()
})
it.each(['runtime','permission','identity'])('refuses %s mismatch before storage and RPC',async field=>{
 if(field==='runtime')state.auth.runtime.mode='UAT_AUTH_SIMULATION'
 if(field==='permission')state.auth.identity.permissions=[]
 if(field==='identity')state.auth.identity.status='ANONYMOUS'
 await render();expect(container.textContent).toBe('');expect(localStorage.length).toBe(0);expect(client.rpc).not.toHaveBeenCalled()
})
it('preserves corrupt recovery bytes and never generates a replacement request',async()=>{
 const key=frozenAnalysisRequestKey(f.actor,scope);localStorage.setItem(key,'{bad')
 await render();expect(container.querySelector('[role=alert]')).toBeTruthy();expect(client.rpc).not.toHaveBeenCalled();expect(localStorage.getItem(key)).toBe('{bad')
 expect(button('Hitung kebutuhan terbaru').disabled).toBe(true)
})
it('fails closed if persistence fails or cross-tab locks are unavailable',async()=>{
 vi.stubGlobal('navigator',{});await render();await until(()=>Boolean(container.querySelector('[role=alert]')))
 expect(localStorage.length).toBe(0);expect(client.rpc).not.toHaveBeenCalled()
})
it('retires a held request after real StorageEvent and keeps the other-tab UUID',async()=>{
 await persistFrozenAnalysisRequest(f.actor,scope,request());let release!:(v:unknown)=>void
 client.rpc.mockImplementation(()=>new Promise(r=>{release=r}));await render();await until(()=>Boolean(release))
 const next={...request(),id:crypto.randomUUID()},key=frozenAnalysisRequestKey(f.actor,scope);localStorage.setItem(key,JSON.stringify(next))
 await act(async()=>{dispatchEvent(new StorageEvent('storage',{key}));release({data:f.job('DONE'),error:null});await tick()})
 expect(container.querySelector('table')).toBeNull();expect(pointer().pending).toEqual(next);expect(end).toHaveBeenCalledOnce()
 expect(client.rpc).toHaveBeenCalledOnce()
})
it('retires a held page after current identity loses read permission',async()=>{
 const normal=server();let release!:(v:unknown)=>void
 client.rpc.mockImplementation((name,args)=>name==='erp_cp7_read_staged_analysis_page_v1'?new Promise(r=>{release=r}):normal(name,args))
 await render();await until(()=>Boolean(release));const bytes=stored()
 state.auth.identity.permissions=[];await render();await act(async()=>{release({data:f.page(0),error:null});await tick()})
 expect(container.textContent).toBe('');expect(stored()).toBe(bytes);expect(end).toHaveBeenCalledOnce()
})
it('clears all rendered quantities and candidate access after a real-shaped access refusal',async()=>{
 await render();await until(()=>container.querySelectorAll('[data-quantity-target]').length===50);const bytes=stored()
 client.rpc.mockResolvedValue({data:null,error:{status:403,code:'42501',message:'CP7_ACCESS_DENIED'}})
 await click('Periksa sumber kebutuhan');expect(container.querySelector('table')).toBeNull();expect(container.querySelector('input[type=search]')).toBeNull()
 expect(stored()).toBe(bytes);expect(container.querySelector('[role=alert]')).toBeTruthy()
})
it('searches every product label and passes the same v2 request/target/access to the actual candidate panel',async()=>{
 await render();await until(()=>container.querySelectorAll('[data-quantity-target]').length===50)
 await search('SKU-1199');expect(container.textContent).toContain('1 produk ditemukan dalam seluruh hasil perhitungan')
 client.rpc.mockResolvedValue({data:null,error:{status:403,code:'42501',message:'CP7_ACCESS_DENIED'}})
 await click('Lihat pembanding SKU-1199');await until(()=>container.querySelector('table')===null)
 const last=client.rpc.mock.calls.at(-1)!;expect(last[0]).toBe('erp_cp7_read_product_analog_candidates_v2')
 expect(last[1]).toEqual({p_request:pointer().pending!.id,p_target:f.headerDoc.product_labels.find(p=>p.sku==='SKU-1199')!.target_key,p_offset:0,p_limit:50,p_access:f.pageSet.access_epoch})
 expect(pointer().pending?.method).toBe(FROZEN_ANALYSIS_REQUEST)
})
it('makes all prefix matches reachable while placing the exact SKU first',async()=>{
 await render();await until(()=>container.querySelectorAll('[data-quantity-target]').length===50);await search('sku-11')
 expect(container.textContent).toContain('111 produk ditemukan');const choices=()=>[...container.querySelectorAll('[data-analog-choice]')]
 expect(choices()[0].textContent).toContain('SKU-11 ·');const seen=new Set<string>()
 while(true){for(const c of choices()){const key=c.getAttribute('data-analog-choice')!;expect(seen.has(key)).toBe(false);seen.add(key)}if(button('20 produk berikutnya').disabled)break;await click('20 produk berikutnya')}
 expect(seen.size).toBe(111);await search('SKU-1199');expect(choices()).toHaveLength(1);expect(button('20 produk sebelumnya').disabled).toBe(true)
})
it('permits a fresh UUID only after an explicit constructor refusal and never silently retries with another method',async()=>{
 client.rpc.mockResolvedValue({data:null,error:{code:'P0001',message:'CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE'}})
 await render();await until(()=>Boolean(container.querySelector('[role=alert]')));const first=pointer().pending!
 expect(button('Hitung kebutuhan terbaru').disabled).toBe(false);client.rpc.mockImplementation(server());await click('Hitung kebutuhan terbaru')
 await until(()=>container.querySelectorAll('[data-quantity-target]').length===50);expect(pointer().pending!.id).not.toBe(first.id);expect(pointer().pending!.method).toBe(first.method)
})
it('keeps previous result and UUID when explicit replacement cannot be persisted',async()=>{
 await render();await until(()=>container.querySelectorAll('[data-quantity-target]').length===50);const bytes=stored(),calls=client.rpc.mock.calls.length
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('quota')});await click('Hitung kebutuhan terbaru')
 expect(stored()).toBe(bytes);expect(client.rpc).toHaveBeenCalledTimes(calls);expect(container.querySelectorAll('[data-quantity-target]')).toHaveLength(50);expect(container.querySelector('[role=alert]')).toBeTruthy()
})
