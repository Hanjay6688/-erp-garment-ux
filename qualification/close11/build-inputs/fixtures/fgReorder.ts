// SS-1: erp_cp7_get_fg_reorder_v1 exactly as cp7_stock_formula.workspace writes it (to_jsonb of an evaluation row, numbers
// as JSON numbers, total as text). Test data only.
export const REORDER_READ_AT = '2026-10-20T03:00:00+00:00'
export const REORDER_RUN_AT = '2026-10-20T02:59:00+00:00'
export const reorderId = (n: number) => `5a5a0000-0000-4000-8000-${String(n).padStart(12, '0')}`
export type ReorderWireRow = Record<string, unknown> & { target_key: string; root_id: string; state: string; basis: string }

/** An item of `n`: 23 free, PATTERN-like sales (mean 3,9), lead 7 days from the profile, 95%: formula point 36, at or under it. */
export function reorderRow(n: number, extra: Record<string, unknown> = {}): ReorderWireRow {
  const root = reorderId(n), size = reorderId(500 + n)
  return { target_key: `${root}:${size}`, root_id: root, size_id: size, model_id: reorderId(900 + n), product_id: root, sku: `KML-${n}`,
    product_name: `Kemeja Linen ${n}`, size_code: 'M', free_pcs: 23, sales_pcs: 117, counted_days: 30, sale_days: 27, daily_mean: 3.9, daily_sd: 1.9182,
    lead_days: 7, lead_basis: 'PROFILE', lead_lots: null, lead_groups: null, buffer_mode: 'STATISTICAL', buffer_days: null, z: 1.6449, safety_pcs: 8.3485,
    formula_point: 36, manual_point: null, manual_revision: null, point: 36, basis: 'FORMULA', reason: null, wip_pcs: 0, wip_status: 'COMPLETE',
    wip_reason: null, state: 'AT_OR_BELOW', changed_at: REORDER_RUN_AT, wip_read_at: null, ...extra }
}
export const reorderSettings = (extra: Record<string, unknown> = {}) => ({ revision: 0, service_level: '0.95', window_days: 30, reason: null as string | null,
  saved_at: null as string | null, ...extra })
export const reorderRun = (extra: Record<string, unknown> = {}) => ({ computed_at: REORDER_RUN_AT, window_from: '2026-09-20', window_through: '2026-10-19',
  settings_revision: 0, service_level: 0.95, window_days: 30, items: 1, at_or_below: 1, wip_read: 1, materials: 4, materials_at_or_below: 1, millis: 420, ...extra })
export function reorderCounts(rows: ReorderWireRow[]) {
  const by = (basis: string) => rows.filter(r => r.basis === basis).length
  return { items: rows.length, at_or_below: rows.filter(r => r.state === 'AT_OR_BELOW').length, manual: by('MANUAL'), formula: by('FORMULA'),
    not_enough_data: by('NOT_ENOUGH_DATA'), no_sales: by('NO_SALES') }
}
type Query = { q?: string; filter?: string; offset?: number; limit?: number }
/** The workspace answering `query` over all `rows` (filter, search, page), as the server does. */
export function reorderWire(rows: ReorderWireRow[] = [reorderRow(1)], query: Query = {}, extra: Record<string, unknown> = {}) {
  const q = (query.q ?? '').trim().toLowerCase(), filter = query.filter ?? 'ALL', offset = query.offset ?? 0, limit = query.limit ?? 25
  const order = { AT_OR_BELOW: 0, ABOVE: 1, NO_POINT: 2 } as Record<string, number>
  const hits = rows.filter(r => (q === '' || [r.sku, r.product_name, r.size_code].filter(Boolean).join(' ').toLowerCase().includes(q))
    && (filter === 'ALL' || (filter === 'AT_OR_BELOW' && r.state === 'AT_OR_BELOW') || (filter === 'MANUAL' && r.basis === 'MANUAL')
      || (filter === 'NOT_ENOUGH_DATA' && r.basis === 'NOT_ENOUGH_DATA')))
    .sort((a, b) => order[a.state] - order[b.state] || String(a.sku).localeCompare(String(b.sku)) || a.target_key.localeCompare(b.target_key))
  const page = hits.slice(offset, offset + limit)
  return { contract_version: 'cp7.fg-reorder.v1', read_at: REORDER_READ_AT, settings: reorderSettings(), run: reorderRun({ items: rows.length,
    at_or_below: rows.filter(r => r.state === 'AT_OR_BELOW').length }), can_manage: true, counts: reorderCounts(rows),
    page: { rows: page, total: String(hits.length), offset, limit, next_offset: offset + page.length < hits.length ? offset + page.length : null }, ...extra }
}
