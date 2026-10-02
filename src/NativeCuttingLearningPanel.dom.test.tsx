// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeCuttingLearningPanel from './NativeCuttingLearningPanel'
import {parseLearningReply,parseModelWorkspace,validateLearningIntent,heldLearning,holdLearning,cuttingLearningKey} from './nativeCuttingLearning'
import {cuttingInputChangedEvent,holdCuttingInput} from './nativeCuttingInputs'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {groupId,actorId,rollId,requestId,context,inputWorkspace,workspace,reply,checkIntent} from '../tests/fixtures/cuttingLearning'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,scope:string
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const auth=structuredClone(recoveryIdentity);Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST'});Object.assign(auth.identity.profile,{authUserId:actorId});auth.identity.permissions.push('production.cutting.view','master.product.view','warehouse.stock.view','sales.invoice.view');scope=auth.runtime.projectRef+':'+auth.identity.profile.id;state.auth=auth;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(group:string|null=groupId,sourceKey='1',parentBusy=false){await act(async()=>root.render(<NativeCuttingLearningPanel groupId={group} sourceKey={sourceKey} parentBusy={parentBusy}/>));await flush()}
async function click(label:string){const button=[...container.querySelectorAll('button')].find(b=>b.textContent===label)!;await act(async()=>button.click());await flush()}
it('available range is admitted only with exact actor, roll, policy and disjoint physical folds',()=>{
 expect(parseLearningReply(reply(),checkIntent(),actorId).assessment?.interval?.center_pcs).toBe('51')
 const foreign=workspace();foreign.actor_scope_id=groupId;expect(()=>parseModelWorkspace(foreign,groupId,rollId,actorId)).toThrow()
 const forged=reply();forged.result.model.evaluation.production_go=true;expect(()=>parseLearningReply(forged,checkIntent(),actorId)).toThrow()
 const overlap=reply();overlap.result.model.evaluation.holdout_rows[0].batch_key=overlap.result.model.evaluation.train_rows[0].batch_key;expect(()=>parseLearningReply(overlap,checkIntent(),actorId)).toThrow()
 const tiny=reply();tiny.result.model.evaluation.calibration_rows[0].physical_at='2026-10-02T01:03:00.000001Z';expect(()=>parseLearningReply(tiny,checkIntent(),actorId)).toThrow()
})
it('policy validation preserves decimal precision and rejects unsupported calibration, unknown facts and forged clocks',()=>{
 const value={id:requestId,kind:'MODEL',payload:{action:'POLICY',group_id:groupId,roll_id:rollId,expected_group_version:'1',expected_input_version:'1',expected_policy_id:null,coverage:'0.75',train_batches:'3',calibration_batches:'3',holdout_batches:'3',explicit_review:true}}
 expect(validateLearningIntent(value)).toEqual(value)
 expect(()=>validateLearningIntent({...value,payload:{...value.payload,coverage:'0.750000000000000000000000000000000001'}})).toThrow()
 expect(()=>validateLearningIntent({...value,payload:{...value.payload,coverage:'0.95'}})).toThrow()
 expect(()=>validateLearningIntent({...value,payload:{...value.payload,known_at:'2025-01-01'}})).toThrow()
})
it('reload recovers the identical UUID and payload, then a current403 retires the old quantitative result',async()=>{
 holdLearning(scope,checkIntent());client.rpc.mockResolvedValue({data:reply(),error:null});await mount(null);expect(client.rpc).not.toHaveBeenCalled();await click('Pulihkan penilaian potong')
 expect(client.rpc.mock.calls[0]).toEqual(['erp_cp7_get_cutting_model_request_v1',{p_payload:checkIntent().payload,p_request:requestId}]);expect(heldLearning(scope).pending).toBeNull();expect(container.querySelector('[data-cutting-assessment]')?.textContent).toContain('51–51 pcs')
 client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'Akses sekarang ditolak'}});await click('Periksa sumber penilaian');expect(container.querySelector('[data-cutting-assessment]')).toBeNull();expect(container.querySelector('[data-cutting-policy]')).toBeNull();expect(container.querySelector('[role=alert]')).not.toBeNull()
})
it('a stale recovered Original clears its exact intent without presenting archived numbers as current',async()=>{
 const archived=reply();archived.original_matches_current_history=false;holdLearning(scope,checkIntent());client.rpc.mockResolvedValue({data:archived,error:null});await mount(null);await click('Pulihkan penilaian potong');expect(heldLearning(scope).pending).toBeNull();expect(container.querySelector('[data-cutting-assessment]')).toBeNull();expect(container.textContent).toContain('Sumber sudah berubah')
})
it('lost command response keeps the exact private intent and never repeats a fresh write',async()=>{
 client.rpc.mockImplementation((name:string)=>Promise.resolve(name==='erp_cp7_get_cutting_input_workspace_v1'?{data:inputWorkspace(),error:null}:name==='erp_cp7_get_cutting_model_workspace_v1'?{data:workspace(),error:null}:{data:null,error:{message:'Balasan hilang'}}))
 await mount();await click('Muat penilaian potong');await click('Nilai hasil potong');const held=heldLearning(scope);expect(held.pending?.kind).toBe('MODEL');const sent=client.rpc.mock.calls.find(([name])=>name==='erp_cp7_capture_cutting_model_v1')!
 client.rpc.mockResolvedValue({data:{...reply(),result:{...reply().result,request_id:held.pending!.id}},error:null});await click('Pulihkan penilaian potong');expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_get_cutting_model_request_v1',sent[1]]);expect(heldLearning(scope).pending).toBeNull();expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_capture_cutting_model_v1')).toHaveLength(1)
})
it('a sibling input intent immediately retires the range and fences learning until that input is recovered',async()=>{
 holdLearning(scope,checkIntent());client.rpc.mockResolvedValue({data:reply(),error:null});await mount(null);await click('Pulihkan penilaian potong');expect(container.querySelector('[data-cutting-assessment]')).not.toBeNull()
 await act(async()=>holdCuttingInput(scope,{id:requestId,payload:{group_id:groupId,expected_group_version:'1',expected_input_version:'1',marker_key:'Susunan',planned_mix:context.planned_mix,roll_inputs:[{roll_id:rollId,family:context.family,width_cm:null}],explicit_review:true}}));await flush()
 expect(container.querySelector('[data-cutting-assessment]')).toBeNull();expect(container.textContent).toContain('Pulihkan rencana potong terlebih dahulu');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Muat penilaian potong')?.disabled).toBe(true)
})
it('late reads, storage changes, parent writes and missing current capabilities retire source data',async()=>{
 let resolve!:(v:unknown)=>void;client.rpc.mockReturnValue(new Promise(r=>{resolve=r}));await mount();await click('Muat penilaian potong');await mount(groupId,'2');await act(async()=>resolve({data:inputWorkspace(),error:null}));await flush();expect(container.textContent).not.toContain('MEREK NYATA')
 localStorage.setItem(cuttingLearningKey(scope),'{broken');await act(async()=>dispatchEvent(new StorageEvent('storage',{key:cuttingLearningKey(scope)})));await flush();expect(container.querySelector('[role=alert]')).not.toBeNull()
 await act(async()=>dispatchEvent(new CustomEvent(cuttingInputChangedEvent,{detail:'another-scope'})));await mount(groupId,'3',true);expect([...container.querySelectorAll('button')].every(b=>b.disabled)).toBe(true)
 const auth=state.auth as typeof recoveryIdentity;auth.identity.permissions=auth.identity.permissions.filter(p=>p!=='warehouse.stock.view');await mount();expect(container.textContent).toBe('')
})
