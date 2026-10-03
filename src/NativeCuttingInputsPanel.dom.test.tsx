// @vitest-environment jsdom
import {act}from'react'
import {createRoot,type Root}from'react-dom/client'
import {beforeEach,afterEach,it,expect,vi}from'vitest'
import NativeCuttingInputsPanel from'./NativeCuttingInputsPanel'
import {parseCuttingInputWorkspace,parseCuttingInputCommand,cuttingInputKey,heldCuttingInput,holdCuttingInput,type CuttingInputIntent}from'./nativeCuttingInputs'
import {recoveryIdentity}from'../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const g='11111111-1111-4111-8111-111111111111',a='22222222-2222-4222-8222-222222222222',r='33333333-3333-4333-8333-333333333333'
const family={brand:'MEREK ASLI',mill:'PABRIK',variant:'JENIS',spec_revision:'1'}
function intent():CuttingInputIntent{return{id:r,payload:{group_id:g,expected_group_version:'1',expected_input_version:null,marker_key:'Susunan',planned_mix:[{size_id:g,drawings:'3'}],roll_inputs:[{roll_id:r,family,width_cm:null}],explicit_review:true}}}
function data(){const group={id:g,po_id:a,version:'1',physical_at:'2025-10-02T01:00:00.123456Z',posted:false,pattern_id:a,pattern_revision:'R1'},anchor={group_id:g,po_id:a,pattern_id:a,pattern_revision:'R1',rolls:[{roll_id:r,material_id:a,unit:'YARD'}],size_ids:[g]};return{contract_version:'cp7.native-cutting-input-workspace.v1',actor_scope_id:a,requested_group_id:g,size_labels:{[g]:'SIZE-NATIVE'},roll_labels:{[r]:'MATERIAL-NATIVE'},group,anchor,record:{id:r,actor_scope_id:a,group_id:g,request_id:r,version:'1',previous_id:null,known_at:'2026-10-02T01:00:00.123456Z',native_anchor:structuredClone(anchor),original_native_group:structuredClone(group),values:{rolls:[{roll_id:r,material_id:a,context:{family,pattern_id:a,pattern_revision:'R1',marker_key:'Susunan',unit:'YARD',planned_mix:[{size_id:g,drawings:'1'}]},width_cm:null,width_basis:'UNKNOWN'}],planned_mix:[{size_id:g,drawings:'1'}],provenance:'EXPLICIT_OPERATOR_INPUT_BOUND_TO_NATIVE_IDENTITIES',output_mix_is_not_preknown_planned_mix:true,automatic_activation:false,business_write:false,production_go:false}},record_matches_native_identity:true,preknown_before_physical:false,can_record:true,model_qualified:false,automatic_activation:false,business_write:false,production_go:false}}
function reply(){return{contract_version:'cp7.native-cutting-input-command.v1',result:{status:'COMMITTED',request_id:r,record:data().record},current:data(),business_write:false,automatic_activation:false,production_go:false}}
let root:Root,container:HTMLDivElement,scope:string
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const auth=structuredClone(recoveryIdentity);Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST'});auth.identity.permissions.push('production.cutting.view','master.product.view','warehouse.stock.view','sales.invoice.view');scope=auth.runtime.projectRef+':'+auth.identity.profile.id;state.auth=auth;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(groupId:string|null=g,sourceKey='source1',parentBusy=false){await act(async()=>root.render(<NativeCuttingInputsPanel groupId={groupId} sourceKey={sourceKey} parentBusy={parentBusy}/>));await flush()}
async function click(text:string){const button=[...container.querySelectorAll('button')].find(b=>b.textContent===text)!;await act(async()=>button.click());await flush()}
it('receiver preserves Native identity/unit, null width and late real clock; fake qualification and conflicting microsecond proof refuse',()=>{
 const p=parseCuttingInputWorkspace(data(),g);expect(p.record?.values.rolls[0].context.unit).toBe('YARD');expect(p.record?.values.rolls[0].width_cm).toBeNull();expect(p.preknown_before_physical).toBe(false)
 const forged=data();forged.preknown_before_physical=true;expect(()=>parseCuttingInputWorkspace(forged,g)).toThrow()
 const micros=data();micros.group.physical_at='2026-10-02T01:00:00.123456Z';micros.record.known_at='2026-10-02T01:00:00.123455Z';micros.preknown_before_physical=true;expect(parseCuttingInputWorkspace(micros,g).preknown_before_physical).toBe(true);micros.record.known_at='2026-10-02T01:00:00.123457Z';expect(()=>parseCuttingInputWorkspace(micros,g)).toThrow()
 const qualified=data();qualified.model_qualified=true;expect(()=>parseCuttingInputWorkspace(qualified,g)).toThrow()
 const missing={...data(),group:null,anchor:null,size_labels:{},roll_labels:{},record_matches_native_identity:false,preknown_before_physical:false,can_record:false};expect(parseCuttingInputWorkspace(missing,g).record?.id).toBe(r)
})
it('command receiver rejects a foreign actor, changed operator family and arbitrary decimal/revision rather than clearing an uncertain intent',()=>{
 expect(parseCuttingInputCommand(reply(),intent()).result.status).toBe('COMMITTED');const actor=reply();actor.result.record.actor_scope_id=g;expect(()=>parseCuttingInputCommand(actor,intent())).toThrow();const width=reply();Object.assign(width.result.record.values.rolls[0],{width_cm:'175.250',width_basis:'OPERATOR_RECORDED_NOT_INFERRED'});expect(()=>parseCuttingInputCommand(width,intent())).toThrow();const revision=reply();revision.result.record.version='2';expect(()=>parseCuttingInputCommand(revision,intent())).toThrow()
})
it('reload with no selected draft recovers only the same private intent, then current403 retires every displayed input fact',async()=>{
 holdCuttingInput(scope,intent());await mount(null);expect(client.rpc).not.toHaveBeenCalled();client.rpc.mockResolvedValue({data:reply(),error:null});await click('Pulihkan rencana potong');expect(client.rpc.mock.calls[0]).toEqual(['erp_cp7_get_cutting_input_request_v1',{p_payload:intent().payload,p_request:r}]);expect(heldCuttingInput(scope).pending).toBeNull();expect(container.textContent).toContain('MEREK ASLI');expect(container.textContent).toContain('setelah waktu potong');client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'Akses sekarang ditolak'}});await click('Periksa sumber rencana');expect(container.textContent).not.toContain('MEREK ASLI');expect(container.querySelector('[role=alert]')).not.toBeNull();expect(client.rpc.mock.calls.map(c=>c[0])).not.toContain('erp_cp7_record_cutting_inputs_v1')
})
it('late current read is retired when Native source selection changes, preserving the uncertain operator-only intent',async()=>{
 let resolve!:(r:unknown)=>void;client.rpc.mockReturnValue(new Promise(r=>{resolve=r}));await mount();await click('Muat rencana potong');await mount(g,'source2');await act(async()=>resolve({data:data(),error:null}));await flush();expect(container.textContent).not.toContain('MEREK ASLI');holdCuttingInput(scope,intent());await act(async()=>dispatchEvent(new StorageEvent('storage',{key:cuttingInputKey(scope)})));await mount(g,'source3',true);expect(heldCuttingInput(scope).pending).toEqual(intent());expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Pulihkan rencana potong')?.disabled).toBe(true)
})
it('the existing Native draft-edit capability enables input; view-only access keeps the form read-only',async()=>{
 client.rpc.mockResolvedValue({data:data(),error:null});await mount();await click('Muat rencana potong');expect(container.querySelector<HTMLInputElement>('fieldset input')?.disabled).toBe(false);expect(container.querySelector<HTMLFieldSetElement>('fieldset')?.disabled).toBe(false)
 const auth=state.auth as typeof recoveryIdentity;auth.identity.permissions=auth.identity.permissions.filter(p=>p!=='production.cutting.edit_draft');await mount();await click('Muat rencana potong');expect(container.querySelector<HTMLFieldSetElement>('fieldset')?.disabled).toBe(true);expect(client.rpc.mock.calls.every(([name])=>name==='erp_cp7_get_cutting_input_workspace_v1')).toBe(true)
})
it('corrupt storage blocks duplicate writes and missing current capability prevents any RPC or fact render',async()=>{
 localStorage.setItem(cuttingInputKey(scope),'{broken');await mount();expect(container.querySelector('[role=alert]')).not.toBeNull();expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Muat rencana potong')?.disabled).toBe(true);const auth=structuredClone(recoveryIdentity);Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST'});state.auth=auth;await mount();expect(container.textContent).toBe('');expect(client.rpc).not.toHaveBeenCalled()
})
