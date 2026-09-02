import { describe, expect, it } from 'vitest'
import { regularFgNotaCardId, selectRegularFgNotaSources } from './fgNota'

describe('regular FG Nota source identity', () => {
  it('recognizes one regular payroll source across repeated QC completions', () => {
    const completionTwo = { parentId:'POT-001', batchId:'001-01', completionCount:2, qty:80 }
    const completionOne = { parentId:'POT-001', batchId:'001-01', completionCount:1, qty:100 }
    const otherBatch = { parentId:'POT-001', batchId:'001-02', completionCount:1, qty:20 }

    const selected = selectRegularFgNotaSources([completionTwo, completionOne, otherBatch])

    expect(selected).toEqual([completionOne, otherBatch])
    expect(regularFgNotaCardId(completionOne)).toBe('qc-POT-001-001-01')
    expect(regularFgNotaCardId(completionTwo)).toBe(regularFgNotaCardId(completionOne))
  })
})
