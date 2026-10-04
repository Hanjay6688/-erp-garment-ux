// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedCashLedgerPage from './ConnectedCashLedgerPage'
import {financeAnalysisFixture} from '../tests/fixtures/financeAnalysis'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import type {AnalysisDates} from './financeAnalysisContract'

const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
let root:Root,container:HTMLDivElement
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset()
 const auth=structuredClone(recoveryIdentity);auth.identity.permissions.push('finance.cash.view','finance.reports.view');mock.auth=auth
 mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:financeAnalysisFixture(p_query,p_query.offset),error:null}))
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedCashLedgerPage/>));await flush()}
async function click(label:string){await act(async()=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!.click());await flush()}
async function fill(label:string,value:string){await act(async()=>{
 const input=container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
 Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}))
});await flush()}
function pages(query:AnalysisDates,offset:number){
 const r=financeAnalysisFixture(query),original=r.cash.entries.rows[0]
 const rows=[...r.cash.entries.rows,...Array.from({length:30},(_,i)=>({...original,id:'44444444-4444-4444-8444-'+String(i).padStart(12,'0'),journal_number:'PAGE-'+i,debit:'1.25',credit:'0.00',net:'1.25'}))]
 Object.assign(r.cash,{closing:'1137.50',debit:'1337.50',net_change:'137.50',ledger_net:'137.50'})
 Object.assign(r.cash.entries,{rows:rows.slice(offset,offset+25),offset,total:'33',next_offset:offset+25<33?offset+25:null})
 return r
}

