import { describe, expect, it } from 'vitest'
import {
  bsPatternLabel, cleanBsQuantity, exactReworkCompletion, parseBsResolutionWorkspace,
} from './bsResolutionModel'

const baseResponse = () => ({
  filter: 'ACTIVE', kind: 'ALL', pattern_id: null, query: null, limit: 50, offset: 0, total: 1,
  lookups: {
    contractors: [{ id: 'contractor-1', code: 'M-01', name: 'Mandor A' }],
    vendors: [{ id: 'vendor-1', code: 'L-01', name: 'Laundry A' }],
    fg_locations: [{ id: 'location-1', code: 'FG-01', name: 'Gudang FG' }],
    work_components: [{ id: 'work-1', code: 'JAHIT', name: 'Jahit', category: 'LABOR' }],
    products: [{ id: 'product-1', sku: 'SKU-1', name: 'Produk 1' }],
    laundry_sources: [{ id: 'delivery-1', number: 'LDR-1', vendor_id: 'vendor-1', vendor_name: 'Laundry A', po_number: 'PO-1', physical_at: '2026-09-03T08:00:00Z', qty_sent_pcs: 10, qty_claimable_pcs: 7 }],
    laundry_receipt_sources: [{ id: 'receipt-line-1', receipt_id: 'receipt-1', number: 'LRC-1', delivery_id: 'delivery-1', delivery_number: 'LDR-1', vendor_id: 'vendor-1', vendor_name: 'Laundry A', po_number: 'PO-1', physical_at: '2026-09-03T09:00:00Z', qty_bs_laundry: 3, qty_claimable_pcs: 2 }],
    settled_claims: [{ id: 'claim-1', number: 'CLM-1', vendor_id: 'vendor-1', vendor_name: 'Laundry A', delivery_id: 'delivery-1', receipt_line_id: null, qty_claimed: 4, compensation_amount: 100_000, available_qty: 2, available_amount: 50_000 }],
  },
  rows: [{
    case_key: 'BS:case-1', kind: 'BS', id: 'case-1', number: 'BS-1', status: 'ON_HOLD', row_version: 4,
    qty_pcs: 10, resolved_qty: 2, active_rework_qty: 0, available_qty: 8, opened_at: '2026-09-03T08:00:00Z',
    po_id: 'po-1', po_number: 'PO-1', model_name: 'Model A', cutting_group_id: 'group-1', group_number: 'POT-1',
    patterns: [{ id: 'pattern-1', code: 'REG', revision: 'R2', name: 'Regular' }],
    product_id: 'product-1', sku: 'SKU-1', product_name: 'Produk 1', responsible_contractor_id: 'contractor-1',
    contractor_name: 'Mandor A', responsible_vendor_id: null, vendor_name: null, detected_stage: 'QC', cause_source: 'SEWING',
    untracked_type: null, claim_type: null, compensation_amount: 0, laundry_delivery_id: null, laundry_receipt_line_id: null,
    legacy_reference: null, notes: 'Tahan cek fisik', next_action: 'RELEASE_HOLD', is_closed: false,
    accessory_bom: { state: 'AVAILABLE', bom_version_id: 'bom-1', items: [
      { id: 'bom-item-1', category_id: 'category-1', code: 'KANCING', name: 'Kancing', base_uom_code: 'PCS', qty_per_good_fg_base: 2, reimbursement_rate: 100, reimbursement_uom_code: 'PCS' },
      { id: 'bom-item-2', category_id: 'category-2', code: 'LABEL', name: 'Label', base_uom_code: 'PCS', qty_per_good_fg_base: 1, reimbursement_rate: 50, reimbursement_uom_code: 'PCS' },
    ] },
    components: [{ id: 'component-1', work_component_id: 'work-1', code: 'JAHIT', name: 'Jahit', category: 'LABOR', completed_before_bs_qty: 0, lifetime_newly_completed_qty: 0, lifetime_paid_qty: 0, notes: null }],
    resolutions: [{ id: 'resolution-1', resolution_type: 'OTHER', qty_pcs: 2, compensation_amount: 0, responsible_contractor_id: null, responsible_vendor_id: null, source_rework_order_id: null, source_laundry_claim_id: null, physical_at: '2026-09-03T09:00:00Z', notes: 'Selesai', created_at: '2026-09-03T09:01:00Z' }],
    rework_orders: [],
    hold_events: [{ id: 'hold-1', action: 'HOLD', previous_status: 'PARTIAL', resulting_status: 'ON_HOLD', reason: 'Cek ulang', physical_at: '2026-09-03T10:00:00Z', actor_id: 'user-1', actor_name: 'Owner', created_at: '2026-09-03T10:00:01Z' }],
  }],
})

