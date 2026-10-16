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
// Owner D14-5 series fixtures: three sizes, one size, five sizes, plus a longer SKU that only contains SKU-3 as text.
const sized=(series:string,sizes:string[],n:number)=>sizes.map((size,i)=>({...stock,product_id:`${n}${i}${n}${i}${n}${i}${n}${i}-1111-4111-8111-111111111111`,product_sku:`${series}-${size}`,commercial_sku:series,size_code:size,available_qty:String(10+i)}))
const catalog=[stock,...sized('SKU-3',['31','32','33'],5),...sized('SKU-1',['27'],6),...sized('SKU-5',['30','31','32','33','34'],7),...sized('SKU-30',['40'],8)]
const stockRows=(q:Record<string,unknown>)=>q.q?catalog.filter(r=>r.commercial_sku.toLowerCase().includes(String(q.q).toLowerCase())):[stock]
const option=(q:Record<string,unknown>)=>{const rows=q.kind==='CUSTOMER'?[{id,code:'C01',name:'Toko A'}]:stockRows(q);return {contract_version:'cp7.sales-form-options.v1',kind:q.kind,physical_at:q.physical_at,location_id:q.location_id??null,availability_basis:'CURRENT_AVAILABLE_NOT_HISTORICAL_STOCK',rows,total:String(rows.length),offset:q.offset??0,limit:q.limit??25,next_offset:null}}
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
 it('splits dozens over one size series and reads 4/5/4 back as 1 lusin 1 potong (owner D14-5)',async()=>{
  const d=detail(),third='44444444-4444-4444-8444-444444444444';d.items.push({...d.items[1],id:third,product_id:third,product_sku:'PHYSICAL-3',size_code:'34',qty_pcs:'4'})
  await mount(d);const series=container.querySelector('[aria-label="Seri SKU-HIST · Vivo"]')!
  expect(series.textContent).toContain('3 ukuran (32/33/34)');expect(series.textContent).toContain('Total seri: 1 lusin 7 potong (19 PCS)')
  await fill('Jumlah invoice 1','4');await fill('Jumlah invoice 2','5');await fill('Jumlah invoice 3','4');expect(series.textContent).toContain('Total seri: 1 lusin 1 potong (13 PCS)')
  await fill('Lusin seri SKU-HIST · Vivo','1');await click(button('Bagi rata ke 3 ukuran seri SKU-HIST · Vivo'))
  expect(['1','2','3'].map(n=>input(`Jumlah invoice ${n}`).value)).toEqual(['4','4','4']);expect(series.textContent).toContain('Total seri: 1 lusin (12 PCS)');expect(input('Draft invoice sudah diperiksa').checked).toBe(false)
  await fill('Sisa potong seri SKU-HIST · Vivo','1');await click(button('Bagi rata ke 3 ukuran seri SKU-HIST · Vivo'))
  expect(series.querySelector('[role="alert"]')!.textContent).toBe('1 lusin 1 potong (13 PCS) tidak bisa dibagi rata ke 3 ukuran. Isi per ukuran, atau ubah jumlahnya.')
  expect(['1','2','3'].map(n=>input(`Jumlah invoice ${n}`).value)).toEqual(['4','4','4'])
 })
 it('picking one size adds the whole series at 1 lusin, a one-size SKU gets 12 PCS, and manual 3/5/4 reads 1 lusin (owner D14-5)',async()=>{
  await mount();const pick=async(q:string,n=0)=>{await fill('Cari barang draft',q);await click(button('Cari barang draft'));await click(container.querySelectorAll<HTMLElement>('[aria-label="Pilih barang invoice"] .cproc-receipt')[n])}
  await pick('SKU-3',1);const three=container.querySelector('[aria-label="Seri SKU-3 · Vivo"]')!
  expect(three.textContent).toContain('3 ukuran (31/32/33)');expect(['1','2','3'].map(n=>input(`Jumlah invoice ${n}`).value)).toEqual(['4','4','4']);expect(three.textContent).toContain('Total seri: 1 lusin (12 PCS)');expect(input('Lusin seri SKU-3 · Vivo').value).toBe('1')
  expect(three.querySelectorAll('article')).toHaveLength(3);expect(three.textContent).not.toContain('SKU-30')
  await fill('Jumlah invoice 1','3');await fill('Jumlah invoice 2','5');await fill('Jumlah invoice 3','4');expect(three.textContent).toContain('Total seri: 1 lusin (12 PCS)')
  await fill('Jumlah invoice 1','4');expect(three.textContent).toContain('Total seri: 1 lusin 1 potong (13 PCS)')
  await fill('Lusin seri SKU-3 · Vivo','2');await click(button('Bagi rata ke 3 ukuran seri SKU-3 · Vivo'));expect(['1','2','3'].map(n=>input(`Jumlah invoice ${n}`).value)).toEqual(['8','8','8']);expect(three.textContent).toContain('Total seri: 2 lusin (24 PCS)')
  await pick('SKU-1');const one=container.querySelector('[aria-label="Seri SKU-1 · Vivo"]')!
  expect(one.textContent).toContain('1 ukuran (27)');expect(input('Jumlah invoice 4').value).toBe('12');expect(one.textContent).toContain('Total seri: 1 lusin (12 PCS)')
  await fill('Lusin seri SKU-1 · Vivo','3');await fill('Sisa potong seri SKU-1 · Vivo','5');await click(button('Bagi rata ke 1 ukuran seri SKU-1 · Vivo'));expect(input('Jumlah invoice 4').value).toBe('41');expect(one.textContent).toContain('Total seri: 3 lusin 5 potong (41 PCS)')
  await pick('SKU-5');const five=container.querySelector('[aria-label="Seri SKU-5 · Vivo"]')!
  expect(['5','6','7','8','9'].map(n=>input(`Jumlah invoice ${n}`).value)).toEqual(['','','','','']);expect(five.querySelector('[role="alert"]')!.textContent).toBe('1 lusin (12 PCS) tidak bisa dibagi rata ke 5 ukuran. Isi per ukuran, atau ubah jumlahnya.')
  await pick('SKU-3');expect(container.querySelectorAll('[aria-label="Seri SKU-3 · Vivo"] article')).toHaveLength(3);expect(three.querySelector('[role="alert"]')!.textContent).toBe('Semua ukuran seri SKU-3 · Vivo yang ada stoknya sudah ada di invoice.')
  expect(['1','2','3'].map(n=>input(`Jumlah invoice ${n}`).value)).toEqual(['8','8','8'])
  const series=client.rpc.mock.calls.map(c=>c[1].p_query).filter(q=>q.kind==='STOCK'&&q.limit===100);expect(series.map(q=>q.q)).toEqual(['SKU-3','SKU-1','SKU-5','SKU-3']);expect(series.every(q=>q.location_id===id&&q.offset===0)).toBe(true)
  await fill('Jumlah invoice 1','11');expect(three.textContent).toContain('stok 10 PCS · melebihi stok')
 })
 it('adds nothing when the series cannot be read completely',async()=>{
  await mount();await fill('Cari barang draft','SKU-3');await click(button('Cari barang draft'))
  // Every page is a valid page of a longer list: after ten pages the series is still not complete.
  client.rpc.mockImplementation(async(_n,a)=>{const o=option(a.p_query);return {data:{...o,total:'5000',next_offset:a.p_query.offset+o.rows.length},error:null}})
  await click(container.querySelector<HTMLElement>('[aria-label="Pilih barang invoice"] .cproc-receipt')!)
  expect(client.rpc.mock.calls.filter(c=>c[1].p_query.limit===100)).toHaveLength(10)
  expect(container.querySelector('[aria-label="Seri SKU-3 · Vivo"]')).toBeNull();expect(container.textContent).toContain('Ukuran seri SKU-3 · Vivo belum terbaca semua. Cari dengan SKU yang lebih tepat.')
  client.rpc.mockImplementation(async(_n,a)=>({data:{...option(a.p_query),limit:25},error:null}))
  await click(container.querySelector<HTMLElement>('[aria-label="Pilih barang invoice"] .cproc-receipt')!)
  expect(container.querySelector('[aria-label="Seri SKU-3 · Vivo"]')).toBeNull();expect(container.textContent).toContain('Pilihan sumber berubah. Cari ulang sumber invoice.')
 })
 it('keeps immutable source IDs for duplicate SKU lines after quantity changes and deletion',async()=>{
  const d=detail();d.items[0].qty_pcs='5';d.items[1]={...d.items[1],product_id:d.items[0].product_id,qty_pcs:'10'}
  await act(async()=>root.render(<SalesDraftPanel initial={d} correction locked={false} stale={false} onSave={saved} onClose={()=>{}}/>));await flush()
  await fill('Jumlah invoice 2','6');await fill('Alasan simpan invoice','Jumlah kedua sebenarnya enam');await click(input('Pembetulan nota sudah diperiksa'));await click(button('Simpan pembetulan nota'))
  expect(saved.mock.calls[0][1].item_lineage).toEqual([d.items[0].id,d.items[1].id]);expect(saved.mock.calls[0][1].items.map((x:{qty_pcs:string})=>x.qty_pcs)).toEqual(['5','6'])
  await click(button('Hapus barang 1'));await click(input('Pembetulan nota sudah diperiksa'));await click(button('Simpan pembetulan nota'))
  expect(saved.mock.calls[1][1].item_lineage).toEqual([d.items[1].id]);expect(saved.mock.calls[1][1].items[0].qty_pcs).toBe('6')
 })
 it('keeps two brands with the same SKU number apart: picking Vivo adds only Vivo sizes (Astra ASTRA-C17-01)',async()=>{
  // ASTRA_UI_SERIES_MUST_PRESERVE_BRAND: Vivo/73001/32 and Widie/73001/32, 30 each; pick Vivo only.
  const vivo={...stock,product_id:'aaaaaaaa-1111-4111-8111-111111111111',product_sku:'V-73001-32',commercial_sku:'73001',size_code:'32',brand_name:'Vivo',available_qty:'30'}
  const widie={...vivo,product_id:'bbbbbbbb-1111-4111-8111-111111111111',product_sku:'W-73001-32',brand_name:'Widie'}
  client.rpc.mockImplementation(async(_n,a)=>{const q=a.p_query;const rows=q.kind==='CUSTOMER'?[{id,code:'C01',name:'Toko A'}]:[vivo,widie];return {data:{...option(q),rows,total:String(rows.length)},error:null}})
  await mount();await fill('Cari barang draft','73001');await click(button('Cari barang draft'))
  await click(container.querySelectorAll<HTMLElement>('[aria-label="Pilih barang invoice"] .cproc-receipt')[0])
  const v=container.querySelector('[aria-label="Seri 73001 · Vivo"]')!
  expect(v.textContent).toContain('1 ukuran (32)');expect(input('Jumlah invoice 1').value).toBe('12');expect(container.querySelector('[aria-label="Jumlah invoice 2"]')).toBeNull()
  expect(container.querySelector('[aria-label="Seri 73001 · Widie"]')).toBeNull()
  await click(button('Cari barang draft'));await click(container.querySelectorAll<HTMLElement>('[aria-label="Pilih barang invoice"] .cproc-receipt')[1])
  const w=container.querySelector('[aria-label="Seri 73001 · Widie"]')!
  expect(w.textContent).toContain('1 ukuran (32)');expect(input('Jumlah invoice 2').value).toBe('12');expect(v.textContent).toContain('1 ukuran (32)')
  await fill('Nomor draft invoice','INV-BRAND');await click(button('Cari pelanggan draft'));await click(container.querySelector<HTMLElement>('[aria-label="Pilih pelanggan invoice"] .cproc-receipt')!)
  await fill('Harga invoice 1','10');await fill('Harga invoice 2','10');await fill('Alasan simpan invoice','Dua merek dengan nomor SKU sama');await reviewed();await click(button('Simpan draft invoice'))
  expect(saved.mock.calls[0][1].items.map((x:{product_id:string;qty_pcs:string})=>[x.product_id,x.qty_pcs])).toEqual([[vivo.product_id,'12'],[widie.product_id,'12']])
 })
 it('cannot save while the sizes of a picked series are still loading, and the review is void (Astra ASTRA-C17-02)',async()=>{
  // ASTRA_UI_PENDING_SERIES_SAVE: a reviewed draft with two lines; picking a new three-size series holds the reader.
  const d=detail();await mount(d);await fill('Alasan simpan invoice','Draft lama sudah diperiksa');await reviewed()
  expect(button('Simpan draft invoice').disabled).toBe(false)
  let finish!:(r:unknown)=>void,held:Record<string,unknown>|null=null
  client.rpc.mockImplementation((_n,a)=>a.p_query.limit===100?new Promise(resolve=>{held=a.p_query;finish=resolve}):Promise.resolve({data:option(a.p_query),error:null}))
  await fill('Cari barang draft','SKU-3');await click(button('Cari barang draft'));await click(container.querySelectorAll<HTMLElement>('[aria-label="Pilih barang invoice"] .cproc-receipt')[0])
  expect(container.textContent).toContain('Memuat semua ukuran seri SKU-3 · Vivo');expect(button('Simpan draft invoice').disabled).toBe(true)
  expect(input('Draft invoice sudah diperiksa').checked).toBe(false);expect(input('Draft invoice sudah diperiksa').disabled).toBe(true)
  await click(button('Simpan draft invoice'));expect(saved).not.toHaveBeenCalled()
  await act(async()=>finish({data:option(held!),error:null}));await flush()
  expect(container.querySelectorAll('[aria-label="Seri SKU-3 · Vivo"] article')).toHaveLength(3);expect(input('Draft invoice sudah diperiksa').checked).toBe(false)
  for(const n of['3','4','5'])await fill(`Harga invoice ${n}`,'10')
  await reviewed();await click(button('Simpan draft invoice'));expect(saved.mock.calls[0][1].items).toHaveLength(5)
 })
})
