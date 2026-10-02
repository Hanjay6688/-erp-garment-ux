import {parseCuttingInputWorkspace, type CuttingInputWorkspace} from './nativeCuttingInputs'

export type ObservationPayload = {group_id:string; expected_group_version:string|null; expected_input_version:string|null}
export type ModelPayload = {action:'CHECK'; group_id:string; roll_id:string; expected_group_version:string; expected_input_version:string; policy_id:string}
export type PolicyPayload = Omit<ModelPayload, 'action'|'policy_id'> & {action:'POLICY'; expected_policy_id:string|null; coverage:string; train_batches:string; calibration_batches:string; holdout_batches:string; explicit_review:true}
export type LearningIntent = {id:string; kind:'OBSERVATION'; payload:ObservationPayload} | {id:string; kind:'MODEL'; payload:ModelPayload|PolicyPayload}
type Feature = NonNullable<CuttingInputWorkspace['record']>['values']['rolls'][number]
export type CuttingPolicy = {id:string; actor_scope_id:string; request_id:string; known_at:string; context:unknown; coverage:string; train_batches:string; calibration_batches:string; holdout_batches:string; previous_id:string|null}
export type ModelWorkspace = {actor:string; groupId:string; rollId:string; input:CuttingInputWorkspace; feature:Feature|null; policy:CuttingPolicy|null}
export type FoldRow = {slice_key:string; batch_key:string; revision_key:string; physical_at:string; known_at:string; consumed:string; rate:string; width_cm:string|null}
export type Assessment = {status:string; reason:string; basis:string|null; interval:null|{lower_pcs:string; center_pcs:string; upper_pcs:string; calibration_batches:string; coverage_target:string; unit:'PCS'}; folds:{train:FoldRow[]; calibration:FoldRow[]; holdout:FoldRow[]}}
export type Observation = {id:string; knownAt:string; records:{id:string; valid:boolean; consumed:string|null; pcs:string|null; unit:string|null}[]; exclusions:{id:string; reason:string}[]}
export type LearningReply = {committed:boolean; current:ModelWorkspace|null; assessment:Assessment|null; observation:Observation|null; currentOriginal:boolean}

const fail = ():never => {throw Error('Catatan hasil potong tidak lengkap atau tidak cocok. Muat ulang sumber.')}
const object = (v:unknown) => v && typeof v==='object' && !Array.isArray(v) ? v as Record<string,unknown> : fail()
const closed = (v:unknown, fields:string[]) => {const r=object(v); if(Object.keys(r).length!==fields.length || fields.some(k=>!(k in r))) fail(); return r}
const text = (v:unknown) => typeof v==='string' && v.length>0 && v.length<=200 ? v : fail()
const id = (v:unknown) => typeof v==='string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(v) ? v : fail()
const version = (v:unknown) => typeof v==='string' && /^[1-9][0-9]{0,18}$/.test(v) && BigInt(v)<=9223372036854775807n ? v : fail()
const decimal = (v:unknown) => typeof v==='string' && v.length<=200 && /^[0-9]+(\.[0-9]+)?$/.test(v) ? v : fail()
const positive = (v:unknown) => {const n=decimal(v); if(!/[1-9]/.test(n)) fail(); return n}
const boolean = (v:unknown) => typeof v==='boolean' ? v : fail()
const nullableId = (v:unknown) => v===null ? null : id(v)
const array = (v:unknown, max=20000) => Array.isArray(v) && v.length<=max ? v as unknown[] : fail()
const flags = (v:Record<string,unknown>) => {for(const key of ['business_write','automatic_activation','production_go']) if(v[key]!==false) fail()}
const time = (v:unknown) => {const s=text(v); if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s))) fail(); return s}
const ticks = (v:string) => BigInt(Date.parse(time(v)))*1000n+BigInt((/\.(\d{1,6})/.exec(v)?.[1]??'').padEnd(6,'0').slice(3))
const canonical = (v:unknown):string => v && typeof v==='object' ? Array.isArray(v) ? '['+v.map(canonical).join(',')+']' : '{'+Object.entries(v).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>JSON.stringify(k)+':'+canonical(x)).join(',')+'}' : JSON.stringify(v)
const same = (a:unknown,b:unknown) => canonical(a)===canonical(b)
const fraction = (v:string) => {const [whole,part='']=decimal(v).split('.'); return {n:BigInt(whole+part),d:10n**BigInt(part.length)}}
const compare = (a:string,b:string) => {const x=fraction(a),y=fraction(b);return x.n*y.d-y.n*x.d}

