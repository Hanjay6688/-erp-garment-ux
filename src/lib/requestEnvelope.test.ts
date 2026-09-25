import { beforeEach, describe, expect, it } from 'vitest'
import { readPendingRequest, replayPendingRequest, sendOnce } from './requestEnvelope'

type Call = { rpc: string; args: Record<string, unknown> }
function sender(results: unknown[]) {
  const calls: Call[] = []
  const send = async (rpc: string, args: Record<string, unknown>) => {
    calls.push({ rpc, args })
    const next = results.shift()
    if (next instanceof Error) throw next
    return { error: next ?? null }
  }
  return { calls, send }
}

describe('W10 / CP6-05: a write keeps its request identity until the server answers', () => {
  beforeEach(() => { globalThis.localStorage?.clear() })

  it('replays the same change after a lost answer with the same UUID', async () => {
    const { calls, send } = sender([new TypeError('Failed to fetch'), null])
    const args = { p_payload: { code: 'REG' }, p_expected_version: 3 }
    const first = await sendOnce('u1:PATTERN', 'erp_save_pattern_v1', args, send)
    expect(first).toMatchObject({ ok: false, state: 'UNKNOWN' })
    expect(readPendingRequest('u1:PATTERN').envelope).not.toBeNull()
    const second = await sendOnce('u1:PATTERN', 'erp_save_pattern_v1', { ...args }, send)
    expect(second).toEqual({ ok: true })
    expect(calls).toHaveLength(2)
    expect(calls[1].args.p_client_request_id).toBe(calls[0].args.p_client_request_id)
    expect(calls[1].args).toEqual(calls[0].args)
    expect(readPendingRequest('u1:PATTERN').envelope).toBeNull()
  })

  it('holds back a different change while one is unknown, and replays the stored one exactly', async () => {
    const { calls, send } = sender([new TypeError('Failed to fetch'), null])
    await sendOnce('u2:ACCESS', 'erp_deactivate_role_v1', { p_role_id: 'r1', p_reason: 'a', p_expected_version: 1 }, send)
    const other = await sendOnce('u2:ACCESS', 'erp_deactivate_role_v1', { p_role_id: 'r2', p_reason: 'b', p_expected_version: 1 }, send)
    expect(other).toMatchObject({ ok: false, state: 'BLOCKED' })
    expect(calls).toHaveLength(1)
    expect(await replayPendingRequest('u2:ACCESS', send)).toEqual({ ok: true })
    expect(calls[1].args).toEqual(calls[0].args)
  })

  it('forgets a request the server refused, so the next change gets a new UUID', async () => {
    const { calls, send } = sender([{ code: 'P0001', message: 'Kode Pola sudah dipakai' }, null])
    const refused = await sendOnce('u3:PATTERN', 'erp_save_pattern_v1', { p_payload: { code: 'A' } }, send)
    expect(refused).toMatchObject({ ok: false, state: 'REFUSED' })
    expect(readPendingRequest('u3:PATTERN').envelope).toBeNull()
    await sendOnce('u3:PATTERN', 'erp_save_pattern_v1', { p_payload: { code: 'B' } }, send)
    expect(calls[1].args.p_client_request_id).not.toBe(calls[0].args.p_client_request_id)
  })
})
