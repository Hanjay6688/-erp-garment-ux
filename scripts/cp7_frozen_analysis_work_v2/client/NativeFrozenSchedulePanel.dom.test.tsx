// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi,type Mock} from 'vitest'
import NativeFrozenSchedulePanel from './NativeFrozenSchedulePanel'
import {recoveryIdentity} from '../../../tests/fixtures/productionRecovery'
import {boundedWorkspaceWire,boundedScheduleOutcome,scheduleJobWire,scheduleConfig,planningQuery,workKey,customerKey} from '../../../tests/fixtures/nativeProductionPlanning'
import {demandRequest} from '../../../tests/fixtures/nativeDemandHistory'
import {scheduleRequestKey} from '../../../src/nativeProductionPlanning'
import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey,persistFrozenAnalysisRequest,readFrozenAnalysisRequest,type FrozenAnalysisRequest} from '../../cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
import {frozenScheduleRequestKey,readFrozenScheduleRequest,persistFrozenScheduleRequest,prepareFrozenScheduleRequest,parseFrozenScheduleWorkspace,type FrozenWorkContext} from './nativeFrozenWork'

const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../../src/auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('../../../src/lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const actor='11111111-1111-4111-8111-111111111111',scope='work-schedule:cp6-disposable'
let root:Root,container:HTMLDivElement,start:Mock<()=>void>,end:Mock<()=>void>,close:Mock<()=>void>
const contract={bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2'}
function wire(id=demandRequest,reviewed=true){return{...boundedWorkspaceWire(id,reviewed),...contract,contract_version:'cp7.planning-schedule-staged-bounded.v2',history_input_coverage:'PENDING'}}
function outcome(id:string,revision='2'){return{...boundedScheduleOutcome(id,revision),...contract,contract_version:'cp7.planning-schedule-staged-bounded-outcome.v2'}}
function response(reviewed=true){client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_source_request:string})=>({data:name==='erp_cp7_request_bounded_staged_analysis_v2'?scheduleJobWire(args.p_request):name==='erp_cp7_get_staged_production_schedule_v1'?wire(args.p_source_request,reviewed):name==='erp_cp7_save_staged_production_schedule_v1'?outcome(args.p_request,reviewed?'2':'1'):null,error:null}))}
function savedCommand(){
 const job=scheduleJobWire(),context:FrozenWorkContext={requestId:demandRequest,reference:{capturedAt:job.reference.captured_at,sourceHash:job.reference.source_hash},runId:null,method:'FROZEN_V2'}
 return prepareFrozenScheduleRequest(parseFrozenScheduleWorkspace(wire(),context),context,actor,scheduleConfig,'reviewed original',crypto.randomUUID())
}
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear()
 const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:actor,rowVersion:1,roleRowVersion:1})
 a.identity.permissions.push('master.product.view','master.product.manage','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=a
 const tails=new Map<string,Promise<void>>()
 vi.stubGlobal('navigator',{locks:{request:async(name:string,_options:unknown,action:()=>unknown)=>{
  const prior=tails.get(name)??Promise.resolve();let release!:()=>void
  const hold=new Promise<void>(r=>{release=r}),tail=prior.then(()=>hold);tails.set(name,tail);await prior
  try{return await action()}finally{release();if(tails.get(name)===tail)tails.delete(name)}
 }}})
 container=document.createElement('div');document.body.append(container);root=createRoot(container);start=vi.fn();end=vi.fn();close=vi.fn()
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks();vi.unstubAllGlobals()})
async function render(query=planningQuery){await act(async()=>root.render(<NativeFrozenSchedulePanel query={query} onSourceReadStart={start} onSourceReadEnd={end} onClose={close}/>))}
const button=(label:string)=>{const b=[...container.querySelectorAll('button')].find(b=>b.textContent===label);expect(b).toBeTruthy();return b!}
async function click(label:string){await act(async()=>button(label).click())}
async function fill(label:string,value:string){
 const e=container.querySelector<HTMLInputElement|HTMLTextAreaElement>(`[aria-label="${label}"]`)!;expect(e).toBeTruthy()
 await act(async()=>{const prototype=e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))})
}
async function remount(query=planningQuery){await act(async()=>root.unmount());root=createRoot(container);await render(query)}

