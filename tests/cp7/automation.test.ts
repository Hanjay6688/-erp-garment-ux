import { describe, expect, it } from 'vitest'
import {
  previewAutomation,
  type AutomationContext,
  type AutomationSignal,
} from '../../docs/cp7/prototypes/automation'

const context: AutomationContext = {
  allocationScopeId: 'fixture-allocation-scope',
  policyVersion: 'fixture-policy-v1',
  activeModelVersion: 'fixture-model-v1',
  trainingEvidence: 'UNKNOWN',
}
const change = (revision = '1'): Extract<AutomationSignal, { kind: 'SOURCE_CHANGE' }> => ({
  kind: 'SOURCE_CHANGE', committed: true,
  source: { kind: 'fixture-fact', id: 'fixture-source', revision },
})
const review: Extract<AutomationSignal, { kind: 'SCHEDULE_OCCURRENCE' }> = {
  kind: 'SCHEDULE_OCCURRENCE', scheduleId: 'fixture-schedule',
  scheduleRevision: '1', occurrenceId: 'fixture-occurrence',
  enabled: true, purpose: 'REVIEW_MODEL',
}

describe('CP7 automation seam — fixture proposals, never operational work', () => {
  it('does not derive posted analysis from an uncommitted source', () => {
    const result = previewAutomation({ ...change(), committed: false }, context)
    expect(result).toMatchObject({
      outcome: 'SUPPRESSED', reason: 'UNCOMMITTED_SOURCE',
      proposedRequestKey: null, proposedWork: [], operational: false,
    })
  })

  it('refreshes the shared analysis without retraining for each committed change', () => {
    const result = previewAutomation(change(), { ...context, trainingEvidence: 'NEW_ELIGIBLE_DATA' })
    expect(result.proposedWork).toEqual([
      'CAPTURE_COHERENT_SNAPSHOT', 'COMPUTE_SHARED_ANALYSIS', 'OBSERVE_CONDITIONS',
    ])
    expect(result.operational).toBe(false)
  })

  it('replay preserves a proposed identity, while a correction gets a new identity', () => {
    const first = previewAutomation(change(), context)
    expect(previewAutomation(change(), context).proposedRequestKey).toBe(first.proposedRequestKey)
    expect(previewAutomation(change('2'), context).proposedRequestKey).not.toBe(first.proposedRequestKey)
  })

  it('does not collapse allocation scopes, policy changes, or model changes', () => {
    const original = previewAutomation(change(), context).proposedRequestKey
    for (const modified of [
      { ...context, allocationScopeId: 'another-scope' },
      { ...context, policyVersion: 'fixture-policy-v2' },
      { ...context, activeModelVersion: 'fixture-model-v2' },
    ]) expect(previewAutomation(change(), modified).proposedRequestKey).not.toBe(original)
  })

  it('keeps source IDs distinct even when they contain separators', () => {
    const a = previewAutomation({
      kind: 'SOURCE_CHANGE', committed: true,
      source: { kind: 'a:b', id: 'c', revision: '1' },
    }, context)
    const b = previewAutomation({
      kind: 'SOURCE_CHANGE', committed: true,
      source: { kind: 'a', id: 'b:c', revision: '1' },
    }, context)
    expect(a.proposedRequestKey).not.toBe(b.proposedRequestKey)
  })

  it('a disabled schedule cannot propose work, even with enough training data', () => {
    expect(previewAutomation({ ...review, enabled: false }, {
      ...context, trainingEvidence: 'NEW_ELIGIBLE_DATA',
    })).toMatchObject({ outcome: 'SUPPRESSED', reason: 'SCHEDULE_DISABLED', proposedWork: [] })
  })

  it.each(['UNKNOWN', 'INSUFFICIENT'] as const)('blocks model review when evidence is %s', trainingEvidence => {
    expect(previewAutomation(review, { ...context, trainingEvidence })).toMatchObject({
      outcome: 'BLOCKED', reason: 'TRAINING_EVIDENCE_REQUIRED', proposedWork: [],
    })
  })

  it('does not train the same history merely because a timer fired again', () => {
    expect(previewAutomation(review, { ...context, trainingEvidence: 'NO_NEW_DATA' })).toMatchObject({
      outcome: 'SUPPRESSED', reason: 'NO_NEW_TRAINING_DATA', proposedWork: [],
    })
  })

  it('eligible training only proposes evaluation; it never promotes a model or writes production', () => {
    const result = previewAutomation(review, { ...context, trainingEvidence: 'NEW_ELIGIBLE_DATA' })
    expect(result).toMatchObject({ mode: 'SHELL_ONLY', operational: false, outcome: 'PROPOSED' })
    expect(result.proposedWork).toEqual(['CAPTURE_COHERENT_SNAPSHOT', 'EVALUATE_MODEL_CANDIDATE'])
    expect(result.requiredIntegration).toContain('ACCEPTED_CP6_BASE_AND_FINAL_SOURCE_CONTRACT')
  })

  it('a later schedule occurrence or edited schedule gets a distinct proposed identity', () => {
    const evidence = { ...context, trainingEvidence: 'NEW_ELIGIBLE_DATA' as const }
    const first = previewAutomation(review, evidence).proposedRequestKey
    expect(previewAutomation({ ...review, occurrenceId: 'next-occurrence' }, evidence)
      .proposedRequestKey).not.toBe(first)
    expect(previewAutomation({ ...review, scheduleRevision: '2' }, evidence)
      .proposedRequestKey).not.toBe(first)
  })

  it('manual refresh does not enable background execution', () => {
    expect(previewAutomation({ kind: 'MANUAL_REQUEST', requestId: 'fixture-request', purpose: 'REFRESH_ANALYSIS' }, context))
      .toMatchObject({ outcome: 'PROPOSED', mode: 'SHELL_ONLY', operational: false })
  })
})
