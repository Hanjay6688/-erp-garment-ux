// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeAnalysisPanel from './NativeAnalysisPanel'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {stagedRun,rehash} from '../tests/fixtures/nativeAnalysisPages'
import {readStagedRequest,stagedRequestKey,stagedCompletedScope} from './nativeStagedJob'
import {readNativeDemandRequest} from './nativeDemandHistory'
import type {NativeDemandQuery} from './nativeDemandHistory'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
// Byte-adaptive pages are uneven: 500, 450 and 250 targets of 1,200.
const scope='analysis:cp6-disposable:actor-1',SIZES=[500,450,250],STAGED='Analisis bertahap (hingga 5.000 target)'
type Args={p_request?:string;p_run?:string;p_index?:number;p_access?:string;p_query?:unknown}
type Staged=Awaited<ReturnType<typeof stagedRun>>
let s:Staged
beforeEach(async()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear()
 s=await stagedRun({targets:1200,pageSizes:SIZES,unreviewed:7})
 const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:s.actor})
 a.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()})
const q=()=>s.query as NativeDemandQuery
async function render(){await act(async()=>root.render(<NativeAnalysisPanel query={q()} onSourceReadStart={vi.fn()} onSourceReadEnd={vi.fn()} onClose={vi.fn()}/>))}
const button=(text:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===text)
async function click(text:string){const b=button(text)!;expect(b,text).toBeTruthy();await act(async()=>b.click())}
async function tick(text:string){const b=[...container.querySelectorAll('label')].find(l=>l.textContent===text)?.querySelector('input');expect(b).toBeTruthy();await act(async()=>b!.click())}
const names=()=>client.rpc.mock.calls.map(c=>c[0])
const macrotask=()=>new Promise<void>(r=>(globalThis as unknown as {setImmediate:(f:()=>void)=>void}).setImmediate(r))
async function until(done:()=>boolean){const started=Date.now();while(!done()&&Date.now()-started<20000)await act(async()=>{await macrotask()});expect(done()).toBe(true)}
const region=()=>container.querySelector('[role="region"][aria-label="Hasil analisis bertahap"]')
const heading=()=>container.querySelector('[aria-label="Target per halaman"] h3')?.textContent
const rows=()=>container.querySelectorAll('[data-analysis-target]').length
const statuses=()=>[...container.querySelectorAll('[role="status"]')].map(e=>e.textContent??'')
const alertText=()=>container.querySelector('[role="alert"]')?.textContent??''
const RUNNING=(units_done:number,extra:Record<string,unknown>={})=>({data:s.job('RUNNING',{units_done,...extra}),error:null})
// The staged job as the server answers it: request → RUNNING, `steps` steps
// until DONE, status reads, then the page set, pages and the source check.
function server(opts:{steps?:number;page?:(i:number,args:Args)=>unknown;source?:'UNCHANGED'|'ARCHIVED_STALE'}={}){
 let id='',stepped=0;const steps=opts.steps??2
 return async(name:string,args:Args)=>{
  // The run's request id is the job's UUID: the fixture is rebuilt for it.
  if(name==='erp_cp7_request_staged_analysis_v1'){id=args.p_request!;expect(args.p_query).toEqual(q());s=await stagedRun({targets:1200,pageSizes:SIZES,unreviewed:7,requestId:id});return RUNNING(12)}
  if(name==='erp_cp7_get_staged_analysis_v1'){expect(args).toEqual({p_request:id});return stepped>=steps?{data:s.job('DONE'),error:null}:RUNNING(12+stepped)}
  if(name==='erp_cp7_step_staged_analysis_v1'){expect(args).toEqual({p_request:id});stepped++;return stepped<steps?RUNNING(12+stepped):{data:s.job('DONE'),error:null}}
  if(name==='erp_cp7_read_staged_analysis_pages_v1'){expect(args).toEqual({p_run:s.runId});return{data:s.pageSet,error:null}}
  if(name==='erp_cp7_read_staged_analysis_page_v1'){expect(args.p_access).toBe(s.pageSet.access_epoch);return(opts.page??(i=>({data:s.page(i),error:null})))(args.p_index!,args)}
  if(name==='erp_cp7_check_staged_analysis_source_v1'){expect(args).toEqual({p_run:s.runId});return{data:{source_state:opts.source??'UNCHANGED',checked_at:'2026-10-07T10:30:00.000000Z'},error:null}}
  throw Error('unexpected '+name)
 }
}

