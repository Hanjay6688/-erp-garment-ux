import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

export type CuttingCorrectionSource = { groupId: string; poId: string; number: string; rowVersion: number }
export type CuttingCorrectionWorkspace = CuttingCorrectionSource & {
  reviewToken: string; eligible: boolean
  blockers: Array<{ kind: 'PICKUP_OR_LIFECYCLE' | 'DOWNSTREAM' | 'PICKUP' | 'MATERIAL_FLOW'; id: string; label: string; status?: 'DRAFT' | 'POSTED' }>
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
function fail(): never { throw new Error('Respons koreksi potongan tidak cocok dengan sumber yang diperiksa.') }
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail()
  return value as Record<string, unknown>
}
function version(value: unknown) {
  if (typeof value !== 'string' || !/^[1-9][0-9]{0,18}$/.test(value)) fail()
  const number = Number(value)
  if (!Number.isSafeInteger(number)) fail()
  return number
}
export function parseCuttingCorrection(value: unknown, source: CuttingCorrectionSource): CuttingCorrectionWorkspace {
  const r = record(value)
  if (Object.keys(r).sort().join('|') !== ['contract_version','group_id','po_id','number','row_version','review_token','eligible','blockers','business_DML'].sort().join('|')
    || r.contract_version !== 'cp7.cutting-reopen-workspace.v1' || r.business_DML !== false
    || r.group_id !== source.groupId || r.po_id !== source.poId || r.number !== source.number
    || version(r.row_version) !== source.rowVersion || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token)
    || typeof r.eligible !== 'boolean' || !Array.isArray(r.blockers)) fail()
  const ids = new Set<string>()
  const blockers = r.blockers.map(value => {
    const b = record(value)
    if (!['PICKUP_OR_LIFECYCLE','DOWNSTREAM','PICKUP','MATERIAL_FLOW'].includes(String(b.kind))
      || typeof b.id !== 'string' || !uuid.test(b.id) || typeof b.label !== 'string' || !b.label
      || Object.keys(b).sort().join('|') !== (b.kind === 'PICKUP' ? 'id|kind|label|status' : 'id|kind|label')
      || (b.kind === 'PICKUP' && !['DRAFT','POSTED'].includes(String(b.status)))) fail()
    const key = `${b.kind}:${b.id}`
    if (ids.has(key)) fail()
    ids.add(key)
    return b as CuttingCorrectionWorkspace['blockers'][number]
  })
  if (r.eligible !== (blockers.length === 0)) fail()
  return { ...source, reviewToken: r.review_token, eligible: r.eligible, blockers }
}
export function cuttingReopenPayload(source: CuttingCorrectionWorkspace, reason: string): Json {
  const text = reason.trim()
  if (!source.eligible || !uuid.test(source.groupId) || !uuid.test(source.poId) || text.length < 5 || text.length > 1000) fail()
  return { group_id: source.groupId, po_id: source.poId, review_token: source.reviewToken, change_reason: text }
}
export function validateCuttingReopen(value: unknown, envelope: ProductionEnvelope): CuttingCorrectionSource {
  const r = record(value), p = record(envelope.payload), native = record(r.Native_response)
  if (envelope.action !== 'REOPEN_POSTED' || r.contract_version !== 'cp7.cutting-reopen-outcome.v1'
    || r.kind !== 'COMMITTED_OUTCOME' || r.action !== envelope.action || r.request_id !== envelope.id
    || r.group_id !== p.group_id || r.po_id !== p.po_id || typeof r.number !== 'string' || !r.number
    || r.status !== 'DRAFT_FOR_CORRECTION' || native.cutting_group_id !== r.group_id || native.status !== 'CUT'
    || native.presewing_reversible !== true || !Number.isSafeInteger(native.row_version) || native.row_version !== version(r.row_version)
    || !Number.isSafeInteger(native.reversed_movement_count) || Number(native.reversed_movement_count) < 1
    || !Number.isSafeInteger(native.reversed_journal_count) || Number(native.reversed_journal_count) < 0) fail()
  return { groupId: String(r.group_id), poId: String(r.po_id), number: r.number, rowVersion: version(r.row_version) }
}
