export type NativeModelQuery={history_run_id:string;target_key:string;horizon_days:string}
export type NativeModelRequest={id:string;q:NativeModelQuery}
export type ModelScore={id:string;complete:number;requested:number;mae:string|null;bias:string|null;tail:string|null;holdoutMae:string|null}
export type NativeModelEvaluation={runId:string;requestId:string;historyRunId:string;targetKey:string;sku:string;name:string;from:string;through:string;knownAt:string;registryAt:string;horizon:number;state:'UNCHANGED'|'ARCHIVED_STALE';selection:'BASELINE_RETAINED'|'CHALLENGER_RECOMMENDED';selected:string;reason:string;mean:string|null;scores:ModelScore[];forecasts:string[]|null;revisionCount:number;sourceHash:string}
const fail=():never=>{throw Error('Hasil evaluasi ramalan belum lengkap atau berubah. Periksa kembali sumber ERP.')}
const object=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const text=(v:unknown)=>typeof v==='string'&&v.length>0?v:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const decimal=(v:unknown,signed=false)=>typeof v==='string'&&(signed?/^-?(0|[1-9][0-9]{0,29})(\.[0-9]{1,30})?$/:/^(0|[1-9][0-9]{0,29})(\.[0-9]{1,30})?$/).test(v)?v:fail()
const nullableDecimal=(v:unknown,signed=false)=>v===null?null:decimal(v,signed)
const count=(v:unknown,max=20000)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0&&v<=max?v:fail()
const stringCount=(v:unknown,max=100)=>typeof v==='string'&&/^(0|[1-9][0-9]*)$/.test(v)&&Number(v)<=max?Number(v):fail()
const instant=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(v)&&Number.isFinite(Date.parse(v))?v:fail()
const day=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v?v:fail()
const array=(v:unknown,max:number)=>Array.isArray(v)&&v.length<=max?v:fail()
const ids=['mean-1','naive-1','moving-mean-7-1','ses-half-1','holt-damped-1','seasonal-7-1','sba-half-1','tsb-half-1']
export function parseModelQuery(value:unknown):NativeModelQuery{
 const v=object(value);if(Object.keys(v).sort().join('|')!=='history_run_id|horizon_days|target_key')fail()
 const target=text(v.target_key).split(':');if(target.length!==2)fail();uuid(target[0]);uuid(target[1]);const h=stringCount(v.horizon_days,90);if(h<1)fail()
 return{history_run_id:uuid(v.history_run_id),target_key:target.join(':'),horizon_days:v.horizon_days as string}
}
export function parseNativeModelEvaluation(value:unknown,q:NativeModelQuery,actor:string):NativeModelEvaluation{
 const v=object(value),h=count(v.horizon_days,90),from=day(v.from_date),through=day(v.through_date),known=instant(v.known_as_of),registry=instant(v.registry_registered_at)
 if(v.contract_version!=='cp7.native-model-result.v1'||v.actor_scope_id!==actor||v.history_run_id!==q.history_run_id||v.target_key!==q.target_key||v.size_id!==q.target_key.split(':')[1]||String(h)!==q.horizon_days
  ||v.registry_id!=='cp7.native-model-policy.v1'||v.knowledge_basis!=='ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES'||v.no_retrospective_availability_backfill!==true
  ||v.automatic_activation!==false||v.apply_allowed!==false||v.production_go!==false||v.policy_meaning!=='TECHNICAL_PROPOSAL_NOT_OWNER_SERVICE_TARGET')fail()
 if(from>through||(Date.parse(through)-Date.parse(from))/86400000>365||Date.parse(through+'T17:00:00Z')>Date.parse(known))fail()
 if(v.source_state!=='UNCHANGED'&&v.source_state!=='ARCHIVED_STALE'||v.selection_status!=='BASELINE_RETAINED'&&v.selection_status!=='CHALLENGER_RECOMMENDED')fail()
 const selected=text(v.selected_model_id);if(!ids.includes(selected))fail();const hash=text(v.source_hash);if(!/^[0-9a-f]{64}$/.test(hash))fail()
 const scores:ModelScore[]=[],seen=new Set<string>();let forecasts:string[]|null=null
 if(v.evaluation!==null){
  const e=object(v.evaluation),holdout=object(e.holdout),definition=object(holdout.definition)
  if(e.contract_version!=='cp7.model-evaluation-result.v1'||e.snapshot_id!==hash||e.scope_id!=='OWN_NATIVE_CAPTURE_HISTORY'||e.target_key!==q.target_key||e.size_id!==v.size_id||e.known_as_of!==known
   ||e.selection_status!==v.selection_status||e.selected_model_id!==selected||e.selection_basis!=='COMPLETE_PAIRED_CHRONOLOGICAL_VALIDATION_ONLY'||e.automatic_activation!==false||holdout.used_for_selection!==false
   ||definition.horizon!==q.horizon_days||day(definition.origin)>through)fail()
  const holds=new Map<string,string|null>();for(const raw of array(holdout.results,2)){const x=object(raw),id=text(x.model_id);if(holds.has(id)||!ids.includes(id))fail();holds.set(id,x.score===null?null:nullableDecimal(object(x.score).mae))}
  for(const raw of [e.baseline,...array(e.challengers,7)]){
   const r=object(raw),model=object(r.model),s=object(r.summary),id=text(model.id);if(seen.has(id)||!ids.includes(id)||instant(model.registered_at)!==registry)fail();seen.add(id)
   const complete=stringCount(s.fold_count,3),requested=stringCount(s.requested_folds,3);if(requested!==3||complete>requested||array(r.folds,3).length!==3)fail()
   const mae=nullableDecimal(s.mae),bias=nullableDecimal(s.signed_bias,true),tail=nullableDecimal(s.tail_abs_error);if(complete===0?(mae!==null||bias!==null||tail!==null):(mae===null||bias===null||tail===null))fail()
   scores.push({id,complete,requested,mae,bias,tail,holdoutMae:holds.get(id)??null})
  }
  if(seen.size!==8||!holds.has('mean-1')||!holds.has(selected))fail()
  if(v.forecast!==null){const f=object(v.forecast);if(f.status==='ELIGIBLE'){forecasts=array(f.forecasts,90).map(x=>decimal(x));if(forecasts.length!==h)fail()}else if(f.status!=='INELIGIBLE')fail()}
 }else if(v.forecast!==null||v.selection_status!=='BASELINE_RETAINED'||selected!=='mean-1')fail()
 return{runId:uuid(v.run_id),requestId:uuid(v.request_id),historyRunId:q.history_run_id,targetKey:q.target_key,sku:text(v.product_sku),name:text(v.product_name),from,through,knownAt:known,registryAt:registry,horizon:h,state:v.source_state as NativeModelEvaluation['state'],selection:v.selection_status as NativeModelEvaluation['selection'],selected,reason:text(v.reason),mean:nullableDecimal(v.fallback_daily_mean),scores,forecasts,revisionCount:count(v.series_revision_count),sourceHash:hash}
}
export const modelRequestKey=(scope:string)=>'erp.cp7.native-model-request.v1:'+scope
export function readModelRequest(scope:string):{pending:NativeModelRequest|null;error:string}{
 try{const raw=localStorage.getItem(modelRequestKey(scope));if(raw===null)return{pending:null,error:''};const v=object(JSON.parse(raw));if(Object.keys(v).sort().join('|')!=='id|q')fail();return{pending:{id:uuid(v.id),q:parseModelQuery(v.q)},error:''}}
 catch{return{pending:null,error:'Permintaan evaluasi tersimpan belum bisa dibaca. Pulihkan penyimpanan sebelum membuat evaluasi baru.'}}
}
export function persistModelRequest(scope:string,r:NativeModelRequest){const held=readModelRequest(scope);if(held.pending||held.error)throw Error('Selesaikan evaluasi tersimpan terlebih dahulu.');parseModelQuery(r.q);uuid(r.id);const raw=JSON.stringify(r);localStorage.setItem(modelRequestKey(scope),raw);if(localStorage.getItem(modelRequestKey(scope))!==raw)throw Error('Permintaan evaluasi belum tersimpan.')}
export function clearModelRequest(scope:string,id:string){const held=readModelRequest(scope);if(held.error||held.pending?.id!==id)throw Error('Permintaan evaluasi tersimpan berubah.');localStorage.removeItem(modelRequestKey(scope));if(localStorage.getItem(modelRequestKey(scope))!==null)throw Error('Permintaan evaluasi belum bisa diselesaikan.')}
