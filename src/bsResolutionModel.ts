export type BsWorkspaceFilter = 'ACTIVE' | 'CLOSED' | 'ALL'
export type BsWorkspaceKind = 'BS' | 'LAUNDRY_CLAIM' | 'ALL'
export type BsResolutionAction =
  | 'CREATE_MANUAL_BS' | 'CLASSIFY_BS' | 'SAVE_REWORK' | 'COMPLETE_REWORK'
  | 'DISPOSE_BS' | 'HOLD_BS' | 'RELEASE_HOLD' | 'REVERSE_DISPOSITION'
  | 'REVERSE_REWORK_COMPLETION' | 'SAVE_CLAIM' | 'RESOLVE_CLAIM'
  | 'REVERSE_CLAIM_RESOLUTION'

export type BsPattern = { id: string; code: string; revision: string; name: string }
export type BsLookup = { id: string; code: string; name: string }
export type BsProductLookup = { id: string; sku: string; name: string }
export type LaundrySourceLookup = {
  id: string; number: string; vendor_id: string; vendor_name: string
  po_number: string; physical_at: string; qty_sent_pcs: number
  qty_claimable_pcs: number
}
export type LaundryReceiptSourceLookup = {
  id: string; receipt_id: string; number: string; delivery_id: string
  delivery_number: string; vendor_id: string; vendor_name: string
  po_number: string; physical_at: string; qty_bs_laundry: number
  qty_claimable_pcs: number
}
export type SettledClaimLookup = {
  id: string; number: string; vendor_id: string; vendor_name: string
  delivery_id: string; receipt_line_id: string | null; qty_claimed: number
  compensation_amount: number; available_qty: number; available_amount: number
}
export type BsCaseComponent = {
  id: string; work_component_id: string; code: string; name: string; category: string
  completed_before_bs_qty: number; lifetime_newly_completed_qty: number
  lifetime_paid_qty: number; remaining_new_work_qty_pcs: number
  default_selected: boolean; default_selection_basis: 'UNPAID_COMPONENT_ENTITLEMENT'
  notes: string | null
}
export type BsResolution = {
  id: string; bs_case_id?: string | null; resolution_type: string; qty_pcs: number
  compensation_amount: number; responsible_contractor_id?: string | null
  responsible_vendor_id?: string | null; source_rework_order_id?: string | null
  source_laundry_claim_id?: string | null; physical_at: string
  notes: string | null; created_at: string
}
export type ReworkComponent = {
  id: string; bs_case_component_id: string; work_component_id: string
  component_code: string; component_name: string; qty_performed: number
  qty_newly_payable: number; rate_snapshot: number; amount_payable: number
  rate_basis: string; notes: string | null
}
export type ReworkAccessoryItem = {
  id: string; bom_item_id: string; category_id: string; code: string; name: string
  qty_per_good_fg_base: number; reimbursement_unit_rate_base: number
  selection_basis: 'UNPAID_BASELINE' | 'MANUAL_REPLACEMENT'
}
export type ReworkAccessoryDecision = {
  state: 'SELECTED' | 'NONE' | 'UNAVAILABLE'; bom_version_id: string | null
  reimbursement_contractor_id: string | null; selected_item_count: number
  selection_sha256: string; basis_at: string; selected_items: ReworkAccessoryItem[]
}
export type BsAccessoryBomItem = {
  id: string; category_id: string; code: string; name: string; base_uom_code: string
  qty_per_good_fg_base: number; reimbursement_rate: number; reimbursement_uom_code: string
  default_selected: boolean; default_selection_basis: 'UNPAID_BASELINE' | 'MANUAL_REPLACEMENT'
  default_reason: 'NO_AVAILABLE_QUANTITY' | 'PRE_FG_UNPAID_BASELINE'
    | 'POST_FG_OR_UNPROVEN_BASELINE' | 'BASELINE_ENTITLEMENT_EXHAUSTED'
  already_entitled_good_qty_pcs: number
  already_cash_settled_good_qty_pcs: number
  remaining_unentitled_good_qty_pcs: number
}
export type BsAccessoryBom = {
  state: 'AVAILABLE' | 'NONE' | 'UNAVAILABLE'; bom_version_id: string | null
  default_policy: 'SERVER_ENTITLEMENT_V2619B'; available_qty_pcs: number; items: BsAccessoryBomItem[]
}
export type ReworkOrder = {
  id: string; rework_number: string; destination_type: 'CONTRACTOR' | 'LAUNDRY'
  contractor_id: string | null; contractor_name: string | null
  vendor_id: string | null; vendor_name: string | null; qty_sent: number
  qty_good_returned: number; qty_bs_returned: number; physical_sent_at: string
  completed_at: string | null; status: 'OPEN' | 'IN_PROGRESS' | 'PARTIAL' | 'COMPLETED' | 'CANCELLED'
  cost_posted: boolean; return_fg_location_id: string | null
  return_fg_location_name: string | null; good_fg_lot_id: string | null
  row_version: number; notes: string | null; components: ReworkComponent[]
  accessory_decision: ReworkAccessoryDecision
}
export type BsHoldEvent = {
  id: string; action: 'HOLD' | 'RELEASE'; previous_status: string
  resulting_status: string; reason: string; physical_at: string
  actor_id: string | null; actor_name: string | null; created_at: string
}
export type BsResolutionRow = {
  case_key: string; kind: 'BS' | 'LAUNDRY_CLAIM'; id: string; number: string
  status: string; row_version: number; qty_pcs: number; resolved_qty: number
  active_rework_qty: number; available_qty: number; opened_at: string
  po_id: string | null; po_number: string | null; model_name: string | null
  cutting_group_id: string | null; group_number: string | null
  patterns: BsPattern[]; product_id: string | null; sku: string | null
  product_name: string | null; responsible_contractor_id: string | null
  contractor_name: string | null; responsible_vendor_id: string | null
  vendor_name: string | null; detected_stage: string; cause_source: string
  untracked_type: string | null; claim_type: string | null
  compensation_amount: number; laundry_delivery_id: string | null
  laundry_receipt_line_id: string | null; legacy_reference: string | null
  notes: string | null; next_action: string; is_closed: boolean
  components: BsCaseComponent[]; resolutions: BsResolution[]
  rework_orders: ReworkOrder[]; hold_events: BsHoldEvent[]
  accessory_bom: BsAccessoryBom | null
}
export type BsResolutionWorkspace = {
  filter: BsWorkspaceFilter; kind: BsWorkspaceKind; pattern_id: string | null
  query: string | null; limit: number; offset: number; total: number
  lookups: {
    contractors: BsLookup[]; vendors: BsLookup[]; fg_locations: BsLookup[]
    work_components: BsLookup[]; products: BsProductLookup[]
    laundry_sources: LaundrySourceLookup[]
    laundry_receipt_sources: LaundryReceiptSourceLookup[]
    settled_claims: SettledClaimLookup[]
  }
  rows: BsResolutionRow[]
}

