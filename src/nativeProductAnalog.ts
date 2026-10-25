import type {NativeDemandQuery} from './nativeDemandHistory'
import {parseStagedReference,stagedInstant,type StagedAnalysis,type StagedReference} from './nativeAnalysisPages'
import {sameBoundedReference} from './nativeBoundedQuantity'
import {parseTargetDemand,type TargetDemand} from './nativeTargetDemand'

export type AnalogReadContext={actor:string;requestId:string;runId:string;targetKey:string;query:NativeDemandQuery;reference:StagedReference;identityHash:string;accessEpoch:string;sourceMethod?:'FROZEN_V2'}
export type AnalogCandidate={key:string;rootId:string;sizeId:string;sku:string;name:string;active:boolean;availableDays:number;stockoutDays:number;unknownDays:number;mean:string;reasons:string[];suggested:boolean;manualReasonRequired:boolean}
export type AnalogCandidates={state:'PLANNING_CONFIG_REQUIRED'|'INSUFFICIENT_REVIEWABLE_HISTORY'|'MANUAL_CHOICE_REQUIRES_SIMILARITY_REASON'|'REVIEW_REQUIRED';total:number;suggested:number;offset:number;limit:50;minimumDays:string|null;profileId:string|null;profileRevision:string|null;producerHash:string;historyHash:string;sourceHash:string;rows:AnalogCandidate[];supportsConsumer?:boolean;targetDemand?:TargetDemand;sourceMethod?:'FROZEN_V2'}
type Reply={data:unknown;error:unknown}
type AnalogClient={rpc(name:'erp_cp7_read_product_analog_candidates_v1',args:{p_request:string;p_target:string;p_offset:number;p_limit:50;p_access:string}):PromiseLike<Reply>}
const fail=():never=>{throw Error('Data produk pembanding belum lengkap atau acuannya berubah. Buka kembali perhitungan tersimpan.')}
const obj=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const text=(v:unknown)=>typeof v==='string'&&v.length>0?v:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const boolean=(v:unknown)=>typeof v==='boolean'?v:fail()
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const array=(v:unknown,max:number):unknown[]=>Array.isArray(v)&&v.length<=max?v:fail()
const parsedState=(v:unknown):AnalogCandidates['state']=>v==='PLANNING_CONFIG_REQUIRED'||v==='INSUFFICIENT_REVIEWABLE_HISTORY'||v==='MANUAL_CHOICE_REQUIRES_SIMILARITY_REASON'||v==='REVIEW_REQUIRED'?v:fail()
const count=(v:unknown)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0&&v<=5000?v:fail()
const pcs=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,29})$/.test(v)?v:fail()
const mean=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,29})(\.[0-9]{1,30})?$/.test(v)?v:fail()
const sameQuery=(v:unknown,q:NativeDemandQuery)=>{const x=obj(v);if(Object.keys(x).length!==3||x.from_date!==q.from_date||x.through_date!==q.through_date||x.group_mode!==q.group_mode)fail()}
const noSelection=(v:Record<string,unknown>,forecast=true)=>{if(v.selected!==false||v.reviewed!==false||forecast&&v.forecast_applied!==false)fail()}
export function analogReadContext(staged:StagedAnalysis,actor:string,targetKey:string):AnalogReadContext{
 const[root,size,...rest]=targetKey.split(':');uuid(root);uuid(size);if(rest.length)fail()
 return{actor:uuid(actor),requestId:staged.set.requestId,runId:staged.set.runId,targetKey,query:{...staged.header.query},reference:{...staged.set.reference},identityHash:staged.set.identityHash,accessEpoch:staged.set.accessEpoch}
}
export function parseAnalogCandidates(value:unknown,context:AnalogReadContext,offset:number,previous?:AnalogCandidates):AnalogCandidates{
 const e=obj(value),r=obj(e.result)
 const frozen=e.contract_version==='cp7.product-analog-candidates-read.v3'
 if(frozen){
  if(context.sourceMethod!=='FROZEN_V2'||e.bounded_request_contract!=='cp7.bounded-analysis-request.v2'||e.bounded_reference_contract!=='cp7.bounded-analysis-reference.v2')fail()
 }else if(context.sourceMethod!==undefined||Object.hasOwn(e,'bounded_request_contract')||Object.hasOwn(e,'bounded_reference_contract'))fail()
 const sourceMethod=frozen?'FROZEN_V2':undefined
 const supportsConsumer=frozen||e.contract_version==='cp7.product-analog-candidates-read.v2'
 if(!supportsConsumer&&e.contract_version!=='cp7.product-analog-candidates-read.v1'||e.source_state!=='CAPTURED_NOT_CHECKED'||e.captured_source_only!==true||e.production_go!==false)fail()
 if(supportsConsumer?e.consumer_capability!=='REVIEWED_ANALOG_FOR_FRESH_CAPTURES':Object.hasOwn(e,'target_demand')||Object.hasOwn(e,'consumer_capability'))fail()
 const targetDemand=supportsConsumer?parseTargetDemand(e.target_demand,{targetKey:context.targetKey,capturedAt:context.reference.capturedAt,query:context.query}):undefined
 if(previous&&(previous.sourceMethod!==sourceMethod||Boolean(previous.supportsConsumer)!==supportsConsumer||JSON.stringify(previous.targetDemand)!==JSON.stringify(targetDemand)))fail()
 noSelection(e)
 if(uuid(e.actor_scope_id)!==context.actor||uuid(e.request_id)!==context.requestId||uuid(e.run_id)!==context.runId||hash(e.identity_hash)!==context.identityHash||hash(e.access_epoch)!==context.accessEpoch)fail()
 if(!sameBoundedReference(parseStagedReference(e.reference),context.reference))fail()
 sameQuery(e.query,context.query);sameQuery(r.query,context.query)
 if(r.contract_version!=='cp7.product-analog-candidates.prototype.v1'||r.target_key!==context.targetKey||r.production_go!==false)fail()
 noSelection(r)
 if(!sameBoundedReference({capturedAt:stagedInstant(r.source_captured_at),sourceHash:context.reference.sourceHash},context.reference))fail()
 const producerHash=hash(e.producer_hash),historyHash=hash(r.history_hash),sourceHash=hash(r.source_hash)
 const total=count(r.total),suggested=count(r.suggested),candidateRows=array(r.candidates,50)
 if(suggested>total||r.offset!==offset||!Number.isSafeInteger(offset)||offset<0||offset>5000||r.limit!==50||candidateRows.length!==Math.min(50,Math.max(0,total-offset)))fail()
 const state=parsedState(r.state)
 const needsProfile=state==='PLANNING_CONFIG_REQUIRED',minimumDays=needsProfile?null:pcs(r.minimum_available_days),profileId=needsProfile?null:uuid(r.profile_id),profileRevision=needsProfile?null:pcs(r.profile_revision)
 if(needsProfile&&(total!==0||suggested!==0)||!needsProfile&&(!minimumDays||BigInt(minimumDays)<1n)||state==='INSUFFICIENT_REVIEWABLE_HISTORY'&&total!==0||state==='MANUAL_CHOICE_REQUIRES_SIMILARITY_REASON'&&(total===0||suggested!==0)||state==='REVIEW_REQUIRED'&&suggested===0)fail()
 if(previous&&(previous.producerHash!==producerHash||previous.historyHash!==historyHash||previous.sourceHash!==sourceHash||previous.total!==total||previous.suggested!==suggested||previous.state!==state||previous.minimumDays!==minimumDays||previous.profileId!==profileId||previous.profileRevision!==profileRevision))fail()
 const days=(Date.parse(context.query.through_date+'T00:00:00Z')-Date.parse(context.query.from_date+'T00:00:00Z'))/86400000+1,seen=new Set<string>()
 const rows:AnalogCandidate[]=candidateRows.map(raw=>{
  const x=obj(raw),key=text(x.target_key),root=uuid(x.root_id),size=uuid(x.size_id)
  if(key!==root+':'+size||size!==context.targetKey.split(':')[1]||key===context.targetKey||seen.has(key)||typeof x.is_active!=='boolean')fail();seen.add(key)
  noSelection(x,false)
  const availableDays=count(x.available_days),stockoutDays=count(x.stockout_days),unknownDays=count(x.unknown_days)
  if(availableDays+stockoutDays+unknownDays!==days||!minimumDays||BigInt(availableDays)<BigInt(minimumDays))fail()
  const reasons=array(x.reasons,3).map(text),allowed=['SAME_PHYSICAL_SIZE','SAME_CAPTURED_MODEL','SAME_CAPTURED_BRAND']
  if(reasons.length===0||reasons[0]!=='SAME_PHYSICAL_SIZE'||new Set(reasons).size!==reasons.length||reasons.some(v=>!allowed.includes(v)))fail()
  const isSuggested=reasons.includes('SAME_CAPTURED_MODEL')||reasons.includes('SAME_CAPTURED_BRAND')
  if(x.suggested!==isSuggested||x.manual_similarity_reason_required!==!isSuggested)fail()
  const refs=array(x.refs,50000);if(refs.length===0)fail()
  for(const rawRef of refs){const ref=obj(rawRef);text(ref.kind);text(ref.id);pcs(ref.revision)}
  return{key,rootId:root,sizeId:size,sku:text(x.sku),name:text(x.product_name),active:boolean(x.is_active),availableDays,stockoutDays,unknownDays,mean:mean(x.observed_available_daily_mean),reasons,suggested:isSuggested,manualReasonRequired:!isSuggested}
 })
 return{state,total,suggested,offset,limit:50,minimumDays,profileId,profileRevision,producerHash,historyHash,sourceHash,rows,supportsConsumer,targetDemand,...(sourceMethod?{sourceMethod}:{})}
}
export async function readProductAnalogCandidates(client:unknown,context:AnalogReadContext,offset=0,previous?:AnalogCandidates){
 if(context.sourceMethod!==undefined||!Number.isSafeInteger(offset)||offset<0||offset>5000)fail()
 const reply=await(client as AnalogClient).rpc('erp_cp7_read_product_analog_candidates_v1',{p_request:context.requestId,p_target:context.targetKey,p_offset:offset,p_limit:50,p_access:context.accessEpoch})
 if(reply.error)throw reply.error
 return parseAnalogCandidates(reply.data,context,offset,previous)
}
