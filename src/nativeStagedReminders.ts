import {stagedInstant} from './nativeAnalysisPages'
import {reminderRuleIds,reminderRuleLabels,parseReminderPolicyConfig,type ReminderRule,type ReminderPolicyConfig} from './nativeReminderPolicy'

// Reminders v2 (snapshot contract v2 §5, owner decision 8 Oct 2026): the
// production, fabric and accessory conditions of ONE staged run of the actor,
// built once by the server one page per request and never changed; each is
// the state at the snapshot time ("data analisis per <time>"). Before a local
// preview is claimed, and again when it is finished, the server checks the
// condition again with the ERP as it is now; a condition resolved since the
// analysis is recorded and not billed. Receivables and payables are always
// read now. Nothing is sent outside the ERP: the preview is a local record.
export type SnapshotState='ACTIVE'|'DATA_REVIEW'|'NO_CURRENT_GAP'|'RESOLVED'
export type Verdict='STILL_OPEN'|'RESOLVED_NOW'|'BELOW_THRESHOLD_NOW'|'UNKNOWN_NOW'|'CHANGED_REVIEW_REQUIRED'|'NO_LONGER_DUE'|'NOT_FOUND_NOW'|'CONDITION_CHANGED'
export type ConditionSet={runId:string;identityHash:string;dataAsOf:string;state:'RUNNING'|'DONE'|'FAILED';stage:'PAGE'|'SEAL'|null;unitsDone:number;unitCount:number;unitAttempts:number
 pagesDone:number;pageCount:number;targetsTotal:number;totals:{conditions:number;byRule:Record<string,Record<string,number>>}|null;setHash:string|null;lastProgressAt:string
 failure:{unit:number;sqlstate:string;code:string}|null;workerActive:boolean}
export type PolicyBinding={basis:'MISSING'|'GLOBAL'|'EXACT_TARGET';policyId:string|null;config:ReminderPolicyConfig|null}
export type ReminderCondition={key:string;ruleId:ReminderRule;kind:'SNAPSHOT'|'LIVE';state:string;reason:string;label:string|null;targetKey:string|null;materialKey:string|null
 value:{state:string;value:string|null;unit:string};conditionHash:string;dataAsOf:string|null;eligibility:string;binding:PolicyBinding
 remaining:string|null;dueDate:string|null}
export type ConditionsPage={runId:string;dataAsOf:string;total:number;rows:ReminderCondition[];readAt:string}
export type ConditionsQuery={run_id:string;rule_id:ReminderRule|null;state:SnapshotState|null;offset:number;limit:number}
export type Recheck={id:string|null;conditionKey:string;ruleId:ReminderRule;kind:'SNAPSHOT'|'LIVE';phase:'CLAIM'|'FINISH'|null;dataAsOf:string|null;checkedAt:string
 verdict:Verdict;reason:string;numbers:Record<string,unknown>}
export type ClaimStatus='CLAIMED'|'LOCAL_SINK_CAPTURED'|'SUPPRESSED'|'UNKNOWN'
export type ReminderClaim={id:string;runId:string;identityHash:string;status:ClaimStatus;conditionKey:string;ruleId:ReminderRule;kind:'SNAPSHOT'|'LIVE';fence:string
 body:string;bodySha256:string;reason:string|null;createdAt:string;finishedAt:string|null;resolution:{outcome:'CAPTURE_CONFIRMED'|'NOT_CAPTURED_CONFIRMED';reason:string}|null}
export type Binding={id:string;revision:string;enabled:boolean;label:string;rules:ReminderRule[];reason:string}
export type PolicyRow={policyId:string;ruleId:ReminderRule;scopeKind:'GLOBAL'|'TARGET';scopeKey:string;revision:string;config:ReminderPolicyConfig;reason:string}
export type ReminderWorkspace={runId:string;identityHash:string;dataAsOf:string;conditions:ConditionSet|null;policies:PolicyRow[];allowedRules:ReminderRule[];manageAllowed:boolean
 binding:Binding|null;claims:ReminderClaim[];rechecks:Recheck[];readAt:string}