const record = (value: unknown, label: string) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} tidak valid.`)
  return value as Record<string, unknown>
}
const text = (value: unknown, label: string) => {
  if (typeof value !== 'string' || value.trim() === '') throw new Error(`${label} tidak valid.`)
  return value
}
const nullableText = (value: unknown) => typeof value === 'string' ? value : null
const number = (value: unknown, label: string, minimum = 0) => {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < minimum) throw new Error(`${label} tidak valid.`)
  return parsed
}
const integer = (value: unknown, label: string, minimum = 0) => {
  const parsed = number(value, label, minimum)
  if (!Number.isSafeInteger(parsed)) throw new Error(`${label} tidak valid.`)
  return parsed
}
const boolean = (value: unknown, label: string) => {
  if (typeof value !== 'boolean') throw new Error(`${label} tidak valid.`)
  return value
}
const exactText = <T extends string>(value: unknown, allowed: readonly T[], label: string): T => {
  const parsed = text(value, label)
  if (!allowed.includes(parsed as T)) throw new Error(`${label} tidak valid.`)
  return parsed as T
}
const list = (value: unknown, label: string) => {
  if (!Array.isArray(value)) throw new Error(`${label} tidak valid.`)
  return value
}

function parseLookup(value: unknown, label: string): BsLookup {
  const raw = record(value, label)
  return { id: text(raw.id, `${label} ID`), code: text(raw.code, `${label} kode`), name: text(raw.name, `${label} nama`) }
}
function parsePattern(value: unknown): BsPattern {
  const raw = record(value, 'Pola kasus')
  return { id: text(raw.id, 'ID Pola'), code: text(raw.code, 'Kode Pola'), revision: text(raw.revision, 'Revisi Pola'), name: text(raw.name, 'Nama Pola') }
}
function parseComponent(value: unknown): BsCaseComponent {
  const raw = record(value, 'Komponen BS')
  const remaining = integer(raw.remaining_new_work_qty_pcs, 'Sisa komponen belum jadi entitlement')
  const defaultSelected = boolean(raw.default_selected, 'Default komponen')
  if (defaultSelected !== (remaining > 0)) throw new Error('Default komponen tidak konsisten dengan sisa entitlement.')
  return {
    id: text(raw.id, 'ID komponen BS'), work_component_id: text(raw.work_component_id, 'ID jenis kerja'),
    code: text(raw.code, 'Kode komponen'), name: text(raw.name, 'Nama komponen'), category: text(raw.category, 'Kategori komponen'),
    completed_before_bs_qty: integer(raw.completed_before_bs_qty, 'Qty komponen sebelum BS'),
    lifetime_newly_completed_qty: integer(raw.lifetime_newly_completed_qty, 'Qty komponen rework'),
    lifetime_paid_qty: integer(raw.lifetime_paid_qty, 'Qty komponen dibayar'),
    remaining_new_work_qty_pcs: remaining,
    default_selected: defaultSelected,
    default_selection_basis: exactText(
      raw.default_selection_basis, ['UNPAID_COMPONENT_ENTITLEMENT'] as const, 'Dasar default komponen',
    ),
    notes: nullableText(raw.notes),
  }
}
function parseResolution(value: unknown): BsResolution {
  const raw = record(value, 'Resolusi BS')
  return {
    id: text(raw.id, 'ID resolusi'), bs_case_id: nullableText(raw.bs_case_id),
    resolution_type: text(raw.resolution_type, 'Jenis resolusi'), qty_pcs: integer(raw.qty_pcs, 'Qty resolusi', 1),
    compensation_amount: number(raw.compensation_amount, 'Nilai kompensasi'),
    responsible_contractor_id: nullableText(raw.responsible_contractor_id),
    responsible_vendor_id: nullableText(raw.responsible_vendor_id),
    source_rework_order_id: nullableText(raw.source_rework_order_id),
    source_laundry_claim_id: nullableText(raw.source_laundry_claim_id),
    physical_at: text(raw.physical_at, 'Waktu fisik resolusi'), notes: nullableText(raw.notes),
    created_at: text(raw.created_at, 'Waktu pencatatan resolusi'),
  }
}
function parseReworkComponent(value: unknown): ReworkComponent {
  const raw = record(value, 'Komponen rework')
  return {
    id: text(raw.id, 'ID komponen rework'), bs_case_component_id: text(raw.bs_case_component_id, 'ID komponen kasus'),
    work_component_id: text(raw.work_component_id, 'ID jenis kerja'), component_code: text(raw.component_code, 'Kode komponen rework'),
    component_name: text(raw.component_name, 'Nama komponen rework'), qty_performed: integer(raw.qty_performed, 'Qty dikerjakan', 1),
    qty_newly_payable: integer(raw.qty_newly_payable, 'Qty baru dibayar'), rate_snapshot: number(raw.rate_snapshot, 'Rate snapshot'),
    amount_payable: number(raw.amount_payable, 'Nilai dibayar'), rate_basis: text(raw.rate_basis, 'Dasar rate'), notes: nullableText(raw.notes),
  }
}
function parseReworkAccessoryItem(value: unknown): ReworkAccessoryItem {
  const raw = record(value, 'Aksesori terpilih')
  return {
    id: text(raw.id, 'ID pilihan aksesori'), bom_item_id: text(raw.bom_item_id, 'ID item BOM aksesori'),
    category_id: text(raw.category_id, 'ID kategori aksesori'), code: text(raw.code, 'Kode aksesori'),
    name: text(raw.name, 'Nama aksesori'),
    qty_per_good_fg_base: number(raw.qty_per_good_fg_base, 'Qty aksesori per Good', Number.EPSILON),
    reimbursement_unit_rate_base: number(raw.reimbursement_unit_rate_base, 'Rate reimbursement aksesori'),
    selection_basis: exactText(
      raw.selection_basis, ['UNPAID_BASELINE', 'MANUAL_REPLACEMENT'] as const, 'Dasar pilihan aksesori',
    ),
  }
}
function parseReworkAccessoryDecision(value: unknown): ReworkAccessoryDecision {
  const raw = record(value, 'Keputusan aksesori rework')
  const state = text(raw.state, 'Status keputusan aksesori')
  if (!['SELECTED', 'NONE', 'UNAVAILABLE'].includes(state)) throw new Error('Status keputusan aksesori tidak valid.')
  const selectedItems = list(raw.selected_items, 'Aksesori rework terpilih').map(parseReworkAccessoryItem)
  const selectedItemCount = integer(raw.selected_item_count, 'Jumlah aksesori terpilih')
  if (selectedItemCount !== selectedItems.length) throw new Error('Jumlah keputusan aksesori tidak konsisten.')
  if ((state === 'SELECTED') !== (selectedItemCount > 0)) throw new Error('Status dan isi keputusan aksesori tidak konsisten.')
  if ((state === 'UNAVAILABLE') !== (raw.bom_version_id == null)) throw new Error('Lineage BOM keputusan aksesori tidak konsisten.')
  const selectionSha = text(raw.selection_sha256, 'Hash keputusan aksesori')
  if (!/^[0-9a-f]{64}$/.test(selectionSha)) throw new Error('Hash keputusan aksesori tidak valid.')
  return {
    state: state as ReworkAccessoryDecision['state'], bom_version_id: nullableText(raw.bom_version_id),
    reimbursement_contractor_id: nullableText(raw.reimbursement_contractor_id),
    selected_item_count: selectedItemCount, selection_sha256: selectionSha,
    basis_at: text(raw.basis_at, 'Waktu dasar keputusan aksesori'), selected_items: selectedItems,
  }
}
function parseAccessoryBom(value: unknown): BsAccessoryBom | null {
  if (value == null) return null
  const raw = record(value, 'BOM aksesori kasus')
  const state = text(raw.state, 'Status BOM aksesori')
  if (!['AVAILABLE', 'NONE', 'UNAVAILABLE'].includes(state)) throw new Error('Status BOM aksesori tidak valid.')
  const items = list(raw.items, 'Item BOM aksesori').map((item) => {
    const itemRaw = record(item, 'Item BOM aksesori')
    const defaultSelected = boolean(itemRaw.default_selected, 'Default pilihan aksesori')
    const defaultBasis = exactText(
      itemRaw.default_selection_basis, ['UNPAID_BASELINE', 'MANUAL_REPLACEMENT'] as const,
      'Dasar default aksesori',
    )
    const defaultReason = exactText(
      itemRaw.default_reason,
      [
        'NO_AVAILABLE_QUANTITY', 'PRE_FG_UNPAID_BASELINE',
        'POST_FG_OR_UNPROVEN_BASELINE', 'BASELINE_ENTITLEMENT_EXHAUSTED',
      ] as const,
      'Alasan default aksesori',
    )
    if (defaultSelected !== (defaultReason === 'PRE_FG_UNPAID_BASELINE')
        || (defaultSelected && defaultBasis !== 'UNPAID_BASELINE')
        || (defaultBasis === 'MANUAL_REPLACEMENT' && defaultSelected)) {
      throw new Error('Default aksesori tidak konsisten dengan basis entitlement.')
    }
    return {
      id: text(itemRaw.id, 'ID item BOM aksesori'), category_id: text(itemRaw.category_id, 'ID kategori aksesori'),
      code: text(itemRaw.code, 'Kode aksesori'), name: text(itemRaw.name, 'Nama aksesori'),
      base_uom_code: text(itemRaw.base_uom_code, 'Satuan dasar aksesori'),
      qty_per_good_fg_base: number(itemRaw.qty_per_good_fg_base, 'Qty aksesori per Good', Number.EPSILON),
      reimbursement_rate: number(itemRaw.reimbursement_rate, 'Rate reimbursement aksesori'),
      reimbursement_uom_code: text(itemRaw.reimbursement_uom_code, 'Satuan reimbursement aksesori'),
      default_selected: defaultSelected,
      default_selection_basis: defaultBasis,
      default_reason: defaultReason,
      already_entitled_good_qty_pcs: integer(itemRaw.already_entitled_good_qty_pcs, 'Good yang sudah menjadi entitlement'),
      already_cash_settled_good_qty_pcs: integer(itemRaw.already_cash_settled_good_qty_pcs, 'Good yang sudah dibayar tunai'),
      remaining_unentitled_good_qty_pcs: integer(
        itemRaw.remaining_unentitled_good_qty_pcs, 'Sisa Good yang belum menjadi entitlement',
      ),
    }
  })
  if ((state === 'AVAILABLE') !== (items.length > 0)) throw new Error('Status dan isi BOM aksesori tidak konsisten.')
  if ((state === 'UNAVAILABLE') !== (raw.bom_version_id == null)) throw new Error('Lineage versi BOM aksesori tidak konsisten.')
  return {
    state: state as BsAccessoryBom['state'], bom_version_id: nullableText(raw.bom_version_id),
    default_policy: exactText(
      raw.default_policy, ['SERVER_ENTITLEMENT_V2619B'] as const, 'Kebijakan default aksesori',
    ),
    available_qty_pcs: integer(raw.available_qty_pcs, 'Qty tersedia untuk keputusan aksesori'), items,
  }
}
function parseRework(value: unknown): ReworkOrder {
  const raw = record(value, 'Order rework')
  const destination = text(raw.destination_type, 'Tujuan rework')
  const status = text(raw.status, 'Status rework')
  if (!['CONTRACTOR', 'LAUNDRY'].includes(destination)) throw new Error('Tujuan rework tidak valid.')
  if (!['OPEN', 'IN_PROGRESS', 'PARTIAL', 'COMPLETED', 'CANCELLED'].includes(status)) throw new Error('Status rework tidak valid.')
  if (typeof raw.cost_posted !== 'boolean') throw new Error('Status posting biaya rework tidak valid.')
  return {
    id: text(raw.id, 'ID rework'), rework_number: text(raw.rework_number, 'Nomor rework'),
    destination_type: destination as ReworkOrder['destination_type'], contractor_id: nullableText(raw.contractor_id),
    contractor_name: nullableText(raw.contractor_name), vendor_id: nullableText(raw.vendor_id), vendor_name: nullableText(raw.vendor_name),
    qty_sent: integer(raw.qty_sent, 'Qty dikirim rework', 1), qty_good_returned: integer(raw.qty_good_returned, 'Good rework'),
    qty_bs_returned: integer(raw.qty_bs_returned, 'BS rework'), physical_sent_at: text(raw.physical_sent_at, 'Waktu kirim rework'),
    completed_at: nullableText(raw.completed_at), status: status as ReworkOrder['status'], cost_posted: raw.cost_posted,
    return_fg_location_id: nullableText(raw.return_fg_location_id), return_fg_location_name: nullableText(raw.return_fg_location_name),
    good_fg_lot_id: nullableText(raw.good_fg_lot_id), row_version: integer(raw.row_version, 'Versi rework', 1),
    notes: nullableText(raw.notes), components: list(raw.components, 'Daftar komponen rework').map(parseReworkComponent),
    accessory_decision: parseReworkAccessoryDecision(raw.accessory_decision),
  }
}
function parseHold(value: unknown): BsHoldEvent {
  const raw = record(value, 'Riwayat HOLD')
  const action = text(raw.action, 'Aksi HOLD')
  if (!['HOLD', 'RELEASE'].includes(action)) throw new Error('Aksi HOLD tidak valid.')
  return {
    id: text(raw.id, 'ID riwayat HOLD'), action: action as BsHoldEvent['action'],
    previous_status: text(raw.previous_status, 'Status sebelum HOLD'), resulting_status: text(raw.resulting_status, 'Status sesudah HOLD'),
    reason: text(raw.reason, 'Alasan HOLD'), physical_at: text(raw.physical_at, 'Waktu fisik HOLD'),
    actor_id: nullableText(raw.actor_id), actor_name: nullableText(raw.actor_name), created_at: text(raw.created_at, 'Waktu pencatatan HOLD'),
  }
}
function parseRow(value: unknown): BsResolutionRow {
  const raw = record(value, 'Baris CP5')
  const kind = text(raw.kind, 'Jenis kasus')
  if (!['BS', 'LAUNDRY_CLAIM'].includes(kind)) throw new Error('Jenis kasus CP5 tidak valid.')
  if (typeof raw.is_closed !== 'boolean') throw new Error('Status tutup CP5 tidak valid.')
  const caseQty = integer(raw.qty_pcs, 'Qty kasus', 1)
  const detectedStage = text(raw.detected_stage, 'Tahap deteksi')
  const availableQty = integer(raw.available_qty, 'Qty tersedia')
  const accessoryBom = parseAccessoryBom(raw.accessory_bom)
  if (kind === 'BS' && accessoryBom?.available_qty_pcs !== availableQty) {
    throw new Error('Qty tersedia BOM aksesori tidak konsisten dengan kasus.')
  }
  if (kind === 'BS' && accessoryBom) {
    const preFgTracked = raw.po_id != null && raw.product_id != null && raw.untracked_type == null
      && ['SEWING', 'LAUNDRY', 'QC'].includes(detectedStage)
    for (const item of accessoryBom.items) {
      if (item.already_cash_settled_good_qty_pcs > item.already_entitled_good_qty_pcs) {
        throw new Error('Pembayaran aksesori melebihi entitlement authoritative.')
      }
      const expectedRemaining = preFgTracked
        ? Math.min(availableQty, Math.max(caseQty - item.already_entitled_good_qty_pcs, 0))
        : 0
      const expectedReason = availableQty <= 0
        ? 'NO_AVAILABLE_QUANTITY'
        : !preFgTracked
          ? 'POST_FG_OR_UNPROVEN_BASELINE'
          : expectedRemaining <= 0
            ? 'BASELINE_ENTITLEMENT_EXHAUSTED'
            : 'PRE_FG_UNPAID_BASELINE'
      if (item.remaining_unentitled_good_qty_pcs !== expectedRemaining
          || item.default_selected !== (expectedRemaining > 0)
          || item.default_reason !== expectedReason
          || item.default_selection_basis !== (expectedRemaining > 0 ? 'UNPAID_BASELINE' : 'MANUAL_REPLACEMENT')) {
        throw new Error('Default aksesori tidak cocok dengan entitlement authoritative kasus.')
      }
    }
  }
  if (kind === 'LAUNDRY_CLAIM' && accessoryBom !== null) {
    throw new Error('Claim Laundry tidak boleh membawa default BOM aksesori.')
  }
  return {
    case_key: text(raw.case_key, 'Kunci kasus'), kind: kind as BsResolutionRow['kind'], id: text(raw.id, 'ID kasus'),
    number: text(raw.number, 'Nomor kasus'), status: text(raw.status, 'Status kasus'), row_version: integer(raw.row_version, 'Versi kasus', 1),
    qty_pcs: caseQty, resolved_qty: integer(raw.resolved_qty, 'Qty resolved'),
    active_rework_qty: integer(raw.active_rework_qty, 'Qty rework aktif'), available_qty: availableQty,
    opened_at: text(raw.opened_at, 'Waktu kasus'), po_id: nullableText(raw.po_id), po_number: nullableText(raw.po_number),
    model_name: nullableText(raw.model_name), cutting_group_id: nullableText(raw.cutting_group_id), group_number: nullableText(raw.group_number),
    patterns: list(raw.patterns, 'Daftar Pola kasus').map(parsePattern), product_id: nullableText(raw.product_id), sku: nullableText(raw.sku),
    product_name: nullableText(raw.product_name), responsible_contractor_id: nullableText(raw.responsible_contractor_id),
    contractor_name: nullableText(raw.contractor_name), responsible_vendor_id: nullableText(raw.responsible_vendor_id), vendor_name: nullableText(raw.vendor_name),
    detected_stage: detectedStage, cause_source: text(raw.cause_source, 'Sumber penyebab'),
    untracked_type: nullableText(raw.untracked_type), claim_type: nullableText(raw.claim_type), compensation_amount: number(raw.compensation_amount, 'Kompensasi'),
    laundry_delivery_id: nullableText(raw.laundry_delivery_id), laundry_receipt_line_id: nullableText(raw.laundry_receipt_line_id),
    legacy_reference: nullableText(raw.legacy_reference), notes: nullableText(raw.notes), next_action: text(raw.next_action, 'Aksi berikutnya'),
    is_closed: raw.is_closed, components: list(raw.components, 'Daftar komponen BS').map(parseComponent),
    resolutions: list(raw.resolutions, 'Daftar resolusi').map(parseResolution), rework_orders: list(raw.rework_orders, 'Daftar rework').map(parseRework),
    hold_events: list(raw.hold_events, 'Daftar riwayat HOLD').map(parseHold),
    accessory_bom: accessoryBom,
  }
}

export function parseBsResolutionWorkspace(value: unknown): BsResolutionWorkspace {
  const raw = record(value, 'Respons CP5')
  const filter = text(raw.filter, 'Filter CP5')
  const kind = text(raw.kind, 'Jenis filter CP5')
  if (!['ACTIVE', 'CLOSED', 'ALL'].includes(filter)) throw new Error('Filter CP5 tidak valid.')
  if (!['BS', 'LAUNDRY_CLAIM', 'ALL'].includes(kind)) throw new Error('Jenis filter CP5 tidak valid.')
  const lookups = record(raw.lookups, 'Lookup CP5')
  return {
    filter: filter as BsWorkspaceFilter, kind: kind as BsWorkspaceKind,
    pattern_id: nullableText(raw.pattern_id), query: nullableText(raw.query),
    limit: integer(raw.limit, 'Limit CP5', 1), offset: integer(raw.offset, 'Offset CP5'), total: integer(raw.total, 'Total CP5'),
    lookups: {
      contractors: list(lookups.contractors, 'Lookup Mandor').map((item) => parseLookup(item, 'Mandor')),
      vendors: list(lookups.vendors, 'Lookup Laundry').map((item) => parseLookup(item, 'Laundry')),
      fg_locations: list(lookups.fg_locations, 'Lookup Gudang FG').map((item) => parseLookup(item, 'Gudang FG')),
      work_components: list(lookups.work_components, 'Lookup komponen kerja').map((item) => parseLookup(item, 'Komponen kerja')),
      products: list(lookups.products, 'Lookup produk').map((item) => { const itemRaw = record(item, 'Produk'); return { id: text(itemRaw.id, 'ID produk'), sku: text(itemRaw.sku, 'SKU'), name: text(itemRaw.name, 'Nama produk') } }),
      laundry_sources: list(lookups.laundry_sources, 'Lookup sumber Laundry').map((item) => { const itemRaw = record(item, 'Sumber Laundry'); return {
        id: text(itemRaw.id, 'ID sumber Laundry'), number: text(itemRaw.number, 'Nomor sumber Laundry'), vendor_id: text(itemRaw.vendor_id, 'Vendor sumber Laundry'),
        vendor_name: text(itemRaw.vendor_name, 'Nama vendor sumber Laundry'), po_number: text(itemRaw.po_number, 'PO sumber Laundry'),
        physical_at: text(itemRaw.physical_at, 'Waktu sumber Laundry'), qty_sent_pcs: integer(itemRaw.qty_sent_pcs, 'Qty sumber Laundry', 1),
        qty_claimable_pcs: integer(itemRaw.qty_claimable_pcs, 'Sisa claim sumber Laundry'),
      } }),
      laundry_receipt_sources: list(lookups.laundry_receipt_sources, 'Lookup penerimaan Laundry').map((item) => { const itemRaw = record(item, 'Penerimaan Laundry'); return {
        id: text(itemRaw.id, 'ID baris penerimaan Laundry'), receipt_id: text(itemRaw.receipt_id, 'ID penerimaan Laundry'),
        number: text(itemRaw.number, 'Nomor penerimaan Laundry'), delivery_id: text(itemRaw.delivery_id, 'ID kiriman Laundry'),
        delivery_number: text(itemRaw.delivery_number, 'Nomor kiriman Laundry'), vendor_id: text(itemRaw.vendor_id, 'Vendor penerimaan Laundry'),
        vendor_name: text(itemRaw.vendor_name, 'Nama vendor penerimaan Laundry'), po_number: text(itemRaw.po_number, 'PO penerimaan Laundry'),
        physical_at: text(itemRaw.physical_at, 'Waktu penerimaan Laundry'), qty_bs_laundry: integer(itemRaw.qty_bs_laundry, 'Qty BS penerimaan Laundry', 1),
        qty_claimable_pcs: integer(itemRaw.qty_claimable_pcs, 'Sisa claim kerusakan', 1),
      } }),
      settled_claims: list(lookups.settled_claims, 'Lookup claim settled').map((item) => { const itemRaw = record(item, 'Claim settled'); return {
        id: text(itemRaw.id, 'ID claim settled'), number: text(itemRaw.number, 'Nomor claim settled'),
        vendor_id: text(itemRaw.vendor_id, 'Vendor claim settled'), vendor_name: text(itemRaw.vendor_name, 'Nama vendor claim settled'),
        delivery_id: text(itemRaw.delivery_id, 'Kiriman claim settled'), receipt_line_id: nullableText(itemRaw.receipt_line_id),
        qty_claimed: integer(itemRaw.qty_claimed, 'Qty claim settled', 1), compensation_amount: number(itemRaw.compensation_amount, 'Nilai claim settled'),
        available_qty: integer(itemRaw.available_qty, 'Sisa qty claim settled', 1), available_amount: number(itemRaw.available_amount, 'Sisa nilai claim settled', Number.EPSILON),
      } }),
    },
    rows: list(raw.rows, 'Daftar kasus CP5').map(parseRow),
  }
}

export const cleanBsQuantity = (raw: string, max: number) => {
  const normalized = raw.trim().replace(',', '.')
  if (!normalized) return ''
  const parsed = Number(normalized)
  if (!Number.isFinite(parsed)) return ''
  return String(Math.min(Math.max(0, Math.floor(max)), Math.max(0, Math.floor(parsed))))
}

export const exactReworkCompletion = (qtyGood: number, qtyBs: number, qtySent: number) =>
  Number.isSafeInteger(qtyGood) && Number.isSafeInteger(qtyBs) && Number.isSafeInteger(qtySent)
  && qtyGood >= 0 && qtyBs >= 0 && qtySent > 0 && qtyGood + qtyBs === qtySent

export const bsPatternLabel = (row: Pick<BsResolutionRow, 'patterns'>) => row.patterns.length > 0
  ? row.patterns.map((pattern) => `${pattern.code} · ${pattern.revision} · ${pattern.name}`).join(' / ')
  : 'Histori lama · Pola belum tercatat'
