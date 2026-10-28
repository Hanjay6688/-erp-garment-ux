// Controlled test data only; imported by DOM/browser proof entries, never by the panel.
import {analogChoiceFixture} from '../../../tests/fixtures/nativeProductAnalogChoice'
import {analogContext,analogReply} from '../../../tests/fixtures/nativeProductAnalog'
import demand from '../../../tests/fixtures/nativeTargetDemandSql.json'
import {parseAnalogCandidates,type AnalogReadContext} from '../../../src/nativeProductAnalog'
import {parseAnalogChoiceWorkspace,prepareAnalogConfirmation} from '../../cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice'
export function frozenChoiceUIFixture(total=1){
 const old=analogChoiceFixture()
 const context:AnalogReadContext={...analogContext(),sourceMethod:'FROZEN_V2',targetKey:demand.analog.target_key,query:{...demand.analog.query,group_mode:'AS_SOLD'},reference:{...analogContext().reference,capturedAt:demand.analog.captured_at}}
 const reply=(offset=0)=>({...analogReply(context,total,offset),contract_version:'cp7.product-analog-candidates-read.v3',bounded_request_contract:'cp7.bounded-analysis-request.v2',bounded_reference_contract:'cp7.bounded-analysis-reference.v2',consumer_capability:'REVIEWED_ANALOG_FOR_FRESH_CAPTURES',target_demand:structuredClone(demand.analog)})
 const candidates=parseAnalogCandidates(reply(),context,0),raw={...old.raw,rows:[{...old.raw.rows[0],target_key:context.targetKey}]}
 const workspace=parseAnalogChoiceWorkspace(raw,context.actor,context.targetKey),row=candidates.rows[0]
 const command=prepareAnalogConfirmation(context,candidates,workspace,row.key,'1.25','Ukuran dan model ditinjau',true,old.command.requestId)
 const evidence={...old.outcome.evidence,target_key:context.targetKey,source_key:row.key,target_product:{id:context.targetKey.split(':')[0],root_id:context.targetKey.split(':')[0],size_id:row.sizeId},source_product:{id:row.rootId,root_id:row.rootId,size_id:row.sizeId,sku:row.sku,product_name:row.name},available_days:String(row.availableDays),captured_at:context.reference.capturedAt,query:context.query}
 const outcome={...old.outcome,contract_version:'cp7.product-analog-choice-outcome.v2',target_key:context.targetKey,evidence}
 return {context,candidates,raw,workspace,command,outcome,reply}
}
