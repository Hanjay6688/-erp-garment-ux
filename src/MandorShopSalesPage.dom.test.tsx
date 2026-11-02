// @vitest-environment jsdom
import {act} from 'react'
import {createRoot, type Root} from 'react-dom/client'
import {afterEach, beforeEach, expect, it, vi} from 'vitest'
import ConnectedSalesPage from './ConnectedSalesPage'
import {readProductionRecovery} from './productionRecovery'
import {buyerCustomer, buyerId, buyerOptions, classification, saleId, salesShopAuth, salesShopRead, storeId} from '../tests/fixtures/mandorShopSales'
const state = vi.hoisted(() => ({auth: null as unknown}))
const client = vi.hoisted(() => ({rpc: vi.fn()}))
vi.mock('./auth/AuthProvider', () => ({useAuth: () => state.auth}))
vi.mock('./lib/supabase', () => ({getUatSupabaseClient: () => client}))
let root: Root, container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, {IS_REACT_ACT_ENVIRONMENT: true}); localStorage.clear(); state.auth = salesShopAuth(); client.rpc.mockReset()
  Object.defineProperty(navigator, 'locks', {configurable: true, value: {request: async (_n: string, _o: unknown, fn: (l: unknown) => Promise<unknown>) => fn({})}})
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks') })
const flush = () => act(async () => { await new Promise(r => setTimeout(r, 0)) })
const button = (s: string) => [...container.querySelectorAll('button')].find(b => b.textContent === s)!
const input = (s: string) => container.querySelector<HTMLInputElement>(`[aria-label="${s}"]`)!
async function click(e: HTMLElement) { await act(async () => e.click()); await flush() }
async function fill(s: string, text: string) { await act(async () => { const e = input(s)
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(e, text); e.dispatchEvent(new Event('input', {bubbles: true}))
}); await flush() }
async function mount() { await act(async () => root.render(<ConnectedSalesPage initialSaleId={saleId}/>)); await flush() }
async function openMandor() {
  await mount(); await click(button('Edit draft invoice')); await click(container.querySelector<HTMLInputElement>('input[value=MANDOR]')!)
  await click(button('Cari mandor')); await click(button('M1 · Epi'))
  await fill('Alasan simpan invoice', 'Pembeli mandor dipilih dan diperiksa'); await click(input('Draft invoice sudah diperiksa'))
}
const writes = () => client.rpc.mock.calls.filter(([n]) => n === 'erp_cp7_save_mandor_shop_sale_v1')
function server() {
  const s = {customer: storeId, version: '5', effects: 0, lost: false, denied: false}
  const cache = new Map<string, unknown>()
  client.rpc.mockImplementation(async (name, p) => {
    if (name === 'erp_cp7_get_sales_v1') return {data: salesShopRead(!!p.p_query.sale_id, s.customer, s.version), error: null}
    if (name === 'erp_cp7_get_mandor_shop_customer_buyer_v1') return {data: classification(p.p_customer, p.p_sales_action), error: null}
    if (name === 'erp_cp7_get_mandor_shop_buyers_v1') return {data: buyerOptions(p.p_sales_action), error: null}
    if (!['erp_cp7_save_mandor_shop_sale_v1', 'erp_cp7_save_sale_v1'].includes(name)) throw Error('Unexpected RPC ' + name)
    if (s.denied) return {data: null, error: {status: 403, code: '42501', message: 'CP7_SALES_ACCESS_DENIED'}}
    if (!cache.has(p.p_request)) {
      s.effects++; s.version = '6'; s.customer = name === 'erp_cp7_save_mandor_shop_sale_v1' ? buyerCustomer : storeId
      cache.set(p.p_request, {contract_version: 'cp7.sales-outcome.v1', kind: 'COMMITTED_OUTCOME', action: p.p_action,
        request_id: p.p_request, sale_id: saleId, status: 'DRAFT', row_version: s.version})
    }
    return s.lost ? {data: null, error: {status: 503, message: 'Reply lost after atomic save'}} : {data: cache.get(p.p_request), error: null}
  })
  return s
}
it('sends one existing durable SALES intent to the atomic Mandor facade and retires the original draft', async () => {
  const s = server(); await openMandor(); expect(writes()).toHaveLength(0)
  await act(async () => { button('Simpan draft invoice').click(); button('Simpan draft invoice').click() }); await flush()
  expect(writes()).toHaveLength(1); expect(s.effects).toBe(1)
  expect(writes()[0][1]).toMatchObject({p_action: 'EDIT', p_expected: '5', p_payload: {sale_id: saleId,
    mandor_buyer: {contractor_id: buyerId, review_token: 'b'.repeat(64)}, items: [{qty_pcs: '1', unit_price_snapshot: '300000.00'}]}})
  expect(client.rpc.mock.calls.some(([n]) => n === 'erp_cp7_prepare_mandor_shop_buyer_v1' || n === 'erp_cp7_save_sale_v1')).toBe(false)
  expect(readProductionRecovery('disposable:actor-1').pending.SALES).toBeUndefined()
  expect(container.querySelector('[aria-label="Draft invoice"]')).toBeNull(); expect(container.textContent).toContain('Epi')
})
it('reconciles a lost atomic save through the identical UUID and document after remount and current access denial', async () => {
  const s = server(); s.lost = true; await openMandor(); await click(button('Simpan draft invoice'))
  const first = structuredClone(writes()[0][1]), pending = structuredClone(readProductionRecovery('disposable:actor-1').pending.SALES)
  expect(pending?.action).toBe('EDIT'); expect(s.effects).toBe(1)
  await act(async () => root.unmount()); root = createRoot(container); s.denied = true; s.lost = false
  await mount(); await click(button('Reconcile transaksi')); expect(writes()[1][1]).toEqual(first)
  expect(readProductionRecovery('disposable:actor-1').pending.SALES).toEqual(pending); expect(s.effects).toBe(1)
  s.denied = false; await click(button('Reconcile transaksi')); expect(writes()[2][1]).toEqual(first)
  expect(s.effects).toBe(1); expect(readProductionRecovery('disposable:actor-1').pending.SALES).toBeUndefined()
})
it('keeps an ordinary store edit on its original Native endpoint with the original exact draft fields', async () => {
  const s = server(); await mount(); await click(button('Edit draft invoice'))
  await fill('Alasan simpan invoice', 'Nota toko biasa sudah diperiksa'); await click(input('Draft invoice sudah diperiksa')); await click(button('Simpan draft invoice'))
  expect(writes()).toHaveLength(0); expect(s.effects).toBe(1)
  const calls = client.rpc.mock.calls.filter(([n]) => n === 'erp_cp7_save_sale_v1'); expect(calls).toHaveLength(1)
  expect(calls[0][1].p_payload).toMatchObject({customer_id: storeId, sale_date: '2026-11-01T02:00:00.123456Z', notes: 'Catatan awal', payment_terms: 'Kredit'})
  expect(calls[0][1].p_payload.mandor_buyer).toBeUndefined()
})
