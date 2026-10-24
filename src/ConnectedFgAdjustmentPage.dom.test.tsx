// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedFgAdjustmentPage from './ConnectedFgAdjustmentPage'
import {parseFgAdjustments,parseFgAdjustmentOutcome} from './fgAdjustmentContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
// OW-09 declared document-reader stand-in: whatever a test serves, the wrapper applies the requested status to the rows
// and echoes the whole-list shape the reader applied before paging (a test that serves its own list is left as is).
const reader=vi.hoisted(()=>({rpc:async(name:string,args:Record<string,unknown>)=>{
 const r=await client.rpc(name,args),q=((args??{}).p_query??{}) as Record<string,unknown>
 if(name!=='erp_cp7_get_fg_adjustments_v1'||!r?.data?.page||!('order' in q)||'list' in r.data.page)return r
 const rows=(r.data.page.rows as {status:string}[]).filter(x=>!q.status||x.status===q.status)
 return {...r,data:{...r.data,page:{...r.data.page,rows,total:q.status?String(rows.length):r.data.page.total,list:{q:q.q,status:q.status,order:q.order}}}}
}}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>reader}))
const id='11111111-1111-4111-8111-111111111111',lot='22222222-2222-4222-8222-222222222222',at='2026-09-29T03:00:00Z'
const position={product_id:id,product_sku:'SKU-PHYSICAL',commercial_sku:'LUNA',product_name:'Celana denim',size_code:'M',brand_name:'Vivo',lot_id:lot,lot_number:'LOT-01',location_id:id,location_name:'Gudang FG',quality_grade:'GRADE_A'}
const totals={physical_qty:'10',reserved_qty:'4',available_qty:'6',quality:'KNOWN'},page=(rows:unknown[])=>({rows,total:String(rows.length),offset:0,limit:25,next_offset:null})
function stock(finance=true){return {contract_version:'cp7.fg-workspace.v1',purpose:'SUMMARY',read_at:at,knowledge:'CURRENT',quantity_basis:'PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION',financial_captured:finance,capabilities:{card:true},unit_code:'PCS',totals,page:page([{...position,...totals,last_movement_at:at,...(finance?{valuation:{state:'UNKNOWN',hpp_version_id:null,hpp_version:null,cost_state:null,calculated_at:null,unit_cost:null,value:null,basis:'CURRENT_RESTATED_LOT_VALUE'}}:{})}])}}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('warehouse.fg.view','warehouse.stock.adjust','finance.hpp.view');state.auth=a;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<ConnectedFgAdjustmentPage/>));await flush()}
async function click(label:string){const b=[...container.querySelectorAll('button')].find(x=>x.textContent===label);if(!b)throw Error(label);await act(async()=>b.click());await flush()}
function server(finance=true){client.rpc.mockImplementation(async(name:string)=>({data:name==='erp_cp7_get_fg_v1'?stock(finance):documents(finance),error:null}))}

