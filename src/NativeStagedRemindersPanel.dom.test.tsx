// @vitest-environment jsdom
// Reminders v2 panel: synthetic DOM checks; the Native and HTTP evidence is the P19 reminders v2 suite.
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeStagedRemindersPanel from './NativeStagedRemindersPanel'
import * as f from '../tests/fixtures/nativeStagedReminders'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
const scope='analysis:cp6-disposable:actor-1'
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear()
 state.auth={runtime:{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'},identity:{status:'AUTHORIZED',profile:{id:'actor-1',authUserId:f.actor,role:'OWNER'},permissions:[]}}
 container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
async function settle(){for(let i=0;i<20;i++)await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function render(){await act(async()=>root.render(<NativeStagedRemindersPanel staged={f.staged} blocked={false}/>));await settle()}
async function click(name:string,within:ParentNode=container){const b=[...within.querySelectorAll('button')].find(x=>x.textContent===name||x.getAttribute('aria-label')===name);expect(b,name).toBeTruthy();await act(async()=>b!.click());await settle()}
function server(o:{manage?:boolean;claim?:(p:Record<string,unknown>,id:string)=>unknown}={}){
 const steps=[f.setStatus('RUNNING',1),f.setStatus('RUNNING',2),f.setStatus('DONE',3)]
 client.rpc.mockImplementation((name:string,a:Record<string,any>)=>{
  const ok=(data:unknown)=>Promise.resolve({data,error:null})
  if(name==='erp_cp7_step_reminder_conditions_v2')return ok(steps.shift()??f.setStatus('DONE',3))
  if(name==='erp_cp7_get_reminder_workspace_v2')return ok(f.workspace(o.manage??true))
  if(name==='erp_cp7_read_reminder_conditions_v2')return ok(f.page(a.p_query))
  if(name==='erp_cp7_recheck_reminder_v2')return ok(f.liveRecheck('STILL_OPEN',f.keys.indexOf(a.p_condition.slice('PRODUCTION_GAP:'.length))+1))
  if(name==='erp_cp7_claim_reminder_v2')return ok(o.claim!(a.p_payload,a.p_request))
  return Promise.resolve({data:null,error:{message:'unexpected '+name}})})
}
it('prepares the conditions step by step, rechecks one now and records a resolved one as not billed; only v2 calls',async()=>{
 server({claim:(_p,id)=>f.command('CLAIM',id,{status:'COMMITTED',outcome:'NOT_SENT',verdict:'RESOLVED_NOW',recheck_id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd',claim_id:null,fence:null},null,f.recheck('RESOLVED_NOW'))})
 await render();expect(container.textContent).toContain('data analisis per');expect(container.textContent).toContain('yang sudah selesai sejak analisis tidak ditagih')
 await click('Siapkan daftar pengingat')
 expect(container.querySelector('[aria-label="Pengingat dari analisis bertahap"]')?.getAttribute('data-set-state')).toBe('DONE')
 expect(container.textContent).toContain('Daftar pengingat siap: 3 kondisi dari 3 target.')
 const item=container.querySelector(`[data-condition-key="PRODUCTION_GAP:${f.keys[0]}"]`)!
 await click('Periksa ulang sekarang SKU-1 · Produk 1',item)
 expect(item.querySelector('[data-verdict="STILL_OPEN"]')?.textContent).toContain('Masih perlu: kurang sedikitnya 4 PCS sekarang')
 await click('Buat pratinjau lokal SKU-1 · Produk 1',item)
 expect(container.textContent).toContain('Tidak dibuat pratinjau. Sudah selesai sejak analisis — tidak ditagih')
 const claimCall=client.rpc.mock.calls.find(c=>c[0]==='erp_cp7_claim_reminder_v2')!
 expect(claimCall[1].p_payload).toEqual({run_id:f.run,identity_hash:f.identityHash,condition_key:'PRODUCTION_GAP:'+f.keys[0],condition_hash:'1'.repeat(64),binding_id:f.bindingId})
 expect(client.rpc.mock.calls.every(c=>String(c[0]).endsWith('_v2'))).toBe(true)
 expect(localStorage.getItem('erp.cp7.reminder-v2-request.v1:'+scope)).toBeNull();expect(container.textContent).not.toMatch(/terkini/i)
})
it('shows a claimed preview with the snapshot time and the recheck',async()=>{
 server({claim:(_p,id)=>f.command('CLAIM',id,{status:'COMMITTED',outcome:'CLAIMED',verdict:'STILL_OPEN',recheck_id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd',claim_id:f.claimId,fence:f.fence},f.claim(),f.recheck('STILL_OPEN'))})
 await render();await click('Siapkan daftar pengingat')
 await click('Buat pratinjau lokal SKU-1 · Produk 1',container.querySelector(`[data-condition-key="PRODUCTION_GAP:${f.keys[0]}"]`)!)
 const article=container.querySelector('[aria-label="Pratinjau lokal pengingat"]')!
 expect(article.getAttribute('data-claim-status')).toBe('CLAIMED');expect(article.textContent).toContain('Data analisis per 2026-10-08 08:00:00 WIB');expect(article.textContent).toContain('Diperiksa ulang')
})
it('lets a viewer read and recheck but not claim or change settings',async()=>{
 server({manage:false});await render();await click('Siapkan daftar pengingat')
 expect(container.querySelectorAll('button[aria-label^="Buat pratinjau lokal"]').length).toBe(0)
 expect(container.querySelectorAll('button[aria-label^="Periksa ulang sekarang"]').length).toBe(3)
 expect(container.textContent).toContain('tidak bisa membuat pratinjau atau mengubah pengaturan');expect(container.textContent).not.toContain('Tujuan dan pengaturan pengingat')
})
it('keeps a pending request and closes it by lookup without sending anything new',async()=>{
 const r={id:'12345678-1234-4234-8234-123456789012',operation:'CLAIM',runId:f.run,payload:{run_id:f.run,identity_hash:f.identityHash,condition_key:'PRODUCTION_GAP:'+f.keys[0],condition_hash:'1'.repeat(64),binding_id:f.bindingId}}
 localStorage.setItem('erp.cp7.reminder-v2-request.v1:'+scope,JSON.stringify(r))
 client.rpc.mockImplementation((name:string,a:Record<string,any>)=>Promise.resolve(name==='erp_cp7_get_reminder_request_v2'?{data:f.command('CLAIM',a.p_request,{status:'NOT_COMMITTED',outcome:null,verdict:null,recheck_id:null,claim_id:null,fence:null}),error:null}
  :name==='erp_cp7_get_reminder_workspace_v2'?{data:f.workspace(true),error:null}:{data:null,error:{message:'unexpected '+name}}))
 await render();expect(container.textContent).toContain('Ada permintaan pengingat yang belum pasti hasilnya')
 await click('Periksa hasil permintaan pengingat')
 expect(client.rpc.mock.calls[0]).toEqual(['erp_cp7_get_reminder_request_v2',{p_payload:r.payload,p_request:r.id,p_operation:'CLAIM'}])
 expect(container.textContent).toContain('Server memastikan permintaan lama belum tersimpan');expect(localStorage.getItem('erp.cp7.reminder-v2-request.v1:'+scope)).toBeNull()
})
