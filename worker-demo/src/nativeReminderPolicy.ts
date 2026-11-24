import {parseNativeAnalysis,type NativeAnalysis,type AnalysisFinanceAccess} from './nativeAnalysis'
import type {NativeDemandQuery} from './nativeDemandHistory'
import {financeDate} from './financeReportContract'

export const reminderRuleIds=['PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED','AR_DUE','AP_DUE'] as const
export type ReminderRule=typeof reminderRuleIds[number]
export const reminderRuleLabels:Record<ReminderRule,string>={PRODUCTION_GAP:'Kebutuhan produksi',ACCESSORY_NEED:'Kebutuhan aksesori',FABRIC_NEED:'Kebutuhan kain',AR_DUE:'Piutang jatuh tempo',AP_DUE:'Utang jatuh tempo'}
export type ReminderPolicyConfig={enabled:boolean|null;threshold_value:string|null;threshold_unit:string|null;cooldown_minutes:string|null;quiet:{enabled:boolean|null;starts_at:string|null;ends_at:string|null;timezone:'Asia/Jakarta'}}
export type ReminderPolicyRow={policy_id:string;rule_id:ReminderRule;scope_kind:'GLOBAL'|'TARGET';scope_key:string;revision:string;previous_id:string|null;config:ReminderPolicyConfig;reason:string;created_at:string;created_by:string}
export type ReminderPolicyPayload={run_id:string;rule_id:ReminderRule;scope_kind:'GLOBAL'|'TARGET';scope_key:string;expected_revision:string;config:ReminderPolicyConfig;reason:string}
export type ReminderPolicyRequest={id:string;query:NativeDemandQuery;payload:ReminderPolicyPayload}
type Result={request_id:string;run_id:string;rule_id:ReminderRule;scope_kind:'GLOBAL'|'TARGET';scope_key:string;status:'COMMITTED'|'NOT_COMMITTED';policy_id:string|null;revision:string|null}
export type NativeReminderPolicy={analysis:NativeAnalysis;rows:ReminderPolicyRow[];rules:ReminderRule[];manageAllowed:boolean;sourceHash:string;readAt:string;result:Result|null}
const fail=():never=>{throw Error('Pengaturan pengingat belum sesuai sumber dan hak akses ERP.')}
const closed=(v:unknown,keys:string[])=>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))return fail();return v as Record<string,unknown>}
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)
const uint=(v:unknown):v is string=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(v)&&BigInt(v)<=9223372036854775807n
const stamp=(v:unknown):v is string=>typeof v==='string'&&financeDate(v.slice(0,10))&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v))
const rule=(v:unknown):v is ReminderRule=>reminderRuleIds.includes(v as ReminderRule)
const tri=(v:unknown)=>v===null||typeof v==='boolean'
const canonical=(v:unknown):string=>JSON.stringify(v===null||typeof v!=='object'?v:Array.isArray(v)?v.map(x=>JSON.parse(canonical(x))):Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>[k,JSON.parse(canonical(x))])))
export function parseReminderPolicyConfig(v:unknown,r:ReminderRule):ReminderPolicyConfig{
 const c=closed(v,['enabled','threshold_value','threshold_unit','cooldown_minutes','quiet']),q=closed(c.quiet,['enabled','starts_at','ends_at','timezone'])
 if(!tri(c.enabled)||!tri(q.enabled)||q.timezone!=='Asia/Jakarta'||c.threshold_value!==null&&(typeof c.threshold_value!=='string'||!/^(0|[1-9][0-9]{0,11})(\.[0-9]{1,12})?$/.test(c.threshold_value))||c.threshold_unit!==null&&(typeof c.threshold_unit!=='string'||!(r==='FABRIC_NEED'?/^[A-Za-z][A-Za-z0-9/_-]{0,23}$/:/^[A-Z][A-Z0-9/_-]{0,23}$/).test(c.threshold_unit))||c.threshold_value!==null&&c.threshold_unit===null||c.cooldown_minutes!==null&&(typeof c.cooldown_minutes!=='string'||!/^(0|[1-9][0-9]{0,5})$/.test(c.cooldown_minutes)||BigInt(c.cooldown_minutes)>525600n))fail()
 if(r==='PRODUCTION_GAP'&&c.threshold_unit!==null&&c.threshold_unit!=='PCS'||['AR_DUE','AP_DUE'].includes(r)&&(c.threshold_unit!==null&&c.threshold_unit!=='DAY'||c.threshold_value!==null&&!/^(0|[1-9][0-9]{0,5})$/.test(c.threshold_value as string)))fail()
 if(q.enabled===true){if(typeof q.starts_at!=='string'||typeof q.ends_at!=='string'||![q.starts_at,q.ends_at].every(t=>/^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(t))||q.starts_at===q.ends_at)fail()}
 else if(q.starts_at!==null||q.ends_at!==null)fail()
 return structuredClone(c) as ReminderPolicyConfig
}
function payload(v:unknown):ReminderPolicyPayload{
 const p=closed(v,['run_id','rule_id','scope_kind','scope_key','expected_revision','config','reason'])
 if(!uuid(p.run_id)||!rule(p.rule_id)||!uint(p.expected_revision)||BigInt(p.expected_revision)>9223372036854775806n||typeof p.reason!=='string'||!p.reason.trim()||p.reason.length>1000||p.scope_kind==='GLOBAL'&&p.scope_key!=='*'||p.scope_kind==='TARGET'&&(!['PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED'].includes(p.rule_id)||typeof p.scope_key!=='string'||!/^[0-9a-f-]{36}:[0-9a-f-]{36}$/.test(p.scope_key))||!['GLOBAL','TARGET'].includes(String(p.scope_kind)))fail()
 parseReminderPolicyConfig(p.config,p.rule_id as ReminderRule);return structuredClone(p) as ReminderPolicyPayload
}
export function parseReminderPolicyRow(value:unknown,allowed:ReminderRule[],targets:Set<string>):ReminderPolicyRow{
 const r=closed(value,['policy_id','rule_id','scope_kind','scope_key','revision','previous_id','config','reason','created_at','created_by'])
 if(!uuid(r.policy_id)||!uuid(r.created_by)||!rule(r.rule_id)||!allowed.includes(r.rule_id as ReminderRule)||!uint(r.revision)||r.revision==='0'||!stamp(r.created_at)||typeof r.reason!=='string'||!r.reason.trim()||r.reason.length>1000||r.revision==='1'&&r.previous_id!==null||r.revision!=='1'&&(!uuid(r.previous_id)||r.previous_id===r.policy_id))fail()
 parseReminderPolicyConfig(r.config,r.rule_id as ReminderRule)
 if(r.scope_kind==='GLOBAL'?r.scope_key!=='*':r.scope_kind!=='TARGET'||!['PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED'].includes(r.rule_id as string)||typeof r.scope_key!=='string'||!/^[0-9a-f-]{36}:[0-9a-f-]{36}$/.test(r.scope_key))fail()
 if(r.scope_kind==='TARGET'&&!targets.has(r.scope_key as string))fail()
 return structuredClone(r) as ReminderPolicyRow
}
export function parseNativeReminderPolicy(v:unknown,q:NativeDemandQuery,actor:string,access:AnalysisFinanceAccess,request?:ReminderPolicyRequest):NativeReminderPolicy{
 const command=Boolean(request),e=closed(v,['contract_version','actor_scope_id','analysis','allowed_rules','rows','page_complete','total','source_hash','read_at','manage_allowed','missing_policy','external_delivery_enabled',...(command?['request_result']:[])])
 if(e.contract_version!=='cp7.native-rule-policy-workspace.v1'||e.actor_scope_id!==actor||e.page_complete!==true||e.external_delivery_enabled!==false||e.missing_policy!=='UNCONFIGURED_NOT_ZERO_NOT_DISABLED'||!stamp(e.read_at)||typeof e.manage_allowed!=='boolean'||typeof e.source_hash!=='string'||!/^[0-9a-f]{64}$/.test(e.source_hash)||!uint(e.total)||BigInt(e.total)>4000n||!Array.isArray(e.rows)||e.rows.length!==Number(e.total)||!Array.isArray(e.allowed_rules)||e.allowed_rules.some(r=>!rule(r))||new Set(e.allowed_rules).size!==e.allowed_rules.length)fail()
 const analysis=parseNativeAnalysis(e.analysis,q,actor,access),targets=new Set(analysis.analysis.recommendations.map(r=>r.target.key)),keys=new Set<string>()
 const allowed=e.allowed_rules as ReminderRule[];const rows=(e.rows as unknown[]).map(value=>{const r=parseReminderPolicyRow(value,allowed,targets);const key=JSON.stringify([r.rule_id,r.scope_kind,r.scope_key]);if(keys.has(key))fail();keys.add(key);return r})
 let result:Result|null=null
 if(request){const r=closed(e.request_result,['request_id','run_id','rule_id','scope_kind','scope_key','status','policy_id','revision']),p=payload(request.payload);if(!uuid(request.id)||r.request_id!==request.id||r.run_id!==p.run_id||analysis.runId!==p.run_id||r.rule_id!==p.rule_id||r.scope_kind!==p.scope_kind||r.scope_key!==p.scope_key||!['COMMITTED','NOT_COMMITTED'].includes(String(r.status)))fail();if(r.status==='NOT_COMMITTED'){if(r.policy_id!==null||r.revision!==null)fail()}else{if(!uuid(r.policy_id)||!uint(r.revision)||BigInt(r.revision)!==BigInt(p.expected_revision)+1n)fail();const latest=rows.find(x=>x.rule_id===p.rule_id&&x.scope_kind===p.scope_kind&&x.scope_key===p.scope_key);if(!latest||BigInt(latest.revision)<BigInt(r.revision as string)||latest.revision===r.revision&&(latest.policy_id!==r.policy_id||canonical(latest.config)!==canonical(p.config)||latest.reason!==p.reason))fail()}result=structuredClone(r) as Result}
 return{analysis,rows,rules:e.allowed_rules as ReminderRule[],manageAllowed:e.manage_allowed as boolean,sourceHash:e.source_hash as string,readAt:e.read_at as string,result}
}
export const reminderPolicyRequestKey=(scope:string)=>'erp.cp7.rule-policy-request.v1:'+scope
function validRequest(v:unknown):v is ReminderPolicyRequest{try{const r=closed(v,['id','query','payload']),q=closed(r.query,['from_date','through_date','group_mode']);if(!uuid(r.id)||!financeDate(q.from_date)||!financeDate(q.through_date)||q.from_date>q.through_date||!['AS_SOLD','RESTATED'].includes(String(q.group_mode))||JSON.stringify(v).length>8000)return false;payload(r.payload);return true}catch{return false}}
export function readReminderPolicyRequest(scope:string):{pending:ReminderPolicyRequest|null;error:string|null}{try{const raw=localStorage.getItem(reminderPolicyRequestKey(scope));if(raw===null)return{pending:null,error:null};const r=JSON.parse(raw);if(!validRequest(r))throw Error();return{pending:r,error:null}}catch{return{pending:null,error:'Permintaan pengaturan pengingat belum bisa dibaca. Isinya dipertahankan.'}}}
export function persistReminderPolicyRequest(scope:string,r:ReminderPolicyRequest){if(!validRequest(r))fail();const held=readReminderPolicyRequest(scope);if(held.error||held.pending&&JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Pastikan hasil pengaturan pengingat yang tertunda.');localStorage.setItem(reminderPolicyRequestKey(scope),JSON.stringify(r));if(JSON.stringify(readReminderPolicyRequest(scope).pending)!==JSON.stringify(r))throw Error('Permintaan pengaturan belum tersimpan.')}
export function clearReminderPolicyRequest(scope:string,id:string){const held=readReminderPolicyRequest(scope);if(held.error||held.pending?.id!==id)throw Error('Permintaan pengaturan berubah.');localStorage.removeItem(reminderPolicyRequestKey(scope));if(localStorage.getItem(reminderPolicyRequestKey(scope))!==null)throw Error('Permintaan pengaturan belum bisa dibersihkan.')}

export type ReminderPolicyHistoryQuery={run_id:string;rule_id:ReminderRule;scope_kind:'GLOBAL'|'TARGET';scope_key:string;before_revision:string|null;through_revision:string|null;limit:25}
export type ReminderPolicyHistory={workspace:NativeReminderPolicy;query:ReminderPolicyHistoryQuery;through:string|null;rows:ReminderPolicyRow[];total:string;nextBefore:string|null}
export function parseReminderPolicyHistory(v:unknown,q:NativeDemandQuery,actor:string,access:AnalysisFinanceAccess,p:ReminderPolicyHistoryQuery):ReminderPolicyHistory{
 const e=closed(v,['contract_version','actor_scope_id','workspace','rule_id','scope_kind','scope_key','through_revision','before_revision','rows','total','limit','next_before_revision','page_complete','history_immutable','external_delivery_enabled'])
 if(e.contract_version!=='cp7.native-policy-history.v1'||e.actor_scope_id!==actor||e.rule_id!==p.rule_id||e.scope_kind!==p.scope_kind||e.scope_key!==p.scope_key||e.before_revision!==p.before_revision||e.page_complete!==true||e.history_immutable!==true||e.external_delivery_enabled!==false||e.limit!==25||!uint(e.total)||!Array.isArray(e.rows)||e.rows.length>25||e.rows.length>Number(e.total)||e.through_revision!==null&&(!uint(e.through_revision)||e.through_revision==='0')||p.through_revision!==null&&p.through_revision!==e.through_revision||e.next_before_revision!==null&&(!uint(e.next_before_revision)||e.next_before_revision==='0'))fail()
 const workspace=parseNativeReminderPolicy(e.workspace,q,actor,access),targets=new Set(workspace.analysis.labels.map(l=>l.key)),seen=new Set<string>();if(workspace.analysis.runId!==p.run_id||p.before_revision!==null&&(!uint(p.before_revision)||p.before_revision==='0')||p.limit!==25)fail()
 let previous:ReminderPolicyRow|null=null
 const rows=(e.rows as unknown[]).map(v=>{const r=parseReminderPolicyRow(v,workspace.rules,targets);if(r.rule_id!==p.rule_id||r.scope_kind!==p.scope_kind||r.scope_key!==p.scope_key||seen.has(r.policy_id)||e.through_revision===null||BigInt(r.revision)>BigInt(e.through_revision as string)||p.before_revision!==null&&BigInt(r.revision)>=BigInt(p.before_revision)||previous&&(BigInt(previous.revision)!==BigInt(r.revision)+1n||previous.previous_id!==r.policy_id)||Date.parse(r.created_at)>Date.parse(workspace.readAt))fail();seen.add(r.policy_id);previous=r;return r})
 if(e.total==='0'?(e.through_revision!==null||rows.length!==0||e.next_before_revision!==null):e.through_revision===null||e.total!==e.through_revision||!rows.length||p.before_revision===null&&(rows[0].revision!==e.through_revision||rows.length!==Math.min(25,Number(e.total))))fail()
 if(e.next_before_revision!==null?(e.next_before_revision!==rows.at(-1)?.revision||rows.length!==25||rows.at(-1)?.revision==='1'):rows.length>0&&rows.at(-1)?.revision!=='1')fail()
 return{workspace,query:p,through:e.through_revision as string|null,rows,total:e.total as string,nextBefore:e.next_before_revision as string|null}
}
