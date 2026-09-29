import {parseAttendanceContractor,parseAttendancePeriod,type AttendanceContractor,type AttendancePeriod} from './attendanceContract'
export const attendanceMarks={PRESENT:'Hadir',ABSENT:'Tidak hadir',HALF_DAY:'Setengah hari',SICK:'Sakit',LEAVE:'Izin / cuti',OFF:'Libur'} as const
export type AttendanceMark=keyof typeof attendanceMarks
export type EntryRecord={id:string;mark:AttendanceMark;paid_fraction:string;notes:string|null;lifecycle:string;supersedes_id:string|null;row_version:string}
export type EntryCell={id:string;worker_id:string;worker_name:string;worker_code:string|null;pay_scheme:string;date:string;eligible:boolean;required:boolean;daily_rate:string|null;record:EntryRecord|null}
export type AttendanceEntry={contract_version:'cp7.attendance-entry.v1';date_from:string;date_to:string;source_token:string;contractor:AttendanceContractor;period:AttendancePeriod|null;page:{rows:EntryCell[];total:string;offset:number;limit:number;next_offset:number|null}}
export type EntryMode='CREATE'|'EDIT'|'CORRECT'|'POST'|'REVERSE'
export type AttendancePreview={contract_version:'cp7.attendance-preview.v1';kind:'READ_ONLY_PREVIEW';contractor_id:string;period_id:string|null;source_token:string;line_count:string;paid_day_equivalent:string;estimated_amount:string}
export type AttendanceOutcome={contract_version:'cp7.attendance-outcome.v1';kind:'COMMITTED_OUTCOME';action:string;request_id:string;period_id:string;contractor_id:string;row_version:string;status:string;source_token:string}
const fail=():never=>{throw Error('Sumber atau hasil absensi tidak sesuai. Muat ulang sebelum melanjutkan.')}
const text=(v:unknown):v is string=>typeof v==='string'
const uuid=(v:unknown)=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,29})$/.test(v)
const version=(v:unknown)=>whole(v)&&v!=='0'
const decimal=(v:unknown,scale=6):v is string=>text(v)&&new RegExp('^(0|[1-9][0-9]{0,29})(\\.[0-9]{1,'+scale+'})?$').test(v)
const date=(v:unknown):v is string=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
const token=(v:unknown)=>text(v)&&/^[a-f0-9]{32}$/.test(v)
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(Object.keys(r).length!==keys.length||keys.some(k=>!(k in r)))return fail();return r}
export function validPaidFraction(mark:string,value:string){if(!/^(0(\.[0-9]{1,4})?|1(\.0{1,4})?)$/.test(value))return false;const [a,b='']=value.split('.'),units=BigInt(a)*10000n+BigInt(b.padEnd(4,'0'));return mark==='HALF_DAY'?units<=5000n:['ABSENT','OFF'].includes(mark)?units===0n:mark in attendanceMarks}
export function parseAttendanceEntry(value:unknown):AttendanceEntry{
 const r=closed(value,['contract_version','date_from','date_to','source_token','contractor','period','page']),p=closed(r.page,['rows','total','offset','limit','next_offset']),c=parseAttendanceContractor(r.contractor),h=r.period===null?null:parseAttendancePeriod(r.period)
 if(r.contract_version!=='cp7.attendance-entry.v1'||!date(r.date_from)||!date(r.date_to)||r.date_to<r.date_from||!token(r.source_token)||h&&(h.contractor_id!==c.id||h.period_start!==r.date_from||h.period_end!==r.date_to)||!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||p.rows.length>Number(p.limit))return fail()
 const end=BigInt(Number(p.offset))+BigInt(p.rows.length),total=BigInt(p.total)
 if(p.rows.length&&end>total||end<total&&p.next_offset===null||p.next_offset!==null&&(p.next_offset!==Number(p.offset)+p.rows.length||!p.rows.length||end>=total))fail()
 for(const row of p.rows){const x=closed(row,['id','worker_id','worker_name','worker_code','pay_scheme','date','eligible','required','daily_rate','record'])
  if(!uuid(x.worker_id)||!text(x.worker_name)||!(x.worker_code===null||text(x.worker_code))||!['DAILY','PIECE','HYBRID','NONE'].includes(String(x.pay_scheme))||!date(x.date)||String(x.date)<String(r.date_from)||String(x.date)>String(r.date_to)||x.id!==`${x.worker_id}:${x.date}`||typeof x.eligible!=='boolean'||typeof x.required!=='boolean'||x.required&&(!x.eligible||!c.attendance_required||!['DAILY','HYBRID'].includes(String(x.pay_scheme)))||!(x.daily_rate===null||decimal(x.daily_rate)))fail()
  if(x.record!==null){const z=closed(x.record,['id','mark','paid_fraction','notes','lifecycle','supersedes_id','row_version']);if(!h||!uuid(z.id)||!text(z.mark)||!text(z.paid_fraction)||!validPaidFraction(z.mark,z.paid_fraction)||!(z.notes===null||text(z.notes))||!['DRAFT','POSTED','CORRECTED','REVERSED','LEGACY_POSTED'].includes(String(z.lifecycle))||!(z.supersedes_id===null||uuid(z.supersedes_id))||!version(z.row_version))fail()}
 }
 if(new Set(p.rows.map(x=>(x as EntryCell).id)).size!==p.rows.length)fail()
 return r as AttendanceEntry
}
export function parseAttendancePreview(value:unknown,payload:unknown):AttendancePreview{
 const r=closed(value,['contract_version','kind','contractor_id','period_id','source_token','line_count','paid_day_equivalent','estimated_amount']),p=payload as {contractor_id:string;source_token:string;document:{period_id?:string;attendance:unknown[]}}
 if(r.contract_version!=='cp7.attendance-preview.v1'||r.kind!=='READ_ONLY_PREVIEW'||r.contractor_id!==p.contractor_id||r.period_id!==(p.document.period_id??null)||r.source_token!==p.source_token||!whole(r.line_count)||BigInt(r.line_count)!==BigInt(p.document.attendance.length)||!decimal(r.paid_day_equivalent,4)||!decimal(r.estimated_amount,10))fail()
 return r as AttendancePreview
}
export function parseAttendanceOutcome(value:unknown,request:string,action:string,payload:unknown):AttendanceOutcome{
 const r=closed(value,['contract_version','kind','action','request_id','period_id','contractor_id','row_version','status','source_token']),outer=closed(payload,['document','expected_version']),p=closed(outer.document,['contractor_id','date_from','date_to','source_token','document']),d=p.document as {period_id?:string}
 const status=({SAVE:'DRAFT',POST:'POSTED',REVERSE:'REVERSED'} as Record<string,string>)[action]
 if(!status||r.contract_version!=='cp7.attendance-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.request_id!==request||r.action!==action||r.status!==status||!uuid(r.period_id)||r.contractor_id!==p.contractor_id||!uuid(r.contractor_id)||!version(r.row_version)||!token(r.source_token)||!d||typeof d!=='object')fail()
 if(d.period_id?r.period_id!==d.period_id||!version(outer.expected_version)||BigInt(String(r.row_version))<=BigInt(String(outer.expected_version)):outer.expected_version!==null||action!=='SAVE')fail()
 return r as AttendanceOutcome
}
