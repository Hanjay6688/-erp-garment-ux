// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedFgStockPage from './ConnectedFgStockPage'
import { parseFgWorkspace, parseFgLedger, type FgMovementList } from './fgContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { demandWire } from '../tests/fixtures/nativeDemandHistory'
import { reorderWire } from '../tests/fixtures/fgReorder'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
// OW-09 declared card-reader stand-in: whatever a test serves, the wrapper applies the requested movement type to the
// rows and echoes the whole-card list (with the served types as choices) like the reader; a served list is left as is.
const reader=vi.hoisted(()=>({rpc:async(name:string,args:Record<string,unknown>)=>{
 const r=await client.rpc(name,args),q=((args??{}).p_query??{}) as Record<string,unknown>
 if(name!=='erp_cp7_get_fg_ledger_v2'||!r?.data?.page||!('order' in q)||'list' in r.data.page)return r
 const all=r.data.page.rows as {movement_type:string}[],rows=all.filter(x=>!q.movement_type||x.movement_type===q.movement_type)
 const movement_types=[...new Set(all.map(x=>x.movement_type))].sort((a,b)=>a<b?-1:a>b?1:0)
 return {...r,data:{...r.data,page:{...r.data.page,rows,total:q.movement_type?String(rows.length):r.data.page.total,list:{q:q.q,movement_type:q.movement_type,order:q.order,movement_types}}}}
}}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>reader}))
const id='11111111-1111-4111-8111-111111111111',lot='22222222-2222-4222-8222-222222222222',at='2026-09-29T03:00:00Z'
const position={product_id:id,product_sku:'SKU-PHYSICAL',commercial_sku:'LUNA',product_name:'Celana denim',size_code:'M',brand_name:'Vivo',lot_id:lot,lot_number:'LOT-01',location_id:id,location_name:'Gudang FG',quality_grade:'GRADE_A'}
const totals={physical_qty:'10',reserved_qty:'4',available_qty:'6',quality:'KNOWN'},page=<T,>(rows:T[])=>({rows,total:String(rows.length),offset:0,limit:25,next_offset:null})
function stock(finance=true){return {contract_version:'cp7.fg-workspace.v1',purpose:'SUMMARY',read_at:at,knowledge:'CURRENT',quantity_basis:'PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION',financial_captured:finance,capabilities:{card:true},unit_code:'PCS',totals,page:page([{...position,...totals,last_movement_at:at,...(finance?{valuation:{state:'UNKNOWN',hpp_version_id:null,hpp_version:null,cost_state:null,calculated_at:null,unit_cost:null,value:null,basis:'CURRENT_RESTATED_LOT_VALUE'}}:{})}])}}
function ledger(finance=true){return {contract_version:'cp7.fg-ledger.v2',purpose:'CARD',read_at:at,knowledge:'CURRENT',financial_captured:finance,position,balances:totals,balance_basis:'COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE',page:page([{id,physical_at:at,recorded_at:at,movement_type:'SALE_RESERVE',source_type:'SALE_ITEM',source_id:id,reversal_of_id:null,customer_name:'Toko A',notes:null,book_order:'9007199254740993',original_physical_delta:'0',correction_count:'0',correction_recorded_at:null,audit_movements:[{id,physical_at:at,recorded_at:at,lot_id:lot,source_type:'SALE_ITEM',source_id:id,reversal_of_id:null,available_delta:'-4',reservation_delta:'4'}],commercial_sku_at_transaction:'OLD-LUNA',qty_signed:'-4',reservation_delta:'4',physical_delta:'0',available_balance:'6',reserved_balance:'4',physical_balance:'10',...(finance?{valuation:{state:'UNKNOWN',unit_cost:null,basis:'CURRENT_RESTATED_MOVEMENT_SNAPSHOT'}}:{})}])}}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('warehouse.fg.view','warehouse.stock.view','finance.hpp.view');state.auth=a;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.useRealTimers();vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<ConnectedFgStockPage/>));await flush()}
async function click(label:string){const b=[...container.querySelectorAll('button')].find(x=>x.textContent===label);if(!b)throw Error(label);await act(async()=>b.click());await flush()}
// SS-1: the summary page also reads Titik pesan ulang (erp_cp7_get_fg_reorder_v1); every fake below answers it with its own workspace.
const withReorder=(answer:(name:string,args?:never)=>unknown)=>async(name:string,args?:never)=>name==='erp_cp7_get_fg_reorder_v1'?{data:reorderWire(),error:null}:answer(name,args)
function server(finance=true){client.rpc.mockImplementation(withReorder(async(name:string)=>({data:name==='erp_cp7_get_fg_v1'?stock(finance):ledger(finance),error:null})))}
describe('FG current stock and complete ledger boundary',()=>{
  it('orders current positions locally and resets browse/zero filters through the current owning reader',async()=>{
    const w=stock(),p=w.page.rows[0];w.page.rows.push({...p,lot_id:id,lot_number:'LOT-02',commercial_sku:'ALPHA'});w.page.total='2';client.rpc.mockImplementation(withReorder(async()=>({data:w,error:null})));await mount();const calls=client.rpc.mock.calls.length
    await act(async()=>{const order=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan halaman barang jadi"]')!;order.value='LABEL_ASC';order.dispatchEvent(new Event('change',{bubbles:true}))});expect(client.rpc).toHaveBeenCalledTimes(calls);expect(container.querySelector('.cfg-position h3')!.textContent).toBe('ALPHA');expect(container.querySelector('.cfg-totals')!.textContent).toContain('10 PCS')
    const input=container.querySelector<HTMLInputElement>('[aria-label="Cari barang jadi"]')!;await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,'LUNA');input.dispatchEvent(new Event('input',{bubbles:true}))});await click('Browse semua');expect(client.rpc.mock.calls.at(-1)![1].p_query).toMatchObject({q:'',show_zero:false,offset:0});expect(input.value).toBe('')
  })
  it('sends movement type and order to the card reader while exact Native running balances stay attached',async()=>{
    const l=ledger(),m=l.page.rows[0];l.page.rows.push({...m,id:lot,commercial_sku_at_transaction:'ALPHA',movement_type:'SALE',qty_signed:'-1',reservation_delta:'0',physical_delta:'-1',available_balance:'5',reserved_balance:'4',physical_balance:'9',original_physical_delta:'-1',audit_movements:[{...m.audit_movements[0],id:lot,available_delta:'-1',reservation_delta:'0'}]});l.page.total='2';client.rpc.mockImplementation(withReorder(async(name:string)=>({data:name==='erp_cp7_get_fg_v1'?stock():structuredClone(l),error:null})));await mount();await click('Lihat mutasi LUNA · M')
    const last=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_fg_ledger_v2').at(-1)![1].p_query
    expect(last()).toMatchObject({q:'',offset:0,movement_type:null,order:'SOURCE'});expect([...container.querySelectorAll('[aria-label="Jenis mutasi FG"] option')].map(o=>o.getAttribute('value'))).toEqual(['','SALE','SALE_RESERVE'])
    await act(async()=>{const type=container.querySelector<HTMLSelectElement>('[aria-label="Jenis mutasi FG"]')!;type.value='SALE';type.dispatchEvent(new Event('change',{bubbles:true}))});await flush();expect(last()).toMatchObject({offset:0,movement_type:'SALE',order:'SOURCE'})
    await act(async()=>{const order=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan mutasi posisi FG"]')!;order.value='LABEL_DESC';order.dispatchEvent(new Event('change',{bubbles:true}))});await flush();expect(last()).toMatchObject({offset:0,movement_type:'SALE',order:'LABEL_DESC'})
    const rows=container.querySelectorAll('[data-fg-movement-id]');expect(rows).toHaveLength(1);expect(rows[0].getAttribute('data-fg-movement-id')).toBe(lot);expect(rows[0].textContent).toContain('Saldo fisik9');expect(rows[0].textContent).toContain('Tersedia5');expect(container.textContent).toContain('Total 1 mutasi');expect(container.textContent).toContain('Filter dan urutan berlaku untuk seluruh hasil, termasuk halaman lain')
    expect(container.querySelector('.cfg-totals')!.textContent).toContain('10 PCS')
  })
  it('walks every movement of a position through the reader: type and order before paging, balances unchanged',async()=>{
    const m=ledger().page.rows[0],kinds=['QC_GOOD','SALE','SALE_RESERVE'],many=Array.from({length:31},(_,i)=>({...m,id:`77777777-7777-4777-8777-${String(i).padStart(12,'0')}`,customer_name:`Toko ${i+1}`,movement_type:kinds[i%3],audit_movements:[{...m.audit_movements[0],id:`88888888-8888-4888-8888-${String(i).padStart(12,'0')}`}]}))
    const label=(x:typeof m)=>`${x.commercial_sku_at_transaction} ${x.customer_name??''} ${x.movement_type}`
    const serve=(q:Record<string,unknown>)=>{const all=many.filter(x=>!q.movement_type||x.movement_type===q.movement_type);if(q.order!=='SOURCE')all.sort((a,b)=>(q.order==='LABEL_DESC'?-1:1)*label(a).localeCompare(label(b),'id',{numeric:true}))
     const off=Number(q.offset),l=ledger();Object.assign(l.page,{rows:all.slice(off,off+25),total:String(all.length),offset:off,next_offset:off+25<all.length?off+25:null,list:{q:q.q,movement_type:q.movement_type,order:q.order,movement_types:kinds}});return l}
    client.rpc.mockImplementation(withReorder(async(name:string,args?:never)=>({data:name==='erp_cp7_get_fg_v1'?stock():serve((args as unknown as {p_query:Record<string,unknown>}).p_query),error:null})));await mount();await click('Lihat mutasi LUNA · M')
    const last=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_fg_ledger_v2').at(-1)![1].p_query,shown=()=>[...container.querySelectorAll('[data-fg-movement-id]')].map(e=>e.getAttribute('data-fg-movement-id'))
    expect(shown()).toHaveLength(25);expect(container.textContent).toContain('31 mutasi cocok dengan pencarian dan filter');await click('Mutasi berikutnya');expect(last().offset).toBe(25);expect(shown()).toHaveLength(6)
    await act(async()=>{const order=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan mutasi posisi FG"]')!;order.value='LABEL_DESC';order.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
    expect(last()).toMatchObject({offset:0,order:'LABEL_DESC'});expect(shown()).toEqual(serve(last()).page.rows.map(x=>x.id));expect(container.querySelector('[data-fg-movement-id] p')!.textContent).toContain('Toko 31')
    await act(async()=>{const type=container.querySelector<HTMLSelectElement>('[aria-label="Jenis mutasi FG"]')!;type.value='QC_GOOD';type.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
    expect(last()).toMatchObject({offset:0,movement_type:'QC_GOOD',order:'LABEL_DESC'});expect(shown()).toHaveLength(11);expect(container.textContent).toContain('Total 11 mutasi');expect(container.textContent).toContain('Fisik di gudang10 PCS')
    const list:FgMovementList={q:'',movement_type:'SALE',order:'LABEL_ASC'},good=serve({...list,offset:0});expect(parseFgLedger(good,true,'CARD',true,list).page.total).toBe('10')
    const variants:((l:ReturnType<typeof serve>)=>void)[]=[l=>{delete (l.page as {list?:unknown}).list},l=>{(l.page as unknown as {list:Record<string,unknown>}).list.movement_type=null},l=>{(l.page as unknown as {list:Record<string,unknown>}).list.order='SOURCE'},l=>{(l.page as unknown as {list:Record<string,unknown>}).list.movement_types=['SALE','QC_GOOD']},l=>{(l.page as unknown as {list:Record<string,unknown>}).list.movement_types=['SALE','SALE']},l=>{(l.page as unknown as {list:Record<string,unknown>}).list.movement_types=['sale']},l=>{(l.page as unknown as {list:Record<string,unknown>}).list.extra=1},l=>{l.page.rows[0].movement_type='QC_GOOD'}]
    for(const change of variants){const l=structuredClone(good);change(l);expect(()=>parseFgLedger(l,true,'CARD',true,list)).toThrow()}
    expect(()=>parseFgLedger(good,true,'CARD',true)).toThrow() // an echo nobody asked for is refused
  })
  it('binds all four selected stock keys and shows historical identity without another stock calculation',async()=>{server();await mount();expect(container.textContent).toContain('10 PCS');expect(container.textContent).toContain('Biaya belum lengkap');expect(container.textContent).not.toContain('Rp0');await click('Lihat mutasi LUNA · M');const sent=client.rpc.mock.calls.find(([n])=>n==='erp_cp7_get_fg_ledger_v2')![1].p_query;expect(sent).toMatchObject({product_id:id,lot_id:lot,location_id:id,quality_grade:'GRADE_A',offset:0});expect(container.textContent).toContain('OLD-LUNA');expect(container.textContent).toContain('Dicadangkan untuk penjualan');expect(client.rpc.mock.calls.every(([name])=>name.startsWith('erp_cp7_get_'))).toBe(true)})
  it('rejects a ledger from another lot before showing its movements',async()=>{server();const handler=client.rpc.getMockImplementation()!;client.rpc.mockImplementation(async(name:string)=>{const r=await handler(name);if(name==='erp_cp7_get_fg_ledger_v2'){r.data.position={...position,lot_id:id};r.data.page.rows[0].audit_movements[0].lot_id=id;}return r});await mount();await click('Lihat mutasi LUNA · M');expect(container.textContent).toContain('Pilihan barang atau halaman berubah');expect(container.textContent).not.toContain('OLD-LUNA')})
  it('labels the corrected card cost as the current lot HPP, not a cost recorded at the movement',async()=>{server();const handler=client.rpc.getMockImplementation()!;client.rpc.mockImplementation(async(name:string)=>{const r=await handler(name);if(name==='erp_cp7_get_fg_ledger_v2'){r.data.page.rows=r.data.page.rows.map((x:Record<string,unknown>)=>({...x,valuation:{state:'KNOWN',unit_cost:'12000.5',basis:'CURRENT_RESTATED_MOVEMENT_SNAPSHOT'}}))}return r});await mount();await click('Lihat mutasi LUNA · M');expect(container.textContent).toContain('HPP lot saat ini Rp');expect(container.textContent).not.toContain('HPP tercatat')})
  it('rejects monetary fields in operations responses and displays no hidden amount',async()=>{const a=state.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.hpp.view');server(false);await mount();expect(container.textContent).not.toContain('Rp');expect(()=>parseFgWorkspace(stock(true),false,'SUMMARY')).toThrow();const wrong=ledger(false);Object.assign(wrong.page.rows[0] as object,{recorded_unit_hpp:'100'});expect(()=>parseFgLedger(wrong,false,'CARD',true)).toThrow()})
  it('refuses partial pages and inconsistent reservation totals while keeping large quantities exact',()=>{const w=stock();expect(()=>parseFgWorkspace({...w,page:{...w.page,total:'2'}},true,'SUMMARY')).toThrow();expect(()=>parseFgWorkspace({...w,totals:{...totals,physical_qty:'11'}},true,'SUMMARY')).toThrow();const big={physical_qty:'9007199254740993',reserved_qty:'1',available_qty:'9007199254740992',quality:'KNOWN'};expect(parseFgWorkspace({...w,totals:big},true,'SUMMARY').totals.physical_qty).toBe('9007199254740993');const l=ledger();Object.assign(l.page.rows[0] as object,{book_order:'-9007199254740993'});expect(parseFgLedger(l,true,'CARD',true).page.rows[0].book_order).toBe('-9007199254740993');expect(parseFgLedger(l,true,'CARD',true).page.rows[0].physical_balance).toBe('10');expect(()=>parseFgLedger({...l,knowledge:'AS_KNOWN'},true,'CARD',true)).toThrow()})
  it('shows effective lot quantity with its immutable audit and rejects incomplete or foreign-lot members',async()=>{
    const w=ledger();Object.assign(w.page.rows[0],{qty_signed:'-3',reservation_delta:'0',physical_delta:'-3',available_balance:'7',reserved_balance:'0',physical_balance:'7',original_physical_delta:'-4',correction_count:'1',correction_recorded_at:at,audit_movements:[{id,physical_at:at,recorded_at:at,lot_id:lot,source_type:'SALE_ITEM',source_id:id,reversal_of_id:null,available_delta:'-4',reservation_delta:'0'},{id:lot,physical_at:at,recorded_at:at,lot_id:lot,source_type:'REVERSAL',source_id:lot,reversal_of_id:id,available_delta:'4',reservation_delta:'0'},{id:'33333333-3333-4333-8333-333333333333',physical_at:at,recorded_at:at,lot_id:lot,source_type:'SALE_ITEM',source_id:lot,reversal_of_id:null,available_delta:'-3',reservation_delta:'0'}]})
    expect(parseFgLedger(w,true,'CARD',true).page.rows[0].physical_delta).toBe('-3');client.rpc.mockImplementation(withReorder(async(name:string)=>({data:name==='erp_cp7_get_fg_v1'?stock():w,error:null})));await mount();await click('Lihat mutasi LUNA · M');expect(container.textContent).toContain('perubahan asal di lot ini -4 PCS');expect(container.textContent).toContain('Riwayat mutasi asal dan pembetulan')
    const wrong=structuredClone(w);wrong.page.rows[0].audit_movements[0].lot_id=id;expect(()=>parseFgLedger(wrong,true,'CARD',true)).toThrow()
    const incomplete=structuredClone(w);incomplete.page.rows[0].audit_movements.pop();expect(()=>parseFgLedger(incomplete,true,'CARD',true)).toThrow()
  })
  it('shows Titik pesan ulang under the summary only, read through its own facade',async()=>{
    server();await mount()
    const panel=container.querySelector('[aria-label="Titik pesan ulang"]')!;expect(panel.textContent).toContain('Titik pesan ulang (safety stock)');expect(panel.textContent).toContain('Perlu produksi')
    expect(container.querySelector('section.cfg')!.compareDocumentPosition(panel)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_get_fg_reorder_v1')).toEqual([['erp_cp7_get_fg_reorder_v1',{p_query:{q:'',filter:'ALL',offset:0,limit:25}}]])
    expect(container.querySelector('[role="alert"]')).toBeNull()
    await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockReset();server()
    await act(async()=>root.render(<ConnectedFgStockPage purpose="CARD"/>));await flush()
    expect(container.querySelector('[aria-label="Titik pesan ulang"]')).toBeNull();expect(client.rpc.mock.calls.some(([name])=>name==='erp_cp7_get_fg_reorder_v1')).toBe(false)
  })
  it('clears old stock after a denied reload',async()=>{server();await mount();client.rpc.mockResolvedValue({data:null,error:{status:403,message:'Hak akses berubah'}});await click('Muat ulang stok');expect(container.textContent).not.toContain('LOT-01');expect(container.querySelector('[role="alert"]')).toBeTruthy()})
  it('retires parent stock during an analysis read and refreshes it without losing dirty search',async()=>{
    const a=state.auth as typeof recoveryIdentity;Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});a.identity.permissions.push('master.product.view','production.wip.view','sales.invoice.view')
    vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-09-30T12:00:00Z'));server();await mount()
    const input=container.querySelector<HTMLInputElement>('[aria-label="Cari barang jadi"]')!
    await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,'isian belum dicari');input.dispatchEvent(new Event('input',{bubbles:true}))})
    let release:(x:unknown)=>void=()=>{};const fresh=stock();fresh.totals={physical_qty:'6',reserved_qty:'0',available_qty:'6',quality:'KNOWN'};Object.assign(fresh.page.rows[0]as object,fresh.totals)
    client.rpc.mockImplementation((name:string)=>name==='erp_cp7_capture_demand_history_v1'?new Promise(r=>release=r):Promise.resolve({data:fresh,error:null}))
    await click('Data permintaan & stok');await click('Muat data permintaan');expect(container.querySelector('.cfg-totals')).toBeNull();expect(container.querySelector('.cfg-position')).toBeNull()
    const args=client.rpc.mock.calls.find(([name])=>name==='erp_cp7_capture_demand_history_v1')![1]
    await act(async()=>release({data:demandWire(args.p_request),error:null}));await flush()
    expect(input.value).toBe('isian belum dicari');expect(container.querySelector('.cfg-totals')?.textContent).toContain('6 PCS');expect(container.querySelector('.cfg-position')?.textContent).not.toContain('10')
    expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_get_fg_v1')).toHaveLength(2)
  })
  it('retires both analysis and parent facts when current access is denied',async()=>{
    const a=state.auth as typeof recoveryIdentity;Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});a.identity.permissions.push('master.product.view','production.wip.view','sales.invoice.view')
    vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-09-30T12:00:00Z'));client.rpc.mockImplementation(withReorder(async(name:string,args?:{p_request:string})=>({data:name==='erp_cp7_capture_demand_history_v1'?demandWire(args!.p_request):stock(),error:null})));await mount();await click('Data permintaan & stok');await click('Muat data permintaan')
    expect(container.querySelector('table')).toBeTruthy();expect(container.querySelector('.cfg-totals')).toBeTruthy()
    client.rpc.mockResolvedValue({data:null,error:{status:403,message:'Hak akses berubah'}});await click('Periksa sumber arsip')
    expect(container.querySelector('table')).toBeNull();expect(container.querySelector('.cfg-totals')).toBeNull();expect(container.querySelector('.cfg-position')).toBeNull();expect(container.querySelector('[role="alert"]')).toBeTruthy()
  })
})
