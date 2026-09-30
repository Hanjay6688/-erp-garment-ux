// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import MiscFinancePanel from './MiscFinancePanel'
import { parseMiscDocument, parseMiscRead, parseMiscOutcome, type MiscQuery, type MiscRead, type MiscDocument } from './miscFinanceContract'
import { persistProductionEnvelope, productionKey, readProductionRecovery } from './productionRecovery'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import type { getUatSupabaseClient } from './lib/supabase'
const state = vi.hoisted(() => ({ auth: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => state.auth }))
const id = '11111111-1111-4111-8111-111111111111', categoryId = '22222222-2222-4222-8222-222222222222', cashId = '33333333-3333-4333-8333-333333333333', originalId = '44444444-4444-4444-8444-444444444444', inverseId = '55555555-5555-4555-8555-555555555555'
const category = { id: categoryId, code: 'OTHER', name: 'Biaya native', type: 'OTHER_EXPENSE' as const, account_id: categoryId, account_code: '5900', account_name: 'Biaya lain', eligible: true, review_token: 'a'.repeat(32) }
const cash = { id: cashId, code: 'CASH', name: 'Kas native', kind: 'CASH', account_id: cashId, account_code: '1000', account_name: 'Kas', eligible: true, review_token: 'b'.repeat(32) }
const query: MiscQuery = { q: '', status: null, transaction_id: null, offset: 0, category_offset: 0, cash_offset: 0 }
function doc(amount = '12.34', status: MiscDocument['status'] = 'DRAFT'): MiscDocument {
  const original = { id: originalId, number: 'JRN-ORIGINAL', status: status === 'REVERSED' ? 'REVERSED' as const : 'POSTED' as const, reversal_of_id: null, economic_date: '2020-01-02', transaction_date: '2020-01-02', posting_at: '2020-01-02T08:00:00Z', period_shifted: false, debit: amount, credit: amount }
  return { id, number: 'MISC-NATIVE', type: 'OTHER_EXPENSE', category_id: categoryId, category_name: category.name, category_eligible: true, cash_account_id: cashId, cash_account_name: cash.name, cash_eligible: true, physical_at: '2020-01-02T08:00:00Z', amount, counterparty_name: null, reference_number: null, notes: null, status, review_token: (status === 'DRAFT' ? 'c' : status === 'POSTED' ? 'd' : 'e').repeat(32), category_source: category, cash_source: cash, journals: status === 'DRAFT' ? [] : status === 'POSTED' ? [original] : [original, { ...original, id: inverseId, number: 'JRN-INVERSE', status: 'POSTED', reversal_of_id: originalId, economic_date: '2020-01-03', transaction_date: '2020-01-03', posting_at: '2020-01-03T08:00:00Z' }] }
}
function read(q: MiscQuery, d: MiscDocument | null = null): MiscRead {
  const page = (rows: unknown[], offset: number) => ({ rows, total: String(rows.length), offset, limit: 25 as const, next_offset: null })
  return { contract_version: 'cp7.misc-read.v1', captured_at: '2026-09-30T03:00:00Z', scope: 'CURRENT_NATIVE_MISC_FINANCE_DOCUMENTS', query: { q: q.q, status: q.status, transaction_id: q.transaction_id }, page: page(d ? [d] : [], q.offset) as MiscRead['page'], categories: page([category], q.category_offset) as MiscRead['categories'], cash_accounts: page([cash], q.cash_offset) as MiscRead['cash_accounts'], detail: q.transaction_id ? d : null }
}
const onChanged = vi.fn(async () => true), onRetire = vi.fn()
let root: Root, container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); client.rpc.mockReset(); onChanged.mockClear(); onRetire.mockClear()
  const auth = structuredClone(recoveryIdentity); auth.identity.permissions.push('finance.journal.view', 'finance.cash.view'); state.auth = auth
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _opts: unknown, fn: (lock: unknown) => Promise<unknown>) => fn({}) } })
  container = globalThis.document.createElement('div'); globalThis.document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const flush = async () => act(async () => { await new Promise(r => setTimeout(r, 0)) })
