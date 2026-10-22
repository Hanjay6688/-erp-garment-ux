// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SupplierTransferPanel from './SupplierTransferPanel'
import SupplierPaymentPanel from './SupplierPaymentPanel'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { supplierPaymentReadFixture, supplierPurchaseId } from '../tests/fixtures/supplierPayments'
import { readProductionRecovery } from './productionRecovery'
import { parseSupplierTransferOutcome, parseSupplierTransferWorkspace, supplierTransferPayload, type SupplierTransferQuery } from './supplierTransferContract'
import type { Json } from './types/database.preconnect'

const state = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn(), source: null as unknown }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => state.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => state }))
vi.mock('./TransactionSourceNavigation', () => ({ useTransactionSource: () => state.source }))
const supplier = 'e5000000-0000-4000-8000-000000000001', bank = 'd4000000-0000-4000-8000-000000000001'
const transfer = 'f6000000-0000-4000-8000-000000000001', replacement = 'f6000000-0000-4000-8000-000000000002'
const receiptId = (n: number) => 'a1000000-0000-4000-8000-' + String(n).padStart(12, '0')
const journal = (id: string, status: 'POSTED' | 'REVERSED') => ({ id, number: 'JRN-' + id.slice(-3), status, economic_date: '2026-10-01',
  accounting_date: '2026-10-01', posting_at: '2026-10-01T03:00:00Z', period_shifted: false })
let box: HTMLDivElement, root: Root
const onReceiptUpdated = vi.fn(async () => true)
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); state.rpc.mockReset(); onReceiptUpdated.mockReset().mockResolvedValue(true)
  const auth = structuredClone(recoveryIdentity); auth.identity.permissions.push('warehouse.procurement.view', 'finance.ap.view', 'finance.ap.pay'); state.auth = auth
  state.source = null
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _options: unknown, run: (lock: unknown) => Promise<unknown>) => run({}) } })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const flush = async () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
async function mount(supplierId: string | null = supplier, focus: string | null = null) {
  await act(async () => root.render(<SupplierTransferPanel supplierId={supplierId} currentPurchaseId={supplierPurchaseId} parentReady receiptRevision="REV-1"
    focusTransferId={focus} onReceiptUpdated={onReceiptUpdated}/>)); await flush()
}
const button = (name: string) => [...box.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent?.trim() === name)
async function click(name: string) { expect(button(name), name).toBeTruthy(); await act(async () => button(name)!.click()); await flush() }
async function input(label: string, value: string) {
  const e = box.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
  expect(e, label).not.toBeNull(); await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(e, value); e.dispatchEvent(new Event('input', { bubbles: true })) }); await flush()
}
async function check(label: string) { await act(async () => box.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!.click()); await flush() }
const writes = () => state.rpc.mock.calls.filter(([name]) => name === 'erp_cp7_save_supplier_transfer_v1')