it('drives a staged job to DONE with the server progress as the busy signal, then shows whole-run totals and uneven target pages with a source check',async()=>{
 let release:(v:unknown)=>void=()=>{};const base=server({steps:1})
 client.rpc.mockImplementation(async(name:string,args:Args)=>{
  if(name==='erp_cp7_step_staged_analysis_v1'&&names().filter(n=>n===name).length===1)return new Promise(r=>{release=r})
  return base(name,args)
 })
 await render();expect(button(STAGED)!.disabled).toBe(false);expect(button('Hitung di latar belakang')).toBeTruthy()
 await click(STAGED);await until(()=>names().includes('erp_cp7_step_staged_analysis_v1'))
 // Busy exactly like the single background job; the progress is the server's.
 expect(button('Tutup analisis bersama')!.disabled).toBe(true);expect(button(STAGED)!.disabled).toBe(true)
 const progress=statuses().find(t=>t.startsWith('Analisis bertahap: tahap '))!
 expect(progress.startsWith('Analisis bertahap: tahap 3 dari 9 (HIST_ROWS) · unit 12 dari 55')).toBe(true);expect(progress).toContain('dimulai jam 16.00.00 WIB')
 const id=client.rpc.mock.calls[0][1].p_request;expect(readStagedRequest(scope).pending).toEqual({id,q:q()});expect(localStorage.getItem('erp.cp7.analysis-staged.v1:'+scope)).toContain(id);expect(region()).toBeNull()
 await act(async()=>{release(RUNNING(13))});await until(()=>Boolean(region())&&rows()>0)
 expect(names()).toEqual(['erp_cp7_request_staged_analysis_v1','erp_cp7_step_staged_analysis_v1','erp_cp7_step_staged_analysis_v1','erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1'])
 expect(client.rpc.mock.calls.at(-1)![1]).toEqual({p_run:s.runId,p_index:0,p_access:'a'.repeat(64)})
 expect(button('Tutup analisis bersama')!.disabled).toBe(false);expect(readStagedRequest(scope).pending).toBeNull();expect(localStorage.getItem(stagedRequestKey(scope))).toBeNull()
 // The region, its run id and summary line as the browser measurement reads them.
 const r=region()!;expect(r.classList.contains('native-analysis-staged')).toBe(true);expect(container.querySelector('.native-analysis-staged .native-analysis-run span')!.textContent).toBe(s.runId)
 expect([...r.querySelectorAll('p')].some(p=>p.textContent!.startsWith('1.200 target dalam 3 halaman.'))).toBe(true)
 // Summary first; every whole-run number is the server's total.
 const summary=r.querySelector('[aria-label="Ringkasan seluruh analisis bertahap"]')!,totals=s.pageSet.totals
 expect(summary.compareDocumentPosition(r.querySelector('[aria-label="Target per halaman"]')!)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
 expect(summary.querySelector('h3')!.textContent).toBe('Ringkasan seluruh analisis · 1.200 target')
 expect(summary.querySelector('[data-total="ACTIVE"]')!.textContent).toBe(`Status produksi aktif: ${totals.recommendations.ACTIVE} target`)
 expect(summary.querySelector('[data-total="POLICY_UNREVIEWED"]')!.textContent).toBe(`Status produksi belum diperiksa: ${totals.policy_unreviewed} target`)
 const first=JSON.parse(s.page(0).body);expect(first.summary.recommendations.ACTIVE).not.toBe(totals.recommendations.ACTIVE)
 expect(heading()).toBe('Target 1–500 dari 1.200');expect(rows()).toBe(first.items.recommendations.length)
 expect(r.textContent).toContain(`Halaman ini hanya memuat target 1–500 dari 1.200: ${first.items.recommendations.length} rekomendasi dan ${first.summary.policy_unreviewed} target`)
 // Nothing presents the page as the whole, and the whole-Original features
 // are stated unavailable: no tabs, report, prompt, plan, stock or finance.
 expect(r.textContent).toContain('belum tersedia untuk analisis bertahap');expect(r.textContent).toContain('Angka keuangan tidak termasuk analisis bertahap')
 expect(container.querySelector('[aria-label="Tampilan analisis bersama"]')).toBeNull();expect(container.querySelector('[aria-label="Isi laporan ERP"]')).toBeNull();expect(container.querySelector('article.native-analysis-result')).toBeNull()
 expect(r.textContent).not.toMatch(/\d dari \d+ produk/);expect(r.textContent).not.toContain('Rencanakan Potongan');expect(r.textContent).not.toContain('Periksa sumber analisis')
 expect(button('Halaman sebelumnya')!.disabled).toBe(true)
 // Next page: progress names the range while it loads, then the new range.
 let hold:(v:unknown)=>void=()=>{};client.rpc.mockImplementation(async(name:string,args:Args)=>name==='erp_cp7_read_staged_analysis_page_v1'&&args.p_index===1?new Promise(r=>{hold=r}):base(name,args))
 await click('Halaman berikutnya')
 expect(statuses().join(' | ')).toContain('Mengambil target 501–950 dari 1.200…');expect(rows()).toBe(0);expect(button('Halaman berikutnya')!.disabled).toBe(true)
 await act(async()=>{hold({data:s.page(1),error:null})});await until(()=>heading()==='Target 501–950 dari 1.200'&&rows()>0)
 expect(statuses().join(' | ')).not.toContain('Mengambil');expect(container.querySelector('[data-page-index]')!.getAttribute('data-page-index')).toBe('1')
 // Any range by choice; the last, uneven page has no next.
 const select=container.querySelector<HTMLSelectElement>('[aria-label="Pilih rentang target"]')!
 expect([...select.options].map(o=>o.textContent)).toEqual(['Target 1–500 dari 1.200','Target 501–950 dari 1.200','Target 951–1.200 dari 1.200'])
 await act(async()=>{select.value='2';select.dispatchEvent(new Event('change',{bubbles:true}))});await until(()=>heading()==='Target 951–1.200 dari 1.200'&&rows()>0)
 expect(button('Halaman berikutnya')!.disabled).toBe(true);expect(button('Halaman sebelumnya')!.disabled).toBe(false)
 expect(names().filter(n=>n==='erp_cp7_read_staged_analysis_page_v1')).toHaveLength(3)
 // Cek sumber: both outcomes come from the server, the pages stay.
 await click('Cek sumber');await until(()=>Boolean(region()!.textContent?.includes('Sumber belum berubah sejak')))
 expect(names().at(-1)).toBe('erp_cp7_check_staged_analysis_source_v1');expect(region()!.querySelector('.native-demand-current')!.textContent).toContain('Sumber belum berubah sejak');expect(rows()).toBeGreaterThan(0)
 client.rpc.mockImplementation(server({source:'ARCHIVED_STALE'}));await click('Cek sumber');await until(()=>Boolean(region()!.textContent?.includes('Sumber sudah berubah; hasil ini arsip')))
 expect(region()!.querySelector('.native-demand-stale')).toBeTruthy();expect(heading()).toBe('Target 951–1.200 dari 1.200');expect(container.querySelector('[role="alert"]')).toBeNull()
},30000)

it('surfaces a FAILED job with its code verbatim, ends the busy state and drops the stored request',async()=>{
 const base=server();client.rpc.mockImplementation(async(name:string,args:Args)=>name==='erp_cp7_step_staged_analysis_v1'?{data:s.job('FAILED',{failure:{unit:12,sqlstate:'42501',code:'CP7_ANALYSIS_ACCESS_CHANGED'}}),error:null}:base(name,args))
 await render();await click(STAGED);await until(()=>alertText().includes('CP7_ANALYSIS_ACCESS_CHANGED'))
 expect(alertText()).toContain('Hak akses berubah');expect(alertText()).toContain('unit 12');expect(button('Tutup analisis bersama')!.disabled).toBe(false);expect(button(STAGED)!.disabled).toBe(false)
 expect(readStagedRequest(scope).pending).toBeNull();expect(region()).toBeNull();expect(button('Lanjutkan analisis bertahap')).toBeUndefined();expect(statuses().some(t=>t.startsWith('Analisis bertahap: tahap'))).toBe(false)
 expect(names()).toEqual(['erp_cp7_request_staged_analysis_v1','erp_cp7_step_staged_analysis_v1'])
},30000)

it('resumes a stored job on mount by reading status, shows "dijeda sejak" with Lanjutkan after a lost step, and continues from there',async()=>{
 const id='0b7e3c2a-1d4f-4a6b-9c8d-7e6f5a4b3c2d';s=await stagedRun({targets:1200,pageSizes:SIZES,unreviewed:7,requestId:id})
 localStorage.setItem(stagedRequestKey(scope),JSON.stringify({id,q:q()}))
 let lost=true;const base=server()
 client.rpc.mockImplementation(async(name:string,args:Args)=>{
  if(name==='erp_cp7_request_staged_analysis_v1')throw Error('a resume never requests again')
  if(name==='erp_cp7_get_staged_analysis_v1'){expect(args).toEqual({p_request:id});return RUNNING(20)}
  if(name==='erp_cp7_step_staged_analysis_v1'&&lost){lost=false;throw new TypeError('Failed to fetch')}
  if(name==='erp_cp7_step_staged_analysis_v1')return{data:s.job('DONE'),error:null}
  return base(name,args)
 })
 await render();await until(()=>statuses().some(t=>t.startsWith('Analisis bertahap dijeda sejak jam 16.05.30 WIB')))
 expect(names()).toEqual(['erp_cp7_get_staged_analysis_v1','erp_cp7_step_staged_analysis_v1']);expect(button('Tutup analisis bersama')!.disabled).toBe(false)
 expect(readStagedRequest(scope).pending?.id).toBe(id);expect(region()).toBeNull();expect(button(STAGED)!.disabled).toBe(true);expect(button('Lanjutkan analisis bertahap')!.disabled).toBe(false)
 await click('Lanjutkan analisis bertahap');await until(()=>Boolean(region())&&rows()>0)
 expect(names().slice(2)).toEqual(['erp_cp7_get_staged_analysis_v1','erp_cp7_step_staged_analysis_v1','erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1'])
 expect(readStagedRequest(scope).pending).toBeNull();expect(container.querySelector('[role="alert"]')).toBeNull();expect(button('Lanjutkan analisis bertahap')).toBeUndefined();expect(heading()).toBe('Target 1–500 dari 1.200')
},30000)

it('offers the staged path when the single capture refuses for its target bound, showing the code as it is',async()=>{
 const base=server()
 client.rpc.mockImplementation(async(name:string,args:Args)=>name==='erp_cp7_capture_operational_analysis_v1'?{data:null,error:{code:'P0001',message:'CP7_NETTING_MATCH_SOURCE_LIMIT',details:null,hint:null}}:base(name,args))
 await render();await click('Ambil analisis ERP terbaru');await until(()=>alertText().includes('CP7_NETTING_MATCH_SOURCE_LIMIT'))
 expect(statuses().some(t=>t.includes(`"${STAGED}"`))).toBe(true);expect(readNativeDemandRequest(scope).pending).toBeNull();expect(button(STAGED)!.disabled).toBe(false);expect(button('Ambil analisis ERP terbaru')!.disabled).toBe(false)
 await click(STAGED);await until(()=>Boolean(region())&&rows()>0)
 expect(names().slice(1)).toEqual(['erp_cp7_request_staged_analysis_v1','erp_cp7_step_staged_analysis_v1','erp_cp7_step_staged_analysis_v1','erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1'])
 expect(container.querySelector('[role="alert"]')).toBeNull();expect(statuses().some(t=>t.includes(`"${STAGED}"`))).toBe(false)
 // Any other refusal keeps the single path's protocol: the request is held.
 await act(async()=>root.unmount());root=createRoot(container);localStorage.clear();client.rpc.mockReset()
 client.rpc.mockImplementation(async()=>({data:null,error:{code:'P0001',message:'CP7_ANALYSIS_ACCESS_DENIED',details:null,hint:null}}))
 await render();await click('Ambil analisis ERP terbaru');await until(()=>alertText().includes('CP7_ANALYSIS_ACCESS_DENIED'))
 expect(readNativeDemandRequest(scope).pending).not.toBeNull();expect(button('Ulangi analisis yang sama')).toBeTruthy();expect(statuses().some(t=>t.includes(`"${STAGED}"`))).toBe(false)
},30000)

it('refuses a page set whose identity is not that of its header and pages; the request is kept for a later read',async()=>{
 const base=server();client.rpc.mockImplementation(async(name:string,args:Args)=>{const r=await base(name,args) as {data:Record<string,any>|null;error:unknown};if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:{...r.data,identity_hash:'0'.repeat(64)},error:null};return r})
 await render();await click(STAGED);await until(()=>alertText().includes('belum sesuai'))
 expect(region()).toBeNull();expect(names()).not.toContain('erp_cp7_read_staged_analysis_page_v1');expect(readStagedRequest(scope).pending).not.toBeNull();expect(button('Lanjutkan analisis bertahap')).toBeTruthy();expect(button('Tutup analisis bersama')!.disabled).toBe(false)
 // The same for a header body that is not the one listed.
 await act(async()=>root.unmount());root=createRoot(container);localStorage.clear();client.rpc.mockReset()
 const again=server();client.rpc.mockImplementation(async(name:string,args:Args)=>{const r=await again(name,args) as {data:Record<string,any>|null;error:unknown};if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:{...r.data,header:{...r.data!.header,body:r.data!.header.body.replace('"TEST"','"TESX"')}},error:null};return r})
 await render();await click(STAGED);await until(()=>alertText().includes('belum sesuai'));expect(region()).toBeNull();expect(readStagedRequest(scope).pending).not.toBeNull()
},30000)

