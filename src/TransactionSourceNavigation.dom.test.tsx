// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest'
import SourceLink,{TransactionSourceProvider,useTransactionSource} from './TransactionSourceNavigation'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>state}))
const source='11111111-1111-4111-8111-111111111111',parent='22222222-2222-4222-8222-222222222222',actor='33333333-3333-4333-8333-333333333333',navigate=vi.fn()
const result=()=>({data:{contract_version:'cp7.transaction-source.v1',actor_scope_id:actor,source:{source_type:'SALE_ITEM',source_id:source},status:'AVAILABLE',document:{domain:'SALE',route:'sales-invoice',id:parent,number:'INV-SOURCE',status:'POSTED',revision:'9007199254740993',focus:null},read_at:'2026-10-03T04:00:00.123456Z',business_DML:false},error:null})
function OwningSelection(){const selected=useTransactionSource('SALE');return <output>{selected?.document.id??'EMPTY'}</output>}
let root:Root,el:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});state.auth={...structuredClone(recoveryIdentity),identity:{...structuredClone(recoveryIdentity.identity),profile:{...recoveryIdentity.identity.profile,authUserId:actor}}};state.rpc.mockReset();state.rpc.mockResolvedValue(result());navigate.mockReset();el=document.createElement('div');document.body.append(el);root=createRoot(el)})
afterEach(async()=>{await act(async()=>root.unmount());el.remove()})
const render=async(scope:string|null='AUTH:1',epoch=0,disabled=false)=>act(async()=>root.render(<TransactionSourceProvider scope={scope} epoch={epoch} onNavigate={navigate}><SourceLink sourceType="SALE_ITEM" sourceId={source} disabled={disabled}/><OwningSelection/></TransactionSourceProvider>))
const click=async()=>act(async()=>el.querySelector('button')!.click())
describe('source navigation authority and route lifetime',()=>{
 it('resolves the child exactly and selects only the owning Native parent without a business write',async()=>{await render();await click();expect(navigate).toHaveBeenCalledExactlyOnceWith('sales-invoice');expect(el.querySelector('output')!.textContent).toBe(parent);expect(state.rpc).toHaveBeenCalledExactlyOnceWith('erp_cp7_resolve_transaction_source_v1',{p_source:{source_type:'SALE_ITEM',source_id:source}})})
 it.each(['scope','epoch'])('retires a held response after a %s change',async kind=>{let done!:(v:unknown)=>void;state.rpc.mockImplementation(()=>new Promise(r=>{done=r}));await render();await click();await render(kind==='scope'?'AUTH:2':'AUTH:1',kind==='epoch'?1:0);await act(async()=>done(result()));expect(navigate).not.toHaveBeenCalled();expect(el.querySelector('output')!.textContent).toBe('EMPTY')})
 it('retires a selection after a manual route change without changing login',async()=>{await render();await click();await render('AUTH:1',1);expect(el.querySelector('output')!.textContent).toBe('EMPTY')})
 it('keeps denied or unsupported sources visible without opening another document',async()=>{state.rpc.mockResolvedValue({data:null,error:{message:'CP7_TRANSACTION_SOURCE_ACCESS_DENIED'}});await render();await click();expect(navigate).not.toHaveBeenCalled();expect(el.querySelector('[role="alert"]')!.textContent).toContain('CP7_TRANSACTION_SOURCE_ACCESS_DENIED');state.rpc.mockResolvedValue({data:{...result().data,status:'UNSUPPORTED_SOURCE',document:null},error:null});await click();expect(el.querySelector('[role="alert"]')!.textContent).toContain('belum dapat dibuka');expect(navigate).not.toHaveBeenCalled()})
 it('does not start reads while a writer has locked its parent, or without current authority',async()=>{await render('AUTH:1',0,true);expect(el.querySelector('button')!.disabled).toBe(true);expect(state.rpc).not.toHaveBeenCalled();await render(null);expect(el.querySelector('button')).toBeNull()})
})
