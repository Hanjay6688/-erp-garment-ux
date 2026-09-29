export const salesStatuses=['DRAFT','POSTED','PARTIAL_PAID','PAID','CANCELLED','REVERSED'] as const
export type SalesStatus=typeof salesStatuses[number]
type Finance={basis:'CURRENT_NATIVE_DOCUMENT';state:'DRAFT_PREVIEW'|'ACTIVE_RECEIVABLE'|'INACTIVE_DOCUMENT';gross_total:string;return_total:string;net_total:string;paid_total:string;open_balance:string|null}
export type SalesHeader={id:string;number:string;customer_id:string;customer_name:string;location_id:string|null;location_name:string|null;physical_at:string;due_date:string|null;status:SalesStatus;row_version:string;notes:string|null;line_count:string;qty_pcs:string;reserved_qty:string;returned_qty:string;financial?:Finance}
export type SalesItem={id:string;product_id:string;product_sku:string;commercial_sku:string;product_name:string;size_code:string;brand_name:string;qty_pcs:string;notes:string|null;financial?:{unit_price:string;discount:string;line_total:string}}
export type SalesRead={contract_version:'cp7.sales-workspace.v1';read_at:string;financial_captured:boolean;read_only:true;page:{rows:SalesHeader[];total:string;offset:number;limit:number;next_offset:number|null};detail:(SalesHeader&{items:SalesItem[]})|null}
const fail=():never=>{throw Error('Data invoice belum lengkap. Muat ulang sebelum melanjutkan.')}
const obj=(v:unknown)=>{if(!v||typeof v!=='object'||Array.isArray(v))return fail();return v as Record<string,unknown>}
function closed(v:unknown,keys:string[]){const r=obj(v);if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
const text=(v:unknown):v is string=>typeof v==='string'
const id=(v:unknown)=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,18})$/.test(v)
const instant=(v:unknown)=>text(v)&&Number.isFinite(Date.parse(v))
const nullableText=(v:unknown)=>v===null||text(v)
const money=(v:unknown):v is string=>text(v)&&/^-?(0|[1-9][0-9]{0,19})(\.[0-9]{1,2})?$/.test(v)
const cents=(v:unknown)=>{if(!money(v))return fail();const negative=v.startsWith('-'),[a,b='']=v.replace(/^-/,'').split('.');return (BigInt(a)*100n+BigInt(b.padEnd(2,'0')))*(negative?-1n:1n)}
function header(v:unknown,finance:boolean,detail=false){
 const r=closed(v,['id','number','customer_id','customer_name','location_id','location_name','physical_at','due_date','status','row_version','notes','line_count','qty_pcs','reserved_qty','returned_qty',...(finance?['financial']:[]),...(detail?['items']:[])])
 if(!id(r.id)||!id(r.customer_id)||!text(r.number)||!text(r.customer_name)||r.location_id!==null&&!id(r.location_id)||!nullableText(r.location_name)||!instant(r.physical_at)||r.due_date!==null&&(!text(r.due_date)||!/^\d{4}-\d{2}-\d{2}$/.test(r.due_date)||!instant(r.due_date))||!salesStatuses.includes(r.status as SalesStatus)||!whole(r.row_version)||r.row_version==='0'||!nullableText(r.notes)||![r.line_count,r.qty_pcs,r.reserved_qty,r.returned_qty].every(whole))fail()
 if(finance){
  const f=closed(r.financial,['basis','state','gross_total','return_total','net_total','paid_total','open_balance']),active=['POSTED','PARTIAL_PAID','PAID'].includes(String(r.status))
  if(f.basis!=='CURRENT_NATIVE_DOCUMENT'||f.state!==(active?'ACTIVE_RECEIVABLE':r.status==='DRAFT'?'DRAFT_PREVIEW':'INACTIVE_DOCUMENT')||![f.gross_total,f.return_total,f.net_total,f.paid_total].every(x=>money(x)&&cents(x)>=0n))fail()
  const net=cents(f.gross_total)-cents(f.return_total);if(cents(f.net_total)!==(net<0n?0n:net)||active&&(cents(f.open_balance)!==cents(f.net_total)-cents(f.paid_total))||!active&&f.open_balance!==null)fail()
 }
 return r
}
export function parseSalesRead(v:unknown,finance:boolean):SalesRead{
 const w=closed(v,['contract_version','read_at','financial_captured','read_only','page','detail'])
 if(w.contract_version!=='cp7.sales-workspace.v1'||!instant(w.read_at)||w.financial_captured!==finance||w.read_only!==true)fail()
 const p=closed(w.page,['rows','total','offset','limit','next_offset'])
 if(!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||p.rows.length>Number(p.limit))return fail()
 const end=BigInt(Number(p.offset)+p.rows.length),total=BigInt(p.total)
 if(p.rows.length&&end>total||end<total&&(p.next_offset!==Number(end)||!p.rows.length)||end>=total&&p.next_offset!==null)fail()
 const ids=p.rows.map(v=>String(header(v,finance).id));if(new Set(ids).size!==ids.length)fail()
 if(w.detail!==null){
  const h=header(w.detail,finance,true);if(!Array.isArray(h.items)||h.items.length>100||BigInt(h.items.length)!==BigInt(String(h.line_count)))return fail()
  const seen=new Set();let qty=0n,amount=0n
  for(const value of h.items){
   const i=closed(value,['id','product_id','product_sku','commercial_sku','product_name','size_code','brand_name','qty_pcs','notes',...(finance?['financial']:[])])
   if(!id(i.id)||seen.has(i.id)||!id(i.product_id)||![i.product_sku,i.commercial_sku,i.product_name,i.size_code,i.brand_name].every(text)||!whole(i.qty_pcs)||i.qty_pcs==='0'||!nullableText(i.notes))return fail()
   seen.add(i.id);qty+=BigInt(i.qty_pcs)
   if(finance){const f=closed(i.financial,['unit_price','discount','line_total']);if(!Object.values(f).every(x=>money(x)&&cents(x)>=0n)||cents(f.line_total)!==BigInt(i.qty_pcs)*cents(f.unit_price)-cents(f.discount))fail();amount+=cents(f.line_total)}
  }
  if(qty!==BigInt(String(h.qty_pcs))||finance&&amount!==cents(obj(h.financial).gross_total))fail()
  const inList=p.rows.find(x=>obj(x).id===h.id);if(inList){const {items:_,...same}=h;if(JSON.stringify(same)!==JSON.stringify(inList)){
   const a=obj(inList);if(Object.keys(same).some(k=>JSON.stringify(same[k])!==JSON.stringify(a[k])))fail()
  }}
 }
 return w as unknown as SalesRead
}
