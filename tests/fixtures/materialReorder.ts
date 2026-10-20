// SS-2/SS-3: erp_cp7_get_material_reorder_v1 exactly as cp7_stock_formula.material_workspace writes it (to_jsonb of a
// material_evaluations row, numbers as JSON numbers, total as text). Test data only.
import { REORDER_READ_AT, REORDER_RUN_AT, reorderRun, reorderSettings } from './fgReorder'

export const materialId = (n: number) => `6b6b0000-0000-4000-8000-${String(n).padStart(12, '0')}`
export type MaterialWireRow = Record<string, unknown> & { material_id: string; material_type: string; state: string; basis: string; sku: string }

/** A material of `n` on the formula: 56 left, 224 used over 30 counted days, lead 6 days, point 63.34, at or under it. */
export function materialRow(n: number, type: 'FABRIC' | 'ACCESSORY' = 'FABRIC', extra: Record<string, unknown> = {}): MaterialWireRow {
  return { material_id: materialId(n), material_type: type, sku: `${type === 'FABRIC' ? 'KC' : 'KCG'}-${n}`, name: `${type === 'FABRIC' ? 'Katun' : 'Kancing'} ${n}`,
    unit_code: type === 'FABRIC' ? 'YD' : 'PCS', free_qty: 56, on_order_qty: 0, usage_qty: 224, counted_days: 30, use_days: 22, daily_mean: 7.4667, daily_sd: 4.6043,
    lead_days: 6, setting_revision: 1, z: 1.6449, safety_qty: 18.5521, formula_point: 63.34, manual_point: null, manual_source: null, point: 63.34,
    basis: 'FORMULA', reason: null, state: 'AT_OR_BELOW', changed_at: REORDER_RUN_AT, ...extra }
}
export function materialCounts(rows: MaterialWireRow[]) {
  const by = (basis: string) => rows.filter(r => r.basis === basis).length
  return { items: rows.length, at_or_below: rows.filter(r => r.state === 'AT_OR_BELOW').length, manual: by('MANUAL'), formula: by('FORMULA'),
    not_enough_data: by('NOT_ENOUGH_DATA'), no_usage: by('NO_USAGE') }
}
type Query = { material_type?: string; q?: string; filter?: string; offset?: number; limit?: number }
/** The workspace answering `query` over the rows of its material type (filter, search, page), as the server does. */
export function materialWire(rows: MaterialWireRow[] = [materialRow(1)], query: Query = {}, extra: Record<string, unknown> = {}) {
  const type = query.material_type ?? 'FABRIC', q = (query.q ?? '').trim().toLowerCase(), filter = query.filter ?? 'ALL'
  const offset = query.offset ?? 0, limit = query.limit ?? 25, mine = rows.filter(r => r.material_type === type)
  const order = { AT_OR_BELOW: 0, ABOVE: 1, NO_POINT: 2 } as Record<string, number>
  const hits = mine.filter(r => (q === '' || `${r.sku} ${r.name}`.toLowerCase().includes(q))
    && (filter === 'ALL' || (filter === 'AT_OR_BELOW' && r.state === 'AT_OR_BELOW') || (filter === 'MANUAL' && r.basis === 'MANUAL')
      || (filter === 'NOT_ENOUGH_DATA' && r.basis === 'NOT_ENOUGH_DATA')))
    .sort((a, b) => order[a.state] - order[b.state] || a.sku.localeCompare(b.sku) || a.material_id.localeCompare(b.material_id))
  const page = hits.slice(offset, offset + limit)
  return { contract_version: 'cp7.material-reorder.v1', material_type: type, read_at: REORDER_READ_AT, settings: reorderSettings(),
    run: reorderRun({ materials: rows.length, materials_at_or_below: rows.filter(r => r.state === 'AT_OR_BELOW').length }), can_manage: true,
    counts: materialCounts(mine), page: { rows: page, total: String(hits.length), offset, limit, next_offset: offset + page.length < hits.length ? offset + page.length : null },
    ...extra }
}
