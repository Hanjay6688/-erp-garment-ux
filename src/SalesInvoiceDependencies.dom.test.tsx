// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SalesInvoiceDependencies from './SalesInvoiceDependencies'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import type {SalesRead} from './salesReadContract'
const state=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn(),open:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>state}))
vi.mock('./TransactionSourceNavigation',()=>({default:({sourceType,sourceId,disabled,label}:{sourceType:string;sourceId:string;disabled:boolean;label:string})=><button disabled={disabled} onClick={()=>state.open(sourceType,sourceId)}>{label}</button>}))
const id='11111111-1111-4111-8111-111111111111',paymentId='22222222-2222-4222-8222-222222222222',returnId='33333333-3333-4333-8333-333333333333'
const source:NonNullable<SalesRead['detail']>={id,number:'INV-1',customer_id:id,customer_name:'Toko',location_id:id,location_name:'Gudang',physical_at:'2026-09-29T03:00:00Z',due_date:null,status:'PARTIAL_PAID',row_version:'9007199254740993',notes:null,payment_terms:null,line_count:'1',qty_pcs:'4',reserved_qty:'0',returned_qty:'1',review_token:'a'.repeat(32),items:[],financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'80.00',return_total:'20.00',net_total:'60.00',paid_total:'30.00',open_balance:'30.00'}}
const payment={id:paymentId,number:'PAY-NATIVE-1',physical_at:'2026-09-29T03:30:00Z',amount:'30.00',cash_account_id:id,cash_account_name:'Bank',method:'BANK_TRANSFER',reference:null,notes:null,status:'POSTED',replaces_payment_id:null}
const returned={id:returnId,number:'RET-NATIVE-1',physical_at:'2026-09-29T04:00:00Z',status:'POSTED',notes:null,line_count:'1',items:[{id,allocation_id:paymentId,product_sku:'SKU-31',lot_number:'LOT-1',location_id:id,location_name:'Gudang',qty_pcs:'1',quality_grade:'GRADE_A',refund_amount:'20.00',notes:null}]}
const page=(rows:unknown[],offset=0,total=String(rows.length),next:number|null=null)=>({rows,total,offset,limit:25,next_offset:next})
const cash=(rows:unknown[]=[payment],offset=0,total=String(rows.length),next:number|null=null)=>({contract_version:'cp7.sales-cash.v1',sale_id:id,row_version:source.row_version,review_token:source.review_token,payments:page(rows,offset,total,next),cash_accounts:page([])})
const returns=(rows:unknown[]=[returned],offset=0,total=String(rows.length),next:number|null=null)=>({contract_version:'cp7.sales-returns.v1',kind:'RETURNS',sale_id:id,row_version:source.row_version,review_token:source.review_token,page:page(rows,offset,total,next)})
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});state.rpc.mockReset();state.open.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view','finance.ar.view','sales.payment.view','sales.return.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container);state.rpc.mockImplementation(async(name)=>({data:name==='erp_cp7_get_sales_cash_v1'?cash():returns(),error:null}))})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
const button=(name:string)=>[...container.querySelectorAll('button')].find(x=>x.textContent===name)!
async function mount(current=true,locked=false,s=source){await act(async()=>root.render(<SalesInvoiceDependencies source={s} current={current} locked={locked}/>));await flush()}
async function click(name:string){await act(async()=>button(name).click());await flush()}
describe('Exact invoice downstream discovery',()=>{
 it('reads only on request and opens actual child identities without changing the invoice or calling a writer',async()=>{
  const original=structuredClone(source);await mount();expect(state.rpc).not.toHaveBeenCalled();expect(container.textContent).toContain('Rincian dokumen belum dimuat');await click('Lihat dokumen penghalang');expect(container.textContent).toContain('PAY-NATIVE-1');expect(container.textContent).toContain('RET-NATIVE-1')
  await click('Buka pembayaran PAY-NATIVE-1');await click('Buka retur RET-NATIVE-1');expect(state.open.mock.calls).toEqual([['SALES_PAYMENT',paymentId],['SALES_RETURN',returnId]]);expect(source).toEqual(original);expect(state.rpc.mock.calls.map(x=>x[0])).toEqual(['erp_cp7_get_sales_cash_v1','erp_cp7_get_sales_returns_v1'])
 })
 it('keeps all-history pagination while excluding reversed rows and reaches an active child on the second page',async()=>{
  const inactive=Array.from({length:25},(_,i)=>({...payment,id:`00000000-0000-4000-8000-${String(i+1).padStart(12,'0')}`,number:`OLD-${i}`,status:'REVERSED'}))
  state.rpc.mockImplementation(async(name,{p_query})=>({data:name==='erp_cp7_get_sales_cash_v1'?(p_query.payment_offset===0?cash(inactive,0,'26',25):cash([payment],25,'26')):returns(),error:null}));await mount();await click('Lihat dokumen penghalang');expect(container.textContent).toContain('26 pembayaran dalam riwayat');expect(container.textContent).toContain('Halaman ini tidak menampilkan pembayaran aktif.');expect(container.textContent).not.toContain('OLD-');await click('Penghalang pembayaran berikutnya');expect(state.rpc.mock.calls.at(-2)![1].p_query.payment_offset).toBe(25);await click('Buka pembayaran PAY-NATIVE-1');expect(state.open).toHaveBeenCalledWith('SALES_PAYMENT',paymentId)
 })
 it('retires both lists on a failed refresh and does not report missing data as an empty dependency list',async()=>{
  await mount();await click('Lihat dokumen penghalang');state.rpc.mockResolvedValue({data:null,error:{message:'Sumber rincian tidak tersedia'}});await click('Lihat dokumen penghalang');expect(container.textContent).not.toContain('PAY-NATIVE-1');expect(container.textContent).not.toContain('RET-NATIVE-1');expect(container.textContent).toContain('Rincian belum dapat dipastikan');expect(container.textContent).not.toContain('Halaman ini tidak menampilkan pembayaran aktif.')
 })
 it('rejects a mismatched current parent version and never mixes one successful list with one stale list',async()=>{
  state.rpc.mockImplementation(async(name)=>({data:name==='erp_cp7_get_sales_cash_v1'?{...cash(),row_version:'9007199254740994'}:returns(),error:null}));await mount();await click('Lihat dokumen penghalang');expect(container.querySelector('[data-invoice-payment-dependency-id]')).toBeNull();expect(container.querySelector('[data-invoice-return-dependency-id]')).toBeNull();expect(container.textContent).toContain('Rincian belum dapat dipastikan')
 })
 it('does not read a forbidden family and clears old children immediately when current authority retires',async()=>{
  const a=state.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='sales.return.view');await mount();await click('Lihat dokumen penghalang');expect(state.rpc.mock.calls.map(x=>x[0])).toEqual(['erp_cp7_get_sales_cash_v1']);expect(container.textContent).toContain('Izin lihat retur diperlukan');expect(container.textContent).not.toContain('RET-NATIVE-1');a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.ar.view');await mount();expect(container.textContent).not.toContain('PAY-NATIVE-1');expect(button('Lihat dokumen penghalang').disabled).toBe(true)
 })
 it('allows an authorized readonly inspection while writers are locked but prevents opening source actions',async()=>{
  await mount(true,true);await click('Lihat dokumen penghalang');expect(container.textContent).toContain('PAY-NATIVE-1');expect(button('Buka pembayaran PAY-NATIVE-1').disabled).toBe(true);await click('Buka pembayaran PAY-NATIVE-1');expect(state.open).not.toHaveBeenCalled();await mount(false,true);expect(container.textContent).not.toContain('PAY-NATIVE-1')
 })
 it('fences an old actor reply after source retirement and keeps previous-page recovery when a page shrinks',async()=>{
  let resolve!:(v:unknown)=>void;state.rpc.mockImplementation((name)=>name==='erp_cp7_get_sales_cash_v1'?new Promise(r=>{resolve=r}):Promise.resolve({data:returns(),error:null}));await mount();await click('Lihat dokumen penghalang');await mount(false);await act(async()=>resolve({data:cash(),error:null}));await flush();expect(container.textContent).not.toContain('PAY-NATIVE-1')
  state.rpc.mockImplementation(async(name,{p_query})=>({data:name==='erp_cp7_get_sales_cash_v1'?(p_query.payment_offset===0?cash(Array.from({length:25},(_,i)=>({...payment,id:`00000000-0000-4000-8000-${String(i+1).padStart(12,'0')}`,number:`PAGE-${i+1}`,status:'REVERSED'})),0,'26',25):cash([],25,'25')):returns(),error:null}));await mount();await click('Lihat dokumen penghalang');await click('Penghalang pembayaran berikutnya');expect(button('Penghalang pembayaran sebelumnya').disabled).toBe(false);expect(container.textContent).not.toContain('26–25');await click('Penghalang pembayaran sebelumnya');expect(state.rpc.mock.calls.at(-2)![1].p_query.payment_offset).toBe(0)
 })
})
