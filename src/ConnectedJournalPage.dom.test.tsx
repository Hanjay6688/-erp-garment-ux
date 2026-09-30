// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedJournalPage from './ConnectedJournalPage'
import {parseJournalRead,type JournalDates,type JournalRead} from './journalReadContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
const id='11111111-1111-4111-8111-111111111111',account='22222222-2222-4222-8222-222222222222',other='33333333-3333-4333-8333-333333333333'
type Query=JournalDates&{offset?:number;journal_id?:string|null}
function fixture(q:Query,amount='10.01'):JournalRead{
 const h={id,number:'JRN-NATIVE-1',source_type:'SALE',source_id:other,status:'POSTED' as const,reversal_of_id:null,description:'Invoice source',economic_date:q.to,transaction_date:q.to,posting_at:'2026-09-30T03:00:00Z',period_shifted:false,line_count:'2',debit:amount,credit:amount,balanced:true}
 const base={account_id:account,account_code:'1100',account_name:'Kas',description:null,customer_id:null,vendor_id:null,contractor_id:null,po_id:null,product_id:null}
 return {contract_version:'cp7.journal-read.v1',captured_at:'2026-09-30T03:00:00Z',knowledge_basis:'CURRENT_RECORDED_KNOWLEDGE',historical_knowledge:'NOT_RECONSTRUCTED',basis:{from:q.from,to:q.to,q:q.q,scope:'POSTED_AND_REVERSED_JOURNALS_BY_ACCOUNTING_DATE'},totals:{journal_count:'1',line_count:'2',debit:amount,credit:amount,unbalanced_journal_count:'0'},page:{rows:[h],total:'1',offset:q.offset??0,limit:25,next_offset:null},detail:q.journal_id?{...h,lines:[{...base,id:account,debit:amount,credit:'0.00'},{...base,id:other,account_code:'3100',account_name:'Modal',debit:'0.00',credit:amount}]}:null}
}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset();const auth=structuredClone(recoveryIdentity);auth.identity.permissions.push('finance.journal.view');mock.auth=auth;mock.rpc.mockImplementation((_name,{p_query})=>Promise.resolve({data:fixture(p_query),error:null}));container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedJournalPage/>));await flush()}
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
const button=(name:string)=>[...container.querySelectorAll('button')].find(e=>e.textContent===name)!
async function fill(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
const dates={from:'2026-09-01',to:'2026-09-29',q:''}
describe('complete native journal source',()=>{
 it('keeps exact money beyond JS integer precision and full selected account lines',async()=>{
  mock.rpc.mockImplementation((_name,{p_query})=>Promise.resolve({data:fixture(p_query,'9007199254740993.01'),error:null}))
  await mount();await click(container.querySelector<HTMLElement>('[data-journal-id]')!)
  expect(container.textContent).toContain('Rp9.007.199.254.740.993,01');expect(container.querySelectorAll('[data-journal-line-id]')).toHaveLength(2);expect(container.textContent).toContain('3100 · Modal')
  expect(mock.rpc.mock.calls.every(([name])=>name==='erp_cp7_get_journal_book_v1')).toBe(true)
 })
 it('preserves reversed originals, linked inverses and different economic/accounting dates',()=>{
  const original=fixture(dates);original.page.rows[0].status='REVERSED';expect(parseJournalRead(original,dates).page.rows[0].status).toBe('REVERSED')
  const inverse=fixture({...dates,journal_id:id});for(const h of [inverse.page.rows[0],inverse.detail!]){h.reversal_of_id=other;h.economic_date='2026-08-31';h.period_shifted=true}
  const r=parseJournalRead(inverse,dates,0,id);expect(r.detail?.reversal_of_id).toBe(other);expect(r.detail?.economic_date).toBe('2026-08-31');expect(r.detail?.transaction_date).toBe(dates.to)
 })
 it('rejects numeric money, wrong basis, hidden/duplicate lines, false balance and page subtotals',()=>{
  const numeric=fixture(dates);Object.assign(numeric.totals,{debit:10.01});expect(()=>parseJournalRead(numeric,dates)).toThrow()
  expect(()=>parseJournalRead(fixture(dates),{...dates,to:'2026-09-28'})).toThrow()
  const missing=fixture({...dates,journal_id:id});missing.detail!.lines.pop();expect(()=>parseJournalRead(missing,dates,0,id)).toThrow()
  const duplicate=fixture({...dates,journal_id:id});duplicate.detail!.lines[1].id=duplicate.detail!.lines[0].id;expect(()=>parseJournalRead(duplicate,dates,0,id)).toThrow()
  const balanced=fixture(dates);balanced.page.rows[0].balanced=false;expect(()=>parseJournalRead(balanced,dates)).toThrow()
  const partial=fixture(dates);partial.totals.debit=partial.totals.credit='1.00';expect(()=>parseJournalRead(partial,dates)).toThrow()
  const draft=fixture(dates);Object.assign(draft.page.rows[0],{status:'DRAFT'});expect(()=>parseJournalRead(draft,dates)).toThrow()
 })
 it('pages25+5 with identical full totals and retires old selected lines during page reads',async()=>{
  mock.rpc.mockImplementation((_name,{p_query})=>{const d=fixture(p_query,'1.25');d.totals={journal_count:'30',line_count:'60',debit:'37.50',credit:'37.50',unbalanced_journal_count:'0'};d.page.total='30';d.page.offset=p_query.offset;d.page.next_offset=p_query.offset===0?25:null;d.page.rows=Array.from({length:p_query.offset===0?25:5},(_,i)=>({...d.page.rows[0],id:`11111111-1111-4111-8111-${String(i+p_query.offset+1).padStart(12,'0')}`,number:'PAGE-'+(i+p_query.offset+1)}));return Promise.resolve({data:d,error:null})})
  await mount();expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(25);expect(container.querySelector('[aria-label="Basis dan total jurnal"]')!.textContent).toContain('Rp37,5')
  await click(button('Jurnal berikutnya'));expect(container.querySelectorAll('[data-journal-id]')).toHaveLength(5);expect(container.querySelector('[aria-label="Basis dan total jurnal"]')!.textContent).toContain('Rp37,5');expect(container.textContent).toContain('Total 30 jurnal');expect(button('Jurnal berikutnya').disabled).toBe(true)
 })
 it('date/search edits retire all amounts and refresh reads entered dates without an old selected source',async()=>{
  await mount();await click(container.querySelector<HTMLElement>('[data-journal-id]')!);const count=mock.rpc.mock.calls.length
  await fill('Cari sumber jurnal','NEW SOURCE');expect(container.textContent).not.toContain('Rp');expect(container.querySelectorAll('[data-journal-line-id]')).toHaveLength(0);expect(mock.rpc.mock.calls).toHaveLength(count)
  await fill('Periode jurnal dari','2026-08-31');await click(button('Muat ulang jurnal'));expect(mock.rpc.mock.calls.at(-1)?.[1].p_query).toMatchObject({q:'NEW SOURCE',from:'2026-08-31',journal_id:null,offset:0})
 })
 it('a late old result cannot repaint after invalid dates',async()=>{
  let resolveOld:((v:unknown)=>void)|null=null,old:Query|null=null;mock.rpc.mockImplementationOnce((_name,{p_query})=>{old=p_query;return new Promise(resolve=>{resolveOld=resolve})})
  await mount();await fill('Periode jurnal sampai','2026-08-01');await click(button('Tampilkan jurnal'));await act(async()=>resolveOld!({data:fixture(old!),error:null}));await flush();expect(container.textContent).toContain('Pilih periode pembukuan');expect(container.textContent).not.toContain('Rp')
 })
 it('an old actor response cannot replace the current actor source',async()=>{
  let resolveOld:((v:unknown)=>void)|null=null,old:Query|null=null;mock.rpc.mockImplementationOnce((_name,{p_query})=>{old=p_query;return new Promise(resolve=>{resolveOld=resolve})})
  await mount();const auth=structuredClone(mock.auth)as typeof recoveryIdentity;auth.identity.profile.id='new-actor';mock.auth=auth
  mock.rpc.mockImplementation((_name,{p_query})=>Promise.resolve({data:fixture(p_query,'20.02'),error:null}));await mount();await act(async()=>resolveOld!({data:fixture(old!,'10.01'),error:null}));await flush()
  expect(container.textContent).toContain('Rp20,02');expect(container.textContent).not.toContain('Rp10,01')
 })
 it('failed or malformed refresh clears financial facts and current journal permission/native role is mandatory',async()=>{
  await mount();mock.rpc.mockResolvedValueOnce({data:null,error:{message:'Hak jurnal dicabut'}});await click(button('Muat ulang jurnal'));expect(container.textContent).toContain('Hak jurnal dicabut');expect(container.textContent).not.toContain('Rp')
  const auth=mock.auth as typeof recoveryIdentity,count=mock.rpc.mock.calls.length;auth.identity.permissions=[];await mount();expect(container.textContent).toContain('Hak melihat jurnal');auth.identity.permissions=['finance.journal.view'];auth.identity.profile.role='STAFF';await mount();expect(container.textContent).toContain('Owner atau Admin');expect(mock.rpc.mock.calls).toHaveLength(count)
 })
})
