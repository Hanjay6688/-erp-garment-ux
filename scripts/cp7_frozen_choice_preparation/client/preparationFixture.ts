import {analogContext} from '../../../tests/fixtures/nativeProductAnalog'
const context=()=>({...analogContext(),sourceMethod:'FROZEN_V2' as const})
export function prepReply(state='QUEUED'){
 const c=context()
 return{contract_version:'cp7.frozen-choice-preparation.v1',source_request:c.requestId,run_id:c.runId,reference:{captured_at:c.reference.capturedAt,source_hash:c.reference.sourceHash},state,stage:'FROZEN_INPUTS',units_done:state==='READY'?1:0,unit_count:1,created_at:'2026-10-26T01:00:00.123456Z',last_progress_at:'2026-10-26T01:00:01.123456Z',unit_attempts:0,worker_active:state==='RUNNING',failure_code:state==='FAILED'?'CP7_CHOICE_PREPARATION_FAILED':null,failure_sqlstate:state==='FAILED'?'22012':null,choice_saved:false,production_go:false}
}