/** 30 open receipts: receipt n owes n*10.00, two pages of 25. One posted transfer pays receipts 1 and 2. */
function workspace(q: SupplierTransferQuery, s: { reversed: boolean; token: string }) {
  const all = Array.from({ length: 30 }, (_, i) => i + 1)
  const own = (n: number) => q.transfer_id === transfer && !s.reversed && n <= 2 ? `${n * 5}.00` : '0.00'
  const rows = all.filter(n => !q.purchase_q || `SJ-${n}`.includes(q.purchase_q)).slice(q.purchase_offset, q.purchase_offset + 25).map(n => ({
    id: receiptId(n), number: `SJ-${n}`, physical_at: `2026-09-${String(n % 28 + 1).padStart(2, '0')}T03:00:00Z`, remaining: `${n * 10}.00`,
    release_on_correction: own(n), payable_after_release: `${n * 10 + Number(own(n))}.00` }))
  const total = all.filter(n => !q.purchase_q || `SJ-${n}`.includes(q.purchase_q)).length
  const selected = q.transfer_id === null ? null : { id: q.transfer_id, number: q.transfer_id === transfer ? 'TRS-1' : 'TRS-2', supplier_id: supplier,
    status: s.reversed ? 'REVERSED' : 'POSTED', payment_date: '2026-10-01T03:00:00Z', amount: '15.00', cash_account_id: bank, cash_name: 'Bank supplier',
    note: 'Transfer gabungan supplier', journal: journal('c3000000-0000-4000-8000-000000000101', s.reversed ? 'REVERSED' : 'POSTED'),
    inverse: s.reversed ? journal('c3000000-0000-4000-8000-000000000102', 'POSTED') : null,
    allocations: [{ purchase_id: receiptId(1), purchase_number: 'SJ-1', payment_id: 'b2000000-0000-4000-8000-000000000201', amount: '5.00' },
      { purchase_id: receiptId(2), purchase_number: 'SJ-2', payment_id: 'b2000000-0000-4000-8000-000000000202', amount: '10.00' }],
    previous_id: null, replacement_id: null }
  return { contract_version: 'cp7.supplier-transfer-workspace.v1', captured_at: '2026-10-03T05:00:00Z', supplier: { id: supplier, name: 'Supplier A' },
    can_write: (state.auth as typeof recoveryIdentity).identity.permissions.includes('finance.ap.pay'), review_token: s.token, query: q,
    receipts: { rows, total: String(total), offset: q.purchase_offset, limit: 25, next_offset: q.purchase_offset + rows.length < total ? q.purchase_offset + rows.length : null },
    cash_accounts: { rows: [{ id: bank, code: 'BANK', name: 'Bank supplier' }], total: '1', offset: 0, limit: 25, next_offset: null },
    transfers: { rows: [{ id: transfer, number: 'TRS-1', status: s.reversed ? 'REVERSED' : 'POSTED', amount: '15.00', payment_date: '2026-10-01T03:00:00Z' }], total: '1', offset: 0, limit: 25, next_offset: null },
    selected }
}
function server(opts: { lose?: boolean } = {}) {
  const s = { effects: 0, lose: Boolean(opts.lose), reversed: false, token: 'f'.repeat(32) }, cache = new Map<string, Json>()
  state.rpc.mockImplementation(async (name, args) => {
    if (name === 'erp_cp7_get_supplier_transfer_v1') return { data: workspace(args.p_query, s), error: null }
    if (name !== 'erp_cp7_save_supplier_transfer_v1') throw Error('Unexpected RPC ' + name)
    const p = args.p_payload
    if (!cache.has(args.p_request)) {
      s.effects++; s.token = 'e'.repeat(32); if (p.action === 'REVERSE') s.reversed = true
      cache.set(args.p_request, { contract_version: 'cp7.supplier-transfer-outcome.v1', kind: 'COMMITTED_OUTCOME', action: p.action, request_id: args.p_request,
        request_payload: p, supplier_id: p.supplier_id, transfer_id: p.action === 'CREATE' ? replacement : p.action === 'CORRECT' ? replacement : p.transfer_id,
        original_transfer_id: p.action === 'CREATE' ? null : p.transfer_id, status: p.action === 'REVERSE' ? 'REVERSED' : 'POSTED' })
    }
    if (s.lose) { s.lose = false; return { data: null, error: { message: 'Committed transfer reply lost' } } }
    return { data: cache.get(args.p_request), error: null }
  })
  return s
}

