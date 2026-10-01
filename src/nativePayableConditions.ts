import {parseNativeAnalysis,type NativeAnalysis,type AnalysisFinanceAccess}from'./nativeAnalysis'
import type {NativeDemandQuery}from'./nativeDemandHistory'
import {parseSupplierCredit,type SupplierCreditWorkspace}from'./supplierCredit'
import {cp6WibDateTimeInput}from'./cp6BusinessTime'
export const payableStates=['DRAFT_ONLY','INACTIVE_DOCUMENT','UNKNOWN_BALANCE','CREDIT_REVIEW','INVOICE_PENDING','ZERO_BALANCE','MISSING_DUE_DATE','OVERDUE','DUE_TODAY','NOT_DUE_YET']as const
type State=typeof payableStates[number]
type Balance=SupplierCreditWorkspace['purchases'][number]
type Liability={purchase_id:string;purchase_number:string;supplier_id:string|null;supplier_code:string|null;supplier_name:string|null;physical_at:string;status:'DRAFT'|'POSTED'|'REVERSED';payment_status:string;receipt_estimate_amount:string;final_ap_amount:string;grni_estimated_amount:string;total_liability_amount:string;paid_amount:string;final_ap_outstanding:string;liability_state:string;active_invoice_numbers:string|null;earliest_due_date:string|null;unfinalized_days:string;row_version:string;created_at:string;updated_at:string;search_text:string}
type Coverage={id:string;price_state:string;invoice_match_state:string;capacity:string;invoiced_qty:string}
type Condition={key:string;source_revision:string;native_source_hash:string;state:State;invoice_pending:boolean;business_resolved:boolean}
export type PayableRow={liability:Liability;balance:Balance|null;receipt_due_date:string|null;due_date:string|null;due_basis:'NATIVE_POSTED_INVOICE_EARLIEST'|'NATIVE_RECEIPT_HEADER'|'MISSING';invoice_coverage:Coverage[];condition:Condition}
export type NativePayableConditions={analysis:NativeAnalysis;rows:PayableRow[];sourceHash:string;asOf:string;readAt:string;source:Record<string,unknown>}
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const text=(v:unknown):v is string=>typeof v==='string',nullableText=(v:unknown)=>v===null||text(v)
const day=(v:unknown):v is string=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
const instant=(v:unknown):v is string=>text(v)&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&day(v.slice(0,10))&&Number.isFinite(Date.parse(v))&&Number(v.slice(11,13))<24&&Number(v.slice(14,16))<60&&Number(v.slice(17,19))<60
const hash=(v:unknown)=>text(v)&&/^[0-9a-f]{64}$/.test(v)
const integer=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,18})$/.test(v)
const version=(v:unknown)=>integer(v)&&BigInt(v)>0n&&BigInt(v)<=9223372036854775807n
// Native quantity × unit-price products retain twelve fractional places.
// Preserve that source precision; no rounding or another money calculation.
const decimal=(v:unknown):v is string=>text(v)&&/^-?(0|[1-9][0-9]{0,23})(?:\.[0-9]{1,12})?$/.test(v)
const units=(s:string)=>{const negative=s.startsWith('-'),[whole,fraction='']=(negative?s.slice(1):s).split('.'),n=BigInt(whole)*1000000000000n+BigInt(fraction.padEnd(12,'0'));return negative?-n:n}
function fail():never{throw Error('Sumber utang bahan pemasok belum lengkap atau tidak sesuai hak akses saat ini.')}
function closed(v:unknown,keys:string[]):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))return fail();return v as Record<string,unknown>}
const liabilityKeys=['purchase_id','purchase_number','supplier_id','supplier_code','supplier_name','physical_at','status','payment_status','receipt_estimate_amount','final_ap_amount','grni_estimated_amount','total_liability_amount','paid_amount','final_ap_outstanding','liability_state','active_invoice_numbers','earliest_due_date','unfinalized_days','row_version','created_at','updated_at','search_text']
function parseRow(v:unknown,asOf:string):PayableRow{
 const r=closed(v,['liability','balance','receipt_due_date','due_date','due_basis','invoice_coverage','condition']),l=closed(r.liability,liabilityKeys)
 if(!uuid(l.purchase_id)||!text(l.purchase_number)||l.supplier_id!==null&&!uuid(l.supplier_id)||![l.supplier_code,l.supplier_name,l.active_invoice_numbers].every(nullableText)||![l.physical_at,l.created_at,l.updated_at].every(instant)||!['DRAFT','POSTED','REVERSED'].includes(String(l.status))||![l.payment_status,l.liability_state,l.search_text].every(text)||!integer(l.unfinalized_days)||!version(l.row_version)||!['receipt_estimate_amount','final_ap_amount','grni_estimated_amount','total_liability_amount','paid_amount','final_ap_outstanding'].every(k=>decimal(l[k]))||l.earliest_due_date!==null&&!day(l.earliest_due_date)||r.receipt_due_date!==null&&!day(r.receipt_due_date))return fail()
 const due=l.earliest_due_date??r.receipt_due_date,basis=l.earliest_due_date!==null?'NATIVE_POSTED_INVOICE_EARLIEST':r.receipt_due_date!==null?'NATIVE_RECEIPT_HEADER':'MISSING'
 if(r.due_date!==due||r.due_basis!==basis||!Array.isArray(r.invoice_coverage)||r.invoice_coverage.length>10000)return fail()
 const ids=new Set<string>();let pending=units(l.grni_estimated_amount as string)>0n
 for(const value of r.invoice_coverage){const c=closed(value,['id','price_state','invoice_match_state','capacity','invoiced_qty']);if(!uuid(c.id)||ids.has(c.id)||!text(c.price_state)||!text(c.invoice_match_state)||!decimal(c.capacity)||!decimal(c.invoiced_qty)||units(c.capacity)<0n||units(c.invoiced_qty)<0n)return fail();ids.add(c.id);pending||=c.invoice_match_state!=='DIRECT_FINAL'&&units(c.capacity)>units(c.invoiced_qty)}
 pending&&=l.status==='POSTED'
 let balance:Balance|null=null
 if(l.status==='POSTED'){
  if(!uuid(l.supplier_id)||!r.invoice_coverage.length)return fail()
  const b=closed(r.balance,['id','number','date','final_ap','paid','remaining','credit_delta','payment_status'])
  if(b.id!==l.purchase_id||b.number!==l.purchase_number||!day(b.date)||b.payment_status!==l.payment_status)return fail()
  balance=parseSupplierCredit({supplier_id:l.supplier_id,page:1,total:0,can_manage:false,suppliers:[],credits:[],purchases:[b]}).purchases[0]
 }else if(r.balance!==null)return fail()
 const remaining=balance?units(balance.remaining):null
 const state:State=l.status==='DRAFT'?'DRAFT_ONLY':l.status!=='POSTED'?'INACTIVE_DOCUMENT':remaining===null?'UNKNOWN_BALANCE':remaining<0n?'CREDIT_REVIEW':remaining===0n&&pending?'INVOICE_PENDING':remaining===0n?'ZERO_BALANCE':due===null?'MISSING_DUE_DATE':String(due)<asOf?'OVERDUE':due===asOf?'DUE_TODAY':'NOT_DUE_YET'
 const c=closed(r.condition,['key','source_revision','native_source_hash','state','invoice_pending','business_resolved'])
 if(c.key!=='AP_MATERIAL:'+l.purchase_id||c.source_revision!==l.row_version||!hash(c.native_source_hash)||c.state!==state||c.invoice_pending!==pending||c.business_resolved!==(state==='ZERO_BALANCE'))return fail()
 return structuredClone(r)as unknown as PayableRow
}
export function parseNativePayableConditions(v:unknown,q:NativeDemandQuery,actor:string,finance:AnalysisFinanceAccess,canViewAP:boolean):NativePayableConditions{
 if(!canViewAP)return fail()
 const e=closed(v,['contract_version','actor_scope_id','analysis','source'])
 if(e.contract_version!=='cp7.native-material-ap-conditions.v1'||e.actor_scope_id!==actor)return fail()
 const analysis=parseNativeAnalysis(e.analysis,q,actor,finance),s=closed(e.source,['contract_version','basis','as_of','read_at','rows','suppliers','page_complete','total','source_hash'])
 if(s.contract_version!=='cp7.native-material-ap-source.v1'||s.basis!=='ACCEPTED_BF_SIGNED_BALANCE_NATIVE_LIABILITY_AND_RECORDED_DUE'||!day(s.as_of)||!instant(s.read_at)||cp6WibDateTimeInput(s.read_at).slice(0,10)!==s.as_of||s.page_complete!==true||!hash(s.source_hash)||!integer(s.total)||BigInt(s.total)>5000n||!Array.isArray(s.rows)||s.rows.length!==Number(s.total)||new TextEncoder().encode(JSON.stringify(s.rows)).byteLength>4000000||!Array.isArray(s.suppliers)||s.suppliers.length>5000)return fail()
 const suppliers=new Set<string>();for(const value of s.suppliers){const p=closed(value,['id','code','name']);if(!uuid(p.id)||suppliers.has(p.id)||!text(p.code)||!text(p.name))return fail();suppliers.add(p.id)}
 const rows=s.rows.map(r=>parseRow(r,s.as_of as string));if(new Set(rows.map(r=>r.liability.purchase_id)).size!==rows.length||rows.some(r=>r.liability.status==='POSTED'&&!suppliers.has(r.liability.supplier_id!))||[...suppliers].some(id=>!rows.some(r=>r.liability.status==='POSTED'&&r.liability.supplier_id===id)))return fail()
 return{analysis,rows,sourceHash:s.source_hash as string,asOf:s.as_of,readAt:s.read_at,source:structuredClone(s)}
}
export const payableStateLabel:Record<State,string>={DRAFT_ONLY:'Draft, belum menjadi utang',INACTIVE_DOCUMENT:'Penerimaan tidak aktif',UNKNOWN_BALANCE:'Sisa utang belum diketahui',CREDIT_REVIEW:'Kredit pemasok, perlu pemeriksaan',INVOICE_PENDING:'Invoice penerimaan belum lengkap',ZERO_BALANCE:'Tagihan final tersisa nol',MISSING_DUE_DATE:'Jatuh tempo belum tercatat',OVERDUE:'Sudah lewat jatuh tempo',DUE_TODAY:'Jatuh tempo hari ini',NOT_DUE_YET:'Belum jatuh tempo'}