describe('CP5 authoritative response boundary', () => {
  it('preserves Pattern, HOLD history, quantities, and canonical nested resolution facts', () => {
    const workspace = parseBsResolutionWorkspace(baseResponse())
    expect(workspace.rows[0]).toMatchObject({ status: 'ON_HOLD', available_qty: 8, next_action: 'RELEASE_HOLD' })
    expect(workspace.rows[0].hold_events[0]).toMatchObject({ action: 'HOLD', previous_status: 'PARTIAL' })
    expect(workspace.rows[0].resolutions[0]).toMatchObject({ resolution_type: 'OTHER', qty_pcs: 2 })
    expect(bsPatternLabel(workspace.rows[0])).toBe('REG · R2 · Regular')
    expect(workspace.lookups.laundry_sources[0]).toMatchObject({ qty_sent_pcs: 10, qty_claimable_pcs: 7 })
    expect(workspace.lookups.laundry_receipt_sources[0]).toMatchObject({ qty_bs_laundry: 3, qty_claimable_pcs: 2 })
    expect(workspace.lookups.settled_claims[0]).toMatchObject({ available_qty: 2, available_amount: 50_000 })
    expect(workspace.rows[0].accessory_bom).toMatchObject({ state: 'AVAILABLE', bom_version_id: 'bom-1' })
    expect(workspace.rows[0].accessory_bom?.items.map((item) => item.code)).toEqual(['KANCING', 'LABEL'])
  })

  it('preserves the immutable selected-accessory decision on a rework order', () => {
    const response = baseResponse()
    response.rows[0].rework_orders = [{
      id: 'rw-1', rework_number: 'RW-1', destination_type: 'CONTRACTOR', contractor_id: 'contractor-1', contractor_name: 'Mandor A', vendor_id: null, vendor_name: null,
      qty_sent: 4, qty_good_returned: 1, qty_bs_returned: 1, physical_sent_at: '2026-09-03T10:00:00Z', completed_at: null, status: 'PARTIAL', cost_posted: false,
      return_fg_location_id: 'location-1', return_fg_location_name: 'Gudang FG', good_fg_lot_id: null, row_version: 2, notes: null, components: [],
      accessory_decision: { state: 'SELECTED', bom_version_id: 'bom-1', reimbursement_contractor_id: 'contractor-1', selected_item_count: 1, selection_sha256: 'a'.repeat(64), basis_at: '2026-09-03T10:00:00Z', selected_items: [
        { id: 'choice-1', bom_item_id: 'bom-item-1', category_id: 'category-1', code: 'KANCING', name: 'Kancing', qty_per_good_fg_base: 2, reimbursement_unit_rate_base: 100 },
      ] },
    }] as never
    const order = parseBsResolutionWorkspace(response).rows[0].rework_orders[0]
    expect(order).toMatchObject({ status: 'PARTIAL', qty_good_returned: 1, qty_bs_returned: 1 })
    expect(order.accessory_decision.selected_items.map((item) => item.code)).toEqual(['KANCING'])
  })

  it('fails closed on malformed nested rework quantities instead of inventing recovery state', () => {
    const response = baseResponse()
    response.rows[0].rework_orders = [{
      id: 'rw-1', rework_number: 'RW-1', destination_type: 'CONTRACTOR', contractor_id: 'contractor-1', contractor_name: 'Mandor A', vendor_id: null, vendor_name: null,
      qty_sent: -1, qty_good_returned: 0, qty_bs_returned: 0, physical_sent_at: '2026-09-03T10:00:00Z', completed_at: null, status: 'OPEN', cost_posted: false,
      return_fg_location_id: null, return_fg_location_name: null, good_fg_lot_id: null, row_version: 1, notes: null, components: [],
    }] as never
    expect(() => parseBsResolutionWorkspace(response)).toThrow(/Qty dikirim rework/)
  })

  it('keeps completion exact and quantity inputs bounded', () => {
    expect(exactReworkCompletion(7, 3, 10)).toBe(true)
    expect(exactReworkCompletion(7, 2, 10)).toBe(false)
    expect(cleanBsQuantity('12.9', 10)).toBe('10')
    expect(cleanBsQuantity('-3', 10)).toBe('0')
    expect(cleanBsQuantity('abc', 10)).toBe('')
  })
})
