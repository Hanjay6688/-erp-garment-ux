import {parseSalesPayment,parseSalesCashAccountPage,type SalesPayment,type SalesCashAccount} from './salesCashContract'
export type PaymentCorrectionLink={original_id:string;replacement_id:string;sale_id:string;actor_scope_id:string;request_id:string;reason:string;recorded_at:string;time_restatement:null|{neutral_journal_id:string;neutral_number:string;neutral_economic_date:string;neutral_transaction_date:string;effective_journal_id:string;effective_number:string;effective_economic_date:string;effective_transaction_date:string}}
type Relative={link:PaymentCorrectionLink;document:SalesPayment}
export type PaymentCorrectionWorkspace={contract_version:'cp7.sales-payment-correction-workspace.v1';captured_at:string;sale_id:string;row_version:string;review_token:string;document:SalesPayment;eligible:boolean;previous:Relative|null;next:Relative|null;cash_accounts:{rows:SalesCashAccount[];total:string;offset:number;limit:number;next_offset:number|null}}
const fail=():never=>{throw Error('Data koreksi pembayaran berubah atau belum lengkap. Muat ulang invoice sebelum melanjutkan.')}
const id=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const timestamp=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v))
const text=(v:unknown):v is string=>typeof v==='string'
const day=(v:unknown)=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(Object.keys(r).length!==keys.length||keys.some(k=>!(k in r)))fail();return r}
function link(v:unknown,saleId:string){
 const r=closed(v,['original_id','replacement_id','sale_id','actor_scope_id','request_id','reason','recorded_at','time_restatement'])
 if(!id(r.original_id)||!id(r.replacement_id)||r.original_id===r.replacement_id||r.sale_id!==saleId||!id(r.actor_scope_id)||!id(r.request_id)||!text(r.reason)||r.reason.trim().length<5||r.reason.length>1000||!timestamp(r.recorded_at))fail()
 if(r.time_restatement!==null){
  const t=closed(r.time_restatement,['neutral_journal_id','neutral_number','neutral_economic_date','neutral_transaction_date','effective_journal_id','effective_number','effective_economic_date','effective_transaction_date'])
  if(!id(t.neutral_journal_id)||!id(t.effective_journal_id)||t.neutral_journal_id===t.effective_journal_id||![t.neutral_number,t.effective_number].every(text))fail()
  for(const key of ['neutral_economic_date','neutral_transaction_date','effective_economic_date','effective_transaction_date'])if(!day(t[key]))fail()
 }
 return r as unknown as PaymentCorrectionLink
}
export function parsePaymentCorrectionWorkspace(v:unknown,source:{id:string;row_version:string;review_token?:string},paymentId:string,bankOffset=0):PaymentCorrectionWorkspace{
 const r=closed(v,['contract_version','captured_at','sale_id','row_version','review_token','document','eligible','previous','next','cash_accounts'])
 if(r.contract_version!=='cp7.sales-payment-correction-workspace.v1'||!timestamp(r.captured_at)||r.sale_id!==source.id||r.row_version!==source.row_version||r.review_token!==source.review_token||!text(r.review_token)||!/^[a-f0-9]{32}$/.test(r.review_token)||typeof r.eligible!=='boolean')fail()
 const document=parseSalesPayment(r.document);if(document.id!==paymentId||!timestamp(document.physical_at))fail()
 for(const key of ['previous','next']as const){if(r[key]===null)continue;const rel=closed(r[key],['link','document']),l=link(rel.link,source.id),d=parseSalesPayment(rel.document)
  if(!['POSTED','REVERSED'].includes(d.status)||key==='previous'&&(l.replacement_id!==paymentId||l.original_id!==d.id||d.status!=='REVERSED')||key==='next'&&(l.original_id!==paymentId||l.replacement_id!==d.id||document.status!=='REVERSED'))fail()
 }
 if(r.eligible&&(document.status!=='POSTED'||document.cash_account_id===null||document.replaces_payment_id!==null||!['CASH','BANK_TRANSFER'].includes(document.method??'')||r.next!==null))fail()
 parseSalesCashAccountPage(r.cash_accounts,bankOffset)
 return r as unknown as PaymentCorrectionWorkspace
}
export function parsePaymentCorrectionOutcome(v:unknown,requestId:string,saleId:string,originalPaymentId:string){
 const r=closed(v,['contract_version','kind','action','request_id','sale_id','status','row_version','payment_id','payment_status','original_payment_id','original_payment_status','link'])
 if(r.contract_version!=='cp7.sales-payment-correction.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!=='PAYMENT_CORRECT'||r.request_id!==requestId||r.sale_id!==saleId||r.original_payment_id!==originalPaymentId||!id(r.payment_id)||r.payment_id===originalPaymentId||r.payment_status!=='POSTED'||r.original_payment_status!=='REVERSED'||!['PARTIAL_PAID','PAID'].includes(String(r.status))||!text(r.row_version)||!/^[1-9][0-9]{0,18}$/.test(r.row_version))fail()
 const l=link(r.link,saleId);if(l.original_id!==originalPaymentId||l.replacement_id!==r.payment_id||l.request_id!==requestId)fail()
 return r as unknown as {sale_id:string;row_version:string;payment_id:string;link:PaymentCorrectionLink}
}
