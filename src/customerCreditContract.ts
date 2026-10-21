import type {Json} from './types/database.preconnect'
import type {SalesRead} from './salesReadContract'

export type CreditSource = NonNullable<SalesRead['detail']>
export type CreditAction = 'APPLY'|'REFUND'|'UNDO'
export type CreditPageKind = 'COHORTS'|'TARGETS'|'CASH'|'EVENTS'
export type CreditPayload = {
  action: CreditAction; cohort_id: string|null; target_sale_id: string|null; cash_account_id: string|null
  restores_event_id: string|null; amount: string|null; physical_at: string; reason: string; reference: string|null
}
export type CreditCommand = CreditPayload & {quote_sha256: string}
export type CreditSelection = {
  action: CreditAction; event_kind: 'APPLY'|'REFUND'; cohort_id: string; customer_id: string
  source_sale_id: string; source_root_sale_id: string; source_current_leaf_id: string
  target_sale_id: string|null; target_root_sale_id: string|null; target_current_leaf_id: string|null
  cash_account_id: string|null; restores_event_id: string|null; amount: string
}
export type CreditReview = {
  contract_version: 'cp7.customer-credit-review.v1'; read_only: true; selection: CreditSelection
  physical_at: string; economic_date: string; transaction_date: string; book_basis: {[key:string]: Json}
  available_credit_after: string; expected_versions: Record<string,string>; quote_sha256: string
}
export type CreditRecovery = {document: CreditCommand; review: CreditReview}
export type CreditCohort = {id:string;return_id:string;return_number:string;available_credit:string;credit_account:{id:string;code:string;name:string}}
export type CreditTarget = {id:string;number:string;customer_id:string;row_version:string;physical_at:string;status:'POSTED'|'PARTIAL_PAID'|'PAID';open_balance:string}
export type CreditCash = {id:string;code:string;name:string;kind:string}
export type CreditEvent = {
  id:string;cohort_id:string;kind:'APPLY'|'REFUND';amount:string;physical_at:string;economic_date:string;book_date:string
  return_number:string;target_sale_id:string|null;target_number:string|null;cash_account_id:string|null;cash_name:string|null
  restores_event_id:string|null;undone_by:string|null
}
export type CreditRows = {COHORTS:CreditCohort;TARGETS:CreditTarget;CASH:CreditCash;EVENTS:CreditEvent}
export type CreditQuery = {kind:CreditPageKind;sale_id:string;expected_version:string;review_token:string;q:string;offset:number;limit:25;dataset_sha256:string|null}
export type CreditWorkspace<K extends CreditPageKind = CreditPageKind> = {
  contract_version:'cp7.customer-credit-workspace.v1';actor_scope_id:string;read_at:string;read_only:true;business_DML:false
  kind:K;q:string;source:{sale_id:string;number:string;customer_id:string;row_version:string;review_token:string}
  capabilities:{apply:boolean;refund:boolean;undo_apply:boolean;undo_refund:boolean};dataset_sha256:string
  page:{offset:number;limit:25;total:string;next_offset:number|null;rows:CreditRows[K][]}
}
export type CreditOutcome = {
  contract_version:'cp7.customer-credit-outcome.v1';kind:'COMMITTED_OUTCOME';action:CreditAction;event_kind:'APPLY'|'REFUND'
  request_id:string;operation_id:string;consumption_event_id:string;journal_id:string;cohort_id:string;source_sale_id:string
  target_sale_id:string|null;cash_account_id:string|null;restores_event_id:string|null;amount:string
  physical_at:string;economic_date:string;transaction_date:string;available_credit:string;invoice_versions:Record<string,string>
}

const fail = ():never => {throw Error('Saldo kredit atau sumber transaksi belum lengkap. Muat ulang invoice dan periksa kembali.')}
const uuid = (v:unknown):v is string => typeof v==='string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v)
const label = (v:unknown):v is string => typeof v==='string' && v.trim().length>0 && v.length<=256
const hash = (v:unknown):v is string => typeof v==='string' && /^[0-9a-f]{64}$/.test(v)
const version = (v:unknown):v is string => typeof v==='string' && /^[1-9][0-9]{0,18}$/.test(v) && BigInt(v)<=9223372036854775807n
const whole = (v:unknown):v is string => typeof v==='string' && /^(0|[1-9][0-9]{0,18})$/.test(v) && BigInt(v)<=9223372036854775807n
function closed(v:unknown,keys:readonly string[]) {
  if(!v || typeof v!=='object' || Array.isArray(v))return fail()
  const row=v as Record<string,unknown>
  if(Object.keys(row).length!==keys.length || keys.some(k=>!Object.hasOwn(row,k)))fail()
  return row
}
export function creditCents(v:unknown):bigint {
  if(typeof v!=='string' || !/^-?(0|[1-9][0-9]{0,19})\.[0-9]{2}$/.test(v) || v==='-0.00')return fail()
  const [a,b]=v.replace(/^-/,'').split('.')
  return (BigInt(a)*100n+BigInt(b))*(v.startsWith('-')?-1n:1n)
}
const nonnegative=(v:unknown)=>creditCents(v)>=0n
const day=(v:unknown):v is string=>typeof v==='string' && /^\d{4}-\d{2}-\d{2}$/.test(v)
  && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10)===v

