import type { Json } from './types/database.preconnect'
import { procurementObject } from './procurementContract'
export type ReturnSource={id:string;material_id:string;material_name:string;material_type:string;material_active:boolean;unit_code:string;receipt_qty:string;posted_return_qty:string;unreturned_qty:string;location_qty:string|null;rolls:{id:string;number:string;receipt_qty:string;location_qty:string|null}[]}
type ReturnFinance={credit_unit_price:string|null;ap_relief_qty:string|null;grni_relief_qty:string|null;ap_relief_amount:string|null;grni_relief_amount:string|null}
export type SupplierReturn={id:string;number:string;supplier_id:string;location_id:string;location_name:string|null;physical_at:string;status:'DRAFT'|'POSTED'|'REVERSED';row_version:string;reason:string|null;line_count:string;single_receipt:boolean;lines:{id:string;purchase_item_id:string|null;purchase_id:string|null;purchase_number:string|null;material_id:string;material_name:string;unit_code:string;roll_id:string|null;roll_number:string|null;qty:string;notes:string|null;finance?:ReturnFinance}[];finance?:{basis:'SOURCE_VALUATION_SNAPSHOTS_NOT_AVAILABLE_CREDIT';ap_relief_amount:string|null;grni_relief_amount:string|null}}
export type SupplierReturns={contract_version:'cp7.supplier-returns.v1';read_at:string;purchase_id:string;purchase_number:string;purchase_status:'DRAFT'|'POSTED'|'REVERSED';purchase_version:string;supplier_id:string|null;receipt_location_id:string|null;selected_location:{id:string;name:string;available:boolean}|null;basis:'CURRENT_POSTED_STOCK_AND_SOURCE_RETURN_DOCUMENTS';financial_captured:boolean;capabilities:{create:boolean;post:boolean;reverse:boolean};source_line_count:string;source_lines:ReturnSource[];page:{rows:SupplierReturn[];total:string;offset:number;limit:number;next_offset:number|null}}
const text=(v:unknown):v is string=>typeof v==='string',nullable=(v:unknown)=>v===null||text(v)
const id=(v:unknown):v is string=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v),nullableId=(v:unknown)=>v===null||id(v)
const decimal=(v:unknown,signed=false)=>text(v)&&(signed?/^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/:/^(0|[1-9][0-9]*)(\.[0-9]+)?$/).test(v)
const maybeDecimal=(v:unknown,signed=false)=>v===null||decimal(v,signed),count=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]*)$/.test(v)
const version=(v:unknown)=>text(v)&&/^[1-9][0-9]{0,18}$/.test(v)&&BigInt(v)<=9223372036854775807n
const instant=(v:unknown)=>text(v)&&/T.*(?:Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v))
function fail():never{throw Error('Data retur supplier belum lengkap atau tidak cocok dengan hak akses. Muat ulang sebelum melanjutkan.')}
function closed(v:unknown,keys:string[],optional:string[]=[]){const o=procurementObject(v);if(keys.some(k=>!Object.hasOwn(o,k))||Object.keys(o).some(k=>!keys.includes(k)&&!optional.includes(k)))fail();return o}
export function parseSupplierReturns(value:unknown,purchase:string,finance:boolean):SupplierReturns{
 const w=closed(value,['contract_version','read_at','purchase_id','purchase_number','purchase_status','purchase_version','supplier_id','receipt_location_id','selected_location','basis','financial_captured','capabilities','source_line_count','source_lines','page'])
 const cap=closed(w.capabilities,['create','post','reverse'])
 if(w.contract_version!=='cp7.supplier-returns.v1'||w.purchase_id!==purchase||!id(w.purchase_id)||!text(w.purchase_number)||!instant(w.read_at)||!['DRAFT','POSTED','REVERSED'].includes(String(w.purchase_status))||!version(w.purchase_version)||!nullableId(w.supplier_id)||!nullableId(w.receipt_location_id)||w.basis!=='CURRENT_POSTED_STOCK_AND_SOURCE_RETURN_DOCUMENTS'||w.financial_captured!==finance||Object.values(cap).some(x=>typeof x!=='boolean'))fail()
 if(w.selected_location!==null){const l=closed(w.selected_location,['id','name','available']);if(!id(l.id)||!text(l.name)||typeof l.available!=='boolean')fail()}
 if(!count(w.source_line_count)||!Array.isArray(w.source_lines)||w.source_lines.length>100||BigInt(w.source_line_count)!==BigInt(w.source_lines.length))return fail()
 const sourceIds=new Set<string>(),rollIds=new Set<string>()
 for(const value of w.source_lines){const l=closed(value,['id','material_id','material_name','material_type','material_active','unit_code','receipt_qty','posted_return_qty','unreturned_qty','location_qty','rolls'])
  if(!id(l.id)||sourceIds.has(l.id)||!id(l.material_id)||![l.material_name,l.material_type,l.unit_code].every(text)||typeof l.material_active!=='boolean'||![l.receipt_qty,l.posted_return_qty].every(x=>decimal(x))||!decimal(l.unreturned_qty,true)||!maybeDecimal(l.location_qty,true)||!Array.isArray(l.rolls))return fail();sourceIds.add(l.id)
  for(const value of l.rolls){const r=closed(value,['id','number','receipt_qty','location_qty']);if(!id(r.id)||rollIds.has(r.id)||!text(r.number)||!decimal(r.receipt_qty)||!maybeDecimal(r.location_qty,true))fail();rollIds.add(r.id)}
 }
 if(rollIds.size>2000)fail()
 const p=closed(w.page,['rows','total','offset','limit','next_offset']);if(!Array.isArray(p.rows)||!count(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>25)return fail()
 const total=BigInt(p.total),offset=BigInt(Number(p.offset)),remaining=total>offset?total-offset:0n,expected=remaining>BigInt(Number(p.limit))?Number(p.limit):Number(remaining)
 if(p.rows.length!==expected||p.next_offset!==(offset+BigInt(p.rows.length)<total?Number(p.offset)+p.rows.length:null))fail()
 const docIds=new Set<string>()
 for(const value of p.rows){const d=closed(value,['id','number','supplier_id','location_id','location_name','physical_at','status','row_version','reason','line_count','single_receipt','lines'],finance?['finance']:[])
  if(!id(d.id)||docIds.has(d.id)||!text(d.number)||!id(d.supplier_id)||!id(d.location_id)||!nullable(d.location_name)||!instant(d.physical_at)||!['DRAFT','POSTED','REVERSED'].includes(String(d.status))||!version(d.row_version)||!nullable(d.reason)||!count(d.line_count)||typeof d.single_receipt!=='boolean'||!Array.isArray(d.lines)||d.lines.length<1||d.lines.length>100||BigInt(d.line_count)!==BigInt(d.lines.length))return fail();docIds.add(d.id)
  const purchases=new Set(),lineIds=new Set()
  for(const value of d.lines){const l=closed(value,['id','purchase_item_id','purchase_id','purchase_number','material_id','material_name','unit_code','roll_id','roll_number','qty','notes'],finance?['finance']:[])
   if(!id(l.id)||lineIds.has(l.id)||!nullableId(l.purchase_item_id)||!nullableId(l.purchase_id)||!nullable(l.purchase_number)||!id(l.material_id)||!text(l.material_name)||!text(l.unit_code)||!nullableId(l.roll_id)||!nullable(l.roll_number)||!decimal(l.qty)||!nullable(l.notes)||l.purchase_id===purchase&&!sourceIds.has(String(l.purchase_item_id)))fail();lineIds.add(l.id);purchases.add(l.purchase_id)
   if(finance){const f=closed(l.finance,['credit_unit_price','ap_relief_qty','grni_relief_qty','ap_relief_amount','grni_relief_amount']);if(Object.values(f).some(x=>!maybeDecimal(x)))fail()}
  }
  if(!purchases.has(purchase)||d.single_receipt!==(purchases.size===1))fail()
  if(finance){const f=closed(d.finance,['basis','ap_relief_amount','grni_relief_amount']);if(f.basis!=='SOURCE_VALUATION_SNAPSHOTS_NOT_AVAILABLE_CREDIT'||!maybeDecimal(f.ap_relief_amount)||!maybeDecimal(f.grni_relief_amount))fail()}
 }
 return w as unknown as SupplierReturns
}
export function parseSupplierReturnOutcome(v:unknown,request:string,action:string,document:Json){
 const r=closed(v,['contract_version','kind','action','request_id','purchase_id','return_id','row_version','status']),p=procurementObject(document)
 const base=action.replace(/_DOCUMENT$/,'')
 if(!['SAVE','POST','REVERSE','SAVE_DOCUMENT','POST_DOCUMENT','REVERSE_DOCUMENT'].includes(action)||r.contract_version!=='cp7.supplier-return-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!==action||r.request_id!==request||!id(r.purchase_id)||r.purchase_id!==p.purchase_id||!id(r.return_id)||!version(r.row_version)||r.status!==({SAVE:'DRAFT',POST:'POSTED',REVERSE:'REVERSED'} as Record<string,string>)[base]||(base==='SAVE'?p.id&&p.id!==r.return_id:p.return_id!==r.return_id))fail()
 return r as {purchase_id:string;return_id:string;row_version:string;status:SupplierReturn['status']}
}

export type SupplierReturnSources={contract_version:'cp7.return-sources.v1';read_at:string;purchase_id:string;supplier_id:string;page:{rows:{id:string;number:string;physical_at:string;row_version:string}[];total:string;offset:number;limit:number;next_offset:number|null}}
export function parseSupplierReturnSources(value:unknown,purchase:string,supplier:string,offset:number):SupplierReturnSources{
 const w=closed(value,['contract_version','read_at','purchase_id','supplier_id','page']),p=closed(w.page,['rows','total','offset','limit','next_offset'])
 if(w.contract_version!=='cp7.return-sources.v1'||w.purchase_id!==purchase||!id(w.purchase_id)||w.supplier_id!==supplier||!id(w.supplier_id)||!instant(w.read_at)||!Array.isArray(p.rows)||!count(p.total)||p.offset!==offset||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>25)return fail()
 const left=BigInt(p.total)>BigInt(offset)?BigInt(p.total)-BigInt(offset):0n
 if(p.rows.length!==Number(left>BigInt(Number(p.limit))?BigInt(Number(p.limit)):left)||p.next_offset!==(BigInt(offset+p.rows.length)<BigInt(p.total)?offset+p.rows.length:null))fail()
 const ids=new Set<string>()
 for(const value of p.rows){const r=closed(value,['id','number','physical_at','row_version']);if(!id(r.id)||ids.has(r.id)||!text(r.number)||!instant(r.physical_at)||!version(r.row_version))fail();ids.add(r.id)}
 return w as unknown as SupplierReturnSources
}
