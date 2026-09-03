export type CuttingOrder = {
  id: string
  po_number: string
  model_id: string
  model_code: string
  model_name: string
  status: string
  current_stage: string
  contractor_id: string | null
  contractor_name: string | null
}

export type CuttingSize = { id: string; code: string; sort_order: number; model_ids: string[] }
export type CuttingLocation = { id: string; code: string; name: string }
export type CuttingContractor = { id: string; code: string; name: string }

export type CuttingRollYield = { slot_no: number; qty_pcs: number }
export type CuttingWorkspaceRoll = {
  id: string
  roll_number: string
  material_id: string
  material_sku: string
  material_name: string
  unit_code: string
  supplier_id: string | null
  supplier_code: string | null
  supplier_name: string | null
  original_qty: number
  available_qty: number
  status: string
  received_at: string | null
}

export type CuttingDraftRoll = Omit<CuttingWorkspaceRoll, 'id' | 'available_qty' | 'status' | 'received_at' | 'supplier_code'> & {
  roll_id: string
  qty_issued: number
  qty_consumed: number
  qty_reported_remaining: number
  yields: CuttingRollYield[]
}

export type CuttingDraft = {
  cutting_group_id: string
  group_number: string
  row_version: number
  po_id: string
  po_number: string
  model_code: string
  model_name: string
  cut_at: string
  source_location_id: string | null
  notes: string | null
  pattern_id: string | null
  pattern_code: string | null
  pattern_revision: string | null
  pattern_name: string | null
  pattern_is_active: boolean | null
  editable: boolean
  size_slots: Array<{
    slot_no: number
    size_id: string
    size_code: string
    drawing_no: number
    label_override: string | null
  }>
  rolls: CuttingDraftRoll[]
}

export type CuttingWorkspace = {
  location_id: string | null
  roll_query: string | null
  limit: number
  offset: number
  roll_total: number
  orders: CuttingOrder[]
  sizes: CuttingSize[]
  locations: CuttingLocation[]
  contractors: CuttingContractor[]
  drafts: CuttingDraft[]
  rolls: CuttingWorkspaceRoll[]
}

export type PickupYield = {
  yield_id: string
  size_slot_id: string
  slot_no: number
  size_id: string
  size_code: string
  drawing_no: number
  label: string | null
  qty_pcs: number
}

export type PickupRoll = {
  cutting_group_roll_id: string
  roll_id: string
  roll_number: string
  material_id: string
  material_sku: string
  material_name: string
  unit_code: string
  supplier_name: string | null
  original_qty: number
  qty_issued: number
  qty_consumed: number
  qty_reported_remaining: number
  yields: PickupYield[]
}

export type PickupBatch = {
  id: string
  batch_no: number
  notes: string | null
  qty_pcs: number
  allocations: Array<{ cutting_roll_yield_id: string; qty_pcs: number }>
}

export type PickupDraft = {
  id: string
  contractor_id: string
  contractor_name: string
  picked_up_at: string
  allocation_mode: 'ROLL' | 'SIZE'
  status: 'DRAFT' | 'POSTED'
  notes: string | null
  row_version: number
  batches: PickupBatch[]
}

export type PickupQueueRow = {
  cutting_group_id: string
  group_number: string
  row_version: number
  po_id: string
  po_number: string
  model_code: string
  model_name: string
  cut_at: string
  status: string
  picked_up_at: string | null
  executor_name: string | null
  source_location_id: string | null
  source_location_code: string | null
  pattern_id: string | null
  pattern_code: string | null
  pattern_revision: string | null
  pattern_name: string | null
  total_qty_issued: number
  total_pieces: number
  pickup_eligible: boolean
  pickup: PickupDraft | null
  rolls: PickupRoll[]
}

export type PickupQueue = {
  filter: 'WAITING' | 'PICKED' | 'ALL'
  pattern_id: string | null
  query: string | null
  limit: number
  offset: number
  total: number
  contractors: CuttingContractor[]
  rows: PickupQueueRow[]
}

export type CuttingSaveResult = {
  cutting_group_id: string
  group_number: string
  status: string
  row_version: number
  pattern_id: string
  pattern_code: string
  pattern_revision: string
  pattern_name: string
  source_location_id: string
  material_issue_posted: boolean
  total_rolls: number
  total_qty_issued: number
  total_qty_consumed: number
  total_qty_reported_remaining: number
  total_pieces: number
}