/** Preserve microseconds in comparisons; Date alone discards the last three. */
function micros(v:unknown):bigint {
  if(typeof v!=='string')return fail()
  const m=/^(\d{4}-\d{2}-\d{2})T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)(?:\.([0-9]{1,6}))?(Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.exec(v)
  if(!m || !day(m[1]))return fail()
  const fraction=(m[5]??'').padEnd(6,'0'),ms=Date.parse(`${m[1]}T${m[2]}:${m[3]}:${m[4]}.${fraction.slice(0,3)}${m[6]}`)
  if(!Number.isFinite(ms))return fail()
  return BigInt(ms)*1000n+BigInt(fraction.slice(3))
}
function wibDay(v:unknown) {return new Date(Number(micros(v)/1000n)+7*60*60*1000).toISOString().slice(0,10)}
function versions(v:unknown):Record<string,string> {
  if(!v || typeof v!=='object' || Array.isArray(v) || !Object.keys(v).length)return fail()
  for(const [key,value] of Object.entries(v))if(!uuid(key) || !version(value))fail()
  return v as Record<string,string>
}

export function creditAmountInput(raw:string):string|null {
  const value=raw.trim().replace(',','.')
  if(!/^(0|[1-9][0-9]{0,15})(?:\.[0-9]{1,2})?$/.test(value))return null
  const [a,b='']=value.split('.'),exact=`${a}.${b.padEnd(2,'0')}`
  return creditCents(exact)>0n?exact:null
}

export function creditPhysicalInput(raw:string):string|null {
  const m=/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})(?::(\d{2})(\.[0-9]{1,6})?)?$/.exec(raw)
  if(!m)return null
  const value=`${m[1]}:${m[2]??'00'}${m[3]??''}+07:00`
  try {micros(value);return value}catch{return null}
}
/** Called only by the operator's explicit 'use now' action. */
export function creditNowInput(now=new Date()) {return new Date(now.getTime()+7*60*60*1000).toISOString().slice(0,23)}

export function parseCreditPayload(value:unknown,command=false):CreditPayload|CreditCommand {
  const p=closed(value,['action','cohort_id','target_sale_id','cash_account_id','restores_event_id','amount','physical_at','reason','reference',...(command?['quote_sha256']:[])])
  if(!['APPLY','REFUND','UNDO'].includes(String(p.action)) || typeof p.reason!=='string' || p.reason!==p.reason.trim() || p.reason.length<5 || p.reason.length>1000
    || p.reference!==null && (typeof p.reference!=='string' || p.reference!==p.reference.trim() || p.reference.length>100)
    || command && !hash(p.quote_sha256))fail()
  micros(p.physical_at)
  for(const key of ['cohort_id','target_sale_id','cash_account_id','restores_event_id'])if(p[key]!==null && !uuid(p[key]))fail()
  if(p.action==='UNDO') {
    if(!uuid(p.restores_event_id) || [p.cohort_id,p.target_sale_id,p.cash_account_id,p.amount].some(x=>x!==null))fail()
  } else if(!uuid(p.cohort_id) || p.restores_event_id!==null || creditCents(p.amount)<=0n
    || (p.action==='APPLY')!==(p.target_sale_id!==null) || (p.action==='REFUND')!==(p.cash_account_id!==null))fail()
  return p as unknown as CreditPayload|CreditCommand
}

