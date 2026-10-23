// Synthetic closed-wire/state tests only; no Native source/RPC/permission proof.
import { describe, expect, it } from 'vitest'
import { acceptQuote, blankChoice, canCommit, commitIntent, emptyQuoteUi, inputIdentity, parseSettlementAccountOptions, parseSettlementOutcome, parseSettlementQuote, retireQuote, startQuote, type Quote, type QuoteInput, type ReadContext, type Unavailable } from './salesReturnSettlementContract'
const id = (n: number) => `b0000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const hash = (n: number) => String(n).repeat(64)
const at = '2026-10-19T03:02:00.000Z'
function input(): QuoteInput {
  return { sale_id: id(1), expected_version: '3', review_token: 'a'.repeat(32), return_payload: { return_number: 'RT-01', physical_at: at, notes: null, change_reason: 'Barang dan nilai diperiksa', items: [{ allocation_id: id(2), location_id: id(3), qty_pcs: '1', quality_grade: 'GRADE_A', refund_amount: '200.00', notes: null }] }, settlement: { ...blankChoice(), mode: 'CREDIT', credit_account_id: id(4) } }
}
function wire(q = input()): Quote {
  const c = q.settlement, ready = c.mode === 'CREDIT' && c.credit_account_id !== null || c.mode === 'REFUND' && !!c.credit_account_id && !!c.cash_account_id && !!c.refund_physical_at
  return { contract_version: 'cp7.sales-return-settlement-quote.v1', kind: 'QUOTE', read_only: true, business_DML: false, captured_at: '2026-10-19T04:00:00Z', input_echo: structuredClone(q),
    source: { sale_id: q.sale_id, sale_number: 'INV-01', customer_id: id(10), customer_name: 'Pelanggan uji', row_version: q.expected_version, review_token: q.review_token },
    binding: { immutable_source_sha256: hash(1), current_state_sha256: hash(2), draft_sha256: hash(3), choice_sha256: hash(4), projection_sha256: hash(5), authority_sha256: hash(6), period_sha256: hash(7), dependency_sha256: hash(8), quote_sha256: ready ? hash(9) : null },
    has_recognition_effect: true, current_credit_amount: '200.00', components: [{ component_key: hash(1), economic_date: '2026-10-19', book_date: '2026-10-19', signed_amount: '200.00', support_sha256: hash(2) }],
    return_projection: { economic_date: '2026-10-19', prior_causal: { contract_version: 'ow04.prior-causal-book-proof.v1', scope: 'PRIOR_CAUSAL_SALE_RETURN', state: 'DATED', causal_book_floor: '2026-10-18', proof_sha256: hash(6) }, journal_effect: 'JOURNAL_EXPECTED', planned_book_date: '2026-10-19', return_amount: '200.00', hpp_amount: '10.00', receivable_account_id: id(5) },
    totals: { before: { gross_total: '1000.00', return_total: '0.00', net_total: '1000.00', payments_received: '1000.00', credit_applied: '0.00', credit_recognized: '0.00', effective_paid: '1000.00', receivable_remaining: '0.00' }, after: { gross_total: '1000.00', return_total: '200.00', net_total: '800.00', payments_received: '1000.00', credit_applied: '0.00', credit_recognized: '200.00', effective_paid: '800.00', receivable_remaining: '0.00' } },
    credit_account: c.credit_account_id ? { id: c.credit_account_id, code: '2105', name: 'Kredit pelanggan uji', facts_sha256: hash(3) } : null,
    cash_account: c.cash_account_id ? { id: c.cash_account_id, code: 'BANK', name: 'Rekening uji', facts_sha256: hash(4) } : null,
    refund_projection: c.mode === 'REFUND' ? { amount: '200.00', physical_at: c.refund_physical_at, economic_date: c.refund_physical_at ? '2026-10-19' : null, book_date: c.refund_physical_at ? '2026-10-19' : null, safe_capacity: c.refund_physical_at ? '200.00' : null, capacity_sha256: c.refund_physical_at ? hash(6) : null } : null,
    capabilities: { record_return: true, recognize_credit: true, refund_cash: true }, readiness: ready ? { state: 'READY', issues: [] } : { state: 'CHOICE_REQUIRED', issues: ['CHOOSE_MODE', 'CHOOSE_CREDIT_ACCOUNT'] } }
}
function parsed(w: Quote) { const q = parseSettlementQuote(w, w.input_echo); if (q.kind !== 'QUOTE') throw Error('Expected quote'); return q }
function zeroCurrent(nonempty: boolean) {
  const q = input(); if (!nonempty) q.settlement = blankChoice()
  const w = wire(q); w.current_credit_amount = '0.00'
  w.components = nonempty ? [{ ...w.components[0] }, { ...w.components[0], component_key: hash(3), economic_date: '2026-10-20', book_date: '2026-10-20', signed_amount: '-200.00' }] : []
  w.has_recognition_effect = nonempty
  w.totals.before = { ...w.totals.before, payments_received: '0.00', effective_paid: '0.00', receivable_remaining: '1000.00' }
  w.totals.after = { ...w.totals.after, payments_received: '0.00', credit_recognized: '0.00', effective_paid: '0.00', receivable_remaining: '800.00' }
  w.readiness = { state: 'READY', issues: [] }; w.binding.quote_sha256 = hash(9)
  return w
}
function largeWire() {
  const q = input(), lineMax = '999999999999999999.99', aggregate = '1999999999999999999.98'
  q.return_payload.items[0].refund_amount = lineMax
  q.return_payload.items.push({ ...q.return_payload.items[0], allocation_id: id(7) })
  const w = wire(q)
  w.current_credit_amount = aggregate; w.components[0].signed_amount = aggregate
  w.return_projection.return_amount = aggregate
  w.totals.before = { gross_total: aggregate, return_total: '0.00', net_total: aggregate, payments_received: aggregate, credit_applied: '0.00', credit_recognized: '0.00', effective_paid: aggregate, receivable_remaining: '0.00' }
  w.totals.after = { gross_total: aggregate, return_total: aggregate, net_total: '0.00', payments_received: aggregate, credit_applied: '0.00', credit_recognized: aggregate, effective_paid: '0.00', receivable_remaining: '0.00' }
  return w
}
/** Synthetic server replies for the independently frozen PF01..PF05 matrix.
 * Book dates here are literal SERVER projection fixtures, never Native runtime
 * evidence or a client algorithm choosing a lawful book day.
 */
function priorCausalWire(state: 'DATED' | 'PROVEN_ABSENT', journal: 'JOURNAL_EXPECTED' | 'NO_JOURNAL'): any {
  const w: any = zeroCurrent(false)
  w.input_echo.return_payload.items[0].refund_amount = '0.00'
  const zeros = { gross_total: '0.00', return_total: '0.00', net_total: '0.00', payments_received: '0.00', credit_applied: '0.00', credit_recognized: '0.00', effective_paid: '0.00', receivable_remaining: '0.00' }
  w.totals = { before: { ...zeros }, after: { ...zeros } }
  w.return_projection = {
    economic_date: '2026-10-19',
    prior_causal: { contract_version: 'ow04.prior-causal-book-proof.v1', scope: 'PRIOR_CAUSAL_SALE_RETURN', state, causal_book_floor: state === 'DATED' ? '2026-10-20' : null, proof_sha256: hash(6) },
    journal_effect: journal,
    planned_book_date: journal === 'NO_JOURNAL' ? null : state === 'DATED' ? '2026-10-20' : '2026-10-19',
    return_amount: '0.00', hpp_amount: journal === 'NO_JOURNAL' ? '0.00' : '10.00', receivable_account_id: null,
  }
  return w
}
const context = (q: QuoteInput): ReadContext => ({ generation: 1, parent_ticket: 'parent-read-1', authority_scope: 'actor-profile-permissions-1', input_identity: inputIdentity(q) })
const flags = { writer_locked: false, source_stale: false, pending_envelope: false }
it('accepts a boolean false refund capability for no-credit returns and refuses SQL null', () => {
  const q = zeroCurrent(false)
  q.capabilities.refund_cash = false
  expect(parseSettlementQuote(q, q.input_echo)).toEqual(q)
  const malformed = structuredClone(q) as any
  malformed.capabilities.refund_cash = null
  expect(() => parseSettlementQuote(malformed, q.input_echo)).toThrow()
})
const receipt = (q: Quote, request = id(99)) => ({ contract_version: 'cp7.sales-return-settlement-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'RETURN_SETTLEMENT', request_id: request, sale_id: q.source.sale_id, return_id: id(11), return_status: 'POSTED', row_version: '4', family_ordinal: '1', credit_id: q.has_recognition_effect ? id(12) : null, refund_event_id: q.input_echo.settlement.mode === 'REFUND' ? id(13) : null, quote_sha256: q.binding.quote_sha256, projection_sha256: q.binding.projection_sha256, actual_manifest_sha256: hash(7), projection_actual_proof_sha256: hash(8), production_go: false })

describe('OW04 proposed quote/parser/state contract only', () => {
  it('PF01 accepts proved prior absence and a genuinely physical zero-money NO_JOURNAL return', () => {
    const w = parsed(priorCausalWire('PROVEN_ABSENT', 'NO_JOURNAL'))
    expect(w.return_projection.planned_book_date).toBeNull()
    expect(w.has_recognition_effect).toBe(false)
    const frozen = commitIntent(w).payload
    expect(frozen.document.settlement).toBeNull()
    expect(Object.keys(frozen.document)).not.toContain('prior_causal')
    expect(parseSettlementOutcome(receipt(w), id(99), frozen).credit_id).toBeNull()
  })
  it('PF02 accepts prior absence before OPENING0/freeSALE/recost10 produces a new HPP-only return journal', () => {
    const w: any = parsed(priorCausalWire('PROVEN_ABSENT', 'JOURNAL_EXPECTED'))
    expect(w.return_projection.prior_causal.causal_book_floor).toBeNull()
    expect(w.return_projection).toMatchObject({ journal_effect: 'JOURNAL_EXPECTED', return_amount: '0.00', hpp_amount: '10.00', receivable_account_id: null, planned_book_date: '2026-10-19' })
    expect(w.components).toEqual([])
    expect(commitIntent(w).payload.document.settlement).toBeNull()
    // Literal independent source arithmetic: 5 owned at10 => FG50/COGS50;
    // return1 at current10 => FG60/COGS40. Frozen SALE cost facts remain0.
  })
  it('PF03 retains a real HPP-only dated ancestor floor even when all customer money totals are zero', () => {
    const w: any = priorCausalWire('DATED', 'JOURNAL_EXPECTED')
    expect(parsed(w).return_projection.planned_book_date).toBe('2026-10-20')
    w.return_projection.planned_book_date = '2026-10-19'
    expect(() => parsed(w)).toThrow()
  })
  it('PF04 keeps the dated ancestor when recost10to0 yields a NO_JOURNAL child despite original allocation10', () => {
    const w: any = parsed(priorCausalWire('DATED', 'NO_JOURNAL'))
    expect(w.return_projection.prior_causal).toMatchObject({ state: 'DATED', causal_book_floor: '2026-10-20' })
    expect(w.return_projection).toMatchObject({ journal_effect: 'NO_JOURNAL', hpp_amount: '0.00', planned_book_date: null })
    expect(commitIntent(w).payload.document.settlement).toBeNull()
    // New current item/movement0 is distinct from the retained allocation10.
    // The closed quote does not expose or rewrite that actual source snapshot.
  })
  it.each([
    ['DATED without its real floor', (w: any) => { w.return_projection.prior_causal.state = 'DATED' }],
    ['ABSENT with an invented floor', (w: any) => { w.return_projection.prior_causal.causal_book_floor = '2026-10-18' }],
    ['missing proof digest', (w: any) => { delete w.return_projection.prior_causal.proof_sha256 }],
    ['short proof digest', (w: any) => { w.return_projection.prior_causal.proof_sha256 = 'a'.repeat(32) }],
    ['unknown source classified as absent', (w: any) => { w.return_projection.prior_causal.state = 'UNKNOWN' }],
    ['unscoped global absence', (w: any) => { w.return_projection.prior_causal.scope = 'ALL_ERP_JOURNALS' }],
  ])('rejects typed prior proof: %s', (_label, change) => {
    const w = priorCausalWire('PROVEN_ABSENT', 'NO_JOURNAL'); change(w)
    expect(() => parsed(w)).toThrow()
  })
  it('never uses net-zero current money to bypass a nonempty signed recognition plan with prior ABSENT', () => {
    const w = priorCausalWire('PROVEN_ABSENT', 'JOURNAL_EXPECTED')
    w.has_recognition_effect = true
    w.components = [{ component_key: hash(1), economic_date: '2026-10-19', book_date: '2026-10-19', signed_amount: '200.00', support_sha256: hash(2) },
      { component_key: hash(3), economic_date: '2026-10-20', book_date: '2026-10-20', signed_amount: '-200.00', support_sha256: hash(4) }]
    w.input_echo.settlement = { ...blankChoice(), mode: 'CREDIT', credit_account_id: id(4) }
    w.credit_account = { id: id(4), code: '2105', name: 'Kredit pelanggan uji', facts_sha256: hash(3) }
    expect(() => parsed(w)).toThrow()
  })
  it('refuses missing prior proof even when every current financial total is zero', () => {
    const w = priorCausalWire('PROVEN_ABSENT', 'NO_JOURNAL'); delete w.return_projection.prior_causal
    expect(() => parsed(w)).toThrow()
  })
  it('PF05 keeps incomplete or forged prior history UNAVAILABLE without a numeric or READY fallback', () => {
    const w = wire(), u: Unavailable = { contract_version: w.contract_version, kind: 'UNAVAILABLE', read_only: true, business_DML: false, captured_at: w.captured_at, input_echo: w.input_echo, source: w.source, reason: 'SOURCE_INCOMPLETE' }
    expect(parseSettlementQuote(u, w.input_echo).kind).toBe('UNAVAILABLE')
    expect(() => parseSettlementQuote({ ...u, prior_causal: { state: 'PROVEN_ABSENT' }, readiness: { state: 'READY', issues: [] } }, w.input_echo)).toThrow()
  })
  it('keeps initial mode/accounts blank and requires a quote for every return', () => {
    expect(blankChoice()).toEqual({ mode: null, credit_account_id: null, cash_account_id: null, refund_physical_at: null, reference: null })
    const q = input(); q.settlement = blankChoice(); const w = parsed(wire(q))
    expect(w.readiness.state).toBe('CHOICE_REQUIRED'); expect(() => commitIntent(w)).toThrow()
    expect(canCommit(emptyQuoteUi(), context(q), flags)).toBe(false)
  })
  it('retains original payment1000 and displays server currentK200/effective800/AR0', () => {
    const q = parsed(wire()), d = commitIntent(q).payload.document
    expect(q.current_credit_amount).toBe('200.00'); expect(q.totals.after).toMatchObject({ payments_received: '1000.00', effective_paid: '800.00', receivable_remaining: '0.00' })
    expect(d.settlement).toEqual({ mode: 'CREDIT', credit_account_id: id(4) })
    expect(Object.keys(d).sort()).toEqual(['change_reason', 'items', 'notes', 'physical_at', 'quote_sha256', 'return_number', 'review_token', 'sale_id', 'settlement'])
    expect(Object.keys(commitIntent(q).payload).sort()).toEqual(['document', 'expected_version'])
  })
  it('requires independent explicit refund time/account and sends no client settlement amount or date pair', () => {
    const q = input(); q.settlement.mode = 'REFUND'; let w = wire(q)
    expect(parsed(w).readiness.state).toBe('CHOICE_REQUIRED')
    q.settlement.cash_account_id = id(6); q.settlement.refund_physical_at = '2026-10-19T04:10:00Z'; w = parsed(wire(q))
    expect(w.refund_projection?.amount).toBe('200.00')
    const d = commitIntent(w).payload.document
    expect(d.settlement).toEqual({ mode: 'REFUND', credit_account_id: id(4), cash_account_id: id(6), refund_physical_at: '2026-10-19T04:10:00Z', reference: null })
    expect(d.physical_at).toBe(at)
    expect(Object.keys(d.settlement ?? {})).not.toContain('amount'); expect(JSON.stringify(d)).not.toMatch(/economic_date|book_date|journal_id|components|lines/)
  })
  it('requires explicit account/cohort for nonempty +200/-200 even when currentK is zero', () => {
    const w = zeroCurrent(true); expect(parsed(w).has_recognition_effect).toBe(true)
    expect(commitIntent(parsed(w)).payload.document.settlement).toEqual({ mode: 'CREDIT', credit_account_id: id(4) })
    w.input_echo.settlement = blankChoice(); w.credit_account = null
    expect(() => parsed(w)).toThrow()
    w.readiness = { state: 'CHOICE_REQUIRED', issues: ['CHOOSE_MODE', 'CHOOSE_CREDIT_ACCOUNT'] }; w.binding.quote_sha256 = null
    expect(parsed(w).current_credit_amount).toBe('0.00'); expect(() => commitIntent(w)).toThrow()
  })
  it('accepts genuinely empty ordinary returns only after quote, including NO_JOURNAL zeroR/zeroHPP', () => {
    const w = parsed(zeroCurrent(false)); expect(commitIntent(w).payload.document.settlement).toBeNull()
    const z = zeroCurrent(false); z.input_echo.return_payload.items[0].refund_amount = '0.00'
    z.return_projection = { ...z.return_projection, journal_effect: 'NO_JOURNAL', planned_book_date: null, receivable_account_id: null, return_amount: '0.00', hpp_amount: '0.00' }
    z.totals.after = structuredClone(z.totals.before)
    expect(parsed(z).return_projection.planned_book_date).toBeNull()
    expect(parseSettlementOutcome(receipt(z), id(99), commitIntent(z).payload).credit_id).toBeNull()
  })
  it.each(['JOURNAL_EXPECTED', 'NO_JOURNAL'] as const)('refuses READY DATED %s without the independently proved causal floor', effect => {
    const w = effect === 'JOURNAL_EXPECTED' ? wire() : zeroCurrent(false)
    if (effect === 'NO_JOURNAL') {
      w.input_echo.return_payload.items[0].refund_amount = '0.00'
      w.return_projection = { ...w.return_projection, journal_effect: 'NO_JOURNAL', planned_book_date: null, receivable_account_id: null, return_amount: '0.00', hpp_amount: '0.00' }
      w.totals.after = structuredClone(w.totals.before)
    }
    ;(w.return_projection.prior_causal as any).causal_book_floor = null
    expect(() => parsed(w)).toThrow()
  })
  it('accepts exact server aggregate/currentK/component amounts above one Native journal line', () => {
    const w = parsed(largeWire())
    expect(w.current_credit_amount).toBe('1999999999999999999.98')
    expect(w.totals.before.payments_received).toBe('1999999999999999999.98')
    expect(commitIntent(w).payload.document.settlement).toEqual({ mode: 'CREDIT', credit_account_id: id(4) })
  })
  it('retains exact large signed cancellation with a nonempty zero-current cohort', () => {
    const w = largeWire(); w.current_credit_amount = '0.00'
    w.components.push({ ...w.components[0], component_key: hash(3), economic_date: '2026-10-20', book_date: '2026-10-20', signed_amount: '-1999999999999999999.98' })
    w.totals.before = { ...w.totals.before, payments_received: '0.00', effective_paid: '0.00', receivable_remaining: '1999999999999999999.98' }
    w.totals.after = { ...w.totals.after, payments_received: '0.00', credit_recognized: '0.00' }
    expect(parsed(w).has_recognition_effect).toBe(true)
    expect(commitIntent(w).payload.document.settlement).not.toBeNull()
  })
  it('rejects a one-cent component mismatch above JavaScript safe integer range', () => {
    const w = largeWire(); w.current_credit_amount = '1999999999999999999.97'
    expect(() => parsed(w)).toThrow()
  })
  it('preserves the existing Native bound on each user return refund input', () => {
    const w = wire(); w.input_echo.return_payload.items[0].refund_amount = '1000000000000000000.00'
    expect(() => parsed(w)).toThrow()
  })
  it.each(['COMPONENT', 'RETURN', 'REFUND'] as const)('rejects READY %s book date before its own economic date', kind => {
    const q = input()
    if (kind === 'REFUND') q.settlement = { ...q.settlement, mode: 'REFUND', cash_account_id: id(6), refund_physical_at: '2026-10-19T04:10:00Z' }
    const w = wire(q)
    if (kind === 'COMPONENT') w.components[0].book_date = '2026-10-18'
    if (kind === 'RETURN') w.return_projection.planned_book_date = '2026-10-18'
    if (kind === 'REFUND') w.refund_projection!.book_date = '2026-10-18'
    expect(() => parsed(w)).toThrow()
  })
  it.each(['2026-10-19T17:05:00Z', '2026-10-20T00:05:00+07:00'])('rejects an economic return date guessed from UTC for %s', physical => {
    const q = input(); q.return_payload.physical_at = physical
    const w = wire(q); w.return_projection.planned_book_date = '2026-10-20'
    expect(() => parsed(w)).toThrow()
  })
  it.each(['2026-10-19T17:05:00Z', '2026-10-20T00:05:00+07:00'])('accepts WIB date for %s and preserves earlier historical component dates', physical => {
    const q = input(); q.return_payload.physical_at = physical
    const w = wire(q); w.return_projection.economic_date = '2026-10-20'; w.return_projection.planned_book_date = '2026-10-20'
    expect(parsed(w).return_projection.economic_date).toBe('2026-10-20')
    expect(w.components[0]).toMatchObject({ economic_date: '2026-10-19', book_date: '2026-10-19' })
    expect(commitIntent(w).payload.document.physical_at).toBe(physical)
  })
  it('binds the independent refund economic date to its explicit WIB physical instant', () => {
    const q = input(); q.settlement = { ...q.settlement, mode: 'REFUND', cash_account_id: id(6), refund_physical_at: '2026-10-19T17:10:00Z' }
    const w = wire(q); w.refund_projection!.book_date = '2026-10-20'
    expect(() => parsed(w)).toThrow()
    w.refund_projection!.economic_date = '2026-10-20'
    expect(parsed(w).return_projection.economic_date).toBe('2026-10-19')
    expect(w.refund_projection!.economic_date).toBe('2026-10-20')
  })
  it.each([
    ['numeric money', (w: any) => { w.current_credit_amount = 200 }],
    ['unknown key', (w: any) => { w.unreviewed_amount = '200.00' }],
    ['missing key', (w: any) => { delete w.binding.period_sha256 }],
    ['short hash', (w: any) => { w.binding.quote_sha256 = 'a'.repeat(32) }],
    ['wrong source version', (w: any) => { w.source.row_version = '4' }],
    ['changed draft echo', (w: any) => { w.input_echo.return_payload.notes = 'changed' }],
    ['component sum mismatch', (w: any) => { w.components[0].signed_amount = '100.00' }],
    ['duplicate pair', (w: any) => { w.components.push({ ...w.components[0], component_key: hash(4), signed_amount: '-200.00' }) }],
    ['negative zero', (w: any) => { w.components[0].signed_amount = '-0.00' }],
    ['invalid calendar day', (w: any) => { w.components[0].economic_date = '2026-02-30' }],
    ['contradictory paid label', (w: any) => { w.totals.after.effective_paid = '1000.00' }],
    ['NO_JOURNAL with invented book date', (w: any) => { w.return_projection.journal_effect = 'NO_JOURNAL' }],
  ])('rejects %s', (_label, change) => { const expected = input(), w = wire(expected); change(w); expect(() => parseSettlementQuote(w, expected)).toThrow() })
  it('never turns unavailable lineage into an empty/zero quote', () => {
    const w = wire(), unavailable: Unavailable = { contract_version: w.contract_version, kind: 'UNAVAILABLE', read_only: true, business_DML: false, captured_at: w.captured_at, input_echo: w.input_echo, source: w.source, reason: 'SOURCE_FAMILY_AMBIGUOUS' }
    expect(parseSettlementQuote(unavailable, w.input_echo).kind).toBe('UNAVAILABLE')
    expect(() => parseSettlementQuote({ ...unavailable, current_credit_amount: '0.00' }, w.input_echo)).toThrow()
    const c = context(w.input_echo), ui = acceptQuote(startQuote(c), c, c, unavailable)
    expect(canCommit({ ...ui, reviewed: true }, c, flags)).toBe(false)
  })
  it.each(['generation', 'parent_ticket', 'authority_scope', 'input_identity'] as const)('rejects an old quote after %s changes', key => {
    const q = parsed(wire()), c = context(q.input_echo), current = { ...c, [key]: key === 'generation' ? 2 : 'changed' }
    const waiting = startQuote(current)
    expect(acceptQuote(waiting, c, current, q)).toBe(waiting)
    const fresh = { ...acceptQuote(startQuote(c), c, c, q), reviewed: true }
    expect(canCommit(fresh, current, flags)).toBe(false)
    expect(retireQuote().reply).toBeNull()
  })
  it('requires explicit review and blocks all pending/lost-reply writers without replacing the envelope', () => {
    const q = parsed(wire()), c = context(q.input_echo), ui = acceptQuote(startQuote(c), c, c, q)
    expect(canCommit(ui, c, flags)).toBe(false)
    expect(canCommit({ ...ui, reviewed: true }, c, flags)).toBe(true)
    expect(canCommit({ ...ui, reviewed: true }, c, { ...flags, pending_envelope: true })).toBe(false)
    const frozen = commitIntent(q), stored = JSON.stringify(frozen)
    q.input_echo.return_payload.notes = 'Later edit must not rewrite the uncertain intent'
    expect(JSON.stringify(frozen)).toBe(stored)
    expect(retireQuote('ACCESS_DENIED')).toEqual({ phase: 'ACCESS_DENIED', context: null, reply: null, reviewed: false })
  })
  it('refuses READY claims after current record/recognition/refund capability is lost', () => {
    for (const permission of ['record_return', 'recognize_credit'] as const) { const w = wire(); w.capabilities[permission] = false; expect(() => parsed(w)).toThrow() }
    const i = input(); i.settlement = { ...i.settlement, mode: 'REFUND', cash_account_id: id(6), refund_physical_at: '2026-10-19T04:10:00Z' }
    const w = wire(i); w.capabilities.refund_cash = false; expect(() => parsed(w)).toThrow()
    w.capabilities.refund_cash = true; w.refund_projection!.safe_capacity = '100.00'; expect(() => parsed(w)).toThrow()
  })
  it('validates receipt after reload from the unchanged envelope without the in-memory quote', () => {
    const q = parsed(wire()), persisted = JSON.parse(JSON.stringify(commitIntent(q).payload)), answer = receipt(q)
    expect(parseSettlementOutcome(answer, id(99), persisted).actual_manifest_sha256).not.toBe(q.binding.projection_sha256)
    expect(() => parseSettlementOutcome({ ...answer, quote_sha256: hash(6) }, id(99), persisted)).toThrow()
    expect(() => parseSettlementOutcome(answer, id(98), persisted)).toThrow()
    expect(() => parseSettlementOutcome({ ...answer, projection_actual_proof_sha256: 'a'.repeat(32) }, id(99), persisted)).toThrow()
  })
  it('keeps account pagination typed and does not select the first server-vetted account', () => {
    const w = wire(), expected = { kind: 'ACCOUNT_OPTIONS' as const, sale_id: w.source.sale_id, expected_version: w.source.row_version, review_token: w.source.review_token, account_kind: 'CREDIT' as const, q: '', offset: 0, limit: 25 as const }
    const options = { contract_version: 'cp7.sales-return-settlement-options.v1', kind: 'ACCOUNT_OPTIONS', read_only: true, business_DML: false, captured_at: w.captured_at, source: w.source, account_kind: 'CREDIT', q: '', rows: [w.credit_account], total: '1', offset: 0, limit: 25, next_offset: null }
    expect(parseSettlementAccountOptions(options, expected).rows).toHaveLength(1)
    expect(blankChoice().credit_account_id).toBeNull()
    expect(() => parseSettlementAccountOptions({ ...options, next_offset: 1 }, expected)).toThrow()
  })
})
