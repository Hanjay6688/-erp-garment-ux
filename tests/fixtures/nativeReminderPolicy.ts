import original from './nativeAnalysisStandin.json'
import type {ReminderPolicyConfig,ReminderPolicyRequest,ReminderPolicyRow} from '../../src/nativeReminderPolicy'
// Receiver/DOM input only. Native qualification uses the real installed schema.
export const emptyReminderConfig:ReminderPolicyConfig={enabled:null,threshold_value:null,threshold_unit:'PCS',cooldown_minutes:null,quiet:{enabled:null,starts_at:null,ends_at:null,timezone:'Asia/Jakarta'}}
export function reminderPolicyFixture(analysis:unknown=original,rows:ReminderPolicyRow[]=[],request?:ReminderPolicyRequest){
 const e={contract_version:'cp7.native-rule-policy-workspace.v1',actor_scope_id:original.analysis.scope.actor_scope_id,analysis:structuredClone(analysis),allowed_rules:['ACCESSORY_NEED','AP_DUE','AR_DUE','FABRIC_NEED','PRODUCTION_GAP'],rows:structuredClone(rows),page_complete:true,total:String(rows.length),source_hash:'a'.repeat(64),read_at:'2026-10-01T10:00:00+00:00',manage_allowed:true,missing_policy:'UNCONFIGURED_NOT_ZERO_NOT_DISABLED',external_delivery_enabled:false}
 if(!request)return e
 return{...e,request_result:{request_id:request.id,run_id:request.payload.run_id,rule_id:request.payload.rule_id,scope_kind:request.payload.scope_kind,scope_key:request.payload.scope_key,status:'COMMITTED',policy_id:rows[0].policy_id,revision:(BigInt(request.payload.expected_revision)+1n).toString()}}
}
export function reminderPolicyRow(request:ReminderPolicyRequest):ReminderPolicyRow{return{policy_id:'00000000-0000-4000-8000-000000000030',rule_id:request.payload.rule_id,scope_kind:request.payload.scope_kind,scope_key:request.payload.scope_key,revision:(BigInt(request.payload.expected_revision)+1n).toString(),previous_id:request.payload.expected_revision==='0'?null:'00000000-0000-4000-8000-000000000029',config:structuredClone(request.payload.config),reason:request.payload.reason,created_at:'2026-10-01T09:59:00+00:00',created_by:original.analysis.scope.actor_scope_id}}
