// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedPayrollPage from './ConnectedPayrollPage'
import {parsePayrollRead,type PayrollHeader} from './payrollContract'
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
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions=['finance.payroll.view'];state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
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
 it('gates money before any network call when only operational access is present',async()=>{const a=structuredClone(recoveryIdentity);a.identity.permissions=['production.fg_handoff.view'];state.auth=a;await mount();expect(container.textContent).toContain('Hak melihat payroll diperlukan');expect(client.rpc).not.toHaveBeenCalled()})
 it('reads native component detail with finance-view only and has no settlement write action',async()=>{server();await mount();await click('Mandor exact');expect(container.querySelector('.cpay-totals')?.textContent).toContain('Rp6.000');expect(container.querySelectorAll('.cpay-line')).toHaveLength(2);expect(container.textContent).toContain('Jahit utama');expect(client.rpc.mock.calls.every(([n])=>n==='erp_cp7_get_payroll_workspace_v1')).toBe(true);expect(container.querySelectorAll('input[type="number"]')).toHaveLength(0)})
 it('retires both list and monetary details when a child revision changes between the two reads',async()=>{server();await mount();await click('Mandor exact');client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>({error:null,data:payload(args.p_section,args.p_section==='WORK'?{...h,review_token:'b'.repeat(32)}:h)}));await click('Muat ulang payroll');expect(container.textContent).toContain('Payroll berubah saat dibaca');expect(container.querySelector('.cpay-totals')).toBeNull();expect(container.textContent).not.toContain('Rp6.000');expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0)})
 it('clears money on failed detail refresh and refuses a detail response for another payroll',async()=>{server();await mount();await click('Mandor exact');client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>args.p_section==='WORK'?{error:{status:403,message:'Access revoked'},data:null}:{error:null,data:payload('PAYROLLS')});await click('Muat ulang payroll');expect(container.textContent).not.toContain('Rp');expect(container.querySelector('.cpay-totals')).toBeNull();client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>({error:null,data:payload(args.p_section,args.p_section==='WORK'?{...h,id:other}:h)}));await click('Muat ulang payroll');expect(container.textContent).toContain('Pilihan payroll atau hak akses berubah');expect(container.textContent).not.toContain('Rp')})
 it('keeps cancelled monetary history explicit and surfaces stale stored totals without recalculating',async()=>{const d={...h,status:'REVERSED',totals_match_items:false};client.rpc.mockImplementation(async(_name:string,args:{p_section:string})=>({error:null,data:payload(args.p_section,d)}));await mount();await click('Mandor exact');expect(container.textContent).toContain('Jumlah pada dokumen batal');expect(container.textContent).toContain('Total belum sesuai rincian');expect(container.textContent).toContain('Rp6.000');expect(client.rpc.mock.calls.every(([n])=>n==='erp_cp7_get_payroll_workspace_v1')).toBe(true)})
})
