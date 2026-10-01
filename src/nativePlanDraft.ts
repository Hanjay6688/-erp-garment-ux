import type {ProductionEnvelope} from './productionRecovery'
import {parseCuttingSaveResult} from './cuttingPersistence'
export type PlanContext={runId:string;targetKey:string;sourceHash:string}
export type PlanOptions={runId:string;targetKey:string;sourceHash:string;coreHash:string;modelId:string;sizeId:string;sku:string;name:string;needed:string|null;capacity:string|null;state:'ACTIVE'|'PAUSED'|'STOPPED'|null;locationId:string|null;assumptions:{id:string;label:string}[];orders:{id:string;number:string;modelId:string}[];patterns:{id:string;code:string;name:string;revision:string}[];rolls:{id:string;number:string;materialId:string;materialName:string;unit:string;available:string}[];locations:{id:string;name:string}[];page:{limit:number;poOffset:number;poTotal:string;patternOffset:number;patternTotal:string;rollOffset:number;rollTotal:string}}
export type PlanForm={orderId:string;patternId:string;locationId:string;cutAt:string;notes:string;reason:string;reviewed:boolean;rolls:{id:string;issued:string;consumed:string;remaining:string;pcs:string}[]}
export type PlanSaved={id:string;planId:string;revision:string;runId:string;targetKey:string;sourceHash:string;state:string;native:{id:string;groupId:string;number:string|null;posted:boolean|null}|null}
export type PlanPreview={draftId:string;revision:string;targetKey:string;needed:string;selected:string;capacity:string;unresolved:string;roundingExtra:string;patternRevision:string;materials:{rollId:string;materialId:string;available:string;issued:string;consumed:string;remaining:string}[]}
const fail=():never=>{throw Error('Rencana belum sesuai sumber ERP, pilihan, atau hak aksesnya.')}
const rec=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const text=(v:unknown):string=>typeof v==='string'&&v.length>0&&v.length<=4000?v:fail()
const guid=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const hash=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const qty=(v:unknown):string=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})(\.[0-9]{1,12})?$/.test(v)?v:fail()
const revision=(v:unknown):string=>typeof v==='string'&&/^[1-9][0-9]{0,14}$/.test(v)?v:fail()
const integer=(v:unknown):number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0?v:fail()
const rows=(v:unknown,max=1000):Record<string,unknown>[]=>Array.isArray(v)&&v.length<=max?v.map(rec):fail()
function unique<T extends{id:string}>(v:T[]):T[]{if(new Set(v.map(x=>x.id)).size!==v.length)return fail();return v}
function target(v:unknown):string{const k=text(v),parts=k.split(':');if(parts.length!==2)return fail();parts.forEach(guid);return k}
function flags(r:Record<string,unknown>,actor:string,contract:string){if(r.contract_version!==contract||r.actor_scope_id!==actor||r.reservation_created!==false||r.production_go!==false)fail()}
export function planOptionsQuery(c:PlanContext,location:string,poQuery='',rollQuery='',poOffset=0,rollOffset=0,patternOffset=0){return{run_id:c.runId,target_key:c.targetKey,location_id:location||null,po_query:poQuery,roll_query:rollQuery,po_offset:String(poOffset),roll_offset:String(rollOffset),pattern_offset:String(patternOffset),limit:'25'}}
export function parsePlanOptions(v:unknown,actor:string,c:PlanContext):PlanOptions{
 const r=rec(v);flags(r,actor,'cp7.plan-options.v1');if(r.run_id!==c.runId||r.target_key!==c.targetKey||r.source_hash!==c.sourceHash)fail()
 const p=rec(r.page),limit=integer(p.limit);if(limit<1||limit>50)fail()
 const modelId=guid(r.model_id),orders=unique(rows(r.orders,limit).map(x=>({id:guid(x.id),number:text(x.number),modelId:guid(x.model_id)}))),patterns=unique(rows(r.patterns,limit).map(x=>({id:guid(x.id),code:text(x.code),name:text(x.name),revision:text(x.revision)}))),rolls=unique(rows(r.rolls,limit).map(x=>({id:guid(x.id),number:text(x.number),materialId:guid(x.material_id),materialName:text(x.material_name),unit:text(x.unit),available:qty(x.available)})))
 if(orders.some(x=>x.modelId!==modelId))fail()
 const page={limit,poOffset:integer(p.po_offset),poTotal:qty(p.po_total),patternOffset:integer(p.pattern_offset),patternTotal:qty(p.pattern_total),rollOffset:integer(p.roll_offset),rollTotal:qty(p.roll_total)}
 for(const[length,offset,total]of[[orders.length,page.poOffset,page.poTotal],[patterns.length,page.patternOffset,page.patternTotal],[rolls.length,page.rollOffset,page.rollTotal]]as const){if(!/^(0|[1-9][0-9]*)$/.test(total)||BigInt(length)!==(BigInt(total)>BigInt(offset)?(BigInt(total)-BigInt(offset)<BigInt(limit)?BigInt(total)-BigInt(offset):BigInt(limit)):0n))fail()}
 const state=r.production_state===null?null:text(r.production_state);if(state!==null&&!['ACTIVE','PAUSED','STOPPED'].includes(state))fail()
 const assumptions=unique(rows(r.assumptions).map(x=>({id:text(x.id),label:text(x.label)})))
 return{runId:guid(r.run_id),targetKey:target(r.target_key),sourceHash:hash(r.source_hash),coreHash:hash(r.core_hash),modelId,sizeId:guid(r.size_id),sku:text(r.product_sku),name:text(r.product_name),needed:r.needed_pcs===null?null:qty(r.needed_pcs),capacity:r.capacity_pcs===null?null:qty(r.capacity_pcs),state:state as PlanOptions['state'],locationId:r.location_id===null?null:guid(r.location_id),assumptions,orders,patterns,rolls,locations:unique(rows(r.locations).map(x=>({id:guid(x.id),name:text(x.name)}))),page}
}
export function planPayload(o:PlanOptions,f:PlanForm,cutAt:string,saved:PlanSaved|null){
 if(!f.reviewed||o.state!=='ACTIVE'||o.needed===null||o.capacity===null||!o.orders.some(x=>x.id===f.orderId)||!o.patterns.some(x=>x.id===f.patternId)||o.locationId!==f.locationId||!f.reason.trim()||f.reason.length>1000||!f.rolls.length||f.rolls.length>100||!Number.isFinite(Date.parse(cutAt)))fail()
 if(new Set(f.rolls.map(x=>x.id)).size!==f.rolls.length)fail()
 const rolls=f.rolls.map(x=>{if(!o.rolls.some(r=>r.id===x.id))fail();[x.issued,x.consumed,x.remaining,x.pcs].forEach(qty);if(!/^[1-9][0-9]{0,8}$/.test(x.pcs))fail();return{roll_id:x.id,qty_issued:x.issued,qty_consumed:x.consumed,qty_reported_remaining:x.remaining,yields:[{slot_no:'1',qty_pcs:x.pcs}]}})
 return{run_id:o.runId,target_key:o.targetKey,plan_id:saved?.planId??null,expected_revision:saved?.revision??null,source_hash:o.sourceHash,reviewed_assumption_ids:o.assumptions.map(x=>x.id),reason:f.reason.trim(),cutting:{po_id:f.orderId,pattern_id:f.patternId,source_location_id:f.locationId,cut_at:cutAt,notes:f.notes.trim()||null,size_slots:[{slot_no:'1',size_id:o.sizeId,drawing_no:'1'}],rolls}}
}
export function validatePlanCommit(v:unknown,e:ProductionEnvelope,actor:string):PlanSaved{
 const r=rec(v),p=rec(e.payload);flags(r,actor,e.action==='SAVE_DRAFT'?'cp7.plan-draft.v1':'cp7.plan-apply-outcome.v1');if(r.request_id!==e.id)fail()
 if(e.action==='SAVE_DRAFT'){
  if(r.run_id!==p.run_id||r.target_key!==p.target_key||r.state!=='SAVED')fail()
  return{id:guid(r.draft_id),planId:guid(r.plan_id),revision:revision(r.revision),runId:guid(r.run_id),targetKey:target(r.target_key),sourceHash:hash(p.source_hash),state:'SAVED',native:null}
 }
 if(e.action!=='APPLY'||r.kind!=='COMMITTED_OUTCOME'||r.draft_id!==p.draft_id||r.revision!==p.expected_revision||r.state!=='NATIVE_DRAFT_CREATED'||r.physical_production_confirmed!==false)fail()
 const n=parseCuttingSaveResult(r.native);if(n.material_issue_posted!==false)fail()
 // The exact immutable header is loaded by its UUID after commit. Never borrow
 // the selected new run/target's label for recovery of an older pending request.
 return{id:guid(r.draft_id),planId:'',revision:revision(r.revision),runId:'',targetKey:target(r.target_key),sourceHash:'',state:'NATIVE_DRAFT_CREATED',native:{id:guid(r.intent_id),groupId:guid(n.cutting_group_id),number:n.group_number,posted:false}}
}
export function parsePlanSaved(v:unknown,actor:string,id:string):PlanSaved{
 const r=rec(v);flags(r,actor,'cp7.plan-draft-read.v1');if(r.draft_id!==id||typeof r.is_latest!=='boolean'||!['SAVED','NATIVE_DRAFT_CREATED','NATIVE_DRAFT_DELETED','NATIVE_MATERIAL_POSTED'].includes(String(r.state)))fail()
 const p=rec(r.payload);if(p.run_id!==r.run_id||p.target_key!==r.target_key||p.source_hash!==r.source_hash)fail()
 const native=r.native_intent===null?null:rec(r.native_intent);if(native!==null&&native.material_issue_posted!==null&&typeof native.material_issue_posted!=='boolean')fail()
 return{id:guid(r.draft_id),planId:guid(r.plan_id),revision:revision(r.revision),runId:guid(r.run_id),targetKey:target(r.target_key),sourceHash:hash(r.source_hash),state:String(r.state),native:native?{id:guid(native.id),groupId:guid(native.cutting_group_id),number:native.group_number===null?null:text(native.group_number),posted:native.material_issue_posted as boolean|null}:null}
}
export function parsePlanPreview(v:unknown,actor:string,s:PlanSaved):PlanPreview{
 const r=rec(v);flags(r,actor,'cp7.plan-preview.v1');if(r.draft_id!==s.id||r.revision!==s.revision||r.plan_id!==s.planId||r.target_key!==s.targetKey||r.source_hash!==s.sourceHash||r.status!=='READY_FOR_EXPLICIT_NATIVE_DRAFT'||r.physical_production_confirmed!==false||r.command!=='erp_save_cutting_group_before_sewing_v2:SAVE_DRAFT')fail()
 hash(r.core_hash);hash(r.composition_hash)
 return{draftId:guid(r.draft_id),revision:revision(r.revision),targetKey:target(r.target_key),needed:qty(r.needed_pcs),selected:qty(r.selected_new_pcs),capacity:qty(r.free_capacity_pcs),unresolved:qty(r.unresolved_pcs),roundingExtra:qty(r.rounding_extra_pcs),patternRevision:text(r.pattern_revision),materials:rows(r.material_rows,100).map(x=>{if(x.basis!=='OPERATOR_SELECTED_DRAFT_COMPOSITION_NOT_PROVEN_INSTALLED_OR_RESERVED')fail();return{rollId:guid(x.roll_id),materialId:guid(x.material_id),available:qty(x.native_available),issued:qty(x.selected_issued),consumed:qty(x.selected_consumption),remaining:qty(x.selected_remaining)}})}
}
export const planPointerKey=(scope:string)=>'erp.cp7.plan-pointer.v1:'+scope
export function readPlanPointer(scope:string):{id:string|null;error:string}{try{const raw=localStorage.getItem(planPointerKey(scope));if(raw===null)return{id:null,error:''};const p=rec(JSON.parse(raw));if(Object.keys(p).join('|')!=='id')fail();return{id:guid(p.id),error:''}}catch{return{id:null,error:'Penunjuk rencana tersimpan belum dapat dibaca. Jejak lama dipertahankan.'}}}
export function rememberPlanPointer(scope:string,id:string){const old=readPlanPointer(scope);if(old.error)throw Error(old.error);const raw=JSON.stringify({id:guid(id)});localStorage.setItem(planPointerKey(scope),raw);if(localStorage.getItem(planPointerKey(scope))!==raw)throw Error('Penunjuk rencana belum tersimpan. Periksa UUID yang sama.')}
