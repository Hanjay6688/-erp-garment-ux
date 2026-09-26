import { describe, expect, it } from 'vitest'
import {
  findLaundryRateAt, parseLaundryBsProductSearch, parseLaundryQcWorkspace,
  productEffectiveAt, totalReadyToSend,
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
      no_fixture_fallback: true, failed_wash_with_charge_supported: true,
    },
    collection_window: {
      transaction_limit: 200, product_limit: 500, query_required_for_more: true,
      transaction_query_scope: 'SOURCE_QUEUE_AND_HISTORY',
      product_search_contract: 'CP6_PRODUCT_SEARCH_V2620B', product_query_decoupled: true,
      products_relevant_to_live_qc: scope === 'QC', products_truncated: false,
      ready_batches_truncated: false, deliveries_truncated: false,
      qc_queue_truncated: false, qc_history_truncated: false, any_truncated: false,
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

function physicalReceiptWorkspace() {
  const workspace = base('LAUNDRY')
  const delivery = {
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
      physical_outstanding_qty_pcs: 1, returned_unprocessed_qty_pcs: 0,
      active_claim_qty_pcs: 0,
      reversible: false, reversal_blocker: 'Masih ada receipt aktif.',
      sizes: [{
        delivery_batch_size_line_id: uuid(22), size_id: uuid(9), size_code: '31',
        sort_order: 1, qty_sent_pcs: 2, good_returned_qty_pcs: 1,
        bs_returned_qty_pcs: 0, outstanding_qty_pcs: 1,
      }],
      receipts: [{
        id: uuid(23), number: 'LRC-001', status: 'POSTED', row_version: 2,
        physical_at: '2026-09-03T00:00:00Z', actual_cost: 1200, actual_rate: 1200,
        cost_status: 'ESTIMATED', event_kind: 'PHYSICAL_RECEIPT',
        failed_wash_attempt_id: null, custody_outcome: null,
        attempted_qty_pcs: null, process_name: 'Cuci',
        reversible: false, reversal_blocker: 'Receipt sudah dipakai QC.',
      }],
    }
  ;(workspace.deliveries as unknown[]).push(delivery)
  return { workspace, receipt: delivery.receipts[0] as Record<string, unknown> }
}

describe('parseLaundryQcWorkspace', () => {
  it('accepts actual wash process on posted and reversed physical receipts without inventing a failed attempt', () => {
    for (const status of ['POSTED', 'REVERSED']) {
      for (const processName of ['Cuci', null]) {
        const { workspace, receipt } = physicalReceiptWorkspace()
        Object.assign(receipt, { status, process_name: processName })
        const parsed = parseLaundryQcWorkspace(workspace).deliveries[0].receipts[0]
        expect(parsed.event_kind).toBe('PHYSICAL_RECEIPT')
        expect(parsed.process_name).toBe(processName)
        expect(parsed.failed_wash_attempt_id).toBeNull()
        expect(parsed.attempted_qty_pcs).toBeNull()
      }
    }
  })

  it('keeps an unknown BD delivery price unknown (null, never zero) and still refuses a coerced rate', () => {
    const { workspace } = physicalReceiptWorkspace()
    const delivery = (workspace.deliveries as Record<string, unknown>[])[0]
    Object.assign(delivery, { estimated_rate_snapshot: null, estimated_cost: null })
    const parsed = parseLaundryQcWorkspace(workspace).deliveries[0]
    expect(parsed.estimated_rate_snapshot).toBeNull()
    expect(parsed.estimated_cost).toBeNull()
    Object.assign(delivery, { estimated_rate_snapshot: '1200' })
    expect(() => parseLaundryQcWorkspace(workspace)).toThrow('Rate estimasi tidak valid')
  })

  it('keeps physical receipts distinct from failed wash attempts with either custody outcome', () => {
    for (const [field, value] of Object.entries({
      failed_wash_attempt_id: uuid(90), custody_outcome: 'RETRY_AT_VENDOR', attempted_qty_pcs: 1,
    })) {
      const { workspace, receipt } = physicalReceiptWorkspace()
      receipt[field] = value
      expect(() => parseLaundryQcWorkspace(workspace)).toThrow('metadata attempt cuci gagal')
    }
    for (const custody of ['RETRY_AT_VENDOR', 'RETURN_UNPROCESSED']) {
      const { workspace, receipt } = physicalReceiptWorkspace()
      Object.assign(receipt, {
        event_kind: 'FAILED_WASH_ATTEMPT', failed_wash_attempt_id: uuid(90),
        custody_outcome: custody, attempted_qty_pcs: 1, process_name: 'Cuci',
      })
      expect(parseLaundryQcWorkspace(workspace).deliveries[0].receipts[0].custody_outcome).toBe(custody)
      for (const field of ['failed_wash_attempt_id', 'custody_outcome', 'attempted_qty_pcs', 'process_name']) {
        const original = receipt[field]
        receipt[field] = null
        expect(() => parseLaundryQcWorkspace(workspace)).toThrow('Metadata attempt cuci gagal tidak lengkap')
        receipt[field] = original
      }
    }
    const malformed = physicalReceiptWorkspace()
    malformed.receipt.process_name = 7
    expect(() => parseLaundryQcWorkspace(malformed.workspace)).toThrow('Nama proses cuci aktual')
  })

  it('accepts conserved authoritative Laundry and QC scopes', () => {
    expect(parseLaundryQcWorkspace(base('LAUNDRY')).ready_batches[0].sizes[0].available_qty_pcs).toBe(8)
    expect(parseLaundryQcWorkspace(base('QC')).qc_queue[0].available_for_qc_qty_pcs).toBe(5)
  })

  it('D08: reads seeded CP3 contractor and model ids (canonical, non RFC-4122) next to v4 ids, and still refuses a malformed id', () => {
    const fixture = base('LAUNDRY')
    Object.assign(fixture.ready_batches[0], { contractor_id: 'a1000000-0000-0000-0000-000000000001' })
    Object.assign(fixture.lookups.products[0], { model_id: 'a2000000-0000-0000-0000-000000000001' })
    const workspace = parseLaundryQcWorkspace(fixture)
    expect(workspace.ready_batches[0].contractor_id).toBe('a1000000-0000-0000-0000-000000000001')
    expect(workspace.ready_batches[0].distribution_batch_id).toBe(uuid(10))
    for (const bad of ['a1000000-0000-0000-0000-00000000001', 'a1000000-0000-0000-0000-00000000000g', '{a1000000-0000-0000-0000-000000000001}']) {
      const broken = base('LAUNDRY')
      Object.assign(broken.ready_batches[0], { contractor_id: bad })
      expect(() => parseLaundryQcWorkspace(broken)).toThrow('bukan UUID valid')
    }
  })

  it('counts one Potongan ready balance once across multiple distribution batches', () => {
    const fixture = base('LAUNDRY')
    fixture.ready_batches.push({
      ...fixture.ready_batches[0], distribution_batch_id: uuid(59), batch_no: 2,
    })
    const workspace = parseLaundryQcWorkspace(fixture)
    expect(totalReadyToSend(workspace.ready_batches)).toBe(8)
  })

  it('rejects any fixture fallback or a backend that silently disables the paid-failure contract', () => {
    const fixture = base('LAUNDRY')
    fixture.readiness.no_fixture_fallback = false
    expect(() => parseLaundryQcWorkspace(fixture)).toThrow('Batas reliability')
    const disabled = base('LAUNDRY')
    disabled.readiness.failed_wash_with_charge_supported = false
    expect(() => parseLaundryQcWorkspace(disabled)).toThrow('Batas reliability')
  })

  it('requires explicit bounded-collection metadata and rejects silent truncation', () => {
    const missing = base('LAUNDRY') as Record<string, unknown>
    delete missing.collection_window
    expect(() => parseLaundryQcWorkspace(missing)).toThrow('Batas koleksi')

    const lying = base('LAUNDRY')
    lying.collection_window.any_truncated = true
    expect(() => parseLaundryQcWorkspace(lying)).toThrow('Status pagination')

    const changedLimit = base('QC')
    changedLimit.collection_window.transaction_limit = 201
    expect(() => parseLaundryQcWorkspace(changedLimit)).toThrow('Kontrak batas koleksi')

    const bounded = base('LAUNDRY')
    bounded.ready_batches = Array.from({ length: 200 }, (_, index) => ({
      ...bounded.ready_batches[0],
      distribution_batch_id: uuid(1000 + index),
      batch_no: index + 1,
    }))
    bounded.collection_window.ready_batches_truncated = true
    bounded.collection_window.any_truncated = true
    expect(parseLaundryQcWorkspace(bounded).ready_batches).toHaveLength(200)
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
    const { workspace: laundry, receipt } = physicalReceiptWorkspace()
    expect(parseLaundryQcWorkspace(laundry).deliveries[0].receipts[0].reversible).toBe(false)
    receipt.reversible = true
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

describe('parseLaundryBsProductSearch', () => {
  it('accepts only a bounded source-bound page with one Model and size', () => {
    const product = lookups().products[0]
    const parsed = parseLaundryBsProductSearch({
      contract_version: 'CP6_LAUNDRY_BS_PRODUCT_SEARCH_V2620C',
      source_delivery_batch_size_line_id: uuid(40),
      physical_at: '2026-09-04T10:00:00Z', query: 'brand', page_limit: 50,
      products: [product], has_more: false, next_cursor: null,
    })
    expect(parsed.products[0].id).toBe(product.id)
  })

  it('rejects mixed source dimensions and contradictory pagination', () => {
    const product = lookups().products[0]
    const page = {
      contract_version: 'CP6_LAUNDRY_BS_PRODUCT_SEARCH_V2620C',
      source_delivery_batch_size_line_id: uuid(40),
      physical_at: '2026-09-04T10:00:00Z', query: null, page_limit: 50,
      products: [product, { ...product, id: uuid(41), size_id: uuid(42), size_code: '32' }],
      has_more: false, next_cursor: null,
    }
    expect(() => parseLaundryBsProductSearch(page)).toThrow('mencampur Model atau ukuran')
    page.products = [product]
    page.has_more = true
    expect(() => parseLaundryBsProductSearch(page)).toThrow('tidak konsisten')
  })
})
