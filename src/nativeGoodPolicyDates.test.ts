// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import wire from '../scripts/cp7_accessory_nonpayable/LOCAL_SETTINGS_CONTROLS.json'
import { clearGoodDateRequest, goodPolicyDate, goodPolicyDateRequestKey, parseGoodDateOutcome,
  parseGoodPolicyDates, parsePreparedGoodDate, persistGoodDateRequest, prepareGoodPolicyDate,
  readGoodDateRequest, readGoodPolicyDates, saveGoodPolicyDate } from './nativeGoodPolicyDates'

const sample = wire.contract_samples, actor = sample.workspace.actor, scope = 'model:good-policy-dates'
const prepared = () => parsePreparedGoodDate({ ...structuredClone(sample.command), sourceEvent: structuredClone(sample.workspace.current_source) }, actor)
const cancelled = () => ({ ...sample.outcome, status: 'CANCELLED', id: null, source_version: null })
beforeEach(() => localStorage.clear())
afterEach(() => { localStorage.clear(); vi.restoreAllMocks() })

it('parses the actual PostgreSQL model workspace, source selection and stored result', () => {
  const w = parseGoodPolicyDates(sample.workspace, actor)
  expect(w.source_events).toHaveLength(30); expect(w.next_source_before).toBe('6')
  const command = prepareGoodPolicyDate(w, w.current_source.id, sample.command.payload.effective_from,
    sample.command.payload.reason, true, sample.command.requestId)
  expect(command).toEqual(prepared())
  expect(parseGoodDateOutcome(sample.outcome, command).status).toBe('SAVED')
})
it('refuses malformed fields, boolean coercion, duplicate source identities and inconsistent cursors', () => {
  for (const mutate of [
    (w: Record<string, unknown>) => { w.can_write = 1 },
    (w: Record<string, unknown>) => { w.extra = true },
    (w: Record<string, unknown>) => { w.actor = '00000000-0000-4000-8000-000000000099' },
    (w: Record<string, unknown>) => { w.next_source_before = '7' },
    (w: Record<string, unknown>) => { w.source_events = [sample.workspace.source_events[0], sample.workspace.source_events[0]] },
    (w: Record<string, unknown>) => { w.current_source = { ...sample.workspace.current_source, status: ['SET'] } },
    (w: Record<string, unknown>) => { w.current_source = { ...sample.workspace.current_source, status: 'PENDING_POLICY_VALUE' } },
  ]) { const w: Record<string, unknown> = structuredClone(sample.workspace); mutate(w); expect(() => parseGoodPolicyDates(w, actor)).toThrow() }
  expect(() => parseGoodPolicyDates(sample.workspace, actor, { beforeVersion: '30', beforeDate: null })).toThrow()
})
it('requires real calendar dates and finite exact version strings', () => {
  expect(goodPolicyDate('2024-02-29')).toBe('2024-02-29')
  for (const date of ['', '2026-02-30', '2026-02-29', '0000-01-01', '2026-1-1', 'infinity']) expect(() => goodPolicyDate(date)).toThrow()
  for (const version of [35, true, '0', '01', '9223372036854775808']) {
    const w = { ...sample.workspace, current_source: { ...sample.workspace.current_source, version } }
    expect(() => parseGoodPolicyDates(w, actor)).toThrow()
  }
})
it('refuses unreviewed, unauthorized, unobserved and wrong-actor commands', () => {
  const w = parseGoodPolicyDates(sample.workspace, actor), p = sample.command.payload
  expect(() => prepareGoodPolicyDate(w, w.current_source.id, p.effective_from, p.reason, false, sample.command.requestId)).toThrow()
  expect(() => prepareGoodPolicyDate({ ...w, can_write: false }, w.current_source.id, p.effective_from, p.reason, true, sample.command.requestId)).toThrow()
  expect(() => prepareGoodPolicyDate(w, '00000000-0000-4000-8000-000000000099', p.effective_from, p.reason, true, sample.command.requestId)).toThrow()
  expect(() => parsePreparedGoodDate(prepared(), '00000000-0000-4000-8000-000000000099')).toThrow()
})
it('refuses a success that changes request, actor, effective date, source, version or reason', () => {
  const changes = { request_id: crypto.randomUUID(), actor: crypto.randomUUID(), effective_from: '2026-12-01',
    source_event_id: crypto.randomUUID(), source_version: '34', reason: 'OTHER REASON', id: null }
  for (const [key, value] of Object.entries(changes)) expect(() => parseGoodDateOutcome({ ...sample.outcome, [key]: value }, prepared())).toThrow()
  expect(() => parseGoodDateOutcome({ ...cancelled(), id: sample.outcome.id }, prepared())).toThrow()
  expect(() => parseGoodDateOutcome({ ...cancelled(), source_version: '0' }, prepared())).toThrow()
})
it('keeps the durable request until its exact verified reply can be retired', async () => {
  const command = prepared(); persistGoodDateRequest(scope, command)
  const rpc = vi.fn(async (_name: string, args: Record<string, unknown>) => {
    expect(readGoodDateRequest(scope, actor).pending).toEqual(command)
    expect(args).toEqual({ p_payload: command.payload, p_request: command.requestId, p_cancel: false })
    return { data: sample.outcome, error: null }
  })
  expect((await saveGoodPolicyDate({ rpc }, command)).status).toBe('SAVED')
  expect(readGoodDateRequest(scope, actor).pending).toEqual(command)
  clearGoodDateRequest(scope, command); expect(readGoodDateRequest(scope, actor).pending).toBeNull()
})
it('cancels with the original request and payload, without inventing a saved policy id or version', async () => {
  const command = prepared(), rpc = vi.fn(async () => ({ data: cancelled(), error: null }))
  expect(await saveGoodPolicyDate({ rpc }, command, true)).toEqual({ status: 'CANCELLED', id: null,
    effective_from: command.payload.effective_from, source_version: null })
  expect(rpc).toHaveBeenCalledWith('erp_cp7_save_good_policy_date_v1', {
    p_payload: command.payload, p_request: command.requestId, p_cancel: true })
})
it('retains malformed, changed and wrong-actor storage instead of overwriting or clearing it', () => {
  const command = prepared(); persistGoodDateRequest(scope, command)
  expect(() => persistGoodDateRequest(scope, command)).toThrow()
  expect(readGoodDateRequest(scope, crypto.randomUUID()).error).not.toBe('')
  const changed = { ...command, requestId: crypto.randomUUID() }
  expect(() => clearGoodDateRequest(scope, changed)).toThrow()
  expect(readGoodDateRequest(scope, actor).pending).toEqual(command)
  localStorage.setItem(goodPolicyDateRequestKey(scope), 'broken')
  expect(readGoodDateRequest(scope, actor).error).not.toBe('')
  expect(() => persistGoodDateRequest(scope, command)).toThrow()
  expect(localStorage.getItem(goodPolicyDateRequestKey(scope))).toBe('broken')
})
it('uses the two literal RPCs and preserves server errors for safe initial-refusal handling', async () => {
  const rpc = vi.fn(async () => ({ data: sample.workspace, error: null }))
  await readGoodPolicyDates({ rpc }, actor)
  expect(rpc).toHaveBeenCalledWith('erp_cp7_get_good_policy_dates_v1', { p_payload: { before_version: null, before_date: null } })
  const refusal = { code: 'P0001', message: 'NONPAYABLE_TIMELINE_STALE' }
  await expect(saveGoodPolicyDate({ rpc: async () => ({ data: null, error: refusal }) }, prepared())).rejects.toBe(refusal)
})
