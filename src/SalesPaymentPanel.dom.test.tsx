// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SalesPaymentPanel from './SalesPaymentPanel'
import {parseSalesCash,salesCashAmount,salesCashCents} from './salesCashContract'
import {parseSalesOutcome,type SalesRead} from './salesReadContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const mock=vi.hoisted(()=>({auth:null as unknown}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
const id='11111111-1111-4111-8111-111111111111',bank='22222222-2222-4222-8222-222222222222',payment='33333333-3333-4333-8333-333333333333',request='44444444-4444-4444-8444-444444444444'
// Stable client: production useMemo receives one client for its runtime.
const fixed=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>fixed}))
const source:NonNullable<SalesRead['detail']>={id,number:'INV-1',customer_id:id,customer_name:'Toko A',location_id:id,location_name:'FG',physical_at:'2026-09-29T03:00:00Z',due_date:null,status:'POSTED',row_version:'9007199254740993',notes:null,payment_terms:null,line_count:'1',qty_pcs:'3',reserved_qty:'0',returned_qty:'0',review_token:'a'.repeat(32),items:[],financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'30.01',return_total:'0.00',net_total:'30.01',paid_total:'0.00',open_balance:'30.01'}}
const p={id:payment,number:'PAY-1',physical_at:'2026-09-29T04:00:00Z',amount:'10.01',cash_account_id:bank,cash_account_name:'Bank utama',method:'BANK_TRANSFER',reference:'REF-1',notes:'Simpan catatan',status:'POSTED',replaces_payment_id:null}
const response=(withPayment=false)=>({contract_version:'cp7.sales-cash.v1',sale_id:id,row_version:source.row_version,review_token:source.review_token,payments:{rows:withPayment?[p]:[],total:withPayment?'1':'0',offset:0,limit:25,next_offset:null},cash_accounts:{rows:[{id:bank,code:'BANK1',name:'Bank utama',kind:'BANK'}],total:'1',offset:0,limit:25,next_offset:null}})
let root:Root,container:HTMLDivElement;const saved=vi.fn()
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});fixed.rpc.mockReset();saved.mockReset();const auth=structuredClone(recoveryIdentity);auth.identity.permissions.push('sales.invoice.view','finance.ar.view','sales.payment.view','sales.payment.create','sales.payment.post','sales.payment.reverse');mock.auth=auth;container=document.createElement('div');document.body.append(container);root=createRoot(container);fixed.rpc.mockResolvedValue({data:response(),error:null})})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(stale=false){await act(async()=>root.render(<SalesPaymentPanel source={source} locked={false} stale={stale} onSave={saved} onClose={()=>{}}/>));await flush()}
const input=(label:string)=>container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
async function fill(label:string,value:string){await act(async()=>{const e=input(label);Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
async function selectHistory(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLSelectElement>(`[aria-label="${label}"]`)!;e.value=value;e.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
async function fillValid(){await fill('Nomor pembayaran pelanggan','PAY-NEW');await fill('Waktu pembayaran pelanggan WIB','2026-09-29T12:31');await fill('Nominal pembayaran pelanggan','10,01');await click(container.querySelector<HTMLElement>('[aria-label="Pilih rekening pembayaran pelanggan"] .cproc-receipt')!)}
describe('P11 exact source cash receipt',()=>{
 it('searches and sorts only the loaded payment page without changing source, reviewed form or sending a writer',async()=>{
  const r=response(true);r.payments.rows=[{...p,number:'PAY-10'},{...p,id:'66666666-6666-4666-8666-666666666666',number:'PAY-2'},{...p,id:'77777777-7777-4777-8777-777777777777',number:'PAY-4',status:'REVERSED'}];r.payments.total='3';const original=structuredClone(r)
  fixed.rpc.mockResolvedValue({data:r,error:null});await mount();await fillValid();await click(input('Pembayaran pelanggan sudah diperiksa'));const reads=fixed.rpc.mock.calls.length
  const numbers=()=>[...container.querySelectorAll('[aria-label="Riwayat pembayaran invoice"] .cproc-item h4')].map(e=>e.textContent?.split(' · ')[0])
  expect(numbers()).toEqual(['PAY-10','PAY-2','PAY-4']);await selectHistory('Urutkan halaman riwayat pembayaran invoice','LABEL_ASC');expect(numbers()).toEqual(['PAY-2','PAY-4','PAY-10'])
  await selectHistory('Status pembayaran di halaman ini','POSTED');expect(numbers()).toEqual(['PAY-2','PAY-10']);await fill('Cari pembayaran di halaman ini','PAY-10');await click(button('Cari pembayaran di halaman ini'));expect(numbers()).toEqual(['PAY-10']);expect(container.textContent).toContain('Menampilkan 1 dari 3 pembayaran pada halaman ini')
  expect(input('Nomor pembayaran pelanggan').value).toBe('PAY-NEW');expect(input('Nominal pembayaran pelanggan').value).toBe('10,01');expect(input('Pembayaran pelanggan sudah diperiksa').checked).toBe(true)
  await click(button('Semua pembayaran di halaman ini'));expect(numbers()).toEqual(['PAY-10','PAY-2','PAY-4']);expect(input('Cari pembayaran di halaman ini').value).toBe('');expect(fixed.rpc).toHaveBeenCalledTimes(reads);expect(saved).not.toHaveBeenCalled();expect(r).toEqual(original)
 })
 it('rejects hidden rounding, wrong source token and incomplete pages',()=>{expect(salesCashAmount('10,01')).toBe('10.01');expect(salesCashAmount('10.001')).toBeNull();expect(salesCashCents('9007199254740993.01')).toBe(900719925474099301n);expect(parseSalesCash(response(),source).cash_accounts.rows[0].id).toBe(bank);expect(()=>parseSalesCash({...response(),review_token:'b'.repeat(32)},source)).toThrow();const r=response();r.cash_accounts.total='2';expect(()=>parseSalesCash(r,source)).toThrow()})
 it('requires explicit amount, real bank and review, preserving exact revision and WIB clock',async()=>{
  await mount();expect(input('Nominal pembayaran pelanggan').value).toBe('');expect(button('Catat pembayaran pelanggan').disabled).toBe(true);await fillValid();await fill('Referensi pembayaran pelanggan','REF-NEW');await fill('Catatan pembayaran pelanggan','Catatan utuh');await click(input('Pembayaran pelanggan sudah diperiksa'));expect(button('Catat pembayaran pelanggan').disabled).toBe(false);await click(button('Catat pembayaran pelanggan'))
  expect(saved).toHaveBeenCalledOnce();const [action,document,version]=saved.mock.calls[0];expect(action).toBe('PAYMENT');expect(version).toBe('9007199254740993');expect(document).toMatchObject({sale_id:id,review_token:source.review_token,amount:'10.01',cash_account_id:bank,payment_date:'2026-09-29T05:31:00.000Z',reference_number:'REF-NEW',notes:'Catatan utuh'})
 })
 it('invalidates review on changed money and rejects fractional cents and overpayment',async()=>{
  await mount();await fillValid();await click(input('Pembayaran pelanggan sudah diperiksa'));await fill('Nominal pembayaran pelanggan','10.001');expect(input('Pembayaran pelanggan sudah diperiksa').checked).toBe(false);await click(input('Pembayaran pelanggan sudah diperiksa'));expect(button('Catat pembayaran pelanggan').disabled).toBe(true);await fill('Nominal pembayaran pelanggan','30.02');await click(input('Pembayaran pelanggan sudah diperiksa'));expect(button('Catat pembayaran pelanggan').disabled).toBe(true);expect(saved).not.toHaveBeenCalled()
 })
 it('reviews the selected native payment for inverse without inventing another receipt',async()=>{
  fixed.rpc.mockResolvedValue({data:response(true),error:null});await mount();await click(button('Koreksi pembayaran PAY-1'));expect(input('Alasan tindakan pembayaran').value).toBe('');await fill('Alasan tindakan pembayaran','Koreksi referensi pembayaran');await click(input('Pembayaran pelanggan sudah diperiksa'));await click(button('Batalkan pembayaran tercatat'))
  expect(saved).toHaveBeenCalledWith('PAYMENT_REVERSE',{sale_id:id,review_token:source.review_token,change_reason:'Koreksi referensi pembayaran',payment_id:payment},source.row_version)
 })
 it('preserves the form while a source refresh fails or its invoice becomes stale',async()=>{
  await mount();await fillValid();fixed.rpc.mockResolvedValue({data:null,error:{message:'Sumber sedang tidak tersedia'}});await click(button('Muat ulang pembayaran'));expect(input('Nominal pembayaran pelanggan').value).toBe('10,01');expect(container.textContent).toContain('Sumber sedang tidak tersedia');expect(container.querySelector('fieldset')!.disabled).toBe(true);await mount(true);expect(input('Nominal pembayaran pelanggan').value).toBe('10,01');expect(saved).not.toHaveBeenCalled()
 })
 it('binds a recovered inverse outcome to the exact payment and rejects false completion',()=>{
  const r={contract_version:'cp7.sales-outcome.v1',kind:'COMMITTED_OUTCOME',action:'PAYMENT_REVERSE',request_id:request,sale_id:id,status:'POSTED',row_version:'9007199254740994',payment_id:payment,payment_status:'REVERSED'}
  expect(parseSalesOutcome(r,request,'PAYMENT_REVERSE',id,payment).payment_id).toBe(payment);expect(()=>parseSalesOutcome(r,request,'PAYMENT_REVERSE',id,bank)).toThrow();expect(()=>parseSalesOutcome({...r,payment_status:'POSTED'},request,'PAYMENT_REVERSE',id,payment)).toThrow()
 })
})
