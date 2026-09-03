import { describe, expect, it } from 'vitest'
import { deriveWipControlStatus, filterByWipControlStatus, type WipChildControlFacts } from './wipControlPolicy'

const terminal: WipChildControlFacts = {
  finalSkuComplete: true,
  unfinishedSewing: false,
  unsentReady: false,
  laundryDraft: false,
  laundryInTransit: false,
  unresolvedLaundryIssue: false,
  pendingFinalSkuHandoff: false,
  openDependency: false,
  operatorActionRequired: false,
}

describe('WIP control status policy', () => {
  it('completes only when every child is terminal with no remaining action', () => {
    expect(deriveWipControlStatus([terminal, terminal])).toBe('COMPLETED')
    expect(deriveWipControlStatus([])).toBe('ACTIVE')
    expect(deriveWipControlStatus([terminal, { ...terminal, finalSkuComplete: false }])).toBe('ACTIVE')
  })

  it.each([
    'unfinishedSewing', 'unsentReady', 'laundryDraft', 'laundryInTransit',
    'unresolvedLaundryIssue', 'pendingFinalSkuHandoff', 'openDependency', 'operatorActionRequired',
  ] as const)('keeps %s active', (blocker) => {
    expect(deriveWipControlStatus([{ ...terminal, [blocker]: true }])).toBe('ACTIVE')
  })

  it('filters without mutating or reclassifying rows', () => {
    const rows = [{ id: 'a', controlStatus: 'ACTIVE' as const }, { id: 'b', controlStatus: 'COMPLETED' as const }]
    expect(filterByWipControlStatus(rows, 'ACTIVE').map((row) => row.id)).toEqual(['a'])
    expect(filterByWipControlStatus(rows, 'COMPLETED').map((row) => row.id)).toEqual(['b'])
    expect(filterByWipControlStatus(rows, 'ALL')).toEqual(rows)
    expect(rows).toHaveLength(2)
  })
})
