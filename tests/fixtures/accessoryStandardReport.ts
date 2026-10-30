import type { AccessoryReportQuery } from '../../src/accessoryStandardReport'
// Independent hand worksheet: issue 7 PCS at inventory cost2 / selling3.25;
// GOOD10 × .5 = standard5, HPP1.50 =>7.50, reimbursement0 (no entitlement).
export const asrId = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
export const asrQuery = (patch: Partial<AccessoryReportQuery> = {}): AccessoryReportQuery => ({ period_start: '2026-10-16', period_end: '2026-10-16',
  contractor_id: asrId(1), po_id: null, q: '', offset: 0, limit: 30, ...patch })
type Row = Record<string, unknown>
export function asrWorkspace(query = asrQuery()): Row {
  const actual: Row = { id: asrId(10), issue_id: asrId(11), issue_number: 'AMBIL-7', po_id: null, po_number: null,
    physical_at: '2026-10-16T03:00:00.000000Z', location_id: asrId(12), material_id: asrId(13), material_sku: 'KANCING-BIRU', material_name: 'Kancing biru 18',
    category_id: asrId(2), qty: '7.000000', unit: 'PCS', unit_known: true, transaction_qty: '7.000000', transaction_uom: 'PCS', base_qty_per_transaction_uom: '1.000000',
    inventory_unit_cost: '2.000000', inventory_cost: '14.000000000000', selling_unit_price: '3.2500', receivable: '22.750000', accessory_price_version_id: null, material_price_version_id: null, movement_ids: [asrId(14)] }
  const standard: Row = { id: asrId(20), lot_id: asrId(21), lot_number: 'GOOD-10', po_id: asrId(3), po_number: 'PO-10', product_id: asrId(22), sku: 'CELANA-32',
    produced_at: '2026-10-16T05:00:00.000000Z', contractor_id: asrId(1), recipient_basis: 'GUARDED_PO', commitment_id: asrId(23), rework_order_id: null, decision_id: null,
    bom_version_id: asrId(24), bom_item_id: asrId(25), category_id: asrId(2), good_qty_pcs: '10', qty_per_good_fg_base: '0.500000', standard_qty: '5.000000',
    unit: 'PCS', unit_reference: 'PCS', unit_known: true, unit_basis_audit_ids: ['9007199254740993'], hpp_method: 'BOM_STANDARD', hpp_unit_cost: '1.500000',
    reimbursement_unit_rate: '0.000000', hpp_cost: '7.500000', reimbursement: '0.000000', costing_basis_at: '2026-10-16T05:00:00.000000Z', costing_basis_source: 'FG_ACCEPTANCE',
    snapshotted_at: '2026-10-16T05:00:00.000000Z', entitlement_ids: [], entitlement_known: true, revisions: [] }
  const lot: Row = { id: asrId(21), lot_number: 'GOOD-10', po_id: asrId(3), po_number: 'PO-10', product_id: asrId(22), sku: 'CELANA-32', produced_at: '2026-10-16T05:00:00.000000Z',
    good_qty_pcs: '10', contractor_id: asrId(1), recipient_basis: 'GUARDED_PO', commitment_id: asrId(23), committed_bom: asrId(24), rework_order_id: null, decision_id: null,
    decision_state: null, expected_snapshot_count: 1, snapshot_count: 1, explicit_zero: false, reasons: [] }
  const row: Row = { category_id: asrId(2), category_name: 'Kancing', unit: 'PCS', unit_reference: 'PCS', actual_qty: '7.000000', standard_qty: '5.000000', delta_qty: '2.000000',
    comparison_status: 'KNOWN', reasons: [], actual_inventory_cost: '14.000000000000', actual_receivable: '22.750000', standard_hpp_cost: '7.500000', standard_reimbursement: '0.000000',
    issue_item_ids: [asrId(10)], snapshot_ids: [asrId(20)] }
  const report: Row = { period_start: query.period_start, period_end: query.period_end, business_timezone: 'Asia/Jakarta', contractor_id: query.contractor_id, po_filter: query.po_id,
    definitions: { actual: 'POSTED_ISSUE_PHYSICAL_WIB', standard: 'ACCEPTED_GOOD_PRODUCED_WIB', comparison: 'PERIOD_COHORTS_NOT_PO_WASTE', cost: 'NATIVE_EFFECTIVE_SNAPSHOTS_WITH_REVISIONS' },
    counts: { issue_items: 1, snapshots: 1, lots: 1, unknown_lots: 0, unallocated_lots: 0, issues_without_po: 1 }, status: 'KNOWN', rows: [row], actual_sources: [actual], standard_sources: [standard], lot_sources: [lot] }
  if (query.po_id !== null) {
    report.actual_sources = []; report.counts = { ...(report.counts as Row), issue_items: 0, issues_without_po: 0 }
    Object.assign(row, { actual_qty: '0', actual_inventory_cost: '0', actual_receivable: '0', delta_qty: '-5', issue_item_ids: [] })
  }
  return { contract_version: 'cp7.accessory-standard-report.v1', business_DML: false, captured_at: '2026-10-16T06:00:00.000000Z', query: { ...query },
    contractors: { offset: query.offset, limit: query.limit, total: 1, next_offset: null, rows: query.offset === 0 ? [{ id: asrId(1), name: 'Mandor Satu', active: true }] : [] },
    selected_contractor: query.contractor_id === null ? null : { id: asrId(1), name: 'Mandor Satu', active: true }, po_options: query.contractor_id === null ? [] : [{ id: asrId(3), number: 'PO-10' }],
    report: query.contractor_id === null ? null : report }
}
export function asrParts(value = asrWorkspace()) {
  const report = value.report as Row
  return { value, report, row: (report.rows as Row[])[0], actual: (report.actual_sources as Row[])[0], standard: (report.standard_sources as Row[])[0], lot: (report.lot_sources as Row[])[0], counts: report.counts as Row }
}
