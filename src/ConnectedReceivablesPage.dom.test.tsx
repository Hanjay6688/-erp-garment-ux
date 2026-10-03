// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedReceivablesPage from './ConnectedReceivablesPage'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import type {SalesRead,SalesStatus} from './salesReadContract'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
const id='11111111-1111-4111-8111-111111111111',line='22222222-2222-4222-8222-222222222222'
function fixture(query:{offset?:number;sale_id?:string|null;status?:SalesStatus}={}):SalesRead{
 const status=query.status||'PARTIAL_PAID',active=['POSTED','PARTIAL_PAID','PAID'].includes(status)
 const financial:NonNullable<SalesRead['detail']>['financial']={basis:'CURRENT_NATIVE_DOCUMENT',state:active?'ACTIVE_RECEIVABLE':status==='DRAFT'?'DRAFT_PREVIEW':'INACTIVE_DOCUMENT',gross_total:'80.00',return_total:'20.00',net_total:'60.00',paid_total:'30.00',open_balance:active?'30.00':null}
 const row={id,number:'INV-NATIVE-1',customer_id:id,customer_name:'Toko sumber',location_id:id,location_name:'Gudang FG',physical_at:'2026-09-29T03:00:00Z',due_date:'2026-10-29',status,row_version:'9007199254740993',notes:null,payment_terms:null,line_count:'1',qty_pcs:'4',reserved_qty:'0',returned_qty:'1',financial}
 return {contract_version:'cp7.sales-workspace.v1',read_at:'2026-09-29T05:00:00Z',financial_captured:true,read_only:true,page:{rows:[row],total:'1',offset:query.offset??0,limit:25,next_offset:null},detail:query.sale_id?{...row,review_token:'a'.repeat(32),items:[{id:line,product_id:id,product_sku:'PHYSICAL',commercial_sku:'HISTORICAL',product_name:'Celana',size_code:'32',brand_name:'Vivo',qty_pcs:'4',notes:null,financial:{unit_price:'20.00',discount:'0.00',line_total:'80.00'}}]}:null}
}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset();const auth=structuredClone(recoveryIdentity);auth.identity.permissions.push('sales.invoice.view','finance.ar.view');mock.auth=auth;mock.rpc.mockImplementation((_name,{p_query})=>Promise.resolve({data:fixture(p_query),error:null}));container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedReceivablesPage/>));await flush()}
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
const button=(name:string)=>[...container.querySelectorAll('button')].find(e=>e.textContent===name)!
async function fill(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function chooseStatus(value:string){await act(async()=>{const e=container.querySelector<HTMLSelectElement>('[aria-label="Status sumber piutang"]')!;e.value=value;e.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
describe('native invoice receivables source',()=>{
 it('browses the owned full list and sorts only current source records without rewriting money',async()=>{
  mock.rpc.mockImplementation((_name,{p_query})=>{const d=fixture(p_query);d.page.rows=[{...d.page.rows[0],number:'INV-10'},{...d.page.rows[0],id:line,number:'INV-2'}];d.page.total='2';return Promise.resolve({data:d,error:null})})
  await mount();const before=mock.rpc.mock.calls.length
  const order=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan halaman piutang pelanggan"]')!
  await act(async()=>{order.value='LABEL_ASC';order.dispatchEvent(new Event('change',{bubbles:true}))})
  expect([...container.querySelectorAll('[data-sale-id] strong:first-child')].map(e=>e.textContent).slice(0,2)).toEqual(['INV-2','INV-10']);expect(mock.rpc.mock.calls).toHaveLength(before)
  expect([...container.querySelectorAll('[data-sale-id]')].every(e=>e.textContent!.includes('Rp30'))).toBe(true)
  await fill('Cari sumber piutang','Toko');await chooseStatus('POSTED');await click(button('Cari piutang'));expect(mock.rpc.mock.calls.at(-1)![1].p_query).toMatchObject({q:'Toko',status:'POSTED',sale_id:null,offset:0})
  await click(button('Browse semua'));expect(mock.rpc.mock.calls.at(-1)![1].p_query).toMatchObject({q:'',status:null,sale_id:null,offset:0})
  expect(new Set(mock.rpc.mock.calls.map(c=>c[0]))).toEqual(new Set(['erp_cp7_get_sales_v1']))
 })
 it('opens the exact source invoice through navigation, and retires source actions when facts retire',async()=>{
  const open=vi.fn();await act(async()=>root.render(<ConnectedReceivablesPage onOpenInvoice={open}/>));await flush()
  const before=mock.rpc.mock.calls.length;await click(button('Buka invoice INV-NATIVE-1'));expect(open).toHaveBeenLastCalledWith(id);expect(mock.rpc.mock.calls).toHaveLength(before)
  await click(container.querySelector<HTMLElement>('[data-sale-id]')!);await click(button('Edit / batalkan invoice INV-NATIVE-1'));expect(open).toHaveBeenCalledTimes(2);expect(open).toHaveBeenLastCalledWith(id)
  await fill('Cari sumber piutang','Berubah');expect(button('Buka invoice INV-NATIVE-1')).toBeUndefined();expect(button('Edit / batalkan invoice INV-NATIVE-1')).toBeUndefined();expect(container.textContent).not.toContain('Rp30')
 })
 it('renders source invoice/return/payment/balance and historical SKU without any financial writer',async()=>{
  await mount();await click(container.querySelector<HTMLElement>('[data-sale-id]')!)
  expect(container.textContent).toContain('Rp30');expect(container.textContent).toContain('HISTORICAL');expect(container.textContent).toContain('Jatuh tempo 2026-10-29')
  expect(container.textContent).toContain('Kondisi dokumen sekarang');expect(container.textContent).toContain('Saldo awal dan penyesuaian buku')
  const detail=container.querySelector('[aria-label="Rincian sumber piutang"]')!
  for(const label of ['Nilai invoice','Retur tercatat','Pembayaran tercatat','Sisa tagihan'])expect(detail.textContent).toContain(label)
  expect(mock.rpc.mock.calls.every(([name])=>name==='erp_cp7_get_sales_v1')).toBe(true)
 })
 it('keeps money above safe integer precision and does not suppress native invoice credit',async()=>{
  mock.rpc.mockImplementationOnce((_name,{p_query})=>{const d=fixture(p_query);Object.assign(d.page.rows[0].financial!,{gross_total:'9007199254740993.01',return_total:'0.00',net_total:'9007199254740993.01',paid_total:'0.00',open_balance:'9007199254740993.01'});return Promise.resolve({data:d,error:null})})
  await mount();expect(container.textContent).toContain('Rp9.007.199.254.740.993,01')
  mock.rpc.mockImplementationOnce((_name,{p_query})=>{const d=fixture(p_query);Object.assign(d.page.rows[0].financial!,{paid_total:'65.00',open_balance:'-5.00'});return Promise.resolve({data:d,error:null})})
  await click(button('Muat ulang piutang'));expect(container.textContent).toContain('Kredit pada invoice');expect(container.textContent).toContain('Rp-5')
 })
 it('never presents draft or cancelled totals as posted receivables',async()=>{
  await mount()
  for(const status of ['DRAFT','CANCELLED','REVERSED']){await chooseStatus(status);expect(container.textContent).not.toContain('Rp');await click(button('Cari piutang'));await click(container.querySelector<HTMLElement>('[data-sale-id]')!);expect(container.textContent).toContain('Dokumen ini belum/tidak menjadi piutang aktif.');expect(container.querySelector('[aria-label="Daftar sumber piutang"]')!.textContent).not.toContain('Rp')}
 })
 it('retires old source on search/status edits and refresh uses the entered filter with cleared selection',async()=>{
  await mount();await click(container.querySelector<HTMLElement>('[data-sale-id]')!);const count=mock.rpc.mock.calls.length
  await fill('Cari sumber piutang','Toko baru');expect(container.textContent).not.toContain('Rp');expect(container.querySelector('[data-sale-id]')).toBeNull();expect(mock.rpc.mock.calls).toHaveLength(count)
  await click(button('Muat ulang piutang'));expect(mock.rpc.mock.calls.at(-1)?.[1].p_query).toMatchObject({q:'Toko baru',sale_id:null,offset:0})
  await chooseStatus('POSTED');expect(container.textContent).not.toContain('Rp');await click(button('Muat ulang piutang'));expect(mock.rpc.mock.calls.at(-1)?.[1].p_query.status).toBe('POSTED')
 })
 it('does not repaint a pending previous query after the input has changed',async()=>{
  let resolveOld:((v:unknown)=>void)|null=null
  mock.rpc.mockImplementationOnce(()=>new Promise(resolve=>{resolveOld=resolve}))
  await mount();await fill('Cari sumber piutang','new query');await act(async()=>resolveOld!({data:fixture(),error:null}));await flush()
  expect(container.textContent).not.toContain('Rp');expect(container.querySelector('[data-sale-id]')).toBeNull()
 })
 it('rejects hidden financial fields, wrong selection, incomplete pages and mismatched status',async()=>{
  await mount()
  mock.rpc.mockResolvedValueOnce({data:{...fixture(),financial_captured:false},error:null});await click(button('Muat ulang piutang'));expect(container.textContent).not.toContain('Rp')
  const wrong=fixture({sale_id:id});mock.rpc.mockResolvedValueOnce({data:wrong,error:null});await click(button('Muat ulang piutang'));expect(container.textContent).toContain('Pilihan sumber piutang berubah')
  const page=fixture();page.page.total='2';mock.rpc.mockResolvedValueOnce({data:page,error:null});await click(button('Muat ulang piutang'));expect(container.textContent).not.toContain('Rp')
  await chooseStatus('POSTED');mock.rpc.mockResolvedValueOnce({data:fixture(),error:null});await click(button('Cari piutang'));expect(container.textContent).toContain('Pilihan sumber piutang berubah')
 })
 it('keeps complete document pagination and refetches the selected invoice on the next page',async()=>{
  mock.rpc.mockImplementation((_name,{p_query})=>{
   const d=fixture(p_query);d.page.total='26';d.page.offset=p_query.offset;d.page.next_offset=p_query.offset===0?25:null
   const row=d.page.rows[0]
   d.page.rows=p_query.offset===0?Array.from({length:25},(_,i)=>({...row,id:`11111111-1111-4111-8111-${String(i+1).padStart(12,'0')}`,number:'PAGE-'+(i+1)})):[{...row,id:'11111111-1111-4111-8111-000000000026',number:'PAGE-26'}]
   return Promise.resolve({data:d,error:null})
  })
  await mount();expect(container.querySelectorAll('[data-sale-id]')).toHaveLength(25);expect(container.textContent).toContain('Total 26 dokumen')
  await click(button('Piutang berikutnya'));expect(container.querySelectorAll('[data-sale-id]')).toHaveLength(1);expect(container.textContent).toContain('PAGE-26');expect(container.textContent).toContain('Total 26 dokumen')
  expect(mock.rpc.mock.calls.at(-1)?.[1].p_query.offset).toBe(25);expect(button('Piutang berikutnya').disabled).toBe(true)
  await click(button('Piutang sebelumnya'));expect(container.querySelectorAll('[data-sale-id]')).toHaveLength(25);expect(mock.rpc.mock.calls.at(-1)?.[1].p_query.offset).toBe(0)
 })
 it('an old actor response cannot replace the current actor source',async()=>{
  let resolveOld:((v:unknown)=>void)|null=null;mock.rpc.mockImplementationOnce(()=>new Promise(resolve=>{resolveOld=resolve}))
  await mount();const auth=structuredClone(mock.auth) as typeof recoveryIdentity;auth.identity.profile.id='new-actor';mock.auth=auth
  mock.rpc.mockImplementation(()=>{const d=fixture();d.page.rows[0].number='CURRENT-ACTOR';return Promise.resolve({data:d,error:null})})
  await mount();await act(async()=>resolveOld!({data:fixture(),error:null}));await flush()
  expect(container.textContent).toContain('CURRENT-ACTOR');expect(container.textContent).not.toContain('INV-NATIVE-1')
 })
 it('retires amounts after failed refresh and requires both current invoice and AR permissions',async()=>{
  await mount();mock.rpc.mockResolvedValueOnce({data:null,error:{message:'Hak sumber dicabut'}});await click(button('Muat ulang piutang'));expect(container.textContent).toContain('Hak sumber dicabut');expect(container.textContent).not.toContain('Rp')
  const auth=mock.auth as typeof recoveryIdentity,count=mock.rpc.mock.calls.length
  for(const permissions of [['sales.invoice.view'],['finance.ar.view']]){auth.identity.permissions=permissions;await mount();expect(container.textContent).toContain('Hak melihat piutang');expect(container.textContent).not.toContain('Rp');expect(mock.rpc.mock.calls).toHaveLength(count)}
 })
})
