// @vitest-environment jsdom
import {act} from 'react'
import {createRoot, type Root} from 'react-dom/client'
import {afterEach, beforeEach, expect, it, vi} from 'vitest'
import SalesDraftPanel from './SalesDraftPanel'
import {buyerCustomer, buyerId, buyerOptions, classification, otherBuyer, salesShopAuth, shopDraft, storeId} from '../tests/fixtures/mandorShopSales'
const state = vi.hoisted(() => ({auth: null as unknown}))
const client = vi.hoisted(() => ({rpc: vi.fn()}))
vi.mock('./auth/AuthProvider', () => ({useAuth: () => state.auth}))
vi.mock('./lib/supabase', () => ({getUatSupabaseClient: () => client}))
let root: Root, container: HTMLDivElement, alive: boolean
const saved = vi.fn(), ticket = {sequence: 1, scope: 'sales', signature: 'same', session: {}}
const fence = {currentReadTicket: () => alive ? ticket : null, isReadCurrent: () => alive}
beforeEach(() => {
  Object.assign(globalThis, {IS_REACT_ACT_ENVIRONMENT: true}); state.auth = salesShopAuth(); alive = true; saved.mockReset(); client.rpc.mockReset()
  client.rpc.mockImplementation(async (name, p) => {
    if (name === 'erp_cp7_get_mandor_shop_customer_buyer_v1') return {data: classification(p.p_customer, p.p_sales_action), error: null}
    if (name === 'erp_cp7_get_mandor_shop_buyers_v1') return {data: buyerOptions(p.p_sales_action), error: null}
    if (name === 'erp_cp7_get_sales_form_v1') return {data: {contract_version: 'cp7.sales-form-options.v1', kind: 'CUSTOMER',
      physical_at: p.p_query.physical_at, location_id: null, availability_basis: 'CURRENT_AVAILABLE_NOT_HISTORICAL_STOCK',
      rows: [{id: storeId, code: 'T1', name: 'Toko Epi'}], total: '1', offset: 0, limit: 25, next_offset: null}, error: null}
    throw Error('Unexpected early write ' + name)
  })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove() })
