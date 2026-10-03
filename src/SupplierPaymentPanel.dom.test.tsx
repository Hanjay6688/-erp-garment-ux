// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SupplierPaymentPanel from './SupplierPaymentPanel'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { supplierPaymentFixture, supplierPaymentReadFixture, supplierPurchaseId as purchase, supplierPaymentId as payment, supplierInverseId } from '../tests/fixtures/supplierPayments'
import { clearProductionEnvelope, persistProductionEnvelope, productionKey, readProductionRecovery } from './productionRecovery'
import { parseSupplierPaymentRead, parseSupplierPaymentOutcome } from './supplierPaymentContract'
import type { Json } from './types/database.preconnect'

const state = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn(), source: null as unknown }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => state.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => state }))
vi.mock('./TransactionSourceNavigation', () => ({ useTransactionSource: () => state.source }))
let box: HTMLDivElement, root: Root
const onReceiptUpdated = vi.fn(async () => true)
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); state.rpc.mockReset(); onReceiptUpdated.mockReset().mockResolvedValue(true)
  const auth = structuredClone(recoveryIdentity); auth.identity.permissions.push('warehouse.procurement.view', 'finance.ap.view', 'finance.ap.pay'); state.auth = auth
  state.source = { key: 'SOURCE-1', document: { id: purchase, focus: { kind: 'SUPPLIER_PAYMENT', id: payment, page_offset: 25 } } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _options: unknown, run: (lock: unknown) => Promise<unknown>) => run({}) } })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const flush = async () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
