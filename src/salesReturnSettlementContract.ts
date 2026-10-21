/** UNINSTALLED PROPOSAL. No RPC/Native writer is implemented by this file.
 * Monetary calculations and permission decisions belong to the server.
 * Cent sums below only reject contradictory wire data; they never derive K.
 */
export type ReturnItem = { allocation_id: string; location_id: string; qty_pcs: string; quality_grade: 'GRADE_A' | 'GRADE_B' | 'HOLD'; refund_amount: string; notes: string | null }
export type ReturnDraft = { return_number: string; physical_at: string; notes: string | null; items: ReturnItem[]; change_reason: string }
export type DraftChoice = { mode: 'CREDIT' | 'REFUND' | null; credit_account_id: string | null; cash_account_id: string | null; refund_physical_at: string | null; reference: string | null }
export const blankChoice = (): DraftChoice => ({ mode: null, credit_account_id: null, cash_account_id: null, refund_physical_at: null, reference: null })
export type QuoteInput = { sale_id: string; expected_version: string; review_token: string; return_payload: ReturnDraft; settlement: DraftChoice }
export type Source = { sale_id: string; sale_number: string; customer_id: string; customer_name: string; row_version: string; review_token: string }
export type AccountProof = { id: string; code: string; name: string; facts_sha256: string }
export type Totals = { gross_total: string; return_total: string; net_total: string; payments_received: string; credit_applied: string; credit_recognized: string; effective_paid: string; receivable_remaining: string }
export type Component = { component_key: string; economic_date: string; book_date: string; signed_amount: string; support_sha256: string }
/** Proposed public summary of the COMPLETE private prior-source proof.
 * Its digest is sealed into the server quote; syntax here grants no authority.
 * It describes existing causal history, independently of the new journal.
 */
export type PriorCausalProof = {
  contract_version: 'ow04.prior-causal-book-proof.v1'; scope: 'PRIOR_CAUSAL_SALE_RETURN'; proof_sha256: string
} & ({ state: 'DATED'; causal_book_floor: string } | { state: 'PROVEN_ABSENT'; causal_book_floor: null })
export type Binding = { immutable_source_sha256: string; current_state_sha256: string; draft_sha256: string; choice_sha256: string; projection_sha256: string; authority_sha256: string; period_sha256: string; dependency_sha256: string; quote_sha256: string | null }
export const issueCodes = ['CHOOSE_MODE', 'CHOOSE_CREDIT_ACCOUNT', 'CHOOSE_REFUND_ACCOUNT', 'ENTER_REFUND_TIME', 'CLEAR_UNNEEDED_SETTLEMENT', 'REFUND_ZERO_CURRENT_AMOUNT', 'REFUND_EXCEEDS_DATED_CAPACITY', 'CREDIT_ACCOUNT_INELIGIBLE', 'CASH_ACCOUNT_INELIGIBLE', 'RETURN_PERMISSION_REQUIRED', 'RECOGNITION_PERMISSION_REQUIRED', 'REFUND_PERMISSION_REQUIRED', 'DEPENDENCY_BLOCKED', 'PERIOD_CHANGED'] as const
export type Issue = typeof issueCodes[number]
export const unavailableCodes = ['SOURCE_FAMILY_UNSUPPORTED', 'SOURCE_FAMILY_AMBIGUOUS', 'SOURCE_INCOMPLETE', 'SOURCE_RECONCILIATION_FAILED', 'PLAN_LIMIT_EXCEEDED'] as const
export type Quote = {
  contract_version: 'cp7.sales-return-settlement-quote.v1'; kind: 'QUOTE'; read_only: true; business_DML: false; captured_at: string
  input_echo: QuoteInput; source: Source; binding: Binding
  has_recognition_effect: boolean; current_credit_amount: string; components: Component[]
  return_projection: { economic_date: string; prior_causal: PriorCausalProof; journal_effect: 'JOURNAL_EXPECTED' | 'NO_JOURNAL'; planned_book_date: string | null; return_amount: string; hpp_amount: string; receivable_account_id: string | null }
  totals: { before: Totals; after: Totals }; credit_account: AccountProof | null; cash_account: AccountProof | null
  refund_projection: { amount: string; physical_at: string | null; economic_date: string | null; book_date: string | null; safe_capacity: string | null; capacity_sha256: string | null } | null
  capabilities: { record_return: boolean; recognize_credit: boolean; refund_cash: boolean }
  readiness: { state: 'CHOICE_REQUIRED' | 'READY' | 'BLOCKED'; issues: Issue[] }
}
export type Unavailable = { contract_version: Quote['contract_version']; kind: 'UNAVAILABLE'; read_only: true; business_DML: false; captured_at: string; input_echo: QuoteInput; source: Source; reason: typeof unavailableCodes[number] }
export type QuoteReply = Quote | Unavailable

