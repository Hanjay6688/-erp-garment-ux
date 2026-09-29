// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedAttendancePage from './ConnectedAttendancePage'
import {parseAttendanceRead,parseRosterOutcome,type AttendancePeriod,type AttendanceWorker} from './attendanceContract'
import {cp6WibDateTimeInput} from './cp6BusinessTime'
import {readProductionRecovery} from './productionRecovery'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',wid='22222222-2222-4222-8222-222222222222',pid='33333333-3333-4333-8333-333333333333',rid='44444444-4444-4444-8444-444444444444',day=cp6WibDateTimeInput().slice(0,10)
const c={id,name:'Mandor riwayat',active_now:true,attendance_required:true}
const w:AttendanceWorker={id:wid,contractor_id:id,code:null,name:'Pekerja historis',job_description:'Jahit',pay_scheme:'DAILY',active_now:false,joined_at:'2025-01-01',left_at:day,notes:null,row_version:'9007199254740993',rate_at:day,daily_rate_at_date:'100.123456',employed_at_date:true}
const h:AttendancePeriod={id:pid,contractor_id:id,number:'ABS-001',period_start:day,period_end:day,pay_date:day,status:'POSTED',correction_of_id:null,notes:null,row_version:'9007199254740993',record_count:'1',consuming_payroll_count:'1'}
const rate={id:rid,worker_id:wid,daily_rate:'100.123456',date_from:'2025-01-01',date_to:null,reason:'Tarif historis'}
const episode={id:rid,worker_id:wid,date_from:'2025-01-01',date_to:day,start_reason:'Mulai bekerja',end_reason:'Berhenti'}
const record={id:rid,period_id:pid,worker_id:wid,worker_name:w.name,date:day,mark:'HALF_DAY',paid_fraction:'0.5000',lifecycle:'POSTED',supersedes_id:null,notes:null,row_version:'9007199254740993'}
function payload(section:string){return {contract_version:'cp7.attendance-workspace.v1',section,date_from:section==='CONTRACTORS'?null:day,date_to:section==='CONTRACTORS'?null:day,source_token:section==='CONTRACTORS'?null:'a'.repeat(32),contractor:section==='CONTRACTORS'?null:c,worker:['RATES','EMPLOYMENT'].includes(section)?w:null,period:section==='RECORDS'?h:null,page:{rows:({CONTRACTORS:[c],WORKERS:[w],PERIODS:[h],RATES:[rate],EMPLOYMENT:[episode],RECORDS:[record]} as Record<string,unknown[]>)[section],total:'1',offset:0,limit:25,next_offset:null as number|null}}}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});const a=structuredClone(recoveryIdentity);a.identity.permissions=['finance.attendance.view'];state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<ConnectedAttendancePage/>));await flush()}
async function click(match:string){const button=[...container.querySelectorAll('button')].find(x=>x.textContent?.startsWith(match));if(!button)throw Error(match);await act(async()=>button.click());await flush()}
function server(){client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>({error:null,data:payload(args.p_section)}))}
describe('dated attendance source boundary',()=>{
 it('retains exact six-decimal prices and bigint versions with explicit missing rates',()=>{
  const p=payload('WORKERS');p.page.rows=[{...w,daily_rate_at_date:'9007199254740993.123456'}]
  const row=parseAttendanceRead(p,'WORKERS').page.rows[0] as AttendanceWorker;expect(row.daily_rate_at_date).toBe('9007199254740993.123456');expect(row.row_version).toBe('9007199254740993')
  p.page.rows=[{...w,daily_rate_at_date:null}];expect((parseAttendanceRead(p,'WORKERS').page.rows[0] as AttendanceWorker).daily_rate_at_date).toBeNull()
 })
 it('rejects a future rate, invalid calendar date, wrong worker parent, and excessive half-day fraction',()=>{
  const p=payload('RATES');p.page.rows=[{...rate,date_from:'9999-01-01'}];expect(()=>parseAttendanceRead(p,'RATES')).toThrow()
  p.page.rows=[{...rate,date_from:'2026-02-31'}];expect(()=>parseAttendanceRead(p,'RATES')).toThrow()
  p.page.rows=[{...rate,worker_id:pid}];expect(()=>parseAttendanceRead(p,'RATES')).toThrow()
  const r=payload('RECORDS');r.page.rows=[{...record,paid_fraction:'0.7500'}];expect(()=>parseAttendanceRead(r,'RECORDS')).toThrow()
 })
 it('keeps period record count independent of one page and refuses a mismatched total',()=>{
  const p=payload('RECORDS');p.period={...h,record_count:'2'};p.page={...p.page,total:'2',limit:1,next_offset:1}
  expect(parseAttendanceRead(p,'RECORDS').period?.record_count).toBe('2');p.page={...p.page,total:'1',next_offset:null};expect(()=>parseAttendanceRead(p,'RECORDS')).toThrow()
 })
 it('requires attendance permission before making a request even with payroll view',async()=>{const a=structuredClone(recoveryIdentity);a.identity.permissions=['finance.payroll.view'];state.auth=a;await mount();expect(container.textContent).toContain('Hak melihat absensi diperlukan');expect(client.rpc).not.toHaveBeenCalled()})
 it('reads inactive worker rates and employment history without writes',async()=>{server();await mount();await click('Mandor riwayat');expect(container.textContent).toContain('Nonaktif sekarang');await click('Pekerja historis');expect(container.querySelector('.catt-lines')?.textContent).toContain('Rp100,123456');await click('Riwayat masa kerja');expect(container.querySelector('.catt-lines')?.textContent).toContain('Berakhir: Berhenti');expect(client.rpc.mock.calls.every(([n])=>n==='erp_cp7_get_attendance_workspace_v1')).toBe(true)})
 it('shows payroll dependency and native mark without treating blanks as absences',async()=>{server();await mount();await click('Mandor riwayat');await click('Periode absensi');await click('ABS-001');expect(container.textContent).toContain('Dipakai oleh 1 payroll aktif');expect(container.textContent).toContain('Hari yang belum dicatat tidak dianggap');expect(container.querySelector('.catt-lines')?.textContent).toContain('Setengah hari');expect(container.querySelector('.catt-lines')?.textContent).toContain('0,5 hari dibayar')})
 it('retires all rate facts after a failed detail request and rejects mixed source revisions',async()=>{server();await mount();await click('Mandor riwayat');await click('Pekerja historis');client.rpc.mockImplementation(async(_n:string,a:{p_section:string})=>a.p_section==='RATES'?{error:{status:403,message:'Access revoked'},data:null}:{error:null,data:payload(a.p_section)});await click('Muat ulang absensi');expect(container.textContent).not.toContain('Rp');expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0)
  client.rpc.mockImplementation(async(_n:string,a:{p_section:string})=>{const p=payload(a.p_section);if(a.p_section==='RATES')p.source_token='b'.repeat(32);return {error:null,data:p}});await click('Muat ulang absensi');expect(container.textContent).toContain('Tarif atau riwayat kerja berubah');expect(container.textContent).not.toContain('Rp')
 })
})