const flush = () => act(async () => { await new Promise(r => setTimeout(r, 0)) })
const button = (text: string) => [...container.querySelectorAll('button')].find(b => b.textContent === text)!
const input = (label: string) => container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
async function click(e: HTMLElement) { await act(async () => e.click()); await flush() }
async function fill(label: string, text: string) { await act(async () => {
  const e = input(label); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(e, text); e.dispatchEvent(new Event('input', {bubbles: true}))
}); await flush() }
async function mount(customer = storeId) { await act(async () => root.render(<SalesDraftPanel initial={shopDraft(customer)} locked={false} stale={false} readFence={fence} onSave={saved} onClose={() => {}}/>)); await flush() }
async function choose(second = false) {
  await click(container.querySelector<HTMLInputElement>('input[value=MANDOR]')!); await click(button('Cari mandor'))
  await click(button(second ? 'M2 · Epi' : 'M1 · Epi'))
}
async function review() { await fill('Alasan simpan invoice', 'Pembeli dan nilai telah diperiksa'); await click(input('Draft invoice sudah diperiksa')) }
it('preserves unsaved quantity, exact price, dates and notes while selecting an unmapped same-name Mandor', async () => {
  await mount(); await fill('Jumlah invoice 1', '2'); await fill('Harga invoice 1', '150000.01'); await choose(true); await review(); await click(button('Simpan draft invoice'))
  expect(saved).toHaveBeenCalledOnce(); const [action, p, version] = saved.mock.calls[0]
  expect(action).toBe('EDIT'); expect(version).toBe('5'); expect(p.customer_id).toBeNull()
  expect(p.mandor_buyer).toEqual({contractor_id: otherBuyer, review_token: 'b'.repeat(64)})
  expect(p.sale_date).toBe(shopDraft().physical_at); expect(p.items[0]).toMatchObject({qty_pcs: '2', unit_price_snapshot: '150000.01', notes: 'Catatan barang'})
  expect(client.rpc.mock.calls.every(([name]) => !name.startsWith('erp_cp7_prepare_') && !name.startsWith('erp_cp7_save_'))).toBe(true)
})
it('classifies an existing Mandor draft with EDIT authority and keeps its explicit mapped customer', async () => {
  await mount(buyerCustomer); expect(container.querySelector<HTMLInputElement>('input[value=MANDOR]')!.checked).toBe(true)
  await review(); await click(button('Simpan draft invoice')); const [, p] = saved.mock.calls[0]
  expect(p.customer_id).toBe(buyerCustomer); expect(p.mandor_buyer.contractor_id).toBe(buyerId)
  expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_mandor_shop_customer_buyer_v1', {p_sales_action: 'EDIT', p_customer: buyerCustomer})
})
it('clears the selected buyer and review on category changes while preserving invoice items for an ordinary store save', async () => {
  await mount(); await fill('Jumlah invoice 1', '3'); await choose(); await review()
  await click(container.querySelector<HTMLInputElement>('input[value=TOKO]')!)
  expect(input('Jumlah invoice 1').value).toBe('3'); expect(input('Draft invoice sudah diperiksa').checked).toBe(false); expect(button('Simpan draft invoice').disabled).toBe(true)
  await click(button('Cari pelanggan draft')); await click(container.querySelector<HTMLElement>('[aria-label="Pilih pelanggan invoice"] .cproc-receipt')!)
  await click(input('Draft invoice sudah diperiksa')); await click(button('Simpan draft invoice'))
  expect(saved.mock.calls[0][1].customer_id).toBe(storeId); expect(saved.mock.calls[0][1].mandor_buyer).toBeUndefined()
})
it('refuses a mismatched initial classification until the same draft buyer is read successfully', async () => {
  client.rpc.mockResolvedValueOnce({data: classification(buyerCustomer), error: null}); await mount(); await review()
  expect(button('Simpan draft invoice').disabled).toBe(true); expect(saved).not.toHaveBeenCalled()
  await click(button('Baca ulang pembeli draft tersimpan')); expect(input('Draft invoice sudah diperiksa').checked).toBe(false)
  await click(input('Draft invoice sudah diperiksa')); await click(button('Simpan draft invoice')); expect(saved).toHaveBeenCalledOnce()
})
it('does not adopt a late master response after the shared invoice authority is retired', async () => {
  await mount(); await click(container.querySelector<HTMLInputElement>('input[value=MANDOR]')!)
  let finish!: (v: unknown) => void; client.rpc.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  await click(button('Cari mandor')); alive = false
  await act(async () => finish({data: buyerOptions(), error: null})); await flush()
  expect(button('M1 · Epi')).toBeUndefined(); expect(button('Simpan draft invoice').disabled).toBe(true); expect(saved).not.toHaveBeenCalled()
})
it('does not save a previously selected Mandor after its parent read ticket becomes stale', async () => {
  await mount(); await choose(); await review(); alive = false
  await fill('Catatan draft invoice', 'Masih milik operator'); await click(input('Draft invoice sudah diperiksa')); await click(button('Simpan draft invoice'))
  expect(saved).not.toHaveBeenCalled(); expect(input('Catatan draft invoice').value).toBe('Masih milik operator')
})
it('uses the exact previous cursor and original query when paging the Mandor master', async () => {
  await mount(); await click(container.querySelector<HTMLInputElement>('input[value=MANDOR]')!)
  client.rpc.mockImplementation(async (_name, p) => {
    const all = buyerOptions(), second = p.p_after === buyerId
    return {data: {...all, rows: [all.rows[second ? 1 : 0]], has_more: !second, next_after: second ? null : buyerId}, error: null}
  })
  await fill('Cari mandor pembeli', 'Epi'); await click(button('Cari mandor')); await click(button('Mandor berikutnya'))
  expect(button('M2 · Epi')).toBeDefined(); await fill('Cari mandor pembeli', 'Belum dicari'); await click(button('Mandor sebelumnya'))
  expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_get_mandor_shop_buyers_v1', {p_sales_action: 'EDIT', p_query: 'Epi', p_after: null, p_limit: 25}])
  expect(button('M1 · Epi')).toBeDefined(); expect(button('M2 · Epi')).toBeUndefined()
})

it('holds the store picker until the existing draft buyer classification resolves without losing edited lines', async () => {
  let finish!: (v: unknown) => void
  client.rpc.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  await mount(buyerCustomer); expect(container.querySelector('[aria-label="Pilih pelanggan invoice"]')).toBeNull()
  await fill('Jumlah invoice 1', '2'); expect(button('Simpan draft invoice').disabled).toBe(true)
  await act(async () => finish({data: classification(buyerCustomer), error: null})); await flush()
  expect(container.querySelector<HTMLInputElement>('input[value=MANDOR]')!.checked).toBe(true)
  expect(input('Jumlah invoice 1').value).toBe('2'); expect(container.querySelector('[aria-label="Pilih pelanggan invoice"]')).toBeNull()
})
