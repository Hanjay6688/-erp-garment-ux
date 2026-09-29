import type { Json } from './types/database.preconnect'
import { procurementObject } from './procurementContract'
export type InvoiceReceiptLine = { id:string;material_id:string;material_name:string;unit_code:string;receipt_qty:string;estimate_unit_price:string;price_state:string;invoice_match_state:string;capacity:string;invoiced_qty:string;remaining_qty:string }
export type InvoiceLine = { id:string;purchase_item_id:string;purchase_id:string;purchase_number:string;material_name:string;unit_code:string;qty:string;unit_price:string;discount:string;net_amount:string }
export type PurchaseInvoice = { id:string;number:string;invoice_date:string;received_at:string;due_date:string|null;status:'DRAFT'|'POSTED'|'REVERSED';row_version:string;notes:string|null;line_count:string;document_net_amount:string;single_receipt:boolean;lines:InvoiceLine[] }
export type PurchaseInvoices = { contract_version:'cp7.purchase-invoices.v1';read_at:string;purchase_id:string;purchase_number:string;purchase_status:'DRAFT'|'POSTED'|'REVERSED';purchase_version:string;supplier_id:string|null;capabilities:{finalize:boolean;reverse:boolean};basis:'INVOICE_DOCUMENTS_NOT_PAYMENT_OUTSTANDING';receipt_line_count:string;receipt_lines:InvoiceReceiptLine[];page:{rows:PurchaseInvoice[];total:string;offset:number;limit:number;next_offset:number|null} }
const id=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const text=(v:unknown):v is string=>typeof v==='string',nullable=(v:unknown)=>v===null||text(v)
const decimal=(v:unknown,signed=false):v is string=>text(v)&&(signed?/^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/:/^(0|[1-9][0-9]*)(\.[0-9]+)?$/).test(v)
const count=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]*)$/.test(v)
const version=(v:unknown):v is string=>text(v)&&/^[1-9][0-9]{0,18}$/.test(v)&&BigInt(v)<=9223372036854775807n
const instant=(v:unknown)=>text(v)&&/T.*(?:Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v))
const date=(v:unknown)=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))
function fail():never{throw new Error('Data invoice belum lengkap atau tidak cocok. Muat ulang sebelum melanjutkan.')}
function closed(v:unknown,keys:string[]){const o=procurementObject(v);if(Object.keys(o).length!==keys.length||keys.some(k=>!Object.hasOwn(o,k)))fail();return o}
export function parsePurchaseInvoices(v:unknown,purchase:string):PurchaseInvoices{
 const w=closed(v,['contract_version','read_at','purchase_id','purchase_number','purchase_status','purchase_version','supplier_id','capabilities','basis','receipt_line_count','receipt_lines','page'])
 const caps=closed(w.capabilities,['finalize','reverse'])
 if(w.contract_version!=='cp7.purchase-invoices.v1'||w.purchase_id!==purchase||!id(w.purchase_id)||!text(w.purchase_number)||!instant(w.read_at)||!['DRAFT','POSTED','REVERSED'].includes(String(w.purchase_status))||!version(w.purchase_version)||w.supplier_id!==null&&!id(w.supplier_id)||Object.values(caps).some(x=>typeof x!=='boolean')||w.basis!=='INVOICE_DOCUMENTS_NOT_PAYMENT_OUTSTANDING')fail()
 if(!count(w.receipt_line_count)||!Array.isArray(w.receipt_lines)||w.receipt_lines.length>100||BigInt(w.receipt_line_count)!==BigInt(w.receipt_lines.length))return fail()
 const sourceIds=new Set<string>()
 for(const value of w.receipt_lines){const l=closed(value,['id','material_id','material_name','unit_code','receipt_qty','estimate_unit_price','price_state','invoice_match_state','capacity','invoiced_qty','remaining_qty']);if(!id(l.id)||sourceIds.has(l.id)||!id(l.material_id)||![l.material_name,l.unit_code,l.price_state,l.invoice_match_state].every(text)||![l.receipt_qty,l.estimate_unit_price,l.capacity,l.invoiced_qty].every(x=>decimal(x))||!decimal(l.remaining_qty,true))fail();sourceIds.add(l.id)}
 const p=closed(w.page,['rows','total','offset','limit','next_offset'])
 if(!Array.isArray(p.rows)||!count(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>25)return fail()
 const total=BigInt(p.total),offset=BigInt(Number(p.offset)),remaining=total>offset?total-offset:0n,expected=remaining>BigInt(Number(p.limit))?Number(p.limit):Number(remaining)
 if(p.rows.length!==expected||p.next_offset!==(offset+BigInt(p.rows.length)<total?Number(p.offset)+p.rows.length:null))fail()
 const docIds=new Set<string>()
 for(const value of p.rows){const d=closed(value,['id','number','invoice_date','received_at','due_date','status','row_version','notes','line_count','document_net_amount','single_receipt','lines']);if(!id(d.id)||docIds.has(d.id)||!text(d.number)||!date(d.invoice_date)||!instant(d.received_at)||d.due_date!==null&&!date(d.due_date)||!['DRAFT','POSTED','REVERSED'].includes(String(d.status))||!version(d.row_version)||!nullable(d.notes)||!decimal(d.document_net_amount)||typeof d.single_receipt!=='boolean'||!count(d.line_count)||!Array.isArray(d.lines)||d.lines.length<1||d.lines.length>100||BigInt(d.line_count)!==BigInt(d.lines.length))return fail();docIds.add(d.id)
  const ids=new Set<string>(),purchases=new Set<string>()
  for(const value of d.lines){const l=closed(value,['id','purchase_item_id','purchase_id','purchase_number','material_name','unit_code','qty','unit_price','discount','net_amount']);if(!id(l.id)||ids.has(l.id)||!id(l.purchase_item_id)||!id(l.purchase_id)||![l.purchase_number,l.material_name,l.unit_code].every(text)||![l.qty,l.unit_price,l.discount,l.net_amount].every(x=>decimal(x))||l.purchase_id===purchase&&!sourceIds.has(l.purchase_item_id))fail();ids.add(l.id);purchases.add(l.purchase_id)}
  if(!purchases.has(purchase)||d.single_receipt!==(purchases.size===1))fail()
 }
 return w as unknown as PurchaseInvoices
}
export function parsePurchaseInvoiceOutcome(v:unknown,request:string,action:string,document:Json){
 const r=closed(v,['contract_version','kind','action','request_id','purchase_id','invoice_id','version_subject','row_version','status']),p=procurementObject(document)
 if(!['FINALIZE','REVERSE'].includes(action)||r.contract_version!=='cp7.purchase-invoice-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!==action||r.request_id!==request||!id(r.purchase_id)||r.purchase_id!==p.purchase_id||!id(r.invoice_id)||!version(r.row_version)||r.version_subject!==(action==='FINALIZE'?'RECEIPT':'INVOICE')||r.status!==(action==='FINALIZE'?'POSTED':'REVERSED')||action==='REVERSE'&&r.invoice_id!==p.invoice_id)fail()
 return r as {purchase_id:string;invoice_id:string;row_version:string;status:'POSTED'|'REVERSED'}
}
export function hasInvoiceCapacity(line:InvoiceReceiptLine){return !line.remaining_qty.startsWith('-')&&/[1-9]/.test(line.remaining_qty)&&line.invoice_match_state!=='DIRECT_FINAL'}
