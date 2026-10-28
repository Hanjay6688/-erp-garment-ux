export const recoveryRuntime = {
  mode: 'UAT_AUTH_SIMULATION', authMode: 'UAT_SUPABASE', businessDataMode: 'PARTIAL_CONNECTED',
  businessRpcEnabled: true, accessControlMode: 'CONNECTED', patternMode: 'CONNECTED', cuttingMode: 'CONNECTED',
  distributionMode: 'CONNECTED', wipStatusMode: 'CONNECTED', bsResolutionMode: 'CONNECTED',
  laundryMode: 'CONNECTED', qcFinalMode: 'CONNECTED', fgHandoffMode: 'BLOCKED_UNTIL_AUTHORITATIVE',
  projectRef: 'disposable', supabaseUrl: 'http://127.0.0.1:54321', browserKey: 'sb_publishable_dom_fixture',
} as const
export const recoveryIdentity = {
  runtime: recoveryRuntime,
  identity: {
    status: 'AUTHORIZED', profile: { id: 'actor-1', role: 'OWNER', isActive: true },
    permissions: ['production.cutting.create', 'production.cutting.edit_draft', 'production.cutting.post',
      'production.distribution.create', 'production.distribution.edit_draft', 'production.distribution.post',
      'master.pattern.view', 'production.wip.view', 'production.wip.adjust'],
  },
}
export const recoveryPatterns = [{ id: 'pattern-1', code: 'REG', revision: 'R1', name: 'Regular',
  sort_order: 1, is_active: true, row_version: 1, updated_at: '2026-09-20T00:00:00Z', updated_by: null, usage_count: 1 }]

