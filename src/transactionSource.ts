export const transactionSourceRoutes={RECEIPT:'procurement',MATERIAL_TRANSFER:'materials-rolls',MATERIAL_COUNT:'stock-adjustment',FG_ADJUSTMENT:'stock-adjustment',SALE:'sales-invoice',MISC_FINANCE:'finance-journal'} as const
export type TransactionDomain=keyof typeof transactionSourceRoutes
export type SourceReference={source_type:string;source_id:string}
export type TransactionDocument={domain:TransactionDomain;route:typeof transactionSourceRoutes[TransactionDomain]|'sales-payments'|'sales-returns';id:string;number:string;status:string|null;revision:string|null;focus:{kind:'PURCHASE_INVOICE'|'SALES_PAYMENT'|'SALES_RETURN';id:string;page_offset:number}|null}
export type TransactionSource={source:SourceReference;status:'AVAILABLE'|'UNSUPPORTED_SOURCE';document:TransactionDocument|null;readAt:string}
const fail=():never=>{throw Error('Transaksi asal belum sesuai referensi dan akses ERP. Muat ulang sumbernya.')}
const object=(v:unknown,keys:string[])=>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))fail();return v as Record<string,unknown>}
export const sourceId=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)
export function parseTransactionSource(v:unknown,expected:SourceReference,actor:string):TransactionSource{
 const e=object(v,['contract_version','actor_scope_id','source','status','document','read_at','business_DML']),s=object(e.source,['source_type','source_id'])
 if(e.contract_version!=='cp7.transaction-source.v1'||e.actor_scope_id!==actor||e.business_DML!==false||s.source_type!==expected.source_type||s.source_id!==expected.source_id||!sourceId(s.source_id)||typeof s.source_type!=='string'||!/^[A-Z][A-Z0-9_]{0,79}$/.test(s.source_type)||typeof e.read_at!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(e.read_at)||!Number.isFinite(Date.parse(e.read_at)))fail()
 if(e.status==='UNSUPPORTED_SOURCE'){if(e.document!==null)fail();return{source:{...expected},status:e.status,document:null,readAt:e.read_at as string}}
 if(e.status!=='AVAILABLE')fail()
 const d=object(e.document,['domain','route','id','number','status','revision','focus'])
 if(typeof d.domain!=='string'||!Object.hasOwn(transactionSourceRoutes,d.domain)||!sourceId(d.id)||typeof d.number!=='string'||!d.number.trim()||d.number.length>256||d.status!==null&&(typeof d.status!=='string'||!/^[A-Z][A-Z0-9_]{0,39}$/.test(d.status))||d.revision!==null&&(typeof d.revision!=='string'||!/^[1-9][0-9]{0,18}$/.test(d.revision)||BigInt(d.revision)>9223372036854775807n))fail()
 const route=transactionSourceRoutes[d.domain as TransactionDomain]
 if(d.route!==route&&!(d.domain==='SALE'&&['sales-payments','sales-returns'].includes(String(d.route))))fail()
 const domains:Record<string,TransactionDomain>={MATERIAL_PURCHASE:'RECEIPT',MATERIAL_PURCHASE_GRNI_RECLASS:'RECEIPT',MATERIAL_PURCHASE_REVERSAL:'RECEIPT',MATERIAL_PURCHASE_ITEM:'RECEIPT',MATERIAL_PURCHASE_ROLL:'RECEIPT',MATERIAL_SUPPLIER_INVOICE:'RECEIPT',MATERIAL_SUPPLIER_INVOICE_LINE:'RECEIPT',SUPPLIER_PAYMENT:'RECEIPT',MATERIAL_TRANSFER:'MATERIAL_TRANSFER',MATERIAL_TRANSFER_ITEM:'MATERIAL_TRANSFER',MATERIAL_ADJUSTMENT:'MATERIAL_COUNT',MATERIAL_ADJUSTMENT_ITEM:'MATERIAL_COUNT',FG_ADJUSTMENT:'FG_ADJUSTMENT',FG_ADJUSTMENT_ITEM:'FG_ADJUSTMENT',SALE:'SALE',SALE_ITEM:'SALE',SALES_ITEM:'SALE',SALES_PAYMENT:'SALE',SALES_RETURN:'SALE',SALES_RETURN_ITEM:'SALE',MISC_FINANCE:'MISC_FINANCE',MISC_CORRECTION_TIME_NEUTRAL:'MISC_FINANCE',MISC_CORRECTION_EFFECTIVE:'MISC_FINANCE'}
 if(expected.source_type!=='JOURNAL_REVERSAL'&&domains[expected.source_type]!==d.domain)fail()
 const direct=['MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS','MATERIAL_PURCHASE_REVERSAL','MATERIAL_TRANSFER','MATERIAL_ADJUSTMENT','FG_ADJUSTMENT','SALE','MISC_FINANCE','MISC_CORRECTION_TIME_NEUTRAL','MISC_CORRECTION_EFFECTIVE']
 if(direct.includes(expected.source_type)&&d.id!==expected.source_id)fail()
 if(d.focus!==null){const f=object(d.focus,['kind','id','page_offset']);if(!Number.isSafeInteger(f.page_offset)||Number(f.page_offset)<0||Number(f.page_offset)>1000000||Number(f.page_offset)%25!==0||!sourceId(f.id)||(f.kind==='PURCHASE_INVOICE'?d.domain!=='RECEIPT':!['SALES_PAYMENT','SALES_RETURN'].includes(String(f.kind))||d.domain!=='SALE'))fail()}
 if(expected.source_type==='SALES_PAYMENT'&&(d.route!=='sales-payments'||(d.focus as {kind?:string;id?:string}|null)?.kind!=='SALES_PAYMENT'||(d.focus as {id?:string}).id!==expected.source_id))fail()
 if(['SALES_RETURN','SALES_RETURN_ITEM'].includes(expected.source_type)&&(d.route!=='sales-returns'||(d.focus as {kind?:string}|null)?.kind!=='SALES_RETURN'))fail()
 if(expected.source_type==='SALES_RETURN'&&(d.focus as {id?:string}).id!==expected.source_id)fail()
 return{source:{...expected},status:'AVAILABLE',document:structuredClone(d) as TransactionDocument,readAt:e.read_at as string}
}
