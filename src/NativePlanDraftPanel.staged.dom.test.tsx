// @vitest-environment jsdom
// Plan v2 from a staged snapshot: synthetic DOM checks with the real shared
// mutation/recovery hook. Native, race and HTTP evidence is the P19 plan v2 suite.
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativePlanDraftPanel from './NativePlanDraftPanel'
import {recoveryIdentity,cuttingCommit} from '../tests/fixtures/productionRecovery'
import * as f from '../tests/fixtures/nativePlan'
import {readProductionRecovery,productionKey} from './productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const scope='cp6-disposable:actor-1',start=vi.fn(),end=vi.fn(),close=vi.fn()
let root:Root,container:HTMLDivElement,applied:boolean
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();start.mockReset();end.mockReset();close.mockReset();applied=false;const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:f.actor});a.identity.permissions.push('master.product.view','warehouse.stock.view','sales.invoice.view','production.cutting.view');state.auth=a;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function render(){await act(async()=>root.render(<NativePlanDraftPanel context={f.stagedContext} onSourceReadStart={start} onSourceReadEnd={end} onClose={close}/>))}
function button(name:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===name);expect(b,`button ${name}`).toBeTruthy();return b!}
async function click(name:string){await act(async()=>button(name).click())}
async function fill(label:string,value:string){await act(async()=>{const node=container.querySelector(`[aria-label="${label}"]`) as HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement;expect(node).toBeTruthy();const proto=node instanceof HTMLSelectElement?HTMLSelectElement.prototype:node instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(node,value);node.dispatchEvent(new Event('input',{bubbles:true}));node.dispatchEvent(new Event('change',{bubbles:true}))})}
async function check(label:string){await act(async()=>(container.querySelector(`[aria-label="${label}"]`) as HTMLInputElement).click())}
let live=f.stagedPreview()
function appliedWire(request:string){return{contract_version:'cp7.plan-apply-outcome.v2',actor_scope_id:f.actor,request_id:request,draft_id:f.draft,revision:'1',target_key:f.stagedContext.targetKey,identity_hash:f.identityHash,data_as_of:f.dataAsOf,live:live.live,state:'NATIVE_DRAFT_CREATED',kind:'COMMITTED_OUTCOME',intent_id:f.order,physical_production_confirmed:false,reservation_created:false,production_go:false,native:{...cuttingCommit('SAVE_DRAFT'),cutting_group_id:f.pattern,group_number:'SYNTHETIC-CUT'}}}
function reply(name:string,args:{p_request?:string}){let data:unknown
 if(name==='erp_cp7_get_plan_options_v2')data=f.stagedOptions();else if(name==='erp_cp7_save_plan_draft_v2')data=f.stagedSaveOutcome(args.p_request!)
 else if(name==='erp_cp7_read_plan_draft_v2')data=applied?{...f.stagedSaved(),state:'NATIVE_DRAFT_CREATED',native_intent:{id:f.order,cutting_group_id:f.pattern,group_number:'SYNTHETIC-CUT',material_issue_posted:false}}:f.stagedSaved()
 else if(name==='erp_cp7_preview_plan_action_v2')data=live;else if(name==='erp_cp7_apply_plan_action_v2'){applied=true;data=appliedWire(args.p_request!)}else throw Error('Unexpected RPC '+name)
 return Promise.resolve({data,error:null})}
