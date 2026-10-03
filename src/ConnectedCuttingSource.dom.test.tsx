// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedPickupPage from './ConnectedPickupPage'
import SourceLink, { TransactionSourceProvider } from './TransactionSourceNavigation'
import { pickupFixture, recoveryIdentity, recoveryPatterns } from '../tests/fixtures/productionRecovery'

const state=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn(),mode:'exact',held:null as null|((value:unknown)=>void)}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>state}))
const group='11111111-1111-4111-8111-111111111111',po='22222222-2222-4222-8222-222222222222',actor='33333333-3333-4333-8333-333333333333'
const document=()=>({domain:'CUTTING',route:'mandor-wip',id:group,number:'CUT-EXACT',status:'CUT',revision:'2',focus:{kind:'CUTTING_GROUP',id:group,parent_id:po,page_offset:100}})
let root:Root,el:HTMLDivElement
const data=(args:Record<string,unknown>)=>{
 const q=pickupFixture();q.filter=String(args.p_filter);q.offset=Number(args.p_offset);q.total=102
 const target={...q.rows[0],cutting_group_id:group,po_id:po,group_number:'CUT-EXACT'}
 q.rows=[{...q.rows[0],group_number:'OTHER'},target]
 if(state.mode==='missing')q.rows.pop()
 if(state.mode==='po')target.po_id=actor
 if(state.mode==='version')target.row_version=3
 return{data:q,error:null}
}
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear()
 state.auth={...structuredClone(recoveryIdentity),identity:{...structuredClone(recoveryIdentity.identity),profile:{...recoveryIdentity.identity.profile,authUserId:actor}}}
 state.mode='exact';state.held=null;state.rpc.mockReset()
 state.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
  if(name==='erp_cp7_resolve_transaction_source_v1')return{data:{contract_version:'cp7.transaction-source.v1',actor_scope_id:actor,source:args.p_source,status:'AVAILABLE',document:document(),read_at:'2026-10-03T04:00:00Z',business_DML:false},error:null}
  if(name==='erp_list_patterns_v1')return{data:recoveryPatterns,error:null}
  if(name==='erp_get_cutting_pickup_queue_v1'){
   if(state.mode==='held'&&args.p_filter==='ALL')return new Promise(resolve=>{state.held=resolve})
   if(state.mode==='denied'&&args.p_filter==='ALL')return{data:null,error:{message:'Current distribution permission denied',code:'42501'}}
   return data(args)
  }
  throw Error('Unexpected business writer '+name)
 })
 el=documentElement();root=createRoot(el)
})
function documentElement(){const node=window.document.createElement('div');window.document.body.append(node);return node}
afterEach(async()=>{await act(async()=>root.unmount());el.remove();localStorage.clear()})
const render=async(epoch=0)=>act(async()=>root.render(<TransactionSourceProvider scope="AUTH:1"epoch={epoch}onNavigate={()=>{}}><SourceLink sourceType="CUTTING_GROUP"sourceId={group}/><ConnectedPickupPage/></TransactionSourceProvider>))
const click=async(label:string)=>act(async()=>{const b=[...el.querySelectorAll<HTMLButtonElement>('button')].find(x=>x.textContent===label);if(!b)throw Error('Missing '+label);b.click()})
const writes=()=>state.rpc.mock.calls.filter(([name])=>name.startsWith('erp_save_'))
describe('Native posted cutting preview refuses substitution and writes',()=>{
 it('opens exact group and PO on page100 while all editing and posting stay disabled',async()=>{
  await render();await click('Buka transaksi asal')
  expect(state.rpc).toHaveBeenCalledWith('erp_get_cutting_pickup_queue_v1',{p_filter:'ALL',p_pattern_id:null,p_query:null,p_limit:100,p_offset:100})
  const selected=el.querySelector('[data-source-focus="true"]');expect(selected?.getAttribute('data-cutting-group-id')).toBe(group);expect(selected?.getAttribute('data-cutting-po-id')).toBe(po)
  for(const b of el.querySelectorAll<HTMLButtonElement>('.cpick-actions button'))expect(b.disabled).toBe(true)
  for(const input of el.querySelectorAll<HTMLInputElement>('.cpick-workspace input'))expect(input.disabled).toBe(true)
  expect(writes()).toEqual([])
 })
 it.each(['missing','po','version','denied'])('retires the old detail on a %s source response',async mode=>{
  await render();state.mode=mode;await click('Buka transaksi asal')
  expect(el.querySelector('[data-cutting-group-id]')).toBeNull();expect(el.querySelector('[role="alert"]')).not.toBeNull();expect(writes()).toEqual([])
 })
 it('retires a held Native source response when manual navigation changes its generation',async()=>{
  await render();state.mode='held';await click('Buka transaksi asal');const held=state.held;expect(held).not.toBeNull()
  state.mode='exact';await render(1);await act(async()=>held!(data({p_filter:'ALL',p_offset:100})))
  expect(el.querySelector('[data-source-focus="true"]')).toBeNull();expect(el.querySelector('[data-cutting-source-id]')).toBeNull();expect(writes()).toEqual([])
 })
 it('leaves the bound preview only through an explicit close and performs a fresh normal read',async()=>{
  await render();await click('Buka transaksi asal');await click('Tutup transaksi asal')
  expect(el.querySelector('[data-cutting-source-id]')).toBeNull()
  expect(state.rpc.mock.calls.at(-1)).toEqual(['erp_get_cutting_pickup_queue_v1',{p_filter:'ALL',p_pattern_id:null,p_query:null,p_limit:100,p_offset:0}]);expect(writes()).toEqual([])
 })
})