const header={id,number:'FG-COUNT',location_id:id,location_name:'Gudang FG',physical_at:at,reason_code:'COUNT_CORRECTION',reason:'Recount',notes:null,status:'DRAFT',row_version:'9007199254740993',managed:true,line_count:'1'}
function documents(finance=true){return {contract_version:'cp7.fg-adjustments.v1',read_at:at,financial_captured:finance,can_adjust:true,page:page([header]),detail:null}}
function detail(finance=true){return {...documents(finance),detail:{...header,editable:true,items:[{id,product_id:id,product_sku:'SKU',commercial_sku:'LUNA',size_code:'M',lot_id:lot,lot_number:'LOT-01',quality_grade:'GRADE_A',qty_signed:'-2',notes:null,...(finance?{valuation:{state:'UNKNOWN',hpp_version_id:null,hpp_version:null,cost_state:null,calculated_at:null,unit_cost:null,value:null,basis:'CURRENT_RESTATED_LOT_VALUE'}}:{})}]}}}
describe('FG correction financial and document boundary',()=>{
 it('labels the whole-list filter honestly, sends it to the reader, preserves stock facts, and browses with the original source reader',async()=>{
  server();await mount()
  const status=container.querySelector<HTMLSelectElement>('[aria-label="Status dokumen penyesuaian FG"]')!
  await act(async()=>{status.value='POSTED';status.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
  expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0);expect(container.textContent).toContain('Fisik 10');expect(container.textContent).toContain('Filter dan urutan berlaku untuk seluruh hasil');expect(container.textContent).toContain('Urutan hanya mengatur halaman yang sedang tampil')
  expect(client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_fg_adjustments_v1').at(-1)![1].p_query).toMatchObject({offset:0,status:'POSTED',order:'SOURCE'})
  const tools=container.querySelector('[aria-label="Cari, browse, urutkan dan filter dokumen penyesuaian FG"]')!,browse=[...tools.querySelectorAll('button')].find(b=>b.textContent==='Browse semua')!
  await act(async()=>browse.click());await flush();expect(status.value).toBe('');expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(1)
  expect(client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_fg_adjustments_v1').at(-1)![1].p_query).toMatchObject({q:'',offset:0,limit:25})
  expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_fg_adjustment_v1')).toBe(false)
 })
 it('searches, filters and orders every document through the reader and restarts at the first page',async()=>{
  const many=Array.from({length:31},(_,i)=>({...header,id:`77777777-7777-4777-8777-${String(i).padStart(12,'0')}`,number:`FGA-${i+1}`,status:(['DRAFT','POSTED','REVERSED'] as const)[i%3]}))
  const serve=(q:Record<string,unknown>)=>{const all=many.filter(d=>(!q.status||d.status===q.status)&&(!q.q||d.number.toLowerCase().includes(String(q.q).toLowerCase())));if(q.order!=='SOURCE')all.sort((a,b)=>(q.order==='LABEL_DESC'?-1:1)*a.number.localeCompare(b.number,'id',{numeric:true}))
   const off=Number(q.offset),w=documents();Object.assign(w.page,{rows:all.slice(off,off+25),total:String(all.length),offset:off,next_offset:off+25<all.length?off+25:null,list:{q:q.q,status:q.status,order:q.order}});return w}
  server();const original=client.rpc.getMockImplementation()!
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>name==='erp_cp7_get_fg_adjustments_v1'?{data:serve(args.p_query as Record<string,unknown>),error:null}:original(name,args))
  await mount();const last=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_fg_adjustments_v1').at(-1)![1].p_query,numbers=()=>[...container.querySelectorAll('.cproc-receipt strong')].map(e=>e.textContent).filter(t=>t?.startsWith('FGA-'))
  expect(last()).toMatchObject({q:'',offset:0,limit:25,status:null,order:'SOURCE'});expect(numbers()).toHaveLength(25);expect(container.textContent).toContain('31 dokumen cocok dengan pencarian dan filter')
  expect(container.textContent).toContain('Filter dan urutan berlaku untuk seluruh hasil, termasuk halaman lain');expect(container.textContent).not.toContain('Filter dan urutan hanya mengatur halaman')
  await click('Dokumen berikutnya');expect(last().offset).toBe(25);expect(numbers()).toHaveLength(6)
  await act(async()=>{const s=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan dokumen penyesuaian FG"]')!;s.value='LABEL_DESC';s.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
  expect(last()).toMatchObject({offset:0,order:'LABEL_DESC'});expect(numbers()).toEqual(serve(last()).page.rows.map(d=>(d as {number:string}).number));expect(numbers()[0]).toBe('FGA-31')
  await act(async()=>{const s=container.querySelector<HTMLSelectElement>('[aria-label="Status dokumen penyesuaian FG"]')!;s.value='REVERSED';s.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
  expect(last()).toMatchObject({offset:0,status:'REVERSED',order:'LABEL_DESC'});expect(numbers()).toHaveLength(10);expect(container.textContent).toContain('10 dokumen cocok')
  await act(async()=>[...container.querySelector(`[aria-label="Cari, browse, urutkan dan filter dokumen penyesuaian FG"]`)!.querySelectorAll('button')].find(b=>b.textContent==='Browse semua')!.click());await flush();expect(last()).toMatchObject({offset:0,q:'',status:null,order:'SOURCE'});expect(numbers()).toHaveLength(25)
  expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_fg_adjustment_v1')).toBe(false)
  const list={q:'',status:'POSTED' as const,order:'LABEL_ASC' as const},good=serve({...list,offset:0});expect(parseFgAdjustments(good,true,list).page.total).toBe('10')
  const variants:((w:ReturnType<typeof serve>)=>void)[]=[w=>{delete (w.page as {list?:unknown}).list},w=>{(w.page as unknown as {list:Record<string,unknown>}).list.status=null},w=>{(w.page as unknown as {list:Record<string,unknown>}).list.order='SOURCE'},w=>{(w.page as unknown as {list:Record<string,unknown>}).list.more=1},w=>{(w.page.rows[0] as {status:string}).status='DRAFT'}]
  for(const change of variants){const w=structuredClone(good);change(w);expect(()=>parseFgAdjustments(w,true,list)).toThrow()}
  expect(()=>parseFgAdjustments(good,true)).toThrow() // an echo nobody asked for is refused
 })
 it('refuses a partial multi-line document or unauthorized values',()=>{const r=detail();expect(()=>parseFgAdjustments({...r,detail:{...r.detail,line_count:'2'}},true)).toThrow();expect(()=>parseFgAdjustments(r,false)).toThrow();expect(parseFgAdjustments(r,true).detail?.row_version).toBe('9007199254740993');const zero=detail();Object.assign(zero.detail.items[0].valuation!,{value:'0'});expect(()=>parseFgAdjustments(zero,true)).toThrow()})
 it('requires the exact action, document and request on committed outcomes',()=>{const r={contract_version:'cp7.fg-adjustment-outcome.v1',kind:'COMMITTED_OUTCOME',action:'POST',request_id:id,adjustment_id:lot,status:'POSTED',row_version:'9007199254740993'};expect(parseFgAdjustmentOutcome(r,id,'POST',{adjustment_id:lot}).row_version).toBe('9007199254740993');expect(()=>parseFgAdjustmentOutcome(r,id,'POST',{adjustment_id:id})).toThrow();expect(()=>parseFgAdjustmentOutcome({...r,row_version:9007199254740993},id,'POST',{adjustment_id:lot})).toThrow();expect(()=>parseFgAdjustmentOutcome({...r,action:'SAVE'},id,'POST',{adjustment_id:lot})).toThrow()})
 it('clears stale stock and document cards after a denied read',async()=>{server();await mount();expect(container.textContent).toContain('LOT-01');client.rpc.mockResolvedValue({data:null,error:{status:403,message:'Hak berubah'}});await click('Muat ulang FG');expect(container.textContent).not.toContain('LOT-01');expect(container.querySelector('[role="alert"]')).toBeTruthy();expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0)})
 it('shows operational quantities without money and never substitutes unknown Rp0',async()=>{const a=state.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.hpp.view');server(false);await mount();expect(container.textContent).toContain('Fisik 10');expect(container.textContent).not.toContain('Rp');expect(client.rpc.mock.calls.every(([name])=>name.startsWith('erp_cp7_get_'))).toBe(true)})
})
