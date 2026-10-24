import {stagedInstant} from './nativeAnalysisPages'
import {sameBoundedReference} from './nativeBoundedQuantity'
import type {AnalogReadContext,AnalogCandidates} from './nativeProductAnalog'

type ObjectValue=Record<string,unknown>
export type AnalogChoiceEvidence={sourceKey:string;targetProductId:string;sourceProductId:string;scale:string;totalPcs:string;days:string;profileId:string;profileRevision:string;capturedAt:string;sourceRequest:string;sourceRun:string}
export type AnalogChoice={targetKey:string;id:string|null;revision:string;state:'UNREVIEWED'|'CONFIRMED_ASSUMPTION'|'CLEARED';action:'CONFIRM'|'CLEAR'|null;requestId:string|null;actor:string|null;recordedAt:string|null;reason:string|null;evidence:AnalogChoiceEvidence|null}
export type AnalogChoiceWorkspace={actor:string;accessEpoch:string;choice:AnalogChoice}
export type AnalogChoicePayload={contract_version:'cp7.product-analog-choice-command.v1';source_request:string|null;source_hash:string|null;access_epoch:string;target_key:string;source_key:string|null;scale_factor:string|null;reason:string;reviewed:true;expected_revision:string;action:'CONFIRM'|'CLEAR'}
type ChoiceReview={context:AnalogReadContext;sourceKey:string;producerHash:string;historyHash:string;sourceHash:string;profileId:string;profileRevision:string;minimumDays:string;availableDays:string}
export type PreparedAnalogChoice={requestId:string;actor:string;payload:AnalogChoicePayload;review:ChoiceReview|null}
type Reply={data:unknown;error:unknown}
type ChoiceClient={rpc(name:'erp_cp7_get_product_analog_choices_v1',args:{p_targets:string[]}):PromiseLike<Reply>;rpc(name:'erp_cp7_save_product_analog_choice_v1',args:{p_payload:AnalogChoicePayload;p_request:string}):PromiseLike<Reply>}
function fail():never{throw Error('Pilihan pembanding belum dapat dipastikan. Baca ulang pilihan tersimpan dan acuannya.')}
const obj=(v:unknown):ObjectValue=>v&&typeof v==='object'&&!Array.isArray(v)?v as ObjectValue:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const pcs=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,29})$/.test(v)?v:fail()
const revision=(v:unknown)=>{const n=pcs(v);if(BigInt(n)>9223372036854775807n)fail();return n}
const target=(v:unknown)=>{if(typeof v!=='string')return fail();const parts=v.split(':');if(parts.length!==2)fail();uuid(parts[0]);uuid(parts[1]);return v}
const scale=(v:unknown)=>{if(typeof v!=='string'||!/^(0|[1-9][0-9]{0,29})(\.[0-9]{1,12})?$/.test(v)||!/[1-9]/.test(v))return fail();return v}
const reason=(v:unknown)=>typeof v==='string'&&v.trim().length>0&&Array.from(v).length<=1000?v:fail()
const decimalUnits=(v:string)=>{const[a,b='']=scale(v).split('.');return BigInt(a+b.padEnd(12,'0'))}
const instantMicros=(v:string)=>{const m=stagedInstant(v).replace(/\+00:00$/,'Z').match(/^(.{19})(?:\.(\d{1,6}))?Z$/);if(!m) return fail();return BigInt(Date.parse(m[1]+'Z'))*1000n+BigInt((m[2]??'').padEnd(6,'0'))}
const queryMatches=(value:unknown,c:AnalogReadContext)=>{const q=obj(value);if(Object.keys(q).length!==3||q.from_date!==c.query.from_date||q.through_date!==c.query.through_date||q.group_mode!==c.query.group_mode)fail()}
function evidence(value:unknown,targetKey:string):AnalogChoiceEvidence{
 const e=obj(value),p=obj(e.target_product),s=obj(e.source_product),sourceKey=target(e.source_key)
 if(e.contract_version!=='cp7.product-analog-material.v1'||e.target_key!==targetKey||e.reviewed!==true||sourceKey===targetKey)fail()
 if(uuid(p.root_id)+':'+uuid(p.size_id)!==targetKey||uuid(s.root_id)+':'+uuid(s.size_id)!==sourceKey||p.size_id!==s.size_id)fail()
 const totalPcs=pcs(e.available_total_pcs),days=pcs(e.available_days),minimum=pcs(e.minimum_available_days)
 if(BigInt(days)<BigInt(minimum)||BigInt(minimum)<1n||BigInt(days)>3661n)fail()
 hash(e.history_hash);hash(e.source_hash);hash(e.analysis_source_hash);hash(e.identity_hash);hash(e.producer_hash)
 const q=obj(e.query);if(typeof q.from_date!=='string'||typeof q.through_date!=='string'||!['AS_SOLD','RESTATED'].includes(String(q.group_mode)))fail()
 if(!Array.isArray(e.refs)||e.refs.length<1)fail()
 for(const raw of e.refs){const r=obj(raw);if(typeof r.kind!=='string'||!r.kind||typeof r.id!=='string'||!r.id)fail();pcs(r.revision)}
 const profileRevision=revision(e.profile_revision);if(profileRevision==='0')fail()
 return{sourceKey,targetProductId:uuid(p.id),sourceProductId:uuid(s.id),scale:scale(e.scale_factor),totalPcs,days,profileId:uuid(e.profile_id),profileRevision,capturedAt:stagedInstant(e.captured_at),sourceRequest:uuid(e.source_request),sourceRun:uuid(e.source_run)}
}
function choice(value:unknown,targetKey:string):AnalogChoice{
 const r=obj(value);if(r.target_key!==targetKey)fail()
 const rev=revision(r.revision)
 if(r.state==='UNREVIEWED'){
  if(rev!=='0'||['choice_id','action','evidence','reason','actor_scope_id','recorded_at','request_id'].some(k=>r[k]!==null))fail()
  return{targetKey,id:null,revision:rev,state:'UNREVIEWED',action:null,requestId:null,actor:null,recordedAt:null,reason:null,evidence:null}
 }
 if(rev==='0'||r.state!=='CLEARED'&&r.state!=='CONFIRMED_ASSUMPTION')fail()
 const cleared=r.state==='CLEARED'
 if(r.action!==(cleared?'CLEAR':'CONFIRM')||cleared&&r.evidence!==null)fail()
 return{targetKey,id:uuid(r.choice_id),revision:rev,state:r.state as 'CLEARED'|'CONFIRMED_ASSUMPTION',action:cleared?'CLEAR':'CONFIRM',requestId:uuid(r.request_id),actor:uuid(r.actor_scope_id),recordedAt:stagedInstant(r.recorded_at),reason:reason(r.reason),evidence:cleared?null:evidence(r.evidence,targetKey)}
}
export function parseAnalogChoiceWorkspace(value:unknown,actor:string,targetKey:string):AnalogChoiceWorkspace{
 const e=obj(value);uuid(actor);target(targetKey)
 if(e.contract_version!=='cp7.product-analog-choices.v1'||e.actor_scope_id!==actor||e.forecast_applied!==false||e.production_go!==false||!Array.isArray(e.rows)||e.rows.length!==1)fail()
 return{actor,accessEpoch:hash(e.access_epoch),choice:choice(e.rows[0],targetKey)}
}
export function prepareAnalogConfirmation(context:AnalogReadContext,candidates:AnalogCandidates,workspace:AnalogChoiceWorkspace,sourceKey:string,scaleFactor:string,explanation:string,reviewed:boolean,requestId:string):PreparedAnalogChoice{
 if(!reviewed||workspace.actor!==context.actor||workspace.accessEpoch!==context.accessEpoch||workspace.choice.targetKey!==context.targetKey||!candidates.profileId||!candidates.profileRevision||!candidates.rows.some(r=>r.key===sourceKey)||revision(workspace.choice.revision)==='9223372036854775807')fail()
 const payload:AnalogChoicePayload={contract_version:'cp7.product-analog-choice-command.v1',source_request:context.requestId,source_hash:context.reference.sourceHash,access_epoch:context.accessEpoch,target_key:context.targetKey,source_key:target(sourceKey),scale_factor:scale(scaleFactor),reason:reason(explanation.trim()),reviewed:true,expected_revision:workspace.choice.revision,action:'CONFIRM'}
 const row=candidates.rows.find(r=>r.key===sourceKey)!
 return parsePreparedAnalogChoice({requestId:uuid(requestId),actor:uuid(context.actor),payload,review:{context:structuredClone(context),sourceKey,producerHash:candidates.producerHash,historyHash:candidates.historyHash,sourceHash:candidates.sourceHash,profileId:candidates.profileId,profileRevision:candidates.profileRevision,minimumDays:candidates.minimumDays,availableDays:String(row.availableDays)}},context.actor,context.targetKey)
}
export function prepareAnalogClear(workspace:AnalogChoiceWorkspace,explanation:string,reviewed:boolean,requestId:string):PreparedAnalogChoice{
 if(!reviewed||workspace.choice.revision==='0'||revision(workspace.choice.revision)==='9223372036854775807')fail()
 return{requestId:uuid(requestId),actor:uuid(workspace.actor),review:null,payload:{contract_version:'cp7.product-analog-choice-command.v1',source_request:null,source_hash:null,access_epoch:hash(workspace.accessEpoch),target_key:target(workspace.choice.targetKey),source_key:null,scale_factor:null,reason:reason(explanation.trim()),reviewed:true,expected_revision:workspace.choice.revision,action:'CLEAR'}}
}
export function parseAnalogChoiceOutcome(value:unknown,command:PreparedAnalogChoice):AnalogChoice{
 const e=obj(value),p=command.payload
 if(e.contract_version!=='cp7.product-analog-choice-outcome.v1'||e.forecast_applied!==false||e.production_go!==false||e.request_id!==command.requestId||e.actor_scope_id!==command.actor||e.action!==p.action||e.reason!==p.reason)fail()
 const parsed=choice(e,p.target_key)
 if(BigInt(parsed.revision)!==BigInt(p.expected_revision)+1n)fail()
 if(p.action==='CONFIRM'){
  const proof=command.review;if(!proof||!parsed.evidence)fail()
  const {context,sourceKey}=proof,evidenceValue=obj(e.evidence)
  if(parsed.evidence.sourceKey!==sourceKey||parsed.evidence.sourceRequest!==context.requestId||parsed.evidence.sourceRun!==context.runId||evidenceValue.analysis_source_hash!==context.reference.sourceHash||evidenceValue.identity_hash!==context.identityHash||evidenceValue.producer_hash!==proof.producerHash||evidenceValue.history_hash!==proof.historyHash||evidenceValue.source_hash!==proof.sourceHash||parsed.evidence.profileId!==proof.profileId||parsed.evidence.profileRevision!==proof.profileRevision||parsed.evidence.days!==proof.availableDays||decimalUnits(parsed.evidence.scale)!==decimalUnits(p.scale_factor!))fail()
  if(!sameBoundedReference({capturedAt:parsed.evidence.capturedAt,sourceHash:context.reference.sourceHash},context.reference))fail()
  if(evidenceValue.minimum_available_days!==proof.minimumDays||instantMicros(parsed.recordedAt!)<instantMicros(context.reference.capturedAt))fail()
  queryMatches(evidenceValue.query,context)
 }else if(command.review!==null||parsed.evidence!==null)fail()
 return parsed
}
export async function readProductAnalogChoice(client:unknown,actor:string,targetKey:string){
 const reply=await(client as ChoiceClient).rpc('erp_cp7_get_product_analog_choices_v1',{p_targets:[target(targetKey)]})
 if(reply.error)throw reply.error
 return parseAnalogChoiceWorkspace(reply.data,actor,targetKey)
}
export async function saveProductAnalogChoice(client:unknown,command:PreparedAnalogChoice){
 const reply=await(client as ChoiceClient).rpc('erp_cp7_save_product_analog_choice_v1',{p_payload:structuredClone(command.payload),p_request:command.requestId})
 if(reply.error)throw reply.error
 return parseAnalogChoiceOutcome(reply.data,command)
}