describe('One supplier transfer paid once and allocated to several receipts', () => {
  it('keeps choices across receipt pages, totals them exactly and sends one create command after review', async () => {
    const s = server(); await mount(); await click('Buat transfer supplier baru')
    await input('Dibayar untuk SJ-3', '12.34')
    await click('Penerimaan berikutnya'); expect(box.textContent).toContain('SJ-30')
    await click('Bayar penuh SJ-27')
    expect(box.textContent).toContain('SJ-3 · Rp12,34'); expect(box.textContent).toContain('Total transfer Rp282,34')
    expect(box.textContent).toContain('sisa utang sesudah bayar Rp17,66')
    await input('Waktu transfer supplier WIB', '2026-10-01T10:00'); await click('BANK · Bank supplier')
    await input('Keterangan transfer supplier', 'Transfer BCA dua penerimaan')
    expect(button('Sahkan transfer supplier')!.disabled).toBe(true)
    await check('Transfer supplier sudah diperiksa'); expect(button('Sahkan transfer supplier')!.disabled).toBe(false)
    await click('Sahkan transfer supplier')
    expect(writes()).toHaveLength(1); expect(s.effects).toBe(1)
    expect(writes()[0][1].p_payload).toEqual({ action: 'CREATE', supplier_id: supplier, review_token: 'f'.repeat(32), reason: 'Transfer BCA dua penerimaan',
      amount: '282.34', cash_account_id: bank, payment_date: '2026-10-01T03:00:00.000Z',
      allocations: [{ purchase_id: receiptId(3), amount: '12.34' }, { purchase_id: receiptId(27), amount: '270.00' }] })
    expect(onReceiptUpdated).toHaveBeenCalledWith(supplierPurchaseId)
  })
  it('blocks an allocation above the remaining debt, a time before arrival, and an unchecked review', async () => {
    server(); await mount(); await click('Buat transfer supplier baru')
    await input('Dibayar untuk SJ-3', '30.01'); expect(box.textContent).toContain('paling banyak sisa utang')
    await input('Waktu transfer supplier WIB', '2026-09-01T10:00'); expect(box.textContent).toContain('sesudah semua barang terpilih diterima')
    await click('BANK · Bank supplier'); await input('Keterangan transfer supplier', 'Transfer BCA dua penerimaan'); await check('Transfer supplier sudah diperiksa')
    expect(button('Sahkan transfer supplier')!.disabled).toBe(true)
    await input('Dibayar untuk SJ-3', '30.00'); await input('Waktu transfer supplier WIB', '2026-10-01T10:00'); await check('Transfer supplier sudah diperiksa')
    expect(button('Sahkan transfer supplier')!.disabled).toBe(false); expect(writes()).toHaveLength(0)
  })
  it('reverses the whole transfer only through the parent with a reason and review', async () => {
    const s = server(); await mount(); await click('Buka transfer TRS-1')
    expect(box.textContent).toContain('Kas keluar satu kali'); expect(box.textContent).toContain('SJ-2')
    await click('Batalkan transfer TRS-1'); expect(button('Balikkan transfer supplier sekarang')!.disabled).toBe(true)
    await input('Alasan pembatalan transfer supplier', 'Transfer salah rekening'); await check('Pembatalan transfer supplier sudah diperiksa')
    await click('Balikkan transfer supplier sekarang')
    expect(writes()[0][1].p_payload).toEqual({ action: 'REVERSE', supplier_id: supplier, transfer_id: transfer, review_token: 'f'.repeat(32), reason: 'Transfer salah rekening' })
    expect(s.reversed).toBe(true); expect(box.textContent).toContain('Sudah dibalik')
  })
  it('corrects a transfer from its own allocations and released debt', async () => {
    server(); await mount(null); await act(async () => root.render(<SupplierTransferPanel supplierId={supplier} currentPurchaseId={supplierPurchaseId} parentReady
      receiptRevision="REV-1" focusTransferId={transfer} onReceiptUpdated={onReceiptUpdated}/>)); await flush()
    await click('Koreksi transfer TRS-1')
    expect(box.textContent).toContain('SJ-1 · Rp5 ·'); expect(box.textContent).toContain('SJ-2 · Rp10 ·')
    await input('Dibayar untuk SJ-1', '15.00'); expect(box.textContent).toContain('SJ-1 · Rp15 · sisa utang sesudah bayar Rp0')
    await input('Keterangan transfer supplier', 'Alokasi SJ-1 dibetulkan'); await check('Transfer supplier sudah diperiksa')
    await click('Sahkan koreksi transfer supplier')
    expect(writes()[0][1].p_payload).toEqual({ action: 'CORRECT', supplier_id: supplier, transfer_id: transfer, review_token: 'f'.repeat(32), reason: 'Alokasi SJ-1 dibetulkan',
      amount: '25.00', cash_account_id: bank, payment_date: '2026-10-01T03:00:00.000Z',
      allocations: [{ purchase_id: receiptId(1), amount: '15.00' }, { purchase_id: receiptId(2), amount: '10.00' }] })
  })
  it('keeps the exact envelope after a lost reply and reconciles the same request once', async () => {
    const s = server({ lose: true }); await mount(); await click('Buat transfer supplier baru'); await click('Bayar penuh SJ-4')
    await input('Waktu transfer supplier WIB', '2026-10-01T10:00'); await click('BANK · Bank supplier')
    await input('Keterangan transfer supplier', 'Transfer BCA satu penerimaan'); await check('Transfer supplier sudah diperiksa')
    await click('Sahkan transfer supplier'); const first = structuredClone(writes()[0][1]); expect(s.effects).toBe(1)
    expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_TRANSFER?.action).toBe('CREATE')
    await act(async () => root.unmount()); root = createRoot(box); await mount(null); await click('Periksa status transfer supplier')
    expect(writes()[1][1]).toEqual(first); expect(s.effects).toBe(1)
    expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_TRANSFER).toBeUndefined()
  })
  it('offers no writing without the current pay right', async () => {
    const a = state.auth as typeof recoveryIdentity; a.identity.permissions = a.identity.permissions.filter(p => p !== 'finance.ap.pay')
    server(); await mount(); expect(button('Buat transfer supplier baru')).toBeUndefined()
    await click('Buka transfer TRS-1'); expect(button('Batalkan transfer TRS-1')).toBeUndefined(); expect(writes()).toHaveLength(0)
  })
})

