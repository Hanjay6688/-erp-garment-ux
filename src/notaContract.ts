import type {MaterialPage} from './materialContract'
import type {Json} from './types/database.preconnect'
export type NotaLine={source_type:string;source_id:string;component_id:string;component_code:string;component_name:string;source_qty:string;eligible_qty:string;allocated_qty:string;remaining_qty:string;held_qty:string;eligible_at:string;eligibility_reason:string;rate?:string;amount?:string}
export type NotaCard={card_key:string;source_type:'PRODUCTION'|'REWORK'|'FG_REPAIR';origin_id:string;origin_number:string;contractor_id:string;contractor_name:string;contractor_active:boolean;po_id:string|null;po_number:string|null;cutting_group_id:string|null;group_number:string|null;bs_case_id:string|null;eligible_at:string;line_count:string;source_token:string;lines:NotaLine[];basis:'NATIVE_REMAINING_COMPONENT_ENTITLEMENT';remaining_amount?:string;claimed_by_note?:string|null}
export type NotaDocument={id:string;note_number:string;contractor_id:string;contractor_name:string;note_date:string;period_start:string;period_end:string;notes:string;status:'DRAFT'|'POSTED'|'VOID';row_version:string;target_payroll_id:string|null;target_version:string|null;posted_payroll_id:string|null;payroll_number:string|null;payroll_status:string|null;posted_at:string|null;void_reason:string|null;created_at:string;updated_at:string;cards:NotaCard[];amount?:string}
export type NotaPayroll={id:string;payroll_number:string;contractor_id:string;period_start:string;period_end:string;status:'DRAFT'|'CALCULATED'|'REVIEW';row_version:string}
export type NotaSection='SOURCES'|'NOTES'|'PAYROLLS'
export type NotaWorkspace<T>={contract_version:'cp7.nota-workspace.v1';section:NotaSection;read_at:string;financial_captured:boolean;can_post:boolean;page:MaterialPage<T>}
const fail=():never=>{throw Error('Data nota belum lengkap atau hasilnya tidak cocok. Muat ulang nota.')}
const text=(v:unknown):v is string=>typeof v==='string'
// Accepted legacy masters contain canonical PostgreSQL UUIDs without RFC version
// or variant bits. Validate their representation, not a new identity policy.
const id=(v:unknown):v is string=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const nullable=(check:(v:unknown)=>boolean,v:unknown)=>v===null||check(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,29})$/.test(v)
const version=(v:unknown)=>whole(v)&&v!=='0'
const instant=(v:unknown)=>text(v)&&/T/.test(v)&&Number.isFinite(Date.parse(v))
const date=(v:unknown)=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))
const money=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,25})(\.[0-9]{1,2})?$/.test(v)
export const notaCents=(v:string)=>{if(!money(v))return fail();const [a,b='']=v.split('.');return BigInt(a)*100n+BigInt(b.padEnd(2,'0'))}
export function notaObject(v:unknown){if(!v||typeof v!=='object'||Array.isArray(v))return fail();return v as Record<string,unknown>}
function closed(v:unknown,keys:string[]){const r=notaObject(v);if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))return fail();return r}
function card(v:unknown,financial:boolean,claimed:boolean):string{
 const c=closed(v,['card_key','source_type','origin_id','origin_number','contractor_id','contractor_name','contractor_active','po_id','po_number','cutting_group_id','group_number','bs_case_id','eligible_at','line_count','source_token','lines','basis',...(financial?['remaining_amount']:[]),...(claimed?['claimed_by_note']:[])])
 if(!id(c.origin_id)||!id(c.contractor_id)||!text(c.source_type)||!['PRODUCTION','REWORK','FG_REPAIR'].includes(c.source_type)||c.card_key!==`${c.source_type}:${c.origin_id}:${c.contractor_id}`||!text(c.origin_number)||!text(c.contractor_name)||typeof c.contractor_active!=='boolean'||!['po_id','cutting_group_id','bs_case_id'].every(k=>nullable(id,c[k]))||!['po_number','group_number'].every(k=>nullable(text,c[k]))||!instant(c.eligible_at)||!whole(c.line_count)||!text(c.source_token)||!/^[a-f0-9]{32}$/.test(c.source_token)||c.basis!=='NATIVE_REMAINING_COMPONENT_ENTITLEMENT'||!Array.isArray(c.lines)||!c.lines.length||String(c.lines.length)!==c.line_count||claimed&&!nullable(id,c.claimed_by_note))return fail()
 const seen=new Set<string>();let sum=0n
 for(const v of c.lines){
  const l=closed(v,['source_type','source_id','component_id','component_code','component_name','source_qty','eligible_qty','allocated_qty','remaining_qty','held_qty','eligible_at','eligibility_reason',...(financial?['rate','amount']:[])])
  if(l.source_type!==c.source_type||!id(l.source_id)||!id(l.component_id)||!text(l.component_code)||!text(l.component_name)||!text(l.eligibility_reason)||!instant(l.eligible_at)||!['source_qty','eligible_qty','allocated_qty','remaining_qty','held_qty'].every(k=>whole(l[k])))fail()
  const q=(k:string)=>BigInt(l[k] as string),key=`${l.source_id}:${l.component_id}`
  if(seen.has(key)||q('remaining_qty')<=0n||q('eligible_qty')>q('source_qty')||q('allocated_qty')+q('remaining_qty')!==q('eligible_qty'))fail();seen.add(key)
  if(financial){if(!money(l.rate)||!money(l.amount)||notaCents(l.rate)*q('remaining_qty')!==notaCents(l.amount))return fail();sum+=notaCents(l.amount)}
 }
 if(financial&&(!money(c.remaining_amount)||notaCents(c.remaining_amount)!==sum))fail()
 return c.card_key as string
}
function document(v:unknown,financial:boolean):string{
 const d=closed(v,['id','note_number','contractor_id','contractor_name','note_date','period_start','period_end','notes','status','row_version','target_payroll_id','target_version','posted_payroll_id','payroll_number','payroll_status','posted_at','void_reason','created_at','updated_at','cards',...(financial?['amount']:[])])
 if(!id(d.id)||!id(d.contractor_id)||!['note_number','contractor_name','notes'].every(k=>text(d[k]))||!['note_date','period_start','period_end'].every(k=>date(d[k]))||!text(d.status)||!['DRAFT','POSTED','VOID'].includes(d.status)||!version(d.row_version)||!nullable(version,d.target_version)||!nullable(id,d.target_payroll_id)||!nullable(id,d.posted_payroll_id)||!['payroll_number','payroll_status','void_reason'].every(k=>nullable(text,d[k]))||!nullable(instant,d.posted_at)||!instant(d.created_at)||!instant(d.updated_at)||!Array.isArray(d.cards)||!d.cards.length||String(d.period_start)>String(d.period_end))return fail()
 const keys=d.cards.map(c=>{const key=card(c,financial,false);if(notaObject(c).contractor_id!==d.contractor_id)fail();return key});if(new Set(keys).size!==keys.length)fail()
 if(d.status==='POSTED'&&(!id(d.posted_payroll_id)||!instant(d.posted_at))||d.status!=='POSTED'&&(d.posted_payroll_id!==null||d.posted_at!==null))fail()
 if(financial&&(!money(d.amount)||notaCents(d.amount)!==d.cards.reduce((a,c)=>a+notaCents(notaObject(c).remaining_amount as string),0n)))fail()
 return d.id
}
function payroll(v:unknown):string{
 const p=closed(v,['id','payroll_number','contractor_id','period_start','period_end','status','row_version'])
 if(!id(p.id)||!id(p.contractor_id)||!text(p.payroll_number)||!date(p.period_start)||!date(p.period_end)||!version(p.row_version)||!text(p.status)||!['DRAFT','CALCULATED','REVIEW'].includes(p.status))return fail();return p.id
}
export function parseNotaWorkspace(v:unknown,section:'SOURCES'):NotaWorkspace<NotaCard>
export function parseNotaWorkspace(v:unknown,section:'NOTES'):NotaWorkspace<NotaDocument>
export function parseNotaWorkspace(v:unknown,section:'PAYROLLS'):NotaWorkspace<NotaPayroll>
export function parseNotaWorkspace(v:unknown,section:NotaSection):NotaWorkspace<NotaCard|NotaDocument|NotaPayroll>{
 const w=closed(v,['contract_version','section','read_at','financial_captured','can_post','page'])
 if(w.contract_version!=='cp7.nota-workspace.v1'||w.section!==section||!instant(w.read_at)||typeof w.financial_captured!=='boolean'||typeof w.can_post!=='boolean')fail()
 const p=closed(w.page,['rows','total','offset','limit','next_offset'])
 if(!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||p.rows.length>Number(p.limit))return fail()
 const end=BigInt(Number(p.offset))+BigInt(p.rows.length),total=BigInt(p.total)
 if(p.rows.length&&end>total||end<total&&p.next_offset===null||p.next_offset!==null&&(p.next_offset!==Number(p.offset)+p.rows.length||!p.rows.length||end>=total))fail()
 const financial=w.financial_captured as boolean,keys=p.rows.map(v=>section==='SOURCES'?card(v,financial,true):section==='NOTES'?document(v,financial):payroll(v));if(new Set(keys).size!==keys.length)fail()
 return w as unknown as NotaWorkspace<NotaCard|NotaDocument|NotaPayroll>
}
export function parseNotaOutcome(v:unknown,request:string,action:string,payload:Json){
 const r=closed(v,['contract_version','kind','action','request_id','note_id','status','row_version','payroll_id']),p=notaObject(payload),d=notaObject(p.document)
 if(r.contract_version!=='cp7.nota-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!==action||r.request_id!==request||!id(r.note_id)||!version(r.row_version)||r.status!==({SAVE:'DRAFT',POST:'POSTED',VOID:'VOID'} as Record<string,string>)[action]||!nullable(id,r.payroll_id)||action==='POST'&&!id(r.payroll_id)||action!=='POST'&&r.payroll_id!==null||d.id&&r.note_id!==d.id)fail()
 return r as {note_id:string;status:string;row_version:string;payroll_id:string|null}
}
