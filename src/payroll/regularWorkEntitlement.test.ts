import { describe, expect, it } from 'vitest'
import { calculateRegularWorkEntitlement } from './regularWorkEntitlement'

describe('calculateRegularWorkEntitlement', () => {
  it('keeps every sewn piece in gross pay and holds only uninstalled stuck components', () => {
    const result = calculateRegularWorkEntitlement({
      sewnQty: 200,
      fullRate: 17_800,
      bsQty: 0,
      bsComponents: [],
      stuckQty: 20,
      stuckComponents: [
        { name: 'Ceming', rate: 2_500 },
        { name: 'Kancing', rate: 500 },
        { name: 'Lipat', rate: 400 },
      ],
    })

    expect(result.gross).toBe(3_560_000)
    expect(result.stuckDeduction).toBe(68_000)
    expect(result.subtotal).toBe(3_492_000)
  })

  it('keeps BS and Stuck component holds separate and additive', () => {
    const result = calculateRegularWorkEntitlement({
      sewnQty: 200,
      fullRate: 17_800,
      bsQty: 5,
      bsComponents: [{ name: 'Ceming', rate: 2_500 }],
      stuckQty: 20,
      stuckComponents: [{ name: 'Lipat', rate: 400 }],
    })

    expect(result.bsDeduction).toBe(12_500)
    expect(result.stuckDeduction).toBe(8_000)
    expect(result.totalDeduction).toBe(20_500)
    expect(result.subtotal).toBe(3_539_500)
  })
})
