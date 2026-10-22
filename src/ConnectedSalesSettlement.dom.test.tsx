// @vitest-environment jsdom
/** Parent/recovery integration with declared server stand-ins, never Native proof. */
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedSalesPage from './ConnectedSalesPage'
import {readProductionRecovery} from './productionRecovery'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import type {AccountOptionsQuery,QuoteInput} from './salesReturnSettlementContract'

const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id=(n:number)=>`11111111-1111-4111-8111-${String(n).padStart(12,'0')}`,sha=(n:number)=>String(n).repeat(64)
const sale=id(1),allocation=id(3),creditAccount=id(4),cashAccount=id(5),destination=id(6),payment=id(8)
const version='9007199254740993',afterVersion='9007199254740994',reviewToken='a'.repeat(32),afterReview='b'.repeat(32)
let committed:boolean,unpaid:boolean,loseReply:boolean,lost:boolean,replayDenied:boolean,wrongReceipt:boolean,reloadFails:boolean,quoteDenied:boolean,accountFacts:number
let quoteRefusal:unknown,settleRefusal:unknown
function source(){return{sale_id:sale,sale_number:'INV-PAID',customer_id:id(2),customer_name:'Toko pemilik invoice',row_version:version,review_token:reviewToken}}
function workspace(selected=true){
  // The reviewed reader03 server transform supplies E. This fixture never
  // relabels or mutates the raw original P1000 payment history below.
  const financial={basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'1000.00',return_total:committed?'200.00':'0.00',net_total:committed?'800.00':'1000.00',paid_total:unpaid?'0.00':committed?'800.00':'1000.00',open_balance:unpaid?committed?'800.00':'1000.00':'0.00'}
  const row={id:sale,number:'INV-PAID',customer_id:id(2),customer_name:'Toko pemilik invoice',location_id:id(7),location_name:'Gudang FG',physical_at:'2026-10-17T03:00:00.000Z',due_date:null,status:unpaid?'POSTED':'PAID',row_version:committed?afterVersion:version,notes:null,payment_terms:null,line_count:'1',qty_pcs:'5',reserved_qty:'0',returned_qty:committed?'1':'0',financial}
  return{contract_version:'cp7.sales-workspace.v1',read_at:'2026-10-20T01:00:00.000Z',financial_captured:true,read_only:true,page:{rows:[row],total:'1',offset:0,limit:25,next_offset:null},detail:selected?{...row,review_token:committed?afterReview:reviewToken,items:[{id:id(9),product_id:id(10),product_sku:'PHYSICAL-32',commercial_sku:'JEANS-32',product_name:'Celana',size_code:'32',brand_name:'Vivo',qty_pcs:'5',notes:null,financial:{unit_price:'200.00',discount:'0.00',line_total:'1000.00'}}]}:null}
}
function returns(kind:string){
  const rows=kind==='ALLOCATIONS'?[{allocation_id:allocation,sale_item_id:id(9),product_id:id(10),product_sku:'PHYSICAL-32',commercial_sku:'JEANS-32',product_name:'Celana',size_code:'32',lot_id:id(11),lot_number:'LOT-1',source_location_name:'Gudang FG',allocated_qty:'5',returned_qty:'0',remaining_qty:'5',sale_item_qty:'5',sale_item_net:'1000.00'}]:kind==='LOCATIONS'?[{id:destination,name:'Gudang retur'}]:[]
  return{contract_version:'cp7.sales-returns.v1',sale_id:sale,row_version:version,review_token:reviewToken,kind,page:{rows,total:String(rows.length),offset:0,limit:25,next_offset:null}}
}
const originalPayment={id:payment,number:'PAY-ORIGINAL',physical_at:'2026-10-18T03:00:00.000Z',amount:'1000.00',cash_account_id:cashAccount,cash_account_name:'Bank asal',method:'BANK_TRANSFER',reference:'PAY-1000',notes:null,status:'POSTED',replaces_payment_id:null}
function account(kind:'CREDIT'|'CASH'){return{id:kind==='CREDIT'?creditAccount:cashAccount,code:kind==='CREDIT'?'2109':'1102',name:kind==='CREDIT'?'Saldo kredit pelanggan':'Bank pengembalian',facts_sha256:sha(accountFacts)}}
function options(q:AccountOptionsQuery){return{contract_version:'cp7.sales-return-settlement-options.v1',kind:'ACCOUNT_OPTIONS',read_only:true,business_DML:false,captured_at:'2026-10-20T01:00:00.000Z',source:source(),account_kind:q.account_kind,q:q.q,rows:[account(q.account_kind)],total:'1',offset:q.offset,limit:25,next_offset:null}}
function quote(q:QuoteInput):any{
  const c=q.settlement,issues:string[]=[]
  if(!unpaid){if(!c.mode)issues.push('CHOOSE_MODE');if(!c.credit_account_id)issues.push('CHOOSE_CREDIT_ACCOUNT');if(c.mode==='REFUND'&&!c.cash_account_id)issues.push('CHOOSE_REFUND_ACCOUNT');if(c.mode==='REFUND'&&!c.refund_physical_at)issues.push('ENTER_REFUND_TIME')}
  else if(c.mode||c.credit_account_id)issues.push('CLEAR_UNNEEDED_SETTLEMENT')
  return{contract_version:'cp7.sales-return-settlement-quote.v1',kind:'QUOTE',read_only:true,business_DML:false,captured_at:'2026-10-20T01:00:00.000Z',input_echo:structuredClone(q),source:source(),
    binding:{immutable_source_sha256:sha(1),current_state_sha256:sha(2),draft_sha256:sha(3),choice_sha256:sha(4),projection_sha256:sha(5),authority_sha256:sha(6),period_sha256:sha(7),dependency_sha256:sha(8),quote_sha256:issues.length?null:sha(accountFacts===6?8:9)},has_recognition_effect:!unpaid,current_credit_amount:unpaid?'0.00':'200.00',components:unpaid?[]:[{component_key:sha(1),economic_date:'2026-10-19',book_date:'2026-10-19',signed_amount:'200.00',support_sha256:sha(2)}],
    return_projection:{economic_date:'2026-10-19',prior_causal:{contract_version:'ow04.prior-causal-book-proof.v1',scope:'PRIOR_CAUSAL_SALE_RETURN',state:'DATED',causal_book_floor:'2026-10-18',proof_sha256:sha(6)},journal_effect:'JOURNAL_EXPECTED',planned_book_date:'2026-10-19',return_amount:'200.00',hpp_amount:'10.00',receivable_account_id:id(12)},
    totals:{before:{gross_total:'1000.00',return_total:'0.00',net_total:'1000.00',payments_received:unpaid?'0.00':'1000.00',credit_applied:'0.00',credit_recognized:'0.00',effective_paid:unpaid?'0.00':'1000.00',receivable_remaining:unpaid?'1000.00':'0.00'},after:{gross_total:'1000.00',return_total:'200.00',net_total:'800.00',payments_received:unpaid?'0.00':'1000.00',credit_applied:'0.00',credit_recognized:unpaid?'0.00':'200.00',effective_paid:unpaid?'0.00':'800.00',receivable_remaining:unpaid?'800.00':'0.00'}},credit_account:c.credit_account_id?account('CREDIT'):null,cash_account:c.cash_account_id?account('CASH'):null,
    refund_projection:c.mode==='REFUND'?{amount:'200.00',physical_at:c.refund_physical_at,economic_date:c.refund_physical_at?'2026-10-20':null,book_date:c.refund_physical_at?'2026-10-20':null,safe_capacity:c.refund_physical_at?'200.00':null,capacity_sha256:c.refund_physical_at?sha(7):null}:null,
    capabilities:{record_return:true,recognize_credit:true,refund_cash:true},readiness:{state:issues.length?'CHOICE_REQUIRED':'READY',issues}}
}
function receipt(request:string,payload:any){return{contract_version:'cp7.sales-return-settlement-outcome.v1',kind:'COMMITTED_OUTCOME',action:'RETURN_SETTLEMENT',request_id:request,sale_id:sale,return_id:id(20),return_status:'POSTED',row_version:afterVersion,family_ordinal:'1',credit_id:payload.settlement?id(21):null,refund_event_id:payload.settlement?.mode==='REFUND'?id(22):null,quote_sha256:wrongReceipt?sha(7):payload.quote_sha256,projection_sha256:sha(5),actual_manifest_sha256:sha(3),projection_actual_proof_sha256:sha(4),production_go:false}}
function allow(){const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view','finance.ar.view','sales.return.view','sales.return.create','sales.return.post','sales.payment.view');state.auth=a}
// OW-09: declared reader stand-ins echo the whole-invoice history list they applied, like the readers do.
const historyList=<T extends {page:object}>(r:T,q:Record<string,unknown>)=>{if('history_order' in q)Object.assign(r.page,{list:{q:q.history_q,status:q.history_status,order:q.history_order}});return r}
const paymentList=(q:Record<string,unknown>)=>'payment_order' in q?{list:{q:q.payment_q,status:q.payment_status,order:q.payment_order}}:{}
let root:Root,container:HTMLDivElement
beforeEach(()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,_options:unknown,callback:(lock:unknown)=>Promise<unknown>)=>callback({})}})
  committed=unpaid=loseReply=lost=replayDenied=wrongReceipt=reloadFails=quoteDenied=false;accountFacts=5;quoteRefusal=settleRefusal=null;allow();client.rpc.mockReset()
  client.rpc.mockImplementation(async(name,args)=>{
    if(name==='erp_cp7_get_sales_v1')return reloadFails&&committed?{data:null,error:{message:'Authoritative read unavailable'}}:{data:workspace(Boolean(args.p_query.sale_id)),error:null}
    if(name==='erp_cp7_get_sales_returns_v1')return{data:historyList(returns(args.p_query.kind),args.p_query),error:null}
    if(name==='erp_cp7_get_sales_return_settlement_quote_v1'){if(quoteRefusal)return{data:null,error:quoteRefusal};if(quoteDenied)return{data:null,error:{status:403,code:'42501',message:'PRIVATE source revoked'}};return{data:args.p_query.kind==='ACCOUNT_OPTIONS'?options(args.p_query):quote(args.p_query),error:null}}
    if(name==='erp_cp7_settle_sales_return_v1'){if(settleRefusal)return{data:null,error:settleRefusal};if(replayDenied)return{data:null,error:{code:'42501',message:'CP7_CREDIT_ACCESS_CHANGED'}};committed=true;if(loseReply&&!lost){lost=true;throw Error('Declared lost response after committed settlement')}return{data:receipt(args.p_request,args.p_payload),error:null}}
    if(name==='erp_cp7_get_sales_cash_v1')return{data:{contract_version:'cp7.sales-cash.v1',sale_id:sale,row_version:committed?afterVersion:version,review_token:committed?afterReview:reviewToken,payments:{rows:[structuredClone(originalPayment)],total:'1',offset:0,limit:25,next_offset:null,...paymentList(args.p_query)},cash_accounts:{rows:[],total:'0',offset:0,limit:25,next_offset:null}},error:null}
    throw Error(`Unowned test route ${name}`)
  })
  container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks')})