export type PickupSaveResult = {
  pickup_id: string
  cutting_group_id: string
  status: 'DRAFT' | 'POSTED' | 'DELETED'
  row_version: number
  group_row_version: number
  picked_up_at: string
  contractor_id: string
  allocation_mode: 'ROLL' | 'SIZE'
  batch_count: number
  allocated_pieces: number
}

export type PickupAllocationMatrix = Record<string, number[]>

function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} tidak valid.`)
  return value as Record<string, unknown>
}

function list(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${label} tidak valid.`)
  return value
}

function text(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.length === 0) throw new Error(`${label} tidak lengkap.`)
  return value
}

function optionalText(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null
}

function number(value: unknown, label: string): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) throw new Error(`${label} tidak valid.`)
  return parsed
}

function bool(value: unknown, label: string): boolean {
  if (typeof value !== 'boolean') throw new Error(`${label} tidak valid.`)
  return value
}

function parseYield(value: unknown): CuttingRollYield {
  const row = object(value, 'Hasil potong')
  return { slot_no: number(row.slot_no, 'Nomor kolom'), qty_pcs: number(row.qty_pcs, 'Jumlah hasil') }
}

function parseWorkspaceRoll(value: unknown): CuttingWorkspaceRoll {
  const row = object(value, 'Roll')
  return {
    id: text(row.id, 'ID roll'), roll_number: text(row.roll_number, 'Nomor roll'),
    material_id: text(row.material_id, 'ID bahan'), material_sku: text(row.material_sku, 'SKU bahan'),
    material_name: text(row.material_name, 'Nama bahan'), unit_code: text(row.unit_code, 'UOM bahan'),
    supplier_id: optionalText(row.supplier_id), supplier_code: optionalText(row.supplier_code),
    supplier_name: optionalText(row.supplier_name), original_qty: number(row.original_qty, 'Qty asal'),
    available_qty: number(row.available_qty, 'Qty tersedia'), status: text(row.status, 'Status roll'),
    received_at: optionalText(row.received_at),
  }
}

function parseDraft(value: unknown): CuttingDraft {
  const row = object(value, 'Draft Potongan')
  return {
    cutting_group_id: text(row.cutting_group_id, 'ID Potongan'),
    group_number: text(row.group_number, 'Nomor Potongan'), row_version: number(row.row_version, 'Versi Potongan'),
    po_id: text(row.po_id, 'ID PO'), po_number: text(row.po_number, 'Nomor PO'),
    model_code: text(row.model_code, 'Kode model'), model_name: text(row.model_name, 'Nama model'),
    cut_at: text(row.cut_at, 'Waktu potong'), source_location_id: optionalText(row.source_location_id),
    notes: optionalText(row.notes), pattern_id: optionalText(row.pattern_id),
    pattern_code: optionalText(row.pattern_code), pattern_revision: optionalText(row.pattern_revision),
    pattern_name: optionalText(row.pattern_name),
    pattern_is_active: row.pattern_is_active === null ? null : bool(row.pattern_is_active, 'Status Pola'),
    editable: bool(row.editable, 'Status edit'),
    size_slots: list(row.size_slots, 'Kolom ukuran').map((candidate) => {
      const slot = object(candidate, 'Kolom ukuran')
      return {
        slot_no: number(slot.slot_no, 'Nomor kolom'), size_id: text(slot.size_id, 'ID ukuran'),
        size_code: text(slot.size_code, 'Kode ukuran'), drawing_no: number(slot.drawing_no, 'Nomor gambar'),
        label_override: optionalText(slot.label_override),
      }
    }),
    rolls: list(row.rolls, 'Roll draft').map((candidate) => {
      const roll = object(candidate, 'Roll draft')
      return {
        roll_id: text(roll.roll_id, 'ID roll'), roll_number: text(roll.roll_number, 'Nomor roll'),
        material_id: text(roll.material_id, 'ID bahan'), material_sku: text(roll.material_sku, 'SKU bahan'),
        material_name: text(roll.material_name, 'Nama bahan'), unit_code: text(roll.unit_code, 'UOM bahan'),
        supplier_id: optionalText(roll.supplier_id), supplier_name: optionalText(roll.supplier_name),
        original_qty: number(roll.original_qty, 'Qty asal'), qty_issued: number(roll.qty_issued, 'Qty keluar'),
        qty_consumed: number(roll.qty_consumed, 'Qty terpakai'),
        qty_reported_remaining: number(roll.qty_reported_remaining, 'Sisa terlapor'),
        yields: list(roll.yields, 'Hasil roll').map(parseYield),
      }
    }),
  }
}

