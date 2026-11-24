/** Proposed notification boundary only. No worker, network calls, credentials or provider chosen. */
export type SourceRef = { kind: string; id: string; revision: string };
export type Channel = 'IN_APP' | 'WHATSAPP';
export type ConditionKind = 'PRODUCTION' | 'ACCESSORY' | 'AR' | 'AP' | 'MANUAL';
export type ConditionEpisode = {
  id: string; condition_key: string; rule_version: string; source_refs: SourceRef[];
  kind: ConditionKind; run_id: string; scope_id: string;
  source_state: 'ACTIVE' | 'RECOVERED' | 'UNKNOWN' | 'DISABLED';
  attention: 'UNSEEN' | 'ACKNOWLEDGED' | 'SNOOZED';
  first_seen_at: string; observed_at: string; due_at: string | null;
  severity: string; action_keys: string[]; quality_reason: string | null;
};
export type Schedule = {
  id: string; version: number; enabled: boolean; timezone: 'Asia/Jakarta';
  mode: 'DAILY' | 'WEEKDAYS' | 'ONCE' | 'DUE_OFFSET';
  config: { local_time: string; weekdays: number[]; once_at: string | null; due_offset_days: number | null };
  quiet_policy_id: string; catch_up_policy_id: string; expiry_seconds: number;
  binding_ids: string[]; next_three_instants: string[];
};
export type RecipientBinding = {
  id: string; version: number; principal_id: string; channel: Channel;
  destination_ref: string; // private verified reference, never raw secret in browser payload
  ownership_verified_at: string | null; opt_in_at: string | null; revoked_at: string | null;
  allowed_scope_id: string; access_epoch: string;
};
export type NotificationEnvelope = {
  intent_id: string; environment_id: string; occurrence_id: string;
  binding_id: string; binding_version: number; channel: Channel;
  schedule_id: string; schedule_version: number; run_id: string; episode_ids: string[];
  source_revision_hash: string; policy_version: string; template_version: string; access_epoch: string;
  scheduled_for: string; evaluated_at: string; expires_at: string;
  authorized_payload: { subject: string; body: string; authenticated_deep_link: string | null };
  payload_hash: string; // immutable after a possibly sent attempt; not part of uniqueness key
};
export type AdapterCapabilities = {
  provider_id: string; config_version: string;
  idempotency: boolean; status_lookup: boolean; delivery_receipt: boolean; read_receipt: boolean;
  max_payload_bytes: number; rate_policy_ref: string; callback_verification_ref: string | null;
  approved_destination_types: string[]; configuration_verified_at: string | null;
};
export type DeliveryAttempt = {
  id: string; intent_id: string; attempt_no: number; payload_hash: string;
  lease_token: string; fencing_epoch: number; request_may_have_left_at: string | null;
  provider_message_id: string | null; dispatched_at: string | null;
  state: 'QUEUED' | 'CLAIMED' | 'SUPPRESSED' | 'ACCEPTED' | 'DELIVERED' | 'READ'
    | 'DEFINITIVELY_REJECTED' | 'FAILED_BEFORE_SEND' | 'UNKNOWN' | 'EXPIRED';
  evidence_ref: string | null; safe_retry_after: string | null;
};
export type ChannelReadiness = {
  contract: 'READY' | 'INCOMPLETE'; local_sink: 'NOT_RUN' | 'PASS' | 'FAIL';
  provider: 'NOT_SELECTED' | 'CONFIGURED'; authorized_test: 'NOT_RUN' | 'ACCEPTED' | 'FAILED' | 'UNKNOWN';
  delivery: 'NOT_RUN' | 'VERIFIED' | 'UNSUPPORTED' | 'UNKNOWN'; live_enabled: boolean;
};
// Runtime constraints: intent uniqueness=(environment,occurrence,binding,channel);
// recheck current permission/source before dispatch; monotonic claim fencing;
// provider ACCEPTED != delivered; no domain writes from ACK/send/callback.
