// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi,type Mock} from 'vitest'
import NativeAnalysisPanel from './NativeAnalysisPanel'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import fixture from '../tests/fixtures/nativeAnalysisStandin.json'
import {analysisFinanceFixture} from '../tests/fixtures/nativeAnalysisFinance'
import {readNativeDemandRequest} from './nativeDemandHistory'
import {analysisArchiveKey} from './nativeAnalysisArchive'
import type {NativeDemandQuery} from './nativeDemandHistory'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,start:Mock<()=>void>,end:Mock<()=>void>,close:Mock<()=>void>,clipboard:Mock
const q=fixture.query as NativeDemandQuery,scope='analysis:cp6-disposable:actor-1'
function wire(requestId:string){return{...structuredClone(fixture),request_id:requestId}}
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
