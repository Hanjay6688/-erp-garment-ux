import type { Json } from './types/database.preconnect'
import { signedSupplierSourceCents } from './supplierCredit'

export type SupplierPaymentJournal = {
  id: string; number: string; status: 'POSTED' | 'REVERSED'; economic_date: string
  accounting_date: string; posting_at: string; period_shifted: boolean
}
export type SupplierPayment = {
  id: string; number: string; status: 'DRAFT' | 'POSTED' | 'REVERSED'; payment_date: string; amount: string
  cash_account_id: string | null; cash_code: string | null; cash_name: string | null
  journal: SupplierPaymentJournal | null; inverse: SupplierPaymentJournal | null; review_token: string
}
export type SupplierPaymentRead = {
  contract_version: 'cp7.supplier-payment-read.v1'; captured_at: string; query: string; selected_payment_id: string | null
  purchase: { id: string; number: string; status: 'DRAFT' | 'POSTED' | 'REVERSED'; supplier_id: string; supplier_name: string }
  Native_AP: { id: string; number: string; date: string; final_ap: string; paid: string; remaining: string; credit_delta: string; payment_status: string } | null
  capabilities: { reverse: boolean }
  page: { rows: SupplierPayment[]; total: string; offset: number; limit: 25; next_offset: number | null }
}
const fail = (): never => { throw Error('Pembayaran supplier belum lengkap atau sudah berubah. Muat ulang pembayaran.') }
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v)
const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0
const token = (v: unknown) => typeof v === 'string' && /^[a-f0-9]{32}$/.test(v)
const date = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v)
  && Number.isFinite(Date.parse(v + 'T00:00:00Z')) && new Date(v + 'T00:00:00Z').toISOString().slice(0, 10) === v
