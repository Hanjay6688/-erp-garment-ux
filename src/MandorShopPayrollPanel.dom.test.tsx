// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import MandorShopPayrollPanel from './MandorShopPayrollPanel'
import { shopAllocation, shopId, shopMandor, shopPayroll, shopWorkspace } from '../tests/fixtures/mandorShop'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { clearProductionEnvelope, persistProductionEnvelope, productionKey, readProductionRecovery } from './productionRecovery'
const state = vi.hoisted(() => ({ auth: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => state.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const onReload = vi.fn(async () => true), onTarget = vi.fn(), onRetire = vi.fn()
const scope = 'disposable:actor-1', domain = 'MANDOR_SHOP_ALLOCATION'
let root: Root, container: HTMLDivElement
const show = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const close = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); client.rpc.mockReset()
  onReload.mockReset().mockResolvedValue(true); onTarget.mockReset(); onRetire.mockReset()
  const auth = structuredClone(recoveryIdentity); auth.identity.permissions = ['finance.payroll.view', 'finance.payroll.approve', 'finance.ar.view']; state.auth = auth
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _options: unknown, use: (v: unknown) => Promise<unknown>) => use({}) } })
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.setAttribute('open', '') } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.removeAttribute('open') } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => {
  await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks()
  for (const [name, original] of [['showModal', show], ['close', close]] as const) {
    if (original) Object.defineProperty(HTMLDialogElement.prototype, name, original); else Reflect.deleteProperty(HTMLDialogElement.prototype, name)
  }
})
const button = (text: string) => [...container.querySelectorAll('button')].find(b => b.textContent === text)
const flush = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
async function mount(ready = true, payroll: string | null = shopPayroll, contractor: string | null = shopMandor) {
  await act(async () => root.render(<MandorShopPayrollPanel payrollId={payroll} contractorId={contractor} payrollNumber="PAY-EPI-W2" contractorName="Epi"
    parentReady={ready} readRevision={0} onReload={onReload} onTarget={onTarget} onRetire={onRetire}/>)); await flush()
}
async function click(text: string) { await act(async () => button(text)!.click()); await flush() }
async function open() { await click('Pasang tagihan belanja') }
async function choose() {
  await click('Pilih nota INV-EPI-01'); await act(async () => container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click()); await flush()
}
const writes = () => client.rpc.mock.calls.filter(([name]) => name === 'erp_cp7_save_mandor_shop_allocation_v1')
function server() {
  const s = { current: shopWorkspace(), effects: 0, lost: false, denied: false, mismatch: false, failRead: false }
  const cache = new Map<string, unknown>()
  client.rpc.mockImplementation(async (name, args) => {
    if (name === 'erp_cp7_get_mandor_shop_payroll_v1') return s.failRead ? { data: null, error: { status: 503, message: 'Read unavailable' } } : { data: structuredClone(s.current), error: null }
    if (name !== 'erp_cp7_save_mandor_shop_allocation_v1') throw Error('Unexpected RPC ' + name)
    if (cache.has(args.p_request) && s.denied) return { data: null, error: { status: 403, code: '42501', message: 'CP7_MANDOR_SHOP_ACCESS_DENIED' } }
    if (!cache.has(args.p_request)) {
      s.effects++; s.current = shopWorkspace(args.p_action === 'RESERVE'); s.current.cards[0].review_token = 'b'.repeat(64)
      cache.set(args.p_request, { contract_version: 'cp7.mandor-shop-allocation-outcome.v1', kind: 'COMMITTED_OUTCOME', action: args.p_action,
        request_id: s.mismatch ? shopId(99) : args.p_request, payroll_id: args.p_payload.payroll_id, sale_id: args.p_payload.sale_id,
        allocation_id: shopAllocation, net_payable: s.current.net_payable_preview, invoice_settled_by_this_command: false })
    }
    return s.lost ? { data: null, error: { status: 503, message: 'Reply lost after commit' } } : { data: cache.get(args.p_request), error: null }
  })
  return s
}
it('opens one source read only on request and binds it to the selected mandor/week', async () => {
  server(); await mount(); expect(client.rpc).not.toHaveBeenCalled(); await open()
  expect(client.rpc).toHaveBeenCalledOnce(); expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_mandor_shop_payroll_v1', { p_payroll: shopPayroll, p_after: null })
  expect(container.textContent).toContain('2026-11-09 sampai 2026-11-15'); expect(writes()).toHaveLength(0)
})
it('stores one immutable intent and refreshes both the parent and the same invoice cards after reservation', async () => {
  const s = server(); await mount(); await open(); await choose(); await click('Pasang tagihan ke payroll')
  expect(writes()).toHaveLength(1); expect(writes()[0][1]).toMatchObject({ p_action: 'RESERVE', p_payload: { payroll_id: shopPayroll, amount: '300000.00' } })
  expect(writes()[0][1].p_payload.contractor_id).toBeUndefined(); expect(s.effects).toBe(1)
  expect(onReload).toHaveBeenCalled(); expect(onTarget).toHaveBeenCalledWith(shopPayroll); expect(onRetire).toHaveBeenCalled()
  expect(readProductionRecovery(scope).pending).toEqual({}); expect(container.textContent).toContain('Rp1.700.000,00')
})
it('a lost committed reply retires every balance; remount replays the exact old request once', async () => {
  const s = server(); await mount(); await open(); await choose(); s.lost = true; await click('Pasang tagihan ke payroll')
  const original = structuredClone(writes()[0][1]); expect(s.effects).toBe(1); expect(container.textContent).not.toContain('Rp')
  expect(readProductionRecovery(scope).pending[domain]?.id).toBe(original.p_request)
  await act(async () => root.unmount()); root = createRoot(container); s.lost = false; const calls = client.rpc.mock.calls.length
  await mount(true, null, null); expect(client.rpc.mock.calls.length).toBe(calls); await click('Periksa status pemasangan tagihan')
  expect(writes()[1][1]).toEqual(original); expect(s.effects).toBe(1); expect(onTarget).toHaveBeenCalledWith(shopPayroll)
  expect(readProductionRecovery(scope).pending).toEqual({})
})
it('a permission-denied replay retains the original uncertainty instead of clearing its request', async () => {
  const s = server(); await mount(); await open(); await choose(); s.lost = true; await click('Pasang tagihan ke payroll')
  const old = readProductionRecovery(scope).pending[domain]; s.lost = false; s.denied = true; await click('Periksa status pemasangan tagihan')
  expect(readProductionRecovery(scope).pending[domain]).toEqual(old); expect(s.effects).toBe(1); expect(container.textContent).not.toContain('Rp')
})
it('a mismatched success request cannot clear the intent or expose balances', async () => {
  const s = server(); s.mismatch = true; await mount(); await open(); await choose(); await click('Pasang tagihan ke payroll')
  expect(readProductionRecovery(scope).pending[domain]).toBeDefined(); expect(container.textContent).not.toContain('Rp'); expect(s.effects).toBe(1)
})
it('a failed parent refresh after commit blocks new writes until an authoritative reload succeeds', async () => {
  const s = server(); await mount(); await open(); await choose(); onReload.mockResolvedValue(false); await click('Pasang tagihan ke payroll')
  expect(s.effects).toBe(1); expect(readProductionRecovery(scope).pending).toEqual({}); expect(container.textContent).not.toContain('Rp')
  expect(container.textContent).toContain('Aksi sudah tersimpan'); onReload.mockResolvedValue(true); await click('Muat ulang tagihan')
  expect(onReload).toHaveBeenCalledTimes(2)
  expect(container.textContent).toContain('Rp1.700.000,00'); expect(s.effects).toBe(1)
})
it('a foreign pending request retires a held read even if it clears before the reply arrives', async () => {
  server(); let reply: ((v: unknown) => void) | undefined
  client.rpc.mockImplementationOnce(() => new Promise(resolve => { reply = resolve }))
  await mount(); await open()
  const input = { action: 'POST', payload: { sale_id: shopId(88) }, expectedVersion: 1 }
  const old = { ...input, id: shopId(87), createdAt: '2026-11-02T08:00:00Z', fingerprint: JSON.stringify(input) }
  await act(async () => { persistProductionEnvelope(scope, 'SALES', old); clearProductionEnvelope(scope, 'SALES', old) })
  await act(async () => reply!({ data: shopWorkspace(), error: null })); await flush()
  expect(container.textContent).not.toContain('Rp'); await click('Muat ulang tagihan'); expect(container.textContent).toContain('Rp2.000.000,00')
})
it('a corrupt recovery record is preserved and prevents source or command requests', async () => {
  server(); const key = productionKey(scope, domain); localStorage.setItem(key, '{'); await mount()
  expect(localStorage.getItem(key)).toBe('{'); expect(client.rpc).not.toHaveBeenCalled(); expect(button('Pasang tagihan belanja')!.disabled).toBe(true)
})
it('without Web Locks the cards remain readable but no reservation action is offered', async () => {
  server(); Reflect.deleteProperty(navigator, 'locks'); await mount(); await open()
  expect(container.textContent).toContain('Rp2.000.000,00'); expect(button('Pilih nota INV-EPI-01')).toBeUndefined(); expect(writes()).toHaveLength(0)
})
it('view-only users read cards without change controls and the selected source retires immediately', async () => {
  const s = server(); s.current.can_change = false
  const auth = state.auth as typeof recoveryIdentity; auth.identity.permissions = ['finance.payroll.view', 'finance.ar.view']
  await mount(); await open(); expect(button('Pilih nota INV-EPI-01')).toBeUndefined(); expect(container.textContent).toContain('Hak mengubah potongan diperlukan')
  await mount(false, shopId(8), null); expect(container.textContent).not.toContain('Rp'); expect(writes()).toHaveLength(0)
})
