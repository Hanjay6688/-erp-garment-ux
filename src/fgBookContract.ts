import type {MaterialPage} from './materialContract'
import type {Json} from './types/database.preconnect'
export type FgBookRow={id:string;book_order:string;physical_at:string;recorded_at:string;product_id:string;brand_id:string;brand_name:string;commercial_sku:string;product_name:string;size_code:string;lot_id:string|null;lot_number:string|null;location_id:string;location_name:string;quality_grade:string;customer_id:string|null;customer_name:string|null;movement_type:string;source_type:string;source_id:string|null;reversal_of_id:string|null;notes:string|null;physical_delta:string;reservation_delta:string;available_delta:string;book_physical_before:string;book_physical_after:string;book_available_after:string;book_reserved_after:string;official_physical_after:string;official_available_after:string;official_reserved_after:string}
export type FgBook={contract_version:'cp7.fg-book.v1';read_at:string;knowledge:'CURRENT';book_token:string;can_order:boolean;quantity_scope:'PHYSICAL_PRODUCT_LOCATION_GRADE';presentation_only:true;page:MaterialPage<FgBookRow>}
export type BookOption={id:string;label:string;code:string}
export type BookFilterKind='BRAND'|'CUSTOMER'|'TYPE'
export type FgBookOptions={contract_version:'cp7.fg-book-options.v1';kind:BookFilterKind;read_at:string;page:MaterialPage<BookOption>}
const fail=():never=>{throw Error('Buku mutasi belum lengkap atau hasilnya tidak cocok. Muat ulang.')}
const text=(v:unknown):v is string=>typeof v==='string'
const nullableText=(v:unknown)=>v===null||text(v)
const id=(v:unknown):v is string=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const nullableId=(v:unknown)=>v===null||id(v)
const instant=(v:unknown)=>text(v)&&Number.isFinite(Date.parse(v))
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,29})$/.test(v)
const signed=(v:unknown):v is string=>text(v)&&/^-?(0|[1-9][0-9]{0,29})$/.test(v)
const token=(v:unknown)=>text(v)&&/^[a-f0-9]{32}$/.test(v)
export function fgBookObject(v:unknown){if(!v||typeof v!=='object'||Array.isArray(v))return fail();return v as Record<string,unknown>}
function closed(v:unknown,keys:string[]){const r=fgBookObject(v);if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
function page(v:unknown,check:(v:unknown)=>string){
 const p=closed(v,['rows','total','offset','limit','next_offset'])
 if(!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||p.rows.length>Number(p.limit))return fail()
 const end=BigInt(Number(p.offset))+BigInt(p.rows.length),total=BigInt(p.total)
 if(p.rows.length&&end>total||end<total&&p.next_offset===null||p.next_offset!==null&&(p.next_offset!==Number(p.offset)+p.rows.length||!p.rows.length||end>=total))fail()
 const keys=p.rows.map(check);if(new Set(keys).size!==keys.length)fail()
}
const quantities=['physical_delta','reservation_delta','available_delta','book_physical_before','book_physical_after','book_available_after','book_reserved_after','official_physical_after','official_available_after','official_reserved_after']
export function parseFgBook(v:unknown):FgBook{
 const b=closed(v,['contract_version','read_at','knowledge','book_token','can_order','quantity_scope','presentation_only','page'])
 if(b.contract_version!=='cp7.fg-book.v1'||!instant(b.read_at)||b.knowledge!=='CURRENT'||!token(b.book_token)||typeof b.can_order!=='boolean'||b.quantity_scope!=='PHYSICAL_PRODUCT_LOCATION_GRADE'||b.presentation_only!==true)fail()
 page(b.page,v=>{
  const r=closed(v,['id','book_order','physical_at','recorded_at','product_id','brand_id','brand_name','commercial_sku','product_name','size_code','lot_id','lot_number','location_id','location_name','quality_grade','customer_id','customer_name','movement_type','source_type','source_id','reversal_of_id','notes',...quantities])
  if(!['id','product_id','brand_id','location_id'].every(k=>id(r[k]))||!['lot_id','customer_id','source_id','reversal_of_id'].every(k=>nullableId(r[k]))||!['lot_number','customer_name','notes'].every(k=>nullableText(r[k]))||!['brand_name','commercial_sku','product_name','size_code','location_name','quality_grade','movement_type','source_type'].every(k=>text(r[k]))||!instant(r.physical_at)||!instant(r.recorded_at)||!signed(r.book_order)||!quantities.every(k=>signed(r[k])))return fail()
  const q=(k:string)=>BigInt(r[k] as string)
  if(q('physical_delta')!==q('available_delta')+q('reservation_delta')||q('book_physical_after')!==q('book_physical_before')+q('physical_delta')||q('book_physical_after')!==q('book_available_after')+q('book_reserved_after')||q('official_physical_after')!==q('official_available_after')+q('official_reserved_after'))fail()
  return r.id as string
 });return b as unknown as FgBook
}
export function parseFgBookOptions(v:unknown,kind:BookFilterKind):FgBookOptions{
 const w=closed(v,['contract_version','kind','read_at','page']);if(w.contract_version!=='cp7.fg-book-options.v1'||w.kind!==kind||!instant(w.read_at))fail()
 page(w.page,v=>{const r=closed(v,['id','label','code']);if(!text(r.id)||!r.id||kind!=='TYPE'&&!id(r.id)||!text(r.label)||!text(r.code))return fail();return r.id})
 return w as unknown as FgBookOptions
}
export function parseFgBookOutcome(v:unknown,request:string,action:string,payload:Json){
 const r=closed(v,['contract_version','kind','action','request_id','source_id','book_token','presentation_only']),p=fgBookObject(payload)
 if(r.contract_version!=='cp7.fg-book-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!==action||r.request_id!==request||!token(r.book_token)||r.presentation_only!==true||r.source_id!==(action==='MOVE'?p.source_id:null))fail()
 return r
}
export function bookDozens(qty:string){const n=BigInt(qty),a=n<0n?-n:n;return `${n<0n?'−':''}${a/12n} lusin ${a%12n} pcs`}
