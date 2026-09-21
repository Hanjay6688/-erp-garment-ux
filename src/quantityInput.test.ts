import { describe, expect, it } from 'vitest'
import { parseQuantityInput, requireQuantityInput } from './quantityInput'

describe('quantity input respects its dimension without changing the raw value', () => {
  it.each(['-2', '1,5', '1.5', '1e3', '2+3', '+2', '', ' ', 'NaN', 'Infinity', '2147483648'])('rejects COUNT %j', (raw) => {
    expect(parseQuantityInput(raw)).toBeNull()
    expect(() => requireQuantityInput(raw)).toThrow()
  })
  it.each(['0', '2', '29', '2147483647'])('accepts exact COUNT %s', (raw) => expect(requireQuantityInput(raw)).toBe(Number(raw)))
  it.each(['1,5', '1.5', '0.000001', '29'])('accepts measured quantity %s', (raw) => {
    expect(requireQuantityInput(raw, 'MEASURE')).toBe(Number(raw.replace(',', '.')))
  })
  it.each(['-1.5', '1e3', '1.234,5', '1,234.5', '1.0000001', '1.', '.5'])('rejects ambiguous or unrepresentable measure %s', (raw) => {
    expect(parseQuantityInput(raw, 'MEASURE')).toBeNull()
  })
  it('rejects over-capacity instead of clamping, including at payload serialization', () => {
    expect(parseQuantityInput('11', 'COUNT', 10)).toBeNull()
    expect(() => requireQuantityInput('11', 'COUNT', 10)).toThrow()
  })
})
