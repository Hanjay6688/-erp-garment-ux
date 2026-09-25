import { describe, expect, it } from 'vitest'
import { isUnansweredFailure, normalizeClientError } from './clientError'

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

describe('W11: a refusal keeps its own message', () => {
  it('shows a page parser refusal as is', () => {
    const result = normalizeClientError(new Error('Model produk bukan UUID valid.'))
    expect(result.code).toBe('REJECTED')
    expect(result.message).toBe('Model produk bukan UUID valid.')
  })
  it('shows a server business rule as is', () => {
    const result = normalizeClientError({ code: 'P0001', message: 'CLOSE_ALREADY_CLOSED: periode sudah ditutup sampai 2026-09-24' })
    expect(result.code).toBe('REJECTED')
    expect(result.message).toContain('CLOSE_ALREADY_CLOSED')
  })
  it('keeps unreachable for failures without an answer', () => {
    expect(normalizeClientError(new TypeError('fetch failed')).code).toBe('BACKEND_UNAVAILABLE')
    expect(normalizeClientError({ message: 'network unavailable', status: 503 }).code).toBe('BACKEND_UNAVAILABLE')
    expect(normalizeClientError({}).code).toBe('BACKEND_UNAVAILABLE')
    expect(isUnansweredFailure({ code: 'P0001', message: 'refused' })).toBe(false)
    expect(isUnansweredFailure(new TypeError('Failed to fetch'))).toBe(true)
  })
})
