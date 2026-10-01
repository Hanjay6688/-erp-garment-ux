import type {NativeModelQuery} from '../../src/nativeModelEvaluation'
export const modelQuery:NativeModelQuery={history_run_id:'11111111-1111-4111-8111-111111111111',target_key:'22222222-2222-4222-8222-222222222222:33333333-3333-4333-8333-333333333333',horizon_days:'1'}
export function modelWire(requestId:string,actor='auth-user-1'){
 return{contract_version:'cp7.native-model-result.v1',actor_scope_id:actor,run_id:'44444444-4444-4444-8444-444444444444',request_id:requestId,
  history_run_id:modelQuery.history_run_id,target_key:modelQuery.target_key,size_id:modelQuery.target_key.split(':')[1],
  product_sku:'UNIT-MODEL-SKU',product_name:'Synthetic UI fixture',from_date:'2026-09-01',through_date:'2026-09-29',known_as_of:'2026-09-30T10:00:00.000000Z',
  registry_id:'cp7.native-model-policy.v1',registry_registered_at:'2026-09-30T09:00:00.000000Z',source_hash:'a'.repeat(64),
  knowledge_basis:'ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES',no_retrospective_availability_backfill:true,horizon_days:1,series_revision_count:29,
  selection_status:'BASELINE_RETAINED',selected_model_id:'mean-1',reason:'REGISTRY_NOT_KNOWN_BEFORE_VALIDATION',fallback_daily_mean:null,evaluation:null,forecast:null,
  automatic_activation:false,apply_allowed:false,production_go:false,policy_meaning:'TECHNICAL_PROPOSAL_NOT_OWNER_SERVICE_TARGET',source_state:'UNCHANGED'}
}
