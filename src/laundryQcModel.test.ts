import { describe, expect, it } from 'vitest'
import {
  findLaundryRateAt, parseLaundryQcWorkspace, productEffectiveAt, totalReadyToSend,
} from './laundryQcModel'

const uuid = (suffix: number) => `00000000-0000-4000-8000-${String(suffix).padStart(12, '0')}`

function lookups() {
  return {
    vendors: [{ id: uuid(1), code: 'LDR-A', name: 'Laundry A' }],
    wash_processes: [{ id: uuid(2), code: 'WASH', name: 'Cuci' }],
    rate_versions: [
      { id: uuid(3), vendor_id: uuid(1), wash_process_id: uuid(2), rate_per_pcs: 1000, effective_from: '2026-01-01T00:00:00Z', effective_to: '2026-06-01T00:00:00Z' },
      { id: uuid(4), vendor_id: uuid(1), wash_process_id: uuid(2), rate_per_pcs: 1200, effective_from: '2026-06-01T00:00:00Z', effective_to: null },
    ],
    fg_locations: [{ id: uuid(5), code: 'FG-A', name: 'FG A' }],
    products: [{
      id: uuid(6), sku: 'SKU-A-31', name: 'Celana A 31', model_id: uuid(7), brand_id: uuid(8),
      model_code: 'M-1', model_name: 'Model Satu', brand_code: 'A', brand_name: 'Brand A', size_id: uuid(9), size_code: '31', color: 'Hitam',
      effective_from: '2026-01-01T00:00:00Z', effective_to: null,
    }],
  }
}

function base(scope: 'LAUNDRY' | 'QC') {
  return {
    contract_version: 'CP6_V2620', scope, generated_at: '2026-09-04T10:00:00Z', lookups: lookups(),
    readiness: {
      laundry_writer_ready: true, qc_writer_ready: true,
      lineage_integrity_ok: true, lineage_issue_count: 0,
      no_fixture_fallback: true, failed_wash_with_charge_supported: false,
    },
    ready_batches: scope === 'LAUNDRY' ? [{
      distribution_batch_id: uuid(10), batch_no: 1, pickup_id: uuid(11), cutting_group_id: uuid(12),
      cutting_group_row_version: 4, group_number: 'P-001', pattern_id: uuid(13), pattern_code: 'PAT-A',
      pattern_revision: 'R1', pattern_name: 'Pola A', po_id: uuid(14), po_number: 'PO-001', po_status: 'SEWING',
      model_code: 'MOD-A', model_name: 'Model A', contractor_id: uuid(15), contractor_code: 'M-01',
      contractor_name: 'Mandor A', picked_up_at: '2026-09-01T00:00:00Z', group_unsent_ready_qty_pcs: 8,
      sizes: [{ size_id: uuid(9), size_code: '31', sort_order: 1, allocated_qty_pcs: 10, sent_qty_pcs: 2, available_qty_pcs: 8 }],
    }] : [],
    deliveries: [],
    qc_queue: scope === 'QC' ? [{
      source_batch_size_line_id: uuid(16), receipt_line_id: uuid(17), receipt_id: uuid(18), receipt_number: 'LRC-001',
      receipt_physical_at: '2026-09-03T00:00:00Z', distribution_batch_id: uuid(10), batch_no: 1,
      delivery_line_id: uuid(19), delivery_id: uuid(20), delivery_number: 'LDR-001', vendor_name: 'Laundry A',
      cutting_group_id: uuid(12), group_number: 'P-001', cutting_group_row_version: 5, po_id: uuid(14),
      po_number: 'PO-001', model_id: uuid(7), model_code: 'MOD-A', model_name: 'Model A', size_id: uuid(9),
      size_code: '31', size_sort: 1, qty_good_received: 8, qc_accounted_qty_pcs: 3,
      available_for_qc_qty_pcs: 5, completion_status: 'READY_FOR_QC', remaining_qc_qty_pcs: 7,
    }] : [],
    qc_history: [], legacy_unlinked: { delivery_count: 0, receipt_count: 0 },
  }
}

