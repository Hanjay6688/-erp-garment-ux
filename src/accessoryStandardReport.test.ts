import { describe, expect, it } from 'vitest'
import { accessoryReportNumber, accessoryReportPeriod, parseAccessoryReportWorkspace } from './accessoryStandardReport'
import { asrId, asrParts, asrQuery, asrWorkspace } from '../tests/fixtures/accessoryStandardReport'

describe('S05 exact read contract (hand worksheet, not Native qualification)', () => {
  it('keeps zero reimbursement standard, physical variant, old BOM and exact source identities', () => {
    const result = parseAccessoryReportWorkspace(asrWorkspace(), asrQuery()), r = result.report!
    expect(r.rows[0]).toMatchObject({ actual_qty: '7.000000', standard_qty: '5.000000', delta_qty: '2.000000', standard_reimbursement: '0.000000' })
    expect(r.standard_sources[0].entitlement_ids).toEqual([])
    expect(r.standard_sources[0].bom_version_id).toBe(asrId(24))
    expect(r.standard_sources[0].unit_basis_audit_ids).toEqual(['9007199254740993'])
    expect(r.actual_sources[0]).toMatchObject({ po_id: null, material_id: asrId(13), transaction_qty: '7.000000', movement_ids: [asrId(14)] })
  })
  it('never rounds a large inventory value or fractional quantity through a JS number', () => {
    const p = asrParts()
    Object.assign(p.actual, { qty: '9007199254.740993', transaction_qty: '9007199254.740993', inventory_unit_cost: '1000000', inventory_cost: '9007199254740993.000000', selling_unit_price: '1', receivable: '9007199254.740993' })
    Object.assign(p.row, { actual_qty: '9007199254.740993', actual_inventory_cost: '9007199254740993.000000', actual_receivable: '9007199254.740993', delta_qty: '9007199249.740993' })
    const r = parseAccessoryReportWorkspace(p.value, asrQuery()).report!
    expect(accessoryReportNumber(r.rows[0].actual_inventory_cost, true)).toBe('Rp9.007.199.254.740.993')
    expect(accessoryReportNumber(r.rows[0].actual_qty)).toBe('9.007.199.254,740993')
  })
  it('keeps the same immutable standard quantity/BOM with a Native effective cost revision', () => {
    const p = asrParts()
    Object.assign(p.standard, { hpp_method: 'CATEGORY_MOVING_AVG', hpp_unit_cost: '2.000000', hpp_cost: '10.000000', revisions: [{ id: asrId(90),
      material_id: asrId(13), old_hpp_unit_cost: '1.500000', new_hpp_unit_cost: '2.000000', old_category_avg_cost: '1.500000', new_category_avg_cost: '2.000000',
      reason: 'Invoice diterima sesudah GOOD', changed_at: '2026-10-17T06:00:00.000000Z' }] })
    p.row.standard_hpp_cost = '10.000000'
    const standard = parseAccessoryReportWorkspace(p.value, asrQuery()).report!.standard_sources[0]
    expect(standard).toMatchObject({ id: asrId(20), bom_version_id: asrId(24), standard_qty: '5.000000', hpp_cost: '10.000000' })
    expect(standard.revisions[0].id).toBe(asrId(90))
    expect(standard.unit_basis_audit_ids).toEqual(['9007199254740993'])
    for (const invalid of ['9007199254740995', 9007199254740995, null, 'not-a-uuid', asrId(90).slice(0, -1)]) {
      Object.assign((p.standard.revisions as Record<string, unknown>[])[0], { id: invalid })
      expect(() => parseAccessoryReportWorkspace(p.value, asrQuery())).toThrow()
    }
  })
  it('distinguishes an explicit empty standard from missing snapshots', () => {
    const p = asrParts()
    p.report.standard_sources = []; Object.assign(p.lot, { snapshot_count: 0, expected_snapshot_count: 0, explicit_zero: true })
    p.counts.snapshots = 0; Object.assign(p.row, { standard_qty: '0', delta_qty: '7', standard_hpp_cost: '0', standard_reimbursement: '0', snapshot_ids: [] })
    expect(parseAccessoryReportWorkspace(p.value, asrQuery()).report!.rows[0].standard_qty).toBe('0')
    Object.assign(p.lot, { expected_snapshot_count: 1, explicit_zero: false, reasons: ['MISSING_OR_EXTRA_SNAPSHOT'] }); p.counts.unknown_lots = 1; p.report.status = 'UNKNOWN'
    Object.assign(p.row, { standard_qty: null, delta_qty: null, standard_hpp_cost: null, standard_reimbursement: null, comparison_status: 'UNKNOWN', reasons: ['INCOMPLETE_LOT_STANDARD', 'NO_CATEGORY_STANDARD'] })
    expect(parseAccessoryReportWorkspace(p.value, asrQuery()).report!.rows[0].standard_qty).toBeNull()
    p.row.standard_qty = '0'; expect(() => parseAccessoryReportWorkspace(p.value, asrQuery())).toThrow()
  })
  it('holds comparison when historical units or an unallocated recipient are unknown', () => {
    const p = asrParts()
    Object.assign(p.standard, { unit: null, unit_known: false, unit_reference: 'LUSIN' }); Object.assign(p.row, { unit: null, delta_qty: null, comparison_status: 'UNKNOWN', reasons: ['HISTORICAL_UNIT_UNKNOWN'] }); p.report.status = 'UNKNOWN'
    expect(parseAccessoryReportWorkspace(p.value, asrQuery()).report!.rows[0].delta_qty).toBeNull()
    Object.assign(p.row, { delta_qty: '2', comparison_status: 'KNOWN', reasons: [] }); expect(() => parseAccessoryReportWorkspace(p.value, asrQuery())).toThrow()
    const u = asrParts(); Object.assign(u.standard, { contractor_id: null, recipient_basis: 'REWORK_DECISION', rework_order_id: asrId(70), decision_id: asrId(71) })
    Object.assign(u.lot, { contractor_id: null, recipient_basis: 'REWORK_DECISION', rework_order_id: asrId(70), decision_id: asrId(71), decision_state: 'SELECTED', reasons: ['UNALLOCATED_RECIPIENT'] })
    Object.assign(u.counts, { unknown_lots: 1, unallocated_lots: 1 }); u.report.status = 'UNKNOWN'
    Object.assign(u.row, { standard_qty: null, standard_hpp_cost: null, standard_reimbursement: null, snapshot_ids: [], comparison_status: 'UNKNOWN', delta_qty: null, reasons: ['INCOMPLETE_LOT_STANDARD', 'UNALLOCATED_RECIPIENT', 'NO_CATEGORY_STANDARD'] })
    expect(parseAccessoryReportWorkspace(u.value, asrQuery()).report!.counts.unallocated_lots).toBe(1)
  })
  it('checks both cohort dates in WIB and applies the same selected PO', () => {
    const p = asrParts(); p.actual.physical_at = '2026-10-15T17:00:00.000000Z'
    expect(parseAccessoryReportWorkspace(p.value, asrQuery()).report!.actual_sources).toHaveLength(1)
    p.actual.physical_at = '2026-10-16T17:00:00.000000Z'; expect(() => parseAccessoryReportWorkspace(p.value, asrQuery())).toThrow()
    const q = asrQuery({ po_id: asrId(3) }), result = parseAccessoryReportWorkspace(asrWorkspace(q), q)
    expect(result.report!.rows[0]).toMatchObject({ actual_qty: '0', delta_qty: '-5' })
    const old = asrWorkspace(); (old.query as Record<string, unknown>).po_id = asrId(3)
    expect(() => parseAccessoryReportWorkspace(old, q)).toThrow()
  })
  it.each([
    ['quantity total', (p: ReturnType<typeof asrParts>) => { p.row.actual_qty = '8' }],
    ['source removed', (p: ReturnType<typeof asrParts>) => { p.report.standard_sources = [] }],
    ['source doubled', (p: ReturnType<typeof asrParts>) => { (p.report.actual_sources as unknown[]).push(p.actual) }],
    ['source ID invented', (p: ReturnType<typeof asrParts>) => { p.row.issue_item_ids = [asrId(99)] }],
    ['cost drift', (p: ReturnType<typeof asrParts>) => { p.standard.hpp_cost = '8'; p.row.standard_hpp_cost = '8' }],
    ['transaction conversion drift', (p: ReturnType<typeof asrParts>) => { p.actual.base_qty_per_transaction_uom = '12' }],
    ['selling price drift', (p: ReturnType<typeof asrParts>) => { p.actual.selling_unit_price = '4' }],
    ['empty without commitment', (p: ReturnType<typeof asrParts>) => { p.lot.explicit_zero = true; p.lot.commitment_id = null }],
    ['not read only', (p: ReturnType<typeof asrParts>) => { p.value.business_DML = true }],
    ['numeric money', (p: ReturnType<typeof asrParts>) => { p.row.actual_inventory_cost = 14 }],
    ['wrong contract', (p: ReturnType<typeof asrParts>) => { p.value.contract_version = 'other' }],
    ['missing unit evidence', (p: ReturnType<typeof asrParts>) => { p.standard.unit_basis_audit_ids = [] }],
    ['unknown without reason', (p: ReturnType<typeof asrParts>) => { p.row.comparison_status = 'UNKNOWN'; p.row.delta_qty = null }],
    ['partial page', (p: ReturnType<typeof asrParts>) => { (p.value.contractors as Record<string, unknown>).total = 2 }],
  ])('refuses %s before UI can show an authoritative comparison', (_name, mutate) => {
    const p = asrParts(); mutate(p); expect(() => parseAccessoryReportWorkspace(p.value, asrQuery())).toThrow()
  })
  it('validates calendar and period bounds', () => {
    expect(accessoryReportPeriod('2026-02-29', '2026-03-01')).toBe(false)
    expect(accessoryReportPeriod('2026-10-17', '2026-10-16')).toBe(false)
    expect(accessoryReportPeriod('2026-01-01', '2027-01-02')).toBe(true)
    expect(accessoryReportPeriod('2026-01-01', '2027-01-03')).toBe(false)
  })
})
