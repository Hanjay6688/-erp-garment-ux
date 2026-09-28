export type SkuLot = { lot_id: string; lot_number: string; product_id: string; size: string; location_id: string; grade: string; qty: string; value: string | null; provisional: boolean; cost_state: string | null; hpp_version_id: string | null }
export type SkuHpp = { group_key: string; sku: string; brand_name: string; qty: string; value: string | null; hpp_per_pcs: string | null; provisional: boolean; lots: SkuLot[] }
export type SkuHppWorkspace = { at: string; page: number; page_size: number; total: number; groups: SkuHpp[] }
export function skuObject(v: unknown): Record<string, unknown> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) throw new Error('Data SKU tidak lengkap.')
  return v as Record<string, unknown>
}
const decimal = (v: unknown) => typeof v === 'string' && /^-?\d+(\.\d+)?$/.test(v)
export function skuMoney(v: string | null): string {
  if (v === null) return 'Belum tersedia'
  if (!decimal(v)) throw new Error('Nilai uang tidak valid.')
  const negative = v.startsWith('-'), [whole, part = ''] = v.replace(/^-/, '').split('.')
  const cents = BigInt(whole) * 100n + BigInt(part.padEnd(3, '0').slice(0, 2)) + (Number(part[2] ?? '0') >= 5 ? 1n : 0n)
  return `${negative ? '−' : ''}Rp${(cents / 100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${(cents % 100n).toString().padStart(2, '0')}`
}
export function parseSkuHpp(v: unknown): SkuHppWorkspace {
  const w = skuObject(v)
  if (typeof w.at !== 'string' || !Number.isFinite(Date.parse(w.at)) || !Number.isSafeInteger(w.page) || Number(w.page) < 1
    || w.page_size !== 50 || !Number.isSafeInteger(w.total) || Number(w.total) < 0 || !Array.isArray(w.groups)) throw new Error('Daftar HPP SKU tidak valid.')
  const keys = new Set<string>()
  for (const x of w.groups) {
    const g = skuObject(x)
    if (typeof g.group_key !== 'string' || keys.has(g.group_key) || typeof g.sku !== 'string' || typeof g.brand_name !== 'string'
      || typeof g.qty !== 'string' || !/^-?\d+$/.test(g.qty) || !Array.isArray(g.lots) || typeof g.provisional !== 'boolean'
      || !(g.value === null || decimal(g.value)) || !(g.hpp_per_pcs === null || decimal(g.hpp_per_pcs))) throw new Error('Ringkasan HPP tidak valid.')
    keys.add(g.group_key)
    let qty = 0n
    const lots = new Set<string>()
    for (const x of g.lots) {
      const l = skuObject(x), key = `${l.lot_id}:${l.product_id}:${l.location_id}:${l.grade}`
      if (!['lot_id', 'lot_number', 'product_id', 'size', 'location_id', 'grade'].every(k => typeof l[k] === 'string')
        || typeof l.qty !== 'string' || !/^-?\d+$/.test(l.qty) || !(l.value === null || decimal(l.value))
        || typeof l.provisional !== 'boolean' || lots.has(key)) throw new Error('Rincian stok tidak valid.')
      lots.add(key); qty += BigInt(l.qty)
    }
    if (qty !== BigInt(g.qty) || (qty === 0n && g.hpp_per_pcs !== null)) throw new Error('Total stok tidak cocok dengan rincian ukuran.')
  }
  return w as SkuHppWorkspace
}
