import type {SupabaseClient} from '@supabase/supabase-js'
import type {Json, PreconnectDatabase} from './types/database.preconnect'

export const cuttingStatusBasis = 'CURRENT_POSTED_PRIOR_PHYSICAL_GROUPS_MATERIAL_PATTERN_REVISION_EXACT_SIZE_SET'
export const cuttingStatusLabels = {
  NOT_FINISHED:'Belum disahkan / dibatalkan', POLICY_REQUIRED:'Aturan penilaian belum ditetapkan',
  POLICY_PAUSED:'Penilaian dijeda', INSUFFICIENT_HISTORY:'Riwayat belum cukup',
  DATA_INCOMPLETE:'Data pembanding belum lengkap', WITHIN:'Wajar menurut riwayat',
  LOW:'Lebih sedikit dari biasanya', HIGH:'Lebih banyak dari biasanya',
} as const
export type CuttingStatus = keyof typeof cuttingStatusLabels
export type CuttingStatusPolicy = {id:string; revision:string; state:'ACTIVE'|'PAUSED'; coverage:string;
  min_groups:string; reason:string; actor:string; recorded_at:string}
export type AutomaticCuttingStatus = {
  group:{id:string; version:string; posted:boolean; physical_at:string; pattern_id:string|null;
    pattern_revision:string|null; pattern_label:string; production_status:string; production_stage:string}
  policy:CuttingStatusPolicy|null; checkedAt:string
  materials:{material_id:string; sku:string; name:string; unit:string; size_ids:string[]; size_labels:string[];
    consumed:string|null; total_pcs:string|null; history_groups:string; status:CuttingStatus;
    lower_pcs:string|null; upper_pcs:string|null}[]
}
export type CuttingStatusPolicyPayload = {expected_revision:string; state:'ACTIVE'|'PAUSED'; coverage:string;
  min_groups:string; reason:string; explicit_review:true}
export type CuttingStatusPolicyIntent = {requestId:string; payload:CuttingStatusPolicyPayload}

// Narrow addon to the existing authenticated client. No new client/session or
// untyped RPC is created. The integrator can fold these three signatures into
// the shared hand-written preconnect contract without changing this wire API.
type StatusDatabase = {public:Omit<PreconnectDatabase['public'],'Functions'>&{Functions:
  PreconnectDatabase['public']['Functions']&{
    erp_cp7_get_cutting_status_v1:{Args:{p_group:string};Returns:Json}
    erp_cp7_save_cutting_status_policy_v1:{Args:{p_payload:Json;p_request:string};Returns:Json}
    erp_cp7_get_cutting_status_policy_request_v1:{Args:{p_payload:Json;p_request:string};Returns:Json}
  }}}
export const cuttingStatusClient = (client:SupabaseClient<PreconnectDatabase>) => client as unknown as SupabaseClient<StatusDatabase>

const fail = ():never => {throw Error('Status hasil potong tidak lengkap atau tidak cocok. Muat ulang sumber.')}
const object = (v:unknown) => v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const closed = (v:unknown,keys:string[]) => {const r=object(v);if(Object.keys(r).length!==keys.length||keys.some(k=>!(k in r)))fail();return r}
const text = (v:unknown,max=1000) => typeof v==='string'&&v.length<=max?v:fail()
const nonempty = (v:unknown,max=1000) => {const s=text(v,max);return s.trim()?s:fail()}
const id = (v:unknown) => typeof v==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(v)?v:fail()
const count = (v:unknown,positive=false) => {
  if(typeof v!=='string'||!/^(0|[1-9][0-9]{0,18})$/.test(v)||BigInt(v)>9223372036854775807n||positive&&BigInt(v)<1n)fail()
  return v as string
}
const decimal = (v:unknown) => typeof v==='string'&&/^(0|[1-9][0-9]{0,19})(\.[0-9]{1,12})?$/.test(v)?v:fail()
const instant = (v:unknown) => {
  const s=text(v,40)
  if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(s)||!Number.isFinite(Date.parse(s)))fail()
  return s
}
const array = <T>(v:unknown,parse:(x:unknown)=>T) => Array.isArray(v)?v.map(parse):fail()
const nullable = <T>(v:unknown,parse:(x:unknown)=>T) => v===null?null:parse(v)
const coverage = (v:unknown) => {
  if(typeof v!=='string'||!/^0\.[0-9]{1,12}$/.test(v)||!/[1-9]/.test(v))fail()
  return v as string
}
const coverageUnits = (v:string) => BigInt(v.slice(2).padEnd(12,'0'))
export function cuttingCoverageFromPercent(raw:string):string {
  const match=/^(0|[1-9][0-9]?)(?:[.,]([0-9]{1,10}))?$/.exec(raw.trim())
  if(!match)throw Error('Isi cakupan rentang lebih dari 0 dan kurang dari 100 persen.')
  const units=BigInt(match[1])*10000000000n+BigInt((match[2]??'').padEnd(10,'0'))
  if(units===0n)throw Error('Cakupan rentang harus lebih dari 0 persen.')
  return '0.'+units.toString().padStart(12,'0').replace(/0+$/,'')
}
export function cuttingCoveragePercent(raw:string):string {
  const units=coverageUnits(coverage(raw)),s=units.toString().padStart(11,'0')
  return (s.slice(0,-10)+'.'+s.slice(-10)).replace(/\.?0+$/,'')
}