export function parseCreditReview(value:unknown,payload:CreditPayload,context?:{source:CreditSource;original?:CreditEvent;target?:CreditTarget}):CreditReview {
  const p=parseCreditPayload(payload),r=closed(value,['contract_version','read_only','selection','physical_at','economic_date','transaction_date','book_basis','available_credit_after','expected_versions','quote_sha256'])
  const s=closed(r.selection,['action','event_kind','cohort_id','customer_id','source_sale_id','source_root_sale_id','source_current_leaf_id',
    'target_sale_id','target_root_sale_id','target_current_leaf_id','cash_account_id','restores_event_id','amount'])
  const map=versions(r.expected_versions)
  if(r.contract_version!=='cp7.customer-credit-review.v1' || r.read_only!==true || !hash(r.quote_sha256) || s.action!==p.action
    || !['APPLY','REFUND'].includes(String(s.event_kind)) || !nonnegative(r.available_credit_after)
    || !day(r.economic_date) || !day(r.transaction_date) || r.transaction_date<r.economic_date
    || micros(r.physical_at)!==micros(p.physical_at) || r.economic_date!==wibDay(r.physical_at))fail()
  for(const key of ['cohort_id','customer_id','source_sale_id','source_root_sale_id','source_current_leaf_id'])if(!uuid(s[key]))fail()
  for(const key of ['target_sale_id','target_root_sale_id','target_current_leaf_id','cash_account_id','restores_event_id'])if(s[key]!==null && !uuid(s[key]))fail()
  if(s.source_sale_id!==s.source_root_sale_id || s.source_sale_id!==s.source_current_leaf_id || !version(map[String(s.source_sale_id)])
    || (s.event_kind==='APPLY')!==(s.target_sale_id!==null) || (s.event_kind==='REFUND')!==(s.cash_account_id!==null)
    || s.target_sale_id===s.source_sale_id || s.target_root_sale_id!==s.target_sale_id || s.target_current_leaf_id!==s.target_sale_id
    || s.target_sale_id!==null && !version(map[String(s.target_sale_id)]) || s.restores_event_id!==p.restores_event_id)fail()
  if(p.action==='UNDO') {if(creditCents(s.amount)>=0n)fail()}
  else if(s.event_kind!==p.action || s.cohort_id!==p.cohort_id || s.target_sale_id!==p.target_sale_id || s.cash_account_id!==p.cash_account_id || s.amount!==p.amount)fail()
  if(!r.book_basis || typeof r.book_basis!=='object' || Array.isArray(r.book_basis) || (r.book_basis as Record<string,unknown>).selected_book_date!==r.transaction_date)fail()
  if(context) {
    const {source,original,target}=context
    if(s.source_sale_id!==source.id || s.customer_id!==source.customer_id || map[source.id]!==source.row_version)fail()
    if(p.action==='UNDO' && (!original || original.id!==p.restores_event_id || original.restores_event_id!==null || original.undone_by!==null
      || s.cohort_id!==original.cohort_id || s.event_kind!==original.kind || creditCents(s.amount)!==-creditCents(original.amount)
      || s.target_sale_id!==original.target_sale_id || s.cash_account_id!==original.cash_account_id))fail()
    if(p.action==='APPLY' && (!target || target.id!==p.target_sale_id || target.customer_id!==source.customer_id || map[target.id]!==target.row_version))fail()
  }
  return r as unknown as CreditReview
}

export function parseCreditRecovery(value:unknown,action?:string):CreditRecovery {
  const r=closed(value,['document','review']),document=parseCreditPayload(r.document,true) as CreditCommand
  const {quote_sha256,...plain}=document,review=parseCreditReview(r.review,plain)
  if(quote_sha256!==review.quote_sha256 || action!==undefined && action!==`CREDIT_${document.action}`)fail()
  return {document,review}
}

export function parseCreditOutcome(value:unknown,request:string,recovery:CreditRecovery):CreditOutcome {
  const {review}=parseCreditRecovery(recovery),s=review.selection
  const r=closed(value,['contract_version','kind','action','event_kind','request_id','operation_id','consumption_event_id','journal_id','cohort_id',
    'source_sale_id','target_sale_id','cash_account_id','restores_event_id','amount','physical_at','economic_date','transaction_date','available_credit','invoice_versions'])
  if(!uuid(request) || r.contract_version!=='cp7.customer-credit-outcome.v1' || r.kind!=='COMMITTED_OUTCOME' || r.request_id!==request
    || !uuid(r.operation_id) || r.operation_id!==r.consumption_event_id || !uuid(r.journal_id)
    || ['action','event_kind','cohort_id','source_sale_id','target_sale_id','cash_account_id','restores_event_id','amount'].some(k=>r[k]!==s[k as keyof CreditSelection])
    || r.physical_at!==review.physical_at || r.economic_date!==review.economic_date || r.transaction_date!==review.transaction_date
    || r.available_credit!==review.available_credit_after)fail()
  const actual=versions(r.invoice_versions),before=review.expected_versions
  if(Object.keys(actual).length!==Object.keys(before).length)fail()
  for(const [id,versionBefore] of Object.entries(before)) {
    const expected=BigInt(versionBefore)+(id===s.source_current_leaf_id || id===s.target_current_leaf_id?1n:0n)
    if(actual[id]!==expected.toString())fail()
  }
  return r as unknown as CreditOutcome
}