it('refuses a tampered page: nothing of it is shown, the summary stays the whole-run summary',async()=>{
 client.rpc.mockImplementation(server({page:async(i)=>{const p=s.page(i);return{data:i===0?await rehash(p,p.body.replace('SOURCE_INPUT_NOT_PROVEN','SOURCE_INPUT_NOT_PROVEX')):p,error:null}}}))
 await render();await click(STAGED);await until(()=>alertText().includes('belum sesuai'))
 expect(rows()).toBe(0);expect(container.querySelector('[data-page-index]')).toBeNull();expect(region()).toBeTruthy();expect(readStagedRequest(scope).pending).toBeNull()
 expect(region()!.querySelector('[aria-label="Ringkasan seluruh analisis bertahap"] h3')!.textContent).toBe('Ringkasan seluruh analisis · 1.200 target')
 await click('Halaman berikutnya');await until(()=>rows()>0);expect(heading()).toBe('Target 501–950 dari 1.200')
},30000)

it('drops the staged view when the access epoch is refused for a page or the source check',async()=>{
 client.rpc.mockImplementation(server({page:async(i)=>i===0?{data:s.page(0),error:null}:{data:null,error:{code:'42501',message:'CP7_ANALYSIS_ACCESS_CHANGED'}}}))
 await render();await click(STAGED);await until(()=>rows()>0)
 await click('Halaman berikutnya');await until(()=>Boolean(container.querySelector('[role="alert"]')))
 expect(region()).toBeNull();expect(rows()).toBe(0)
},30000)