function policy(v:unknown):CuttingStatusPolicy {
  const r=closed(v,['id','revision','state','coverage','min_groups','reason','actor','recorded_at'])
  if(r.state!=='ACTIVE'&&r.state!=='PAUSED')fail()
  const minimum=count(r.min_groups,true);if(BigInt(minimum)>1000000n)fail()
  return {id:id(r.id),revision:count(r.revision,true),state:r.state as 'ACTIVE'|'PAUSED',coverage:coverage(r.coverage),
    min_groups:minimum,reason:nonempty(r.reason),actor:id(r.actor),recorded_at:instant(r.recorded_at)}
}

export function parseAutomaticCuttingStatus(v:unknown,groupId:string):AutomaticCuttingStatus {
  const r=closed(v,['contract_version','checked_at','group','policy','materials','scope','basis','business_write'])
  if(r.contract_version!=='cp7.automatic-cutting-status.v1'||r.scope!=='FACTORY'||r.basis!==cuttingStatusBasis||r.business_write!==false)fail()
  const g=closed(r.group,['id','version','posted','physical_at','pattern_id','pattern_revision','pattern_label','production_status','production_stage'])
  if(g.id!==groupId||typeof g.posted!=='boolean')fail()
  const group={id:id(g.id),version:count(g.version,true),posted:g.posted as boolean,physical_at:instant(g.physical_at),
    pattern_id:nullable(g.pattern_id,id),pattern_revision:nullable(g.pattern_revision,x=>nonempty(x,100)),
    pattern_label:text(g.pattern_label,300),production_status:nonempty(g.production_status,64),production_stage:nonempty(g.production_stage,64)}
  const pol=nullable(r.policy,policy)
  const materials=array(r.materials,x=>{
    const m=closed(x,['material_id','sku','name','unit','size_ids','size_labels','consumed','total_pcs','history_groups','status','lower_pcs','upper_pcs'])
    if(typeof m.status!=='string'||!Object.hasOwn(cuttingStatusLabels,m.status))fail()
    const status=m.status as CuttingStatus,sizes=array(m.size_ids,id),labels=array(m.size_labels,x=>nonempty(x,100))
    if(new Set(sizes).size!==sizes.length||sizes.length!==labels.length)fail()
    const row={material_id:id(m.material_id),sku:nonempty(m.sku,200),name:nonempty(m.name,300),unit:nonempty(m.unit,30),
      size_ids:sizes,size_labels:labels,consumed:nullable(m.consumed,decimal),total_pcs:nullable(m.total_pcs,count),
      history_groups:count(m.history_groups),status,lower_pcs:nullable(m.lower_pcs,count),upper_pcs:nullable(m.upper_pcs,count)}
    const judged=status==='WITHIN'||status==='LOW'||status==='HIGH'
    if(!group.posted&&status!=='NOT_FINISHED'||group.posted&&status==='NOT_FINISHED')fail()
    if(status==='POLICY_REQUIRED'&&pol!==null||status==='POLICY_PAUSED'&&pol?.state!=='PAUSED')fail()
    if(status==='INSUFFICIENT_HISTORY'&&(pol?.state!=='ACTIVE'||BigInt(row.history_groups)>=BigInt(pol.min_groups)))fail()
    if(judged){
      if(pol?.state!=='ACTIVE'||!group.pattern_id||!group.pattern_revision||sizes.length===0||row.total_pcs===null||BigInt(row.total_pcs)<1n||row.consumed===null||!/[1-9]/.test(row.consumed)||row.lower_pcs===null||row.upper_pcs===null||BigInt(row.history_groups)<BigInt(pol.min_groups))fail()
      const actual=BigInt(row.total_pcs!),low=BigInt(row.lower_pcs!),high=BigInt(row.upper_pcs!)
      if(low>high||status==='LOW'&&actual>=low||status==='HIGH'&&actual<=high||status==='WITHIN'&&(actual<low||actual>high))fail()
    }else if(row.lower_pcs!==null||row.upper_pcs!==null)fail()
    return row
  })
  if(new Set(materials.map(m=>m.material_id)).size!==materials.length)fail()
  return {group,policy:pol,checkedAt:instant(r.checked_at),materials}
}

