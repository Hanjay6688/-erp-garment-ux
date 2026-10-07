import { describe, expect, it } from 'vitest'
import { matchesSearch, searchTokens, searchValues } from './search'

describe('matchesSearch', () => {
  it('matches every word anywhere in the displayed fields, in any order', () => {
    const row = ['BATCH DISTRIBUSI 02B', '25 pcs', 'Siap laundry', 'BS bahan · cuci warna hitam']
    expect(matchesSearch('siap laundry 25', ...row)).toBe(true)
    expect(matchesSearch('hitam 02b', ...row)).toBe(true)
    expect(matchesSearch('putih', ...row)).toBe(false)
  })
  it('treats an empty query as no filter and ignores empty parts', () => {
    expect(matchesSearch('   ', 'x')).toBe(true)
    expect(matchesSearch('vivo', null, undefined, false, ['Vivo · Classic'])).toBe(true)
    expect(searchTokens('  Siap   Diambil ')).toEqual(['siap', 'diambil'])
  })
  it('compares case- and accent-insensitively', () => {
    expect(matchesSearch('SINARAN', 'Sinaran')).toBe(true)
    expect(matchesSearch('cafe', 'Café Denim')).toBe(true)
  })
})

describe('searchValues', () => {
  it('turns a row into searchable text, including id-ID formatted numbers and nested values', () => {
    const row = { number:'INV-260827-019', gross:6480000, lines:[{ sku:'73001', qty:12 }], due:'26 Sep 2026', paid:false }
    expect(matchesSearch('6.480.000', searchValues(row))).toBe(true)
    expect(matchesSearch('73001 26 sep', searchValues(row))).toBe(true)
    expect(searchValues(row)).not.toContain('false')
  })
})