const time = (v: unknown): v is string => typeof v === 'string' && v.includes('T') && Number.isFinite(Date.parse(v))
function closed(v: unknown, keys: string[]) {
  if (!v || typeof v !== 'object' || Array.isArray(v) || Object.keys(v).sort().join('|') !== [...keys].sort().join('|')) return fail()
  return v as Record<string, unknown>
}
function cents(v: unknown) {
  if (typeof v !== 'string' || !/^-?(0|[1-9][0-9]{0,17})\.\d{2}$/.test(v)) return fail()
  return signedSupplierSourceCents(v)
}
function journal(v: unknown): SupplierPaymentJournal {
  const r = closed(v, ['id', 'number', 'status', 'economic_date', 'accounting_date', 'posting_at', 'period_shifted'])
  if (!uuid(r.id) || !text(r.number) || !['POSTED', 'REVERSED'].includes(String(r.status))
    || !date(r.economic_date) || !date(r.accounting_date) || !time(r.posting_at) || typeof r.period_shifted !== 'boolean') fail()
  return r as unknown as SupplierPaymentJournal
}
function payment(v: unknown): SupplierPayment {
  const r = closed(v, ['id', 'number', 'status', 'payment_date', 'amount', 'cash_account_id', 'cash_code', 'cash_name', 'journal', 'inverse', 'review_token'])
  if (!uuid(r.id) || !text(r.number) || !['DRAFT', 'POSTED', 'REVERSED'].includes(String(r.status))
    || !(date(r.payment_date) || time(r.payment_date)) || cents(r.amount) <= 0n || !token(r.review_token)
    || !(r.cash_account_id === null || uuid(r.cash_account_id)) || ![r.cash_code, r.cash_name].every(x => x === null || text(x))) fail()
  const j = r.journal === null ? null : journal(r.journal), inverse = r.inverse === null ? null : journal(r.inverse)
  if (r.status === 'DRAFT' && (j || inverse) || r.status === 'POSTED' && (!j || j.status !== 'POSTED' || inverse)
    || r.status === 'REVERSED' && (!j || j.status !== 'REVERSED' || !inverse || inverse.status !== 'POSTED')
    || j && inverse && j.id === inverse.id) fail()
  return { ...r, journal: j, inverse } as unknown as SupplierPayment
}
export function parseSupplierPaymentRead(value: unknown, purchaseId: string, query: string, offset: number | null, selectedPayment: string | null = null): SupplierPaymentRead {
  const r = closed(value, ['contract_version', 'captured_at', 'query', 'selected_payment_id', 'purchase', 'Native_AP', 'capabilities', 'page'])
  const h = closed(r.purchase, ['id', 'number', 'status', 'supplier_id', 'supplier_name']), cap = closed(r.capabilities, ['reverse'])
  if (r.contract_version !== 'cp7.supplier-payment-read.v1' || !time(r.captured_at) || r.query !== query || r.selected_payment_id !== selectedPayment
    || !uuid(h.id) || h.id !== purchaseId || !uuid(h.supplier_id) || !text(h.number) || !text(h.supplier_name)
    || !['DRAFT', 'POSTED', 'REVERSED'].includes(String(h.status)) || typeof cap.reverse !== 'boolean') fail()
  const ap = r.Native_AP === null ? null : closed(r.Native_AP, ['id', 'number', 'date', 'final_ap', 'paid', 'remaining', 'credit_delta', 'payment_status'])
  if (h.status === 'POSTED' && !ap || ap && (ap.id !== h.id || ap.number !== h.number || !date(ap.date) || !text(ap.payment_status)
    || cents(ap.paid) < 0n || cents(ap.final_ap) !== cents(ap.paid) + cents(ap.remaining))) fail()
  if (ap) cents(ap.credit_delta)
  const p = closed(r.page, ['rows', 'total', 'offset', 'limit', 'next_offset'])
  if (!Array.isArray(p.rows) || typeof p.total !== 'string' || !/^(0|[1-9][0-9]{0,29})$/.test(p.total)
    || offset !== null && p.offset !== offset || !Number.isSafeInteger(p.offset) || Number(p.offset) < 0 || Number(p.offset) > 1000000 || p.limit !== 25 || p.rows.length > 25) fail()
  const actualOffset = Number(p.offset), rows = (p.rows as unknown[]).map(payment), end = BigInt(actualOffset) + BigInt(rows.length), total = BigInt(p.total as string)
  if (new Set(rows.map(x => x.id)).size !== rows.length || rows.length && end > total
    || end < total && p.next_offset === null
    || p.next_offset !== null && (!rows.length || p.next_offset !== actualOffset + rows.length || end >= total)
    || selectedPayment !== null && !rows.some(p => p.id === selectedPayment)) fail()
  if (ap) {
    const shownPaid = rows.filter(x => x.status === 'POSTED').reduce((sum, x) => sum + cents(x.amount), 0n)
    if (shownPaid > cents(ap.paid) || query === '' && actualOffset === 0 && p.next_offset === null && shownPaid !== cents(ap.paid)) fail()
  }
  return { ...r, page: { ...p, rows } } as unknown as SupplierPaymentRead
}
function canonical(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(canonical)
  if (v && typeof v === 'object') return Object.fromEntries(Object.keys(v).sort().map(k => [k, canonical((v as Record<string, unknown>)[k])]))
  return v
}
export function parseSupplierPaymentOutcome(value: unknown, requestId: string, payload: Json) {
  const r = closed(value, ['contract_version', 'kind', 'action', 'request_id', 'request_payload', 'purchase_id', 'payment_id', 'status', 'inverse_journal_id'])
  const d = closed(payload, ['purchase_id', 'payment_id', 'review_token', 'reason'])
  if (r.contract_version !== 'cp7.supplier-payment-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== 'REVERSE'
    || r.request_id !== requestId || r.purchase_id !== d.purchase_id || r.payment_id !== d.payment_id || r.status !== 'REVERSED'
    || ![r.purchase_id, r.payment_id, r.inverse_journal_id].every(uuid)
    || JSON.stringify(canonical(r.request_payload)) !== JSON.stringify(canonical(d))) fail()
  return r as unknown as { purchase_id: string; payment_id: string; inverse_journal_id: string; status: 'REVERSED' }
}
