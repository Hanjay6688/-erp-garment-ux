import { describe, expect, it } from 'vitest'
import { ClientAppError, normalizeClientError } from './clientError'
import { createRequestId, PendingMutationLock } from './idempotency'

const requestId = '018f7c2e-7b8a-7ab1-8d4a-1234567890ab'

describe('idempotency utilities', () => {
  it('accepts a canonical UUID generated for request_uuid', () => {
    expect(createRequestId(() => requestId)).toBe(requestId)
  })

  it('rejects a malformed request_uuid before an operation runs', async () => {
    const lock = new PendingMutationLock()
    let called = false
    await expect(lock.run('not-a-uuid', async () => { called = true }))
      .rejects.toMatchObject({ code: 'INVALID_REQUEST_ID' })
    expect(called).toBe(false)
  })

  it('blocks the same request while pending and releases it afterwards', async () => {
    const lock = new PendingMutationLock()
    let release: ((value: string) => void) | undefined
    const first = lock.run(requestId, () => new Promise<string>((resolve) => { release = resolve }))
    expect(lock.isPending(requestId)).toBe(true)
    await expect(lock.run(requestId, async () => 'duplicate'))
      .rejects.toMatchObject({ code: 'MUTATION_IN_FLIGHT' })
    release?.('done')
    await expect(first).resolves.toBe('done')
    expect(lock.isPending(requestId)).toBe(false)
  })
})

describe('client error normalization', () => {
  it('maps Data API schema and optimistic concurrency errors without leaking raw text', () => {
    expect(normalizeClientError({ code: 'PGRST106', message: 'raw internals' }))
      .toMatchObject({ code: 'PROFILE_API_SCHEMA_UNAVAILABLE', retryable: false })
    expect(normalizeClientError({ message: 'expected_version mismatch with row_version' }))
      .toMatchObject({ code: 'VERSION_CONFLICT', retryable: false })
  })

  it('preserves an intentional client error', () => {
    const source = new ClientAppError('BUSINESS_RPC_DISABLED', 'disabled')
    expect(normalizeClientError(source)).toBe(source)
  })
})
