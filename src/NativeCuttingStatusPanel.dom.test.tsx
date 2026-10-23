// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeCuttingStatusPanel from './NativeCuttingStatusPanel'
import {pendingCuttingStatusPolicies,holdCuttingStatusPolicy,cuttingStatusPolicyPrefix} from './nativeCuttingStatus'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {cuttingStatusFixture,statusGroup,statusActor,statusIntent,statusPolicyReply} from '../tests/fixtures/cuttingStatus'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
function authFixture(){const base=structuredClone(recoveryIdentity);return {...base,runtime:{...base.runtime,mode:'DISPOSABLE_TEST'},
  identity:{...base.identity,profile:{...base.identity.profile,authUserId:statusActor,rowVersion:1,roleRowVersion:1},
    permissions:[...base.identity.permissions,'production.cutting.view','master.product.view','warehouse.stock.view','sales.invoice.view','master.product.manage']}}}
let root:Root,container:HTMLDivElement
const denied=vi.fn()
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();state.auth=authFixture();client.rpc.mockReset();denied.mockReset()
  client.rpc.mockResolvedValue({data:cuttingStatusFixture(),error:null});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(group:string|null=statusGroup,sourceKey='1',parentBusy=false){await act(async()=>root.render(<NativeCuttingStatusPanel groupId={group} sourceKey={sourceKey} parentBusy={parentBusy} onAuthorityLost={denied}/>));await flush()}
