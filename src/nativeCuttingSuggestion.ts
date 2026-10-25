import type {ProductionEnvelope} from './productionRecovery'
import {rec,hash,guid,target,fail} from './nativePlanDraft'
import {validateStagedPlanCommit} from './nativeStagedPlan'
import {planInstantMicros} from './nativePlanInstant'
import {normalizeClientError} from './lib/clientError'

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
 return await(client as CheckedSaveClient).rpc('erp_cp7_save_cutting_suggestion_v1',{p_payload:e.payload,p_request:e.id})
}
// The shared recovery hook must receive the original database rejection code.
// Translate only its displayed definite refusal, after recovery has classified
// it. A failed replay stays uncertain; auth and failed-refresh messages survive.
export function cuttingSuggestionNotice(error:unknown,recoveryError:string):string|undefined{
 if(!error||typeof error!=='object')return
 const raw=error as Record<string,unknown>
 if(raw.code!=='40001')return
 const normalized=normalizeClientError(error)
 if(normalized.code!=='RETRYABLE_CONFLICT')return
 const suffix=recoveryError.slice(normalized.message.length)
 if(!recoveryError.startsWith(normalized.message)||(suffix!==''&&suffix!==' Refetch authoritative gagal; writer tetap terkunci.'))return
 const message=raw.message==='CP7_CUTTING_SUGGESTION_SOURCE_CHANGED'?'Data untuk saran potong sudah berubah. Ambil analisis terbaru sebelum menyimpan.'
  :raw.message==='CP7_CUTTING_SUGGESTION_NOT_FEASIBLE'?'Saran potong belum layak atau datanya belum lengkap. Periksa kembali stok, bahan dan kapasitas.':null
 return message?message+suffix:undefined
}
export function validateCuttingSuggestion(v:unknown,e:ProductionEnvelope,actor:string){
 if(!isCuttingSuggestionSave(e)||rec(e.payload).cutting_save_contract!==CUTTING_SAVE_CONTRACT)fail()
 const saved=validateStagedPlanCommit(v,e,actor),r=rec(v),g=rec(r.cutting_save_guard),p=rec(e.payload)
 const keys=['contract_version','run_id','target_key','identity_hash','checked_at','feasible']
 if(Object.keys(g).length!==keys.length||keys.some(k=>!Object.hasOwn(g,k))||g.contract_version!==CUTTING_SAVE_CONTRACT
  ||g.run_id!==p.run_id||g.target_key!==p.target_key||g.identity_hash!==p.identity_hash||g.feasible!==true
  ||planInstantMicros(g.checked_at)<planInstantMicros(r.data_as_of))fail()
 return saved
}
