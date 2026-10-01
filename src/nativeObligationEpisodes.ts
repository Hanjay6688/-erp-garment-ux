import {parseNativeAnalysis,type NativeAnalysis,type AnalysisFinanceAccess}from'./nativeAnalysis'
import type{NativeDemandQuery}from'./nativeDemandHistory'
import {cp6WibDateTimeInput}from'./cp6BusinessTime'
export type ObligationDomain='AR'|'MATERIAL_AP'
export type ObligationRequest={id:string;query:NativeDemandQuery;semanticHash:string;payload:{run_id:string;domain:ObligationDomain}}
export type ObligationEpisode={id:string;number:string;previous_episode_id:string|null;state:'ACTIVE'|'RESOLVED'|'ARCHIVED';freshness:'KNOWN'|'UNKNOWN';first_observed_at:string;last_observed_at:string;last_known_observed_at:string|null;closed_at:string|null;revision:string}
export type ObligationObservation={source_id:string;source_label:string;condition_state:string;freshness:'KNOWN'|'UNKNOWN';reason:string;source_revision:string;native_source_hash:string|null;business_resolved:boolean;transition:string;episode:ObligationEpisode|null}
export type NativeObligationObservation={analysis:NativeAnalysis;domain:ObligationDomain;requestId:string;status:'COMMITTED'|'NOT_COMMITTED';sourceStatus:'COMPLETE'|'INCOMPLETE'|'NOT_EVALUATED';sourceHash:string|null;observedAt:string|null;sourceTotal:string|null;rows:ObligationObservation[];result:Record<string,unknown>}
const fail=():never=>{throw Error('Catatan pemeriksaan tagihan belum lengkap atau tidak sesuai hak akses saat ini.')}
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
const uint=(v:unknown):v is string=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(v)&&BigInt(v)<=9223372036854775807n
const positive=(v:unknown)=>uint(v)&&v!=='0'
const day=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
const stamp=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&day(v.slice(0,10))&&Number(v.slice(11,13))<24&&Number(v.slice(14,16))<60&&Number(v.slice(17,19))<60&&Number.isFinite(Date.parse(v))
function closed(v:unknown,keys:string[]):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))return fail();return v as Record<string,unknown>}
const conditions=['DRAFT_ONLY','INACTIVE_DOCUMENT','UNKNOWN_BALANCE','CREDIT_REVIEW','INVOICE_PENDING','ZERO_BALANCE','MISSING_DUE_DATE','OVERDUE','DUE_TODAY','NOT_DUE_YET','SOURCE_UNKNOWN']
const reasons=['SOURCE_INCOMPLETE','MISSING_FROM_COMPLETE_SOURCE','NATIVE_BALANCE_UNKNOWN','NATIVE_ZERO_AND_REQUIRED_INVOICE_COVERAGE','NATIVE_DOCUMENT_INACTIVE','NATIVE_CONDITION_REQUIRES_REVIEW']
const transitions=['NO_EPISODE','DATA_UNKNOWN','RESOLVED','ARCHIVED','OBSERVED','OPENED','REOPENED_NEW_EPISODE']
function episode(v:unknown):ObligationEpisode|null{
 if(v===null)return null
 const e=closed(v,['id','number','previous_episode_id','state','freshness','first_observed_at','last_observed_at','last_known_observed_at','closed_at','revision'])
 if(!uuid(e.id)||!positive(e.number)||!positive(e.revision)||e.previous_episode_id!==null&&!uuid(e.previous_episode_id)||e.previous_episode_id===e.id||!['ACTIVE','RESOLVED','ARCHIVED'].includes(String(e.state))||!['KNOWN','UNKNOWN'].includes(String(e.freshness))||![e.first_observed_at,e.last_observed_at].every(stamp)||e.last_known_observed_at!==null&&!stamp(e.last_known_observed_at)||e.closed_at!==null&&!stamp(e.closed_at)||e.state==='ACTIVE'&&e.closed_at!==null||e.state!=='ACTIVE'&&e.closed_at===null||e.state==='RESOLVED'&&e.freshness!=='KNOWN'||(e.number==='1')!==(e.previous_episode_id===null))return fail()
 if(Date.parse(String(e.first_observed_at))>Date.parse(String(e.last_observed_at))||e.last_known_observed_at!==null&&(Date.parse(String(e.last_known_observed_at))>Date.parse(String(e.last_observed_at))||Date.parse(String(e.last_known_observed_at))<Date.parse(String(e.first_observed_at)))||e.closed_at!==null&&e.closed_at!==e.last_observed_at)return fail()
 return structuredClone(e)as ObligationEpisode
}
export function parseNativeObligationObservation(v:unknown,q:NativeDemandQuery,actor:string,finance:AnalysisFinanceAccess,domain:ObligationDomain,canView:boolean):NativeObligationObservation{
 if(!canView)return fail()
 const e=closed(v,['contract_version','actor_scope_id','analysis','rule_version','read_kind','result','read_at'])
 if(e.contract_version!=='cp7.native-obligation-observation.v1'||e.actor_scope_id!==actor||e.rule_version!=='cp7.native-obligation.v1'||e.read_kind!=='SAVED_OBSERVATION'||!stamp(e.read_at))return fail()
 const analysis=parseNativeAnalysis(e.analysis,q,actor,finance),r=closed(e.result,['request_id','status','domain','source_status','source_hash','as_of','source_read_at','observed_at','source_total','rows'])
 if(!uuid(r.request_id)||r.domain!==domain||!['COMMITTED','NOT_COMMITTED'].includes(String(r.status))||!['COMPLETE','INCOMPLETE','NOT_EVALUATED'].includes(String(r.source_status))||!Array.isArray(r.rows)||r.rows.length>10000)return fail()
 if(r.status==='NOT_COMMITTED'){
  if(r.source_status!=='NOT_EVALUATED'||r.rows.length||[r.source_hash,r.as_of,r.source_read_at,r.observed_at,r.source_total].some(x=>x!==null))return fail()
 }else{
  if(!stamp(r.observed_at)||r.source_status==='NOT_EVALUATED'||Date.parse(r.observed_at)>Date.parse(e.read_at))return fail()
  if(r.source_status==='COMPLETE'? !hash(r.source_hash)||!day(r.as_of)||!stamp(r.source_read_at)||cp6WibDateTimeInput(r.source_read_at).slice(0,10)!==r.as_of||Date.parse(r.source_read_at)>Date.parse(r.observed_at)||!uint(r.source_total)||BigInt(r.source_total)>5000n : [r.source_hash,r.as_of,r.source_read_at,r.source_total].some(x=>x!==null))return fail()
 }
 const ids=new Set<string>(),rows=r.rows.map(value=>{
  const o=closed(value,['source_id','source_label','condition_state','freshness','reason','source_revision','native_source_hash','business_resolved','transition','episode'])
  if(!uuid(o.source_id)||typeof o.source_label!=='string'||!o.source_label.trim()||ids.has(o.source_id)||!positive(o.source_revision)||!conditions.includes(String(o.condition_state))||!reasons.includes(String(o.reason))||!transitions.includes(String(o.transition))||!['KNOWN','UNKNOWN'].includes(String(o.freshness))||o.native_source_hash!==null&&!hash(o.native_source_hash)||o.business_resolved!==(o.condition_state==='ZERO_BALANCE')||o.freshness!==(['UNKNOWN_BALANCE','SOURCE_UNKNOWN'].includes(String(o.condition_state))?'UNKNOWN':'KNOWN')||domain==='AR'&&o.condition_state==='INVOICE_PENDING')return fail()
  ids.add(o.source_id);const ep=episode(o.episode)
  if(o.condition_state==='SOURCE_UNKNOWN'?(o.native_source_hash!==null||!ep||ep.state!=='ACTIVE'||o.transition!=='DATA_UNKNOWN'||!['SOURCE_INCOMPLETE','MISSING_FROM_COMPLETE_SOURCE'].includes(String(o.reason))):o.native_source_hash===null)return fail()
  if(r.source_status==='INCOMPLETE'&&(o.condition_state!=='SOURCE_UNKNOWN'||o.reason!=='SOURCE_INCOMPLETE')||r.source_status==='COMPLETE'&&o.reason==='SOURCE_INCOMPLETE')return fail()
  if(o.condition_state!=='SOURCE_UNKNOWN'&&o.reason!==(o.condition_state==='UNKNOWN_BALANCE'?'NATIVE_BALANCE_UNKNOWN':o.condition_state==='ZERO_BALANCE'?'NATIVE_ZERO_AND_REQUIRED_INVOICE_COVERAGE':['DRAFT_ONLY','INACTIVE_DOCUMENT'].includes(String(o.condition_state))?'NATIVE_DOCUMENT_INACTIVE':'NATIVE_CONDITION_REQUIRES_REVIEW'))return fail()
  if(o.transition==='NO_EPISODE'&&!['ZERO_BALANCE','DRAFT_ONLY','INACTIVE_DOCUMENT'].includes(String(o.condition_state))||o.transition!=='NO_EPISODE'&&!ep||ep&&o.transition!=='NO_EPISODE'&&(ep.last_observed_at!==r.observed_at||ep.freshness!==o.freshness))return fail()
  if(ep&&(o.transition==='RESOLVED'&&(ep.state!=='RESOLVED'||!o.business_resolved)||o.transition==='ARCHIVED'&&(ep.state!=='ARCHIVED'||o.business_resolved)||['OPENED','REOPENED_NEW_EPISODE','OBSERVED','DATA_UNKNOWN'].includes(String(o.transition))&&(ep.state!=='ACTIVE'||o.business_resolved)||o.transition==='OPENED'&&ep.number!=='1'||o.transition==='REOPENED_NEW_EPISODE'&&ep.previous_episode_id===null))return fail()
  return{...structuredClone(o),episode:ep}as ObligationObservation
 })
 if(r.source_status==='COMPLETE'&&rows.filter(x=>x.condition_state!=='SOURCE_UNKNOWN').length!==Number(r.source_total))return fail()
 return{analysis,domain,requestId:r.request_id,status:r.status as NativeObligationObservation['status'],sourceStatus:r.source_status as NativeObligationObservation['sourceStatus'],sourceHash:r.source_hash as string|null,observedAt:r.observed_at as string|null,sourceTotal:r.source_total as string|null,rows,result:structuredClone(r)}
}
export const obligationRequestKey=(scope:string)=>`erp.cp7.obligation-request.v1:${scope}`
function valid(v:unknown):v is ObligationRequest{try{const e=closed(v,['id','query','semanticHash','payload']),q=closed(e.query,['from_date','through_date','group_mode']),p=closed(e.payload,['run_id','domain']);return uuid(e.id)&&hash(e.semanticHash)&&uuid(p.run_id)&&['AR','MATERIAL_AP'].includes(String(p.domain))&&day(q.from_date)&&day(q.through_date)&&q.from_date<=q.through_date&&['AS_SOLD','RESTATED'].includes(String(q.group_mode))&&JSON.stringify(v).length<=16000}catch{return false}}
export function readObligationRequest(scope:string):{pending:ObligationRequest|null;error:string|null}{try{const raw=localStorage.getItem(obligationRequestKey(scope));if(raw===null)return{pending:null,error:null};const v=JSON.parse(raw);if(!valid(v))throw Error();return{pending:v,error:null}}catch{return{pending:null,error:'Permintaan pemeriksaan tagihan tersimpan belum dapat dibaca. Isinya dipertahankan.'}}}
export function persistObligationRequest(scope:string,r:ObligationRequest){if(!valid(r))return fail();const held=readObligationRequest(scope);if(held.error||held.pending&&JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Pastikan permintaan pemeriksaan tagihan tersimpan terlebih dahulu.');localStorage.setItem(obligationRequestKey(scope),JSON.stringify(r));if(JSON.stringify(readObligationRequest(scope).pending)!==JSON.stringify(r))throw Error('Permintaan pemeriksaan tagihan belum tersimpan.')}
export function clearObligationRequest(scope:string,id:string){const r=readObligationRequest(scope);if(r.error||r.pending?.id!==id)throw Error('Permintaan pemeriksaan tagihan tersimpan berubah.');localStorage.removeItem(obligationRequestKey(scope));if(localStorage.getItem(obligationRequestKey(scope))!==null)throw Error('Permintaan pemeriksaan tagihan belum dapat dibersihkan.')}

export type ObligationHistoryQuery={run_id:string;domain:ObligationDomain;source_id:string;before_episode:string|null;through_episode:string|null;limit:25}
export type ObligationHistoryRow={source_label:string;condition_state:string;reason:string;source_revision:string;native_source_hash:string;episode:ObligationEpisode}
export type NativeObligationHistory={analysis:NativeAnalysis;domain:ObligationDomain;sourceId:string;sourceLabel:string;sourceScopeHash:string;sourceScopeReadAt:string;through:string;before:string|null;total:string;rows:ObligationHistoryRow[];nextBefore:string|null;readAt:string}
export function parseNativeObligationHistory(v:unknown,q:NativeDemandQuery,actor:string,finance:AnalysisFinanceAccess,p:ObligationHistoryQuery,canView:boolean):NativeObligationHistory{
 if(!canView||!uuid(p.source_id)||p.limit!==25)return fail()
 const e=closed(v,['contract_version','actor_scope_id','analysis','read_kind','domain','source_id','source_label','source_scope_hash','source_scope_read_at','through_episode','before_episode','limit','total','rows','next_before_episode','page_complete','read_at'])
 if(e.contract_version!=='cp7.native-obligation-history.v1'||e.actor_scope_id!==actor||e.read_kind!=='SAVED_EPISODE_HISTORY'||e.domain!==p.domain||e.source_id!==p.source_id||typeof e.source_label!=='string'||!e.source_label.trim()||!hash(e.source_scope_hash)||!stamp(e.source_scope_read_at)||!stamp(e.read_at)||Date.parse(e.source_scope_read_at)>Date.parse(e.read_at)||!uint(e.through_episode)||!uint(e.total)||BigInt(e.total)>10000n||e.before_episode!==p.before_episode||p.through_episode!==null&&e.through_episode!==p.through_episode||e.limit!==25||e.page_complete!==true||!Array.isArray(e.rows)||e.rows.length>25||e.rows.length>Number(e.total)||e.next_before_episode!==null&&!positive(e.next_before_episode))return fail()
 const analysis=parseNativeAnalysis(e.analysis,q,actor,finance)
 if(analysis.runId!==p.run_id||(p.before_episode===null)!==(p.through_episode===null)||p.before_episode!==null&&!positive(p.before_episode)||p.through_episode!==null&&!positive(p.through_episode))return fail()
 if(e.total==='0'?(e.rows.length!==0||e.next_before_episode!==null||e.through_episode!=='0'):e.rows.length===0)return fail()
 if(p.before_episode===null&&e.rows.length!==Math.min(25,Number(e.total)))return fail()
 if(p.before_episode!==null&&BigInt(p.before_episode)>BigInt(String(e.through_episode))+1n)return fail()
 const ids=new Set<string>();let previousNumber:bigint|null=null
 const rows=e.rows.map(value=>{
  const o=closed(value,['source_label','condition_state','reason','source_revision','native_source_hash','episode']),ep=episode(o.episode)
  if(!ep||ids.has(ep.id)||typeof o.source_label!=='string'||!o.source_label.trim()||!conditions.includes(String(o.condition_state))||!reasons.includes(String(o.reason))||!positive(o.source_revision)||!hash(o.native_source_hash)||Date.parse(ep.last_observed_at)>Date.parse(e.read_at)||BigInt(ep.number)>BigInt(String(e.through_episode))||p.before_episode!==null&&BigInt(ep.number)>=BigInt(p.before_episode)||previousNumber!==null&&BigInt(ep.number)>=previousNumber)return fail()
  if(ep.state==='RESOLVED'&&(o.condition_state!=='ZERO_BALANCE'||o.reason!=='NATIVE_ZERO_AND_REQUIRED_INVOICE_COVERAGE')||ep.state==='ARCHIVED'&&(!['DRAFT_ONLY','INACTIVE_DOCUMENT'].includes(String(o.condition_state))||o.reason!=='NATIVE_DOCUMENT_INACTIVE')||ep.state==='ACTIVE'&&['DRAFT_ONLY','INACTIVE_DOCUMENT','ZERO_BALANCE'].includes(String(o.condition_state))||p.domain==='AR'&&o.condition_state==='INVOICE_PENDING')return fail()
  // Native keeps the last known condition when an observation becomes
  // incomplete. Its UNKNOWN freshness/reason must remain visible as saved.
  if(ep.freshness==='UNKNOWN'){
   if(ep.state!=='ACTIVE'||(o.reason==='NATIVE_BALANCE_UNKNOWN'?o.condition_state!=='UNKNOWN_BALANCE':!['SOURCE_INCOMPLETE','MISSING_FROM_COMPLETE_SOURCE'].includes(String(o.reason))))return fail()
  }else if(['UNKNOWN_BALANCE','SOURCE_UNKNOWN'].includes(String(o.condition_state))||o.reason!==(o.condition_state==='ZERO_BALANCE'?'NATIVE_ZERO_AND_REQUIRED_INVOICE_COVERAGE':['DRAFT_ONLY','INACTIVE_DOCUMENT'].includes(String(o.condition_state))?'NATIVE_DOCUMENT_INACTIVE':'NATIVE_CONDITION_REQUIRES_REVIEW'))return fail()
  ids.add(ep.id);previousNumber=BigInt(ep.number);return{...structuredClone(o),episode:ep}as ObligationHistoryRow
 })
 if(e.next_before_episode!==null&&(e.next_before_episode!==rows.at(-1)?.episode.number||rows.length!==25)||p.before_episode===null&&(BigInt(String(e.total))>BigInt(rows.length))!==(e.next_before_episode!==null))return fail()
 return{analysis,domain:p.domain,sourceId:p.source_id,sourceLabel:e.source_label,sourceScopeHash:e.source_scope_hash as string,sourceScopeReadAt:e.source_scope_read_at,through:e.through_episode as string,before:p.before_episode,total:e.total,rows,nextBefore:e.next_before_episode as string|null,readAt:e.read_at}
}