async function click(label:string){const button=[...container.querySelectorAll('button')].find(x=>x.textContent===label);expect(button).toBeDefined();await act(async()=>button!.click());await flush()}
async function fill(label:string,next:string){
  const wrapper=[...container.querySelectorAll('label')].find(x=>x.textContent?.startsWith(label))
  const input=wrapper?.querySelector('input') as HTMLInputElement
  expect(input).toBeDefined()
  await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,next);input.dispatchEvent(new Event('input',{bubbles:true}))})
}
it('loads status automatically without a manual assessment or learning capture',async()=>{
  await mount();expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_cutting_status_v1',{p_group:statusGroup})
  expect(container.textContent).toContain('Wajar menurut riwayat');expect(container.textContent).toContain('Total hasil: 100 pcs')
  expect(container.textContent).toContain('80–120 pcs');expect(container.textContent).toContain('seluruh pabrik')
  expect(client.rpc.mock.calls.every(([name])=>name==='erp_cp7_get_cutting_status_v1')).toBe(true)
})
it('draft selection and a pending parent do not present an earlier result as physical completion',async()=>{
  await mount(null);expect(client.rpc).not.toHaveBeenCalled();expect(container.textContent).toContain('Status muncul otomatis')
  await mount();expect(container.textContent).toContain('Wajar menurut riwayat')
  await mount(statusGroup,'1',true);expect(container.textContent).not.toContain('Wajar menurut riwayat');expect(container.textContent).toContain('Menunggu hasil penyimpanan')
})
it('does not guess a policy value and leaves the explicit owner form blank',async()=>{
  const data=cuttingStatusFixture();client.rpc.mockResolvedValue({data:{...data,policy:null,materials:[{...data.materials[0],status:'POLICY_REQUIRED',lower_pcs:null,upper_pcs:null}]},error:null})
  await mount();expect(container.textContent).toContain('Aturan penilaian belum ditetapkan')
  expect([...container.querySelectorAll('input:not([type=checkbox])')].every(x=>(x as HTMLInputElement).value==='')).toBe(true)
  expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_cutting_status_policy_v1')).toHaveLength(0)
})
it('retires a delayed old group response after another cutting is selected',async()=>{
  let resolve!:(v:unknown)=>void;client.rpc.mockImplementation((_name:string,args:{p_group:string})=>args.p_group===statusGroup?new Promise(r=>{resolve=r}):Promise.resolve({data:cuttingStatusFixture(statusActor),error:null}))
  await mount();await mount(statusActor,'2')
  await act(async()=>resolve({data:{...cuttingStatusFixture(),materials:[{...cuttingStatusFixture().materials[0],name:'OLD MATERIAL'}]},error:null}));await flush()
  expect(container.textContent).not.toContain('OLD MATERIAL');expect(container.textContent).toContain('Bahan A')
})
it.each([{code:'42501',message:'Akses ditolak'},{status:401,message:'Sesi berakhir'}])('clears protected facts on current access refusal and does not retry forever: %j',async error=>{
  await mount();client.rpc.mockResolvedValue({data:null,error});await mount(statusGroup,'2')
  expect(container.textContent).not.toContain('Wajar menurut riwayat');expect(container.querySelector('[role=alert]')).not.toBeNull();expect(denied).toHaveBeenCalledTimes(1)
  const calls=client.rpc.mock.calls.length;await mount(statusGroup,'3');await act(async()=>dispatchEvent(new Event('focus')));await flush()
  expect(client.rpc).toHaveBeenCalledTimes(calls)
})
it('recovers the same UUID after reload without making another write',async()=>{
  const intent=statusIntent(),scope='disposable:'+statusActor;holdCuttingStatusPolicy(scope,intent)
  let recovered=false
  client.rpc.mockImplementation((name:string)=>{
    if(name==='erp_cp7_get_cutting_status_policy_request_v1'){recovered=true;return Promise.resolve({data:statusPolicyReply(intent),error:null})}
    const data=cuttingStatusFixture();if(recovered)data.policy.revision='2'
    return Promise.resolve({data,error:null})
  })
  await mount();expect(container.textContent).toContain('Penyimpanan aturan belum dipastikan')
  await click('Periksa aturan tertunda '+intent.requestId.slice(0,8))
  expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_cutting_status_policy_request_v1',{p_payload:intent.payload,p_request:intent.requestId})
  expect(pendingCuttingStatusPolicies(scope)).toEqual([])
  expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_cutting_status_policy_v1')).toHaveLength(0)
  expect(container.textContent).toContain('Aturan versi 2')
})
it('saves only an explicitly reviewed policy and keeps its exact intent after a lost reply',async()=>{
  client.rpc.mockImplementation((name:string)=>Promise.resolve(name==='erp_cp7_get_cutting_status_v1'
    ?{data:cuttingStatusFixture(),error:null}:{data:null,error:{message:'reply lost'}}))
  await mount();await fill('Cakupan rentang riwayat','90');await fill('Minimum kelompok pembanding','5');await fill('Alasan perubahan','Aturan yang saya periksa')
  const check=container.querySelector('input[type=checkbox]') as HTMLInputElement
  await act(async()=>check.click());await click('Simpan aturan hasil potong')
  const writes=client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_cutting_status_policy_v1')
  expect(writes).toHaveLength(1)
  const held=pendingCuttingStatusPolicies('disposable:'+statusActor)
  expect(held).toHaveLength(1);expect(held[0].requestId).toBe(writes[0][1].p_request)
  expect(held[0].payload).toEqual({expected_revision:'1',state:'ACTIVE',coverage:'0.9',min_groups:'5',reason:'Aturan yang saya periksa',explicit_review:true})
  expect(container.textContent).toContain('Penyimpanan aturan belum dipastikan')
  expect(container.textContent).not.toContain('Wajar menurut riwayat')
})
it('damaged recovery state blocks policy writes and an ADMIN only reads status',async()=>{
  localStorage.setItem(cuttingStatusPolicyPrefix('disposable:'+statusActor)+statusGroup,'{broken')
  await mount();expect(container.textContent).toContain('Penyimpanan baru ditahan')
  localStorage.clear();const auth=state.auth as ReturnType<typeof authFixture>;auth.identity.profile.role='ADMIN'
  await mount(statusGroup,'2');expect(container.textContent).toContain('Wajar menurut riwayat')
  expect(container.querySelector('details')).toBeNull()
})
