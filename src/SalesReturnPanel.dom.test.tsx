// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SalesReturnPanel from './SalesReturnPanel'
import {parseSalesReturns,salesReturnTotal,type SalesReturnKind} from './salesReturnContract'
import {parseSalesOutcome,type SalesRead} from './salesReadContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
const alloc2='66666666-6666-4666-8666-666666666666'
const id='11111111-1111-4111-8111-111111111111',alloc='22222222-2222-4222-8222-222222222222',destination='33333333-3333-4333-8333-333333333333',returnId='44444444-4444-4444-8444-444444444444',request='55555555-5555-4555-8555-555555555555'
const source:NonNullable<SalesRead['detail']>={id,number:'INV-1',customer_id:id,customer_name:'Toko A',location_id:id,location_name:'Gudang asal',physical_at:'2026-09-29T03:00:00Z',due_date:null,status:'POSTED',row_version:'9007199254740993',notes:null,payment_terms:null,line_count:'1',qty_pcs:'4',reserved_qty:'0',returned_qty:'0',review_token:'a'.repeat(32),items:[],financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'80.00',return_total:'0.00',net_total:'80.00',paid_total:'0.00',open_balance:'80.00'}}
const allocation={allocation_id:alloc,sale_item_id:id,product_id:id,product_sku:'PHYS-31',commercial_sku:'JEANS-31',product_name:'Jeans',size_code:'31',lot_id:id,lot_number:'LOT-1',source_location_name:'Gudang asal',allocated_qty:'2',returned_qty:'0',remaining_qty:'2',sale_item_qty:'4',sale_item_net:'80.00'}
const record={id:returnId,number:'RET-1',physical_at:'2026-09-29T04:00:00Z',status:'POSTED',notes:'Catatan utuh',line_count:'1',items:[{id,allocation_id:alloc,product_sku:'PHYS-31',lot_number:'LOT-1',location_id:destination,location_name:'Gudang lain',qty_pcs:'1',quality_grade:'GRADE_B',refund_amount:'20.00',notes:'Cacat terverifikasi'}]}
const response=(kind:SalesReturnKind,history=false)=>{const rows=kind==='ALLOCATIONS'?[allocation,{...allocation,allocation_id:alloc2}]:kind==='LOCATIONS'?[{id,name:'Gudang asal'},{id:destination,name:'Gudang lain'}]:history?[record]:[];return {contract_version:'cp7.sales-returns.v1',sale_id:id,row_version:source.row_version,review_token:source.review_token,kind,page:{rows,total:String(rows.length),offset:0,limit:25,next_offset:null}}}
let root:Root,container:HTMLDivElement;const saved=vi.fn()
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset();saved.mockReset();const auth=structuredClone(recoveryIdentity);auth.identity.permissions.push('sales.invoice.view','finance.ar.view','sales.return.view','sales.return.create','sales.return.post','sales.return.reverse');mock.auth=auth;container=document.createElement('div');document.body.append(container);root=createRoot(container);mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:response(p_query.kind),error:null}))})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(stale=false){await act(async()=>root.render(<SalesReturnPanel source={source} locked={false} stale={stale} onSave={saved} onClose={()=>{}}/>));await flush()}
const input=(label:string)=>container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
async function fill(label:string,value:string){await act(async()=>{const e=input(label);Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function select(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLSelectElement>(`[aria-label="${label}"]`)!;e.value=value;e.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
async function add(location='Gudang lain'){await click(button(location));await click(container.querySelector<HTMLElement>('[aria-label="Pilih alokasi retur"] .cproc-receipt:not(:disabled)')!)}
async function header(){await fill('Nomor retur pelanggan','RET-NEW');await fill('Waktu retur pelanggan WIB','2026-09-29T12:31')}
describe('P11 selected-allocation physical return',()=>{
 it('retains entered lines and review across owning history renders with the same read ticket callbacks',async()=>{
  const ticket={sequence:1,scope:'owning',signature:'source' as string|null,session:{}},currentReadTicket=()=>ticket,isReadCurrent=(t:typeof ticket)=>t===ticket,inputs={},onInvalid=vi.fn()
  const render=async()=>{await act(async()=>root.render(<SalesReturnPanel source={source} locked={false} stale={false} onSave={saved} onClose={()=>{}} inputs={inputs} onInvalid={onInvalid} readFence={{currentReadTicket,isReadCurrent}}/>));await flush()}
  await render();await header();await add();await fill('Jumlah retur 1','1');await fill('Nilai retur 1','20');await click(input('Retur pelanggan sudah diperiksa'));expect(input('Retur pelanggan sudah diperiksa').checked).toBe(true);const reads=mock.rpc.mock.calls.length
  await render();expect(mock.rpc).toHaveBeenCalledTimes(reads);expect(input('Jumlah retur 1').value).toBe('1');expect(input('Nilai retur 1').value).toBe('20');expect(input('Retur pelanggan sudah diperiksa').checked).toBe(true);expect(button('Catat retur pelanggan').disabled).toBe(false);expect(saved).not.toHaveBeenCalled();expect(onInvalid).not.toHaveBeenCalled()
 })
 it('filters the loaded return page without changing physical lines, source order or dispatching a writer',async()=>{
  const rows=[{...record,number:'RET-10'},{...record,id:'77777777-7777-4777-8777-777777777777',number:'RET-2',status:'REVERSED',items:[{...record.items[0],id:'88888888-8888-4888-8888-888888888888'}]}]
  const original=structuredClone(rows);mock.rpc.mockImplementation((_rpc,{p_query})=>{const r=response(p_query.kind);if(p_query.kind==='RETURNS'){r.page.rows=rows;r.page.total='2'}return Promise.resolve({data:r,error:null})});await mount();await fill('Nomor retur pelanggan','RET-OWN');const reads=mock.rpc.mock.calls.length
  const numbers=()=>[...container.querySelectorAll('[aria-label="Riwayat retur invoice"] .cproc-item h4')].map(e=>e.textContent?.split(' · ')[0])
  expect(numbers()).toEqual(['RET-10','RET-2']);await select('Urutkan halaman riwayat retur invoice','LABEL_ASC');expect(numbers()).toEqual(['RET-2','RET-10']);await select('Status retur di halaman ini','POSTED');expect(numbers()).toEqual(['RET-10'])
  await fill('Cari riwayat retur di halaman ini','LOT-1');await click(button('Cari riwayat retur di halaman ini'));expect(numbers()).toEqual(['RET-10']);expect(container.textContent).toContain('Menampilkan 1 dari 2 retur pada halaman ini');expect(input('Nomor retur pelanggan').value).toBe('RET-OWN')
  await click(button('Semua retur di halaman ini'));expect(numbers()).toEqual(['RET-10','RET-2']);expect(mock.rpc).toHaveBeenCalledTimes(reads);expect(saved).not.toHaveBeenCalled();expect(rows).toEqual(original)
 })
 it('rejects stale source, incomplete history, impossible capacity and injected cost',()=>{
  expect(parseSalesReturns(response('ALLOCATIONS'),'ALLOCATIONS',source).page.total).toBe('2')
  expect(()=>parseSalesReturns({...response('ALLOCATIONS'),review_token:'b'.repeat(32)},'ALLOCATIONS',source)).toThrow()
  const short=response('RETURNS',true);short.page.rows=[{...record,line_count:'2'}];expect(()=>parseSalesReturns(short,'RETURNS',source)).toThrow()
  const bad=response('ALLOCATIONS');bad.page.rows=[{...allocation,remaining_qty:'5'}];expect(()=>parseSalesReturns(bad,'ALLOCATIONS',source)).toThrow()
  expect(()=>parseSalesReturns({...response('ALLOCATIONS'),unit_hpp:'0'},'ALLOCATIONS',source)).toThrow()
  expect(salesReturnTotal(['9007199254740993.01','0,02'])).toBe('9007199254740993.03');expect(salesReturnTotal([''])).toBeNull()
 })
 it('binds separate grades and destinations to original allocations without client HPP',async()=>{
  await mount();await header();await add();expect(input('Jumlah retur 1').value).toBe('');expect(input('Nilai retur 1').value).toBe('');await fill('Jumlah retur 1','1');await fill('Nilai retur 1','20,01');await select('Grade retur 1','GRADE_B');await fill('Catatan barang retur 1','Cacat tercatat')
  await add('Gudang asal');await fill('Jumlah retur 2','2');await fill('Nilai retur 2','39,99');await select('Grade retur 2','HOLD');await fill('Catatan retur pelanggan','Dua gudang dan kondisi diperiksa');await click(input('Retur pelanggan sudah diperiksa'));await click(button('Catat retur pelanggan'))
  expect(saved).toHaveBeenCalledOnce();expect(saved.mock.calls[0]).toEqual(['RETURN',{sale_id:id,review_token:source.review_token,change_reason:'Barang retur dan invoice sudah diperiksa',return_number:'RET-NEW',physical_at:'2026-09-29T05:31:00.000Z',notes:'Dua gudang dan kondisi diperiksa',items:[{allocation_id:alloc,location_id:destination,qty_pcs:'1',quality_grade:'GRADE_B',refund_amount:'20.01',notes:'Cacat tercatat'},{allocation_id:alloc2,location_id:id,qty_pcs:'2',quality_grade:'HOLD',refund_amount:'39.99',notes:null}]},source.row_version])
 })
 it('prevents repeating the selected allocation, enforces its cap and requires explicit refund even at zero',async()=>{
  await mount();await header();await add();await fill('Jumlah retur 1','3');await fill('Nilai retur 1','0');await add();await fill('Jumlah retur 2','1');expect(container.querySelector<HTMLButtonElement>('[aria-label="Pilih alokasi retur"] .cproc-receipt')!.disabled).toBe(true);await fill('Nilai retur 2','20');await click(input('Retur pelanggan sudah diperiksa'));expect(button('Catat retur pelanggan').disabled).toBe(true)
  await fill('Jumlah retur 1','2');expect(input('Retur pelanggan sudah diperiksa').checked).toBe(false);await fill('Nilai retur 2','20.001');await click(input('Retur pelanggan sudah diperiksa'));expect(button('Catat retur pelanggan').disabled).toBe(true)
  await fill('Nilai retur 2','0');await click(input('Retur pelanggan sudah diperiksa'));expect(button('Catat retur pelanggan').disabled).toBe(false);await click(button('Catat retur pelanggan'));expect(saved.mock.calls[0][1].items.map((x:{refund_amount:string})=>x.refund_amount)).toEqual(['0','0'])
 })
 it('inverse requires selecting a posted original return and a new reason',async()=>{
  mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:response(p_query.kind,true),error:null}));await mount();expect(container.textContent).toContain('Grade B → Gudang lain');await click(button('Koreksi retur RET-1'));expect(input('Alasan tindakan retur').value).toBe('');await click(input('Retur pelanggan sudah diperiksa'));expect(button('Batalkan retur tercatat').disabled).toBe(true)
  await fill('Alasan tindakan retur','Barang salah diterima');await click(input('Retur pelanggan sudah diperiksa'));await click(button('Batalkan retur tercatat'));expect(saved).toHaveBeenCalledWith('RETURN_REVERSE',{sale_id:id,review_token:source.review_token,return_id:returnId,change_reason:'Barang salah diterima'},source.row_version)
 })
 it('keeps entered values but locks effects on failed refresh and stale invoice',async()=>{
  await mount();await header();await add();await fill('Jumlah retur 1','2');await fill('Nilai retur 1','40');mock.rpc.mockResolvedValue({data:null,error:{message:'Sumber retur tidak tersedia'}});await click(button('Muat ulang sumber retur'));expect(input('Jumlah retur 1').value).toBe('2');expect(input('Nilai retur 1').value).toBe('40');expect(container.querySelector('fieldset')!.disabled).toBe(true);expect(container.textContent).toContain('Sumber retur tidak tersedia');await mount(true);expect(input('Jumlah retur 1').value).toBe('2');expect(saved).not.toHaveBeenCalled()
 })
 it('keeps history visible without offering unauthorized write or legacy-only inverse',async()=>{
  const auth=mock.auth as typeof recoveryIdentity;auth.identity.permissions=auth.identity.permissions.filter(p=>p!=='sales.return.post');auth.identity.profile.role='STAFF';mock.rpc.mockImplementation((_rpc,{p_query})=>Promise.resolve({data:response(p_query.kind,true),error:null}));await mount();expect(container.textContent).toContain('RET-1');expect(container.querySelector('form[aria-label="Catat retur pelanggan"]')).toBeNull();expect(input('Nomor retur pelanggan')).toBeNull();expect(input('Retur pelanggan sudah diperiksa')).toBeNull();expect(button('Catat retur pelanggan')).toBeUndefined();expect(button('Koreksi retur RET-1')).toBeUndefined();expect(container.querySelector('form[aria-label="Cari, browse, urutkan dan filter riwayat retur invoice"]')).not.toBeNull();const reads=mock.rpc.mock.calls.length;await fill('Cari riwayat retur di halaman ini','RET-1');await click(button('Cari riwayat retur di halaman ini'));expect(container.textContent).toContain('RET-1');expect(mock.rpc).toHaveBeenCalledTimes(reads);expect(saved).not.toHaveBeenCalled()
 })
 it('binds recovery to exact return identity and refuses false invoice reversal',()=>{
  const r={contract_version:'cp7.sales-outcome.v1',kind:'COMMITTED_OUTCOME',action:'RETURN_REVERSE',request_id:request,sale_id:id,status:'POSTED',row_version:'9007199254740994',return_id:returnId,return_status:'REVERSED'}
  expect(parseSalesOutcome(r,request,'RETURN_REVERSE',id,undefined,returnId).return_id).toBe(returnId);expect(()=>parseSalesOutcome(r,request,'RETURN_REVERSE',id,undefined,destination)).toThrow();expect(()=>parseSalesOutcome({...r,return_status:'POSTED'},request,'RETURN_REVERSE',id,undefined,returnId)).toThrow()
  const sale={contract_version:r.contract_version,kind:r.kind,action:'SALE_REVERSE',request_id:request,sale_id:id,status:'REVERSED',row_version:r.row_version};expect(parseSalesOutcome(sale,request,'SALE_REVERSE',id).status).toBe('REVERSED');expect(()=>parseSalesOutcome({...sale,status:'POSTED'},request,'SALE_REVERSE',id)).toThrow()
 })
})
