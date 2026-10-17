import { salesStatuses, type SalesStatus } from './salesReadContract'

// R3-03 (owner D16-1): closed parser of public.erp_cp7_get_customer_history_v1 (scripts/cp7-src/sales/customer-history.sql).
// Every key is required and no other key is accepted; amounts are present only when the read captured finance.ar.view.
export type HistoryCounts = { invoices: string; payments: string; returns: string; cancellations: string }
export type HistoryCustomerFinance = {
  basis: 'CURRENT_NATIVE_DOCUMENT'; active_invoices: string; invoice_total: string; return_total: string; net_total: string
  paid_total: string; open_balance: string
}
export type HistoryCustomer = {
  id: string; code: string; name: string; is_active: boolean; counts: HistoryCounts; last_invoice_at: string | null
  financial?: HistoryCustomerFinance
}
export type HistoryKind = 'INVOICE' | 'PAYMENT' | 'RETURN' | 'CANCELLATION'
export type HistoryDocument = 'INVOICE' | 'PAYMENT' | 'RETURN'
export type HistoryEvent = {
  id: string; kind: HistoryKind; document: HistoryDocument; document_id: string; number: string; at: string; wib_date: string
  invoice_id: string; invoice_number: string; status: string; qty_pcs: string | null; method: string | null; location_name: string | null
  financial?: { amount: string }
}
export type HistoryInvoiceFinance = {
  basis: 'CURRENT_NATIVE_DOCUMENT'; state: 'DRAFT_PREVIEW' | 'ACTIVE_RECEIVABLE' | 'INACTIVE_DOCUMENT'; gross_total: string
  return_total: string; net_total: string; paid_total: string; open_balance: string | null
}
export type HistoryInvoice = {
  id: string; number: string; status: SalesStatus; physical_at: string; due_date: string | null; qty_pcs: string; financial?: HistoryInvoiceFinance
}
export type HistoryPage<T> = { rows: T[]; total: string; offset: number; limit: number; next_offset: number | null }
type Common = { contract_version: 'cp7.customer-history.v1'; read_at: string; financial_captured: boolean; can_export: boolean; read_only: true; business_DML: false }
export type HistoryList = Common & { mode: 'LIST'; page: HistoryPage<HistoryCustomer> }
export type HistoryDetail = Common & { mode: 'CUSTOMER'; customer: HistoryCustomer; timeline: HistoryPage<HistoryEvent>; invoices: HistoryInvoice[] }
export type HistoryExpectation = { financial: boolean; offset: number; limit: number }

const DOCUMENT_STATUSES = ['DRAFT', 'POSTED', 'REVERSED']
const ACTIVE = ['POSTED', 'PARTIAL_PAID', 'PAID']
const WIB_MS = 7 * 60 * 60 * 1000

function fail(): never { throw new Error('Data riwayat pelanggan belum lengkap. Muat ulang sebelum melanjutkan.') }
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail()
  return value as Record<string, unknown>
}
function closed(value: unknown, keys: string[]) {
  const r = record(value)
  if (Object.keys(r).length !== keys.length || keys.some(key => !(key in r))) fail()
  return r
}
function text(value: unknown): string { if (typeof value !== 'string' || value === '') fail(); return value }
function nullableText(value: unknown): string | null { return value === null ? null : text(value) }
function id(value: unknown) { const v = text(value); if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)) fail(); return v }
function whole(value: unknown) { const v = text(value); if (!/^(0|[1-9][0-9]{0,18})$/.test(v)) fail(); return v }
function instant(value: unknown) { const v = text(value); if (!Number.isFinite(Date.parse(v))) fail(); return v }
function day(value: unknown) { const v = text(value); if (!/^\d{4}-\d{2}-\d{2}$/.test(v) || !Number.isFinite(Date.parse(v))) fail(); return v }
function flag(value: unknown) { if (typeof value !== 'boolean') fail(); return value }
function cents(value: unknown): bigint {
  const v = text(value)
  if (!/^-?(0|[1-9][0-9]{0,19})\.[0-9]{2}$/.test(v)) fail()
  const negative = v.startsWith('-'), [a, b] = v.replace(/^-/, '').split('.')
  return (BigInt(a) * 100n + BigInt(b)) * (negative ? -1n : 1n)
}
function plain(value: unknown) { if (cents(value) < 0n) fail(); return value as string }
/** The WIB calendar date of an instant, without the device's timezone. */
export function wibDate(at: string) { return new Date(Date.parse(at) + WIB_MS).toISOString().slice(0, 10) }

