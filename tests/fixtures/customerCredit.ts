/** Declared client-test stand-ins only. No Native/Auth/financial qualification. */
import type {CreditPayload,CreditReview,CreditEvent,CreditWorkspace,CreditPageKind,CreditOutcome,CreditSource} from '../../src/customerCreditContract'
export const creditId=(n:number)=>`11111111-1111-4111-8111-${String(n).padStart(12,'0')}`
export const creditActor=creditId(99),creditSale=creditId(1),creditCustomer=creditId(2),creditTarget=creditId(3)
export const creditVersion='9007199254740993',creditTargetVersion='9007199254740997',creditToken='a'.repeat(32)
export function creditSource(version=creditVersion,token=creditToken):CreditSource {
  return {id:creditSale,number:'INV-SOURCE',customer_id:creditCustomer,customer_name:'Pelanggan privat',location_id:creditId(4),location_name:'Gudang',
    physical_at:'2026-10-18T03:00:00Z',due_date:null,status:'PAID',row_version:version,notes:null,payment_terms:null,line_count:'1',qty_pcs:'10',reserved_qty:'0',returned_qty:'2',review_token:token,
    financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'1000.00',return_total:'200.00',net_total:'800.00',paid_total:'800.00',open_balance:'0.00'},
    items:[{id:creditId(5),product_id:creditId(6),product_sku:'SKU-1',commercial_sku:'SKU-1',product_name:'Barang',size_code:'S',brand_name:'Vivo',qty_pcs:'10',notes:null,financial:{unit_price:'100.00',discount:'0.00',line_total:'1000.00'}}]}
}
export const creditCohort={id:creditId(10),return_id:creditId(11),return_number:'RET-SOURCE',available_credit:'200.00',credit_account:{id:creditId(13),code:'2109',name:'Saldo kredit pelanggan'}}
export const creditBank={id:creditId(12),code:'1102',name:'Bank pengembalian',kind:'BANK'}
export const creditTargetRow={id:creditTarget,number:'INV-TARGET',customer_id:creditCustomer,row_version:creditTargetVersion,physical_at:'2026-10-18T04:00:00Z',status:'POSTED' as const,open_balance:'500.00'}
export function creditEvent(kind:'APPLY'|'REFUND'='APPLY',amount='80.00'):CreditEvent {
  return {id:creditId(20),cohort_id:creditCohort.id,kind,amount,physical_at:'2026-10-19T03:00:00.123456Z',economic_date:'2026-10-19',book_date:'2026-10-19',return_number:'RET-SOURCE',
    target_sale_id:kind==='APPLY'?creditTarget:null,target_number:kind==='APPLY'?'INV-TARGET':null,
    cash_account_id:kind==='REFUND'?creditBank.id:null,cash_name:kind==='REFUND'?creditBank.name:null,restores_event_id:null,undone_by:null}
}
export function creditPayload(action:CreditPayload['action']='APPLY'):CreditPayload {
  return {action,cohort_id:action==='UNDO'?null:creditCohort.id,target_sale_id:action==='APPLY'?creditTarget:null,cash_account_id:action==='REFUND'?creditBank.id:null,
    restores_event_id:action==='UNDO'?creditEvent().id:null,amount:action==='UNDO'?null:'80.00',physical_at:'2026-10-20T10:00:00.123456+07:00',reason:'Transaksi kredit sudah diperiksa',reference:null}
}
export function creditReview(p=creditPayload(),original=creditEvent()):CreditReview {
  const kind=p.action==='UNDO'?original.kind:p.action,frac=(/\.(\d+)/.exec(p.physical_at)?.[1]??'').padEnd(6,'0')
  const physical=new Date(p.physical_at).toISOString().slice(0,-1)+frac.slice(3)+'Z'
  const economic=new Date(Date.parse(physical)+7*60*60*1000).toISOString().slice(0,10)
  return {contract_version:'cp7.customer-credit-review.v1',read_only:true,selection:{action:p.action,event_kind:kind,cohort_id:creditCohort.id,customer_id:creditCustomer,
    source_sale_id:creditSale,source_root_sale_id:creditSale,source_current_leaf_id:creditSale,
    target_sale_id:kind==='APPLY'?creditTarget:null,target_root_sale_id:kind==='APPLY'?creditTarget:null,target_current_leaf_id:kind==='APPLY'?creditTarget:null,
    cash_account_id:kind==='REFUND'?creditBank.id:null,restores_event_id:p.restores_event_id,amount:p.action==='UNDO'?`-${original.amount}`:p.amount!},
    physical_at:physical,economic_date:economic,transaction_date:economic,book_basis:{selected_book_date:economic},available_credit_after:p.action==='UNDO'?'200.00':'120.00',
    expected_versions:{[creditSale]:creditVersion,...(kind==='APPLY'?{[creditTarget]:creditTargetVersion}:{})},quote_sha256:'b'.repeat(64)}
}
export function creditOutcome(request:string,review:CreditReview):CreditOutcome {
  const s=review.selection
  return {contract_version:'cp7.customer-credit-outcome.v1',kind:'COMMITTED_OUTCOME',request_id:request,operation_id:creditId(50),consumption_event_id:creditId(50),journal_id:creditId(51),
    action:s.action,event_kind:s.event_kind,cohort_id:s.cohort_id,source_sale_id:s.source_sale_id,target_sale_id:s.target_sale_id,cash_account_id:s.cash_account_id,
    restores_event_id:s.restores_event_id,amount:s.amount,physical_at:review.physical_at,economic_date:review.economic_date,transaction_date:review.transaction_date,
    available_credit:review.available_credit_after,invoice_versions:Object.fromEntries(Object.entries(review.expected_versions).map(([id,v])=>[id,(BigInt(v)+(id===s.source_sale_id||id===s.target_sale_id?1n:0n)).toString()]))}
}
export function creditWorkspace<K extends CreditPageKind>(kind:K,source=creditSource(),events=[creditEvent()]):CreditWorkspace<K> {
  const rows={COHORTS:[creditCohort],TARGETS:[creditTargetRow],CASH:[creditBank],EVENTS:events}[kind]
  return {contract_version:'cp7.customer-credit-workspace.v1',actor_scope_id:creditActor,read_at:'2026-10-20T03:00:00.000001Z',read_only:true,business_DML:false,kind,q:'',
    source:{sale_id:source.id,number:source.number,customer_id:source.customer_id,row_version:source.row_version,review_token:source.review_token!},
    capabilities:{apply:true,refund:true,undo_apply:true,undo_refund:true},dataset_sha256:'c'.repeat(64),
    page:{offset:0,limit:25,total:rows.length.toString(),next_offset:null,rows}}as CreditWorkspace<K>
}
