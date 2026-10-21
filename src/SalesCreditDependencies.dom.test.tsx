// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SalesCreditDependencies from './SalesCreditDependencies'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import type {CreditDependencySource,SalesCreditDependencies as Reply} from './salesCreditDependenciesContract'

const state=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn(),open:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>state}))
vi.mock('./TransactionSourceNavigation',()=>({default:({sourceType,sourceId,disabled,label}:{sourceType:string;sourceId:string;disabled:boolean;label:string})=><button disabled={disabled} onClick={()=>state.open(sourceType,sourceId)}>{label}</button>}))
const id=(n:number)=>`11111111-1111-4111-8111-${String(n).padStart(12,'0')}`
const actor=id(2)
const source:CreditDependencySource={id:id(1),number:'INV-1',status:'PAID',row_version:'9007199254740993',review_token:'a'.repeat(32)}
const response=():Reply=>({contract_version:'cp7.sales-credit-dependencies.v1',actor_scope_id:actor,read_at:'2026-10-21T09:00:00Z',read_only:true,business_DML:false,
  source:{sale_id:source.id,number:source.number,status:source.status,row_version:source.row_version,review_token:source.review_token!},
  dependency_sha256:'b'.repeat(64),page:{offset:0,limit:25,total:'1',next_offset:null},dependencies:[{event_id:id(3),kind:'REFUND',amount:'100.01',economic_date:'2026-10-20',book_date:'2026-10-21',source_sale_id:source.id,source_sale_number:'INV-1',source_return_id:id(4),source_return_number:'RET-1',target_sale:null,journal_id:id(5)}]})
let root:Root,container:HTMLDivElement
beforeEach(()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true})
  const auth=structuredClone(recoveryIdentity);auth.identity.permissions.push('sales.invoice.view','sales.return.view','finance.ar.view')
  Object.assign(auth.identity.profile,{authUserId:actor,rowVersion:1,roleRowVersion:1});state.auth=auth
  state.rpc.mockReset();state.open.mockReset();state.rpc.mockResolvedValue({data:response(),error:null})
  container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const mount=async(props:Partial<{source:CreditDependencySource;current:boolean;locked:boolean}>={})=>{await act(async()=>root.render(<SalesCreditDependencies source={source} current locked={false} {...props}/>))}
const button=(label:string)=>{const b=Array.from(container.querySelectorAll('button')).find(x=>x.textContent===label);if(!b)throw Error('Missing '+label);return b}
const click=async(label:string)=>{await act(async()=>button(label).click())}

describe('current credit dependency navigation',()=>{
  it('reads only on demand and opens the actual linked return without writing money',async()=>{
    await mount();expect(state.rpc).not.toHaveBeenCalled();await click('Lihat penggunaan saldo kredit')
    expect(state.rpc).toHaveBeenCalledExactlyOnceWith('erp_cp7_get_sales_credit_dependencies_v1',{p_query:{sale_id:source.id,expected_version:source.row_version,review_token:source.review_token,offset:0,limit:25}})
    expect(container.textContent).toContain('Pengembalian uang · Rp100,01');expect(container.textContent).toContain('tanggal buku 2026-10-21')
    await click('Buka retur asal RET-1');expect(state.open).toHaveBeenCalledExactlyOnceWith('SALES_RETURN',id(4))
  })
  it('requires every current read permission before displaying or requesting private details',async()=>{
    for(const permission of ['sales.invoice.view','sales.return.view','finance.ar.view']){
      const auth=structuredClone(recoveryIdentity);auth.identity.permissions=['sales.invoice.view','sales.return.view','finance.ar.view'].filter(p=>p!==permission);state.auth=auth
      await mount();expect(container.textContent).toBe('');expect(state.rpc).not.toHaveBeenCalled()
    }
  })
  it('retires prior facts on an unavailable refresh and never reports the failure as no usage',async()=>{
    await mount();await click('Lihat penggunaan saldo kredit');state.rpc.mockResolvedValue({data:null,error:{message:'Sumber berubah'}})
    await click('Lihat penggunaan saldo kredit');expect(container.textContent).not.toContain('RET-1')
    expect(container.textContent).toContain('Penggunaan saldo kredit belum dapat dipastikan');expect(container.textContent).not.toContain('Tidak ada penggunaan saldo kredit aktif')
  })
  it('hides an in-flight reply when the writer locks the workspace',async()=>{
    let resolve!:(value:unknown)=>void;state.rpc.mockReturnValue(new Promise(r=>{resolve=r}))
    await mount();await click('Lihat penggunaan saldo kredit');await mount({locked:true})
    await act(async()=>resolve({data:response(),error:null}));expect(container.querySelector('[data-credit-dependency-id]')).toBeNull()
    expect(button('Lihat penggunaan saldo kredit').disabled).toBe(true);expect(state.open).not.toHaveBeenCalled()
  })
  it('rejects a late parent response after revision or authority changes',async()=>{
    let resolve!:(value:unknown)=>void;state.rpc.mockReturnValue(new Promise(r=>{resolve=r}))
    await mount();await click('Lihat penggunaan saldo kredit');await mount({source:{...source,row_version:'9007199254740994'}})
    await act(async()=>resolve({data:response(),error:null}));expect(container.querySelector('[data-credit-dependency-id]')).toBeNull()
    state.rpc.mockResolvedValue({data:response(),error:null});await mount();await click('Lihat penggunaan saldo kredit')
    const auth=structuredClone(state.auth as typeof recoveryIdentity);auth.identity.permissions=auth.identity.permissions.filter(p=>p!=='finance.ar.view');state.auth=auth
    await mount();expect(container.textContent).toBe('');expect(state.open).not.toHaveBeenCalled()
  })
  it('keeps pagination bound to the current invoice and names an APPLY target',async()=>{
    const first=response();first.page={offset:0,limit:25,total:'26',next_offset:25};first.dependencies=Array.from({length:25},(_,i)=>({...first.dependencies[0],event_id:id(i+10)}))
    const next=response();next.page={offset:25,limit:25,total:'26',next_offset:null};next.dependencies[0]={...next.dependencies[0],kind:'APPLY',target_sale:{id:id(80),number:'INV-TARGET'}}
    state.rpc.mockImplementation(async(_name,{p_query})=>({data:p_query.offset===0?first:next,error:null}))
    await mount();await click('Lihat penggunaan saldo kredit');await click('Penggunaan kredit berikutnya')
    expect(state.rpc.mock.calls.at(-1)?.[1].p_query.offset).toBe(25);expect(container.querySelectorAll('[data-credit-dependency-id]')).toHaveLength(1)
    await click('Buka invoice pemakaian INV-TARGET');expect(state.open).toHaveBeenCalledWith('SALE',id(80))
  })
})