export function validateCuttingStatusPolicyIntent(v:unknown):CuttingStatusPolicyIntent {
  const r=closed(v,['requestId','payload']),p=closed(r.payload,['expected_revision','state','coverage','min_groups','reason','explicit_review'])
  if(p.explicit_review!==true||p.state!=='ACTIVE'&&p.state!=='PAUSED')fail()
  const revision=count(p.expected_revision),minimum=count(p.min_groups,true)
  if(BigInt(revision)>9223372036854775806n||BigInt(minimum)>1000000n)fail()
  return {requestId:id(r.requestId),payload:{expected_revision:revision,state:p.state as 'ACTIVE'|'PAUSED',
    coverage:coverage(p.coverage),min_groups:minimum,reason:nonempty(p.reason),explicit_review:true}}
}
export function validateCuttingStatusPolicyResult(v:unknown,intent:CuttingStatusPolicyIntent,actor:string):'COMMITTED'|'NOT_COMMITTED' {
  const r=closed(v,['contract_version','request_id','status','policy'])
  if(r.contract_version!=='cp7.automatic-cutting-policy-result.v1'||r.request_id!==intent.requestId)fail()
  if(r.status==='NOT_COMMITTED'){if(r.policy!==null)fail();return 'NOT_COMMITTED'}
  if(r.status!=='COMMITTED')fail()
  const p=policy(r.policy),expected=intent.payload
  if(p.actor!==actor||BigInt(p.revision)!==BigInt(expected.expected_revision)+1n||p.state!==expected.state||
    coverageUnits(p.coverage)!==coverageUnits(expected.coverage)||p.min_groups!==expected.min_groups||p.reason!==expected.reason.trim())fail()
  return 'COMMITTED'
}

// One durable entry per UUID: simultaneous tabs can never overwrite another
// lost-reply intent. Both remain recoverable; the server revision lock admits
// only one conflicting edit. Entries are removed only after a matched reply.
export const cuttingStatusPolicyEvent='erp:cutting-status-policy'
export const cuttingStatusPolicyPrefix=(scope:string)=>`erp-cutting-status-policy.v1:${scope}:`
export function pendingCuttingStatusPolicies(scope:string):CuttingStatusPolicyIntent[] {
  const prefix=cuttingStatusPolicyPrefix(scope),pending:CuttingStatusPolicyIntent[]=[]
  for(let n=0;n<localStorage.length;n++){
    const key=localStorage.key(n);if(!key?.startsWith(prefix))continue
    const raw=localStorage.getItem(key)??fail();if(raw.length>8192)fail()
    const intent=validateCuttingStatusPolicyIntent(JSON.parse(raw))
    if(key!==prefix+intent.requestId)fail()
    pending.push(intent)
  }
  return pending.sort((a,b)=>a.requestId.localeCompare(b.requestId))
}
export function holdCuttingStatusPolicy(scope:string,intent:CuttingStatusPolicyIntent){
  const checked=validateCuttingStatusPolicyIntent(intent),key=cuttingStatusPolicyPrefix(scope)+checked.requestId,raw=JSON.stringify(checked)
  const old=localStorage.getItem(key);if(old!==null&&old!==raw)fail()
  localStorage.setItem(key,raw);if(localStorage.getItem(key)!==raw)fail()
  dispatchEvent(new CustomEvent(cuttingStatusPolicyEvent,{detail:scope}))
}
export function releaseCuttingStatusPolicy(scope:string,intent:CuttingStatusPolicyIntent){
  const key=cuttingStatusPolicyPrefix(scope)+intent.requestId,raw=localStorage.getItem(key)
  if(raw!==JSON.stringify(validateCuttingStatusPolicyIntent(intent)))fail()
  localStorage.removeItem(key);if(localStorage.getItem(key)!==null)fail()
  dispatchEvent(new CustomEvent(cuttingStatusPolicyEvent,{detail:scope}))
}