export function parseCuttingWorkspace(value: unknown): CuttingWorkspace {
  const raw = object(value, 'Respons workspace cutting')
  return {
    location_id: optionalText(raw.location_id), roll_query: optionalText(raw.roll_query),
    limit: number(raw.limit, 'Limit'), offset: number(raw.offset, 'Offset'),
    roll_total: number(raw.roll_total, 'Total roll'),
    orders: list(raw.orders, 'Daftar PO').map((candidate) => {
      const row = object(candidate, 'PO')
      return {
        id: text(row.id, 'ID PO'), po_number: text(row.po_number, 'Nomor PO'),
        model_id: text(row.model_id, 'ID model'), model_code: text(row.model_code, 'Kode model'),
        model_name: text(row.model_name, 'Nama model'), status: text(row.status, 'Status PO'),
        current_stage: text(row.current_stage, 'Tahap PO'), contractor_id: optionalText(row.contractor_id),
        contractor_name: optionalText(row.contractor_name),
      }
    }),
    sizes: list(raw.sizes, 'Daftar ukuran').map((candidate) => {
      const row = object(candidate, 'Ukuran')
      return {
        id: text(row.id, 'ID ukuran'), code: text(row.code, 'Kode ukuran'),
        sort_order: number(row.sort_order, 'Urutan ukuran'),
        model_ids: list(row.model_ids, 'Model ukuran').map((modelId) => text(modelId, 'ID model ukuran')),
      }
    }),
    locations: list(raw.locations, 'Daftar lokasi').map((candidate) => {
      const row = object(candidate, 'Lokasi')
      return { id: text(row.id, 'ID lokasi'), code: text(row.code, 'Kode lokasi'), name: text(row.name, 'Nama lokasi') }
    }),
    contractors: list(raw.contractors, 'Daftar Mandor').map((candidate) => {
      const row = object(candidate, 'Mandor')
      return { id: text(row.id, 'ID Mandor'), code: text(row.code, 'Kode Mandor'), name: text(row.name, 'Nama Mandor') }
    }),
    drafts: list(raw.drafts, 'Daftar draft').map(parseDraft),
    rolls: list(raw.rolls, 'Daftar roll').map(parseWorkspaceRoll),
  }
}

function parsePickupYield(value: unknown): PickupYield {
  const row = object(value, 'Lineage hasil potong')
  return {
    yield_id: text(row.yield_id, 'ID hasil'), size_slot_id: text(row.size_slot_id, 'ID kolom'),
    slot_no: number(row.slot_no, 'Nomor kolom'), size_id: text(row.size_id, 'ID ukuran'),
    size_code: text(row.size_code, 'Kode ukuran'), drawing_no: number(row.drawing_no, 'Nomor gambar'),
    label: optionalText(row.label), qty_pcs: number(row.qty_pcs, 'Qty hasil'),
  }
}

function parsePickupBatch(value: unknown): PickupBatch {
  const row = object(value, 'Batch Distribusi')
  return {
    id: text(row.id, 'ID batch'), batch_no: number(row.batch_no, 'Nomor batch'),
    notes: optionalText(row.notes), qty_pcs: number(row.qty_pcs, 'Qty batch'),
    allocations: list(row.allocations, 'Alokasi batch').map((candidate) => {
      const allocation = object(candidate, 'Alokasi batch')
      return {
        cutting_roll_yield_id: text(allocation.cutting_roll_yield_id, 'ID hasil potong'),
        qty_pcs: number(allocation.qty_pcs, 'Qty alokasi'),
      }
    }),
  }
}

function parsePickupDraft(value: unknown): PickupDraft | null {
  if (value === null || value === undefined) return null
  const row = object(value, 'Draft pickup')
  const mode = text(row.allocation_mode, 'Mode alokasi')
  const status = text(row.status, 'Status pickup')
  if (!['ROLL', 'SIZE'].includes(mode) || !['DRAFT', 'POSTED'].includes(status)) throw new Error('Lifecycle pickup tidak valid.')
  return {
    id: text(row.id, 'ID pickup'), contractor_id: text(row.contractor_id, 'ID Mandor'),
    contractor_name: text(row.contractor_name, 'Nama Mandor'), picked_up_at: text(row.picked_up_at, 'Waktu pickup'),
    allocation_mode: mode as PickupDraft['allocation_mode'], status: status as PickupDraft['status'],
    notes: optionalText(row.notes), row_version: number(row.row_version, 'Versi pickup'),
    batches: list(row.batches, 'Batch pickup').map(parsePickupBatch),
  }
}

