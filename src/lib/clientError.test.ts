import { describe, expect, it } from 'vitest'
import { normalizeClientError } from './clientError'

describe('backend conflict messages', () => {
  it('does not claim a different rework order has already been processed', () => {
    const result = normalizeClientError({ code: '23505', message: 'duplicate key value violates unique constraint "uq_fg_lots_qc_item"' })
    expect(result.code).toBe('DATA_CONFLICT')
    expect(result.message).not.toContain('sudah pernah diproses')
    expect(result.retryable).toBe(false)
  })
  it('keeps an idempotency identity conflict distinct without claiming success', () => {
    const result = normalizeClientError({ code: 'P0001', message: 'Idempotency key reused with a different request' })
    expect(result.code).toBe('DUPLICATE_REQUEST')
    expect(result.message).not.toContain('sudah pernah diproses')
    expect(result.retryable).toBe(false)
  })
})
