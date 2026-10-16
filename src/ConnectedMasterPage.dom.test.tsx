// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedMasterPage from './ConnectedMasterPage'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const cus = '11111111-1111-4111-8111-111111111111', mandor = '22222222-2222-4222-8222-222222222222', model = '33333333-3333-4333-8333-333333333333'
const jahit = '44444444-4444-4444-8444-444444444444', rateId = '55555555-5555-4555-8555-555555555555'
const token = 'a'.repeat(32)
const customer = (extra: Record<string, unknown> = {}) => ({ id: cus, code: 'CUS-1', name: 'Toko Satu', active: true, phone: '0812', address: null,
  created_at: '2026-10-01T00:00:00+00:00', updated_at: '2026-10-01T00:00:00+00:00', ...extra })
const ws = (kind: string, selected: Record<string, unknown> | null, extra: Record<string, unknown> = {}) => ({ contract_version: 'cp7.master-workspace.v1', kind,
  can_write: true, can_price: true, today: '2026-10-16',
  page: { total: 1, rows: [kind === 'MANDOR' ? { id: mandor, code: 'MDR-1', name: 'Mandor Satu', active: true, attendance_required: true, is_special: false }
    : { id: cus, code: 'CUS-1', name: 'Toko Satu', active: true, phone: '0812' }], offset: 0, limit: 20, query: '', status: 'ACTIVE' },
  selected, selected_missing: false, options: {}, ...extra })
const sel = (entity: Record<string, unknown>, extra: Record<string, unknown> = {}) => ({ entity, review_token: token, usage: { sales: 0, sales_draft: 0, returns: 0, opening: 0 },
  used: false, deactivate_blockers: [], audit: [{ at: '2026-10-01T03:00:00+00:00', table: 'customers', action: 'INSERT', actor: 'Owner', reason: 'Pelanggan baru', fields: ['customer_code'] }], ...extra })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset()
  auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...recoveryIdentity.identity.permissions, 'master.customer.view', 'master.customer.manage'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: 'shared', mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
