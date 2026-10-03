import type { Json } from './types/database.preconnect'
import { financeDate } from './financeReportContract'

export type MiscType = 'OTHER_INCOME' | 'OTHER_EXPENSE'
export type MiscAction = 'SAVE' | 'POST' | 'REVERSE'
export type MiscQuery = { q: string; status: 'DRAFT' | 'POSTED' | 'REVERSED' | null; transaction_id: string | null; offset: number; category_offset: number; cash_offset: number }
type Page<T> = { rows: T[]; total: string; offset: number; limit: 25; next_offset: number | null }
type Account = { id: string; code: string; name: string; account_id: string; account_code: string; account_name: string; eligible: boolean; review_token: string }
export type MiscCategory = Account & { type: MiscType }
export type MiscCash = Account & { kind: string }
export type MiscJournal = { id: string; number: string; status: 'POSTED' | 'REVERSED'; reversal_of_id: string | null; economic_date: string; transaction_date: string; posting_at: string; period_shifted: boolean; debit: string; credit: string }
export type MiscDocument = {
  id: string; number: string; type: MiscType; category_id: string; category_name: string | null; category_eligible: boolean;
  cash_account_id: string; cash_account_name: string | null; cash_eligible: boolean; physical_at: string; amount: string;
  counterparty_name: string | null; reference_number: string | null; notes: string | null; status: 'DRAFT' | 'POSTED' | 'REVERSED';
  review_token: string; category_source: MiscCategory | null; cash_source: MiscCash | null; journals: MiscJournal[]
}
export type MiscRead = { contract_version: 'cp7.misc-read.v1'; captured_at: string; scope: 'CURRENT_NATIVE_MISC_FINANCE_DOCUMENTS'; query: Pick<MiscQuery, 'q' | 'status' | 'transaction_id'>; page: Page<MiscDocument>; categories: Page<MiscCategory>; cash_accounts: Page<MiscCash>; detail: MiscDocument | null }
export type MiscOutcome = { contract_version: 'cp7.misc-outcome.v1'; kind: 'COMMITTED_OUTCOME'; action: MiscAction; request_id: string; transaction_id: string; document: MiscDocument }
export type MiscTimeRestatement = { neutral_journal_id: string; neutral_number: string; neutral_economic_date: string; neutral_transaction_date: string; effective_journal_id: string; effective_number: string; effective_economic_date: string; effective_transaction_date: string }
export type MiscCorrectionLink = { original_id: string; replacement_id: string; actor_scope_id: string; request_id: string; reason: string; recorded_at: string; time_restatement: MiscTimeRestatement | null }
export type MiscCorrectionOutcome = { contract_version: 'cp7.misc-correction.v1'; kind: 'COMMITTED_OUTCOME'; action: 'CORRECT'; request_id: string; transaction_id: string; original_review_token: string; original_document: MiscDocument; document: MiscDocument; link: MiscCorrectionLink }
export type MiscMutationOutcome = MiscOutcome | MiscCorrectionOutcome
export type MiscCorrectionHistory = { contract_version: 'cp7.misc-correction-history.v1'; captured_at: string; transaction_id: string; previous: { link: MiscCorrectionLink; document: MiscDocument } | null; next: { link: MiscCorrectionLink; document: MiscDocument } | null }
const fail = (): never => { throw Error('Transaksi atau sumber rekening berubah atau belum lengkap. Muat ulang sebelum melanjutkan.') }
const text = (v: unknown): v is string => typeof v === 'string'
const uuid = (v: unknown) => text(v) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const token = (v: unknown) => text(v) && /^[a-f0-9]{32}$/.test(v)
const instant = (v: unknown) => text(v) && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v) && financeDate(v.slice(0, 10)) && Number.isFinite(Date.parse(v))
const whole = (v: unknown): v is string => text(v) && /^(0|[1-9][0-9]{0,20})$/.test(v)
const nullable = (v: unknown, max: number) => v === null || text(v) && v.length <= max
export function miscAmount(v: string): string | null {
  const n = v.trim().replace(',', '.')
  return /^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$/.test(n) ? n : null
}
export function miscCents(v: string): bigint {
  if (miscAmount(v) !== v) return fail()
  const [a, b = ''] = v.split('.')
  return BigInt(a) * 100n + BigInt(b.padEnd(2, '0'))
}
function closed(v: unknown, keys: string[]) {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return fail()
  const r = v as Record<string, unknown>
  if (keys.some(k => !(k in r)) || Object.keys(r).some(k => !keys.includes(k))) fail()
  return r
}
function option(v: unknown, category: boolean, eligibleOnly: boolean) {
  const r = closed(v, ['id', 'code', 'name', 'account_id', 'account_code', 'account_name', 'eligible', 'review_token', category ? 'type' : 'kind'])
  if (!uuid(r.id) || !uuid(r.account_id) || ![r.code, r.name, r.account_code, r.account_name].every(text) || !token(r.review_token) || typeof r.eligible !== 'boolean' || eligibleOnly && !r.eligible) fail()
  if (category ? !['OTHER_INCOME', 'OTHER_EXPENSE'].includes(String(r.type)) : !text(r.kind)) fail()
  return r
}
export function parseMiscDocument(v: unknown): MiscDocument {
  const r = closed(v, ['id', 'number', 'type', 'category_id', 'category_name', 'category_eligible', 'cash_account_id', 'cash_account_name', 'cash_eligible', 'physical_at', 'amount', 'counterparty_name', 'reference_number', 'notes', 'status', 'review_token', 'category_source', 'cash_source', 'journals'])
  if (![r.id, r.category_id, r.cash_account_id].every(uuid) || !text(r.number) || !r.number.trim() || Array.from(r.number).length > 60 || !['OTHER_INCOME', 'OTHER_EXPENSE'].includes(String(r.type)) || !['DRAFT', 'POSTED', 'REVERSED'].includes(String(r.status)) || !instant(r.physical_at) || !token(r.review_token) || !text(r.amount) || miscAmount(r.amount) !== r.amount || miscCents(r.amount) <= 0n || !nullable(r.category_name, 120) || !nullable(r.cash_account_name, 120) || !nullable(r.counterparty_name, 150) || !nullable(r.reference_number, 100) || !nullable(r.notes, 2000) || typeof r.category_eligible !== 'boolean' || typeof r.cash_eligible !== 'boolean' || !Array.isArray(r.journals)) return fail()
  const category = r.category_source === null ? null : option(r.category_source, true, false)
  const cash = r.cash_source === null ? null : option(r.cash_source, false, false)
  if (category ? category.id !== r.category_id || category.name !== r.category_name || category.eligible !== r.category_eligible : r.category_eligible || r.category_name !== null) fail()
  if (cash ? cash.id !== r.cash_account_id || cash.name !== r.cash_account_name || cash.eligible !== r.cash_eligible : r.cash_eligible || r.cash_account_name !== null) fail()
  const ids = new Set<string>()
  for (const value of r.journals) {
    const j = closed(value, ['id', 'number', 'status', 'reversal_of_id', 'economic_date', 'transaction_date', 'posting_at', 'period_shifted', 'debit', 'credit'])
    if (!uuid(j.id) || ids.has(j.id as string) || !text(j.number) || !['POSTED', 'REVERSED'].includes(String(j.status)) || j.reversal_of_id !== null && !uuid(j.reversal_of_id) || !financeDate(j.economic_date) || !financeDate(j.transaction_date) || !instant(j.posting_at) || typeof j.period_shifted !== 'boolean' || j.period_shifted !== (j.economic_date !== j.transaction_date) || !text(j.debit) || !text(j.credit) || miscAmount(j.debit) !== j.debit || miscAmount(j.credit) !== j.credit || miscCents(j.debit) !== miscCents(r.amount) || miscCents(j.credit) !== miscCents(r.amount)) return fail()
    ids.add(j.id as string)
  }
  const journals = r.journals as MiscJournal[], original = journals.filter(j => j.reversal_of_id === null)
  if (r.status === 'DRAFT' ? journals.length !== 0 : original.length !== 1) fail()
  if (r.status === 'POSTED' && (journals.length !== 1 || original[0].status !== 'POSTED')) fail()
  if (r.status === 'REVERSED' && (journals.length !== 2 || original[0].status !== 'REVERSED' || journals.filter(j => j.reversal_of_id === original[0].id && j.status === 'POSTED').length !== 1)) fail()
  return r as unknown as MiscDocument
}
function page<T>(v: unknown, offset: number, parse: (v: unknown) => T): Page<T> {
  const p = closed(v, ['rows', 'total', 'offset', 'limit', 'next_offset'])
  if (!Array.isArray(p.rows) || p.rows.length > 25 || !whole(p.total) || p.offset !== offset || p.limit !== 25) return fail()
  const total = BigInt(p.total), end = BigInt(offset + p.rows.length)
  if (p.rows.length && end > total || end < total && (!p.rows.length || p.next_offset !== Number(end)) || end >= total && p.next_offset !== null) fail()
  const ids = new Set<string>()
  for (const v of p.rows) { const r = parse(v) as T & { id: string }; if (ids.has(r.id)) fail(); ids.add(r.id) }
  return p as unknown as Page<T>
}
export function parseMiscRead(v: unknown, query: MiscQuery): MiscRead {
  const r = closed(v, ['contract_version', 'captured_at', 'scope', 'query', 'page', 'categories', 'cash_accounts', 'detail'])
  if (r.contract_version !== 'cp7.misc-read.v1' || r.scope !== 'CURRENT_NATIVE_MISC_FINANCE_DOCUMENTS' || !instant(r.captured_at)) fail()
  const q = closed(r.query, ['q', 'status', 'transaction_id'])
  if (q.q !== query.q || q.status !== query.status || q.transaction_id !== query.transaction_id) fail()
  const documents = page(r.page, query.offset, parseMiscDocument)
  if (query.status && documents.rows.some(d => d.status !== query.status)) fail()
  page(r.categories, query.category_offset, v => option(v, true, true)); page(r.cash_accounts, query.cash_offset, v => option(v, false, true))
  if (query.transaction_id === null ? r.detail !== null : parseMiscDocument(r.detail).id !== query.transaction_id) fail()
  if (r.detail !== null) {
    const d = parseMiscDocument(r.detail), listed = documents.rows.find(t => t.id === d.id)
    if (listed && JSON.stringify(listed) !== JSON.stringify(d)) fail()
  }
  return r as unknown as MiscRead
}
export function parseMiscOutcome(v: unknown, request: string, action: string, payload: Json): MiscOutcome {
  const r = closed(v, ['contract_version', 'kind', 'action', 'request_id', 'transaction_id', 'document'])
  if (r.contract_version !== 'cp7.misc-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || !uuid(request) || r.request_id !== request || r.action !== action || !['SAVE', 'POST', 'REVERSE'].includes(action) || !uuid(r.transaction_id) || !payload || typeof payload !== 'object' || Array.isArray(payload)) return fail()
  const d = parseMiscDocument(r.document), p = payload as Record<string, Json>
  if (d.id !== r.transaction_id || p.transaction_id !== null && p.transaction_id !== d.id || d.status !== ({ SAVE: 'DRAFT', POST: 'POSTED', REVERSE: 'REVERSED' } as Record<string, string>)[action]) fail()
  if (action === 'SAVE' && (d.number !== p.transaction_number || d.type !== p.transaction_type || d.category_id !== p.category_id || d.cash_account_id !== p.cash_account_id || typeof p.amount !== 'string' || miscCents(d.amount) !== miscCents(p.amount) || typeof p.physical_at !== 'string' || Date.parse(d.physical_at) !== Date.parse(p.physical_at) || d.counterparty_name !== p.counterparty_name || d.reference_number !== p.reference_number || d.notes !== p.notes)) fail()
  return r as unknown as MiscOutcome
}

export function miscCorrectionNumber(original: string, request: string): string {
  if (!uuid(request)) return fail()
  return Array.from(original).slice(0, 20).join('') + ' · K-' + request.replaceAll('-', '')
}
function instantMicros(v: unknown): bigint {
  if (!instant(v)) return fail()
  const value = v as string, fraction = value.match(/\.([0-9]{1,6})(?:Z|[+-][0-9]{2}:[0-9]{2})$/)?.[1] ?? ''
  return BigInt(Date.parse(value)) * 1000n + BigInt(fraction.padEnd(6, '0').slice(3))
}
function parseCorrectionLink(v: unknown): MiscCorrectionLink {
  const r = closed(v, ['original_id', 'replacement_id', 'actor_scope_id', 'request_id', 'reason', 'recorded_at', 'time_restatement'])
  if (![r.original_id, r.replacement_id, r.actor_scope_id, r.request_id].every(uuid) || r.original_id === r.replacement_id || !text(r.reason) || r.reason !== r.reason.trim() || r.reason.length < 5 || r.reason.length > 1000 || !instant(r.recorded_at)) fail()
  if (r.time_restatement !== null) {
    const t = closed(r.time_restatement, ['neutral_journal_id', 'neutral_number', 'neutral_economic_date', 'neutral_transaction_date', 'effective_journal_id', 'effective_number', 'effective_economic_date', 'effective_transaction_date'])
    if (!uuid(t.neutral_journal_id) || !uuid(t.effective_journal_id) || t.neutral_journal_id === t.effective_journal_id || !text(t.neutral_number) || !t.neutral_number || !text(t.effective_number) || !t.effective_number || ![t.neutral_economic_date, t.neutral_transaction_date, t.effective_economic_date, t.effective_transaction_date].every(financeDate) || t.neutral_economic_date === t.effective_economic_date) fail()
  }
  return r as unknown as MiscCorrectionLink
}
function validateRestatement(link: MiscCorrectionLink, original: MiscDocument) {
  const journal = original.journals.find(j => j.reversal_of_id === null), inverse = original.journals.find(j => j.reversal_of_id === journal?.id)
  if (!journal || !inverse) return fail()
  if ((journal.economic_date === inverse.economic_date) !== (link.time_restatement === null)) fail()
  const t = link.time_restatement
  if (t && (t.effective_economic_date !== journal.economic_date || t.neutral_economic_date !== inverse.economic_date || original.journals.some(j => j.id === t.neutral_journal_id || j.id === t.effective_journal_id))) fail()
}
export function parseMiscMutationOutcome(v: unknown, request: string, action: string, payload: Json): MiscMutationOutcome {
  if (action !== 'CORRECT') return parseMiscOutcome(v, request, action, payload)
  const r = closed(v, ['contract_version', 'kind', 'action', 'request_id', 'transaction_id', 'original_review_token', 'original_document', 'document', 'link'])
  const p = closed(payload, ['transaction_id', 'review_token', 'replacement', 'change_reason'])
  const replacement = closed(p.replacement, ['transaction_id', 'review_token', 'transaction_number', 'transaction_type', 'category_id', 'category_review_token', 'cash_account_id', 'cash_review_token', 'physical_at', 'amount', 'counterparty_name', 'reference_number', 'notes', 'change_reason'])
  if (r.contract_version !== 'cp7.misc-correction.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== 'CORRECT' || r.request_id !== request || !uuid(request) || !uuid(p.transaction_id) || !token(p.review_token) || r.original_review_token !== p.review_token || replacement.transaction_id !== null || replacement.review_token !== null || replacement.change_reason !== p.change_reason) return fail()
  const old = parseMiscDocument(r.original_document), next = parseMiscDocument(r.document), link = parseCorrectionLink(r.link)
  if (old.id !== p.transaction_id || old.status !== 'REVERSED' || old.number !== replacement.transaction_number || old.id === next.id || next.status !== 'POSTED' || next.id !== r.transaction_id || next.number !== miscCorrectionNumber(old.number, request) || link.original_id !== old.id || link.replacement_id !== next.id || link.request_id !== request || link.reason !== p.change_reason) fail()
  if (next.type !== replacement.transaction_type || next.category_id !== replacement.category_id || next.cash_account_id !== replacement.cash_account_id || !text(replacement.amount) || miscCents(next.amount) !== miscCents(replacement.amount) || instantMicros(next.physical_at) !== instantMicros(replacement.physical_at) || next.counterparty_name !== replacement.counterparty_name || next.reference_number !== replacement.reference_number || next.notes !== replacement.notes) fail()
  if (old.journals.some(j => next.journals.some(n => n.id === j.id))) fail()
  validateRestatement(link, old)
  if (link.time_restatement && next.journals.some(j => j.id === link.time_restatement!.neutral_journal_id || j.id === link.time_restatement!.effective_journal_id)) fail()
  return r as unknown as MiscCorrectionOutcome
}
export function parseMiscCorrectionHistory(v: unknown, transaction: string): MiscCorrectionHistory {
  const r = closed(v, ['contract_version', 'captured_at', 'transaction_id', 'previous', 'next'])
  if (r.contract_version !== 'cp7.misc-correction-history.v1' || !instant(r.captured_at) || !uuid(transaction) || r.transaction_id !== transaction) fail()
  const ids = new Set([transaction])
  for (const side of ['previous', 'next'] as const) {
    if (r[side] === null) continue
    const edge = closed(r[side], ['link', 'document']), link = parseCorrectionLink(edge.link), d = parseMiscDocument(edge.document)
    if (ids.has(d.id) || (side === 'previous' ? link.replacement_id !== transaction || link.original_id !== d.id || d.status !== 'REVERSED' : link.original_id !== transaction || link.replacement_id !== d.id)) fail()
    if (side === 'previous') validateRestatement(link, d)
    ids.add(d.id)
  }
  return r as unknown as MiscCorrectionHistory
}
