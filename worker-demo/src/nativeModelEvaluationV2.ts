import {parseModelQuery,type NativeModelQuery,type ModelScore} from './nativeModelEvaluation'
import {parseModelPolicySource,fixedModelDefinitions,type ModelPolicySource,type ModelDefinition,type ModelMethod} from './nativeModelPolicy'

export const modelV2Method='erp_cp7_capture_model_evaluation_v2'as const
export type ModelV2Request={requestId:string;actor:string;method:typeof modelV2Method;query:NativeModelQuery}
export type ModelV2Run={runId:string;requestId:string;actor:string;query:NativeModelQuery;capturedAt:string;knownAt:string;registryAt:string;from:string;through:string;sku:string;name:string;sourceHash:string;engineHash:string;policy:ModelPolicySource|null;selected:string;mean:string|null;scores:ModelScore[];forecastFrom:string;forecasts:string[]|null;admittedAtCapture:boolean;eligibleNow:boolean;reason:string;sourceState:'UNCHANGED'|'ARCHIVED_STALE';checkedAt:string;immutableSignature:string}
type Obj=Record<string,unknown>
function fail():never{throw Error('Evaluasi sesuai kebijakan belum dapat dipastikan. Periksa kembali sumber dan hasil tersimpan.')}
const obj=(x:unknown):Obj=>x&&typeof x==='object'&&!Array.isArray(x)?x as Obj:fail()
const exact=(x:Obj,keys:string[])=>{if(Object.keys(x).sort().join('|')!==[...keys].sort().join('|'))fail()}
const text=(x:unknown)=>typeof x==='string'&&x.length>0?x:fail()
const uuid=(x:unknown)=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(x)?x:fail()
const hash=(x:unknown,n=64)=>typeof x==='string'&&new RegExp(`^[0-9a-f]{${n}}$`).test(x)?x:fail()
const count=(x:unknown,max=20000)=>typeof x==='number'&&Number.isSafeInteger(x)&&x>=0&&x<=max?x:fail()
const stringCount=(x:unknown,max:number)=>typeof x==='string'&&/^(0|[1-9][0-9]*)$/.test(x)&&Number(x)<=max?Number(x):fail()
const decimal=(x:unknown,signed=false)=>typeof x==='string'&&(signed?/^-?(0|[1-9][0-9]{0,29})(\.[0-9]{1,30})?$/:/^(0|[1-9][0-9]{0,29})(\.[0-9]{1,30})?$/).test(x)?x:fail()
const nullable=(x:unknown,signed=false)=>x===null?null:decimal(x,signed)
const bool=(x:unknown)=>typeof x==='boolean'?x:fail()
const array=(x:unknown,max:number)=>Array.isArray(x)&&x.length<=max?x:fail()
const day=(x:unknown)=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x?x:fail()
const instant=(x:unknown)=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(x)&&Number.isFinite(Date.parse(x))?x:fail()
const micros=(x:unknown)=>{const s=instant(x);return BigInt(Date.parse(s.slice(0,19)+'Z'))*1000n+BigInt(s.slice(20,26))}
const wibDay=(x:unknown)=>new Date(Date.parse(instant(x))+7*3600000).toISOString().slice(0,10)
const nextDay=(x:string)=>new Date(Date.parse(day(x))+86400000).toISOString().slice(0,10)
const canonical=(x:unknown):string=>JSON.stringify(x,(_key,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v)
const definitions=fixedModelDefinitions()
function model(raw:unknown,registryAt:string):ModelDefinition{
 const m=obj(raw);exact(m,['id','method','params','registered_at']);const expected=definitions.find(d=>d.id===m.id)
 if(!expected||m.method!==expected.method||canonical(m.params)!==canonical(expected.params)||instant(m.registered_at)!==registryAt)fail()
 return expected
}
function forecast(raw:unknown,m:ModelDefinition,horizon:number):string[]|null{
 const f=obj(raw)
 if(f.status==='INELIGIBLE'){exact(f,['status','method','reason']);if(f.method!==m.method)fail();text(f.reason);return null}
 exact(f,['method','params','reason','status','forecasts','kernel_version','training_count'])
 if(f.status!=='ELIGIBLE'||f.method!==m.method||canonical(f.params)!==canonical(m.params))fail()
 count(f.training_count,366);text(f.reason);if(f.kernel_version!==m.method.toLowerCase()+'-1')fail()
 const values=array(f.forecasts,90).map(x=>decimal(x));if(values.length!==horizon)fail();return values
}
export function parseModelV2Request(value:unknown,actor:string):ModelV2Request{
 const v=obj(value);exact(v,['requestId','actor','method','query']);if(v.method!==modelV2Method||uuid(v.actor)!==uuid(actor))fail()
 return{requestId:uuid(v.requestId),actor,method:modelV2Method,query:parseModelQuery(v.query)}
}
export function parseModelV2Run(value:unknown,query:NativeModelQuery,actor:string,prior?:ModelV2Run):ModelV2Run{
 const q=parseModelQuery(query),v=obj(value);exact(v,['contract_version','run_id','request_id','actor_scope_id','captured_at','query','assessment','current_guard','forecast_applied','production_go'])
 if(v.contract_version!=='cp7.native-model-run.v2'||v.actor_scope_id!==uuid(actor)||canonical(parseModelQuery(v.query))!==canonical(q)||v.forecast_applied!==false||v.production_go!==false)fail()
 const a=obj(v.assessment);exact(a,['contract_version','source_hash','engine_hash','source','policy_source','policy_current','evaluation','evaluation_state','baseline','activation','current_consumption_recheck_required','automatic_activation','apply_allowed','forecast_applied','production_go'])
 if(a.contract_version!=='cp7.native-model-assessment.v2'||a.current_consumption_recheck_required!==true||a.automatic_activation!==false||a.apply_allowed!==false||a.forecast_applied!==false||a.production_go!==false)fail()
 const sourceHash=hash(a.source_hash),engineHash=hash(a.engine_hash,32),s=obj(a.source),b=obj(a.baseline)
 exact(s,['history_run_id','target_key','size_id','product_sku','product_name','from_date','through_date','known_as_of','registry_id','registered_at','horizon_days','series_revision_count','knowledge_basis','no_retrospective_availability_backfill'])
 exact(b,['method','daily_mean']);if(b.method!=='MEAN')fail();const mean=nullable(b.daily_mean)
 if(s.history_run_id!==q.history_run_id||s.target_key!==q.target_key||s.size_id!==q.target_key.split(':')[1]||s.horizon_days!==q.horizon_days||s.knowledge_basis!=='ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES'||s.no_retrospective_availability_backfill!==true)fail()
 const from=day(s.from_date),through=day(s.through_date),knownAt=instant(s.known_as_of),registryAt=instant(s.registered_at),capturedAt=instant(v.captured_at),horizon=Number(q.horizon_days)
 if(from>through||(Date.parse(through)-Date.parse(from))/86400000>365||nextDay(through)>wibDay(knownAt)||micros(knownAt)>micros(capturedAt))fail()
 count(s.series_revision_count)
 const policy=a.policy_source===null?null:parseModelPolicySource(a.policy_source),policyCurrent=bool(a.policy_current)
 if(policy?(s.registry_id!==policy.policy.registry_id||registryAt!==policy.policy.recorded_at||micros(registryAt)>micros(knownAt)):s.registry_id!=='cp7.native-model-policy.v1')fail()
 const allowed=policy?definitions.filter(d=>d.method==='MEAN'||policy.policy.config.allowed_methods.includes(d.method as ModelMethod)):definitions
 const gate=obj(a.activation);exact(gate,['contract_version','state','reason','target_key','size_id','source_hash','engine_hash','known_as_of','horizon_days','forecast_from_date','policy_id','policy_revision','policy_recorded_at','registry_id','selected_model','forecast','holdout_used_for_selection','forecast_applied','production_go'])
 if(gate.contract_version!=='cp7.model-activation-gate.v1'||gate.target_key!==q.target_key||gate.size_id!==s.size_id||gate.source_hash!==sourceHash||gate.engine_hash!==engineHash||gate.horizon_days!==q.horizon_days||gate.known_as_of!==capturedAt||gate.holdout_used_for_selection!==false||gate.forecast_applied!==false||gate.production_go!==false)fail()
 for(const [field,expected]of [['policy_id',policy?.policy.id??null],['policy_revision',policy?.policy.revision??null],['policy_recorded_at',policy?.policy.recorded_at??null],['registry_id',policy?.policy.registry_id??null]])if(gate[field!]!==expected)fail()
 const forecastFrom=day(gate.forecast_from_date);if(forecastFrom!==wibDay(capturedAt)||!['ELIGIBLE','BASELINE_REQUIRED'].includes(String(gate.state)))fail();text(gate.reason)
 const scores:ModelScore[]=[],holds=new Map<string,string|null>();let selected='mean-1',forecasts:string[]|null=null
 if(a.evaluation_state==='NOT_REQUESTED_NO_ALLOWED_CHALLENGER'){
  if(!policy||policy.policy.config.allowed_methods.length!==0||a.evaluation!==null||gate.state!=='BASELINE_REQUIRED')fail()
 }else{
  if(a.evaluation_state!=='EVALUATED')fail();const e=obj(a.evaluation)
  exact(e,['contract_version','target_key','size_id','history_run_id','from_date','through_date','known_as_of','product_sku','product_name','source_hash','registry_id','registry_registered_at','knowledge_basis','no_retrospective_availability_backfill','horizon_days','series_revision_count','selection_status','selected_model_id','reason','fallback_daily_mean','evaluation','forecast','automatic_activation','apply_allowed','production_go','policy_meaning'])
  if(e.contract_version!=='cp7.native-model-result.v1'||e.source_hash!==sourceHash||e.registry_registered_at!==registryAt||e.horizon_days!==horizon||e.fallback_daily_mean!==mean||e.automatic_activation!==false||e.apply_allowed!==false||e.production_go!==false||e.policy_meaning!==(policy?'EXPLICIT_OWNER_ACTIVATION_POLICY':'TECHNICAL_PROPOSAL_NOT_OWNER_SERVICE_TARGET'))fail()
  for(const key of ['target_key','size_id','history_run_id','from_date','through_date','known_as_of','product_sku','product_name','registry_id','knowledge_basis','no_retrospective_availability_backfill','series_revision_count'])if(e[key]!==s[key])fail()
  selected=text(e.selected_model_id);const chosen=allowed.find(d=>d.id===selected);if(!chosen||!['BASELINE_RETAINED','CHALLENGER_RECOMMENDED'].includes(String(e.selection_status)))fail();text(e.reason)
  if(e.evaluation===null){if(e.forecast!==null||selected!=='mean-1'||e.selection_status!=='BASELINE_RETAINED')fail()}
  else{
   const results=obj(e.evaluation),holdout=obj(results.holdout),definition=obj(holdout.definition)
   if(results.contract_version!=='cp7.model-evaluation-result.v1'||results.kernel_version!=='rolling-evaluation-2'||results.snapshot_id!==sourceHash||results.scope_id!=='OWN_NATIVE_CAPTURE_HISTORY'||results.target_key!==q.target_key||results.size_id!==s.size_id||results.known_as_of!==knownAt||results.selected_model_id!==selected||results.selection_status!==e.selection_status||results.automatic_activation!==false||results.selection_basis!=='COMPLETE_PAIRED_CHRONOLOGICAL_VALIDATION_ONLY'||holdout.used_for_selection!==false||definition.horizon!==q.horizon_days||day(definition.origin)>through)fail()
   if(policy&&canonical(results.policy)!==canonical(policy.policy.config.promotion))fail()
   for(const raw of array(holdout.results,2)){const x=obj(raw),id=text(x.model_id);if(holds.has(id)||!['mean-1',selected].includes(id))fail();holds.set(id,x.score===null?null:decimal(obj(x.score).mae))}
   const seen=new Set<string>()
   for(const raw of [results.baseline,...array(results.challengers,7)]){
    const row=obj(raw),m=model(row.model,registryAt),summary=obj(row.summary)
    if(seen.has(m.id)||!allowed.some(d=>d.id===m.id))fail();seen.add(m.id)
    const complete=stringCount(summary.fold_count,3),requested=stringCount(summary.requested_folds,3)
    if(requested!==3||complete>requested||array(row.folds,3).length!==3)fail()
    const mae=nullable(summary.mae),bias=nullable(summary.signed_bias,true),tail=nullable(summary.tail_abs_error)
    if(complete===0?(mae!==null||bias!==null||tail!==null):(mae===null||bias===null||tail===null))fail()
    scores.push({id:m.id,complete,requested,mae,bias,tail,holdoutMae:holds.get(m.id)??null})
   }
   if(canonical([...seen].sort())!==canonical(allowed.map(d=>d.id).sort())||!holds.has('mean-1')||!holds.has(selected))fail()
   if(e.forecast!==null)forecast(e.forecast,chosen,horizon)
  }
  if(gate.state==='ELIGIBLE'){
   if(!policy||policy.policy.state!=='ACTIVE'||!policyCurrent||e.selection_status!=='CHALLENGER_RECOMMENDED'||selected==='mean-1'||nextDay(through)!==forecastFrom||horizon>Number(policy.policy.config.maximum_horizon_days))fail()
   const admitted=model(gate.selected_model,registryAt),f=obj(gate.forecast)
   if(admitted.id!==selected||canonical(gate.forecast)!==canonical(e.forecast)||count(f.training_count,366)<Number(policy.policy.config.minimum_training_days)||holds.get(selected)==null||scores.filter(x=>x.id==='mean-1'||x.id===selected).some(x=>x.complete!==3))fail()
   forecasts=forecast(gate.forecast,admitted,horizon);if(!forecasts)fail()
  }
 }
 if(gate.state==='BASELINE_REQUIRED'&&(gate.forecast!==null||gate.selected_model!==null))fail()
 const g=obj(v.current_guard);exact(g,['contract_version','state','reason','source_state','history_unchanged','engine_unchanged','policy_unchanged','forecast_origin_current','checked_at','forecast_applied','production_go'])
 if(g.contract_version!=='cp7.native-model-current-guard.v2'||g.forecast_applied!==false||g.production_go!==false||!['ELIGIBLE','BASELINE_REQUIRED'].includes(String(g.state)))fail()
 const checkedAt=instant(g.checked_at),fresh=[g.history_unchanged,g.engine_unchanged,g.policy_unchanged,g.forecast_origin_current].map(bool).every(Boolean)
 const clockValid=micros(checkedAt)>=micros(capturedAt)
 if(g.source_state!==(fresh?'UNCHANGED':'ARCHIVED_STALE')||g.state!==(fresh&&clockValid&&gate.state==='ELIGIBLE'?'ELIGIBLE':'BASELINE_REQUIRED'))fail()
 const expectedReason=!clockValid?'CURRENT_CLOCK_PRECEDES_EVALUATION':!g.history_unchanged?'NATIVE_HISTORY_SOURCE_CHANGED':!g.engine_unchanged?'MODEL_ENGINE_CHANGED':!g.policy_unchanged?'ACTIVATION_POLICY_CHANGED':!g.forecast_origin_current?'MODEL_FORECAST_ORIGIN_NOT_CURRENT':gate.state!=='ELIGIBLE'?gate.reason:'CURRENT_NATIVE_SOURCE_POLICY_ENGINE_AND_DATED_ADMISSION'
 if(g.reason!==expectedReason)fail()
 if(g.forecast_origin_current&&(nextDay(through)!==wibDay(checkedAt)||forecastFrom!==wibDay(checkedAt)))fail()
 text(g.reason)
 const {current_guard:_guard,...immutable}=v;const immutableSignature=canonical(immutable)
 const out:ModelV2Run={runId:uuid(v.run_id),requestId:uuid(v.request_id),actor,query:q,capturedAt,knownAt,registryAt,from,through,sku:text(s.product_sku),name:text(s.product_name),sourceHash,engineHash,policy,selected,mean,scores,forecastFrom,forecasts,admittedAtCapture:gate.state==='ELIGIBLE',eligibleNow:g.state==='ELIGIBLE',reason:g.reason as string,sourceState:g.source_state as ModelV2Run['sourceState'],checkedAt,immutableSignature}
 if(prior&&(prior.immutableSignature!==immutableSignature||prior.actor!==actor||canonical(prior.query)!==canonical(q)))fail()
 return out
}
type Reply={data:unknown;error:unknown}
type Client={rpc(name:typeof modelV2Method,args:{p_query:NativeModelQuery;p_request:string}):PromiseLike<Reply>;rpc(name:'erp_cp7_read_model_evaluation_v2',args:{p_run:string}):PromiseLike<Reply>}
export async function captureModelV2(client:unknown,request:ModelV2Request){const r=parseModelV2Request(request,request.actor),reply=await(client as Client).rpc('erp_cp7_capture_model_evaluation_v2',{p_query:structuredClone(r.query),p_request:r.requestId});if(reply.error)throw reply.error;const out=parseModelV2Run(reply.data,r.query,r.actor);if(out.requestId!==r.requestId)fail();return out}
export async function readModelV2(client:unknown,prior:ModelV2Run){const reply=await(client as Client).rpc('erp_cp7_read_model_evaluation_v2',{p_run:prior.runId});if(reply.error)throw reply.error;return parseModelV2Run(reply.data,prior.query,prior.actor,prior)}
export const modelV2RequestKey=(scope:string)=>'erp.cp7.native-model-request.v2:'+scope
export function readModelV2Request(scope:string,actor:string):{pending:ModelV2Request|null;error:string}{try{const raw=localStorage.getItem(modelV2RequestKey(scope));return{pending:raw===null?null:parseModelV2Request(JSON.parse(raw),actor),error:''}}catch{return{pending:null,error:'Permintaan evaluasi sesuai kebijakan belum dapat dibaca. Pulihkan catatan sebelum membuat evaluasi baru.'}}}
export function persistModelV2Request(scope:string,request:ModelV2Request){const r=parseModelV2Request(request,request.actor),held=readModelV2Request(scope,r.actor);if(held.pending||held.error)throw Error('Periksa permintaan evaluasi sebelumnya terlebih dahulu.');const raw=JSON.stringify(r),key=modelV2RequestKey(scope);localStorage.setItem(key,raw);if(localStorage.getItem(key)!==raw)throw Error('Permintaan belum tercatat di perangkat. Evaluasi belum dikirim.')}
export function clearModelV2Request(scope:string,request:ModelV2Request){const held=readModelV2Request(scope,request.actor);if(held.error||canonical(held.pending)!==canonical(request))throw Error('Permintaan evaluasi tersimpan berubah. Periksa hasil yang sama.');const key=modelV2RequestKey(scope);localStorage.removeItem(key);if(localStorage.getItem(key)!==null)throw Error('Catatan evaluasi belum dapat diselesaikan.')}