const fail = (): never => { throw Error('Perhitungan penyelesaian retur berubah atau belum lengkap. Periksa ulang sumber retur.') }
const text = (v: unknown): v is string => typeof v === 'string'
const nonblank = (v: unknown): v is string => text(v) && v.trim().length > 0
const uuid = (v: unknown): v is string => text(v) && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const sha = (v: unknown): v is string => text(v) && /^[0-9a-f]{64}$/.test(v)
const revision = (v: unknown): v is string => text(v) && /^[1-9][0-9]{0,18}$/.test(v) && BigInt(v) <= 9223372036854775807n
const oldReview = (v: unknown): v is string => text(v) && /^[0-9a-f]{32}$/.test(v)
const stamp = (v: unknown): v is string => text(v) && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
const day = (v: unknown): v is string => text(v) && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v
const wibDayFormatter = new Intl.DateTimeFormat('en', { timeZone: 'Asia/Jakarta', calendar: 'gregory', numberingSystem: 'latn', year: 'numeric', month: '2-digit', day: '2-digit' })
/** Wire consistency for explicit new-return/refund instants, never a book-date selector. */
function wibDay(physical: string): string {
  const parts = wibDayFormatter.formatToParts(new Date(physical))
  const part = (kind: 'year' | 'month' | 'day') => parts.find(p => p.type === kind)?.value ?? fail()
  return `${part('year').padStart(4, '0')}-${part('month')}-${part('day')}`
}
const money = (v: unknown): v is string => text(v) && /^(0|[1-9][0-9]*)\.\d{2}$/.test(v)
const signed = (v: unknown): v is string => text(v) && /^-?(0|[1-9][0-9]*)\.\d{2}$/.test(v) && v !== '-0.00'
// Existing Native line-input bound; never apply it to server totals or 2D atoms.
const nativeReturnMoney = (v: unknown): v is string => text(v) && /^(0|[1-9][0-9]{0,17})\.\d{2}$/.test(v)
const cents = (v: string) => { const n = v.startsWith('-'), [a, b] = (n ? v.slice(1) : v).split('.'); return (BigInt(a) * 100n + BigInt(b)) * (n ? -1n : 1n) }
const nullable = (v: unknown, check: (x: unknown) => boolean) => v === null || check(v)
function closed(v: unknown, keys: readonly string[]): Record<string, unknown> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return fail()
  const r = v as Record<string, unknown>
  if (Object.keys(r).length !== keys.length || keys.some(k => !Object.hasOwn(r, k))) fail()
  return r
}
/** Local identity only. This is not the server's cryptographic JSON protocol. */
export function inputIdentity(v: unknown): string {
  const sort = (x: unknown): unknown => Array.isArray(x) ? x.map(sort) : x && typeof x === 'object'
    ? Object.fromEntries(Object.entries(x).sort(([a], [b]) => a.localeCompare(b)).map(([k, value]) => [k, sort(value)])) : x
  return JSON.stringify(sort(v))
}
export function parseQuoteInput(v: unknown): QuoteInput {
  const r = closed(v, ['sale_id', 'expected_version', 'review_token', 'return_payload', 'settlement'])
  if (!uuid(r.sale_id) || !revision(r.expected_version) || !oldReview(r.review_token)) fail()
  const d = closed(r.return_payload, ['return_number', 'physical_at', 'notes', 'items', 'change_reason'])
  if (!nonblank(d.return_number) || d.return_number.length > 60 || !stamp(d.physical_at) || !nullable(d.notes, x => text(x) && x.length <= 2000)
    || !text(d.change_reason) || d.change_reason.trim().length < 5 || d.change_reason.length > 1000 || !Array.isArray(d.items) || d.items.length < 1 || d.items.length > 100) return fail()
  const seen = new Set<string>()
  for (const value of d.items) {
    const i = closed(value, ['allocation_id', 'location_id', 'qty_pcs', 'quality_grade', 'refund_amount', 'notes'])
    if (!uuid(i.allocation_id) || !uuid(i.location_id) || seen.has(i.allocation_id) || !text(i.qty_pcs) || !/^[1-9][0-9]{0,8}$/.test(i.qty_pcs)
      || !['GRADE_A', 'GRADE_B', 'HOLD'].includes(String(i.quality_grade)) || !nativeReturnMoney(i.refund_amount) || !nullable(i.notes, x => text(x) && x.length <= 2000)) fail()
    seen.add(String(i.allocation_id))
  }
  const c = closed(r.settlement, ['mode', 'credit_account_id', 'cash_account_id', 'refund_physical_at', 'reference'])
  if (!nullable(c.mode, x => x === 'CREDIT' || x === 'REFUND') || !nullable(c.credit_account_id, uuid) || !nullable(c.cash_account_id, uuid)
    || !nullable(c.refund_physical_at, stamp) || !nullable(c.reference, x => text(x) && x.length <= 100)) fail()
  if (c.mode !== 'REFUND' && (c.cash_account_id !== null || c.refund_physical_at !== null || c.reference !== null)) fail()
  return r as unknown as QuoteInput
}
function source(v: unknown, expected: QuoteInput): Source {
  const s = closed(v, ['sale_id', 'sale_number', 'customer_id', 'customer_name', 'row_version', 'review_token'])
  if (s.sale_id !== expected.sale_id || s.row_version !== expected.expected_version || s.review_token !== expected.review_token || !nonblank(s.sale_number) || !uuid(s.customer_id) || !nonblank(s.customer_name)) fail()
  return s as unknown as Source
}
function account(v: unknown, selected: string | null): AccountProof | null {
  if (v === null) return null
  const a = closed(v, ['id', 'code', 'name', 'facts_sha256'])
  if (a.id !== selected || !uuid(a.id) || !nonblank(a.code) || !nonblank(a.name) || !sha(a.facts_sha256)) fail()
  return a as unknown as AccountProof
}
const totalsKeys = ['gross_total', 'return_total', 'net_total', 'payments_received', 'credit_applied', 'credit_recognized', 'effective_paid', 'receivable_remaining'] as const
function totals(v: unknown): Totals {
  const t = closed(v, totalsKeys)
  if (!totalsKeys.every(k => money(t[k]))) fail()
  const n = (k: typeof totalsKeys[number]) => cents(String(t[k]))
  if (n('gross_total') - n('return_total') !== n('net_total') || n('payments_received') + n('credit_applied') - n('credit_recognized') !== n('effective_paid')
    || n('net_total') - n('effective_paid') !== n('receivable_remaining')) fail()
  return t as unknown as Totals
}
function priorCausal(v: unknown): PriorCausalProof {
  const p = closed(v, ['contract_version', 'scope', 'state', 'causal_book_floor', 'proof_sha256'])
  if (p.contract_version !== 'ow04.prior-causal-book-proof.v1' || p.scope !== 'PRIOR_CAUSAL_SALE_RETURN' || !sha(p.proof_sha256)) return fail()
  if (p.state === 'DATED' ? !day(p.causal_book_floor) : p.state !== 'PROVEN_ABSENT' || p.causal_book_floor !== null) return fail()
  return p as unknown as PriorCausalProof
}
export function parseSettlementQuote(value: unknown, query: QuoteInput): QuoteReply {
  parseQuoteInput(query)
  const common = ['contract_version', 'kind', 'read_only', 'business_DML', 'captured_at', 'input_echo', 'source']
  const r0 = value as { kind?: unknown } | null
  const r = closed(value, r0?.kind === 'UNAVAILABLE' ? [...common, 'reason'] : [...common, 'binding', 'has_recognition_effect', 'current_credit_amount', 'components', 'return_projection', 'totals', 'credit_account', 'cash_account', 'refund_projection', 'capabilities', 'readiness'])
  if (r.contract_version !== 'cp7.sales-return-settlement-quote.v1' || r.read_only !== true || r.business_DML !== false || !stamp(r.captured_at)
    || inputIdentity(parseQuoteInput(r.input_echo)) !== inputIdentity(query)) fail()
  source(r.source, query)
  if (r.kind === 'UNAVAILABLE') {
    if (!unavailableCodes.includes(r.reason as typeof unavailableCodes[number])) fail()
    return r as unknown as Unavailable
  }
  if (r.kind !== 'QUOTE') fail()
  const b = closed(r.binding, ['immutable_source_sha256', 'current_state_sha256', 'draft_sha256', 'choice_sha256', 'projection_sha256', 'authority_sha256', 'period_sha256', 'dependency_sha256', 'quote_sha256'])
  if (!Object.entries(b).every(([k, v]) => k === 'quote_sha256' ? nullable(v, sha) : sha(v))) fail()
  if (typeof r.has_recognition_effect !== 'boolean' || !money(r.current_credit_amount) || !Array.isArray(r.components)) return fail()
  const keys = new Set<string>(), pairs = new Set<string>(); let total = 0n, previous = ''
  for (const value of r.components) {
    const c = closed(value, ['component_key', 'economic_date', 'book_date', 'signed_amount', 'support_sha256'])
    if (!sha(c.component_key) || !day(c.economic_date) || !day(c.book_date) || c.book_date < c.economic_date
      || !signed(c.signed_amount) || cents(c.signed_amount) === 0n || !sha(c.support_sha256)) fail()
    const pair = `${c.economic_date}/${c.book_date}`
    if (keys.has(String(c.component_key)) || pairs.has(pair) || pair < previous) fail()
    keys.add(String(c.component_key)); pairs.add(pair); previous = pair; total += cents(String(c.signed_amount))
  }
  if (r.has_recognition_effect !== (r.components.length > 0) || total !== cents(r.current_credit_amount)) fail()
  const p = closed(r.return_projection, ['economic_date', 'prior_causal', 'journal_effect', 'planned_book_date', 'return_amount', 'hpp_amount', 'receivable_account_id'])
  const prior = priorCausal(p.prior_causal)
  if (!day(p.economic_date) || p.economic_date !== wibDay(query.return_payload.physical_at)
    || !money(p.return_amount) || !money(p.hpp_amount) || !nullable(p.receivable_account_id, uuid)) return fail()
  const zero = p.return_amount === '0.00' && p.hpp_amount === '0.00'
  if (zero ? p.journal_effect !== 'NO_JOURNAL' || p.planned_book_date !== null || p.receivable_account_id !== null || r.has_recognition_effect
    : p.journal_effect !== 'JOURNAL_EXPECTED' || !day(p.planned_book_date)) fail()
  if (day(p.planned_book_date) && (p.planned_book_date < p.economic_date || prior.state === 'DATED' && p.planned_book_date < prior.causal_book_floor)) fail()
  const t = closed(r.totals, ['before', 'after']), before = totals(t.before), after = totals(t.after)
  if (prior.state === 'PROVEN_ABSENT') {
    // Full scoped absence must already be proved server-side. These zero/empty
    // consistency checks alone NEVER establish absence or authorize this path.
    // Current HPP may be10 after a real recost, producing an HPP-only new J.
    if (r.has_recognition_effect || r.current_credit_amount !== '0.00' || p.return_amount !== '0.00' || p.receivable_account_id !== null
      || !totalsKeys.every(k => before[k] === '0.00' && after[k] === '0.00')) fail()
  }
  account(r.credit_account, query.settlement.credit_account_id); account(r.cash_account, query.settlement.cash_account_id)
  const caps = closed(r.capabilities, ['record_return', 'recognize_credit', 'refund_cash'])
  if (!Object.values(caps).every(x => typeof x === 'boolean')) fail()
  const ready = closed(r.readiness, ['state', 'issues'])
  if (!['CHOICE_REQUIRED', 'READY', 'BLOCKED'].includes(String(ready.state)) || !Array.isArray(ready.issues) || new Set(ready.issues).size !== ready.issues.length || !ready.issues.every(x => issueCodes.includes(x as Issue))) fail()
  const issues = ready.issues as Issue[]
  let refund: Record<string, unknown> | null = null
  if (r.refund_projection !== null) {
    refund = closed(r.refund_projection, ['amount', 'physical_at', 'economic_date', 'book_date', 'safe_capacity', 'capacity_sha256'])
    if (query.settlement.mode !== 'REFUND' || refund.amount !== r.current_credit_amount || refund.physical_at !== query.settlement.refund_physical_at
      || !nullable(refund.economic_date, day) || !nullable(refund.book_date, day) || !nullable(refund.safe_capacity, money) || !nullable(refund.capacity_sha256, sha)) fail()
    if (day(refund.economic_date) && (!stamp(query.settlement.refund_physical_at) || refund.economic_date !== wibDay(query.settlement.refund_physical_at))) fail()
    if (day(refund.book_date) && day(refund.economic_date) && refund.book_date < refund.economic_date) fail()
  } else if (query.settlement.mode === 'REFUND') fail()
  if (ready.state === 'READY') {
    if (!sha(b.quote_sha256) || issues.length > 0 || caps.record_return !== true) fail()
    if (r.has_recognition_effect) {
      if (query.settlement.mode === null || !r.credit_account || caps.recognize_credit !== true) fail()
    } else if (query.settlement.mode !== null || query.settlement.credit_account_id !== null || r.credit_account !== null) fail()
    if (query.settlement.mode === 'REFUND') {
      if (!r.cash_account || !stamp(query.settlement.refund_physical_at) || !refund || !day(refund.economic_date) || !day(refund.book_date)
        || !money(refund.safe_capacity) || cents(refund.safe_capacity) < cents(r.current_credit_amount) || !sha(refund.capacity_sha256)
        || caps.refund_cash !== true || r.current_credit_amount === '0.00') fail()
    }
  } else if (b.quote_sha256 !== null || issues.length === 0) fail()
  return r as unknown as Quote
}

