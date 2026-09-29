import type { Json } from './types/database.preconnect'
export type RecostRow={id:string;entity_type:string;entity_id:string;po_number:string|null;status:'PENDING'|'RUNNING'|'FAILED';reason:string;recalc_from:string|null;queued_at:string;attempt_count:number;next_attempt_at:string|null;error_message:string|null;error_truncated:boolean;eligible:boolean}
export type RecostQueue={contract_version:'cp7.recost-queue.v1';captured_at:string;scope:'CURRENT_QUEUE_ALL_ENTITIES';batch_semantics:'AT_MOST_20_ELIGIBLE_UNLOCKED_NATIVE_JOBS';counts:Record<'pending'|'running'|'failed'|'done'|'eligible'|'exhausted',string>;page:{rows:RecostRow[];total:string;offset:number;limit:25;next_offset:number|null}}
export type RecostOutcome={contract_version:'cp7.recost-outcome.v1';kind:'COMMITTED_OUTCOME';action:'PROCESS_ELIGIBLE';request_id:string;limit:20;completed:number;processed_at:string;batch_semantics:RecostQueue['batch_semantics'];queue_after:RecostQueue}
const fail=():never=>{throw Error('Status hitung ulang belum lengkap. Muat ulang antrean sebelum melanjutkan.')}
const text=(v:unknown):v is string=>typeof v==='string'
const integer=(v:unknown):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,20})$/.test(v)
const uuid=(v:unknown)=>text(v)&&/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(v)
// PostgreSQL queue eligibility has microsecond precision. Date.parse alone
// collapses distinct instants within one millisecond and can reject valid rows.
function instantMicros(v:unknown):bigint|null{
 if(!text(v))return null
 const m=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,6}))?(?:Z|[+-]\d{2}:\d{2})$/.exec(v),ms=Date.parse(v)
 if(!m||!Number.isFinite(ms))return null
 return BigInt(ms)*1000n+BigInt((m[1]??'').padEnd(6,'0').slice(3))
}
const instant=(v:unknown)=>instantMicros(v)!==null
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
export function parseRecostQueue(value:unknown,offset=0):RecostQueue{
 const r=closed(value,['contract_version','captured_at','scope','batch_semantics','counts','page'])
 if(r.contract_version!=='cp7.recost-queue.v1'||!instant(r.captured_at)||r.scope!=='CURRENT_QUEUE_ALL_ENTITIES'||r.batch_semantics!=='AT_MOST_20_ELIGIBLE_UNLOCKED_NATIVE_JOBS')fail()
 const c=closed(r.counts,['pending','running','failed','done','eligible','exhausted']);if(!Object.values(c).every(whole))return fail()
 const n=(k:string)=>BigInt(c[k] as string)
 if(n('eligible')<n('pending')||n('eligible')>n('pending')+n('failed')-n('exhausted')||n('exhausted')>n('failed'))fail()
 const p=closed(r.page,['rows','total','offset','limit','next_offset']);if(!Array.isArray(p.rows)||p.rows.length>25||!whole(p.total)||p.offset!==offset||p.limit!==25)return fail()
 if(BigInt(p.total)!==n('pending')+n('running')+n('failed'))fail()
 const end=BigInt(offset+p.rows.length),total=BigInt(p.total);if(p.rows.length&&end>total||end<total&&(!p.rows.length||p.next_offset!==Number(end))||end>=total&&p.next_offset!==null)fail()
 const ids=new Set<string>();for(const value of p.rows){const row=closed(value,['id','entity_type','entity_id','po_number','status','reason','recalc_from','queued_at','attempt_count','next_attempt_at','error_message','error_truncated','eligible'])
  if(!whole(row.id)||row.id==='0'||ids.has(row.id)||!text(row.entity_type)||!uuid(row.entity_id)||row.po_number!==null&&!text(row.po_number)||!['PENDING','RUNNING','FAILED'].includes(String(row.status))||!text(row.reason)||!instant(row.queued_at)||row.recalc_from!==null&&!instant(row.recalc_from)||!integer(row.attempt_count)||row.next_attempt_at!==null&&!instant(row.next_attempt_at)||row.error_message!==null&&(!text(row.error_message)||row.error_message.length>2000)||typeof row.error_truncated!=='boolean'||row.error_truncated&&row.error_message===null||typeof row.eligible!=='boolean')return fail()
  const eligible=row.status==='PENDING'||row.status==='FAILED'&&row.attempt_count<3&&(row.next_attempt_at===null||instantMicros(row.next_attempt_at)!<=instantMicros(r.captured_at)!)
  if(row.eligible!==eligible)fail();ids.add(row.id)
 }
 return r as unknown as RecostQueue
}
export function parseRecostOutcome(value:unknown,request:string,payload:Json):RecostOutcome{
 const r=closed(value,['contract_version','kind','action','request_id','limit','completed','processed_at','batch_semantics','queue_after']),p=closed(payload,['limit','reason'])
 if(r.contract_version!=='cp7.recost-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!=='PROCESS_ELIGIBLE'||!uuid(request)||r.request_id!==request||p.limit!==20||r.limit!==20||!integer(r.completed)||r.completed>20||!instant(r.processed_at)||r.batch_semantics!=='AT_MOST_20_ELIGIBLE_UNLOCKED_NATIVE_JOBS')fail()
 parseRecostQueue(r.queue_after);return r as unknown as RecostOutcome
}
