export const salesStatuses=['DRAFT','POSTED','PARTIAL_PAID','PAID','CANCELLED','REVERSED'] as const
export type SalesStatus=typeof salesStatuses[number]
type Finance={basis:'CURRENT_NATIVE_DOCUMENT';state:'DRAFT_PREVIEW'|'ACTIVE_RECEIVABLE'|'INACTIVE_DOCUMENT';gross_total:string;return_total:string;net_total:string;paid_total:string;open_balance:string|null}
export type SalesHeader={id:string;number:string;customer_id:string;customer_name:string;location_id:string|null;location_name:string|null;physical_at:string;due_date:string|null;status:SalesStatus;row_version:string;notes:string|null;payment_terms:string|null;line_count:string;qty_pcs:string;reserved_qty:string;returned_qty:string;financial?:Finance}
export type SalesItem={id:string;product_id:string;product_sku:string;commercial_sku:string;product_name:string;size_code:string;brand_name:string;qty_pcs:string;notes:string|null;financial?:{unit_price:string;discount:string;line_total:string}}
export type SalesRead={contract_version:'cp7.sales-workspace.v1';read_at:string;financial_captured:boolean;read_only:true;page:{rows:SalesHeader[];total:string;offset:number;limit:number;next_offset:number|null};detail:(SalesHeader&{items:SalesItem[];review_token?:string})|null}
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
 const r=closed(v,['id','number','customer_id','customer_name','location_id','location_name','physical_at','due_date','status','row_version','notes','payment_terms','line_count','qty_pcs','reserved_qty','returned_qty',...(finance?['financial']:[]),...(detail?['items',...(finance?['review_token']:[])]:[])])
 if(detail&&finance&&(!text(r.review_token)||!(/^[a-f0-9]{32}$/).test(r.review_token)))fail()
 if(!id(r.id)||!id(r.customer_id)||!text(r.number)||!text(r.customer_name)||r.location_id!==null&&!id(r.location_id)||!nullableText(r.location_name)||!instant(r.physical_at)||r.due_date!==null&&(!text(r.due_date)||!/^\d{4}-\d{2}-\d{2}$/.test(r.due_date)||!instant(r.due_date))||!salesStatuses.includes(r.status as SalesStatus)||!whole(r.row_version)||r.row_version==='0'||!nullableText(r.notes)||!nullableText(r.payment_terms)||![r.line_count,r.qty_pcs,r.reserved_qty,r.returned_qty].every(whole))fail()
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
  const inList=p.rows.find(x=>obj(x).id===h.id);if(inList){const {items:_,review_token:__,...same}=h;if(JSON.stringify(same)!==JSON.stringify(inList)){
   const a=obj(inList);if(Object.keys(same).some(k=>JSON.stringify(same[k])!==JSON.stringify(a[k])))fail()
  }}
 }
 return w as unknown as SalesRead
}

