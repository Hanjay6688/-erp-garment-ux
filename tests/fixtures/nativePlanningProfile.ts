// Synthetic CLIENT WIRE only, never native/Auth source qualification.
import {demandWire,demandRoot,demandSize,demandRequest,demandRun} from './nativeDemandHistory'
export const planningId='55555555-5555-4555-8555-555555555555'
export const planningConfig={mean_mode:'SELECTED_MANUAL' as const,daily_pcs:'10',minimum_available_days:'20',lead_days:'3',review_days:'7',buffer_days:'0'}
export const planningQuery={from_date:'2026-09-29',through_date:'2026-09-29',group_mode:'AS_SOLD' as const}
export function planningProfile(reviewed=true){return{root_id:demandRoot,product_version_id:demandRoot,size_id:demandSize,sku:'SKU-NATIVE-WIRE',product_name:'Celana ukuran M',profile_id:reviewed?planningId:null,revision:reviewed?'1':'0',quality:reviewed?'SELECTED_ASSUMPTION':'UNREVIEWED',config:reviewed?{...planningConfig}:null,reason:reviewed?'Explicit client wire fixture':null,recorded_at:reviewed?'2026-09-30T12:00:00Z':null}}
export function profileWire(reviewed=true){return{contract_version:'cp7.planning-profile.v1',rows:[planningProfile(reviewed)]}}
export function baselineWire(request=demandRequest){
 const hash='b'.repeat(64),scope='GLOBAL_CURRENT_PHYSICAL_ROOTS',h=demandWire(request),refs=[{kind:'PRODUCT',id:demandRoot,revision:'1'},{kind:'PLANNING_PROFILE',id:planningId,revision:'1'}]
 return{contract_version:'cp7.native-baseline.v1',captured_at:h.captured_at,source_hash:hash,scope,history_run_result:h,rows:[{target_key:demandRoot+':'+demandSize,size_id:demandSize,sku:'SKU-NATIVE-WIRE',product_name:'Celana ukuran M',available_fg_pcs:'76',profile:planningProfile(),
  demand_estimate:{status:'SCENARIO',basis:'SELECTED_MANUAL_ASSUMPTION',daily_pcs:'10',inputs:{contract_version:'cp7.demand-estimate-input.v1',snapshot_id:hash,scope_id:scope,target_key:demandRoot+':'+demandSize,size_id:demandSize,minimum_own_available_days:'20',own:null,analog:null,manual:{daily_pcs:'10',assumption_id:planningId,selected:true,refs},refs}},
  target:{status:'SCENARIO',kernel_version:'target-days-1',horizon_days:'10',horizon_demand_pcs:'100',buffer_pcs:'0',target_pcs:'100',formula:'ceil(D * (L + R + B))',inputs:{contract_version:'cp7.target-input.v1',snapshot_id:hash,scope_id:scope,mode:'DAYS',daily_mean:'10',lead_days:'3',review_days:'7',buffer_days:'0',quantile:null,horizon_samples:[],refs}},
  production_policy:null,start_new_pcs:null,final_gap_pcs:null,supply_state:'UNKNOWN',capacity_state:'UNKNOWN',timeline_state:'UNKNOWN',reason:'PRODUCTION_POLICY_UNREVIEWED_OR_IDENTITY_UNAVAILABLE',refs}],target_basis:'DAYS_WITH_SELECTED_PROFILE_ASSUMPTIONS',apply_enabled:false,model_basis:'BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN',production_go:false,source_state:'UNCHANGED',run_id:demandRun,request_id:request}
}
