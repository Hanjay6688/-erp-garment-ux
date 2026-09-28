/**
 * Executable contract prototype, S0 only. This is a pure, typed fixture planner,
 * not a scheduler, an RPC parser, authorization, or a production worker.
 * No CP6 event/table names, numerical policies, or active schedules are assumed.
 */
export type AnalysisWork =
  | 'CAPTURE_COHERENT_SNAPSHOT'
  | 'COMPUTE_SHARED_ANALYSIS'
  | 'OBSERVE_CONDITIONS'
  | 'EVALUATE_MODEL_CANDIDATE'

export type AnalysisPurpose = 'REFRESH_ANALYSIS' | 'REVIEW_MODEL'

export type AutomationSignal =
  | {
    kind: 'SOURCE_CHANGE'
    committed: boolean
    source: { kind: string; id: string; revision: string }
  }
  | {
    kind: 'MANUAL_REQUEST'
    requestId: string
    purpose: AnalysisPurpose
  }
  | {
    kind: 'SCHEDULE_OCCURRENCE'
    scheduleId: string
    scheduleRevision: string
    occurrenceId: string
    enabled: boolean
    purpose: AnalysisPurpose
  }

export type AutomationContext = {
  /** Authoritative allocation scope; never a temporary UI display filter. */
  allocationScopeId: string
  policyVersion: string
  activeModelVersion: string
  /** Evidence supplied by a future eligibility evaluator; no magic row count. */
  trainingEvidence: 'NEW_ELIGIBLE_DATA' | 'NO_NEW_DATA' | 'INSUFFICIENT' | 'UNKNOWN'
}

export type AutomationPreview = {
  mode: 'SHELL_ONLY'
  operational: false
  outcome: 'PROPOSED' | 'SUPPRESSED' | 'BLOCKED'
  reason:
    | 'ANALYSIS_REFRESH_PROPOSED'
    | 'MODEL_EVALUATION_PROPOSED'
    | 'UNCOMMITTED_SOURCE'
    | 'SCHEDULE_DISABLED'
    | 'NO_NEW_TRAINING_DATA'
    | 'TRAINING_EVIDENCE_REQUIRED'
  /** Stable fixture identity. NOT a durable dedupe receipt or a queue claim. */
  proposedRequestKey: string | null
  proposedWork: AnalysisWork[]
  requiredIntegration: readonly string[]
}

const requiredIntegration = Object.freeze([
  'ACCEPTED_CP6_BASE_AND_FINAL_SOURCE_CONTRACT',
  'SERVER_AUTHORIZATION_AND_COHERENT_SNAPSHOT',
  'NATIVE_ENGINE_AND_CONDITION_EVALUATOR_PROOFS',
  'CP7C_SCHEDULER_QUEUE_WORKER_ACCEPTANCE_FOR_AUTOMATION',
])

/** No timers, network, persistence, callbacks, business writes, or model promotion. */
export function previewAutomation(
  signal: AutomationSignal,
  context: AutomationContext,
): AutomationPreview {
  const base = {
    mode: 'SHELL_ONLY' as const,
    operational: false as const,
    requiredIntegration,
  }

  if (signal.kind === 'SOURCE_CHANGE' && !signal.committed) return {
    ...base, outcome: 'SUPPRESSED', reason: 'UNCOMMITTED_SOURCE',
    proposedRequestKey: null, proposedWork: [],
  }
  if (signal.kind === 'SCHEDULE_OCCURRENCE' && !signal.enabled) return {
    ...base, outcome: 'SUPPRESSED', reason: 'SCHEDULE_DISABLED',
    proposedRequestKey: null, proposedWork: [],
  }

  const purpose = signal.kind === 'SOURCE_CHANGE' ? 'REFRESH_ANALYSIS' : signal.purpose
  if (purpose === 'REVIEW_MODEL' && context.trainingEvidence !== 'NEW_ELIGIBLE_DATA') {
    return {
      ...base,
      outcome: context.trainingEvidence === 'NO_NEW_DATA' ? 'SUPPRESSED' : 'BLOCKED',
      reason: context.trainingEvidence === 'NO_NEW_DATA'
        ? 'NO_NEW_TRAINING_DATA' : 'TRAINING_EVIDENCE_REQUIRED',
      proposedRequestKey: null, proposedWork: [],
    }
  }

  // An array encoding keeps separator-bearing IDs distinct. Identity remains
  // proposed until final server contracts define persistence and replay rules.
  const signalIdentity = signal.kind === 'SOURCE_CHANGE'
    ? [signal.kind, signal.source.kind, signal.source.id, signal.source.revision]
    : signal.kind === 'MANUAL_REQUEST'
      ? [signal.kind, signal.requestId]
      : [signal.kind, signal.scheduleId, signal.scheduleRevision, signal.occurrenceId]
  const proposedRequestKey = JSON.stringify([
    'cp7.automation.preview.v1', context.allocationScopeId,
    context.policyVersion, context.activeModelVersion, purpose, signalIdentity,
  ])

  return purpose === 'REFRESH_ANALYSIS' ? {
    ...base, outcome: 'PROPOSED', reason: 'ANALYSIS_REFRESH_PROPOSED',
    proposedRequestKey,
    proposedWork: ['CAPTURE_COHERENT_SNAPSHOT', 'COMPUTE_SHARED_ANALYSIS', 'OBSERVE_CONDITIONS'],
  } : {
    ...base, outcome: 'PROPOSED', reason: 'MODEL_EVALUATION_PROPOSED',
    proposedRequestKey,
    proposedWork: ['CAPTURE_COHERENT_SNAPSHOT', 'EVALUATE_MODEL_CANDIDATE'],
  }
}
