export const money = (value: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value)

export { dozenPieces } from '../fgQuantity'

export const parseDecimal = (value: string) => {
  const parsed = Number(value.trim().replace(/\s/g, '').replace(',', '.'))
  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0
}

export const cleanDecimalInput = (value: string, decimalPlaces = 2) => {
  const compact = value.replace(/\./g, ',').replace(/[^0-9,]/g, '')
  const [rawInteger = '', ...rawDecimals] = compact.split(',')
  const integer = rawInteger.replace(/^0+(?=\d)/, '')
  if (rawDecimals.length === 0) return integer
  return `${integer || '0'},${rawDecimals.join('').slice(0, decimalPlaces)}`
}

export const formatQuantity = (value: number, digits = 1) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: digits }).format(value)