const exact=(v:ObjectValue,keys:string[])=>{if(Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))fail()}
const day=(v:unknown)=>{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v)||new Date(v+'T00:00:00Z').toISOString().slice(0,10)!==v)fail();return v}
// Stored recovery is a typed command and its original review, never a new
// request reconstructed from the currently open snapshot or form.
export function parsePreparedAnalogChoice(value:unknown,actor:string,targetKey:string):PreparedAnalogChoice{
 const r=obj(value),p=obj(r.payload);exact(r,['requestId','actor','payload','review'])
 exact(p,['contract_version','source_request','source_hash','access_epoch','target_key','source_key','scale_factor','reason','reviewed','expected_revision','action'])
 if(uuid(r.actor)!==uuid(actor)||p.target_key!==target(targetKey)||p.contract_version!=='cp7.product-analog-choice-command.v1'||p.reviewed!==true||!['CONFIRM','CLEAR'].includes(String(p.action))||revision(p.expected_revision)==='9223372036854775807'||reason(p.reason).trim()!==p.reason)fail()
 hash(p.access_epoch);uuid(r.requestId)
 if(p.action==='CLEAR'){
  if(r.review!==null||p.expected_revision==='0'||['source_request','source_hash','source_key','scale_factor'].some(k=>p[k]!==null))fail()
 }else{
  uuid(p.source_request);hash(p.source_hash);scale(p.scale_factor)
  if(target(p.source_key)===targetKey||String(p.source_key).split(':')[1]!==targetKey.split(':')[1])fail()
  const v=obj(r.review),c=obj(v.context),q=obj(c.query),ref=obj(c.reference)
  exact(v,['context','sourceKey','producerHash','historyHash','sourceHash','profileId','profileRevision','minimumDays','availableDays'])
  exact(c,['actor','requestId','runId','targetKey','query','reference','identityHash','accessEpoch']);exact(q,['from_date','through_date','group_mode']);exact(ref,['capturedAt','sourceHash'])
  if(c.actor!==actor||c.targetKey!==targetKey||c.requestId!==p.source_request||c.accessEpoch!==p.access_epoch||ref.sourceHash!==p.source_hash||v.sourceKey!==p.source_key)fail()
  uuid(c.runId);hash(c.identityHash);stagedInstant(ref.capturedAt)
  const from=day(q.from_date),through=day(q.through_date),days=(Date.parse(through)-Date.parse(from))/86400000+1
  if(days<1||days>3661||!['AS_SOLD','RESTATED'].includes(String(q.group_mode)))fail()
  for(const k of ['producerHash','historyHash','sourceHash'])hash(v[k])
  uuid(v.profileId);if(revision(v.profileRevision)==='0'||BigInt(pcs(v.minimumDays))<1n||BigInt(pcs(v.availableDays))<BigInt(String(v.minimumDays))||BigInt(String(v.availableDays))>BigInt(days))fail()
 }
 return structuredClone(r)as PreparedAnalogChoice
}
export const analogChoiceRequestKey=(scope:string,targetKey:string)=>'erp.cp7.analog-choice.v1:'+scope+':'+targetKey
export function readAnalogChoiceRequest(scope:string,actor:string,targetKey:string):{pending:PreparedAnalogChoice|null;error:string}{
 try{const raw=localStorage.getItem(analogChoiceRequestKey(scope,targetKey));return{pending:raw===null?null:parsePreparedAnalogChoice(JSON.parse(raw),actor,targetKey),error:''}}
 catch{return{pending:null,error:'Catatan konfirmasi belum bisa dibaca. Pulihkan catatan sebelum menyimpan lagi.'}}
}
export function persistAnalogChoiceRequest(scope:string,r:PreparedAnalogChoice){
 const held=readAnalogChoiceRequest(scope,r.actor,r.payload.target_key);if(held.error||held.pending)throw Error('Periksa hasil konfirmasi tersimpan terlebih dahulu.')
 parsePreparedAnalogChoice(r,r.actor,r.payload.target_key)
 const key=analogChoiceRequestKey(scope,r.payload.target_key),raw=JSON.stringify(r);localStorage.setItem(key,raw)
 if(localStorage.getItem(key)!==raw)throw Error('Konfirmasi belum tercatat di perangkat. Penyimpanan belum dikirim.')
}
export function clearAnalogChoiceRequest(scope:string,r:PreparedAnalogChoice){
 const held=readAnalogChoiceRequest(scope,r.actor,r.payload.target_key)
 if(held.error||JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Catatan konfirmasi berubah. Periksa permintaan yang sama.')
 const key=analogChoiceRequestKey(scope,r.payload.target_key);localStorage.removeItem(key)
 if(localStorage.getItem(key)!==null)throw Error('Catatan konfirmasi belum dapat diselesaikan.')
}
