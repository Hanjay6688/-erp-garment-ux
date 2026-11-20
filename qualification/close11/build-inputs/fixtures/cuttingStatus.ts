import {cuttingStatusBasis,type CuttingStatusPolicyIntent} from '../../src/nativeCuttingStatus'
export const statusGroup='00000011-0000-4000-8000-000000000000'
export const statusActor='00000001-0000-4000-8000-000000000000'
export const statusPolicy='00000012-0000-4000-8000-000000000000'
export const statusRequest='00000013-0000-4000-8000-000000000000'
export function cuttingStatusFixture(group=statusGroup){
  return {contract_version:'cp7.automatic-cutting-status.v1',checked_at:'2026-10-23T01:00:00.123456Z',
    group:{id:group,version:'2',posted:true,physical_at:'2026-10-22T01:00:00.000000Z',
      pattern_id:'00000014-0000-4000-8000-000000000000',pattern_revision:'R1',pattern_label:'REG · Pola reguler',
      production_status:'SEWING',production_stage:'SEWING'},
    policy:{id:statusPolicy,revision:'1',state:'ACTIVE',coverage:'0.8',min_groups:'3',reason:'Aturan fixture eksplisit',
      actor:statusActor,recorded_at:'2026-10-22T00:00:00.000000Z'},
    materials:[{material_id:'00000015-0000-4000-8000-000000000000',sku:'FAB-A',name:'Bahan A',unit:'M',
      size_ids:['00000016-0000-4000-8000-000000000000'],size_labels:['S–M'],consumed:'10',total_pcs:'100',
      history_groups:'3',status:'WITHIN',lower_pcs:'80',upper_pcs:'120'}],
    scope:'FACTORY',basis:cuttingStatusBasis,business_write:false}
}
export function statusIntent(requestId=statusRequest):CuttingStatusPolicyIntent{
  return {requestId,payload:{expected_revision:'1',state:'ACTIVE',coverage:'0.8',min_groups:'3',reason:'Alasan fixture baru',explicit_review:true}}
}
export function statusPolicyReply(intent=statusIntent()){
  return {contract_version:'cp7.automatic-cutting-policy-result.v1',request_id:intent.requestId,status:'COMMITTED',
    policy:{...cuttingStatusFixture().policy,revision:(BigInt(intent.payload.expected_revision)+1n).toString(),
      state:intent.payload.state,coverage:intent.payload.coverage,min_groups:intent.payload.min_groups,reason:intent.payload.reason.trim()}}
}
