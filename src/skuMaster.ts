import { skuObject } from './skuHpp'
import type { Json } from './types/database.preconnect'
export type SkuBom = { category_id: string; qty_per_good_fg_base: string | number; hpp_method: string; hpp_standard_rate?: string | number | null; hpp_uom_code?: string | null; reimbursement_rate: string | number; reimbursement_uom_code: string; notes?: string | null }
export type SkuWork = { contractor_id?: string | null; work_component_id: string; rate: string | number; special?: boolean }
export type SkuLaundry = { vendor_id: string; kind: string; ref_id: string; rate_status: string; rate: string | number | null; reason: string | null }
export type SkuSettings = { price: string | number | null; bom: SkuBom[] | null; work_rates: SkuWork[]; laundry_rates: SkuLaundry[] }
export type SkuMember = { id: string; size_id: string; size: string }
export type SkuGroup = { id: string; sku: string; brand_id: string; brand_name: string; model_id: string; model_name: string; color_name: string; revision: string; effective_from: string; members: SkuMember[]; settings: SkuSettings | null }
export type SkuProduct = SkuMember & { sku: string; brand_id: string; brand_name: string; model_id: string; model_name: string; color_name: string; group_id: string | null }
export type SkuLookup = { id: string; name: string; unit?: string; category?: string; kind?: string; vendor_id?: string | null }
export type SkuMasterWorkspace = { at: string; page: number; page_size: number; groups_total: number; products_total: number; can_edit: boolean; groups: SkuGroup[]; related_groups: SkuGroup[]; products: SkuProduct[]; selected_products: SkuProduct[]; legacy_basis: Json[] | null; lookups: { accessories: SkuLookup[]; work: SkuLookup[]; contractors: SkuLookup[]; vendors: SkuLookup[]; laundry: SkuLookup[] } | null }
export const emptySkuSettings = (): SkuSettings => ({ price: null, bom: null, work_rates: [], laundry_rates: [] })
export function parseSkuMaster(v: unknown): SkuMasterWorkspace {
  const w = skuObject(v)
  if (typeof w.at !== 'string' || !Number.isFinite(Date.parse(w.at)) || !Number.isSafeInteger(w.page) || Number(w.page) < 1 || w.page_size !== 50
    || !Number.isSafeInteger(w.groups_total) || !Number.isSafeInteger(w.products_total) || typeof w.can_edit !== 'boolean') throw new Error('Master SKU tidak valid.')
  for (const field of ['groups', 'related_groups', 'products', 'selected_products']) {
    if (!Array.isArray(w[field])) throw new Error('Daftar SKU tidak lengkap.')
    const ids = new Set<string>()
    for (const value of w[field] as unknown[]) {
      const r = skuObject(value)
      if (!['id', 'sku', 'brand_id', 'brand_name', 'model_id', 'model_name', 'color_name'].every(k => typeof r[k] === 'string') || ids.has(String(r.id))) throw new Error('Identitas SKU tidak valid.')
      ids.add(String(r.id))
      if (field.includes('groups')) {
        if (!Array.isArray(r.members) || typeof r.revision !== 'string' || !/^\d+$/.test(r.revision)) throw new Error('Anggota SKU tidak valid.')
        const sizes = new Set<string>()
        for (const v of r.members) { const m = skuObject(v); if (!['id','size_id','size'].every(k => typeof m[k] === 'string') || sizes.has(String(m.size_id))) throw new Error('Ukuran SKU tidak valid.'); sizes.add(String(m.size_id)) }
        if (r.settings !== null) { const s = skuObject(r.settings); if (!('price' in s) || !(s.bom === null || Array.isArray(s.bom)) || !Array.isArray(s.work_rates) || !Array.isArray(s.laundry_rates)) throw new Error('Pengaturan SKU tidak lengkap.') }
      }
    }
  }
  if (w.legacy_basis !== null && !Array.isArray(w.legacy_basis)) throw new Error('Dasar harga/resep tidak valid.')
  if (w.lookups !== null) { const l = skuObject(w.lookups); for (const k of ['accessories','work','contractors','vendors','laundry']) if (!Array.isArray(l[k])) throw new Error('Pilihan master tidak lengkap.') }
  return w as SkuMasterWorkspace
}
/** Exact text conversion; no floating-point rounding or removal of an ambiguous separator. */
function moneyText(value: string | number): string {
  const text=String(value).trim().replace(',', '.')
  if (!/^\d+(?:\.\d{1,2})?$/.test(text)) throw new Error('Nominal harus angka tanpa pemisah ribuan, maksimal dua desimal.')
  const [whole,fraction='']=text.split('.')
  return `${whole.replace(/^0+(?=\d)/,'')}.${fraction.padEnd(2,'0')}`
}
function normalizeSettings(s: SkuSettings): SkuSettings {
  return { ...s,price:s.price === null ? null : moneyText(s.price),
    work_rates:s.work_rates.map(r=>({...r,rate:moneyText(r.rate)})),
    laundry_rates:[] }
}
/** Includes both sides of a transfer, retaining source settings and every unrelated member. */
export function skuGroupChanges(target: SkuGroup, related: SkuGroup[], basis: Json[]) {
  const selected = new Set(target.members.map(m => m.id))
  const groups = [target, ...related.filter(g => g.id !== target.id && g.members.some(m => selected.has(m.id))).map(g => ({ ...g, members: g.members.filter(m => !selected.has(m.id)) }))]
  return groups.map(g => {
    if (!g.settings) throw new Error('Hak baca harga/resep semua SKU asal diperlukan.')
    const roots = new Set(g.members.map(m => m.id)), legacy = basis.filter(x => roots.has(String(skuObject(x).product_root)))
    if (legacy.length !== roots.size) throw new Error('Harga/resep anggota belum seluruhnya diperiksa.')
    return { id: g.id, expected_version: g.revision, brand_id: g.brand_id, model_id: g.model_id, color_name: g.color_name, sku: g.sku, members: [...roots], settings: normalizeSettings(g.settings), legacy_basis: legacy }
  })
}