const flush=async()=>act(async()=>{await new Promise(resolve=>setTimeout(resolve,0))})
const button=(name:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===name)!
const field=(name:string)=>container.querySelector<HTMLInputElement>(`input[aria-label="${name}"]`)!
const summary=()=>container.querySelector('[aria-label="Hasil pemeriksaan penyelesaian retur"]')
async function click(e:HTMLElement){expect(e).toBeTruthy();await act(async()=>e.click());await flush()}
async function fill(name:string,value:string){await act(async()=>{const e=field(name);expect(e).not.toBeNull();Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function select(mode:string){await act(async()=>{const e=container.querySelector<HTMLSelectElement>('select[aria-label="Penyelesaian nilai retur"]')!;expect(e).not.toBeNull();e.value=mode;e.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
async function mount(){await act(async()=>root.render(<ConnectedSalesPage view="sales-returns" initialSaleId={sale}/>));await flush()}
async function open(time=true){await mount();await click(button('Retur fisik invoice'));expect(field('Waktu retur pelanggan WIB').value).toBe('');await fill('Nomor retur pelanggan','RET-PAID');await click(button('Gudang retur'));await click(container.querySelector<HTMLElement>('[aria-label="Pilih alokasi retur"] .cproc-receipt')!);await fill('Jumlah retur 1','1');await fill('Nilai retur 1','200');if(time)await fill('Waktu retur pelanggan WIB','2026-10-19T10:00')}
async function ready(mode:'CREDIT'|'REFUND'='CREDIT'){
  await open();await select(mode);await click(button('Cari akun saldo kredit pelanggan'));await click(button('2109 · Saldo kredit pelanggan'))
  if(mode==='REFUND'){expect(field('Waktu pengembalian uang WIB').value).toBe('');await click(button('Cari rekening pengembalian uang'));await click(button('1102 · Bank pengembalian'));await fill('Waktu pengembalian uang WIB','2026-10-20T00:01')}
  await click(button('Periksa penyelesaian retur'));expect(summary()).not.toBeNull();await click(field('Retur pelanggan sudah diperiksa'));expect(button('Catat retur dan penyelesaian').disabled).toBe(false)
}
const sends=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_settle_sales_return_v1')
const scope=()=>`${recoveryIdentity.runtime.projectRef}:${recoveryIdentity.identity.profile.id}`

describe('OW04 real parent/section/recovery wiring with explicit mocked server contracts',()=>{
  it.each(['CREDIT','REFUND'] as const)('routes %s to fixed facade and refreshes E800/AR0 while raw payment history stays P1000',async mode=>{
    await ready(mode);await click(button('Catat retur dan penyelesaian'));expect(sends()).toHaveLength(1);const sent=sends()[0][1]
    expect(sent.p_expected).toBe(version);expect(sent.p_payload).toMatchObject({sale_id:sale,review_token:reviewToken,return_number:'RET-PAID',physical_at:'2026-10-19T03:00:00.000Z',quote_sha256:sha(9),items:[{allocation_id:allocation,location_id:destination,qty_pcs:'1',refund_amount:'200.00'}],settlement:{mode,credit_account_id:creditAccount}})
    if(mode==='REFUND')expect(sent.p_payload.settlement).toMatchObject({cash_account_id:cashAccount,refund_physical_at:'2026-10-19T17:01:00.000Z'})
    expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined();expect(container.querySelector('[aria-label="Retur fisik invoice"]')).toBeNull()
    expect(container.querySelector('[aria-label="Nilai invoice"]')?.textContent).toContain('Pelunasan efektif invoice Rp800');expect(container.textContent).toContain('Sisa pembayaran Rp0')
    await click(button('Pembayaran invoice'));expect(container.querySelector(`[data-payment-id="${payment}"] h4`)?.textContent).toBe('PAY-ORIGINAL · Rp1.000')
  })
  it('keeps physical time blank and blocks native form-submit from bypassing the quote',async()=>{
    await open(false);expect(button('Periksa penyelesaian retur').disabled).toBe(true);expect(button('Catat retur pelanggan')).toBeUndefined()
    await act(async()=>container.querySelector('form[aria-label="Catat retur pelanggan"]')!.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));await flush();expect(sends()).toHaveLength(0);expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false)
    await fill('Waktu retur pelanggan WIB','2026-10-19T10:00');expect(button('Periksa penyelesaian retur').disabled).toBe(false);await click(button('Periksa penyelesaian retur'));expect(container.textContent).toContain('Pilih penyelesaian nilai retur.');expect(button('Catat retur dan penyelesaian').disabled).toBe(true)
  })
  it('quotes a truly empty unpaid credit plan and still sends null settlement through the fixed wrapper',async()=>{
    unpaid=true;await open();await click(button('Periksa penyelesaian retur'));expect(summary()).not.toBeNull();expect(container.textContent).toContain('Retur ini tidak membentuk saldo kredit');await click(field('Retur pelanggan sudah diperiksa'));await click(button('Catat retur dan penyelesaian'))
    expect(sends()).toHaveLength(1);expect(sends()[0][1].p_payload.settlement).toBeNull();expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false);expect(container.textContent).toContain('Sisa pembayaran Rp800')
  })
  it('bumps parent generation for same UUID re-selection so changed eligibility can be requoted and reviewed',async()=>{
    await ready();accountFacts=6;await click(button('Cari akun saldo kredit pelanggan'));await click(button('2109 · Saldo kredit pelanggan'))
    expect(summary()).toBeNull();expect(field('Retur pelanggan sudah diperiksa').checked).toBe(false);expect(button('Catat retur dan penyelesaian').disabled).toBe(true);expect(button('Periksa penyelesaian retur').disabled).toBe(false)
    await click(button('Periksa penyelesaian retur'));expect(summary()).not.toBeNull();expect(field('Retur pelanggan sudah diperiksa').checked).toBe(false);await click(field('Retur pelanggan sudah diperiksa'));await click(button('Catat retur dan penyelesaian'));expect(sends()[0][1].p_payload.quote_sha256).toBe(sha(8))
  })
  it('retires the old intent synchronously when a draft input changes before React renders the next generation',async()=>{
    await ready();const submit=button('Catat retur dan penyelesaian'),amount=field('Nilai retur 1')
    await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(amount,'100');amount.dispatchEvent(new Event('input',{bubbles:true}));submit.click()});await flush()
    expect(sends()).toHaveLength(0);expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false);expect(summary()).toBeNull();expect(field('Retur pelanggan sudah diperiksa').checked).toBe(false)
  })
  it('retains exact envelope across lost reply/remount/replay denial, then reconciles without an in-memory quote',async()=>{
    loseReply=true;await ready();await click(button('Catat retur dan penyelesaian'));const frozen=structuredClone(readProductionRecovery(scope()).pending.SALES);expect(frozen?.action).toBe('RETURN_SETTLEMENT');expect(frozen?.expectedVersion).toBeNull();expect((frozen?.payload as any).expected_version).toBe(version);const quoteReads=client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_sales_return_settlement_quote_v1').length
    await act(async()=>root.unmount());root=createRoot(container);replayDenied=true;(state.auth as typeof recoveryIdentity).identity.permissions=(state.auth as typeof recoveryIdentity).identity.permissions.filter(p=>p!=='sales.return.post');await mount();await click(button('Reconcile transaksi'));expect(readProductionRecovery(scope()).pending.SALES).toEqual(frozen)
    replayDenied=false;allow();await mount();await click(button('Reconcile transaksi'));expect(sends()).toHaveLength(3);expect(sends()[1][1]).toEqual(sends()[0][1]);expect(sends()[2][1]).toEqual(sends()[0][1]);expect(client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_get_sales_return_settlement_quote_v1')).toHaveLength(quoteReads);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined();expect(container.textContent).toContain('Pelunasan efektif invoice Rp800')
  })
  it('keeps a wrong-quote success uncertain and validates the frozen digest on replay',async()=>{
    wrongReceipt=true;await ready();await click(button('Catat retur dan penyelesaian'));const frozen=structuredClone(readProductionRecovery(scope()).pending.SALES);expect(frozen?.action).toBe('RETURN_SETTLEMENT');expect(button('Reconcile transaksi')).toBeDefined();wrongReceipt=false;await click(button('Reconcile transaksi'));expect(sends()).toHaveLength(2);expect(sends()[1][1]).toEqual(sends()[0][1]);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined()
  })
  it('retires the committed form and keeps all writers locked until authoritative reload succeeds',async()=>{
    reloadFails=true;await ready();await click(button('Catat retur dan penyelesaian'));expect(sends()).toHaveLength(1);expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined();expect(container.querySelector('[aria-label="Retur fisik invoice"]')).toBeNull();expect(container.textContent).toContain('refresh authoritative gagal');expect(button('Retur fisik invoice')).toBeUndefined()
    reloadFails=false;await click(button('Muat ulang invoice'));expect(button('Retur fisik invoice').disabled).toBe(false);expect(sends()).toHaveLength(1)
  })
  it('retires source facts on a current quote403 and never falls back to the legacy RETURN route',async()=>{
    await open();quoteDenied=true;await click(button('Periksa penyelesaian retur'));expect(sends()).toHaveLength(0);expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false);expect(container.querySelector('[aria-label="Retur fisik invoice"]')).toBeNull();expect(container.textContent).not.toContain('Toko pemilik invoice');expect(container.textContent).not.toContain('PRIVATE source revoked')
  })
})

