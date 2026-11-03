const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const token = /^[0-9a-f]{64}$/
const payrollStatuses = ['DRAFT', 'CALCULATED', 'REVIEW', 'APPROVED', 'PAID', 'REVERSED'] as const
export type MandorShopAction = 'RESERVE' | 'RELEASE'
export type MandorShopAllocation = {
  id: string; payroll_id: string; payroll_number: string; period_start: string; period_end: string
  payroll_status: string; amount: string; state: 'RESERVED' | 'SETTLED' | 'RELEASED'
}
export type MandorShopCard = {
  sale_id: string; number: string; physical_at: string; net_invoice: string; paid_amount: string
  outstanding: string; allocated_amount: string; available_to_reserve: string
  allocations: MandorShopAllocation[]; review_token: string
}
export type MandorShopWorkspace = {
  payroll_id: string; contractor_id: string; status: string; period_start: string; period_end: string
  net_payable_preview: string; reserved_amount: string; can_change: boolean
  cards: MandorShopCard[]; has_more: boolean; next_after: string | null
}
export type MandorShopBuyer = {
  contractor_id: string; code: string; name: string; customer_id: string | null
  can_select: boolean; review_token: string
}
export type MandorShopBuyerOptions = {
  sales_action: 'CREATE' | 'EDIT'; rows: MandorShopBuyer[]; has_more: boolean; next_after: string | null
}

function fail(): never { throw Error('Data tagihan belanja tidak cocok dengan sumber yang dipilih. Muat ulang sumber.') }
function record(v: unknown): Record<string, unknown> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) fail()
  return v as Record<string, unknown>
}
function text(v: unknown, pattern?: RegExp): string {
  if (typeof v !== 'string' || !v.trim() || pattern && !pattern.test(v)) fail()
  return v
}
function rows(v: unknown): unknown[] { if (!Array.isArray(v)) fail(); return v }
function bool(v: unknown): boolean { if (typeof v !== 'boolean') fail(); return v }
function date(v: unknown): string {
  const s = text(v, /^\d{4}-\d{2}-\d{2}$/), n = new Date(s + 'T00:00:00Z')
  if (!Number.isFinite(n.getTime()) || n.toISOString().slice(0, 10) !== s) fail()
  return s
}
function stamp(v: unknown): string {
  const s = text(v, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/)
  if (!Number.isFinite(Date.parse(s))) fail()
  date(s.slice(0, 10))
  return s
}
function status(v: unknown): string {
  const s = text(v)
  if (!(payrollStatuses as readonly string[]).includes(s)) fail()
  return s
}
/** Exact cents from operator input. Comma is accepted; grouping and exponent notation are not. */
export function mandorShopCents(v: string): bigint | null {
  const m = /^(0|[1-9][0-9]{0,17})(?:[.,]([0-9]{1,2}))?$/.exec(v.trim())
  return m ? BigInt(m[1]) * 100n + BigInt((m[2] ?? '').padEnd(2, '0')) : null
}
export function mandorShopAmount(v: bigint): string {
  const negative = v < 0n, absolute = negative ? -v : v
  return `${negative ? '-' : ''}${absolute / 100n}.${String(absolute % 100n).padStart(2, '0')}`
}
function amount(v: unknown): string {
  const s = text(v, /^-?(0|[1-9][0-9]{0,17})(?:\.[0-9]{1,2})?$/)
  const cents = mandorShopCents(s.startsWith('-') ? s.slice(1) : s)
  if (cents === null) fail()
  return mandorShopAmount(s.startsWith('-') ? -cents : cents)
}
export function mandorShopSignedCents(v: string): bigint {
  const s = amount(v), cents = mandorShopCents(s.startsWith('-') ? s.slice(1) : s)
  if (cents === null) fail()
  return s.startsWith('-') ? -cents : cents
}
export function mandorShopRupiah(v: string): string {
  const [whole, cents] = amount(v).split('.')
  return `Rp${whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${cents}`
}
function unique(values: string[]) { if (new Set(values).size !== values.length) fail() }
function page(after: unknown, more: boolean, ids: string[]): string | null {
  if (!more) { if (after !== null) fail(); return null }
  const next = text(after, uuid)
  if (!ids.length || next !== ids.at(-1)) fail()
  return next
}

