// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach,beforeEach,describe,expect,it,vi } from 'vitest'
import ConnectedMaterialCountPage from './ConnectedMaterialCountPage'
import { parseCounts,parseCountPreview } from './materialCountContract'
import { readProductionRecovery } from './productionRecovery'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
// OW-09 declared document-reader stand-in: whatever a test serves, the wrapper applies the requested status to the rows
// and echoes the whole-list shape the reader applied before paging (a test that serves its own list is left as is).
const reader=vi.hoisted(()=>({rpc:async(name:string,args:Record<string,unknown>)=>{
 const r=await client.rpc(name,args),q=((args??{}).p_query??{}) as Record<string,unknown>
 if(name!=='erp_cp7_get_material_counts_v1'||!r?.data?.page||!('order' in q)||'list' in r.data.page)return r
 const rows=(r.data.page.rows as {status:string}[]).filter(x=>!q.status||x.status===q.status)
 return {...r,data:{...r.data,page:{...r.data.page,rows,total:q.status?String(rows.length):r.data.page.total,list:{q:q.q,status:q.status,order:q.order}}}}
}}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>reader}))
const id='11111111-1111-4111-8111-111111111111',doc='22222222-2222-4222-8222-222222222222',at='2026-09-29T03:00:03.123456Z',token='a'.repeat(32)
const page=(rows:unknown[])=>({rows,total:String(rows.length),offset:0,limit:25,next_offset:null})
function stock(finance=true){return {contract_version:'cp7.material-workspace.v1',kind:'LIVE_MATERIAL_LEDGER',read_at:at,quantity_basis:'POSTED_PHYSICAL_LEDGER_CURRENT_KNOWLEDGE',financial_captured:finance,capabilities:{transfer:true,reverse_transfer:true},totals_by_unit:[{unit_code:'PCS',qty:'10',quality:'KNOWN'}],page:page([{material_id:id,material_sku:'BUTTON',material_name:'Kancing',material_type:'ACCESSORY',unit_code:'PCS',roll_id:null,roll_number:null,location_id:id,location_name:'Gudang',qty:'10',last_movement_at:at,quality:'KNOWN',availability:'ON_HAND',...(finance?{valuation:{state:'KNOWN',unit_cost:'10',value:'100',basis:'CURRENT_MATERIAL_MOVING_AVERAGE'}}:{})}])}}
function countDocs(finance=true,posted=false,detail=false){const row={id:doc,number:'COUNT-1',location_id:id,location_name:'Gudang',physical_at:at,reason_code:'COUNT_CORRECTION',status:posted?'POSTED':'DRAFT',row_version:posted?'9007199254740994':'9007199254740993',notes:'Sudah dihitung',managed_count:true,line_count:'1'};return {contract_version:'cp7.material-counts.v1',read_at:at,financial_captured:finance,capabilities:{adjust:true,reverse:true},page:page([row]),detail:detail?{...row,edit:posted?null:{physical_qty:'8',...(finance?{input_unit_cost:null}:{})},items:[{id,material_id:id,material_sku:'BUTTON',material_name:'Kancing',unit_code:'PCS',roll_id:null,roll_number:null,qty_signed:'-2',physical_qty:'8',notes:null,...(finance?{valuation:{input_unit_cost:null,restated_value:posted?'-20':null,basis:'CURRENT_RESTATED_DOCUMENT_NOT_STOCK'}}:{})}]}:null}}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('warehouse.material.view','warehouse.stock.adjust','finance.hpp.view');state.auth=a;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<ConnectedMaterialCountPage/>));await flush()}
function button(label:string){const el=[...container.querySelectorAll('button')].find(b=>b.textContent===label);if(!el)throw Error('Missing '+label);return el}
async function click(label:string){await act(async()=>button(label).click());await flush()}
async function fill(label:string,value:string){const el=container.querySelector<HTMLInputElement|HTMLTextAreaElement>(`[aria-label="${label}"]`)!;await act(async()=>{Object.getOwnPropertyDescriptor(el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function check(){await act(async()=>container.querySelector<HTMLInputElement>('.cmat-count-detail input[type="checkbox"]')!.click());await flush()}
const writes=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_material_count_v1')
function server(finance=true){const s={posted:false,lose:false,failRead:false,effects:0,wrongQty:false,deleted:false},cache=new Map<string,unknown>();client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
 if(name==='erp_cp7_get_materials_v1')return s.failRead&&s.posted?{data:null,error:{message:'Read unavailable'}}:{data:stock(finance),error:null}
 if(name==='erp_cp7_get_material_counts_v1'){if(s.deleted){return (args.p_query as Record<string,unknown>).adjustment_id?{data:null,error:{message:'CP7_COUNT_NOT_FOUND'}}:{data:{...countDocs(finance),page:page([])},error:null}}return {data:countDocs(finance,s.posted,Boolean((args.p_query as Record<string,unknown>).adjustment_id)),error:null}}
 if(name==='erp_cp7_preview_material_count_v1'){const p=args.p_scope as Record<string,unknown>;return {data:{contract_version:'cp7.material-count-preview.v1',read_at:at,location_id:id,physical_at:p.physical_at,basis:'POSTED_PHYSICAL_AT_COUNT_CURRENT_KNOWLEDGE',items:[{material_id:id,material_sku:'BUTTON',material_name:'Kancing',unit_code:'PCS',roll_id:null,roll_number:null,system_qty:'10',physical_qty:s.wrongQty?'7':'8',qty_signed:'-2',basis_token:token}]},error:null}}
 if(name==='erp_cp7_save_material_count_v1'){const key=String(args.p_request);if(!cache.has(key)){s.effects++;s.posted=args.p_action==='POST';cache.set(key,{contract_version:'cp7.material-count-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:key,adjustment_id:doc,status:s.posted?'POSTED':'DRAFT',row_version:s.posted?'9007199254740994':'9007199254740993'})}return s.lose?{data:null,error:{status:503,message:'Lost committed reply'}}:{data:cache.get(key),error:null}}
 throw Error('Unexpected RPC '+name)
});return s}
async function select(){await act(async()=>container.querySelector<HTMLButtonElement>('.cproc-receipt')!.click());await flush();await check()}
async function form(){await click('Hitung Kancing');await fill('Nomor hitung fisik','COUNT-NEW');await fill('Waktu hitung WIB','2026-09-29T10:00');await fill('Jumlah fisik bahan','8');await fill('Catatan hitung fisik','Hitung ulang dan foto gudang');await click('Periksa selisih')}
it('keeps whole-list status filtering separate from stock and does not create a count or business write',async()=>{
 server();await mount()
 const status=container.querySelector<HTMLSelectElement>('[aria-label="Status dokumen hitung fisik"]')!
 await act(async()=>{status.value='POSTED';status.dispatchEvent(new Event('change',{bubbles:true}))});await flush();expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0);expect(container.textContent).toContain('Saldo sekarang 10');expect(writes()).toHaveLength(0)
 expect(client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_material_counts_v1').at(-1)![1].p_query).toMatchObject({offset:0,status:'POSTED',order:'SOURCE'})
 const tools=container.querySelector('[aria-label="Cari, browse, urutkan dan filter dokumen hitung fisik"]')!,browse=[...tools.querySelectorAll('button')].find(b=>b.textContent==='Browse semua')!
 await act(async()=>browse.click());await flush();expect(status.value).toBe('');expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(1);expect(writes()).toHaveLength(0)
})
describe('OW-09 count document list',()=>{
 it('searches, filters and orders every document through the reader and restarts at the first page',async()=>{
  const many=Array.from({length:31},(_,i)=>({...(countDocs(true).page.rows[0] as {status:string}),id:`77777777-7777-4777-8777-${String(i).padStart(12,'0')}`,number:`CNT-${i+1}`,status:(['DRAFT','POSTED','REVERSED'] as const)[i%3]}))
  const serve=(q:Record<string,unknown>)=>{const all=many.filter(d=>(!q.status||d.status===q.status)&&(!q.q||d.number.toLowerCase().includes(String(q.q).toLowerCase())));if(q.order!=='SOURCE')all.sort((a,b)=>(q.order==='LABEL_DESC'?-1:1)*a.number.localeCompare(b.number,'id',{numeric:true}))
   const off=Number(q.offset),w=countDocs(true);Object.assign(w.page,{rows:all.slice(off,off+25),total:String(all.length),offset:off,next_offset:off+25<all.length?off+25:null,list:{q:q.q,status:q.status,order:q.order}});return w}
  server();const original=client.rpc.getMockImplementation()!
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>name==='erp_cp7_get_material_counts_v1'?{data:serve(args.p_query as Record<string,unknown>),error:null}:original(name,args))
  await mount();const last=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_material_counts_v1').at(-1)![1].p_query,numbers=()=>[...container.querySelectorAll('.cproc-receipt strong')].map(e=>e.textContent).filter(t=>t?.startsWith('CNT-'))
  expect(last()).toMatchObject({q:'',offset:0,limit:25,status:null,order:'SOURCE'});expect(numbers()).toHaveLength(25);expect(container.textContent).toContain('31 pemeriksaan cocok dengan pencarian dan filter')
  expect(container.textContent).toContain('Filter dan urutan berlaku untuk seluruh hasil, termasuk halaman lain');expect(container.textContent).not.toContain('Filter dan urutan hanya mengatur halaman')
  await click('Pemeriksaan berikutnya');expect(last().offset).toBe(25);expect(numbers()).toHaveLength(6)
  await act(async()=>{const s=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan dokumen hitung fisik"]')!;s.value='LABEL_DESC';s.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
  expect(last()).toMatchObject({offset:0,order:'LABEL_DESC'});expect(numbers()).toEqual(serve(last()).page.rows.map(d=>(d as {number:string}).number));expect(numbers()[0]).toBe('CNT-31')
  await act(async()=>{const s=container.querySelector<HTMLSelectElement>('[aria-label="Status dokumen hitung fisik"]')!;s.value='REVERSED';s.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
  expect(last()).toMatchObject({offset:0,status:'REVERSED',order:'LABEL_DESC'});expect(numbers()).toHaveLength(10);expect(container.textContent).toContain('10 pemeriksaan cocok')
  await act(async()=>[...container.querySelector(`[aria-label="Cari, browse, urutkan dan filter dokumen hitung fisik"]`)!.querySelectorAll('button')].find(b=>b.textContent==='Browse semua')!.click());await flush();expect(last()).toMatchObject({offset:0,q:'',status:null,order:'SOURCE'});expect(numbers()).toHaveLength(25)
  expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_material_count_v1')).toBe(false)
  const list={q:'',status:'POSTED' as const,order:'LABEL_ASC' as const},good=serve({...list,offset:0});expect(parseCounts(good,true,list).page.total).toBe('10')
  const variants:((w:ReturnType<typeof serve>)=>void)[]=[w=>{delete (w.page as {list?:unknown}).list},w=>{(w.page as unknown as {list:Record<string,unknown>}).list.status=null},w=>{(w.page as unknown as {list:Record<string,unknown>}).list.order='SOURCE'},w=>{(w.page as unknown as {list:Record<string,unknown>}).list.more=1},w=>{(w.page.rows[0] as {status:string}).status='DRAFT'}]
  for(const change of variants){const w=structuredClone(good);change(w);expect(()=>parseCounts(w,true,list)).toThrow()}
  expect(()=>parseCounts(good,true)).toThrow() // an echo nobody asked for is refused
 })
})
function multiServer(edit=false){
 server();const original=client.rpc.getMockImplementation()!
 const second={...(stock().page.rows[0] as Record<string,unknown>),material_id:doc,material_sku:'ZIP',material_name:'Resleting'}
 const inputs=[{material_id:id,material_sku:'BUTTON',material_name:'Kancing',unit_code:'PCS',roll_id:null,roll_number:null,physical_qty:'8',notes:'Baris pertama',input_unit_cost:null},
  {material_id:doc,material_sku:'ZIP',material_name:'Resleting',unit_code:'PCS',roll_id:null,roll_number:null,physical_qty:'10',notes:'Jumlah sesuai',input_unit_cost:null}]
 client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
  if(name==='erp_cp7_get_materials_v1')return {data:{...stock(),totals_by_unit:[{unit_code:'PCS',qty:'30',quality:'KNOWN'}],page:page([...stock().page.rows,second,{...second,location_id:doc,location_name:'Gudang lain'}])},error:null}
  if(name==='erp_cp7_get_material_counts_v1'&&edit&&(args.p_query as Record<string,unknown>).adjustment_id){const d=countDocs(true,false,true);return {data:{...d,detail:{...d.detail,edit:{items:inputs}}},error:null}}
  if(name==='erp_cp7_preview_material_count_v1'){
   const p=args.p_scope as {physical_at:string;items:{material_id:string;physical_qty:string}[]}
   return {data:{contract_version:'cp7.material-count-preview.v1',read_at:at,location_id:id,physical_at:p.physical_at,basis:'POSTED_PHYSICAL_AT_COUNT_CURRENT_KNOWLEDGE',items:[...p.items].reverse().map(item=>({...inputs.find(i=>i.material_id===item.material_id)!,notes:undefined,input_unit_cost:undefined,system_qty:'10',physical_qty:item.physical_qty,qty_signed:item.material_id===id?'-2':'0',basis_token:token})).map(({notes:_,input_unit_cost:__,...line})=>line)},error:null}
  }
  return original(name,args)
 })
 return inputs
}
describe('physical count connected boundary',()=>{
 it('submits physical quantity and server basis without any client delta or system balance',async()=>{server();await mount();await form();expect(container.textContent).toContain('selisih -2 PCS');await click('Simpan draft hitung fisik');const sent=writes()[0][1];expect(sent.p_payload.items).toEqual([{material_id:id,roll_id:null,physical_qty:'8',basis_token:token}]);expect(sent.p_expected).toBeNull()})
 it('invalidates review when quantity or physical time changes',async()=>{server();await mount();await form();expect(button('Simpan draft hitung fisik').disabled).toBe(false);await fill('Jumlah fisik bahan','7');expect(button('Simpan draft hitung fisik').disabled).toBe(true);expect(writes()).toHaveLength(0)})
 it('rejects a preview for another physical quantity',async()=>{const s=server();s.wrongQty=true;await mount();await form();expect(container.textContent).toContain('Pratinjau hitung fisik tidak cocok');expect(button('Simpan draft hitung fisik').disabled).toBe(true)})
 it('posts an explicitly reviewed exact version and retires the old action',async()=>{server();await mount();await select();await click('Sahkan hitung fisik');expect(writes()[0][1].p_expected).toBe('9007199254740993');expect(container.textContent).toContain('Penyesuaian stok sudah disahkan');expect(readProductionRecovery('disposable:actor-1').pending.MATERIAL_COUNT).toBeUndefined()})
 it('replays the same request after a lost commit response and remount',async()=>{const s=server();await mount();await select();s.lose=true;await click('Sahkan hitung fisik');const original=structuredClone(writes()[0][1]);await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile transaksi');expect(writes()[1][1]).toEqual(original);expect(s.effects).toBe(1);expect(container.textContent).toContain('Penyesuaian stok sudah disahkan')})
 it('keeps old actions retired after a committed result whose reload fails',async()=>{const s=server();await mount();await select();const old=button('Sahkan hitung fisik');s.failRead=true;await click('Sahkan hitung fisik');expect(container.textContent).not.toContain('Sahkan hitung fisik');await act(async()=>old.click());expect(writes()).toHaveLength(1);s.failRead=false;await click('Muat ulang');expect(container.textContent).toContain('Penyesuaian stok sudah disahkan')})
 it('recovers a committed draft that another authorized action subsequently deleted',async()=>{const s=server();await mount();await form();s.lose=true;await click('Simpan draft hitung fisik');const sent=structuredClone(writes()[0][1]);s.lose=false;s.deleted=true;await click('Reconcile transaksi');expect(writes()[1][1]).toEqual(sent);expect(readProductionRecovery('disposable:actor-1').pending.MATERIAL_COUNT).toBeUndefined();expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0);expect(button('Hitung Kancing').disabled).toBe(false)})
 it('edits the exact draft version and retains its full original timestamp',async()=>{server();await mount();await select();await click('Edit draft hitung fisik');expect((container.querySelector('[aria-label="Jumlah fisik bahan"]') as HTMLInputElement).value).toBe('8');await fill('Catatan hitung fisik','Koreksi catatan setelah hitung ulang');await click('Periksa selisih');await click('Simpan draft hitung fisik');const sent=writes()[0][1];expect(sent.p_expected).toBe('9007199254740993');expect(sent.p_payload.id).toBe(doc);expect(sent.p_payload.physical_at).toBe(at);expect(sent.p_payload.notes).toBe('Koreksi catatan setelah hitung ulang')})
 it('rejects operational money leakage and incomplete document details',()=>{expect(()=>parseCounts(countDocs(true,true,true),false)).toThrow();const d=countDocs(false,false,true);expect(()=>parseCounts({...d,detail:{...d.detail,line_count:'2'}},false)).toThrow();expect(()=>parseCountPreview({items:[]})).toThrow()})
 it('preserves two physical inputs including zero difference and matches preview by source rather than order',async()=>{
  multiServer();await mount();await click('Hitung Kancing');await fill('Jumlah fisik bahan','8')
  const other=[...container.querySelectorAll('.cmat-roll')].find(row=>row.textContent?.includes('Gudang lain'))!;expect(other.querySelector('button')!.disabled).toBe(true)
  await click('Hitung Resleting');await fill('Jumlah fisik Resleting ZIP','10');await fill('Nomor hitung fisik','COUNT-MULTI');await fill('Waktu hitung WIB','2026-09-29T10:00');await fill('Catatan hitung fisik','Dua posisi dihitung');await click('Periksa selisih')
  expect(container.querySelectorAll('.cmat-count-input')).toHaveLength(2);expect(container.textContent).toContain('Hasil hitung tetap disimpan tanpa mutasi penyesuaian.')
  await click('Simpan draft hitung fisik');expect(writes()[0][1].p_payload.items).toEqual([{material_id:id,roll_id:null,physical_qty:'8',basis_token:token},{material_id:doc,roll_id:null,physical_qty:'10',basis_token:token}])
 })
 it('reopens all original inputs and preserves zero-count notes and exact document timestamp on edit',async()=>{
  multiServer(true);await mount();await select();await click('Edit draft hitung fisik');expect(container.querySelectorAll('.cmat-count-input')).toHaveLength(2)
  expect((container.querySelector('[aria-label="Jumlah fisik Resleting ZIP"]') as HTMLInputElement).value).toBe('10')
  await click('Periksa selisih');await click('Simpan draft hitung fisik');const sent=writes()[0][1]
  expect(sent.p_payload.physical_at).toBe(at);expect(sent.p_expected).toBe('9007199254740993');expect(sent.p_payload.items).toHaveLength(2);expect(sent.p_payload.items[1]).toMatchObject({physical_qty:'10',notes:'Jumlah sesuai'})
 })
 it('invalidates the entire review after removing a counted source',async()=>{
  multiServer(true);await mount();await select();await click('Edit draft hitung fisik');await click('Periksa selisih');expect(button('Simpan draft hitung fisik').disabled).toBe(false)
  await act(async()=>container.querySelector<HTMLButtonElement>('[aria-label="Lepas Resleting ZIP dari pemeriksaan"]')!.click());await flush()
  expect(container.querySelectorAll('.cmat-count-input')).toHaveLength(1);expect(button('Simpan draft hitung fisik').disabled).toBe(true);expect(writes()).toHaveLength(0)
 })
 it('refuses duplicate, missing or financially unredacted editable source inputs',()=>{
  const inputs=multiServer(true),d=countDocs(true,false,true),detail={...d.detail,edit:{items:inputs}}
  expect(()=>parseCounts({...d,detail},true)).not.toThrow()
  expect(()=>parseCounts({...d,detail:{...detail,edit:{items:[inputs[1]]}}},true)).toThrow()
  expect(()=>parseCounts({...d,detail:{...detail,edit:{items:[...inputs,inputs[1]]}}},true)).toThrow()
  const ops=countDocs(false,false,true);expect(()=>parseCounts({...ops,detail:{...ops.detail,edit:{items:inputs}}},false)).toThrow()
 })
})
