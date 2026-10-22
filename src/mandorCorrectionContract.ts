import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

export type MandorCorrectionWorkspace = {
  poId: string; poNumber: string; contractorId: string
  contractors: { id: string; name: string }[]; groupCount: number; pickupCount: number
  blockers: { order: number; kind: string; id: string; number: string | null; status: string | null; step: string }[]
  eligible: boolean; reviewToken: string; afterStep: string
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
function fail(): never { throw new Error('Respons koreksi mandor tidak cocok dengan PO yang diperiksa.') }
function object(v: unknown): Record<string, unknown> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) fail()
  return v as Record<string, unknown>
}
function text(v: unknown) { if (typeof v !== 'string' || !v.trim()) fail(); return v }
function id(v: unknown) { const s = text(v); if (!uuid.test(s)) fail(); return s }
function count(v: unknown) { if (typeof v !== 'number' || !Number.isSafeInteger(v) || v < 0) fail(); return v }
export function correctionPoFromSewing(value: unknown, groupId: string): string {
  const r = object(value)
  if (r.contract_version !== 'cp7.sewing-completion-workspace.v1' || r.group_id !== groupId) fail()
  return id(r.po_id)
}
export function parseMandorCorrection(value: unknown, poId: string): MandorCorrectionWorkspace {
  const r = object(value)
  if (r.contract_version !== 'cp7.mandor-correction-workspace.v1' || r.po_id !== poId || r.business_DML !== false
      || typeof r.eligible !== 'boolean' || !Array.isArray(r.contractors) || !Array.isArray(r.blockers)) fail()
  const contractors = r.contractors.map(v => { const c = object(v); return { id: id(c.id), name: text(c.name) } })
  if (new Set(contractors.map(c => c.id)).size !== contractors.length) fail()
  const blockers = r.blockers.map(v => {
    const b = object(v)
    return { order: count(b.order), kind: text(b.kind), id: id(b.id), number: b.number == null ? null : text(b.number),
      status: b.status == null ? null : text(b.status), step: text(b.step) }
  })
  if (r.eligible !== (blockers.length === 0)) fail()
  const reviewToken = text(r.review_token)
  if (!/^[0-9a-f]{32}$/.test(reviewToken)) fail()
  const contractorId = r.contractor_id === null ? '' : id(r.contractor_id)
  return { poId: id(r.po_id), poNumber: text(r.po_number), contractorId, contractors,
    groupCount: count(r.group_count), pickupCount: count(r.pickup_count), blockers,
    eligible: r.eligible, reviewToken, afterStep: text(r.after_step) }
}
export function mandorCorrectionPayload(w: MandorCorrectionWorkspace, target: string, reason: string): Json {
  if (!w.eligible || !uuid.test(target) || target === w.contractorId || !w.contractors.some(c => c.id === target)
      || reason.trim().length < 5 || reason.trim().length > 1000) throw new Error('Periksa mandor pengganti dan alasan koreksi.')
  return { po_id: w.poId, contractor_id: target, review_token: w.reviewToken, change_reason: reason.trim() }
}
export function validateMandorCorrection(value: unknown, envelope: ProductionEnvelope) {
  const r = object(value), p = object(envelope.payload)
  if (envelope.action !== 'CORRECT_MANDOR' || r.contract_version !== 'cp7.mandor-correction-result.v1'
      || r.request_id !== envelope.id || r.po_id !== p.po_id || r.contractor_id !== p.contractor_id
      || r.status !== 'PICKUPS_REPLACED' || r.sewing_repost_required !== true || r.wage_history_reassigned !== false
      || !Array.isArray(r.replacements) || r.replacements.length === 0) fail()
  if (id(r.old_contractor_id) === id(r.contractor_id)) fail()
  const groups = r.replacements.map(v => {
    const row = object(v)
    if (id(row.old_pickup_id) === id(row.new_pickup_id) || count(row.allocated_pieces) === 0) fail()
    const at = text(row.picked_up_at)
    if (Number.isNaN(new Date(at).getTime())) fail()
    return id(row.group_id)
  })
  if (new Set(groups).size !== groups.length) fail()
  return { poNumber: text(r.po_number), pickupCount: groups.length }
}
