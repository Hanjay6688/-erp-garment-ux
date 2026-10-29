// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { beforeEach, afterEach, it, expect, vi } from 'vitest'
import ConnectedProductConversionPage from './ConnectedProductConversionPage'
import ConnectedSkuMasterPage from './ConnectedSkuMasterPage'
import { recoveryRuntime } from '../tests/fixtures/productionRecovery'
const mock = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => mock.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mock }))
const u = (n: number) => `10000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const source = { product_id: u(1), sku: '1002', product_name: 'Vivo 1002 31', brand_name: 'Vivo', size: '31', location_id: u(9), location_name: 'Gudang A', stock: { physical: 10, reserved: 1, available: 9 } }
const targets = [{ id: u(2), sku: '1001', product_name: 'Widie 1001 34', brand_name: 'Widie', size: '34', recommended: true }, { id: u(3), sku: '1003', product_name: 'Lain 1003 36', brand_name: 'Lain', size: '36', recommended: false }]
let root: Root, box: HTMLDivElement, denied: boolean, stale: boolean, available: number
function workspace(filters: Record<string, unknown> = {}) {
  const selection = filters.selection as { source_product_id: string; target_product_id: string | null; location_id: string } | undefined
  return { contract_version: 'cp7.sku-conversion.v1', lots: [], targets, documents: [], total: 0, page: 1, page_size: 25, targets_total: 2, target_page: 1, documents_total: 0, document_page: 1, sources: [{ ...source, stock: { physical: available + 1, available, reserved: 1 } }], sources_total: 1,
    ...(selection ? { selection: { ...selection, source_stock: { physical: available + 1, available, reserved: 1 }, target_stock: selection.target_product_id ? { physical: 4, available: 4, reserved: 0 } : null } } : {}) }
}
const detail = (p: Record<string, unknown>) => ({ ...p, location_name: 'Gudang A', source_sku: '1002', target_sku: '1001', source_revision: 'server-reviewed', source_stock: { physical: available + 1, available, reserved: 1 }, target_stock: { physical: 4, available: 4, reserved: 0 }, source_after: { physical: available + 1 - Number(p.qty_pcs), available: available - Number(p.qty_pcs), reserved: 1 }, target_after: { physical: 4 + Number(p.qty_pcs), available: 4 + Number(p.qty_pcs), reserved: 0 }, cost: { source_value: '40.04' }, allocations: [{ source_lot_id: u(10), lot_number: 'L1', qty_pcs: Number(p.qty_pcs), source_revision: 'lot-reviewed', source_value: '40.04' }] })
const ok = (data: unknown) => ({ data, error: null })
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); mock.rpc.mockReset(); denied = false; stale = false; available = 9
  mock.auth = { runtime: recoveryRuntime, identity: { status: 'AUTHORIZED', profile: { id: u(90), role: 'OWNER', rowVersion: 1, roleRowVersion: 1, isActive: true }, permissions: ['warehouse.brand_conversion.view', 'warehouse.brand_conversion.post', 'warehouse.brand_conversion.reverse', 'master.product.view', 'master.product.manage'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_n: string, _o: unknown, fn: (lock: object) => Promise<unknown>) => fn({}) } })
  mock.rpc.mockImplementation(async (name: string, args: Record<string, any>) => {
    if (name === 'erp_get_product_conversion_workspace_v1') return denied ? { data: null, error: { status: 403, code: '42501', message: 'Hak berubah' } } : ok(args.p_filters.preview ? { preview: detail(args.p_filters.preview) } : workspace(args.p_filters))
    if (name === 'erp_save_product_conversion_action_v1') {
      if (stale) { available = 5; return { data: null, error: { code: 'P0001', message: 'STALE_VERSION: stok berubah; periksa pratinjau terbaru' } } }
      const p = args.p_payload, id = args.p_client_request_id; const v = detail(p); available -= Number(p.qty_pcs)
      return ok({ ...v, conversion_id: id, request_id: id, action: 'POST', status: 'POSTED', destination_lot_id: u(81), conversion_ids: [id], destination_lot_ids: [u(81)] })
    }
    throw new Error('Unexpected RPC ' + name)
  })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const settle = async () => act(async () => { await new Promise(r => setTimeout(r, 0)) })
async function click(name: string) { const b = [...box.querySelectorAll('button')].find(b => b.textContent?.trim() === name); expect(b, name).toBeTruthy(); await act(async () => b!.click()); await settle() }
const field = (name: string) => [...box.querySelectorAll('label')].find(l => l.firstChild?.textContent === name)?.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input,select,textarea')
async function change(name: string, value: string) {
  const e = field(name)!; expect(e, name).toBeTruthy()
  await act(async () => { const proto = e.tagName === 'SELECT' ? HTMLSelectElement.prototype : e.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(e, value); e.dispatchEvent(new Event(e.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })) }); await settle()
}
async function prepare(target = u(2)) {
  await act(async () => root.render(<ConnectedProductConversionPage/>)); await settle()
  await change('SKU asal dan gudang', `${u(1)}:${u(9)}`); await change('SKU tujuan', target); await change('Jumlah PCS', '2'); await change('Waktu fisik · WIB', '2026-10-20T07:00'); await change('Alasan', 'Barang tercampur laundry')
}
const writes = () => mock.rpc.mock.calls.filter(([name]) => name === 'erp_save_product_conversion_action_v1')

it('shows fresh product/size/location before-after stock, recommendations and other target models/sizes, with no operator lot selection', async () => {
  await prepare(u(3))
  expect(box.textContent).toContain('Asal · fisik 10 → 8 PCS'); expect(box.textContent).toContain('Tujuan · fisik 4 → 6 PCS')
  expect(box.textContent).toContain('dicadangkan 1 PCS'); expect(box.textContent).toContain('Padanan · Widie · 1001 · ukuran 34')
  expect((field('SKU tujuan') as HTMLSelectElement).value).toBe(u(3)); expect(field('Lot dan gudang')).toBeUndefined()
  const reads = mock.rpc.mock.calls.filter(([name]) => name === 'erp_get_product_conversion_workspace_v1')
  expect(reads.some(([, args]) => args.p_filters.selection?.target_product_id === u(3))).toBe(true)
  await click('Lihat pratinjau'); expect(box.textContent).toContain('Asal: 10 → 8 PCS; tersedia 9 → 7 PCS')
  await click('Catat konversi fisik'); expect(writes()).toHaveLength(1)
  expect(writes()[0][1].p_payload).toMatchObject({ source_product_id: u(1), target_product_id: u(3), location_id: u(9), qty_pcs: 2, expected_version: 'server-reviewed', physical_at: '2026-10-20T00:00:00.000Z' })
})
it('a failed fresh read clears old quantities and offers no write or fabricated zero', async () => {
  await prepare(); denied = true; await click('Muat ulang')
  expect(box.textContent).toContain('Stok belum diketahui'); expect(box.textContent).not.toContain('Asal · fisik'); expect(box.textContent).not.toContain('Catat konversi fisik'); expect(writes()).toHaveLength(0)
})
it('refuses a fresh stock response for a different target instead of showing its numbers under the selected SKU', async () => {
  await prepare()
  const original = mock.rpc.getMockImplementation()!
  mock.rpc.mockImplementation(async (name: string, args: Record<string, any>) => {
    const r = await original(name, args)
    if (name === 'erp_get_product_conversion_workspace_v1' && r.data?.selection) r.data.selection.target_product_id = u(3)
    return r
  })
  await click('Muat ulang'); expect(box.textContent).toContain('Lingkup stok berubah atau tidak cocok'); expect(box.textContent).not.toContain('Tujuan · fisik'); expect(writes()).toHaveLength(0)
})
it.each(['SEARCH', 'PAGE'] as const)('clears the reviewed target when %s removes it from the visible options and requires a new choice', async (mode) => {
  const original = mock.rpc.getMockImplementation()!
  mock.rpc.mockImplementation(async (name: string, args: Record<string, any>) => {
    const r = await original(name, args)
    if (name === 'erp_get_product_conversion_workspace_v1' && !args.p_filters.preview && r.data) {
      r.data.targets_total = 26; r.data.target_page = args.p_filters.target_page ?? 1
      if (args.p_filters.target_query || r.data.target_page === 2) r.data.targets = [targets[1]]
    }
    return r
  })
  await prepare(); await click('Lihat pratinjau'); expect(box.textContent).toContain('Catat konversi fisik')
  if (mode === 'SEARCH') { await change('Cari SKU tujuan', 'Lain'); await click('Cari tujuan') } else await click('Tujuan berikutnya')
  const select = field('SKU tujuan') as HTMLSelectElement
  expect(select.value).toBe(''); expect([...select.options].map(o => o.value)).toEqual(['', u(3)])
  expect(box.textContent).not.toContain('Catat konversi fisik'); expect(box.textContent).not.toContain('Tujuan · fisik')
  const readsBefore = mock.rpc.mock.calls.filter(([name, args]) => name === 'erp_get_product_conversion_workspace_v1' && args.p_filters.preview).length
  await click('Lihat pratinjau') // disabled without an explicitly visible target
  expect(mock.rpc.mock.calls.filter(([name, args]) => name === 'erp_get_product_conversion_workspace_v1' && args.p_filters.preview)).toHaveLength(readsBefore)
  expect(writes()).toHaveLength(0)
  await change('SKU tujuan', u(3)); await click('Lihat pratinjau'); await click('Catat konversi fisik')
  expect(writes()).toHaveLength(1); expect(writes()[0][1].p_payload.target_product_id).toBe(u(3))
})
it('stale rejection refreshes authoritative quantities and requires a new reviewed preview', async () => {
  await prepare(); await click('Lihat pratinjau'); stale = true; await click('Catat konversi fisik')
  expect(writes()).toHaveLength(1); expect(box.textContent).toContain('Asal · fisik 6 → 4 PCS'); expect(box.textContent).toContain('STALE_VERSION')
  expect(box.textContent).not.toContain('Catat konversi fisik'); expect(localStorage.getItem('irrelevant')).toBeNull()
})
it('double click shares one immutable request and cannot duplicate the stock command', async () => {
  await prepare(); await click('Lihat pratinjau'); const b = [...box.querySelectorAll('button')].find(b => b.textContent === 'Catat konversi fisik')!
  await act(async () => { b.click(); b.click() }); await settle(); expect(writes()).toHaveLength(1)
})
it.each(['SEARCH', 'PAGE'] as const)('master pair editing is one group action and %s cannot save an invisible unsaved partner', async (mode) => {
  const one = { id: u(21), sku: '1002', brand_name: 'Vivo', model_name: 'Classic', members: [{ id: u(1), size: '31' }, { id: u(4), size: '32' }, { id: u(5), size: '33' }] }, two = { id: u(22), sku: '1001', brand_name: 'Widie', model_name: 'Slim', members: [{ id: u(2), size: '34' }] }
  const other = { ...two, id: u(23), sku: '9999', brand_name: 'Lain' }
  let current: typeof two | null = null
  mock.rpc.mockImplementation(async (name: string, args: Record<string, any>) => {
    if (name === 'erp_get_sku_workspace_v1') return ok({ at: '2026-10-20T00:00:00Z', page: 1, page_size: 50, groups_total: 1, products_total: 0, can_edit: false, products: [], selected_products: [], related_groups: [], lookups: null, legacy_basis: null,
      groups: [{ ...one, brand_id: u(31), model_id: u(41), color_name: 'Blue', revision: '1', effective_from: '2026-01-01T00:00:00Z', members: one.members.map((m, i) => ({ ...m, size_id: u(51 + i) })), settings: null, counterpart: current }], pairing: { revision: current ? 'revision-two' : 'revision-one', source: args.p_filters.pair_source_id ? one : null, current, options: args.p_filters.pair_query || args.p_filters.pair_page === 2 ? [two] : [two, other], total: 51, page: args.p_filters.pair_page ?? 1, page_size: 50, can_edit: true } })
    if (name === 'erp_save_sku_action_v1') { current = two; return ok({ ...args.p_payload, request_id: args.p_client_request_id, action: 'SAVE_PAIR', status: 'SAVED', revision: 'revision-two', removed: [] }) }
    throw Error(name)
  })
  await act(async () => root.render(<ConnectedSkuMasterPage/>)); await settle(); await click('Atur padanan 1002'); await change('SKU padanan', u(22)); await change('Alasan padanan', 'Padanan untuk laundry tercampur'); await click('Simpan padanan dua arah')
  const sent = mock.rpc.mock.calls.filter(([n]) => n === 'erp_save_sku_action_v1'); expect(sent).toHaveLength(1); expect(sent[0][1].p_action).toBe('SAVE_PAIR')
  expect(sent[0][1].p_payload).toMatchObject({ source_group_id: u(21), target_group_id: u(22), expected_version: 'revision-one' }); expect(box.textContent).toContain('Widie · 1001')
  expect(mock.rpc.mock.calls.some(([name]) => name.includes('conversion_action'))).toBe(false)
  await change('SKU padanan', u(23)); await change('Alasan padanan', 'Unsaved new target')
  if (mode === 'SEARCH') { await change('Cari padanan', 'Widie'); await click('Cari padanan') } else await click('Padanan berikutnya')
  expect((field('SKU padanan') as HTMLSelectElement).value).toBe(u(22))
  expect((field('Alasan padanan') as HTMLInputElement).value).toBe('')
  await click('Simpan padanan dua arah')
  expect(mock.rpc.mock.calls.filter(([n]) => n === 'erp_save_sku_action_v1')).toHaveLength(1)

})
