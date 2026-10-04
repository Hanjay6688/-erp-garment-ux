import { parseSupplierPayment, type SupplierPayment, type SupplierPaymentRead } from './supplierPaymentContract'
import { parseSalesCashAccountPage, type SalesCashAccount } from './salesCashContract'
import type { Json } from './types/database.preconnect'
const fail=():never=>{throw Error('Perubahan pembayaran supplier belum lengkap atau sumbernya berubah. Muat ulang pembayaran.')}
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v)
const time=(v:unknown):v is string=>typeof v==='string'&&v.includes('T')&&Number.isFinite(Date.parse(v))
const date=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))return fail();return v as Record<string,unknown>}
function canonical(v:unknown):unknown{if(Array.isArray(v))return v.map(canonical);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical((v as Record<string,unknown>)[k])]));return v}
export type SupplierPaymentCorrectionLink={original_id:string;replacement_id:string;purchase_id:string;actor_scope_id:string;request_id:string;reason:string;recorded_at:string;time_restatement:null|{neutral_journal_id:string;neutral_number:string;neutral_economic_date:string;neutral_transaction_date:string;effective_journal_id:string;effective_number:string;effective_economic_date:string;effective_transaction_date:string}}
function link(v:unknown,purchaseId:string):SupplierPaymentCorrectionLink{
 const d=closed(v,['original_id','replacement_id','purchase_id','actor_scope_id','request_id','reason','recorded_at','time_restatement'])
 if(![d.original_id,d.replacement_id,d.purchase_id,d.actor_scope_id,d.request_id].every(uuid)||d.purchase_id!==purchaseId||d.original_id===d.replacement_id||typeof d.reason!=='string'||d.reason.trim().length<5||d.reason.length>1000||!time(d.recorded_at))fail()
 if(d.time_restatement!==null){const t=closed(d.time_restatement,['neutral_journal_id','neutral_number','neutral_economic_date','neutral_transaction_date','effective_journal_id','effective_number','effective_economic_date','effective_transaction_date']);if(!uuid(t.neutral_journal_id)||!uuid(t.effective_journal_id)||t.neutral_journal_id===t.effective_journal_id||![t.neutral_number,t.effective_number].every(x=>typeof x==='string'&&x.length>0)||![t.neutral_economic_date,t.neutral_transaction_date,t.effective_economic_date,t.effective_transaction_date].every(date))fail()}
 return d as unknown as SupplierPaymentCorrectionLink
}
export type SupplierPaymentCorrectionRead={contract_version:'cp7.supplier-payment-correction-workspace.v1';captured_at:string;purchase_id:string;Native_AP:SupplierPaymentRead['Native_AP'];document:SupplierPayment;can_correct:boolean;eligible:boolean;previous:null|{link:SupplierPaymentCorrectionLink;document:SupplierPayment};next:null|{link:SupplierPaymentCorrectionLink;document:SupplierPayment};cash_accounts:{rows:SalesCashAccount[];total:string;offset:number;limit:25;next_offset:number|null}}
export function parseSupplierPaymentCorrectionRead(value:unknown,source:SupplierPaymentRead,payment:SupplierPayment,bankOffset:number):SupplierPaymentCorrectionRead{
 const r=closed(value,['contract_version','captured_at','purchase_id','Native_AP','document','can_correct','eligible','previous','next','cash_accounts'])
 const d=parseSupplierPayment(r.document)
 if(r.contract_version!=='cp7.supplier-payment-correction-workspace.v1'||!time(r.captured_at)||r.purchase_id!==source.purchase.id||d.id!==payment.id||JSON.stringify(canonical(d))!==JSON.stringify(canonical(payment))||typeof r.eligible!=='boolean'||r.can_correct!==source.capabilities.reverse||JSON.stringify(canonical(r.Native_AP))!==JSON.stringify(canonical(source.Native_AP)))fail()
 const adjacent=(v:unknown,previous:boolean)=>{if(v===null)return null;const a=closed(v,['link','document']),l=link(a.link,source.purchase.id),p=parseSupplierPayment(a.document);if(previous?(l.replacement_id!==d.id||l.original_id!==p.id||p.status!=='REVERSED'):(l.original_id!==d.id||l.replacement_id!==p.id||d.status!=='REVERSED'))fail();return{link:l,document:p}}
 const previous=adjacent(r.previous,true),next=adjacent(r.next,false)
 if(r.eligible&&(d.status!=='POSTED'||source.purchase.status!=='POSTED'||!source.Native_AP||d.cash_account_id===null||next))fail()
 return{...r,document:d,previous,next,cash_accounts:parseSalesCashAccountPage(r.cash_accounts,bankOffset,25)}as SupplierPaymentCorrectionRead
}
export function parseSupplierPaymentCorrectionOutcome(value:unknown,request:string,payload:Json){
 const r=closed(value,['contract_version','kind','action','request_id','request_payload','purchase_id','original_payment_id','payment_id','original_status','status','link'])
 if(!payload||typeof payload!=='object'||Array.isArray(payload))return fail()
 const p=payload as Record<string,Json|undefined>
 if(r.contract_version!=='cp7.supplier-payment-correction.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!=='CORRECT'||r.request_id!==request||r.purchase_id!==p.purchase_id||r.original_payment_id!==p.payment_id||![r.purchase_id,r.original_payment_id,r.payment_id].every(uuid)||r.original_payment_id===r.payment_id||r.original_status!=='REVERSED'||r.status!=='POSTED'||JSON.stringify(canonical(r.request_payload))!==JSON.stringify(canonical(payload)))fail()
 const l=link(r.link,r.purchase_id as string)
 if(l.original_id!==r.original_payment_id||l.replacement_id!==r.payment_id||l.request_id!==request||l.reason!==String(p.change_reason).trim())fail()
 return r as unknown as {purchase_id:string;original_payment_id:string;payment_id:string;status:'POSTED';link:SupplierPaymentCorrectionLink}
}