export type ReadContext = { generation: number; parent_ticket: string; authority_scope: string; input_identity: string }
export type QuoteUi = { phase: 'EMPTY' | 'LOADING' | 'CURRENT' | 'UNAVAILABLE' | 'STALE' | 'ACCESS_DENIED'; context: ReadContext | null; reply: QuoteReply | null; reviewed: boolean }
export const emptyQuoteUi = (): QuoteUi => ({ phase: 'EMPTY', context: null, reply: null, reviewed: false })
export function startQuote(context: ReadContext): QuoteUi { return { phase: 'LOADING', context, reply: null, reviewed: false } }
const sameContext = (a: ReadContext | null, b: ReadContext) => a !== null && a.generation === b.generation && a.parent_ticket === b.parent_ticket && a.authority_scope === b.authority_scope && a.input_identity === b.input_identity
export function acceptQuote(ui: QuoteUi, returnedFor: ReadContext, current: ReadContext, reply: QuoteReply): QuoteUi {
  if (ui.phase !== 'LOADING' || !sameContext(ui.context, returnedFor) || !sameContext(returnedFor, current) || inputIdentity(reply.input_echo) !== current.input_identity) return ui
  return { phase: reply.kind === 'UNAVAILABLE' ? 'UNAVAILABLE' : 'CURRENT', context: current, reply, reviewed: false }
}
export function retireQuote(phase: 'STALE' | 'ACCESS_DENIED' = 'STALE'): QuoteUi { return { phase, context: null, reply: null, reviewed: false } }
export function canCommit(ui: QuoteUi, current: ReadContext, flags: { writer_locked: boolean; source_stale: boolean; pending_envelope: boolean }): boolean {
  return !flags.writer_locked && !flags.source_stale && !flags.pending_envelope && ui.phase === 'CURRENT' && sameContext(ui.context, current)
    && ui.reviewed && ui.reply?.kind === 'QUOTE' && ui.reply.readiness.state === 'READY'
}
export type CommitChoice = { mode: 'CREDIT'; credit_account_id: string } | { mode: 'REFUND'; credit_account_id: string; cash_account_id: string; refund_physical_at: string; reference: string | null } | null
export type CommitDocument = ReturnDraft & { sale_id: string; review_token: string; settlement: CommitChoice; quote_sha256: string }
export type RecoveryPayload = { document: CommitDocument; expected_version: string }
/** Pass to useProductionMutation.run; that hook allocates and persists the UUID.
 * No amounts, dates, source/journal IDs or arbitrary lines from the plan enter the command.
 */
