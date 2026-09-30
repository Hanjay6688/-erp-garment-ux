// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import ConnectedCashLedgerPage from './ConnectedCashLedgerPage'
import ConnectedFinanceOverviewPage from './ConnectedFinanceOverviewPage'
import ConnectedFinanceReportPage from './ConnectedFinanceReportPage'
import ConnectedReceivablesPage from './ConnectedReceivablesPage'
import { clearProductionEnvelope, persistProductionEnvelope, productionKey, readProductionRecovery } from './productionRecovery'
import { financialRecoveryMessage } from './useFinancialRecoveryGate'
import { financeReportFixture } from '../tests/fixtures/financeReport'
import { financeAnalysisFixture } from '../tests/fixtures/financeAnalysis'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'

const mock = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => mock.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mock }))
vi.mock('./FinancePeriodPanel', () => ({ default: () => null }))
const scope = 'disposable:actor-1', id = '11111111-1111-4111-8111-111111111111'
function invoice() {
  return { contract_version: 'cp7.sales-workspace.v1', read_at: '2026-09-29T05:00:00Z', financial_captured: true, read_only: true,
    page: { total: '1', offset: 0, limit: 25, next_offset: null, rows: [{ id, number: 'INV-RECOVERY', customer_id: id, customer_name: 'Toko', location_id: id, location_name: 'Gudang', physical_at: '2026-09-29T03:00:00Z', due_date: null, status: 'PARTIAL_PAID', row_version: '1', notes: null, payment_terms: null, line_count: '1', qty_pcs: '4', reserved_qty: '0', returned_qty: '0', financial: { basis: 'CURRENT_NATIVE_DOCUMENT', state: 'ACTIVE_RECEIVABLE', gross_total: '80.00', return_total: '0.00', net_total: '80.00', paid_total: '30.00', open_balance: '50.00' } }] }, detail: null }
}
const pages = [
  { name: 'cash', view: () => <ConnectedCashLedgerPage/>, refresh: 'Tampilkan kas' },
  { name: 'overview', view: () => <ConnectedFinanceOverviewPage onNavigate={() => {}}/>, refresh: 'Tampilkan ringkasan' },
  { name: 'report', view: () => <ConnectedFinanceReportPage/>, refresh: 'Muat ulang laporan' },
  { name: 'receivables', view: () => <ConnectedReceivablesPage/>, refresh: 'Muat ulang piutang' },
]
function reply(name: string, args: { p_query: Parameters<typeof financeReportFixture>[0] }) {
  return { data: name === 'erp_cp7_get_sales_v1' ? invoice() : name === 'erp_cp7_get_finance_analysis_v1' ? financeAnalysisFixture(args.p_query as Parameters<typeof financeAnalysisFixture>[0]) : financeReportFixture(args.p_query), error: null }
}
function pending(target = scope) {
  const input = { action: 'POST', payload: { transaction_id: id, review_token: 'a'.repeat(32), change_reason: 'Transaksi sumber diperiksa' }, expectedVersion: null }
  const envelope = { ...input, id, fingerprint: JSON.stringify(input), createdAt: '2026-09-30T03:00:00Z' }
  expect(persistProductionEnvelope(target, 'FINANCE_MISC', envelope)).toBe(true)
}
function complete() { expect(clearProductionEnvelope(scope, 'FINANCE_MISC', readProductionRecovery(scope).pending.FINANCE_MISC!)).toBe(true) }
let root: Root, container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); mock.rpc.mockReset()
  const auth = structuredClone(recoveryIdentity); auth.identity.permissions.push('finance.cash.view', 'finance.dashboard.view', 'finance.reports.view', 'finance.ar.view', 'sales.invoice.view'); mock.auth = auth
  mock.rpc.mockImplementation((name, args) => Promise.resolve(reply(name, args)))
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear() })
const flush = async () => act(async () => { await new Promise(r => setTimeout(r, 0)) })
async function mount(page: typeof pages[number]) { await act(async () => root.render(page.view())); await flush() }
async function refresh(page: typeof pages[number]) { await act(async () => [...container.querySelectorAll('button')].find(b => b.textContent === page.refresh)!.click()); await flush() }

it.each(pages)('$name blocks a saved uncertain transaction after route mount until exact recovery and fresh read', async page => {
  pending(); await mount(page)
  expect(container.textContent).toContain(financialRecoveryMessage); expect(container.textContent).not.toContain('Rp'); expect(mock.rpc).not.toHaveBeenCalled()
  await refresh(page); expect(mock.rpc).not.toHaveBeenCalled()
  await act(async () => complete()); await flush()
  expect(container.textContent).not.toContain('Rp'); await refresh(page); expect(container.textContent).toContain('Rp')
})
it.each(pages)('$name retires facts on recovery and rejects a held read even after the uncertainty clears', async page => {
  await mount(page); expect(container.textContent).toContain('Rp')
  let resolveOld!: (value: unknown) => void, oldReply: unknown
  mock.rpc.mockImplementationOnce((name, args) => { oldReply = reply(name, args); return new Promise(resolve => { resolveOld = resolve }) })
  await refresh(page); await act(async () => pending()); await flush()
  expect(container.textContent).not.toContain('Rp'); expect(container.textContent).toContain(financialRecoveryMessage)
  await act(async () => complete()); await act(async () => resolveOld(oldReply)); await flush()
  expect(container.textContent).not.toContain('Rp'); await refresh(page); expect(container.textContent).toContain('Rp')
})
it.each(pages)('$name preserves corrupt recovery storage and keeps all money retired', async page => {
  await mount(page); expect(container.textContent).toContain('Rp')
  const key = productionKey(scope, 'FINANCE_MISC')
  await act(async () => { localStorage.setItem(key, '{'); window.dispatchEvent(new StorageEvent('storage', { key, newValue: '{', storageArea: localStorage })) }); await flush()
  const calls = mock.rpc.mock.calls.length; await refresh(page)
  expect(localStorage.getItem(key)).toBe('{'); expect(mock.rpc).toHaveBeenCalledTimes(calls); expect(container.textContent).not.toContain('Rp'); expect(container.textContent).toContain(financialRecoveryMessage)
})
it.each(pages)('$name keeps another actor recovery isolated from the current actor facts', async page => {
  pending('disposable:other-actor'); await mount(page); expect(container.textContent).toContain('Rp'); expect(container.textContent).not.toContain(financialRecoveryMessage)
})
