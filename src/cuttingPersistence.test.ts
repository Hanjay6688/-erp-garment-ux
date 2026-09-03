import { describe, expect, it } from 'vitest'
import {
  draftPickupAllocations,
  parseCuttingSaveResult,
  parseCuttingWorkspace,
  parsePickupQueue,
  parsePickupSaveResult,
  pickupAllocationState,
  pickupBatchesPayload,
  seedPickupAllocations,
  type PickupQueueRow,
} from './cuttingPersistence'

const queueRow: PickupQueueRow = {
  cutting_group_id: 'group-1', group_number: 'POT-001', row_version: 4,
  po_id: 'po-1', po_number: 'PO-001', model_code: 'MDL', model_name: 'Model',
  assigned_contractor_id: 'mandor-1', assigned_contractor_name: 'Mandor A',
  cut_at: '2026-09-03T00:00:00Z', status: 'CUT', picked_up_at: null, executor_name: null,
  source_location_id: 'loc-1', source_location_code: 'RM', pickup_eligible: true,
  pattern_id: 'pattern-1', pattern_code: 'REG', pattern_revision: 'R1', pattern_name: 'Regular',
  total_qty_issued: 20, total_pieces: 9, pickup: null,
  rolls: [
    {
      cutting_group_roll_id: 'group-roll-1', roll_id: 'roll-1', roll_number: 'R-1',
      material_id: 'material-1', material_sku: 'FAB-1', material_name: 'Fabric', unit_code: 'yd',
      supplier_name: 'Supplier', original_qty: 20, qty_issued: 20, qty_consumed: 18,
      qty_reported_remaining: 2,
      yields: [
        { yield_id: 'yield-s', size_slot_id: 'slot-s', slot_no: 1, size_id: 'size-s', size_code: 'S', drawing_no: 1, label: null, qty_pcs: 4 },
        { yield_id: 'yield-m', size_slot_id: 'slot-m', slot_no: 2, size_id: 'size-m', size_code: 'M', drawing_no: 1, label: null, qty_pcs: 5 },
      ],
    },
  ],
}

describe('cutting persistence response boundary', () => {
  it('parses the connected workspace including resumable canonical drafts', () => {
    const parsed = parseCuttingWorkspace({
      location_id: 'loc-1', roll_query: null, limit: 100, offset: 0, roll_total: 1,
      orders: [{
        id: 'po-1', po_number: 'PO-001', model_id: 'model-1', model_code: 'MDL', model_name: 'Model',
        status: 'CUTTING', current_stage: 'CUTTING', contractor_id: null, contractor_name: null,
      }],
      sizes: [{ id: 'size-s', code: 'S', sort_order: 1, model_ids: ['model-1'] }],
      locations: [{ id: 'loc-1', code: 'RM', name: 'Raw Material' }],
      contractors: [{ id: 'mandor-1', code: 'M-1', name: 'Mandor A' }],
      drafts: [{
        cutting_group_id: 'group-1', group_number: 'POT-001', row_version: 2,
        po_id: 'po-1', po_number: 'PO-001', model_code: 'MDL', model_name: 'Model',
        cut_at: '2026-09-03T00:00:00Z', source_location_id: 'loc-1', notes: null,
        pattern_id: 'pattern-1', pattern_code: 'REG', pattern_revision: 'R1', pattern_name: 'Regular',
        pattern_is_active: true, editable: true,
        size_slots: [{ slot_no: 1, size_id: 'size-s', size_code: 'S', drawing_no: 1, label_override: null }],
        rolls: [{
          roll_id: 'roll-1', roll_number: 'R-1', material_id: 'material-1', material_sku: 'FAB-1',
          material_name: 'Fabric', unit_code: 'yd', supplier_id: null, supplier_name: null,
          original_qty: 20, qty_issued: 20, qty_consumed: 18, qty_reported_remaining: 2,
          yields: [{ slot_no: 1, qty_pcs: 9 }],
        }],
      }],
      rolls: [{
        id: 'roll-1', roll_number: 'R-1', material_id: 'material-1', material_sku: 'FAB-1',
        material_name: 'Fabric', unit_code: 'yd', supplier_id: null, supplier_code: null,
        supplier_name: null, original_qty: 20, available_qty: 20, status: 'AVAILABLE', received_at: null,
      }],
    })
    expect(parsed.drafts[0]).toMatchObject({ cutting_group_id: 'group-1', pattern_code: 'REG', editable: true })
    expect(parsed.sizes[0].model_ids).toEqual(['model-1'])
    expect(parsed.rolls[0].available_qty).toBe(20)
  })

  it('keeps grandfathered nullable Pola/location facts readable', () => {
    const parsed = parseCuttingWorkspace({
      location_id: null, roll_query: null, limit: 100, offset: 0, roll_total: 0,
      orders: [], sizes: [], locations: [], contractors: [], rolls: [],
      drafts: [{
        cutting_group_id: 'legacy', group_number: 'OLD', row_version: 1,
        po_id: 'po', po_number: 'PO', model_code: 'M', model_name: 'Model',
        cut_at: '2025-01-01T00:00:00Z', source_location_id: null, notes: null,
        pattern_id: null, pattern_code: null, pattern_revision: null, pattern_name: null,
        pattern_is_active: null, editable: true, size_slots: [], rolls: [],
      }],
    })
    expect(parsed.drafts[0]).toMatchObject({ source_location_id: null, pattern_id: null })
  })

  it('rejects malformed workspace identity instead of inventing client data', () => {
    expect(() => parseCuttingWorkspace({
      location_id: null, roll_query: null, limit: 100, offset: 0, roll_total: 0,
      orders: [{ id: null }], sizes: [], locations: [], contractors: [], drafts: [], rolls: [],
    })).toThrow(/ID PO/)
  })

  it('parses cutting and pickup mutation receipts', () => {
    expect(parseCuttingSaveResult({
      cutting_group_id: 'group-1', group_number: 'POT-001', status: 'CUT', row_version: 3,
      pattern_id: 'pattern-1', pattern_code: 'REG', pattern_revision: 'R1', pattern_name: 'Regular',
      source_location_id: 'loc-1', material_issue_posted: true, total_rolls: 1,
      total_qty_issued: 20, total_qty_consumed: 18, total_qty_reported_remaining: 2, total_pieces: 9,
    })).toMatchObject({ material_issue_posted: true, total_pieces: 9 })
    expect(parsePickupSaveResult({
      pickup_id: 'pickup-1', cutting_group_id: 'group-1', status: 'POSTED', row_version: 2,
      group_row_version: 5, picked_up_at: '2026-09-03T01:00:00Z', contractor_id: 'mandor-1',
      allocation_mode: 'ROLL', batch_count: 2, allocated_pieces: 9,
    })).toMatchObject({ status: 'POSTED', allocated_pieces: 9 })
  })
})

