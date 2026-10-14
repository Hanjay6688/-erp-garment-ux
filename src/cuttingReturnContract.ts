import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// SG-02 (owner D14-4): leftover fabric of a posted cutting goes back to the warehouse, the same roll with its value,
// and the PO cost drops by that value. Quantities are exact decimals (scale 6) and never pass through floats.
export type CuttingReturnSource = { groupId: string; poId: string; number: string; rowVersion: number }
export type CuttingReturnRoll = {
  cuttingGroupRollId: string; rollId: string; rollNumber: string; materialSku: string; materialName: string | null; unitCode: string | null
  qtyIssued: string; qtyConsumed: string; qtyReportedRemaining: string; unitCost: string | null
}
export type CuttingReturnBlocker = { kind: 'NOT_POSTED' | 'ALREADY_RETURNED' | 'RETURN_FACTS_PRESENT' | 'WAREHOUSE' | 'NOTHING_LEFT'; id: string; label: string }
export type CuttingReturnWorkspace = CuttingReturnSource & {
  reviewToken: string; cutAt: string; openFrom: string; warehouse: { id: string; code: string; name: string } | null
  rolls: CuttingReturnRoll[]; eligible: boolean; blockers: CuttingReturnBlocker[]
}
export type CuttingReturnOutcome = CuttingReturnSource & { returnedAt: string; value: string; recostQueued: boolean }

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const decimal = /^(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?$/
const blockerKinds = ['NOT_POSTED', 'ALREADY_RETURNED', 'RETURN_FACTS_PRESENT', 'WAREHOUSE', 'NOTHING_LEFT']
const SCALE = 1_000_000n
function fail(): never { throw new Error('Respons kain kembali ke gudang tidak cocok dengan potongan yang diperiksa.') }
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
function instant(value: unknown) { const t = text(value); if (Number.isNaN(new Date(t).getTime())) fail(); return t }

/** An exact non-negative decimal of at most 6 places as an integer number of millionths, or null. */
export function micro(value: string): bigint | null {
  const v = value.trim()
  if (!decimal.test(v)) return null
  const [whole, fraction = ''] = v.split('.')
  return BigInt(whole) * SCALE + BigInt(fraction.padEnd(6, '0'))
}
export function microText(value: bigint) {
  const whole = value / SCALE, fraction = (value % SCALE).toString().padStart(6, '0').replace(/0+$/, '')
  return fraction ? `${whole}.${fraction}` : String(whole)
}
/** qty × unit cost rounded half up to whole cents, as the Native journal posts it (nothing below half a cent). */
export function returnValueCents(qty: string, unitCost: string | null): bigint {
  const q = micro(qty), c = unitCost === null ? 0n : micro(unitCost)
  if (q === null || c === null) return 0n
  const product = q * c // 12 decimal places
  if (product <= 5n * 10n ** 9n) return 0n // value <= 0.005: Native posts no journal line
  return (product + 5n * 10n ** 9n) / 10n ** 10n
}
export function rupiah(cents: bigint) {
  const whole = (cents / 100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `Rp${whole},${(cents % 100n).toString().padStart(2, '0')}`
}

export function parseCuttingReturn(value: unknown, source: CuttingReturnSource): CuttingReturnWorkspace {
  const r = record(value)
  keys(r, ['contract_version', 'group_id', 'po_id', 'number', 'row_version', 'review_token', 'cut_at', 'open_from', 'warehouse', 'rolls', 'eligible', 'blockers', 'business_DML'])
  if (r.contract_version !== 'cp7.cutting-return-workspace.v1' || r.business_DML !== false
    || r.group_id !== source.groupId || r.po_id !== source.poId || r.number !== source.number
    || version(r.row_version) !== source.rowVersion || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token)
    || typeof r.eligible !== 'boolean' || !Array.isArray(r.rolls) || !Array.isArray(r.blockers)
    || typeof r.open_from !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(r.open_from)) fail()
  let warehouse: CuttingReturnWorkspace['warehouse'] = null
  if (r.warehouse !== null) {
    const w = record(r.warehouse); keys(w, ['id', 'code', 'name'])
    if (typeof w.id !== 'string' || !uuid.test(w.id)) fail()
    warehouse = { id: w.id, code: text(w.code), name: text(w.name) }
  }
  const seen = new Set<string>()
  const rolls = r.rolls.map(value => {
    const x = record(value)
    keys(x, ['cutting_group_roll_id', 'roll_id', 'roll_number', 'material_sku', 'material_name', 'unit_code', 'qty_issued', 'qty_consumed', 'qty_reported_remaining', 'unit_cost'])
    if (typeof x.cutting_group_roll_id !== 'string' || !uuid.test(x.cutting_group_roll_id) || seen.has(x.cutting_group_roll_id)
      || typeof x.roll_id !== 'string' || !uuid.test(x.roll_id)) fail()
    seen.add(x.cutting_group_roll_id)
    for (const k of ['qty_issued', 'qty_consumed', 'qty_reported_remaining']) if (typeof x[k] !== 'string' || micro(x[k] as string) === null) fail()
    if (x.unit_cost !== null && (typeof x.unit_cost !== 'string' || micro(x.unit_cost) === null)) fail()
    return {
      cuttingGroupRollId: x.cutting_group_roll_id, rollId: x.roll_id, rollNumber: text(x.roll_number), materialSku: text(x.material_sku),
      materialName: optionalText(x.material_name), unitCode: optionalText(x.unit_code), qtyIssued: x.qty_issued as string,
      qtyConsumed: x.qty_consumed as string, qtyReportedRemaining: x.qty_reported_remaining as string, unitCost: x.unit_cost as string | null,
    }
  })
  const ids = new Set<string>()
  const blockers = r.blockers.map(value => {
    const b = record(value); keys(b, ['kind', 'id', 'label'])
    if (!blockerKinds.includes(String(b.kind)) || typeof b.id !== 'string' || !uuid.test(b.id) || ids.has(String(b.kind))) fail()
    ids.add(String(b.kind))
    return { kind: b.kind, id: b.id, label: text(b.label) } as CuttingReturnBlocker
  })
  if (r.eligible !== (blockers.length === 0) || (r.eligible && (!warehouse || rolls.length === 0))) fail()
  return { ...source, reviewToken: r.review_token, cutAt: instant(r.cut_at), openFrom: r.open_from, warehouse, rolls, eligible: r.eligible, blockers }
}

export type CuttingReturnEntry = { cuttingGroupRollId: string; qty: string }
/** Plain-language problems of the entered quantities; empty when the entry can be sent. */
export function cuttingReturnProblems(source: CuttingReturnWorkspace, entries: CuttingReturnEntry[]) {
  const problems: string[] = []
  const positive = entries.filter(e => e.qty.trim() !== '')
  if (!positive.length) problems.push('Isi jumlah kain kembali untuk minimal satu roll.')
  for (const e of positive) {
    const roll = source.rolls.find(r => r.cuttingGroupRollId === e.cuttingGroupRollId)
    const qty = micro(e.qty), left = roll ? micro(roll.qtyReportedRemaining) : null
    if (!roll || left === null) { problems.push('Roll tidak ada di potongan ini.'); continue }
    if (qty === null || qty <= 0n) problems.push(`Roll ${roll.rollNumber}: isi angka lebih dari 0 (paling banyak 6 angka di belakang koma).`)
    else if (qty > left) problems.push(`Roll ${roll.rollNumber}: kain kembali ${microText(qty)} melebihi sisa yang dicatat saat potong (${microText(left)}).`)
  }
  return problems
}
export function cuttingReturnPayload(source: CuttingReturnWorkspace, entries: CuttingReturnEntry[], returnedAtIso: string, reason: string): Json {
  const why = reason.trim()
  if (!source.eligible || cuttingReturnProblems(source, entries).length || why.length < 5 || why.length > 1000
    || Number.isNaN(new Date(returnedAtIso).getTime())) fail()
  return {
    group_id: source.groupId, po_id: source.poId, review_token: source.reviewToken, returned_at: returnedAtIso, change_reason: why,
    rolls: entries.filter(e => e.qty.trim() !== '').map(e => ({ cutting_group_roll_id: e.cuttingGroupRollId, qty_returned: microText(micro(e.qty) as bigint) })),
  }
}
export function validateCuttingReturn(value: unknown, envelope: ProductionEnvelope): CuttingReturnOutcome {
  const r = record(value), p = record(envelope.payload)
  keys(r, ['contract_version', 'kind', 'action', 'request_id', 'group_id', 'po_id', 'number', 'row_version', 'returned_at', 'rolls', 'value', 'recost_queued'])
  if (envelope.action !== 'RETURN_FABRIC' || r.contract_version !== 'cp7.cutting-return-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME'
    || r.action !== envelope.action || r.request_id !== envelope.id || r.group_id !== p.group_id || r.po_id !== p.po_id
    || typeof r.value !== 'string' || micro(r.value) === null || typeof r.recost_queued !== 'boolean' || !Array.isArray(r.rolls)
    || !Array.isArray(p.rolls) || r.rolls.length !== p.rolls.length
    || new Date(instant(r.returned_at)).getTime() !== new Date(String(p.returned_at)).getTime()) fail()
  r.rolls.forEach((value, i) => {
    const x = record(value), y = record((p.rolls as unknown[])[i])
    if (x.cutting_group_roll_id !== y.cutting_group_roll_id || typeof x.qty_returned !== 'string'
      || micro(x.qty_returned) !== micro(String(y.qty_returned))) fail()
  })
  return { groupId: String(r.group_id), poId: String(r.po_id), number: text(r.number), rowVersion: version(r.row_version),
    returnedAt: String(r.returned_at), value: r.value, recostQueued: r.recost_queued }
}
