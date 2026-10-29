// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import AttendancePeriodChoicePanel from './AttendancePeriodChoicePanel'
import type {AttendancePeriodChoicePanelProps} from './AttendancePeriodChoicePanel'
import {ATTENDANCE_CHOICE_ACTIONS,type AttendanceChoiceAction,type AttendanceChoicePayload,type AttendanceChoiceWorkspace} from './attendancePeriodChoiceContract'
import {persistProductionEnvelope,productionKey,readProductionRecovery,type ProductionEnvelope} from './productionRecovery'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {attendanceChoiceCurrent as current,attendanceChoiceEnvelope as envelope,attendanceChoiceHistory as history,attendanceChoiceIds as ids,attendanceChoiceOutcomeFixture as outcome,attendanceChoicePreviewFixture as preview,attendanceChoiceQuery as query,attendanceChoiceWorkspace as workspace} from '../tests/fixtures/attendancePeriodChoice'
const auth=vi.hoisted(()=>({current:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>auth.current}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
type Row=Record<string,unknown>
type Response={data:unknown;error:unknown}
let root:Root,container:HTMLDivElement,state:{w:AttendanceChoiceWorkspace;lose:boolean;effects:number;refusal:unknown;previewRefusal:unknown;receipts:Map<string,unknown>}
const committed=vi.fn(async()=>true),invalid=vi.fn()
const sourcePeriod={start:query.period_start,end:query.period_end}
function owner(extra:Row={}){return {...recoveryIdentity,identity:{...recoveryIdentity.identity,profile:{...recoveryIdentity.identity.profile,id:ids.actor,authUserId:ids.actor,fullName:'Owner Uji',rowVersion:1,roleRowVersion:1},permissions:['finance.hpp.view','finance.hpp.manage'],...extra}}}
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();committed.mockClear();invalid.mockClear();auth.current=owner()
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,_options:unknown,cb:(lock:unknown)=>Promise<unknown>)=>cb({name:'global',mode:'exclusive'})}})
 state={w:workspace(),lose:false,effects:0,refusal:null,previewRefusal:null,receipts:new Map()}
 client.rpc.mockImplementation(async(name:string,args:Row):Promise<Response>=>{
  if(name==='erp_cp7_get_attendance_choice_v1'){
   const start=args.p_period_start as string,end=args.p_period_end as string,offset=args.p_offset as number,limit=args.p_limit as number
   const all=state.w.history,rows=all.slice(offset,offset+limit)
   return {data:{...state.w,period_start:start,period_end:end,offset,limit,history:rows,history_total:String(all.length),next_offset:offset+rows.length<all.length?offset+rows.length:null},error:null}
  }
  if(name==='erp_cp7_preview_attendance_choice_v1')return state.previewRefusal?{data:null,error:state.previewRefusal}:{data:preview(state.w,args.p_payload as AttendanceChoicePayload,args.p_action as AttendanceChoiceAction),error:null}
  if(name==='erp_cp7_save_attendance_choice_v1'){
   if(state.refusal)return {data:null,error:state.refusal}
   const key=args.p_request as string,p=args.p_payload as AttendanceChoicePayload,a=args.p_action as AttendanceChoiceAction
   const e:ProductionEnvelope={action:a,payload:args.p_payload as ProductionEnvelope['payload'],expectedVersion:null,id:key,createdAt:'2026-10-30T00:00:00Z',fingerprint:JSON.stringify({action:a,payload:args.p_payload,expectedVersion:null})}
   if(!state.receipts.has(key)){state.effects++;state.receipts.set(key,outcome(e));state.w=a==='CHOOSE'||a==='CORRECT'?current(p.choice??'CARRY'):a==='ALLOCATE'?current('CARRY',true):a==='CANCEL_ALLOCATION'?current():workspace()}
   return state.lose?{data:null,error:{status:503,message:'Lost response'}}:{data:state.receipts.get(key),error:null}
  }
  throw Error('Unexpected RPC '+name)
 })
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(props:Partial<AttendancePeriodChoicePanelProps>={}){await act(async()=>root.render(<AttendancePeriodChoicePanel onCommitted={committed} onInvalid={invalid} initialPeriod={sourcePeriod} {...props}/>));await flush()}
const button=(label:string)=>[...container.querySelectorAll<HTMLButtonElement>('button')].find(x=>x.textContent===label)!
const field=(label:string)=>container.querySelector<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>(`[aria-label="${label}"]`)!
async function change(label:string,value:string){await act(async()=>{const el=field(label),proto=el instanceof HTMLSelectElement?HTMLSelectElement.prototype:el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(el,value);el.dispatchEvent(new Event(el instanceof HTMLSelectElement?'change':'input',{bubbles:true}))});await flush()}
async function click(el:HTMLElement){await act(async()=>el.click());await flush()}
const writes=()=>client.rpc.mock.calls.filter(c=>c[0]==='erp_cp7_save_attendance_choice_v1')
async function input(a:AttendanceChoiceAction='CHOOSE',selected:'CARRY'|'EXPENSE'='CARRY'){
 await change('Tindakan pilihan biaya',a)
 if(a==='CHOOSE'||a==='CORRECT')await change('Pilihan biaya absensi',selected)
 if(a==='ALLOCATE'){await change('Mulai periode hasil jahit','2026-10-08');await change('Akhir periode hasil jahit','2026-10-14')}
 await change('Alasan pilihan biaya absensi','Biaya periode sudah diperiksa Owner')
}
async function reviewed(){await click(button('Periksa perubahan biaya'));await click(field('Pilihan biaya sudah diperiksa'))}
describe('S03 standalone UI with declared SQL/RPC doubles; zero Auth/browser/Native credit',()=>{
 it('reads with all four exact arguments and never creates an automatic decision',async()=>{
  await mount();expect(client.rpc.mock.calls[0]).toEqual(['erp_cp7_get_attendance_choice_v1',{p_period_start:query.period_start,p_period_end:query.period_end,p_offset:0,p_limit:25}]);expect(container.textContent).toContain('Rp100');expect(writes()).toHaveLength(0);expect(button('Simpan pilihan biaya').disabled).toBe(true);expect(field('Tindakan pilihan biaya').value).toBe('')
 })
 it('requires actual Owner/view/manage rights and authoritative can_manage',async()=>{
  auth.current=owner({profile:{...(owner().identity.profile),role:'ADMIN'}});await mount();expect(client.rpc).not.toHaveBeenCalled();expect(container.textContent).toContain('Owner aktif')
  auth.current=owner({permissions:['finance.hpp.view']});await mount();expect(container.textContent).toContain('memerlukan hak mengelola HPP');expect(container.querySelector('[aria-label="Tindakan pilihan biaya"]')).toBeNull()
  auth.current=owner();state.w.can_manage=false;await mount({refresh:1});expect(container.querySelector('[aria-label="Tindakan pilihan biaya"]')).toBeNull();expect(writes()).toHaveLength(0)
 })
 it.each(ATTENDANCE_CHOICE_ACTIONS)('reviews and sends %s once with exactly six fields plus its token',async a=>{
  if(a!=='CHOOSE')state.w=current(a==='REVERSE'?'EXPENSE':'CARRY',a==='CANCEL_ALLOCATION')
  await mount();await input(a);expect(button('Simpan pilihan biaya').disabled).toBe(true);await reviewed();expect(button('Simpan pilihan biaya').disabled).toBe(false)
  await act(async()=>{button('Simpan pilihan biaya').click();button('Simpan pilihan biaya').click()});await flush()
  expect(writes()).toHaveLength(1);const args=writes()[0][1] as Row;expect(args.p_action).toBe(a);expect(Object.keys(args.p_payload as Row).sort()).toEqual(['period_start','period_end','choice','output_start','output_end','reason','review_token'].sort());expect((args.p_payload as Row).review_token).toBe('b'.repeat(64));expect(state.effects).toBe(1);expect(committed).toHaveBeenCalledOnce()
 })
 it('allows only owning reversal when source-period sewing appears after a choice',async()=>{
  state.w={...current(),original_period_sewing_qty:'1'};await mount();const actions=[...container.querySelectorAll<HTMLSelectElement>('[aria-label="Tindakan pilihan biaya"] option')].map(e=>e.value);expect(actions).toEqual(['','REVERSE']);expect(writes()).toHaveLength(0)
 })
 it('reads an owning PostgreSQL md5 UUID choice and keeps audit IDs intact',async()=>{
  const pg='f3b101d0-158b-cc5c-fd15-058776bab27e',w=current(),h=w.history[0];if(h.event!=='CHOOSE')throw Error('fixture');state.w={...w,current_choice:{...w.current_choice!,decision_id:pg},history:[{...h,event_id:pg,decision_id:pg}]};await mount();expect(container.textContent).toContain(pg);expect(container.textContent).toContain('Pilihan yang berlaku');expect(writes()).toHaveLength(0)
 })
 it('shows an active carried allocation as allocated, without claiming its cost is still waiting',async()=>{
  state.w=current('CARRY',true);await mount();expect(container.textContent).toContain('Biaya sudah dialokasikan');expect(container.textContent).not.toContain('Biaya masih menunggu. Belum ada jurnal alokasi');expect(container.textContent).toContain(ids.pool)
 })
 it('shows the exact expense account, amount, source period and both dates before confirmation',async()=>{
  await mount();await input('CHOOSE','EXPENSE');await click(button('Periksa perubahan biaya'));const q=container.querySelector('[aria-label="Tinjauan perubahan biaya"]')!;expect(q.textContent).toContain('Beban periode ini');expect(q.textContent).toContain('Rp100');expect(q.textContent).toContain('6200 · Beban periode absensi');expect(q.textContent).toContain('Tanggal ekonomi: 2026-10-07 · tanggal buku: 2026-10-07');expect(button('Simpan pilihan biaya').disabled).toBe(true);expect(writes()).toHaveLength(0)
 })
 it('does not turn unknown figures into zero and blocks even typed retained facts with a source problem',async()=>{
  state.w=workspace({source_problem:'CP7_S03_NO_ELIGIBLE_COST',amount_cents:null,source_binding:null,original_period_sewing_qty:null});await mount();expect(container.textContent).toContain('Belum diketahui');expect(container.textContent).not.toContain('Rp0');expect(button('Periksa perubahan biaya').disabled).toBe(true)
  state.w=workspace({source_problem:'CP7_S03_SOURCE_CHANGED'});await mount({refresh:1});expect(button('Periksa perubahan biaya').disabled).toBe(true);expect(writes()).toHaveLength(0)
 })
 it('retires review immediately when reason, action, date, source refresh or parent block changes',async()=>{
  await mount();await input();await reviewed();await change('Alasan pilihan biaya absensi','Alasan diperbarui Owner');expect(button('Simpan pilihan biaya').disabled).toBe(true);expect(container.querySelector('[aria-label="Tinjauan perubahan biaya"]')).toBeNull()
  await reviewed();await mount({blocked:true});expect(button('Simpan pilihan biaya')?.disabled??true).toBe(true);expect(container.querySelector('[aria-label="Tinjauan perubahan biaya"]')).toBeNull();await mount({blocked:false,refresh:1});expect(writes()).toHaveLength(0)
  await change('Mulai periode asal','2026-10-02');expect(container.querySelector('[aria-label="Tinjauan perubahan biaya"]')).toBeNull();expect(button('Simpan pilihan biaya')).toBeUndefined()
 })
 it('discards a delayed preview when input or actor changes and never copies it into the new context',async()=>{
  await mount();await input();let resolve!:(r:Response)=>void;client.rpc.mockImplementationOnce(()=>new Promise<Response>(r=>{resolve=r}));await click(button('Periksa perubahan biaya'));await change('Alasan pilihan biaya absensi','Isian baru saat respons masih berjalan')
  await act(async()=>resolve({data:preview(workspace(),{period_start:query.period_start,period_end:query.period_end,choice:'CARRY',output_start:null,output_end:null,reason:'Biaya periode sudah diperiksa Owner'},'CHOOSE'),error:null}));await flush();expect(container.querySelector('[aria-label="Tinjauan perubahan biaya"]')).toBeNull()
  let reply!:(r:Response)=>void;client.rpc.mockImplementationOnce(()=>new Promise<Response>(r=>{reply=r}));await click(button('Periksa perubahan biaya'));auth.current=owner({profile:{...owner().identity.profile,id:'00000000-0000-4000-8000-000000000099'}});await mount();await act(async()=>reply({data:{},error:null}));await flush();expect(container.querySelector('[aria-label="Tinjauan perubahan biaya"]')).toBeNull();expect(writes()).toHaveLength(0);expect(invalid).not.toHaveBeenCalled()
 })
 it('does not publish a delayed period read after the source period has changed',async()=>{
  let resolve!:(r:Response)=>void;client.rpc.mockImplementationOnce(()=>new Promise<Response>(r=>{resolve=r}));await mount();await change('Mulai periode asal','2026-10-02');await act(async()=>resolve({data:workspace(),error:null}));await flush();expect(container.textContent).not.toContain('Biaya absensi sumber');expect(writes()).toHaveLength(0)
 })
 it('retires permission-denied preview and preserves operator input without post or silent zero',async()=>{
  await mount();await input();state.previewRefusal={code:'42501',status:403,message:'CP7_S03_ACCESS_CHANGED'};await click(button('Periksa perubahan biaya'));expect(invalid).toHaveBeenCalledOnce();expect(container.textContent).toContain('Hak akses berubah');expect(container.querySelector('[aria-label="Tinjauan perubahan biaya"]')).toBeNull();expect(writes()).toHaveLength(0)
  state.previewRefusal=null;await click(button('Muat ulang periode'));expect(field('Alasan pilihan biaya absensi').value).toBe('Biaya periode sudah diperiksa Owner');expect(button('Simpan pilihan biaya').disabled).toBe(true)
 })
 it('retires stale source preview, reloads current source and requires explicit review again',async()=>{
  await mount();await input();state.previewRefusal={code:'P0001',message:'CP7_S03_STALE_REVIEW: changed'};await click(button('Periksa perubahan biaya'));expect(container.textContent).toContain('Muat ulang periode lalu periksa perubahan lagi');expect(field('Alasan pilihan biaya absensi').value).toBe('Biaya periode sudah diperiksa Owner');expect(button('Simpan pilihan biaya').disabled).toBe(true);expect(writes()).toHaveLength(0)
 })
 it('keeps the explicit initial refusal after reload without reporting a committed decision',async()=>{
  await mount();await input('CHOOSE','EXPENSE');await reviewed();state.refusal={code:'P0001',message:'CP7_S03_EXPENSE_BEFORE_WIP_AVAILABLE: source date'};await click(button('Simpan pilihan biaya'));expect(container.textContent).toContain('Biaya belum tersedia pada tanggal pengakuan atau tanggal buku');expect(field('Alasan pilihan biaya absensi').value).toBe('Biaya periode sudah diperiksa Owner');expect(committed).not.toHaveBeenCalled();expect(state.effects).toBe(0);expect(readProductionRecovery('disposable:'+ids.actor).pending).toEqual({});expect(button('Simpan pilihan biaya').disabled).toBe(true)
 })
 it('distinguishes confirmed commit from a failed parent refresh and never resubmits that decision',async()=>{
  await mount();await input();await reviewed();committed.mockRejectedValueOnce(Error('parent refresh failed'));await click(button('Simpan pilihan biaya'));expect(container.textContent).toContain('Pilihan sudah tercatat, tetapi periode belum berhasil dimuat ulang');expect(state.effects).toBe(1);expect(readProductionRecovery('disposable:'+ids.actor).pending).toEqual({});expect(writes()).toHaveLength(1);await click(button('Muat ulang periode'));expect(container.textContent).not.toContain('tetapi periode belum berhasil dimuat ulang');expect(writes()).toHaveLength(1)
 })
 it('keeps one uncertain UUID/action/token/payload through remount and explicitly recovers the historical receipt',async()=>{
  await mount();await input();await reviewed();state.lose=true;await click(button('Simpan pilihan biaya'));expect(state.effects).toBe(1);const original=structuredClone(writes()[0][1]);expect(container.textContent).toContain('Jawaban penyimpanan sebelumnya belum pasti');expect(button('Simpan pilihan biaya').disabled).toBe(true)
  await act(async()=>root.unmount());root=createRoot(container);await mount();expect(writes()).toHaveLength(1);state.lose=false;await click(button('Periksa hasil penyimpanan'));expect(writes()).toHaveLength(2);expect(writes()[1][1]).toEqual(original);expect(state.effects).toBe(1);expect(readProductionRecovery('disposable:'+ids.actor).pending).toEqual({});expect(committed).toHaveBeenCalledOnce()
 })
 it.each([{name:'different',period:{start:'2026-10-08',end:'2026-10-14'}},{name:'empty',period:{start:'',end:''}}])('keeps old-period identity separate after $name-period remount for uncertain and confirmed replay',async({period})=>{
  await mount();await input();await reviewed();state.lose=true;await click(button('Simpan pilihan biaya'));const original=structuredClone(writes()[0][1]);await act(async()=>root.unmount());root=createRoot(container);state.w=workspace();await mount({initialPeriod:period});
  const pending=container.querySelector('[aria-label="Permintaan biaya absensi tertunda"]')!;expect(pending).not.toBeNull();expect(pending.textContent).toContain('1 Okt 2026');expect(pending.textContent).toContain('7 Okt 2026');expect(pending.textContent).toContain((original as Row).p_request as string);expect(field('Mulai periode asal').value).toBe(period.start);expect(field('Akhir periode asal').value).toBe(period.end)
  await click(button('Periksa hasil penyimpanan'));expect(writes()[1][1]).toEqual(original);expect(readProductionRecovery('disposable:'+ids.actor).pending.ATTENDANCE_PERIOD_CHOICE?.id).toBe((original as Row).p_request);expect(committed).not.toHaveBeenCalled();expect(field('Mulai periode asal').value).toBe(period.start)
  const reads=client.rpc.mock.calls.filter(c=>c[0]==='erp_cp7_get_attendance_choice_v1').length;state.lose=false;await click(button('Periksa hasil penyimpanan'));expect(writes()[2][1]).toEqual(original);expect(state.effects).toBe(1);expect(readProductionRecovery('disposable:'+ids.actor).pending).toEqual({});expect(committed).not.toHaveBeenCalled();expect(field('Mulai periode asal').value).toBe(period.start);expect(field('Akhir periode asal').value).toBe(period.end);expect(container.textContent).not.toContain('Pilihan biaya absensi sudah tercatat.');expect(client.rpc.mock.calls.filter(c=>c[0]==='erp_cp7_get_attendance_choice_v1')).toHaveLength(reads);const recovered=container.querySelector('[aria-label="Hasil permintaan periode terdahulu"]');expect(recovered?.textContent).toContain('1 Okt 2026');expect(recovered?.textContent).toContain('7 Okt 2026')
 })
 it.each([{name:'different',period:{start:'2026-10-08',end:'2026-10-14'}},{name:'empty',period:{start:'',end:''}}])('does not publish a confirmed old receipt or parent commit into the $name visible period',async({period})=>{
  await mount();await input();await reviewed();state.lose=true;await click(button('Simpan pilihan biaya'));const original=structuredClone(writes()[0][1]);await act(async()=>root.unmount());root=createRoot(container);state.w=workspace();await mount({initialPeriod:period});state.lose=false;await click(button('Periksa hasil penyimpanan'));expect(writes()[1][1]).toEqual(original);expect(state.effects).toBe(1);expect(committed).not.toHaveBeenCalled();expect(container.textContent).not.toContain('Pilihan biaya absensi sudah tercatat.');expect(field('Mulai periode asal').value).toBe(period.start);expect(field('Akhir periode asal').value).toBe(period.end)
 })
 it('keeps uncertain UUID after a replay permission refusal and never starts a new request',async()=>{
  await mount();await input();await reviewed();state.lose=true;await click(button('Simpan pilihan biaya'));const original=writes()[0][1] as Row;state.lose=false;state.refusal={code:'42501',message:'CP7_S03_OWNER_REQUIRED'};await click(button('Periksa hasil penyimpanan'));expect(writes()[1][1]).toEqual(original);expect(readProductionRecovery('disposable:'+ids.actor).pending.ATTENDANCE_PERIOD_CHOICE?.id).toBe(original.p_request);expect(committed).not.toHaveBeenCalled();expect(container.textContent).not.toContain('sudah tercatat')
 })
 it('honors a foreign global pending writer and corrupt own recovery without deleting their records',async()=>{
  await mount();await input();await reviewed();const foreign={...envelope(),action:'HOLD_BS',payload:{x:1},expectedVersion:1};foreign.fingerprint=JSON.stringify({action:foreign.action,payload:foreign.payload,expectedVersion:1});await act(async()=>{expect(persistProductionEnvelope('disposable:'+ids.actor,'BS',foreign)).toBe(true)});await flush();expect(button('Simpan pilihan biaya').disabled).toBe(true);expect(container.textContent).toContain('transaksi lain');expect(writes()).toHaveLength(0)
  await act(async()=>root.unmount());root=createRoot(container);localStorage.clear();const key=productionKey('disposable:'+ids.actor,'ATTENDANCE_PERIOD_CHOICE');localStorage.setItem(key,'{');await mount();expect(container.textContent).toContain('tidak dapat dibaca');expect(localStorage.getItem(key)).toBe('{');expect(writes()).toHaveLength(0)
 })
 it('discards a late save response after actor replacement, preserving the old actor recovery record',async()=>{
  await mount();await input();await reviewed();let resolve!:(r:Response)=>void;client.rpc.mockImplementationOnce(()=>new Promise<Response>(r=>{resolve=r}));await click(button('Simpan pilihan biaya'));const args=writes()[0][1] as Row,e={...envelope(),id:args.p_request as string,payload:args.p_payload as ProductionEnvelope['payload']};
  const actor='00000000-0000-4000-8000-000000000099';auth.current=owner({profile:{...owner().identity.profile,id:actor,authUserId:actor}});await mount();await act(async()=>resolve({data:outcome(e),error:null}));await flush();expect(committed).not.toHaveBeenCalled();expect(container.textContent).not.toContain('sudah tercatat');expect(readProductionRecovery('disposable:'+ids.actor).pending.ATTENDANCE_PERIOD_CHOICE?.id).toBe(args.p_request);expect(readProductionRecovery('disposable:'+actor).pending).toEqual({});expect(writes()).toHaveLength(1)
 })
 it('retires a prepared review on current manage-right revocation',async()=>{
  await mount();await input();await reviewed();auth.current=owner({permissions:['finance.hpp.view']});await mount();expect(container.querySelector('[aria-label="Tinjauan perubahan biaya"]')).toBeNull();expect(container.querySelector('[aria-label="Tindakan pilihan biaya"]')).toBeNull();expect(writes()).toHaveLength(0)
 })
 it('retains the exact pending request when a success response is malformed',async()=>{
  await mount();await input();await reviewed();client.rpc.mockImplementationOnce(async()=>({data:{status:'COMMITTED'},error:null}));await click(button('Simpan pilihan biaya'));const args=writes()[0][1] as Row;expect(readProductionRecovery('disposable:'+ids.actor).pending.ATTENDANCE_PERIOD_CHOICE?.id).toBe(args.p_request);expect(container.textContent).toContain('Jawaban penyimpanan sebelumnya belum pasti');expect(committed).not.toHaveBeenCalled()
 })
 it('paginates exact audit events, preserves microsecond order and displays WIB timestamps and actors',async()=>{
  const events=history();for(let n=0;n<23;n++)events.push({...history()[2],event_id:`00000000-0000-4000-8000-${String(100+n).padStart(12,'0')}`,decision_id:`00000000-0000-4000-8000-${String(100+n).padStart(12,'0')}`});events.sort((a,b)=>b.recorded_at.localeCompare(a.recorded_at)||b.event_id.localeCompare(a.event_id));state.w=workspace({history:events,history_total:String(events.length)});await mount();expect(container.querySelectorAll('.attendance-choice-history li')).toHaveLength(25);expect(container.textContent).toContain('WIB');expect(container.textContent).toContain(ids.actor);await click(button('Riwayat berikutnya'));expect(client.rpc.mock.calls.at(-1)?.[1].p_offset).toBe(25);expect(container.querySelectorAll('.attendance-choice-history li')).toHaveLength(1);expect(container.textContent).toContain('26 catatan riwayat');expect(writes()).toHaveLength(0)
 })
})
