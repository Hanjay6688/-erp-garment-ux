import {parseAnalogCandidates} from '../../src/nativeProductAnalog'
import {analogContext,analogReply,analogId} from './nativeProductAnalog'
import {parseAnalogChoiceWorkspace,prepareAnalogConfirmation} from '../../src/nativeProductAnalogChoice'

export function analogChoiceFixture(){
 const context=analogContext(),candidates=parseAnalogCandidates(analogReply(context),context,0)
 const raw={contract_version:'cp7.product-analog-choices.v1',actor_scope_id:context.actor,access_epoch:context.accessEpoch,forecast_applied:false,production_go:false,rows:[{target_key:context.targetKey,choice_id:null,revision:'0',state:'UNREVIEWED',action:null,request_id:null,actor_scope_id:null,recorded_at:null,reason:null,evidence:null}]}
 const workspace=parseAnalogChoiceWorkspace(raw,context.actor,context.targetKey)
 const command=prepareAnalogConfirmation(context,candidates,workspace,candidates.rows[0].key,'1.2500',' Ukuran dan model ditinjau ',true,analogId(500))
 const row=candidates.rows[0]
 const evidence={contract_version:'cp7.product-analog-material.v1',target_key:context.targetKey,source_key:row.key,reviewed:true,target_product:{id:analogId(4),root_id:analogId(4),size_id:row.sizeId},source_product:{id:row.rootId,root_id:row.rootId,size_id:row.sizeId,sku:row.sku,product_name:row.name},available_total_pcs:'0',available_days:'1',minimum_available_days:'1',scale_factor:'1.25',profile_id:candidates.profileId,profile_revision:candidates.profileRevision,captured_at:context.reference.capturedAt,query:{...context.query},history_hash:candidates.historyHash,source_hash:candidates.sourceHash,analysis_source_hash:context.reference.sourceHash,identity_hash:context.identityHash,producer_hash:candidates.producerHash,source_request:context.requestId,source_run:context.runId,refs:[{kind:'PRODUCT',id:row.rootId,revision:'1'}]}
 const outcome={contract_version:'cp7.product-analog-choice-outcome.v1',choice_id:analogId(501),target_key:context.targetKey,revision:'1',action:'CONFIRM',request_id:command.requestId,recorded_at:'2026-10-24T00:00:01.123456+00:00',evidence,reason:command.payload.reason,actor_scope_id:context.actor,state:'CONFIRMED_ASSUMPTION',forecast_applied:false,production_go:false}
 return{context,candidates,raw,workspace,command,outcome}
}
