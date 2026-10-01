// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi,type Mock} from 'vitest'
import {nativeEpisodeFixture}from'../tests/fixtures/nativeObligationEpisodes'
import {obligationRequestKey}from'./nativeObligationEpisodes'
import NativeAnalysisPanel from './NativeAnalysisPanel'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import fixture from '../tests/fixtures/nativeAnalysisStandin.json'
import {analysisFinanceFixture} from '../tests/fixtures/nativeAnalysisFinance'
import {attentionFixture} from '../tests/fixtures/nativeAttention'
import {nativeReceivableFixture} from '../tests/fixtures/nativeReceivableConditions'
import {nativePayableFixture} from '../tests/fixtures/nativePayableConditions'
import {readAttentionRequest} from './nativeAnalysisAttention'
import {readNativeDemandRequest} from './nativeDemandHistory'
import {analysisArchiveKey} from './nativeAnalysisArchive'
import type {NativeDemandQuery} from './nativeDemandHistory'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,start:Mock<()=>void>,end:Mock<()=>void>,close:Mock<()=>void>,clipboard:Mock
const q=fixture.query as NativeDemandQuery,scope='analysis:cp6-disposable:actor-1'
function wire(requestId:string){return{...structuredClone(fixture),request_id:requestId}}
function serverArchive(requestId=fixture.request_id){return{contract_version:'cp7.native-analysis-archives.v1',actor_scope_id:fixture.analysis.scope.actor_scope_id,rows:[{runId:fixture.run_id,requestId,query:structuredClone(q),capturedAt:fixture.analysis.snapshot.generated_at,sourceHash:fixture.analysis.snapshot.source_hash,semanticHash:fixture.analysis.semantic_hash}],total_visible:'1',next_before_run:null,page_complete:true,read_at:'2026-10-01T00:00:00+00:00'}}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear();const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:fixture.analysis.scope.actor_scope_id});a.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container);start=vi.fn();end=vi.fn();close=vi.fn();clipboard=vi.fn().mockResolvedValue(undefined);Object.defineProperty(navigator,'clipboard',{value:{writeText:clipboard},configurable:true})})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()})
async function render(query=q){await act(async()=>root.render(<NativeAnalysisPanel query={query} onSourceReadStart={start} onSourceReadEnd={end} onClose={close}/>))}
async function click(text:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===text)!;expect(b).toBeTruthy();await act(async()=>b.click())}
async function fill(text:string){const e=container.querySelector<HTMLTextAreaElement>('[aria-label="Pertanyaan analisis ERP"]')!;await act(async()=>{Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value')!.set!.call(e,text);e.dispatchEvent(new Event('input',{bubbles:true}))})}
it('shares one server analysis across production/report/reminder/AI; tabs and search never recapture or reallocate',async()=>{
 client.rpc.mockImplementation(async(_name:string,args:{p_request:string})=>({data:wire(args.p_request),error:null}));await render();expect(client.rpc).not.toHaveBeenCalled();await click('Ambil analisis ERP terbaru');expect(container.querySelector('.native-analysis-result')).toBeTruthy()
 for(const tab of['Laporan','Pengingat','Tanya AI','Produksi'])await click(tab)
 expect(client.rpc).toHaveBeenCalledTimes(1);expect(container.textContent).not.toContain('DATA CONTOH');expect(start).toHaveBeenCalledTimes(1);expect(end).toHaveBeenCalledTimes(1)
})
it('stores exact UUID and query before send, and recovers the committed lost reply after remount with the same original query',async()=>{
 let first:string|undefined;client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>{expect(readNativeDemandRequest(scope).pending?.id).toBe(args.p_request);if(!first){first=args.p_request;throw Error('lost reply')}return{data:wire(args.p_request),error:null}})
 await render();await click('Ambil analisis ERP terbaru');expect(readNativeDemandRequest(scope).pending?.id).toBe(first);await act(async()=>root.unmount());root=createRoot(container);await render({...q,group_mode:'RESTATED'});await click('Ulangi analisis yang sama')
 expect(client.rpc.mock.calls[1][1]).toEqual(client.rpc.mock.calls[0][1]);expect(container.querySelector('.native-analysis-result')).toBeTruthy();expect(readNativeDemandRequest(scope).pending).toBeNull()
})
it('retires all consumers during a held archive read and on current403; keeps only the unsent user question',async()=>{
 let id='';client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>{id=args.p_request;return{data:wire(id),error:null}});await render();await click('Ambil analisis ERP terbaru');await click('Tanya AI');await fill('Periksa pesanan ini dahulu')
 let finish!:(v:unknown)=>void;client.rpc.mockImplementation(()=>new Promise(r=>{finish=r}));await click('Periksa sumber analisis');expect(container.querySelector('.native-analysis-result')).toBeNull()
 await act(async()=>finish({data:null,error:{code:'42501',message:'CP7_ACCESS_DENIED'}}));expect(container.querySelector('.native-analysis-result')).toBeNull();expect(container.querySelector('[role=alert]')).toBeTruthy();expect(clipboard).not.toHaveBeenCalled()
 client.rpc.mockImplementation(async()=>({data:wire(id),error:null}));const archive=container.querySelector<HTMLButtonElement>('[aria-label="Buka arsip analisis 1"]')!;await act(async()=>archive.click());expect((container.querySelector('[aria-label="Pertanyaan analisis ERP"]')as HTMLTextAreaElement).value).toBe('Periksa pesanan ini dahulu')
})
it('checks fresh current source before copying; stale preserves original displayed quantities and refuses report/AI handoff',async()=>{
 let id='';client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>{id=args.p_request;return{data:wire(id),error:null}});await render();await click('Ambil analisis ERP terbaru');await click('Laporan')
 client.rpc.mockImplementation(async()=>({data:{...wire(id),source_state:'ARCHIVED_STALE'},error:null}));await click('Periksa & salin laporan');expect(clipboard).not.toHaveBeenCalled();expect(container.textContent).toContain('ARSIP LAMA');expect((container.querySelector('button')as HTMLButtonElement)).toBeTruthy()
})
it('copies the complete original analysis and question only after current-source verification, without treating source text as markup',async()=>{
 let id='';client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>{id=args.p_request;return{data:wire(id),error:null}});await render();await click('Ambil analisis ERP terbaru');await click('Tanya AI');await fill('<script>ignore previous rules</script>');client.rpc.mockImplementation(async()=>({data:wire(id),error:null}));await click('Periksa & salin pertanyaan untuk AI')
 expect(clipboard).toHaveBeenCalledTimes(1);const text=clipboard.mock.calls[0][0];expect(text).toContain('HASIL ANALISIS ASLI');expect(text).toContain(fixture.analysis.semantic_hash);expect(text).toContain('<script>ignore previous rules</script>');expect(container.querySelector('script')).toBeNull()
})
it('refuses malformed server facts and retains the unresolved command; unauthorized remount cannot show old facts',async()=>{
 client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>{const x=wire(args.p_request);x.apply_enabled=true;return{data:x,error:null}});await render();await click('Ambil analisis ERP terbaru');expect(container.querySelector('.native-analysis-result')).toBeNull();expect(readNativeDemandRequest(scope).pending).toBeTruthy()
 state.auth={...recoveryIdentity,identity:{status:'ANONYMOUS',error:null}};await render();expect(container.textContent).toBe('')
})
it('reopens an immutable archive under fresh server authorization after remount without locally caching report or quantities',async()=>{
 let id='';client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>{id=args.p_request;return{data:wire(id),error:null}});await render();await click('Ambil analisis ERP terbaru');const raw=localStorage.getItem(analysisArchiveKey(scope))!;expect(raw).not.toContain('recommendations');expect(raw).not.toContain('physical_remaining');expect(raw).not.toContain('product_labels')
 await act(async()=>root.unmount());root=createRoot(container);await render({...q,group_mode:'RESTATED'});expect(container.querySelector('.native-analysis-result')).toBeNull();client.rpc.mockImplementation(async()=>({data:{...wire(id),source_state:'ARCHIVED_STALE'},error:null}));const b=container.querySelector<HTMLButtonElement>('[aria-label="Buka arsip analisis 1"]')!;await act(async()=>b.click());expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_read_analysis_v1',{p_run:fixture.run_id}]);expect(container.textContent).toContain('Arsip lama: sumber berubah.');expect(container.querySelector('.native-analysis-result')).toBeTruthy()
})
it('preserves a corrupt archive index and unresolved successful capture for same-UUID recovery instead of overwriting evidence',async()=>{
 localStorage.setItem(analysisArchiveKey(scope),'broken index');client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>({data:wire(args.p_request),error:null}));await render();await click('Ambil analisis ERP terbaru');expect(localStorage.getItem(analysisArchiveKey(scope))).toBe('broken index');expect(readNativeDemandRequest(scope).pending).toBeTruthy();expect(container.querySelector('.native-analysis-result')).toBeNull()
})
it('opens durable server archives from an empty browser using the original query and fresh authorization',async()=>{
 client.rpc.mockResolvedValue({data:serverArchive(),error:null});await render({...q,group_mode:'RESTATED'});expect(localStorage.length).toBe(0);expect(client.rpc).not.toHaveBeenCalled()
 await click('Muat arsip laporan dari server');expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_list_analysis_archives_v1',{p_query:{before_run:null,limit:25}}]);expect(container.querySelector('.native-analysis-result')).toBeNull();expect(localStorage.length).toBe(0)
 client.rpc.mockResolvedValue({data:{...wire(fixture.request_id),source_state:'ARCHIVED_STALE'},error:null});await act(async()=>container.querySelector<HTMLButtonElement>('[aria-label="Buka arsip server 1"]')!.click())
 expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_read_analysis_v1',{p_run:fixture.run_id}]);expect(container.textContent).toContain('Arsip lama: sumber berubah.');expect(localStorage.length).toBe(0);expect(clipboard).not.toHaveBeenCalled()
})
it('retires displayed analysis during server archive listing and keeps it retired after a current403',async()=>{
 client.rpc.mockImplementation(async(_name:string,args:{p_request:string})=>({data:wire(args.p_request),error:null}));await render();await click('Ambil analisis ERP terbaru');await click('Tanya AI');await fill('Pertanyaan operator dipertahankan')
 let finish!:(v:unknown)=>void;client.rpc.mockImplementation(()=>new Promise(r=>{finish=r}));await click('Muat arsip laporan dari server');expect(container.querySelector('.native-analysis-result')).toBeNull();expect(start).toHaveBeenCalledTimes(2)
 await act(async()=>finish({data:null,error:{code:'42501',message:'CP7_ACCESS_DENIED'}}));expect(container.querySelector('[aria-label="Buka arsip server 1"]')).toBeNull();expect(container.querySelector('.native-analysis-result')).toBeNull()
 const requestId=JSON.parse(localStorage.getItem(analysisArchiveKey(scope))!)[0].requestId;client.rpc.mockResolvedValue({data:serverArchive(requestId),error:null});await click('Muat arsip laporan dari server');client.rpc.mockResolvedValue({data:wire(requestId),error:null});await act(async()=>container.querySelector<HTMLButtonElement>('[aria-label="Buka arsip server 1"]')!.click());await click('Tanya AI');expect((container.querySelector('[aria-label="Pertanyaan analisis ERP"]')as HTMLTextAreaElement).value).toBe('Pertanyaan operator dipertahankan')
})
it('rejects another actor archive list and ignores a delayed list after unmount',async()=>{
 client.rpc.mockResolvedValue({data:{...serverArchive(),actor_scope_id:'00000000-0000-4000-8000-000000000001'},error:null});await render();await click('Muat arsip laporan dari server');expect(container.querySelector('[aria-label="Buka arsip server 1"]')).toBeNull();expect(container.querySelector('[role=alert]')).toBeTruthy()
 let finish!:(v:unknown)=>void;client.rpc.mockImplementation(()=>new Promise(r=>{finish=r}));await click('Muat arsip laporan dari server');await act(async()=>root.unmount());root=createRoot(container);await render();await act(async()=>finish({data:serverArchive(),error:null}));expect(container.querySelector('[aria-label="Buka arsip server 1"]')).toBeNull();expect(container.querySelector('.native-analysis-result')).toBeNull()
})
it('preserves the Native internal-role boundary for saved attention while keeping four-Ops analysis available',async()=>{
 const a=state.auth as typeof recoveryIdentity;state.auth={...a,identity:{...a.identity,profile:{...a.identity.profile,role:'CUSTOM_OPS'}}}
 client.rpc.mockImplementation(async(_name:string,args:{p_request:string})=>({data:wire(args.p_request),error:null}));await render();await click('Ambil analisis ERP terbaru');await click('Pengingat')
 expect(container.textContent).toContain('Perhatian tersimpan dan pengingat pribadi tersedia untuk pemilik, admin, atau staf ERP.')
 const button=[...container.querySelectorAll('button')].find(b=>b.textContent==='Muat perhatian tersimpan')!;expect(button.disabled).toBe(true);expect(client.rpc).toHaveBeenCalledTimes(1);expect(container.querySelector('.native-analysis-result')).toBeTruthy()
})
it('loads the actual Native AR source explicitly, retains its original analysis, and retires all sources on AR-only403',async()=>{
 const a=state.auth as typeof recoveryIdentity;a.identity.permissions.push('finance.ar.view');let id=''
 client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{if(name==='erp_cp7_capture_analysis_v1'){id=args.p_request;return{data:wire(id),error:null}}return{data:nativeReceivableFixture(wire(id)),error:null}})
 await render();await click('Ambil analisis ERP terbaru');await click('Tanya AI');await fill('Pertanyaan tetap milik operator');await click('Pengingat');expect(client.rpc).toHaveBeenCalledTimes(1);expect(container.textContent).toContain('Sumber piutang belum dimuat.')
 await click('Periksa piutang pelanggan dari ERP');expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_get_analysis_receivable_conditions_v1',{p_run:fixture.run_id}]);expect(container.textContent).toContain('Sisa tagihan Rp300');expect(container.textContent).toContain('Sudah lewat jatuh tempo');expect(localStorage.getItem(analysisArchiveKey(scope))).not.toContain('300.00')
 client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'CP7_REMINDER_AR_ACCESS_DENIED'}});await click('Periksa piutang pelanggan dari ERP');expect(container.querySelector('.native-analysis-result')).toBeNull();expect(container.textContent).not.toContain('Sisa tagihan Rp300');expect(clipboard).not.toHaveBeenCalled()
 client.rpc.mockResolvedValue({data:wire(id),error:null});await act(async()=>container.querySelector<HTMLButtonElement>('[aria-label="Buka arsip analisis 1"]')!.click());await click('Tanya AI');expect((container.querySelector('[aria-label="Pertanyaan analisis ERP"]')as HTMLTextAreaElement).value).toBe('Pertanyaan tetap milik operator')
})
it('pages all complete AR documents locally without another read, capture, or hidden first-page total',async()=>{
 const a=state.auth as typeof recoveryIdentity;a.identity.permissions.push('finance.ar.view');let id=''
 client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{
  if(name==='erp_cp7_capture_analysis_v1'){id=args.p_request;return{data:wire(id),error:null}}
  const e=nativeReceivableFixture(wire(id)),s=e.source,seed=s.pages[0].page.rows[0],c=s.conditions[0]
  const rows=Array.from({length:26},(_,i)=>({...structuredClone(seed),id:'00000000-0000-4000-8000-'+String(i+1).padStart(12,'0'),number:'AR-PAGE-'+String(i+1)}));s.total='26'
  s.pages=[{...structuredClone(s.pages[0]),page:{rows:rows.slice(0,25),total:'26',offset:0,limit:25,next_offset:25}},{...structuredClone(s.pages[0]),page:{rows:rows.slice(25),total:'26',offset:25,limit:25,next_offset:null}}]
  s.conditions=rows.map(r=>({...structuredClone(c),key:'AR:'+r.id,source_id:r.id}));return{data:e,error:null}
 });await render();await click('Ambil analisis ERP terbaru');await click('Pengingat');await click('Periksa piutang pelanggan dari ERP');expect(container.querySelectorAll('[aria-label^="Piutang AR-PAGE-"]')).toHaveLength(25);expect(container.textContent).toContain('26 invoice.');expect(container.querySelector('[aria-label="Piutang AR-PAGE-26"]')).toBeNull()
 await click('Piutang berikutnya');expect(container.querySelectorAll('[aria-label^="Piutang AR-PAGE-"]')).toHaveLength(1);expect(container.querySelector('[aria-label="Piutang AR-PAGE-26"]')).toBeTruthy();expect(container.textContent).toContain('Halaman 2 dari 2');await click('Piutang sebelumnya');expect(container.querySelectorAll('[aria-label^="Piutang AR-PAGE-"]')).toHaveLength(25);expect(client.rpc).toHaveBeenCalledTimes(2)
})
it('loads Native supplier AP explicitly, retires both AR and AP during a held read and AP-only403, and preserves operator fields',async()=>{
 const a=state.auth as typeof recoveryIdentity;a.identity.permissions.push('finance.ar.view','finance.ap.view');let id=''
 client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{if(name==='erp_cp7_capture_analysis_v1'){id=args.p_request;return{data:wire(id),error:null}}return{data:nativeReceivableFixture(wire(id)),error:null}})
 await render();await click('Ambil analisis ERP terbaru');await click('Tanya AI');await fill('Pertanyaan utang tetap milik operator');await click('Pengingat');expect(client.rpc).toHaveBeenCalledTimes(1);expect(container.textContent).toContain('Sumber utang bahan belum dimuat.')
 await click('Periksa piutang pelanggan dari ERP');expect(container.textContent).toContain('Sisa tagihan Rp300')
 let resolve!:(value:unknown)=>void;client.rpc.mockImplementation(()=>new Promise(r=>{resolve=r}));await click('Periksa utang bahan pemasok dari ERP');expect(container.querySelector('.native-analysis-result')).toBeNull();expect(container.textContent).not.toContain('Sisa tagihan Rp300');expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_get_analysis_payable_conditions_v1',{p_run:fixture.run_id}]);await act(async()=>resolve({data:nativePayableFixture(wire(id)),error:null}));expect(container.textContent).toContain('Saldo tagihan final Rp300');expect(container.textContent).toContain('Sudah lewat jatuh tempo');expect(localStorage.getItem(analysisArchiveKey(scope))).not.toContain('300.00')
 client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'CP7_REMINDER_AP_ACCESS_DENIED'}});await click('Periksa utang bahan pemasok dari ERP');expect(container.querySelector('.native-analysis-result')).toBeNull();expect(container.textContent).not.toContain('Saldo tagihan final Rp300');expect(clipboard).not.toHaveBeenCalled()
 client.rpc.mockResolvedValue({data:wire(id),error:null});await act(async()=>container.querySelector<HTMLButtonElement>('[aria-label="Buka arsip analisis 1"]')!.click());await click('Tanya AI');expect((container.querySelector('[aria-label="Pertanyaan analisis ERP"]')as HTMLTextAreaElement).value).toBe('Pertanyaan utang tetap milik operator')
})
it('shows the exact financial source under current report rights and stores only an archive pointer',async()=>{
 const auth=state.auth as typeof recoveryIdentity;auth.identity.permissions.push('finance.reports.view')
 client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>({data:{...analysisFinanceFixture(),request_id:args.p_request},error:null}))
 await render();await click('Ambil analisis ERP terbaru');await click('Laporan');expect(container.textContent).toContain('Rp9.007.199.254.740.993,01');expect(container.textContent).toContain('Rp-7,02')
 await click('Tanya AI');expect(container.textContent).toContain('SUMBER KEUANGAN ERP ASLI');const stored=localStorage.getItem(analysisArchiveKey(scope))!;expect(stored).not.toContain('9007199254740993');expect(stored).not.toContain('financial_source');expect(stored).not.toContain('report')
})
it('retires financial and operational analysis on report-only403 and on a permissions remount while keeping four Ops rights',async()=>{
 const auth=state.auth as typeof recoveryIdentity;auth.identity.permissions.push('finance.reports.view')
 client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>({data:{...analysisFinanceFixture(),request_id:args.p_request},error:null}))
 await render();await click('Ambil analisis ERP terbaru');await click('Laporan');expect(container.textContent).toContain('Rp9.007.199.254.740.993,01')
 client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'CP7_ANALYSIS_FINANCE_ACCESS_DENIED'}});await click('Periksa sumber analisis');expect(container.querySelector('.native-analysis-result')).toBeNull();expect(container.textContent).not.toContain('Rp');expect(clipboard).not.toHaveBeenCalled()
 auth.identity.permissions=auth.identity.permissions.filter(p=>p!=='finance.reports.view');await render();expect(container.querySelector('.native-analysis')).toBeTruthy();expect(container.querySelector('.native-analysis-result')).toBeNull();expect(container.textContent).not.toContain('Rp')
})
it('persists the attention intent before send and recovers its lost reply after remount with original query and UUID',async()=>{
 let captureId='';client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{if(name==='erp_cp7_capture_analysis_v1'){captureId=args.p_request;return{data:wire(captureId),error:null}}return{data:attentionFixture(wire(captureId)),error:null}})
 await render();await click('Ambil analisis ERP terbaru');await click('Pengingat');expect(container.textContent).toContain('Belum dimuat');await click('Muat perhatian tersimpan')
 client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{expect(name).toBe('erp_cp7_save_analysis_attention_v1');expect(readAttentionRequest(scope).pending?.id).toBe(args.p_request);throw Error('lost reply')})
 await click('Sudah dibaca');const sent=client.rpc.mock.calls.at(-1)!;expect(readAttentionRequest(scope).pending).toBeTruthy();expect(container.querySelector('.native-analysis-result')).toBeNull()
 await act(async()=>root.unmount());root=createRoot(container);await render({...q,group_mode:'RESTATED'})
 client.rpc.mockImplementation(async(_name:string,args:{p_request:string;p_payload:{action_key:string}})=>{const v=attentionFixture(wire(captureId));const row=v.rows.find(r=>r.action_key===args.p_payload.action_key)!;row.attention={state:'ACK',resume_at:null,resume_due:false,revision:'1',updated_at:v.read_at};return{data:{...v,request_result:{request_id:args.p_request,run_id:fixture.run_id,action_key:args.p_payload.action_key,revision:'1',status:'COMMITTED'}},error:null}})
 await click('Ulangi perhatian yang sama');expect(client.rpc.mock.calls.at(-1)).toEqual(sent);expect(readAttentionRequest(scope).pending).toBeNull();expect(container.textContent).toContain('Sudah dibaca');expect(container.textContent).toContain('masih perlu diperiksa')
})
it('keeps an unknown attention outcome after403 and retires it only after the server seals NOT_COMMITTED',async()=>{
 let id='';client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{if(name==='erp_cp7_capture_analysis_v1'){id=args.p_request;return{data:wire(id),error:null}}return{data:attentionFixture(wire(id)),error:null}})
 await render();await click('Ambil analisis ERP terbaru');await click('Pengingat');await click('Muat perhatian tersimpan');client.rpc.mockRejectedValue(Error('network lost'));await click('Selesai ditinjau');const held=readAttentionRequest(scope).pending!
 client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'CP7_REMINDER_ACCESS_DENIED'}});await click('Periksa hasil perhatian tersimpan');expect(readAttentionRequest(scope).pending).toEqual(held);expect(container.querySelector('.native-analysis-result')).toBeNull()
 client.rpc.mockResolvedValue({data:{...attentionFixture(wire(id)),request_result:{request_id:held.id,run_id:fixture.run_id,action_key:held.payload.action_key,revision:null,status:'NOT_COMMITTED'}},error:null});await click('Periksa hasil perhatian tersimpan')
 expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_get_analysis_attention_request_v1',{p_payload:held.payload,p_request:held.id}]);expect(readAttentionRequest(scope).pending).toBeNull();expect(container.textContent).toContain('Server memastikan permintaan ini belum tersimpan');expect(container.textContent).not.toContain('Tugas ditandai selesai')
})
it('keeps dirty own-user schedule fields across a denied read and converts the entered time in WIB',async()=>{
 let id='';client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{if(name==='erp_cp7_capture_analysis_v1'){id=args.p_request;return{data:wire(id),error:null}}if(name==='erp_cp7_read_analysis_v1')return{data:wire(id),error:null};return{data:attentionFixture(wire(id)),error:null}})
 await render();await click('Ambil analisis ERP terbaru');await click('Pengingat');await click('Muat perhatian tersimpan')
 const fillInput=async(text:string,value:string)=>{const label=[...container.querySelectorAll('label')].find(l=>l.textContent===text)!,input=label.querySelector('input')!;await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}))})}
 await fillInput('Judul pengingat','Cek bahan besok');await fillInput('Waktu pengingat · WIB','2026-10-05T08:30')
 client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'CP7_ACCESS_DENIED'}});await click('Periksa sumber analisis');expect(container.querySelector('.native-analysis-result')).toBeNull()
 client.rpc.mockImplementation(async(name:string)=>({data:name==='erp_cp7_read_analysis_v1'?wire(id):attentionFixture(wire(id)),error:null}));const archive=container.querySelector<HTMLButtonElement>('[aria-label="Buka arsip analisis 1"]')!;await act(async()=>archive.click());await click('Muat perhatian tersimpan')
 const title=[...container.querySelectorAll('label')].find(l=>l.textContent==='Judul pengingat')!.querySelector('input')!;expect(title.value).toBe('Cek bahan besok')
 client.rpc.mockRejectedValue(Error('preserve intent'));await click('Simpan jadwal pengingat ERP');expect(readAttentionRequest(scope).pending?.payload.details).toEqual({title:'Cek bahan besok',note:'',priority:'NORMAL',due_at:'2026-10-05T01:30:00.000Z'})
})

