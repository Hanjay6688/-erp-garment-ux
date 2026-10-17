// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SalesDraftPanel from '../../src/SalesDraftPanel'
import {parseSalesFormOptions,salesLineTotal,salesMoneyInput,type SalesRead} from '../../src/salesReadContract'
import {recoveryIdentity} from '../../tests/fixtures/productionRecovery'
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../src/auth/AuthProvider',()=>({useAuth:()=>recoveryIdentity}))
vi.mock('../../src/lib/supabase',()=>({getUatSupabaseClient:()=>client}))
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


// Separate case: a commercial SKU number is unique per brand, not globally
// (bf_skus_v1 UNIQUE(brand_id,sku)); no earlier UI case is repeated.
it('ASTRA_UI_SERIES_MUST_PRESERVE_BRAND',async()=>{
 const a={...stock,product_id:product,product_sku:'VIVO-73001-32',commercial_sku:'73001',brand_name:'Vivo',size_code:'32'}
 const z={...stock,product_id:other,product_sku:'WIDIE-73001-32',commercial_sku:'73001',brand_name:'Widie',size_code:'32'}
 client.rpc.mockImplementation(async(_n,args)=>{const q=args.p_query;const rows=[a,z];return {data:{contract_version:'cp7.sales-form-options.v1',kind:'STOCK',physical_at:q.physical_at,location_id:q.location_id??null,availability_basis:'CURRENT_AVAILABLE_NOT_HISTORICAL_STOCK',rows,total:'2',offset:0,limit:q.limit,next_offset:null},error:null}})
 await mount();await fill('Cari barang draft','73001');await click(button('Cari barang draft'))
 const choices=container.querySelectorAll<HTMLElement>('[aria-label="Pilih barang invoice"] .cproc-receipt')
 expect(choices[0].textContent).toContain('Vivo');await click(choices[0])
 const rows=[...container.querySelectorAll('.cproc-size-cell')].map(x=>({text:x.textContent,qty:x.querySelector('input')?.value}))
 const evidence={selected:'Vivo / 73001 / 32',rows,series:container.querySelector('.cproc-series')?.textContent,expected:'only Vivo series is added; its single size receives12'}
 console.log(JSON.stringify({group:'ASTRA_UI_IDENTITY',case:'ASTRA_UI_SERIES_MUST_PRESERVE_BRAND',status:rows.length===1&&rows[0].qty==='12'?'PASS':'COUNTEREXAMPLE',evidence}))
})
