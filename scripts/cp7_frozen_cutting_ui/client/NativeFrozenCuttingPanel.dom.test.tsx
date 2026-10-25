// @vitest-environment jsdom
// Controlled RPC/identity; actual shared quantity, form and recovery components.
// These tests do not qualify Native feasibility or a physical cutting order.
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeFrozenCuttingPanel from './NativeFrozenCuttingPanel'
import NativeFrozenQuantityPanel from '../../cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel'
import {recoveryIdentity} from '../../../tests/fixtures/productionRecovery'
import {stagedRun} from '../../../tests/fixtures/nativeAnalysisPages'
import * as plan from '../../../tests/fixtures/nativePlan'
import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey,persistFrozenAnalysisRequest,readFrozenAnalysisRequest} from '../../cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
import {productionKey,readProductionRecovery} from '../../../src/productionRecovery'
const state=vi.hoisted(()=>({auth:null as any}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../../src/auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('../../../src/lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,f:Awaited<ReturnType<typeof stagedRun>>
const scope='frozen-quantity:cp6-disposable:actor-1',productionScope='cp6-disposable:actor-1',start=vi.fn(),end=vi.fn(),close=vi.fn()
const tick=()=>new Promise<void>(r=>setTimeout(r,0))
async function until(done:()=>boolean){const at=Date.now();while(!done()&&Date.now()-at<3000)await act(async()=>{await tick()});expect(done()).toBe(true)}
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
async function click(label:string){expect(button(label)).toBeTruthy();await act(async()=>{button(label).click();await tick()})}
async function render(quantityOnly=false){await act(async()=>{const C=quantityOnly?NativeFrozenQuantityPanel:NativeFrozenCuttingPanel;root.render(<C query={f.query} onSourceReadStart={start} onSourceReadEnd={end} onClose={close}/>);await tick()})}
const target=()=>f.headerDoc.product_labels[0].target_key as string
const request=()=>readFrozenAnalysisRequest(f.actor,scope).pending!
const bytes=()=>localStorage.getItem(frozenAnalysisRequestKey(f.actor,scope))
function options(){const o=plan.stagedOptions(),r=f.original.analysis.recommendations[0];return{...o,actor_scope_id:f.actor,run_id:f.runId,target_key:target(),identity_hash:f.identityHash,data_as_of:f.reference.captured_at,size_id:target().split(':')[1],product_sku:f.headerDoc.product_labels[0].sku,needed_pcs:r.q_conditional.value,available_fg_pcs:r.actual_fg.value}}
async function normal(name:string,args:any){
 if(name==='erp_cp7_request_bounded_staged_analysis_v2'){expect(args.p_request).toBe(request().id);expect(args.p_query).toEqual(f.query);return{data:f.job('DONE'),error:null}}
 if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:f.pageSet,error:null}
 if(name==='erp_cp7_read_staged_analysis_page_v1')return{data:f.page(args.p_index),error:null}
 if(name==='erp_cp7_get_plan_options_v2')return{data:options(),error:null}
 if(name==='erp_cp7_check_staged_analysis_source_v1')return{data:{source_state:'ARCHIVED_STALE',checked_at:'2026-10-25T19:00:00.123457Z'},error:null}
 throw Error('Unexpected RPC '+name)
}
beforeEach(async()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();start.mockReset();end.mockReset();close.mockReset()
 const tails=new Map<string,Promise<void>>()
 vi.stubGlobal('navigator',{locks:{request:async(name:string,options:{ifAvailable?:boolean},fn:(lock:unknown)=>unknown)=>{
  if(options.ifAvailable&&tails.has(name))return fn(null)
  const prior=tails.get(name)??Promise.resolve();let release!:()=>void;const held=new Promise<void>(r=>{release=r}),tail=prior.then(()=>held);tails.set(name,tail)
  await prior;try{return await fn({name})}finally{release();if(tails.get(name)===tail)tails.delete(name)}
 }}})
 f=await stagedRun({targets:1,capturedAt:'2026-10-07T09:00:00.123456Z'})
 await persistFrozenAnalysisRequest(f.actor,scope,{id:f.pageSet.request_id,actor:f.actor,q:f.query,method:FROZEN_ANALYSIS_REQUEST})
 const auth=structuredClone(recoveryIdentity);Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(auth.identity.profile,{authUserId:f.actor,rowVersion:1,roleRowVersion:1})
 auth.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view','production.cutting.view');state.auth=auth
 container=document.createElement('div');document.body.append(container);root=createRoot(container);client.rpc.mockImplementation(normal)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks();vi.unstubAllGlobals()})
async function ready(){await render();await until(()=>container.querySelectorAll('[data-quantity-target]').length===1)}
async function open(){await ready();await click('Periksa saran potong');expect(container.querySelector('[aria-label="Rencana Potongan ERP"]')).toBeTruthy()}
it('opens the actual checked form with exact admitted identity and microseconds, while ordinary quantity stays read only',async()=>{
 await render(true);await until(()=>container.querySelectorAll('[data-quantity-target]').length===1);expect(button('Periksa saran potong')).toBeUndefined()
 await act(async()=>root.unmount());root=createRoot(container);await open();const original=bytes()
 expect(button('Hitung kebutuhan terbaru').disabled).toBe(true);expect(button('Sumber berikutnya').disabled).toBe(true)
 expect(container.textContent).toContain('Saran ini memakai mesin rencana yang sama. Jumlah boleh diubah.')
 await click('Muat pilihan Potongan dari ERP');const call=client.rpc.mock.calls.at(-1)!
 expect(call[0]).toBe('erp_cp7_get_plan_options_v2');expect(call[1].p_query).toMatchObject({run_id:f.runId,target_key:target()})
 expect(container.querySelector('.native-plan-result')?.textContent).toContain('Kebutuhan setelah pembagian: 0 PCS')
 expect(bytes()).toBe(original);expect(client.rpc.mock.calls.some(([n])=>n.includes('save_'))).toBe(false)
 await click('Tutup rencana Potongan');expect(button('Hitung kebutuhan terbaru').disabled).toBe(false)
})
it('does not offer cutting without its current view permission or after a stale source check',async()=>{
 state.auth.identity.permissions=state.auth.identity.permissions.filter((p:string)=>p!=='production.cutting.view');await ready();expect(button('Periksa saran potong')).toBeUndefined()
 state.auth.identity.permissions.push('production.cutting.view');await ready();await click('Periksa sumber kebutuhan')
 expect(button('Periksa saran potong').disabled).toBe(true);expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_get_plan_options_v2')).toBe(false)
})
it('retires an open form on a real other-tab storage event and preserves that replacement UUID',async()=>{
 await open();await click('Muat pilihan Potongan dari ERP');const next={...request(),id:crypto.randomUUID()},key=frozenAnalysisRequestKey(f.actor,scope)
 localStorage.setItem(key,JSON.stringify(next));await act(async()=>{dispatchEvent(new StorageEvent('storage',{key}));await tick()})
 expect(container.querySelector('[aria-label="Rencana Potongan ERP"]')).toBeNull();expect(container.querySelector('table')).toBeNull();expect(request()).toEqual(next)
})
it('retires the parent quantities and open form when its options read returns current-access 403',async()=>{
 await open();const original=bytes();client.rpc.mockImplementation((name,args)=>name==='erp_cp7_get_plan_options_v2'?Promise.resolve({data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}}):normal(name,args))
 await click('Muat pilihan Potongan dari ERP')
 expect(container.querySelector('[aria-label="Rencana Potongan ERP"]')).toBeNull();expect(container.querySelector('table')).toBeNull();expect(bytes()).toBe(original)
})
it('keeps an original checked-save recovery envelope when current-access 403 rejects its replay',async()=>{
 await open();const payload={run_id:f.runId,target_key:target(),identity_hash:f.identityHash,cutting_save_contract:'cp7.cutting-checked-save.v1'},input={action:'SAVE_DRAFT',payload,expectedVersion:null}
 const envelope={...input,id:crypto.randomUUID(),createdAt:'2026-10-25T19:00:00Z',fingerprint:JSON.stringify(input)},key=productionKey(productionScope,'PLAN_APPLY_STAGED')
 localStorage.setItem(key,JSON.stringify(envelope));await act(async()=>{dispatchEvent(new StorageEvent('storage',{key}));await tick()})
 const pending=localStorage.getItem(key);client.rpc.mockImplementation((name,args)=>name==='erp_cp7_save_cutting_suggestion_v1'?Promise.resolve({data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}}):normal(name,args))
 await click('Reconcile transaksi');expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_save_cutting_suggestion_v1',{p_payload:payload,p_request:envelope.id}])
 expect(readProductionRecovery(productionScope).pending.PLAN_APPLY_STAGED).toEqual(envelope);expect(localStorage.getItem(key)).toBe(pending)
 expect(container.querySelector('[aria-label="Rencana Potongan ERP"]')).toBeNull();expect(container.querySelector('table')).toBeNull()
})