export type Operation='BINDING'|'POLICY'|'CLAIM'|'OUTCOME'|'RESOLUTION'
export type ReminderRequest={id:string;operation:Operation;runId:string;payload:Record<string,unknown>}
export type CommandResult={operation:Operation;status:'COMMITTED'|'NOT_COMMITTED';outcome:'CLAIMED'|'NOT_SENT'|null;verdict:Verdict|null;claimId:string|null
 localStatus:ClaimStatus|null;claim:ReminderClaim|null;recheck:Recheck|null;bindingId:string|null;policyId:string|null}

function fail():never{throw Error('Pengingat dari analisis bertahap belum sesuai kontrak CP7.')}
const obj=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const exact=(v:Record<string,unknown>,keys:readonly string[])=>{if(Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))fail()}
const has=(v:Record<string,unknown>,keys:readonly string[])=>{if(keys.some(k=>!Object.hasOwn(v,k)))fail()}
const guid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)
const uuid=(v:unknown):string=>guid(v)?v:fail()
const hex=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const count=(v:unknown,min:number,max:number)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min&&v<=max?v:fail()
const str=(v:unknown,max=2000)=>typeof v==='string'&&v.length<=max?v:fail()
const nstr=(v:unknown,max=2000)=>v===null?null:str(v,max)
const rule=(v:unknown):ReminderRule=>reminderRuleIds.includes(v as ReminderRule)?v as ReminderRule:fail()
const instant=(v:unknown)=>stagedInstant(v)
const ninstant=(v:unknown)=>v===null?null:stagedInstant(v)
const VERDICTS:readonly Verdict[]=['STILL_OPEN','RESOLVED_NOW','BELOW_THRESHOLD_NOW','UNKNOWN_NOW','CHANGED_REVIEW_REQUIRED','NO_LONGER_DUE','NOT_FOUND_NOW','CONDITION_CHANGED']
const verdict=(v:unknown):Verdict=>VERDICTS.includes(v as Verdict)?v as Verdict:fail()
// The snapshot is never presented as current data.
const notCurrent=(s:string)=>/terkini/i.test(s)?fail():s

const SET=['contract_version','run_id','identity_hash','data_as_of','state','stage','units_done','unit_count','unit_attempts','pages_done','page_count','targets_total',
 'totals','set_hash','last_progress_at','failure','worker_active','sent']
