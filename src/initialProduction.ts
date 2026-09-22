export type InitialProductionSource = {
  opening_item_id: string; source_key: string; batch_id: string; po_number: string;
  balance_type: 'WIP' | 'BS'; stage: 'SEWING' | 'LAUNDRY' | 'QC'; size_code: string;
  qty_pcs: number; remaining_qty_pcs: number; completed_qty_pcs: number;
  contractor_name: string | null; vendor_name: string | null;
  original_amount?: string; current_amount?: string;
  outputs: { id: string; qty_pcs: number; date: string; reversed: boolean }[];
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Rincian saldo produksi tidak lengkap.')
  return value as Record<string, unknown>
}
function text(value: unknown, id = false): string {
  if (typeof value !== 'string' || !value.trim() || (id && !uuid.test(value))) throw new Error('Identitas saldo produksi tidak valid.')
  return value
}
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Jumlah saldo produksi tidak valid.')
  return value
}
function money(value: unknown): string {
  if (typeof value !== 'string' || !/^\d{1,18}\.\d{2}$/.test(value)) throw new Error('Nilai saldo produksi tidak valid.')
  return value
}
export function parseInitialProductionSources(value: unknown, withMoney = false): InitialProductionSource[] {
  if (value === undefined) return []
  if (!Array.isArray(value)) throw new Error('Daftar saldo produksi tidak valid.')
  const seen = new Set<string>()
  return value.map(candidate => {
    const r = object(candidate), id = text(r.opening_item_id, true)
    if (seen.has(id)) throw new Error('Saldo produksi tercantum dua kali.')
    seen.add(id)
    if (r.balance_type !== 'WIP' && r.balance_type !== 'BS') throw new Error('Jenis saldo produksi tidak valid.')
    if (r.stage !== 'SEWING' && r.stage !== 'LAUNDRY' && r.stage !== 'QC') throw new Error('Tahap saldo produksi tidak valid.')
    const qty = count(r.qty_pcs), remaining = count(r.remaining_qty_pcs), completed = count(r.completed_qty_pcs)
    if (!qty || remaining > qty || completed > qty || (r.balance_type === 'WIP' && remaining + completed !== qty)) throw new Error('Sisa saldo produksi tidak cocok.')
    if (!Array.isArray(r.outputs)) throw new Error('Riwayat hasil WIP tidak lengkap.')
    const outputs = r.outputs.map(value => {
      const o = object(value)
      if (typeof o.reversed !== 'boolean' || typeof o.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(o.date)) throw new Error('Riwayat hasil WIP tidak valid.')
      return { id:text(o.id, true), qty_pcs:count(o.qty_pcs), date:o.date, reversed:o.reversed }
    })
    return { opening_item_id:id, source_key:text(r.source_key), batch_id:text(r.batch_id, true), po_number:text(r.po_number),
      balance_type:r.balance_type, stage:r.stage, size_code:text(r.size_code), qty_pcs:qty, remaining_qty_pcs:remaining, completed_qty_pcs:completed,
      contractor_name:r.contractor_name === null ? null : text(r.contractor_name), vendor_name:r.vendor_name === null ? null : text(r.vendor_name),
      ...(withMoney ? { original_amount:money(r.original_amount), current_amount:money(r.current_amount) } : {}), outputs }
  })
}