describe('A receipt payment that belongs to a transfer', () => {
  it('names its transfer, offers to open it, and hides individual edit and reversal', async () => {
    const read = supplierPaymentReadFixture(0), row = read.page.rows[0]
    const child = { ...row, transfer: { id: transfer, number: 'TRS-1', amount: '15.00', status: 'POSTED', allocations_count: '2' } }
    read.page.rows = [child as typeof row, ...read.page.rows.slice(1)]
    state.rpc.mockImplementation(async name => name === 'erp_cp7_get_supplier_payments_v1' ? { data: read, error: null } : { data: null, error: { message: 'unexpected' } })
    const opened = vi.fn()
    await act(async () => root.render(<SupplierPaymentPanel purchaseId={supplierPurchaseId} parentReady receiptRevision="REV-1" onReceiptUpdated={onReceiptUpdated} onOpenTransfer={opened}/>)); await flush()
    expect(box.textContent).toContain('Bagian dari transfer TRS-1'); expect(button(`Edit pembayaran supplier ${row.number}`)).toBeUndefined()
    expect(button(`Tinjau pembatalan ${row.number}`)).toBeUndefined()
    await click('Buka transfer TRS-1'); expect(opened).toHaveBeenCalledWith(transfer)
  })
})

describe('Transfer contract', () => {
  const q: SupplierTransferQuery = { supplier_id: supplier, transfer_id: transfer, purchase_q: '', purchase_offset: 0, bank_q: '', bank_offset: 0, transfer_offset: 0 }
  const s = { reversed: false, token: 'f'.repeat(32) }
  it('binds the workspace to the query and checks exact allocation totals and released debt', () => {
    expect(parseSupplierTransferWorkspace(workspace(q, s), q).selected?.allocations).toHaveLength(2)
    expect(() => parseSupplierTransferWorkspace(workspace(q, s), { ...q, purchase_offset: 25 })).toThrow()
    const bad = workspace(q, s); bad.selected!.amount = '15.01'; expect(() => parseSupplierTransferWorkspace(bad, q)).toThrow()
    const released = workspace(q, s); released.receipts.rows[0].release_on_correction = '4.00'; released.receipts.rows[0].payable_after_release = '14.00'
    expect(() => parseSupplierTransferWorkspace(released, q)).toThrow()
    expect(() => parseSupplierTransferWorkspace({ ...workspace(q, s), extra: 1 }, q)).toThrow()
  })
  it('builds the payload in exact cents and refuses duplicates', () => {
    const base = { action: 'CREATE' as const, supplier_id: supplier, review_token: 'f'.repeat(32), reason: 'Transfer gabungan', cash_account_id: bank, payment_date: '2026-10-01T03:00:00.000Z' }
    expect(supplierTransferPayload(base, [{ purchase_id: receiptId(2), amount: '0.20' }, { purchase_id: receiptId(1), amount: '0.10' }])?.amount).toBe('0.30')
    expect(supplierTransferPayload(base, [{ purchase_id: receiptId(1), amount: '0.10' }, { purchase_id: receiptId(1), amount: '0.20' }])).toBeNull()
    expect(supplierTransferPayload(base, [{ purchase_id: receiptId(1), amount: '0.00' }])).toBeNull()
  })
  it('accepts only the outcome of the exact request', () => {
    const payload = { action: 'REVERSE', supplier_id: supplier, transfer_id: transfer, review_token: 'f'.repeat(32), reason: 'Transfer salah rekening' }
    const outcome = { contract_version: 'cp7.supplier-transfer-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'REVERSE', request_id: replacement, request_payload: payload,
      supplier_id: supplier, transfer_id: transfer, original_transfer_id: transfer, status: 'REVERSED' }
    expect(parseSupplierTransferOutcome(outcome, replacement, payload).status).toBe('REVERSED')
    expect(() => parseSupplierTransferOutcome({ ...outcome, status: 'POSTED' }, replacement, payload)).toThrow()
    expect(() => parseSupplierTransferOutcome(outcome, transfer, payload)).toThrow()
  })
})