function page<T>(value: unknown, expect: HistoryExpectation, row: (v: unknown) => T): HistoryPage<T> {
  const p = closed(value, ['rows', 'total', 'offset', 'limit', 'next_offset'])
  if (!Array.isArray(p.rows) || p.offset !== expect.offset || p.limit !== expect.limit || p.rows.length > expect.limit) fail()
  const total = BigInt(whole(p.total)), end = BigInt(expect.offset + p.rows.length)
  if (p.rows.length && end > total || end < total && p.next_offset !== Number(end) || end >= total && p.next_offset !== null) fail()
  return { rows: p.rows.map(row), total: p.total as string, offset: expect.offset, limit: expect.limit, next_offset: p.next_offset as number | null }
}

function customer(value: unknown, financial: boolean): HistoryCustomer {
  const c = closed(value, ['id', 'code', 'name', 'is_active', 'counts', 'last_invoice_at', ...(financial ? ['financial'] : [])])
  const n = closed(c.counts, ['invoices', 'payments', 'returns', 'cancellations'])
  const counts = { invoices: whole(n.invoices), payments: whole(n.payments), returns: whole(n.returns), cancellations: whole(n.cancellations) }
  const out: HistoryCustomer = { id: id(c.id), code: text(c.code), name: text(c.name), is_active: flag(c.is_active), counts,
    last_invoice_at: c.last_invoice_at === null ? null : instant(c.last_invoice_at) }
  if ((out.last_invoice_at === null) !== (counts.invoices === '0')) fail()
  if (financial) {
    const f = closed(c.financial, ['basis', 'active_invoices', 'invoice_total', 'return_total', 'net_total', 'paid_total', 'open_balance'])
    if (f.basis !== 'CURRENT_NATIVE_DOCUMENT' || BigInt(whole(f.active_invoices)) > BigInt(counts.invoices)) fail()
    for (const key of ['invoice_total', 'return_total', 'net_total', 'paid_total']) plain(f[key])
    // The open balance of the active invoices is their net value less what was paid on them.
    if (cents(f.open_balance) !== cents(f.net_total) - cents(f.paid_total)) fail()
    out.financial = f as HistoryCustomerFinance
  }
  return out
}

function event(value: unknown, financial: boolean): HistoryEvent {
  const e = closed(value, ['id', 'kind', 'document', 'document_id', 'number', 'at', 'wib_date', 'invoice_id', 'invoice_number', 'status',
    'qty_pcs', 'method', 'location_name', ...(financial ? ['financial'] : [])])
  const kind = e.kind as HistoryKind, document = e.document as HistoryDocument
  if (!['INVOICE', 'PAYMENT', 'RETURN', 'CANCELLATION'].includes(kind) || !['INVOICE', 'PAYMENT', 'RETURN'].includes(document)
    || kind !== 'CANCELLATION' && kind !== document) fail()
  const out: HistoryEvent = { id: text(e.id), kind, document, document_id: id(e.document_id), number: text(e.number), at: instant(e.at),
    wib_date: day(e.wib_date), invoice_id: id(e.invoice_id), invoice_number: text(e.invoice_number), status: text(e.status),
    qty_pcs: e.qty_pcs === null ? null : whole(e.qty_pcs), method: nullableText(e.method), location_name: nullableText(e.location_name) }
  if (out.id !== `${kind}:${out.document_id}` || out.wib_date !== wibDate(out.at)) fail()
  if (document === 'INVOICE' ? !salesStatuses.includes(out.status as SalesStatus) || out.invoice_id !== out.document_id
    || out.invoice_number !== out.number || out.qty_pcs === null || out.method !== null : !DOCUMENT_STATUSES.includes(out.status)) fail()
  if (document === 'PAYMENT' && (out.qty_pcs !== null || out.location_name !== null) || document === 'RETURN' && (out.qty_pcs === null || out.method !== null || out.location_name !== null)) fail()
  if (kind === 'CANCELLATION' && !(document === 'INVOICE' ? ['CANCELLED', 'REVERSED'] : ['REVERSED']).includes(out.status)) fail()
  if (financial) out.financial = { amount: plain(closed(e.financial, ['amount']).amount) }
  return out
}

