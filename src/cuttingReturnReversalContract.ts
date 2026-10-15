import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'
import { micro, microText } from './cuttingReturnContract'

// SG-02 cancel / correct (owner D14-10): "Ya, buat tombol batal/koreksi retur kain. Pembalikan stok, hutang/kredit,
// jurnal, dan HPP yang terdampak harus selesai dalam satu transaksi, dengan riwayat asli tetap tersimpan. Kalau ada
// transaksi lanjutan yang menghalangi, tampilkan bagian mana yang harus dibetulkan terlebih dahulu."
export type ReversalSource = { groupId: string; poId: string; number: string; rowVersion: number }
export type LaterUse = { movementId: string; movementType: string; qty: string; physicalAt: string; sourceType: string; sourceId: string | null; label: string }
export type ReturnedRoll = {
  movementId: string; cuttingGroupRollId: string; rollId: string; rollNumber: string; materialSku: string; materialName: string | null
  unitCode: string | null; qtyReturned: string; returnedAt: string; unitCost: string; qtyReportedRemaining: string | null; availableNow: string
  laterUses: LaterUse[]
}
export type ReversalBlocker =
  | { kind: 'NOT_RETURNED'; id: string; label: string }
  | { kind: 'PERIOD_CLOSED'; id: string; label: string; closedThrough: string }
  | { kind: 'LATER_USE'; id: string; label: string; qtyReturned: string; availableNow: string; uses: LaterUse[] }
export type ReversalWorkspace = ReversalSource & { reviewToken: string; cutAt: string; returned: ReturnedRoll[]; eligible: boolean; blockers: ReversalBlocker[] }
export type ReversalOutcome = ReversalSource & { action: 'CANCEL_RETURN' | 'CORRECT_RETURN'; at: string; replacementValue: string | null; recostQueued: boolean }

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
function fail(): never { throw new Error('Respons batal kain kembali tidak cocok dengan potongan yang diperiksa.') }
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail()
  return value as Record<string, unknown>
}
function keys(r: Record<string, unknown>, expected: string[]) {
  if (Object.keys(r).sort().join('|') !== [...expected].sort().join('|')) fail()
}
function version(value: unknown) {
  if (typeof value !== 'string' || !/^[1-9][0-9]{0,18}$/.test(value)) fail()
  const number = Number(value)
  if (!Number.isSafeInteger(number)) fail()
  return number
}
function text(value: unknown) { if (typeof value !== 'string' || !value) fail(); return value }
function optionalText(value: unknown) { if (value === null) return null; return text(value) }
function id(value: unknown) { if (typeof value !== 'string' || !uuid.test(value)) fail(); return value }
function instant(value: unknown) { const t = text(value); if (Number.isNaN(new Date(t).getTime())) fail(); return t }
function quantity(value: unknown) { if (typeof value !== 'string' || micro(value) === null) fail(); return value }
function signed(value: unknown) {
  if (typeof value !== 'string' || micro(value.startsWith('-') ? value.slice(1) : value) === null) fail()
  return value
}
function laterUse(value: unknown): LaterUse {
  const u = record(value)
  keys(u, ['movement_id', 'movement_type', 'qty', 'physical_at', 'source_type', 'source_id', 'label'])
  return { movementId: id(u.movement_id), movementType: text(u.movement_type), qty: signed(u.qty), physicalAt: instant(u.physical_at),
    sourceType: text(u.source_type), sourceId: u.source_id === null ? null : id(u.source_id), label: text(u.label) }
}

export function parseReversal(value: unknown, source: ReversalSource): ReversalWorkspace {
  const r = record(value)
  keys(r, ['contract_version', 'group_id', 'po_id', 'number', 'row_version', 'review_token', 'cut_at', 'returned', 'eligible', 'blockers', 'business_DML'])
  if (r.contract_version !== 'cp7.cutting-return-reversal-workspace.v1' || r.business_DML !== false
    || r.group_id !== source.groupId || r.po_id !== source.poId || r.number !== source.number
    || version(r.row_version) !== source.rowVersion || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token)
    || typeof r.eligible !== 'boolean' || !Array.isArray(r.returned) || !Array.isArray(r.blockers)) fail()
  const seen = new Set<string>()
  const returned = r.returned.map(value => {
    const x = record(value)
    keys(x, ['movement_id', 'cutting_group_roll_id', 'roll_id', 'roll_number', 'material_sku', 'material_name', 'unit_code', 'qty_returned',
      'returned_at', 'unit_cost', 'qty_reported_remaining', 'available_now', 'later_uses'])
    if (seen.has(id(x.cutting_group_roll_id)) || !Array.isArray(x.later_uses)) fail()
    seen.add(x.cutting_group_roll_id as string)
    return {
      movementId: id(x.movement_id), cuttingGroupRollId: x.cutting_group_roll_id as string, rollId: id(x.roll_id), rollNumber: text(x.roll_number),
      materialSku: text(x.material_sku), materialName: optionalText(x.material_name), unitCode: optionalText(x.unit_code),
      qtyReturned: quantity(x.qty_returned), returnedAt: instant(x.returned_at), unitCost: quantity(x.unit_cost),
      qtyReportedRemaining: x.qty_reported_remaining === null ? null : quantity(x.qty_reported_remaining), availableNow: signed(x.available_now),
      laterUses: x.later_uses.map(laterUse),
    }
  })
  const kinds = new Set<string>()
  const blockers = r.blockers.map((value): ReversalBlocker => {
    const b = record(value)
    if (b.kind === 'NOT_RETURNED') { keys(b, ['kind', 'id', 'label']); if (kinds.has('NOT_RETURNED')) fail(); kinds.add('NOT_RETURNED'); return { kind: 'NOT_RETURNED', id: id(b.id), label: text(b.label) } }
    if (b.kind === 'PERIOD_CLOSED') {
      keys(b, ['kind', 'id', 'label', 'closed_through'])
      if (kinds.has('PERIOD_CLOSED') || typeof b.closed_through !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(b.closed_through)) fail()
      kinds.add('PERIOD_CLOSED'); return { kind: 'PERIOD_CLOSED', id: id(b.id), label: text(b.label), closedThrough: b.closed_through }
    }
    if (b.kind === 'LATER_USE') {
      keys(b, ['kind', 'id', 'label', 'qty_returned', 'available_now', 'uses'])
      if (!Array.isArray(b.uses) || !seen.has(id(b.id))) fail()
      return { kind: 'LATER_USE', id: b.id as string, label: text(b.label), qtyReturned: quantity(b.qty_returned), availableNow: signed(b.available_now), uses: b.uses.map(laterUse) }
    }
    return fail()
  })
  if (r.eligible !== (blockers.length === 0) || (r.eligible && returned.length === 0)) fail()
  return { ...source, reviewToken: r.review_token, cutAt: instant(r.cut_at), returned, eligible: r.eligible, blockers }
}