it('shows pending history separately from physical work, blank assumptions and customer ownership',async()=>{
 response(false);await render();expect(client.rpc).not.toHaveBeenCalled();await click('Ambil stok proses terbaru')
 expect(container.textContent).toContain('Riwayat stok sedang disiapkan');expect(container.textContent).toContain('perhitungan kebutuhan belum selesai')
 expect(container.querySelector<HTMLInputElement>('[aria-label="Waktu satu PCS baru"]')!.value).toBe('')
 expect(container.querySelector<HTMLInputElement>(`[aria-label="SEWING menit ${workKey}"]`)!.value).toBe('')
 expect(container.querySelector(`[aria-label="Bagus ${customerKey}"]`)).toBeNull();expect(container.textContent).toContain('tidak menambah stok perusahaan')
 expect(readFrozenAnalysisRequest(actor,scope).pending).toBeNull();expect(start).toHaveBeenCalledTimes(1);expect(end).toHaveBeenCalledTimes(1)
})
it('retains original method/query/UUID until validated work and recovers after remount with a different query',async()=>{
 client.rpc.mockImplementation(async(name:string,args:{p_request:string})=>name==='erp_cp7_request_bounded_staged_analysis_v2'?{data:scheduleJobWire(args.p_request),error:null}:{data:null,error:Error('reply lost')})
 await render();await click('Ambil stok proses terbaru');const first=structuredClone(client.rpc.mock.calls[0]),held=readFrozenAnalysisRequest(actor,scope).pending
 expect(held).toEqual({id:first[1].p_request,actor,q:planningQuery,method:FROZEN_ANALYSIS_REQUEST});expect(container.querySelector('form')).toBeNull()
 response();await remount({...planningQuery,from_date:'2026-09-28'});await click('Ulangi pembacaan stok proses')
 expect(client.rpc.mock.calls[2]).toEqual(first);expect(readFrozenAnalysisRequest(actor,scope).pending).toBeNull();expect(container.querySelector('form')).toBeTruthy()
})
it('rejects a previous-method workspace without clearing its v2 source request',async()=>{
 client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_source_request:string})=>({data:name==='erp_cp7_request_bounded_staged_analysis_v2'?scheduleJobWire(args.p_request):boundedWorkspaceWire(args.p_source_request),error:null}))
 await render();await click('Ambil stok proses terbaru');expect(container.querySelector('form')).toBeNull();expect(readFrozenAnalysisRequest(actor,scope).pending).not.toBeNull();expect(container.querySelector('[role=alert]')).toBeTruthy()
})
it('persists the exact save before send and replays reply loss with original microseconds after remount',async()=>{
 response();await render();await click('Ambil stok proses terbaru');await fill('Alasan jadwal','reviewed unchanged timestamps')
 let persisted=false
 client.rpc.mockImplementation(async(_name:string,args:{p_request:string;p_payload:unknown})=>{persisted=readFrozenScheduleRequest(scope,actor).pending?.id===args.p_request;return{data:null,error:Error('reply lost')}})
 await click('Simpan jadwal yang diperiksa');const first=structuredClone(client.rpc.mock.calls.at(-1)!),held=readFrozenScheduleRequest(scope,actor).pending,bytes=localStorage.getItem(frozenScheduleRequestKey(scope,actor))
 expect(persisted).toBe(true);expect(held?.sourceMethod).toBe('FROZEN_V2');expect(first[1].p_payload.config).toEqual(scheduleConfig)
 expect(first[1].p_payload.config.through_at).toBe('2026-10-02T12:00:00.123456Z');expect(first[1].p_payload.actor).toBeUndefined()
 response();await remount();await click('Ulangi simpan jadwal yang sama');expect(client.rpc.mock.calls.at(-1)).toEqual(first);expect(bytes).not.toBeNull()
 expect(readFrozenScheduleRequest(scope,actor).pending).toBeNull();expect(container.textContent).toContain('Jadwal tersimpan')
})
it.each(['read-first','save-first'])('recovers coexisting read and save independently: %s',async order=>{
 const read:FrozenAnalysisRequest={id:demandRequest,actor,q:planningQuery,method:FROZEN_ANALYSIS_REQUEST},saved=savedCommand()
 await persistFrozenAnalysisRequest(actor,scope,read);await persistFrozenScheduleRequest(scope,saved);response();await render()
 expect(button('Ambil stok proses terbaru').disabled).toBe(true)
 await click(order==='read-first'?'Ulangi pembacaan stok proses':'Ulangi simpan jadwal yang sama')
 expect(order==='read-first'?readFrozenScheduleRequest(scope,actor).pending:readFrozenAnalysisRequest(actor,scope).pending).toEqual(order==='read-first'?saved:read)
 await click(order==='read-first'?'Ulangi simpan jadwal yang sama':'Ulangi pembacaan stok proses')
 expect(readFrozenAnalysisRequest(actor,scope).pending).toBeNull();expect(readFrozenScheduleRequest(scope,actor).pending).toBeNull()
 expect(client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_staged_production_schedule_v1')).toEqual([['erp_cp7_save_staged_production_schedule_v1',{p_request:saved.id,p_payload:saved.payload}]])
})
it('retires a held reply on storage replacement without clearing the replacement request',async()=>{
 let release!:(v:unknown)=>void,id=''
 client.rpc.mockImplementation((name:string,args:{p_request:string})=>{if(name==='erp_cp7_request_bounded_staged_analysis_v2'){id=args.p_request;return Promise.resolve({data:scheduleJobWire(id),error:null})}return new Promise(r=>{release=r})})
 await render();await click('Ambil stok proses terbaru');const key=frozenAnalysisRequestKey(actor,scope),replacement={id:crypto.randomUUID(),actor,q:planningQuery,method:FROZEN_ANALYSIS_REQUEST}
 localStorage.setItem(key,JSON.stringify(replacement));await act(async()=>dispatchEvent(new StorageEvent('storage',{key})))
 await act(async()=>release({data:wire(id),error:null}));expect(container.querySelector('form')).toBeNull();expect(readFrozenAnalysisRequest(actor,scope).pending).toEqual(replacement);expect(end).toHaveBeenCalledTimes(1)
})
it('keeps dirty input on a newer revision and requires explicit adoption',async()=>{
 response();await render();await click('Ambil stok proses terbaru');await fill('Waktu satu PCS baru','3')
 const fresh=wire(client.rpc.mock.calls[0][1].p_request);fresh.revision='2';fresh.plan!.revision='2';fresh.plan!.config.unit_minutes='4'
 client.rpc.mockResolvedValue({data:fresh,error:null});await click('Periksa sumber stok proses')
 expect(container.querySelector<HTMLInputElement>('[aria-label="Waktu satu PCS baru"]')!.value).toBe('3');expect(button('Simpan jadwal yang diperiksa').disabled).toBe(true);expect(container.textContent).toContain('Isianmu masih ada')
 await click('Gunakan sumber jadwal terbaru');expect(container.querySelector<HTMLInputElement>('[aria-label="Waktu satu PCS baru"]')!.value).toBe('4')
})
it('blocks UNKNOWN physical work without fabricating zero or a production quantity',async()=>{
 client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_source_request:string})=>({data:name==='erp_cp7_request_bounded_staged_analysis_v2'?scheduleJobWire(args.p_request):{...wire(args.p_source_request,false),production_capture_state:'UNKNOWN',position_requirements:[]},error:null}))
 await render();await click('Ambil stok proses terbaru');expect(container.textContent).toContain('Jumlah stok proses belum dapat dicocokkan');expect(button('Simpan jadwal yang diperiksa').disabled).toBe(true)
 expect(container.querySelectorAll('.native-production-work')).toHaveLength(0)
})
it.each([{code:'42501'},{status:403},{status:401}])('retires displayed work on current access denial and retains exact save: %j',async denied=>{
 response();await render();await click('Ambil stok proses terbaru');await fill('Alasan jadwal','reviewed')
 client.rpc.mockResolvedValue({data:null,error:{...denied,message:'access changed'}});await click('Simpan jadwal yang diperiksa')
 expect(container.querySelector('form')).toBeNull();expect(container.querySelector('.native-demand-current')).toBeNull();expect(readFrozenScheduleRequest(scope,actor).pending).not.toBeNull()
})
it('rechecks permission while a reply is pending and blocks retry after manage permission is removed',async()=>{
 let release!:(v:unknown)=>void,id=''
 client.rpc.mockImplementation((name:string,args:{p_request:string})=>{if(name==='erp_cp7_request_bounded_staged_analysis_v2'){id=args.p_request;return Promise.resolve({data:scheduleJobWire(id),error:null})}return new Promise(r=>{release=r})})
 await render();await click('Ambil stok proses terbaru');const a=state.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='warehouse.stock.view');await render()
 await act(async()=>release({data:wire(id),error:null}));expect(container.querySelector('section')).toBeNull();expect(readFrozenAnalysisRequest(actor,scope).pending?.id).toBe(id);expect(end).toHaveBeenCalledTimes(1)
 a.identity.permissions.push('warehouse.stock.view');a.identity.permissions=a.identity.permissions.filter(p=>p!=='master.product.manage');await persistFrozenScheduleRequest(scope,savedCommand());await render()
 expect(button('Ulangi simpan jadwal yang sama').disabled).toBe(true)
})
it('isolates old v1 storage and refuses corrupt new storage without replacing either',async()=>{
 const oldKey=scheduleRequestKey('cp6-disposable:actor-1'),key=frozenScheduleRequestKey(scope,actor);localStorage.setItem(oldKey,'untouched-v1');localStorage.setItem(key,'broken-v2');await render()
 expect(button('Ambil stok proses terbaru').disabled).toBe(true);expect(localStorage.getItem(oldKey)).toBe('untouched-v1');expect(localStorage.getItem(key)).toBe('broken-v2');expect(client.rpc).not.toHaveBeenCalled()
})
it('sends only one command on double click and ignores a late reply after close',async()=>{
 let release!:(v:unknown)=>void;client.rpc.mockImplementation(()=>new Promise(r=>{release=r}));await render()
 await act(async()=>{const b=button('Ambil stok proses terbaru');b.click();b.click()});expect(client.rpc).toHaveBeenCalledTimes(1)
 const id=client.rpc.mock.calls[0][1].p_request;await click('Tutup jadwal produksi');await act(async()=>release({data:scheduleJobWire(id),error:null}))
 expect(client.rpc).toHaveBeenCalledTimes(1);expect(container.querySelector('form')).toBeNull();expect(close).toHaveBeenCalledTimes(1);expect(end).toHaveBeenCalledTimes(1);expect(readFrozenAnalysisRequest(actor,scope).pending?.id).toBe(id)
})
