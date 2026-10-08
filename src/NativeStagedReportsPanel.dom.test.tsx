// @vitest-environment jsdom
// Business Report v2 panel: synthetic DOM checks. Native, race and HTTP
// evidence is the P19 report v2 suite.
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeStagedReportsPanel from './NativeStagedReportsPanel'
import * as f from '../tests/fixtures/nativeStagedReports'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const scope='analysis:cp6-disposable:actor-1',key='erp.cp7.report-request.v2:'+scope
let root:Root,container:HTMLDivElement,units:number,outcome:'DONE'|'FAILED'
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();units=0;outcome='DONE'
 state.auth={runtime:{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'},identity:{status:'AUTHORIZED',profile:{id:'actor-1',authUserId:f.actor,role:'OWNER'},permissions:[]}}
 container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()})
async function render(ownerReports=false){await act(async()=>root.render(<NativeStagedReportsPanel staged={f.staged} blocked={false} financeAccess={{ownerReports,preflight:false}}/>))}
function button(name:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===name);expect(b,`button ${name}`).toBeTruthy();return b!}
async function click(name:string){await act(async()=>button(name).click());await settle()}
// Hash checks use crypto.subtle, which resolves outside React's act queue.
async function settle(){for(let i=0;i<20;i++)await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function fill(label:string,value:string){await act(async()=>{const node=container.querySelector(`[aria-label="${label}"]`) as HTMLInputElement|HTMLTextAreaElement;expect(node).toBeTruthy()
 const proto=node instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(node,value);node.dispatchEvent(new Event('input',{bubbles:true}))})}
async function check(label:string){await act(async()=>(container.querySelector(`[aria-label="${label}"]`) as HTMLInputElement).click())}
function reply(name:string,args:{p_request?:string;p_payload?:Record<string,unknown>;p_index?:number}){let data:unknown
 const extra=(args.p_payload?.finance==='INCLUDED'?{finance:'INCLUDED'}:{})
 if(name==='erp_cp7_publish_report_v2'||name==='erp_cp7_get_report_request_v2')data={...f.job(units),request_id:args.p_request,...extra}
 else if(name==='erp_cp7_step_report_v2'){units++;data=units===3&&outcome==='FAILED'?{...f.job(units,'FAILED'),request_id:args.p_request}:{...f.job(units,units===5?'DONE':'RUNNING'),request_id:args.p_request,...extra}}
 else if(name==='erp_cp7_read_report_v2')data=f.report();else if(name==='erp_cp7_read_report_section_v2')data=f.section(args.p_index!)
 else if(name==='erp_cp7_list_reports_v2')data=f.index();else throw Error('Unexpected RPC '+name)
 return Promise.resolve({data,error:null})}
async function publish(){await fill('Judul laporan bertahap','Briefing pagi');await fill('Alasan laporan bertahap','Ditinjau dari analisis bertahap');await check('Laporan bertahap sudah ditinjau');await click('Buat laporan dari analisis ini')}
it('publishes a reviewed report step by step, then shows the sealed summary with its snapshot time and one section on demand',async()=>{
 client.rpc.mockImplementation(reply);await render();expect(client.rpc).not.toHaveBeenCalled()
 const region=container.querySelector('[aria-label="Laporan analisis bertahap"]')!
 expect(region.textContent).toContain('Laporan memakai data analisis per');expect(region.textContent).toContain('bukan angka saat ini')
 expect(container.querySelector('[aria-label="Sertakan keuangan dan HPP pada laporan bertahap"]')).toBeNull()
 await publish()
 const names=client.rpc.mock.calls.map(c=>c[0])
 expect(names).toEqual(['erp_cp7_publish_report_v2','erp_cp7_step_report_v2','erp_cp7_step_report_v2','erp_cp7_step_report_v2','erp_cp7_step_report_v2','erp_cp7_step_report_v2','erp_cp7_read_report_v2'])
 const sent=client.rpc.mock.calls[0][1];expect(sent.p_payload).toEqual({...f.payload(),title:'Briefing pagi',reason:'Ditinjau dari analisis bertahap'})
 expect(new Set(client.rpc.mock.calls.slice(1,6).map(c=>c[1].p_request))).toEqual(new Set([sent.p_request]))
 const article=container.querySelector('[aria-label="Isi laporan bertahap"]')!
 expect(article.getAttribute('data-freshness-state')).toBe('CHANGES_RECORDED');expect(article.textContent).toContain('ada 3 perubahan tercatat sejak data diambil')
 expect(container.querySelector('[aria-label="Ringkasan laporan bertahap"]')?.textContent).toBe(f.summary)
 expect(localStorage.getItem(key)).toBeNull();expect(container.textContent).toContain('Laporan tersimpan.')
 await click('Buka bagian laporan');expect(container.querySelector('[aria-label="Bagian laporan bertahap"]')?.textContent).toBe(f.sectionBodies[0])
 expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_read_report_section_v2',{p_id:f.publication,p_index:0,p_access:'f'.repeat(64)}])
 expect(container.textContent).not.toMatch(/terkini/i);expect(names.some(n=>n.endsWith('_v1'))).toBe(false)
})
it('includes finance only for an owner report reader who chooses it',async()=>{
 client.rpc.mockImplementation(reply);await render(true);await check('Sertakan keuangan dan HPP pada laporan bertahap');await publish()
 expect(client.rpc.mock.calls[0][1].p_payload.finance).toBe('INCLUDED')
})
it('shows a failed job in plain words and closes the pending request; nothing is read',async()=>{
 outcome='FAILED';client.rpc.mockImplementation(reply);await render();await publish()
 expect(container.querySelector('[role="alert"]')?.textContent).toContain('Hak akses berubah selama laporan disusun. Tidak ada laporan yang disimpan.')
 expect(client.rpc.mock.calls.some(c=>c[0]==='erp_cp7_read_report_v2')).toBe(false);expect(localStorage.getItem(key)).toBeNull()
})
it('keeps a lost reply pending and resumes the same request after a reload',async()=>{
 client.rpc.mockImplementation((n:string,a:{p_request?:string})=>n==='erp_cp7_step_report_v2'&&units===2?Promise.reject(Error('network')):reply(n,a))
 await render();await publish();const held=JSON.parse(localStorage.getItem(key)!);expect(held.payload.title).toBe('Briefing pagi')
 await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockReset();client.rpc.mockImplementation(reply);await render()
 expect(container.textContent).toContain('Ada laporan dari analisis ini yang belum selesai disusun.')
 expect(button('Buat laporan dari analisis ini').disabled).toBe(true)
 await click('Lanjutkan laporan yang tertunda');expect(client.rpc.mock.calls[0]).toEqual(['erp_cp7_publish_report_v2',{p_payload:held.payload,p_request:held.id}])
 expect(container.querySelector('[aria-label="Isi laporan bertahap"]')).toBeTruthy();expect(localStorage.getItem(key)).toBeNull()
})
it('lists the actor\'s staged reports and starts a revision of the latest in the same series and kind',async()=>{
 client.rpc.mockImplementation(reply);await render();await click('Muat laporan bertahap tersimpan');await click('Briefing pagi · versi 1 · data per '+container.querySelector('[aria-label="Buka laporan bertahap 1"]')!.textContent!.split('data per ')[1])
 await click('Buat revisi dari laporan ini');await fill('Judul laporan bertahap','Briefing pagi (revisi)');await fill('Alasan laporan bertahap','Revisi');await check('Laporan bertahap sudah ditinjau')
 units=0;client.rpc.mockImplementation((n:string,a:{p_request?:string;p_payload?:Record<string,unknown>})=>n==='erp_cp7_publish_report_v2'?Promise.resolve({data:{...f.job(0),request_id:a.p_request,revision:'2'},error:null}):reply(n,a))
 await click('Simpan revisi laporan bertahap')
 const p=client.rpc.mock.calls.find(c=>c[0]==='erp_cp7_publish_report_v2')![1].p_payload;expect([p.series_id,p.expected_revision,p.kind]).toEqual([f.series,'1','DAILY'])
})