export function parseSalesOutcome(v:unknown,requestId:string,action:string,saleId:string|null,expectedPaymentId:string|null=null,expectedReturnId:string|null=null){
 const cash=['PAYMENT','PAYMENT_REVERSE'].includes(action),returned=['RETURN','RETURN_REVERSE'].includes(action),r=closed(v,['contract_version','kind','action','request_id','sale_id','status','row_version',...(cash?['payment_id','payment_status']:[]),...(returned?['return_id','return_status']:[])])
 if(r.contract_version!=='cp7.sales-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||!['CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE'].includes(action)||r.action!==action||r.request_id!==requestId||(action==='CREATE'?saleId!==null:r.sale_id!==saleId)||!id(r.sale_id)||!whole(r.row_version)||r.row_version==='0')fail()
 if(cash){if(action==='PAYMENT_REVERSE'&&r.payment_id!==expectedPaymentId||!id(r.payment_id)||r.payment_status!==(action==='PAYMENT'?'POSTED':'REVERSED')||!(action==='PAYMENT'?['PARTIAL_PAID','PAID']:['POSTED','PARTIAL_PAID','PAID']).includes(String(r.status)))fail()}
 else if(returned){if(action==='RETURN_REVERSE'&&r.return_id!==expectedReturnId||!id(r.return_id)||r.return_status!==(action==='RETURN'?'POSTED':'REVERSED')||!['POSTED','PARTIAL_PAID','PAID'].includes(String(r.status)))fail()}
 else if(r.status!==({CREATE:'DRAFT',EDIT:'DRAFT',POST:'POSTED',CANCEL:'CANCELLED',SALE_REVERSE:'REVERSED'} as Record<string,string>)[action])fail()
 return r as {sale_id:string;status:SalesStatus;row_version:string;payment_id?:string;payment_status?:'POSTED'|'REVERSED';return_id?:string;return_status?:'POSTED'|'REVERSED'}
}

export type SalesCustomerOption={id:string;code:string;name:string}
export type SalesStockOption={product_id:string;product_sku:string;product_name:string;commercial_sku:string;size_code:string;brand_name:string;location_id:string;location_name:string;available_qty:string}
export type SalesFormOptions={contract_version:'cp7.sales-form-options.v1';kind:'CUSTOMER'|'STOCK';physical_at:string;location_id:string|null;availability_basis:'CURRENT_AVAILABLE_NOT_HISTORICAL_STOCK';rows:(SalesCustomerOption|SalesStockOption)[];total:string;offset:number;limit:number;next_offset:number|null}
export function parseSalesFormOptions(v:unknown,kind:'CUSTOMER'|'STOCK',at:string,location:string|null):SalesFormOptions{
 const w=closed(v,['contract_version','kind','physical_at','location_id','availability_basis','rows','total','offset','limit','next_offset'])
 if(w.contract_version!=='cp7.sales-form-options.v1'||w.kind!==kind||!instant(w.physical_at)||Date.parse(String(w.physical_at))!==Date.parse(at)||w.location_id!==location||w.availability_basis!=='CURRENT_AVAILABLE_NOT_HISTORICAL_STOCK'||!Array.isArray(w.rows)||!whole(w.total)||!Number.isSafeInteger(w.offset)||Number(w.offset)<0||!Number.isSafeInteger(w.limit)||Number(w.limit)<1||Number(w.limit)>100||w.rows.length>Number(w.limit))return fail()
 const end=BigInt(Number(w.offset)+w.rows.length),total=BigInt(w.total);if(w.rows.length&&end>total||end<total&&(!w.rows.length||w.next_offset!==Number(end))||end>=total&&w.next_offset!==null)fail()
 const seen=new Set()
 for(const value of w.rows){
  if(kind==='CUSTOMER'){const r=closed(value,['id','code','name']);if(!id(r.id)||!text(r.code)||!text(r.name)||seen.has(r.id))fail();seen.add(r.id)}
  else{const r=closed(value,['product_id','product_sku','product_name','commercial_sku','size_code','brand_name','location_id','location_name','available_qty']),key=`${r.product_id}/${r.location_id}`;if(!id(r.product_id)||!id(r.location_id)||location!==null&&r.location_id!==location||![r.product_sku,r.product_name,r.commercial_sku,r.size_code,r.brand_name,r.location_name].every(text)||!whole(r.available_qty)||r.available_qty==='0'||seen.has(key))fail();seen.add(key)}
 }
 return w as unknown as SalesFormOptions
}
export const salesMoneyInput=(raw:string)=>{const n=raw.trim().replace(',','.');return /^(0|[1-9][0-9]{0,15})(\.[0-9]{1,2})?$/.test(n)?n:null}
export const salesQtyInput=(raw:string)=>/^[1-9][0-9]{0,8}$/.test(raw.trim())?raw.trim():null
export function salesLineTotal(qty:string,price:string,discount:string){const q=salesQtyInput(qty),p=salesMoneyInput(price),d=salesMoneyInput(discount);if(!q||p===null||d===null)return null;const amount=BigInt(q)*cents(p)-cents(d);if(amount<0n)return null;return `${amount/100n}.${String(amount%100n).padStart(2,'0')}`}
