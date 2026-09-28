import { expect, it } from 'vitest'
import type { AnalysisResult, FactValue } from '../../src/cp7/contract'
import { frameworkExample } from '../../src/cp7/fixture'
import { assertFixtureCoherence, projectShell } from '../../src/cp7/workspace'
import { previewWhatsApp } from '../../src/cp7/notification'

it.each(['KNOWN', 'ASSUMED', 'UNKNOWN'] as const)('restricts the entire comparison for %s facts through every access transition', state => {
  const source: AnalysisResult = structuredClone(frameworkExample)
  const ref = { kind: 'COST', id: 'private-comparison-source', revision: '1' }
  const fact = (unit: string): FactValue => state === 'UNKNOWN'
    ? { state, unit, reason: 'private-comparison-reason', refs: [ref] }
    : { state, unit, value: '987654321.09', refs: [ref], ...(state === 'ASSUMED' ? { assumption_ids: [source.assumptions[0].id] } : {}) }
  // Currency is not a permission: financial ratios and unclassified metrics
  // must not bypass the restriction by using a different unit or metric ID.
  source.plan_comparisons = [['COST', 'IDR'], ['GROSS_MARGIN_RATE', '%'], ['UNCLASSIFIED', 'USD']].map(([metric_id, unit]) => ({
    plan_id: 'private-comparison-plan', plan_version: 1, metric_id,
    planned: fact(unit), actual: fact(unit), knowledge_mode: 'RESTATED',
    interpretation: 'private-comparison-interpretation Rp987.654.321,09',
  }))
  assertFixtureCoherence(source)
  const original = structuredClone(source)
  const shell = { kind: 'READY' as const, analysis: source, message: 'fixture' }
  for (const access of ['OWNER', 'OPERATIONS', 'DENIED', 'OPERATIONS', 'OWNER'] as const) {
    const view = projectShell(shell, access)
    if (access === 'OWNER') {
      expect(view.analysis).toEqual(original)
      expect(view.analysis).not.toBe(source)
    } else {
      for (const output of [JSON.stringify(view), view.report, view.prompt, previewWhatsApp(view)]) {
        expect(output).not.toMatch(/987654321|987\.654\.321|private-comparison/)
      }
      if (access === 'OPERATIONS') {
        expect(view.analysis?.plan_comparisons).toEqual([])
        expect(view.rows).toEqual(original.recommendations)
        expect(view.analysis?.allocation_edges).toEqual(original.allocation_edges)
        expect(view.actions).toHaveLength(original.actions.length)
      } else {
        expect(view).toEqual({ analysis: null, rows: [], actions: [], report: '', prompt: '', denied: true })
        expect(previewWhatsApp(view)).toBe('')
      }
    }
    expect(source).toEqual(original)
  }
})