async function input(label:string,value:string){const el=container.querySelector(`[aria-label="${label}"]`) as HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement;expect(el).not.toBeNull();await act(async()=>{const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(el,value);el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}))});await flush()}
function writerServer(lost=false){
 const a=structuredClone(recoveryIdentity);a.identity.permissions=['finance.attendance.view','finance.attendance.create','finance.attendance.edit_draft'];state.auth=a
 let current={...w},token='a'.repeat(32),replyLost=false;const cached=new Map<string,unknown>()
 client.rpc.mockImplementation(async(name:string,p:{p_section:string;p_action:string;p_request:string;p_expected:string|null;p_payload:{document:Record<string,unknown>}})=>{
  if(name==='erp_cp7_save_roster_v1'){
   if(cached.has(p.p_request))return {error:null,data:cached.get(p.p_request)}
   const d=p.p_payload.document;current={...current,row_version:(BigInt(current.row_version)+1n).toString(),...(p.p_action==='CREATE_WORKER'?{name:String(d.worker_name),active_now:Boolean(d.is_active),daily_rate_at_date:String(d.initial_daily_rate)}:{})};token='b'.repeat(32)
   const result={contract_version:'cp7.roster-outcome.v1',kind:'COMMITTED_OUTCOME',action:p.p_action,request_id:p.p_request,worker_id:wid,contractor_id:id,row_version:current.row_version,status:current.active_now?'ACTIVE':'INACTIVE',source_token:token};cached.set(p.p_request,result)
   if(lost&&!replyLost){replyLost=true;return {error:{status:503,message:'Lost response after commit'},data:null}}
   return {error:null,data:result}
  }
  const r=payload(p.p_section);if(p.p_section!=='CONTRACTORS')r.source_token=token;if(p.p_section==='WORKERS')r.page.rows=[current];if(['RATES','EMPLOYMENT'].includes(p.p_section))r.worker=current;return {error:null,data:r}
 })
}
describe('roster editor and durable exact intent',()=>{
 it('preserves native owner/admin authority even when a custom role has attendance edit permissions',async()=>{writerServer();const a=structuredClone(recoveryIdentity);a.identity.profile.role='CUSTOM' as typeof a.identity.profile.role;a.identity.permissions=['finance.attendance.view','finance.attendance.create','finance.attendance.edit_draft'];state.auth=a;await mount();await click('Mandor riwayat');await click('Pekerja historis');expect(container.textContent).not.toContain('Tambah pekerja');expect(container.textContent).not.toContain('Ubah pekerja');expect(container.textContent).not.toContain('Tambah tarif harian')})
 it('requires an explicit initial rate and sends six decimal string money, dates and reviewed source token',async()=>{writerServer();await mount();await click('Mandor riwayat');await click('Tambah pekerja');await input('Nama pekerja','Pekerja baru');await input('Pekerjaan pekerja','Jahit');await input('Alasan perubahan pekerja','Mulai kerja dan tarif telah diperiksa');const save=()=>[...container.querySelectorAll('button')].find(b=>b.textContent==='Simpan pekerja')!;expect(save().disabled).toBe(true);await input('Tarif harian pekerja','100,123456');expect(save().disabled).toBe(false);await click('Simpan pekerja');const p=client.rpc.mock.calls.find(([n])=>n==='erp_cp7_save_roster_v1')![1];expect(p.p_expected).toBeNull();expect(p.p_payload).toMatchObject({contractor_id:id,date_from:day,date_to:day,source_token:'a'.repeat(32),document:{initial_daily_rate:'100.123456',rate_effective_from:day,joined_at:day}});expect(container.textContent).toContain('Pekerja baru');expect(readProductionRecovery('disposable:actor-1').pending).toEqual({})})
 it('recovers a committed rate after remount with the exact old version, token, date, rate and UUID',async()=>{writerServer(true);await mount();await click('Mandor riwayat');await click('Pekerja historis');await click('Tambah tarif harian');await input('Tarif harian pekerja','200,654321');await input('Tarif berlaku mulai','2026-10-01');await input('Alasan perubahan pekerja','Tarif mulai tanggal yang disepakati');await click('Simpan tarif');expect(readProductionRecovery('disposable:actor-1').pending.ROSTER?.action).toBe('SET_RATE');expect(container.querySelector('[aria-label="Form pekerja dan tarif"]')).toBeNull();await act(async()=>root.unmount());root=createRoot(container);await mount();await click('Periksa status simpan pekerja');const calls=client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_roster_v1');expect(calls).toHaveLength(2);expect(calls[0][1]).toEqual(calls[1][1]);expect(calls[1][1]).toMatchObject({p_expected:'9007199254740993',p_payload:{source_token:'a'.repeat(32),document:{daily_rate:'200.654321',effective_from:'2026-10-01'}}});expect(readProductionRecovery('disposable:actor-1').pending).toEqual({})})
 it('keeps original start immutable and explicitly records a reactivation date after the stop',async()=>{writerServer();await mount();await click('Mandor riwayat');await click('Pekerja historis');await click('Ubah pekerja');expect((container.querySelector('[aria-label="Tanggal mulai pekerja"]') as HTMLInputElement).disabled).toBe(true);await input('Status pekerja','ACTIVE');expect(container.querySelector('[aria-label="Tanggal kembali pekerja"]')).not.toBeNull();await input('Alasan perubahan pekerja','Pekerja kembali dengan masa kerja baru');expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Simpan pekerja')!.disabled).toBe(true)})
 it('rejects a wrong worker, contractor, status, version or request in a purported committed outcome',()=>{const p={document:{contractor_id:id,date_from:day,date_to:day,source_token:'a'.repeat(32),document:{worker_id:wid,is_active:false}},expected_version:'9007199254740993'},r={contract_version:'cp7.roster-outcome.v1',kind:'COMMITTED_OUTCOME',action:'UPDATE_WORKER',request_id:rid,worker_id:wid,contractor_id:id,row_version:'9007199254740994',status:'INACTIVE',source_token:'b'.repeat(32)};expect(parseRosterOutcome(r,rid,'UPDATE_WORKER',p).row_version).toBe('9007199254740994');for(const bad of [{worker_id:pid},{contractor_id:pid},{status:'ACTIVE'},{row_version:'9007199254740993'},{request_id:pid}])expect(()=>parseRosterOutcome({...r,...bad},rid,'UPDATE_WORKER',p)).toThrow()})
})