export type CorrectionEntry = { cuttingGroupRollId: string; qty: string }
/** Plain-language problems of a correction; empty for a plain cancel or a correction that can be sent. */
export function correctionProblems(source: ReversalWorkspace, correcting: boolean, entries: CorrectionEntry[]) {
  if (!correcting) return []
  const problems: string[] = []
  const filled = entries.filter(e => e.qty.trim() !== '')
  if (!filled.length) problems.push('Isi jumlah yang benar untuk minimal satu roll, atau pilih "Batalkan saja".')
  for (const e of filled) {
    const roll = source.returned.find(r => r.cuttingGroupRollId === e.cuttingGroupRollId)
    const qty = micro(e.qty), left = roll?.qtyReportedRemaining == null ? null : micro(roll.qtyReportedRemaining)
    if (!roll || left === null) { problems.push('Roll tidak ada di kain kembali potongan ini.'); continue }
    if (qty === null || qty <= 0n) problems.push(`Roll ${roll.rollNumber}: isi angka lebih dari 0 (paling banyak 6 angka di belakang koma).`)
    else if (qty > left) problems.push(`Roll ${roll.rollNumber}: ${microText(qty)} melebihi sisa yang dicatat saat potong (${microText(left)}).`)
  }
  return problems
}
export function reversalPayload(source: ReversalWorkspace, correcting: boolean, entries: CorrectionEntry[], reason: string): Json {
  const why = reason.trim()
  if (!source.eligible || correctionProblems(source, correcting, entries).length || why.length < 5 || why.length > 1000) fail()
  return {
    group_id: source.groupId, po_id: source.poId, review_token: source.reviewToken, change_reason: why,
    replacement_rolls: correcting ? entries.filter(e => e.qty.trim() !== '').map(e => ({ cutting_group_roll_id: e.cuttingGroupRollId, qty_returned: microText(micro(e.qty) as bigint) })) : [],
  }
}
export function validateReversal(value: unknown, envelope: ProductionEnvelope): ReversalOutcome {
  const r = record(value), p = record(envelope.payload)
  keys(r, ['contract_version', 'kind', 'action', 'request_id', 'group_id', 'po_id', 'number', 'row_version', 'at', 'reversed_movements', 'reversed_journals', 'replacement', 'recost_queued'])
  const wanted = Array.isArray(p.replacement_rolls) ? p.replacement_rolls : fail()
  if (envelope.action !== 'REVERSE_RETURN' || r.contract_version !== 'cp7.cutting-return-reversal-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME'
    || r.action !== (wanted.length ? 'CORRECT_RETURN' : 'CANCEL_RETURN') || r.request_id !== envelope.id || r.group_id !== p.group_id || r.po_id !== p.po_id
    || !Number.isSafeInteger(r.reversed_movements) || (r.reversed_movements as number) < 1 || !Number.isSafeInteger(r.reversed_journals)
    || typeof r.recost_queued !== 'boolean') fail()
  let replacementValue: string | null = null
  if (wanted.length) {
    const x = record(r.replacement); keys(x, ['rolls', 'value'])
    if (!Array.isArray(x.rolls) || x.rolls.length !== wanted.length || typeof x.value !== 'string' || micro(x.value) === null) fail()
    x.rolls.forEach((value, i) => {
      const a = record(value), b = record(wanted[i])
      if (a.cutting_group_roll_id !== b.cutting_group_roll_id || typeof a.qty_returned !== 'string' || micro(a.qty_returned) !== micro(String(b.qty_returned))) fail()
    })
    replacementValue = x.value
  } else if (r.replacement !== null) fail()
  return { groupId: String(r.group_id), poId: String(r.po_id), number: text(r.number), rowVersion: version(r.row_version),
    action: r.action as ReversalOutcome['action'], at: instant(r.at), replacementValue, recostQueued: r.recost_queued }
}