async function form(){await click('Muat pilihan Potongan dari ERP');await fill('Gudang bahan rencana',f.location);await click('Muat pilihan Potongan dari ERP');await fill('PO rencana',f.order);await fill('Pola rencana',f.pattern);await fill('Waktu pencatatan draf WIB','2026-10-08T15:00:00');await click('Pilih roll SYNTHETIC-ROLL');await fill('Keluar roll rencana 1','1');await fill('Terpakai roll rencana 1','0.5');await fill('Sisa roll rencana 1','0.5');await fill('Hasil roll rencana 1','60');await fill('Alasan rencana Potongan','Dari analisis bertahap');await check('Asumsi dan komposisi rencana sudah diperiksa')}
async function inspect(){await click('Periksa pratinjau rencana');await fill('Alasan membuat draf Potongan','Pratinjau terkini sudah diperiksa');await check('Pratinjau sudah diperiksa untuk membuat draf')}
beforeEach(()=>{live=f.stagedPreview()})
it('plans from the dated snapshot through the v2 commands only, and states the snapshot time and the live recheck',async()=>{
 client.rpc.mockImplementation(reply);await render();expect(client.rpc).not.toHaveBeenCalled()
 expect(container.querySelector('[data-plan-kind="STAGED"]')?.textContent).toContain('Rencana dari analisis bertahap: data per')
 await form();expect(container.textContent).toContain('bukan angka saat ini');expect(container.textContent).not.toMatch(/terkini/i)
 await click('Simpan rencana Potongan')
 const save=client.rpc.mock.calls.find(c=>c[0]==='erp_cp7_save_plan_draft_v2')![1];expect(save.p_payload.identity_hash).toBe(f.identityHash);expect(save.p_payload).not.toHaveProperty('source_hash')
 await inspect();expect(container.querySelector('[aria-label="Pemeriksaan ulang rencana"]')?.getAttribute('data-apply-ready')).toBe('true')
 expect(container.textContent).toContain('Kebutuhan sekarang: 100 PCS')
 // A plan from a staged run has no whole Original to compare against.
 expect([...container.querySelectorAll('button')].some(b=>b.textContent==='Bandingkan rencana dengan hasil produksi')).toBe(false)
 await click('Buat draf Potongan di ERP');expect(container.textContent).toContain('draf Potongan sudah dibuat')
 expect(client.rpc.mock.calls.map(c=>c[0]).filter(n=>n.endsWith('_v1'))).toEqual([])
 expect(readProductionRecovery(scope).pending).toEqual({});expect(localStorage.getItem('erp.cp7.plan-pointer.v2:'+scope)).toBe(JSON.stringify({id:f.draft}))
 expect(localStorage.getItem('erp.cp7.plan-pointer.v1:'+scope)).toBeNull();expect(start.mock.calls.length).toBe(end.mock.calls.length)
})
it('names what changed and keeps the draft button disabled when the recheck refuses (stock up, need below the plan)',async()=>{
 live=f.stagedPreview('50');client.rpc.mockImplementation(reply);await render();await form();await click('Simpan rencana Potongan');await inspect()
 const box=container.querySelector('[aria-label="Pemeriksaan ulang rencana"]')!;expect(box.getAttribute('data-apply-ready')).toBe('false')
 expect(box.textContent).toContain('Kebutuhan sekarang: 55 PCS (saat data diambil 100 PCS)');expect(box.textContent).toContain('Stok barang jadi 5 → 50 PCS')
 expect([...box.querySelectorAll('[data-check]')].map(e=>e.getAttribute('data-check'))).toEqual(['NEED'])
 expect(button('Buat draf Potongan di ERP').disabled).toBe(true);expect(client.rpc.mock.calls.some(c=>c[0]==='erp_cp7_apply_plan_action_v2')).toBe(false)
})
it('shows the server refusal at apply in plain words with its numbers, and keeps a v1 envelope apart',async()=>{
 client.rpc.mockImplementation(reply);await render();await form();await click('Simpan rencana Potongan');await inspect()
 client.rpc.mockImplementation((n:string,a:{p_request?:string})=>n==='erp_cp7_apply_plan_action_v2'?Promise.resolve({data:null,error:{code:'40001',message:'CP7_PLAN_V2_NEED_CHANGED',details:JSON.stringify({code:'CP7_PLAN_V2_NEED_CHANGED',need_now_pcs:'40',selected_new_pcs:'60',increase_pcs:'60'})}}):reply(n,a))
 await click('Buat draf Potongan di ERP')
 expect(container.textContent).toContain('Kebutuhan sekarang 40 pcs, rencana 60 pcs (stok barang jadi dan barang dalam proses naik 60 pcs sejak data diambil). Tinjau ulang rencana.')
 expect(localStorage.getItem(productionKey(scope,'PLAN_APPLY'))).toBeNull()
})
