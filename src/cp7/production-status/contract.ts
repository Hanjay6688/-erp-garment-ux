/** Untrusted policy transport boundary. This module has no operational side effects. */
export type ProductionState = 'ACTIVE' | 'PAUSED' | 'STOPPED'
export type Policy = {
  quality: 'UNREVIEWED' | 'MEMBERSHIP_CHANGED' | 'KNOWN'
  state: ProductionState | null
  last_reviewed_state: ProductionState | null
  reason: string | null
  review_at: string | null
  review_due: boolean
  recorded_at: string | null
}
export type AvailableSku = {
  status: 'AVAILABLE'; sku_id: string; sku: string; brand_id: string
  commercial_version_id: string; commercial_revision: string
  members: string[]; policy_revision: string; policy: Policy
}
export type PolicyWorkspace = {
  contract_version: 'cp7.production-policy.v1'; knowledge_mode: 'CURRENT'
  generated_at: string; rows: (AvailableSku | { status: 'UNAVAILABLE'; sku_id: string })[]
}
export type PolicyChange = {
  sku_id: string; commercial_version_id: string; commercial_revision: string
  members: string[]; policy_revision: string; state: ProductionState
  reason: string; review_at: string | null
}
export type PolicyIntent = { p_request: string; p_changes: PolicyChange[] }
export type PolicyOutcome = {
  contract_version: 'cp7.production-policy-outcome.v1'; kind: 'COMMITTED_OUTCOME'
  request_id: string; recorded_at: string; replayed: boolean
  applied: { sku_id: string; revision: string; state: ProductionState; policy_id: string }[]
}
const fail = (code: string): never => { throw new Error(`CP7_POLICY_${code}`) }
const object = (value: unknown): Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : fail('SHAPE')
const fields = (value: Record<string, unknown>, names: string[]) => {
  if (Object.keys(value).length !== names.length || names.some(name => !Object.hasOwn(value, name))) fail('FIELDS')
}
const text = (value: unknown) => { if (typeof value !== 'string' || value.trim() === '') fail('TEXT') }
const uuid = (value: unknown) => {
  if (typeof value !== 'string' || !/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/.test(value)) fail('ID')
}
const revision = (value: unknown) => {
  if (typeof value !== 'string' || !/^(?:0|[1-9][0-9]*)$/.test(value) || BigInt(value) > 9223372036854775807n) fail('REVISION')
}
const state = (value: unknown) => {
  if (!['ACTIVE', 'PAUSED', 'STOPPED'].includes(value as string)) fail('STATE')
}
const instant = (value: unknown) => {
  if (typeof value !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(value)
    || !Number.isFinite(Date.parse(value))) fail('TIME')
}
const ids = (value: unknown, max: number): string[] => {
  if (!Array.isArray(value) || value.length < 1 || value.length > max) return fail('SCOPE')
  value.forEach(uuid)
  if (new Set(value).size !== value.length) fail('DUPLICATE')
  return value as string[]
}

