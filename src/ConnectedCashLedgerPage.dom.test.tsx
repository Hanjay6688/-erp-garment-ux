// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedCashLedgerPage from './ConnectedCashLedgerPage'
import {financeAnalysisFixture,withEntryList} from '../tests/fixtures/financeAnalysis'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {parseFinanceAnalysis,type AnalysisDates,type CashEntryList} from './financeAnalysisContract'

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
function pages(query:AnalysisDates&Partial<CashEntryList>,offset:number){
 const r=financeAnalysisFixture(query),original=r.cash.entries.rows[0]
 const rows=[...r.cash.entries.rows,...Array.from({length:30},(_,i)=>({...original,id:'44444444-4444-4444-8444-'+String(i).padStart(12,'0'),journal_number:'PAGE-'+i,debit:'1.25',credit:'0.00',net:'1.25'}))]
 Object.assign(r.cash,{closing:'1137.50',debit:'1337.50',net_change:'137.50',ledger_net:'137.50'})
 Object.assign(r.cash.entries,{rows:rows.slice(offset,offset+25),offset,total:'33',next_offset:offset+25<33?offset+25:null})
 return withEntryList(r,query)
}
// OW-09 reader stand-in: 33 journals, filter + natural order over all of them, then the page; count and sums of the matching set.
type Query=AnalysisDates&CashEntryList&{offset:number;limit:number}
const cent=(v:string)=>Math.round(Number(v)*100),rupiah=(c:number)=>`${c<0?'-':''}${Math.floor(Math.abs(c)/100)}.${String(Math.abs(c)%100).padStart(2,'0')}`
function reader(query:Query){
 const r=financeAnalysisFixture(query),original=r.cash.entries.rows[0]
 const all=[...r.cash.entries.rows,...Array.from({length:30},(_,i)=>({...original,id:'55555555-5555-4555-8555-'+String(i).padStart(12,'0'),journal_number:'KAS-'+(i+1),status:i%3===0?'REVERSED':'POSTED',source_type:i%4===0?'MISC_FINANCE':'SALES_PAYMENT',debit:i%2?'2.50':'0.00',credit:i%2?'0.00':'1.10',net:i%2?'2.50':'-1.10'}))]
 const debit=all.reduce((s,x)=>s+cent(x.debit),0),credit=all.reduce((s,x)=>s+cent(x.credit),0)
 Object.assign(r.cash,{debit:rupiah(debit),credit:rupiah(credit),closing:rupiah(cent(r.cash.opening)+debit-credit),net_change:rupiah(debit-credit),ledger_net:rupiah(debit-credit)})
 const match=all.filter(x=>(!query.entry_status||x.status===query.entry_status)&&(!query.entry_q||[x.journal_number,x.source_type].join(' ').toLowerCase().includes(query.entry_q.toLowerCase())))
 if(query.entry_order!=='SOURCE')match.sort((a,b)=>(query.entry_order==='LABEL_DESC'?-1:1)*a.journal_number.localeCompare(b.journal_number,'id',{numeric:true}))
 const md=match.reduce((s,x)=>s+cent(x.debit),0),mc=match.reduce((s,x)=>s+cent(x.credit),0),end=query.offset+25
 Object.assign(r.cash.entries,{rows:match.slice(query.offset,end),offset:query.offset,total:String(match.length),next_offset:end<match.length?end:null,list:{q:query.entry_q,status:query.entry_status,order:query.entry_order},sums:{debit:rupiah(md),credit:rupiah(mc),net:rupiah(md-mc)}})
 return r as typeof r&{cash:{entries:{list:{q:string;status:string|null;order:string};sums:{debit:string;credit:string;net:string}}}}
}
const shown=()=>[...container.querySelectorAll('[data-journal-id] strong')].map(e=>e.textContent)
async function choose(label:string,value:string){await act(async()=>{const s=container.querySelector<HTMLSelectElement>(`[aria-label="${label}"]`)!;s.value=value;s.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}

describe('connected cash uses complete native source and retires stale money',()=>{
 it('searches, filters and orders the whole period through the reader while complete period cash totals stay unchanged',async()=>{
  mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:reader(p_query),error:null}));await mount()
  expect(mock.rpc.mock.calls[0][1].p_query).toMatchObject({offset:0,limit:25,entry_q:'',entry_status:null,entry_order:'SOURCE'})
  expect(container.textContent).toContain('Filter dan urutan berlaku untuk seluruh hasil, termasuk halaman lain');expect(container.textContent).not.toContain('hanya mengatur halaman');expect(container.textContent).not.toContain('Pencarian hanya menelusuri halaman')
  const period=container.querySelector('[aria-label="Saldo dan perubahan kas"]')!.textContent;expect(container.textContent).toContain('Total 33 jurnal cocok')
  await click('Jurnal berikutnya');expect(mock.rpc.mock.calls.at(-1)![1].p_query.offset).toBe(25)
  // A new order is applied by the reader to all 33 journals and restarts at the first page; the screen does not re-sort.
  await choose('Urutkan jurnal kas','LABEL_DESC');let q=mock.rpc.mock.calls.at(-1)![1].p_query;expect(q).toMatchObject({offset:0,entry_order:'LABEL_DESC',entry_status:null,entry_q:''})
  expect(shown()).toEqual(reader({...q}).cash.entries.rows.map(x=>x.journal_number));expect(shown()[0]).toBe('KAS-30');expect(shown()).toHaveLength(25)
  await click('Jurnal berikutnya');expect(shown()).toEqual(reader({...q,offset:25}).cash.entries.rows.map(x=>x.journal_number));expect(shown()).toHaveLength(8)
  // Status filter: count, sums and pages all follow the same matching set; period balances stay the whole period.
  await choose('Status jurnal kas','REVERSED');q=mock.rpc.mock.calls.at(-1)![1].p_query;expect(q).toMatchObject({offset:0,entry_status:'REVERSED',entry_order:'LABEL_DESC'})
  const reversed=reader({...q});expect(reversed.cash.entries.total).toBe('10');expect(container.textContent).toContain('Total 10 jurnal cocok')
  expect(container.querySelector('[data-cash-matching-sums]')!.textContent).toBe('Jumlah jurnal yang cocok: debit Rp12,5 · kredit Rp5,5 · bersih Rp7.')
  expect(container.querySelector('[aria-label="Saldo dan perubahan kas"]')!.textContent).toBe(period)
  await fill('Cari jurnal kas','misc');await click('Tampilkan kas');q=mock.rpc.mock.calls.at(-1)![1].p_query;expect(q).toMatchObject({offset:0,entry_q:'misc',entry_status:'REVERSED'});expect(shown()).toEqual(reader({...q}).cash.entries.rows.map(x=>x.journal_number))
  await click('Browse semua jurnal');expect(mock.rpc.mock.calls.at(-1)![1].p_query).toMatchObject({offset:0,entry_q:'',entry_status:null,entry_order:'SOURCE'});expect(container.textContent).toContain('Total 33 jurnal cocok')
  expect(container.querySelector('[aria-label="Saldo dan perubahan kas"]')!.textContent).toBe(period)
 })
 it('keeps page25 when the same period and list are shown again, starts at page0 for a new search, and keeps Native aggregates',async()=>{
  mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:pages(p_query,p_query.offset),error:null}));await mount();await click('Jurnal berikutnya');const calls=mock.rpc.mock.calls.length
  await click('Tampilkan kas');expect(mock.rpc).toHaveBeenCalledTimes(calls+1);expect(mock.rpc.mock.calls.at(-1)![1].p_query.offset).toBe(25);expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(8);expect(container.textContent).toContain('Total 33 jurnal');expect(container.textContent).toContain('Perubahan kas bersihRp137,5')
  mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:reader(p_query),error:null}))
  await fill('Cari jurnal kas','KAS-29');await click('Tampilkan kas');expect(mock.rpc.mock.calls.at(-1)![1].p_query).toMatchObject({offset:0,entry_q:'KAS-29'});expect(shown()).toEqual(['KAS-29']);expect(container.textContent).toContain('Total 1 jurnal cocok')
 })
 it('refuses a list answer that does not belong to the list the screen asked for',async()=>{
  const dates={from:'2026-09-01',to:'2026-09-29',as_of:'2026-09-29',compare_from:'2026-08-31',compare_to:'2026-08-31'},list:CashEntryList={entry_q:'',entry_status:'REVERSED',entry_order:'LABEL_ASC'}
  const good=reader({...dates,...list,offset:0,limit:25});expect(parseFinanceAnalysis(good,dates,0,list).cash.entries.total).toBe('10')
  type R=ReturnType<typeof reader>
  const variants:((r:R)=>void)[]=[r=>{delete (r.cash.entries as {list?:unknown}).list},r=>{delete (r.cash.entries as {sums?:unknown}).sums},r=>{r.cash.entries.list.order='SOURCE'},r=>{r.cash.entries.list.status=null},r=>{(r.cash.entries.list as Record<string,unknown>).extra=1},
   r=>{r.cash.entries.sums.net='0.00'},r=>{r.cash.entries.sums.debit='-1.00'},r=>{(r.cash.entries.sums as Record<string,unknown>).credit=11},r=>{r.cash.entries.rows[0].status='POSTED'}]
  for(const change of variants){const r=structuredClone(good);change(r);expect(()=>parseFinanceAnalysis(r,dates,0,list)).toThrow()}
  const whole={...list,entry_status:null},all=reader({...dates,...whole,offset:0,limit:25});expect(()=>parseFinanceAnalysis(all,dates,0,whole)).not.toThrow()
  all.cash.entries.sums.debit='1.00';all.cash.entries.sums.net='-35.20';expect(()=>parseFinanceAnalysis(all,dates,0,whole)).toThrow() // unfiltered sums must be the whole period
  expect(()=>parseFinanceAnalysis(good,dates,0)).toThrow() // an echo nobody asked for is refused too
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
