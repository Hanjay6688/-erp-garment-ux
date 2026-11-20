// PL-5 B wire fixtures: the history yield policy workspace and the history yield a plan preview states.
export const yieldTarget='0b1c2d3e-0000-4000-8000-000000000001:0b1c2d3e-0000-4000-8000-000000000002'
export const yieldActor='0b1c2d3e-0000-4000-8000-0000000000a1'
export function policyRow(revision:string,state:'ACTIVE'|'PAUSED',values:{window_days?:string;min_groups?:string;min_cut_pcs?:string}={}){
 return{id:`0b1c2d3e-0000-4000-8000-${revision.padStart(12,'0')}`,revision,state,window_days:values.window_days??'180',min_groups:values.min_groups??'5',min_cut_pcs:values.min_cut_pcs??'200',
  confidence:'0.90',method:'WILSON_SCORE_ONE_SIDED_LOWER_BOUND',rounding:'FLOOR_PERMILLE',levels:['PRODUCT_SIZE','MODEL'],reason:'Keputusan owner 8 Okt 2026',actor:yieldActor,actor_role:'OWNER',recorded_at:'2026-10-08T08:00:00+00:00'}
}
export function policyWorkspace(revisions:ReturnType<typeof policyRow>[]=[],manage=true){
 return{contract_version:'cp7.history-yield-policy.v1',state:revisions[0]?.state??'PENDING_POLICY_VALUE',current:revisions[0]??null,revisions,
  decided_package:{decision:'OWNER_DECISION_2026_10_08',window_days:'180',min_groups:'5',min_cut_pcs:'200',confidence:'0.90',method:'WILSON_SCORE_ONE_SIDED_LOWER_BOUND',rounding:'FLOOR_PERMILLE',levels:['PRODUCT_SIZE','MODEL']},
  manage_allowed:manage}
}
export function historyPending(){
 return{status:'PENDING_POLICY_VALUE',reason:'OWNER_HISTORY_YIELD_POLICY_NOT_APPROVED',window_days:null,minimum_sample:null,lower_bound:null,numerator:null,denominator:null,target_key:yieldTarget}
}
const common=()=>({contract_version:'cp7.history-yield.v2',target_key:yieldTarget,root_id:yieldTarget.split(':')[0],size_id:yieldTarget.split(':')[1],model_id:yieldActor,
 checked_at:'2026-10-08T09:00:00+00:00',window_first_day:'2026-04-12',kernel_version:'k'.repeat(64),basis:'PL8_STORED_PROOF_MATCHING_CURRENT_FACTS',
 policy:{id:policyRow('1','ACTIVE').id,revision:'1',state:'ACTIVE',window_days:'180',min_groups:'5',min_cut_pcs:'200',confidence:'0.90',actor_role:'OWNER',recorded_at:'2026-10-08T08:00:00+00:00'},
 window_days:'180',minimum_sample:{groups:'5',cut_pcs:'200'},excluded:{stale_or_unverifiable:'0',outside_window:'0',unattributed:'0',not_spent_now:'0'}})
export function historyAvailable(){
 return{...common(),status:'AVAILABLE',reason:'HISTORY_LOWER_BOUND_AT_POLICY',level:'PRODUCT_SIZE',
  levels:[{level:'PRODUCT_SIZE',status:'SUFFICIENT',reason:null,groups:'5',cut_pcs:'200',fg_pcs:'185',raw_numerator:'185',raw_denominator:'200',lower_bound_permille:'897'},{level:'MODEL',status:'NOT_EVALUATED',reason:'PRODUCT_SIZE_SUFFICIENT'}],
  groups:'5',cut_pcs:'200',fg_pcs:'185',lower_bound_permille:'897',lower_bound:'0.897',numerator:'897',denominator:'1000',proofs:[]}
}
export function historyInsufficient(){
 const level=(name:string)=>({level:name,status:'INSUFFICIENT_SAMPLE',reason:'HISTORY_SAMPLE_BELOW_POLICY',groups:'2',cut_pcs:'80',fg_pcs:'74',raw_numerator:'74',raw_denominator:'80',lower_bound_permille:null})
 return{...common(),status:'INSUFFICIENT_SAMPLE',reason:'HISTORY_SAMPLE_BELOW_POLICY',level:null,levels:[level('PRODUCT_SIZE'),level('MODEL')],
  groups:null,cut_pcs:null,fg_pcs:null,lower_bound_permille:null,lower_bound:null,numerator:null,denominator:null,proofs:[]}
}