export function parseMandorShopWorkspace(value: unknown, payroll: string, contractor: string): MandorShopWorkspace {
  const r = record(value)
  if (r.contract_version !== 'cp7.mandor-shop-workspace.v1' || r.payroll_id !== payroll || r.contractor_id !== contractor) fail()
  text(payroll, uuid); text(contractor, uuid)
  const cards = rows(r.cards).map(value => {
    const c = record(value), sale = text(c.sale_id, uuid)
    const allocations = rows(c.allocations).map(value => {
      const row = record(value), a = record(row.allocation), state = text(a.state)
      if (a.sale_id !== sale || a.contractor_id !== contractor || !['RESERVED', 'SETTLED', 'RELEASED'].includes(state)) fail()
      const start = date(row.period_start), end = date(row.period_end), money = amount(a.amount)
      if (end < start || mandorShopSignedCents(money) <= 0n) fail()
      return { id: text(a.allocation_id, uuid), payroll_id: text(a.payroll_id, uuid),
        payroll_number: text(row.payroll_number), period_start: start, period_end: end,
        payroll_status: status(row.payroll_status), amount: money, state: state as MandorShopAllocation['state'] }
    })
    unique(allocations.map(a => a.id))
    const net = amount(c.net_invoice), paid = amount(c.paid_amount), outstanding = amount(c.outstanding)
    const allocated = amount(c.allocated_amount), available = amount(c.available_to_reserve)
    const reserved = allocations.filter(a => a.state === 'RESERVED').reduce((n, a) => n + mandorShopSignedCents(a.amount), 0n)
    if (mandorShopSignedCents(outstanding) !== mandorShopSignedCents(net) - mandorShopSignedCents(paid)
      || mandorShopSignedCents(allocated) !== reserved
      || mandorShopSignedCents(available) !== mandorShopSignedCents(outstanding) - reserved) fail()
    return { sale_id: sale, number: text(c.number), physical_at: stamp(c.physical_at), net_invoice: net,
      paid_amount: paid, outstanding, allocated_amount: allocated, available_to_reserve: available,
      allocations, review_token: text(c.review_token, token) }
  })
  unique(cards.map(c => c.sale_id))
  if (cards.length > 100) fail()
  const start = date(r.period_start), end = date(r.period_end), more = bool(r.has_more)
  if (end < start) fail()
  const state = status(r.status), change = bool(r.can_change)
  if (change && !['DRAFT', 'CALCULATED', 'REVIEW'].includes(state)) fail()
  return { payroll_id: payroll, contractor_id: contractor, status: state, period_start: start, period_end: end,
    net_payable_preview: amount(r.net_payable_preview), reserved_amount: amount(r.reserved_amount), can_change: change,
    cards, has_more: more, next_after: page(r.next_after, more, cards.map(c => c.sale_id)) }
}

export function parseMandorShopAllocationOutcome(value: unknown, request: string, action: MandorShopAction, payroll: string, sale: string) {
  const r = record(value)
  if (r.contract_version !== 'cp7.mandor-shop-allocation-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME'
    || r.request_id !== request || r.action !== action || r.payroll_id !== payroll || r.sale_id !== sale
    || r.invoice_settled_by_this_command !== false) fail()
  return { allocation_id: text(r.allocation_id, uuid), net_payable: amount(r.net_payable) }
}
export function parseMandorShopBuyerOptions(value: unknown, action: 'CREATE' | 'EDIT'): MandorShopBuyerOptions {
  const r = record(value)
  if (r.contract_version !== 'cp7.mandor-shop-buyer-options.v1' || r.buyer_category !== 'MANDOR' || r.sales_action !== action) fail()
  const buyers = rows(r.rows).map(value => {
    const b = record(value)
    return { contractor_id: text(b.contractor_id, uuid), code: text(b.code), name: text(b.name),
      customer_id: b.customer_id === null ? null : text(b.customer_id, uuid),
      can_select: bool(b.can_select), review_token: text(b.review_token, token) }
  })
  unique(buyers.map(b => b.contractor_id)); if (buyers.length > 100) fail()
  const more = bool(r.has_more)
  return { sales_action: action, rows: buyers, has_more: more, next_after: page(r.next_after, more, buyers.map(b => b.contractor_id)) }
}
export function parseMandorShopBuyerOutcome(value: unknown, request: string, contractor: string) {
  const r = record(value)
  if (r.contract_version !== 'cp7.mandor-shop-buyer-outcome.v1' || r.buyer_category !== 'MANDOR'
    || r.request_id !== request || r.contractor_id !== contractor) fail()
  return { contractor_id: text(r.contractor_id, uuid), customer_id: text(r.customer_id, uuid),
    name: text(r.name), customer_code: text(r.customer_code) }
}
