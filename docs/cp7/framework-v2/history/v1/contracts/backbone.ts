/** Proposed CP7 boundary v1. Preparation artifact; no ERP implementation. */
export type Decimal = string; // runtime decimal pattern + exact NUMERIC conversion required
export type SourceRef = { kind: string; id: string; revision: string };
export type FactValue =
  | { state: 'KNOWN'; value: Decimal; unit: string; refs: SourceRef[] }
  | { state: 'ASSUMED'; value: Decimal; unit: string; refs: SourceRef[]; assumption_ids: string[] }
  | { state: 'UNKNOWN' | 'CONFLICT' | 'NOT_APPLICABLE'; unit: string; reason: string; refs: SourceRef[] };
export type ProductionState = 'ACTIVE' | 'PAUSED' | 'STOPPED';
export type Target =
  | { kind: 'PRODUCT'; key: string; brand_id: string; product_id: string; product_version_id: string; size_id: string }
  | { kind: 'CANDIDATE'; key: string; pattern_revision_id: string; material_constraint: string; size_id: string; finish_constraint: string; allowed_brand_ids: string[] };
export type Quality = 'COMPLETE' | 'ASSUMED' | 'UNKNOWN' | 'CONFLICT' | 'PARTIAL' | 'NOT_APPLICABLE';
export type AnalysisRequest = {
  request_id: string;
  scope_id: string;
  effective_as_of: string;
  known_as_of: string;
  knowledge_mode: 'CURRENT' | 'AS_KNOWN' | 'RESTATED';
  policy_version: string;
};
export type AnalysisResult = {
  contract_version: 'cp7.analysis.v1';
  fixture_kind?: 'SYNTHETIC_CONTRACT_ORACLE';
  run_id: string;
  status: 'COMPLETE' | 'PARTIAL' | 'BLOCKED';
  snapshot: {
    snapshot_id: string; effective_as_of: string; known_as_of: string; generated_at: string;
    timezone: 'Asia/Jakarta'; knowledge_mode: 'CURRENT' | 'AS_KNOWN' | 'RESTATED';
    capture_complete: boolean; fact_count: number; source_hash: string;
  };
  versions: { engine: string; policy: string; models: string; template: string; access_epoch: string };
  scope: { actor_scope_id: string; allocation_scope_id: string; display_filter: string };
  quality: { quantity: Quality; demand: Quality; identity: Quality; timing: Quality; materials: Quality; capacity: Quality; financial: Quality };
  scenario: { id: string; version: number; kind: 'BASE' | 'CONDITIONAL'; assumption_ids: string[] };
  assumptions: Array<{ id: string; label: string; origin: 'OWNER_INPUT' | 'TECHNICAL_FALLBACK' | 'SCENARIO'; confirmed_for_operation: boolean }>;
  dependencies: Array<{ domain: string; revision: string; completeness: Quality; fact_count: number; source_hash: string }>;
  policy_basis: { lead_time_new_days: FactValue; review_days: FactValue; buffer_mode: 'DAYS' | 'STATISTICAL'; buffer_days: FactValue; service_target: FactValue; rounding_multiple: FactValue };
  demand_models: Array<{ target_key: string; method_id: string; version: string; mode: 'FALLBACK' | 'EVALUATED'; demand_rate: FactValue; observed_days: number; stockout_days: number; unknown_days: number; horizon_days: number; selection_reason: string; validation_fold_ids: string[]; scores: Array<{ method_id: string; metric_id: string; value: FactValue }> }>;
  material_needs: Array<{ target_key: string; material_key: string | null; gross: FactValue; installed_proven: FactValue; unused_allocated_proven: FactValue; additional_external: FactValue; reason: string }>;
  capacity_checks: Array<{ stage: string; calendar_version: string; available: FactValue; existing_load: FactValue; feasible_new: FactValue; status: 'FEASIBLE' | 'INFEASIBLE' | 'ASSUMED' | 'UNKNOWN' }>;
  metrics: Array<{ metric_id: string; version: string; value: FactValue; formula_ref: string; operands: FactValue[]; readiness: 'READY' | 'LIMITED' | 'BLOCKED' }>;
  plan_comparisons: Array<{ plan_id: string; plan_version: number; metric_id: string; planned: FactValue; actual: FactValue; knowledge_mode: 'AS_KNOWN' | 'RESTATED'; interpretation: string }>;
  generation_warnings: string[];
  sources: Array<{
    source_key: string; size_id: string; stage: string; supply_kind: 'DIRECTED' | 'CANDIDATE';
    physical_remaining: FactValue; eligible_projected: FactValue; allocated: FactValue;
    eta: string | null; eta_basis: 'CONFIRMED_PLAN' | 'HISTORY' | 'ASSUMED' | 'UNKNOWN';
    match: 'CONFIRMED_TARGET' | 'CANDIDATE_MATCH' | 'NEEDS_CHECK' | 'INCOMPATIBLE' | 'UNKNOWN';
    refs: SourceRef[];
  }>;
  recommendations: Array<{
    target: Target; production_state: ProductionState; actual_fg: FactValue; target_qty: FactValue;
    q_base: FactValue; q_conditional: FactValue; suggested_new: FactValue; rounding_extra: FactValue;
    reason_codes: string[]; assumption_ids: string[];
  }>;
  timeline: Array<{ date: string; target_key: string; demand: Decimal; directed_supply: Decimal; candidate_supply: Decimal; proposed_new_supply: Decimal; balance_end: Decimal; mode: 'BACKLOG' | 'LOST_SALES'; assumed: boolean }>;
  actions: Array<{ key: string; intent: string; source_keys: string[]; target_keys: string[]; primary_reason: string; conditional: boolean; source_links: SourceRef[] }>;
  financial_readiness: 'READY' | 'LIMITED' | 'BLOCKED';
  stale: { is_stale: boolean; reasons: string[] };
  semantic_hash: string;
};
export type ApplyPlanActionRequest = {
  draft_id: string; draft_version: number; action_id: string;
  request_id: string; payload_hash: string;
  expected_dependency_hash: string; confirmed_review: true;
};
export type ApplyResult =
  | { outcome: 'APPLIED' | 'REPLAY'; request_id: string; domain_refs: SourceRef[]; refetch_required: true }
  | { outcome: 'REFUSED'; request_id: string; code: 'STALE' | 'UNAUTHORIZED' | 'CAPACITY_CHANGED' | 'PRODUCTION_STOPPED' | 'PAYLOAD_MISMATCH' | 'RECOVERY_PENDING'; effects: 0 }
  | { outcome: 'VERIFYING'; request_id: string; retry_policy: 'SAME_ID_SAME_PAYLOAD_ONLY'; writer_fenced: true };
