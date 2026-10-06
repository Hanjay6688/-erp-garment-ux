// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SupplierPaymentPanel from './SupplierPaymentPanel'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { supplierPaymentFixture, supplierPaymentReadFixture, supplierPurchaseId as purchase } from '../tests/fixtures/supplierPayments'
import { readProductionRecovery } from './productionRecovery'
import { parseSupplierPaymentCreateOutcome, parseSupplierPaymentCreateRead } from './supplierPaymentCreateContract'
import type { Json } from './types/database.preconnect'

const state = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn(), source: null as unknown }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => state.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => state }))
vi.mock('./TransactionSourceNavigation', () => ({ useTransactionSource: () => state.source }))
const created = 'b2000000-0000-4000-8000-000000000099', bank = 'd4000000-0000-4000-8000-000000000001'
let box: HTMLDivElement, root: Root
const onReceiptUpdated = vi.fn(async () => true)
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); state.rpc.mockReset(); onReceiptUpdated.mockReset().mockResolvedValue(true)
  const auth = structuredClone(recoveryIdentity); auth.identity.permissions.push('warehouse.procurement.view', 'finance.ap.view', 'finance.ap.pay'); state.auth = auth
  state.source = { key: 'SOURCE-1', document: { id: purchase, focus: { kind: 'SUPPLIER_PAYMENT', id: 'b2000000-0000-4000-8000-000000000026', page_offset: 25 } } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _options: unknown, run: (lock: unknown) => Promise<unknown>) => run({}) } })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const flush = async () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