describe('connected cash uses complete native source and retires stale money',()=>{
 it('searches and orders only the displayed page while complete period cash totals stay unchanged',async()=>{
  await mount();const calls=mock.rpc.mock.calls.length,ids=[...container.querySelectorAll('[data-journal-id]')].map(e=>e.getAttribute('data-journal-id'))
  await act(async()=>{const order=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan halaman jurnal kas"]')!;order.value='LABEL_DESC';order.dispatchEvent(new Event('change',{bubbles:true}))});expect(mock.rpc).toHaveBeenCalledTimes(calls)
  expect(new Set([...container.querySelectorAll('[data-journal-id]')].map(e=>e.getAttribute('data-journal-id')))).toEqual(new Set(ids))
  const number=container.querySelector('[data-journal-id] strong')!.textContent!;await fill('Cari jurnal kas di halaman',number);await click('Tampilkan kas');expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(1);expect(mock.rpc).toHaveBeenCalledTimes(calls+1);expect(container.textContent).toContain('Perubahan kas bersihRp100');expect(container.textContent).toContain('Pencarian hanya menelusuri halaman yang sedang tampil')
  await click('Browse halaman ini');expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(3);expect(mock.rpc.mock.calls.at(-1)![1].p_query.offset).toBe(0);expect(container.textContent).toContain('Perubahan kas bersihRp100')
 })
 it('keeps page filtering on page25 without silently moving to page0 or changing Native aggregates',async()=>{
  mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:pages(p_query,p_query.offset),error:null}));await mount();await click('Jurnal berikutnya');const calls=mock.rpc.mock.calls.length
  await fill('Cari jurnal kas di halaman','PAGE-29');await click('Tampilkan kas');expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(1);expect(mock.rpc).toHaveBeenCalledTimes(calls+1);expect(mock.rpc.mock.calls.at(-1)![1].p_query.offset).toBe(25);expect(container.textContent).toContain('Total 33 jurnal');expect(container.textContent).toContain('Perubahan kas bersihRp137,5');await click('Browse halaman ini');expect(mock.rpc.mock.calls.at(-1)![1].p_query.offset).toBe(25);expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(8)
 })
 it('loads the native dated source and keeps cash distinct from sale revenue',async()=>{
  await mount();expect(mock.rpc.mock.calls[0][0]).toBe('erp_cp7_get_finance_analysis_v1')
  expect(container.textContent).toContain('Perubahan kas bersihRp100');expect(container.textContent).toContain('Debit rekening kas/bankRp1.300')
  expect(container.textContent).toContain('Penerimaan kas tidak otomatis menjadi penjualan');expect(container.textContent).toContain('bersih Rp0')
  expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(3);expect(container.textContent).not.toContain('SIMULASI')
 })
 it('loads both source pages while keeping the complete33-source aggregates',async()=>{
  mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:pages(p_query,p_query.offset),error:null}))
  await mount();const first=[...container.querySelectorAll('[data-journal-id]')].map(e=>e.getAttribute('data-journal-id'))
  expect(first).toHaveLength(25);expect(container.textContent).toContain('Perubahan kas bersihRp137,5');await click('Jurnal berikutnya')
  const second=[...container.querySelectorAll('[data-journal-id]')].map(e=>e.getAttribute('data-journal-id'))
  expect(second).toHaveLength(8);expect(new Set([...first,...second]).size).toBe(33)
  expect(container.textContent).toContain('Perubahan kas bersihRp137,5');expect(container.textContent).toContain('Total 33 jurnal')
  expect(mock.rpc.mock.calls.at(-1)![1].p_query.offset).toBe(25)
 })
 it('preserves exact cents beyond the JavaScript safe integer',async()=>{
  mock.rpc.mockImplementation((_rpc,{p_query})=>{
   const r=financeAnalysisFixture(p_query);Object.assign(r.cash,{opening:'9007199254740993.01',closing:'9007199254741093.01'})
   return Promise.resolve({data:r,error:null})
  })
  await mount();expect(container.textContent).toContain('Rp9.007.199.254.740.993,01');expect(container.textContent).toContain('Rp9.007.199.254.741.093,01')
 })
 it('removes all old money and source rows when the next page fails',async()=>{
  mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:pages(p_query,p_query.offset),error:null}))
  await mount();mock.rpc.mockResolvedValue({data:null,error:{message:'Sumber jurnal kas terputus'}});await click('Jurnal berikutnya')
  expect(container.textContent).not.toContain('Rp');expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(0)
  expect(container.textContent).toContain('Sumber jurnal kas terputus');expect(container.querySelector('[aria-label="Periode kas dari"]')).not.toBeNull()
 })
 it('ignores a completed earlier read after the user changes the period',async()=>{
  let resolveOld!: (value:unknown)=>void,oldQuery!:AnalysisDates
  mock.rpc.mockImplementationOnce((_rpc,{p_query})=>{oldQuery=p_query;return new Promise(resolve=>{resolveOld=resolve})})
  await mount();await fill('Periode kas dari',new Date(Date.parse(oldQuery.from+'T00:00:00Z')-86400000).toISOString().slice(0,10))
  await act(async()=>resolveOld({data:financeAnalysisFixture(oldQuery),error:null}));await flush()
  expect(container.textContent).not.toContain('Rp');expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(0)
 })
 it('retires an old actor response after the actor is replaced',async()=>{
  let resolveOld!: (value:unknown)=>void,oldQuery!:AnalysisDates
  mock.rpc.mockImplementationOnce((_rpc,{p_query})=>{oldQuery=p_query;return new Promise(resolve=>{resolveOld=resolve})})
  await mount();const auth=structuredClone(mock.auth) as typeof recoveryIdentity;auth.identity.profile.id='actor-2';mock.auth=auth
  mock.rpc.mockImplementation((_rpc,{p_query})=>{const r=financeAnalysisFixture(p_query);r.cash.entries.rows[0].journal_number='NEW-ACTOR';return Promise.resolve({data:r,error:null})})
  await mount();expect(container.textContent).toContain('NEW-ACTOR')
  await act(async()=>resolveOld({data:financeAnalysisFixture(oldQuery),error:null}));await flush();expect(container.textContent).toContain('NEW-ACTOR')
 })
 it('requires cash navigation plus current financial report access and native owner role',async()=>{
  const auth=mock.auth as typeof recoveryIdentity;auth.identity.permissions=['finance.cash.view'];await mount()
  expect(mock.rpc).not.toHaveBeenCalled();auth.identity.permissions=['finance.reports.view'];await mount();expect(mock.rpc).not.toHaveBeenCalled()
  auth.identity.permissions=['finance.cash.view','finance.reports.view'];auth.identity.profile.role='STAFF';await mount()
  expect(mock.rpc).not.toHaveBeenCalled();expect(container.textContent).toContain('Owner atau Admin')
 })
})
