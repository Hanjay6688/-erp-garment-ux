export type SalesCashAccount={id:string;code:string;name:string;kind:string}
export type SalesPayment={id:string;number:string;physical_at:string;amount:string;cash_account_id:string|null;cash_account_name:string|null;method:string|null;reference:string|null;notes:string|null;status:'DRAFT'|'POSTED'|'REVERSED';replaces_payment_id:string|null}
type Page<T>={rows:T[];total:string;offset:number;limit:number;next_offset:number|null}
export type SalesCash={contract_version:'cp7.sales-cash.v1';sale_id:string;row_version:string;review_token:string;payments:Page<SalesPayment>;cash_accounts:Page<SalesCashAccount>}
const fail=():never=>{throw Error('Data pembayaran berubah atau belum lengkap. Muat ulang invoice sebelum melanjutkan.')}
const text=(v:unknown):v is string=>typeof v==='string'
const id=(v:unknown)=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,18})$/.test(v)
const nullableText=(v:unknown)=>v===null||text(v)
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
export const salesCashAmount=(v:string)=>{const n=v.trim().replace(',','.');return /^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$/.test(n)?n:null}
export const salesCashCents=(v:string)=>{if(salesCashAmount(v)!==v)return fail();const [a,b='']=v.split('.');return BigInt(a)*100n+BigInt(b.padEnd(2,'0'))}
function page(v:unknown,offset:number,limit:number,kind:'payments'|'cash_accounts'){
 const r=closed(v,['rows','total','offset','limit','next_offset'])
 if(r.offset!==offset||r.limit!==limit||!whole(r.total)||!Array.isArray(r.rows)||r.rows.length>limit)return fail()
 const end=BigInt(offset+r.rows.length),total=BigInt(r.total);if(r.rows.length&&end>total||end<total&&(!r.rows.length||r.next_offset!==Number(end))||end>=total&&r.next_offset!==null)fail()
 const seen=new Set()
 for(const value of r.rows){
  const x=closed(value,kind==='payments'?['id','number','physical_at','amount','cash_account_id','cash_account_name','method','reference','notes','status','replaces_payment_id']:['id','code','name','kind'])
  if(!id(x.id)||seen.has(x.id))fail();seen.add(x.id)
  if(kind==='payments'){
   if(!text(x.number)||!text(x.physical_at)||!Number.isFinite(Date.parse(x.physical_at))||!text(x.amount)||salesCashAmount(x.amount)!==x.amount||salesCashCents(x.amount)<=0n||x.cash_account_id!==null&&!id(x.cash_account_id)||![x.cash_account_name,x.method,x.reference,x.notes].every(nullableText)||!['DRAFT','POSTED','REVERSED'].includes(String(x.status))||x.replaces_payment_id!==null&&!id(x.replaces_payment_id))fail()
  }else if(![x.code,x.name,x.kind].every(text))fail()
 }
 return r
}
export function parseSalesCash(v:unknown,source:{id:string;row_version:string;review_token?:string},paymentOffset=0,bankOffset=0,limit=25):SalesCash{
 const r=closed(v,['contract_version','sale_id','row_version','review_token','payments','cash_accounts'])
 if(r.contract_version!=='cp7.sales-cash.v1'||r.sale_id!==source.id||r.row_version!==source.row_version||r.review_token!==source.review_token||!text(r.review_token)||!/^[a-f0-9]{32}$/.test(r.review_token))fail()
 page(r.payments,paymentOffset,limit,'payments');page(r.cash_accounts,bankOffset,limit,'cash_accounts')
 return r as unknown as SalesCash
}