export function commitIntent(q: Quote): { action: 'RETURN_SETTLEMENT'; payload: RecoveryPayload; expectedVersion: null } {
  parseSettlementQuote(q, q.input_echo)
  if (q.readiness.state !== 'READY' || !q.binding.quote_sha256) return fail()
  const input = q.input_echo, c = input.settlement
  const settlement: CommitChoice = !q.has_recognition_effect ? null : c.mode === 'CREDIT' && c.credit_account_id
    ? { mode: 'CREDIT', credit_account_id: c.credit_account_id } : c.mode === 'REFUND' && c.credit_account_id && c.cash_account_id && c.refund_physical_at
      ? { mode: 'REFUND', credit_account_id: c.credit_account_id, cash_account_id: c.cash_account_id, refund_physical_at: c.refund_physical_at, reference: c.reference } : fail()
  return structuredClone({ action: 'RETURN_SETTLEMENT', payload: { document: { ...input.return_payload, sale_id: input.sale_id, review_token: input.review_token, settlement, quote_sha256: q.binding.quote_sha256 }, expected_version: input.expected_version }, expectedVersion: null })
}
export type SettlementOutcome = { contract_version: 'cp7.sales-return-settlement-outcome.v1'; kind: 'COMMITTED_OUTCOME'; action: 'RETURN_SETTLEMENT'; request_id: string; sale_id: string; return_id: string; return_status: 'POSTED'; row_version: string; family_ordinal: string; credit_id: string | null; refund_event_id: string | null; quote_sha256: string; projection_sha256: string; actual_manifest_sha256: string; projection_actual_proof_sha256: string; production_go: false }
export function parseSettlementOutcome(v: unknown, request: string, envelope: RecoveryPayload): SettlementOutcome {
  const d = envelope.document
  const r = closed(v, ['contract_version', 'kind', 'action', 'request_id', 'sale_id', 'return_id', 'return_status', 'row_version', 'family_ordinal', 'credit_id', 'refund_event_id', 'quote_sha256', 'projection_sha256', 'actual_manifest_sha256', 'projection_actual_proof_sha256', 'production_go'])
  if (r.contract_version !== 'cp7.sales-return-settlement-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== 'RETURN_SETTLEMENT' || r.request_id !== request || !uuid(r.request_id)
    || r.sale_id !== d.sale_id || !uuid(r.return_id) || r.return_status !== 'POSTED' || !revision(r.row_version) || !revision(r.family_ordinal)
    || !nullable(r.credit_id, uuid) || !nullable(r.refund_event_id, uuid) || Boolean(r.credit_id) !== (d.settlement !== null)
    || Boolean(r.refund_event_id) !== (d.settlement?.mode === 'REFUND') || !sha(r.quote_sha256) || !sha(r.projection_sha256) || r.quote_sha256 !== d.quote_sha256
    || !sha(r.actual_manifest_sha256) || !sha(r.projection_actual_proof_sha256) || r.production_go !== false) fail()
  // The echoed quote digest binds the projected semantics server-side. Recovery
  // needs only the frozen document, not the lost in-memory quote. Never compare
  // actual_manifest_sha256 with projection_sha256: actual journal UUIDs are new.
  return r as unknown as SettlementOutcome
}