export function cuttingFixture() {
  return {
    location_id: 'loc-1', roll_query: null, limit: 100, offset: 0, roll_total: 1,
    orders: [{ id: 'po-1', po_number: 'PO-1', model_id: 'model-1', model_code: 'M', model_name: 'Model', status: 'CUTTING', current_stage: 'CUTTING', contractor_id: null, contractor_name: null }],
    sizes: [{ id: 'size-s', code: 'S', sort_order: 1, model_ids: ['model-1'] }],
    locations: [{ id: 'loc-1', code: 'RM', name: 'Bahan' }], contractors: [{ id: 'mandor-1', code: 'M1', name: 'Mandor' }],
    drafts: [{ cutting_group_id: 'group-1', group_number: 'CUT-1', row_version: 1, po_id: 'po-1', po_number: 'PO-1',
      model_code: 'M', model_name: 'Model', cut_at: '2026-09-20T00:00:00Z', source_location_id: 'loc-1', notes: null as string | null,
      pattern_id: 'pattern-1', pattern_code: 'REG', pattern_revision: 'R1', pattern_name: 'Regular', pattern_is_active: true, editable: true,
      size_slots: [{ slot_no: 1, size_id: 'size-s', size_code: 'S', drawing_no: 1, label_override: null }],
      rolls: [{ roll_id: 'roll-1', roll_number: 'R-1', material_id: 'material-1', material_sku: 'FAB', material_name: 'Fabric',
        unit_code: 'yd', supplier_id: null, supplier_name: null, original_qty: 20, qty_issued: 20, qty_consumed: 18,
        qty_reported_remaining: 2, yields: [{ slot_no: 1, qty_pcs: 9 }] }],
    }],
    rolls: [{ id: 'roll-1', roll_number: 'R-1', material_id: 'material-1', material_sku: 'FAB', material_name: 'Fabric', unit_code: 'yd',
      supplier_id: null, supplier_code: null, supplier_name: null, original_qty: 20, available_qty: 20, status: 'AVAILABLE', received_at: null }],
  }
}
export function cuttingSelectorFixture(args: Record<string, unknown> = {}) {
  const base = cuttingFixture()
  const drafts = base.drafts.map(draft => ({ ...draft, model_id: 'model-1' }))
  return { ...base, drafts, contract_version: 2,
    location_id: (args.p_location_id as string | null) ?? null,
    order_page: { query: (args.p_order_query as string | null) ?? null, limit: 50, offset: 0, total: 1 },
    draft_page: { query: (args.p_draft_query as string | null) ?? null, limit: 25, offset: 0, total: 1 },
    selected_order_id: (args.p_selected_order_id as string | null) ?? null,
    selected_order: args.p_selected_order_id === 'po-1' ? base.orders[0] : null,
    selected_draft_id: (args.p_selected_draft_id as string | null) ?? null,
    selected_draft: args.p_selected_draft_id === 'group-1' ? drafts[0] : null,
  }
}
export function pickupFixture() {
  return { filter: 'WAITING', pattern_id: null, query: null, limit: 100, offset: 0, total: 1,
    contractors: [{ id: 'mandor-1', code: 'M1', name: 'Mandor' }], rows: [{
      cutting_group_id: 'group-1', group_number: 'CUT-1', row_version: 2, po_id: 'po-1', po_number: 'PO-1', model_code: 'M', model_name: 'Model',
      assigned_contractor_id: 'mandor-1', assigned_contractor_name: 'Mandor', cut_at: '2026-09-20T00:00:00Z', status: 'CUT', picked_up_at: null,
      executor_name: null, source_location_id: 'loc-1', source_location_code: 'RM', pickup_eligible: true,
      pattern_id: 'pattern-1', pattern_code: 'REG', pattern_revision: 'R1', pattern_name: 'Regular', total_qty_issued: 20, total_pieces: 9, pickup: null,
      rolls: [{ cutting_group_roll_id: 'group-roll-1', roll_id: 'roll-1', roll_number: 'R-1', material_id: 'material-1', material_sku: 'FAB', material_name: 'Fabric',
        unit_code: 'yd', supplier_name: null, original_qty: 20, qty_issued: 20, qty_consumed: 18, qty_reported_remaining: 2,
        yields: [{ yield_id: 'yield-s', size_slot_id: 'slot-s', slot_no: 1, size_id: 'size-s', size_code: 'S', drawing_no: 1, label: null, qty_pcs: 9 }],
      }],
    }] }
}
export function cuttingCommit(action: string) {
  if (action === 'DELETE') return { cutting_group_id: 'group-1', status: 'DELETED' }
  return { cutting_group_id: 'group-1', group_number: 'CUT-1', status: 'CUT', row_version: 2,
    pattern_id: 'pattern-1', pattern_code: 'REG', pattern_revision: 'R1', pattern_name: 'Regular', source_location_id: 'loc-1',
    material_issue_posted: action === 'POST', total_rolls: 1, total_qty_issued: 20, total_qty_consumed: 18, total_qty_reported_remaining: 2, total_pieces: 9 }
}
export function pickupCommit(action: string) {
  return { pickup_id: 'pickup-1', cutting_group_id: 'group-1', status: action === 'POST' ? 'POSTED' : action === 'DELETE' ? 'DELETED' : 'DRAFT',
    row_version: 1, group_row_version: 3, picked_up_at: '2026-09-20T01:00:00Z', contractor_id: 'mandor-1', allocation_mode: 'ROLL', batch_count: 1, allocated_pieces: 9 }
}

export function wipFixture() {
  return { filter: 'ACTIVE', sort: 'PATTERN', pattern_id: null, rows: [{
    cutting_group_id: 'group-1', po_number: 'PO-1', group_number: 'CUT-1', model_code: 'M', model_name: 'Model',
    executor_name: null, pattern_id: null, pattern_code: null, pattern_revision: null, pattern_name: null,
    pattern_sort_order: null, pattern_is_active: null, effective_qty_pcs: 10, sewn_qty_pcs: 0,
    unfinished_sewing_qty_pcs: 10, unsent_ready_qty_pcs: 0, laundry_draft_qty_pcs: 0,
    laundry_in_transit_qty_pcs: 0, unresolved_laundry_issue_qty_pcs: 0,
    pending_final_sku_handoff_qty_pcs: 0, remaining_final_sku_qty_pcs: 10,
    open_bs_count: 0, open_rework_count: 0, open_flag_count: 0, open_flags: [],
    distribution: null, control_status: 'ACTIVE', updated_at: '2026-09-21T12:00:00Z', row_version: 1,
  }], opening_rows: [] }
}

