// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeFrozenAnalogPanel from './NativeFrozenAnalogPanel'
import {frozenChoiceUIFixture} from './fixtures'
import {persistAnalogChoiceRequest,readAnalogChoiceRequest} from '../../cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice'
import {recoveryIdentity} from '../../../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as any}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../../src/auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('../../../src/lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,f:ReturnType<typeof frozenChoiceUIFixture>
const close=vi.fn(),lost=vi.fn(),tick=()=>new Promise<void>(r=>setTimeout(r,0))
const mount=async()=>act(async()=>{root.render(<NativeFrozenAnalogPanel context={f.context} label="Produk baru" onClose={close} onAccessLost={lost}/>);await tick()})
const click=async(label:string)=>act(async()=>{const b=[...container.querySelectorAll('button')].find(b=>b.textContent===label)!;expect(b).toBeTruthy();b.click();await tick()})
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();close.mockReset();lost.mockReset();localStorage.clear();f=frozenChoiceUIFixture(51)
 vi.stubGlobal('navigator',{locks:{request:async(_name:string,_options:unknown,fn:()=>unknown)=>await fn()}})
 const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:f.context.actor,rowVersion:1,roleRowVersion:1});a.identity.permissions.push('master.product.view','master.product.manage','warehouse.stock.view','sales.invoice.view');state.auth=a
 client.rpc.mockImplementation(async(name:string,args:{p_offset:number})=>({data:name==='erp_cp7_read_product_analog_candidates_v2'?f.reply(args.p_offset):f.raw,error:null}))
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks();vi.unstubAllGlobals();localStorage.clear()})
it('reads explicit v2 candidates, all pages and exact historical target provenance',async()=>{
 await mount();expect(container.querySelectorAll('[data-analog-target]')).toHaveLength(50);expect(container.textContent).toContain('PEMBANDING-0');expect(container.textContent).toContain('perkiraan berbasis produk pembanding')
 await click('50 kandidat berikutnya');expect(container.querySelectorAll('[data-analog-target]')).toHaveLength(1);expect(container.textContent).toContain('PEMBANDING-50')
 expect(client.rpc.mock.calls.map(c=>c[0])).toEqual(['erp_cp7_read_product_analog_candidates_v2','erp_cp7_read_product_analog_candidates_v2']);expect(client.rpc.mock.calls[1][1].p_offset).toBe(50)
})
it.each(['runtime','actor','permission','method'])('refuses %s mismatch before any RPC',async kind=>{
 if(kind==='runtime')state.auth.runtime.mode='UAT_AUTH_SIMULATION'
 if(kind==='actor')state.auth.identity.profile.authUserId='00000000-0000-4000-8000-000000000999'
 if(kind==='permission')state.auth.identity.permissions=state.auth.identity.permissions.filter((p:string)=>p!=='sales.invoice.view')
 if(kind==='method')delete f.context.sourceMethod
 await mount();expect(container.textContent).toBe('');expect(client.rpc).not.toHaveBeenCalled()
})
it('retires late candidates when the actual identity loses read access',async()=>{
 let release!:(v:unknown)=>void;const reply=f.reply()
 client.rpc.mockImplementation(()=>new Promise(resolve=>{release=resolve}));await mount()
 state.auth.identity.permissions=[];await mount();await act(async()=>{release({data:reply,error:null});await tick()})
 expect(container.textContent).toBe('');expect(lost).not.toHaveBeenCalled()
})
it('clears candidate and choice data on server access denial while paging',async()=>{
 await mount();await click('Atur pilihan pembanding');expect(container.textContent).toContain('Belum ada pilihan yang dikonfirmasi.')
 client.rpc.mockResolvedValue({data:null,error:{code:'42501',status:403,message:'access denied'}})
 await click('50 kandidat berikutnya');expect(container.querySelector('tbody')).toBeNull();expect(container.querySelector('.native-analog-choice')).toBeNull();expect(lost).toHaveBeenCalledOnce()
})
it('rejects a changed page source rather than combining two snapshots',async()=>{
 await mount();client.rpc.mockImplementation(async()=>{const r=f.reply(50);r.result.history_hash='9'.repeat(64);return{data:r,error:null}})
 await click('50 kandidat berikutnya');expect(container.querySelector('tbody')).toBeNull();expect(container.querySelector('[role=alert]')).toBeTruthy()
})

it('recovers an already committed choice even when its archived candidate source can no longer be read',async()=>{
 const scope='product-analog:cp6-disposable';await persistAnalogChoiceRequest(scope,f.command)
 client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_payload:{reason:string}})=>{
  if(name==='erp_cp7_read_product_analog_candidates_v2')return{data:null,error:{code:'P0001',message:'CP7_ANALYSIS_RUN_EXPIRED'}}
  if(name==='erp_cp7_get_product_analog_choices_v1')return{data:f.raw,error:null}
  expect(name).toBe('erp_cp7_save_product_analog_choice_v2');expect(args.p_request).toBe(f.command.requestId);expect(args.p_payload).toEqual(f.command.payload)
  return{data:{...f.outcome,request_id:args.p_request,reason:args.p_payload.reason},error:null}
 })
 await mount();expect(container.querySelector('tbody')).toBeNull();await click('Atur pilihan pembanding');await click('Periksa hasil konfirmasi yang sama')
 expect(readAnalogChoiceRequest(scope,f.context.actor,f.context.targetKey).pending).toBeNull();expect(container.textContent).toContain('konfirmasi revisi 1 tersimpan')
})