it('retires every source before episode writes and recovers a lost reply with the same fact-free UUID intent',async()=>{
 const auth=state.auth as typeof recoveryIdentity;auth.identity.profile.role='STAFF';auth.identity.permissions.push('finance.ar.view')
 let captureId='';client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>{captureId=args.p_request;return{data:wire(captureId),error:null}});await render();await click('Ambil analisis ERP terbaru');await click('Tanya AI');await fill('Pertanyaan riwayat tetap milik operator');await click('Pengingat')
 let finish!:(v:unknown)=>void;client.rpc.mockImplementation(()=>new Promise(resolve=>{finish=resolve}));await click('Catat pemeriksaan piutang ERP');expect(container.querySelector('.native-analysis-result')).toBeNull();expect(start).toHaveBeenCalled();const request=JSON.parse(localStorage.getItem(obligationRequestKey(scope))!);expect(Object.keys(request.payload).sort()).toEqual(['domain','run_id']);expect(JSON.stringify(request)).not.toContain('remaining');expect(JSON.stringify(request)).not.toContain('financial_source')
 await act(async()=>finish({data:null,error:{message:'Reply lost after Native monitoring commit'}}));expect(container.textContent).toContain('Hasil pemeriksaan tagihan belum dipastikan.');expect(localStorage.getItem(obligationRequestKey(scope))).toBeTruthy()
 client.rpc.mockResolvedValue({data:nativeEpisodeFixture(request.id,wire(captureId)),error:null});await click('Periksa hasil pemeriksaan tagihan');expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_get_obligation_episode_request_v1',{p_payload:request.payload,p_request:request.id}]);expect(localStorage.getItem(obligationRequestKey(scope))).toBeNull();expect(container.textContent).toContain('Masalah masih terbuka');expect(container.textContent).toContain('Periksa sumber ERP untuk saldo terbaru.');await click('Tanya AI');expect((container.querySelector('[aria-label="Pertanyaan analisis ERP"]')as HTMLTextAreaElement).value).toBe('Pertanyaan riwayat tetap milik operator')
})
it('episode403 retains only intent and dirty question; a current-authority absent seal retires the old request without new facts',async()=>{
 const auth=state.auth as typeof recoveryIdentity;auth.identity.profile.role='STAFF';auth.identity.permissions.push('finance.ar.view')
 let captureId='';client.rpc.mockImplementation(async(_n:string,args:{p_request:string})=>{captureId=args.p_request;return{data:wire(captureId),error:null}});await render();await click('Ambil analisis ERP terbaru');await click('Tanya AI');await fill('Pertanyaan setelah pemeriksaan ditolak');await click('Pengingat');client.rpc.mockResolvedValue({data:null,error:{code:'42501',message:'CP7_OBLIGATION_ACCESS_DENIED'}});await click('Catat pemeriksaan piutang ERP');expect(container.querySelector('.native-analysis-result')).toBeNull();expect(clipboard).not.toHaveBeenCalled();const request=JSON.parse(localStorage.getItem(obligationRequestKey(scope))!);const absent=nativeEpisodeFixture(request.id,wire(captureId));Object.assign(absent.result,{status:'NOT_COMMITTED',source_status:'NOT_EVALUATED',source_hash:null,as_of:null,source_read_at:null,source_total:null,observed_at:null,rows:[]});client.rpc.mockResolvedValue({data:absent,error:null});await click('Periksa hasil pemeriksaan tagihan');expect(localStorage.getItem(obligationRequestKey(scope))).toBeNull();expect(container.textContent).toContain('Server memastikan pemeriksaan ini belum tersimpan.');await click('Tanya AI');expect((container.querySelector('[aria-label="Pertanyaan analisis ERP"]')as HTMLTextAreaElement).value).toBe('Pertanyaan setelah pemeriksaan ditolak')
})
