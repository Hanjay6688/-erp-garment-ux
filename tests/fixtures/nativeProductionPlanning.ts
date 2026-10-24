// SYNTHETIC_CLIENT_WIRE. Native/Auth qualifications live in retained CI reports.
import {baselineWire,unifiedBaselineWire,planningQuery,planningId} from './nativePlanningProfile'
import {demandRoot,demandSize,demandRun,demandRequest} from './nativeDemandHistory'
export const workKey='OPEN:'+demandRoot+':SEWING'
export const customerKey='OPEN:'+planningId+':SEWING'
export const supplyHash='c'.repeat(64)
export const scheduleConfig={basis:'SELECTED_ASSUMPTIONS' as const,resource_scope:'SINGLE_HOMOGENEOUS_SELECTED_CENTRE' as const,work_centre_key:'Explicit selected centre',through_at:'2026-10-02T12:00:00.123456Z',unit_minutes:'2',windows:[{key:'selected-work',starts_at:'2026-10-01T01:00:00.123456Z',ends_at:'2026-10-01T03:00:00.123456Z',other_load_minutes:'0'}],positions:[{position_key:workKey,target_key:demandRoot+':'+demandSize,eligible_input_pcs:'8',yield_numerator:'9',yield_denominator:'10',remaining_steps:[{stage:'SEWING',remaining_minutes:'15'},{stage:'LAUNDRY',remaining_minutes:'20'},{stage:'QC',remaining_minutes:'10'}]},{position_key:customerKey,target_key:null,eligible_input_pcs:'8',yield_numerator:null,yield_denominator:null,remaining_steps:[{stage:'SEWING',remaining_minutes:'15'},{stage:'LAUNDRY',remaining_minutes:'20'},{stage:'QC',remaining_minutes:'10'}]}]}
function work(eligible=true){return{key:eligible?workKey:customerKey,pool_key:'OPEN:'+(eligible?demandRoot:planningId),stage:'SEWING_ACTIVE',size_id:demandSize,ownership:eligible?'COMPANY':'CUSTOMER',eligible_company_wip:eligible,remaining_pcs:'8'}}
export function supplyWire(request=demandRequest){const baseline=baselineWire(request);return{contract_version:'cp7.native-supply.v2',run_id:demandRun,request_id:request,source_hash:supplyHash,captured_at:baseline.captured_at,source_state:'UNCHANGED',scope:'GLOBAL_CURRENT_PHYSICAL_ROOTS_AND_POSTED_PRODUCTION_ORIGINS',apply_enabled:false,production_go:false,baseline_run_result:baseline,wip:{contract_version:'cp7.wip-position.v1',snapshot_id:baseline.captured_at,status:'COMPLETE',scope:'GLOBAL_NATIVE_POSTED_PRODUCTION_ORIGINS',positions:[work(),work(false)]}}}
export function workspaceWire(reviewed=false){const s=supplyWire();return{contract_version:'cp7.planning-schedule.v1',source_run:s.run_id,source_hash:s.source_hash,current_source_hash:s.source_hash,captured_at:s.captured_at,source_state:'UNCHANGED',revision:reviewed?'1':'0',production_go:false,plan_state:reviewed?'SELECTED_ASSUMPTIONS':'UNREVIEWED',plan:reviewed?{plan_id:planningId,revision:'1',source_run:s.run_id,source_hash:s.source_hash,recorded_at:s.captured_at,config:structuredClone(scheduleConfig)}:null,position_requirements:s.wip.positions.map(p=>({position_key:p.key,pool_key:p.pool_key,stage:p.stage,size_id:p.size_id,ownership:p.ownership,eligible_company_wip:p.eligible_company_wip,remaining_pcs:p.remaining_pcs,remaining_route:['SEWING','LAUNDRY','QC'],target_candidates:p.eligible_company_wip?[{target_key:demandRoot+':'+demandSize,product_version_id:demandRoot,sku:'SKU-NATIVE-WIRE',product_name:'Celana ukuran M'}]:[]}))}}
export function scheduleOutcome(request:string,revision='1'){return{contract_version:'cp7.planning-schedule-outcome.v1',plan_id:planningId,revision,request_id:request,source_hash:supplyHash,quality:'SELECTED_ASSUMPTIONS',production_go:false}}
// SYNTHETIC_CLIENT_WIRE for the additive staged work route, never Native proof.
export function scheduleJobWire(request=demandRequest,state:'RUNNING'|'DONE'|'FAILED'='RUNNING'){
 return{contract_version:'cp7.native-analysis-staged-job.v1',request_id:request,state,stage:state==='DONE'?null:'HIST_ROWS',stage_index:1,stage_count:9,units_done:state==='DONE'?55:0,unit_count:55,plan_final:state==='DONE',targets_total:1,targets_done_in_stage:0,reference:{captured_at:supplyWire().captured_at.replace('Z','+00:00'),source_hash:'a'.repeat(64)},last_progress_at:supplyWire().captured_at,unit_attempts:0,run_id:state==='DONE'?demandRun:null,failure:state==='FAILED'?{unit:0,sqlstate:'P0001',code:'CP7_PLANNING_CAPTURE_INCOMPLETE'}:null,apply_enabled:false,production_go:false}
}
export function stagedWorkspaceWire(request=demandRequest,reviewed=false){
 return{...workspaceWire(reviewed),contract_version:'cp7.planning-schedule-staged.v1',source_request_id:request,analysis_state:'RUNNING',analysis_source_hash:'a'.repeat(64),history_capture_state:'COMPLETE',production_capture_state:'COMPLETE',staged_review_contract:'cp7.schedule-staged-review.v1'}
}
export function stagedScheduleOutcome(request:string,revision='1'){
 return{...scheduleOutcome(request,revision),contract_version:'cp7.planning-schedule-staged-outcome.v1',staged_review_contract:'cp7.schedule-staged-review.v1',source_run:demandRun}
}
// Separate explicit bounded-method wire, with unchanged raw capture truth.
export function boundedWorkspaceWire(request=demandRequest,reviewed=false){
 return{...stagedWorkspaceWire(request,reviewed),contract_version:'cp7.planning-schedule-staged-bounded.v1',history_capture_state:'INCOMPLETE',
  bounded_request_contract:'cp7.bounded-analysis-request.v1',bounded_reference_contract:'cp7.bounded-analysis-reference.v1',history_input_coverage:'COMPLETE'}
}
export function boundedScheduleOutcome(request:string,revision='1'){
 return{...stagedScheduleOutcome(request,revision),contract_version:'cp7.planning-schedule-staged-bounded-outcome.v1',
  bounded_request_contract:'cp7.bounded-analysis-request.v1',bounded_reference_contract:'cp7.bounded-analysis-reference.v1'}
}
export function nettingWire(request=demandRequest,unknown=false){const supply=supplyWire(request),hash='d'.repeat(64),row=supply.baseline_run_result.rows[0],capacity={status:unknown?'UNKNOWN':'SCENARIO',capacity_pcs:unknown?null:'15'},net={status:unknown?'UNKNOWN':'SCENARIO',q_base_pcs:unknown?null:'17',q_conditional_pcs:unknown?null:'17',directed_on_time_pcs:unknown?null:'7',inputs:{snapshot_id:supply.captured_at,scope_id:'GLOBAL_NATIVE_PLANNING',target_key:row.target_key,size_id:row.size_id,available_fg_pcs:row.available_fg_pcs,target_pcs:row.target.target_pcs}}
 return{contract_version:'cp7.native-netting.v1',run_id:demandRun,request_id:request,source_hash:hash,captured_at:supply.captured_at,source_state:'UNCHANGED',status:unknown?'PARTIAL':'SCENARIO',apply_enabled:false,production_go:false,material_state:'UNKNOWN',schedule_run_result:{contract_version:'cp7.native-planning-scenario.v1',captured_at:supply.captured_at,source_hash:'e'.repeat(64),supply_run_result:supply,schedule_state:'SELECTED_ASSUMPTIONS',apply_enabled:false,production_go:false,wip:supply.wip,capacity,etas:supply.wip.positions.map(p=>({position_key:p.key,result:{status:unknown?'UNKNOWN':'CONDITIONAL',eta:unknown?null:'2026-10-01T01:45:00.123456Z'}}))},allocation:{status:unknown?'UNKNOWN':'SCENARIO'},rows:[{...row,raw_gap_pcs:'24',directed_on_time_good_pcs:unknown?null:'7',base_gap_pcs:unknown?null:'17',conditional_gap_pcs:unknown?null:'17',candidate_allocated_good_pcs:unknown?null:'0',net,timeline:{status:unknown?'UNKNOWN':'SCENARIO',first_known_gap:unknown?null:{at:'2026-10-03T12:00:00.123456Z'}},new_start_capacity:capacity,material_state:'UNKNOWN',apply_enabled:false,reason:'SELECTED_SCENARIO_ONLY'}]}}
