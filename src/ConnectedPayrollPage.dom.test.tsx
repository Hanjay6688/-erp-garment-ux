// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedPayrollPage from './ConnectedPayrollPage'
import {readProductionRecovery} from './productionRecovery'
import {parsePayrollRead,parsePayrollOutcome,type PayrollHeader} from './payrollContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222',at='2026-09-29T03:00:00.000000Z'
const h:PayrollHeader={id,payroll_number:'PAY-001',contractor_id:other,contractor_name:'Mandor exact',attendance_required:false,period_start:'2026-09-29',period_end:'2026-09-29',status:'CALCULATED',row_version:'9007199254740993',review_token:'a'.repeat(32),notes:null,labor_total:'6000.00',attendance_total:'0.00',reimburse_total:'0.00',deduction_total:'0.00',manual_adjustment:'0.00',net_payable:'6000.00',payment_cash_account_id:null,payment_cash_account_name:null,payment_date:'2026-09-29',settled_at:null,created_at:at,updated_at:at,totals_match_items:true,counts:{work:'2',attendance:'0',reimbursements:'0',deductions:'0',notes:'0'}}
const line={id,po_id:null,po_number:null,component_id:'a4000000-0000-0000-0000-000000000001',component_code:'SEW',component_name:'Jahit utama',source_type:'FG_REPAIR',source_id:other,qty:'1',rate:'2000.00',amount:'2000.00'}
const work=[line,{...line,id:other,qty:'2',amount:'4000.00'}]
function payload(section:string,doc=h,rows:unknown[]=section==='PAYROLLS'?[doc]:work){return {contract_version:'cp7.payroll-workspace.v1',section,read_at:at,capabilities:{approve:false,pay:false},document:section==='PAYROLLS'?null:doc,page:{rows,total:String(rows.length),offset:0,limit:25,next_offset:null}}}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});const a=structuredClone(recoveryIdentity);a.identity.permissions=['finance.payroll.view'];state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<ConnectedPayrollPage/>));await flush()}
async function click(match:string){const button=[...container.querySelectorAll('button')].find(x=>x.textContent?.startsWith(match));if(!button)throw Error(match);await act(async()=>button.click());await flush()}
function server(){client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>({error:null,data:payload(args.p_section)}))}
describe('financial payroll review boundary',()=>{
 it('preserves exact high money and row versions and rejects inconsistent totals and line amounts',()=>{
  const large={...h,labor_total:'9007199254740993.01',manual_adjustment:'-0.01',net_payable:'9007199254740993.00'}
  const parsed=parsePayrollRead(payload('PAYROLLS',large),'PAYROLLS').page.rows[0] as PayrollHeader
  expect(parsed.row_version).toBe('9007199254740993');expect(parsed.net_payable).toBe('9007199254740993.00')
  expect(()=>parsePayrollRead(payload('PAYROLLS',{...large,net_payable:'9007199254740993.01'}),'PAYROLLS')).toThrow()
  expect(()=>parsePayrollRead(payload('WORK',h,[{...line,amount:'3000'},work[1]]),'WORK')).toThrow()
 })
 it('keeps a full document total distinct from one detail page and rejects a false page count',()=>{
  const data=payload('WORK',h,[line]);data.page={rows:[line],total:'2',offset:0,limit:1,next_offset:1 as unknown as null}
  expect(parsePayrollRead(data,'WORK').document?.net_payable).toBe('6000.00')
  expect(()=>parsePayrollRead({...data,page:{...data.page,total:'1',next_offset:null}},'WORK')).toThrow()
 })
 it('preserves legacy nullable attendance history without inventing a worker name or date',()=>{const old={...h,labor_total:'0.00',attendance_total:'100.00',net_payable:'100.00',attendance_required:true,counts:{...h.counts,work:'0',attendance:'1'}};const row={id,worker_id:other,attendance_record_id:id,date:null,worker_name:null,job_description:null,paid_fraction:'1.0000',daily_rate:'100.00',rate_version_id:null,amount:'100.00'};expect(parsePayrollRead(payload('ATTENDANCE',old,[row]),'ATTENDANCE').page.rows[0]).toEqual(row)})
 it('gates money before any network call when only operational access is present',async()=>{const a=structuredClone(recoveryIdentity);a.identity.permissions=['production.fg_handoff.view'];state.auth=a;await mount();expect(container.textContent).toContain('Hak melihat payroll diperlukan');expect(client.rpc).not.toHaveBeenCalled()})
 it('reads native component detail with finance-view only and has no settlement write action',async()=>{server();await mount();await click('Mandor exact');expect(container.querySelector('.cpay-totals')?.textContent).toContain('Rp6.000');expect(container.querySelectorAll('.cpay-line')).toHaveLength(2);expect(container.textContent).toContain('Jahit utama');expect(client.rpc.mock.calls.every(([n])=>n==='erp_cp7_get_payroll_workspace_v1')).toBe(true);expect(container.querySelectorAll('input[type="number"]')).toHaveLength(0)})
 it('retires both list and monetary details when a child revision changes between the two reads',async()=>{server();await mount();await click('Mandor exact');client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>({error:null,data:payload(args.p_section,args.p_section==='WORK'?{...h,review_token:'b'.repeat(32)}:h)}));await click('Muat ulang payroll');expect(container.textContent).toContain('Payroll berubah saat dibaca');expect(container.querySelector('.cpay-totals')).toBeNull();expect(container.textContent).not.toContain('Rp6.000');expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0)})
 it('clears money on failed detail refresh and refuses a detail response for another payroll',async()=>{server();await mount();await click('Mandor exact');client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>args.p_section==='WORK'?{error:{status:403,message:'Access revoked'},data:null}:{error:null,data:payload('PAYROLLS')});await click('Muat ulang payroll');expect(container.textContent).not.toContain('Rp');expect(container.querySelector('.cpay-totals')).toBeNull();client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>({error:null,data:payload(args.p_section,args.p_section==='WORK'?{...h,id:other}:h)}));await click('Muat ulang payroll');expect(container.textContent).toContain('Pilihan payroll atau hak akses berubah');expect(container.textContent).not.toContain('Rp')})
 it('keeps cancelled monetary history explicit and surfaces stale stored totals without recalculating',async()=>{const d={...h,status:'REVERSED',totals_match_items:false};client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>({error:null,data:payload(args.p_section,d)}));await mount();await click('Mandor exact');expect(container.textContent).toContain('Jumlah pada dokumen batal');expect(container.textContent).toContain('Total belum sesuai rincian');expect(container.textContent).toContain('Rp6.000');expect(client.rpc.mock.calls.every(([n])=>n==='erp_cp7_get_payroll_workspace_v1')).toBe(true)})
})

