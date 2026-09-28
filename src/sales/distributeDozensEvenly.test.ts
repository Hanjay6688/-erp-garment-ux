import { describe, expect, it } from 'vitest'
import { distributeDozensEvenly } from './distributeDozensEvenly'

describe('distributeDozensEvenly', () => {
  it('distributes one dozen evenly across three active sizes', () => {
    expect(distributeDozensEvenly(1)).toEqual([4, 4, 4])
  })

  it('uses the actual SKU membership, including a singleton and a regrouped range', () => {
    expect(distributeDozensEvenly(1, 1)).toEqual([12])
    expect(distributeDozensEvenly(1, 2)).toEqual([6, 6])
    expect(distributeDozensEvenly(1, 4)).toEqual([3, 3, 3, 3])
    expect(distributeDozensEvenly(2, 3)).toEqual([8, 8, 8])
  })

  it('requires an explicit allocation when equal whole pieces are impossible', () => {
    expect(distributeDozensEvenly(1, 5)).toBeNull()
    expect(distributeDozensEvenly(1.1, 1)).toBeNull()
    for (const sizeCount of [0, -1, 2.5, NaN, Infinity]) expect(distributeDozensEvenly(1, sizeCount)).toBeNull()
  })

  it('distributes 1.25 dozen only because it is 15 whole pieces', () => {
    expect(distributeDozensEvenly(1.25)).toEqual([5, 5, 5])
  })

  it('rejects a fractional piece result instead of silently rounding', () => {
    expect(distributeDozensEvenly(1.1)).toBeNull()
  })

  it('rejects negative input', () => {
    expect(distributeDozensEvenly(-1)).toBeNull()
  })

  it('rejects totals outside the safe-integer piece range', () => {
    expect(distributeDozensEvenly(1e20)).toBeNull()
    expect(distributeDozensEvenly(Number.MAX_SAFE_INTEGER)).toBeNull()
  })
})
