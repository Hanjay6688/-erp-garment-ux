import {salesCashAmount} from './salesCashContract'
import type {SalesHeader} from './salesReadContract'
export type ReturnCorrectionLine={id:string;allocation_id:string;product_id:string;product_sku:string;lot_id:string;lot_number:string;location_id:string;location_name:string;qty_pcs:string;quality_grade:'GRADE_A'|'GRADE_B'|'HOLD';refund_amount:string;notes:string|null}
export type ReturnCorrectionDocument={id:string;sale_id:string;number:string;physical_at:string;status:'POSTED'|'REVERSED'|'DRAFT';notes:string|null;items:ReturnCorrectionLine[]}
export type ReturnCorrectionAllocation={allocation_id:string;sale_item_id:string;product_id:string;product_sku:string;product_name:string;size_code:string;lot_id:string;lot_number:string;source_location_name:string;allocated_qty:string;peer_returned_qty:string;replacement_capacity:string;sale_item_qty:string;sale_item_net:string}
export type ReturnCorrectionLink={id:string;original_id:string;replacement_id:string;sale_id:string;actor_scope_id:string;request_id:string;reason:string;recorded_at:string;time_restatement:{source_journal_id:string;inverse_journal_id:string;neutral_journal_id:string;effective_journal_id:string;native_economic_date:string;corrected_economic_date:string}|null}
type Relative={link:ReturnCorrectionLink;document:ReturnCorrectionDocument}
export type ReturnCorrectionWorkspace={contract_version:'cp7.sales-return-correction-workspace.v1';read_at:string;source:{sale_id:string;row_version:string;review_token:string};document:ReturnCorrectionDocument;return_review_token:string;financial:NonNullable<SalesHeader['financial']>;eligible:boolean;can_correct:boolean;allocations:{rows:ReturnCorrectionAllocation[];total:string;offset:number;limit:number;next_offset:number|null};current_allocations:ReturnCorrectionAllocation[];previous:Relative|null;next:Relative|null;production_go:false}
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
export function parseReturnCorrectionWorkspace(v:unknown,source:{id:string;row_version:string;review_token?:string},returnId:string,offset=0):ReturnCorrectionWorkspace{
 const r=closed(v,['contract_version','read_at','source','document','return_review_token','financial','eligible','can_correct','allocations','current_allocations','previous','next','production_go']),s=closed(r.source,['sale_id','row_version','review_token'])
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
