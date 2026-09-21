// Preserve the input string in the form. Separators are decimal separators,
// never thousands separators; COUNT cannot contain a fraction or exponent.
export function parseQuantityInput(raw: string | number, dimension: 'COUNT' | 'MEASURE' = 'COUNT', max = dimension === 'COUNT' ? 2_147_483_647 : Number.MAX_SAFE_INTEGER): number | null {
  const value = String(raw).trim()
  if (!(dimension === 'COUNT' ? /^\d+$/ : /^\d+(?:[.,]\d{1,6})?$/).test(value)) return null
  const parsed = Number(value.replace(',', '.'))
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > max || (dimension === 'COUNT' && !Number.isSafeInteger(parsed))) return null
  const canonical = value.replace(',', '.').replace(/^0+(?=\d)/, '').replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '')
  if (dimension === 'MEASURE' && String(parsed) !== canonical) return null
  return parsed
}

export function requireQuantityInput(raw: string | number, dimension: 'COUNT' | 'MEASURE' = 'COUNT', max?: number) {
  const value = parseQuantityInput(raw, dimension, max)
  if (value === null) throw new Error(dimension === 'COUNT' ? 'Qty PCS harus bilangan bulat dalam batas sumber.' : 'Qty bahan harus angka positif dengan maksimal 6 desimal.')
  return value
}
