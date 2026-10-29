import type { ProductionEnvelope } from './productionRecovery'
import { hppPoolRefusalText } from './hppPoolContract'
import { normalizeClientError } from './lib/clientError'

// UI-only contract for WIRE_CONTRACT.md at 7e91ec5e6. No installation claim.
export const ATTENDANCE_CHOICE_ACTIONS = ['CHOOSE', 'CORRECT', 'REVERSE', 'ALLOCATE', 'CANCEL_ALLOCATION'] as const
export type AttendanceChoiceAction = typeof ATTENDANCE_CHOICE_ACTIONS[number]
export type AttendanceChoice = 'CARRY' | 'EXPENSE'
export type AttendanceChoicePayload = { period_start:string;period_end:string;choice:AttendanceChoice|null;output_start:string|null;output_end:string|null;reason:string }
export type AttendanceChoiceSavePayload = AttendanceChoicePayload & {review_token:string}
export type AttendanceChoiceQuery = {period_start:string;period_end:string;offset:number;limit:number}
export type AttendanceChoiceHistory = {event_id:string;decision_id:string;reason:string;recorded_at:string;actor:string} & (
 | {event:'CHOOSE';choice:AttendanceChoice;amount_cents:string;journal_id:string|null;correction_of:string|null}
 | {event:'REVERSE';journal_id:string|null}
 | {event:'ALLOCATE';allocation_id:string;pool_id:string;output_start:string;output_end:string}
 | {event:'CANCEL_ALLOCATION';allocation_id:string;pool_id:string;journal_id:string})
export type AttendanceChoiceWorkspace = {contract_version:'cp7.attendance-period-choice-workspace.v1';period_start:string;period_end:string;
 amount_cents:string|null;source_binding:string|null;original_period_sewing_qty:string|null;source_problem:string|null;closed_through:string|null;
 current_choice:{decision_id:string;choice:AttendanceChoice;reason:string;journal_id:string|null}|null;
 current_allocation:{allocation_id:string;pool_id:string;output_start:string;output_end:string}|null;
 history:AttendanceChoiceHistory[];history_total:string;offset:number;limit:number;next_offset:number|null;can_manage:boolean;business_DML:false}
export type AttendanceChoicePreview = {contract_version:'cp7.attendance-period-choice.v1';action:AttendanceChoiceAction;payload:AttendanceChoicePayload;
 amount:string;amount_cents:string;source_count:string;denominator_qty:string|null;economic_date:string|null;book_date:string|null;
 inverse_economic_date:string|null;inverse_book_date:string|null;decision_id:string|null;allocation_id:string|null;pool_id:string|null;
 source_binding:string;review_token:string;expense_account:{id:string;code:string;name:string}|null;can_apply:true;business_DML:false}
export type AttendanceChoiceOutcome = {contract_version:'cp7.attendance-period-choice-command.v1';action:AttendanceChoiceAction;request_id:string;
 period_start:string;period_end:string;decision_id:string;event_id:string;amount_cents:string;pool_id:string|null;
 native_result:null|{pool_id:string;status:'ACTIVE';row_version:number;journal_entry_id:string;validation:'PASS'}
 |{pool_id:string;status:'CANCELLED';row_version:number;reversal_journal_entry_id:string;residue_expected:0};inverse_journal_id:string|null;
 dated_WIP:{all_original_debits_nonnegative_on_every_economic_and_book_cutoff:true;dated_available_WIP:{line_id:string;axis:'ECONOMIC'|'BOOK';date:string;available_cents:string}[]};status:'COMMITTED'}
