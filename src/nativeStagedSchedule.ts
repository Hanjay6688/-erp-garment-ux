import {STAGED_SCHEDULE_CONTRACT,type ScheduleRequest} from './nativeProductionPlanning'

// B owns these two reviewed facades. A composes their generated types and
// shared registry entries; this exposes no general string-RPC escape.
type StagedScheduleClient={
 rpc(name:'erp_cp7_get_staged_production_schedule_v1',args:{p_source_request:string}):PromiseLike<{data:unknown;error:unknown}>
 rpc(name:'erp_cp7_save_staged_production_schedule_v1',args:{p_payload:unknown;p_request:string}):PromiseLike<{data:unknown;error:unknown}>
}
export async function readStagedSchedule(client:unknown,requestId:string){
 return await(client as StagedScheduleClient).rpc('erp_cp7_get_staged_production_schedule_v1',{p_source_request:requestId})
}
export async function saveStagedSchedule(client:unknown,request:ScheduleRequest){
 if(request.payload.staged_review_contract!==STAGED_SCHEDULE_CONTRACT)throw Error('Permintaan jadwal bertahap tidak sesuai catatan asalnya.')
 return await(client as StagedScheduleClient).rpc('erp_cp7_save_staged_production_schedule_v1',{p_payload:request.payload,p_request:request.id})
}
