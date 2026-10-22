import {salesCashAmount,salesCashCents} from './salesCashContract'
export type SalesReturnKind='ALLOCATIONS'|'RETURNS'|'LOCATIONS'
export type SalesReturnAllocation={allocation_id:string;sale_item_id:string;product_id:string;product_sku:string;commercial_sku:string;product_name:string;size_code:string;lot_id:string;lot_number:string;source_location_name:string;allocated_qty:string;returned_qty:string;remaining_qty:string;sale_item_qty:string;sale_item_net:string}
export type SalesReturnLocation={id:string;name:string}
export type SalesReturnLine={id:string;allocation_id:string;product_sku:string;lot_number:string;location_id:string;location_name:string;qty_pcs:string;quality_grade:'GRADE_A'|'GRADE_B'|'HOLD';refund_amount:string;notes:string|null}
export type SalesReturnRecord={id:string;number:string;physical_at:string;status:'DRAFT'|'POSTED'|'REVERSED';notes:string|null;line_count:string;items:SalesReturnLine[]}
export type SalesReturnRead<T>={contract_version:'cp7.sales-returns.v1';kind:SalesReturnKind;sale_id:string;row_version:string;review_token:string;page:{rows:T[];total:string;offset:number;limit:number;next_offset:number|null}}
const fail=():never=>{throw Error('Sumber retur berubah atau belum lengkap. Muat ulang invoice sebelum melanjutkan.')}
const text=(v:unknown):v is string=>typeof v==='string'
const id=(v:unknown)=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,18})$/.test(v)
const money=(v:unknown):v is string=>text(v)&&salesCashAmount(v)===v
const nullableText=(v:unknown)=>v===null||text(v)
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
export function parseSalesReturns<T extends SalesReturnAllocation|SalesReturnLocation|SalesReturnRecord>(v:unknown,kind:SalesReturnKind,source:{id:string;row_version:string;review_token?:string},offset=0,limit=25):SalesReturnRead<T>{
 const r=closed(v,['contract_version','kind','sale_id','row_version','review_token','page'])
 if(r.contract_version!=='cp7.sales-returns.v1'||r.kind!==kind||r.sale_id!==source.id||r.row_version!==source.row_version||r.review_token!==source.review_token||!text(r.review_token)||!/^[a-f0-9]{32}$/.test(r.review_token))fail()
 const p=closed(r.page,['rows','total','offset','limit','next_offset'])
 if(p.offset!==offset||p.limit!==limit||!Array.isArray(p.rows)||p.rows.length>limit||!whole(p.total))return fail()
 const end=BigInt(offset+p.rows.length),total=BigInt(p.total);if(p.rows.length&&end>total||end<total&&(!p.rows.length||p.next_offset!==Number(end))||end>=total&&p.next_offset!==null)fail()
 const seen=new Set()
 for(const value of p.rows){
  if(kind==='ALLOCATIONS'){
   const a=closed(value,['allocation_id','sale_item_id','product_id','product_sku','commercial_sku','product_name','size_code','lot_id','lot_number','source_location_name','allocated_qty','returned_qty','remaining_qty','sale_item_qty','sale_item_net'])
   if(![a.allocation_id,a.sale_item_id,a.product_id,a.lot_id].every(id)||![a.product_sku,a.commercial_sku,a.product_name,a.size_code,a.lot_number,a.source_location_name].every(text)||![a.allocated_qty,a.returned_qty,a.remaining_qty,a.sale_item_qty].every(whole)||!money(a.sale_item_net)||seen.has(a.allocation_id))fail()
   if(BigInt(String(a.remaining_qty))<=0n||BigInt(String(a.allocated_qty))>BigInt(String(a.sale_item_qty))||BigInt(String(a.allocated_qty))-BigInt(String(a.returned_qty))!==BigInt(String(a.remaining_qty)))fail();seen.add(a.allocation_id)
  }else if(kind==='LOCATIONS'){
   const l=closed(value,['id','name']);if(!id(l.id)||!text(l.name)||seen.has(l.id))fail();seen.add(l.id)
  }else{
   const h=closed(value,['id','number','physical_at','status','notes','line_count','items'])
   if(!id(h.id)||seen.has(h.id)||!text(h.number)||!text(h.physical_at)||!Number.isFinite(Date.parse(h.physical_at))||!['DRAFT','POSTED','REVERSED'].includes(String(h.status))||!nullableText(h.notes)||!whole(h.line_count)||!Array.isArray(h.items)||h.items.length>100||BigInt(h.items.length)!==BigInt(h.line_count))return fail();seen.add(h.id)
   const lines=new Set()
   for(const item of h.items){const i=closed(item,['id','allocation_id','product_sku','lot_number','location_id','location_name','qty_pcs','quality_grade','refund_amount','notes']);if(![i.id,i.allocation_id,i.location_id].every(id)||lines.has(i.id)||![i.product_sku,i.lot_number,i.location_name].every(text)||!whole(i.qty_pcs)||i.qty_pcs==='0'||!['GRADE_A','GRADE_B','HOLD'].includes(String(i.quality_grade))||!money(i.refund_amount)||!nullableText(i.notes))fail();lines.add(i.id)}
  }
 }
 return r as unknown as SalesReturnRead<T>
}
export function salesReturnTotal(amounts:string[]){let total=0n;for(const amount of amounts){const n=salesCashAmount(amount);if(n===null)return null;total+=salesCashCents(n)}return `${total/100n}.${String(total%100n).padStart(2,'0')}`}