export function parsePolicyWorkspace(value: unknown, requested: readonly string[]): PolicyWorkspace {
  ids([...requested], 200)
  const v = object(value)
  fields(v, ['contract_version', 'knowledge_mode', 'generated_at', 'rows'])
  if (v.contract_version !== 'cp7.production-policy.v1' || v.knowledge_mode !== 'CURRENT') fail('VERSION')
  instant(v.generated_at)
  if (!Array.isArray(v.rows) || v.rows.length !== requested.length) return fail('INCOMPLETE')
  const seen = new Set<string>(); const members = new Set<string>()
  for (const raw of v.rows) {
    const r = object(raw); uuid(r.sku_id)
    const sku = r.sku_id as string
    if (!requested.includes(sku) || seen.has(sku)) fail('SCOPE')
    seen.add(sku)
    if (r.status === 'UNAVAILABLE') { fields(r, ['status', 'sku_id']); continue }
    fields(r, ['status', 'sku_id', 'sku', 'brand_id', 'commercial_version_id', 'commercial_revision', 'members', 'policy_revision', 'policy'])
    if (r.status !== 'AVAILABLE') fail('STATUS')
    text(r.sku); uuid(r.brand_id); uuid(r.commercial_version_id); revision(r.commercial_revision); revision(r.policy_revision)
    if (r.commercial_revision === '0') fail('REVISION')
    for (const id of ids(r.members, 500)) {
      if (members.has(id)) fail('MEMBERSHIP_CONFLICT')
      members.add(id)
    }
    const p = object(r.policy)
    fields(p, ['quality', 'state', 'last_reviewed_state', 'reason', 'review_at', 'review_due', 'recorded_at'])
    if (typeof p.review_due !== 'boolean') fail('SHAPE')
    if (p.quality === 'UNREVIEWED') {
      if (r.policy_revision !== '0' || [p.state, p.last_reviewed_state, p.reason, p.review_at, p.recorded_at].some(x => x !== null) || p.review_due) fail('UNREVIEWED')
    } else {
      if (r.policy_revision === '0') fail('REVISION')
      state(p.last_reviewed_state); text(p.reason); instant(p.recorded_at)
      if (p.review_at !== null) instant(p.review_at)
      if (p.quality === 'KNOWN') {
        state(p.state)
        if (p.state !== p.last_reviewed_state) fail('STATE')
      } else if (p.quality !== 'MEMBERSHIP_CHANGED' || p.state !== null) fail('QUALITY')
    }
  }
  return structuredClone(v) as PolicyWorkspace
}

/** Freeze an explicit intent before sending; preserve it after an ambiguous response. */
export function preparePolicyIntent(rows: readonly AvailableSku[], target: ProductionState, reason: string,
  reviewAt: string | null, requestId: string): PolicyIntent {
  state(target); uuid(requestId); text(reason)
  if (reason.trim().length > 1000 || rows.length < 1 || rows.length > 100) fail('REQUEST')
  ids(rows.map(r => r.sku_id), 100)
  if (reviewAt !== null) instant(reviewAt)
  const changes = rows.map(r => ({ sku_id: r.sku_id, commercial_version_id: r.commercial_version_id,
    commercial_revision: r.commercial_revision, members: [...r.members], policy_revision: r.policy_revision,
    state: target, reason: reason.trim(), review_at: reviewAt }))
  return structuredClone({ p_request: requestId, p_changes: changes })
}

export function parsePolicyOutcome(value: unknown, intent: PolicyIntent): PolicyOutcome {
  const v = object(value)
  fields(v, ['contract_version', 'kind', 'request_id', 'recorded_at', 'replayed', 'applied'])
  if (v.contract_version !== 'cp7.production-policy-outcome.v1' || v.kind !== 'COMMITTED_OUTCOME') fail('VERSION')
  if (v.request_id !== intent.p_request || typeof v.replayed !== 'boolean') fail('OUTCOME_REQUEST')
  instant(v.recorded_at)
  if (!Array.isArray(v.applied) || v.applied.length !== intent.p_changes.length) return fail('PARTIAL_OUTCOME')
  const seen = new Set<string>(); const events = new Set<string>()
  for (const raw of v.applied) {
    const a = object(raw)
    fields(a, ['sku_id', 'revision', 'state', 'policy_id'])
    uuid(a.sku_id); uuid(a.policy_id); revision(a.revision); state(a.state)
    const change = intent.p_changes.find(c => c.sku_id === a.sku_id)
    if (!change || seen.has(a.sku_id as string) || events.has(a.policy_id as string)
      || a.state !== change.state || BigInt(a.revision as string) !== BigInt(change.policy_revision) + 1n) fail('OUTCOME_SCOPE')
    seen.add(a.sku_id as string); events.add(a.policy_id as string)
  }
  return structuredClone(v) as PolicyOutcome
}