export function parsePickupQueue(value: unknown): PickupQueue {
  const raw = object(value, 'Respons antrean pickup')
  const filter = text(raw.filter, 'Filter pickup')
  if (!['WAITING', 'PICKED', 'ALL'].includes(filter)) throw new Error('Filter pickup tidak valid.')
  return {
    filter: filter as PickupQueue['filter'], pattern_id: optionalText(raw.pattern_id), query: optionalText(raw.query),
    limit: number(raw.limit, 'Limit'), offset: number(raw.offset, 'Offset'), total: number(raw.total, 'Total pickup'),
    contractors: list(raw.contractors, 'Daftar Mandor pickup').map((candidate) => {
      const row = object(candidate, 'Mandor pickup')
      return { id: text(row.id, 'ID Mandor'), code: text(row.code, 'Kode Mandor'), name: text(row.name, 'Nama Mandor') }
    }),
    rows: list(raw.rows, 'Baris pickup').map((candidate) => {
      const row = object(candidate, 'Baris pickup')
      return {
        cutting_group_id: text(row.cutting_group_id, 'ID Potongan'),
        group_number: text(row.group_number, 'Nomor Potongan'), row_version: number(row.row_version, 'Versi Potongan'),
        po_id: text(row.po_id, 'ID PO'), po_number: text(row.po_number, 'Nomor PO'),
        model_code: text(row.model_code, 'Kode model'), model_name: text(row.model_name, 'Nama model'),
        cut_at: text(row.cut_at, 'Waktu potong'), status: text(row.status, 'Status Potongan'),
        picked_up_at: optionalText(row.picked_up_at), executor_name: optionalText(row.executor_name),
        source_location_id: optionalText(row.source_location_id),
        source_location_code: optionalText(row.source_location_code),
        pattern_id: optionalText(row.pattern_id), pattern_code: optionalText(row.pattern_code),
        pattern_revision: optionalText(row.pattern_revision), pattern_name: optionalText(row.pattern_name),
        total_qty_issued: number(row.total_qty_issued, 'Qty bahan'), total_pieces: number(row.total_pieces, 'Qty potongan'),
        pickup_eligible: bool(row.pickup_eligible, 'Status kelayakan pickup'),
        pickup: parsePickupDraft(row.pickup),
        rolls: list(row.rolls, 'Roll Potongan').map((candidateRoll) => {
          const roll = object(candidateRoll, 'Roll Potongan')
          return {
            cutting_group_roll_id: text(roll.cutting_group_roll_id, 'ID roll Potongan'),
            roll_id: text(roll.roll_id, 'ID roll'), roll_number: text(roll.roll_number, 'Nomor roll'),
            material_id: text(roll.material_id, 'ID bahan'), material_sku: text(roll.material_sku, 'SKU bahan'),
            material_name: text(roll.material_name, 'Nama bahan'), unit_code: text(roll.unit_code, 'UOM bahan'),
            supplier_name: optionalText(roll.supplier_name), original_qty: number(roll.original_qty, 'Qty asal'),
            qty_issued: number(roll.qty_issued, 'Qty keluar'), qty_consumed: number(roll.qty_consumed, 'Qty terpakai'),
            qty_reported_remaining: number(roll.qty_reported_remaining, 'Sisa terlapor'),
            yields: list(roll.yields, 'Hasil Potongan').map(parsePickupYield),
          }
        }),
      }
    }),
  }
}

export function parseCuttingSaveResult(value: unknown): CuttingSaveResult {
  const row = object(value, 'Respons simpan Potongan')
  return {
    cutting_group_id: text(row.cutting_group_id, 'ID Potongan'), group_number: text(row.group_number, 'Nomor Potongan'),
    status: text(row.status, 'Status Potongan'), row_version: number(row.row_version, 'Versi Potongan'),
    pattern_id: text(row.pattern_id, 'ID Pola'), pattern_code: text(row.pattern_code, 'Kode Pola'),
    pattern_revision: text(row.pattern_revision, 'Revisi Pola'), pattern_name: text(row.pattern_name, 'Nama Pola'),
    source_location_id: text(row.source_location_id, 'Lokasi sumber'),
    material_issue_posted: bool(row.material_issue_posted, 'Status posting bahan'),
    total_rolls: number(row.total_rolls, 'Total roll'), total_qty_issued: number(row.total_qty_issued, 'Qty keluar'),
    total_qty_consumed: number(row.total_qty_consumed, 'Qty terpakai'),
    total_qty_reported_remaining: number(row.total_qty_reported_remaining, 'Sisa terlapor'),
    total_pieces: number(row.total_pieces, 'Total potongan'),
  }
}

