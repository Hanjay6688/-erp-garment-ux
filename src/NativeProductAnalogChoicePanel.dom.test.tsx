// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,it,expect,vi} from 'vitest'
import NativeProductAnalogChoicePanel from './NativeProductAnalogChoicePanel'
import {analogChoiceFixture} from '../tests/fixtures/nativeProductAnalogChoice'
import {readAnalogChoiceRequest,persistAnalogChoiceRequest,clearAnalogChoiceRequest,analogChoiceRequestKey} from './nativeProductAnalogChoice'
let root:Root,container:HTMLDivElement,f:ReturnType<typeof analogChoiceFixture>
const scope='disposable:analog-choice',rpc=vi.fn(),lost=vi.fn(),tick=()=>new Promise<void>(resolve=>setTimeout(resolve,0))
const stored=()=>readAnalogChoiceRequest(scope,f.context.actor,f.context.targetKey)
const mount=async(manage=true)=>act(async()=>{root.render(<NativeProductAnalogChoicePanel client={{rpc}} context={f.context} candidates={f.candidates} scope={scope} canManage={manage} onAccessLost={lost}/>);await tick()})
const click=async(text:string)=>act(async()=>{const b=[...container.querySelectorAll('button')].find(b=>b.textContent===text)!;expect(b).toBeDefined();b.click();await tick()})
async function input(selector:string,value:string){await act(async()=>{const el=container.querySelector(selector)as HTMLInputElement;const proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:el instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(el,value);el.dispatchEvent(new Event(el instanceof HTMLSelectElement?'change':'input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));await tick()})}
const fill=async()=>{await input('select',f.candidates.rows[0].key);await input('input[inputmode="decimal"]','1.25');await input('textarea','Periksa kain dan model');await act(async()=>{(container.querySelector('input[type="checkbox"]')as HTMLInputElement).click();await tick()})}
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();rpc.mockReset();lost.mockReset();f=analogChoiceFixture()
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,_options:unknown,fn:(lock:object)=>unknown)=>fn({})}})
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
 rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_product_analog_choices_v1'?{data:f.raw,error:null}:{data:null,error:new TypeError('delivery lost')})
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
it('persists before sending, blocks duplicates, then reconciles the identical command after reload',async()=>{
 let first:Record<string,unknown>|null=null
 rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
  if(name==='erp_cp7_get_product_analog_choices_v1')return{data:f.raw,error:null}
  expect(stored().pending?.requestId).toBe(args.p_request)
  if(!first){first=structuredClone(args);return{data:null,error:new TypeError('delivery lost')}}
  expect(args).toEqual(first)
  return{data:{...f.outcome,request_id:args.p_request,reason:(args.p_payload as {reason:string}).reason},error:null}
 })
 await mount();expect((container.querySelector('input[inputmode="decimal"]')as HTMLInputElement).value).toBe('')
 const select=container.querySelector('select')!;expect([...select.labels!].map(label=>label.textContent)).toEqual(['Produk pembanding'])
 await fill();expect([...container.querySelector('textarea')!.labels!].map(label=>label.textContent)).toEqual(['Alasan kesamaan atau pencabutan']);await click('Simpan pilihan pembanding');expect(stored().pending).not.toBeNull()
 expect((container.querySelector('fieldset')as HTMLFieldSetElement).disabled).toBe(true)
 await act(async()=>root.unmount());root=createRoot(container);await mount()
 await click('Periksa hasil konfirmasi yang sama');expect(stored().pending).toBeNull();expect(container.textContent).toContain('revisi 1 tersimpan')
 expect(rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_product_analog_choice_v1')).toHaveLength(2)
})
it('retains uncertain replay even when current access is revoked',async()=>{
 persistAnalogChoiceRequest(scope,f.command)
 rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_product_analog_choices_v1'?{data:f.raw,error:null}:{data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}})
 await mount();await click('Periksa hasil konfirmasi yang sama');expect(stored().pending).toEqual(f.command);expect(lost).toHaveBeenCalledOnce()
})
it('releases only a definite first database refusal and requires a new workspace read',async()=>{
 rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_product_analog_choices_v1'?{data:f.raw,error:null}:{data:null,error:{code:'40001',message:'CP7_ANALOG_CHOICE_SOURCE_CHANGED'}})
 await mount();await fill();await click('Simpan pilihan pembanding');expect(stored().pending).toBeNull();expect((container.querySelector('fieldset')as HTMLFieldSetElement).disabled).toBe(true)
})
it('keeps the command when a success response contradicts the reviewed snapshot',async()=>{
 rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>name==='erp_cp7_get_product_analog_choices_v1'?{data:f.raw,error:null}:{data:{...f.outcome,request_id:args.p_request,reason:(args.p_payload as {reason:string}).reason,evidence:{...f.outcome.evidence,history_hash:'9'.repeat(64)}},error:null})
 await mount();await fill();await click('Simpan pilihan pembanding');expect(stored().pending).not.toBeNull();expect(container.textContent).not.toContain('revisi 1 tersimpan')
})
it('does not send when durable storage fails or when the browser lock is unavailable',async()=>{
 await mount();await fill();const write=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('storage unavailable')})
 await click('Simpan pilihan pembanding');expect(rpc.mock.calls.every(([name])=>name==='erp_cp7_get_product_analog_choices_v1')).toBe(true)
 write.mockRestore();Object.defineProperty(navigator,'locks',{configurable:true,value:undefined})
 await click('Simpan pilihan pembanding');expect(stored().pending).toBeNull();expect(rpc.mock.calls).toHaveLength(1)
})
it('retires a late response after a cross-tab change without clearing the original pending command',async()=>{
 let release:(value:unknown)=>void=()=>{}
 rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_product_analog_choices_v1'?{data:f.raw,error:null}:new Promise(resolve=>{release=resolve}))
 await mount();await fill();await click('Simpan pilihan pembanding');const command=stored().pending!
 await act(async()=>{dispatchEvent(new StorageEvent('storage',{key:analogChoiceRequestKey(scope,f.context.targetKey)}));await tick()})
 await act(async()=>{release({data:{...f.outcome,request_id:command.requestId,reason:command.payload.reason},error:null});await tick()})
 expect(stored().pending).toEqual(command);expect(container.textContent).not.toContain('revisi 1 tersimpan')
})
it('does not permit a foreign actor, corrupted record or changed payload to clear recovery',async()=>{
 persistAnalogChoiceRequest(scope,f.command)
 expect(readAnalogChoiceRequest(scope,'00000000-0000-4000-8000-000000000999',f.context.targetKey).error).not.toBe('')
 expect(()=>clearAnalogChoiceRequest(scope,{...f.command,payload:{...f.command.payload,reason:'changed'}})).toThrow()
 expect(stored().pending).toEqual(f.command)
 localStorage.setItem(analogChoiceRequestKey(scope,f.context.targetKey),'broken')
 await mount();expect((container.querySelector('fieldset')as HTMLFieldSetElement).disabled).toBe(true);expect(stored().error).not.toBe('')
})
it('shows stored choices to a reader without granting write controls',async()=>{
 await mount(false);expect((container.querySelector('fieldset')as HTMLFieldSetElement).disabled).toBe(true);expect(container.textContent).toContain('Izin mengelola produk diperlukan')
 expect(rpc.mock.calls).toHaveLength(1)
})