async function mount(purchaseId: string | null = purchase, parentReady = true) { await act(async () => root.render(<SupplierPaymentPanel purchaseId={purchaseId} parentReady={parentReady} receiptRevision="REV-1" onReceiptUpdated={onReceiptUpdated}/>)); await flush() }
const button = (name: string) => [...box.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent?.trim() === name)!
async function click(name: string) { expect(button(name)).toBeTruthy(); await act(async () => button(name).click()); await flush() }
async function input(label: string, value: string) {
  const e = box.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[aria-label="${label}"]`)!
  expect(e).not.toBeNull(); await act(async () => { const proto = e.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(e, value); e.dispatchEvent(new Event('input', { bubbles: true })) }); await flush()
}
const writes = () => state.rpc.mock.calls.filter(([name]) => name === 'erp_cp7_reverse_supplier_payment_v1')
function server() {
  const s = { failRead: false, lose: false, effects: 0, reversed: false }, cache = new Map<string, Json>()
  state.rpc.mockImplementation(async (name, args) => {
    if (name === 'erp_cp7_get_supplier_payments_v1') {
      if (s.failRead) return { data: null, error: { code: '42501', message: 'Current source denied' } }
      const r = supplierPaymentReadFixture(args.p_offset, args.p_q, args.p_payment)
      const auth = state.auth as typeof recoveryIdentity
      r.capabilities.reverse = auth.identity.permissions.includes('finance.ap.pay')
      if (s.reversed) { r.Native_AP!.paid = '250.00'; r.Native_AP!.remaining = '750.00'; const p = r.page.rows.find(p => p.id === payment)
        if (p) { p.status = 'REVERSED'; p.journal!.status = 'REVERSED'
          p.inverse = { ...p.journal!, id: supplierInverseId, number: 'JRN-SUP-REVERSE', status: 'POSTED', economic_date: '2026-10-03', accounting_date: '2026-10-03' } } }
      return { data: r, error: null }
    }
    if (name !== 'erp_cp7_reverse_supplier_payment_v1') throw Error('Unexpected RPC ' + name)
    if (!cache.has(args.p_request)) { s.effects++; s.reversed = true; cache.set(args.p_request, {
      contract_version: 'cp7.supplier-payment-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'REVERSE', request_id: args.p_request,
      request_payload: args.p_payload, purchase_id: args.p_payload.purchase_id, payment_id: args.p_payload.payment_id, status: 'REVERSED', inverse_journal_id: supplierInverseId }) }
    if (s.lose) { s.lose = false; return { data: null, error: { message: 'Committed reply lost' } } }
    return { data: cache.get(args.p_request), error: null }
  })
  return s
}
async function review() { await click('Tinjau pembatalan PAY-SUP-026'); await input('Alasan pembatalan pembayaran supplier', 'Uang belum benar benar dibayarkan'); await act(async () => box.querySelector<HTMLInputElement>('[aria-label="Pembayaran supplier sudah diperiksa"]')!.click()); await flush() }
describe('Exact supplier payment and owning inverse', () => {
  it('opens the exact Native parent and child on page25 without a client scan or write', async () => {
    server(); await mount(); expect(state.rpc.mock.calls[0][1]).toEqual({ p_purchase: purchase, p_q: '', p_offset: 25, p_payment: payment })
    expect(box.querySelector('[data-source-focus="true"]')?.getAttribute('data-supplier-payment-id')).toBe(payment)
    expect(box.textContent).toContain('Rp740'); expect(writes()).toHaveLength(0)
  })
  it('requires reason and explicit review, retires displayed money at send, and reconciles the same UUID after reload', async () => {
    const s = server(); s.lose = true; await mount(); await click('Tinjau pembatalan PAY-SUP-026'); expect(button('Balikkan pembayaran supplier sekarang').disabled).toBe(true)
    await input('Alasan pembatalan pembayaran supplier', 'Uang belum benar benar dibayarkan'); expect(button('Balikkan pembayaran supplier sekarang').disabled).toBe(true)
    await act(async () => box.querySelector<HTMLInputElement>('[aria-label="Pembayaran supplier sudah diperiksa"]')!.click()); await flush(); await click('Balikkan pembayaran supplier sekarang')
    expect(s.effects).toBe(1); expect(box.textContent).not.toContain('Rp'); const first = structuredClone(writes()[0][1]); expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_PAYMENT?.id).toBe(first.p_request)
    await act(async () => root.unmount()); root = createRoot(box); await mount(null); await click('Periksa status pembatalan supplier')
    expect(writes()[1][1]).toEqual(first); expect(s.effects).toBe(1); expect(onReceiptUpdated).toHaveBeenCalledWith(purchase)
    expect(box.textContent).toContain('Rp750'); expect(box.textContent).toContain('JRN-SUP-REVERSE'); expect(box.textContent).toContain('2026-10-03')
  })
  it('failed current read retires amounts and confirmation, retains only own reason for a fresh review', async () => {
    const s = server(); await mount(); await review(); s.failRead = true; await click('Muat ulang pembayaran supplier')
    expect(box.textContent).not.toContain('Rp'); expect(box.querySelector('[data-supplier-payment-id]')).toBeNull(); s.failRead = false
    await click('Muat ulang pembayaran supplier'); await click('Tinjau pembatalan PAY-SUP-026')
    expect(box.querySelector<HTMLTextAreaElement>('[aria-label="Alasan pembatalan pembayaran supplier"]')!.value).toBe('Uang belum benar benar dibayarkan')
    expect(box.querySelector<HTMLInputElement>('[aria-label="Pembayaran supplier sudah diperiksa"]')!.checked).toBe(false); expect(writes()).toHaveLength(0)
  })
  it('search editing retires the old payment and keeps the query form available until the explicit server search', async () => {
    server(); await mount(); await input('Cari pembayaran supplier', 'PAY-SUP'); expect(box.textContent).not.toContain('Rp'); expect(button('Cari pembayaran supplier')).toBeTruthy()
    const form = box.querySelector<HTMLFormElement>('.record-tools')!; await act(async () => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))); await flush()
    expect(state.rpc.mock.calls.at(-1)?.[1]).toEqual({ p_purchase: purchase, p_q: 'PAY-SUP', p_offset: 0, p_payment: null }); expect(writes()).toHaveLength(0)
  })
  it('a held success cannot repaint money after a shared envelope ABA invalidation', async () => {
    server(); let release: (value: unknown) => void = () => {}; state.rpc.mockImplementationOnce(() => new Promise(resolve => { release = resolve })); await mount()
    const body = { action: 'POST', payload: { sale_id: purchase }, expectedVersion: 1 }, envelope = { ...body, id: payment, createdAt: '2026-10-03T00:00:00Z', fingerprint: JSON.stringify(body) }
    await act(async () => { persistProductionEnvelope('disposable:actor-1', 'SALES', envelope); clearProductionEnvelope('disposable:actor-1', 'SALES', envelope) })
    await act(async () => release({ data: supplierPaymentReadFixture(25, '', payment), error: null })); await flush(); expect(box.textContent).not.toContain('Rp'); await click('Muat ulang pembayaran supplier'); expect(box.textContent).toContain('Rp740')
  })
  it('current authority remount retires another actor reason and does not offer a forbidden inverse', async () => {
    server(); await mount(); await review(); const a = structuredClone(state.auth) as typeof recoveryIdentity; a.identity.profile.id = 'actor-2'; a.identity.permissions = a.identity.permissions.filter(p => p !== 'finance.ap.pay'); state.auth = a
    await mount(); expect(button('Tinjau pembatalan PAY-SUP-026')).toBeUndefined(); a.identity.permissions.push('finance.ap.pay'); await mount(); await click('Tinjau pembatalan PAY-SUP-026')
    expect(box.querySelector<HTMLTextAreaElement>('[aria-label="Alasan pembatalan pembayaran supplier"]')!.value).toBe(''); expect(writes()).toHaveLength(0)
  })
  it('corrupt recovery stays intact and prevents every financial source and writer RPC', async () => {
    server(); const key = productionKey('disposable:actor-1', 'SUPPLIER_PAYMENT'); localStorage.setItem(key, '{'); await mount()
    expect(localStorage.getItem(key)).toBe('{'); expect(state.rpc).not.toHaveBeenCalled(); expect(box.textContent).not.toContain('Rp')
  })
  it('parent source loading retires its child money and review without losing an operator reason', async () => {
    server(); await mount(); await review(); await mount(purchase, false); expect(box.textContent).not.toContain('Rp')
    expect(box.querySelector('[data-supplier-payment-id]')).toBeNull(); await mount(); await click('Tinjau pembatalan PAY-SUP-026')
    expect(box.querySelector<HTMLTextAreaElement>('[aria-label="Alasan pembatalan pembayaran supplier"]')!.value).toBe('Uang belum benar benar dibayarkan')
    expect(box.querySelector<HTMLInputElement>('[aria-label="Pembayaran supplier sudah diperiksa"]')!.checked).toBe(false); expect(writes()).toHaveLength(0)
  })
  it('an authorized readonly source remains visible without Web Locks while every inverse is disabled', async () => {
    server(); Reflect.deleteProperty(navigator, 'locks'); await mount(); expect(box.textContent).toContain('Rp740'); expect(button('Tinjau pembatalan PAY-SUP-026').disabled).toBe(true); expect(writes()).toHaveLength(0)
  })
  it('rejects wrong parent/child windows and exact-money contradictions including unsafe JS integers', () => {
    const r = supplierPaymentReadFixture(); expect(parseSupplierPaymentRead(r, purchase, '', 25).page.rows[0].id).toBe(payment)
    for (const change of [{ purchase: { ...r.purchase, id: payment } }, { page: { ...r.page, offset: 0 } }, { Native_AP: { ...r.Native_AP, remaining: '741.00' } }, { extra: true }]) expect(() => parseSupplierPaymentRead({ ...r, ...change }, purchase, '', 25)).toThrow()
    r.Native_AP!.final_ap = '9007199254740993.01'; r.Native_AP!.paid = '260.00'; r.Native_AP!.remaining = '9007199254740733.01'; expect(parseSupplierPaymentRead(r, purchase, '', 25).Native_AP!.remaining).toBe('9007199254740733.01')
    const p = supplierPaymentFixture(); p.inverse = { ...p.journal!, id: supplierInverseId }; r.page.rows = [p]; expect(() => parseSupplierPaymentRead(r, purchase, '', 25)).toThrow()
  })
  it('binds committed outcome to exact original request and refuses a different target or reason', () => {
    const payload = { purchase_id: purchase, payment_id: payment, review_token: 'a'.repeat(32), reason: 'Review actual payment' }
    const r = { contract_version: 'cp7.supplier-payment-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'REVERSE', request_id: payment, request_payload: payload, purchase_id: purchase, payment_id: payment, status: 'REVERSED', inverse_journal_id: supplierInverseId }
    expect(parseSupplierPaymentOutcome(r, payment, payload).payment_id).toBe(payment)
    expect(() => parseSupplierPaymentOutcome(r, payment, { ...payload, reason: 'Other intent' })).toThrow()
    expect(() => parseSupplierPaymentOutcome({ ...r, payment_id: purchase }, payment, payload)).toThrow()
  })
})
