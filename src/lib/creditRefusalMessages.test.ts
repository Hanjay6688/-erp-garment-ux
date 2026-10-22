import { describe, expect, it } from 'vitest'
import { normalizeClientError } from './clientError'
import { creditRefusalMessage, parseCreditRefusalDetail, serverRefusalCode } from './creditRefusalMessages'

// The exact jsonb::text form cp7_credit_followups.detail_v1 returns (PostgreSQL orders jsonb keys by length, then bytes).
const pg = (refusal: string, action: string | null, reasons: string[], blockers: string[] = []) =>
  `{"action": ${action === null ? 'null' : `"${action}"`}, "reasons": [${reasons.map(x => `"${x}"`).join(', ')}], "refusal": "${refusal}", `
  + `"contract": "cp7.credit-followups.refusal.v1", "source_blockers": [${blockers.map(x => `"${x}"`).join(', ')}]}`
const INITIAL = 'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'
const REGISTERED = 'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION'
const CORRECTION = 'CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED'
const GENERIC = 'belum dapat diperiksa'

describe('OW-04b part 3: retained credit refusals name the reason and the next step', () => {
  it.each([
    ['PRIOR_CREDIT_RETURN', 'sudah punya retur yang menjadi saldo kredit pelanggan atau uang kembali'],
    ['CREDIT_APPLIED_TO_INVOICE', 'pernah dibayar memakai saldo kredit pelanggan'],
    ['NOTE_REVISED', 'pernah dibetulkan lewat Benerin nota'],
    ['RETURN_CORRECTED', 'pernah dibetulkan lewat Edit retur'],
  ])('a return on an invoice with %s says why and what to do next', (reason, why) => {
    const text = creditRefusalMessage(INITIAL, pg('INITIAL_SOURCE_FAMILY', null, [reason]))!
    expect(text).toContain('Retur ini belum bisa dicatat dan diselesaikan (uang kembali atau saldo kredit) pada invoice ini.')
    expect(text).toContain('Alasannya: ')
    expect(text).toContain(why)
    expect(text).toContain('Langkah berikutnya:')
    expect(text).toContain('butir OW-04b')
    expect(text).toContain('riwayat kredit tetap disimpan')
    expect(text).toContain('beri tahu admin')
    expect(text).not.toContain(GENERIC)
  })
  it('lists every true reason and the admin check codes of a blocked source history', () => {
    const text = creditRefusalMessage(INITIAL, pg('INITIAL_SOURCE_FAMILY', null, ['SOURCE_HISTORY_BLOCKED', 'PRIOR_CREDIT_RETURN'],
      ['AR_MAPPING_OR_ACCOUNT_CHANGED', 'RESTATEMENT_PRECEDES_ORIGINAL_BOOK']))!
    expect(text).toContain('riwayat jurnal invoice ini belum lengkap atau tidak cocok dengan dokumennya; invoice ini sudah punya retur')
    expect(text).toContain('kode pemeriksaan AR_MAPPING_OR_ACCOUNT_CHANGED, RESTATEMENT_PRECEDES_ORIGINAL_BOOK')
    expect(text).toContain('butir OW-04b')
  })
  it.each([
    ['PAYMENT', 'Pembayaran baru belum bisa dicatat pada invoice ini.', 'CREDIT_APPLIED_TO_INVOICE'],
    ['RETURN_REVERSE', 'Retur pada invoice ini belum bisa diubah lewat Edit retur, Benerin nota, atau pembatalan berantai.', 'PRIOR_CREDIT_RETURN'],
    ['SALE_REVERSE', 'Nota ini belum bisa dibetulkan (Benerin nota) atau dibatalkan.', 'PRIOR_CREDIT_RETURN'],
    ['PAYMENT_REVERSE', 'Pembayaran invoice ini belum bisa dibatalkan lewat Benerin nota atau pembatalan berantai.', 'CREDIT_APPLIED_TO_INVOICE'],
  ])('a %s reaching the Native writer on an invoice in credit names the screen action', (action, header, reason) => {
    const text = creditRefusalMessage(REGISTERED, pg('REGISTERED_SOURCE_MUTATION', action, [reason]))!
    expect(text.startsWith(header)).toBe(true)
    expect(text).toContain('Langkah berikutnya:')
  })
  it('names a note or return correction under credit', () => {
    expect(creditRefusalMessage(CORRECTION, pg('SOURCE_CORRECTION', null, ['NOTE_REVISED', 'RETURN_CORRECTED'])))
      .toContain('invoice ini pernah dibetulkan lewat Benerin nota, atau merupakan nota penggantinya; ada retur pada invoice ini yang pernah dibetulkan lewat Edit retur')
  })
  it('asks to report the code for an unclassified history, never a guessed reason', () => {
    const text = creditRefusalMessage(INITIAL, pg('INITIAL_SOURCE_FAMILY', null, ['UNCLASSIFIED']))!
    expect(text).toContain('riwayat invoice ini belum bisa dicocokkan')
    expect(text).toContain(`beri tahu admin dengan kode ${INITIAL}`)
    expect(text).not.toContain('butir OW-04b')
  })
})

