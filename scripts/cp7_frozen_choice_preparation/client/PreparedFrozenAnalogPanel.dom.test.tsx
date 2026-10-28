// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import PreparedFrozenAnalogPanel from './PreparedFrozenAnalogPanel'
import {frozenChoiceUIFixture} from '../../cp7_frozen_choice_ui/client/fixtures'
import {persistAnalogChoiceRequest,readAnalogChoiceRequest} from '../../cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice'
import {recoveryIdentity} from '../../../tests/fixtures/productionRecovery'
import {prepReply} from './preparationFixture'
const state=vi.hoisted(()=>({auth:null as any}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../../src/auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('../../../src/lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,f:ReturnType<typeof frozenChoiceUIFixture>
const close=vi.fn(),lost=vi.fn(),tick=()=>new Promise<void>(r=>setTimeout(r,0))
const mount=async()=>act(async()=>{root.render(<PreparedFrozenAnalogPanel context={f.context} label="Produk baru" onClose={close} onAccessLost={lost}/>);await tick()})
const click=async(label:string)=>act(async()=>{const b=[...container.querySelectorAll('button')].find(b=>b.textContent===label)!;expect(b).toBeTruthy();b.click();await tick()})
const reply=(s:string)=>({...prepReply(s),source_request:f.context.requestId,run_id:f.context.runId,reference:{captured_at:f.context.reference.capturedAt,source_hash:f.context.reference.sourceHash}})
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();close.mockReset();lost.mockReset();localStorage.clear();f=frozenChoiceUIFixture(51)
 vi.stubGlobal('navigator',{locks:{request:async(_n:string,_o:unknown,fn:()=>unknown)=>await fn()}})
 const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:f.context.actor,rowVersion:1,roleRowVersion:1});a.identity.permissions.push('master.product.view','master.product.manage','warehouse.stock.view','sales.invoice.view');state.auth=a
 client.rpc.mockImplementation(async(name:string,args:{p_offset:number})=>{
  if(name==='erp_cp7_get_frozen_choice_preparation_v1')return{data:null,error:{message:'CP7_CHOICE_PREPARATION_NOT_STARTED'}}
  return{data:name==='erp_cp7_request_frozen_choice_preparation_v1'?reply('QUEUED'):name==='erp_cp7_step_frozen_choice_preparation_v1'?reply('READY'):name==='erp_cp7_read_product_analog_candidates_v2'?f.reply(args.p_offset):f.raw,error:null}
 })
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks();vi.unstubAllGlobals();localStorage.clear()})
it('prepares once before the first candidate read and reuses it for later pages',async()=>{
 await mount();expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_read_product_analog_candidates_v2')).toBe(false)
 await click('Siapkan pemeriksaan pilihan');expect(container.querySelectorAll('[data-analog-target]')).toHaveLength(50)
 await click('50 kandidat berikutnya');expect(container.querySelectorAll('[data-analog-target]')).toHaveLength(1)
 const calls=client.rpc.mock.calls.map(([n])=>n);expect(calls.indexOf('erp_cp7_step_frozen_choice_preparation_v1')).toBeLessThan(calls.indexOf('erp_cp7_read_product_analog_candidates_v2'))
 expect(calls.filter(n=>n==='erp_cp7_step_frozen_choice_preparation_v1')).toHaveLength(1)
})
it('already-ready reopening reads candidates without requesting or repeating preparation',async()=>{
 client.rpc.mockImplementation(async(name:string,args:{p_offset:number})=>({data:name==='erp_cp7_get_frozen_choice_preparation_v1'?reply('READY'):name==='erp_cp7_read_product_analog_candidates_v2'?f.reply(args.p_offset):f.raw,error:null}))
 await mount();expect(container.querySelectorAll('[data-analog-target]')).toHaveLength(50)
 expect(client.rpc.mock.calls.some(([n])=>n.includes('_step_')||n.includes('_request_'))).toBe(false)
})
it('a lost SAVE receipt remains recoverable even when preparation source has expired',async()=>{
 const scope='product-analog:cp6-disposable';await persistAnalogChoiceRequest(scope,f.command)
 client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_payload:{reason:string}})=>{
  if(name==='erp_cp7_get_frozen_choice_preparation_v1')return{data:null,error:{code:'P0001',message:'CP7_ANALYSIS_RESULT_EXPIRED'}}
  if(name==='erp_cp7_get_product_analog_choices_v1')return{data:f.raw,error:null}
  expect(name).toBe('erp_cp7_save_product_analog_choice_v2');expect(args.p_request).toBe(f.command.requestId);expect(args.p_payload).toEqual(f.command.payload)
  return{data:f.outcome,error:null}
 })
 await mount();await click('Periksa hasil konfirmasi yang sama');expect(readAnalogChoiceRequest(scope,f.context.actor,f.context.targetKey).pending).toBeNull()
 expect(container.textContent).toContain('konfirmasi revisi 1 tersimpan')
})
it.each(['actor','permission','method'])('refuses %s before any preparation or candidate RPC',async kind=>{
 if(kind==='actor')state.auth.identity.profile.authUserId='00000000-0000-4000-8000-000000000999'
 if(kind==='permission')state.auth.identity.permissions=[]
 if(kind==='method')delete f.context.sourceMethod
 await mount();expect(client.rpc).not.toHaveBeenCalled();expect(container.textContent).toBe('')
})
it('allows closing while a real preparation reply is still pending and retires it on unmount',async()=>{
 let release!:(v:unknown)=>void
 client.rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_frozen_choice_preparation_v1'?new Promise(resolve=>{release=resolve}):{data:f.raw,error:null})
 await mount();await click('Tutup persiapan pembanding');expect(close).toHaveBeenCalledOnce()
 await act(async()=>{root.render(null);await tick();release({data:reply('READY'),error:null});await tick()})
 expect(container.textContent).toBe('');expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_read_product_analog_candidates_v2')).toBe(false)
})
