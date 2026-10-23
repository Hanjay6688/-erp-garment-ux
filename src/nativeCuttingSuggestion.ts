import type {ProductionEnvelope} from './productionRecovery'
import {rec,hash,guid,target,fail} from './nativePlanDraft'
import {validateStagedPlanCommit} from './nativeStagedPlan'

export const CUTTING_SAVE_CONTRACT='cp7.cutting-checked-save.v1'
export function cuttingSuggestionPayload(p:Record<string,unknown>){
 guid(p.run_id);target(p.target_key);hash(p.identity_hash)
 if('cutting_save_contract'in p)fail()
 return{...p,cutting_save_contract:CUTTING_SAVE_CONTRACT}
}
// Persist the route inside the existing staged recovery payload. A reopen in
// the ordinary planning screen must replay this exact guarded route too.
export function isCuttingSuggestionSave(e:ProductionEnvelope){
 return e.action==='SAVE_DRAFT'&&Object.hasOwn(rec(e.payload),'cutting_save_contract')
}
type CheckedSaveClient={rpc:(name:'erp_cp7_save_cutting_suggestion_v1',args:{p_payload:unknown;p_request:string})=>PromiseLike<{data:unknown;error:unknown}>}
export async function sendCuttingSuggestion(client:unknown,e:ProductionEnvelope){
 if(!isCuttingSuggestionSave(e)||rec(e.payload).cutting_save_contract!==CUTTING_SAVE_CONTRACT)fail()
 // B's new RPC: A adds this pair to the generated types/shared source registry
 // when composing the stage. No general string-RPC escape is exposed.
 const r=await(client as CheckedSaveClient).rpc('erp_cp7_save_cutting_suggestion_v1',{p_payload:e.payload,p_request:e.id})
 if(r.error&&typeof r.error==='object'){
  const error=r.error as Record<string,unknown>
  const message=error.message==='CP7_CUTTING_SUGGESTION_SOURCE_CHANGED'?'Data untuk saran potong sudah berubah. Ambil analisis terbaru sebelum menyimpan.'
   :error.message==='CP7_CUTTING_SUGGESTION_NOT_FEASIBLE'?'Saran potong belum layak atau datanya belum lengkap. Periksa kembali stok, bahan dan kapasitas.':null
  if(message)return{data:r.data,error:{...error,message}}
 }
 return r
}
export function validateCuttingSuggestion(v:unknown,e:ProductionEnvelope,actor:string){
 if(!isCuttingSuggestionSave(e)||rec(e.payload).cutting_save_contract!==CUTTING_SAVE_CONTRACT)fail()
 const saved=validateStagedPlanCommit(v,e,actor),r=rec(v),g=rec(r.cutting_save_guard),p=rec(e.payload)
 const keys=['contract_version','run_id','target_key','identity_hash','checked_at','feasible']
 if(Object.keys(g).length!==keys.length||keys.some(k=>!Object.hasOwn(g,k))||g.contract_version!==CUTTING_SAVE_CONTRACT
  ||g.run_id!==p.run_id||g.target_key!==p.target_key||g.identity_hash!==p.identity_hash||g.feasible!==true
  ||typeof g.checked_at!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(g.checked_at)
  ||!Number.isFinite(Date.parse(g.checked_at))||Date.parse(g.checked_at)<Date.parse(String(r.data_as_of)))fail()
 return saved
}
