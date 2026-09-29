// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedFinanceReportPage from './ConnectedFinanceReportPage'
import {parseFinanceReport,type FinanceDates} from './financeReportContract'
import {financeReportFixture,filingId} from '../tests/fixtures/financeReport'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
const dates={from:'2026-09-01',to:'2026-09-28',as_of:'2026-09-28'}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset();const auth=structuredClone(recoveryIdentity);auth.identity.permissions.push('finance.reports.view');mock.auth=auth;container=document.createElement('div');document.body.append(container);root=createRoot(container);mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:financeReportFixture(p_query,p_query.filing_id),error:null}))})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedFinanceReportPage/>));await flush()}
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
async function fill(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
describe('P13 exact dated financial source and immutable filing',()=>{
 it('keeps huge exact amounts, signed loss, unavailable ratios and archived values',()=>{const r=parseFinanceReport(financeReportFixture(dates,filingId,true),dates,filingId,0,true);expect(r.snapshot.financial_position.assets).toBe('9007199254740993.01');expect(r.snapshot.financial_position.current_earnings).toBe('-7.02');expect(r.snapshot.performance.gross_margin_pct).toBeNull();expect(r.filing?.gl_balances['3100']).toBe('-9007199254740993.01')})
 it('refuses numeric JSON amounts, wrong dates and mislabeled current supplier exposure',()=>{
  const raw=financeReportFixture(dates);Object.assign(raw.snapshot.financial_position,{assets:9007199254740993});expect(()=>parseFinanceReport(raw,dates)).toThrow()
  expect(()=>parseFinanceReport(financeReportFixture(dates),{...dates,as_of:'2026-09-29'})).toThrow()
  const wrong=financeReportFixture(dates);wrong.snapshot.basis.supplier_exposure_basis='HISTORICAL';expect(()=>parseFinanceReport(wrong,dates)).toThrow()
 })
 it('refuses false READY, incomplete filing pages and an unrelated archived date',()=>{
  const r=financeReportFixture(dates);r.snapshot.data_confidence.critical_issue_count='1';expect(()=>parseFinanceReport(r,dates)).toThrow()
  const hidden=financeReportFixture(dates);Object.assign(hidden.snapshot.data_confidence,{blockers:[{family:'COST',code:'UNKNOWN_COST',severity:'POLICY',scope:'AS_OF',impact_date:dates.as_of,reference:null,reason:'Biaya belum diketahui'}]});expect(()=>parseFinanceReport(hidden,dates)).toThrow()
  const page=financeReportFixture(dates);page.filings.total='2';expect(()=>parseFinanceReport(page,dates)).toThrow()
  const f=financeReportFixture(dates,filingId);f.filing!.closed_through='2026-09-27';expect(()=>parseFinanceReport(f,dates,filingId)).toThrow()
  const permission=financeReportFixture(dates,null,true);expect(()=>parseFinanceReport(permission,dates)).toThrow()
 })
 it('renders exact financial values and labels current knowledge and supplier exposure',async()=>{await mount();expect(container.textContent).toContain('Rp9.007.199.254.740.993,01');expect(container.textContent).toContain('Rp-7,02');expect(container.textContent).toContain('Margin kotor: Belum dapat dihitung');expect(container.textContent).toContain('kondisi operasional sekarang');expect(container.textContent).toContain('bukan rekonstruksi informasi');expect(container.querySelector('[aria-label="Pemeriksaan tutup buku"]')).toBeNull()})
 it('reads a selected native filing without any close or journal mutation RPC',async()=>{await mount();await click(container.querySelector<HTMLElement>('[aria-label="Arsip penutupan keuangan"] .cproc-receipt')!);expect(container.querySelector('[aria-label="Saldo asli saat penutupan"]')?.textContent).toContain('Rp-9.007.199.254.740.993,01');expect(mock.rpc.mock.calls.every(([rpc])=>rpc==='erp_cp7_get_finance_report_v1')).toBe(true);expect(mock.rpc.mock.calls.at(-1)?.[1].p_query.filing_id).toBe(filingId)})
 it('retires sensitive financial facts on failed refresh while preserving selected dates',async()=>{await mount();await fill('Periode laporan dari',dates.from);await fill('Periode laporan sampai',dates.to);await fill('Posisi laporan pada',dates.as_of);await click(button('Tampilkan laporan'));mock.rpc.mockResolvedValue({data:null,error:{message:'Sumber laporan tidak tersedia'}});await click(button('Muat ulang laporan'));expect(container.querySelector('[aria-label="Posisi keuangan tercatat"]')).toBeNull();expect(container.textContent).not.toContain('9.007.199.254.740.993');expect(container.textContent).toContain('Sumber laporan tidak tersedia');expect(container.querySelector<HTMLInputElement>('[aria-label="Posisi laporan pada"]')?.value).toBe(dates.as_of)})
 it('retires an old actor response when identity changes during a read',async()=>{let resolveOld:((v:unknown)=>void)|null=null,oldDates:FinanceDates|null=null;mock.rpc.mockImplementationOnce((_rpc,{p_query})=>{oldDates=p_query;return new Promise(r=>{resolveOld=r})});await mount();const auth=structuredClone(mock.auth) as typeof recoveryIdentity;auth.identity.profile.id='actor-2';mock.auth=auth;mock.rpc.mockImplementation((_rpc,{p_query})=>{const r=financeReportFixture(p_query);r.snapshot.financial_position.assets='123.45';return Promise.resolve({data:r,error:null})});await mount();expect(container.querySelector('[aria-label="Posisi keuangan tercatat"]')?.textContent).toContain('Rp123,45');await act(async()=>resolveOld!({data:financeReportFixture(oldDates!),error:null}));await flush();expect(container.querySelector('[aria-label="Posisi keuangan tercatat"]')?.textContent).toContain('Rp123,45');expect(container.textContent).not.toContain('9.007.199.254.740.993')})
 it('requires current report access and preserves the native owner report role restriction',async()=>{const auth=mock.auth as typeof recoveryIdentity;auth.identity.permissions=[];await mount();expect(container.textContent).toContain('Hak melihat laporan');expect(mock.rpc).not.toHaveBeenCalled();auth.identity.permissions=['finance.reports.view'];auth.identity.profile.role='STAFF';await mount();expect(container.textContent).toContain('Owner atau Admin');expect(mock.rpc).not.toHaveBeenCalled()})
})
