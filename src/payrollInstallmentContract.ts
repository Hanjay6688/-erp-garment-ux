import type {Json} from './types/database.preconnect'
import type {MaterialPage} from './materialContract'
export type InstallmentAction='PAY'|'REVERSE_PAYMENT'|'REVERSE_PAYROLL'
export type InstallmentDocument={payroll_id:string;payroll_number:string;contractor_id:string;contractor_name:string;native_status:string;payment_state:'NOT_APPROVED'|'UNPAID'|'PARTIAL'|'PAID'|'REVERSED';managed:boolean;approved_net:string;paid_amount:string;remaining_amount:string|null;row_version:string;source_review_token:string;review_token:string}
export type InstallmentPayment={id:string;amount:string;payment_date:string;cash_account_id:string;cash_account_code:string;cash_account_name:string;journal_id:string;journal_number:string;status:'POSTED'|'REVERSED';economic_date:string;accounting_date:string;posting_at:string;period_shifted:boolean;reversal_journal_id:string|null;reversal_journal_number:string|null;reversal_economic_date:string|null;reversal_accounting_date:string|null;reversal_posting_at:string|null}
export type InstallmentCash={id:string;code:string;name:string;kind:string;account_id:string;account_code:string;account_name:string;eligible:true;review_token:string}
export type InstallmentRead={contract_version:'cp7.payroll-installment-read.v1';captured_at:string;document:InstallmentDocument;payments:MaterialPage<InstallmentPayment>;cash_accounts:MaterialPage<InstallmentCash>;capabilities:{pay:boolean;reverse_payroll:boolean}}
const fail=():never=>{throw Error('Catatan pembayaran gaji belum lengkap atau sudah berubah. Muat ulang pembayaran.')}
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const text=(v:unknown):v is string=>typeof v==='string'
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,29})$/.test(v)
const token=(v:unknown):v is string=>text(v)&&/^[a-f0-9]{32}$/.test(v)
const time=(v:unknown):v is string=>text(v)&&v.includes('T')&&Number.isFinite(Date.parse(v))
const date=(v:unknown):v is string=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
const nullable=(test:(v:unknown)=>boolean,v:unknown)=>v===null||test(v)
function obj(v:unknown){if(!v||typeof v!=='object'||Array.isArray(v))return fail();return v as Record<string,unknown>}
function closed(v:unknown,keys:string[]){const r=obj(v);if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
export function installmentCents(v:unknown):bigint{
 if(!text(v)||!/^(-?)(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$/.test(v))return fail()
 const [a,b='']=v.replace('-','').split('.'),n=BigInt(a)*100n+BigInt(b.padEnd(2,'0'));return v.startsWith('-')?-n:n
}
export function validInstallmentAmount(v:string,remaining:string){try{const n=installmentCents(v);return n>0n&&n<=installmentCents(remaining)}catch{return false}}
function page<T>(v:unknown,parse:(x:unknown)=>T):MaterialPage<T>{
 const r=closed(v,['rows','total','offset','limit','next_offset'])
 if(!Array.isArray(r.rows)||!whole(r.total)||r.limit!==25||!Number.isSafeInteger(r.offset)||Number(r.offset)<0||r.rows.length>25)return fail()
 const end=BigInt(Number(r.offset))+BigInt(r.rows.length),total=BigInt(r.total)
 if(r.rows.length&&end>total||end<total&&r.next_offset===null||r.next_offset!==null&&(!r.rows.length||r.next_offset!==Number(r.offset)+r.rows.length||end>=total))fail()
 const rows=r.rows.map(parse);if(new Set(rows.map(x=>obj(x).id)).size!==rows.length)fail()
 return {...r,rows}as unknown as MaterialPage<T>
}
function payment(v:unknown):InstallmentPayment{
 const r=closed(v,['id','amount','payment_date','cash_account_id','cash_account_code','cash_account_name','journal_id','journal_number','status','economic_date','accounting_date','posting_at','period_shifted','reversal_journal_id','reversal_journal_number','reversal_economic_date','reversal_accounting_date','reversal_posting_at'])
 if(!['id','cash_account_id','journal_id'].every(k=>uuid(r[k]))||!['cash_account_code','cash_account_name','journal_number'].every(k=>text(r[k]))||installmentCents(r.amount)<=0n||!['payment_date','economic_date','accounting_date'].every(k=>date(r[k]))||r.payment_date!==r.economic_date||!time(r.posting_at)||typeof r.period_shifted!=='boolean'||!['POSTED','REVERSED'].includes(String(r.status))||!nullable(uuid,r.reversal_journal_id)||!nullable(text,r.reversal_journal_number)||!nullable(date,r.reversal_economic_date)||!nullable(date,r.reversal_accounting_date)||!nullable(time,r.reversal_posting_at))fail()
 const inverse=['reversal_journal_id','reversal_journal_number','reversal_economic_date','reversal_accounting_date','reversal_posting_at']
 if(r.status==='POSTED'&&inverse.some(k=>r[k]!==null)||r.status==='REVERSED'&&inverse.some(k=>r[k]===null)||r.reversal_journal_id===r.journal_id)fail()
 return r as unknown as InstallmentPayment
}
function cash(v:unknown):InstallmentCash{
 const r=closed(v,['id','code','name','kind','account_id','account_code','account_name','eligible','review_token'])
 if(!uuid(r.id)||!uuid(r.account_id)||!['code','name','kind','account_code','account_name'].every(k=>text(r[k]))||r.eligible!==true||!token(r.review_token))fail()
 return r as unknown as InstallmentCash
}
export function parseInstallmentRead(v:unknown,payrollId:string):InstallmentRead{
 const r=closed(v,['contract_version','captured_at','document','payments','cash_accounts','capabilities']),d=closed(r.document,['payroll_id','payroll_number','contractor_id','contractor_name','native_status','payment_state','managed','approved_net','paid_amount','remaining_amount','row_version','source_review_token','review_token']),cap=closed(r.capabilities,['pay','reverse_payroll'])
 if(r.contract_version!=='cp7.payroll-installment-read.v1'||!time(r.captured_at)||!uuid(d.payroll_id)||d.payroll_id!==payrollId||!uuid(d.contractor_id)||!text(d.payroll_number)||!text(d.contractor_name)||!['DRAFT','CALCULATED','REVIEW','APPROVED','PAID','REVERSED'].includes(String(d.native_status))||!['NOT_APPROVED','UNPAID','PARTIAL','PAID','REVERSED'].includes(String(d.payment_state))||typeof d.managed!=='boolean'||!whole(d.row_version)||BigInt(d.row_version)<=0n||BigInt(d.row_version)>9223372036854775807n||!token(d.review_token)||!token(d.source_review_token)||typeof cap.pay!=='boolean'||typeof cap.reverse_payroll!=='boolean'||cap.reverse_payroll&&!cap.pay)fail()
 const net=installmentCents(d.approved_net),paid=installmentCents(d.paid_amount);if(paid<0n)fail()
 if(d.native_status==='APPROVED'||d.native_status==='PAID'){
  if(net<0n||paid>net||installmentCents(d.remaining_amount)!==net-paid)fail()
  if(d.native_status==='PAID'&&(paid!==net||d.payment_state!=='PAID')||d.native_status==='APPROVED'&&(d.payment_state!==(paid>0n?'PARTIAL':'UNPAID')||paid>0n&&paid>=net))fail()
 }else if(d.remaining_amount!==null||paid!==0n||d.payment_state!==(d.native_status==='REVERSED'?'REVERSED':'NOT_APPROVED'))fail()
 const payments=page(r.payments,payment),banks=page(r.cash_accounts,cash)
 if(d.managed){
  if(net<=0n||payments.total==='0')fail()
  const visible=payments.rows.filter(p=>p.status==='POSTED').reduce((n,p)=>n+installmentCents(p.amount),0n)
  if(visible>paid||payments.offset===0&&payments.next_offset===null&&visible!==paid)fail()
 }else if(payments.total!=='0')fail()
 return {...r,payments,cash_accounts:banks}as unknown as InstallmentRead
}
function canonical(v:unknown):unknown{if(Array.isArray(v))return v.map(canonical);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical((v as Record<string,unknown>)[k])]));return v}
export function parseInstallmentOutcome(v:unknown,request:string,action:string,envelopePayload:Json){
 const r=closed(v,['contract_version','kind','action','request_id','request_payload','expected_version','payroll_id','payment_id','native_status','payment_state','row_version','review_token']),p=obj(envelopePayload),d=obj(p.document)
 if(r.contract_version!=='cp7.payroll-installment-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!==action||r.request_id!==request||!['PAY','REVERSE_PAYMENT','REVERSE_PAYROLL'].includes(action)||!uuid(r.payroll_id)||r.payroll_id!==d.payroll_id||r.expected_version!==p.expected_version||JSON.stringify(canonical(r.request_payload))!==JSON.stringify(canonical(d))||!whole(r.row_version)||BigInt(r.row_version)<=0n||!token(r.review_token))fail()
 if(action==='PAY'&&(!uuid(r.payment_id)||!['APPROVED','PAID'].includes(String(r.native_status))||!['PARTIAL','PAID'].includes(String(r.payment_state)))||action==='REVERSE_PAYMENT'&&(!uuid(r.payment_id)||r.payment_id!==d.payment_id||r.native_status!=='APPROVED'||!['UNPAID','PARTIAL'].includes(String(r.payment_state)))||action==='REVERSE_PAYROLL'&&(r.payment_id!==null||r.native_status!=='REVERSED'||r.payment_state!=='REVERSED'))fail()
 return r as unknown as {payroll_id:string;payment_id:string|null;native_status:string;payment_state:string;row_version:string;review_token:string}
}
