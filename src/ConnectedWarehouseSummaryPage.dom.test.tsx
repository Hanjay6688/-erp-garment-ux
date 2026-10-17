// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedWarehouseSummaryPage from './ConnectedWarehouseSummaryPage'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {ATTENTION_RULES,summaryAccess,type AccessoryLine,type Attention,type FgPart,type MaterialLine,type SummaryValuation,type WarehouseMenu,type WarehouseSummary} from './warehouseSummaryContract'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
const A='11111111-1111-4111-8111-111111111111',B='22222222-2222-4222-8222-222222222222',F='33333333-3333-4333-8333-333333333333',M='44444444-4444-4444-8444-444444444444'
const OWNER=['warehouse.dashboard.view','warehouse.material.view','warehouse.accessory.view','warehouse.fg.view','warehouse.procurement.view','warehouse.stock.adjust','master.fabric.view','finance.hpp.view']
const GUDANG=['warehouse.dashboard.view','warehouse.material.view','warehouse.accessory.view','warehouse.fg.view','warehouse.procurement.view','warehouse.movement.view','warehouse.stock.view']
const mv=(value:string,unknown='0')=>({value,unknown_count:unknown,basis:'CURRENT_MATERIAL_MOVING_AVERAGE' as const})
const fv=(value:string,unknown='0')=>({value,unknown_count:unknown,basis:'CURRENT_RESTATED_LOT_VALUE' as const})
// A server answer as the facade gives it for the permissions passed: hidden parts null, values only with finance.hpp.view.
function fixture(permissions:string[],query:{q?:string;offset?:number}={}):WarehouseSummary{
 const a=summaryAccess(permissions),fin=a.finance
 const withValue=<T extends object>(o:T,v:SummaryValuation)=>fin?{...o,valuation:v}:o
 const mat=(lines:MaterialLine[],v:string)=>withValue({lines},mv(v))
 const acc=(lines:AccessoryLine[],v:SummaryValuation)=>withValue({lines},v)
 const fgp=(part:Omit<FgPart,'valuation'>,v:SummaryValuation)=>withValue(part,v)
 const rows=[
  {location_id:A,location_code:'WH-A',location_name:'Gudang Bahan A',location_type:'RAW_MATERIAL_WAREHOUSE',is_active:true,zone_kind:null,
   materials:a.materials?mat([{kind:'FABRIC',unit_code:'YD',qty:'1234.500000',rolls:'3',balances:'4',quality:'CONFLICT'},{kind:'OTHER',unit_code:'PCS',qty:'20.000000',rolls:'0',balances:'1',quality:'KNOWN'}],'12537.654321'):null,
   accessories:a.accessories?acc([{unit_code:'PCS',qty:'100.000000',items:'2',balances:'2',quality:'KNOWN'}],mv('33.33')):null,
   finished_goods:a.finished_goods?fgp({physical_qty:'0',reserved_qty:'0',available_qty:'0',positions:'0',quality:'KNOWN',grades:[]},fv('0')):null},
  {location_id:B,location_code:'WH-B',location_name:'Gudang Bahan B',location_type:'RAW_MATERIAL_WAREHOUSE',is_active:false,zone_kind:'SERVICE_POST',
   materials:a.materials?mat([{kind:'FABRIC',unit_code:'YD',qty:'9.750000',rolls:'1',balances:'1',quality:'KNOWN'}],'0'):null,
   accessories:a.accessories?acc([{unit_code:'GROSS',qty:'-3.000000',items:'1',balances:'1',quality:'CONFLICT'}],mv('0','1')):null,
   finished_goods:a.finished_goods?fgp({physical_qty:'0',reserved_qty:'0',available_qty:'0',positions:'0',quality:'KNOWN',grades:[]},fv('0')):null},
  {location_id:F,location_code:'FG-1',location_name:'Gudang Barang Jadi',location_type:'FG_WAREHOUSE',is_active:true,zone_kind:null,
   materials:a.materials?mat([],'0'):null,accessories:a.accessories?acc([],mv('0')):null,
   finished_goods:a.finished_goods?fgp({physical_qty:'17',reserved_qty:'3',available_qty:'14',positions:'4',quality:'KNOWN',grades:[{quality_grade:'GRADE_A',physical_qty:'16'},{quality_grade:'GRADE_B',physical_qty:'1'}]},fv('160.493814','1')):null},
 ].filter(r=>r.materials?.lines.length||r.accessories?.lines.length||Number(r.finished_goods?.positions??'0')>0)
 const attention:Attention[]=(Object.keys(ATTENTION_RULES) as Attention['kind'][]).filter(k=>ATTENTION_RULES[k].allowed(a)).map(k=>({kind:k,menu:ATTENTION_RULES[k].menu,count:k==='MATERIAL_TRANSFER_DRAFT'?'0':'2',
  ...(k==='FABRIC_BELOW_MINIMUM'?{rows:[{material_id:M,material_sku:'KAIN-1',material_name:'Denim biru',unit_code:'YD',qty:'12.250000',minimum_qty:'100.000000'},{material_id:B,material_sku:'KAIN-3',material_name:'Drill',unit_code:'M',qty:'0',minimum_qty:'2.000000'}]}:{})}))
 return {contract_version:'cp7.warehouse-summary.v1',kind:'LIVE_WAREHOUSE_SUMMARY',read_at:'2026-10-17T03:00:00Z',business_DML:false,financial_captured:fin,q:query.q??'',
  sections:{materials:a.materials,accessories:a.accessories,finished_goods:a.finished_goods},
  totals:{materials:a.materials?mat([{kind:'FABRIC',unit_code:'YD',qty:'1244.250000',rolls:'4',balances:'5',quality:'CONFLICT'},{kind:'OTHER',unit_code:'PCS',qty:'20.000000',rolls:'0',balances:'1',quality:'KNOWN'}],'12537.654321'):null,
   accessories:a.accessories?acc([{unit_code:'GROSS',qty:'-3.000000',items:'1',balances:'1',quality:'CONFLICT'},{unit_code:'PCS',qty:'100.000000',items:'2',balances:'2',quality:'KNOWN'}],mv('33.33','1')):null,
   finished_goods:a.finished_goods?fgp({physical_qty:'17',reserved_qty:'3',available_qty:'14',positions:'4',quality:'KNOWN',grades:[{quality_grade:'GRADE_A',physical_qty:'16'},{quality_grade:'GRADE_B',physical_qty:'1'}]},fv('160.493814','1')):null},
  page:{rows:rows as WarehouseSummary['page']['rows'],total:String(rows.length),offset:query.offset??0,limit:25,next_offset:null},attention}
}
let root:Root,container:HTMLDivElement,nav:ReturnType<typeof vi.fn<(page:WarehouseMenu)=>void>>
function identity(permissions:string[]){const auth=structuredClone(recoveryIdentity) as typeof recoveryIdentity;(auth.identity as {permissions:string[]}).permissions=permissions;return auth}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset();nav=vi.fn<(page:WarehouseMenu)=>void>();mock.auth=identity(OWNER)
 mock.rpc.mockImplementation((_name,{p_query})=>Promise.resolve({data:fixture((mock.auth as typeof recoveryIdentity).identity.permissions as unknown as string[],p_query),error:null}))
 container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedWarehouseSummaryPage onNavigate={nav}/>));await flush()}
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
const buttons=(name:string)=>[...container.querySelectorAll('button')].filter(e=>e.textContent===name)
const button=(name:string)=>buttons(name)[0]
const region=(name:string)=>container.querySelector<HTMLElement>(`[aria-label="${name}"]`)
async function type(value:string){await act(async()=>{const e=container.querySelector<HTMLInputElement>('input[aria-label="Cari gudang"]')!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
const badAnswer=(change:(d:WarehouseSummary&Record<string,unknown>)=>void)=>{const d=fixture(OWNER) as WarehouseSummary&Record<string,unknown>;change(d);mock.rpc.mockResolvedValueOnce({data:d,error:null})}

describe('Ringkasan Gudang from the connected summary read',()=>{
 it('shows totals, every location, values and the checks as an owner, read once with the bounded query',async()=>{
  await mount()
  expect(mock.rpc.mock.calls).toEqual([['erp_cp7_get_warehouse_summary_v1',{p_query:{q:'',offset:0,limit:25}}]])
  const totals=region('Total bahan dan roll')!.textContent!
  expect(totals).toContain('1.244,25 YD');expect(totals).toContain('4 roll berisi');expect(totals).toContain('20 PCS');expect(totals).toContain('Nilai bahan Rp12.537,65')
  expect(totals).toContain('ada saldo yang perlu diperiksa')
  expect(region('Total aksesori')!.textContent).toContain('-3 GROSS');expect(region('Total aksesori')!.textContent).toContain('1 saldo belum diketahui nilainya')
  const fg=region('Total barang jadi')!.textContent!
  expect(fg).toContain('17 pcs');expect(fg).toContain('Dicadangkan 3 · tersedia 14');expect(fg).toContain('GRADE A 16 · GRADE B 1 pcs');expect(fg).toContain('Rp160,49')
  expect(region('Stok Gudang Bahan A')!.textContent).toContain('1.234,5 YD');expect(region('Stok Gudang Bahan B')!.textContent).toContain('Pos jasa aksesori · Nonaktif')
  expect(region('Stok Gudang Barang Jadi')!.textContent).not.toContain('Bahan & Roll')
  expect(container.textContent).toContain('Total 3 gudang berisi stok')
  const attention=region('Perlu diperhatikan')!
  expect(attention.querySelectorAll('[data-attention]')).toHaveLength(8)
  expect(attention.querySelector('[data-attention="MATERIAL_TRANSFER_DRAFT"]')).toBeNull()
  expect(attention.textContent).toContain('KAIN-1 · Denim biru: stok 12,25 YD, minimum 100 YD')
  expect(attention.textContent).toContain('2 hitung fisik atau penyesuaian bahan masih draft.')
  await click(attention.querySelector<HTMLElement>('[data-attention="RECEIPT_DRAFT"] button')!);expect(nav).toHaveBeenLastCalledWith('procurement')
  await click(attention.querySelector<HTMLElement>('[data-attention="FG_ADJUSTMENT_DRAFT"] button')!);expect(nav).toHaveBeenLastCalledWith('stock-adjustment')
  await click(button('Buka Bahan & Roll'));expect(nav).toHaveBeenLastCalledWith('materials-rolls')
  await click(button('Buka Ringkasan Barang Jadi'));expect(nav).toHaveBeenLastCalledWith('fg-summary')
  expect(mock.rpc).toHaveBeenCalledTimes(1)
 })
 it('a limited role (GUDANG) sees no value, no Stock Adjustment check and no link it may not open',async()=>{
  mock.auth=identity(GUDANG);await mount()
  expect(container.textContent).not.toContain('Rp');expect(container.textContent).toContain('Nilai stok tidak ditampilkan karena hak melihat HPP belum diberikan.')
  const attention=region('Perlu diperhatikan')!
  expect([...attention.querySelectorAll('[data-attention]')].map(e=>e.getAttribute('data-attention'))).toEqual(['MATERIAL_BALANCE_REVIEW','ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS','ACCESSORY_NEGATIVE','FG_POSITION_REVIEW','RECEIPT_DRAFT'])
  expect(button('Buka Stock Adjustment')).toBeUndefined();expect(container.textContent).not.toContain('KAIN-1')
  // The server answering a value or a check the role may not see is refused, without any figure.
  for(const change of [(d:WarehouseSummary)=>{d.financial_captured=true},(d:WarehouseSummary)=>{d.attention.push({kind:'MATERIAL_COUNT_DRAFT',menu:'stock-adjustment',count:'1'})},
   (d:WarehouseSummary)=>{(d.page.rows[0].materials as Record<string,unknown>).valuation=mv('1')}]){
   const d=fixture(GUDANG);change(d);mock.rpc.mockResolvedValueOnce({data:d,error:null});await click(button('Muat ulang ringkasan'))
   expect(container.querySelector('[role="alert"]')!.textContent).toContain('Data ringkasan gudang belum lengkap');expect(container.textContent).not.toContain('YD');expect(container.textContent).not.toContain('Rp')
  }
 })
 it('hides each section without its own key and lists only locations of the visible sections',async()=>{
  mock.auth=identity(['warehouse.dashboard.view','warehouse.fg.view']);await mount()
  expect(region('Total bahan dan roll')).toBeNull();expect(region('Total aksesori')).toBeNull();expect(region('Total barang jadi')).not.toBeNull()
  expect(container.textContent).toContain('Bagian Bahan & Roll, Aksesori tidak ditampilkan');expect(container.textContent).not.toContain('YD')
  expect([...container.querySelectorAll('[data-location-id]')].map(e=>e.getAttribute('data-location-id'))).toEqual([F])
  expect([...container.querySelectorAll('[data-attention]')].map(e=>e.getAttribute('data-attention'))).toEqual(['FG_POSITION_REVIEW'])
  const d=fixture(['warehouse.dashboard.view','warehouse.fg.view']);d.sections.materials=true;mock.rpc.mockResolvedValueOnce({data:d,error:null})
  await click(button('Muat ulang ringkasan'));expect(container.textContent).toContain('Data ringkasan gudang belum lengkap');expect(container.textContent).not.toContain('pcs')
 })
 it('without warehouse.dashboard.view nothing is read',async()=>{
  mock.auth=identity(['warehouse.material.view','warehouse.fg.view']);await mount()
  expect(container.textContent).toContain('Hak melihat ringkasan gudang belum diberikan.');expect(mock.rpc).not.toHaveBeenCalled()
 })
 it('loading, failure and empty states show no figure',async()=>{
  let resolve:((v:unknown)=>void)|null=null;mock.rpc.mockImplementationOnce(()=>new Promise(r=>{resolve=r}))
  await mount();expect(container.querySelector('[role="status"]')!.textContent).toBe('Membaca stok gudang…');expect(container.textContent).not.toMatch(/\d/)
  await act(async()=>resolve!({data:null,error:{code:'42501',message:'CP7_WAREHOUSE_SUMMARY_DENIED'}}));await flush()
  expect(container.querySelector('[role="alert"]')!.textContent).toContain('Akun tidak memiliki izin');expect(container.textContent).not.toContain('YD')
  const empty=fixture(OWNER);empty.page={rows:[],total:'0',offset:0,limit:25,next_offset:null}
  for(const t of [empty.totals.materials!,empty.totals.accessories!])t.lines=[]
  Object.assign(empty.totals.finished_goods!,{physical_qty:'0',reserved_qty:'0',available_qty:'0',positions:'0',grades:[]})
  empty.attention=empty.attention.map(a=>({...a,count:'0',...(a.rows?{rows:[]}:{})}))
  mock.rpc.mockResolvedValueOnce({data:empty,error:null});await click(button('Muat ulang ringkasan'))
  expect(container.textContent).toContain('Belum ada stok di gudang yang bisa Anda lihat.');expect(container.textContent).toContain('Tidak ada yang perlu diperhatikan dari pemeriksaan ini.')
  expect(container.querySelectorAll('[data-attention]')).toHaveLength(0)
 })
 it('refuses an answer whose rows do not add up to its totals, unknown keys and a value without basis',async()=>{
  await mount()
  for(const change of [(d:WarehouseSummary&Record<string,unknown>)=>{d.page.rows[0].materials!.lines[0].qty='1234.000000'},(d:WarehouseSummary&Record<string,unknown>)=>{d.extra=1},
   (d:WarehouseSummary&Record<string,unknown>)=>{d.totals.finished_goods!.physical_qty='18'},(d:WarehouseSummary&Record<string,unknown>)=>{d.business_DML=true as false},
   (d:WarehouseSummary&Record<string,unknown>)=>{d.totals.materials!.valuation!.basis='CURRENT_RESTATED_LOT_VALUE'},(d:WarehouseSummary&Record<string,unknown>)=>{d.attention=d.attention.slice(1)}]){
   badAnswer(change);await click(button('Muat ulang ringkasan'))
   expect(container.querySelector('[role="alert"]')!.textContent).toContain('Data ringkasan gudang belum lengkap');expect(container.textContent).not.toContain('YD')
  }
 })
 it('search retires figures at once, sends the query, pages, and a late answer of an older query is not painted',async()=>{
  await mount();await type('gudang b');expect(container.textContent).not.toContain('YD');expect(mock.rpc).toHaveBeenCalledTimes(1)
  await click(button('Cari gudang'));expect(mock.rpc.mock.calls.at(-1)![1].p_query).toEqual({q:'gudang b',offset:0,limit:25})
  expect(container.textContent).toContain('pencarian "gudang b"');expect(region('Total bahan dan roll')!.textContent).toContain('Bahan & Roll sesuai pencarian')
  mock.rpc.mockImplementationOnce((_n,{p_query})=>{const d=fixture(OWNER,p_query);d.page.total='30';d.page.next_offset=null;return Promise.resolve({data:d,error:null})})
  await click(button('Muat ulang ringkasan'));expect(container.textContent).toContain('Data ringkasan gudang belum lengkap')
  mock.rpc.mockImplementationOnce((_n,{p_query})=>{const d=fixture(OWNER,p_query);d.page.total='28';d.page.next_offset=3;return Promise.resolve({data:d,error:null})})
  await click(button('Muat ulang ringkasan'));expect(button('Gudang berikutnya').disabled).toBe(false)
  await click(button('Gudang berikutnya'));expect(mock.rpc.mock.calls.at(-1)![1].p_query).toEqual({q:'gudang b',offset:3,limit:25})
  let resolve:((v:unknown)=>void)|null=null;mock.rpc.mockImplementationOnce(()=>new Promise(r=>{resolve=r}))
  await click(button('Semua gudang'));await type('lain');await act(async()=>resolve!({data:fixture(OWNER),error:null}));await flush()
  expect(container.textContent).not.toContain('YD');expect(container.querySelector('[data-location-id]')).toBeNull()
 })
 it('an answer for another search is refused',async()=>{
  mock.rpc.mockImplementationOnce(()=>Promise.resolve({data:fixture(OWNER,{q:'lain'}),error:null}));await mount()
  expect(container.textContent).toContain('Pencarian berubah. Muat ulang ringkasan.');expect(container.textContent).not.toContain('YD')
 })
})
