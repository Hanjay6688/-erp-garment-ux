import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// SG-01 (Fable FABLE-009, Astra SG-01): a POSTED pickup (Bagi Potongan) is reversed before any sewing. Closed parsers for
// the workspace and the committed outcome of scripts/cp7-src/cutting-correction/pickup.sql.
export type PickupReversalSource = { groupId: string; poId: string; number: string; pickupId: string }
export type PickupReversalBlocker = { kind: string; id: string | null; label: string | null; status: string | null }
export type PickupReversalRestore = {
  executorName: string | null; poStatus: string | null; poStage: string | null; clearMandor: boolean
  mandorBoundBy: Array<{ kind: string; id: string }>; otherGroupsPickedUp: boolean
}
export type PickupReversalWorkspace = PickupReversalSource & {
  poNumber: string; pickupVersion: string; pickedUpAt: string; contractorId: string; contractorName: string | null
  batchCount: number; pieces: number; restore: PickupReversalRestore; reviewToken: string; eligible: boolean; blockers: PickupReversalBlocker[]
}
export type PickupReversalOutcome = { groupId: string; pickupId: string; number: string; poStatus: string; poStage: string; mandorCleared: boolean }

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
function fail(): never { throw new Error('Respons batal Bagi Potongan tidak cocok dengan potongan yang diperiksa.') }
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail()
  return value as Record<string, unknown>
}
function keys(r: Record<string, unknown>, expected: string[]) {
  if (Object.keys(r).sort().join('|') !== [...expected].sort().join('|')) fail()
}
function text(value: unknown) { if (typeof value !== 'string' || !value) fail(); return value }
function nullableText(value: unknown) { return value === null || value === undefined ? null : text(value) }
function id(value: unknown) { const v = text(value); if (!uuid.test(v)) fail(); return v }
function count(value: unknown) { if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) fail(); return value }

export function parsePickupReversal(value: unknown, source: PickupReversalSource): PickupReversalWorkspace {
  const r = record(value)
  keys(r, ['contract_version', 'group_id', 'po_id', 'number', 'po_number', 'pickup_id', 'pickup_version', 'picked_up_at', 'contractor_id',
    'contractor_name', 'batch_count', 'pieces', 'restore', 'review_token', 'eligible', 'blockers', 'business_DML'])
  if (r.contract_version !== 'cp7.pickup-reversal-workspace.v1' || r.business_DML !== false || r.group_id !== source.groupId
    || r.po_id !== source.poId || r.pickup_id !== source.pickupId || typeof r.eligible !== 'boolean'
    || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token)
    || typeof r.pickup_version !== 'string' || !/^[1-9][0-9]{0,18}$/.test(r.pickup_version) || !Array.isArray(r.blockers)) fail()
  const x = record(r.restore)
  keys(x, ['executor_name', 'po_status', 'po_stage', 'clear_mandor', 'mandor_bound_by', 'other_groups_picked_up'])
  if (typeof x.clear_mandor !== 'boolean' || typeof x.other_groups_picked_up !== 'boolean' || !Array.isArray(x.mandor_bound_by)) fail()
  const restore: PickupReversalRestore = {
    executorName: nullableText(x.executor_name), poStatus: nullableText(x.po_status), poStage: nullableText(x.po_stage),
    clearMandor: x.clear_mandor, otherGroupsPickedUp: x.other_groups_picked_up,
    mandorBoundBy: x.mandor_bound_by.map(v => { const b = record(v); return { kind: text(b.kind), id: id(b.id) } }),
  }
  const blockers = r.blockers.map(v => {
    const b = record(v)
    return { kind: text(b.kind), id: b.id === undefined || b.id === null ? null : text(b.id), label: nullableText(b.label), status: nullableText(b.status) }
  })
  if (r.eligible !== (blockers.length === 0) || (r.eligible && (!restore.poStatus || !restore.poStage))) fail()
  const pickedUpAt = text(r.picked_up_at)
  if (Number.isNaN(new Date(pickedUpAt).getTime())) fail()
  return {
    ...source, number: text(r.number), poNumber: text(r.po_number), pickupVersion: r.pickup_version, pickedUpAt,
    contractorId: id(r.contractor_id), contractorName: nullableText(r.contractor_name), batchCount: count(r.batch_count), pieces: count(r.pieces),
    restore, reviewToken: r.review_token, eligible: r.eligible, blockers,
  }
}