describe('the detail is parsed strictly (fail closed)', () => {
  const good = JSON.parse(pg('INITIAL_SOURCE_FAMILY', null, ['PRIOR_CREDIT_RETURN'])) as Record<string, unknown>
  it('accepts exactly the server shape', () => {
    expect(parseCreditRefusalDetail(JSON.stringify(good), 'INITIAL_SOURCE_FAMILY')).toEqual({kind:'INITIAL_SOURCE_FAMILY', action:null, reasons:['PRIOR_CREDIT_RETURN'], sourceBlockers:[]})
  })
  it.each([
    ['missing detail', undefined],
    ['not JSON', '{reasons'],
    ['extra key', JSON.stringify({...good, hint:'x'})],
    ['missing key', JSON.stringify({...good, source_blockers:undefined})],
    ['other contract', JSON.stringify({...good, contract:'cp7.other.v1'})],
    ['other refusal kind', JSON.stringify({...good, refusal:'SOURCE_CORRECTION'})],
    ['action on a return', JSON.stringify({...good, action:'PAYMENT'})],
    ['unknown reason', JSON.stringify({...good, reasons:['SOMETHING_ELSE']})],
    ['reason of another refusal', JSON.stringify({...good, refusal:'SOURCE_CORRECTION', reasons:['PRIOR_CREDIT_RETURN']})],
    ['empty reasons', JSON.stringify({...good, reasons:[]})],
    ['duplicate reason', JSON.stringify({...good, reasons:['PRIOR_CREDIT_RETURN', 'PRIOR_CREDIT_RETURN']})],
    ['unclassified with another reason', JSON.stringify({...good, reasons:['UNCLASSIFIED', 'PRIOR_CREDIT_RETURN']})],
    ['blocker without blocked history', JSON.stringify({...good, source_blockers:['AR_MAPPING_OR_ACCOUNT_CHANGED']})],
    ['blocker that is not a code', JSON.stringify({...good, reasons:['SOURCE_HISTORY_BLOCKED'], source_blockers:['<b>x</b>']})],
  ])('refuses %s and shows the code to report instead of a reason', (_label, detail) => {
    expect(parseCreditRefusalDetail(detail, 'INITIAL_SOURCE_FAMILY')).toBeNull()
    const text = creditRefusalMessage(INITIAL, detail)!
    expect(text).toContain('Alasan rinci dari server tidak dapat dibaca.')
    expect(text).toContain(`beri tahu admin dengan kode ${INITIAL}`)
    expect(text).not.toContain('Alasannya:')
  })
  it('requires a known action on a Native writer refusal', () => {
    expect(parseCreditRefusalDetail(pg('REGISTERED_SOURCE_MUTATION', null, ['PRIOR_CREDIT_RETURN']), 'REGISTERED_SOURCE_MUTATION')).toBeNull()
    expect(parseCreditRefusalDetail(pg('REGISTERED_SOURCE_MUTATION', 'DELETE', ['PRIOR_CREDIT_RETURN']), 'REGISTERED_SOURCE_MUTATION')).toBeNull()
  })
})

