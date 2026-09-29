// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedAttendancePage from './ConnectedAttendancePage'
import {parseAttendanceRead,type AttendancePeriod,type AttendanceWorker} from './attendanceContract'
import {cp6WibDateTimeInput} from './cp6BusinessTime'
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
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions=['finance.attendance.view'];state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
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