export function parseConditionSet(v:unknown,runId:string,identityHash:string):ConditionSet{
 const s=obj(v);exact(s,SET)
 if(s.contract_version!=='cp7.reminder-condition-set.v2'||s.sent!==false||uuid(s.run_id)!==runId||hex(s.identity_hash)!==identityHash||typeof s.worker_active!=='boolean')fail()
 const state=s.state==='RUNNING'||s.state==='DONE'||s.state==='FAILED'?s.state:fail()
 const pageCount=count(s.page_count,0,1000000),unitCount=count(s.unit_count,1,1000001),unitsDone=count(s.units_done,0,unitCount)
 if(unitCount!==pageCount+1||count(s.pages_done,0,pageCount)!==Math.min(unitsDone,pageCount))fail()
 const stage=state==='RUNNING'?(unitsDone<pageCount?'PAGE':'SEAL'):null;if(s.stage!==stage)fail()
 let totals:ConditionSet['totals']=null
 if(state==='DONE'){if(unitsDone!==unitCount)fail();const t=obj(s.totals);exact(t,['conditions','by_rule']);const br=obj(t.by_rule)
  const byRule:Record<string,Record<string,number>>={};let sum=0
  for(const[k,x]of Object.entries(br)){rule(k);const m=obj(x);byRule[k]={};for(const[st,n]of Object.entries(m)){if(!['ACTIVE','DATA_REVIEW','NO_CURRENT_GAP','RESOLVED'].includes(st))fail();byRule[k][st]=count(n,1,10000000);sum+=byRule[k][st]}}
  if(count(t.conditions,0,10000000)!==sum)fail();totals={conditions:sum,byRule};hex(s.set_hash)}
 else if(s.totals!==null||s.set_hash!==null)fail()
 let failure:ConditionSet['failure']=null
 if(state==='FAILED'){const f=obj(s.failure);exact(f,['unit','sqlstate','code']);if(typeof f.sqlstate!=='string'||!/^[0-9A-Z]{5}$/.test(f.sqlstate)||typeof f.code!=='string'||!/^CP7_[A-Z0-9_]+$/.test(f.code))fail()
  failure={unit:count(f.unit,0,unitCount),sqlstate:f.sqlstate,code:f.code}}else if(s.failure!==null)fail()
 return{runId,identityHash,dataAsOf:instant(s.data_as_of),state,stage,unitsDone,unitCount,unitAttempts:count(s.unit_attempts,0,1000),pagesDone:Math.min(unitsDone,pageCount),pageCount,
  targetsTotal:count(s.targets_total,0,1000000),totals,setHash:state==='DONE'?s.set_hash as string:null,lastProgressAt:instant(s.last_progress_at),failure,workerActive:s.worker_active}
}
function binding(v:unknown,r:ReminderRule):PolicyBinding{
 const b=obj(v);has(b,['basis','policy']);if(!['MISSING','GLOBAL','EXACT_TARGET'].includes(b.basis as string))fail()
 if(b.basis==='MISSING'){if(b.policy!==null)fail();return{basis:'MISSING',policyId:null,config:null}}
 const p=obj(b.policy);return{basis:b.basis as PolicyBinding['basis'],policyId:uuid(p.policy_id),config:parseReminderPolicyConfig(p.config,r)}
}
function fact(v:unknown){const f=obj(v);if(typeof f.state!=='string'||typeof f.unit!=='string')fail();const value=f.value===undefined?null:typeof f.value==='string'&&/^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/.test(f.value)?f.value:fail();return{state:f.state,value,unit:f.unit}}
// One condition row: a snapshot row (with its snapshot time) or a live
// receivable/payable row (read now).
export function parseCondition(v:unknown,kind:'SNAPSHOT'|'LIVE',dataAsOf:string|null):ReminderCondition{
 const r=obj(v);has(r,['key','rule_id','state','reason','label','target_key','material_key','value','condition_hash','eligibility','policy_binding','kind','delivery_sent'])
 if(r.kind!==kind||r.delivery_sent!==false)fail()
 const ruleId=rule(r.rule_id),key=str(r.key,400)
 if(!key.startsWith(ruleId+':'))fail()
 if(kind==='SNAPSHOT'&&(!['PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED'].includes(ruleId)||!['ACTIVE','DATA_REVIEW','NO_CURRENT_GAP','RESOLVED'].includes(r.state as string)||instant(r.data_as_of)!==dataAsOf))fail()
 if(kind==='LIVE'&&!['AR_DUE','AP_DUE'].includes(ruleId))fail()
 const fs=r.financial_source===undefined||r.financial_source===null?null:obj(r.financial_source)
 const rem=fs?obj(fs.remaining):null
 return{key,ruleId,kind,state:str(r.state,40),reason:str(r.reason,200),label:r.label===null?null:notCurrent(str(r.label,400)),targetKey:nstr(r.target_key,80),materialKey:nstr(r.material_key,200),
  value:fact(r.value),conditionHash:hex(r.condition_hash),dataAsOf:kind==='SNAPSHOT'?dataAsOf:null,eligibility:str(r.eligibility,60),binding:binding(r.policy_binding,ruleId),
  remaining:rem&&typeof rem.value==='string'?rem.value:null,dueDate:fs&&typeof fs.recorded_due_date==='string'?fs.recorded_due_date:null}
}
// The server echoes the query as jsonb, whose keys come back in jsonb's own
// order: the echo is compared key by key, never as text.
const QUERY_KEYS=['run_id','rule_id','state','offset','limit'] as const
const sameQuery=(v:unknown,q:ConditionsQuery)=>{const x=obj(v);exact(x,QUERY_KEYS);return QUERY_KEYS.every(k=>x[k]===q[k])}
export function parseConditionsPage(v:unknown,q:ConditionsQuery,actor:string,identityHash:string):ConditionsPage{
 const p=obj(v);exact(p,['contract_version','actor_scope_id','run_id','identity_hash','data_as_of','set','query','total','rows','read_at','eligibility_basis','recheck_required_before_preview','external_delivery_enabled','sent'])
 if(p.contract_version!=='cp7.reminder-conditions.v2'||p.actor_scope_id!==actor||p.run_id!==q.run_id||p.identity_hash!==identityHash||p.eligibility_basis!=='SNAPSHOT_VALUE_POLICY_AT_READ'
  ||p.recheck_required_before_preview!==true||p.external_delivery_enabled!==false||p.sent!==false||!sameQuery(p.query,q)||!Array.isArray(p.rows)||p.rows.length>q.limit)fail()
 const dataAsOf=instant(p.data_as_of),total=count(p.total,0,10000000)
 const rows=(p.rows as unknown[]).map(x=>parseCondition(x,'SNAPSHOT',dataAsOf))
 if(rows.some(r=>q.rule_id!==null&&r.ruleId!==q.rule_id||q.state!==null&&r.state!==q.state)||new Set(rows.map(r=>r.key)).size!==rows.length||q.offset+rows.length>total)fail()
 return{runId:q.run_id,dataAsOf,total,rows,readAt:instant(p.read_at)}
}
export function parseObligations(v:unknown,runId:string,actor:string):{rows:ReminderCondition[];readAt:string;coverage:Record<string,string>}{
 const p=obj(v);exact(p,['contract_version','actor_scope_id','run_id','rows','coverage','total','read_at','basis','external_delivery_enabled','sent'])
 if(p.contract_version!=='cp7.reminder-obligations.v2'||p.actor_scope_id!==actor||p.run_id!==runId||p.basis!=='READ_NOW_NOT_FROM_SNAPSHOT'||p.external_delivery_enabled!==false||p.sent!==false||!Array.isArray(p.rows))fail()
 const rows=(p.rows as unknown[]).map(x=>parseCondition(x,'LIVE',null));if(count(p.total,0,15000)!==rows.length||new Set(rows.map(r=>r.key)).size!==rows.length)fail()
 const coverage:Record<string,string>={};for(const[k,x]of Object.entries(obj(p.coverage)))coverage[k]=str(x,200)
 return{rows,readAt:instant(p.read_at),coverage}
}
function recheck(v:unknown):Recheck{
 const r=obj(v);has(r,['condition_key','rule_id','kind','data_as_of','checked_at','verdict','reason','numbers'])
 const kind=r.kind==='SNAPSHOT'||r.kind==='LIVE'?r.kind:fail()
 if((kind==='SNAPSHOT')!==(r.data_as_of!==null))fail()
 return{id:r.id===undefined?null:uuid(r.id),conditionKey:str(r.condition_key,400),ruleId:rule(r.rule_id),kind,phase:r.phase===undefined?null:r.phase==='CLAIM'||r.phase==='FINISH'?r.phase:fail(),
  dataAsOf:ninstant(r.data_as_of),checkedAt:instant(r.checked_at),verdict:verdict(r.verdict),reason:str(r.reason,200),numbers:obj(r.numbers)}
}
export function parseRecheck(v:unknown,runId:string,actor:string,key:string):Recheck{
 const r=obj(v);if(r.contract_version!=='cp7.reminder-recheck.v2'||r.actor_scope_id!==actor||r.run_id!==runId||r.recorded!==false||r.sent!==false||r.external_delivery_enabled!==false||r.condition_key!==key)fail()
 return recheck(r)
}
function claim(v:unknown):ReminderClaim{
 const c=obj(v);exact(c,['id','run_id','identity_hash','status','occurrence_key','binding_id','environment','condition_key','rule_id','kind','condition_hash','episode_id','policy_id',
  'recheck_id','finish_recheck_id','body_sha256','body','fence','created_at','finished_at','reason','resolution'])
 if(c.environment!=='LOCAL_TEST_SINK'||!['CLAIMED','LOCAL_SINK_CAPTURED','SUPPRESSED','UNKNOWN'].includes(c.status as string))fail()
 const body=notCurrent(str(c.body,4000));if(!body.startsWith('PRATINJAU LOKAL — BELUM DIKIRIM\n'))fail()
 const res=c.resolution===null?null:obj(c.resolution)
 return{id:uuid(c.id),runId:uuid(c.run_id),identityHash:hex(c.identity_hash),status:c.status as ClaimStatus,conditionKey:str(c.condition_key,400),ruleId:rule(c.rule_id),
  kind:c.kind==='SNAPSHOT'||c.kind==='LIVE'?c.kind:fail(),fence:uuid(c.fence),body,bodySha256:hex(c.body_sha256),reason:nstr(c.reason,200),createdAt:instant(c.created_at),
  finishedAt:ninstant(c.finished_at),resolution:res?{outcome:res.outcome==='CAPTURE_CONFIRMED'||res.outcome==='NOT_CAPTURED_CONFIRMED'?res.outcome:fail(),reason:str(res.reason,1000)}:null}
}
function policyRow(v:unknown):PolicyRow{
 const p=obj(v);has(p,['policy_id','rule_id','scope_kind','scope_key','revision','config','reason'])
 const ruleId=rule(p.rule_id);if(p.scope_kind!=='GLOBAL'&&p.scope_kind!=='TARGET')fail()
 return{policyId:uuid(p.policy_id),ruleId,scopeKind:p.scope_kind,scopeKey:str(p.scope_key,80),revision:typeof p.revision==='string'&&/^[1-9][0-9]{0,18}$/.test(p.revision)?p.revision:fail(),
  config:parseReminderPolicyConfig(p.config,ruleId),reason:str(p.reason,1000)}
}
export function parseWorkspace(v:unknown,runId:string,identityHash:string,actor:string):ReminderWorkspace{
 const w=obj(v);exact(w,['contract_version','actor_scope_id','run_id','identity_hash','data_as_of','conditions','policies','allowed_rules','manage_allowed','missing_policy','binding',
  'claims','rechecks','read_at','external_delivery_enabled','scheduler_enabled','sent'])
 if(w.contract_version!=='cp7.reminder-workspace.v2'||w.actor_scope_id!==actor||w.run_id!==runId||w.identity_hash!==identityHash||typeof w.manage_allowed!=='boolean'
  ||w.missing_policy!=='UNCONFIGURED_NOT_ZERO_NOT_DISABLED'||w.external_delivery_enabled!==false||w.scheduler_enabled!==false||w.sent!==false
  ||!Array.isArray(w.policies)||!Array.isArray(w.allowed_rules)||!Array.isArray(w.claims)||!Array.isArray(w.rechecks)||w.claims.length>200||w.rechecks.length>200)fail()
 if(!w.manage_allowed&&(w.binding!==null||w.claims.length||w.rechecks.length))fail()
 const b=w.binding===null?null:obj(w.binding)
 return{runId,identityHash,dataAsOf:instant(w.data_as_of),conditions:w.conditions===null?null:parseConditionSet(w.conditions,runId,identityHash),
  policies:(w.policies as unknown[]).map(policyRow),allowedRules:(w.allowed_rules as unknown[]).map(rule),manageAllowed:w.manage_allowed,
  binding:b?{id:uuid(b.id),revision:typeof b.revision==='string'&&/^[1-9][0-9]{0,18}$/.test(b.revision)?b.revision:fail(),enabled:typeof b.enabled==='boolean'?b.enabled:fail(),
   label:str(b.label,120),rules:Array.isArray(b.rules)?(b.rules as unknown[]).map(rule):fail(),reason:str(b.reason,1000)}:null,
  claims:(w.claims as unknown[]).map(claim),rechecks:(w.rechecks as unknown[]).map(recheck),readAt:instant(w.read_at)}
}
// A command's reply, bound to its request: the same request UUID, the
// claim and recheck it names.
export function parseCommand(v:unknown,r:ReminderRequest,actor:string):CommandResult{
 const c=obj(v);exact(c,['contract_version','actor_scope_id','operation','run_id','identity_hash','result','claim','recheck','external_delivery_enabled','scheduler_enabled','sent'])
 if(c.contract_version!=='cp7.reminder-command.v2'||c.actor_scope_id!==actor||c.operation!==r.operation||c.run_id!==r.runId||c.identity_hash!==r.payload.identity_hash
  ||c.external_delivery_enabled!==false||c.scheduler_enabled!==false||c.sent!==false)fail()
 const res=obj(c.result);if(res.request_id!==r.id||res.status!=='COMMITTED'&&res.status!=='NOT_COMMITTED')fail()
 const cl=c.claim===null?null:claim(c.claim),rc=c.recheck===null?null:recheck(c.recheck)
 if((res.claim_id??null)!==(cl?.id??null)&&r.operation!=='BINDING'&&r.operation!=='POLICY')fail()
 return{operation:r.operation,status:res.status,outcome:res.outcome==='CLAIMED'||res.outcome==='NOT_SENT'?res.outcome:null,verdict:res.verdict==null?null:verdict(res.verdict),
  claimId:cl?.id??null,localStatus:res.local_status==null?null:res.local_status as ClaimStatus,claim:cl,recheck:rc,bindingId:guid(res.binding_id)?res.binding_id:null,
  policyId:guid(res.policy_id)?res.policy_id:null}
}

