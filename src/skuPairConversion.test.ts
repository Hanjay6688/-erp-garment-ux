import { describe, it, expect } from 'vitest'
import { autoConversionPayload, parseAutoConversionPreview, parseConversionWorkspace, validateConversionResult, type ConversionSource } from './productConversion'
import { skuPairPayload, validateSkuPairResult } from './skuMaster'
import { parseProductionEnvelope } from './productionRecovery'
const u = (n: number) => `10000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const source: ConversionSource = { product_id: u(1), sku: '1002', product_name: 'Vivo 1002 31', brand_name: 'Vivo', size: '31', location_id: u(9), location_name: 'Gudang A', stock: { physical: 10, reserved: 1, available: 9 } }
const payload = autoConversionPayload(source, u(2), '4', '2026-10-20T07:00', 'Barang tercampur')
const preview = () => ({ ...payload, location_name: 'Gudang A', source_sku: '1002', target_sku: '1001', source_revision: 'opaque-latest-server-value', source_stock: source.stock, target_stock: { physical: 4, reserved: 0, available: 4 }, source_after: { physical: 6, reserved: 1, available: 5 }, target_after: { physical: 8, reserved: 0, available: 8 }, cost: { source_value: '60.06' }, allocations: [{ source_lot_id: u(10), qty_pcs: 2, source_revision: 'v1', source_value: '20.02', lot_number: 'L1' }, { source_lot_id: u(11), qty_pcs: 2, source_revision: 'v2', source_value: '40.04', lot_number: 'L2' }] })
describe('owner 29 October pair and conversion boundary', () => {
  it('retains an exact SAVE_PAIR recovery envelope only in the SKU domain', () => {
    const command = { action: 'SAVE_PAIR', payload: skuPairPayload(u(21), u(22), 'reviewed', 'Padanan owner'), expectedVersion: null }
    const envelope = { ...command, id: u(90), createdAt: '2026-10-29T00:00:00Z', fingerprint: JSON.stringify(command) }
    const raw = JSON.stringify(envelope)
    expect(parseProductionEnvelope(raw, 'SKU')).toEqual(envelope)
    expect(() => parseProductionEnvelope(raw, 'PRODUCT_CONVERSION')).toThrow()
  })
  it('sends explicit physical product and location, preserves WIB time, and refuses self or unavailable quantities', () => {
    expect(payload).toMatchObject({ source_product_id: u(1), target_product_id: u(2), physical_at: '2026-10-20T00:00:00.000Z', qty_pcs: 4 })
    for (const [target, qty] of [[u(1), '1'], [u(2), '10'], [u(2), '1.5']]) expect(() => autoConversionPayload(source, target, qty, '2026-10-20T07:00', 'reason')).toThrow()
  })
  it('accepts multi-lot before/after proof and refuses altered reservations, quantities or wrong target scope', () => {
    expect(parseAutoConversionPreview(preview(), payload).allocations).toHaveLength(2)
    const variants = [() => ({ ...preview(), target_product_id: u(3) }), () => ({ ...preview(), source_after: { physical: 6, reserved: 0, available: 6 } }), () => ({ ...preview(), allocations: [preview().allocations[0]] })]
    for (const invalid of variants) expect(() => parseAutoConversionPreview(invalid(), payload)).toThrow()
    const hidden = { ...preview(), cost: {}, allocations: preview().allocations.map(a => ({ ...a, source_value: null })) }
    expect(parseAutoConversionPreview(hidden, payload).cost).toEqual({})
  })
  it('requires source/target and unique Native allocation IDs on successful automatic conversion', () => {
    const result = { ...preview(), conversion_id: u(80), request_id: u(80), action: 'POST', status: 'POSTED', destination_lot_id: u(81), conversion_ids: [u(80), u(82)], destination_lot_ids: [u(81), u(83)] }
    validateConversionResult(result, 'POST', u(80), payload)
    for (const invalid of [{ ...result, qty_pcs: 1 }, { ...result, conversion_ids: [u(80), u(80)] }, { ...result, destination_lot_ids: [u(81)] }]) expect(() => validateConversionResult(invalid, 'POST', u(80), payload)).toThrow()
  })
  it('refuses duplicate product/location source rows and missing stock rather than displaying zero', () => {
    const w = { contract_version: 'cp7.sku-conversion.v1', sources: [source], sources_total: 1, lots: [], targets: [], documents: [], total: 0, page: 1, page_size: 25, targets_total: 0, target_page: 1, documents_total: 0, document_page: 1 }
    expect(parseConversionWorkspace(w).sources?.[0]).toEqual(source)
    expect(() => parseConversionWorkspace({ ...w, sources: [source, source] })).toThrow('ganda')
    expect(() => parseConversionWorkspace({ ...w, sources: [{ ...source, stock: null }] })).toThrow()
  })
  it('pair edits do not request stock writers or per-size membership changes and responses must match both endpoints', () => {
    const p = skuPairPayload(u(21), u(22), 'opaque-master-revision', 'Padanan owner')
    expect(Object.keys(p).sort()).toEqual(['expected_version', 'reason', 'source_group_id', 'target_group_id'])
    const r = { request_id: u(90), action: 'SAVE_PAIR', status: 'SAVED', source_group_id: u(21), target_group_id: u(22), revision: 'next', removed: [] }
    validateSkuPairResult(r, u(90), p)
    expect(() => validateSkuPairResult({ ...r, target_group_id: u(23) }, u(90), p)).toThrow()
    expect(skuPairPayload(u(22), '', 'next', 'Hapus padanan').target_group_id).toBeNull()
    expect(() => skuPairPayload(u(21), u(21), 'next', 'self')).toThrow()
  })
})
