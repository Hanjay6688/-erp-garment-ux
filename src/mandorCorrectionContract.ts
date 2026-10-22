import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

export type MandorCorrectionBlocker = {
  order: number; kind: string; id: string; number: string | null; status: string | null; step: string
  menu: string | null; source: { sourceType: string; sourceId: string } | null
}
export type MandorCorrectionHistory = {
  generationNo: number; recordedAt: string; actorName: string | null; oldContractorName: string; newContractorName: string
  reason: string; pickupCount: number
}
export type MandorCorrectionWorkspace = {
  poId: string; poNumber: string; contractorId: string
  contractors: { id: string; name: string }[]; groupCount: number; pickupCount: number
  blockers: MandorCorrectionBlocker[]
  eligible: boolean; reviewToken: string; afterStep: string
  afterSteps: { menu: string; step: string }[]; history: MandorCorrectionHistory[]
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
function time(v: unknown) { const s = text(v); if (Number.isNaN(new Date(s).getTime())) fail(); return s }
// The server names a sidebar menu as "Section › Item"; anything else is not a menu the operator can open.
function menu(v: unknown) { const s = text(v); if (!/^[A-Z][A-Za-z ]+ › \S.*$/.test(s)) fail(); return s }
function source(v: unknown) {
  if (v === null) return null
  const r = object(v)
  if (Object.keys(r).sort().join('|') !== 'source_id|source_type' || typeof r.source_type !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(r.source_type)) fail()
  return { sourceType: r.source_type, sourceId: id(r.source_id) }
}
export function correctionPoFromSewing(value: unknown, groupId: string): string {
  const r = object(value)
  if (r.contract_version !== 'cp7.sewing-completion-workspace.v1' || r.group_id !== groupId) fail()
  return id(r.po_id)
}
export function parseMandorCorrection(value: unknown, poId: string): MandorCorrectionWorkspace {
  const r = object(value)
  if (r.contract_version !== 'cp7.mandor-correction-workspace.v1' || r.po_id !== poId || r.business_DML !== false
      || typeof r.eligible !== 'boolean' || !Array.isArray(r.contractors) || !Array.isArray(r.blockers)
      || !Array.isArray(r.after_steps) || r.after_steps.length === 0 || !Array.isArray(r.history)) fail()
  const contractors = r.contractors.map(v => { const c = object(v); return { id: id(c.id), name: text(c.name) } })
  if (new Set(contractors.map(c => c.id)).size !== contractors.length) fail()
  const blockers = r.blockers.map(v => {
    const b = object(v)
    if (!('menu' in b) || !('source' in b)) fail()
    return { order: count(b.order), kind: text(b.kind), id: id(b.id), number: b.number == null ? null : text(b.number),
      status: b.status == null ? null : text(b.status), step: text(b.step), menu: b.menu === null ? null : menu(b.menu), source: source(b.source) }
  })
  const afterSteps = r.after_steps.map(v => { const a = object(v); return { menu: menu(a.menu), step: text(a.step) } })
  const history = r.history.map(v => {
    const h = object(v)
    return { generationNo: count(h.generation_no), recordedAt: time(h.recorded_at), actorName: h.actor_name === null ? null : text(h.actor_name),
      oldContractorName: text(h.old_contractor_name), newContractorName: text(h.new_contractor_name), reason: text(h.reason),
      pickupCount: count(h.pickup_count) }
  })
  if (history.some((h, i) => i > 0 && h.generationNo >= history[i - 1].generationNo)) fail()
  if (r.eligible !== (blockers.length === 0)) fail()
  const reviewToken = text(r.review_token)
  if (!/^[0-9a-f]{32}$/.test(reviewToken)) fail()
  const contractorId = r.contractor_id === null ? '' : id(r.contractor_id)
  return { poId: id(r.po_id), poNumber: text(r.po_number), contractorId, contractors,
    groupCount: count(r.group_count), pickupCount: count(r.pickup_count), blockers,
    eligible: r.eligible, reviewToken, afterStep: text(r.after_step), afterSteps, history }
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
