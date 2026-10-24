// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,it,expect,vi} from 'vitest'
import NativeModelPolicyPanel from './NativeModelPolicyPanel'
import wire from '../tests/fixtures/nativeModelPolicySql.json'
import {readModelPolicyRequest,persistModelPolicyRequest,prepareModelPolicy,parseModelPolicyWorkspace,modelPolicyRequestKey} from './nativeModelPolicy'
let root:Root,container:HTMLDivElement
const scope='disposable:model-policy',actor=wire.workspace.actor_scope_id,rpc=vi.fn(),lost=vi.fn(),client={rpc}
const tick=()=>new Promise<void>(resolve=>setTimeout(resolve,0)),stored=()=>readModelPolicyRequest(scope,actor)
const command=()=>prepareModelPolicy(parseModelPolicyWorkspace(wire.workspace,actor),'SET',wire.payload.config,wire.payload.reason,true,wire.requestId)
const mount=async(manage=true)=>act(async()=>{root.render(<NativeModelPolicyPanel client={client} scope={scope} actor={actor} canManage={manage} onAccessLost={lost}/>);await tick()})
const button=(text:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===text)!
const click=async(text:string)=>act(async()=>{expect(button(text)).toBeDefined();button(text).click();await tick()})
const edit=async(el:HTMLInputElement|HTMLTextAreaElement,value:string)=>act(async()=>{Object.getOwnPropertyDescriptor(el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));await tick()})
const review=async()=>act(async()=>{([...container.querySelectorAll('input[type=checkbox]')].at(-1)as HTMLInputElement).click();await tick()})
const fill=async()=>{const values=['20','90','3','0','0','0','7'];for(const[i,el]of[...container.querySelectorAll<HTMLInputElement>('input:not([type=checkbox])')].entries())await edit(el,values[i]);await edit(container.querySelector('textarea')!,wire.payload.reason);await act(async()=>{(container.querySelector('input[type=checkbox]')as HTMLInputElement).click();await tick()});await review()}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();rpc.mockReset();lost.mockReset();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,_options:unknown,fn:(lock:object)=>unknown)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container);rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_model_activation_policy_v1'?{data:wire.workspace,error:null}:{data:null,error:new TypeError('reply lost')})})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
it('starts without thresholds or selected methods, explains no activation and sends no write',async()=>{
 await mount();expect([...container.querySelectorAll<HTMLInputElement>('input:not([type=checkbox])')].every(x=>x.value==='')).toBe(true)
 expect([...container.querySelectorAll<HTMLInputElement>('input[type=checkbox]')].every(x=>!x.checked)).toBe(true)
 expect(button('Simpan kebijakan yang ditinjau').disabled).toBe(true);expect(container.textContent).toContain('belum mengaktifkan ramalan')
 for(const el of container.querySelectorAll<HTMLInputElement>('input:not([type=checkbox])'))expect(el.labels?.length).toBe(1)
 expect(rpc).toHaveBeenCalledTimes(1)
})
it('persists before sending and retries the identical command after a lost reply and remount',async()=>{
 let first:Record<string,unknown>|null=null
 rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
  if(name==='erp_cp7_get_model_activation_policy_v1')return{data:wire.workspace,error:null}
  expect(stored().pending?.requestId).toBe(args.p_request)
  if(!first){first=structuredClone(args);return{data:null,error:new TypeError('reply lost')}}
  expect(args).toEqual(first);return{data:{...wire.outcome,request_id:args.p_request},error:null}
 })
 await mount();await fill();await click('Simpan kebijakan yang ditinjau');expect(stored().pending).not.toBeNull();expect(container.querySelector('fieldset')!.disabled).toBe(true)
 await act(async()=>root.unmount());root=createRoot(container);await mount();await click('Periksa hasil kebijakan yang sama')
 expect(stored().pending).toBeNull();expect(container.textContent).toContain('revisi 1 tersimpan');expect(rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_model_activation_policy_v1')).toHaveLength(2)
})
it('can suspend a stored policy without filling or changing its thresholds',async()=>{
 const prior={policy:wire.outcome.policy,actor_scope_id:actor,request_id:wire.requestId,template_hash:wire.outcome.template_hash}
 rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
  if(name==='erp_cp7_get_model_activation_policy_v1')return{data:{...wire.workspace,current:prior,revision:'1',state:'ACTIVE'},error:null}
  const p=args.p_payload as Record<string,unknown>;expect(p.action).toBe('SUSPEND');expect(p.config).toBeNull();expect(p.template_hash).toBeNull()
  return{data:null,error:new TypeError('reply lost')}
 })
 await mount();expect([...container.querySelectorAll<HTMLInputElement>('input:not([type=checkbox])')].every(x=>x.value==='')).toBe(true)
 await edit(container.querySelector('textarea')!,'Withdraw reviewed policy');await review();await click('Cabut kebijakan model');expect(stored().pending?.prior).toEqual(prior)
})
it('copies saved fields only on explicit selection and clears review after editing',async()=>{
 rpc.mockResolvedValue({data:{...wire.workspace,current:{policy:wire.outcome.policy,actor_scope_id:actor,request_id:wire.requestId,template_hash:wire.outcome.template_hash},revision:'1',state:'ACTIVE'},error:null})
 await mount();await click('Isi dari kebijakan tersimpan');expect(container.querySelector<HTMLInputElement>('input')!.value).toBe('20')
 await edit(container.querySelector('textarea')!,'Reviewed copy');await review();expect(button('Simpan kebijakan yang ditinjau').disabled).toBe(false)
 await edit(container.querySelector<HTMLInputElement>('input')!,'21');expect(button('Simpan kebijakan yang ditinjau').disabled).toBe(true)
})
it('retains an uncertain replay after access loss and hides the last workspace',async()=>{
 persistModelPolicyRequest(scope,command());rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_model_activation_policy_v1'?{data:wire.workspace,error:null}:{data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}})
 await mount();await click('Periksa hasil kebijakan yang sama');expect(stored().pending).toEqual(command());expect(lost).toHaveBeenCalledOnce();expect(container.querySelector('fieldset')!.disabled).toBe(true)
})
it('releases only a definite first database refusal and requires a fresh read',async()=>{
 rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_model_activation_policy_v1'?{data:wire.workspace,error:null}:{data:null,error:{code:'P0001',message:'CP7_MODEL_POLICY_REVISION_CHANGED'}})
 await mount();await fill();await click('Simpan kebijakan yang ditinjau');expect(stored().pending).toBeNull();expect(container.querySelector('fieldset')!.disabled).toBe(true)
})
it('keeps a command if the success receipt silently changes its thresholds',async()=>{
 rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>name==='erp_cp7_get_model_activation_policy_v1'?{data:wire.workspace,error:null}:{data:{...wire.outcome,request_id:args.p_request,policy:{...wire.outcome.policy,config:{...wire.outcome.policy.config,minimum_training_days:'21'}}},error:null})
 await mount();await fill();await click('Simpan kebijakan yang ditinjau');expect(stored().pending).not.toBeNull();expect(container.textContent).not.toContain('revisi 1 tersimpan')
})
it('does not send when durable storage or the browser lock is unavailable',async()=>{
 await mount();await fill();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('storage unavailable')});await click('Simpan kebijakan yang ditinjau');expect(rpc).toHaveBeenCalledTimes(1)
 vi.restoreAllMocks();Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});await click('Simpan kebijakan yang ditinjau');expect(rpc).toHaveBeenCalledTimes(1)
})
it('ignores a late success after another tab changes recovery',async()=>{
 let release:(r:unknown)=>void=()=>{}
 rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_model_activation_policy_v1'?{data:wire.workspace,error:null}:new Promise(resolve=>{release=resolve}))
 await mount();await fill();await click('Simpan kebijakan yang ditinjau');const held=stored().pending!
 await act(async()=>{dispatchEvent(new StorageEvent('storage',{key:modelPolicyRequestKey(scope)}));await tick()})
 await act(async()=>{release({data:{...wire.outcome,request_id:held.requestId},error:null});await tick()})
 expect(stored().pending).toEqual(held);expect(container.textContent).not.toContain('revisi 1 tersimpan')
})
it('blocks a reader and corrupted recovery without issuing a write',async()=>{
 localStorage.setItem(modelPolicyRequestKey(scope),'broken');await mount(false);expect(container.querySelector('fieldset')!.disabled).toBe(true);expect(container.textContent).toContain('Owner atau admin');expect(rpc).toHaveBeenCalledTimes(1)
})