export {planningQuery}

/** Explicit manual10/day, lead8 + review2: point80, target100. A directed7
 * arrives on day9: it reduces target need24->17, but cannot cover lead stock76. */
export function dualHorizonNettingWire(request=demandRequest){
 const value=nettingWire(request),baseline=unifiedBaselineWire(request),row=baseline.rows[0]
 Object.assign(row.profile.config!,{lead_days:'8',review_days:'2'})
 Object.assign(row.target.inputs,{lead_days:'8',review_days:'2'})
 Object.assign(row.target,{lead_demand_pcs:'80',review_demand_pcs:'20',reorder_point_pcs:'80'})
 const deadline='2026-10-10T12:00:00.000001Z',leadDeadline='2026-10-08T12:00:00.000001Z'
 const supply={physical_key:workKey,snapshot_id:value.captured_at,target_key:row.target_key,size_id:row.size_id,kind:'DIRECTED',qty_pcs:'7',eta:'2026-10-09T12:00:00.000001Z',eligible:true,refs:row.refs}
 const inputs={contract_version:'cp7.net-input.v2',snapshot_id:value.captured_at,scope_id:'GLOBAL_NATIVE_PLANNING',scenario_id:'synthetic-scenario',target_key:row.target_key,size_id:row.size_id,
  deadline,lead_deadline:leadDeadline,target_pcs:'100',reorder_point_pcs:'80',available_fg_pcs:'76',supplies:[supply],refs:row.refs}
 const leadInputs={...inputs,contract_version:'cp7.net-input.v1',deadline:leadDeadline,target_pcs:'80'} as Record<string,unknown>
 delete leadInputs.lead_deadline;delete leadInputs.reorder_point_pcs
 const net={...value.rows[0].net,kernel_version:'net-dual-horizon-2',inputs,lead_net:{status:'SCENARIO',q_base_pcs:'4',q_conditional_pcs:'4',directed_on_time_pcs:'0',incoming_on_time_pcs:'0',candidate_on_time_pcs:'0',inputs:leadInputs},
  lead_position_base_pcs:'76',lead_position_conditional_pcs:'76',base_reorder_state:'AT_OR_BELOW',conditional_reorder_state:'AT_OR_BELOW'}
 return {...value,schedule_run_result:{...value.schedule_run_result,supply_run_result:{...value.schedule_run_result.supply_run_result,baseline_run_result:baseline}},rows:[{...value.rows[0],...row,net}]}
}