it('states that financial figures are not part of a staged run when the finance choice is ticked, and still runs the operational job',async()=>{
 const auth=state.auth as typeof recoveryIdentity;auth.identity.permissions.push('finance.reports.view')
 client.rpc.mockImplementation(server())
 await render();expect(container.textContent).not.toContain('Angka keuangan tidak termasuk analisis bertahap')
 await tick('Sertakan angka keuangan (menunggu buku besar)');expect(container.textContent).toContain('Angka keuangan tidak termasuk analisis bertahap.')
 await click(STAGED);await until(()=>Boolean(region())&&rows()>0)
 expect(names()[0]).toBe('erp_cp7_request_staged_analysis_v1');expect(Object.keys(client.rpc.mock.calls[0][1]).sort()).toEqual(['p_query','p_request']);expect(region()!.textContent).toContain('Angka keuangan tidak termasuk analisis bertahap')
 expect(region()!.textContent).not.toContain('Rp');expect(button('Muat angka keuangan')).toBeUndefined()
},30000)

it('abandons the loop on unmount: a late step reply drives nothing further and the request stays for a resume',async()=>{
 let release:(v:unknown)=>void=()=>{};const base=server()
 client.rpc.mockImplementation(async(name:string,args:Args)=>name==='erp_cp7_step_staged_analysis_v1'?new Promise(r=>{release=r}):base(name,args))
 await render();await click(STAGED);await until(()=>names().includes('erp_cp7_step_staged_analysis_v1'))
 await act(async()=>root.unmount());root=createRoot(container)
 await act(async()=>{release(RUNNING(13))});for(let i=0;i<5;i++)await act(async()=>{await macrotask()})
 expect(names()).toEqual(['erp_cp7_request_staged_analysis_v1','erp_cp7_step_staged_analysis_v1']);expect(readStagedRequest(scope).pending).not.toBeNull()
},30000)


