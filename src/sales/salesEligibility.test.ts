import { describe, expect, it } from 'vitest'
import { isSellableGoodAtLocation, parseManualPieceQuantity } from './salesEligibility'

describe('sales FG eligibility', () => {
  it('requires the selected location and GOOD grade together', () => {
    expect(isSellableGoodAtLocation({ location: 'Gudang FG Utama', grade: 'Good' }, 'Gudang FG Utama')).toBe(true)
    expect(isSellableGoodAtLocation({ location: 'Gudang FG Cadangan', grade: 'Good' }, 'Gudang FG Utama')).toBe(false)
    expect(isSellableGoodAtLocation({ location: 'Gudang FG Utama', grade: 'BS' }, 'Gudang FG Utama')).toBe(false)
  })
})

describe('manual piece quantity parsing', () => {
  it('accepts only safe non-negative whole pieces', () => {
    expect(parseManualPieceQuantity('12')).toBe(12)
    expect(parseManualPieceQuantity('0012')).toBe(12)
    expect(parseManualPieceQuantity('')).toBe(0)
  })

  it('rejects coercion, fractions, negatives, infinity, and unsafe integers', () => {
    for (const value of ['-1', '1.5', '1e3', 'Infinity', '9007199254740992']) {
      expect(parseManualPieceQuantity(value)).toBeNull()
    }
  })
})