describe('other refusals of the return settlement and the shared client error path', () => {
  it('maps the settlement refusals a user can act on', () => {
    expect(creditRefusalMessage('CP7_SALES_REVIEW_CHANGED', null)).toBe('Invoice berubah sejak dibuka. Muat ulang invoice, lalu periksa lagi.')
    expect(creditRefusalMessage('AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION', null)).toContain('Kurangi jumlah PCS')
    expect(creditRefusalMessage('CP7_CREDIT_LIABILITY_RECONCILIATION_FAILED', null)).toContain('Pilih akun lain')
    expect(creditRefusalMessage('CP7_CREDIT_HPP_TARGET_BOOK_NOT_RECONCILED', null)).toContain('kode CP7_CREDIT_HPP_TARGET_BOOK_NOT_RECONCILED')
    expect(creditRefusalMessage('CP7_CREDIT_SOMETHING_NEW', null)).toBe('Permintaan ini ditolak oleh pemeriksaan saldo kredit (kode CP7_CREDIT_SOMETHING_NEW). '
      + 'Muat ulang invoice dan periksa lagi; bila tetap muncul, beri tahu admin dengan kode CP7_CREDIT_SOMETHING_NEW.')
  })
  it('leaves other codes and free text to their own mappers', () => {
    expect(creditRefusalMessage('CP7_CASH_NEGATIVE: saldo Bank (B1) menjadi minus -200.00', null)).toBeNull()
    expect(creditRefusalMessage('PRIVATE SQL secret', null)).toBeNull()
    expect(creditRefusalMessage(undefined, null)).toBeNull()
    expect(serverRefusalCode('CP7_X_Y')).toBe('CP7_X_Y')
    expect(serverRefusalCode('PRIVATE SQL secret')).toBeNull()
  })
  it('normalizeClientError shows the named refusal on save screens (Edit retur, Benerin nota, payment, settlement)', () => {
    const e = normalizeClientError({code:'P0001', message:REGISTERED, details:pg('REGISTERED_SOURCE_MUTATION', 'RETURN_REVERSE', ['PRIOR_CREDIT_RETURN'])})
    expect(e.code).toBe('REJECTED')
    expect(e.message.startsWith('Retur pada invoice ini belum bisa diubah lewat Edit retur')).toBe(true)
    expect(e.message).toContain('Langkah berikutnya:')
    expect(normalizeClientError({code:'P0001', message:INITIAL, details:pg('INITIAL_SOURCE_FAMILY', null, ['PRIOR_CREDIT_RETURN'])}).message).not.toContain(INITIAL)
  })
  it('keeps the existing consumer texts, access, cash and transport outcomes unchanged', () => {
    expect(normalizeClientError({code:'P0001', message:'CP7_CREDIT_CONSUMER_REVIEW_CHANGED'}).message).toBe('Saldo, invoice tujuan, rekening, atau hak akses berubah. Muat ulang invoice lalu periksa kembali transaksi kredit.')
    expect(normalizeClientError({code:'42501', message:'CP7_CREDIT_ACCESS_CHANGED'}).code).toBe('FORBIDDEN')
    expect(normalizeClientError({code:'P0001', message:'CP7_CASH_NEGATIVE: saldo Bank (B1) menjadi minus -200.00 pada tanggal 2026-10-21 atau sesudahnya (tanggal ekonomi). Kas/bank tidak boleh minus; catat dulu uang masuk atau pilih rekening lain.'}).message)
      .toBe('Saldo Bank (B1) menjadi minus -200.00 pada tanggal 2026-10-21 atau sesudahnya (tanggal ekonomi). Kas/bank tidak boleh minus; catat dulu uang masuk atau pilih rekening lain.')
    expect(normalizeClientError(new TypeError('Failed to fetch')).code).toBe('BACKEND_UNAVAILABLE')
  })
})
