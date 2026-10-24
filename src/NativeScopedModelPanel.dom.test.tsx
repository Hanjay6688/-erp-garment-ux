// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeScopedModelPanel from './NativeScopedModelPanel'
import wire from '../tests/fixtures/nativeScopedModelSql.json'
import {parseScopedHistoryQuery,scopedHistoryRecovery,scopedModelRecovery,scopedHistoryMethod,scopedModelMethod} from './nativeScopedModel'
import {parseModelQuery} from './nativeModelEvaluation'
let root:Root,container:HTMLDivElement
const scope='disposable:scoped-panel',actor=wire.actor,q=parseScopedHistoryQuery(wire.history.query),rpc=vi.fn(),start=vi.fn(),end=vi.fn(),lost=vi.fn(),block=vi.fn(),close=vi.fn(),client={rpc}
const tick=()=>new Promise<void>(r=>setTimeout(r,0))
const mount=async(overrides:Partial<Parameters<typeof NativeScopedModelPanel>[0]>={})=>act(async()=>{root.render(<NativeScopedModelPanel client={client} scope={scope} actor={actor} query={q} disabled={false} onSourceReadStart={start} onSourceReadEnd={end} onAccessLost={lost} onBlockingChange={block} onClose={close} {...overrides}/>);await tick()})
const button=(text:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===text)!
const click=async(text:string)=>act(async()=>{expect(button(text)).toBeDefined();button(text).click();await tick()})
const edit=async(value:string)=>act(async()=>{const e=container.querySelector('input')!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}));await tick()})
const captureHistory='Simpan riwayat produk saat ini',captureModel='Simpan evaluasi produk',retryHistory='Periksa riwayat yang sama',retryModel='Periksa evaluasi produk yang sama'
const modelRequest=(raw=wire.model)=>({requestId:raw.request_id,actor,method:scopedModelMethod,query:parseModelQuery(raw.query)})
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();for(const f of[rpc,start,end,lost,block,close])f.mockReset();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(lock:object)=>unknown)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container);rpc.mockResolvedValue({data:null,error:new TypeError('lost response')})})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
it('waits for explicit history capture and requires an explicit forecast horizon',async()=>{
 await mount();expect(rpc).not.toHaveBeenCalled();expect(container.querySelector('input')).toBeNull()
 rpc.mockImplementation(async(_name:string,args:{p_request:string})=>({data:{...wire.history,request_id:args.p_request},error:null}))
 await click(captureHistory);expect(container.querySelector('input')!.value).toBe('');expect(button(captureModel).disabled).toBe(true)
 expect(container.textContent).toContain('Stok fisik');expect(container.textContent).toContain('hari belum diketahui')
})
it('persists history before RPC, remounts, and replays exactly the original method and payload',async()=>{
 let original:unknown
 rpc.mockImplementation(async(name:string,args:{p_request:string;p_query:unknown})=>{expect(name).toBe(scopedHistoryMethod);expect(scopedHistoryRecovery.read(scope,actor).pending?.requestId).toBe(args.p_request);if(!original){original=structuredClone(args);return{data:null,error:new TypeError('lost response')}}expect(args).toEqual(original);return{data:{...wire.history,request_id:args.p_request},error:null}})
 await mount();await click(captureHistory);expect(button(captureHistory).disabled).toBe(true)
 await act(async()=>root.unmount());root=createRoot(container);await mount({query:null});await click(retryHistory)
 expect(rpc).toHaveBeenCalledTimes(2);expect(scopedHistoryRecovery.read(scope,actor).pending).toBeNull()
 expect(start.mock.calls.length).toBe(end.mock.calls.length)
})
it('captures a model from the returned scoped UUID and recovers an uncertain evaluation',async()=>{
 let modelArgs:unknown
 rpc.mockImplementation(async(name:string,args:{p_request:string;p_query:unknown})=>{
  if(name===scopedHistoryMethod)return{data:{...wire.history,request_id:args.p_request},error:null}
  expect(name).toBe(scopedModelMethod);expect(args.p_query).toEqual(wire.model.query)
  expect(scopedModelRecovery.read(scope,actor).pending?.requestId).toBe(args.p_request)
  if(!modelArgs){modelArgs=structuredClone(args);return{data:null,error:new TypeError('lost model response')}}
  expect(args).toEqual(modelArgs);return{data:{...wire.model,request_id:args.p_request},error:null}
 })
 await mount();await click(captureHistory);await edit('7');await click(captureModel)
 expect(scopedModelRecovery.read(scope,actor).pending).not.toBeNull()
 await act(async()=>root.unmount());root=createRoot(container);await mount({query:null});await click(retryModel)
 expect(scopedModelRecovery.read(scope,actor).pending).toBeNull();expect(container.textContent).toContain('Belum ada kebijakan penggunaan model')
 expect(container.textContent).toContain('belum diterapkan pada target produksi');expect(rpc).toHaveBeenCalledTimes(3)
})
it('recovers a model without recapturing history, then retires changed sources without rewriting its archive',async()=>{
 scopedModelRecovery.persist(scope,modelRequest(wire.beforeSourceChange))
 rpc.mockResolvedValueOnce({data:wire.beforeSourceChange,error:null}).mockResolvedValueOnce({data:wire.afterSourceChange,error:null})
 await mount({query:null});await click(retryModel);await click('Periksa sumber dan kelayakan arsip')
 expect(rpc.mock.calls.map(x=>x[0])).toEqual([scopedModelMethod,'erp_cp7_read_model_evaluation_v3'])
 expect(container.textContent).toContain('Sumber berubah sejak evaluasi disimpan.')
 expect(container.textContent).toContain('Arsip: sumber, kebijakan')
})
it('retires displayed data and preserves replay when current access is revoked',async()=>{
 scopedModelRecovery.persist(scope,modelRequest());rpc.mockResolvedValue({data:null,error:{code:'42501',message:'denied'}})
 await mount({query:null});await click(retryModel)
 expect(lost).toHaveBeenCalledTimes(1);expect(scopedModelRecovery.read(scope,actor).pending).not.toBeNull()
 expect(button(retryModel).disabled).toBe(true);expect(container.querySelector('h4')).toBeNull()
})
it('does not send on missing locks, corrupt storage or a period above366days',async()=>{
 Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});await mount();await click(captureHistory);expect(rpc).not.toHaveBeenCalled();expect(scopedHistoryRecovery.read(scope,actor).pending).toBeNull()
 await mount({query:{...q,through_date:'2027-10-01'}});expect(button(captureHistory).disabled).toBe(true)
 expect(container.textContent).toContain('paling banyak 366 hari')
})
it('checks another tab and current storage after waiting for the browser lock',async()=>{
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(lock:object)=>unknown)=>{scopedModelRecovery.persist(scope,modelRequest());return fn({})}}})
 await mount();await click(captureHistory);expect(rpc).not.toHaveBeenCalled();expect(scopedModelRecovery.read(scope,actor).pending).not.toBeNull()
 expect(button(retryModel)).toBeDefined()
})
it('does not clear a late successful response after target change or unmount',async()=>{
 let resolve!:(r:unknown)=>void;rpc.mockImplementation(()=>new Promise(r=>{resolve=r}))
 await mount();await click(captureHistory);const held=scopedHistoryRecovery.read(scope,actor).pending!
 await mount({query:{...q,target_key:crypto.randomUUID()+':'+crypto.randomUUID()}})
 await act(async()=>{resolve({data:{...wire.history,request_id:held.requestId},error:null});await tick()})
 expect(scopedHistoryRecovery.read(scope,actor).pending).toEqual(held);expect(container.querySelector('h4')).toBeNull()
 expect(start.mock.calls.length).toBe(end.mock.calls.length)
})