async function mount(purchaseId: string | null = purchase) { await act(async () => root.render(<SupplierPaymentPanel purchaseId={purchaseId} parentReady receiptRevision="REV-1" onReceiptUpdated={onReceiptUpdated}/>)); await flush() }
const button = (name: string) => [...box.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent?.trim() === name)
async function click(name: string) { expect(button(name)).toBeTruthy(); await act(async () => button(name)!.click()); await flush() }
async function input(label: string, value: string) {
  const e = box.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
  expect(e).not.toBeNull(); await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(e, value); e.dispatchEvent(new Event('input', { bubbles: true })) }); await flush()
}
const writes = () => state.rpc.mock.calls.filter(([name]) => name === 'erp_cp7_create_supplier_payment_v1')
function workspace(read = supplierPaymentReadFixture(0)) {
  return { contract_version: 'cp7.supplier-payment-create-workspace.v1', captured_at: read.captured_at,
    purchase: { ...read.purchase, physical_at: '2026-09-24T03:00:00+00:00' }, Native_AP: read.Native_AP, eligible: true, review_token: 'f'.repeat(32), can_create: true,
    cash_accounts: { rows: [{ id: bank, code: 'BANK', name: 'Bank supplier', kind: 'BANK' }], total: '1', offset: 0, limit: 25, next_offset: null } }
}
function server(opts: { lose?: boolean; mismatch?: boolean } = {}) {
  const s = { effects: 0, lose: Boolean(opts.lose) }, cache = new Map<string, Json>()
  state.rpc.mockImplementation(async (name, args) => {
    if (name === 'erp_cp7_get_supplier_payments_v1') {
      const r = supplierPaymentReadFixture(25, args.p_q, args.p_payment)
      r.capabilities.reverse = (state.auth as typeof recoveryIdentity).identity.permissions.includes('finance.ap.pay')
      if (s.effects) { const p = supplierPaymentFixture(); p.id = created; p.number = 'B-NEW'; p.amount = '40.00'; p.review_token = 'e'.repeat(32)
        p.journal = { ...p.journal!, id: 'c3000000-0000-4000-8000-000000000099', number: 'JRN-SUP-NEW' }
        r.page.rows = [...r.page.rows, p]; r.page.total = '27'; r.Native_AP!.paid = '300.00'; r.Native_AP!.remaining = '700.00'; r.selected_payment_id = args.p_payment }
      return { data: r, error: null }
    }
    if (name === 'erp_cp7_get_supplier_payment_create_v1') {
      const w = workspace(supplierPaymentReadFixture(25)); if (opts.mismatch) w.Native_AP!.remaining = '739.00'
      return { data: w, error: null }
    }
    if (name !== 'erp_cp7_create_supplier_payment_v1') throw Error('Unexpected RPC ' + name)
    if (!cache.has(args.p_request)) { s.effects++; cache.set(args.p_request, { contract_version: 'cp7.supplier-payment-create.v1', kind: 'COMMITTED_OUTCOME', action: 'CREATE',
      request_id: args.p_request, request_payload: args.p_payload, purchase_id: args.p_payload.purchase_id, payment_id: created, status: 'POSTED', amount: args.p_payload.amount, remaining_after: '700.00' }) }
    if (s.lose) { s.lose = false; return { data: null, error: { message: 'Committed payment reply lost' } } }
    return { data: cache.get(args.p_request), error: null }
  })
  return s
}
async function fill(amount = '40.00') {
  await click('Bayar supplier SJ-SUP-001'); await input('Nominal pembayaran supplier baru', amount)
  await input('Waktu pembayaran supplier baru WIB', '2026-10-01T10:00'); await click('BANK · Bank supplier')
  await input('Keterangan pembayaran supplier baru', 'Transfer BCA pelunasan sebagian')
  await act(async () => box.querySelector<HTMLInputElement>('[aria-label="Pembayaran supplier baru sudah diperiksa"]')!.click()); await flush()
}
describe('Recording a new supplier payment through one owning command', () => {
  it('sends one exact create command after explicit review and reloads the new remaining AP', async () => {
    const s = server(); await mount(); await fill(); expect(button('Sahkan pembayaran supplier')!.disabled).toBe(false)
    await click('Sahkan pembayaran supplier')
    expect(writes()).toHaveLength(1); expect(s.effects).toBe(1)
    expect(writes()[0][1].p_payload).toEqual({ purchase_id: purchase, review_token: 'f'.repeat(32), amount: '40.00', cash_account_id: bank, payment_date: '2026-10-01T03:00:00.000Z', note: 'Transfer BCA pelunasan sebagian' })
    expect(onReceiptUpdated).toHaveBeenCalledWith(purchase); expect(box.textContent).toContain('Rp700'); expect(box.textContent).toContain('B-NEW')
  })
  it('keeps the payment button disabled above the remaining AP and without review', async () => {
    server(); await mount(); await fill('740.01'); expect(button('Sahkan pembayaran supplier')!.disabled).toBe(true)
    expect(box.textContent).toContain('paling banyak sisa utang')
    await input('Nominal pembayaran supplier baru', '740.00'); expect(button('Sahkan pembayaran supplier')!.disabled).toBe(true)
    await act(async () => box.querySelector<HTMLInputElement>('[aria-label="Pembayaran supplier baru sudah diperiksa"]')!.click()); await flush()
    expect(button('Sahkan pembayaran supplier')!.disabled).toBe(false); expect(writes()).toHaveLength(0)
  })
  it('retains the exact envelope after a committed lost reply and reconciles the same UUID once after reload', async () => {
    const s = server({ lose: true }); await mount(); await fill(); await click('Sahkan pembayaran supplier')
    const first = structuredClone(writes()[0][1]); expect(s.effects).toBe(1); expect(box.textContent).not.toContain('Rp')
    expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_PAYMENT?.action).toBe('CREATE')
    await act(async () => root.unmount()); root = createRoot(box); await mount(null); await click('Periksa status pembatalan supplier')
    expect(writes()[1][1]).toEqual(first); expect(s.effects).toBe(1); expect(box.textContent).toContain('Rp700')
    expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_PAYMENT).toBeUndefined()
  })
  it('refuses a create workspace whose AP differs from the payment list and never writes', async () => {
    server({ mismatch: true }); await mount(); await click('Bayar supplier SJ-SUP-001')
    expect(box.textContent).toContain('Data pembayaran supplier baru belum lengkap atau sudah berubah'); expect(box.textContent).not.toContain('Rp740')
    expect(box.querySelector('[aria-label="Pembayaran supplier baru"]')).toBeNull(); expect(writes()).toHaveLength(0)
  })
  it('offers no payment entry without the current pay right', async () => {
    const a = state.auth as typeof recoveryIdentity; a.identity.permissions = a.identity.permissions.filter(p => p !== 'finance.ap.pay')
    server(); await mount(); expect(button('Bayar supplier SJ-SUP-001')).toBeUndefined(); expect(writes()).toHaveLength(0)
  })
  it('parsers bind the workspace to its list and the outcome to its exact request', () => {
    const read = supplierPaymentReadFixture(25), w = workspace(read)
    expect(parseSupplierPaymentCreateRead(w, read, 0).review_token).toBe('f'.repeat(32))
    expect(() => parseSupplierPaymentCreateRead({ ...w, eligible: false }, read, 0)).toThrow()
    expect(() => parseSupplierPaymentCreateRead({ ...w, extra: 1 }, read, 0)).toThrow()
    const payload = { purchase_id: purchase, review_token: 'f'.repeat(32), amount: '40.00', cash_account_id: bank, payment_date: '2026-10-01T03:00:00.000Z', note: 'Transfer BCA pelunasan' }
    const outcome = { contract_version: 'cp7.supplier-payment-create.v1', kind: 'COMMITTED_OUTCOME', action: 'CREATE', request_id: created, request_payload: payload, purchase_id: purchase, payment_id: created, status: 'POSTED', amount: '40.00', remaining_after: '700.00' }
    expect(parseSupplierPaymentCreateOutcome(outcome, created, payload).payment_id).toBe(created)
    expect(() => parseSupplierPaymentCreateOutcome({ ...outcome, amount: '41.00' }, created, payload)).toThrow()
    expect(() => parseSupplierPaymentCreateOutcome(outcome, purchase, payload)).toThrow()
  })
})
