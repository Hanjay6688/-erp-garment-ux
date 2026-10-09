import { describe, expect, it } from 'vitest'
import { isUnansweredFailure, normalizeClientError } from './clientError'

describe('backend conflict messages', () => {
  it('explains note corrections refused for a re-priced returned line or a reallocated payment', () => {
    expect(normalizeClientError({ code: 'P0001', message: 'CP7_NOTE_RETURNED_LINE_PRICE_CHANGED' }).message).toContain('Betulkan atau batalkan returnya dulu')
    expect(normalizeClientError({ code: 'P0001', message: 'CP7_NOTE_REALLOCATED_PAYMENT_REVIEW_REQUIRED' }).message).toContain('koreksi pembayaran')
  })
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

describe('owning miscellaneous correction refusals', () => {
  it('gives the operator the next action after a stale review, changed options, already-corrected source or posted draft', () => {
    for (const [message, next] of [['CP7_MISC_REVIEW_CHANGED', 'Muat ulang'], ['CP7_MISC_OPTIONS_CHANGED', 'pilih kembali'], ['CP7_MISC_ALREADY_CORRECTED', 'dokumen pengganti'], ['CP7_MISC_DRAFT_ONLY', 'koreksi transaksi tercatat']]) {
      const result = normalizeClientError({ code: 'P0001', message }); expect(result.code).toBe('REJECTED'); expect(result.retryable).toBe(false); expect(result.message).toContain(next)
    }
  })
  it('keeps authorization and uncertain transport failures distinct from business correction refusals', () => {
    expect(normalizeClientError({ code: '42501', message: 'CP7_MISC_ACCESS_CHANGED' }).code).toBe('FORBIDDEN')
    expect(normalizeClientError({ code: 'P0001', message: 'CP7_MISC_REQUEST_CHANGED' }).message).toContain('hasil permintaan sebelumnya')
    expect(normalizeClientError(new TypeError('Failed to fetch')).code).toBe('BACKEND_UNAVAILABLE')
  })
})

describe('plan v2 refusals from a dated snapshot', () => {
  it('states the numbers the server sent and asks for a review, never a retry', () => {
    const e = normalizeClientError({ code: '40001', message: 'CP7_PLAN_V2_CAPACITY_USED', details: JSON.stringify({ capacity_now_pcs: '12', capacity_used_by_other_plans_pcs: '48', selected_new_pcs: '20' }) })
    expect([e.code, e.retryable, e.message]).toEqual(['REJECTED', false, 'Kapasitas potong tersisa 12 pcs (rencana lain memakai 48 pcs), rencana 20 pcs. Tinjau ulang rencana.'])
  })
  it('says the same for an earlier-analysis plan refused under the shared capacity lock', () => {
    const e = normalizeClientError({ code: '40001', message: 'CP7_PLAN_CAPACITY_USED', details: JSON.stringify({ capacity_now_pcs: '1', capacity_used_by_other_plans_pcs: '59', selected_new_pcs: '2' }) })
    expect([e.code, e.retryable, e.message]).toEqual(['REJECTED', false, 'Kapasitas potong tersisa 1 pcs (rencana lain memakai 59 pcs), rencana 2 pcs. Tinjau ulang rencana.'])
  })
  it('keeps a plain sentence when the numbers are missing or not numbers', () => {
    expect(normalizeClientError({ code: '40001', message: 'CP7_PLAN_V2_NEED_CHANGED', details: 'not json' }).message).toBe('Kebutuhan sudah berubah sejak data diambil. Tinjau ulang rencana.')
    expect(normalizeClientError({ code: '40001', message: 'CP7_PLAN_V2_NEED_CHANGED', details: JSON.stringify({ need_now_pcs: 'x', selected_new_pcs: '2' }) }).message).toBe('Kebutuhan sudah berubah sejak data diambil. Tinjau ulang rencana.')
  })
  it('leaves any other 40001 as the generic retryable conflict', () => {
    expect(normalizeClientError({ code: '40001', message: 'could not serialize access' }).code).toBe('RETRYABLE_CONFLICT')
  })
})
