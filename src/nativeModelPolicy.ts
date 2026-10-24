import {stagedInstant} from './nativeAnalysisPages'

export const modelMethods=['NAIVE','MOVING_MEAN','SES','DAMPED_HOLT','SEASONAL_NAIVE','SBA','TSB']as const
export type ModelMethod=typeof modelMethods[number]
export type ModelPolicyConfig={minimum_training_days:string;maximum_horizon_days:string;allowed_methods:ModelMethod[];promotion:{minimum_complete_folds:string;minimum_mae_improvement:string;maximum_bias_worsening:string;maximum_tail_worsening:string;season_lag:string}}
export type ModelPolicy={id:string;revision:string;registry_id:string;recorded_at:string;state:'ACTIVE'|'SUSPENDED';reason:string;config:ModelPolicyConfig}
export type ModelPolicySource={policy:ModelPolicy;actor_scope_id:string;request_id:string;template_hash:string}
export type ModelDefinition={id:string;method:string;params:Record<string,string|null>}
export type ModelPolicyWorkspace={actor:string;accessEpoch:string;canWrite:boolean;revision:string;state:'UNREVIEWED'|'ACTIVE'|'SUSPENDED';current:ModelPolicySource|null;template:{hash:string;models:{baseline:ModelDefinition;challengers:ModelDefinition[]}}}
export type ModelPolicyPayload={contract_version:'cp7.model-activation-policy-command.v1';action:'SET'|'SUSPEND';config:ModelPolicyConfig|null;template_hash:string|null;reason:string;reviewed:true;expected_revision:string;access_epoch:string}
export type PreparedModelPolicy={requestId:string;actor:string;payload:ModelPolicyPayload;prior:ModelPolicySource|null}
type Obj=Record<string,unknown>
function fail():never{throw Error('Kebijakan model belum dapat dipastikan. Baca ulang versi tersimpan sebelum melanjutkan.')}
const obj=(x:unknown):Obj=>x&&typeof x==='object'&&!Array.isArray(x)?x as Obj:fail()
const exact=(x:Obj,keys:string[])=>{if(Object.keys(x).sort().join('|')!==[...keys].sort().join('|'))fail()}
const uuid=(x:unknown)=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(x)?x:fail()
const hash=(x:unknown)=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x)?x:fail()
const revision=(x:unknown)=>{if(typeof x!=='string'||!/^(0|[1-9][0-9]{0,18})$/.test(x)||BigInt(x)>9223372036854775807n)fail();return x}
const integer=(x:unknown,max:number)=>{const s=revision(x);if(BigInt(s)<1n||BigInt(s)>BigInt(max))fail();return s}
const decimal=(x:unknown)=>typeof x==='string'&&/^(0|[1-9][0-9]{0,29})(\.[0-9]{1,12})?$/.test(x)?x:fail()
const reason=(x:unknown)=>typeof x==='string'&&x.trim()===x&&x.length>0&&Array.from(x).length<=1000?x:fail()
const micros=(x:string)=>{const m=stagedInstant(x).replace(/\+00:00$/,'Z').match(/^(.{19})(?:\.(\d{1,6}))?Z$/);if(!m)fail();return BigInt(Date.parse(m[1]+'Z'))*1000n+BigInt((m[2]??'').padEnd(6,'0'))}
const canonical=(x:unknown):string=>JSON.stringify(x,(_key,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v)
export function parseModelPolicyConfig(value:unknown):ModelPolicyConfig{
 const c=obj(value);exact(c,['minimum_training_days','maximum_horizon_days','allowed_methods','promotion'])
 const p=obj(c.promotion);exact(p,['minimum_complete_folds','minimum_mae_improvement','maximum_bias_worsening','maximum_tail_worsening','season_lag'])
 if(!Array.isArray(c.allowed_methods)||c.allowed_methods.length>7||new Set(c.allowed_methods).size!==c.allowed_methods.length||c.allowed_methods.some(m=>!modelMethods.includes(m)))fail()
 return{minimum_training_days:integer(c.minimum_training_days,366),maximum_horizon_days:integer(c.maximum_horizon_days,90),allowed_methods:[...c.allowed_methods],promotion:{minimum_complete_folds:integer(p.minimum_complete_folds,100),minimum_mae_improvement:decimal(p.minimum_mae_improvement),maximum_bias_worsening:decimal(p.maximum_bias_worsening),maximum_tail_worsening:decimal(p.maximum_tail_worsening),season_lag:integer(p.season_lag,3660)}}
}
function policy(value:unknown):ModelPolicy{
 const p=obj(value);exact(p,['id','revision','registry_id','recorded_at','state','reason','config'])
 const id=uuid(p.id);if(p.registry_id!=='cp7.owner-model-policy.'+id||revision(p.revision)==='0'||!['ACTIVE','SUSPENDED'].includes(String(p.state)))fail()
 return{id,revision:revision(p.revision),registry_id:p.registry_id,recorded_at:stagedInstant(p.recorded_at),state:p.state as ModelPolicy['state'],reason:reason(p.reason),config:parseModelPolicyConfig(p.config)}
}
function source(value:unknown):ModelPolicySource{
 const p=obj(value);exact(p,['policy','actor_scope_id','request_id','template_hash'])
 return{policy:policy(p.policy),actor_scope_id:uuid(p.actor_scope_id),request_id:uuid(p.request_id),template_hash:hash(p.template_hash)}
}
export {source as parseModelPolicySource}
// Fixed prospective candidate definitions from the existing Native registry.
// Thresholds and allowed methods are intentionally absent from this template.
const definitions:ModelDefinition[]=[{id:'mean-1',method:'MEAN',params:{}},{id:'naive-1',method:'NAIVE',params:{}},{id:'moving-mean-7-1',method:'MOVING_MEAN',params:{window:'7'}},{id:'ses-half-1',method:'SES',params:{alpha:'0.5',initial_level:null}},{id:'holt-damped-1',method:'DAMPED_HOLT',params:{alpha:'0.5',beta:'0.5',phi:'0.9',initial_level:null,initial_trend:'0'}},{id:'seasonal-7-1',method:'SEASONAL_NAIVE',params:{season:'7'}},{id:'sba-half-1',method:'SBA',params:{alpha:'0.5',beta:'0.5'}},{id:'tsb-half-1',method:'TSB',params:{alpha:'0.5',beta:'0.5'}}]
export function fixedModelDefinitions():ModelDefinition[]{return structuredClone(definitions)}
function template(value:unknown):ModelPolicyWorkspace['template']{
 const t=obj(value);exact(t,['models','hash']);const m=obj(t.models);exact(m,['baseline','challengers'])
 if(!Array.isArray(m.challengers)||canonical([m.baseline,...m.challengers])!==canonical(definitions))fail()
 return{hash:hash(t.hash),models:{baseline:structuredClone(definitions[0]),challengers:structuredClone(definitions.slice(1))}}
}
export function parseModelPolicyWorkspace(value:unknown,actor:string):ModelPolicyWorkspace{
 const w=obj(value);exact(w,['contract_version','actor_scope_id','access_epoch','can_write','revision','current','state','model_template','forecast_applied','production_go'])
 if(w.contract_version!=='cp7.model-activation-policy-workspace.v1'||w.actor_scope_id!==uuid(actor)||typeof w.can_write!=='boolean'||w.forecast_applied!==false||w.production_go!==false)fail()
 const current=w.current===null?null:source(w.current),rev=revision(w.revision)
 if(current?current.policy.revision!==rev||current.policy.state!==w.state:rev!=='0'||w.state!=='UNREVIEWED')fail()
 return{actor,accessEpoch:hash(w.access_epoch),canWrite:w.can_write,revision:rev,state:w.state as ModelPolicyWorkspace['state'],current,template:template(w.model_template)}
}
export function prepareModelPolicy(w:ModelPolicyWorkspace,action:'SET'|'SUSPEND',config:unknown,explanation:string,reviewed:boolean,id:string):PreparedModelPolicy{
 if(!w.canWrite||!reviewed||w.revision==='9223372036854775807'||action==='SUSPEND'&&!w.current)fail()
 return parsePreparedModelPolicy({requestId:id,actor:w.actor,prior:w.current,payload:{contract_version:'cp7.model-activation-policy-command.v1',action,config:action==='SET'?parseModelPolicyConfig(config):null,template_hash:action==='SET'?w.template.hash:null,reason:reason(explanation.trim()),reviewed:true,expected_revision:w.revision,access_epoch:w.accessEpoch}},w.actor)
}
export function parsePreparedModelPolicy(value:unknown,actor:string):PreparedModelPolicy{
 const r=obj(value);exact(r,['requestId','actor','payload','prior']);const p=obj(r.payload)
 exact(p,['contract_version','action','config','template_hash','reason','reviewed','expected_revision','access_epoch'])
 if(uuid(r.actor)!==uuid(actor)||p.contract_version!=='cp7.model-activation-policy-command.v1'||!['SET','SUSPEND'].includes(String(p.action))||p.reviewed!==true)fail()
 const prior=r.prior===null?null:source(r.prior),rev=revision(p.expected_revision)
 if(rev==='9223372036854775807'||rev!==(prior?.policy.revision??'0'))fail()
 if(p.action==='SET'){parseModelPolicyConfig(p.config);hash(p.template_hash)}
 else if(!prior||p.config!==null||p.template_hash!==null)fail()
 reason(p.reason);hash(p.access_epoch);uuid(r.requestId)
 return structuredClone(r)as PreparedModelPolicy
}
export function parseModelPolicyOutcome(value:unknown,command:PreparedModelPolicy):ModelPolicy{
 parsePreparedModelPolicy(command,command.actor)
 const r=obj(value),p=command.payload;exact(r,['contract_version','request_id','actor_scope_id','policy','template_hash','forecast_applied','production_go'])
 if(r.contract_version!=='cp7.model-activation-policy-outcome.v1'||r.request_id!==command.requestId||r.actor_scope_id!==command.actor||r.forecast_applied!==false||r.production_go!==false)fail()
 const saved=policy(r.policy)
 if(BigInt(saved.revision)!==BigInt(p.expected_revision)+1n||saved.reason!==p.reason||saved.state!==(p.action==='SET'?'ACTIVE':'SUSPENDED'))fail()
 if(canonical(saved.config)!==canonical(p.action==='SET'?p.config:command.prior?.policy.config)||hash(r.template_hash)!==(p.action==='SET'?p.template_hash:command.prior?.template_hash))fail()
 if(command.prior&&(micros(saved.recorded_at)<micros(command.prior.policy.recorded_at)||saved.id===command.prior.policy.id))fail()
 return saved
}
type Reply={data:unknown;error:unknown}
type Client={rpc(name:'erp_cp7_get_model_activation_policy_v1'):PromiseLike<Reply>;rpc(name:'erp_cp7_save_model_activation_policy_v1',args:{p_payload:ModelPolicyPayload;p_request:string}):PromiseLike<Reply>}
export async function readModelPolicy(client:unknown,actor:string){const r=await(client as Client).rpc('erp_cp7_get_model_activation_policy_v1');if(r.error)throw r.error;return parseModelPolicyWorkspace(r.data,actor)}
export async function saveModelPolicy(client:unknown,command:PreparedModelPolicy){parsePreparedModelPolicy(command,command.actor);const r=await(client as Client).rpc('erp_cp7_save_model_activation_policy_v1',{p_payload:structuredClone(command.payload),p_request:command.requestId});if(r.error)throw r.error;return parseModelPolicyOutcome(r.data,command)}
export const modelPolicyRequestKey=(scope:string)=>'erp.cp7.model-policy.v1:'+scope
export function readModelPolicyRequest(scope:string,actor:string):{pending:PreparedModelPolicy|null;error:string}{
 try{const s=localStorage.getItem(modelPolicyRequestKey(scope));return{pending:s===null?null:parsePreparedModelPolicy(JSON.parse(s),actor),error:''}}
 catch{return{pending:null,error:'Catatan kebijakan belum dapat dibaca. Pulihkan catatan sebelum menyimpan lagi.'}}
}
export function persistModelPolicyRequest(scope:string,r:PreparedModelPolicy){
 const old=readModelPolicyRequest(scope,r.actor);if(old.error||old.pending)throw Error('Periksa hasil permintaan kebijakan sebelumnya terlebih dahulu.')
 parsePreparedModelPolicy(r,r.actor);const key=modelPolicyRequestKey(scope),raw=JSON.stringify(r);localStorage.setItem(key,raw)
 if(localStorage.getItem(key)!==raw)throw Error('Permintaan kebijakan belum tercatat di perangkat. Penyimpanan belum dikirim.')
}
export function clearModelPolicyRequest(scope:string,r:PreparedModelPolicy){
 const old=readModelPolicyRequest(scope,r.actor);if(old.error||canonical(old.pending)!==canonical(r))throw Error('Catatan kebijakan berubah. Periksa permintaan yang sama.')
 const key=modelPolicyRequestKey(scope);localStorage.removeItem(key);if(localStorage.getItem(key)!==null)throw Error('Catatan kebijakan belum dapat diselesaikan.')
}
