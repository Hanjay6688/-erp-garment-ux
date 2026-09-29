import { expect, it } from 'vitest'
import { parsePolicyOutcome, parsePolicyWorkspace, preparePolicyIntent, type AvailableSku } from '../../src/cp7/production-status/contract'
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const at = '2026-09-29T08:00:00.123456+07:00'
const item = (n = 1): AvailableSku => ({ status: 'AVAILABLE', sku_id: id(n), sku: `SKU-${n}`, brand_id: id(20),
  commercial_version_id: id(n + 10), commercial_revision: '1', members: [id(n + 30)], policy_revision: '0',
  policy: { quality: 'UNREVIEWED', state: null, last_reviewed_state: null, reason: null, review_at: null, review_due: false, recorded_at: null } })
const workspace = () => ({ contract_version: 'cp7.production-policy.v1', knowledge_mode: 'CURRENT', generated_at: at, rows: [item()] })
it('keeps an unreviewed SKU unknown and represents an unavailable SKU explicitly', () => {
  const w = workspace(); const result = parsePolicyWorkspace(w, [id(1)])
  expect(result.rows[0]).toEqual(item())
  expect(result).not.toBe(w)
  const unavailable = { ...w, rows: [{ status: 'UNAVAILABLE', sku_id: id(1) }] }
  expect(parsePolicyWorkspace(unavailable, [id(1)]).rows[0].status).toBe('UNAVAILABLE')
})
it('rejects missing, duplicate or out-of-scope SKU rows and overlapping members', () => {
  expect(() => parsePolicyWorkspace({ ...workspace(), rows: [] }, [id(1)])).toThrow('INCOMPLETE')
  expect(() => parsePolicyWorkspace(workspace(), [id(2)])).toThrow('SCOPE')
  const other = item(2); other.members = [...item().members]
  expect(() => parsePolicyWorkspace({ ...workspace(), rows: [item(), other] }, [id(1), id(2)])).toThrow('MEMBERSHIP_CONFLICT')
  expect(() => parsePolicyWorkspace({ ...workspace(), rows: [item(), item()] }, [id(1), id(2)])).toThrow('SCOPE')
})
it('rejects financial extras and never turns an unknown policy into ACTIVE', () => {
  const extra = workspace(); Object.assign(extra.rows[0], { margin: '9000000' })
  expect(() => parsePolicyWorkspace(extra, [id(1)])).toThrow('FIELDS')
  const active = workspace(); active.rows[0].policy.state = 'ACTIVE'
  expect(() => parsePolicyWorkspace(active, [id(1)])).toThrow('UNREVIEWED')
  const stale = workspace(); stale.rows[0].policy_revision = '1'
  stale.rows[0].policy = { quality: 'MEMBERSHIP_CHANGED', state: 'ACTIVE', last_reviewed_state: 'ACTIVE', reason: 'Prior review', review_at: null, review_due: false, recorded_at: at }
  expect(() => parsePolicyWorkspace(stale, [id(1)])).toThrow('QUALITY')
})
it('preserves the exact reviewed intent after the preview object changes', () => {
  const selected = item(); selected.policy_revision = '9007199254740993'
  const intent = preparePolicyIntent([selected], 'STOPPED', '  Review range  ', null, id(90))
  selected.members.push(id(99)); selected.policy_revision = '9007199254740994'
  expect(intent.p_changes[0].members).toEqual([id(31)])
  expect(intent.p_changes[0].policy_revision).toBe('9007199254740993')
  expect(intent.p_changes[0].reason).toBe('Review range')
})
it('validates all committed rows against the original request with exact bigint versions', () => {
  const selected = item(); selected.policy_revision = '9007199254740993'
  const intent = preparePolicyIntent([selected], 'PAUSED', 'Review', null, id(90))
  const result = { contract_version: 'cp7.production-policy-outcome.v1', kind: 'COMMITTED_OUTCOME', request_id: id(90), recorded_at: at, replayed: true,
    applied: [{ sku_id: id(1), revision: '9007199254740994', state: 'PAUSED', policy_id: id(91) }] }
  expect(parsePolicyOutcome(result, intent).replayed).toBe(true)
  expect(() => parsePolicyOutcome({ ...result, applied: [] }, intent)).toThrow('PARTIAL_OUTCOME')
  expect(() => parsePolicyOutcome({ ...result, request_id: id(89) }, intent)).toThrow('OUTCOME_REQUEST')
  expect(() => parsePolicyOutcome({ ...result, applied: [{ ...result.applied[0], revision: '9007199254740993' }] }, intent)).toThrow('OUTCOME_SCOPE')
  expect(() => parsePolicyOutcome({ ...result, applied: [{ ...result.applied[0], state: 'ACTIVE' }] }, intent)).toThrow('OUTCOME_SCOPE')
})