function button(name: string) {
  const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === name || b.getAttribute('aria-label') === name)
  if (!b) throw new Error(`Missing ${name}: ${container.textContent}`); return b
}
const has = (name: string) => [...container.querySelectorAll('button')].some(b => b.textContent === name || b.getAttribute('aria-label') === name)
async function click(name: string) { await act(async () => button(name).click()); await settle() }
function field(label: string) { const el = container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`); if (!el) throw new Error(`Missing ${label}: ${container.textContent}`); return el }
async function type(label: string, value: string) {
  const el = field(label), proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype
  await act(async () => { Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
}
async function check(label: string) { await act(async () => field(label).click()); await settle() }
const saves = () => client.rpc.mock.calls.filter(([n]) => n === 'erp_cp7_save_master_v1' || n === 'erp_cp7_save_work_rate_v1')

describe('layar data master tersambung (D15-3)', () => {
  it('reads the active list first and creates a customer with a closed payload, then opens it', async () => {
    let created = false
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_master_v1') {
        const q = args.p_query as Record<string, unknown>
        return { data: ws('CUSTOMER', q.id && created ? sel(customer({ code: 'CUS-9', name: 'Toko Baru', id: cus })) : null), error: null }
      }
      if (name === 'erp_cp7_save_master_v1') { created = true
        return { data: { contract_version: 'cp7.master-outcome.v1', kind: 'COMMITTED_OUTCOME', master_kind: 'CUSTOMER', action: 'CREATE', request_id: args.p_request,
          id: cus, entity: customer({ code: 'CUS-9', name: 'Toko Baru' }), review_token: token }, error: null } }
      throw new Error(name)
    })
    await act(async () => root.render(<ConnectedMasterPage view="master-customers"/>)); await settle()
    expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_master_v1', { p_kind: 'CUSTOMER', p_query: { q: '', status: 'ACTIVE', offset: 0, limit: 20, id: null } })
    expect(container.textContent).toContain('CUS-1 · Toko Satu')
    await click('Tambah pelanggan')
    await type('Kode', 'cus-9'); await type('Nama pelanggan', ' Toko Baru '); await type('Alasan simpan pelanggan', 'Pelanggan baru buka')
    expect(button('Simpan pelanggan').disabled).toBe(true)
    await check('simpan pelanggan sudah diperiksa')
    await click('Simpan pelanggan')
    expect(saves()).toHaveLength(1)
    const [, args] = saves()[0]
    expect(args.p_kind).toBe('CUSTOMER')
    expect(args.p_payload).toEqual({ action: 'CREATE', reason: 'Pelanggan baru buka', fields: { code: 'cus-9', name: 'Toko Baru', phone: null, address: null } })
    expect(container.textContent).toContain('Tersimpan: pelanggan CUS-9 · Toko Baru dibuat dan langsung bisa dipakai.')
    expect(client.rpc).toHaveBeenLastCalledWith('erp_cp7_get_master_v1', { p_kind: 'CUSTOMER', p_query: { q: '', status: 'ACTIVE', offset: 0, limit: 20, id: cus } })
  })

  it('keeps the code of a used customer, sends the reviewed token, and shows why deactivation is refused', async () => {
    const used = sel(customer(), { used: true, usage: { sales: 3, sales_draft: 1, returns: 0, opening: 0 }, deactivate_blockers: [{ kind: 'OPEN_SALES_DRAFT', count: 1 }] })
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_master_v1') return { data: ws('CUSTOMER', (args.p_query as Record<string, unknown>).id ? used : null), error: null }
      return { data: null, error: { code: 'P0001', message: 'CP7_MASTER_CODE_IN_USE' } }
    })
    await act(async () => root.render(<ConnectedMasterPage view="master-customers"/>)); await settle()
    await click('Pilih pelanggan CUS-1')
    expect(container.textContent).toContain('Penjualan: 3')
    expect(container.textContent).toContain('Draf penjualan: 1')
    expect(container.textContent).toContain('"Pelanggan baru"')
    await click('Nonaktifkan')
    expect(container.textContent).toContain('Masih ada 1 draf penjualan untuk pelanggan ini.')
    expect(has('Nonaktifkan pelanggan')).toBe(false)
    await click('Batal'); await click('Ubah')
    expect(field('Kode').disabled).toBe(true)
    await type('Nama pelanggan', 'Toko Satu Jaya'); await type('Alasan simpan pelanggan', 'Nama toko dibetulkan'); await check('simpan pelanggan sudah diperiksa')
    await click('Simpan pelanggan')
    expect(saves()[0][1].p_payload).toEqual({ action: 'UPDATE', reason: 'Nama toko dibetulkan', id: cus, review_token: token,
      fields: { code: 'CUS-1', name: 'Toko Satu Jaya', phone: '0812', address: null } })
    expect(container.textContent).toContain('Kode tidak bisa diganti karena data ini sudah dipakai transaksi.')
  })

  it('is read-only without the manage right', async () => {
    client.rpc.mockResolvedValue({ data: ws('CUSTOMER', null, { can_write: false, can_price: false }), error: null })
    await act(async () => root.render(<ConnectedMasterPage view="master-customers"/>)); await settle()
    expect(has('Tambah pelanggan')).toBe(false)
    expect(container.textContent).toContain('hanya bisa melihat pelanggan')
  })

  it('needs the date an attendance or Special change applies from, and opens the Mandor rates for the chosen Mandor', async () => {
    const m = { id: mandor, code: 'MDR-1', name: 'Mandor Satu', active: true, attendance_required: true, notes: null, created_at: '2026-10-01T00:00:00+00:00',
      updated_at: '2026-10-01T00:00:00+00:00', policies: [{ id: rateId, effective_from: '2026-10-01', effective_to: null, is_special: false, attendance_required: true, reason: 'baru', row_version: 1 }] }
    const rates = (component: Record<string, unknown>) => ({ contract_version: 'cp7.work-rate-workspace.v1', can_write: true, can_price: true, today: '2026-10-16',
      contractor: { id: mandor, code: 'MDR-1', name: 'Mandor Satu', active: true, attendance_required: true, is_special: false },
      models: { total: 1, offset: 0, query: '', rows: [{ id: model, code: 'MDL-1', name: 'Model Satu', active: true, components: 1 }] },
      model: { id: model, code: 'MDL-1', name: 'Model Satu', active: true, current_bom_id: rateId, bom_review_token: 'b'.repeat(32),
        bom: [{ id: rateId, version_no: 1, effective_from: '2025-12-31T17:00:00+00:00', effective_to: null, is_active: true, notes: null, last_use: null,
          items: [{ component_id: jahit, code: 'JAHIT', name: 'Jahit', sequence_no: 1, default_rate: '2.00' }] }],
        components: [component] }, component_catalog: [{ id: jahit, code: 'JAHIT', name: 'Jahit', category: 'LABOR', sequence_default: 10 }] })
    const comp = { component_id: jahit, code: 'JAHIT', name: 'Jahit', default_rate: '2.00', in_current_bom: true, versions: [], current: null, review_token: 'c'.repeat(32) }
    auth.current = { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions: [...recoveryIdentity.identity.permissions, 'master.workforce.view', 'master.workforce.manage', 'master.price.edit_draft'] } }
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_master_v1') return { data: ws('MANDOR', (args.p_query as Record<string, unknown>).id ? sel(m, { usage: {} }) : null), error: null }
      if (name === 'erp_cp7_get_work_rates_v1') {
        const q = args.p_query as Record<string, unknown>
        return { data: { ...rates(comp), contractor: q.contractor_id ? rates(comp).contractor : null, model: q.model_id ? rates(comp).model : null }, error: null }
      }
      if (name === 'erp_cp7_save_work_rate_v1') return { data: { contract_version: 'cp7.work-rate-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'SET_RATE',
        request_id: args.p_request, id: rateId, after: [], review_token: 'd'.repeat(32) }, error: null }
      return { data: null, error: { code: 'P0001', message: 'CP7_MASTER_POLICY_DATE' } }
    })
    await act(async () => root.render(<ConnectedMasterPage view="master-workforce"/>)); await settle()
    expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_work_rates_v1', { p_query: { contractor_id: null, model_id: null, q: '', offset: 0 } })
    await click('Pilih mandor MDR-1')
    expect(container.textContent).toContain('Mandor Special hari ini')
    await click('Ubah')
    await check('Mandor Special'); await type('Alasan simpan mandor', 'Mandor jadi Special'); await check('simpan mandor sudah diperiksa')
    await click('Simpan mandor')
    expect(saves()[0][1].p_payload).toMatchObject({ action: 'UPDATE', fields: { is_special: true, policy_from: null } })
    expect(container.textContent).toContain('Isi tanggal mulai berlaku untuk perubahan "Wajib absensi" atau "Mandor Special".')
    expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_work_rates_v1', { p_query: { contractor_id: mandor, model_id: null, q: '', offset: 0 } })
    await click('Pilih model MDL-1')
    expect(container.textContent).toContain('Belum ada tarif mandor ini; upah memakai tarif bawaan model Rp2/pcs.')
    await type('Tarif JAHIT', '1500'); await type('Tarif JAHIT berlaku mulai', '2026-10-01'); await type('Alasan tarif JAHIT', 'Tarif jahit mandor baru')
    await check('Tarif JAHIT sudah diperiksa'); await click('Simpan tarif JAHIT')
    const rate = saves().find(([n]) => n === 'erp_cp7_save_work_rate_v1')!
    expect(rate[1]).toMatchObject({ p_action: 'SET_RATE', p_payload: { contractor_id: mandor, model_id: model, work_component_id: jahit, review_token: 'c'.repeat(32),
      rate: '1500', effective_date: '2026-10-01', reason: 'Tarif jahit mandor baru' } })
    expect(container.textContent).toContain('Tersimpan: tarif Rp1.500/pcs berlaku mulai 2026-10-01.')
  })
})