async function mount() { await act(async () => root.render(<MiscFinancePanel client={client as unknown as ReturnType<typeof getUatSupabaseClient>} onChanged={onChanged} onRetire={onRetire}/>)); await flush() }
const button = (text: string) => [...container.querySelectorAll('button')].find(b => b.textContent === text)!
async function click(text: string) { await act(async () => button(text).click()); await flush() }
async function fill(label: string, value: string) {
  await act(async () => { const input = container.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[aria-label="${label}"]`)!; Object.getOwnPropertyDescriptor(input.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value')!.set!.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true })) }); await flush()
}
async function check(label: string) { await act(async () => container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!.click()); await flush() }
const writes = () => client.rpc.mock.calls.filter(([name]) => name === 'erp_cp7_save_misc_finance_v1')
function server(initial: MiscDocument | null = null) {
  const s = { doc: initial, lost: false, failRead: false, effects: 0, mismatch: false }, cache = new Map<string, unknown>()
  client.rpc.mockImplementation(async (name, args) => {
    if (name === 'erp_cp7_get_misc_finance_v1') return s.failRead ? { data: null, error: { message: 'Sumber tidak tersedia' } } : { data: read({ ...query, ...args.p_query }, s.doc), error: null }
    if (name !== 'erp_cp7_save_misc_finance_v1') throw Error('Unexpected ' + name)
    if (!cache.has(args.p_request)) {
      s.effects++; const p = args.p_payload, status = args.p_action === 'SAVE' ? 'DRAFT' : args.p_action === 'POST' ? 'POSTED' : 'REVERSED'
      s.doc = doc(args.p_action === 'SAVE' ? p.amount : s.doc!.amount, status)
      if (args.p_action === 'SAVE') Object.assign(s.doc, { number: p.transaction_number, type: p.transaction_type, physical_at: p.physical_at, counterparty_name: p.counterparty_name, reference_number: p.reference_number, notes: p.notes })
      cache.set(args.p_request, { contract_version: 'cp7.misc-outcome.v1', kind: 'COMMITTED_OUTCOME', action: args.p_action, request_id: s.mismatch ? inverseId : args.p_request, transaction_id: id, document: structuredClone(s.doc) })
    }
    return s.lost ? { data: null, error: { status: 503, message: 'Lost reply' } } : { data: cache.get(args.p_request), error: null }
  }); return s
}
async function prepare(amount = '12.34') {
  await click('Buat transaksi lain'); await fill('Nomor transaksi lain', 'MISC-REVIEWED'); await fill('Waktu transaksi lain WIB', '2020-01-02T15:00'); await fill('Nominal transaksi lain', amount)
  await act(async () => container.querySelector<HTMLElement>('[data-misc-category-id]')!.click()); await act(async () => container.querySelector<HTMLElement>('[data-misc-cash-id]')!.click())
  await fill('Alasan simpan transaksi lain', 'Sumber dan nominal sudah diperiksa'); await check('Draft transaksi lain sudah diperiksa')
}
async function prepareAction() { await fill('Alasan posting atau pembalikan transaksi lain', 'Sumber dan dampak kas sudah diperiksa'); await check('Transaksi lain untuk posting atau pembalikan sudah diperiksa') }
it('rejects numeric money, missing or contradictory native journals, duplicate sources and wrong selected scope', () => {
  expect(parseMiscDocument(doc('9007199254740993.01')).amount).toBe('9007199254740993.01')
  const numeric = doc(); Object.assign(numeric, { amount: 12.34 }); expect(() => parseMiscDocument(numeric)).toThrow()
  const incomplete = doc('12.34', 'POSTED'); incomplete.journals = []; expect(() => parseMiscDocument(incomplete)).toThrow()
  const inverse = doc('12.34', 'REVERSED'); inverse.journals[1].reversal_of_id = cashId; expect(() => parseMiscDocument(inverse)).toThrow()
  const wrong = doc('12.34', 'POSTED'); wrong.journals[0].credit = '12.35'; expect(() => parseMiscDocument(wrong)).toThrow()
  const duplicate = read(query, doc()); duplicate.page.rows.push(duplicate.page.rows[0]); duplicate.page.total = '2'; expect(() => parseMiscRead(duplicate, query)).toThrow()
  expect(() => parseMiscRead(read(query), { ...query, transaction_id: id })).toThrow()
  expect(() => parseMiscOutcome({}, id, 'POST', { transaction_id: id })).toThrow()
})
it('saves an explicitly reviewed exact large draft with native category/cash tokens and no invented revision', async () => {
  const s = server(); await mount(); await prepare('9007199254740993.01'); expect(button('Simpan draft transaksi lain').disabled).toBe(false); await click('Simpan draft transaksi lain')
  expect(writes()[0][1]).toMatchObject({ p_action: 'SAVE', p_expected: null, p_payload: { amount: '9007199254740993.01', physical_at: '2020-01-02T08:00:00.000Z', category_review_token: category.review_token, cash_review_token: cash.review_token, transaction_id: null, review_token: null } })
  expect(s.doc?.journals).toHaveLength(0); expect(container.textContent).toContain('Rp9.007.199.254.740.993,01'); expect(onChanged).toHaveBeenCalledOnce(); expect(onRetire).toHaveBeenCalled()
})
it('posts only a fresh reviewed draft and displays both original and linked dated inverse after reversal', async () => {
  const s = server(doc()); await mount(); await act(async () => container.querySelector<HTMLElement>('[data-misc-id]')!.click()); await flush()
  expect(button('Posting transaksi lain').disabled).toBe(true); await prepareAction(); await click('Posting transaksi lain')
  expect(writes()[0][1].p_payload.review_token).toBe('c'.repeat(32)); expect(container.querySelectorAll('[data-misc-journal-id]')).toHaveLength(1)
  await prepareAction(); await click('Balikkan transaksi lain'); expect(s.doc?.status).toBe('REVERSED'); expect(container.querySelectorAll('[data-misc-journal-id]')).toHaveLength(2); expect(container.textContent).toContain('2020-01-02'); expect(container.textContent).toContain('2020-01-03'); expect(button('Ubah draft transaksi lain')).toBeUndefined()
})
it('editing a draft sends the complete native review token and changes to the form retire confirmation', async () => {
  server(doc()); await mount(); await act(async () => container.querySelector<HTMLElement>('[data-misc-id]')!.click()); await flush(); await click('Ubah draft transaksi lain')
  await fill('Alasan simpan transaksi lain', 'Perbaikan sumber draft'); await check('Draft transaksi lain sudah diperiksa'); await fill('Nominal transaksi lain', '22.22'); expect(button('Simpan draft transaksi lain').disabled).toBe(true)
  await check('Draft transaksi lain sudah diperiksa'); await click('Simpan draft transaksi lain'); expect(writes()[0][1].p_payload).toMatchObject({ transaction_id: id, review_token: 'c'.repeat(32), amount: '22.22' })
})
it('keeps a committed POST with lost reply in durable recovery and remount replays the identical envelope once', async () => {
  const s = server(doc()); await mount(); await act(async () => container.querySelector<HTMLElement>('[data-misc-id]')!.click()); await flush(); await prepareAction(); s.lost = true; await click('Posting transaksi lain')
  const original = structuredClone(writes()[0][1]); expect(readProductionRecovery('disposable:actor-1').pending.FINANCE_MISC?.id).toBe(original.p_request); expect(container.querySelectorAll('[data-misc-id]')).toHaveLength(0)
  await act(async () => root.unmount()); root = createRoot(container); s.lost = false; await mount(); await click('Reconcile transaksi'); expect(writes()[1][1]).toEqual(original); expect(s.effects).toBe(1); expect(readProductionRecovery('disposable:actor-1').pending).toEqual({}); expect(container.querySelectorAll('[data-misc-journal-id]')).toHaveLength(1)
})
it('an amount-only draft edit preserves the native timestamp seconds and microseconds', async () => {
  const original = doc(); original.physical_at = '2020-01-02T08:00:59.123456+00:00'; server(original); await mount(); await act(async () => container.querySelector<HTMLElement>('[data-misc-id]')!.click()); await flush(); await click('Ubah draft transaksi lain')
  await fill('Nominal transaksi lain', '22.22'); await fill('Alasan simpan transaksi lain', 'Nominal diperbaiki waktu sumber tetap'); await check('Draft transaksi lain sudah diperiksa'); await click('Simpan draft transaksi lain')
  expect(writes()[0][1].p_payload.physical_at).toBe(original.physical_at)
})
it('a foreign pending transaction freezes the financial source and prevents a new misc writer', async () => {
  server(doc()); await mount(); const input = { action: 'POST', payload: { sale_id: id }, expectedVersion: 1 }, envelope = { ...input, fingerprint: JSON.stringify(input), id: originalId, createdAt: '2026-09-30T03:00:00Z' }
  await act(async () => { expect(persistProductionEnvelope('disposable:actor-1', 'SALES', envelope)).toBe(true) }); await flush(); expect(container.querySelectorAll('[data-misc-id]')).toHaveLength(0); expect(container.textContent).toContain('Penjualan & Invoice'); expect(writes()).toHaveLength(0)
})
it('failed or stale reads retire all native money and cannot reopen the form or a writer', async () => {
  const s = server(doc()); await mount(); s.failRead = true; await click('Muat ulang transaksi lain'); expect(container.textContent).toContain('Sumber tidak tersedia'); expect(container.textContent).not.toContain('Rp'); expect(button('Buat transaksi lain')).toBeUndefined(); expect(writes()).toHaveLength(0)
})
it('a wrong success UUID remains uncertain and preserves the original recovery envelope', async () => {
  const s = server(); await mount(); await prepare(); s.mismatch = true; await click('Simpan draft transaksi lain'); expect(readProductionRecovery('disposable:actor-1').pending.FINANCE_MISC).toBeDefined(); expect(container.textContent).toContain('UUID/action'); expect(container.querySelectorAll('[data-misc-id]')).toHaveLength(0)
})
it('a failed post-commit refresh keeps the completed result and prevents another writer until a fresh read succeeds', async () => {
  const s = server(); await mount(); await prepare(); s.failRead = true; await click('Simpan draft transaksi lain')
  expect(s.effects).toBe(1); expect(readProductionRecovery('disposable:actor-1').pending).toEqual({}); expect(container.textContent).toContain('Aksi sudah tersimpan'); expect(container.textContent).toContain('MISC-REVIEWED'); expect(container.querySelectorAll('[data-misc-id]')).toHaveLength(0); expect(button('Buat transaksi lain')).toBeUndefined()
  s.failRead = false; await click('Muat ulang transaksi lain'); expect(button('Buat transaksi lain').disabled).toBe(false); expect(s.effects).toBe(1)
})
it('a late response from an old actor cannot repaint the new actor financial source', async () => {
  const s = server(doc('20.02')); let oldResolve: ((v: unknown) => void) | null = null
  client.rpc.mockImplementationOnce(() => new Promise(resolve => { oldResolve = resolve })); await mount()
  const auth = structuredClone(state.auth) as typeof recoveryIdentity; auth.identity.profile.id = 'actor-2'; state.auth = auth; await mount(); await act(async () => oldResolve!({ data: read(query, doc('10.01')), error: null })); await flush()
  expect(container.textContent).toContain('Rp20,02'); expect(container.textContent).not.toContain('Rp10,01'); expect(s.effects).toBe(0)
})
it('requires the native Owner/Admin role and both current permissions without issuing a read or writer RPC', async () => {
  server(); const auth = state.auth as typeof recoveryIdentity; auth.identity.profile.role = 'STAFF'; await mount(); expect(container.textContent).toContain('Owner atau Admin'); expect(client.rpc).not.toHaveBeenCalled()
  auth.identity.profile.role = 'OWNER'; auth.identity.permissions = ['finance.journal.view']; await mount(); expect(client.rpc).not.toHaveBeenCalled()
})
it('corrupt misc recovery storage is retained and blocks all new writing', async () => {
  server(); const key = productionKey('disposable:actor-1', 'FINANCE_MISC'); localStorage.setItem(key, '{'); await mount(); expect(localStorage.getItem(key)).toBe('{'); expect(button('Buat transaksi lain')).toBeUndefined(); expect(writes()).toHaveLength(0)
})
