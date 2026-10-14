// D14-6 kasbon tunai: closed parsers for the kasbon workspace and command outcome (scripts/cp7-src/payroll/kasbon.sql).
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const money = /^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$/
const day = /^\d{4}-\d{2}-\d{2}$/
export type KasbonAllocation = { deduction_id: string; payroll_id: string; payroll_number: string; payroll_status: string; amount: string }
export type Kasbon = {
  id: string; number: string; contractor_id: string; advance_date: string; amount: string; status: 'GIVEN' | 'CANCELLED'; reason: string
  cash_account_id: string; recovered: string; reserved: string; free: string; allocations: KasbonAllocation[]
}
export type KasbonDraft = { id: string; payroll_number: string; status: string; row_version: string; period_start: string; period_end: string; earnings: string; deduction_total: string; net_payable: string }
export type KasbonCash = { id: string; code: string; name: string; review_token: string }
export type KasbonWorkspace = {
  contractor: { id: string; code: string; name: string }; advances: Kasbon[]; payroll_drafts: KasbonDraft[]; cash_accounts: KasbonCash[]
  open_from: string; today: string; review_token: string; can_write: boolean
}
export type KasbonAction = 'GIVE' | 'ALLOCATE' | 'CANCEL'
function fail(): never { throw new Error('Data kasbon tidak cocok dengan mandor yang dipilih. Muat ulang kasbon.') }
function rec(v: unknown): Record<string, unknown> { if (!v || typeof v !== 'object' || Array.isArray(v)) fail(); return v as Record<string, unknown> }
function str(v: unknown, re?: RegExp) { if (typeof v !== 'string' || !v || (re && !re.test(v))) fail(); return v }
function list(v: unknown) { if (!Array.isArray(v)) fail(); return v }
function kasbon(v: unknown, contractor: string): Kasbon {
  const r = rec(v)
  if (r.status !== 'GIVEN' && r.status !== 'CANCELLED') fail()
  const k: Kasbon = {
    id: str(r.id, uuid), number: str(r.number), contractor_id: str(r.contractor_id, uuid), advance_date: str(r.advance_date, day), amount: str(r.amount, money),
    status: r.status, reason: str(r.reason), cash_account_id: str(r.cash_account_id, uuid), recovered: str(r.recovered, money), reserved: str(r.reserved, money),
    free: str(r.free, money),
    allocations: list(r.allocations).map(a => {
      const x = rec(a)
      return { deduction_id: str(x.deduction_id, uuid), payroll_id: str(x.payroll_id, uuid), payroll_number: str(x.payroll_number), payroll_status: str(x.payroll_status), amount: str(x.amount, money) }
    }),
  }
  if (k.contractor_id !== contractor) fail()
  return k
}
export function parseKasbonWorkspace(v: unknown, contractor: string): KasbonWorkspace {
  const r = rec(v)
  if (r.contract_version !== 'cp7.kasbon-workspace.v1' || r.business_DML !== false || typeof r.can_write !== 'boolean') fail()
  const c = rec(r.contractor)
  if (c.id !== contractor) fail()
  return {
    contractor: { id: str(c.id, uuid), code: str(c.code), name: str(c.name) },
    advances: list(r.advances).map(x => kasbon(x, contractor)),
    payroll_drafts: list(r.payroll_drafts).map(x => {
      const d = rec(x)
      return { id: str(d.id, uuid), payroll_number: str(d.payroll_number), status: str(d.status), row_version: str(d.row_version, /^[1-9][0-9]{0,18}$/),
        period_start: str(d.period_start, day), period_end: str(d.period_end, day), earnings: str(d.earnings, money), deduction_total: str(d.deduction_total, money), net_payable: str(d.net_payable, money) }
    }),
    cash_accounts: list(r.cash_accounts).map(x => { const a = rec(x); return { id: str(a.id, uuid), code: str(a.code), name: str(a.name), review_token: str(a.review_token, /^[a-f0-9]{32}$/) } }),
    open_from: str(r.open_from, day), today: str(r.today, day), review_token: str(r.review_token, /^[a-f0-9]{32}$/), can_write: r.can_write,
  }
}
export function parseKasbonOutcome(v: unknown, request: string, action: KasbonAction, contractor: string): Kasbon {
  const r = rec(v)
  if (r.contract_version !== 'cp7.kasbon-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== action || r.request_id !== request || r.contractor_id !== contractor) fail()
  return kasbon(r.advance, contractor)
}
/** Cents of a typed amount: digits with at most two decimals, else null. */
export function kasbonCents(v: string): bigint | null {
  const m = /^(0|[1-9][0-9]{0,14})(?:[.,]([0-9]{1,2}))?$/.exec(v.trim())
  return m ? BigInt(m[1]) * 100n + BigInt((m[2] ?? '').padEnd(2, '0')) : null
}
export function kasbonAmountText(cents: bigint) { return `${cents / 100n}.${(cents % 100n).toString().padStart(2, '0')}` }
export function moneyCents(v: string) { const neg = v.startsWith('-'); const c = kasbonCents(neg ? v.slice(1) : v) ?? 0n; return neg ? -c : c }
