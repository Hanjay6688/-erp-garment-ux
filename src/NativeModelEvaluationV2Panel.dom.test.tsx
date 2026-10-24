// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,it,expect,vi} from 'vitest'
import NativeModelEvaluationV2Panel from './NativeModelEvaluationV2Panel'
import wire from '../tests/fixtures/nativeModelEvaluationV2Sql.json'
import {modelV2Method,modelV2RequestKey,persistModelV2Request,readModelV2Request} from './nativeModelEvaluationV2'
import {parseModelQuery,persistModelRequest} from './nativeModelEvaluation'
let root:Root,container:HTMLDivElement
const scope='disposable:model-v2',actor=wire.actor,rpc=vi.fn(),lost=vi.fn(),start=vi.fn(),end=vi.fn(),block=vi.fn(),client={rpc}
const q=parseModelQuery(wire.eligible.query),tick=()=>new Promise<void>(resolve=>setTimeout(resolve,0)),stored=()=>readModelV2Request(scope,actor)
const request=()=>({requestId:wire.eligible.request_id,actor,method:modelV2Method,query:q})
const mount=async(overrides:Partial<Parameters<typeof NativeModelEvaluationV2Panel>[0]>={})=>act(async()=>{root.render(<NativeModelEvaluationV2Panel client={client} scope={scope} actor={actor} historyRunId={q.history_run_id} targetKey={q.target_key} disabled={false} onSourceReadStart={start} onSourceReadEnd={end} onAccessLost={lost} onBlockingChange={block} {...overrides}/>);await tick()})
const button=(text:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===text)!
const click=async(text:string)=>act(async()=>{expect(button(text)).toBeDefined();button(text).click();await tick()})
const edit=async(value:string)=>act(async()=>{const el=container.querySelector('input')!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));await tick()})
const save='Simpan evaluasi sesuai kebijakan',retry='Periksa hasil evaluasi yang sama',check='Periksa kelayakan arsip saat ini'
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();for(const m of[rpc,lost,start,end,block])m.mockReset();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,_options:unknown,fn:(lock:object)=>unknown)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container);rpc.mockResolvedValue({data:null,error:new TypeError('reply lost')})})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
it('starts with an empty explicit horizon and never captures on mount',async()=>{await mount();expect(container.querySelector('input')!.value).toBe('');expect(button(save).disabled).toBe(true);expect(rpc).not.toHaveBeenCalled();expect(start).not.toHaveBeenCalled()})
it('persists before sending, recovers after remount and replays the exact method, UUID and payload',async()=>{
 let first:unknown
 rpc.mockImplementation(async(name:string,args:{p_request:string;p_query:unknown})=>{expect(name).toBe(modelV2Method);expect(stored().pending?.requestId).toBe(args.p_request);if(!first){first=structuredClone(args);return{data:null,error:new TypeError('reply lost')}}expect(args).toEqual(first);return{data:{...wire.eligible,request_id:args.p_request},error:null}})
 await mount();await edit('7');await click(save);expect(stored().pending).not.toBeNull();expect(button(save).disabled).toBe(true)
 await act(async()=>root.unmount());root=createRoot(container);await mount();await click(retry)
 expect(stored().pending).toBeNull();expect(rpc).toHaveBeenCalledTimes(2);expect(container.textContent).toContain('Model memenuhi syarat saat diperiksa.');expect(container.textContent).toContain('2026-10-30');expect(start.mock.calls.length).toBe(end.mock.calls.length)
})
it('keeps the archived vector but retires current eligibility when policy changes',async()=>{
 persistModelV2Request(scope,request());rpc.mockResolvedValueOnce({data:wire.eligible,error:null}).mockResolvedValueOnce({data:wire.withdrawn,error:null})
 await mount();await click(retry);await click(check)
 expect(container.textContent).toContain('Kebijakan sudah berubah');expect(container.textContent).toContain('tidak boleh dipakai sebagai ramalan aktif');expect(container.textContent).toContain('Model memenuhi syarat ketika evaluasi disimpan.');expect(container.querySelectorAll('tbody').length).toBe(2)
})
it('keeps the source and baseline when no challenger is permitted, without inventing scores',async()=>{
 const raw=wire.noAllowedModel;persistModelV2Request(scope,{...request(),requestId:raw.request_id});rpc.mockResolvedValue({data:raw,error:null});await mount();await click(retry)
 expect(container.textContent).toContain('Kebijakan tidak mengizinkan model pembanding.');expect(container.textContent).toContain('SYNTHETIC');expect(container.querySelector('table')).toBeNull();expect(container.textContent).toContain('50,5')
})
it('retires figures on a current 403, retains dirty horizon and balances parent reads',async()=>{
 persistModelV2Request(scope,request());rpc.mockResolvedValueOnce({data:wire.eligible,error:null}).mockResolvedValueOnce({data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}})
 await mount();await click(retry);await click(check);expect(lost).toHaveBeenCalledOnce();expect(container.textContent).not.toContain('SYNTHETIC');expect(container.querySelector('input')!.value).toBe('7');expect(start.mock.calls.length).toBe(end.mock.calls.length)
})
it('retains an uncertain replay even if current access is revoked',async()=>{persistModelV2Request(scope,request());rpc.mockResolvedValue({data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}});await mount();await click(retry);expect(stored().pending).toEqual(request());expect(lost).toHaveBeenCalledOnce()})
it('releases a definite first rollback but keeps malformed success for exact recovery',async()=>{
 rpc.mockResolvedValueOnce({data:null,error:{code:'P0001',message:'CP7_MODEL_V2_HISTORY_STALE'}}).mockResolvedValueOnce({data:{...wire.eligible,forecast_applied:true},error:null})
 await mount();await edit('7');await click(save);expect(stored().pending).toBeNull();await click(save);expect(stored().pending).not.toBeNull();expect(container.textContent).not.toContain('SYNTHETIC')
})
it.each(['missing','unavailable','legacy','corrupt','storage']as const)('sends nothing when %s blocks a new request',async kind=>{
 if(kind==='missing')Object.defineProperty(navigator,'locks',{configurable:true,value:undefined})
 if(kind==='unavailable')Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,_options:unknown,fn:(lock:null)=>unknown)=>fn(null)}})
 if(kind==='legacy')persistModelRequest(scope,{id:crypto.randomUUID(),q})
 if(kind==='corrupt')localStorage.setItem(modelV2RequestKey(scope),'broken')
 if(kind==='storage')vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{})
 await mount();await edit('7');await click(save);expect(rpc).not.toHaveBeenCalled();expect(start.mock.calls.length).toBe(end.mock.calls.length)
})
it('ignores a late response after another tab changes the recovery record',async()=>{
 let resolve!:(x:unknown)=>void;rpc.mockImplementation(()=>new Promise(r=>{resolve=r}));await mount();await edit('7');await click(save);const old=stored().pending!
 await act(async()=>{localStorage.setItem(modelV2RequestKey(scope),JSON.stringify({...old,requestId:crypto.randomUUID()}));dispatchEvent(new StorageEvent('storage',{key:modelV2RequestKey(scope)}));await tick()})
 await act(async()=>{resolve({data:{...wire.eligible,request_id:old.requestId},error:null});await tick()})
 expect(stored().pending?.requestId).not.toBe(old.requestId);expect(container.textContent).not.toContain('SYNTHETIC');expect(start.mock.calls.length).toBe(end.mock.calls.length)
})
it('ignores a late response after the history selection changes and retains the original request',async()=>{
 let resolve!:(x:unknown)=>void;rpc.mockImplementation(()=>new Promise(r=>{resolve=r}));await mount();await edit('7');await click(save);const old=stored().pending!
 await mount({historyRunId:crypto.randomUUID()});await act(async()=>{resolve({data:{...wire.eligible,request_id:old.requestId},error:null});await tick()})
 expect(stored().pending).toEqual(old);expect(container.textContent).not.toContain('SYNTHETIC');expect(start.mock.calls.length).toBe(end.mock.calls.length)
})
