// S05 D17-19C. Exact strings across SQL/RPC/UI; no floating-point money or
// quantities. A malformed/partial response cannot become a usable comparison.
export const ACCESSORY_REPORT_CONTRACT = 'cp7.accessory-standard-report.v1'
export type AccessoryReportQuery = { period_start: string; period_end: string; contractor_id: string | null; po_id: string | null; q: string; offset: number; limit: number }
type Contractor = { id: string; name: string; active: boolean }
export type AccessoryReportRow = { category_id: string | null; category_name: string; unit: string | null; unit_reference: string | null;
  actual_qty: string; standard_qty: string | null; delta_qty: string | null; comparison_status: 'KNOWN' | 'UNKNOWN'; reasons: string[];
  actual_inventory_cost: string; actual_receivable: string | null; standard_hpp_cost: string | null; standard_reimbursement: string | null;
  issue_item_ids: string[]; snapshot_ids: string[] }
export type AccessoryActualSource = { id: string; issue_id: string; issue_number: string; po_id: string | null; po_number: string | null; physical_at: string;
  location_id: string; material_id: string; material_sku: string; material_name: string; category_id: string | null; qty: string; unit: string | null;
  unit_known: boolean; transaction_qty: string | null; transaction_uom: string | null; base_qty_per_transaction_uom: string | null;
  inventory_unit_cost: string; inventory_cost: string; selling_unit_price: string; receivable: string | null; accessory_price_version_id: string | null; material_price_version_id: string | null; movement_ids: string[] }
export type AccessoryStandardSource = { id: string; lot_id: string; lot_number: string; po_id: string; po_number: string | null; product_id: string; sku: string;
  produced_at: string; contractor_id: string | null; recipient_basis: 'GUARDED_PO' | 'REWORK_DECISION'; commitment_id: string | null; rework_order_id: string | null; decision_id: string | null;
  bom_version_id: string; bom_item_id: string; category_id: string; good_qty_pcs: string; qty_per_good_fg_base: string; standard_qty: string;
  unit: string | null; unit_reference: string | null; unit_known: boolean; unit_basis_audit_ids: string[]; hpp_method: 'CATEGORY_MOVING_AVG' | 'BOM_STANDARD';
  hpp_unit_cost: string; reimbursement_unit_rate: string; hpp_cost: string; reimbursement: string; costing_basis_at: string;
  costing_basis_source: 'FIRST_FINANCIAL_USE' | 'FG_ACCEPTANCE'; snapshotted_at: string; entitlement_ids: string[]; entitlement_known: boolean;
  revisions: { id: string; material_id: string | null; old_hpp_unit_cost: string; new_hpp_unit_cost: string; old_category_avg_cost: string | null; new_category_avg_cost: string; reason: string; changed_at: string }[] }
export type AccessoryLotSource = { id: string; lot_number: string; po_id: string | null; po_number: string | null; product_id: string; sku: string; produced_at: string;
  good_qty_pcs: string; contractor_id: string | null; recipient_basis: 'GUARDED_PO' | 'REWORK_DECISION'; commitment_id: string | null; committed_bom: string | null;
  rework_order_id: string | null; decision_id: string | null; decision_state: 'SELECTED' | 'NONE' | 'UNAVAILABLE' | null;
  expected_snapshot_count: number | null; snapshot_count: number; explicit_zero: boolean; reasons: string[] }
export type AccessoryPeriodReport = { period_start: string; period_end: string; business_timezone: 'Asia/Jakarta'; contractor_id: string; po_filter: string | null;
  status: 'KNOWN' | 'UNKNOWN' | 'NO_GOOD_OUTPUT'; counts: { issue_items: number; snapshots: number; lots: number; unknown_lots: number; unallocated_lots: number; issues_without_po: number };
  rows: AccessoryReportRow[]; actual_sources: AccessoryActualSource[]; standard_sources: AccessoryStandardSource[]; lot_sources: AccessoryLotSource[] }
