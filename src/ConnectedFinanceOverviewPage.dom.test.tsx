// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedFinanceOverviewPage from './ConnectedFinanceOverviewPage'
import {financeReportFixture} from '../tests/fixtures/financeReport'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import type {FinanceDates} from './financeReportContract'

const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn(),navigate:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
let root:Root,container:HTMLDivElement
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true})
 mock.rpc.mockReset();mock.navigate.mockReset()
 const auth=structuredClone(recoveryIdentity);auth.identity.permissions.push('finance.dashboard.view','finance.reports.view');mock.auth=auth
 mock.rpc.mockImplementation((_name,{p_query})=>Promise.resolve({data:financeReportFixture(p_query),error:null}))
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedFinanceOverviewPage onNavigate={mock.navigate}/>));await flush()}
const button=(name:string)=>[...container.querySelectorAll('button')].find(e=>e.textContent===name)!
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
async function fill(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
describe('native finance overview',()=>{
 it('shows exact book values, recorded losses and unavailable ratios without simulated amounts',async()=>{
  mock.rpc.mockImplementation((_name,{p_query})=>{const d=financeReportFixture(p_query);d.snapshot.financial_position.cash='9007199254740993.01';Object.assign(d.snapshot.performance,{net_profit:'-7.02'});return Promise.resolve({data:d,error:null})})
  await mount()
  expect(container.textContent).toContain('Rp9.007.199.254.740.993,01');expect(container.textContent).toContain('Rp-7,02')
  expect(container.textContent).toContain('Margin kotor: Belum dapat dihitung');expect(container.textContent).toContain('Kondisi operasional sekarang')
  expect(container.textContent).not.toContain('141 jt');expect(container.textContent).not.toContain('111 hari')
  expect(mock.rpc.mock.calls.every(([name])=>name==='erp_cp7_get_finance_report_v1')).toBe(true)
  expect(mock.rpc.mock.calls[0][1].p_query).toMatchObject({filing_id:null,offset:0,limit:25})
 })
 it('shows a policy blocker and preserves provisional amounts without declaring READY',async()=>{
  mock.rpc.mockImplementation((_name,{p_query})=>{const d=financeReportFixture(p_query);const c=d.snapshot.data_confidence as unknown as Record<string,unknown>;Object.assign(c,{status:'BLOCKED',critical_issue_count:'1',blockers:[{family:'COST',code:'UNKNOWN_COST',severity:'POLICY',scope:'AS_OF',impact_date:p_query.as_of,reference:null,reason:'Biaya laundry belum diketahui'}],failed_checks:[{check_name:'UNKNOWN_COST',severity:'CRITICAL',issue_count:'1',details:'Biaya laundry belum diketahui'}]});return Promise.resolve({data:d,error:null})})
  await mount();expect(container.textContent).toContain('Ada penghalang');expect(container.textContent).toContain('Biaya laundry belum diketahui');expect(container.textContent).toContain('Biaya dan laba belum final')
  expect(container.textContent).not.toContain('Angka lolos pemeriksaan');expect(container.querySelector('[aria-label="Saldo ringkasan tercatat"]')).not.toBeNull()
 })
 it('retires every amount immediately on all date edits and reads only the submitted dates',async()=>{
  await mount()
  for(const [label,value]of [['Periode ringkasan dari','2026-08-31'],['Periode ringkasan sampai','2026-09-01'],['Posisi ringkasan pada','2026-09-01']]){
   const count=mock.rpc.mock.calls.length;await fill(label,value)
   expect(container.textContent).not.toContain('Rp');expect(mock.rpc.mock.calls).toHaveLength(count)
   await click(button('Tampilkan ringkasan'));expect(container.querySelector('[aria-label="Saldo ringkasan tercatat"]')).not.toBeNull()
  }
  expect(mock.rpc.mock.calls.at(-1)?.[1].p_query).toMatchObject({from:'2026-08-31',to:'2026-09-01',as_of:'2026-09-01'})
 })
 it('an old successful response cannot repaint after an invalid-date submission',async()=>{
  let resolveOld:((v:unknown)=>void)|null=null,oldDates:FinanceDates|null=null
  mock.rpc.mockImplementationOnce((_name,{p_query})=>{oldDates=p_query;return new Promise(resolve=>{resolveOld=resolve})})
  await mount();await fill('Posisi ringkasan pada','2026-08-31');await click(button('Tampilkan ringkasan'))
  await act(async()=>resolveOld!({data:financeReportFixture(oldDates!),error:null}));await flush()
  expect(container.textContent).toContain('Pilih tanggal mulai');expect(container.textContent).not.toContain('Rp');expect(mock.rpc).toHaveBeenCalledTimes(1)
 })
 it('clears sensitive money after failed refresh and refuses a mismatched source basis',async()=>{
  await mount();mock.rpc.mockResolvedValueOnce({data:null,error:{message:'Hak laporan dicabut'}});await click(button('Tampilkan ringkasan'))
  expect(container.textContent).toContain('Hak laporan dicabut');expect(container.textContent).not.toContain('Rp')
  mock.rpc.mockImplementationOnce((_name,{p_query})=>Promise.resolve({data:financeReportFixture({...p_query,as_of:'2026-01-01'}),error:null}));await click(button('Tampilkan ringkasan'))
  expect(container.textContent).toContain('basis tanggal berubah');expect(container.textContent).not.toContain('Rp')
 })
 it('retires the previous actor response and gates dashboard, report and owner/admin access',async()=>{
  let resolveOld:((v:unknown)=>void)|null=null,oldDates:FinanceDates|null=null
  mock.rpc.mockImplementationOnce((_name,{p_query})=>{oldDates=p_query;return new Promise(resolve=>{resolveOld=resolve})})
  await mount();const auth=structuredClone(mock.auth) as typeof recoveryIdentity;auth.identity.profile.id='other-actor';mock.auth=auth
  mock.rpc.mockImplementation((_name,{p_query})=>{const d=financeReportFixture(p_query);d.snapshot.financial_position.assets='123.45';return Promise.resolve({data:d,error:null})})
  await mount();await act(async()=>resolveOld!({data:financeReportFixture(oldDates!),error:null}));await flush()
  expect(container.textContent).toContain('Rp123,45');expect(container.textContent).not.toContain('9.007.199.254.740.993')
  const count=mock.rpc.mock.calls.length
  for(const permissions of [['finance.dashboard.view'],['finance.reports.view']]){auth.identity.permissions=permissions;await mount();expect(container.textContent).toContain('Hak melihat ringkasan');expect(container.textContent).not.toContain('Rp')}
  auth.identity.permissions=['finance.dashboard.view','finance.reports.view'];auth.identity.profile.role='STAFF';await mount();expect(container.textContent).toContain('Owner atau Admin');expect(mock.rpc.mock.calls).toHaveLength(count)
 })
 it('opens the matching source workspaces without mutating financial facts',async()=>{
  await mount();const count=mock.rpc.mock.calls.length
  await click(button('Periksa kas dan bank'));expect(mock.navigate).toHaveBeenLastCalledWith('finance-cash')
  await click(button('Periksa piutang pelanggan menurut buku'));expect(mock.navigate).toHaveBeenLastCalledWith('finance-reports')
  await click(button('Buka laporan'));expect(mock.navigate).toHaveBeenLastCalledWith('finance-reports')
  expect(mock.rpc.mock.calls).toHaveLength(count)
 })
})
