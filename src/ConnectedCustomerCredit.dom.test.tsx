// @vitest-environment jsdom
/** Actual parent/recovery wiring with explicit server stand-ins, not Auth/Native proof. */
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedSalesPage from './ConnectedSalesPage'
import {readProductionRecovery} from './productionRecovery'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {creditActor,creditBank,creditId,creditCohort,creditEvent,creditOutcome,creditReview,creditSale,creditSource,creditTarget,creditTargetRow,creditVersion,creditWorkspace} from '../tests/fixtures/customerCredit'
import type {CreditPayload,CreditQuery} from './customerCreditContract'

const auth=vi.hoisted(()=>({current:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>auth.current}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const permissions=['sales.invoice.view','sales.invoice.create','sales.invoice.post','sales.invoice.edit_draft','finance.ar.view','finance.cash.view',
  'sales.return.view','sales.return.create','sales.return.post','sales.return.reverse','sales.payment.view','sales.payment.create','sales.payment.post','sales.payment.reverse']
function allow(){const a=structuredClone(recoveryIdentity);Object.assign(a.identity.profile,{authUserId:creditActor,rowVersion:1,roleRowVersion:1});a.identity.permissions=permissions.slice();auth.current=a}
let refusalCode='CP7_CREDIT_CONSUMER_REVIEW_CHANGED'
let root:Root,container:HTMLDivElement,commits:number,loseReply:boolean,lost:boolean,denyReplay:boolean,wrongReceipt:boolean,readFailure:boolean,refuseInitial:boolean
let denyQuote:boolean,delayQuote:((value:unknown)=>void)|null,holdQuote:boolean
let cached:Map<string,ReturnType<typeof creditOutcome>>,original:ReturnType<typeof creditEvent>
function sales(selected:boolean){
  const d=creditSource((BigInt(creditVersion)+BigInt(commits)).toString(),commits?'d'.repeat(32):undefined)
  const {items,review_token,...h}=d
  return {contract_version:'cp7.sales-workspace.v1',read_at:'2026-10-20T03:00:00Z',financial_captured:true,read_only:true,
    page:{rows:[h],total:'1',offset:0,limit:25,next_offset:null},detail:selected?{...h,items,review_token}:null}
}
beforeEach(()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear()
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,_options:unknown,callback:(lock:unknown)=>Promise<unknown>)=>callback({})}})
  refusalCode='CP7_CREDIT_CONSUMER_REVIEW_CHANGED';commits=0;loseReply=lost=denyReplay=wrongReceipt=readFailure=refuseInitial=denyQuote=holdQuote=false;delayQuote=null;cached=new Map();original=creditEvent();allow();client.rpc.mockReset()
  client.rpc.mockImplementation(async(name,args)=>{
    if(name==='erp_cp7_get_sales_v1')return readFailure&&commits?{data:null,error:{message:'Current read unavailable'}}:{data:sales(Boolean(args.p_query.sale_id)),error:null}
    if(name==='erp_cp7_get_customer_credit_workspace_v1') {
      const q=args.p_query as CreditQuery,source=creditSource(q.expected_version,q.review_token),data=creditWorkspace(q.kind,source,[original]);data.q=q.q
      return {data,error:null}
    }
    if(name==='erp_cp7_get_customer_credit_review_v1') {
      if(denyQuote)return {data:null,error:{status:403,code:'42501',message:'PRIVATE source revoked'}}
      const data=creditReview(args.p_payload as CreditPayload,original)
      if(holdQuote)return new Promise(resolve=>{delayQuote=resolve})
      return {data,error:null}
    }
    if(name==='erp_cp7_customer_credit_command_v1') {
      if(denyReplay)return {data:null,error:{status:403,code:'42501',message:'Permission revoked before idempotency read'}}
      if(refuseInitial)return {data:null,error:{code:'P0001',message:refusalCode}}
      if(!cached.has(args.p_request)){
        const {quote_sha256:_,...payload}=args.p_payload
        const q=creditReview(payload,original);cached.set(args.p_request,creditOutcome(args.p_request,q));++commits
      }
      if(loseReply&&!lost){lost=true;throw Error('Declared network loss after commit')}
      const data=structuredClone(cached.get(args.p_request))!
      if(wrongReceipt)data.amount='1.00'
      return {data,error:null}
    }
    throw Error('Unowned mock route '+name)
  })
  container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks')})
