import { describe, expect, it } from 'vitest'
import { alignSizeQuantities } from './sizeQuantities'
describe('physical size continuity', () => {
  it('keeps a fourth size and reordered partial receipts on their original sizes', () => {
    const target = ['31', '32', '33', '34']
    const a = alignSizeQuantities(['34', '32'], [7, 5], target)
    const b = alignSizeQuantities(['31', '33'], [4, 2], target)
    expect(a.map((qty, i) => qty + b[i])).toEqual([4, 5, 2, 7])
    expect(alignSizeQuantities(['27'], [12], ['27'])).toEqual([12])
  })
  it('refuses a missing receiver, duplicate identity or malformed quantity vector', () => {
    expect(() => alignSizeQuantities(['34'], [7], ['31', '32', '33'])).toThrow()
    expect(() => alignSizeQuantities(['31', '31'], [4, 5], ['31'])).toThrow()
    expect(() => alignSizeQuantities(['27'], [], ['27'])).toThrow()
    expect(() => alignSizeQuantities(['27'], [1.5], ['27'])).toThrow()
  })
})