export function parsePickupSaveResult(value: unknown): PickupSaveResult {
  const row = object(value, 'Respons simpan pickup')
  const status = text(row.status, 'Status pickup')
  const mode = text(row.allocation_mode, 'Mode alokasi')
  if (!['DRAFT', 'POSTED', 'DELETED'].includes(status)) throw new Error('Lifecycle pickup tidak valid.')
  if (!['ROLL', 'SIZE'].includes(mode)) throw new Error('Mode alokasi pickup tidak valid.')
  return {
    pickup_id: text(row.pickup_id, 'ID pickup'), cutting_group_id: text(row.cutting_group_id, 'ID Potongan'),
    status: status as PickupSaveResult['status'], row_version: number(row.row_version, 'Versi pickup'),
    group_row_version: number(row.group_row_version, 'Versi Potongan'), picked_up_at: text(row.picked_up_at, 'Waktu pickup'),
    contractor_id: text(row.contractor_id, 'ID Mandor'),
    allocation_mode: mode as PickupSaveResult['allocation_mode'],
    batch_count: number(row.batch_count, 'Jumlah batch'), allocated_pieces: number(row.allocated_pieces, 'Qty terbagi'),
  }
}

export function seedPickupAllocations(
  row: PickupQueueRow,
  batchCount: number,
  mode: 'ROLL' | 'SIZE',
): PickupAllocationMatrix {
  const count = Math.max(1, Math.floor(batchCount))
  const matrix: PickupAllocationMatrix = {}
  if (mode === 'ROLL') {
    row.rolls.forEach((roll, rollIndex) => {
      roll.yields.forEach((yieldRow) => {
        matrix[yieldRow.yield_id] = Array.from({ length: count }, (_, index) => index === rollIndex % count ? yieldRow.qty_pcs : 0)
      })
    })
  } else {
    const sizeOrder = [...new Set(row.rolls.flatMap((roll) => roll.yields.map((yieldRow) => yieldRow.size_id)))]
    row.rolls.forEach((roll) => roll.yields.forEach((yieldRow) => {
      const target = Math.max(0, sizeOrder.indexOf(yieldRow.size_id)) % count
      matrix[yieldRow.yield_id] = Array.from({ length: count }, (_, index) => index === target ? yieldRow.qty_pcs : 0)
    }))
  }
  return matrix
}

export function pickupAllocationState(row: PickupQueueRow, matrix: PickupAllocationMatrix, batchCount: number) {
  const yields = row.rolls.flatMap((roll) => roll.yields)
  const sourceTotal = yields.reduce((sum, yieldRow) => sum + yieldRow.qty_pcs, 0)
  const allocatedTotal = yields.reduce((sum, yieldRow) =>
    sum + (matrix[yieldRow.yield_id] ?? []).reduce((batchSum, qty) => batchSum + Math.max(0, Number(qty) || 0), 0), 0)
  const exact = yields.every((yieldRow) =>
    (matrix[yieldRow.yield_id] ?? []).reduce((sum, qty) => sum + Math.max(0, Number(qty) || 0), 0) === yieldRow.qty_pcs)
  const batchTotals = Array.from({ length: Math.max(1, batchCount) }, (_, batchIndex) => yields.reduce((sum, yieldRow) =>
    sum + Math.max(0, Number(matrix[yieldRow.yield_id]?.[batchIndex]) || 0), 0))
  return { sourceTotal, allocatedTotal, exact, batchTotals, everyBatchUsed: batchTotals.every((qty) => qty > 0) }
}

export function pickupBatchesPayload(matrix: PickupAllocationMatrix, notes: readonly string[], batchCount: number) {
  return Array.from({ length: Math.max(1, batchCount) }, (_, batchIndex) => ({
    batch_no: batchIndex + 1,
    notes: notes[batchIndex]?.trim() || null,
    allocations: Object.entries(matrix).flatMap(([cutting_roll_yield_id, quantities]) => {
      const qty_pcs = Math.max(0, Math.floor(Number(quantities[batchIndex]) || 0))
      return qty_pcs > 0 ? [{ cutting_roll_yield_id, qty_pcs }] : []
    }),
  }))
}

export function draftPickupAllocations(pickup: PickupDraft, batchCount: number): PickupAllocationMatrix {
  const matrix: PickupAllocationMatrix = {}
  pickup.batches.forEach((batch) => batch.allocations.forEach((allocation) => {
    const values = matrix[allocation.cutting_roll_yield_id] ?? Array.from({ length: batchCount }, () => 0)
    values[batch.batch_no - 1] = allocation.qty_pcs
    matrix[allocation.cutting_roll_yield_id] = values
  }))
  return matrix
}
