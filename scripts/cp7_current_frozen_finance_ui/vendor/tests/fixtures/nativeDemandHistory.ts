// Synthetic CLIENT WIRE only. Native business arithmetic is tested separately
// by cp7_planning_history_cases.py against unchanged ERP writers and real Auth.
export const demandRoot='11111111-1111-4111-8111-111111111111',demandSize='22222222-2222-4222-8222-222222222222'
export const demandRequest='33333333-3333-4333-8333-333333333333',demandRun='44444444-4444-4444-8444-444444444444'
export function demandWire(request=demandRequest){
 const captured='2026-09-30T12:00:00.000001Z',hash='a'.repeat(64),key=demandRoot+':'+demandSize,scope='GLOBAL_CURRENT_PHYSICAL_ROOTS',refs=[{kind:'PRODUCT',id:demandRoot,revision:'1'}]
 return{contract_version:'cp7.native-demand-history.v1',scope,capture_complete:true,captured_at:captured,source_hash:hash,
  current_stock:[{target_key:key,root_id:demandRoot,size_id:demandSize,sku:'SKU-NATIVE-WIRE',product_name:'Celana ukuran M',is_active:true,
   grade_basis:'NATIVE_SELLABLE_GRADE_A_AND_B',projection_basis:'CURRENT_STOCK_ONLY_NO_FORECAST',native_available_pcs:'76',refs,
   availability:{status:'KNOWN',kernel_version:'availability-1',physical_fg_pcs:'100',reserved_pcs:'24',available_fg_pcs:'76',projected_residual_pcs:'76',
    inputs:{snapshot_id:hash,scope_id:scope,target_key:key,size_id:demandSize,residual_future_pcs:'0'}}}],
  history:{contract_version:'cp7.demand-result.v1',kernel_version:'demand-1',snapshot_id:hash,scope_id:scope,known_as_of:captured,effective_as_of:captured,
   from_date:'2026-09-29',through_date:'2026-09-29',status:'CAPTURE_COMPLETE',group_mode:'AS_SOLD',
   rows:[{target_key:key,size_id:demandSize,gross_observed_pcs:'0',draft_reserved_pcs:'24',available_days:0,unknown_days:1,stockout_days:0,
    calendar_sales_mean:'0',available_sales_mean:null,days:[{date:'2026-09-29',state:'UNKNOWN',gross_observed_pcs:'0',returned_pcs:'0',training_pcs:null}],refs}],
   group_events:[],selected_events:[]},availability_knowledge_basis:'CURRENT_CAPTURE_RESTATED_LEDGER',training_known_at:captured,
  model_eligibility:'HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED',versions:{producer:'native-demand-1',history:'demand-1',availability:'availability-1'},
  production_go:false,source_state:'UNCHANGED',run_id:demandRun,request_id:request}
}