describe('parseLaundryQcWorkspace', () => {
  it('accepts conserved authoritative Laundry and QC scopes', () => {
    expect(parseLaundryQcWorkspace(base('LAUNDRY')).ready_batches[0].sizes[0].available_qty_pcs).toBe(8)
    expect(parseLaundryQcWorkspace(base('QC')).qc_queue[0].available_for_qc_qty_pcs).toBe(5)
  })

  it('counts one Potongan ready balance once across multiple distribution batches', () => {
    const fixture = base('LAUNDRY')
    fixture.ready_batches.push({
      ...fixture.ready_batches[0], distribution_batch_id: uuid(59), batch_no: 2,
    })
    const workspace = parseLaundryQcWorkspace(fixture)
    expect(totalReadyToSend(workspace.ready_batches)).toBe(8)
  })

  it('rejects any fixture fallback or charged-failure shortcut', () => {
    const fixture = base('LAUNDRY')
    fixture.readiness.no_fixture_fallback = false
    expect(() => parseLaundryQcWorkspace(fixture)).toThrow('Batas reliability')
    const charged = base('LAUNDRY')
    charged.readiness.failed_wash_with_charge_supported = true
    expect(() => parseLaundryQcWorkspace(charged)).toThrow('Batas reliability')
  })

  it('fails closed when backend reports any CP6 lineage issue', () => {
    const brokenLineage = base('LAUNDRY')
    brokenLineage.readiness.lineage_integrity_ok = false as true
    brokenLineage.readiness.lineage_issue_count = 1 as 0
    expect(() => parseLaundryQcWorkspace(brokenLineage)).toThrow('Batas reliability')
  })

  it('rejects changed or deleted quantity conservation', () => {
    const fixture = base('LAUNDRY')
    fixture.ready_batches[0].sizes[0].available_qty_pcs = 9
    expect(() => parseLaundryQcWorkspace(fixture)).toThrow('Konservasi size')
    const qc = base('QC')
    qc.qc_queue[0].available_for_qc_qty_pcs = 6
    expect(() => parseLaundryQcWorkspace(qc)).toThrow('Konservasi Good')
  })

  it('rejects null/string numeric coercion and malformed authoritative timestamps', () => {
    const nullQty = base('LAUNDRY')
    nullQty.ready_batches[0].sizes[0].sent_qty_pcs = null as unknown as number
    expect(() => parseLaundryQcWorkspace(nullQty)).toThrow('Qty sudah dikirim tidak valid')

    const stringRate = base('LAUNDRY')
    stringRate.lookups.rate_versions[0].rate_per_pcs = '1000' as unknown as number
    expect(() => parseLaundryQcWorkspace(stringRate)).toThrow('Rate per pcs tidak valid')

    const badTime = base('LAUNDRY')
    badTime.generated_at = '4 September 2026'
    expect(() => parseLaundryQcWorkspace(badTime)).toThrow('timestamp authoritative')

    const reversedRate = base('LAUNDRY')
    reversedRate.lookups.rate_versions[0].effective_to = '2025-12-31T00:00:00Z'
    expect(() => parseLaundryQcWorkspace(reversedRate)).toThrow('periode berlaku terbalik')

    const readinessLie = base('LAUNDRY')
    readinessLie.readiness.laundry_writer_ready = false
    expect(() => parseLaundryQcWorkspace(readinessLie)).toThrow('Flag kesiapan writer')
  })

  it('accepts one Brand + SKU across exact sizes and the same number under another Brand', () => {
    const fixture = base('LAUNDRY')
    const first = fixture.lookups.products[0]
    fixture.lookups.products.push({
      ...first, id: uuid(60), size_id: uuid(61), size_code: '32', name: 'Celana A 32',
    }, {
      ...first, id: uuid(62), brand_id: uuid(63), brand_code: 'B', brand_name: 'Brand B',
      model_id: uuid(64), model_code: 'M-2', model_name: 'Model Dua', color: 'Biru',
    })
    const parsed = parseLaundryQcWorkspace(fixture)
    expect(parsed.lookups.products).toHaveLength(3)
    expect(parsed.lookups.products.map((product) => `${product.brand_name}:${product.sku}`))
      .toEqual(['Brand A:SKU-A-31', 'Brand A:SKU-A-31', 'Brand B:SKU-A-31'])
  })

  it('rejects ambiguous same-size identity or model/color drift inside one Brand + SKU', () => {
    const sameSize = base('LAUNDRY')
    sameSize.lookups.products.push({ ...sameSize.lookups.products[0], id: uuid(70) })
    expect(() => parseLaundryQcWorkspace(sameSize)).toThrow('Merek + Nomor SKU + size yang sama')

    const drift = base('LAUNDRY')
    drift.lookups.products.push({
      ...drift.lookups.products[0], id: uuid(71), size_id: uuid(72), size_code: '32',
      model_id: uuid(73), model_code: 'M-OTHER', model_name: 'Model Lain',
    })
    expect(() => parseLaundryQcWorkspace(drift)).toThrow('tidak konsisten pada Model/warna')

    const duplicateCombination = base('LAUNDRY')
    duplicateCombination.lookups.products.push({
      ...duplicateCombination.lookups.products[0], id: uuid(79), sku: 'SKU-LAIN-31',
    })
    expect(() => parseLaundryQcWorkspace(duplicateCombination))
      .toThrow('kombinasi Merek/Model/warna/size aktif')
  })

  it('rejects contradictory lookup metadata and Potongan versions before rendering a writer', () => {
    const brandConflict = base('LAUNDRY')
    brandConflict.lookups.products.push({
      ...brandConflict.lookups.products[0], id: uuid(74), sku: 'SKU-B-31',
      brand_code: 'BENTROK', brand_name: 'Nama Merek Berbeda',
    })
    expect(() => parseLaundryQcWorkspace(brandConflict)).toThrow('Metadata Merek Final SKU kontradiktif')

    const groupConflict = base('QC')
    groupConflict.qc_queue.push({
      ...groupConflict.qc_queue[0], source_batch_size_line_id: uuid(75),
      receipt_line_id: uuid(76), receipt_id: uuid(77), group_number: 'P-TERUBAH',
    })
    expect(() => parseLaundryQcWorkspace(groupConflict)).toThrow('Metadata Potongan antrean QC kontradiktif')
  })

  it('rejects cross-scope writer data leakage', () => {
    const fixture = base('LAUNDRY')
    fixture.qc_queue = base('QC').qc_queue
    expect(() => parseLaundryQcWorkspace(fixture)).toThrow('membocorkan data QC')
  })

  it('requires every reversal affordance to match the backend blocker decision', () => {
    const laundry = base('LAUNDRY')
    const blockedDelivery = {
      delivery_id: uuid(20), delivery_number: 'LDR-001', row_version: 3,
      status: 'PARTIAL_RETURN', physical_at: '2026-09-02T00:00:00Z',
      target_dyeing_color: 'Hitam', special_instruction: null, po_id: uuid(14),
      po_number: 'PO-001', model_id: uuid(7), cutting_group_id: uuid(12),
      group_number: 'P-001', cutting_group_row_version: 4, model_code: 'MOD-A',
      model_name: 'Model A', contractor_name: 'Mandor A', vendor_id: uuid(1),
      vendor_code: 'LDR-A', vendor_name: 'Laundry A', wash_process_id: uuid(2),
      process_code: 'WASH', process_name: 'Cuci', delivery_line_id: uuid(21),
      qty_sent_pcs: 2, estimated_rate_snapshot: 1200, estimated_cost: 2400,
      distribution_batch_id: uuid(10), batch_no: 1, returned_qty_pcs: 1,
      physical_outstanding_qty_pcs: 1, active_claim_qty_pcs: 0,
      reversible: false, reversal_blocker: 'Masih ada receipt aktif.',
      sizes: [{
        delivery_batch_size_line_id: uuid(22), size_id: uuid(9), size_code: '31',
        sort_order: 1, qty_sent_pcs: 2, good_returned_qty_pcs: 1,
        bs_returned_qty_pcs: 0, outstanding_qty_pcs: 1,
      }],
      receipts: [{
        id: uuid(23), number: 'LRC-001', status: 'POSTED', row_version: 2,
        physical_at: '2026-09-03T00:00:00Z', actual_cost: 1200,
        reversible: false, reversal_blocker: 'Receipt sudah dipakai QC.',
      }],
    }
    ;(laundry.deliveries as unknown[]).push(blockedDelivery)
    expect(parseLaundryQcWorkspace(laundry).deliveries[0].receipts[0].reversible).toBe(false)
    blockedDelivery.receipts[0].reversible = true
    expect(() => parseLaundryQcWorkspace(laundry)).toThrow('reversal penerimaan kontradiktif')

    const qc = base('QC')
    const blockedQc = {
      qc_inspection_id: uuid(24), inspection_number: 'FGP-001', status: 'POSTED',
      row_version: 4, physical_at: '2026-09-03T01:00:00Z',
      destination_location_id: uuid(5), location_name: 'FG A', po_id: uuid(14),
      po_number: 'PO-001', good_qty_pcs: 1, bs_qty_pcs: 0,
      cutting_group_count: 1, reversible: false,
      reversal_blocker: 'FG hasil QC masih dipakai transaksi downstream aktif.',
    }
    ;(qc.qc_history as unknown[]).push(blockedQc)
    expect(parseLaundryQcWorkspace(qc).qc_history[0].reversible).toBe(false)
    blockedQc.reversible = true
    expect(() => parseLaundryQcWorkspace(qc)).toThrow('reversal QC kontradiktif')
  })

  it('selects the exact backdated rate interval and product interval', () => {
    const workspace = parseLaundryQcWorkspace(base('LAUNDRY'))
    expect(findLaundryRateAt(workspace, uuid(1), uuid(2), '2026-05-31T23:59:59Z')?.rate_per_pcs).toBe(1000)
    expect(findLaundryRateAt(workspace, uuid(1), uuid(2), '2026-06-01T00:00:00Z')?.rate_per_pcs).toBe(1200)
    expect(productEffectiveAt(workspace.lookups.products[0], '2026-09-04T00:00:00Z')).toBe(true)
  })

  it('fails closed when two rate versions overlap at the physical time', () => {
    const fixture = base('LAUNDRY')
    fixture.lookups.rate_versions.push({
      id: uuid(99), vendor_id: uuid(1), wash_process_id: uuid(2), rate_per_pcs: 9999,
      effective_from: '2026-08-01T00:00:00Z', effective_to: null,
    })
    expect(() => parseLaundryQcWorkspace(fixture)).toThrow('Versi rate Laundry bertumpuk')
  })
})
