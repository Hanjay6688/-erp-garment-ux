// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SalesDraftPanel from './SalesDraftPanel'
import {parseSalesFormOptions,salesLineTotal,salesMoneyInput,type SalesRead} from './salesReadContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>recoveryIdentity}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',product='22222222-2222-4222-8222-222222222222',other='33333333-3333-4333-8333-333333333333',at='2026-09-29T03:00:03.123Z'
const stock={product_id:product,product_sku:'PHYSICAL-1',product_name:'Celana',commercial_sku:'SKU-HIST',size_code:'32',brand_name:'Vivo',location_id:id,location_name:'Gudang FG',available_qty:'30'}
const option=(q:Record<string,unknown>)=>({contract_version:'cp7.sales-form-options.v1',kind:q.kind,physical_at:q.physical_at,location_id:q.location_id??null,availability_basis:'CURRENT_AVAILABLE_NOT_HISTORICAL_STOCK',rows:q.kind==='CUSTOMER'?[{id,code:'C01',name:'Toko A'}]:[stock],total:'1',offset:0,limit:25,next_offset:null})
function detail():NonNullable<SalesRead['detail']>{return {id,number:'INV-1',customer_id:id,customer_name:'Toko A',location_id:id,location_name:'Gudang FG',physical_at:at,due_date:'2026-10-29',status:'DRAFT',row_version:'9007199254740993',notes:'Jangan hilangkan catatan',payment_terms:'Transfer setelah review',line_count:'2',qty_pcs:'15',reserved_qty:'15',returned_qty:'0',review_token:'a'.repeat(32),items:[{id:product,product_id:product,product_sku:'PHYSICAL-1',commercial_sku:'SKU-HIST',product_name:'Celana',size_code:'32',brand_name:'Vivo',qty_pcs:'13',notes:'Baris pertama',financial:{unit_price:'20.00',discount:'0.00',line_total:'260.00'}},{id:other,product_id:other,product_sku:'PHYSICAL-2',commercial_sku:'SKU-HIST',product_name:'Celana',size_code:'33',brand_name:'Vivo',qty_pcs:'2',notes:'Baris kedua',financial:{unit_price:'10.01',discount:'0.02',line_total:'20.00'}}]}}
let root:Root,container:HTMLDivElement;const saved=vi.fn()
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();saved.mockReset();container=document.createElement('div');document.body.append(container);root=createRoot(container);client.rpc.mockImplementation(async(_n,a)=>({data:option(a.p_query),error:null}))})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(initial:NonNullable<SalesRead['detail']>|null=null,stale=false){await act(async()=>root.render(<SalesDraftPanel initial={initial} locked={false} stale={stale} onSave={saved} onClose={()=>{}}/>));await flush()}
const input=(label:string)=>container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
async function fill(label:string,value:string){await act(async()=>{const e=input(label);Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
const button=(label:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===label)!
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
async function reviewed(){await click(input('Draft invoice sudah diperiksa'))}
describe('P11 complete draft form',()=>{
 it('keeps exact cents and integer quantities without accepting hidden rounding',()=>{expect(salesLineTotal('13','10,01','0,02')).toBe('130.11');expect(salesLineTotal('3','10.01','0.02')).toBe('30.01');expect(salesMoneyInput('10.001')).toBeNull();expect(salesLineTotal('1.5','20','0')).toBeNull();expect(salesLineTotal('1','2','3')).toBeNull();expect(salesLineTotal('1','0','0')).toBe('0.00')})
 it('rejects wrong source date, hidden cost and incomplete option pages',()=>{const q={kind:'STOCK',physical_at:at,location_id:id},o=option(q);expect(parseSalesFormOptions(o,'STOCK',at,id).rows).toHaveLength(1);expect(()=>parseSalesFormOptions(o,'STOCK','2026-09-30T00:00:00Z',id)).toThrow();expect(()=>parseSalesFormOptions({...o,total:'2'},'STOCK',at,id)).toThrow();expect(()=>parseSalesFormOptions({...o,rows:[{...stock,hpp:'10'}]},'STOCK',at,id)).toThrow()})
 it('selects real source IDs, preserves manual13 and only applies the dozen helper on request',async()=>{
  await mount();await fill('Nomor draft invoice','INV-NEW');await click(button('Cari pelanggan draft'));await click(container.querySelector<HTMLElement>('[aria-label="Pilih pelanggan invoice"] .cproc-receipt')!);await click(button('Cari barang draft'));await click(container.querySelector<HTMLElement>('[aria-label="Pilih barang invoice"] .cproc-receipt')!)
  await fill('Jumlah invoice 1','13');await fill('Harga invoice 1','10,01');await fill('Potongan invoice 1','0,02');await fill('Lusin invoice 1','2');await fill('Sisa PCS invoice 1','0');expect(input('Jumlah invoice 1').value).toBe('13')
  await fill('Alasan simpan invoice','Semua data diperiksa');await reviewed();await click(button('Simpan draft invoice'));expect(saved).toHaveBeenCalledTimes(1);const [action,p,version]=saved.mock.calls[0];expect(action).toBe('CREATE');expect(version).toBeNull();expect(p.customer_id).toBe(id);expect(p.source_location_id).toBe(id);expect(p.items[0]).toEqual({product_id:product,qty_pcs:'13',unit_price_snapshot:'10.01',discount_amount:'0.02',notes:null})
  await click(button('Terapkan lusin baris 1'));expect(input('Jumlah invoice 1').value).toBe('24');expect(input('Draft invoice sudah diperiksa').checked).toBe(false)
 })
 it('edits one quantity without losing exact time, version, second price or notes',async()=>{
  const d=detail();await mount(d);await fill('Jumlah invoice 1','5');await fill('Alasan simpan invoice','Koreksi jumlah menjadi5');await reviewed();await click(button('Simpan draft invoice'))
  const [action,p,version]=saved.mock.calls[0];expect(action).toBe('EDIT');expect(version).toBe(d.row_version);expect(p.sale_date).toBe(at);expect(p.review_token).toBe(d.review_token);expect(p.due_date).toBe(d.due_date);expect(p.payment_terms).toBe(d.payment_terms);expect(p.notes).toBe(d.notes);expect(p.items[1]).toEqual({product_id:other,qty_pcs:'2',unit_price_snapshot:'10.01',discount_amount:'0.02',notes:'Baris kedua'});expect(container.querySelector('.cproc-total')?.textContent).toContain('Rp120')
 })
 it('retires late source results after the invoice date changes',async()=>{
  let finish!:(r:unknown)=>void;client.rpc.mockImplementation((_n,a)=>new Promise(resolve=>{finish=r=>resolve(r);void a}));await mount();await click(button('Cari barang draft'));const query=client.rpc.mock.calls[0][1].p_query
  await fill('Waktu draft invoice WIB','2026-09-28T12:00');await act(async()=>finish({data:option(query),error:null}));await flush();expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0)
 })
 it('keeps entered draft but blocks saving when its reviewed source is stale',async()=>{
  const d=detail();await mount(d);await fill('Jumlah invoice 1','5');await fill('Alasan simpan invoice','Alasan masih dipertahankan');await reviewed();await mount(d,true);expect(input('Jumlah invoice 1').value).toBe('5');expect(input('Alasan simpan invoice').value).toBe('Alasan masih dipertahankan');await click(button('Simpan draft invoice'));expect(saved).not.toHaveBeenCalled();expect(container.textContent).toContain('Dokumen berubah')
 })
 it('keeps immutable source IDs for duplicate SKU lines after quantity changes and deletion',async()=>{
  const d=detail();d.items[0].qty_pcs='5';d.items[1]={...d.items[1],product_id:d.items[0].product_id,qty_pcs:'10'}
  await act(async()=>root.render(<SalesDraftPanel initial={d} correction locked={false} stale={false} onSave={saved} onClose={()=>{}}/>));await flush()
  await fill('Jumlah invoice 2','6');await fill('Alasan simpan invoice','Jumlah kedua sebenarnya enam');await click(input('Pembetulan nota sudah diperiksa'));await click(button('Simpan pembetulan nota'))
  expect(saved.mock.calls[0][1].item_lineage).toEqual([d.items[0].id,d.items[1].id]);expect(saved.mock.calls[0][1].items.map((x:{qty_pcs:string})=>x.qty_pcs)).toEqual(['5','6'])
  await click(button('Hapus barang 1'));await click(input('Pembetulan nota sudah diperiksa'));await click(button('Simpan pembetulan nota'))
  expect(saved.mock.calls[1][1].item_lineage).toEqual([d.items[1].id]);expect(saved.mock.calls[1][1].items[0].qty_pcs).toBe('6')
 })
})