describe('pickup lineage allocation', () => {
  it('seeds whole-roll allocation and proves exact reconciliation', () => {
    const matrix = seedPickupAllocations(queueRow, 2, 'ROLL')
    expect(matrix).toEqual({ 'yield-s': [4, 0], 'yield-m': [5, 0] })
    expect(pickupAllocationState(queueRow, matrix, 2)).toEqual({
      sourceTotal: 9, allocatedTotal: 9, exact: true, batchTotals: [9, 0], everyBatchUsed: false,
    })
  })

  it('seeds by size, serializes only positive cells, and detects over-allocation', () => {
    const matrix = seedPickupAllocations(queueRow, 2, 'SIZE')
    expect(matrix).toEqual({ 'yield-s': [4, 0], 'yield-m': [0, 5] })
    expect(pickupBatchesPayload(matrix, ['S only', 'M only'], 2)).toEqual([
      { batch_no: 1, notes: 'S only', allocations: [{ cutting_roll_yield_id: 'yield-s', qty_pcs: 4 }] },
      { batch_no: 2, notes: 'M only', allocations: [{ cutting_roll_yield_id: 'yield-m', qty_pcs: 5 }] },
    ])
    expect(pickupAllocationState(queueRow, { ...matrix, 'yield-s': [5, 0] }, 2).exact).toBe(false)
  })

  it('restores an editable draft matrix by canonical yield id', () => {
    expect(draftPickupAllocations({
      id: 'pickup-1', contractor_id: 'mandor-1', contractor_name: 'Mandor A',
      picked_up_at: '2026-09-03T00:00:00Z', allocation_mode: 'SIZE', status: 'DRAFT',
      notes: null, row_version: 2,
      batches: [
        { id: 'b1', batch_no: 1, notes: null, qty_pcs: 4, allocations: [{ cutting_roll_yield_id: 'yield-s', qty_pcs: 4 }] },
        { id: 'b2', batch_no: 2, notes: null, qty_pcs: 5, allocations: [{ cutting_roll_yield_id: 'yield-m', qty_pcs: 5 }] },
      ],
    }, 2)).toEqual({ 'yield-s': [4, 0], 'yield-m': [0, 5] })
  })
})

describe('pickup queue parser', () => {
  it('preserves draft allocation identity needed for safe resume', () => {
    const parsed = parsePickupQueue({
      filter: 'WAITING', pattern_id: null, query: null, limit: 50, offset: 0, total: 1,
      contractors: [{ id: 'mandor-1', code: 'M-1', name: 'Mandor A' }],
      rows: [{
        ...queueRow,
        pickup: {
          id: 'pickup-1', contractor_id: 'mandor-1', contractor_name: 'Mandor A',
          picked_up_at: '2026-09-03T00:00:00Z', allocation_mode: 'ROLL', status: 'DRAFT', notes: null,
          row_version: 2,
          batches: [{
            id: 'batch-1', batch_no: 1, notes: null, qty_pcs: 9,
            allocations: [
              { cutting_roll_yield_id: 'yield-s', qty_pcs: 4 },
              { cutting_roll_yield_id: 'yield-m', qty_pcs: 5 },
            ],
          }],
        },
      }],
    })
    expect(parsed.rows[0].pickup?.batches[0].allocations).toHaveLength(2)
    expect(parsed.rows[0]).toMatchObject({ assigned_contractor_id: 'mandor-1', assigned_contractor_name: 'Mandor A' })
  })
})
