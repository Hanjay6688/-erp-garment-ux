// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedSalesPage from './ConnectedSalesPage'
import {parseSalesRead} from './salesReadContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',line='22222222-2222-4222-8222-222222222222'
function data(finance=true,selected=false){
 const financial={basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'80.00',return_total:'20.00',net_total:'60.00',paid_total:'30.00',open_balance:'30.00'}
 const row={id,number:'INV-1',customer_id:id,customer_name:'Toko satu',location_id:id,location_name:'Gudang FG',physical_at:'2026-09-29T03:00:00Z',due_date:'2026-10-29',status:'PARTIAL_PAID',row_version:'9007199254740993',notes:null,line_count:'1',qty_pcs:'4',reserved_qty:'0',returned_qty:'1',...(finance?{financial}: {})}
 return {contract_version:'cp7.sales-workspace.v1',read_at:'2026-09-29T05:00:00Z',financial_captured:finance,read_only:true,page:{rows:[row],total:'1',offset:0,limit:25,next_offset:null},detail:selected?{...row,items:[{id:line,product_id:id,product_sku:'PHYSICAL',commercial_sku:'HISTORICAL',product_name:'Celana',size_code:'32',brand_name:'Vivo',qty_pcs:'4',notes:null,...(finance?{financial:{unit_price:'20.00',discount:'0.00',line_total:'80.00'}}:{})}]}:null}
}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view','finance.ar.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedSalesPage/>));await flush()}
async function click(button:HTMLButtonElement){await act(async()=>button.click());await flush()}
const reload=()=>[...container.querySelectorAll('button')].find(x=>x.textContent==='Muat ulang invoice')!
describe('P11 invoice source boundary',()=>{
 it('keeps exact versions and source price arithmetic',()=>{const d=parseSalesRead(data(true,true),true);expect(d.detail?.row_version).toBe('9007199254740993');expect(d.detail?.financial?.open_balance).toBe('30.00');expect(d.detail?.items[0].commercial_sku).toBe('HISTORICAL')})
 it('rejects wrong balances, hidden finance, missing lines and wrong pages',()=>{
  const values:unknown[]=[];const a=data(true,true);a.detail!.financial!.open_balance='50.00';values.push(a)
  const b=data(true,true);b.detail!.items=[];values.push(b)
  const c=data();c.page.total='2';values.push(c)
  for(const value of values)expect(()=>parseSalesRead(value,true)).toThrow()
  expect(()=>parseSalesRead(data(true,true),false)).toThrow()
  const leak=data(false,true);Object.assign(leak.detail!,{financial:{gross_total:'80.00'}});expect(()=>parseSalesRead(leak,false)).toThrow()
 })
 it('does not label a draft total as posted AR',()=>{const x=data(true,true);for(const r of [x.page.rows[0],x.detail!]){r.status='DRAFT';r.financial!.state='DRAFT_PREVIEW';r.financial!.open_balance=null as unknown as string}expect(parseSalesRead(x,true).detail?.financial?.open_balance).toBeNull()})
 it('renders real fields then clears source and money after failed refresh',async()=>{
  let fail=false;client.rpc.mockImplementation(async(_name,args)=>fail?{data:null,error:{message:'Read unavailable'}}:{data:data(true,!!args.p_query.sale_id),error:null});await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);expect(container.textContent).toContain('HISTORICAL');expect(container.textContent).toContain('Sisa pembayaran Rp30');fail=true;await click(reload());expect(container.querySelector('[role="alert"]')?.textContent).toContain('Read unavailable');expect(container.textContent).not.toContain('Rp');expect(container.textContent).not.toContain('INV-1')
 })
 it('never sends or renders a write and hides finance for operations',async()=>{
  const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view');state.auth=a;client.rpc.mockImplementation(async(_name,args)=>({data:data(false,!!args.p_query.sale_id),error:null}));await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);expect(container.textContent).toContain('HISTORICAL');expect(container.textContent).not.toContain('Rp');expect(new Set(client.rpc.mock.calls.map(x=>x[0]))).toEqual(new Set(['erp_cp7_get_sales_v1']))
 })
 it('ignores an old pending response after current authority remounts',async()=>{
  let finish!:(r:unknown)=>void;client.rpc.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));await mount();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view');state.auth=a;client.rpc.mockResolvedValue({data:data(false),error:null});await act(async()=>root.render(<ConnectedSalesPage/>));await flush();await act(async()=>finish({data:data(true,true),error:null}));await flush();expect(container.textContent).not.toContain('Rp');expect(container.querySelector('[role="alert"]')).toBeNull()
 })
})