function policy(raw:unknown, actor:string):CuttingPolicy {
  const p=closed(raw,['id','actor_scope_id','request_id','known_at','context','coverage','train_batches','calibration_batches','holdout_batches','previous_id','policy_kind','automatic_activation'])
  if(p.actor_scope_id!==actor || p.policy_kind!=='EXPLICIT_PROSPECTIVE_PROPOSAL_NOT_FACTORY_GUARANTEE' || p.automatic_activation!==false) fail()
  object(p.context)
  const result={id:id(p.id),actor_scope_id:id(p.actor_scope_id),request_id:id(p.request_id),known_at:time(p.known_at),context:p.context,coverage:decimal(p.coverage),train_batches:version(p.train_batches),calibration_batches:version(p.calibration_batches),holdout_batches:version(p.holdout_batches),previous_id:nullableId(p.previous_id)}
  validatePolicyNumbers(result)
  return result
}
function validatePolicyNumbers(p:{coverage:string;train_batches:string;calibration_batches:string;holdout_batches:string}) {
  const c=fraction(p.coverage), counts=[p.train_batches,p.calibration_batches,p.holdout_batches].map(x=>BigInt(version(x)))
  if(c.n<=0n || c.n>=c.d || counts.some(n=>n<3n||n>10000n) || counts.reduce((a,b)=>a+b)>20000n || ((counts[1]+1n)*c.n+c.d-1n)/c.d>counts[1]) fail()
}
export function parseModelWorkspace(raw:unknown, groupId:string, rollId:string, actor:string):ModelWorkspace {
  const w=closed(raw,['contract_version','actor_scope_id','group_id','roll_id','input','feature','policy','business_write','automatic_activation','production_go']);flags(w)
  if(w.contract_version!=='cp7.native-cutting-model-workspace.v1' || id(w.actor_scope_id)!==id(actor) || id(w.group_id)!==id(groupId) || id(w.roll_id)!==id(rollId)) fail()
  const input=parseCuttingInputWorkspace(w.input,groupId)
  if(input.actor_scope_id!==actor) fail()
  const feature=input.record?.values.rolls.find(r=>r.roll_id===rollId)??null
  if(!same(feature,w.feature)) fail()
  const selected=w.policy===null?null:policy(w.policy,actor)
  if(selected&&(!feature||!same(selected.context,feature.context))) fail()
  return {actor,groupId,rollId,input,feature,policy:selected}
}
export function validateLearningIntent(raw:unknown):LearningIntent {
  const intent=closed(raw,['id','kind','payload']);id(intent.id)
  if(intent.kind==='OBSERVATION') {
    const p=closed(intent.payload,['group_id','expected_group_version','expected_input_version'])
    return {id:id(intent.id),kind:'OBSERVATION',payload:{group_id:id(p.group_id),expected_group_version:p.expected_group_version===null?null:version(p.expected_group_version),expected_input_version:p.expected_input_version===null?null:version(p.expected_input_version)}}
  }
  if(intent.kind!=='MODEL') fail()
  const p=object(intent.payload),common={group_id:id(p.group_id),roll_id:id(p.roll_id),expected_group_version:version(p.expected_group_version),expected_input_version:version(p.expected_input_version)}
  if(p.action==='CHECK') {
    closed(p,['action','group_id','roll_id','expected_group_version','expected_input_version','policy_id'])
    return {id:id(intent.id),kind:'MODEL',payload:{action:'CHECK',...common,policy_id:id(p.policy_id)}}
  }
  closed(p,['action','group_id','roll_id','expected_group_version','expected_input_version','expected_policy_id','coverage','train_batches','calibration_batches','holdout_batches','explicit_review'])
  if(p.action!=='POLICY'||p.explicit_review!==true) fail()
  const numbers={coverage:decimal(p.coverage),train_batches:version(p.train_batches),calibration_batches:version(p.calibration_batches),holdout_batches:version(p.holdout_batches)}
  validatePolicyNumbers(numbers)
  return {id:id(intent.id),kind:'MODEL',payload:{action:'POLICY',...common,...numbers,expected_policy_id:nullableId(p.expected_policy_id),explicit_review:true}}
}
function fold(raw:unknown):FoldRow[] {
  const rows=array(raw).map(v=>{const r=closed(v,['slice_key','batch_key','revision_key','physical_at','known_at','consumed','rate','width_cm']);const at=time(r.physical_at),known=time(r.known_at);if(ticks(known)<ticks(at)) fail();return {slice_key:id(r.slice_key),batch_key:id(r.batch_key),revision_key:id(r.revision_key),physical_at:at,known_at:known,consumed:positive(r.consumed),rate:decimal(r.rate),width_cm:r.width_cm===null?null:positive(r.width_cm)}})
  if(new Set(rows.map(r=>r.slice_key)).size!==rows.length) fail()
  return rows
}
function assessment(raw:unknown, p:CuttingPolicy, currentGroup:string):Assessment {
  const e=object(raw);flags(e)
  const reason=text(e.reason),status=text(e.status)
  if(status==='UNAVAILABLE') {if(e.interval!==null) fail();return {status,reason,basis:null,interval:null,folds:{train:[],calibration:[],holdout:[]}}}
  if(!['PREDICTION_ONLY','LOW_REVIEW_REQUIRED','HIGH_REVIEW_REQUIRED','WITHIN_EMPIRICAL_INTERVAL'].includes(status)||e.selected_holdout_qualified!==true||!['WITH_RECORDED_WIDTH','WITHOUT_WIDTH'].includes(String(e.basis))||e.meaning!=='EMPIRICAL_NEW_CUTTING_EVENT_RANGE_NOT_CAUSE_OR_DESIGN_LIMIT') fail()
  const i=closed(e.interval,['lower_pcs','center_pcs','upper_pcs','calibration_batches','coverage_target','unit'])
  const interval={lower_pcs:decimal(i.lower_pcs),center_pcs:positive(i.center_pcs),upper_pcs:positive(i.upper_pcs),calibration_batches:version(i.calibration_batches),coverage_target:decimal(i.coverage_target),unit:'PCS' as const}
  if(i.unit!=='PCS'||compare(interval.lower_pcs,interval.center_pcs)>0n||compare(interval.center_pcs,interval.upper_pcs)>0n||interval.coverage_target!==p.coverage||interval.calibration_batches!==p.calibration_batches||e.prospective_policy_id!==p.id) fail()
  const folds={train:fold(e.train_rows),calibration:fold(e.calibration_rows),holdout:fold(e.holdout_rows)}, allBatches=new Set<string>()
  let previous=ticks(p.known_at)
  for(const [name,required] of [['train',p.train_batches],['calibration',p.calibration_batches],['holdout',p.holdout_batches]] as const) {
    const batches=new Set(folds[name].map(r=>r.batch_key))
    if(BigInt(batches.size)!==BigInt(required)||batches.has(currentGroup)||[...batches].some(b=>allBatches.has(b))||folds[name].some(r=>ticks(r.physical_at)<=previous)) fail()
    for(const batch of batches) allBatches.add(batch)
    previous=folds[name].reduce((n,r)=>ticks(r.known_at)>n?ticks(r.known_at):n,previous)
  }
  return {status,reason,basis:text(e.basis),interval,folds}
}
export function parseLearningReply(raw:unknown, intent:LearningIntent, actor:string):LearningReply {
  intent=validateLearningIntent(intent)
  if(intent.kind==='MODEL') {
    const v=closed(raw,['contract_version','actor_scope_id','result','current','original_matches_current_inputs','original_matches_current_history','original_matches_current_policy','business_write','automatic_activation','production_go']);flags(v)
    if(v.contract_version!=='cp7.native-cutting-model-command.v1'||id(v.actor_scope_id)!==actor) fail()
    const p=intent.payload,r=closed(v.result,['status','request_id','action','policy','model']),current=parseModelWorkspace(v.current,p.group_id,p.roll_id,actor)
    if(r.request_id!==intent.id||r.action!==p.action||!['COMMITTED','NOT_COMMITTED'].includes(String(r.status))) fail()
    const committed=r.status==='COMMITTED',saved=r.policy===null?null:policy(r.policy,actor)
    if(committed!==Boolean(saved)||!committed&&r.model!==null) fail()
    let e:Assessment|null=null
    if(committed&&p.action==='POLICY') {
      if(r.model!==null||saved!.request_id!==intent.id||saved!.previous_id!==p.expected_policy_id||['coverage','train_batches','calibration_batches','holdout_batches'].some(k=>saved![k as keyof CuttingPolicy]!==p[k as keyof PolicyPayload])) fail()
    } else if(committed) {
      const model=closed(r.model,['id','known_at','input_record_id','source_scope','evaluation','business_write','automatic_activation','production_go']);flags(model);id(model.id);time(model.known_at);id(model.input_record_id)
      if(saved!.id!==(p as ModelPayload).policy_id) fail()
      const scope=object(model.source_scope)
      if(scope.sample_scope!=='ACTOR_PROSPECTIVE_INPUT_CONTEXTS_NOT_UNRECORDED_FACTORY_HISTORY') fail()
      boolean(scope.source_complete);array(scope.records);array(scope.native_groups);array(scope.input_groups);array(scope.unavailable)
      e=assessment(model.evaluation,saved!,p.group_id)
      if(v.original_matches_current_inputs===true&&model.input_record_id!==current.input.record?.id) fail()
    }
    const currentOriginal=p.action==='POLICY'?boolean(v.original_matches_current_policy):boolean(v.original_matches_current_inputs)&&boolean(v.original_matches_current_history)&&boolean(v.original_matches_current_policy)
    // Validate every match flag even when an earlier one was false.
    boolean(v.original_matches_current_inputs);boolean(v.original_matches_current_history);boolean(v.original_matches_current_policy)
    if(v.original_matches_current_policy===true&&saved?.id!==current.policy?.id) fail()
    return {committed,current,assessment:e,observation:null,currentOriginal}
  }
  const v=closed(raw,['contract_version','actor_scope_id','result','current_native_source','current_input_record_id','original_matches_current_inputs','original_matches_current_native','model_trained','business_write','automatic_activation','production_go']);flags(v)
  if(v.contract_version!=='cp7.native-cutting-observation-command.v1'||id(v.actor_scope_id)!==actor||v.model_trained!==false) fail()
  nullableId(v.current_input_record_id)
  const r=closed(v.result,['status','request_id','observation'])
  if(r.request_id!==intent.id||!['COMMITTED','NOT_COMMITTED'].includes(String(r.status))) fail()
  const committed=r.status==='COMMITTED'
  if(committed!==(r.observation!==null)) fail()
  let observation:Observation|null=null
  if(committed) {
    const o=closed(r.observation,['id','actor_scope_id','request_id','group_id','known_at','input_record_id','native_source','records','exclusions','knowledge_basis','model_trained','production_go'])
    if(o.actor_scope_id!==actor||o.request_id!==intent.id||o.group_id!==intent.payload.group_id||o.knowledge_basis!=='REAL_CAPTURE_CLOCK_NOT_HISTORICAL_IMPUTATION'||o.model_trained!==false||o.production_go!==false) fail()
    nullableId(o.input_record_id)
    if(v.original_matches_current_inputs===true&&o.input_record_id!==v.current_input_record_id||v.original_matches_current_native===true&&!same(o.native_source,v.current_native_source)) fail()
    const records=array(o.records,1000).map(x=>{const z=closed(x,['slice_key','batch_key','revision_key','physical_at','known_at','input_known_at','native_valid','context','consumed','actual_pcs','width_cm']);const physical=time(z.physical_at),known=time(z.known_at),valid=boolean(z.native_valid);if(id(z.batch_key)!==intent.payload.group_id||ticks(known)!==ticks(time(o.known_at))||id(z.revision_key)!==o.id||ticks(physical)>ticks(known)) fail();if(valid&&(z.input_known_at===null||ticks(time(z.input_known_at))>=ticks(physical)||z.context===null||z.consumed===null||z.actual_pcs===null)) fail();const context=z.context===null?null:object(z.context);return {id:id(z.slice_key),valid,consumed:z.consumed===null?null:decimal(z.consumed),pcs:z.actual_pcs===null?null:decimal(z.actual_pcs),unit:context===null?null:text(context.unit)}})
    if(new Set(records.map(x=>x.id)).size!==records.length) fail()
    const exclusions=array(o.exclusions,1000).map(x=>{const z=closed(x,['slice_id','reason']);return {id:id(z.slice_id),reason:text(z.reason)}})
    observation={id:id(o.id),knownAt:time(o.known_at),records,exclusions}
  }
  const currentOriginal=boolean(v.original_matches_current_inputs)&&boolean(v.original_matches_current_native)
  boolean(v.original_matches_current_native)
  return {committed,current:null,assessment:null,observation,currentOriginal}
}
export const cuttingLearningKey=(scope:string)=>'erp.cp7.cutting-learning-intent.v1:'+scope
export function heldLearning(scope:string):{pending:LearningIntent|null;error:string} {
  try {const raw=localStorage.getItem(cuttingLearningKey(scope));return {pending:raw===null?null:validateLearningIntent(JSON.parse(raw)),error:''}}
  catch {return {pending:null,error:'Catatan penilaian belum dapat dipulihkan. Periksa penyimpanan sebelum menyimpan lagi.'}}
}
export function holdLearning(scope:string, intent:LearningIntent) {
  const held=heldLearning(scope);if(held.pending||held.error) throw Error('Pulihkan penilaian tersimpan terlebih dahulu.')
  const raw=JSON.stringify(validateLearningIntent(intent));localStorage.setItem(cuttingLearningKey(scope),raw)
  if(localStorage.getItem(cuttingLearningKey(scope))!==raw) throw Error('Permintaan belum tersimpan; penilaian ditahan.')
}
export function releaseLearning(scope:string, intent:LearningIntent) {
  const held=heldLearning(scope);if(held.error||!same(held.pending,intent)) throw Error('Catatan permintaan berubah.')
  localStorage.removeItem(cuttingLearningKey(scope));if(localStorage.getItem(cuttingLearningKey(scope))!==null) throw Error('Catatan pemulihan belum selesai.')
}
