export type PocketOpeningUsage = { id: string; document_number: string; line_number: string; date: string; material_sku: string; material_name: string; qty: string; original_amount: string; amount: string; allocation_status: 'ALLOCATED' | 'UNALLOCATED'; prior_allocation_reference: string | null; receipt_backed: boolean; active_period: string | null }
export type PocketOpeningSewing = { id: string; document_number: string; line_number: string; date: string; contractor_name: string; qty: number; target_kind: 'WIP' | 'BS' | 'FINISHED_GOODS' | 'COGS'; sold_reference: string | null; target_reference: string; allocated_amount: string }
export type PocketOpening = { usage: PocketOpeningUsage[]; usage_count: number; sewing: PocketOpeningSewing[]; sewing_count: number }
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(v)
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,18}\.\d{2}$/.test(v)
const day = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v)
const count = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0
const object = (v: unknown): Record<string, unknown> => { if (!v || typeof v !== 'object' || Array.isArray(v)) throw new Error('Riwayat kain kantong saldo awal tidak lengkap.'); return v as Record<string, unknown> }
export function parsePocketOpening(value: unknown): PocketOpening | null {
  const w = object(value)
  // Old runtime compatibility: absent extension is distinct from a known empty history.
  if (w.opening_usage === undefined && w.opening_sewing === undefined && w.opening_usage_count === undefined && w.opening_sewing_count === undefined) return null
  if (!Array.isArray(w.opening_usage) || !Array.isArray(w.opening_sewing) || !count(w.opening_usage_count) || !count(w.opening_sewing_count)
    || w.opening_usage.length > w.opening_usage_count || w.opening_sewing.length > w.opening_sewing_count) throw new Error('Daftar sumber kain kantong saldo awal tidak lengkap.')
  const usage = w.opening_usage.map(v => {
    const s = object(v)
    if (!uuid(s.id) || ![s.document_number,s.line_number,s.material_sku,s.material_name].every(text) || !day(s.date)
      || typeof s.qty !== 'string' || !/^\d{1,12}\.\d{6}$/.test(s.qty) || Number(s.qty) <= 0 || !money(s.original_amount) || !money(s.amount)
      || !['ALLOCATED','UNALLOCATED'].includes(String(s.allocation_status)) || typeof s.receipt_backed !== 'boolean'
      || (s.active_period !== null && !uuid(s.active_period)) || (s.prior_allocation_reference !== null && !text(s.prior_allocation_reference))
      || (s.allocation_status === 'ALLOCATED') !== (s.prior_allocation_reference !== null)) throw new Error('Sumber biaya kain kantong saldo awal tidak valid.')
    return s as PocketOpeningUsage
  })
  const sewing = w.opening_sewing.map(v => {
    const s = object(v)
    if (!uuid(s.id) || ![s.document_number,s.line_number,s.contractor_name,s.target_reference].every(text) || !day(s.date) || !count(s.qty) || !s.qty
      || !['WIP','BS','FINISHED_GOODS','COGS'].includes(String(s.target_kind)) || !money(s.allocated_amount)
      || (s.sold_reference !== null && !text(s.sold_reference)) || (s.target_kind === 'COGS') !== (s.sold_reference !== null)) throw new Error('Hasil jahit saldo awal tidak valid.')
    return s as PocketOpeningSewing
  })
  if (new Set(usage.map(x=>x.id)).size !== usage.length || new Set(sewing.map(x=>x.id)).size !== sewing.length) throw new Error('Riwayat kain kantong ditampilkan dua kali.')
  return { usage, usage_count: w.opening_usage_count, sewing, sewing_count: w.opening_sewing_count }
}
