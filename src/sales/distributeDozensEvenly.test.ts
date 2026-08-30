import { describe, expect, it } from 'vitest'
import { distributeDozensEvenly } from './distributeDozensEvenly'

describe('distributeDozensEvenly', () => {
  it('distributes one dozen evenly across three active sizes', () => {
    expect(distributeDozensEvenly(1)).toEqual([4, 4, 4])
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
