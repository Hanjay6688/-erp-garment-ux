export type OpeningWipSplit = { id: string; bs_case_id: string; bs_number: string; bs_status: string; qty_pcs: number;
  stage_from: 'SEWING' | 'LAUNDRY'; date: string; reversed: boolean; resolved_qty_pcs: number }
/** BB (ALL-W04/W02): the pickup of cut pieces waiting at cutover and the BS split off an opening WIP. */
export type OpeningWipState = { current_stage: 'CUTTING' | 'SEWING' | 'LAUNDRY' | 'QC'; location_code: string | null;
  pickup: { id: string; contractor_code: string; contractor_name: string; date: string; po_contractor_assigned: boolean } | null;
  split_qty_pcs: number; splits: OpeningWipSplit[] }
export type InitialProductionSource = {
  opening_item_id: string; source_key: string; batch_id: string; po_number: string;
  balance_type: 'WIP' | 'BS'; stage: 'CUTTING' | 'SEWING' | 'LAUNDRY' | 'QC'; size_code: string;
  qty_pcs: number; remaining_qty_pcs: number; completed_qty_pcs: number;
  contractor_name: string | null; vendor_name: string | null;
  original_amount?: string; current_amount?: string;
  outputs: { id: string; qty_pcs: number; date: string; reversed: boolean }[];
  bb?: OpeningWipState;
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
const day = (value: unknown): string => {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Tanggal saldo produksi tidak valid.')
  return value
}
/** A server with BB always sends the current stage and the pickup/split part together; one without the other is incomplete. */
function openingWipState(r: Record<string, unknown>): OpeningWipState {
  const part = object(r.bb)
  if (!['CUTTING', 'SEWING', 'LAUNDRY', 'QC'].includes(String(r.current_stage)) || (r.stage !== 'CUTTING' && r.current_stage !== r.stage)
    || (r.stage === 'CUTTING' && r.current_stage !== (part.pickup === null ? 'CUTTING' : 'SEWING'))) throw new Error('Tahap saldo produksi tidak cocok.')
  if (!Array.isArray(part.splits)) throw new Error('Riwayat pisah BS tidak lengkap.')
  const pickup = part.pickup === null ? null : (() => {
    const p = object(part.pickup)
    if (typeof p.po_contractor_assigned !== 'boolean') throw new Error('Pickup saldo produksi tidak valid.')
    return { id:text(p.id, true), contractor_code:text(p.contractor_code), contractor_name:text(p.contractor_name), date:day(p.date), po_contractor_assigned:p.po_contractor_assigned }
  })()
  const splits = part.splits.map((value): OpeningWipSplit => {
    const s = object(value)
    if (s.stage_from !== 'SEWING' && s.stage_from !== 'LAUNDRY' || typeof s.reversed !== 'boolean') throw new Error('Pisah BS tidak valid.')
    return { id:text(s.id, true), bs_case_id:text(s.bs_case_id, true), bs_number:text(s.bs_number), bs_status:text(s.bs_status), qty_pcs:count(s.qty_pcs),
      stage_from:s.stage_from, date:day(s.date), reversed:s.reversed, resolved_qty_pcs:count(s.resolved_qty_pcs) }
  })
  const split_qty_pcs = count(part.split_qty_pcs)
  if (split_qty_pcs !== splits.filter(s => !s.reversed).reduce((sum, s) => sum + s.qty_pcs, 0)) throw new Error('Jumlah pisah BS tidak cocok.')
  return { current_stage:r.current_stage as OpeningWipState['current_stage'], location_code:r.location_code === null || r.location_code === undefined ? null : text(r.location_code),
    pickup, split_qty_pcs, splits }
}
export function parseInitialProductionSources(value: unknown, withMoney = false): InitialProductionSource[] {
  // A missing collection is an incomplete read, not an empty one; only an explicit [] establishes zero.
  if (value === undefined) throw new Error('Daftar saldo produksi tidak terbaca lengkap.')
  if (!Array.isArray(value)) throw new Error('Daftar saldo produksi tidak valid.')
  const seen = new Set<string>()
  return value.map(candidate => {
    const r = object(candidate), id = text(r.opening_item_id, true)
    if (seen.has(id)) throw new Error('Saldo produksi tercantum dua kali.')
    seen.add(id)
    if (r.balance_type !== 'WIP' && r.balance_type !== 'BS') throw new Error('Jenis saldo produksi tidak valid.')
    if (!['CUTTING', 'SEWING', 'LAUNDRY', 'QC'].includes(String(r.stage)) || (r.stage === 'CUTTING' && r.balance_type !== 'WIP')) throw new Error('Tahap saldo produksi tidak valid.')
    const bb = r.bb === undefined && r.current_stage === undefined ? undefined : openingWipState(r)
    const qty = count(r.qty_pcs), remaining = count(r.remaining_qty_pcs), completed = count(r.completed_qty_pcs), split = bb?.split_qty_pcs ?? 0
    if (!qty || remaining > qty || completed > qty || (r.balance_type === 'WIP' && remaining + completed + split !== qty)) throw new Error('Sisa saldo produksi tidak cocok.')
    if (!Array.isArray(r.outputs)) throw new Error('Riwayat hasil WIP tidak lengkap.')
    const outputs = r.outputs.map(value => {
      const o = object(value)
      if (typeof o.reversed !== 'boolean' || typeof o.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(o.date)) throw new Error('Riwayat hasil WIP tidak valid.')
      return { id:text(o.id, true), qty_pcs:count(o.qty_pcs), date:o.date, reversed:o.reversed }
    })
    return { opening_item_id:id, source_key:text(r.source_key), batch_id:text(r.batch_id, true), po_number:text(r.po_number),
      balance_type:r.balance_type, stage:r.stage as InitialProductionSource['stage'], size_code:text(r.size_code), qty_pcs:qty, remaining_qty_pcs:remaining, completed_qty_pcs:completed,
      contractor_name:r.contractor_name === null ? null : text(r.contractor_name), vendor_name:r.vendor_name === null ? null : text(r.vendor_name),
      ...(withMoney ? { original_amount:money(r.original_amount), current_amount:money(r.current_amount) } : {}), outputs, ...(bb ? { bb } : {}) }
  })
}