// OW-04b (retest 23 Oct 2026) parts 3 and 4 on the real sales page: a refusal names its reason and next step; a cash
// refund refused by the dated cash guard records nothing and says which bank and date. Server stand-ins, not Native.
describe('OW04b refused return settlement on the sales page',()=>{
  it('names why a second return on a credit invoice cannot be settled yet and what to do next',async()=>{
    quoteRefusal={code:'P0001',message:'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED',hint:null,
      details:'{"action": null, "reasons": ["PRIOR_CREDIT_RETURN"], "refusal": "INITIAL_SOURCE_FAMILY", "contract": "cp7.credit-followups.refusal.v1", "source_blockers": []}'}
    await open();await click(button('Periksa penyelesaian retur'))
    expect(container.textContent).toContain('Retur ini belum bisa dicatat dan diselesaikan (uang kembali atau saldo kredit) pada invoice ini.')
    expect(container.textContent).toContain('Alasannya: invoice ini sudah punya retur yang menjadi saldo kredit pelanggan atau uang kembali.')
    expect(container.textContent).toContain('Langkah berikutnya:');expect(container.textContent).not.toContain('belum dapat diperiksa')
    expect(sends()).toHaveLength(0);expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false);expect(summary()).toBeNull()
  })
  it('shows the bank, shortfall and date when a refund is refused for lack of cash, and records nothing',async()=>{
    settleRefusal={code:'P0001',message:'CP7_CASH_NEGATIVE: saldo Bank pengembalian (1102) menjadi minus -200.00 pada tanggal 2026-10-20 atau sesudahnya (tanggal ekonomi). Kas/bank tidak boleh minus; catat dulu uang masuk atau pilih rekening lain.'}
    await ready('REFUND');await click(button('Catat retur dan penyelesaian'));expect(sends()).toHaveLength(1);expect(committed).toBe(false)
    expect(container.textContent).toContain('Saldo Bank pengembalian (1102) menjadi minus -200.00 pada tanggal 2026-10-20 atau sesudahnya (tanggal ekonomi). Kas/bank tidak boleh minus; catat dulu uang masuk atau pilih rekening lain.')
    expect(readProductionRecovery(scope()).pending.SALES).toBeUndefined();expect(container.textContent).not.toContain('Pelunasan efektif invoice Rp800')
    expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false)
  })
})