export function creditQuery(kind:CreditPageKind,source:CreditSource,q='',offset=0,dataset_sha256:string|null=null):CreditQuery {
  if(!uuid(source.id) || !version(source.row_version) || typeof source.review_token!=='string' || !/^[0-9a-f]{32}$/.test(source.review_token)
    || q.length>120 || q!==q.trim() || !Number.isSafeInteger(offset) || offset<0 || offset>1000000 || offset%25!==0
    || dataset_sha256!==null && !hash(dataset_sha256) || offset>0 && dataset_sha256===null || ['COHORTS','EVENTS'].includes(kind)&&q!=='')return fail()
  return {kind,sale_id:source.id,expected_version:source.row_version,review_token:source.review_token,q,offset,limit:25,dataset_sha256}
}

export function parseCreditWorkspace<K extends CreditPageKind>(value:unknown,query:CreditQuery & {kind:K},source:CreditSource,actor:string):CreditWorkspace<K> {
  const r=closed(value,['contract_version','actor_scope_id','read_at','read_only','business_DML','kind','q','source','capabilities','dataset_sha256','page'])
  const s=closed(r.source,['sale_id','number','customer_id','row_version','review_token'])
  const caps=closed(r.capabilities,['apply','refund','undo_apply','undo_refund']),page=closed(r.page,['offset','limit','total','next_offset','rows'])
  creditQuery(query.kind,source,query.q,query.offset,query.dataset_sha256)
  if(!uuid(actor) || r.contract_version!=='cp7.customer-credit-workspace.v1' || r.actor_scope_id!==actor || r.read_only!==true || r.business_DML!==false
    || r.kind!==query.kind || r.q!==query.q || s.sale_id!==source.id || s.number!==source.number || s.customer_id!==source.customer_id
    || s.row_version!==source.row_version || s.review_token!==source.review_token || !hash(r.dataset_sha256)
    || query.dataset_sha256!==null && r.dataset_sha256!==query.dataset_sha256 || Object.values(caps).some(x=>typeof x!=='boolean')
    || page.offset!==query.offset || page.limit!==25 || !whole(page.total) || !Array.isArray(page.rows))fail()
  micros(r.read_at)
  const remaining=BigInt(page.total as string)-BigInt(query.offset),n=remaining<=0n?0:remaining>=25n?25:Number(remaining)
  if((page.rows as unknown[]).length!==n || page.next_offset!==(BigInt(query.offset+n)<BigInt(page.total as string)?query.offset+25:null))fail()
  const seen=new Set<string>()
  for(const value of page.rows as unknown[]) {
    let row:Record<string,unknown>
    if(query.kind==='COHORTS') {
      row=closed(value,['id','return_id','return_number','available_credit','credit_account'])
      const account=closed(row.credit_account,['id','code','name'])
      if(!uuid(row.return_id) || !label(row.return_number) || !nonnegative(row.available_credit) || !uuid(account.id) || !label(account.code) || !label(account.name))fail()
    } else if(query.kind==='TARGETS') {
      row=closed(value,['id','number','customer_id','row_version','physical_at','status','open_balance'])
      if(!label(row.number) || row.id===source.id || row.customer_id!==source.customer_id || !version(row.row_version)
        || !['POSTED','PARTIAL_PAID','PAID'].includes(String(row.status)) || !nonnegative(row.open_balance)
        || (row.status==='PAID')!==(creditCents(row.open_balance)===0n))fail()
      micros(row.physical_at)
    } else if(query.kind==='CASH') {
      row=closed(value,['id','code','name','kind'])
      if(![row.code,row.name,row.kind].every(label))fail()
    } else {
      row=closed(value,['id','cohort_id','kind','amount','physical_at','economic_date','book_date','return_number','target_sale_id','target_number','cash_account_id','cash_name','restores_event_id','undone_by'])
      for(const key of ['target_sale_id','cash_account_id','restores_event_id','undone_by'])if(row[key]!==null && !uuid(row[key]))fail()
      if(!uuid(row.cohort_id) || !['APPLY','REFUND'].includes(String(row.kind)) || creditCents(row.amount)===0n
        || (creditCents(row.amount)<0n)!==(row.restores_event_id!==null) || row.restores_event_id!==null && row.undone_by!==null
        || (row.kind==='APPLY')!==(row.target_sale_id!==null) || (row.kind==='REFUND')!==(row.cash_account_id!==null)
        || row.target_sale_id!==null && !label(row.target_number) || row.target_sale_id===null && row.target_number!==null
        || row.cash_account_id!==null && !label(row.cash_name) || row.cash_account_id===null && row.cash_name!==null
        || !label(row.return_number) || !day(row.economic_date) || !day(row.book_date) || row.book_date<row.economic_date
        || row.economic_date!==wibDay(row.physical_at))fail()
    }
    const rowId=row.id
    if(!uuid(rowId) || seen.has(rowId))return fail()
    seen.add(rowId)
  }
  return r as unknown as CreditWorkspace<K>
}