it('reopens the completed result after remount using the same request and verified pages without recomputing',async()=>{
 client.rpc.mockImplementation(server({steps:1}));await render();await click(STAGED);await until(()=>Boolean(region())&&Boolean(heading()))
 expect(readStagedRequest(scope).pending).toBeNull();const saved=readStagedRequest(stagedCompletedScope(scope)).pending
 expect(saved?.id).toBe(s.pageSet.request_id);expect(localStorage.getItem(stagedRequestKey(stagedCompletedScope(scope)))).not.toContain('analysis_header')
 const before=client.rpc.mock.calls.length
 await act(async()=>root.unmount());root=createRoot(container);await render();await until(()=>Boolean(region())&&Boolean(heading()))
 expect(names().slice(before)).toEqual(['erp_cp7_get_staged_analysis_v1','erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1'])
 expect(readStagedRequest(scope).pending).toBeNull();expect(readStagedRequest(stagedCompletedScope(scope)).pending?.id).toBe(saved?.id)
})

it('pauses an in-flight unit, leaves the same request stored, and resumes from server status',async()=>{
 let release:(v:unknown)=>void=()=>{};const base=server({steps:1})
 client.rpc.mockImplementation(async(name:string,args:Args)=>{
  if(name==='erp_cp7_step_staged_analysis_v1'){const result=await base(name,args);return new Promise(r=>{release=()=>r(result)})}
  return base(name,args)
 })
 await render();await click(STAGED);await until(()=>Boolean(button('Jeda analisis bertahap')))
 const id=readStagedRequest(scope).pending?.id;await click('Jeda analisis bertahap');expect(button('Tutup analisis bersama')?.disabled).toBe(false)
 expect(statuses().some(t=>t.startsWith('Analisis bertahap dijeda'))).toBe(true)
 await act(async()=>release(null));expect(readStagedRequest(scope).pending?.id).toBe(id)
 await click('Lanjutkan analisis bertahap');await until(()=>Boolean(region())&&Boolean(heading()))
 expect(names().filter(n=>n==='erp_cp7_request_staged_analysis_v1')).toHaveLength(1)
 expect(names().filter(n=>n==='erp_cp7_step_staged_analysis_v1')).toHaveLength(1)
})
