// Synthetic Native-shape fixture for operator input lifecycle checks; not business acceptance evidence.
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

export function laundryQcInputFixture(scope: 'LAUNDRY' | 'QC') {
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
