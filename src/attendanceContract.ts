import type {MaterialPage} from './materialContract'
export type AttendanceSection='CONTRACTORS'|'WORKERS'|'RATES'|'EMPLOYMENT'|'PERIODS'|'RECORDS'
export type AttendanceContractor={id:string;name:string;active_now:boolean;attendance_required:boolean}
export type AttendanceWorker={id:string;contractor_id:string;code:string|null;name:string;job_description:string|null;pay_scheme:string;active_now:boolean;joined_at:string|null;left_at:string|null;notes:string|null;row_version:string;rate_at:string;daily_rate_at_date:string|null;employed_at_date:boolean}
export type AttendancePeriod={id:string;contractor_id:string;number:string;period_start:string;period_end:string;pay_date:string;status:string;correction_of_id:string|null;notes:string|null;row_version:string;record_count:string;consuming_payroll_count:string}
export type AttendanceRate={id:string;worker_id:string;daily_rate:string;date_from:string;date_to:string|null;reason:string}
export type AttendanceEmployment={id:string;worker_id:string;date_from:string;date_to:string|null;start_reason:string;end_reason:string|null}
export type AttendanceRecord={id:string;period_id:string;worker_id:string;worker_name:string;date:string;mark:string;paid_fraction:string;lifecycle:string;supersedes_id:string|null;notes:string|null;row_version:string}
export type AttendanceRow=AttendanceContractor|AttendanceWorker|AttendancePeriod|AttendanceRate|AttendanceEmployment|AttendanceRecord
export type AttendanceRead={contract_version:'cp7.attendance-workspace.v1';section:AttendanceSection;date_from:string|null;date_to:string|null;source_token:string|null;contractor:AttendanceContractor|null;worker:AttendanceWorker|null;period:AttendancePeriod|null;page:MaterialPage<AttendanceRow>}
const fail=():never=>{throw Error('Sumber absensi belum lengkap atau berubah. Muat ulang absensi.')}
const text=(v:unknown):v is string=>typeof v==='string'
const uuid=(v:unknown)=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,29})$/.test(v)
const version=(v:unknown)=>whole(v)&&v!=='0'
const nullable=(test:(v:unknown)=>boolean,v:unknown)=>v===null||test(v)
const decimal=(v:unknown,scale=6):v is string=>text(v)&&new RegExp('^(0|[1-9][0-9]{0,25})(\\.[0-9]{1,'+scale+'})?$').test(v)
const date=(v:unknown):v is string=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(Object.keys(r).length!==keys.length||keys.some(k=>!(k in r)))fail();return r}
function contractor(v:unknown):AttendanceContractor{const r=closed(v,['id','name','active_now','attendance_required']);if(!uuid(r.id)||!text(r.name)||typeof r.active_now!=='boolean'||typeof r.attendance_required!=='boolean')fail();return r as AttendanceContractor}
function worker(v:unknown):AttendanceWorker{
 const r=closed(v,['id','contractor_id','code','name','job_description','pay_scheme','active_now','joined_at','left_at','notes','row_version','rate_at','daily_rate_at_date','employed_at_date'])
 if(!uuid(r.id)||!uuid(r.contractor_id)||!nullable(text,r.code)||!text(r.name)||!nullable(text,r.job_description)||!['DAILY','PIECE','HYBRID','NONE'].includes(String(r.pay_scheme))||typeof r.active_now!=='boolean'||typeof r.employed_at_date!=='boolean'||!nullable(date,r.joined_at)||!nullable(date,r.left_at)||!nullable(text,r.notes)||!version(r.row_version)||!date(r.rate_at)||!nullable(v=>decimal(v),r.daily_rate_at_date))fail()
 return r as AttendanceWorker
}
function period(v:unknown):AttendancePeriod{
 const r=closed(v,['id','contractor_id','number','period_start','period_end','pay_date','status','correction_of_id','notes','row_version','record_count','consuming_payroll_count'])
 if(!uuid(r.id)||!uuid(r.contractor_id)||!text(r.number)||!date(r.period_start)||!date(r.period_end)||r.period_end<r.period_start||!date(r.pay_date)||!['DRAFT','POSTED','CORRECTED','REVERSED'].includes(String(r.status))||!nullable(uuid,r.correction_of_id)||!nullable(text,r.notes)||!version(r.row_version)||!whole(r.record_count)||!whole(r.consuming_payroll_count))fail()
 return r as AttendancePeriod
}
export function parseAttendanceRead(v:unknown,section:AttendanceSection):AttendanceRead{
 const r=closed(v,['contract_version','section','date_from','date_to','source_token','contractor','worker','period','page']),p=closed(r.page,['rows','total','offset','limit','next_offset'])
 if(r.contract_version!=='cp7.attendance-workspace.v1'||r.section!==section||!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||p.rows.length>Number(p.limit))return fail()
 const end=BigInt(Number(p.offset))+BigInt(p.rows.length),total=BigInt(p.total)
 if(p.rows.length&&end>total||end<total&&p.next_offset===null||p.next_offset!==null&&(p.next_offset!==Number(p.offset)+p.rows.length||!p.rows.length||end>=total))fail()
 if(section==='CONTRACTORS'){
  if([r.date_from,r.date_to,r.source_token,r.contractor,r.worker,r.period].some(x=>x!==null))fail();p.rows.forEach(contractor)
 }else{
  const c=contractor(r.contractor)
  if(!date(r.date_from)||!date(r.date_to)||r.date_to<r.date_from||!text(r.source_token)||!/^[a-f0-9]{32}$/.test(r.source_token))fail()
  const w=r.worker===null?null:worker(r.worker),h=r.period===null?null:period(r.period)
  if(w&&(w.contractor_id!==c.id||w.rate_at!==r.date_from)||h&&(h.contractor_id!==c.id||h.period_start!==r.date_from||h.period_end!==r.date_to))fail()
  if(section==='WORKERS'||section==='PERIODS'){
   if(w||h)fail()
   for(const item of p.rows){const row=section==='WORKERS'?worker(item):period(item);if(row.contractor_id!==c.id||section==='WORKERS'&&(row as AttendanceWorker).rate_at!==r.date_from)fail()}
  }else if(section==='RATES'||section==='EMPLOYMENT'){
   if(!w||h)fail()
   for(const item of p.rows){
    const row=closed(item,section==='RATES'?['id','worker_id','daily_rate','date_from','date_to','reason']:['id','worker_id','date_from','date_to','start_reason','end_reason'])
    if(!uuid(row.id)||row.worker_id!==w?.id||!date(row.date_from)||!nullable(date,row.date_to)||row.date_to!==null&&String(row.date_to)<String(row.date_from)||String(row.date_from)>String(r.date_to)||row.date_to!==null&&String(row.date_to)<String(r.date_from))fail()
    if(section==='RATES'?(!decimal(row.daily_rate)||!text(row.reason)):(!text(row.start_reason)||!nullable(text,row.end_reason)))fail()
   }
  }else{
   if(w||!h||h.record_count!==p.total)fail()
   for(const item of p.rows){
    const row=closed(item,['id','period_id','worker_id','worker_name','date','mark','paid_fraction','lifecycle','supersedes_id','notes','row_version'])
    if(!uuid(row.id)||!uuid(row.worker_id)||row.period_id!==h?.id||!text(row.worker_name)||!date(row.date)||String(row.date)<String(r.date_from)||String(row.date)>String(r.date_to)||!['PRESENT','ABSENT','HALF_DAY','SICK','LEAVE','OFF'].includes(String(row.mark))||!decimal(row.paid_fraction,4)||!['DRAFT','POSTED','CORRECTED','REVERSED','LEGACY_POSTED'].includes(String(row.lifecycle))||!nullable(uuid,row.supersedes_id)||!nullable(text,row.notes)||!version(row.row_version))fail()
    const [a,b='']=String(row.paid_fraction).split('.'),units=BigInt(a)*10000n+BigInt(b.padEnd(4,'0'));if(units>10000n||row.mark==='HALF_DAY'&&units>5000n)fail()
   }
  }
 }
 if(new Set(p.rows.map(x=>(x as AttendanceRow).id)).size!==p.rows.length)fail()
 return r as unknown as AttendanceRead
}