/** Optional picker branch of the SAME proposed read RPC. Picker pagination
 * is not an economic quote and never returns a commit token. No new default
 * account or all-accounts unbounded read is required.
 */
export type AccountOptionsQuery = { kind: 'ACCOUNT_OPTIONS'; sale_id: string; expected_version: string; review_token: string; account_kind: 'CREDIT' | 'CASH'; q: string; offset: number; limit: 25 }
export type AccountOptions = { contract_version: 'cp7.sales-return-settlement-options.v1'; kind: 'ACCOUNT_OPTIONS'; read_only: true; business_DML: false; captured_at: string; source: Source; account_kind: 'CREDIT' | 'CASH'; q: string; rows: AccountProof[]; total: string; offset: number; limit: 25; next_offset: number | null }
export function parseSettlementAccountOptions(v: unknown, expected: AccountOptionsQuery): AccountOptions {
  if (expected.kind !== 'ACCOUNT_OPTIONS' || !uuid(expected.sale_id) || !revision(expected.expected_version) || !oldReview(expected.review_token)
    || !['CREDIT', 'CASH'].includes(expected.account_kind) || !text(expected.q) || expected.q.length > 120 || !Number.isSafeInteger(expected.offset)
    || expected.offset < 0 || expected.offset > 1000000 || expected.limit !== 25) fail()
  const r = closed(v, ['contract_version', 'kind', 'read_only', 'business_DML', 'captured_at', 'source', 'account_kind', 'q', 'rows', 'total', 'offset', 'limit', 'next_offset'])
  if (r.contract_version !== 'cp7.sales-return-settlement-options.v1' || r.kind !== 'ACCOUNT_OPTIONS' || r.read_only !== true || r.business_DML !== false || !stamp(r.captured_at)
    || r.account_kind !== expected.account_kind || r.q !== expected.q || r.offset !== expected.offset || r.limit !== expected.limit || !Array.isArray(r.rows) || r.rows.length > 25
    || !text(r.total) || !/^(0|[1-9][0-9]{0,18})$/.test(r.total)) return fail()
  source(r.source, { sale_id: expected.sale_id, expected_version: expected.expected_version, review_token: expected.review_token } as QuoteInput)
  const seen = new Set<string>()
  for (const row of r.rows) { const a = row as { id?: unknown }; if (!uuid(a.id) || seen.has(a.id)) fail(); account(row, String(a.id)); seen.add(String(a.id)) }
  const end = BigInt(expected.offset + r.rows.length), total = BigInt(r.total)
  if (end > total || end < total && (!r.rows.length || r.next_offset !== Number(end)) || end >= total && r.next_offset !== null) fail()
  return r as unknown as AccountOptions
}
