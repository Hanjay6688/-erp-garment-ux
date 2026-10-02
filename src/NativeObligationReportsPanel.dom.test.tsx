// @vitest-environment jsdom
import {act,useRef,useState} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {reportCrypto} from '../tests/fixtures/reportCrypto.mjs'
import {appendixPreviewFixture,appendixDocumentFixture,appendixActor,appendixFinance} from '../tests/fixtures/nativeObligationReports'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {parseNativeReport,type NativeReport} from './nativeAnalysisReports'
import {readObligationReportRequest,type ObligationReportRequest} from './nativeObligationReports'
import NativeObligationReportsPanel from './NativeObligationReportsPanel'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,base:NativeReport
const scope='analysis:cp6-disposable:actor-1'
function Host(){const seq=useRef(0),[generation,setGeneration]=useState(0),[context,setContext]=useState(base.analysis);return <NativeObligationReportsPanel base={base} context={context} generation={generation} blocked={false} access={appendixFinance} onReadStart={()=>{const n=++seq.current;setGeneration(n);return n}} isReadCurrent={n=>seq.current===n} onReadEnd={()=>{}} onAnalysis={(a,n)=>{if(n===seq.current)setContext(a)}} requireClear={()=>{}}/>}
beforeEach(async()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});vi.stubGlobal('crypto',reportCrypto);localStorage.clear();client.rpc.mockReset()
 const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:appendixActor});a.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view','finance.ar.view','finance.ap.view','finance.payroll.view');state.auth=a
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(lock:object)=>unknown)=>fn({})}})
 base=await parseNativeReport(appendixPreviewFixture().base_report,appendixActor,appendixFinance);container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.unstubAllGlobals()})
async function render(){await act(async()=>root.render(<Host/>))}
async function click(label:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===label)!;expect(b).toBeTruthy();await act(async()=>b.click());await act(async()=>new Promise(resolve=>setTimeout(resolve,20)))}
async function fill(label:string,value:string){const field=container.querySelector<HTMLInputElement|HTMLTextAreaElement>(`[aria-label="${label}"]`)!;await act(async()=>{Object.getOwnPropertyDescriptor(field instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(field,value);field.dispatchEvent(new Event('input',{bubbles:true}))})}
async function review(){await act(async()=>container.querySelector<HTMLInputElement>('[aria-label="Lampiran tagihan sudah ditinjau"]')!.click())}
async function settled(check:()=>void){await vi.waitFor(async()=>{await act(async()=>{await new Promise(resolve=>setTimeout(resolve,0))});check()},{timeout:3000,interval:20})}
it('retires saved salary facts and a late read on narrower revocation, preserving operator fields and AP access',async()=>{
 client.rpc.mockResolvedValue({data:appendixPreviewFixture(),error:null});await render();expect(client.rpc).not.toHaveBeenCalled();await fill('Judul lampiran tagihan','Judul yang belum dikirim');await fill('Alasan lampiran tagihan','Alasan operator');await click('Periksa tagihan untuk laporan yang dibuka');expect(container.textContent).toContain('9007199254740993.01 IDR')
 let resolve!:(v:unknown)=>void;client.rpc.mockImplementation(()=>new Promise(r=>{resolve=r}));await click('Periksa tagihan untuk laporan yang dibuka');const auth=state.auth as typeof recoveryIdentity;auth.identity.permissions=auth.identity.permissions.filter(p=>p!=='finance.payroll.view');await render();expect(auth.identity.permissions).toContain('finance.ap.view');expect(container.textContent).not.toContain('9007199254740993.01 IDR')
 await act(async()=>resolve({data:appendixPreviewFixture(),error:null}));expect(container.textContent).not.toContain('9007199254740993.01 IDR');expect(container.querySelector<HTMLInputElement>('[aria-label="Judul lampiran tagihan"]')!.value).toBe('Judul yang belum dikirim');expect(container.querySelector<HTMLTextAreaElement>('[aria-label="Alasan lampiran tagihan"]')!.value).toBe('Alasan operator')
})
it('persists intent before send, recovers an uncertain committed reply after remount using the identical request, and never implicitly recaptures',async()=>{
 let held:ObligationReportRequest|null=null
 client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{
  if(name==='erp_cp7_get_obligation_report_preview_v1')return{data:appendixPreviewFixture(),error:null}
  const r=readObligationReportRequest(scope).pending!;expect(r.id).toBe(args.p_request)
  if(name==='erp_cp7_publish_obligation_report_v1'){held=r;throw Error('Stand-in committed reply lost')}
  return{data:{contract_version:'cp7.obligation-report-command.v1',request_id:r.id,status:'COMMITTED',document:await appendixDocumentFixture(r),production_go:false},error:null}
 })
 await render();await fill('Judul lampiran tagihan','Judul operator');await fill('Alasan lampiran tagihan','Alasan operator');await click('Periksa tagihan untuk laporan yang dibuka');await review();await click('Simpan lampiran tagihan yang ditinjau');expect(held).toBeTruthy();expect(readObligationReportRequest(scope).pending).toEqual(held)
 await act(async()=>root.unmount());root=createRoot(container);await render();await click('Periksa hasil lampiran tersimpan');await settled(()=>expect(readObligationReportRequest(scope).pending).toBeNull());expect(client.rpc.mock.calls[2][1]).toEqual(client.rpc.mock.calls[1][1]);expect(container.querySelector('[aria-label="Teks lampiran tagihan tersimpan"]')?.textContent).toContain('9007199254740993.01 IDR');expect(container.querySelector<HTMLInputElement>('[aria-label="Judul lampiran tagihan"]')!.value).toBe('Judul operator');expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_capture_analysis_v1')).toBe(false)
})
