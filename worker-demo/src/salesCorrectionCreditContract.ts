import { isoDayText, lowercaseHex64, versionedUuidText } from './lib/contractPatterns'
import { creditCents } from './customerCreditContract'
import type { SalesRead } from './salesReadContract'

type ActiveConsumer = {
  event_id: string
  event_kind: 'APPLY' | 'REFUND'
  amount: string
  target_sale_id: string | null
}

export type ReturnCreditReview = {
  state: 'REVIEW_REQUIRED' | 'READY' | 'REFUSE'
  review_token: string | null
  credit_delta: string | null
  before_available: string | null
  after_available: string | null
  issues: string[]
  active_consumers: ActiveConsumer[]
}

type CarryConsumer = {
  event_id: string
  amount: string
  historical_target_id: string
  economic_date: string
  transaction_date: string
}
export type NoteCreditBasis = {
  basis_sha256: string
  transfer_amount: string
  minimum_replacement_net: string
  issues: string[]
  consumers: CarryConsumer[]
}

const fail = (): never => { throw new Error('Rincian saldo kredit pembetulan belum lengkap. Muat ulang dokumen sebelum melanjutkan.') }
const uuid = (v: unknown): v is string => typeof v === 'string' && versionedUuidText.test(v)
const hash = (v: unknown): v is string => typeof v === 'string' && lowercaseHex64.test(v)
const day = (v: unknown): v is string => typeof v === 'string' && isoDayText.test(v)
  && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v

function fields(value: unknown, keys: string[]) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return fail()
  const record = value as Record<string, unknown>
  if (Object.keys(record).length !== keys.length || keys.some(key => !Object.hasOwn(record, key))) return fail()
  return record
}

function issuesOf(value: unknown): string[] {
  if (!Array.isArray(value) || !value.every(v => typeof v === 'string' && /^[A-Z][A-Z0-9_]{1,100}$/.test(v))) return fail()
  return value
}

function uniqueEvents(rows: { event_id: string }[]) {
  if (new Set(rows.map(row => row.event_id.toLowerCase())).size !== rows.length) fail()
}

export function parseReturnCreditReview(value: unknown): ReturnCreditReview {
  const r = fields(value, ['contract_version', 'state', 'review_token', 'credit_delta', 'before_available',
    'after_available', 'issues', 'active_consumers', 'families', 'source_authority_proven', 'increase_policy',
    'shortfall_policy', 'replacement_invoice_policy'])
  const state = r.state
  if (r.contract_version !== 'cp7.credit-correction-de.v1' || r.increase_policy !== 'AUTO_CREDIT_INCREMENT'
    || r.shortfall_policy !== 'UNDO_ACTIVE_CONSUMERS_FIRST' || r.replacement_invoice_policy !== 'AUTO_TRANSFER_TO_REPLACEMENT'
    || !Array.isArray(r.active_consumers) || !Array.isArray(r.families)
    || (state !== 'REVIEW_REQUIRED' && state !== 'READY' && state !== 'REFUSE')) return fail()
  const issues = issuesOf(r.issues)
  const amounts = [r.credit_delta, r.before_available, r.after_available]
  if (state === 'REVIEW_REQUIRED') {
    if (r.review_token !== null || r.source_authority_proven !== false || amounts.some(v => v !== null)
      || issues.length || r.families.length) return fail()
  } else {
    if (!hash(r.review_token) || r.source_authority_proven !== true
      || creditCents(r.before_available) + creditCents(r.credit_delta) !== creditCents(r.after_available)
      || (state === 'READY') !== (issues.length === 0)) return fail()
  }
  const active_consumers = r.active_consumers.map((value): ActiveConsumer => {
    const event = fields(value, ['event_id', 'event_kind', 'amount', 'cohort_id', 'family_ordinal', 'target_sale_id', 'journal_id', 'undo_action'])
    const { event_id, event_kind, amount, target_sale_id } = event
    if (!uuid(event_id) || !uuid(event.cohort_id) || !uuid(event.journal_id)
      || typeof event.family_ordinal !== 'string' || !/^[1-9][0-9]*$/.test(event.family_ordinal)
      || (event_kind !== 'APPLY' && event_kind !== 'REFUND') || typeof amount !== 'string' || creditCents(amount) <= 0n
      || (event_kind === 'APPLY' ? !uuid(target_sale_id) : target_sale_id !== null)
      || typeof event.undo_action !== 'string' || !event.undo_action) return fail()
    return { event_id, event_kind, amount, target_sale_id: target_sale_id as string | null }
  })
  uniqueEvents(active_consumers)
  return { state, review_token: r.review_token as string | null, credit_delta: r.credit_delta as string | null,
    before_available: r.before_available as string | null, after_available: r.after_available as string | null, issues, active_consumers }
}

export function parseNoteCreditBasis(value: unknown, source: NonNullable<SalesRead['detail']>, root: string): NoteCreditBasis {
  const r = fields(value, ['contract_version', 'sale_id', 'root_sale_id', 'row_version', 'review_token',
    'basis_sha256', 'transfer_amount', 'minimum_replacement_net', 'original_net', 'policy', 'issues', 'consumers'])
  const { basis_sha256, transfer_amount, minimum_replacement_net } = r
  if (!source.financial) return fail()
  const [gross, fraction = ''] = source.financial.gross_total.split('.')
  if (r.contract_version !== 'cp7.note-credit-carry-basis.v1' || r.policy !== 'AUTO_TRANSFER_TO_REPLACEMENT'
    || r.sale_id !== source.id || r.root_sale_id !== root || r.row_version !== source.row_version
    || r.review_token !== source.review_token || !hash(basis_sha256)
    || typeof transfer_amount !== 'string' || typeof minimum_replacement_net !== 'string' || !Array.isArray(r.consumers)
    || creditCents(transfer_amount) < 0n || creditCents(minimum_replacement_net) < creditCents(transfer_amount)
    || creditCents(r.original_net) !== creditCents(`${gross}.${fraction.padEnd(2, '0')}`)) return fail()
  const consumers = r.consumers.map((value): CarryConsumer => {
    const event = fields(value, ['event_id', 'amount', 'cohort_id', 'journal_id', 'historical_target_id', 'economic_date', 'transaction_date'])
    const { event_id, amount, historical_target_id, economic_date, transaction_date } = event
    if (!uuid(event_id) || !uuid(event.cohort_id) || !uuid(event.journal_id) || !uuid(historical_target_id)
      || !day(economic_date) || !day(transaction_date) || transaction_date < economic_date
      || typeof amount !== 'string' || creditCents(amount) === 0n) return fail()
    return { event_id, amount, historical_target_id, economic_date, transaction_date }
  })
  uniqueEvents(consumers)
  return { basis_sha256, transfer_amount, minimum_replacement_net, issues: issuesOf(r.issues), consumers }
}

export function noteCarryReview(basis: NoteCreditBasis, replacementNet: bigint) {
  const carried = creditCents(basis.transfer_amount)
  if (basis.issues.length || carried === 0n || replacementNet < creditCents(basis.minimum_replacement_net)) return null
  const amount = (cents: bigint) => `${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`
  return { contract_version: 'cp7.note-credit-carry-review.v1', basis_sha256: basis.basis_sha256,
    transfer_amount: basis.transfer_amount, replacement_net: amount(replacementNet), remaining_amount: amount(replacementNet - carried) }
}