const flush=async()=>act(async()=>{await new Promise(resolve=>setTimeout(resolve,0))})
const button=(name:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===name)!
const input=(name:string)=>container.querySelector<HTMLInputElement>(`input[aria-label="${name}"]`)!
const summary=()=>container.querySelector('[aria-label="Pemeriksaan transaksi kredit"]')
const sends=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_customer_credit_command_v1')
const scope=()=>`${recoveryIdentity.runtime.projectRef}:${recoveryIdentity.identity.profile.id}`
async function click(e:HTMLElement){expect(e).toBeTruthy();await act(async()=>e.click());await flush()}
async function fill(name:string,value:string){await act(async()=>{const e=input(name);expect(e).not.toBeNull();Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function select(value:string){await act(async()=>{const s=container.querySelector<HTMLSelectElement>('select[aria-label="Tindakan saldo kredit"]')!;s.value=value;s.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
async function mount(){await act(async()=>root.render(<ConnectedSalesPage initialSaleId={creditSale}/>));await flush()}
async function open(){await mount();await click(button('Saldo kredit pelanggan'));expect(input('Waktu transaksi saldo kredit WIB').value).toBe('')}
async function prepare(action:'APPLY'|'REFUND'|'UNDO'='APPLY',quote=true){
  await open()
  if(action==='UNDO') {await click(button('Periksa riwayat kredit'));await click(button('Periksa pembatalan pemakaian saldo RET-SOURCE'))}
  else {
    await click(button('Periksa saldo dari retur'));await click(container.querySelector<HTMLElement>(`[data-credit-cohort-id="${creditCohort.id}"]`)!);await select(action);await fill('Nominal saldo kredit','80')
    if(action==='APPLY'){await click(button('Cari invoice tujuan kredit'));await click(container.querySelector<HTMLElement>(`[data-credit-target-id="${creditTarget}"]`)!)}
    else{await click(button('Cari rekening kredit'));await click(container.querySelector<HTMLElement>(`[data-credit-cash-id="${creditBank.id}"]`)!)}
  }
  await fill('Waktu transaksi saldo kredit WIB','2026-10-20T10:00:00.123');await fill('Alasan tindakan saldo kredit','Kredit pelanggan sudah diperiksa')
  if(quote){await click(button('Periksa transaksi kredit'));expect(summary()).not.toBeNull();await click(input('Transaksi kredit sudah diperiksa'));expect(button('Simpan transaksi kredit').disabled).toBe(false)}
}

describe('consumer UI parent/recovery with declared server contracts',()=>{
  it('names the replacement on an original APPLY undo and carries the exact current version through the owning facade',async()=>{
    await prepare('UNDO',false)
    const usual=client.rpc.getMockImplementation()!,current=creditId(83)
    const checked=()=>{const q=creditReview({...creditPayloadForUi(),action:'UNDO',cohort_id:null,target_sale_id:null,restores_event_id:original.id,amount:null},original)
      return {...q,selection:{...q.selection,target_sale_id:current,target_root_sale_id:creditTarget,target_current_leaf_id:current},expected_versions:{[creditSale]:creditVersion,[current]:'17'},
        target_assignment:{contract_version:'cp7.note-credit-target-assignment.v1' as const,root_sale_id:creditTarget,historical_target_id:creditTarget,current_sale_id:current,current_number:'INV-TARGET-R1',revision_id:creditId(84),original_event_id:original.id,proof_sha256:'d'.repeat(64)}}}
    client.rpc.mockImplementation(async(name,args)=>{
      if(name==='erp_cp7_get_customer_credit_review_v1')return {data:checked(),error:null}
      if(name==='erp_cp7_customer_credit_command_v1'){++commits;return {data:creditOutcome(args.p_request,checked()),error:null}}
      return usual(name,args)
    })
    await click(button('Periksa transaksi kredit'));expect(summary()?.textContent).toContain('invoice pengganti INV-TARGET-R1')
    await click(input('Transaksi kredit sudah diperiksa'));await click(button('Simpan transaksi kredit'))
    expect(sends()).toHaveLength(1);expect(sends()[0][1].p_expected_versions).toEqual({[creditSale]:creditVersion,[current]:'17'})
    expect(sends()[0][1].p_payload).toMatchObject({restores_event_id:original.id,target_sale_id:null,amount:null})
    expect(commits).toBe(1);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined()
  })
  it.each(['APPLY','REFUND','UNDO']as const)('sends %s once through its owning facade, retains exact versions and retires the form',async action=>{
    await prepare(action);await click(button('Simpan transaksi kredit'))
    expect(sends()).toHaveLength(1);const sent=sends()[0][1]
    expect(sent.p_expected_versions[creditSale]).toBe(creditVersion)
    expect(sent.p_payload).toMatchObject({action,physical_at:'2026-10-20T10:00:00.123+07:00',quote_sha256:'b'.repeat(64)})
    if(action==='UNDO')expect(sent.p_payload).toMatchObject({restores_event_id:original.id,amount:null,cohort_id:null,target_sale_id:null,cash_account_id:null})
    else expect(sent.p_payload.amount).toBe('80.00')
    expect(client.rpc.mock.calls.some(([name])=>name==='erp_cp7_save_sale_v1')).toBe(false)
    expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined();expect(commits).toBe(1)
    expect(container.querySelector('[aria-label="Saldo kredit pelanggan"]')).toBeNull();expect(button('Saldo kredit pelanggan').disabled).toBe(false)
  })
  it('retains original UUID/payload/version map through loss, remount, permission refusal and exact replay without requoting',async()=>{
    loseReply=true;await prepare();await click(button('Simpan transaksi kredit'))
    const frozen=structuredClone(readProductionRecovery(scope()).pending.SALES);expect(frozen?.action).toBe('CREDIT_APPLY')
    const quoteCount=client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_get_customer_credit_review_v1').length
    expect(button('Buat invoice').disabled).toBe(true);await act(async()=>root.unmount());root=createRoot(container)
    denyReplay=true;allow();(auth.current as typeof recoveryIdentity).identity.permissions=permissions.filter(p=>p!=='sales.payment.post')
    await mount();await click(button('Reconcile transaksi'));expect(readProductionRecovery(scope()).pending.SALES).toEqual(frozen)
    denyReplay=false;allow();await mount();await click(button('Reconcile transaksi'))
    expect(sends()).toHaveLength(3);for(const call of sends().slice(1))expect(call[1]).toEqual(sends()[0][1])
    expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_get_customer_credit_review_v1')).toHaveLength(quoteCount)
    expect(commits).toBe(1);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined()
  })
  it('retires a checked intent synchronously when an input changes before the next React render',async()=>{
    await prepare();const save=button('Simpan transaksi kredit'),field=input('Nominal saldo kredit')
    expect(field.maxLength).toBe(-1)
    await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(field,'81');field.dispatchEvent(new Event('input',{bubbles:true}));save.click()});await flush()
    expect(sends()).toHaveLength(0);expect(summary()).toBeNull()
  })
  it('rejects an old quote after the parent source read is invalidated and replaced',async()=>{
    holdQuote=true;await prepare('APPLY',false);await click(button('Periksa transaksi kredit'));expect(delayQuote).not.toBeNull()
    await click(button('Muat ulang invoice'))
    const q=creditReview({...creditPayloadForUi(),physical_at:'2026-10-20T10:00:00.123+07:00'})
    await act(async()=>delayQuote!({data:q,error:null}));await flush()
    expect(summary()).toBeNull();expect(sends()).toHaveLength(0);expect(input('Nominal saldo kredit').value).toBe('80')
  })
  it('hides old private source facts on a real-shaped quote403 while preserving operator input',async()=>{
    denyQuote=true;await prepare('APPLY',false);await click(button('Periksa transaksi kredit'))
    expect(summary()).toBeNull();expect(sends()).toHaveLength(0);expect(container.textContent).not.toContain('Pelanggan privat')
    expect(container.textContent).not.toContain('PRIVATE source revoked');expect(input('Nominal saldo kredit').value).toBe('80')
    expect(button('Periksa transaksi kredit').disabled).toBe(true)
  })
  it('keeps an inconsistent success uncertain, then validates the saved historical receipt on replay',async()=>{
    wrongReceipt=true;await prepare();await click(button('Simpan transaksi kredit'));const frozen=structuredClone(readProductionRecovery(scope()).pending.SALES)
    expect(frozen?.action).toBe('CREDIT_APPLY');wrongReceipt=false;await click(button('Reconcile transaksi'))
    expect(sends()).toHaveLength(2);expect(sends()[1][1]).toEqual(sends()[0][1]);expect(commits).toBe(1);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined()
  })
  it('retains global writer locks after a verified commit whose authoritative refresh fails',async()=>{
    readFailure=true;await prepare();await click(button('Simpan transaksi kredit'))
    expect(commits).toBe(1);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined();expect(container.textContent).toContain('refresh authoritative gagal')
    expect(container.querySelector('[aria-label="Saldo kredit pelanggan"]')).toBeNull();expect(button('Buat invoice').disabled).toBe(true)
    readFailure=false;await click(button('Muat ulang invoice'));expect(button('Saldo kredit pelanggan').disabled).toBe(false);expect(sends()).toHaveLength(1)
  })
  it('names why an undo or new use is refused when a return on the target invoice depends on it (OW-04b slice C)',async()=>{
    refusalCode='CP7_CREDIT_CONSUMER_FAMILY_ADJUSTMENT_REVIEW_REQUIRED';refuseInitial=true;await prepare();await click(button('Simpan transaksi kredit'))
    expect(commits).toBe(0);expect(container.textContent).toContain('retur pada invoice tujuan ikut dihitung dari saldo yang dipakai')
    expect(container.textContent).toContain('Langkah berikutnya: biarkan pemakaian saldo ini')
  })
  it('keeps editable input after a definite rollback, requires fresh source choices, and allows a reviewed retry',async()=>{
    refuseInitial=true;await prepare();await click(button('Simpan transaksi kredit'))
    expect(commits).toBe(0);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined();expect(input('Nominal saldo kredit').value).toBe('80')
    expect(summary()).toBeNull();expect(button('Periksa transaksi kredit').disabled).toBe(true)
    refuseInitial=false;await click(button('Periksa saldo dari retur'));await click(container.querySelector<HTMLElement>(`[data-credit-cohort-id="${creditCohort.id}"]`)!)
    await click(button('Cari invoice tujuan kredit'));await click(container.querySelector<HTMLElement>(`[data-credit-target-id="${creditTarget}"]`)!)
    await click(button('Periksa transaksi kredit'));await click(input('Transaksi kredit sudah diperiksa'));await click(button('Simpan transaksi kredit'));expect(commits).toBe(1)
  })
})
function creditPayloadForUi():CreditPayload {return {action:'APPLY',cohort_id:creditCohort.id,target_sale_id:creditTargetRow.id,cash_account_id:null,restores_event_id:null,amount:'80.00',physical_at:'2026-10-20T10:00:00.123+07:00',reason:'Kredit pelanggan sudah diperiksa',reference:null}}