function invoice(value: unknown, financial: boolean): HistoryInvoice {
  const i = closed(value, ['id', 'number', 'status', 'physical_at', 'due_date', 'qty_pcs', ...(financial ? ['financial'] : [])])
  if (!salesStatuses.includes(i.status as SalesStatus)) fail()
  const out: HistoryInvoice = { id: id(i.id), number: text(i.number), status: i.status as SalesStatus, physical_at: instant(i.physical_at),
    due_date: i.due_date === null ? null : day(i.due_date), qty_pcs: whole(i.qty_pcs) }
  if (financial) {
    const f = closed(i.financial, ['basis', 'state', 'gross_total', 'return_total', 'net_total', 'paid_total', 'open_balance'])
    const active = ACTIVE.includes(out.status)
    if (f.basis !== 'CURRENT_NATIVE_DOCUMENT' || f.state !== (active ? 'ACTIVE_RECEIVABLE' : out.status === 'DRAFT' ? 'DRAFT_PREVIEW' : 'INACTIVE_DOCUMENT')) fail()
    for (const key of ['gross_total', 'return_total', 'net_total', 'paid_total']) plain(f[key])
    const net = cents(f.gross_total) - cents(f.return_total)
    if (cents(f.net_total) !== (net < 0n ? 0n : net)) fail()
    if (active ? cents(f.open_balance) !== cents(f.net_total) - cents(f.paid_total) : f.open_balance !== null) fail()
    out.financial = f as HistoryInvoiceFinance
  }
  return out
}

function common(r: Record<string, unknown>, mode: 'LIST' | 'CUSTOMER', expect: HistoryExpectation) {
  if (r.contract_version !== 'cp7.customer-history.v1' || r.mode !== mode || r.financial_captured !== expect.financial
    || r.read_only !== true || r.business_DML !== false) fail()
  instant(r.read_at); flag(r.can_export)
}

export function parseHistoryList(value: unknown, expect: HistoryExpectation): HistoryList {
  const r = closed(value, ['contract_version', 'mode', 'read_at', 'financial_captured', 'can_export', 'read_only', 'business_DML', 'page'])
  common(r, 'LIST', expect)
  const p = page(r.page, expect, v => customer(v, expect.financial))
  if (new Set(p.rows.map(c => c.id)).size !== p.rows.length) fail()
  return { ...(r as Common), mode: 'LIST', page: p }
}

export function parseHistoryDetail(value: unknown, expect: HistoryExpectation & { customerId: string }): HistoryDetail {
  const r = closed(value, ['contract_version', 'mode', 'read_at', 'financial_captured', 'can_export', 'read_only', 'business_DML', 'customer', 'timeline', 'invoices'])
  common(r, 'CUSTOMER', expect)
  const c = customer(r.customer, expect.financial)
  if (c.id !== expect.customerId) fail()
  const t = page(r.timeline, expect, v => event(v, expect.financial))
  // Every invoice, payment and return has its event, and every cancellation one more.
  if (BigInt(t.total) !== BigInt(c.counts.invoices) + BigInt(c.counts.payments) + BigInt(c.counts.returns) + BigInt(c.counts.cancellations)) fail()
  if (new Set(t.rows.map(e => e.id)).size !== t.rows.length) fail()
  for (let n = 1; n < t.rows.length; n++) if (Date.parse(t.rows[n - 1].at) < Date.parse(t.rows[n].at)) fail()
  if (!Array.isArray(r.invoices)) fail()
  const invoices = r.invoices.map(v => invoice(v, expect.financial)), byId = new Map(invoices.map(i => [i.id, i]))
  if (byId.size !== invoices.length || byId.size !== new Set(t.rows.map(e => e.invoice_id)).size) fail()
  for (const e of t.rows) {
    const i = byId.get(e.invoice_id)
    if (!i || i.number !== e.invoice_number) fail()
    if (e.document === 'INVOICE' && (e.status !== i.status || e.qty_pcs !== i.qty_pcs || e.financial && i.financial && e.financial.amount !== i.financial.gross_total)) fail()
  }
  return { ...(r as Common), mode: 'CUSTOMER', customer: c, timeline: t, invoices }
}
