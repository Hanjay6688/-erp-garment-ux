import { describe, expect, it } from 'vitest'
import { conversionPayload, parseConversionWorkspace, validateConversionResult, type ConversionLot } from './productConversion'
const id = 'a1000000-0000-0000-0000-000000000001', target = 'a2000000-0000-0000-0000-000000000001'
const lot: ConversionLot = { id, lot_number: 'LOT-1', product_id: id, sku: 'SOURCE', product_name: 'Sumber', location_id: id, location_name: 'Gudang', qty: 6, source_revision: 'opaque-revision', unit_hpp: '10.010000' }
const ws = { lots: [lot], targets: [{ id: target, sku: 'TARGET', product_name: 'Tujuan' }], documents: [], total: 1, page: 1, page_size: 25, targets_total: 1, target_page: 1, documents_total: 0, document_page: 1 }
describe('conversion boundary', () => {
  it('keeps canonical legacy IDs, exact money and opaque revisions', () => { expect(parseConversionWorkspace(ws).lots[0]).toEqual(lot) })
  it('does not treat missing stock as zero or accept duplicate composite lots', () => {
    expect(() => parseConversionWorkspace({ ...ws, lots: [{ ...lot, qty: null }] })).toThrow()
    expect(() => parseConversionWorkspace({ ...ws, lots: [lot, lot] })).toThrow()
  })
  it('uses WIB time and refuses quantities beyond the selected lot', () => {
    const p = conversionPayload(lot, target, '6', '2026-09-26T09:00', 'Ganti label')
    expect(p.physical_at).toBe('2026-09-26T02:00:00.000Z')
    expect(p.expected_version).toBe('opaque-revision')
    expect(() => conversionPayload(lot, target, '7', '2026-09-26T09:00', 'Ganti label')).toThrow()
  })
  it('retains recovery for mismatched request, target or reversal', () => {
    expect(() => validateConversionResult({ request_id: target, action: 'POST', conversion_id: id, status: 'POSTED', destination_lot_id: target }, 'POST', id, {})).toThrow()
    expect(() => validateConversionResult({ request_id: id, action: 'SAVE_REWORK', rework_id: id, target_product_id: id }, 'SAVE_REWORK', id, { target_product_id: target })).toThrow()
    expect(() => validateConversionResult({ request_id: id, action: 'REVERSE', conversion_id: target, status: 'REVERSED' }, 'REVERSE', id, { conversion_id: id })).toThrow()
  })
})
