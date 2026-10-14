import { describe, expect, it } from 'vitest'
import { dozensText, seriesTotal, splitSeriesDozens } from './seriesDozens'

describe('owner D14-5: dozens across one size series, both ways', () => {
  it('reads per-size pieces back as dozens and pieces (4/5/4 is 1 lusin 1 potong)', () => {
    expect(dozensText(seriesTotal(['4', '5', '4'])!)).toBe('1 lusin 1 potong')
    expect(dozensText(seriesTotal(['4', '4', '4'])!)).toBe('1 lusin')
    expect(dozensText(seriesTotal(['5'])!)).toBe('5 potong')
    expect(dozensText(seriesTotal(['12', '12', '13'])!)).toBe('3 lusin 1 potong')
  })
  it('waits while a size is still empty or not a whole number', () => {
    expect(seriesTotal(['4', '', '4'])).toBeNull()
    expect(seriesTotal(['4', '1.5', '4'])).toBeNull()
    expect(seriesTotal([])).toBeNull()
  })
  it('splits dozens evenly over the sizes of the series', () => {
    expect(splitSeriesDozens('1', '', 3)).toEqual({ ok: true, perSize: '4', total: 12n })
    expect(splitSeriesDozens('2', '0', 4)).toEqual({ ok: true, perSize: '6', total: 24n })
    expect(splitSeriesDozens('1', '3', 5)).toEqual({ ok: true, perSize: '3', total: 15n })
  })
  it('refuses an uneven split with a plain sentence instead of rounding', () => {
    expect(splitSeriesDozens('1', '1', 3)).toEqual({ ok: false, message: '1 lusin 1 potong (13 PCS) tidak bisa dibagi rata ke 3 ukuran. Isi per ukuran, atau ubah jumlahnya.' })
    expect(splitSeriesDozens('1', '', 5).ok).toBe(false)
  })
  it('refuses fractions, a twelfth piece and zero', () => {
    expect(splitSeriesDozens('1.5', '', 3).ok).toBe(false)
    expect(splitSeriesDozens('1', '12', 3).ok).toBe(false)
    expect(splitSeriesDozens('0', '0', 3)).toEqual({ ok: false, message: 'Jumlah lusin masih nol.' })
  })
})
