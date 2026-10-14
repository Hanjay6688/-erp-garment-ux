import { describe, expect, it } from 'vitest'
import { micro, microText, returnValueCents, rupiah } from './cuttingReturnContract'

describe('exact fabric return arithmetic', () => {
  it('keeps six decimal places without floats', () => {
    expect(micro('1.25')).toBe(1_250_000n); expect(micro('0.000001')).toBe(1n); expect(micro('1.2345678')).toBeNull()
    expect(micro('-1')).toBeNull(); expect(micro('01')).toBeNull(); expect(microText(2_500_000n)).toBe('2.5'); expect(microText(3_000_000n)).toBe('3')
  })
  it('values a line like the Native journal: half up to cents, nothing at or below half a cent', () => {
    expect(returnValueCents('1.25', '10000.000000')).toBe(1_250_000n)
    expect(returnValueCents('0.333333', '0.03')).toBe(1n) // 0.00999999 -> 0.01
    expect(returnValueCents('1', '0.005')).toBe(0n) // exactly half a cent: no Native journal line
    expect(returnValueCents('1', '0.005001')).toBe(1n)
    expect(returnValueCents('2', null)).toBe(0n)
    expect(rupiah(1_250_000n)).toBe('Rp12.500,00'); expect(rupiah(5n)).toBe('Rp0,05')
  })
})
