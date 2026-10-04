// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SalesReturnCorrectionPanel from './SalesReturnCorrectionPanel'
import {parseReturnCorrectionWorkspace,parseReturnCorrectionOutcome,returnCorrectionCents,type ReturnCorrectionWorkspace} from './salesReturnCorrectionContract'
import type {SalesRead} from './salesReadContract'
import type {SalesReturnLocation,SalesReturnRead} from './salesReturnContract'
import type {RetainedFormInput} from './useRetainedFormInput'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
// Declared UI stand-in; real source routing is qualified in Native browsers.
vi.mock('./TransactionSourceNavigation',()=>({default:({sourceId,label}:{sourceId:string;label:string})=><button data-source-id={sourceId}>{label}</button>}))
const sale='11111111-1111-4111-8111-111111111111',ret='22222222-2222-4222-8222-222222222222',allocation='33333333-3333-4333-8333-333333333333',location='44444444-4444-4444-8444-444444444444',old='55555555-5555-4555-8555-555555555555',request='66666666-6666-4666-8666-666666666666',other='77777777-7777-4777-8777-777777777777'
const source:NonNullable<SalesRead['detail']>={id:sale,number:'INV-RET',customer_id:sale,customer_name:'Toko',location_id:location,location_name:'FG',physical_at:'2025-09-28T03:00:00Z',due_date:null,status:'POSTED',row_version:'9007199254740993',notes:null,payment_terms:null,line_count:'1',qty_pcs:'4',reserved_qty:'0',returned_qty:'2',review_token:'a'.repeat(32),items:[],financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'80.00',return_total:'40.00',net_total:'40.00',paid_total:'0.00',open_balance:'40.00'}}
const document={id:ret,sale_id:sale,number:'RET-1',physical_at:'2025-09-28T04:00:59.123456+00:00',status:'POSTED' as const,notes:'Catatan asli',items:[{id:ret,allocation_id:allocation,product_id:sale,product_sku:'JEANS-31',lot_id:location,lot_number:'LOT-1',location_id:location,location_name:'FG',qty_pcs:'2',quality_grade:'GRADE_A' as const,refund_amount:'40.00',notes:'Barang asal'}]}
const choice={allocation_id:allocation,sale_item_id:sale,product_id:sale,product_sku:'JEANS-31',product_name:'Jeans',size_code:'31',lot_id:location,lot_number:'LOT-1',source_location_name:'FG',allocated_qty:'4',peer_returned_qty:'0',replacement_capacity:'4',sale_item_qty:'4',sale_item_net:'80.00'}
const link={id:request,original_id:old,replacement_id:ret,sale_id:sale,actor_scope_id:sale,request_id:request,reason:'Pemeriksaan retur awal',recorded_at:'2026-09-29T04:00:00Z',time_restatement:null}
const response=():ReturnCorrectionWorkspace=>({contract_version:'cp7.sales-return-correction-workspace.v1',read_at:'2026-09-29T04:00:00Z',source:{sale_id:sale,row_version:source.row_version,review_token:source.review_token!},document:structuredClone(document),return_review_token:'b'.repeat(32),financial:structuredClone(source.financial!),eligible:true,can_correct:true,allocations:{rows:[structuredClone(choice)],total:'1',offset:0,limit:25,next_offset:null},current_allocations:[structuredClone(choice)],previous:null,next:null,production_go:false})
const locations:SalesReturnRead<SalesReturnLocation>={contract_version:'cp7.sales-returns.v1',sale_id:sale,row_version:source.row_version,review_token:source.review_token!,kind:'LOCATIONS',page:{rows:[{id:location,name:'FG'}],total:'1',offset:0,limit:25,next_offset:null}}
let root:Root,container:HTMLDivElement,inputs:RetainedFormInput,ready:boolean,key:number,currentTicket:typeof ticket
const saved=vi.fn(),invalid=vi.fn(),ticket:{sequence:number;scope:string;signature:string|null;session:object}={sequence:1,scope:'test',signature:'signature',session:{}}
const fence={currentReadTicket:()=>ready?currentTicket:null,isReadCurrent:(t:typeof ticket)=>ready&&t===currentTicket}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset();saved.mockReset();invalid.mockReset();ready=true;currentTicket=ticket;key=0;inputs={};const a=structuredClone(recoveryIdentity);a.identity.profile.role='OWNER';a.identity.permissions.push('sales.invoice.view','finance.ar.view','sales.return.view','sales.return.create','sales.return.post','sales.return.reverse','finance.hpp.view');mock.auth=a;mock.rpc.mockResolvedValue({data:response(),error:null});container=globalThis.document.createElement('div');globalThis.document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(edit=true,locked=false,stale=false){await act(async()=>root.render(<SalesReturnCorrectionPanel key={key} source={source} returnId={ret} number="RET-1" initialEdit={edit} locked={locked} stale={stale} inputs={inputs} locations={locations} readFence={fence} onInvalid={invalid} onClose={()=>{}} onSave={saved} onLocationSearch={()=>{}} onLocationPage={()=>{}}/>));await flush()}
const input=(label:string)=>container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
async function fill(label:string,value:string){await act(async()=>{const e=input(label);Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
async function review(){await fill('Alasan pembetulan retur','Barang dan invoice diperiksa ulang');await click(input('Pembetulan retur sudah diperiksa'))}
describe('return correction source boundaries and declared UI stand-ins',()=>{
 it('emits one reviewed replacement bound to original allocation and exact microseconds',async()=>{
  await mount();await fill('Jumlah pembetulan retur 1','1');await fill('Nilai pembetulan retur 1','20,01');await review();expect(input('Pembetulan retur sudah diperiksa').checked).toBe(true);await click(button('Simpan pembetulan retur'))
  expect(saved).toHaveBeenCalledOnce();expect(saved).toHaveBeenCalledWith('RETURN_CORRECT',{sale_id:sale,return_id:ret,review_token:source.review_token,return_review_token:'b'.repeat(32),change_reason:'Barang dan invoice diperiksa ulang',replacement:{physical_at:document.physical_at,notes:'Catatan asli',items:[{allocation_id:allocation,location_id:location,qty_pcs:'1',quality_grade:'GRADE_A',refund_amount:'20.01',notes:'Barang asal'}]}},source.row_version);expect(new Set(mock.rpc.mock.calls.map(c=>c[0]))).toEqual(new Set(['erp_cp7_get_sales_return_correction_v1']))
 })
 it('refuses unchanged fields, excess capacity, sub-cent money and excess paid refund',async()=>{
  await mount();await review();expect(button('Simpan pembetulan retur').disabled).toBe(true);await fill('Jumlah pembetulan retur 1','5');await review();expect(button('Simpan pembetulan retur').disabled).toBe(true);await fill('Jumlah pembetulan retur 1','3');await fill('Nilai pembetulan retur 1','20.001');await review();expect(button('Simpan pembetulan retur').disabled).toBe(true)
  const w=response();w.financial.paid_total='40.00';w.financial.open_balance='0.00';mock.rpc.mockResolvedValue({data:w,error:null});await click(button('Muat ulang pembetulan retur'));await fill('Nilai pembetulan retur 1','40.01');await review();expect(button('Simpan pembetulan retur').disabled).toBe(true);await fill('Nilai pembetulan retur 1','40');await review();expect(button('Simpan pembetulan retur').disabled).toBe(false);expect(saved).not.toHaveBeenCalled()
 })
 it('changes physical time only after an explicit WIB edit',async()=>{
  await mount();await fill('Waktu pembetulan retur WIB','2025-09-29T12:31');await review();await click(button('Simpan pembetulan retur'));expect(saved.mock.calls[0][1].replacement.physical_at).toBe('2025-09-29T05:31:00.000Z')
 })
 it('restores actual prior content with a fresh reason and its exact microseconds',async()=>{
  const w=response();w.previous={link,document:{...structuredClone(document),id:old,number:'RET-OLD',status:'REVERSED',physical_at:'2025-09-28T04:01:59.654321+00:00',items:[{...document.items[0],qty_pcs:'3',refund_amount:'60.00'}]}};mock.rpc.mockResolvedValue({data:w,error:null});await mount(false);expect(container.querySelector('form')).toBeNull();await click(button('Pulihkan isi retur sebelum pembetulan'));expect(input('Jumlah pembetulan retur 1').value).toBe('3');expect(input('Alasan pembetulan retur').value).toBe('');expect(button('Simpan pembetulan retur').disabled).toBe(true);await review();await click(button('Simpan pembetulan retur'));expect(saved.mock.calls[0][1].return_id).toBe(ret);expect(saved.mock.calls[0][1].replacement.physical_at).toBe(w.previous.document.physical_at)
 })
 it('retires a failed current read while retaining only operator input across remount',async()=>{
  await mount();await fill('Jumlah pembetulan retur 1','1');await fill('Nilai pembetulan retur 1','20');await fill('Alasan pembetulan retur','Catatan operator tidak hilang');mock.rpc.mockResolvedValue({data:null,error:{message:'Sumber retur gagal dimuat'}});await click(button('Muat ulang pembetulan retur'));expect(invalid).toHaveBeenCalledWith('Sumber retur gagal dimuat');expect(container.querySelector('form')).toBeNull()
  ++key;mock.rpc.mockResolvedValue({data:response(),error:null});await mount();expect(input('Jumlah pembetulan retur 1').value).toBe('1');expect(input('Nilai pembetulan retur 1').value).toBe('20');expect(input('Alasan pembetulan retur').value).toBe('Catatan operator tidak hilang');expect(input('Pembetulan retur sudah diperiksa').checked).toBe(false);expect(JSON.stringify(inputs)).not.toMatch(/replacement_capacity|current_allocations|return_review_token|review_ticket/);expect(saved).not.toHaveBeenCalled()
 })
 it('ignores late facts after the owning invoice ticket is retired',async()=>{
  let resolve!:(v:{data:ReturnCorrectionWorkspace;error:null})=>void;mock.rpc.mockImplementation(()=>new Promise(r=>{resolve=r}));await mount();ready=false;await act(async()=>resolve({data:response(),error:null}));await flush();expect(container.querySelector('form')).toBeNull();expect(container.textContent).not.toContain('Maksimum pengganti');expect(invalid).not.toHaveBeenCalled();expect(saved).not.toHaveBeenCalled()
 })
 it('does not start a new leaf read without a current owning invoice',async()=>{
  ready=false;await mount();expect(mock.rpc).not.toHaveBeenCalled();expect(container.querySelector('form')).toBeNull();expect(container.textContent).toContain('Muat ulang invoice');expect(saved).not.toHaveBeenCalled()
 })
 it('requires a fresh leaf read when the owning invoice ticket changes even with equal header fields',async()=>{
  await mount();await fill('Jumlah pembetulan retur 1','1');await fill('Nilai pembetulan retur 1','20');await review();expect(button('Simpan pembetulan retur').disabled).toBe(false);const reads=mock.rpc.mock.calls.length
  currentTicket={...ticket,sequence:2};await mount();expect(mock.rpc).toHaveBeenCalledTimes(reads);expect(button('Simpan pembetulan retur').disabled).toBe(true);expect(container.textContent).toContain('Muat ulang pembetulan retur sebelum melanjutkan');await click(button('Simpan pembetulan retur'));expect(saved).not.toHaveBeenCalled()
  await click(button('Muat ulang pembetulan retur'));expect(input('Jumlah pembetulan retur 1').value).toBe('1');expect(input('Pembetulan retur sudah diperiksa').checked).toBe(false);await review();expect(button('Simpan pembetulan retur').disabled).toBe(false)
 })
 it('requires selected retained allocations to be loaded again before a writer is enabled',async()=>{
  inputs[`return.${sale}.${ret}.lines`]=[{key:'own-1',allocation_id:other,location_id:location,qty:'1',grade:'GRADE_A',refund:'20',notes:''}];await mount();await review();expect(container.textContent).toContain('Cari SKU atau lot');expect(button('Simpan pembetulan retur').disabled).toBe(true);expect(saved).not.toHaveBeenCalled()
 })
 it('shows history while denying absent permission and locks stale or pending writes',async()=>{
  await mount();await fill('Jumlah pembetulan retur 1','1');await review();await mount(true,true);expect(button('Simpan pembetulan retur').disabled).toBe(true);await mount(true,false,true);expect(button('Simpan pembetulan retur').disabled).toBe(true)
  const a=mock.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.hpp.view');++key;const w=response();w.can_correct=false;mock.rpc.mockResolvedValue({data:w,error:null});await mount(false);expect(container.textContent).toContain('RET-1');expect(container.querySelector('form')).toBeNull();expect(button('Edit retur tercatat')).toBeUndefined();expect(saved).not.toHaveBeenCalled()
 })
 it('rejects stale parents, injected cost, missing physical lines and invented capacity',()=>{
  const w=response();expect(parseReturnCorrectionWorkspace(w,source,ret).document.id).toBe(ret);expect(()=>parseReturnCorrectionWorkspace({...w,unit_hpp:'0'},source,ret)).toThrow();expect(()=>parseReturnCorrectionWorkspace({...w,source:{...w.source,row_version:'1'}},source,ret)).toThrow();expect(()=>parseReturnCorrectionWorkspace({...w,document:{...w.document,items:[]}},source,ret)).toThrow();expect(()=>parseReturnCorrectionWorkspace({...w,current_allocations:[{...choice,replacement_capacity:'5'}]},source,ret)).toThrow();expect(()=>parseReturnCorrectionWorkspace({...w,financial:{...w.financial,open_balance:'1.00'}},source,ret)).toThrow()
 })
 it('accepts only the exact committed original, request and actual replacement page',()=>{
  const result={contract_version:'cp7.sales-return-correction.v1',kind:'COMMITTED_OUTCOME',action:'RETURN_CORRECT',request_id:request,sale_id:sale,row_version:'9007199254740994',status:'POSTED',original_return_id:old,original_return_status:'REVERSED',return_id:ret,return_status:'POSTED',return_page_offset:25,link,production_go:false};expect(parseReturnCorrectionOutcome(result,request,sale,old).return_page_offset).toBe(25);expect(()=>parseReturnCorrectionOutcome(result,request,sale,other)).toThrow();expect(()=>parseReturnCorrectionOutcome({...result,return_page_offset:1},request,sale,old)).toThrow();expect(()=>parseReturnCorrectionOutcome({...result,link:{...link,request_id:other}},request,sale,old)).toThrow();expect(()=>parseReturnCorrectionOutcome({...result,stock_after:'999'},request,sale,old)).toThrow()
 })
 it('keeps large aggregate Native cents exact without floating point',()=>{
  expect(returnCorrectionCents('9007199254740993.01')).toBe(900719925474099301n);expect(returnCorrectionCents('99999999999999999999.99')).toBe(9999999999999999999999n);expect(()=>returnCorrectionCents('20.001')).toThrow()
 })
})
