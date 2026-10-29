import {salesCashAmount} from './salesCashContract'
import type {SalesHeader} from './salesReadContract'
export type ReturnCorrectionLine={id:string;allocation_id:string;product_id:string;product_sku:string;lot_id:string;lot_number:string;location_id:string;location_name:string;qty_pcs:string;quality_grade:'GRADE_A'|'GRADE_B'|'HOLD';refund_amount:string;notes:string|null}
export type ReturnCorrectionDocument={id:string;sale_id:string;number:string;physical_at:string;status:'POSTED'|'REVERSED'|'DRAFT';notes:string|null;items:ReturnCorrectionLine[]}
export type ReturnCorrectionAllocation={allocation_id:string;sale_item_id:string;product_id:string;product_sku:string;product_name:string;size_code:string;lot_id:string;lot_number:string;source_location_name:string;allocated_qty:string;peer_returned_qty:string;replacement_capacity:string;sale_item_qty:string;sale_item_net:string}
export type ReturnCorrectionLink={id:string;original_id:string;replacement_id:string;sale_id:string;actor_scope_id:string;request_id:string;reason:string;recorded_at:string;time_restatement:{source_journal_id:string;inverse_journal_id:string;neutral_journal_id:string;effective_journal_id:string;native_economic_date:string;corrected_economic_date:string}|null}
type Relative={link:ReturnCorrectionLink;document:ReturnCorrectionDocument}
export type ReturnCreditConsumer={event_id:string;event_kind:'APPLY'|'REFUND';amount:string;cohort_id:string;family_ordinal:string;target_sale_id:string|null;journal_id:string;undo_action:string}
export type ReturnCreditReview={contract_version:'cp7.credit-correction-de.v1';state:'REVIEW_REQUIRED'|'READY'|'REFUSE';review_token:string|null;credit_delta:string|null;before_available:string|null;after_available:string|null;issues:string[];active_consumers:ReturnCreditConsumer[];families:{family_id:string;ordinal:string;before_credit:string;after_credit:string;delta:string;capacity_ok:boolean;needs_cohort_configuration:boolean;vector:{amount:string;economic_date:string;transaction_date:string}[]}[];source_authority_proven:boolean;increase_policy:'AUTO_CREDIT_INCREMENT';shortfall_policy:'UNDO_ACTIVE_CONSUMERS_FIRST';replacement_invoice_policy:'AUTO_TRANSFER_TO_REPLACEMENT'}
export type ReturnCorrectionWorkspace={contract_version:'cp7.sales-return-correction-workspace.v1';read_at:string;source:{sale_id:string;row_version:string;review_token:string};document:ReturnCorrectionDocument;return_review_token:string;financial:NonNullable<SalesHeader['financial']>;eligible:boolean;can_correct:boolean;allocations:{rows:ReturnCorrectionAllocation[];total:string;offset:number;limit:number;next_offset:number|null};current_allocations:ReturnCorrectionAllocation[];previous:Relative|null;next:Relative|null;production_go:false;credit_correction?:ReturnCreditReview}
const fail=():never=>{throw Error('Data pembetulan retur berubah atau belum lengkap. Muat ulang invoice sebelum melanjutkan.')}
const text=(v:unknown):v is string=>typeof v==='string'
const id=(v:unknown):v is string=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,18})$/.test(v)
const token=(v:unknown)=>text(v)&&/^[a-f0-9]{32}$/.test(v)
const money=(v:unknown):v is string=>text(v)&&salesCashAmount(v)===v
const financialMoney=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,19})(\.[0-9]{1,2})?$/.test(v)
export function returnCorrectionCents(v:string){if(!financialMoney(v))return fail();const [a,b='']=v.split('.');return BigInt(a)*100n+BigInt(b.padEnd(2,'0'))}
const nullableText=(v:unknown)=>v===null||text(v)&&v.length<=2000
const stamp=(v:unknown):v is string=>text(v)&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v))
const day=(v:unknown)=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(Object.keys(r).length!==keys.length||keys.some(k=>!(k in r)))fail();return r}
function allocation(v:unknown){
 const r=closed(v,['allocation_id','sale_item_id','product_id','product_sku','product_name','size_code','lot_id','lot_number','source_location_name','allocated_qty','peer_returned_qty','replacement_capacity','sale_item_qty','sale_item_net'])
 if(!['allocation_id','sale_item_id','product_id','lot_id'].every(k=>id(r[k]))||!['product_sku','product_name','size_code','lot_number','source_location_name'].every(k=>text(r[k]))||!['allocated_qty','peer_returned_qty','replacement_capacity','sale_item_qty'].every(k=>whole(r[k]))||!money(r.sale_item_net))fail()
 if(BigInt(String(r.allocated_qty))<=0n||BigInt(String(r.allocated_qty))>BigInt(String(r.sale_item_qty))||BigInt(String(r.peer_returned_qty))+BigInt(String(r.replacement_capacity))!==BigInt(String(r.allocated_qty)))fail()
 return r as unknown as ReturnCorrectionAllocation
}
export function parseReturnCorrectionDocument(v:unknown,saleId:string){
 const r=closed(v,['id','sale_id','number','physical_at','status','notes','items'])
 if(!id(r.id)||r.sale_id!==saleId||!text(r.number)||!r.number.trim()||r.number.length>60||!stamp(r.physical_at)||!['DRAFT','POSTED','REVERSED'].includes(String(r.status))||!nullableText(r.notes)||!Array.isArray(r.items)||r.items.length<1||r.items.length>100)fail()
 const items=r.items as unknown[],ids=new Set<string>(),allocations=new Set<string>()
 for(const value of items){const i=closed(value,['id','allocation_id','product_id','product_sku','lot_id','lot_number','location_id','location_name','qty_pcs','quality_grade','refund_amount','notes'])
  if(!['id','allocation_id','product_id','lot_id','location_id'].every(k=>id(i[k]))||!['product_sku','lot_number','location_name'].every(k=>text(i[k]))||!whole(i.qty_pcs)||BigInt(i.qty_pcs)<=0n||BigInt(i.qty_pcs)>999999999n||!['GRADE_A','GRADE_B','HOLD'].includes(String(i.quality_grade))||!money(i.refund_amount)||!nullableText(i.notes)||ids.has(String(i.id))||allocations.has(String(i.allocation_id)))fail()
  ids.add(String(i.id));allocations.add(String(i.allocation_id))
 }
 return r as unknown as ReturnCorrectionDocument
}
function link(v:unknown,saleId:string){
 const r=closed(v,['id','original_id','replacement_id','sale_id','actor_scope_id','request_id','reason','recorded_at','time_restatement'])
 if(!['id','original_id','replacement_id','actor_scope_id','request_id'].every(k=>id(r[k]))||r.original_id===r.replacement_id||r.sale_id!==saleId||!text(r.reason)||r.reason.trim().length<5||r.reason.length>1000||!stamp(r.recorded_at))fail()
 if(r.time_restatement!==null){const t=closed(r.time_restatement,['source_journal_id','inverse_journal_id','neutral_journal_id','effective_journal_id','native_economic_date','corrected_economic_date'])
  const journals=['source_journal_id','inverse_journal_id','neutral_journal_id','effective_journal_id'].map(k=>t[k]);if(!journals.every(id)||new Set(journals).size!==4||!day(t.native_economic_date)||!day(t.corrected_economic_date))fail()
 }
 return r as unknown as ReturnCorrectionLink
}
function financial(v:unknown){
 const r=closed(v,['basis','state','gross_total','return_total','net_total','paid_total','open_balance'])
 if(r.basis!=='CURRENT_NATIVE_DOCUMENT'||!['DRAFT_PREVIEW','ACTIVE_RECEIVABLE','INACTIVE_DOCUMENT'].includes(String(r.state))||!['gross_total','return_total','net_total','paid_total'].every(k=>financialMoney(r[k]))||r.open_balance!==null&&!financialMoney(r.open_balance))fail()
 const cents=(k:string)=>returnCorrectionCents(String(r[k])),net=cents('gross_total')-cents('return_total')
 if(net<0n||cents('net_total')!==net||r.state==='ACTIVE_RECEIVABLE'&&(r.open_balance===null||cents('paid_total')>net||returnCorrectionCents(String(r.open_balance))!==net-cents('paid_total'))||r.state==='INACTIVE_DOCUMENT'&&r.open_balance!==null)fail()
 return r as unknown as NonNullable<SalesHeader['financial']>
}
const signedCents=(v:unknown):v is string=>text(v)&&/^-?(0|[1-9][0-9]{0,19})\.[0-9]{2}$/.test(v)&&v!=='-0.00'
const signedValue=(v:string)=>v.startsWith('-')?-returnCorrectionCents(v.slice(1)):returnCorrectionCents(v)
export function parseReturnCreditReview(v:unknown):ReturnCreditReview{
 const r=closed(v,['contract_version','state','review_token','credit_delta','before_available','after_available','issues','active_consumers','families','source_authority_proven','increase_policy','shortfall_policy','replacement_invoice_policy'])
 if(r.contract_version!=='cp7.credit-correction-de.v1'||!['REVIEW_REQUIRED','READY','REFUSE'].includes(String(r.state))||typeof r.source_authority_proven!=='boolean'||r.increase_policy!=='AUTO_CREDIT_INCREMENT'||r.shortfall_policy!=='UNDO_ACTIVE_CONSUMERS_FIRST'||r.replacement_invoice_policy!=='AUTO_TRANSFER_TO_REPLACEMENT'||!Array.isArray(r.issues)||!Array.isArray(r.active_consumers)||!Array.isArray(r.families))fail()
 const issueRows=r.issues as unknown[],consumerRows=r.active_consumers as unknown[],familyRows=r.families as unknown[]
 const issues=['PHYSICAL_OR_QUANTITY_CHANGE_ADAPTER_REQUIRED','INCOMING_CREDIT_CORRECTION_ADAPTER_REQUIRED','CAUSAL_BOOK_FLOOR_ADAPTER_REQUIRED','STOCK_HPP_CLASS_ADAPTER_REQUIRED','SIGNED_DECREASE_ADAPTER_REQUIRED','UNDO_ACTIVE_CONSUMERS_FIRST','HISTORICAL_CAPACITY_ADAPTER_REQUIRED','SIGNED_COMPONENT_ADAPTER_REQUIRED','REFUND_EXCEEDS_ORIGINAL_NET_SALES_CAP','REFUND_CAP_SOURCE_UNAVAILABLE']
 if(issueRows.some(i=>!text(i)||!issues.includes(i))||new Set(issueRows).size!==issueRows.length)fail()
 if(r.state==='REVIEW_REQUIRED'){if(r.review_token!==null||r.credit_delta!==null||r.before_available!==null||r.after_available!==null||r.source_authority_proven!==false||familyRows.length||issueRows.length)fail()}
 else if(!text(r.review_token)||!/^[a-f0-9]{64}$/.test(r.review_token)||!signedCents(r.credit_delta)||!signedCents(r.before_available)||!signedCents(r.after_available)||r.source_authority_proven!==true||r.state==='READY'&&issueRows.length||r.state==='REFUSE'&&!issueRows.length)fail()
 const ids=new Set<string>()
 for(const value of consumerRows){const e=closed(value,['event_id','event_kind','amount','cohort_id','family_ordinal','target_sale_id','journal_id','undo_action'])
  if(!id(e.event_id)||!id(e.cohort_id)||!id(e.journal_id)||!whole(e.family_ordinal)||BigInt(e.family_ordinal)<=0n||!signedCents(e.amount)||signedValue(String(e.amount))<=0n||ids.has(String(e.event_id))||!['APPLY','REFUND'].includes(String(e.event_kind)))fail()
  if(e.event_kind==='APPLY'? !id(e.target_sale_id)||e.undo_action!=='Batalkan penggunaan kredit di invoice tujuan':e.target_sale_id!==null||e.undo_action!=='Batalkan pengembalian uang kredit')fail();ids.add(String(e.event_id))
 }
 ids.clear();let total=0n
 for(const value of familyRows){const f=closed(value,['family_id','ordinal','before_credit','after_credit','delta','capacity_ok','needs_cohort_configuration','vector'])
  if(!id(f.family_id)||ids.has(String(f.family_id))||!whole(f.ordinal)||BigInt(f.ordinal)<=0n||!signedCents(f.before_credit)||!signedCents(f.after_credit)||!signedCents(f.delta)||signedValue(String(f.before_credit))<0n||signedValue(String(f.after_credit))<0n||signedValue(String(f.delta))!==signedValue(String(f.after_credit))-signedValue(String(f.before_credit))||typeof f.capacity_ok!=='boolean'||typeof f.needs_cohort_configuration!=='boolean'||!Array.isArray(f.vector))fail()
  if(r.state==='READY'&&(!f.capacity_ok||f.needs_cohort_configuration))fail();let components=0n
  for(const value of f.vector as unknown[]){const c=closed(value,['amount','economic_date','transaction_date']);if(!signedCents(c.amount)||signedValue(String(c.amount))===0n||r.state==='READY'&&signedValue(String(c.amount))<0n||!day(c.economic_date)||!day(c.transaction_date)||String(c.transaction_date)<String(c.economic_date))fail();components+=signedValue(String(c.amount))}
  if(components!==signedValue(String(f.delta)))fail();total+=signedValue(String(f.delta));ids.add(String(f.family_id))
 }
 if(r.state==='READY'&&signedValue(String(r.credit_delta))<=0n)fail()
 if(r.state!=='REVIEW_REQUIRED'&&(!familyRows.length||total!==signedValue(String(r.credit_delta))||signedValue(String(r.after_available))-signedValue(String(r.before_available))!==total))fail()
 return r as unknown as ReturnCreditReview
}
export function parseReturnCorrectionWorkspace(v:unknown,source:{id:string;row_version:string;review_token?:string},returnId:string,offset=0):ReturnCorrectionWorkspace{
 const hasCredit=!!v&&typeof v==='object'&&Object.hasOwn(v,'credit_correction'),r=closed(v,['contract_version','read_at','source','document','return_review_token','financial','eligible','can_correct','allocations','current_allocations','previous','next','production_go',...(hasCredit?['credit_correction']:[])]),s=closed(r.source,['sale_id','row_version','review_token'])
 if(hasCredit)parseReturnCreditReview(r.credit_correction)
 if(r.contract_version!=='cp7.sales-return-correction-workspace.v1'||!stamp(r.read_at)||s.sale_id!==source.id||s.row_version!==source.row_version||s.review_token!==source.review_token||!token(s.review_token)||!token(r.return_review_token)||typeof r.eligible!=='boolean'||typeof r.can_correct!=='boolean'||r.production_go!==false)fail()
 const d=parseReturnCorrectionDocument(r.document,source.id),f=financial(r.financial);if(d.id!==returnId)fail()
 const p=closed(r.allocations,['rows','total','offset','limit','next_offset'])
 if(!Array.isArray(p.rows)||p.rows.length>25||!whole(p.total)||p.offset!==offset||p.limit!==25||!Number.isInteger(offset)||offset<0||offset>1000000||p.next_offset!==null&&(!Number.isInteger(p.next_offset)||Number(p.next_offset)>1000000))fail()
 const rows=p.rows as unknown[],end=BigInt(offset)+BigInt(rows.length),total=BigInt(String(p.total))
 if(rows.length&&end>total||end<total&&(!rows.length||p.next_offset!==Number(end))||end>=total&&p.next_offset!==null)fail()
 const choices=rows.map(allocation);if(new Set(choices.map(x=>x.allocation_id)).size!==choices.length||choices.some(x=>BigInt(x.replacement_capacity)<=0n))fail()
 if(!Array.isArray(r.current_allocations)||r.current_allocations.length!==d.items.length)fail()
 const current=(r.current_allocations as unknown[]).map(allocation);if(new Set(current.map(x=>x.allocation_id)).size!==current.length)fail()
 for(const i of d.items){const a=current.find(x=>x.allocation_id===i.allocation_id);if(!a||a.product_id!==i.product_id||a.lot_id!==i.lot_id)fail()}
 for(const key of ['previous','next']as const){if(r[key]===null)continue;const rel=closed(r[key],['link','document']),l=link(rel.link,source.id),other=parseReturnCorrectionDocument(rel.document,source.id)
  if(!['POSTED','REVERSED'].includes(other.status)||key==='previous'&&(l.replacement_id!==returnId||l.original_id!==other.id||other.status!=='REVERSED')||key==='next'&&(l.original_id!==returnId||l.replacement_id!==other.id||d.status!=='REVERSED'))fail()
 }
 if(r.eligible&&(d.status!=='POSTED'||r.next!==null||f.state!=='ACTIVE_RECEIVABLE')||r.can_correct&&!r.eligible)fail()
 return r as unknown as ReturnCorrectionWorkspace
}
export function parseReturnCorrectionOutcome(v:unknown,requestId:string,saleId:string,originalReturnId:string){
 const r=closed(v,['contract_version','kind','action','request_id','sale_id','row_version','status','original_return_id','original_return_status','return_id','return_status','return_page_offset','link','production_go'])
 if(!Number.isInteger(r.return_page_offset)||Number(r.return_page_offset)<0||Number(r.return_page_offset)>1000000||Number(r.return_page_offset)%25!==0)fail()
 if(r.contract_version!=='cp7.sales-return-correction.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!=='RETURN_CORRECT'||r.request_id!==requestId||r.sale_id!==saleId||r.original_return_id!==originalReturnId||r.original_return_status!=='REVERSED'||!id(r.return_id)||r.return_id===originalReturnId||r.return_status!=='POSTED'||!['POSTED','PARTIAL_PAID','PAID'].includes(String(r.status))||!whole(r.row_version)||BigInt(r.row_version)<=0n||r.production_go!==false)fail()
 const l=link(r.link,saleId);if(l.original_id!==originalReturnId||l.replacement_id!==r.return_id||l.request_id!==requestId)fail()
 return r as unknown as {sale_id:string;row_version:string;return_id:string;return_page_offset:number;link:ReturnCorrectionLink}
}
