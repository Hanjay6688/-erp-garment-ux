// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi,type Mock} from 'vitest'
import NativeProductionPlanningPanel from './NativeProductionPlanningPanel'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {supplyWire,workspaceWire,stagedWorkspaceWire,scheduleJobWire,stagedScheduleOutcome,nettingWire,dualHorizonNettingWire,scheduleOutcome,planningQuery,workKey,customerKey} from '../tests/fixtures/nativeProductionPlanning'
import {readScheduleRequest,scheduleRequestKey} from './nativeProductionPlanning'
import {schedulePayload,parseNativeSupply,parseScheduleWorkspace} from './nativeProductionPlanning'
import {nativeDemandRequestKey,persistNativeDemandRequest,readNativeDemandRequest} from './nativeDemandHistory'
import {demandRequest} from '../tests/fixtures/nativeDemandHistory'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,start:Mock<()=>void>,end:Mock<()=>void>,close:Mock<()=>void>
const scope='cp6-disposable:actor-1'
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear();const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});a.identity.permissions.push('master.product.view','master.product.manage','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container);start=vi.fn();end=vi.fn();close=vi.fn()})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()})
async function render(query=planningQuery){await act(async()=>root.render(<NativeProductionPlanningPanel query={query} onSourceReadStart={start} onSourceReadEnd={end} onClose={close}/>))}
async function click(label:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===label)!;expect(b).toBeTruthy();await act(async()=>b.click())}
async function fill(label:string,value:string){const e=container.querySelector<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>(`[aria-label="${label}"]`)!;expect(e).toBeTruthy();await act(async()=>{const prototype=e instanceof HTMLSelectElement?HTMLSelectElement.prototype:e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event(e instanceof HTMLSelectElement?'change':'input',{bubbles:true}))})}
function reply(reviewed=false){client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_source_request:string})=>({data:name==='erp_cp7_request_staged_analysis_v1'?scheduleJobWire(args.p_request):name==='erp_cp7_get_staged_production_schedule_v1'?stagedWorkspaceWire(args.p_source_request,reviewed):name==='erp_cp7_get_production_schedule_v1'?workspaceWire(reviewed):name.includes('production_supply')?supplyWire(args.p_request):name.includes('netting')?nettingWire(args.p_request):null,error:null}))}
async function fillSchedule(){await fill('Tempat kerja pilihan','Explicit centre');await fill('Batas jadwal WIB','2026-10-02T19:00');await fill('Waktu satu PCS baru','2');await fill('Mulai kerja 1 WIB','2026-10-01T08:00');await fill('Selesai kerja 1 WIB','2026-10-01T10:00');await fill('Beban lain 1','0');await fill(`Bagus ${workKey}`,'9');await fill(`Acuan ${workKey}`,'10');for(const key of[workKey,customerKey])for(const stage of['SEWING','LAUNDRY','QC'])await fill(`${stage} menit ${key}`,stage==='SEWING'?'15':stage==='LAUNDRY'?'20':'10');await fill('Alasan jadwal','explicit reviewed work')}
it('shows the server lead trigger and target separately, and retires them on current denial',async()=>{
 client.rpc.mockImplementation(async(_name:string,args:{p_request:string})=>({data:dualHorizonNettingWire(args.p_request),error:null}))
 await render();await click('Hitung kekurangan seluruh produk')
 const cell=container.querySelector('td[data-label="Kapan perlu ditinjau"]')
 expect(cell?.textContent).toContain('Titik pesan ulang tercapai');expect(cell?.textContent).toContain('80 PCS');expect(cell?.textContent).toContain('76 PCS')
 expect(container.querySelector('td[data-label="Target"]')?.textContent).toBe('100 PCS')
 expect(container.querySelector('td[data-label="Kurang setelah stok proses terikat"]')?.textContent).toBe('17 PCS')
 expect(container.textContent).toContain('hanya mengurangi jumlah target')
 client.rpc.mockResolvedValue({data:null,error:{status:403,message:'CP7_ACCESS_DENIED'}});await click('Periksa sumber kekurangan')
 expect(container.querySelector('.native-production-result')).toBeNull()
})
it('loads one global source and server routes with blank timing/yield assumptions including customer work',async()=>{reply();await render();expect(client.rpc).not.toHaveBeenCalled();await click('Ambil stok proses terbaru');expect((container.querySelector('[aria-label="Waktu satu PCS baru"]')as HTMLInputElement).value).toBe('');expect((container.querySelector(`[aria-label="SEWING menit ${workKey}"]`)as HTMLInputElement).value).toBe('');expect(container.querySelector(`[aria-label="Bagus ${customerKey}"]`)).toBeNull();expect(container.textContent).toContain('Milik pelanggan');expect(start).toHaveBeenCalledTimes(1);expect(end).toHaveBeenCalledTimes(1)})
it('persists exact metadata UUID before send and replays it after response loss/remount despite newer schedule',async()=>{reply();await render();await click('Ambil stok proses terbaru');await fillSchedule();client.rpc.mockResolvedValue({data:null,error:Error('reply lost')});await click('Simpan jadwal yang diperiksa');const original=structuredClone(client.rpc.mock.calls.find(([name])=>name==='erp_cp7_save_staged_production_schedule_v1')!);expect(readScheduleRequest(scope).pending?.id).toBe(original[1].p_request);expect(original[1].p_payload.config.positions[1].target_key).toBeNull();expect(original[1].p_payload.config.positions[1].yield_numerator).toBeNull()
 await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>({data:name==='erp_cp7_save_staged_production_schedule_v1'?stagedScheduleOutcome(args.p_request):null,error:null}));await render();await click('Ulangi simpan jadwal yang sama');expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_staged_production_schedule_v1')[1]).toEqual(original);expect(readScheduleRequest(scope).pending).toBeNull();expect(container.textContent).toContain('Jadwal tersimpan')})
it('keeps dirty quantities/times and original revision after new source review; requires explicit adoption',async()=>{reply(true);await render();await click('Ambil stok proses terbaru');await fill('Waktu satu PCS baru','3');const fresh=stagedWorkspaceWire(undefined,true);fresh.revision='2';fresh.plan!.revision='2';fresh.plan!.config.unit_minutes='4';client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_source_request:string})=>({data:name==='erp_cp7_get_staged_production_schedule_v1'?{...fresh,source_request_id:args.p_source_request}:scheduleJobWire(args.p_request),error:null}));await click('Periksa sumber stok proses');expect((container.querySelector('[aria-label="Waktu satu PCS baru"]')as HTMLInputElement).value).toBe('3');expect(container.textContent).toContain('Isianmu masih ada');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Simpan jadwal yang diperiksa')!.disabled).toBe(true);await click('Gunakan sumber jadwal terbaru');expect((container.querySelector('[aria-label="Waktu satu PCS baru"]')as HTMLInputElement).value).toBe('4')})
it('retries a lost netting capture with the original complete query/UUID after remount and retires results on current403',async()=>{client.rpc.mockResolvedValue({data:null,error:Error('reply lost')});await render();await click('Hitung kekurangan seluruh produk');const original=structuredClone(client.rpc.mock.calls[0]);await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockImplementation(async(_name:string,args:{p_request:string})=>({data:nettingWire(args.p_request??original[1].p_request),error:null}));await render({...planningQuery,from_date:'2026-09-28'});await click('Ulangi kekurangan yang sama');expect(client.rpc.mock.calls[1]).toEqual(original);expect(container.querySelector('.native-production-result')?.textContent).toContain('17 PCS');client.rpc.mockResolvedValue({data:null,error:{status:403,message:'CP7_ACCESS_DENIED'}});await click('Periksa sumber kekurangan');expect(container.querySelector('.native-production-result')).toBeNull();expect(container.querySelector('[role=alert]')).toBeTruthy()})
it('ignores a held response after close and preserves its request for recovery',async()=>{let release:(x:unknown)=>void=()=>{};client.rpc.mockImplementation(()=>new Promise(r=>release=r));await render();await click('Hitung kekurangan seluruh produk');const request=client.rpc.mock.calls[0][1].p_request;await click('Tutup jadwal produksi');await act(async()=>release({data:nettingWire(request),error:null}));expect(container.querySelector('.native-production-result')).toBeNull();expect(close).toHaveBeenCalledTimes(1);expect(end).toHaveBeenCalledTimes(1);expect(localStorage.length).toBe(1)})
it('refuses replacing corrupt saved metadata and retains it after fresh permission denial',async()=>{localStorage.setItem(scheduleRequestKey(scope),'broken');reply();await render();expect(container.textContent).toContain('Permintaan jadwal tersimpan belum bisa dibaca');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Ambil stok proses terbaru')!.disabled).toBe(true);expect(localStorage.getItem(scheduleRequestKey(scope))).toBe('broken')})
it('does not send duplicate source requests while the first request is held',async()=>{
 let release:(v:unknown)=>void=()=>{};client.rpc.mockImplementation(()=>new Promise(r=>release=r));await render()
 const button=[...container.querySelectorAll('button')].find(b=>b.textContent==='Ambil stok proses terbaru')!
 await act(async()=>{button.click();button.click()});expect(client.rpc).toHaveBeenCalledTimes(1)
 const args=client.rpc.mock.calls[0][1];expect(args.p_query).toEqual({...planningQuery,finance_mode:'DEFERRED'});expect(readNativeDemandRequest('staged-schedule-source:'+scope).pending).toEqual({id:args.p_request,q:planningQuery})
 await act(async()=>release({data:null,error:Error('uncertain')}));expect(readNativeDemandRequest('staged-schedule-source:'+scope).pending?.id).toBe(args.p_request)
})
it('retains a staged source until its work guidance is verified, and retries the same query after remount',async()=>{
 let request='';client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>{if(name==='erp_cp7_request_staged_analysis_v1'){request=args.p_request;return{data:scheduleJobWire(request),error:null}}return{data:null,error:Error('guidance reply lost')}})
 await render();await click('Ambil stok proses terbaru');const first=structuredClone(client.rpc.mock.calls[0]);expect(readNativeDemandRequest('staged-schedule-source:'+scope).pending?.id).toBe(request);expect(container.querySelector('form')).toBeNull()
 await act(async()=>root.unmount());root=createRoot(container);reply();await render({...planningQuery,from_date:'2026-09-28'});await click('Ulangi stok proses yang sama')
 expect(client.rpc.mock.calls[2]).toEqual(first);expect(readNativeDemandRequest('staged-schedule-source:'+scope).pending).toBeNull();expect(container.querySelector('form')).toBeTruthy()
})
it('recovers an old supply request through its original facade and preserves a lost legacy save on replay',async()=>{
 const held={id:demandRequest,q:planningQuery};persistNativeDemandRequest('supply:'+scope,held);reply();await render();expect(client.rpc).not.toHaveBeenCalled();await click('Pulihkan stok proses versi lama')
 expect(client.rpc.mock.calls[0]).toEqual(['erp_cp7_capture_production_supply_v1',{p_query:planningQuery,p_request:demandRequest}]);expect(client.rpc.mock.calls.some(([name])=>name==='erp_cp7_request_staged_analysis_v1')).toBe(false)
 await fillSchedule();client.rpc.mockResolvedValue({data:null,error:Error('reply lost')});await click('Simpan jadwal yang diperiksa')
 const original=structuredClone(client.rpc.mock.calls.find(([name])=>name==='erp_cp7_save_production_schedule_v1')!);expect(original).toBeTruthy();expect(original[1].p_payload.staged_review_contract).toBeUndefined()
 await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>({data:name==='erp_cp7_save_production_schedule_v1'?scheduleOutcome(args.p_request):null,error:null}));await render();await click('Ulangi simpan jadwal yang sama')
 expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_production_schedule_v1')[1]).toEqual(original);expect(readScheduleRequest(scope).pending).toBeNull()
})
it('recovers a pre-existing old schedule even when the screen now defaults to staged work',async()=>{
 const w=parseScheduleWorkspace(workspaceWire(),parseNativeSupply(supplyWire(),planningQuery)),r={id:demandRequest,payload:schedulePayload(w,workspaceWire(true).plan!.config,'old unsent-or-lost request')}
 localStorage.setItem(scheduleRequestKey(scope),JSON.stringify(r));client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>({data:name==='erp_cp7_save_production_schedule_v1'?scheduleOutcome(args.p_request):null,error:null}));await render();await click('Ulangi simpan jadwal yang sama')
 expect(client.rpc.mock.calls).toEqual([['erp_cp7_save_production_schedule_v1',{p_request:r.id,p_payload:r.payload}]])
})
it('shows failed analysis and incomplete history honestly while allowing valid work metadata',async()=>{
 let id='';client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_source_request:string})=>{if(name==='erp_cp7_request_staged_analysis_v1'){id=args.p_request;return{data:scheduleJobWire(id,'FAILED'),error:null}}return{data:{...stagedWorkspaceWire(args.p_source_request),analysis_state:'FAILED',history_capture_state:'INCOMPLETE'},error:null}})
 await render();await click('Ambil stok proses terbaru');expect(container.textContent).toContain('Perhitungan kebutuhan terhenti');expect(container.textContent).toContain('Riwayat stok belum lengkap');expect(container.textContent).toContain('jumlah produksi belum dipastikan');expect(container.querySelector('.native-production-result')).toBeNull()
 expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Simpan jadwal yang diperiksa')!.disabled).toBe(false)
})
it('retires staged guidance on current denial but preserves dirty work for explicit review',async()=>{
 reply();await render();await click('Ambil stok proses terbaru');await fill('Waktu satu PCS baru','3')
 client.rpc.mockResolvedValue({data:null,error:{status:403,message:'CP7_ACCESS_DENIED'}});await click('Periksa sumber stok proses')
 expect(container.querySelector('.native-demand-current')).toBeNull();expect((container.querySelector('[aria-label="Waktu satu PCS baru"]')as HTMLInputElement).value).toBe('3');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Simpan jadwal yang diperiksa')!.disabled).toBe(true)
})
it('ignores staged guidance held across a permission change and keeps the request recoverable',async()=>{
 let release:(x:unknown)=>void=()=>{},id='';client.rpc.mockImplementation((name:string,args:{p_request:string})=>{if(name==='erp_cp7_request_staged_analysis_v1'){id=args.p_request;return Promise.resolve({data:scheduleJobWire(id),error:null})}return new Promise(r=>release=r)})
 await render();await click('Ambil stok proses terbaru');const auth=state.auth as typeof recoveryIdentity;auth.identity.permissions=auth.identity.permissions.filter(p=>p!=='warehouse.stock.view');await render()
 await act(async()=>release({data:stagedWorkspaceWire(id),error:null}));expect(container.querySelector('form')).toBeNull();expect(readNativeDemandRequest('staged-schedule-source:'+scope).pending?.id).toBe(id);expect(end).toHaveBeenCalledTimes(1)
})
it('retires a held staged reply on cross-tab recovery changes without erasing the changed record',async()=>{
 let release:(x:unknown)=>void=()=>{},id='';client.rpc.mockImplementation((name:string,args:{p_request:string})=>{if(name==='erp_cp7_request_staged_analysis_v1'){id=args.p_request;return Promise.resolve({data:scheduleJobWire(id),error:null})}return new Promise(r=>release=r)})
 await render();await click('Ambil stok proses terbaru');const key=nativeDemandRequestKey('staged-schedule-source:'+scope),replacement={id:crypto.randomUUID(),q:planningQuery};localStorage.setItem(key,JSON.stringify(replacement));await act(async()=>dispatchEvent(new StorageEvent('storage',{key})))
 await act(async()=>release({data:stagedWorkspaceWire(id),error:null}));expect(container.querySelector('form')).toBeNull();expect(readNativeDemandRequest('staged-schedule-source:'+scope).pending).toEqual(replacement)
})
it('keeps both legacy and staged recovery records visible and never overwrites either',async()=>{
 persistNativeDemandRequest('supply:'+scope,{id:demandRequest,q:planningQuery});persistNativeDemandRequest('staged-schedule-source:'+scope,{id:crypto.randomUUID(),q:planningQuery});await render()
 expect(container.textContent).toContain('Pulihkan stok proses versi lama');expect(container.textContent).toContain('Ulangi stok proses yang sama');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Ambil stok proses terbaru')!.disabled).toBe(true);expect(client.rpc).not.toHaveBeenCalled()
})
it('releases only a first confirmed stale save refusal while preserving dirty work and requiring a new source',async()=>{
 reply();await render();await click('Ambil stok proses terbaru');await fillSchedule();await fill('Waktu satu PCS baru','3');client.rpc.mockResolvedValue({data:null,error:{code:'40001',message:'CP7_SCHEDULE_SOURCE_CHANGED'}});await click('Simpan jadwal yang diperiksa')
 expect(readScheduleRequest(scope).pending).toBeNull();expect(container.textContent).toContain('Isianmu masih ada');expect((container.querySelector('[aria-label="Waktu satu PCS baru"]')as HTMLInputElement).value).toBe('3');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Ambil stok proses terbaru')!.disabled).toBe(false);expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Simpan jadwal yang diperiksa')!.disabled).toBe(true)
})
it('retains the exact UUID after an uncertain save even if its replay later refuses a stale source',async()=>{
 reply();await render();await click('Ambil stok proses terbaru');await fillSchedule();client.rpc.mockResolvedValue({data:null,error:Error('committed reply may have been lost')});await click('Simpan jadwal yang diperiksa');const held=readScheduleRequest(scope).pending;expect(held).toBeTruthy()
 client.rpc.mockResolvedValue({data:null,error:{code:'40001',message:'CP7_SCHEDULE_SOURCE_CHANGED'}});await click('Ulangi simpan jadwal yang sama');expect(readScheduleRequest(scope).pending).toEqual(held);expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Ambil stok proses terbaru')!.disabled).toBe(true)
})
