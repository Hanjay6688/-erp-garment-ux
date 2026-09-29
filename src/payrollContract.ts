import type {MaterialPage} from './materialContract'
import {parseNotaWorkspace,type NotaDocument} from './notaContract'
export type PayrollSection='PAYROLLS'|'WORK'|'ATTENDANCE'|'REIMBURSEMENTS'|'DEDUCTIONS'|'NOTES'
export type PayrollHeader={id:string;payroll_number:string;contractor_id:string;contractor_name:string;attendance_required:boolean;period_start:string;period_end:string;status:string;row_version:string;review_token:string;notes:string|null;labor_total:string;attendance_total:string;reimburse_total:string;deduction_total:string;manual_adjustment:string;net_payable:string;payment_cash_account_id:string|null;payment_cash_account_name:string|null;payment_date:string;settled_at:string|null;created_at:string;updated_at:string;totals_match_items:boolean;counts:{work:string;attendance:string;reimbursements:string;deductions:string;notes:string}}
export type PayrollLine=Record<string,string|null>
export type PayrollRead={contract_version:'cp7.payroll-workspace.v1';section:PayrollSection;read_at:string;capabilities:{approve:boolean;pay:boolean};document:PayrollHeader|null;page:MaterialPage<PayrollHeader|PayrollLine|NotaDocument>}
const fail=():never=>{throw Error('Rincian payroll belum lengkap atau sudah berubah. Muat ulang payroll.')}
const text=(v:unknown):v is string=>typeof v==='string'
const uuid=(v:unknown)=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,29})$/.test(v)
const date=(v:unknown)=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))
const time=(v:unknown)=>text(v)&&v.includes('T')&&Number.isFinite(Date.parse(v))
const nullable=(test:(v:unknown)=>boolean,v:unknown)=>v===null||test(v)
const decimal=(v:unknown,scale=2)=>text(v)&&new RegExp('^-?(0|[1-9][0-9]{0,25})(\\.[0-9]{1,'+scale+'})?$').test(v)
function cents(v:unknown){if(!decimal(v))return fail();const s=v as string,[a,b='']=s.replace('-','').split('.'),c=BigInt(a)*100n+BigInt(b.padEnd(2,'0'));return s.startsWith('-')?-c:c}
function obj(v:unknown){if(!v||typeof v!=='object'||Array.isArray(v))return fail();return v as Record<string,unknown>}
function closed(v:unknown,keys:string[]){const r=obj(v);if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
const amounts=['labor_total','attendance_total','reimburse_total','deduction_total','manual_adjustment','net_payable']
function header(v:unknown):PayrollHeader{
 const p=closed(v,['id','payroll_number','contractor_id','contractor_name','attendance_required','period_start','period_end','status','row_version','review_token','notes',...amounts,'payment_cash_account_id','payment_cash_account_name','payment_date','settled_at','created_at','updated_at','totals_match_items','counts'])
 if(!uuid(p.id)||!uuid(p.contractor_id)||!text(p.payroll_number)||!text(p.contractor_name)||typeof p.attendance_required!=='boolean'||typeof p.totals_match_items!=='boolean'||!['period_start','period_end','payment_date'].every(k=>date(p[k]))||!text(p.status)||!['DRAFT','CALCULATED','REVIEW','APPROVED','PAID','REVERSED'].includes(p.status)||!whole(p.row_version)||p.row_version==='0'||!text(p.review_token)||!/^[a-f0-9]{32}$/.test(p.review_token)||!nullable(text,p.notes)||!amounts.every(k=>decimal(p[k]))||!nullable(uuid,p.payment_cash_account_id)||!nullable(text,p.payment_cash_account_name)||!nullable(time,p.settled_at)||!time(p.created_at)||!time(p.updated_at))fail()
 if(cents(p.labor_total)+cents(p.attendance_total)+cents(p.reimburse_total)-cents(p.deduction_total)+cents(p.manual_adjustment)!==cents(p.net_payable))fail()
 const counts=closed(p.counts,['work','attendance','reimbursements','deductions','notes']);if(!Object.values(counts).every(whole))fail()
 return p as unknown as PayrollHeader
}
const lineKeys={WORK:['id','po_id','po_number','component_id','component_code','component_name','source_type','source_id','qty','rate','amount'],ATTENDANCE:['id','worker_id','attendance_record_id','date','worker_name','job_description','paid_fraction','daily_rate','rate_version_id','amount'],REIMBURSEMENTS:['id','amount','description','source_type','source_id','po_id','opening_payable_balance_id','opening_carry_entitlement_id','opening_carry_qty','bc_credit_event_id'],DEDUCTIONS:['id','type','amount','notes','contractor_issue_item_id','bs_resolution_id','opening_cash_advance_balance_id']}
export function parsePayrollRead(v:unknown,section:PayrollSection):PayrollRead{
 const r=closed(v,['contract_version','section','read_at','capabilities','document','page']),cap=closed(r.capabilities,['approve','pay']),p=closed(r.page,['rows','total','offset','limit','next_offset'])
 if(r.contract_version!=='cp7.payroll-workspace.v1'||r.section!==section||!time(r.read_at)||typeof cap.approve!=='boolean'||typeof cap.pay!=='boolean'||!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||p.rows.length>Number(p.limit))return fail()
 const end=BigInt(Number(p.offset))+BigInt(p.rows.length),total=BigInt(p.total)
 if(p.rows.length&&end>total||end<total&&p.next_offset===null||p.next_offset!==null&&(p.next_offset!==Number(p.offset)+p.rows.length||!p.rows.length||end>=total))fail()
 if(section==='PAYROLLS'){if(r.document!==null)fail();p.rows.forEach(header)}else{
  const h=header(r.document);if(h.counts[section.toLowerCase() as keyof PayrollHeader['counts']]!==p.total)fail()
  if(section==='NOTES'){
   const notes=parseNotaWorkspace({contract_version:'cp7.nota-workspace.v1',section:'NOTES',read_at:r.read_at,financial_captured:true,can_post:false,page:p},'NOTES')
   if(notes.page.rows.some(n=>n.status!=='POSTED'||n.posted_payroll_id!==h.id||n.contractor_id!==h.contractor_id||n.payroll_status!==h.status||n.payroll_number!==h.payroll_number))fail()
  }
  else for(const row of p.rows){
   const l=closed(row,lineKeys[section]);if(!uuid(l.id)||!Object.values(l).every(x=>nullable(text,x))||!decimal(l.amount))fail()
   if(Object.entries(l).some(([k,x])=>k.endsWith('_id')&&!nullable(uuid,x)))fail()
   if(section==='WORK'&&(!text(l.component_name)||!text(l.component_code)||!['PRODUCTION','REWORK','FG_REPAIR'].includes(String(l.source_type))||!uuid(l.component_id)||!uuid(l.source_id)||!whole(l.qty)||!decimal(l.rate)||cents(l.rate)*BigInt(l.qty)!==cents(l.amount)))fail()
   if(section==='ATTENDANCE'&&(!date(l.date)||!decimal(l.paid_fraction,4)||!decimal(l.daily_rate)))fail()
   if(section==='REIMBURSEMENTS'&&!nullable(v=>decimal(v,6),l.opening_carry_qty))fail()
  }
 }
 if(new Set(p.rows.map(x=>obj(x).id)).size!==p.rows.length)fail()
 return r as unknown as PayrollRead
}