async function input(label:string,value:string){const el=container.querySelector(`[aria-label="${label}"]`) as HTMLInputElement|HTMLTextAreaElement;await act(async()=>{const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function reviewed(){await input('Alasan tindakan payroll','Rincian dan dokumen sumber telah diperiksa');await act(async()=>(container.querySelector('[aria-label="Rincian payroll sudah diperiksa"]') as HTMLInputElement).click());await flush()}
function writerServer(initialStatus='CALCULATED',lostPay=false){
 const a=structuredClone(recoveryIdentity);a.identity.permissions=['finance.payroll.view','finance.payroll.approve','finance.payroll.pay'];state.auth=a
 let current={...structuredClone(h),status:initialStatus},lost=false
 const cached=new Map<string,unknown>()
 client.rpc.mockImplementation(async(name:string,p:{p_section:string;p_action:string;p_request:string;p_expected:string;p_payload:{cash_account_id?:string;payment_date?:string}})=>{
  if(name==='erp_cp7_save_payroll_v1'){
   if(cached.has(p.p_request))return {error:null,data:cached.get(p.p_request)}
   current={...current,status:({PREPARE:'CALCULATED',APPROVE:'APPROVED',PAY:'PAID',CANCEL:'REVERSED',REVERSE:'REVERSED'} as Record<string,string>)[p.p_action],row_version:(BigInt(current.row_version)+1n).toString(),review_token:'b'.repeat(32)}
   if(p.p_action==='PAY')current={...current,payment_date:p.p_payload.payment_date!,payment_cash_account_id:p.p_payload.cash_account_id!,payment_cash_account_name:'Kas pengujian',settled_at:at}
   const result={contract_version:'cp7.payroll-outcome.v1',kind:'COMMITTED_OUTCOME',action:p.p_action,request_id:p.p_request,payroll_id:id,status:current.status,row_version:current.row_version,review_token:current.review_token};cached.set(p.p_request,result)
   if(lostPay&&p.p_action==='PAY'&&!lost){lost=true;return {error:{status:503,message:'Reply lost after commit'},data:null}}
   return {error:null,data:result}
  }
  const r=p.p_section==='CASH_ACCOUNTS'?payload('CASH_ACCOUNTS',current,[{id:other,code:'KAS-TEST',name:'Kas pengujian',kind:'CASH'}]):payload(p.p_section,current)
  if(p.p_section==='CASH_ACCOUNTS')r.document=null
  r.capabilities={approve:true,pay:true};return {error:null,data:r}
 })
}
describe('payroll controlled financial actions',()=>{
 it('requires explicit approval review and sends the exact large header version and child token',async()=>{writerServer();await mount();await click('Mandor exact');await click('Setujui payroll');const commit=[...container.querySelectorAll('button')].find(b=>b.textContent==='Setujui payroll sekarang')!;expect(commit.disabled).toBe(true);await reviewed();expect(commit.disabled).toBe(false);await click('Setujui payroll sekarang');const call=client.rpc.mock.calls.find(([name])=>name==='erp_cp7_save_payroll_v1')![1];expect(call.p_action).toBe('APPROVE');expect(call.p_expected).toBe('9007199254740993');expect(call.p_payload).toEqual({id,review_token:h.review_token,change_reason:'Rincian dan dokumen sumber telah diperiksa'});expect(container.textContent).toContain('Disetujui');expect(readProductionRecovery('disposable:actor-1').pending).toEqual({})})
 it('recovers a committed payment after remount with the identical UUID, date, cash account and exact version',async()=>{writerServer('APPROVED',true);await mount();await click('Mandor exact');await click('Lunasi payroll');await click('Cari akun pembayaran');await click('KAS-TEST');await input('Tanggal pembayaran payroll','2026-01-01');await reviewed();await click('Lunasi payroll sekarang');const before=readProductionRecovery('disposable:actor-1').pending.PAYROLL;expect(before?.action).toBe('PAY');expect(container.textContent).toContain('Status transaksi payroll belum pasti');await act(async()=>root.unmount());root=createRoot(container);await mount();await click('Periksa status payroll');const calls=client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_payroll_v1');expect(calls).toHaveLength(2);expect(calls[0][1]).toEqual(calls[1][1]);expect(calls[1][1].p_expected).toBe('9007199254740993');expect(calls[1][1].p_payload.payment_date).toBe('2026-01-01');expect(calls[1][1].p_payload.cash_account_id).toBe(other);expect(container.textContent).toContain('Jumlah dilunasi');expect(readProductionRecovery('disposable:actor-1').pending).toEqual({})})
 it('refuses an unrelated document or action even when a server response claims success',()=>{const p={document:{id},expected_version:'9007199254740993'},r={contract_version:'cp7.payroll-outcome.v1',kind:'COMMITTED_OUTCOME',action:'PAY',request_id:id,payroll_id:other,status:'PAID',row_version:'9007199254740994',review_token:'b'.repeat(32)};expect(()=>parsePayrollOutcome(r,id,'PAY',p)).toThrow();expect(()=>parsePayrollOutcome({...r,payroll_id:id},other,'PAY',p)).toThrow();expect(()=>parsePayrollOutcome({...r,payroll_id:id},id,'APPROVE',p)).toThrow();expect(()=>parsePayrollOutcome({...r,payroll_id:id,status:'APPROVED'},id,'PAY',p)).toThrow()})
})