export function pickupReversalPayload(w: PickupReversalWorkspace, reason: string): Json {
  const why = reason.trim()
  if (!w.eligible || why.length < 5 || why.length > 1000) fail()
  return { group_id: w.groupId, pickup_id: w.pickupId, review_token: w.reviewToken, change_reason: why }
}

export function validatePickupReversal(value: unknown, envelope: ProductionEnvelope): PickupReversalOutcome {
  const r = record(value), p = record(envelope.payload)
  keys(r, ['contract_version', 'kind', 'action', 'request_id', 'group_id', 'pickup_id', 'po_id', 'number', 'result'])
  if (envelope.action !== 'REVERSE_PICKUP' || r.contract_version !== 'cp7.pickup-reversal-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME'
    || r.action !== envelope.action || r.request_id !== envelope.id || r.group_id !== p.group_id || r.pickup_id !== p.pickup_id) fail()
  const x = record(r.result)
  keys(x, ['pickup_status', 'group_status', 'po_status', 'po_stage', 'mandor_cleared', 'mandor_bound_by'])
  if (x.pickup_status !== 'REVERSED' || x.group_status !== 'CUT' || typeof x.mandor_cleared !== 'boolean' || !Array.isArray(x.mandor_bound_by)) fail()
  return { groupId: id(r.group_id), pickupId: id(r.pickup_id), number: text(r.number), poStatus: text(x.po_status), poStage: text(x.po_stage), mandorCleared: x.mandor_cleared }
}

const kinds: Record<string, string> = {
  NO_POSTED_PICKUP: 'Potongan ini belum punya Bagi Potongan yang sudah dicatat.',
  GROUP_STATE: 'Status potongan tidak cocok dengan Bagi Potongan yang tercatat.',
  DOWNSTREAM: 'Potongan ini sudah masuk proses lanjutan (jahit, laundry, QC, atau barang jadi).',
  WIP_EVENT: 'Sudah ada catatan status WIP.',
  WORK_COMPLETION: 'Sudah ada setoran jahit (termasuk yang masih draf).',
  QC: 'Sudah ada catatan QC.',
  LAUNDRY: 'Sudah ada kiriman laundry.',
  LAUNDRY_BATCH: 'Batch ini sudah dipakai di kiriman laundry.',
  FG_LOT: 'Sudah ada barang jadi dari potongan ini.',
  BS_CASE: 'Sudah ada kasus BS.',
  SCRAP: 'Sudah ada catatan scrap.',
  QTY_CORRECTION: 'Sudah ada koreksi jumlah potongan.',
  SEWING_TERMINAL: 'Sudah ada catatan selesai jahit.',
  ATTENDANCE_POOL: 'Sudah dipakai di pembagian HPP absensi.',
  WIP_FLAG: 'Sudah ada tanda WIP.',
  POCKET: 'Sudah dipakai di kain kantong.',
  PO_STATE: 'Production Order sedang ditahan, selesai, atau dibatalkan.',
  NO_POST_AUDIT: 'Catatan saat Bagi Potongan diposting tidak lengkap, jadi nilai sebelumnya tidak bisa dipulihkan dengan pasti.',
  GROUP_CHANGED_SINCE_PICKUP: 'Data potongan sudah berubah sejak Bagi Potongan dicatat.',
  PO_CHANGED_SINCE_PICKUP: 'Status Production Order sudah berubah sejak Bagi Potongan dicatat.',
  PO_STAGE_BEFORE_PICKUP: 'Status Production Order sebelum Bagi Potongan tidak bisa dipulihkan.',
}
export function pickupBlockerText(b: PickupReversalBlocker) {
  return `${kinds[b.kind] ?? `Ada catatan lain yang terikat (${b.kind}).`}${b.status ? ` Status: ${b.status}.` : ''}`
}
export const boundText: Record<string, string> = {
  OTHER_PICKUP: 'Bagi Potongan lain di PO yang sama', MATERIAL_ISSUE: 'pengambilan bahan mandor', WORK_COMPLETION: 'setoran jahit',
  PAYROLL_WORK: 'upah di payroll', WORK_SNAPSHOT: 'tarif kerja PO', ACCESSORY_ENTITLEMENT: 'penggantian aksesori', REWORK: 'rework',
}