// The pending command is kept per actor scope, so a reload resends the same
// request (the server answers the same UUID and payload with the same result)
// or looks it up (an unknown UUID is closed for good).
export const reminderV2RequestKey=(scope:string)=>`erp.cp7.reminder-v2-request.v1:${scope}`
const OPS:readonly Operation[]=['BINDING','POLICY','CLAIM','OUTCOME','RESOLUTION']
function request(v:unknown):ReminderRequest{const r=obj(v);exact(r,['id','operation','runId','payload']);if(!OPS.includes(r.operation as Operation))fail()
 const p=obj(r.payload);if(p.run_id!==r.runId)fail();hex(p.identity_hash);return{id:uuid(r.id),operation:r.operation as Operation,runId:uuid(r.runId),payload:p}}
export function readReminderRequest(scope:string):{pending:ReminderRequest|null;error:string|null}{
 try{const s=localStorage.getItem(reminderV2RequestKey(scope));return{pending:s===null?null:request(JSON.parse(s)),error:null}}
 catch{return{pending:null,error:'Permintaan pengingat tersimpan belum dapat dibaca. Catatannya dipertahankan.'}}
}
export function persistReminderRequest(scope:string,r:ReminderRequest){
 request(r);const held=readReminderRequest(scope)
 if(held.error||held.pending&&JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Selesaikan permintaan pengingat yang tertunda terlebih dahulu.')
 const s=JSON.stringify(r);try{localStorage.setItem(reminderV2RequestKey(scope),s)}catch{/* checked below */}
 if(localStorage.getItem(reminderV2RequestKey(scope))!==s)throw Error('Permintaan pengingat belum tersimpan; tidak ada permintaan yang dikirim.')
}
export function clearReminderRequest(scope:string,r:ReminderRequest){
 const held=readReminderRequest(scope);if(held.error||JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Permintaan pengingat tersimpan berubah.')
 try{localStorage.removeItem(reminderV2RequestKey(scope))}catch{/* checked below */}
 if(localStorage.getItem(reminderV2RequestKey(scope))!==null)throw Error('Permintaan pengingat belum dapat diselesaikan.')
}

export type Reply={data:unknown;error:unknown}
export const CONDITION_SET_BACKOFF_MS=2000
// Step the condition set while RUNNING; a skipped step (another session runs
// the page) waits and steps again. Returns the final set, or null once aborted.
export async function driveConditionSet(o:{step:()=>PromiseLike<Reply>;runId:string;identityHash:string;aborted?:()=>boolean;sleep?:(ms:number)=>Promise<void>;onStatus?:(s:ConditionSet)=>void}):Promise<ConditionSet|null>{
 const aborted=o.aborted??(()=>false),sleep=o.sleep??(ms=>new Promise<void>(r=>setTimeout(r,ms)))
 for(;;){
  if(aborted())return null
  const r=await o.step();if(r.error)throw r.error
  const s=parseConditionSet(r.data,o.runId,o.identityHash);o.onStatus?.(s)
  if(s.state!=='RUNNING')return s
  if(s.workerActive){await sleep(CONDITION_SET_BACKOFF_MS)}
 }
}

export const snapshotStateLabels:Record<SnapshotState,string>={ACTIVE:'Perlu ditangani saat analisis',DATA_REVIEW:'Data perlu diperiksa',NO_CURRENT_GAP:'Tidak ada kekurangan pada skenario ini',RESOLVED:'Sudah cukup saat analisis'}
export const claimStatusLabels:Record<ClaimStatus,string>={CLAIMED:'Pratinjau dibuat, belum dicatat',LOCAL_SINK_CAPTURED:'Tercatat di pratinjau lokal',SUPPRESSED:'Ditahan oleh pemeriksaan ulang',UNKNOWN:'Hasil lokal belum pasti'}
const n=(v:unknown)=>typeof v==='string'?v:'?'
// The recheck in words: what the snapshot said and what is true now.
export function verdictText(r:Recheck):string{
 const x=r.numbers
 switch(r.verdict){
  case'STILL_OPEN':return r.kind==='SNAPSHOT'?(r.ruleId==='PRODUCTION_GAP'?`Masih perlu: kurang sedikitnya ${n(x.need_now_pcs)} PCS sekarang (analisis: ${n(x.need_snapshot_pcs)} PCS).`:'Masih perlu: kebutuhan produksi dan bahan tidak berubah sejak analisis.')
   :`Masih terbuka: lewat jatuh tempo ${n(x.days_overdue)} hari, sisa ${n(x.remaining_idr)} IDR.`
  case'RESOLVED_NOW':return r.kind==='SNAPSHOT'?`Sudah selesai sejak analisis — tidak ditagih: kurang ${n(x.need_snapshot_pcs)} PCS saat analisis; stok jadi dan barang dalam proses naik ${n(x.increase_pcs)} PCS.`
   :'Sudah lunas atau selesai — tidak ditagih.'
  case'BELOW_THRESHOLD_NOW':return r.kind==='SNAPSHOT'&&r.ruleId==='PRODUCTION_GAP'?`Kekurangan sekarang ${n(x.need_now_pcs)} PCS, di bawah batas pengaturan ${n(x.threshold)} — tidak dibuat pratinjau.`:`Di bawah batas pengaturan ${n(x.threshold)} — tidak dibuat pratinjau.`
  case'UNKNOWN_NOW':return'Belum bisa dipastikan sekarang (data proses atau sumber belum lengkap) — tidak dibuat pratinjau.'
  case'CHANGED_REVIEW_REQUIRED':return r.reason==='FABRIC_MATERIAL_CHANGED_AFTER_SNAPSHOT'?'Ada gerakan stok, PO, atau rencana potong bahan ini sejak analisis; jalankan analisis baru.'
   :r.reason==='TARGET_PLANNED_AFTER_SNAPSHOT'?'Sudah ada rencana produksi untuk produk ini sejak analisis; jalankan analisis baru.':'Produk, kebijakan produksi, atau kebutuhan berubah sejak analisis; jalankan analisis baru.'
  case'NO_LONGER_DUE':return'Belum jatuh tempo atau dokumennya tidak aktif lagi — tidak ditagih.'
  case'NOT_FOUND_NOW':return'Kondisi ini tidak ada lagi di sumber ERP — tidak ditagih.'
  case'CONDITION_CHANGED':return'Angka kondisi berubah sejak dibaca (misalnya ada pembayaran sebagian); baca ulang sebelum membuat pratinjau.'
 }
}
const failureText:Record<string,string>={CP7_REMINDER_V2_STAGE_STOPPED:'Satu halaman dihentikan batas waktu server tiga kali berturut-turut.',
 CP7_REMINDER_V2_SNAPSHOT_INVARIANT:'Isi analisis tidak konsisten dengan indeksnya.',CP7_REMINDER_V2_LABEL_AMBIGUOUS:'Satu target punya lebih dari satu nama produk di analisis ini.'}
export const conditionSetFailureText=(f:NonNullable<ConditionSet['failure']>)=>`Daftar pengingat gagal disiapkan pada langkah ${f.unit} (${f.code}). ${failureText[f.code]??'Server menolak langkah ini.'} Jalankan analisis baru bila perlu.`
export const conditionSetProgressText=(s:ConditionSet)=>s.state==='RUNNING'?`Menyiapkan daftar pengingat: ${s.stage==='PAGE'?`halaman ${s.pagesDone+1} dari ${s.pageCount}`:'memeriksa kelengkapan'}`+(s.unitAttempts?` · percobaan ulang ${s.unitAttempts}`:'')+(s.workerActive?' · sesi lain sedang menyiapkan halaman ini':'')+'.'
 :s.state==='DONE'?`Daftar pengingat siap: ${s.totals?.conditions??0} kondisi dari ${s.targetsTotal} target.`:'Daftar pengingat gagal disiapkan.'
export const ruleLabel=(r:ReminderRule)=>reminderRuleLabels[r]
