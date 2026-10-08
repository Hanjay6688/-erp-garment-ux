// @vitest-environment jsdom
import{act}from'react'
import{createRoot,type Root}from'react-dom/client'
import{beforeEach,afterEach,it,expect,vi}from'vitest'
import NativeHistoryYieldPolicyPanel from'./NativeHistoryYieldPolicyPanel'
import{recoveryIdentity}from'../tests/fixtures/productionRecovery'
import{policyRow,policyWorkspace}from'../tests/fixtures/nativeHistoryYield'
import{readYieldPolicyRequest}from'./nativeHistoryYieldPolicy'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
const scope='cp6-disposable:actor-1'
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear();const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});a.identity.permissions.push('master.product.view','master.product.manage','production.wip.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()})
async function render(){await act(async()=>root.render(<NativeHistoryYieldPolicyPanel onClose={()=>{}}/>))}
async function click(label:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===label)!;await act(async()=>b.click())}
async function fill(label:string,value:string){const e=container.querySelector<HTMLInputElement|HTMLTextAreaElement>(`[aria-label="${label}"]`)!;await act(async()=>{Object.getOwnPropertyDescriptor(e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))})}
const value=(label:string)=>(container.querySelector(`[aria-label="${label}"]`)as HTMLInputElement).value
it('shows the owner-approved package, not in force until saved, and saves it as version 1',async()=>{
 let saved=false
 client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_payload:Record<string,string>})=>name==='erp_cp7_get_history_yield_policy_v1'
  ?{data:policyWorkspace(saved?[policyRow('1','ACTIVE')]:[]),error:null}
  :(saved=true,{data:{contract_version:'cp7.history-yield-policy-outcome.v1',request_id:args.p_request,policy:{...policyRow('1','ACTIVE'),reason:args.p_payload.reason}},error:null}))
 await render()
 expect(container.textContent).toContain('Paket keputusan owner 8 Okt 2026: 180 hari, minimal 5 grup selesai dan 200 PCS potong, batas bawah 90%. Berlaku setelah disimpan.')
 expect(container.querySelector('[data-policy-state]')?.getAttribute('data-policy-state')).toBe('PENDING_POLICY_VALUE')
 expect([value('Jendela histori hari'),value('Minimal grup selesai'),value('Minimal PCS potong')]).toEqual(['180','5','200'])
 await fill('Alasan kebijakan yield','Keputusan owner 8 Okt 2026');await click('Simpan kebijakan yield')
 const call=client.rpc.mock.calls.find(([n])=>n==='erp_cp7_save_history_yield_policy_v1')!
 expect(call[1].p_payload).toEqual({expected_revision:'0',state:'ACTIVE',window_days:'180',min_groups:'5',min_cut_pcs:'200',confidence:'0.90',reason:'Keputusan owner 8 Okt 2026'})
 expect(container.textContent).toContain('Kebijakan versi 1 tersimpan (aktif).');expect(readYieldPolicyRequest(scope).pending).toBeNull()
 expect(container.querySelector('[data-policy-state]')?.getAttribute('data-policy-state')).toBe('ACTIVE')
})
it('keeps the same request through a lost reply and repeats it unchanged',async()=>{
 client.rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_history_yield_policy_v1'?{data:policyWorkspace(),error:null}:{data:null,error:Error('reply lost')})
 await render();await fill('Alasan kebijakan yield','alasan');await click('Simpan kebijakan yield')
 const first=client.rpc.mock.calls.find(([n])=>n==='erp_cp7_save_history_yield_policy_v1')!;expect(readYieldPolicyRequest(scope).pending?.id).toBe(first[1].p_request)
 client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>name==='erp_cp7_get_history_yield_policy_v1'?{data:policyWorkspace([policyRow('1','ACTIVE')]),error:null}
  :{data:{contract_version:'cp7.history-yield-policy-outcome.v1',request_id:args.p_request,policy:{...policyRow('1','ACTIVE'),reason:'alasan'}},error:null})
 await click('Ulangi simpan kebijakan yang sama')
 expect(client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_history_yield_policy_v1')[1]).toEqual(first);expect(readYieldPolicyRequest(scope).pending).toBeNull()
})
it('lets a viewer read the versions but not save',async()=>{
 client.rpc.mockResolvedValue({data:policyWorkspace([policyRow('2','PAUSED'),policyRow('1','ACTIVE')],false),error:null});await render()
 expect(container.textContent).toContain('Dijeda: histori tidak dipakai');expect(container.textContent).toContain('Hanya pemilik atau admin');expect(container.querySelectorAll('[data-revision]').length).toBe(2)
 expect((container.querySelector('fieldset')as HTMLFieldSetElement).disabled).toBe(true)
})
