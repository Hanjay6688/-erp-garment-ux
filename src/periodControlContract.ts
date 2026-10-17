import { financeDate, parseFinancePreflight, type FinanceReport } from './financeReportContract'
import type { Json } from './types/database.preconnect'
export type PeriodControl = {
 contract_version:'cp7.period-control.v1';captured_at:string;through:string;review_token:string
 control:{closed_through:string|null;version_token:string}
 preflight:NonNullable<FinanceReport['close_preflight']>
 current_filing:null|{id:string;closed_through:string;filed_at:string}
 // Owner D16-5: the merged page keeps the history of close and reopen (Native audit log of the control row), newest first.
 history:{at:string;action:'CLOSE'|'REOPEN';from:string|null;to:string|null;by:string|null;reason:string|null}[]
}
const fail=():never=>{throw Error('Pemeriksaan periode berubah atau belum lengkap. Periksa ulang sebelum melanjutkan.')}
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{32}$/.test(v)
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(v)
const instant=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T/.test(v)&&Number.isFinite(Date.parse(v))
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
export function parsePeriodControl(value:unknown,through:string):PeriodControl{
 const r=closed(value,['contract_version','captured_at','through','review_token','control','preflight','current_filing','history'])
 if(r.contract_version!=='cp7.period-control.v1'||!instant(r.captured_at)||!financeDate(through)||r.through!==through||!hash(r.review_token))fail()
 const c=closed(r.control,['closed_through','version_token']);if(c.closed_through!==null&&!financeDate(c.closed_through)||!hash(c.version_token))fail()
 const p=parseFinancePreflight(r.preflight,through);if(p.closed_through!==c.closed_through)fail()
 if(r.current_filing!==null){const f=closed(r.current_filing,['id','closed_through','filed_at']);if(!uuid(f.id)||!financeDate(f.closed_through)||f.closed_through!==c.closed_through||!instant(f.filed_at))fail()}
 if(!Array.isArray(r.history)||r.history.length>50)fail()
 let previous=Infinity
 for(const item of r.history as unknown[]){
  const h=closed(item,['at','action','from','to','by','reason']),day=(v:unknown)=>v===null||financeDate(v)
  if(!instant(h.at)||Date.parse(h.at as string)>previous||!day(h.from)||!day(h.to)||h.by!==null&&typeof h.by!=='string'||h.reason!==null&&typeof h.reason!=='string')fail()
  // CLOSE moves the closed-through date later; REOPEN moves it earlier or clears it.
  const later=h.to!==null&&(h.from===null||(h.to as string)>(h.from as string))
  if(h.action!==(later?'CLOSE':'REOPEN'))fail()
  previous=Date.parse(h.at as string)
 }
 return r as unknown as PeriodControl
}
export function parsePeriodOutcome(value:unknown,request:string,action:string,payload:Json){
 const r=closed(value,['contract_version','kind','action','request_id','closed_through','version_token','filing_id']),p=closed(payload,['through','review_through','review_token','reason'])
 if(!['CLOSE','REOPEN'].includes(action)||r.contract_version!=='cp7.period-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!==action||r.request_id!==request||r.closed_through!==p.through||r.closed_through!==null&&!financeDate(r.closed_through)||!hash(r.version_token)||action==='CLOSE'&&(!uuid(r.filing_id)||r.closed_through===null)||action==='REOPEN'&&r.filing_id!==null)fail()
 return r as {action:string;closed_through:string|null;version_token:string;filing_id:string|null}
}
