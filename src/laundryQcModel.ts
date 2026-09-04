export type LaundryQcScope = 'LAUNDRY' | 'QC'
export type LaundryQcAction =
  | 'POST_DELIVERY' | 'POST_RECEIPT' | 'POST_FAILED_WASH' | 'REVERSE_DELIVERY'
  | 'REVERSE_RECEIPT' | 'POST_FINAL_SKU' | 'REVERSE_FINAL_SKU'

export type Cp6Lookup = { id: string; code: string; name: string }
export type Cp6Rate = {
  id: string; vendor_id: string; wash_process_id: string; rate_per_pcs: number
  effective_from: string; effective_to: string | null
}
export type Cp6Product = {
  id: string; sku: string; name: string; model_id: string; brand_id: string
  model_code: string; model_name: string
  brand_code: string; brand_name: string; size_id: string; size_code: string
  color: string; effective_from: string; effective_to: string | null
}
export type Cp6ReadySize = {
  size_id: string; size_code: string; sort_order: number
  allocated_qty_pcs: number; sent_qty_pcs: number; available_qty_pcs: number
}
export type Cp6ReadyBatch = {
  distribution_batch_id: string; batch_no: number; pickup_id: string
  cutting_group_id: string; cutting_group_row_version: number; group_number: string
  pattern_id: string | null; pattern_code: string | null
  pattern_revision: string | null; pattern_name: string | null
  po_id: string; po_number: string; po_status: string
  model_code: string; model_name: string; contractor_id: string
  contractor_code: string; contractor_name: string; picked_up_at: string
  group_unsent_ready_qty_pcs: number; sizes: Cp6ReadySize[]
}
export type Cp6DeliverySize = {
  delivery_batch_size_line_id: string; size_id: string; size_code: string
  sort_order: number; qty_sent_pcs: number; good_returned_qty_pcs: number
  bs_returned_qty_pcs: number; outstanding_qty_pcs: number
}
export type Cp6ReceiptSummary = {
  id: string; number: string; status: string; row_version: number
  physical_at: string; actual_cost: number | null; actual_rate: number | null
  cost_status: string; event_kind: 'PHYSICAL_RECEIPT' | 'FAILED_WASH_ATTEMPT'
  failed_wash_attempt_id: string | null
  custody_outcome: 'RETRY_AT_VENDOR' | 'RETURN_UNPROCESSED' | null
  attempted_qty_pcs: number | null; process_name: string | null
  reversible: boolean; reversal_blocker: string | null
}
export type Cp6Delivery = {
  delivery_id: string; delivery_number: string; row_version: number; status: string
  physical_at: string; target_dyeing_color: string; special_instruction: string | null
  po_id: string; po_number: string; model_id: string; cutting_group_id: string; group_number: string
  cutting_group_row_version: number; model_code: string; model_name: string
  contractor_name: string | null; vendor_id: string; vendor_code: string
  vendor_name: string; wash_process_id: string | null; process_code: string | null
  process_name: string | null; delivery_line_id: string; qty_sent_pcs: number
  estimated_rate_snapshot: number; estimated_cost: number
  distribution_batch_id: string; batch_no: number; returned_qty_pcs: number
  physical_outstanding_qty_pcs: number; returned_unprocessed_qty_pcs: number
  active_claim_qty_pcs: number
  reversible: boolean; reversal_blocker: string | null
  sizes: Cp6DeliverySize[]; receipts: Cp6ReceiptSummary[]
}
export type Cp6QcQueueRow = {
  source_batch_size_line_id: string; receipt_line_id: string; receipt_id: string
  receipt_number: string; receipt_physical_at: string; distribution_batch_id: string
  batch_no: number; delivery_line_id: string; delivery_id: string
  delivery_number: string; vendor_name: string; cutting_group_id: string
  group_number: string; cutting_group_row_version: number; po_id: string
  po_number: string; model_id: string; model_code: string; model_name: string
  size_id: string; size_code: string; size_sort: number; qty_good_received: number
  qc_accounted_qty_pcs: number; available_for_qc_qty_pcs: number
  completion_status: string; remaining_qc_qty_pcs: number
}
export type Cp6QcHistory = {
  qc_inspection_id: string; inspection_number: string; status: string
  row_version: number; physical_at: string; destination_location_id: string
  location_name: string; po_id: string; po_number: string; good_qty_pcs: number
  bs_qty_pcs: number; cutting_group_count: number
  reversible: boolean; reversal_blocker: string | null
}
export type LaundryQcWorkspace = {
  contract_version: 'CP6_V2620'; scope: LaundryQcScope; generated_at: string
  lookups: {
    vendors: Cp6Lookup[]; wash_processes: Cp6Lookup[]; rate_versions: Cp6Rate[]
    fg_locations: Cp6Lookup[]; products: Cp6Product[]
  }
  readiness: {
    laundry_writer_ready: boolean; qc_writer_ready: boolean
    lineage_integrity_ok: true; lineage_issue_count: 0
    no_fixture_fallback: true; failed_wash_with_charge_supported: true
  }
  ready_batches: Cp6ReadyBatch[]; deliveries: Cp6Delivery[]
  qc_queue: Cp6QcQueueRow[]; qc_history: Cp6QcHistory[]
  legacy_unlinked: { delivery_count: number; receipt_count: number }
}

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const record = (value: unknown, label: string) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} tidak valid.`)
  return value as Record<string, unknown>
}
const list = (value: unknown, label: string) => {
  if (!Array.isArray(value)) throw new Error(`${label} tidak valid.`)
  return value
}
const text = (value: unknown, label: string) => {
  if (typeof value !== 'string' || value.trim() === '') throw new Error(`${label} tidak valid.`)
  return value
}
const nullableText = (value: unknown, label: string) => {
  if (value === null) return null
  return text(value, label)
}
const timestampPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/
const timestamp = (value: unknown, label: string) => {
  const parsed = text(value, label)
  if (!timestampPattern.test(parsed) || !Number.isFinite(Date.parse(parsed))) {
    throw new Error(`${label} bukan timestamp authoritative valid.`)
  }
  return parsed
}
const nullableTimestamp = (value: unknown, label: string) => value === null ? null : timestamp(value, label)
const id = (value: unknown, label: string) => {
  const parsed = text(value, label)
  if (!uuidPattern.test(parsed)) throw new Error(`${label} bukan UUID valid.`)
  return parsed
}
const number = (value: unknown, label: string, minimum = 0) => {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < minimum) {
    throw new Error(`${label} tidak valid.`)
  }
  return value
}
const integer = (value: unknown, label: string, minimum = 0) => {
  const parsed = number(value, label, minimum)
  if (!Number.isSafeInteger(parsed)) throw new Error(`${label} tidak valid.`)
  return parsed
}
const bool = (value: unknown, label: string) => {
  if (typeof value !== 'boolean') throw new Error(`${label} tidak valid.`)
  return value
}
const optionalMoney = (value: unknown, label: string) => value === null ? null : number(value, label)
const normalizedText = (value: string) => value.trim().toLowerCase()

function assertPeriod(effectiveFrom: string, effectiveTo: string | null, label: string) {
  if (effectiveTo !== null && Date.parse(effectiveTo) <= Date.parse(effectiveFrom)) {
    throw new Error(`${label} memiliki periode berlaku terbalik atau kosong.`)
  }
}

function assertUnique<T>(rows: T[], key: (row: T) => string, label: string) {
  const seen = new Set<string>()
  rows.forEach((row) => {
    const value = key(row)
    if (seen.has(value)) throw new Error(`${label} duplikat pada payload authoritative.`)
    seen.add(value)
  })
}

function assertStableMetadata<T>(
  rows: T[], key: (row: T) => string, signature: (row: T) => string, label: string,
) {
  const seen = new Map<string, string>()
  rows.forEach((row) => {
    const identity = key(row)
    const value = signature(row)
    const prior = seen.get(identity)
    if (prior !== undefined && prior !== value) {
      throw new Error(`${label} kontradiktif pada payload authoritative.`)
    }
    seen.set(identity, value)
  })
}

function parseLookup(value: unknown, label: string): Cp6Lookup {
  const raw = record(value, label)
  return { id: id(raw.id, `${label} ID`), code: text(raw.code, `${label} kode`), name: text(raw.name, `${label} nama`) }
}

function parseRate(value: unknown): Cp6Rate {
  const raw = record(value, 'Rate Laundry')
  const parsed = {
    id: id(raw.id, 'ID rate'), vendor_id: id(raw.vendor_id, 'Vendor rate'),
    wash_process_id: id(raw.wash_process_id, 'Proses rate'),
    rate_per_pcs: number(raw.rate_per_pcs, 'Rate per pcs'),
    effective_from: timestamp(raw.effective_from, 'Waktu berlaku rate'),
    effective_to: nullableTimestamp(raw.effective_to, 'Akhir rate'),
  }
  assertPeriod(parsed.effective_from, parsed.effective_to, 'Rate Laundry')
  return parsed
}

function parseProduct(value: unknown): Cp6Product {
  const raw = record(value, 'Final SKU')
  const parsed = {
    id: id(raw.id, 'ID Final SKU'), sku: text(raw.sku, 'SKU'), name: text(raw.name, 'Nama produk'),
    model_id: id(raw.model_id, 'Model produk'), brand_id: id(raw.brand_id, 'Merek produk'),
    model_code: text(raw.model_code, 'Kode model produk'),
    model_name: text(raw.model_name, 'Nama model produk'),
    brand_code: text(raw.brand_code, 'Kode merek'), brand_name: text(raw.brand_name, 'Nama merek'),
    size_id: id(raw.size_id, 'Size produk'), size_code: text(raw.size_code, 'Kode size'),
    color: text(raw.color, 'Warna produk'), effective_from: timestamp(raw.effective_from, 'Waktu berlaku produk'),
    effective_to: nullableTimestamp(raw.effective_to, 'Akhir produk'),
  }
  assertPeriod(parsed.effective_from, parsed.effective_to, 'Final SKU')
  return parsed
}

function parseReadySize(value: unknown): Cp6ReadySize {
  const raw = record(value, 'Size batch siap Laundry')
  const allocated = integer(raw.allocated_qty_pcs, 'Qty distribusi')
  const sent = integer(raw.sent_qty_pcs, 'Qty sudah dikirim')
  const available = integer(raw.available_qty_pcs, 'Qty tersedia')
  if (sent > allocated || available !== allocated - sent) throw new Error('Konservasi size batch siap Laundry tidak konsisten.')
  return {
    size_id: id(raw.size_id, 'ID size'), size_code: text(raw.size_code, 'Kode size'),
    sort_order: integer(raw.sort_order, 'Urutan size'), allocated_qty_pcs: allocated,
    sent_qty_pcs: sent, available_qty_pcs: available,
  }
}

function parseReadyBatch(value: unknown): Cp6ReadyBatch {
  const raw = record(value, 'Batch siap Laundry')
  const sizes = list(raw.sizes, 'Size batch siap Laundry').map(parseReadySize)
  assertUnique(sizes, (size) => size.size_id, 'Size dalam satu batch Laundry')
  if (!sizes.some((size) => size.available_qty_pcs > 0)) throw new Error('Batch siap Laundry tidak memiliki sisa size.')
  return {
    distribution_batch_id: id(raw.distribution_batch_id, 'ID batch distribusi'),
    batch_no: integer(raw.batch_no, 'Nomor batch', 1), pickup_id: id(raw.pickup_id, 'ID pickup'),
    cutting_group_id: id(raw.cutting_group_id, 'ID Potongan'),
    cutting_group_row_version: integer(raw.cutting_group_row_version, 'Versi Potongan', 1),
    group_number: text(raw.group_number, 'Nomor Potongan'), pattern_id: raw.pattern_id === null ? null : id(raw.pattern_id, 'ID Pola'),
    pattern_code: nullableText(raw.pattern_code, 'Kode Pola'),
    pattern_revision: nullableText(raw.pattern_revision, 'Revisi Pola'),
    pattern_name: nullableText(raw.pattern_name, 'Nama Pola'), po_id: id(raw.po_id, 'ID PO'),
    po_number: text(raw.po_number, 'Nomor PO'), po_status: text(raw.po_status, 'Status PO'),
    model_code: text(raw.model_code, 'Kode model'), model_name: text(raw.model_name, 'Nama model'),
    contractor_id: id(raw.contractor_id, 'ID Mandor'), contractor_code: text(raw.contractor_code, 'Kode Mandor'),
    contractor_name: text(raw.contractor_name, 'Nama Mandor'), picked_up_at: timestamp(raw.picked_up_at, 'Waktu pickup'),
    group_unsent_ready_qty_pcs: integer(raw.group_unsent_ready_qty_pcs, 'Qty jahit siap kirim'), sizes,
  }
}

function parseDeliverySize(value: unknown, deliveryReversed: boolean): Cp6DeliverySize {
  const raw = record(value, 'Size pengiriman Laundry')
  const sent = integer(raw.qty_sent_pcs, 'Qty kirim size', 1)
  const good = integer(raw.good_returned_qty_pcs, 'Good kembali')
  const bs = integer(raw.bs_returned_qty_pcs, 'BS Laundry kembali')
  const outstanding = integer(raw.outstanding_qty_pcs, 'Outstanding Laundry')
  if (good + bs > sent || outstanding !== (deliveryReversed ? 0 : sent - good - bs)) {
    throw new Error('Konservasi size pengiriman Laundry tidak konsisten.')
  }
  return {
    delivery_batch_size_line_id: id(raw.delivery_batch_size_line_id, 'ID sumber batch/size'),
    size_id: id(raw.size_id, 'ID size pengiriman'), size_code: text(raw.size_code, 'Kode size pengiriman'),
    sort_order: integer(raw.sort_order, 'Urutan size pengiriman'), qty_sent_pcs: sent,
    good_returned_qty_pcs: good, bs_returned_qty_pcs: bs, outstanding_qty_pcs: outstanding,
  }
}

function parseReceiptSummary(value: unknown): Cp6ReceiptSummary {
  const raw = record(value, 'Ringkasan penerimaan Laundry')
  const reversible = bool(raw.reversible, 'Status reversal penerimaan')
  const blocker = nullableText(raw.reversal_blocker, 'Penghambat reversal penerimaan')
  if (reversible !== (blocker === null)) {
    throw new Error('Status dan penghambat reversal penerimaan kontradiktif.')
  }
  const eventKind = text(raw.event_kind, 'Jenis peristiwa Laundry')
  if (!['PHYSICAL_RECEIPT', 'FAILED_WASH_ATTEMPT'].includes(eventKind)) {
    throw new Error('Jenis peristiwa Laundry tidak dikenal.')
  }
  const failedAttemptId = raw.failed_wash_attempt_id === null
    ? null : id(raw.failed_wash_attempt_id, 'ID attempt cuci gagal')
  const custodyOutcome = raw.custody_outcome === null
    ? null : text(raw.custody_outcome, 'Hasil custody cuci gagal')
  const attemptedQty = raw.attempted_qty_pcs === null
    ? null : integer(raw.attempted_qty_pcs, 'Qty attempt cuci gagal', 1)
  const processName = nullableText(raw.process_name, 'Proses attempt cuci gagal')
  if (eventKind === 'PHYSICAL_RECEIPT'
    && (failedAttemptId !== null || custodyOutcome !== null || attemptedQty !== null || processName !== null)) {
    throw new Error('Penerimaan fisik membawa metadata attempt cuci gagal.')
  }
  if (eventKind === 'FAILED_WASH_ATTEMPT'
    && (failedAttemptId === null || !['RETRY_AT_VENDOR', 'RETURN_UNPROCESSED'].includes(custodyOutcome ?? '')
      || attemptedQty === null || processName === null)) {
    throw new Error('Metadata attempt cuci gagal tidak lengkap.')
  }
  return {
    id: id(raw.id, 'ID penerimaan'), number: text(raw.number, 'Nomor penerimaan'),
    status: text(raw.status, 'Status penerimaan'), row_version: integer(raw.row_version, 'Versi penerimaan', 1),
    physical_at: timestamp(raw.physical_at, 'Waktu penerimaan'), actual_cost: optionalMoney(raw.actual_cost, 'Biaya aktual'),
    actual_rate: optionalMoney(raw.actual_rate, 'Tarif aktual'), cost_status: text(raw.cost_status, 'Status biaya'),
    event_kind: eventKind as Cp6ReceiptSummary['event_kind'], failed_wash_attempt_id: failedAttemptId,
    custody_outcome: custodyOutcome as Cp6ReceiptSummary['custody_outcome'],
    attempted_qty_pcs: attemptedQty, process_name: processName,
    reversible, reversal_blocker: blocker,
  }
}

function parseDelivery(value: unknown): Cp6Delivery {
  const raw = record(value, 'Pengiriman Laundry')
  const deliveryStatus = text(raw.status, 'Status pengiriman')
  const deliveryReversed = deliveryStatus === 'REVERSED'
  const sizes = list(raw.sizes, 'Size pengiriman')
    .map((row) => parseDeliverySize(row, deliveryReversed))
  const receipts = list(raw.receipts, 'Penerimaan Laundry').map(parseReceiptSummary)
  assertUnique(sizes, (size) => size.delivery_batch_size_line_id, 'Sumber batch/size pengiriman Laundry')
  assertUnique(sizes, (size) => size.size_id, 'Size dalam satu pengiriman Laundry')
  assertUnique(receipts, (receipt) => receipt.id, 'Penerimaan dalam satu pengiriman Laundry')
  const sent = integer(raw.qty_sent_pcs, 'Total dikirim', 1)
  const returned = integer(raw.returned_qty_pcs, 'Total kembali')
  const outstanding = integer(raw.physical_outstanding_qty_pcs, 'Total di luar')
  const returnedUnprocessed = integer(raw.returned_unprocessed_qty_pcs, 'Total kembali tanpa diproses')
  const activeClaim = integer(raw.active_claim_qty_pcs, 'Qty claim aktif')
  const reversible = bool(raw.reversible, 'Status reversal pengiriman')
  const blocker = nullableText(raw.reversal_blocker, 'Penghambat reversal pengiriman')
  if (sizes.reduce((sum, row) => sum + row.qty_sent_pcs, 0) !== sent
    || returned > sent || returnedUnprocessed > sent
    || returned + returnedUnprocessed + outstanding !== sent
    || deliveryReversed !== (returnedUnprocessed === sent)
    || sizes.reduce((sum, row) => sum + row.outstanding_qty_pcs, 0) !== outstanding
    || activeClaim > outstanding) {
    throw new Error('Agregat pengiriman Laundry tidak sama dengan fakta size.')
  }
  if (reversible !== (blocker === null)) {
    throw new Error('Status dan penghambat reversal pengiriman kontradiktif.')
  }
  return {
    delivery_id: id(raw.delivery_id, 'ID pengiriman'), delivery_number: text(raw.delivery_number, 'Nomor pengiriman'),
    row_version: integer(raw.row_version, 'Versi pengiriman', 1), status: deliveryStatus,
    physical_at: timestamp(raw.physical_at, 'Waktu pengiriman'), target_dyeing_color: text(raw.target_dyeing_color, 'Warna target'),
    special_instruction: nullableText(raw.special_instruction, 'Instruksi khusus'), po_id: id(raw.po_id, 'ID PO pengiriman'),
    po_number: text(raw.po_number, 'Nomor PO pengiriman'), model_id: id(raw.model_id, 'ID model pengiriman'),
    cutting_group_id: id(raw.cutting_group_id, 'ID Potongan pengiriman'),
    group_number: text(raw.group_number, 'Nomor Potongan pengiriman'),
    cutting_group_row_version: integer(raw.cutting_group_row_version, 'Versi Potongan pengiriman', 1),
    model_code: text(raw.model_code, 'Kode model pengiriman'), model_name: text(raw.model_name, 'Nama model pengiriman'),
    contractor_name: nullableText(raw.contractor_name, 'Mandor pengiriman'), vendor_id: id(raw.vendor_id, 'ID vendor'),
    vendor_code: text(raw.vendor_code, 'Kode vendor'), vendor_name: text(raw.vendor_name, 'Nama vendor'),
    wash_process_id: raw.wash_process_id === null ? null : id(raw.wash_process_id, 'ID proses cuci'),
    process_code: nullableText(raw.process_code, 'Kode proses cuci'), process_name: nullableText(raw.process_name, 'Nama proses cuci'),
    delivery_line_id: id(raw.delivery_line_id, 'ID baris pengiriman'), qty_sent_pcs: sent,
    estimated_rate_snapshot: number(raw.estimated_rate_snapshot, 'Rate estimasi'),
    estimated_cost: number(raw.estimated_cost, 'Biaya estimasi'),
    distribution_batch_id: id(raw.distribution_batch_id, 'ID batch pengiriman'), batch_no: integer(raw.batch_no, 'Nomor batch pengiriman', 1),
    returned_qty_pcs: returned, physical_outstanding_qty_pcs: outstanding,
    returned_unprocessed_qty_pcs: returnedUnprocessed,
    active_claim_qty_pcs: activeClaim,
    reversible, reversal_blocker: blocker, sizes,
    receipts,
  }
}

function parseQcQueue(value: unknown): Cp6QcQueueRow {
  const raw = record(value, 'Antrean QC')
  const good = integer(raw.qty_good_received, 'Good tersedia dari Laundry', 1)
  const used = integer(raw.qc_accounted_qty_pcs, 'Qty sudah QC')
  const available = integer(raw.available_for_qc_qty_pcs, 'Qty siap QC', 1)
  if (used > good || available !== good - used) throw new Error('Konservasi Good Laundry ke QC tidak konsisten.')
  return {
    source_batch_size_line_id: id(raw.source_batch_size_line_id, 'ID sumber QC batch/size'),
    receipt_line_id: id(raw.receipt_line_id, 'ID baris penerimaan QC'), receipt_id: id(raw.receipt_id, 'ID penerimaan QC'),
    receipt_number: text(raw.receipt_number, 'Nomor penerimaan QC'), receipt_physical_at: timestamp(raw.receipt_physical_at, 'Waktu penerimaan QC'),
    distribution_batch_id: id(raw.distribution_batch_id, 'ID batch QC'), batch_no: integer(raw.batch_no, 'Nomor batch QC', 1),
    delivery_line_id: id(raw.delivery_line_id, 'ID baris kirim QC'), delivery_id: id(raw.delivery_id, 'ID kirim QC'),
    delivery_number: text(raw.delivery_number, 'Nomor kirim QC'), vendor_name: text(raw.vendor_name, 'Vendor QC'),
    cutting_group_id: id(raw.cutting_group_id, 'ID Potongan QC'), group_number: text(raw.group_number, 'Nomor Potongan QC'),
    cutting_group_row_version: integer(raw.cutting_group_row_version, 'Versi Potongan QC', 1), po_id: id(raw.po_id, 'ID PO QC'),
    po_number: text(raw.po_number, 'Nomor PO QC'), model_id: id(raw.model_id, 'ID model QC'),
    model_code: text(raw.model_code, 'Kode model QC'), model_name: text(raw.model_name, 'Nama model QC'),
    size_id: id(raw.size_id, 'ID size QC'), size_code: text(raw.size_code, 'Kode size QC'),
    size_sort: integer(raw.size_sort, 'Urutan size QC'), qty_good_received: good,
    qc_accounted_qty_pcs: used, available_for_qc_qty_pcs: available,
    completion_status: text(raw.completion_status, 'Status penyelesaian QC'),
    remaining_qc_qty_pcs: integer(raw.remaining_qc_qty_pcs, 'Sisa QC Potongan'),
  }
}

function parseQcHistory(value: unknown): Cp6QcHistory {
  const raw = record(value, 'Histori QC')
  const reversible = bool(raw.reversible, 'Status reversal QC')
  const blocker = nullableText(raw.reversal_blocker, 'Penghambat reversal QC')
  if (reversible !== (blocker === null)) {
    throw new Error('Status dan penghambat reversal QC kontradiktif.')
  }
  return {
    qc_inspection_id: id(raw.qc_inspection_id, 'ID QC'), inspection_number: text(raw.inspection_number, 'Nomor QC'),
    status: text(raw.status, 'Status QC'), row_version: integer(raw.row_version, 'Versi QC', 1),
    physical_at: timestamp(raw.physical_at, 'Waktu QC'), destination_location_id: id(raw.destination_location_id, 'Lokasi QC'),
    location_name: text(raw.location_name, 'Nama lokasi QC'), po_id: id(raw.po_id, 'ID PO histori QC'),
    po_number: text(raw.po_number, 'Nomor PO histori QC'), good_qty_pcs: integer(raw.good_qty_pcs, 'Good QC'),
    bs_qty_pcs: integer(raw.bs_qty_pcs, 'BS QC'), cutting_group_count: integer(raw.cutting_group_count, 'Jumlah Potongan', 1),
    reversible, reversal_blocker: blocker,
  }
}

export function parseLaundryQcWorkspace(value: unknown): LaundryQcWorkspace {
  const raw = record(value, 'Workspace Laundry/QC')
  if (raw.contract_version !== 'CP6_V2620' || !['LAUNDRY', 'QC'].includes(String(raw.scope))) {
    throw new Error('Versi kontrak workspace Laundry/QC tidak cocok.')
  }
  const lookupsRaw = record(raw.lookups, 'Lookup Laundry/QC')
  const readinessRaw = record(raw.readiness, 'Kesiapan writer Laundry/QC')
  if (readinessRaw.no_fixture_fallback !== true || readinessRaw.failed_wash_with_charge_supported !== true
    || readinessRaw.lineage_integrity_ok !== true
    || integer(readinessRaw.lineage_issue_count, 'Jumlah masalah lineage') !== 0) {
    throw new Error('Batas reliability Laundry/QC tidak cocok.')
  }
  const scope = raw.scope as LaundryQcScope
  const readyBatches = list(raw.ready_batches, 'Batch Laundry').map(parseReadyBatch)
  const deliveries = list(raw.deliveries, 'Pengiriman Laundry').map(parseDelivery)
  const qcQueue = list(raw.qc_queue, 'Antrean QC').map(parseQcQueue)
  const qcHistory = list(raw.qc_history, 'Histori QC').map(parseQcHistory)
  if (scope === 'LAUNDRY' && (qcQueue.length > 0 || qcHistory.length > 0)) throw new Error('Scope Laundry membocorkan data QC.')
  if (scope === 'QC' && (readyBatches.length > 0 || deliveries.length > 0)) throw new Error('Scope QC membocorkan data Laundry writer.')
  const legacyRaw = record(raw.legacy_unlinked, 'Ringkasan lineage lama')
  const vendors = list(lookupsRaw.vendors, 'Vendor').map((row) => parseLookup(row, 'Vendor'))
  const washProcesses = list(lookupsRaw.wash_processes, 'Proses cuci')
    .map((row) => parseLookup(row, 'Proses cuci'))
  const rateVersions = list(lookupsRaw.rate_versions, 'Versi rate').map(parseRate)
  const fgLocations = list(lookupsRaw.fg_locations, 'Lokasi FG')
    .map((row) => parseLookup(row, 'Lokasi FG'))
  const products = list(lookupsRaw.products, 'Produk').map(parseProduct)
  assertUnique(vendors, (row) => row.id, 'ID Vendor')
  assertUnique(vendors, (row) => normalizedText(row.code), 'Kode Vendor')
  assertUnique(washProcesses, (row) => row.id, 'ID proses cuci')
  assertUnique(washProcesses, (row) => normalizedText(row.code), 'Kode proses cuci')
  assertUnique(rateVersions, (row) => row.id, 'ID versi rate Laundry')
  assertUnique(fgLocations, (row) => row.id, 'ID lokasi FG')
  assertUnique(fgLocations, (row) => normalizedText(row.code), 'Kode lokasi FG')
  assertUnique(products, (row) => row.id, 'ID Final SKU')
  assertUnique(readyBatches, (row) => row.distribution_batch_id, 'ID batch distribusi siap Laundry')
  assertUnique(deliveries, (row) => row.delivery_id, 'ID pengiriman Laundry')
  assertUnique(deliveries, (row) => row.delivery_line_id, 'ID baris pengiriman Laundry')
  assertUnique(qcQueue, (row) => row.source_batch_size_line_id, 'Sumber batch/size antrean QC')
  assertUnique(qcHistory, (row) => row.qc_inspection_id, 'ID histori QC')

  const vendorIds = new Set(vendors.map((row) => row.id))
  const processIds = new Set(washProcesses.map((row) => row.id))
  if (rateVersions.some((row) => !vendorIds.has(row.vendor_id) || !processIds.has(row.wash_process_id))) {
    throw new Error('Versi rate Laundry menunjuk Vendor/proses yang tidak ada di lookup authoritative.')
  }
  for (let leftIndex = 0; leftIndex < rateVersions.length; leftIndex += 1) {
    const left = rateVersions[leftIndex]
    for (let rightIndex = leftIndex + 1; rightIndex < rateVersions.length; rightIndex += 1) {
      const right = rateVersions[rightIndex]
      if (left.vendor_id !== right.vendor_id || left.wash_process_id !== right.wash_process_id) continue
      const overlaps = Date.parse(left.effective_from) < (right.effective_to === null ? Infinity : Date.parse(right.effective_to))
        && Date.parse(right.effective_from) < (left.effective_to === null ? Infinity : Date.parse(left.effective_to))
      if (overlaps) throw new Error('Versi rate Laundry bertumpuk pada Vendor/proses yang sama.')
    }
  }

  assertStableMetadata(products, (row) => row.brand_id,
    (row) => JSON.stringify([row.brand_code, row.brand_name]), 'Metadata Merek Final SKU')
  assertStableMetadata(products, (row) => row.model_id,
    (row) => JSON.stringify([row.model_code, row.model_name]), 'Metadata Model Final SKU')
  assertStableMetadata(products, (row) => row.size_id,
    (row) => row.size_code, 'Metadata size Final SKU')
  assertStableMetadata(readyBatches, (row) => row.cutting_group_id, (row) => JSON.stringify([
    row.cutting_group_row_version, row.group_number, row.po_id, row.po_number,
    row.model_code, row.model_name, row.contractor_id, row.contractor_code,
    row.contractor_name, row.pattern_id, row.pattern_code, row.pattern_revision,
    row.pattern_name, row.group_unsent_ready_qty_pcs,
  ]), 'Metadata Potongan batch siap Laundry')
  assertStableMetadata(qcQueue, (row) => row.cutting_group_id, (row) => JSON.stringify([
    row.cutting_group_row_version, row.group_number, row.po_id, row.po_number,
    row.model_id, row.model_code, row.model_name, row.remaining_qc_qty_pcs,
    row.completion_status,
  ]), 'Metadata Potongan antrean QC')

  const sizeReferences = [
    ...products.map((row) => ({ id: row.size_id, code: row.size_code })),
    ...readyBatches.flatMap((batch) => batch.sizes.map((row) => ({ id: row.size_id, code: row.size_code }))),
    ...deliveries.flatMap((delivery) => delivery.sizes.map((row) => ({ id: row.size_id, code: row.size_code }))),
    ...qcQueue.map((row) => ({ id: row.size_id, code: row.size_code })),
  ]
  assertStableMetadata(sizeReferences, (row) => row.id, (row) => row.code, 'Metadata size lintas workspace')

  for (let leftIndex = 0; leftIndex < products.length; leftIndex += 1) {
    const left = products[leftIndex]
    for (let rightIndex = leftIndex + 1; rightIndex < products.length; rightIndex += 1) {
      const right = products[rightIndex]
      const sameHumanSku = left.brand_id === right.brand_id
        && normalizedText(left.sku) === normalizedText(right.sku)
      const overlaps = Date.parse(left.effective_from) < (right.effective_to === null ? Infinity : Date.parse(right.effective_to))
        && Date.parse(right.effective_from) < (left.effective_to === null ? Infinity : Date.parse(left.effective_to))
      if (!overlaps) continue
      if (sameHumanSku) {
        if (left.size_id === right.size_id) {
          throw new Error('Lookup produk memiliki dua identitas aktif untuk Merek + Nomor SKU + size yang sama.')
        }
        if (left.model_id !== right.model_id
          || normalizedText(left.color) !== normalizedText(right.color)) {
          throw new Error('Varian size satu Merek + Nomor SKU tidak konsisten pada Model/warna.')
        }
      }
      if (left.brand_id === right.brand_id && left.model_id === right.model_id
        && normalizedText(left.color) === normalizedText(right.color)
        && left.size_id === right.size_id) {
        throw new Error('Lookup produk memetakan kombinasi Merek/Model/warna/size aktif ke lebih dari satu Nomor SKU.')
      }
    }
  }
  const expectedLaundryReady = vendors.length > 0 && washProcesses.length > 0 && rateVersions.length > 0
  const expectedQcReady = fgLocations.length > 0 && products.length > 0
  if (bool(readinessRaw.laundry_writer_ready, 'Kesiapan Laundry') !== expectedLaundryReady
    || bool(readinessRaw.qc_writer_ready, 'Kesiapan QC') !== expectedQcReady) {
    throw new Error('Flag kesiapan writer tidak sama dengan master authoritative yang tersedia.')
  }
  return {
    contract_version: 'CP6_V2620', scope, generated_at: timestamp(raw.generated_at, 'Waktu workspace'),
    lookups: {
      vendors, wash_processes: washProcesses, rate_versions: rateVersions,
      fg_locations: fgLocations, products,
    },
    readiness: {
      laundry_writer_ready: expectedLaundryReady, qc_writer_ready: expectedQcReady,
      lineage_integrity_ok: true, lineage_issue_count: 0,
      no_fixture_fallback: true, failed_wash_with_charge_supported: true,
    },
    ready_batches: readyBatches, deliveries, qc_queue: qcQueue, qc_history: qcHistory,
    legacy_unlinked: {
      delivery_count: integer(legacyRaw.delivery_count, 'Pengiriman tanpa lineage CP6'),
      receipt_count: integer(legacyRaw.receipt_count, 'Penerimaan tanpa lineage CP6'),
    },
  }
}

export function findLaundryRateAt(
  workspace: LaundryQcWorkspace, vendorId: string, processId: string, physicalAt: string,
) {
  const at = new Date(physicalAt).getTime()
  if (!Number.isFinite(at)) return null
  const matches = workspace.lookups.rate_versions
    .filter((rate) => rate.vendor_id === vendorId && rate.wash_process_id === processId
      && new Date(rate.effective_from).getTime() <= at
      && (rate.effective_to === null || new Date(rate.effective_to).getTime() > at))
  return matches.length === 1 ? matches[0] : null
}

export function productEffectiveAt(product: Cp6Product, physicalAt: string) {
  const at = new Date(physicalAt).getTime()
  return Number.isFinite(at) && new Date(product.effective_from).getTime() <= at
    && (product.effective_to === null || new Date(product.effective_to).getTime() > at)
}

export function totalReadyToSend(batches: Cp6ReadyBatch[]) {
  const byGroup = new Map<string, { unsent: number; batchCapacity: number }>()
  batches.forEach((batch) => {
    const batchCapacity = batch.sizes.reduce((sum, size) => sum + size.available_qty_pcs, 0)
    const current = byGroup.get(batch.cutting_group_id)
    if (current) current.batchCapacity += batchCapacity
    else byGroup.set(batch.cutting_group_id, {
      unsent: batch.group_unsent_ready_qty_pcs, batchCapacity,
    })
  })
  return [...byGroup.values()].reduce(
    (sum, group) => sum + Math.min(group.unsent, group.batchCapacity), 0,
  )
}