type Row = Record<string,unknown>
const fail = ():never => {throw Error('Data pilihan biaya absensi berubah atau belum lengkap. Muat ulang periode, lalu periksa lagi.')}
const text = (v:unknown):v is string => typeof v==='string'
// Native deterministic md5::uuid identities have arbitrary version/variant bits.
const uuid = (v:unknown):v is string => text(v)&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v)
const nullableUuid = (v:unknown) => v===null||uuid(v)
const sha = (v:unknown):v is string => text(v)&&/^[a-f0-9]{64}$/.test(v)
const whole = (v:unknown):v is string => text(v)&&/^(0|[1-9][0-9]*)$/.test(v)
const integer = (v:unknown):v is string => whole(v)&&BigInt(v)<=9223372036854775807n
const positive = (v:unknown):v is string => integer(v)&&BigInt(v)>0n
// PostgreSQL btrim(text) removes U+0020; length(text) counts Unicode characters.
export const attendanceChoiceReason=(v:string)=>v.replace(/^ +| +$/g,'')
const reason = (v:unknown):v is string => text(v)&&v===attendanceChoiceReason(v)&&Array.from(v).length>=5&&Array.from(v).length<=1000
const choice = (v:unknown):v is AttendanceChoice => v==='CARRY'||v==='EXPENSE'
const closed = (v:unknown,keys:readonly string[]):Row => {
 if(!v||typeof v!=='object'||Array.isArray(v))return fail()
 const row=v as Row
 if(Object.keys(row).length!==keys.length||keys.some(k=>!Object.hasOwn(row,k)))return fail()
 return row
}
export function attendanceChoiceDay(v:unknown):v is string {
 if(!text(v)||!/^\d{4}-\d{2}-\d{2}$/.test(v)||v.slice(0,4)==='0000')return false
 const d=new Date(v+'T00:00:00Z');return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===v
}
const nullableDay = (v:unknown) => v===null||attendanceChoiceDay(v)
function period(a:unknown,b:unknown){if(!attendanceChoiceDay(a)||!attendanceChoiceDay(b)||b<a||(Date.parse(b)-Date.parse(a))/86400000>366)fail()}
function stamp(v:unknown){if(!text(v)||!attendanceChoiceDay(v.slice(0,10))||!/^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(v)||!Number.isFinite(Date.parse(v)))fail()}
function micros(v:string){stamp(v);return BigInt(Date.parse(v))*1000n+BigInt((v.match(/\.(\d+)/)?.[1]??'').padEnd(6,'0').slice(3))}
export function attendanceChoiceDecimal(cents:string){if(!integer(cents))return fail();const n=BigInt(cents);return `${n/100n}.${String(n%100n).padStart(2,'0')}`}
export function attendanceChoiceRupiah(cents:string){const [a,b]=attendanceChoiceDecimal(cents).split('.');return `Rp${a.replace(/\B(?=(\d{3})+(?!\d))/g,'.')}${b==='00'?'':','+b}`}
export function attendanceChoicePayload(action:AttendanceChoiceAction,v:unknown):AttendanceChoicePayload {
 if(!ATTENDANCE_CHOICE_ACTIONS.includes(action))return fail()
 const r=closed(v,['period_start','period_end','choice','output_start','output_end','reason']);period(r.period_start,r.period_end)
 if(!reason(r.reason))return fail()
 if(action==='CHOOSE'||action==='CORRECT'){if(!choice(r.choice))fail()}else if(r.choice!==null)fail()
 if(action==='ALLOCATE'){period(r.output_start,r.output_end);if(String(r.output_start)<=String(r.period_end))fail()}
 else if(r.output_start!==null||r.output_end!==null)fail()
 return r as AttendanceChoicePayload
}
export function attendanceChoiceSavePayload(action:AttendanceChoiceAction,v:unknown):AttendanceChoiceSavePayload {
 const r=closed(v,['period_start','period_end','choice','output_start','output_end','reason','review_token'])
 const {review_token,...p}=r;if(!sha(review_token))fail();attendanceChoicePayload(action,p);return r as AttendanceChoiceSavePayload
}
export function attendanceChoiceReadQuery(v:unknown):AttendanceChoiceQuery {
 const q=closed(v,['period_start','period_end','offset','limit']);period(q.period_start,q.period_end)
 if(!Number.isInteger(q.offset)||Number(q.offset)<0||Number(q.offset)>100000||!Number.isInteger(q.limit)||Number(q.limit)<1||Number(q.limit)>50)fail()
 return q as AttendanceChoiceQuery
}
export function attendanceChoiceActions(w:AttendanceChoiceWorkspace):AttendanceChoiceAction[]{
 if(w.source_problem!==null||w.source_binding===null||w.amount_cents===null||w.original_period_sewing_qty===null||!positive(w.amount_cents))return []
 if(w.current_allocation)return w.closed_through&&w.current_allocation.output_end<=w.closed_through?[]:['CANCEL_ALLOCATION']
 const sourceOpen=w.closed_through===null||w.period_end>w.closed_through
 if(w.current_choice){if(w.original_period_sewing_qty!=='0')return sourceOpen?['REVERSE']:[];return [...(sourceOpen?['CORRECT','REVERSE'] as const:[]),...(w.current_choice.choice==='CARRY'?['ALLOCATE'] as const:[])]}
 return sourceOpen&&w.original_period_sewing_qty==='0'?['CHOOSE']:[]
}
function history(v:unknown):AttendanceChoiceHistory {
 if(!v||typeof v!=='object')return fail();const e=(v as Row).event
 const extra=e==='CHOOSE'?['choice','amount_cents','journal_id','correction_of']:e==='REVERSE'?['journal_id']:e==='ALLOCATE'?['allocation_id','pool_id','output_start','output_end']:e==='CANCEL_ALLOCATION'?['allocation_id','pool_id','journal_id']:fail()
 const r=closed(v,['event_id','event','decision_id','reason','recorded_at','actor',...extra]);stamp(r.recorded_at)
 if(!uuid(r.event_id)||!uuid(r.decision_id)||!uuid(r.actor)||!reason(r.reason))fail()
 if(e==='CHOOSE'){if(r.event_id!==r.decision_id||!choice(r.choice)||!positive(r.amount_cents)||!nullableUuid(r.correction_of)||r.correction_of===r.decision_id||!(r.choice==='CARRY'?r.journal_id===null:uuid(r.journal_id)))fail()}
 if(e==='REVERSE'&&!nullableUuid(r.journal_id))fail()
 if(e==='ALLOCATE'||e==='CANCEL_ALLOCATION'){if(!uuid(r.allocation_id)||!uuid(r.pool_id))fail();if(e==='ALLOCATE'){period(r.output_start,r.output_end);if(r.event_id!==r.allocation_id)fail()}else if(!uuid(r.journal_id))fail()}
 return r as AttendanceChoiceHistory
}
export function parseAttendanceChoiceWorkspace(v:unknown,q:AttendanceChoiceQuery):AttendanceChoiceWorkspace {
 attendanceChoiceReadQuery(q)
 const r=closed(v,['contract_version','period_start','period_end','amount_cents','source_binding','original_period_sewing_qty','source_problem','closed_through','current_choice','current_allocation','history','history_total','offset','limit','next_offset','can_manage','business_DML'])
 if(r.contract_version!=='cp7.attendance-period-choice-workspace.v1'||r.business_DML!==false||r.period_start!==q.period_start||r.period_end!==q.period_end||r.offset!==q.offset||r.limit!==q.limit||typeof r.can_manage!=='boolean'||!nullableDay(r.closed_through))fail()
 if(r.amount_cents!==null&&!integer(r.amount_cents)||r.source_binding!==null&&!sha(r.source_binding)||r.original_period_sewing_qty!==null&&!integer(r.original_period_sewing_qty)||r.source_problem!==null&&(!text(r.source_problem)||!r.source_problem.trim()))fail()
 if(r.source_problem===null&&(r.amount_cents===null||r.source_binding===null||r.original_period_sewing_qty===null))fail()
 if(r.current_choice!==null){const c=closed(r.current_choice,['decision_id','choice','reason','journal_id']);if(!uuid(c.decision_id)||!choice(c.choice)||!reason(c.reason)||!(c.choice==='CARRY'?c.journal_id===null:uuid(c.journal_id)))fail()}
 if(r.current_allocation!==null){const a=closed(r.current_allocation,['allocation_id','pool_id','output_start','output_end']);period(a.output_start,a.output_end);if(!r.current_choice||(r.current_choice as Row).choice!=='CARRY'||!uuid(a.allocation_id)||!uuid(a.pool_id)||String(a.output_start)<=q.period_end)fail()}
 if(!Array.isArray(r.history)||r.history.length>q.limit||!integer(r.history_total))fail()
 const entries=(r.history as unknown[]).map(history),ids=new Set(entries.map(e=>e.event_id.toLowerCase())),total=BigInt(String(r.history_total)),end=BigInt(q.offset)+BigInt(entries.length)
 if(ids.size!==entries.length||entries.length&&end>total||end<total&&(!entries.length||r.next_offset!==q.offset+entries.length)||end>=total&&r.next_offset!==null||r.current_choice&&total===0n)fail()
 for(let i=0;i<entries.length;i++){const h=entries[i],previous=entries[i-1];if(h.event==='ALLOCATE'&&h.output_start<=q.period_end)fail();if(previous&&(micros(h.recorded_at)>micros(previous.recorded_at)||micros(h.recorded_at)===micros(previous.recorded_at)&&h.event_id.toLowerCase()>previous.event_id.toLowerCase()))fail()}
 return {...r,history:entries} as AttendanceChoiceWorkspace
}
export function parseAttendanceChoicePreview(v:unknown,action:AttendanceChoiceAction,p:AttendanceChoicePayload,w:AttendanceChoiceWorkspace):AttendanceChoicePreview {
 attendanceChoicePayload(action,p)
 const r=closed(v,['contract_version','action','payload','amount','amount_cents','source_count','denominator_qty','economic_date','book_date','inverse_economic_date','inverse_book_date','decision_id','allocation_id','pool_id','source_binding','review_token','expense_account','can_apply','business_DML'])
 const payload=attendanceChoicePayload(action,r.payload)
 if(r.contract_version!=='cp7.attendance-period-choice.v1'||r.action!==action||r.can_apply!==true||r.business_DML!==false||!Object.keys(p).every(k=>p[k as keyof AttendanceChoicePayload]===payload[k as keyof AttendanceChoicePayload])||!attendanceChoiceActions(w).includes(action))fail()
 if(w.source_problem!==null||r.source_binding!==w.source_binding||r.amount_cents!==w.amount_cents||!positive(r.amount_cents)||r.amount!==attendanceChoiceDecimal(String(r.amount_cents))||!positive(r.source_count)||!sha(r.review_token)||!sha(r.source_binding))fail()
 if(r.decision_id!==(w.current_choice?.decision_id??null)||r.allocation_id!==(w.current_allocation?.allocation_id??null)||r.pool_id!==(w.current_allocation?.pool_id??null))fail()
 for(const k of ['economic_date','book_date','inverse_economic_date','inverse_book_date'])if(!nullableDay(r[k]))fail()
 const expense=(action==='CHOOSE'||action==='CORRECT')&&p.choice==='EXPENSE',allocation=action==='ALLOCATE'
 const inverse=action==='CANCEL_ALLOCATION'||(action==='CORRECT'||action==='REVERSE')&&w.current_choice?.choice==='EXPENSE'
 if(expense||allocation){if(r.economic_date!==(allocation?p.output_end:p.period_end)||!attendanceChoiceDay(r.book_date)||String(r.book_date)<String(r.economic_date)||w.closed_through!==null&&String(r.book_date)<=w.closed_through)fail()}
 else if(r.economic_date!==null||r.book_date!==null)fail()
 if(inverse){if(!attendanceChoiceDay(r.inverse_economic_date)||!attendanceChoiceDay(r.inverse_book_date)||r.inverse_book_date<r.inverse_economic_date||w.closed_through!==null&&r.inverse_book_date<=w.closed_through)fail()}else if(r.inverse_economic_date!==null||r.inverse_book_date!==null)fail()
 if(allocation?!positive(r.denominator_qty):r.denominator_qty!==null)fail()
 if(expense){const a=closed(r.expense_account,['id','code','name']);if(!uuid(a.id)||!text(a.code)||!a.code.trim()||!text(a.name)||!a.name.trim())fail()}else if(r.expense_account!==null)fail()
 return r as AttendanceChoicePreview
}
export function parseAttendanceChoiceOutcome(v:unknown,e:ProductionEnvelope):AttendanceChoiceOutcome {
 if(e.expectedVersion!==null||!uuid(e.id)||!ATTENDANCE_CHOICE_ACTIONS.includes(e.action as AttendanceChoiceAction))return fail()
 const p=attendanceChoiceSavePayload(e.action as AttendanceChoiceAction,e.payload)
 const r=closed(v,['contract_version','action','request_id','period_start','period_end','decision_id','event_id','amount_cents','pool_id','native_result','inverse_journal_id','dated_WIP','status'])
 if(r.contract_version!=='cp7.attendance-period-choice-command.v1'||r.status!=='COMMITTED'||r.action!==e.action||r.request_id!==e.id||r.period_start!==p.period_start||r.period_end!==p.period_end||!uuid(r.decision_id)||!uuid(r.event_id)||!positive(r.amount_cents)||!nullableUuid(r.pool_id)||!nullableUuid(r.inverse_journal_id))fail()
 if((e.action==='CHOOSE'||e.action==='CORRECT')&&r.decision_id!==r.event_id)fail()
 if(e.action==='ALLOCATE'||e.action==='CANCEL_ALLOCATION'){
  const active=e.action==='ALLOCATE',n=closed(r.native_result,['pool_id','status','row_version',...(active?['journal_entry_id','validation']:['reversal_journal_entry_id','residue_expected'])])
  if(!uuid(r.pool_id)||n.pool_id!==r.pool_id||n.status!==(active?'ACTIVE':'CANCELLED')||!Number.isSafeInteger(n.row_version)||Number(n.row_version)<=0||!uuid(n[active?'journal_entry_id':'reversal_journal_entry_id'])||(active?n.validation!=='PASS':n.residue_expected!==0)||r.inverse_journal_id!==null)fail()
 }else if(r.pool_id!==null||r.native_result!==null||e.action==='CHOOSE'&&r.inverse_journal_id!==null)fail()
 const proof=closed(r.dated_WIP,['all_original_debits_nonnegative_on_every_economic_and_book_cutoff','dated_available_WIP'])
 if(proof.all_original_debits_nonnegative_on_every_economic_and_book_cutoff!==true||!Array.isArray(proof.dated_available_WIP)||!proof.dated_available_WIP.length)fail()
 const seen=new Set<string>()
 for(const v of proof.dated_available_WIP as unknown[]){const x=closed(v,['line_id','axis','date','available_cents']);const key=JSON.stringify([x.line_id,x.axis,x.date]);if(!uuid(x.line_id)||!['ECONOMIC','BOOK'].includes(String(x.axis))||!attendanceChoiceDay(x.date)||!whole(x.available_cents)||seen.has(key))fail();seen.add(key)}
 return r as AttendanceChoiceOutcome
}
export function attendanceChoiceError(error:unknown):string {
 const e=error&&typeof error==='object'?error as Row:{},message=typeof e.message==='string'?e.message:''
 if(e.code==='42501'||e.status===401||e.status===403||/CP7_S03_(OWNER_REQUIRED|USER_INACTIVE|ACCESS_CHANGED)/.test(message))return 'Hak akses berubah. Pilihan biaya ini hanya dapat dikelola Owner dengan hak HPP. Muat ulang atau masuk kembali.'
 const groups:[string,string][]=[
  ['STALE_REVIEW|SOURCE_CHANGED','Sumber, pilihan, rekening, atau hak berubah. Muat ulang periode lalu periksa perubahan lagi.'],
  ['PERIOD_CLOSED','Periode terkait sudah ditutup. Buka kembali melalui Keuangan → Laporan & Tutup Buku → Tutup Buku, lalu muat ulang.'],
  ['EXPENSE_BEFORE_WIP_AVAILABLE|ALLOCATION_BEFORE_WIP_AVAILABLE|WIP_NEGATIVE_DATED','Biaya belum tersedia pada tanggal pengakuan atau tanggal buku yang diperlukan. Periksa riwayat biaya dan tanggal periode; jangan memundurkan tanggal.'],
  ['LATER_OUTPUT_NOT_AVAILABLE','Periode tujuan belum memiliki hasil jahit yang memenuhi syarat. Biaya tetap menunggu; pilih periode tujuan yang sesuai.'],
  ['OUTPUT_EXISTS','Periode asal sudah memiliki hasil jahit. Periksa pool HPP untuk periode tersebut.'],
  ['NO_ELIGIBLE_COST','Belum ada biaya absensi disetujui yang memenuhi syarat pada periode ini. Periksa payroll dan kebijakan HPP mandor.'],
  ['CANCEL_CARRY_FIRST','Batalkan alokasi biaya ke periode tujuan terlebih dahulu melalui pilihan periode ini, lalu periksa koreksi atau pembatalannya.'],
  ['CURRENT_CARRY_REQUIRED|CHOICE_EXISTS|CHOICE_NOT_FOUND|ACTIVE_CARRY_ALLOCATION_REQUIRED','Pilihan atau alokasi aktif sudah berubah. Muat ulang periode dan ikuti tindakan yang tersedia pada pilihan saat ini.'],
  ['EXPENSE_ACCOUNT_REQUIRED','Rekening beban periode belum memenuhi syarat. Periksa pengaturan rekening beban, lalu muat ulang dan periksa lagi.'],
  ['NATIVE_POOL_OWNS_PERIOD|SOURCE_OWNED_BY_NATIVE_POOL|SOURCE_ALREADY_CLAIMED','Biaya ini sudah digunakan oleh pool atau pilihan lain. Periksa pool HPP dan riwayat periode asal sebelum melanjutkan.'],
  ['PERIOD_FUTURE|SEPARATE_LATER_OUTPUT_PERIOD_REQUIRED','Periksa tanggal periode: tujuan harus sesudah periode asal dan hasilnya sudah terjadi.'],
  ['REQUEST_CHANGED','Isian berbeda dari permintaan sebelumnya. Periksa hasil permintaan lama sebelum membuat tindakan baru.'],
 ]
 for(const [codes,words]of groups)if(new RegExp('CP7_S03_('+codes+')(?::|$)').test(message))return words
 const native=hppPoolRefusalText(message);if(native)return native
 if(message&&!/CP7_|\berp\.|\bSQL\b|PL\/pgSQL|\bselect\s|\bfunction\b|\brelation\b/i.test(message)&&message.length<=400&&e.code==='P0001')return message
 const normalized=normalizeClientError(error)
 return normalized.code==='FORBIDDEN'||normalized.code==='AUTH_REQUIRED'?normalized.message:'Perubahan belum dapat dipastikan. Muat ulang periode dan periksa sumber serta riwayat biaya sebelum melanjutkan.'
}
type RpcName='erp_cp7_get_attendance_choice_v1'|'erp_cp7_preview_attendance_choice_v1'|'erp_cp7_save_attendance_choice_v1'
type RpcBoundary={rpc:(name:RpcName,args:Record<string,unknown>)=>PromiseLike<{data:unknown;error:unknown}>}
export function attendanceChoiceRpc(client:unknown){const c=client as RpcBoundary;return {
 workspace:(query:AttendanceChoiceQuery)=>{const q=attendanceChoiceReadQuery(query);return c.rpc('erp_cp7_get_attendance_choice_v1',{p_period_start:q.period_start,p_period_end:q.period_end,p_offset:q.offset,p_limit:q.limit})},
 preview:(action:AttendanceChoiceAction,p:AttendanceChoicePayload)=>c.rpc('erp_cp7_preview_attendance_choice_v1',{p_action:action,p_payload:attendanceChoicePayload(action,p)}),
 save:(e:ProductionEnvelope)=>{if(e.expectedVersion!==null||!uuid(e.id)||e.fingerprint!==JSON.stringify({action:e.action,payload:e.payload,expectedVersion:null}))return fail();return c.rpc('erp_cp7_save_attendance_choice_v1',{p_action:e.action,p_payload:attendanceChoiceSavePayload(e.action as AttendanceChoiceAction,e.payload),p_request:e.id})},
}}
