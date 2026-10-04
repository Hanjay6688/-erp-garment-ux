// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SalesPaymentCorrectionPanel from './SalesPaymentCorrectionPanel'
import {parsePaymentCorrectionWorkspace,parsePaymentCorrectionOutcome,type PaymentCorrectionWorkspace} from './salesPaymentCorrectionContract'
import {parseTransactionSource} from './transactionSource'
import type {SalesRead} from './salesReadContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
// Declared component stand-in: Native routing is proved separately in CI.
vi.mock('./TransactionSourceNavigation',()=>({default:({sourceId,label,disabled}:{sourceId:string;label:string;disabled:boolean})=><button data-source-id={sourceId} disabled={disabled}>{label}</button>}))
const sale='11111111-1111-4111-8111-111111111111',payment='22222222-2222-4222-8222-222222222222',bank='33333333-3333-4333-8333-333333333333',old='44444444-4444-4444-8444-444444444444',request='55555555-5555-4555-8555-555555555555'
const source:NonNullable<SalesRead['detail']>={id:sale,number:'INV-1',customer_id:sale,customer_name:'Toko',location_id:sale,location_name:'FG',physical_at:'2026-09-28T03:00:00Z',due_date:null,status:'PARTIAL_PAID',row_version:'9007199254740993',notes:null,payment_terms:null,line_count:'1',qty_pcs:'4',reserved_qty:'0',returned_qty:'0',review_token:'a'.repeat(32),items:[],financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'80.00',return_total:'0.00',net_total:'80.00',paid_total:'30.01',open_balance:'49.99'}}
const paymentDocument={id:payment,number:'PAY-1',physical_at:'2025-09-28T04:00:59.123456+00:00',amount:'30.01',cash_account_id:bank,cash_account_name:'Bank utama',method:'BANK_TRANSFER',reference:'REF-1',notes:'Catatan utuh',status:'POSTED' as const,replaces_payment_id:null}
const link={original_id:old,replacement_id:payment,sale_id:sale,actor_scope_id:sale,request_id:request,reason:'Koreksi pertama setelah pemeriksaan',recorded_at:'2026-09-29T04:00:00Z',time_restatement:null}
const response=():PaymentCorrectionWorkspace=>({contract_version:'cp7.sales-payment-correction-workspace.v1',captured_at:'2026-09-29T04:00:00Z',sale_id:sale,row_version:source.row_version,review_token:source.review_token!,document:structuredClone(paymentDocument),eligible:true,previous:null,next:null,cash_accounts:{rows:[{id:bank,code:'BANK-1',name:'Bank utama',kind:'BANK'}],total:'1',offset:0,limit:25,next_offset:null}})
let root:Root,container:HTMLDivElement;const saved=vi.fn()
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset();saved.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view','finance.ar.view','sales.payment.view','sales.payment.create','sales.payment.post','sales.payment.reverse');mock.auth=a;mock.rpc.mockResolvedValue({data:response(),error:null});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(edit=true,locked=false,stale=false){await act(async()=>root.render(<SalesPaymentCorrectionPanel source={source} payment={paymentDocument} edit={edit} locked={locked} stale={stale} onClose={()=>{}} onSave={saved}/>));await flush()}
const input=(label:string)=>container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
async function fill(label:string,value:string){await act(async()=>{const e=input(label);Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
async function review(){await fill('Alasan koreksi pembayaran','Nominal diperiksa dan diperbaiki');await click(input('Koreksi pembayaran sudah diperiksa'))}
describe('ordinary payment correction component and strict server stand-ins',()=>{
 it('emits one reviewed intent with exact source revision and original microseconds',async()=>{
  await mount();expect(saved).not.toHaveBeenCalled();expect(button('Simpan koreksi pembayaran').disabled).toBe(true);await fill('Nominal koreksi pembayaran','20,01');await review();await click(button('Simpan koreksi pembayaran'))
  expect(saved).toHaveBeenCalledOnce();expect(saved).toHaveBeenCalledWith('PAYMENT_CORRECT',{sale_id:sale,payment_id:payment,review_token:source.review_token,change_reason:'Nominal diperiksa dan diperbaiki',replacement:{payment_number:'PAY-1',payment_date:paymentDocument.physical_at,amount:'20.01',cash_account_id:bank,payment_method:'BANK_TRANSFER',reference_number:'REF-1',notes:'Catatan utuh'}},source.row_version)
  expect(new Set(mock.rpc.mock.calls.map(c=>c[0]))).toEqual(new Set(['erp_cp7_get_sales_payment_correction_v1']))
 })
 it('uses the replacement capacity and refuses cents rounding, overpayment, no change and retired writers',async()=>{
  await mount();await fill('Nominal koreksi pembayaran','80.01');await review();expect(button('Simpan koreksi pembayaran').disabled).toBe(true);await fill('Nominal koreksi pembayaran','20.001');expect(input('Koreksi pembayaran sudah diperiksa').checked).toBe(false);await review();expect(button('Simpan koreksi pembayaran').disabled).toBe(true)
  await fill('Nominal koreksi pembayaran','30.01');await review();expect(button('Simpan koreksi pembayaran').disabled).toBe(true);await fill('Nominal koreksi pembayaran','30.010');await review();expect(button('Simpan koreksi pembayaran').disabled).toBe(true);await fill('Nominal koreksi pembayaran','80.00');await review();expect(button('Simpan koreksi pembayaran').disabled).toBe(false);await mount(true,true);expect(button('Simpan koreksi pembayaran').disabled).toBe(true);expect(saved).not.toHaveBeenCalled()
 })
 it('changes the true WIB time only when edited and preserves the explicit account and notes',async()=>{
  await mount();await fill('Waktu koreksi pembayaran WIB','2025-09-29T12:31');await fill('Referensi koreksi pembayaran','REF-2');await fill('Catatan koreksi pembayaran','Catatan diperbaiki');await review();await click(button('Simpan koreksi pembayaran'))
  expect(saved.mock.calls[0][1].replacement).toMatchObject({payment_date:'2025-09-29T05:31:00.000Z',amount:'30.01',cash_account_id:bank,reference_number:'REF-2',notes:'Catatan diperbaiki'})
 })
 it('restores all actual prior fields with a new reviewed correction, retaining its microseconds',async()=>{
  const w=response();w.previous={link,document:{...paymentDocument,id:old,number:'PAY-OLD',status:'REVERSED',amount:'35.02',physical_at:'2025-09-27T04:01:59.654321+00:00',method:'CASH',reference:'OLD-REF',notes:'Catatan sebelum koreksi'}};mock.rpc.mockResolvedValue({data:w,error:null});await mount(false);expect(container.querySelector('form')).toBeNull();await click(button('Pulihkan isi pembayaran sebelum koreksi'));expect(input('Nominal koreksi pembayaran').value).toBe('35.02');expect(input('Alasan koreksi pembayaran').value).toBe('');await review();await click(button('Simpan koreksi pembayaran'))
  expect(saved.mock.calls[0][1].payment_id).toBe(payment);expect(saved.mock.calls[0][1].replacement).toMatchObject({payment_number:'PAY-1',payment_date:w.previous.document.physical_at,amount:'35.02',payment_method:'CASH',reference_number:'OLD-REF',notes:'Catatan sebelum koreksi'})
 })
 it('shows exact adjacent source IDs and keeps a role without reverse permission read-only',async()=>{
  const w=response();w.previous={link,document:{...paymentDocument,id:old,number:'PAY-OLD',status:'REVERSED'}};mock.rpc.mockResolvedValue({data:w,error:null});const a=mock.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='sales.payment.reverse');await mount(false)
  expect(container.querySelector('[data-source-id]')!.getAttribute('data-source-id')).toBe(old);expect(button('Edit pembayaran tercatat')).toBeUndefined();expect(button('Pulihkan isi pembayaran sebelum koreksi')).toBeUndefined();expect(container.querySelector('form')).toBeNull();expect(saved).not.toHaveBeenCalled()
 })
 it('retires old verified facts on failed refresh and refuses stale parent data',async()=>{
  await mount();await fill('Nominal koreksi pembayaran','20.01');await review();mock.rpc.mockResolvedValue({data:null,error:{message:'Sumber gagal dimuat'}});await click(button('Muat ulang perubahan pembayaran'));expect(container.textContent).toContain('Sumber gagal dimuat');expect(container.textContent).not.toContain('Data diperiksa');expect(button('Simpan koreksi pembayaran')).toBeUndefined();expect(saved).not.toHaveBeenCalled()
  mock.rpc.mockResolvedValue({data:response(),error:null});await click(button('Muat ulang perubahan pembayaran'));expect(input('Nominal koreksi pembayaran').value).toBe('20.01');expect(input('Koreksi pembayaran sudah diperiksa').checked).toBe(false);await mount(true,false,true);expect(button('Simpan koreksi pembayaran').disabled).toBe(true)
 })
 it('ignores an older response after a fresh read and keeps bank pages source-bound',async()=>{
  let finish!:(v:unknown)=>void;mock.rpc.mockImplementationOnce(()=>new Promise(r=>{finish=r}));await mount();await act(async()=>root.unmount());root=createRoot(container);const w=response();w.document.cash_account_name='Nama bank saat pembacaan baru';mock.rpc.mockResolvedValue({data:w,error:null});await mount();await act(async()=>finish({data:response(),error:null}));await flush();expect(container.textContent).toContain('Rekening terpilih: Nama bank saat pembacaan baru');expect(saved).not.toHaveBeenCalled()
  const page=response();page.cash_accounts={rows:[{id:old,code:'BANK-2',name:'Rekening halaman kedua',kind:'BANK'}],total:'26',offset:25,limit:25,next_offset:null};const first=response();first.cash_accounts.rows=[...first.cash_accounts.rows,...Array.from({length:24},(_,i)=>({id:`66666666-6666-4666-8666-${String(i).padStart(12,'0')}`,code:`BANK-X${i}`,name:`Rekening ${i}`,kind:'BANK'}))];first.cash_accounts.total='26';first.cash_accounts.next_offset=25;mock.rpc.mockResolvedValueOnce({data:first,error:null}).mockResolvedValueOnce({data:page,error:null});await click(button('Muat ulang perubahan pembayaran'));await click(button('Rekening koreksi berikutnya'));expect(mock.rpc.mock.calls.at(-1)![1].p_query.bank_offset).toBe(25);expect(container.textContent).toContain('Rekening halaman kedua')
 })
 it('refuses wrong child, lineage, pagination and falsely completed correction outcomes',()=>{
  expect(parsePaymentCorrectionWorkspace(response(),source,payment).document.id).toBe(payment)
  for(const w of [{...response(),review_token:'b'.repeat(32)},{...response(),document:{...paymentDocument,id:old}},{...response(),previous:{link:{...link,replacement_id:old},document:{...paymentDocument,id:old,status:'REVERSED'}}},{...response(),cash_accounts:{...response().cash_accounts,total:'2',next_offset:null}}])expect(()=>parsePaymentCorrectionWorkspace(w,source,payment)).toThrow()
  const r={contract_version:'cp7.sales-payment-correction.v1',kind:'COMMITTED_OUTCOME',action:'PAYMENT_CORRECT',request_id:request,sale_id:sale,status:'PARTIAL_PAID',row_version:'9007199254740994',original_payment_id:old,original_payment_status:'REVERSED',payment_id:payment,payment_status:'POSTED',link}
  expect(parsePaymentCorrectionOutcome(r,request,sale,old).payment_id).toBe(payment)
  for(const bad of [{...r,original_payment_id:bank},{...r,payment_status:'DRAFT'},{...r,link:{...link,request_id:bank}},{...r,link:{...link,replacement_id:bank}},{...r,unknown:true}])expect(()=>parsePaymentCorrectionOutcome(bad,request,sale,old)).toThrow()
  for(const kind of ['PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE']){const ref={source_type:kind,source_id:old},body={contract_version:'cp7.transaction-source.v1',actor_scope_id:sale,source:ref,status:'AVAILABLE',read_at:'2026-09-29T04:00:00Z',business_DML:false,document:{domain:'SALE',route:'sales-payments',id:sale,number:'INV-1',status:'PARTIAL_PAID',revision:source.row_version,focus:{kind:'SALES_PAYMENT',id:old,page_offset:25}}};expect(parseTransactionSource(body,ref,sale).document?.focus?.id).toBe(old);expect(()=>parseTransactionSource({...body,document:{...body.document,focus:{...body.document.focus,id:payment}}},ref,sale)).toThrow()}
 })
})