export type AccessoryReportWorkspace = { captured_at: string; contractors: { offset: number; limit: number; total: number; next_offset: number | null; rows: Contractor[] };
  selected_contractor: Contractor | null; po_options: { id: string; number: string }[]; report: AccessoryPeriodReport | null }
type Obj = Record<string, unknown>
const bad = (): never => { throw new Error('Data laporan aksesori tidak lengkap atau tidak cocok. Muat ulang sebelum memakai angkanya.') }
const object = (v: unknown): Obj => v !== null && typeof v === 'object' && !Array.isArray(v) ? v as Obj : bad()
const str = (v: unknown): string => typeof v === 'string' && v.length > 0 && v.length <= 4000 ? v : bad()
const nullable = <T>(v: unknown, parse: (x: unknown) => T): T | null => v === null ? null : parse(v)
const bool = (v: unknown): boolean => typeof v === 'boolean' ? v : bad()
const count = (v: unknown): number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 && v <= 10000000 ? v : bad()
const arr = <T>(v: unknown, parse: (x: unknown) => T): T[] => Array.isArray(v) && v.length <= 3000 ? v.map(parse) : bad()
const uuid = (v: unknown): string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v) ? v : bad()
const idText = (v: unknown): string => typeof v === 'string' && /^[1-9]\d{0,30}$/.test(v) ? v : bad()
const integer = (v: unknown): string => typeof v === 'string' && /^[1-9]\d{0,30}$/.test(v) ? v : bad()
const decimal = (v: unknown): string => typeof v === 'string' && /^\d{1,45}(?:\.\d{1,12})?$/.test(v) ? v : bad()
const signed = (v: unknown): string => typeof v === 'string' && /^-?\d{1,45}(?:\.\d{1,12})?$/.test(v) ? v : bad()
export function accessoryReportDay(v: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v) || v < '2000-01-01' || v > '9999-12-31') return false
  const d = new Date(`${v}T00:00:00Z`)
  return !Number.isNaN(d.valueOf()) && d.toISOString().slice(0, 10) === v
}
export function accessoryReportPeriod(start: string, end: string) {
  return accessoryReportDay(start) && accessoryReportDay(end) && end >= start && (Date.parse(end) - Date.parse(start)) / 86400000 <= 366
}
const at = (v: unknown) => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(v) && Number.isFinite(Date.parse(v)) ? v : bad()
const choice = <T extends string>(v: unknown, values: readonly T[]): T => typeof v === 'string' && values.includes(v as T) ? v as T : bad()
const strings = (v: unknown) => arr(v, str)
const ids = (v: unknown) => unique(arr(v, uuid))
function unique<T>(v: T[]): T[] { if (new Set(v).size !== v.length) bad(); return v }
const sameIds = (a: string[], b: string[]) => a.length === b.length && a.every(x => b.includes(x))
const scale = 1000000000000n
export function accessoryReportScaled(value: string): bigint {
  const [whole, fraction = ''] = signed(value).split('.')
  return (whole.startsWith('-') ? -1n : 1n) * (BigInt(whole.replace('-', '')) * scale + BigInt(fraction.padEnd(12, '0')))
}
export function accessoryReportNumber(value: string | null, rupiah = false) {
  if (value === null) return 'Belum diketahui'
  const [whole, tail = ''] = signed(value).split('.'), negative = whole.startsWith('-')
  const digits = whole.replace('-', '').replace(/^0+(?=\d)/, ''), fraction = tail.replace(/0+$/, '')
  return `${negative ? '−' : ''}${rupiah ? 'Rp' : ''}${digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}${fraction ? ',' + fraction : ''}`
}
const recipient = (v: unknown) => choice(v, ['GUARDED_PO', 'REWORK_DECISION'] as const)
function contractor(v: unknown): Contractor { const r = object(v); return { id: uuid(r.id), name: str(r.name), active: bool(r.active) } }
function actual(v: unknown): AccessoryActualSource {
  const r = object(v)
  return { id: uuid(r.id), issue_id: uuid(r.issue_id), issue_number: str(r.issue_number), po_id: nullable(r.po_id, uuid), po_number: nullable(r.po_number, str),
    physical_at: at(r.physical_at), location_id: uuid(r.location_id), material_id: uuid(r.material_id), material_sku: str(r.material_sku), material_name: str(r.material_name),
    category_id: nullable(r.category_id, uuid), qty: decimal(r.qty), unit: nullable(r.unit, str), unit_known: bool(r.unit_known), transaction_qty: nullable(r.transaction_qty, decimal),
    transaction_uom: nullable(r.transaction_uom, str), base_qty_per_transaction_uom: nullable(r.base_qty_per_transaction_uom, decimal), inventory_unit_cost: decimal(r.inventory_unit_cost),
    inventory_cost: decimal(r.inventory_cost), selling_unit_price: decimal(r.selling_unit_price), receivable: nullable(r.receivable, decimal), accessory_price_version_id: nullable(r.accessory_price_version_id, uuid),
    material_price_version_id: nullable(r.material_price_version_id, uuid), movement_ids: ids(r.movement_ids) }
}
function standard(v: unknown): AccessoryStandardSource {
  const r = object(v)
  return { id: uuid(r.id), lot_id: uuid(r.lot_id), lot_number: str(r.lot_number), po_id: uuid(r.po_id), po_number: nullable(r.po_number, str), product_id: uuid(r.product_id),
    sku: str(r.sku), produced_at: at(r.produced_at), contractor_id: nullable(r.contractor_id, uuid), recipient_basis: recipient(r.recipient_basis), commitment_id: nullable(r.commitment_id, uuid),
    rework_order_id: nullable(r.rework_order_id, uuid), decision_id: nullable(r.decision_id, uuid), bom_version_id: uuid(r.bom_version_id), bom_item_id: uuid(r.bom_item_id), category_id: uuid(r.category_id),
    good_qty_pcs: integer(r.good_qty_pcs), qty_per_good_fg_base: decimal(r.qty_per_good_fg_base), standard_qty: decimal(r.standard_qty), unit: nullable(r.unit, str),
    unit_reference: nullable(r.unit_reference, str), unit_known: bool(r.unit_known), unit_basis_audit_ids: unique(arr(r.unit_basis_audit_ids, idText)),
    hpp_method: choice(r.hpp_method, ['CATEGORY_MOVING_AVG', 'BOM_STANDARD'] as const), hpp_unit_cost: decimal(r.hpp_unit_cost), reimbursement_unit_rate: decimal(r.reimbursement_unit_rate),
    hpp_cost: decimal(r.hpp_cost), reimbursement: decimal(r.reimbursement), costing_basis_at: at(r.costing_basis_at),
    costing_basis_source: choice(r.costing_basis_source, ['FIRST_FINANCIAL_USE', 'FG_ACCEPTANCE'] as const), snapshotted_at: at(r.snapshotted_at), entitlement_ids: ids(r.entitlement_ids),
    entitlement_known: bool(r.entitlement_known), revisions: arr(r.revisions, v => { const x = object(v); return { id: idText(x.id), material_id: nullable(x.material_id, uuid),
      old_hpp_unit_cost: decimal(x.old_hpp_unit_cost), new_hpp_unit_cost: decimal(x.new_hpp_unit_cost), old_category_avg_cost: nullable(x.old_category_avg_cost, decimal),
      new_category_avg_cost: decimal(x.new_category_avg_cost), reason: str(x.reason), changed_at: at(x.changed_at) } }) }
}
function lot(v: unknown): AccessoryLotSource {
  const r = object(v)
  return { id: uuid(r.id), lot_number: str(r.lot_number), po_id: nullable(r.po_id, uuid), po_number: nullable(r.po_number, str), product_id: uuid(r.product_id), sku: str(r.sku),
    produced_at: at(r.produced_at), good_qty_pcs: integer(r.good_qty_pcs), contractor_id: nullable(r.contractor_id, uuid), recipient_basis: recipient(r.recipient_basis),
    commitment_id: nullable(r.commitment_id, uuid), committed_bom: nullable(r.committed_bom, uuid), rework_order_id: nullable(r.rework_order_id, uuid), decision_id: nullable(r.decision_id, uuid),
    decision_state: nullable(r.decision_state, v => choice(v, ['SELECTED', 'NONE', 'UNAVAILABLE'] as const)), expected_snapshot_count: nullable(r.expected_snapshot_count, count),
    snapshot_count: count(r.snapshot_count), explicit_zero: bool(r.explicit_zero), reasons: unique(strings(r.reasons)) }
}
function row(v: unknown): AccessoryReportRow {
  const r = object(v)
  return { category_id: nullable(r.category_id, uuid), category_name: str(r.category_name), unit: nullable(r.unit, str), unit_reference: nullable(r.unit_reference, str),
    actual_qty: decimal(r.actual_qty), standard_qty: nullable(r.standard_qty, decimal), delta_qty: nullable(r.delta_qty, signed),
    comparison_status: choice(r.comparison_status, ['KNOWN', 'UNKNOWN'] as const), reasons: unique(strings(r.reasons)), actual_inventory_cost: decimal(r.actual_inventory_cost),
    actual_receivable: nullable(r.actual_receivable, decimal), standard_hpp_cost: nullable(r.standard_hpp_cost, decimal), standard_reimbursement: nullable(r.standard_reimbursement, decimal),
    issue_item_ids: ids(r.issue_item_ids), snapshot_ids: ids(r.snapshot_ids) }
}
function wibDay(timestamp: string) { return new Date(Date.parse(timestamp) + 7 * 3600000).toISOString().slice(0, 10) }
function parseReport(v: unknown, q: AccessoryReportQuery): AccessoryPeriodReport {
  const r = object(v), d = object(r.definitions), c = object(r.counts)
  if (r.period_start !== q.period_start || r.period_end !== q.period_end || r.contractor_id !== q.contractor_id || r.po_filter !== q.po_id || r.business_timezone !== 'Asia/Jakarta'
    || d.actual !== 'POSTED_ISSUE_PHYSICAL_WIB' || d.standard !== 'ACCEPTED_GOOD_PRODUCED_WIB' || d.comparison !== 'PERIOD_COHORTS_NOT_PO_WASTE' || d.cost !== 'NATIVE_EFFECTIVE_SNAPSHOTS_WITH_REVISIONS') bad()
  const report: AccessoryPeriodReport = { period_start: q.period_start, period_end: q.period_end, business_timezone: 'Asia/Jakarta', contractor_id: uuid(q.contractor_id), po_filter: q.po_id,
    status: choice(r.status, ['KNOWN', 'UNKNOWN', 'NO_GOOD_OUTPUT'] as const), counts: { issue_items: count(c.issue_items), snapshots: count(c.snapshots), lots: count(c.lots),
      unknown_lots: count(c.unknown_lots), unallocated_lots: count(c.unallocated_lots), issues_without_po: count(c.issues_without_po) },
    rows: arr(r.rows, row), actual_sources: arr(r.actual_sources, actual), standard_sources: arr(r.standard_sources, standard), lot_sources: arr(r.lot_sources, lot) }
  const a = report.actual_sources, s = report.standard_sources, l = report.lot_sources
  unique(a.map(x => x.id)); unique(s.map(x => x.id)); unique(l.map(x => x.id)); unique(report.rows.map(x => x.category_id))
  if (report.counts.issue_items !== a.length || report.counts.snapshots !== s.length || report.counts.lots !== l.length || a.length + s.length + l.length > 3000
    || report.counts.unknown_lots !== l.filter(x => x.reasons.length).length || report.counts.unallocated_lots !== l.filter(x => x.contractor_id === null).length
    || report.counts.issues_without_po !== a.filter(x => x.po_id === null).length) bad()
  for (const source of [...a, ...l]) {
    const day = wibDay('physical_at' in source ? source.physical_at : source.produced_at)
    if (day < q.period_start || day > q.period_end || (q.po_id !== null && source.po_id !== q.po_id)) bad()
  }
  const mul = (qty: string, cost: string) => accessoryReportScaled(qty) * accessoryReportScaled(cost) / scale
  const round6 = (value: bigint) => (value + 500000n) / 1000000n * 1000000n
  for (const x of a) {
    if (accessoryReportScaled(x.qty) <= 0n || mul(x.qty, x.inventory_unit_cost) !== accessoryReportScaled(x.inventory_cost) || x.unit_known !== (x.unit !== null)
      || (x.unit_known && x.movement_ids.length === 0)
      || (x.transaction_qty !== null && x.base_qty_per_transaction_uom !== null && round6(mul(x.transaction_qty, x.base_qty_per_transaction_uom)) !== accessoryReportScaled(x.qty))
      || (x.transaction_qty !== null && (x.receivable === null || round6(mul(x.transaction_qty, x.selling_unit_price)) !== accessoryReportScaled(x.receivable)))) bad()
  }
  for (const x of s) {
    const parent = l.find(p => p.id === x.lot_id)
    if (!parent || parent.po_id !== x.po_id || parent.product_id !== x.product_id || parent.produced_at !== x.produced_at || parent.contractor_id !== x.contractor_id
      || x.unit_known !== (x.unit !== null) || (x.unit_known && x.unit_basis_audit_ids.length === 0)
      || BigInt(x.good_qty_pcs) * accessoryReportScaled(x.qty_per_good_fg_base) !== accessoryReportScaled(x.standard_qty)
      || round6(mul(x.standard_qty, x.hpp_unit_cost)) !== accessoryReportScaled(x.hpp_cost)
      || round6(mul(x.standard_qty, x.reimbursement_unit_rate)) !== accessoryReportScaled(x.reimbursement)) bad()
    unique(x.revisions.map(x => x.id))
  }
  for (const x of l) {
    if (x.snapshot_count !== s.filter(s => s.lot_id === x.id).length || (x.contractor_id !== null && x.contractor_id !== q.contractor_id)
      || (x.contractor_id === null && !x.reasons.includes('UNALLOCATED_RECIPIENT'))
      || (x.explicit_zero && (x.snapshot_count !== 0 || x.expected_snapshot_count !== 0 || !x.commitment_id || !x.committed_bom
        || (x.rework_order_id !== null && x.decision_state !== 'NONE')))) bad()
  }
  const sum = <T>(xs: T[], get: (x: T) => string) => xs.reduce((total, x) => total + accessoryReportScaled(get(x)), 0n)
  const allEmpty = l.some(x => x.contractor_id === q.contractor_id) && l.filter(x => x.contractor_id === q.contractor_id).every(x => x.explicit_zero) && report.counts.unknown_lots === 0
  const keys = unique([...new Set([...a.map(x => x.category_id), ...s.filter(x => x.contractor_id === q.contractor_id).map(x => x.category_id)])])
  if (keys.length !== report.rows.length || keys.some(k => !report.rows.some(r => r.category_id === k))) bad()
  for (const r of report.rows) {
    const actual = a.filter(x => x.category_id === r.category_id), standards = s.filter(x => x.category_id === r.category_id && x.contractor_id === q.contractor_id)
    if (!sameIds(r.issue_item_ids, actual.map(x => x.id)) || !sameIds(r.snapshot_ids, standards.map(x => x.id))
      || sum(actual, x => x.qty) !== accessoryReportScaled(r.actual_qty) || sum(actual, x => x.inventory_cost) !== accessoryReportScaled(r.actual_inventory_cost)
      || (actual.some(x => x.receivable === null) ? r.actual_receivable !== null : r.actual_receivable === null || sum(actual, x => x.receivable!) !== accessoryReportScaled(r.actual_receivable))) bad()
    for (const [field, get] of [['standard_qty', (x: AccessoryStandardSource) => x.standard_qty], ['standard_hpp_cost', (x: AccessoryStandardSource) => x.hpp_cost],
      ['standard_reimbursement', (x: AccessoryStandardSource) => x.reimbursement]] as const) {
      const value = r[field]
      if (standards.length > 0 ? value === null || sum(standards, get) !== accessoryReportScaled(value) : allEmpty ? value === null || accessoryReportScaled(value) !== 0n : value !== null) bad()
    }
    const sourceIncomplete = report.counts.unknown_lots > 0 || report.counts.unallocated_lots > 0 || s.some(x => !x.entitlement_known)
      || actual.some(x => !x.unit_known) || standards.some(x => !x.unit_known) || r.category_id === null || r.standard_qty === null
    if (r.comparison_status === 'KNOWN') {
      if (sourceIncomplete || r.reasons.length || r.unit === null || r.delta_qty === null || accessoryReportScaled(r.delta_qty) !== accessoryReportScaled(r.actual_qty) - accessoryReportScaled(r.standard_qty!)) bad()
      if ([...actual, ...standards].some(x => x.unit !== r.unit)) bad()
    } else if (!r.reasons.length || r.delta_qty !== null) bad()
  }
  const unknown = l.some(x => x.reasons.length) || s.some(x => !x.entitlement_known) || report.rows.some(x => x.comparison_status === 'UNKNOWN')
  if (report.status !== (unknown ? 'UNKNOWN' : l.some(x => x.contractor_id === q.contractor_id) ? 'KNOWN' : 'NO_GOOD_OUTPUT')) bad()
  return report
}
export function parseAccessoryReportWorkspace(value: unknown, query: AccessoryReportQuery): AccessoryReportWorkspace {
  const r = object(value), q = object(r.query), page = object(r.contractors)
  if (r.contract_version !== ACCESSORY_REPORT_CONTRACT || r.business_DML !== false || !accessoryReportPeriod(query.period_start, query.period_end)
    || Object.keys(query).some(k => q[k] !== query[k as keyof AccessoryReportQuery]) || Object.keys(q).length !== Object.keys(query).length) bad()
  const rows = arr(page.rows, contractor), total = count(page.total), offset = count(page.offset), limit = count(page.limit), next = nullable(page.next_offset, count)
  unique(rows.map(x => x.id))
  if (offset !== query.offset || limit !== query.limit || rows.length !== Math.min(limit, Math.max(0, total - offset))
    || next !== (offset + rows.length < total ? offset + rows.length : null)) bad()
  const selected = nullable(r.selected_contractor, contractor), options = arr(r.po_options, x => { const p = object(x); return { id: uuid(p.id), number: str(p.number) } })
  unique(options.map(x => x.id))
  if ((selected?.id ?? null) !== query.contractor_id || (query.po_id !== null && !options.some(x => x.id === query.po_id)) || (selected === null && options.length > 0)) bad()
  const report = nullable(r.report, x => parseReport(x, query))
  if ((report === null) !== (query.contractor_id === null)) bad()
  return { captured_at: at(r.captured_at), contractors: { offset, limit, total, next_offset: next, rows }, selected_contractor: selected, po_options: options, report }
}
const reasons: Record<string, string> = {
  UNALLOCATED_RECIPIENT: 'Penerima mandor belum terbukti', MISSING_COMMITMENT: 'Komitmen BOM belum tersedia', MISSING_REWORK_STANDARD: 'Pilihan aksesori rework belum tersedia',
  REWORK_COMMITMENT_MISMATCH: 'Pilihan rework dan komitmen BOM tidak cocok', MISSING_OR_EXTRA_SNAPSHOT: 'Snapshot standar belum lengkap', SNAPSHOT_LINEAGE_MISMATCH: 'Sumber snapshot tidak cocok',
  INCOMPLETE_LOT_STANDARD: 'Ada lot GOOD dengan standar belum lengkap', ENTITLEMENT_MISMATCH: 'Hak penggantian tidak cocok dengan snapshot',
  HISTORICAL_UNIT_UNKNOWN: 'Satuan historis belum terbukti', NO_CATEGORY_STANDARD: 'Standar kategori pada hasil GOOD periode ini belum tersedia',
}
export const accessoryReportReason = (code: string) => reasons[code] ?? 'Sumber perlu diperiksa'
